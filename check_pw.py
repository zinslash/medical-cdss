"""
check_pw.py — diagnostic. Run:  python check_pw.py

Tells you whether the stored hash matches the password you think you set,
and whether the reset actually wrote to the row login reads from.
Delete this file when you're done.
"""
import bcrypt
import user_db

EMAIL = input("Email: ").strip().lower()
PASSWORD = input("Password you're trying to log in with: ")

print("\n" + "=" * 60)

# 1. Which table(s) hold this email?
patient = user_db.get_patient_by_email(EMAIL)
doctor = user_db.get_doctor_by_email(EMAIL)

print(f"found in app_patients : {'YES' if patient else 'no'}")
print(f"found in app_doctors  : {'YES' if doctor else 'no'}")

if not patient and not doctor:
    print("\n>>> No account with that email. Check for typos or a different")
    print(">>> email than the one you reset. Emails are stored lowercased.")
    raise SystemExit

if patient and doctor:
    print("\n>>> WARNING: same email in BOTH tables. Login checks patients")
    print(">>> first, so the doctor row is unreachable.")

row = patient or doctor
stored = row["password"]

print("=" * 60)
print(f"stored hash    : {stored[:35]}...")
print(f"hash length    : {len(stored)}  (bcrypt should be 60)")
print(f"starts with    : {stored[:4]}  (bcrypt should be $2a$ or $2b$)")

# 2. Does the password verify?
print("=" * 60)
try:
    ok = bcrypt.checkpw(PASSWORD.encode("utf-8"), stored.encode("utf-8"))
    print(f"password matches: {ok}")
except Exception as e:
    print(f"checkpw threw   : {e}")
    ok = False

# 3. Common gotchas
print("=" * 60)
if not ok:
    if len(stored) != 60:
        print(">>> The hash is not 60 characters. Your MySQL `password` column")
        print(">>> is probably too short and is TRUNCATING the hash on write.")
        print(">>> Fix: ALTER TABLE app_patients MODIFY password VARCHAR(255);")
        print(">>>      ALTER TABLE app_doctors  MODIFY password VARCHAR(255);")
    elif not stored.startswith(("$2a$", "$2b$", "$2y$")):
        print(">>> That doesn't look like a bcrypt hash at all.")
    else:
        # Is it maybe still the OLD password?
        guess = input("\nOld password (blank to skip): ")
        if guess and bcrypt.checkpw(guess.encode("utf-8"), stored.encode("utf-8")):
            print(">>> The OLD password still works -- the reset never wrote.")
            print(">>> The UPDATE hit a different row or a different table.")
        else:
            print(">>> Hash is valid but matches neither password.")
            print(">>> Check for a trailing space, or that you reset the same")
            print(">>> account you're logging into.")
else:
    print(">>> The password IS correct in the database.")
    print(">>> So the problem is in the login request, not the reset.")
    print(">>> Check you're posting to /api/login with this exact email.")
print("=" * 60)