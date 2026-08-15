"""
MOCK PAYMENT GATEWAY  —  sandbox only. No real money moves. Delete before launch.

Standalone service, run it beside app.py:

    python mock_gateway.py          # http://127.0.0.1:4000

Copies the handshake SSLCommerz and bKash use, so going live is a credentials
change rather than a rewrite:

    1. app.py   --POST /api/v1/session-->  gateway   (returns redirect URL)
    2. patient  --GET  /checkout/<key>-->  gateway   (hosted payment page)
    3. patient pays                        gateway
    4. gateway --redirect--> /payment/return
    5. gateway --POST--> /payment/ipn                (signed, server-to-server)
    6. app.py   --POST /api/v1/validate--> gateway   (the source of truth)
"""

import hashlib
import hmac
import html
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import requests
import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="Mock Payment Gateway (sandbox)")

PORT = int(os.environ.get("GATEWAY_PORT", 4000))
BASE_URL = os.environ.get("GATEWAY_BASE_URL", f"http://127.0.0.1:{PORT}")

# Fire every webhook twice. Real gateways genuinely do this — your app must
# survive it. Leave it on while developing.
DUPLICATE_IPN = os.environ.get("DUPLICATE_IPN", "true").lower() == "true"

STORES = {"testbox": {"store_passwd": "testbox@ssl"}}
SESSIONS = {}
LOCK = threading.Lock()

TEST_CARDS = {
    "4111111111111111": ("VALID", "VISA", None),
    "5555555555554444": ("VALID", "MASTERCARD", None),
    "4000000000000002": ("FAILED", "VISA", "Card declined by issuer"),
    "4000000000009995": ("FAILED", "VISA", "Insufficient funds"),
    "4000000000000069": ("FAILED", "VISA", "Card expired"),
}

TEST_WALLETS = {
    "01700000000": ("VALID", None),
    "01700000001": ("FAILED", "Insufficient balance in wallet"),
    "01700000002": ("FAILED", "Wrong PIN entered"),
}

WALLET_OTP = "123456"
WALLET_PIN = "12345"


def rid(p):
    return p + secrets.token_hex(6).upper()


def money(n):
    return f"{float(n):.2f}"


def sign(payload, secret):
    base = "&".join(f"{k}={payload[k]}" for k in sorted(payload)
                    if k != "signature" and payload[k] is not None)
    return hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()


def with_params(url, s):
    parts = list(urlparse(url))
    q = dict(parse_qsl(parts[4]))
    q.update({"tran_id": s["tran_id"], "val_id": s["val_id"], "status": s["status"]})
    parts[4] = urlencode(q)
    return urlunparse(parts)


def fire_ipn(s):
    if not s.get("ipn_url"):
        return
    payload = {
        "val_id": s["val_id"], "tran_id": s["tran_id"], "status": s["status"],
        "amount": money(s["amount"]), "currency": s["currency"],
        "method": s["method"] or "", "card_brand": s["card_brand"] or "",
        "bank_tran_id": s["bank_tran_id"] or "", "tran_date": s["tran_date"] or "",
    }
    payload["signature"] = sign(payload, STORES[s["store_id"]]["store_passwd"])

    def deliver():
        for d in range(2 if DUPLICATE_IPN else 1):
            for attempt in range(1, 4):
                try:
                    r = requests.post(s["ipn_url"], json=payload, timeout=10)
                    print(f"[ipn] {s['tran_id']} delivery {d+1} -> {r.status_code}", flush=True)
                    if r.ok:
                        break
                except Exception as e:
                    print(f"[ipn] {s['tran_id']} attempt {attempt} failed: {e}", flush=True)
                time.sleep(attempt)

    threading.Thread(target=deliver, daemon=True).start()


