import mysql.connector
from mysql.connector import Error

# Configuration pointing to your XAMPP database named 'ai_triage_db'
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "ai_triage_db",  # Your exact XAMPP database name
}

def get_connection():
    """Opens a connection to the ai_user_db MySQL server."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"❌ Error connecting to ai_triage_db: {e}")
    return None

def init_user_db():
    """
    Creates the ai_triage_db database if it doesn't exist, then builds
    the app_patients and app_doctors tables inside it.
    """
    try:
        temp_conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"]
        )
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        temp_cursor.close()
        temp_conn.close()
    except Error as e:
        print(f"⚠️ Could not verify/create database: {e}")

    conn = get_connection()
    if not conn:
        return

    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_doctors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            specialty VARCHAR(255) NOT NULL,
            experience INT NULL
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
    print("✅ Database 'ai_triage_db' and user tables initialized successfully!")


def insert_app_patient(full_name, email, password, age, gender, problem):
    conn = None
    try:
        conn = get_connection()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO app_patients (full_name, email, password, age, gender, problem)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (full_name, email, password, age, gender, problem))
        conn.commit()
        return True
    except Error as e:
        if getattr(e, "errno", None) != 1062:
            print(f"⚠️ MySQL Error: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def insert_app_doctor(full_name, email, password, specialty, experience):
    conn = None
    try:
        conn = get_connection()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO app_doctors (full_name, email, password, specialty, experience)
            VALUES (%s, %s, %s, %s, %s)
        ''', (full_name, email, password, specialty, experience))
        conn.commit()
        return True
    except Error as e:
        if getattr(e, "errno", None) != 1062:
            print(f"⚠️ MySQL Error: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def get_patient_by_email(email: str):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM app_patients WHERE email = %s", (email,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def get_doctor_by_email(email: str):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM app_doctors WHERE email = %s", (email,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result