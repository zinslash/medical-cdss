"""
sslcommerz.py  —  real SSLCommerz adapter (sandbox and live).

payments.py talks to this through three functions, so switching between the
local mock and the real gateway is one line in .env:

    PAYMENT_PROVIDER=mock          # mock_gateway.py on port 4000
    PAYMENT_PROVIDER=sslcommerz    # the real sandbox

Docs: https://developer.sslcommerz.com/doc/v4/

WHAT WORKS ON LOCALHOST
  - session creation        yes (your server calls out to them)
  - hosted payment page     yes (the customer's browser goes to sslcommerz.com)
  - success/fail/cancel     yes (their page POSTs the browser back to you)
  - validation API          yes (your server calls out to them)
  - IPN webhook             NO  -- they cannot reach 127.0.0.1

The IPN is the only piece that needs a public URL. The browser redirect still
triggers verification, so a localhost demo records payments correctly. Use
ngrok and set the IPN URL in the sandbox panel if you want the webhook too.
"""

import hashlib
import os

import requests

IS_LIVE = os.environ.get("SSLC_IS_LIVE", "false").lower() == "true"

BASE = os.environ.get("SSLC_BASE_OVERRIDE") or (
    "https://securepay.sslcommerz.com" if IS_LIVE else "https://sandbox.sslcommerz.com")
INIT_URL = f"{BASE}/gwprocess/v4/api.php"
VALIDATE_URL = f"{BASE}/validator/api/validationserverAPI.php"
TRAN_QUERY_URL = f"{BASE}/validator/api/merchantTransIDvalidationAPI.php"

# Sandbox demo credentials. Register at https://developer.sslcommerz.com to get
# your own -- no trade licence needed for a sandbox account.
STORE_ID = os.environ.get("SSLC_STORE_ID", "testbox")
STORE_PASSWD = os.environ.get("SSLC_STORE_PASSWD", "qwerty")

# SSLCommerz treats both of these as "the money is good".
SUCCESS_STATUSES = {"VALID", "VALIDATED"}


def create_session(*, order_id, amount, currency, product_name,
                   customer_name, customer_email, customer_phone,
                   success_url, fail_url, cancel_url, ipn_url):
    """
    Returns (checkout_url, error). Exactly one of them is None.

    SSLCommerz wants form-encoded fields, not JSON, and rejects the request
    if any of the customer or product fields are missing -- even for a
    non-physical service, where most of them are meaningless.
    """
    payload = {
        "store_id": STORE_ID,
        "store_passwd": STORE_PASSWD,
        "total_amount": f"{float(amount):.2f}",
        "currency": currency or "BDT",
        "tran_id": order_id,

        "success_url": success_url,
        "fail_url": fail_url,
        "cancel_url": cancel_url,
        "ipn_url": ipn_url,

        # Product fields — all three are required.
        "product_name": product_name[:255],
        "product_category": "Healthcare",
        "product_profile": "non-physical-goods",

        # Customer fields — all required, even the address ones.
        "cus_name": customer_name or "Patient",
        "cus_email": customer_email or "patient@example.com",
        "cus_add1": "Dhaka",
        "cus_city": "Dhaka",
        "cus_postcode": "1000",
        "cus_country": "Bangladesh",
        "cus_phone": customer_phone or "01700000000",

        # A consultation ships nothing, but these are still mandatory.
        "shipping_method": "NO",
        "num_of_item": 1,
    }

    try:
        res = requests.post(INIT_URL, data=payload, timeout=30)
        data = res.json()
    except Exception as e:
        return None, f"Could not reach SSLCommerz: {e}"

    if data.get("status") != "SUCCESS":
        # failedreason is usually the useful one; GatewayPageURL is absent.
        reason = data.get("failedreason") or data.get("status") or "Unknown error"
        return None, reason

    url = data.get("GatewayPageURL")
    if not url:
        return None, "SSLCommerz returned no GatewayPageURL"

    return url, None


