import os
import json
import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


# =====================================================================
# DESIGN NOTE
#
# This module returns STRUCTURED output (a dict), not a wall of text, so
# the frontend can render alerts, actions and escalation criteria as
# separate UI elements with their own severity styling.
#
# On dosing: patient age and sex are used for RISK STRATIFICATION and to
# adjust ESCALATION THRESHOLDS -- not to compute drug doses. An LLM that
# hallucinates a milligram figure for a 4-year-old causes real harm, and
# dose calculation is a solved problem that belongs in a validated drug
# database, not a language model. The system names appropriate drug
# CLASSES and defers the number to the package insert and a pharmacist,
# which is what patient-facing guidance actually does.
# =====================================================================


# Age bands that genuinely change clinical reasoning
def _age_band(age):
    if age is None:
        return "unknown"
    try:
        age = int(age)
    except (TypeError, ValueError):
        return "unknown"

    if age < 2:
        return "infant"
    if age < 12:
        return "child"
    if age < 18:
        return "adolescent"
    if age < 65:
        return "adult"
    return "older_adult"


# Populations where standard OTC advice needs extra caution
def _cautions_for(age_band, gender):
    cautions = []

    if age_band in ("infant", "child"):
        cautions.append(
            "Paediatric patient: aspirin is contraindicated (Reye's syndrome risk). "
            "All dosing must be weight-based and confirmed by a paediatrician or pharmacist."
        )
    if age_band == "older_adult":
        cautions.append(
            "Older adult: NSAIDs (ibuprofen, naproxen) carry elevated GI bleed and renal "
            "risk in this group, and interactions with common cardiac/antihypertensive "
            "medication are likely. Confirm with a pharmacist before use."
        )
    if age_band == "adolescent":
        cautions.append("Adolescent: avoid aspirin during any suspected viral illness.")
    if str(gender).strip().lower() in ("female", "f", "woman"):
        cautions.append(
            "If pregnant or breastfeeding, NSAIDs and several OTC preparations are "
            "restricted -- confirm with a clinician before taking anything."
        )

    return cautions


def _urgency_from_signals(diagnosis, pain_level, progression, age_band):
    """
    Deterministic escalation logic. This deliberately does NOT depend on the
    LLM -- urgency is too important to leave to a generative model that may
    phrase things inconsistently between runs.
    """
    diag_upper = str(diagnosis).upper().strip()
    abnormal = "NORMAL" not in diag_upper and diag_upper not in ("NONE", "")
    inconclusive = "INCONCLUSIVE" in diag_upper

    try:
        pain = int(pain_level)
    except (TypeError, ValueError):
        pain = 0

    worsening = str(progression).strip().lower() in ("worse", "worsening")

    # Very young and very old patients decompensate faster, so the same
    # symptom score warrants earlier escalation.
    vulnerable = age_band in ("infant", "older_adult")
    pain_threshold = 6 if vulnerable else 8

    if abnormal and not inconclusive:
        return "URGENT"
    if pain >= pain_threshold or (worsening and pain >= 5):
        return "URGENT" if vulnerable else "PROMPT"
    if inconclusive:
        return "PROMPT"
    if worsening:
        return "PROMPT"
    return "ROUTINE"


# Red flags worth naming explicitly per scan type. These are the symptoms
# that mean "stop reading this and get help now" regardless of what the
# model predicted.
_RED_FLAGS = {
    "CHEST": [
        "Difficulty breathing or breathlessness at rest",
        "Chest pain that is crushing, or spreads to the arm, jaw or back",
        "Blue or grey lips, face or fingertips",
        "Coughing up blood",
        "Confusion or unusual drowsiness",
        "Fever above 39°C that does not come down",
    ],
    "BRAIN": [
        "Sudden severe headache, described as the worst ever",
        "Weakness or numbness on one side of the body",
        "Slurred speech, or difficulty finding words",
        "Sudden vision loss or double vision",
        "Seizure, fainting, or loss of consciousness",
        "Repeated vomiting with headache",
    ],
    "BONE": [
        "Visible deformity, or bone breaking the skin",
        "Complete inability to bear weight or use the limb",
        "Numbness, pins and needles, or the limb turning pale or cold",
        "Rapidly increasing swelling or severe tightness",
        "Fever with a hot, red, painful joint",
    ],
}

