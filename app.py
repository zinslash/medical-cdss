import uvicorn
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, UploadFile, Request, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import base64
import cv2
import numpy as np
from io import BytesIO
import os
import datetime
import bcrypt

from model import RouterAIModel, MedicalAIModel
from cam_regions import extract_regions
from database import (
    get_protocol,
    init_db,
    save_patient_scan,
    get_previous_scan,
    save_patient_interval_update,
    get_patient_history
)

import user_db
from triage import get_dynamic_clinical_advice
from payments import router as payments_router, init_payment_db, issue_token
from password_reset import router as reset_router, init_reset_db
from doctor_portal import (router as doctor_router, init_doctor_portal_db,
                           register_doctor_in_catalog)
from doctor_match import router as match_router

app = FastAPI(title="Multimodal Medical AI Pipeline & CDSS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)
app.include_router(reset_router)
app.include_router(doctor_router)
app.include_router(match_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

init_db()
user_db.init_user_db()
init_payment_db()
init_reset_db()
init_doctor_portal_db()

print("⏳ Loading medical AI model architecture... Please wait.")
router_ai = RouterAIModel('best_router_model.pth')
chest_ai = MedicalAIModel('best_chest_model.pth')
brain_ai = MedicalAIModel('best_brain_model.pth')
bone_ai = MedicalAIModel('best_fracture_model.pth')
print("✅ All clinical models loaded successfully!")


def compute_temporal_delta(current_heatmap_raw, previous_heatmap_raw):
    if current_heatmap_raw.shape != previous_heatmap_raw.shape:
        previous_heatmap_raw = cv2.resize(previous_heatmap_raw,
                                          (current_heatmap_raw.shape[1], current_heatmap_raw.shape[0]))

    delta = current_heatmap_raw - previous_heatmap_raw
    h, w = delta.shape
    delta_vis = np.zeros((h, w, 3), dtype=np.uint8)

    progression = np.clip(delta, 0, 1)
    regression = np.clip(-delta, 0, 1)

    delta_vis[:, :, 2] = (progression * 255).astype(np.uint8)
    delta_vis[:, :, 0] = (regression * 255).astype(np.uint8)

    return cv2.GaussianBlur(delta_vis, (5, 5), 0)


# --- PAGE ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/index", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="welcome.html")

@app.get("/payment1", response_class=HTMLResponse)
async def payment_page(request: Request):
    return templates.TemplateResponse(request=request, name="payment1.html")

@app.get("/payment2", response_class=HTMLResponse)
async def payment2_page(request: Request):
    return templates.TemplateResponse(request=request, name="payment2.html")

@app.get("/paymentsuccess", response_class=HTMLResponse)
async def payment_success_page(request: Request):
    return templates.TemplateResponse(request=request, name="paymentsuccessful.html")

@app.get("/paymentsummary", response_class=HTMLResponse)
async def payment_summary_page(request: Request):
    return templates.TemplateResponse(request=request, name="payment_summary.html")

@app.get("/doctors", response_class=HTMLResponse)
async def doctors_page(request: Request):
    return templates.TemplateResponse(request=request, name="doctors.html")

@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    return templates.TemplateResponse(request=request, name="schedule.html")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html")

@app.get("/triage", response_class=HTMLResponse)
async def triage_page(request: Request):
    return templates.TemplateResponse(request=request, name="triage.html")

@app.get("/patient", response_class=HTMLResponse)
async def patient_page(request: Request):
    return templates.TemplateResponse(request=request, name="patient.html")

@app.get("/doctor", response_class=HTMLResponse)
async def doctor_page(request: Request):
    return templates.TemplateResponse(request=request, name="doctor.html")

@app.get("/doctor/requests", response_class=HTMLResponse)
async def doctor_requests_page(request: Request):
    return templates.TemplateResponse(request=request, name="doctor_requests.html")


# --- API ROUTES ---

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

    # Attention regions derived from the Grad-CAM map -- computed per image
    # from what the model actually focused on. Wrapped so a failure here
    # degrades to "no boxes" rather than killing the whole analysis.
    try:
        regions = extract_regions(
            raw_cam=raw_current_map,
            label=pred_class,
            overall_confidence=confidence,
            threshold=0.55,   # raise for fewer/tighter boxes
            max_boxes=3
        )
    except Exception as region_err:
        print(f"⚠️ Region extraction failed (non-fatal): {region_err}")
        regions = []

    # The upload is saved with a .jpg extension regardless of what was sent,
    # so read the real MIME type off the upload instead of assuming JPEG.
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

    # ---- Demographics, so guidance is stratified per patient ------------
    patient_record = user_db.get_patient_by_email(patient_id)
    if patient_record:
        age = patient_record.get("age")
        gender = patient_record.get("gender")
        known_problem = patient_record.get("problem")
    else:
        age = gender = known_problem = None
        print(f"ℹ️ No patient record for '{patient_id}' -- guidance will not be "
              f"age/sex stratified.")

    # Scan confidence is stored 0-1; the triage engine and UI use percent.
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
        # weight_kg=...  <- wire up once app_patients has a weight column
    )


    stored_summary = (
        f"[{clinical_plan.get('urgency', 'ROUTINE')}] "
        f"{clinical_plan.get('headline', 'Clinical guidance')}\n\n"
        f"{clinical_plan.get('summary', '')}\n\n"
        f"Actions: " + "; ".join(clinical_plan.get("immediate_actions", []))
    )

    try:
        save_patient_interval_update(
            patient_id=patient_id,
            pain_level=pain_level,
            primary_symptom=primary_symptom,
            progression=symptom_progression,
            notes=additional_notes,
            suggestions=stored_summary
        )
    except Exception as db_err:
        # Logging the check-in is secondary to showing the patient their
        # guidance -- don't fail the whole request over a storage problem.
        print(f"⚠️ Could not save interval update (non-fatal): {db_err}")

    return {
        "status": "success",
        "message": "Routine status log successfully recorded.",
        "correlated_scan_context": f"{scan_type} ({prediction})",
        "scan_confidence": confidence_pct,
        "clinical_plan": clinical_plan,
        # kept so any older frontend code still finds something readable
        "patient_suggestions": stored_summary,
    }


@app.post('/api/signup_patient')
async def signup_patient(
        full_name: str = Body(...),
        email: str = Body(...),
        password: str = Body(...),
        age: int = Body(None),
        gender: str = Body(None),
        problem: str = Body(None)
):
    clean_email = email.strip().lower()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    success = user_db.insert_app_patient(
        full_name=full_name,
        email=clean_email,
        password=hashed_password,
        age=age,
        gender=gender,
        problem=problem
    )

    if success:
        return {"status": "success", "message": "Patient profile created successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Email already exists or invalid data.")


@app.post('/api/login_patient')
async def login_patient(
        email: str = Body(...),
        password: str = Body(...)
):
    clean_email = email.strip().lower()
    user = user_db.get_patient_by_email(clean_email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    stored_hash = user["password"]
    password_matches = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

    if not password_matches:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "status": "success",
        "message": "Login successful!",
        "token": issue_token(user["email"], "patient"),
        "patient": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "age": user["age"],
            "gender": user["gender"],
            "problem": user["problem"],
        }
    }