def validate(val_id):
    """
    Server-to-server confirmation. This — not the browser redirect, not the
    IPN body — is what decides whether an order is paid.

    Returns a dict in the same shape the mock gateway uses, so settle_order()
    in payments.py needs no branching.
    """
    try:
        res = requests.get(VALIDATE_URL, params={
            "val_id": val_id,
            "store_id": STORE_ID,
            "store_passwd": STORE_PASSWD,
            "format": "json",
        }, timeout=30)
        d = res.json()
    except Exception as e:
        return {"status": "FAILED", "failedreason": f"Validation call failed: {e}"}

    return _normalise(d)


def query_by_tran_id(tran_id):
    """
    Ask SSLCommerz what happened to an order, using OUR order id rather than
    their val_id.

    This is the reconciliation path. It matters because the IPN cannot reach a
    localhost server, so if the customer's browser never made it back — they
    closed the tab, the redirect was blocked, the network dropped — the order
    sits at 'pending' even though the money moved. This asks directly.

    Returns the same normalised shape as validate().
    """
    try:
        res = requests.get(TRAN_QUERY_URL, params={
            "tran_id": tran_id,
            "store_id": STORE_ID,
            "store_passwd": STORE_PASSWD,
            "format": "json",
        }, timeout=30)
        d = res.json()
    except Exception as e:
        return {"status": "FAILED", "failedreason": f"Query call failed: {e}"}

    # This endpoint answers with a list of attempts under "element".
    elements = d.get("element") or []
    if not elements:
        return {"status": "FAILED",
                "failedreason": d.get("errorReason") or "No transaction found"}

    # Prefer a successful attempt; a customer may have retried after a failure.
    best = next((e for e in elements
                 if (e.get("status") or "").upper() in SUCCESS_STATUSES), elements[0])

    return _normalise(best)


def _normalise(d):
    raw_status = (d.get("status") or "").upper()

    if raw_status in SUCCESS_STATUSES:
        status = "VALID"
    elif raw_status == "CANCELLED":
        status = "CANCELLED"
    else:
        status = "FAILED"

    return {
        "status": status,
        "val_id": d.get("val_id"),
        "tran_id": d.get("tran_id"),
        "amount": d.get("amount"),
        "currency": d.get("currency"),
        "method": _method_from(d),
        "card_brand": d.get("card_brand") or d.get("card_type"),
        "bank_tran_id": d.get("bank_tran_id"),
        "tran_date": d.get("tran_date"),
        "failedreason": d.get("error") or d.get("failedreason"),
        "raw_status": raw_status,
    }


def _method_from(d):
    card_type = (d.get("card_type") or "").upper()
    if "BKASH" in card_type:
        return "BKASH"
    if "NAGAD" in card_type:
        return "NAGAD"
    if "ROCKET" in card_type or "DBBL MOBILE" in card_type:
        return "ROCKET"
    if any(b in card_type for b in ("VISA", "MASTER", "AMEX", "DBBL NEXUS")):
        return "CARD"
    return card_type.split("-")[0] or "UNKNOWN"


def verify_ipn(form):
    """
    SSLCommerz signs IPN posts with verify_sign / verify_key.

    The scheme: take the fields named in verify_key, sort them, append
    store_passwd hashed with MD5, then MD5 the whole string. Compare to
    verify_sign.

    Returns False when the signature is absent or wrong. Note that a passing
    signature still isn't proof of payment — always call validate() after.
    """
    verify_sign = form.get("verify_sign")
    verify_key = form.get("verify_key")
    if not verify_sign or not verify_key:
        return False

    keys = verify_key.split(",")
    pairs = {k: form.get(k, "") for k in keys}
    pairs["store_passwd"] = hashlib.md5(STORE_PASSWD.encode()).hexdigest()

    base = "&".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    computed = hashlib.md5(base.encode()).hexdigest()

    return computed == verify_sign


def describe():
    return {
        "provider": "sslcommerz",
        "environment": "live" if IS_LIVE else "sandbox",
        "store_id": STORE_ID,
        "init_url": INIT_URL,
    }