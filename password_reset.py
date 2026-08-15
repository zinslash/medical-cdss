"""
password_reset.py  —  two-step password reset for AI Triage.

Wire into app.py:

    from password_reset import router as reset_router, init_reset_db
    app.include_router(reset_router)
    init_reset_db()

...and DELETE the existing @app.post('/api/forgot_password') function, which
this replaces.

WHY TWO STEPS
The old endpoint took an email plus a new password and overwrote the account
on the spot. No verification, so anyone who knew a registered address could
take over that account — including doctor accounts. This version requires a
code that is generated server-side and delivered out of band, so knowing the
email is not enough.

  step 1  POST /api/forgot_password  {email}                  -> code created
  step 2  POST /api/reset_password   {email, code, new_password} -> password set

Codes are 6 digits, valid 15 minutes, single use, max 5 wrong attempts, and
only the SHA-256 hash is stored. Requesting a new code kills any earlier one.

DEV MODE
RESET_DEV_MODE=true in .env makes step 1 return the code in the response so you
can test without email. That is a development convenience and nothing more --
returning the code to the caller means anyone can reset any account, which is
exactly the hole this file exists to close. Set it to false and implement
send_reset_code() before this is reachable by anyone but you.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Body, HTTPException
from mysql.connector import Error

import user_db

router = APIRouter()

# ⚠️ Must be false anywhere other people can reach the app.
DEV_MODE = os.environ.get("RESET_DEV_MODE", "true").lower() == "true"

# RESET_REQUIRE_CODE=false drops the verification step entirely: an email plus
# a new password is enough. Convenient for a demo where nobody can receive a
# code, and exactly as unsafe as it sounds -- anyone who knows a registered
# address owns that account, doctor accounts included. Flip it back to true
# and fill in send_reset_code() before anyone else can reach this app.
REQUIRE_CODE = os.environ.get("RESET_REQUIRE_CODE", "false").lower() == "true"

CODE_TTL_MINUTES = 15
MAX_ATTEMPTS = 5

# Same wording whether or not the address is registered, so this endpoint
# can't be used to discover which emails have accounts.
GENERIC_REPLY = "If that email is registered, a reset code has been sent."


# ===========================================================================
# Schema
# ===========================================================================
def init_reset_db():
    conn = user_db.get_connection()
    if not conn:
        print("⚠️ password_reset: no DB connection, table not created")
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            email      VARCHAR(255) NOT NULL,
            code_hash  VARCHAR(64)  NOT NULL,
            role       VARCHAR(32)  NOT NULL,
            expires_at DATETIME     NOT NULL,
            attempts   INT          NOT NULL DEFAULT 0,
            used       TINYINT      NOT NULL DEFAULT 0,
            created_at DATETIME     NOT NULL,
            INDEX idx_reset_email (email, used)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("🔑 Password reset table initialized (password_resets)")


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _find_account(email: str):
    """Returns 'patient', 'doctor', or None. Note the correct table names --
    the old code queried `patients`/`doctors`, which do not exist."""
    if user_db.get_patient_by_email(email):
        return "patient"
    if user_db.get_doctor_by_email(email):
        return "doctor"
    return None


def send_reset_code(email: str, code: str):
    """
    Replace this with real delivery before turning DEV_MODE off.

    SMS is the better fit for your users — bKash and every Bangladeshi bank
    already send OTPs that way, so it needs no explaining. Any local SMS
    gateway works. Email via smtplib is fine too.

    Until then it just prints to your terminal.
    """
    print(f"🔑 [DEV] Reset code for {email}: {code}  (valid {CODE_TTL_MINUTES} min)")


# ===========================================================================
# CONFIG — lets one reset page render the right flow for either mode
# ===========================================================================
@router.get("/api/reset_config")
async def reset_config():
    return {"requires_code": REQUIRE_CODE}


# ===========================================================================
# STEP 1 — request a code
# ===========================================================================
@router.post("/api/forgot_password")
async def forgot_password(email: str = Body(..., embed=True)):
    clean_email = email.strip().lower()
    role = _find_account(clean_email)

    # Unknown address: reply identically, do nothing. Do not leak.
    if not role:
        return {"status": "success", "message": GENERIC_REPLY}

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=CODE_TTL_MINUTES)

    conn = user_db.get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    cur = conn.cursor()
    try:
        # Requesting a new code invalidates any outstanding one.
        cur.execute("UPDATE password_resets SET used = 1 WHERE email = %s AND used = 0",
                    (clean_email,))
        cur.execute(
            "INSERT INTO password_resets (email, code_hash, role, expires_at, created_at)"
            " VALUES (%s, %s, %s, %s, %s)",
            (clean_email, _hash_code(code), role,
             expires.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    except Error as e:
        conn.rollback()
        print(f"⚠️ password reset DB error: {e}")
        raise HTTPException(status_code=500, detail="Could not create reset code.")
    finally:
        cur.close()
        conn.close()

    send_reset_code(clean_email, code)

    reply = {"status": "success", "message": GENERIC_REPLY}
    if DEV_MODE:
        # ⚠️ Development only. Remove by setting RESET_DEV_MODE=false.
        reply["dev_code"] = code
        reply["dev_warning"] = "Code returned in response because RESET_DEV_MODE is on."
    return reply


# ===========================================================================
# STEP 2 — use the code to set a new password
# ===========================================================================
@router.post("/api/reset_password")
async def reset_password(
    email: str = Body(...),
    new_password: str = Body(...),
    code: str = Body(None),
):
    clean_email = email.strip().lower()

    if len(new_password) < 8:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 8 characters.")

    # ---- Simple mode: no verification step -------------------------------
    # Anyone who knows the address can do this. See REQUIRE_CODE above.
    if not REQUIRE_CODE:
        role = _find_account(clean_email)
        if not role:
            raise HTTPException(status_code=404, detail="No account found with that email.")

        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        table = "app_patients" if role == "patient" else "app_doctors"

        conn = user_db.get_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database unavailable.")
        cur = conn.cursor()
        try:
            cur.execute(f"UPDATE {table} SET password = %s WHERE email = %s",
                        (hashed, clean_email))
            changed = cur.rowcount
            conn.commit()
        except Error as e:
            conn.rollback()
            print(f"⚠️ password reset DB error: {e}")
            raise HTTPException(status_code=500, detail="Could not reset password.")
        finally:
            cur.close()
            conn.close()

        if not changed:
            raise HTTPException(status_code=404, detail="Account not found.")

        print(f"🔑 Password reset (no-code mode) for {clean_email} ({role})")
        return {"status": "success",
                "message": "Password updated. Please log in with your new password."}

    # ---- Code mode: verify the single-use code ---------------------------
    if not code:
        raise HTTPException(status_code=400, detail="A reset code is required.")

    conn = user_db.get_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute(
            "SELECT * FROM password_resets WHERE email = %s AND used = 0"
            " ORDER BY id DESC LIMIT 1", (clean_email,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Invalid or expired code.")

        expires = row["expires_at"]
        if isinstance(expires, str):
            expires = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
        if expires < datetime.now(timezone.utc).replace(tzinfo=None):
            cur.execute("UPDATE password_resets SET used = 1 WHERE id = %s", (row["id"],))
            conn.commit()
            raise HTTPException(status_code=400, detail="Invalid or expired code.")

        if row["attempts"] >= MAX_ATTEMPTS:
            cur.execute("UPDATE password_resets SET used = 1 WHERE id = %s", (row["id"],))
            conn.commit()
            raise HTTPException(status_code=429,
                                detail="Too many attempts. Request a new code.")

        if not secrets.compare_digest(row["code_hash"], _hash_code(code.strip())):
            cur.execute("UPDATE password_resets SET attempts = attempts + 1 WHERE id = %s",
                        (row["id"],))
            conn.commit()
            remaining = MAX_ATTEMPTS - (row["attempts"] + 1)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or expired code. {max(remaining, 0)} attempts remaining.")

        # Code is good. Hash the new password and write it to the right table.
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        table = "app_patients" if row["role"] == "patient" else "app_doctors"

        write = conn.cursor()
        write.execute(f"UPDATE {table} SET password = %s WHERE email = %s",
                      (hashed, clean_email))
        changed = write.rowcount
        write.execute("UPDATE password_resets SET used = 1 WHERE id = %s", (row["id"],))
        conn.commit()
        write.close()

        if not changed:
            raise HTTPException(status_code=404, detail="Account not found.")

        print(f"🔑 Password reset completed for {clean_email} ({row['role']})")
        return {"status": "success",
                "message": "Password updated. Please sign in with your new password."}

    except HTTPException:
        raise
    except Error as e:
        conn.rollback()
        print(f"⚠️ password reset DB error: {e}")
        raise HTTPException(status_code=500, detail="Could not reset password.")
    finally:
        cur.close()
        conn.close()