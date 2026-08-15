import sqlite3
import datetime


CLINICAL_PROTOCOLS = {
    "chest": {
        0: {
            "condition": "NORMAL",
            "impression": "Lungs appear clear. No visible opacities or signs of consolidation.",
            "triage": "Standard preventative care. No immediate emergency action required."
        },
        1: {
            "condition": "PNEUMONIA",
            "impression": "Consolidation or opacities detected indicative of fluid/infection in the lungs.",
            "triage": "URGENT: Consult a pulmonologist or primary care physician immediately. Monitor blood oxygen levels."
        }
    },
    "brain": {
        0: {
            "condition": "NORMAL",
            "impression": "Brain parenchyma appears unremarkable. No visible mass effect, hemorrhage, or structural lesions.",
            "triage": "Standard preventative care. No immediate emergency action required."
        },
        1: {
            "condition": "BRAIN ABNORMALITY / TUMOR",
            "impression": "Anomalous hyperintense region or structural asymmetry detected within cranial tissue.",
            "triage": "URGENT: Immediate neurological evaluation and follow-up diagnostic imaging recommended."
        }
    },
    "bone": {
        0: {
            "condition": "NORMAL",
            "impression": "Cortical bone alignment is intact. No evidence of disruption or fracture lines.",
            "triage": "Standard preventative care. Continue routine orthopedic care."
        },
        1: {
            "condition": "FRACTURE DETECTED",
            "impression": "Discontinuation of cortical bone architecture observed indicative of osseous trauma.",
            "triage": "URGENT: Immobilize the affected extremity and consult an orthopedic specialist immediately."
        }
    }
}


def get_protocol(scan_type: str, class_label):

    try:
        organ = str(scan_type).lower().strip()
        label_str = str(class_label).upper().strip()

        # 1. BRAIN ROUTING
        if "brain" in organ:
            if "ABNORMAL" in label_str or "TUMOR" in label_str or label_str == "1":
                return CLINICAL_PROTOCOLS["brain"][1]
            else:
                return CLINICAL_PROTOCOLS["brain"][0]

                # 2. CHEST ROUTING
        elif "chest" in organ:
            if "PNEUMONIA" in label_str or "ABNORMAL" in label_str or label_str == "1":
                return CLINICAL_PROTOCOLS["chest"][1]
            else:
                return CLINICAL_PROTOCOLS["chest"][0]

        # 3. BONE ROUTING
        elif "bone" in organ:
            if "FRACTURE" in label_str or "ABNORMAL" in label_str or label_str == "1":
                return CLINICAL_PROTOCOLS["bone"][1]
            else:
                return CLINICAL_PROTOCOLS["bone"][0]

        # Safe Fallback
        return CLINICAL_PROTOCOLS["brain"][0]

    except Exception as e:
        print(f"❌ Safety Fallback Triggered: {e}")
        return {
            "condition": "Analysis Inconclusive",
            "impression": "Clinical Decision Support System experienced a parsing fallback.",
            "triage": "Please manually review the raw model inference results."
        }

# Add this inside init_db(), alongside your existing CREATE TABLE calls
def init_bookings_table():
    conn = sqlite3.connect(DB_PATH)  # use whatever DB_PATH/connection your file already uses
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id TEXT NOT NULL,
            doctor_name TEXT,
            specialty TEXT,
            patient_email TEXT NOT NULL,
            patient_name TEXT,
            patient_age TEXT,
            patient_gender TEXT,
            appointment_date TEXT,
            appointment_time TEXT,
            problem TEXT,
            fee REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_booking(doctor_id, doctor_name, specialty, patient_email, patient_name,
                  patient_age, patient_gender, appointment_date, appointment_time,
                  problem, fee):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings
        (doctor_id, doctor_name, specialty, patient_email, patient_name,
         patient_age, patient_gender, appointment_date, appointment_time, problem, fee)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (doctor_id, doctor_name, specialty, patient_email, patient_name,
          patient_age, patient_gender, appointment_date, appointment_time, problem, fee))
    conn.commit()
    conn.close()