@app.post('/api/signup_doctor')
async def signup_doctor(
        full_name: str = Body(...),
        email: str = Body(...),
        password: str = Body(...),
        specialty: str = Body(None),
        experience: int = Body(None)
):
    clean_email = email.strip().lower()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    success = user_db.insert_app_doctor(
        full_name=full_name,
        email=clean_email,
        password=hashed_password,
        specialty=specialty,
        experience=experience
    )

    if success:
        register_doctor_in_catalog(clean_email, full_name, specialty, experience)
        return {"status": "success", "message": "Doctor profile created successfully!"}
    else:
        raise HTTPException(status_code=400, detail="Email already exists or invalid data.")


@app.post('/api/login_doctor')
async def login_doctor(
        email: str = Body(...),
        password: str = Body(...)
):
    clean_email = email.strip().lower()
    user = user_db.get_doctor_by_email(clean_email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    stored_hash = user["password"]
    password_matches = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

    if not password_matches:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "status": "success",
        "message": "Login successful!",
        "token": issue_token(user["email"], "doctor"),
        "doctor": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "specialty": user["specialty"],
            "experience": user["experience"],
        }
    }


@app.post('/api/login')
async def unified_login(
        email: str = Body(...),
        password: str = Body(...)
):
    clean_email = email.strip().lower()

    patient = user_db.get_patient_by_email(clean_email)
    if patient and bcrypt.checkpw(password.encode('utf-8'), patient["password"].encode('utf-8')):
        return {
            "status": "success",
            "role": "patient",
            "message": "Patient login successful!",
            "token": issue_token(patient["email"], "patient"),
            "user": {
                "id": patient["id"],
                "full_name": patient["full_name"],
                "email": patient["email"],
                "age": patient["age"],
                "gender": patient["gender"],
                "problem": patient["problem"],
            }
        }

    doctor = user_db.get_doctor_by_email(clean_email)
    if doctor and bcrypt.checkpw(password.encode('utf-8'), doctor["password"].encode('utf-8')):
        return {
            "status": "success",
            "role": "doctor",
            "message": "Doctor login successful!",
            "token": issue_token(doctor["email"], "doctor"),
            "user": {
                "id": doctor["id"],
                "full_name": doctor["full_name"],
                "email": doctor["email"],
                "specialty": doctor["specialty"],
                "experience": doctor["experience"],
            }
        }

    raise HTTPException(status_code=401, detail="Invalid email or password.")


@app.get('/api/patient_profile/{email}')
async def patient_profile(email: str):
    clean_email = email.strip().lower()
    user = user_db.get_patient_by_email(clean_email)

    if not user:
        raise HTTPException(status_code=404, detail="Patient not found.")

    history = get_patient_history(clean_email)
    scans = history.get("scans", []) if history else []

    timeline = [
        {
            "scan_type": row[0],
            "diagnosis": row[1],
            "confidence": round(float(row[2]) * 100, 2) if row[2] is not None else None,
            "date": row[3],
        }
        for row in scans
    ]

    return {
        "status": "success",
        "patient": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "age": user["age"],
            "gender": user["gender"],
            "problem": user["problem"],
        },
        "timeline": timeline
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)