# ===========================================================================
# 1. SESSION CREATE
# ===========================================================================
@app.post("/api/v1/session")
async def create_session(request: Request):
    b = await request.json()
    store = STORES.get(b.get("store_id"))
    if not store or store["store_passwd"] != b.get("store_passwd"):
        return JSONResponse({"status": "FAILED", "failedreason": "Invalid store credentials"}, 401)
    if not b.get("tran_id"):
        return JSONResponse({"status": "FAILED", "failedreason": "tran_id is required"}, 400)
    try:
        amount = float(b.get("total_amount"))
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:
        return JSONResponse({"status": "FAILED", "failedreason": "total_amount must be positive"}, 400)

    with LOCK:
        if any(s["tran_id"] == b["tran_id"] and s["store_id"] == b["store_id"]
               for s in SESSIONS.values()):
            return JSONResponse({"status": "FAILED", "failedreason": "tran_id already used"}, 409)
        key = rid("SK")
        SESSIONS[key] = {
            "sessionkey": key, "store_id": b["store_id"], "tran_id": b["tran_id"],
            "amount": amount, "currency": b.get("currency", "BDT"), "status": "PENDING",
            "method": None, "card_brand": None, "bank_tran_id": None, "val_id": None,
            "tran_date": None, "fail_reason": None,
            "product_name": b.get("product_name", "Order"),
            "cus_name": b.get("cus_name", "Patient"),
            "success_url": b.get("success_url"), "fail_url": b.get("fail_url"),
            "cancel_url": b.get("cancel_url"), "ipn_url": b.get("ipn_url"),
        }
    print(f"[session] created {b['tran_id']} for {money(amount)}", flush=True)
    return {"status": "SUCCESS", "sessionkey": key,
            "GatewayPageURL": f"{BASE_URL}/checkout/{key}"}


# ===========================================================================
# 2 & 3. HOSTED CHECKOUT PAGE + SUBMISSION
# ===========================================================================
@app.get("/checkout/{key}", response_class=HTMLResponse)
async def checkout(key: str):
    s = SESSIONS.get(key)
    if not s:
        return HTMLResponse(page_404(), 404)
    if s["status"] != "PENDING":
        return HTMLResponse(page_closed(s), 410)
    return HTMLResponse(checkout_page(s, None))


@app.post("/checkout/{key}/pay")
async def pay(
    key: str,
    method: str = Form(None),
    card_number: str = Form(""),
    expiry: str = Form(""),
    cvv: str = Form(""),
    msisdn: str = Form(""),
    otp: str = Form(""),
    pin: str = Form(""),
):
    s = SESSIONS.get(key)
    if not s:
        return HTMLResponse(page_404(), 404)
    if s["status"] != "PENDING":
        return HTMLResponse(page_closed(s), 410)

    if method == "cancel":
        settle(s, "CANCELLED", None)
        return RedirectResponse(with_params(s["cancel_url"], s), status_code=303)

    if method == "card":
        pan = "".join(c for c in card_number if c.isdigit())
        if len(pan) < 13:
            return HTMLResponse(checkout_page(s, "Enter a full card number."))
        if not (cvv.strip().isdigit() and 3 <= len(cvv.strip()) <= 4):
            return HTMLResponse(checkout_page(s, "CVV must be 3 or 4 digits."))
        e = expiry.strip()
        if len(e) != 5 or e[2] != "/" or not (e[:2] + e[3:]).isdigit():
            return HTMLResponse(checkout_page(s, "Expiry must look like MM/YY."))
        if pan not in TEST_CARDS:
            return HTMLResponse(checkout_page(s, "Unknown test card. Use one from the list below."))
        outcome, brand, reason = TEST_CARDS[pan]
        s["method"], s["card_brand"] = "CARD", brand

    elif method == "bkash":
        num = "".join(c for c in msisdn if c.isdigit())
        if num not in TEST_WALLETS:
            return HTMLResponse(checkout_page(s, "Unknown test wallet. Use one from the list below."))
        if otp.strip() != WALLET_OTP:
            return HTMLResponse(checkout_page(s, "That OTP is not correct."))
        if pin.strip() != WALLET_PIN:
            return HTMLResponse(checkout_page(s, "That PIN is not correct."))
        outcome, reason = TEST_WALLETS[num]
        s["method"], s["card_brand"] = "BKASH", "BKASH"

    else:
        return HTMLResponse(checkout_page(s, "Pick a payment method."))

    settle(s, outcome, reason)
    target = s["success_url"] if outcome == "VALID" else s["fail_url"]
    return RedirectResponse(with_params(target, s), status_code=303)


def settle(s, status, reason):
    s["status"] = status
    s["fail_reason"] = reason
    s["val_id"] = rid("VAL")
    s["bank_tran_id"] = rid("BTX")
    s["tran_date"] = datetime.now(timezone.utc).isoformat()
    print(f"[pay] {s['tran_id']} {s['method']} -> {status}"
          + (f" ({reason})" if reason else ""), flush=True)
    fire_ipn(s)


