"""
Applies four targeted fixes to triage.html.

Run:  python patch_triage.py path/to/triage.html
"""
import json
import shutil
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "triage.html"
anchors = json.load(open("anchors.json"))

src = open(path, encoding="utf-8").read()
before = src

# ---------------------------------------------------------------------------
# FIX 1 — the session guard only accepted patients.
#
# It read localStorage.loggedInPatient and redirected anything else to /login.
# A doctor has loggedInDoctor set, never loggedInPatient, so pressing "Upload a
# scan" from the doctor dashboard bounced straight back out with no message.
#
# Doctors can now use the page, but a scan still has to be attributed to a
# patient, so they choose one instead of it being filled in for them.
# ---------------------------------------------------------------------------
NEW_GUARD = '''    (async function initSession() {
        const headerLabel = document.getElementById('headerUserLabel');
        const patientIdField = document.getElementById('patientId');
        const symPatientIdField = document.getElementById('symPatientId');
        const hint = document.getElementById('patientIdHint');

        let patient = null, doctor = null;
        try {
            patient = JSON.parse(localStorage.getItem('loggedInPatient') || 'null');
            doctor  = JSON.parse(localStorage.getItem('loggedInDoctor')  || 'null');
        } catch (err) {
            console.error('Stored session could not be read:', err);
        }

        // ---- Patient: the scan is theirs, so the field is fixed ----------
        if (patient) {
            const identifier = patient.email;
            patientIdField.value = identifier;
            symPatientIdField.value = identifier;
            headerLabel.innerText = 'Logged in as ' + (patient.full_name || identifier);
            return;
        }

        // ---- Doctor: they pick which patient this scan belongs to --------
        if (doctor) {
            headerLabel.innerText = 'Logged in as ' + (doctor.full_name || doctor.email)
                                  + ' \\u00b7 doctor';

            patientIdField.readOnly = false;
            symPatientIdField.readOnly = false;
            patientIdField.placeholder = 'Patient email';
            symPatientIdField.placeholder = 'Patient email';
            patientIdField.setAttribute('list', 'patientOptions');
            symPatientIdField.setAttribute('list', 'patientOptions');
            hint.classList.remove('hidden');

            // Offer the patients who have actually booked this doctor.
            try {
                const token = localStorage.getItem('authToken');
                if (!token) return;

                const res = await fetch('/api/doctor/requests?status=all', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (!res.ok) return;

                const data = await res.json();
                const seen = new Map();
                data.upcoming.concat(data.past).forEach(a => {
                    if (a.patient_email && !seen.has(a.patient_email)) {
                        seen.set(a.patient_email, a.patient_name || a.patient_email);
                    }
                });

                if (seen.size === 0) return;

                const dl = document.getElementById('patientOptions');
                dl.innerHTML = '';
                seen.forEach((name, email) => {
                    const opt = document.createElement('option');
                    opt.value = email;
                    opt.label = name;
                    dl.appendChild(opt);
                });
                hint.innerText = seen.size === 1
                    ? '1 patient has booked you. Start typing to pick them.'
                    : seen.size + ' patients have booked you. Start typing to pick one.';
            } catch (err) {
                console.error('Could not load your patient list:', err);
            }
            return;
        }

        // ---- Nobody is signed in ----------------------------------------
        headerLabel.innerText = 'Not signed in \\u2014 taking you to log in...';
        window.location.href = '/login';
    })();

    // Keep the two patient fields in step, whichever one is edited.
    document.getElementById('patientId').addEventListener('input', e => {
        document.getElementById('symPatientId').value = e.target.value;
    });'''

assert anchors["guard"] in src, "session guard block not found"
src = src.replace(anchors["guard"], NEW_GUARD)

# ---------------------------------------------------------------------------
# FIX 2 — "Back to Home" pointed at "/", which is now the landing page.
# ---------------------------------------------------------------------------
assert anchors["back"] in src, "back button not found"
src = src.replace(anchors["back"],
                  '''        <a href="/home" class="back-btn">&larr; Back to Home</a>''')

# ---------------------------------------------------------------------------
# FIX 3 — the patient field needs a datalist and a hint line for doctors.
# ---------------------------------------------------------------------------
assert anchors["field"] in src, "patientId field not found"
src = src.replace(anchors["field"], '''                <input type="text" id="patientId" class="form-input" placeholder="Log in to auto-fill" required readonly autocomplete="off">
                <datalist id="patientOptions"></datalist>
                <p id="patientIdHint" class="field-hint hidden">Enter the email of the patient this scan belongs to.</p>''')

assert anchors["symfield"] in src, "symPatientId field not found"
src = src.replace(anchors["symfield"], '''                <input type="text" id="symPatientId" class="form-input" placeholder="Log in to auto-fill" required readonly autocomplete="off">''')

# ---------------------------------------------------------------------------
# FIX 4 — style for the hint line.
# ---------------------------------------------------------------------------
src = src.replace('''        .hidden { display: none !important; }''',
'''        .hidden { display: none !important; }

        .field-hint {
            font-size: 12.5px;
            color: #6B7280;
            margin-top: 6px;
            line-height: 1.45;
        }''')

assert src != before, "nothing changed"
shutil.copy(path, path + ".bak")
open(path, "w", encoding="utf-8").write(src)
print("patched. original saved as", path + ".bak")