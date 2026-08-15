# =====================================================================
# COMPLETE REPLACEMENT for the /analyze route in app.py
#
# Replace your whole existing @app.post("/analyze") function with the one
# below, and add this line near your other imports at the top of app.py:
#
#     from cam_regions import extract_regions
#
# Changes from your current version:
#   1. Extracts Grad-CAM attention regions and returns them as "regions"
#   2. Returns the original radiograph as "original_image" so the frontend
#      can draw boxes over the plain scan rather than the heat overlay
#   3. Detects the real image format instead of assuming JPEG, since the
#      upload is saved with a .jpg extension regardless of what was sent
# =====================================================================

@app.post("/analyze")
async def analyze_scan(patient_id: str = Body(...), file: UploadFile = File(...)):
    patient_id = patient_id.strip().lower()
    raw_upload = await file.read()
    image_bytes = BytesIO(raw_upload)

    scan_type = router_ai.predict_scan_type(image_bytes)

    if scan_type == "unknown":
        return {
            "status": "error",
            "message": "Unrecognized scan layout. Please upload a clear Chest X-Ray, Brain MRI, or Bone X-Ray."
        }

    image_bytes.seek(0)
    current_save_path = f"data/saved_scans/{patient_id}_{int(datetime.datetime.now().timestamp())}.jpg"
    os.makedirs(os.path.dirname(current_save_path), exist_ok=True)
    with open(current_save_path, "wb") as f:
        f.write(image_bytes.getbuffer())
    image_bytes.seek(0)

    previous_record = get_previous_scan(patient_id, scan_type)

    if scan_type == "brain":
        pred_class, confidence, current_heatmap, raw_current_map = brain_ai.predict_and_explain(image_bytes)
    elif scan_type == "bone":
        pred_class, confidence, current_heatmap, raw_current_map = bone_ai.predict_and_explain(image_bytes)
    else:
        pred_class, confidence, current_heatmap, raw_current_map = chest_ai.predict_and_explain(image_bytes)

    delta_b64 = None
    if previous_record:
        prev_file_path = previous_record[0]
        if os.path.exists(prev_file_path):
            with open(prev_file_path, "rb") as pf:
                prev_bytes = BytesIO(pf.read())

            if scan_type == "brain":
                _, _, _, raw_prev_map = brain_ai.predict_and_explain(prev_bytes)
            elif scan_type == "bone":
                _, _, _, raw_prev_map = bone_ai.predict_and_explain(prev_bytes)
            else:
                _, _, _, raw_prev_map = chest_ai.predict_and_explain(prev_bytes)

            delta_map = compute_temporal_delta(raw_current_map, raw_prev_map)
            _, d_buffer = cv2.imencode('.jpg', delta_map)
            delta_b64 = base64.b64encode(d_buffer).decode('utf-8')

    try:
        save_patient_scan(patient_id, scan_type, current_save_path, pred_class, confidence)
    except Exception as db_err:
        print(f"⚠️ Non-fatal Database Error: {db_err}")

    clinical_data = get_protocol(scan_type, pred_class)

    _, buffer = cv2.imencode('.jpg', current_heatmap)
    heatmap_b64 = base64.b64encode(buffer).decode('utf-8')

    # ---- Attention regions from the Grad-CAM map ------------------------
    # Computed per-image from what the model actually attended to. Nothing
    # here is hardcoded; if the activation is diffuse, no boxes come back.
    try:
        regions = extract_regions(
            raw_cam=raw_current_map,
            label=pred_class,
            overall_confidence=confidence,
            threshold=0.55,   # raise for fewer/tighter boxes, lower for more
            max_boxes=3
        )
    except Exception as region_err:
        print(f"⚠️ Region extraction failed (non-fatal): {region_err}")
        regions = []

    # ---- Original radiograph, for drawing boxes over ---------------------
    # The upload is saved with a .jpg extension regardless of what was
    # actually sent, so derive the real MIME type from the upload rather
    # than hardcoding image/jpeg.
    mime = file.content_type if file.content_type in ("image/png", "image/jpeg") else "image/jpeg"
    original_b64 = base64.b64encode(raw_upload).decode('utf-8')

    return {
        "status": "success",
        "scan_type_detected": scan_type.upper(),
        "diagnosis": pred_class,
        "confidence": round(confidence * 100, 2),
        "heatmap": heatmap_b64,
        "original_image": original_b64,
        "original_mime": mime,
        "regions": regions,
        "clinical_data": clinical_data,
        "has_historical_timeline": True if delta_b64 else False,
        "delta_heatmap": delta_b64,
        "previous_scan_date": previous_record[3] if previous_record else None
    }