"""
doctor_portal.py  —  makes registered doctors bookable, and makes the calendar real.

Wire into app.py:

    from doctor_portal import (router as doctor_router, init_doctor_portal_db,
                               register_doctor_in_catalog)
    app.include_router(doctor_router)
    init_doctor_portal_db()

...and add one line inside signup_doctor() so new accounts appear in the
directory. See DOCTOR_PORTAL.md.

TWO IDEAS
  app_doctors      = login accounts        (user_db.py owns this)
  doctors_catalog  = the bookable directory (payments.py owns this)

They were unconnected: a doctor could register and never appear to patients.
`account_email` now links them, and signup writes both.

AVAILABILITY
A doctor is free at a given time when all of these hold:
  - the weekday is in their available_days
  - the time falls inside their consulting hours
  - no confirmed or awaiting-payment appointment already holds that slot
"""

import hashlib
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Body, HTTPException, Request

import user_db
from payments import _rows, _write, read_token

router = APIRouter()

WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DEFAULT_DAYS = "0,1,2,3,4,5"        # Mon–Sat, matching the "Mon - Sat" badge
DEFAULT_START = "09:00"
DEFAULT_END = "16:00"
SLOT_MINUTES = 30
DEFAULT_FEE = 800.00

# An appointment holds its slot while it's paid for, and while payment is
# pending — otherwise two patients could pay for the same time.
HOLDING_STATUSES = ("confirmed", "awaiting_payment")