def get_bookings_for_doctor(doctor_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, patient_name, patient_email, patient_age, patient_gender,
               appointment_date, appointment_time, problem, fee, status, created_at
        FROM bookings
        WHERE doctor_id = ?
        ORDER BY created_at DESC
    """, (str(doctor_id),))
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "patient_name": row[1],
            "patient_email": row[2],
            "patient_age": row[3],
            "patient_gender": row[4],
            "appointment_date": row[5],
            "appointment_time": row[6],
            "problem": row[7],
            "fee": row[8],
            "status": row[9],
            "created_at": row[10],
        }
        for row in rows
    ]

# =====================================================================
# 2. SQLite Database Configuration
# =====================================================================
DB_NAME = "medical_pipeline.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS patient_scans
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       patient_id
                       TEXT
                       NOT
                       NULL,
                       scan_type
                       TEXT
                       NOT
                       NULL,
                       file_path
                       TEXT
                       NOT
                       NULL,
                       prediction
                       TEXT
                       NOT
                       NULL,
                       confidence
                       REAL
                       NOT
                       NULL,
                       timestamp
                       DATETIME
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS patient_updates
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       patient_id
                       TEXT
                       NOT
                       NULL,
                       pain_level
                       INTEGER
                       NOT
                       NULL,
                       primary_symptom
                       TEXT
                       NOT
                       NULL,
                       symptom_progression
                       TEXT
                       NOT
                       NULL,
                       additional_notes
                       TEXT,
                       generated_suggestions
                       TEXT,
                       timestamp
                       DATETIME
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')

    conn.commit()
    conn.close()
    print("💾 Database tables initialized successfully!")



def save_patient_scan(patient_id: str, scan_type: str, file_path: str, prediction: str, confidence: float):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
                   SELECT id
                   FROM patient_scans
                   WHERE patient_id = ?
                     AND scan_type = ?
                   ORDER BY timestamp DESC LIMIT 1
                   ''', (patient_id, scan_type.lower()))

    existing_row = cursor.fetchone()

    if existing_row:
        cursor.execute('''
                       UPDATE patient_scans
                       SET file_path  = ?,
                           prediction = ?,
                           confidence = ?,
                           timestamp  = ?
                       WHERE id = ?
                       ''', (file_path, str(prediction), float(confidence), datetime.datetime.now(), existing_row[0]))
    else:
        cursor.execute('''
                       INSERT INTO patient_scans (patient_id, scan_type, file_path, prediction, confidence, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', (patient_id, scan_type.lower(), file_path, str(prediction), float(confidence),
                             datetime.datetime.now()))

    conn.commit()
    conn.close()


def get_previous_scan(patient_id: str, scan_type: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
                   SELECT file_path, prediction, confidence, timestamp
                   FROM patient_scans
                   WHERE patient_id = ? AND scan_type = ?
                   ORDER BY timestamp DESC LIMIT 1
                   ''', (patient_id, scan_type.lower()))
    row = cursor.fetchone()
    conn.close()
    return row


def save_patient_interval_update(patient_id: str, pain_level: int, primary_symptom: str, progression: str, notes: str,
                                 suggestions: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
                   INSERT INTO patient_updates (patient_id, pain_level, primary_symptom, symptom_progression,
                                                additional_notes, generated_suggestions, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ''', (patient_id, int(pain_level), primary_symptom, progression, notes, suggestions,
                         datetime.datetime.now()))
    conn.commit()
    conn.close()


def get_patient_history(patient_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT scan_type, prediction, confidence, timestamp FROM patient_scans WHERE patient_id = ? ORDER BY timestamp DESC',
        (patient_id,))
    scans = cursor.fetchall()
    cursor.execute(
        'SELECT pain_level, primary_symptom, symptom_progression, generated_suggestions, timestamp FROM patient_updates WHERE patient_id = ? ORDER BY timestamp DESC',
        (patient_id,))
    updates = cursor.fetchall()
    conn.close()
    return {"scans": scans, "symptom_updates": updates}


# Initialize database
init_db()