import mysql.connector
from mysql.connector import Error



DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "medical_pipeline",
}


def get_connection():
    """Opens a fresh connection to the XAMPP MySQL server."""
    return mysql.connector.connect(**DB_CONFIG)


def init_app_db():
    """
    Initializes the separate app tables (app_doctors, app_patients) inside
    the medical_pipeline MySQL database. Safe to call every startup --
    CREATE TABLE IF NOT EXISTS won't touch existing data.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_doctors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            specialty VARCHAR(255) NOT NULL,
            experience VARCHAR(255) NULL,
            focus_areas VARCHAR(255) NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_patients (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            age INT NULL,
            gender VARCHAR(50) NULL,
            problem VARCHAR(255) NULL
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()


def insert_app_patient(full_name, email, password, age, gender, problem):
    """
    Inserts a patient into app_patients.
    Returns True on success, False if the email already exists (or another
    DB error occurs).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO app_patients (full_name, email, password, age, gender, problem)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (full_name, email, password, age, gender, problem))
        conn.commit()
        return True

    except Error as e:
        # 1062 = MySQL's duplicate-entry error (violates UNIQUE on email)
        if getattr(e, "errno", None) == 1062:
            print(f"⚠️ Signup failed: email '{email}' already exists.")
        else:
            print(f"⚠️ MySQL Error during signup: {e}")
        return False

    finally:
        if conn is not None and conn.is_connected():
            cursor.close()
            conn.close()


def insert_app_doctor(full_name, specialty, experience, focus_areas):
    """Inserts a doctor into app_doctors."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO app_doctors (full_name, specialty, experience, focus_areas)
        VALUES (%s, %s, %s, %s)
    ''', (full_name, specialty, experience, focus_areas))
    conn.commit()
    cursor.close()
    conn.close()
    return True


def get_patient_by_email(email: str):
    """
    Fetches a patient record by email as a dict. Used for login verification.
    Returns None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM app_patients WHERE email = %s", (email,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def insert_app_doctor(full_name, email, password, specialty, experience):
    """Inserts a new doctor record into the XAMPP MySQL database."""
    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        query = """
                INSERT INTO doctors (full_name, email, password, specialty, experience)
                VALUES (%s, %s, %s, %s, %s) \
                """
        cursor.execute(query, (full_name, email, password, specialty, experience))
        connection.commit()
        return True
    except Exception as e:
        print(f"Error inserting doctor: {e}")
        return False
    finally:
        cursor.close()
        connection.close()


def get_doctor_by_email(email):
    """Retrieves a doctor record by email for authentication."""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM doctors WHERE email = %s"
        cursor.execute(query, (email,))
        doctor = cursor.fetchone()
        return doctor
    except Exception as e:
        print(f"Error fetching doctor: {e}")
        return None
    finally:
        cursor.close()
        connection.close()