_GENERIC_RED_FLAGS = [
    "Difficulty breathing",
    "Loss of consciousness or confusion",
    "Uncontrolled bleeding",
    "Symptoms that escalate suddenly rather than gradually",
]


def _fallback_plan(scan_type, diagnosis, symptom, urgency, age_band, cautions):
    """
    Used when the LLM is unavailable. Deterministic, conservative, and
    never invents specifics -- better a plain plan than a broken one
    during a live demo.
    """
    if urgency == "URGENT":
        actions = [
            "Arrange to be seen today -- emergency department or urgent care.",
            "Do not drive yourself if you feel unwell; have someone take you.",
            "Bring this report and any previous imaging with you.",
        ]
        otc = []
    elif urgency == "PROMPT":
        actions = [
            "Book an appointment with your doctor within the next 24-48 hours.",
            "Rest and avoid activity that reproduces the symptom.",
            "Write down when the symptom appears and what makes it better or worse.",
        ]
        otc = [
            "Simple analgesia (paracetamol/acetaminophen) is usually the first choice. "
            "Follow the package directions for your age and weight."
        ]
    else:
        actions = [
            "Rest, keep hydrated, and monitor how the symptom changes over 48 hours.",
            "Avoid strenuous activity until the symptom settles.",
        ]
        otc = [
            "Paracetamol/acetaminophen for general pain or fever, per package directions.",
            "Ask a pharmacist before combining any products -- many contain the same "
            "active ingredient, and doubling up is the most common cause of accidental overdose.",
        ]

    return {
        "summary": f"Automated guidance for '{symptom}' following a {scan_type} scan "
                   f"reported as {diagnosis}.",
        "immediate_actions": actions,
        "otc_guidance": otc,
        "monitoring": [
            "Note any change in severity, and whether new symptoms appear.",
            "Seek care sooner if anything on the red-flag list below occurs.",
        ],
        "cautions": cautions,
        "llm_available": False,
    }


