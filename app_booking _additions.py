# =====================================================================
# ADD/REPLACE these pieces in your existing app.py
# =====================================================================

# 1. Update your import line to include the new function:
#
# from database import (
#     get_protocol,
#     init_db,
#     save_patient_scan,
#     get_previous_scan,
#     save_patient_interval_update,
#     get_patient_history,
#     save_booking,
#     get_bookings_for_doctor,
#     update_booking_status,   # <-- new
# )


# 2. Replace your existing create_booking route with this version —
#    it now RETURNS the new booking_id, which the frontend needs to
#    carry through the payment flow (payment1 -> payment2 -> success)
#    so we know which booking to mark confirmed afterward.

@app.post('/api/create_booking')
async def create_booking(
    doctor_id: str = Body(...),
    doctor_name: str = Body(...),
    specialty: str = Body(...),
    patient_email: str = Body(...),
    patient_name: str = Body(...),
    patient_age: str = Body(None),
    patient_gender: str = Body(None),
    appointment_date: str = Body(...),
    appointment_time: str = Body(...),
    problem: str = Body(None),
    fee: float = Body(0)
):
    new_booking_id = save_booking(
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        specialty=specialty,
        patient_email=patient_email.strip().lower(),
        patient_name=patient_name,
        patient_age=patient_age,
        patient_gender=patient_gender,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        problem=problem,
        fee=fee
    )
    return {
        "status": "success",
        "message": "Booking recorded.",
        "booking_id": new_booking_id   # frontend must hang onto this
    }


# 3. NEW route — call this the moment a payment is confirmed.
#    This is the missing link between "payment succeeded" and
#    "doctor sees it on /doctor/requests".

@app.post('/api/confirm_booking/{booking_id}')
async def confirm_booking(booking_id: int):
    success = update_booking_status(booking_id, "confirmed")
    if not success:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return {"status": "success", "message": "Booking marked as confirmed."}