# ===========================================================================
# 4. VALIDATION — the source of truth
# ===========================================================================
@app.post("/api/v1/validate")
async def validate(request: Request):
    b = await request.json()
    store = STORES.get(b.get("store_id"))
    if not store or store["store_passwd"] != b.get("store_passwd"):
        return JSONResponse({"status": "FAILED", "failedreason": "Invalid store credentials"}, 401)

    s = next((x for x in SESSIONS.values()
              if x["val_id"] == b.get("val_id") and x["store_id"] == b["store_id"]), None)
    if not s:
        return JSONResponse({"status": "INVALID_TRANSACTION"}, 404)

    return {
        "status": s["status"], "val_id": s["val_id"], "tran_id": s["tran_id"],
        "amount": money(s["amount"]), "currency": s["currency"], "method": s["method"],
        "card_brand": s["card_brand"], "bank_tran_id": s["bank_tran_id"],
        "tran_date": s["tran_date"], "failedreason": s["fail_reason"],
    }


@app.get("/api/v1/_transactions")
async def all_txns():
    return [{k: v for k, v in s.items()
             if k not in ("success_url", "fail_url", "cancel_url", "ipn_url")}
            for s in SESSIONS.values()]


# ===========================================================================
# Views — styled to sit next to your League Spartan / #225FFF pages
# ===========================================================================
def shell(title, body):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=League+Spartan:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
 *{{margin:0;padding:0;box-sizing:border-box;font-family:'League Spartan',-apple-system,"Segoe UI",Roboto,sans-serif}}
 body{{background:#F8FAFC;min-height:100vh;display:flex;justify-content:center;align-items:flex-start;padding:24px 16px}}
 .wrap{{width:100%;max-width:440px}}
 .band{{background:#FFF4D6;color:#8A5A00;border:1px solid #F0D48A;border-radius:12px;
   padding:10px 14px;margin-bottom:14px;font-size:12px;font-weight:600;letter-spacing:.3px}}
 .card{{background:#fff;border-radius:24px;box-shadow:0 10px 30px rgba(0,0,0,.08);overflow:hidden}}
 .head{{background:#225FFF;color:#fff;padding:26px 24px 30px;text-align:center;
   border-bottom-left-radius:24px;border-bottom-right-radius:24px}}
 .head h1{{font-size:19px;font-weight:600}}
 .head .who{{font-size:13px;opacity:.85;margin-top:3px}}
 .head .amt{{font-size:34px;font-weight:700;margin-top:14px;letter-spacing:.5px}}
 .body{{padding:22px 24px 26px}}
 .tabs{{display:flex;gap:10px;margin-bottom:18px}}
 .tabs button{{flex:1;padding:11px;border:1px solid #E2E8F0;background:#F8FAFC;color:#64748B;
   border-radius:14px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit}}
 .tabs button[aria-selected=true]{{background:#ECF1FF;border-color:#225FFF;color:#225FFF}}
 label{{display:block;font-size:13px;font-weight:500;color:#374151;margin:0 0 6px}}
 input{{width:100%;background:#ECF1FF;border:1px solid transparent;border-radius:14px;
   padding:12px 16px;font-size:16px;color:#225FFF;outline:none;font-family:inherit}}
 input:focus{{border-color:#225FFF;background:#fff;box-shadow:0 0 0 3px rgba(34,95,255,.15)}}
 .row{{display:flex;gap:12px}}.row>div{{flex:1}}
 .fg{{margin-bottom:16px}}
 .pay{{width:100%;height:52px;background:#225FFF;border:0;border-radius:26px;color:#fff;
   font-size:18px;font-weight:600;cursor:pointer;box-shadow:0 4px 12px rgba(34,95,255,.3);
   margin-top:6px;font-family:inherit}}
 .pay:hover{{background:#1A4CE0}}
 .cancel{{width:100%;padding:12px;margin-top:10px;border:0;background:none;color:#64748B;
   font-size:14px;text-decoration:underline;cursor:pointer;font-family:inherit}}
 .err{{background:#FEF2F2;border:1px solid #FECACA;color:#B91C1C;border-radius:14px;
   padding:11px 14px;font-size:14px;margin-bottom:16px}}
 .ref{{margin-top:16px;border:1px solid #E2E8F0;border-radius:16px;background:#F8FAFC}}
 .ref summary{{cursor:pointer;padding:12px 16px;font-size:13px;font-weight:600;color:#64748B}}
 .ref table{{width:100%;border-collapse:collapse;font-size:12.5px}}
 .ref td{{padding:6px 16px;border-top:1px solid #E2E8F0;color:#64748B}}
 .ref td:first-child{{color:#1E293B;font-weight:500;white-space:nowrap}}
 .done{{text-align:center;padding:36px 24px}}
 .done h1{{font-size:18px;color:#1E293B;margin-bottom:8px}}
 .done p{{font-size:14px;color:#64748B}}
</style></head><body><div class="wrap">
<div class="band">SANDBOX — test instruments only, no money moves</div>
{body}</div></body></html>"""


def checkout_page(s, error):
    cards = "".join(f"<tr><td>{p}</td><td>{r or 'Approved'}</td></tr>"
                    for p, (_, _, r) in TEST_CARDS.items())
    wallets = "".join(f"<tr><td>{m}</td><td>{r or 'Approved'}</td></tr>"
                      for m, (_, r) in TEST_WALLETS.items())
    err = f'<div class="err">{html.escape(error)}</div>' if error else ""

    return shell(f"Pay {s['currency']} {money(s['amount'])}", f"""
<div class="card">
  <div class="head">
    <h1>{html.escape(s['product_name'])}</h1>
    <div class="who">Order {html.escape(s['tran_id'])}</div>
    <div class="amt">{s['currency']} {money(s['amount'])}</div>
  </div>
  <div class="body">
    {err}
    <div class="tabs" role="tablist">
      <button type="button" role="tab" id="t-card" aria-selected="true" onclick="pick('card')">Card</button>
      <button type="button" role="tab" id="t-bkash" aria-selected="false" onclick="pick('bkash')">bKash</button>
    </div>
    <form method="post" action="/checkout/{s['sessionkey']}/pay">
      <input type="hidden" name="method" id="method" value="card">
      <div id="pane-card">
        <div class="fg"><label for="card_number">Card number</label>
          <input id="card_number" name="card_number" inputmode="numeric" autocomplete="off"
                 placeholder="4111 1111 1111 1111"></div>
        <div class="row">
          <div class="fg"><label for="expiry">Expiry</label>
            <input id="expiry" name="expiry" placeholder="12/28" autocomplete="off"></div>
          <div class="fg"><label for="cvv">CVV</label>
            <input id="cvv" name="cvv" inputmode="numeric" placeholder="123" autocomplete="off"></div>
        </div>
      </div>
      <div id="pane-bkash" hidden>
        <div class="fg"><label for="msisdn">bKash account number</label>
          <input id="msisdn" name="msisdn" inputmode="numeric" placeholder="01700000000" autocomplete="off"></div>
        <div class="row">
          <div class="fg"><label for="otp">OTP</label>
            <input id="otp" name="otp" inputmode="numeric" placeholder="{WALLET_OTP}" autocomplete="off"></div>
          <div class="fg"><label for="pin">PIN</label>
            <input id="pin" name="pin" inputmode="numeric" placeholder="{WALLET_PIN}" autocomplete="off"></div>
        </div>
      </div>
      <button class="pay" type="submit">Pay {s['currency']} {money(s['amount'])}</button>
      <button class="cancel" type="submit"
              onclick="document.getElementById('method').value='cancel'">Cancel and go back</button>
    </form>
    <details class="ref"><summary>Test instruments</summary>
      <table><tbody>{cards}<tr><td colspan="2" style="height:8px"></td></tr>{wallets}
      <tr><td>OTP / PIN</td><td>{WALLET_OTP} / {WALLET_PIN}</td></tr></tbody></table></details>
  </div>
</div>
<script>
function pick(m){{
  document.getElementById('method').value=m;
  document.getElementById('pane-card').hidden = m!=='card';
  document.getElementById('pane-bkash').hidden = m!=='bkash';
  document.getElementById('t-card').setAttribute('aria-selected', m==='card');
  document.getElementById('t-bkash').setAttribute('aria-selected', m==='bkash');
}}
</script>""")


def page_closed(s):
    return shell("Session closed", f"""<div class="card done">
      <h1>This payment session is closed</h1>
      <p>Order {html.escape(s['tran_id'])} was already settled as
      {html.escape(s['status'])}. Start a new booking.</p></div>""")


def page_404():
    return shell("Not found", """<div class="card done">
      <h1>No such payment session</h1>
      <p>The link is wrong, or the gateway restarted and cleared its memory.</p></div>""")


if __name__ == "__main__":
    print(f"\n  Mock gateway on {BASE_URL}")
    print("  store_id: testbox   store_passwd: testbox@ssl")
    print(f"  duplicate IPN delivery: {'ON' if DUPLICATE_IPN else 'off'}\n")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")