def get_dynamic_clinical_advice(scan_type, diagnosis, confidence, pain_level,
                                progression, symptom,
                                age=None, gender=None, known_problem=None,
                                weight_kg=None):
    """
    Returns a STRUCTURED dict, not a string:

        {
          "urgency": "URGENT" | "PROMPT" | "ROUTINE",
          "headline": str,
          "patient_context": {...},
          "summary": str,
          "immediate_actions": [str],
          "otc_guidance": [str],
          "monitoring": [str],
          "cautions": [str],
          "red_flags": [str],
          "disclaimer": str,
          "generated_at": iso timestamp
        }

    age / gender / known_problem come from the patient record so guidance
    is stratified rather than one-size-fits-all. weight_kg is accepted but
    optional -- your app_patients table has no weight column yet; add one
    if you want it surfaced in the context panel.
    """
    diag_upper = str(diagnosis).upper().strip()
    scan_key = str(scan_type).upper().strip()
    band = _age_band(age)
    cautions = _cautions_for(band, gender)
    now = datetime.datetime.now().isoformat(timespec='seconds')

    red_flags = _RED_FLAGS.get(scan_key, _GENERIC_RED_FLAGS)

    patient_context = {
        "age": age,
        "age_band": band,
        "gender": gender,
        "known_problem": known_problem,
        "weight_kg": weight_kg,
    }

    # ---- No scan on file -------------------------------------------------
    if diag_upper in ("NONE", "") or scan_key == "UNKNOWN":
        return {
            "urgency": "ROUTINE",
            "headline": "No scan on file for this patient",
            "patient_context": patient_context,
            "summary": "No imaging has been recorded against this patient ID yet, so "
                       "symptom guidance cannot be cross-referenced against a scan.",
            "immediate_actions": [
                "Check the patient ID matches exactly, with no trailing spaces.",
                "Upload a scan first, then submit the symptom check-in again.",
            ],
            "otc_guidance": [],
            "monitoring": [],
            "cautions": cautions,
            "red_flags": red_flags,
            "disclaimer": DISCLAIMER,
            "generated_at": now,
        }

    urgency = _urgency_from_signals(diagnosis, pain_level, progression, band)

    # ---- Try the LLM for the narrative parts -----------------------------
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

        prompt = ChatPromptTemplate.from_template("""
You are a clinical decision support assistant producing patient-facing guidance.
Return ONLY valid JSON. No markdown, no code fences, no preamble.

IMAGING RESULT
Scan type: {scan_type}
Model prediction: {diagnosis}
Model confidence: {confidence}%

PATIENT
Age: {age} (band: {age_band})
Sex: {gender}
Reported ongoing problem: {known_problem}

CURRENT SYMPTOMS
Primary symptom: {symptom}
Pain: {pain_level}/10
Change since last check-in: {progression}

TRIAGE LEVEL ALREADY DETERMINED: {urgency}
Write guidance consistent with this level. Do not soften or escalate it.

HARD RULES
- NEVER state a specific dose, milligram amount, tablet count, or frequency.
  Name the drug CLASS or common generic name only, and direct the patient to
  the package directions and a pharmacist for the amount. Dose errors are the
  main harm vector here and you do not have the information to compute one.
- Do not name prescription-only medicines as something the patient should take.
- Tailor the wording to the age band. Guidance for an infant, an adult, and an
  older adult should differ meaningfully.
- If the model prediction is abnormal or inconclusive, do not reassure. Say
  plainly that it needs clinician review.
- Confidence below 70% means the model is uncertain -- say so rather than
  presenting the prediction as established.
- Be warm and plain-spoken. No jargon the patient would have to look up.

Return exactly this JSON shape:
{{
  "headline": "one short line summarising the situation",
  "summary": "2-3 sentences: what the scan showed, how certain, what it means for them",
  "immediate_actions": ["2-4 concrete things to do now, ordered by priority"],
  "otc_guidance": ["1-3 items naming drug class/generic name, always deferring the dose"],
  "monitoring": ["2-3 things to watch for over the next 24-48 hours"]
}}
""")

        chain = prompt | llm
        response = chain.invoke({
            "scan_type": scan_type,
            "diagnosis": diagnosis,
            "confidence": confidence,
            "age": age if age is not None else "not recorded",
            "age_band": band,
            "gender": gender or "not recorded",
            "known_problem": known_problem or "none recorded",
            "symptom": symptom,
            "pain_level": pain_level,
            "progression": progression,
            "urgency": urgency,
        })

        raw = response.content.strip()
        # Models sometimes wrap JSON in fences despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        plan = json.loads(raw)

        return {
            "urgency": urgency,
            "headline": plan.get("headline", "Clinical guidance"),
            "patient_context": patient_context,
            "summary": plan.get("summary", ""),
            "immediate_actions": plan.get("immediate_actions", []),
            "otc_guidance": plan.get("otc_guidance", []),
            "monitoring": plan.get("monitoring", []),
            "cautions": cautions,
            "red_flags": red_flags,
            "disclaimer": DISCLAIMER,
            "generated_at": now,
            "llm_available": True,
        }

    except Exception as e:
        print(f"❌ LLM unavailable, using deterministic fallback: {e}")
        fallback = _fallback_plan(scan_type, diagnosis, symptom, urgency, band, cautions)
        return {
            "urgency": urgency,
            "headline": {
                "URGENT": "Needs to be seen today",
                "PROMPT": "Needs a clinician within 24-48 hours",
                "ROUTINE": "Self-care with monitoring",
            }[urgency],
            "patient_context": patient_context,
            "summary": fallback["summary"],
            "immediate_actions": fallback["immediate_actions"],
            "otc_guidance": fallback["otc_guidance"],
            "monitoring": fallback["monitoring"],
            "cautions": cautions,
            "red_flags": red_flags,
            "disclaimer": DISCLAIMER,
            "generated_at": now,
            "llm_available": False,
        }


DISCLAIMER = (
    "This is an automated research prototype, not a medical device and not a "
    "diagnosis. The imaging model is imperfect and can be confidently wrong. "
    "Nothing here replaces assessment by a qualified clinician. If you feel "
    "seriously unwell, seek emergency care regardless of what this says."
)