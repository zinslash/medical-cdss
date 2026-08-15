"""
doctor_match.py  —  suggests relevant specialists based on what the scan showed.

Wire into app.py:

    from doctor_match import router as match_router
    app.include_router(match_router)

WHY A KEYWORD MAP RATHER THAN A SPECIALTY TABLE
`doctors_catalog.specialty` is free text typed at signup, so the same field
holds "Neurologist", "Neurology", "Consultant Neurosurgeon", "neuro" and so
on. Matching on substrings handles that variation without forcing every
doctor to pick from a fixed list. The trade-off is that a badly-typed
specialty won't match -- so there is always a general-physician fallback.
"""

from fastapi import APIRouter, HTTPException

from payments import _rows

router = APIRouter()


# Each organ maps to the substrings worth matching against, ordered so the
# most specific specialty ranks first. Matching is case-insensitive.
SPECIALTY_MAP = {
    "BRAIN": {
        "label": "Neurology",
        "keywords": ["neurolog", "neurosurg", "neuro"],
        "why": "Brain imaging findings are read and managed by neurologists; "
               "surgical questions go to a neurosurgeon.",
    },
    "CHEST": {
        "label": "Pulmonology",
        "keywords": ["pulmon", "respirat", "chest", "thoracic", "lung"],
        "why": "Chest radiograph findings are managed by pulmonologists "
               "(respiratory physicians).",
    },
    "BONE": {
        "label": "Orthopaedics",
        "keywords": ["orthop", "orthoped", "orthopaed", "ortho", "trauma",
                     "musculoskeletal", "rheumat"],
        "why": "Fractures and other bone findings are managed by orthopaedic "
               "surgeons; joint and inflammatory conditions by rheumatologists.",
    },
}

# Used when no specialist matches, and as a general option alongside
# specialists for normal results.
GENERAL_KEYWORDS = ["general", "physician", "family", "internal", "medicine", "gp"]


def _find_by_keywords(keywords, limit=6):
    """
    Returns listed doctors whose specialty contains any of the keywords.
    Ordered by how early the keyword matches (a "Neurologist" outranks a
    "General Physician with neurology interest"), then by experience.
    """
    if not keywords:
        return []

    clauses = " OR ".join(["LOWER(specialty) LIKE %s"] * len(keywords))
    params = tuple(f"%{k.lower()}%" for k in keywords)

    rows = _rows(
        "SELECT doctor_key, full_name, specialty, fee, experience, initials,"
        "       rating, reviews, bio"
        " FROM doctors_catalog"
        f" WHERE is_listed = 1 AND ({clauses})"
        " ORDER BY COALESCE(experience, 0) DESC, full_name"
        " LIMIT %s",
        (*params, limit),
    )

    out = []
    for r in rows or []:
        out.append({
            "doctor_key": r["doctor_key"],
            "full_name": r["full_name"],
            "specialty": r["specialty"],
            "fee": float(r["fee"]) if r["fee"] is not None else None,
            "experience": r.get("experience"),
            "initials": r.get("initials"),
            "rating": float(r["rating"]) if r.get("rating") is not None else None,
            "reviews": r.get("reviews") or 0,
            "bio": r.get("bio"),
        })
    return out


def suggest_for_scan(scan_type, diagnosis=None, limit=4):
    """
    Core logic, callable directly as well as over HTTP.

    Returns:
        {
          "scan_type": "BRAIN",
          "specialty_label": "Neurology",
          "why": "...",
          "specialists": [...],
          "general": [...],
          "fallback_used": bool,
          "note": str
        }
    """
    key = str(scan_type or "").upper().strip()
    mapping = SPECIALTY_MAP.get(key)

    if not mapping:
        # Unknown or missing scan type -- offer general physicians only,
        # rather than guessing at a specialty.
        general = _find_by_keywords(GENERAL_KEYWORDS, limit=limit)
        return {
            "scan_type": key or "UNKNOWN",
            "specialty_label": "General medicine",
            "why": "No scan type was identified, so no specialty can be "
                   "matched. A general physician can direct you further.",
            "specialists": [],
            "general": general,
            "fallback_used": True,
            "note": "Upload a scan first for a specialty-matched suggestion."
                    if not general else "",
        }

    specialists = _find_by_keywords(mapping["keywords"], limit=limit)
    general = _find_by_keywords(GENERAL_KEYWORDS, limit=3)

    diag_upper = str(diagnosis or "").upper()
    is_normal = "NORMAL" in diag_upper
    is_uncertain = "INCONCLUSIVE" in diag_upper

    if specialists:
        if is_normal:
            note = (f"The scan read as normal. If symptoms persist, these "
                    f"{mapping['label'].lower()} specialists cover this area.")
        elif is_uncertain:
            note = (f"The model was not confident enough to call this either "
                    f"way. A {mapping['label'].lower()} specialist should "
                    f"review the images directly.")
        else:
            note = (f"The scan flagged a possible finding. These "
                    f"{mapping['label'].lower()} specialists can review it.")
        fallback_used = False
    else:
        note = (f"No {mapping['label'].lower()} specialists are currently "
                f"listed. A general physician can assess you and refer on.")
        fallback_used = True

    return {
        "scan_type": key,
        "specialty_label": mapping["label"],
        "why": mapping["why"],
        "specialists": specialists,
        "general": general,
        "fallback_used": fallback_used,
        "note": note,
    }


@router.get("/api/suggest_doctors/{scan_type}")
async def suggest_doctors(scan_type: str, diagnosis: str = None, limit: int = 4):
    """
    GET /api/suggest_doctors/BRAIN?diagnosis=NORMAL

    Open endpoint -- it exposes only the public directory listing, the same
    information already shown on the doctors page.
    """
    if limit < 1 or limit > 12:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 12.")

    return {"status": "success", **suggest_for_scan(scan_type, diagnosis, limit)}