# ===========================================================================
# Schema
# ===========================================================================
def init_doctor_portal_db():
    conn = user_db.get_connection()
    if not conn:
        print("⚠️ doctor_portal: no DB connection")
        return
    cur = conn.cursor()

    cur.execute(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = DATABASE() AND table_name = 'doctors_catalog'")
    existing = {r[0].lower() for r in cur.fetchall()}

    for name, spec in {
        "account_email": "VARCHAR(255) NULL",
        "available_days": f"VARCHAR(32) NULL DEFAULT '{DEFAULT_DAYS}'",
        "slot_start": f"VARCHAR(8) NULL DEFAULT '{DEFAULT_START}'",
        "slot_end": f"VARCHAR(8) NULL DEFAULT '{DEFAULT_END}'",
        "experience": "INT NULL",
        "bio": "TEXT NULL",
        "is_listed": "TINYINT NOT NULL DEFAULT 1",
    }.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE doctors_catalog ADD COLUMN {name} {spec}")
            print(f"   + added doctors_catalog.{name}")

    # Backfill the seeded demo doctors so they have working hours too.
    cur.execute(
        "UPDATE doctors_catalog SET available_days=%s WHERE available_days IS NULL",
        (DEFAULT_DAYS,))
    cur.execute(
        "UPDATE doctors_catalog SET slot_start=%s, slot_end=%s"
        " WHERE slot_start IS NULL OR slot_end IS NULL",
        (DEFAULT_START, DEFAULT_END))

    conn.commit()
    cur.close()
    conn.close()
    print("🩺 Doctor portal ready (availability + catalog linking)")


# ===========================================================================
# Registration — called from signup_doctor() in app.py
# ===========================================================================
def _key_for(email: str) -> str:
    """Stable, readable key derived from the account email."""
    slug = re.sub(r"[^a-z0-9]+", "", email.split("@")[0].lower())[:12] or "doc"
    digest = hashlib.sha1(email.strip().lower().encode()).hexdigest()[:6]
    return f"doc-{slug}-{digest}"


def register_doctor_in_catalog(email, full_name, specialty, experience=None,
                               fee=DEFAULT_FEE):
    """
    Put a newly registered doctor into the bookable directory.

    Idempotent: signing up twice, or calling this at login, updates the existing
    row instead of creating a duplicate.
    """
    email = (email or "").strip().lower()
    if not email:
        return None

    key = _key_for(email)
    initials = "".join(w[0] for w in re.sub(r"^dr\.?\s*", "", full_name or "",
                                            flags=re.I).split()[:2]).upper() or "DR"

    _write(
        "INSERT INTO doctors_catalog"
        " (doctor_key, full_name, specialty, fee, rating, reviews, initials,"
        "  account_email, available_days, slot_start, slot_end, experience, is_listed)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)"
        " ON DUPLICATE KEY UPDATE full_name=VALUES(full_name),"
        " specialty=VALUES(specialty), initials=VALUES(initials),"
        " experience=VALUES(experience), account_email=VALUES(account_email)",
        (key, full_name, specialty or "General Physician", fee, None, 0,
         initials, email, DEFAULT_DAYS, DEFAULT_START, DEFAULT_END, experience),
    )
    print(f"🩺 Doctor listed in catalog: {full_name} ({key})")
    return key


# ===========================================================================
# Auth — the doctor's own pages need a doctor token, not just any token
# ===========================================================================
def require_doctor(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")
    claims = read_token(auth[7:].strip())
    if not claims:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if claims["role"] != "doctor":
        raise HTTPException(status_code=403, detail="This area is for doctors.")
    return claims


def _catalog_for(email):
    return _rows("SELECT * FROM doctors_catalog WHERE account_email = %s",
                 (email,), one=True)


# ===========================================================================
# Slot helpers
# ===========================================================================
def _slots_between(start, end):
    """['9:00 AM', '9:30 AM', ...] between two HH:MM strings.

    Built by hand rather than with strftime("%-I") — that format is glibc-only
    and raises on Windows.
    """
    try:
        t = datetime.strptime(start or DEFAULT_START, "%H:%M")
        stop = datetime.strptime(end or DEFAULT_END, "%H:%M")
    except ValueError:
        t = datetime.strptime(DEFAULT_START, "%H:%M")
        stop = datetime.strptime(DEFAULT_END, "%H:%M")

    out = []
    while t < stop:
        hour12 = t.hour % 12 or 12
        meridiem = "AM" if t.hour < 12 else "PM"
        out.append(f"{hour12}:{t.minute:02d} {meridiem}")
        t += timedelta(minutes=SLOT_MINUTES)
    return out


def _day_list(csv):
    try:
        return sorted({int(x) for x in (csv or DEFAULT_DAYS).split(",") if x.strip() != ""})
    except ValueError:
        return [0, 1, 2, 3, 4, 5]


# ===========================================================================
# 1. AVAILABILITY — what schedule.html and the calendar both read
# ===========================================================================
@router.get("/api/doctors_catalog/{doctor_key}/availability")
async def availability(doctor_key: str, days: int = 30):
    """
    The next `days` days for this doctor: which dates they work, and which
    time slots are already taken on each.
    """
    doc = _rows("SELECT * FROM doctors_catalog WHERE doctor_key = %s",
                (doctor_key,), one=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Unknown doctor.")

    working = _day_list(doc.get("available_days"))
    all_slots = _slots_between(doc.get("slot_start"), doc.get("slot_end"))

    today = date.today()
    horizon = today + timedelta(days=days)

    holds = ",".join(["%s"] * len(HOLDING_STATUSES))
    taken_rows = _rows(
        "SELECT appt_date, appt_time FROM appointments"
        f" WHERE doctor_key = %s AND status IN ({holds}) AND appt_date >= %s",
        (doctor_key, *HOLDING_STATUSES, today.isoformat()),
    )
    taken = {}
    for r in taken_rows:
        taken.setdefault(str(r["appt_date"]), set()).add(r["appt_time"])

    out = []
    for i in range(days):
        d = today + timedelta(days=i)
        iso = d.isoformat()
        booked = sorted(taken.get(iso, set()))
        works = d.weekday() in working
        free = [s for s in all_slots if s not in booked] if works else []
        out.append({
            "date": iso,
            "day": d.day,
            "weekday": WEEKDAYS[d.weekday()],
            "working": works,
            "slots": all_slots if works else [],
            "booked": booked,
            "free_count": len(free),
        })

    return {
        "status": "success",
        "doctor": {
            "doctor_key": doc["doctor_key"],
            "full_name": doc["full_name"],
            "specialty": doc["specialty"],
            "fee": float(doc["fee"]),
            "available_days": working,
            "slot_start": doc.get("slot_start") or DEFAULT_START,
            "slot_end": doc.get("slot_end") or DEFAULT_END,
        },
        "horizon": horizon.isoformat(),
        "days": out,
    }


# ===========================================================================
# 2. THE DOCTOR'S OWN PROFILE
# ===========================================================================
@router.get("/api/doctor/requests")
async def doctor_requests(request: Request, status: str = "confirmed"):
    """
    The booking feed for the doctor's requests page.

    Only paid bookings appear by default. An appointment sits at
    'awaiting_payment' until the gateway confirms the money, so listing those
    would show the doctor consultations nobody has paid for.

      status=confirmed  paid bookings only (default)
      status=pending    started but unpaid
      status=all        everything
    """
    claims = require_doctor(request)
    doc = _catalog_for(claims["email"])
    if not doc:
        acct = user_db.get_doctor_by_email(claims["email"])
        if not acct:
            raise HTTPException(status_code=404, detail="Doctor account not found.")
        register_doctor_in_catalog(acct["email"], acct["full_name"],
                                   acct.get("specialty"), acct.get("experience"))
        doc = _catalog_for(claims["email"])

    if status == "confirmed":
        wanted = ("confirmed",)
    elif status == "pending":
        wanted = ("awaiting_payment",)
    else:
        wanted = HOLDING_STATUSES

    marks = ",".join(["%s"] * len(wanted))
    rows = _rows(
        "SELECT a.id, a.patient_name, a.patient_email, a.patient_age,"
        " a.patient_gender, a.patient_type, a.problem, a.appt_date, a.appt_time,"
        " a.fee, a.status, a.created_at,"
        " p.order_id, p.method, p.paid_at, p.bank_tran_id"
        " FROM appointments a"
        " LEFT JOIN payments p ON p.appointment_id = a.id AND p.status = 'paid'"
        f" WHERE a.doctor_key = %s AND a.status IN ({marks})"
        " ORDER BY a.appt_date, a.appt_time",
        (doc["doctor_key"], *wanted),
    )

    today = date.today().isoformat()
    upcoming, past = [], []
    for r in rows:
        r["fee"] = float(r["fee"])
        r["appt_date"] = str(r["appt_date"])
        r["created_at"] = str(r["created_at"])
        r["paid"] = r["order_id"] is not None
        (upcoming if r["appt_date"] >= today else past).append(r)

    return {
        "status": "success",
        "doctor": {"doctor_key": doc["doctor_key"], "full_name": doc["full_name"]},
        "counts": {"upcoming": len(upcoming), "past": len(past), "total": len(rows)},
        "upcoming": upcoming,
        "past": past,
    }


@router.get("/api/doctor/me")
async def doctor_me(request: Request):
    claims = require_doctor(request)
    doc = _catalog_for(claims["email"])

    if not doc:
        # Registered before this feature existed — list them now.
        acct = user_db.get_doctor_by_email(claims["email"])
        if not acct:
            raise HTTPException(status_code=404, detail="Doctor account not found.")
        register_doctor_in_catalog(acct["email"], acct["full_name"],
                                   acct.get("specialty"), acct.get("experience"))
        doc = _catalog_for(claims["email"])

    holds = ",".join(["%s"] * len(HOLDING_STATUSES))
    appts = _rows(
        "SELECT id, patient_name, patient_email, appt_date, appt_time, status, fee"
        " FROM appointments WHERE doctor_key = %s"
        f" AND status IN ({holds}) ORDER BY appt_date, appt_time",
        (doc["doctor_key"], *HOLDING_STATUSES),
    )
    for a in appts:
        a["fee"] = float(a["fee"])
        a["appt_date"] = str(a["appt_date"])

    return {
        "status": "success",
        "doctor": {
            "doctor_key": doc["doctor_key"],
            "full_name": doc["full_name"],
            "specialty": doc["specialty"],
            "fee": float(doc["fee"]),
            "experience": doc.get("experience"),
            "bio": doc.get("bio"),
            "available_days": _day_list(doc.get("available_days")),
            "slot_start": doc.get("slot_start") or DEFAULT_START,
            "slot_end": doc.get("slot_end") or DEFAULT_END,
            "is_listed": bool(doc.get("is_listed", 1)),
            "initials": doc.get("initials"),
        },
        "appointments": appts,
    }


@router.put("/api/doctor/me")
async def update_doctor_me(
    request: Request,
    fee: float = Body(None),
    available_days: list = Body(None),
    slot_start: str = Body(None),
    slot_end: str = Body(None),
    bio: str = Body(None),
    experience: int = Body(None),
    is_listed: bool = Body(None),
):
    claims = require_doctor(request)
    doc = _catalog_for(claims["email"])
    if not doc:
        raise HTTPException(status_code=404, detail="You are not in the directory yet.")

    sets, params = [], []

    if fee is not None:
        if fee < 0 or fee > 100000:
            raise HTTPException(status_code=400, detail="Fee must be between 0 and 100000.")
        sets.append("fee=%s"); params.append(float(fee))

    if available_days is not None:
        days = sorted({int(d) for d in available_days if 0 <= int(d) <= 6})
        if not days:
            raise HTTPException(status_code=400, detail="Pick at least one working day.")
        sets.append("available_days=%s"); params.append(",".join(str(d) for d in days))

    for field, value in (("slot_start", slot_start), ("slot_end", slot_end)):
        if value is not None:
            if not re.fullmatch(r"\d{2}:\d{2}", value):
                raise HTTPException(status_code=400, detail=f"{field} must look like 09:00.")
            sets.append(f"{field}=%s"); params.append(value)

    if slot_start and slot_end and slot_start >= slot_end:
        raise HTTPException(status_code=400, detail="Start time must be before end time.")

    if bio is not None:
        sets.append("bio=%s"); params.append(bio[:1000])
    if experience is not None:
        sets.append("experience=%s"); params.append(int(experience))
    if is_listed is not None:
        sets.append("is_listed=%s"); params.append(1 if is_listed else 0)

    if not sets:
        return {"status": "success", "message": "Nothing to update."}

    params.append(doc["doctor_key"])
    _write(f"UPDATE doctors_catalog SET {', '.join(sets)} WHERE doctor_key=%s", tuple(params))

    return {"status": "success", "message": "Profile updated."}