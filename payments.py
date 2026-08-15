"""
payments.py  —  real payment layer for the AI Triage appointment flow.

Wire into app.py with three lines:

    from payments import router as payments_router, init_payment_db, issue_token
    app.include_router(payments_router)
    init_payment_db()

Uses your existing XAMPP MySQL database (ai_triage_db) via user_db.get_connection(),
so appointments and payments sit alongside app_patients / app_doctors.

Four rules are load-bearing:
  1. the consultation fee is read from the database, never from the browser
  2. the browser redirect is NOT proof of payment — it only triggers verification
  3. the IPN webhook is verified by signature, then verified again by API call
  4. settling an order is idempotent, because IPNs arrive more than once
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Body, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from mysql.connector import Error

import user_db

# Load .env here too. app.py already does this, but doing it again costs
# nothing and means payments.py works no matter what order things import in.
load_dotenv()

router = APIRouter()

# --- config: put these in .env ---------------------------------------------
# "mock" = mock_gateway.py on port 4000.  "sslcommerz" = the real sandbox.
#
# Read fresh on every call rather than once at import. Reading it at import
# time meant a .env that loaded late left this stuck on "mock" with nothing
# in the logs to say so -- the failure just looked like the wrong gateway.
def payment_provider() -> str:
    return os.environ.get("PAYMENT_PROVIDER", "mock").strip().lower()


def use_sslc() -> bool:
    return payment_provider() == "sslcommerz"


# Values that are obviously still placeholders rather than real credentials.
_PLACEHOLDERS = {
    "your_sandbox_store_id", "your_sandbox_store_password",
    "aitri68f2a1b3c4d5e", "aitri68f2a1b3c4d5e@ssl",
    "your-store-id", "your-store-password", "",
}


def sslc_credentials_problem():
    """Returns a human-readable problem, or None when the credentials look real."""
    store_id = os.environ.get("SSLC_STORE_ID", "").strip()
    passwd = os.environ.get("SSLC_STORE_PASSWD", "").strip()

    if store_id.lower() in _PLACEHOLDERS or passwd.lower() in _PLACEHOLDERS:
        return ("SSLC_STORE_ID / SSLC_STORE_PASSWD in .env are still placeholder "
                "text. Copy the real values from https://sandbox.sslcommerz.com/manage/ "
                "under My Stores.")
    if not store_id or not passwd:
        return ("SSLC_STORE_ID / SSLC_STORE_PASSWD are missing from .env. "
                "PAYMENT_PROVIDER is set to sslcommerz, so both are required.")
    return None


GATEWAY = os.environ.get("GATEWAY_BASE_URL", "http://127.0.0.1:4000")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8001")
STORE_ID = os.environ.get("STORE_ID", "testbox")
STORE_PASSWD = os.environ.get("STORE_PASSWD", "testbox@ssl")

# Signs the login tokens. MUST be set in .env for production — a fixed default
# would let anyone forge a token for any patient.
AUTH_SECRET = os.environ.get("AUTH_SECRET", "dev-only-change-me")
TOKEN_TTL_SECONDS = 60 * 60 * 12

# Seeded on first run. Fees live here so the browser can't invent one.
# These mirror the directory in doctors.html — keep the keys in sync.
DEFAULT_DOCTORS = [
    {"doctor_key": "d1",  "full_name": "Dr. Nurul Alam",      "specialty": "Orthopedic Surgeon", "fee": 1000.00, "rating": 5.0, "reviews": 60, "initials": "NA"},
    {"doctor_key": "d2",  "full_name": "Dr. Farhana Kabir",   "specialty": "Orthopedic Surgeon", "fee":  900.00, "rating": 4.8, "reviews": 34, "initials": "FK"},
    {"doctor_key": "d3",  "full_name": "Dr. Imran Hossain",   "specialty": "Cardiologist",       "fee": 1500.00, "rating": 4.9, "reviews": 82, "initials": "IH"},
    {"doctor_key": "d4",  "full_name": "Dr. Shirin Akhter",   "specialty": "Cardiologist",       "fee": 1400.00, "rating": 4.7, "reviews": 51, "initials": "SA"},
    {"doctor_key": "d5",  "full_name": "Dr. Kamal Hasan",     "specialty": "Neurologist",        "fee": 1600.00, "rating": 4.9, "reviews": 47, "initials": "KH"},
    {"doctor_key": "d6",  "full_name": "Dr. Tania Sultana",   "specialty": "Dermatologist",      "fee":  800.00, "rating": 4.6, "reviews": 29, "initials": "TS"},
    {"doctor_key": "d7",  "full_name": "Dr. Rafiqul Islam",   "specialty": "Pediatrician",       "fee":  700.00, "rating": 4.8, "reviews": 65, "initials": "RI"},
    {"doctor_key": "d8",  "full_name": "Dr. Nusrat Jahan",    "specialty": "Gynecologist",       "fee": 1200.00, "rating": 4.9, "reviews": 73, "initials": "NJ"},
    {"doctor_key": "d9",  "full_name": "Dr. Asif Chowdhury",  "specialty": "ENT Specialist",     "fee":  850.00, "rating": 4.5, "reviews": 22, "initials": "AC"},
    {"doctor_key": "d10", "full_name": "Dr. Mehjabin Rahman", "specialty": "Psychiatrist",       "fee": 1300.00, "rating": 4.9, "reviews": 38, "initials": "MR"},
    {"doctor_key": "d11", "full_name": "Dr. Zahid Karim",     "specialty": "General Physician",  "fee":  500.00, "rating": 4.7, "reviews": 91, "initials": "ZK"},
    {"doctor_key": "d12", "full_name": "Dr. Sabina Yasmin",   "specialty": "General Physician",  "fee":  500.00, "rating": 4.6, "reviews": 58, "initials": "SY"},
]

SPECIALIZATION_ORDER = [
    "Orthopedic Surgeon", "Cardiologist", "Neurologist", "Dermatologist",
    "Pediatrician", "Gynecologist", "ENT Specialist", "Psychiatrist",
    "General Physician",
]


# ===========================================================================
# Schema
# ===========================================================================
def init_payment_db():
    """Call once at startup, after user_db.init_user_db(). Safe to re-run."""
    conn = user_db.get_connection()
    if not conn:
        print("⚠️ payments: no DB connection, tables not created")
        return
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doctors_catalog (
            doctor_key  VARCHAR(64)  PRIMARY KEY,
            full_name   VARCHAR(255) NOT NULL,
            specialty   VARCHAR(255) NOT NULL,
            fee         DECIMAL(10,2) NOT NULL,
            rating      DECIMAL(3,1) NULL,
            reviews     INT          NULL,
            initials    VARCHAR(8)   NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            patient_email VARCHAR(255) NOT NULL,
            doctor_key    VARCHAR(64)  NOT NULL,
            doctor_name   VARCHAR(255) NOT NULL,
            specialty     VARCHAR(255) NOT NULL,
            appt_date     VARCHAR(64)  NOT NULL,
            appt_time     VARCHAR(64)  NOT NULL,
            patient_type  VARCHAR(64)  NULL,
            patient_name  VARCHAR(255) NULL,
            patient_age   INT          NULL,
            patient_gender VARCHAR(32) NULL,
            problem       TEXT         NULL,
            fee           DECIMAL(10,2) NOT NULL,
            status        VARCHAR(32)  NOT NULL DEFAULT 'awaiting_payment',
            created_at    DATETIME     NOT NULL,
            INDEX idx_appt_patient (patient_email, status)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            order_id       VARCHAR(64)  PRIMARY KEY,
            appointment_id INT          NOT NULL,
            patient_email  VARCHAR(255) NOT NULL,
            amount         DECIMAL(10,2) NOT NULL,
            currency       VARCHAR(8)   NOT NULL DEFAULT 'BDT',
            status         VARCHAR(32)  NOT NULL DEFAULT 'pending',
            method         VARCHAR(32)  NULL,
            val_id         VARCHAR(64)  NULL,
            bank_tran_id   VARCHAR(64)  NULL UNIQUE,
            fail_reason    VARCHAR(255) NULL,
            created_at     DATETIME     NOT NULL,
            paid_at        VARCHAR(64)  NULL,
            INDEX idx_pay_patient (patient_email, status)
        )
    """)

    # CREATE TABLE IF NOT EXISTS won't touch a table that already exists, so
    # add any columns introduced after the first run.
    _add_missing_columns(cur, "doctors_catalog", {
        "rating": "DECIMAL(3,1) NULL",
        "reviews": "INT NULL",
        "initials": "VARCHAR(8) NULL",
    })
    _add_missing_columns(cur, "appointments", {
        "patient_age": "INT NULL",
        "patient_gender": "VARCHAR(32) NULL",
        "problem": "TEXT NULL",
    })

    for d in DEFAULT_DOCTORS:
        cur.execute(
            "INSERT INTO doctors_catalog"
            " (doctor_key, full_name, specialty, fee, rating, reviews, initials)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s)"
            " ON DUPLICATE KEY UPDATE full_name=VALUES(full_name),"
            " specialty=VALUES(specialty), fee=VALUES(fee), rating=VALUES(rating),"
            " reviews=VALUES(reviews), initials=VALUES(initials)",
            (d["doctor_key"], d["full_name"], d["specialty"], d["fee"],
             d["rating"], d["reviews"], d["initials"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"💳 Payment tables initialized ({len(DEFAULT_DOCTORS)} doctors in catalog)")

    # Say plainly which gateway is in use. Silence here was what made the
    # wrong-provider problem so hard to see.
    provider = payment_provider()
    if provider == "sslcommerz":
        problem = sslc_credentials_problem()
        if problem:
            print(f"🔌 Payment provider: SSLCOMMERZ  ⚠️  {problem}")
        else:
            env = "LIVE" if os.environ.get("SSLC_IS_LIVE", "").lower() == "true" else "sandbox"
            print(f"🔌 Payment provider: SSLCOMMERZ ({env}), "
                  f"store {os.environ.get('SSLC_STORE_ID')}")
    elif provider == "mock":
        print(f"🔌 Payment provider: MOCK — local gateway at {GATEWAY}. "
              f"Set PAYMENT_PROVIDER=sslcommerz in .env for the real sandbox.")
    else:
        print(f"🔌 Payment provider: '{provider}' is not recognised — "
              f"falling back to MOCK. Use 'mock' or 'sslcommerz'.")


def _add_missing_columns(cur, table, columns):
    """MySQL 8 has no ADD COLUMN IF NOT EXISTS, so check information_schema."""
    cur.execute(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = DATABASE() AND table_name = %s", (table,))
    existing = {r[0].lower() for r in cur.fetchall()}
    for name, spec in columns.items():
        if name.lower() not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")
            print(f"   + added {table}.{name}")


# ===========================================================================
# Minimal auth — your app currently has none, so payments can't tell who's who
# ===========================================================================
def issue_token(email: str, role: str = "patient") -> str:
    """Call this from your login routes and return it to the frontend."""
    payload = f"{email.strip().lower()}|{role}|{int(time.time()) + TOKEN_TTL_SECONDS}"
    sig = hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def read_token(token: str):
    try:
        email, role, exp, sig = token.split("|")
    except (ValueError, AttributeError):
        return None
    expected = hmac.new(
        AUTH_SECRET.encode(), f"{email}|{role}|{exp}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    if int(exp) < time.time():
        return None
    return {"email": email, "role": role}


def require_patient(authorization: str = Header(None)):
    """Send as:  Authorization: Bearer <token>"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")
    claims = read_token(authorization[7:].strip())
    if not claims:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    return claims


# ===========================================================================
# DB helpers
# ===========================================================================
def _rows(sql, params=(), one=False):
    conn = user_db.get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    out = cur.fetchone() if one else cur.fetchall()
    cur.close()
    conn.close()
    return out


def _write(sql, params=()):
    conn = user_db.get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount, cur.lastrowid
    except Error as e:
        conn.rollback()
        if getattr(e, "errno", None) == 1062:   # duplicate key
            return 0, None
        raise
    finally:
        cur.close()
        conn.close()


# ===========================================================================
# 1. DOCTOR LIST — so doctors.html stops hardcoding fees
# ===========================================================================
@router.get("/api/doctors_catalog")
async def doctors_catalog():
    # is_listed lets a doctor take themselves off the directory without the
    # row being deleted. The column may not exist on an older database.
    try:
        rows = _rows(
            "SELECT doctor_key, full_name, specialty, fee, rating, reviews, initials"
            " FROM doctors_catalog WHERE is_listed = 1")
    except Exception:
        rows = _rows(
            "SELECT doctor_key, full_name, specialty, fee, rating, reviews, initials"
            " FROM doctors_catalog")
    order = {name: i for i, name in enumerate(SPECIALIZATION_ORDER)}
    rows.sort(key=lambda r: (order.get(r["specialty"], 99), r["full_name"]))
    return {
        "status": "success",
        "specializations": SPECIALIZATION_ORDER,
        "doctors": [
            {**r,
             "fee": float(r["fee"]),
             "rating": float(r["rating"]) if r["rating"] is not None else None}
            for r in rows
        ],
    }


# ===========================================================================
# 2. CREATE APPOINTMENT — the server sets the fee, not the browser
# ===========================================================================
@router.post("/api/appointments")
async def create_appointment(
    request: Request,
    doctor_key: str = Body(...),
    appt_date: str = Body(...),
    appt_time: str = Body(...),
    patient_type: str = Body(None),
    patient_name: str = Body(None),
    patient_age: int = Body(None),
    patient_gender: str = Body(None),
    problem: str = Body(None),
):
    claims = require_patient(request.headers.get("authorization"))

    doctor = _rows(
        "SELECT * FROM doctors_catalog WHERE doctor_key = %s", (doctor_key,), one=True
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Unknown doctor.")

    # Note: no `fee` parameter exists on this endpoint. That is deliberate.
    rowcount, appt_id = _write(
        "INSERT INTO appointments (patient_email, doctor_key, doctor_name, specialty,"
        " appt_date, appt_time, patient_type, patient_name, patient_age,"
        " patient_gender, problem, fee, status, created_at)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (claims["email"], doctor_key, doctor["full_name"], doctor["specialty"],
         appt_date, appt_time, patient_type, patient_name, patient_age,
         patient_gender, problem,
         float(doctor["fee"]), "awaiting_payment",
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    )

    return {
        "status": "success",
        "appointment": {
            "id": appt_id,
            "doctor_name": doctor["full_name"],
            "specialty": doctor["specialty"],
            "date": appt_date,
            "time": appt_time,
            "patient_type": patient_type,
            "patient_name": patient_name,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "problem": problem,
            "fee": float(doctor["fee"]),
            "currency": "BDT",
        },
    }


@router.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: int, request: Request):
    claims = require_patient(request.headers.get("authorization"))
    appt = _rows(
        "SELECT * FROM appointments WHERE id = %s AND patient_email = %s",
        (appointment_id, claims["email"]), one=True,
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    appt["fee"] = float(appt["fee"])
    appt["created_at"] = str(appt["created_at"])
    return {"status": "success", "appointment": appt}


# ===========================================================================
# 3. START CHECKOUT — hands off to the gateway's hosted page
# ===========================================================================
@router.post("/api/payments/checkout")
async def start_checkout(request: Request, appointment_id: int = Body(..., embed=True)):
    claims = require_patient(request.headers.get("authorization"))

    appt = _rows(
        "SELECT * FROM appointments WHERE id = %s AND patient_email = %s",
        (appointment_id, claims["email"]), one=True,
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if appt["status"] == "confirmed":
        raise HTTPException(status_code=409, detail="This appointment is already paid.")

    amount = float(appt["fee"])          # from the DB, every time
    order_id = "ORD-" + secrets.token_hex(5).upper()

    _write(
        "INSERT INTO payments (order_id, appointment_id, patient_email, amount,"
        " currency, status, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (order_id, appointment_id, claims["email"], amount, "BDT", "pending",
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    )

    product_name = f"{appt['doctor_name']} - {appt['specialty']}"
    customer_name = appt["patient_name"] or claims["email"]

    # ---- Real SSLCommerz -------------------------------------------------
    if use_sslc():
        problem = sslc_credentials_problem()
        if problem:
            print(f"⚠️ {problem}")
            _mark_unpaid(order_id, "failed", "Gateway not configured")
            raise HTTPException(status_code=500, detail=problem)

        import sslcommerz
        checkout_url, error = sslcommerz.create_session(
            order_id=order_id,
            amount=amount,
            currency="BDT",
            product_name=product_name,
            customer_name=customer_name,
            customer_email=claims["email"],
            customer_phone=None,
            success_url=f"{APP_BASE_URL}/payment/return",
            fail_url=f"{APP_BASE_URL}/payment/return",
            cancel_url=f"{APP_BASE_URL}/payment/return",
            ipn_url=f"{APP_BASE_URL}/payment/ipn",
        )
        if error:
            print(f"⚠️ SSLCommerz init failed: {error}")
            _mark_unpaid(order_id, "failed", error)
            raise HTTPException(status_code=502, detail=f"Payment could not start: {error}")

        return {"status": "success", "order_id": order_id, "checkout_url": checkout_url}

    # ---- Local mock ------------------------------------------------------
    try:
        res = requests.post(
            f"{GATEWAY}/api/v1/session",
            json={
                "store_id": STORE_ID,
                "store_passwd": STORE_PASSWD,
                "total_amount": amount,
                "currency": "BDT",
                "tran_id": order_id,
                "product_name": product_name,
                "cus_name": customer_name,
                "success_url": f"{APP_BASE_URL}/payment/return",
                "fail_url": f"{APP_BASE_URL}/payment/return",
                "cancel_url": f"{APP_BASE_URL}/payment/return",
                "ipn_url": f"{APP_BASE_URL}/payment/ipn",
            },
            timeout=15,
        )
        data = res.json()
    except Exception as e:
        print(f"⚠️ gateway unreachable: {e}")
        _mark_unpaid(order_id, "failed", "Payment service unreachable")
        raise HTTPException(status_code=502, detail="Payment service is unavailable.")

    if data.get("status") != "SUCCESS":
        _mark_unpaid(order_id, "failed", data.get("failedreason"))
        raise HTTPException(status_code=502, detail=data.get("failedreason", "Could not start payment"))

    return {"status": "success", "order_id": order_id, "checkout_url": data["GatewayPageURL"]}


# ===========================================================================
# 4. BROWSER RETURN — untrusted. Verify, then bounce to your existing pages.
# ===========================================================================
@router.api_route("/payment/return", methods=["GET", "POST"])
async def payment_return(request: Request):
    """
    SSLCommerz POSTs the customer's browser back here with form fields; the
    mock gateway redirects with query params. Accept both.

    Either way this is untrusted -- it only tells us WHICH order to go and
    verify server-to-server.
    """
    if request.method == "POST":
        form = await request.form()
        tran_id = form.get("tran_id")
        val_id = form.get("val_id")
        status_hint = (form.get("status") or "").upper()
    else:
        tran_id = request.query_params.get("tran_id")
        val_id = request.query_params.get("val_id")
        status_hint = (request.query_params.get("status") or "").upper()

    # On a cancel or fail SSLCommerz sends no val_id at all.
    if tran_id and not val_id and status_hint in ("FAILED", "CANCELLED"):
        _mark_unpaid(tran_id,
                     "cancelled" if status_hint == "CANCELLED" else "failed",
                     "Cancelled by user" if status_hint == "CANCELLED" else "Payment failed")
        reason = "Payment cancelled." if status_hint == "CANCELLED" else "Payment failed."
        return RedirectResponse(f"/payment1?error={reason}", status_code=303)

    if tran_id and val_id:
        settle_order(tran_id, val_id, source="return")
        row = _rows("SELECT status, fail_reason FROM payments WHERE order_id = %s",
                    (tran_id,), one=True)
        if row and row["status"] == "paid":
            return RedirectResponse(f"/paymentsuccess?order_id={tran_id}", status_code=303)
        reason = (row or {}).get("fail_reason") or "Payment could not be confirmed."
        return RedirectResponse(f"/payment1?error={reason}", status_code=303)
    return RedirectResponse("/payment1?error=Missing+payment+reference", status_code=303)


# ===========================================================================
# 5. IPN WEBHOOK — the reliable path. Fires even if the browser is closed.
# ===========================================================================
@router.post("/payment/ipn")
async def payment_ipn(request: Request):
    """
    Note: SSLCommerz cannot reach 127.0.0.1, so on a local setup this never
    fires and the browser redirect does the work. Expose the app with ngrok
    and register the URL in the sandbox panel to exercise it.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = dict(await request.form())

    if use_sslc():
        import sslcommerz
        valid = sslcommerz.verify_ipn(payload)
    else:
        valid = verify_signature(payload)
    if not valid:
        print(f"⚠️ bad IPN signature for {payload.get('tran_id')}")
        raise HTTPException(status_code=400, detail="bad signature")

    settle_order(payload.get("tran_id"), payload.get("val_id"), source="ipn")
    return {"status": "ok"}          # answer fast or the gateway keeps retrying


# ===========================================================================
# Settlement — shared by both paths above
# ===========================================================================
def settle_order(order_id, val_id, source):
    order = _rows("SELECT * FROM payments WHERE order_id = %s", (order_id,), one=True)
    if not order:
        return False

    if use_sslc():
        import sslcommerz
        # No val_id means we're reconciling — ask by our own order id instead.
        v = (sslcommerz.validate(val_id) if val_id
             else sslcommerz.query_by_tran_id(order_id))
    else:
        try:
            v = requests.post(
                f"{GATEWAY}/api/v1/validate",
                json={"store_id": STORE_ID, "store_passwd": STORE_PASSWD, "val_id": val_id},
                timeout=15,
            ).json()
        except Exception as e:
            print(f"⚠️ validate call failed: {e}")
            return False

    # --- not approved ---
    if v.get("status") != "VALID":
        # A reconciliation that finds nothing is inconclusive, not a failure —
        # the customer may still be on the gateway page. Leave it pending.
        if source == "recheck" and not v.get("tran_id"):
            print(f"[recheck] {order_id} no result yet, leaving pending")
            return False
        if order["status"] == "pending":
            new = "cancelled" if v.get("status") == "CANCELLED" else "failed"
            reason = v.get("failedreason") or ("Cancelled by user" if new == "cancelled" else v.get("status"))
            _mark_unpaid(order_id, new, reason)
            print(f"[{source}] {order_id} -> {new}")
        return False

    # --- the gateway must have charged exactly what we asked for ---
    if abs(float(v["amount"]) - float(order["amount"])) > 0.001 or v["currency"] != order["currency"]:
        _write("UPDATE payments SET status='review', fail_reason=%s WHERE order_id=%s",
               ("Amount mismatch", order_id))
        print(f"❌ [{source}] {order_id} AMOUNT MISMATCH: gateway {v['amount']} {v['currency']}, "
              f"expected {order['amount']} {order['currency']}")
        return False

    # --- idempotent settle: UNIQUE(bank_tran_id) rejects the second delivery ---
    rowcount, _ = _write(
        "UPDATE payments SET status='paid', method=%s, val_id=%s, bank_tran_id=%s,"
        " paid_at=%s, fail_reason=NULL WHERE order_id=%s AND status <> 'paid'",
        (v.get("method"), v.get("val_id"), v.get("bank_tran_id"), v.get("tran_date"), order_id),
    )

    if rowcount:
        _write("UPDATE appointments SET status='confirmed' WHERE id=%s", (order["appointment_id"],))
        print(f"[{source}] {order_id} PAID {v['amount']} {v['currency']} via {v.get('method')}")
        # -> fulfil here: send confirmation email / SMS, notify the doctor
    else:
        print(f"[{source}] {order_id} duplicate delivery ignored")

    return True


def _mark_unpaid(order_id, status, reason):
    """status is 'failed' or 'cancelled'. Never downgrades an already-paid order."""
    _write("UPDATE payments SET status=%s, fail_reason=%s WHERE order_id=%s AND status='pending'",
           (status, reason, order_id))


def verify_signature(payload: dict) -> bool:
    base = "&".join(
        f"{k}={payload[k]}" for k in sorted(payload)
        if k != "signature" and payload[k] is not None
    )
    expected = hmac.new(STORE_PASSWD.encode(), base.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, str(payload.get("signature", "")))


# ===========================================================================
# 6. STATUS — what paymentsuccessful.html reads instead of sessionStorage
# ===========================================================================
@router.get("/api/payments/{order_id}")
async def payment_status(order_id: str):
    """
    Deliberately unauthenticated: the success page is reached by redirect from
    the gateway, before the frontend has re-attached its token. The order_id is
    a 10-byte random string and only non-sensitive booking details are returned.
    """
    row = _rows(
        "SELECT p.order_id, p.status, p.amount, p.currency, p.method, p.fail_reason,"
        " a.doctor_name, a.specialty, a.appt_date, a.appt_time, a.patient_name"
        " FROM payments p JOIN appointments a ON a.id = p.appointment_id"
        " WHERE p.order_id = %s", (order_id,), one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Order not found.")
    row["amount"] = float(row["amount"])
    return {"status": "success", "payment": row}


@router.post("/api/payments/{order_id}/recheck")
async def recheck_payment(order_id: str):
    """
    Ask the gateway directly what happened to this order and settle accordingly.

    Needed because the IPN cannot reach a localhost server: if the customer's
    browser never made it back from the gateway, the order stays 'pending' even
    though the payment went through. The success page calls this automatically,
    and you can call it by hand for any stuck order.
    """
    order = _rows("SELECT status FROM payments WHERE order_id = %s", (order_id,), one=True)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order["status"] == "paid":
        return {"status": "success", "payment_status": "paid", "changed": False}

    settle_order(order_id, None, source="recheck")

    row = _rows("SELECT status, fail_reason FROM payments WHERE order_id = %s",
                (order_id,), one=True)
    return {
        "status": "success",
        "payment_status": row["status"],
        "changed": row["status"] != order["status"],
        "detail": row["fail_reason"],
    }


@router.get("/api/payment_provider")
async def payment_provider_info():
    """Diagnostic. Open http://127.0.0.1:8000/api/payment_provider in a browser
    to see which gateway the RUNNING server is using — which is not always what
    .env says, if the server was started before .env was edited."""
    provider = payment_provider()
    info = {"provider": provider}
    if provider == "sslcommerz":
        problem = sslc_credentials_problem()
        info["store_id"] = os.environ.get("SSLC_STORE_ID")
        info["environment"] = ("live" if os.environ.get("SSLC_IS_LIVE", "").lower() == "true"
                               else "sandbox")
        info["ready"] = problem is None
        if problem:
            info["problem"] = problem
    else:
        info["gateway_url"] = GATEWAY
        info["note"] = "Using the local mock. Set PAYMENT_PROVIDER=sslcommerz in .env and restart."
    return info


@router.get("/api/my_appointments")
async def my_appointments(request: Request):
    claims = require_patient(request.headers.get("authorization"))
    rows = _rows(
        "SELECT id, doctor_name, specialty, appt_date, appt_time, fee, status"
        " FROM appointments WHERE patient_email = %s ORDER BY id DESC",
        (claims["email"],),
    )
    for r in rows:
        r["fee"] = float(r["fee"])
    return {"status": "success", "appointments": rows}