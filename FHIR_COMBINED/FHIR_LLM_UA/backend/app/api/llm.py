# backend/app/api/llm.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy import text
import os

from ..core.database import engine
from ..core.llm import generate_chat, model_name
from ..core.prompts import render_prompt

router = APIRouter(prefix="/patients", tags=["llm"])

# ---- tunables (env overrides) ----
MAX_CONDITIONS = int(os.getenv("LLM_MAX_CONDITIONS", "50"))       # after dedupe
MAX_OBSERVATIONS = int(os.getenv("LLM_MAX_OBSERVATIONS", "100"))  # all rows for trends
MAX_NOTES = int(os.getenv("LLM_MAX_NOTES", "10"))                 # most-recent notes

# ---- response model ----
class LlmSummaryResponse(BaseModel):
    patientId: str
    model: str
    summary: str
    contextCounts: Dict[str, int]

# ---- helpers ----
def _iso(v):
    try:
        return v.isoformat() if v else None
    except Exception:
        return str(v) if v else None

def _age_years(d):
    if not d:
        return None
    from datetime import date as _date
    t = _date.today()
    return t.year - d.year - ((t.month, t.day) < (d.month, d.day))

def _parse_numeric_date(n: Any) -> Optional[str]:
    """Parse e.g., 20230221.00 -> '2023-02-21' for LOINC 67723-7 fallback."""
    if n is None:
        return None
    try:
        s = str(int(float(n)))  # handles decimal-as-string or float
        if len(s) == 8:
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    except Exception:
        pass
    return None

# ---- route ----
@router.get("/{patient_id}/llm_summary", response_model=LlmSummaryResponse)
def llm_patient_summary(patient_id: str, category: str = "patient_summary"):
    """
    Generate a category-specific summary for the selected patient.
    category: patient_summary | conditions | observations | notes
    """
    with engine.connect() as conn:
        # Demographics
        sql_p = """
        SELECT patient_id, CONCAT(given_name, ' ', family_name) AS name,
               birth_date, gender, city, state, postal_code
        FROM patients
        WHERE patient_id = :pid
        LIMIT 1
        """
        p = conn.execute(text(sql_p), {"pid": patient_id}).mappings().first()
        if not p:
            raise HTTPException(status_code=404, detail="patient not found")

        # Conditions (dedupe by code|display, newest first), then cap by MAX_CONDITIONS
        sql_c = """
        SELECT c.code, c.display, c.clinical_status, c.effectiveDateTime AS recordedDate
        FROM conditions c
        WHERE c.patient_id = :pid
        ORDER BY COALESCE(c.effectiveDateTime, '1000-01-01') DESC, c.id DESC
        """
        rows_c = conn.execute(text(sql_c), {"pid": patient_id}).mappings().all()
        seen = set()
        conditions: List[Dict[str, Any]] = []
        for r in rows_c:
            key = f"{r['code']}|{r['display']}"
            if key in seen:
                continue
            seen.add(key)
            conditions.append({
                "code": r["code"],
                "display": r["display"],
                "clinicalStatus": r["clinical_status"],
                "recordedDate": _iso(r["recordedDate"]),
            })
            if len(conditions) >= MAX_CONDITIONS:
                break

        # Observations: ALL rows for trends (ordered newest first), cap by MAX_OBSERVATIONS
        # (We keep fallback for 67723-7 when effectiveDateTime is NULL)
        sql_o = """
        SELECT o.code, o.display, o.value_numeric AS valueNumber, o.value_string AS valueString,
               o.unit, o.effectiveDateTime, o.value_numeric AS raw_num
        FROM observations o
        WHERE o.patient_id = :pid
        ORDER BY COALESCE(o.effectiveDateTime, '1000-01-01') DESC, o.id DESC
        """
        rows_o = conn.execute(text(sql_o), {"pid": patient_id}).mappings().all()
        observations: List[Dict[str, Any]] = []
        for r in rows_o:
            eff = r["effectiveDateTime"]
            if not eff and (r["code"] or "") == "67723-7":
                eff = _parse_numeric_date(r["raw_num"])

            # Convert Decimal to float for JSON serialization
            value_number = r["valueNumber"]
            if value_number is not None:
                try:
                    value_number = float(value_number)
                except (ValueError, TypeError):
                    value_number = None

            observations.append({
                "code": r["code"],
                "display": r["display"],
                "valueNumber": value_number,
                "valueString": r["valueString"],
                "unit": r["unit"],
                "effectiveDateTime": _iso(eff),
            })
            if len(observations) >= MAX_OBSERVATIONS:
                break

        # Notes: most-recent first, limited by MAX_NOTES
        sql_n = """
        SELECT COALESCE(n.note_datetime, n.created_at) AS created,
               n.note_text AS text, n.source_type AS sourceType,
               n.filename_txt AS fileName, n.base_key AS baseKey
        FROM notes n
        WHERE n.patient_id = :pid
        ORDER BY COALESCE(n.note_datetime, n.created_at) DESC, n.id DESC
        LIMIT :limit
        """
        rows_n = conn.execute(text(sql_n), {"pid": patient_id, "limit": MAX_NOTES}).mappings().all()
        notes = [{
            "created": _iso(r["created"]),
            "text": r["text"],
            "sourceType": r["sourceType"],
            "fileName": r["fileName"],
            "baseKey": r["baseKey"],
        } for r in rows_n]

    # Compact demographics for prompt
    demo = {
        "patientId": p["patient_id"],
        "name": p["name"],
        "birthDate": _iso(p["birth_date"]),
        "ageYears": _age_years(p["birth_date"]),
        "gender": p["gender"],
        "city": p["city"], "state": p["state"], "postalCode": p["postal_code"],
    }

    context_counts = {
        "conditions": len(conditions),
        "observations": len(observations),
        "notes": len(notes),
    }

    # ---------- Build category-specific prompts ----------
    prompts = render_prompt(
        category,
        demo=demo,
        conditions=conditions,
        observations=observations,
        notes=notes,
    )  # -> {'system': ..., 'user': ...}

    # ---------- Generate ----------
    summary_text = generate_chat(prompts["system"], prompts["user"]).strip()

    return LlmSummaryResponse(
        patientId=str(patient_id),
        model=model_name(),
        summary=summary_text,
        contextCounts=context_counts,
    )
