# =====================================================================
# REPLACE your existing /patient/update-status route in app.py with this.
#
# The change: it now looks up the patient's record and passes age, gender
# and their recorded ongoing problem into the triage engine, so guidance
# is stratified by patient rather than identical for everyone.
#
# It also returns the full structured dict instead of a text blob, which
# is what the new triage.html renders.
# =====================================================================

@app.post("/patient/update-status")
async def update_patient_status(
        patient_id: str = Body(...),
        pain_level: int = Body(...),
        primary_symptom: str = Body(...),
        symptom_progression: str = Body(...),
        additional_notes: str = Body(None)
):
    patient_id = patient_id.strip().lower()

    # ---- Most recent imaging result for this patient --------------------
    history = get_patient_history(patient_id)

    if history and history.get("scans") and len(history["scans"]) > 0:
        most_recent_scan = history["scans"][0]
        scan_type = most_recent_scan[0].upper()
        prediction = most_recent_scan[1]
        confidence = float(most_recent_scan[2])
    else:
        scan_type = "UNKNOWN"
        prediction = "None"
        confidence = 0.0

    # ---- Patient demographics, so advice can be stratified --------------
    patient_record = user_db.get_patient_by_email(patient_id)
    if patient_record:
        age = patient_record.get("age")
        gender = patient_record.get("gender")
        known_problem = patient_record.get("problem")
    else:
        age = gender = known_problem = None
        print(f"ℹ️ No patient record for '{patient_id}' -- guidance will not be "
              f"age/sex stratified.")

    # Confidence is stored 0-1 in the scan table but the triage engine and
    # the UI both talk in percent.
    confidence_pct = round(confidence * 100, 2) if confidence <= 1 else round(confidence, 2)

    clinical_plan = get_dynamic_clinical_advice(
        scan_type=scan_type,
        diagnosis=prediction,
        confidence=confidence_pct,
        pain_level=pain_level,
        progression=symptom_progression,
        symptom=primary_symptom,
        age=age,
        gender=gender,
        known_problem=known_problem,
        # weight_kg=...  <- add once app_patients has a weight column
    )

    # The DB column expects text, so store a readable rendering of the plan
    # rather than the raw dict.
    stored_summary = (
        f"[{clinical_plan['urgency']}] {clinical_plan['headline']}\n\n"
        f"{clinical_plan['summary']}\n\n"
        f"Actions: " + "; ".join(clinical_plan.get("immediate_actions", []))
    )

    save_patient_interval_update(
        patient_id=patient_id,
        pain_level=pain_level,
        primary_symptom=primary_symptom,
        progression=symptom_progression,
        notes=additional_notes,
        suggestions=stored_summary
    )

    return {
        "status": "success",
        "message": "Routine status log successfully recorded.",
        "correlated_scan_context": f"{scan_type} ({prediction})",
        "scan_confidence": confidence_pct,
        "clinical_plan": clinical_plan,
        # kept for backward compatibility with any older frontend code
        "patient_suggestions": stored_summary,
    }