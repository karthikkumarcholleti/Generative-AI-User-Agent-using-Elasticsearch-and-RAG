# backend/app/api/summary.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy import text
import os
import time
import math
from datetime import datetime

try:
    from scipy.stats import linregress as _linregress
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False

from ..core.database import engine
from ..core.llm import generate_chat, model_name
from ..core.prompts import render_prompt
from .condition_categorizer import categorize_condition, group_conditions_by_category
import logging

# Import torch for OOM error handling
try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["summary"])

# ---- tunables (env overrides) ----
MAX_CONDITIONS = int(os.getenv("LLM_MAX_CONDITIONS", "50"))       # after dedupe
MAX_OBSERVATIONS = int(os.getenv("LLM_MAX_OBSERVATIONS", "100"))  # reduced from 200 to 100 to save memory
MAX_NOTES = int(os.getenv("LLM_MAX_NOTES", "3"))                  # reduced from 5 to 3 for memory efficiency
MAX_NOTE_CHARS = int(os.getenv("LLM_MAX_NOTE_CHARS", "2500"))     # reduced from 4000 to 2500 for memory efficiency

# ---- In-memory cache for summaries ----
summary_cache: Dict[str, Dict[str, Any]] = {}
MAX_CACHE_SIZE = int(os.getenv("LLM_MAX_CACHE_PATIENTS", "3"))  # Keep only last 3 patients

# ---- Patient session tracking ----
_current_patient_id: Optional[str] = None

# ---- response models ----
class LlmSummaryResponse(BaseModel):
    patientId: str
    model: str
    summary: str
    contextCounts: Dict[str, int]

class AllSummariesResponse(BaseModel):
    patientId: str
    model: str
    summaries: Dict[str, str]  # category -> summary text
    contextCounts: Dict[str, int]
    generatedAt: str

class SummaryDemographics(BaseModel):
    patientId: str
    name: str
    birthDate: Optional[str] = None
    ageYears: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None

class SummaryCondition(BaseModel):
    code: Optional[str] = None
    display: Optional[str] = None
    clinicalStatus: Optional[str] = None
    recordedDate: Optional[str] = None

class SummaryObservation(BaseModel):
    code: Optional[str] = None
    display: Optional[str] = None
    valueNumber: Optional[float] = None
    valueString: Optional[str] = None
    unit: Optional[str] = None
    effectiveDateTime: Optional[str] = None

class SummaryNote(BaseModel):
    created: Optional[str] = None
    text: Optional[str] = None
    sourceType: Optional[str] = None
    fileName: Optional[str] = None
    baseKey: Optional[str] = None

class PatientSummary(BaseModel):
    patientId: str
    demographics: SummaryDemographics
    conditions: List[SummaryCondition]
    observations: List[SummaryObservation]
    notes: List[SummaryNote]
    encounters: List[dict]  # empty for now

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

def _parse_date_safe(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date or date-range string to datetime. For ranges ('A to B') uses B (latest)."""
    if not date_str:
        return None
    s = date_str.strip()
    if " to " in s:
        s = s.split(" to ")[-1].strip()
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _abnormality_score(value: Optional[float], display: str) -> float:
    """Return 0.0 (normal) – 1.0 (critical) using REFERENCE_RANGES as single source of truth."""
    if value is None:
        return 0.1
    try:
        from .visualization_service import REFERENCE_RANGES
    except ImportError:
        return 0.2
    display_lower = (display or "").lower()
    ref = None
    for key, ranges in REFERENCE_RANGES.items():
        if key in display_lower:
            ref = ranges
            break
    if ref is None:
        return 0.2
    if ref.get("critical_high") and value > ref["critical_high"]:
        return 1.0
    if ref.get("critical_low") and value < ref["critical_low"]:
        return 1.0
    if ref.get("high") and value > ref["high"]:
        return 0.7
    if ref.get("low") and value < ref["low"]:
        return 0.7
    return 0.0


def _clinical_priority_score(obs: Dict[str, Any]) -> float:
    """Score 0–1 for observation importance: abnormal + recent + frequently measured = higher."""
    display = obs.get("display") or obs.get("code") or ""
    value = obs.get("valueNumber")
    date_str = obs.get("effectiveDateTime") or ""
    measurement_count = obs.get("measurement_count", 1) or 1

    abnormality = _abnormality_score(value, display)

    latest_date = _parse_date_safe(date_str)
    if latest_date:
        days_ago = max((datetime.now() - latest_date).days, 0)
        recency = math.exp(-days_ago / 90.0)
    else:
        recency = 0.5

    frequency = min(math.log1p(measurement_count) / 5.0, 1.0)

    return (abnormality * 0.50) + (recency * 0.30) + (frequency * 0.20)


def _compute_trend(obs_list: List[Dict[str, Any]]) -> str:
    """Statistical trend via scipy linregress (gate: p<0.05, R²≥0.5, n≥3).
    Falls back to 'stable' when data are insufficient or not significant.
    obs_list is newest-first; we reverse for chronological regression.
    """
    pairs = []
    for o in reversed(obs_list):
        val = o.get("valueNumber")
        dt = _parse_date_safe(o.get("effectiveDateTime"))
        if val is not None and dt is not None:
            pairs.append((dt, val))

    if len(pairs) < 3 or not _SCIPY_AVAILABLE:
        return "stable"

    t0 = pairs[0][0]
    x = [(p[0] - t0).days for p in pairs]
    y = [p[1] for p in pairs]

    try:
        slope, _, r_value, p_value, _ = _linregress(x, y)
    except Exception:
        return "stable"

    r_squared = r_value ** 2
    # Standard gate: p<0.05 AND R²≥0.5
    # Exception: n=3 has only 1 residual df — p<0.05 requires t>12.7, unreachable for most
    # real clinical series. With n=3, trust R²≥0.8 alone (nearly perfect linear fit).
    if r_squared < 0.5:
        return "stable"
    if p_value >= 0.05 and not (len(pairs) == 3 and r_squared >= 0.8):
        return "stable"
    return "increasing" if slope > 0 else "decreasing"


def _clean_demographics(demo: Dict[str, Any]) -> Dict[str, Any]:
    """Remove null/empty values from demographics to reduce token usage"""
    cleaned = {}
    for key, value in demo.items():
        # Keep the value if it's not None, not empty string, and not 'null' string
        if value is not None and value != '' and str(value).lower() != 'null':
            cleaned[key] = value
        else:
            # Use descriptive placeholders instead of null
            if key == 'birthDate':
                cleaned[key] = 'date not recorded'
            elif key == 'ageYears':
                cleaned[key] = 'value not recorded'
            elif key in ['gender', 'city', 'state', 'postalCode']:
                cleaned[key] = 'value not recorded'
            elif key == 'name':
                cleaned[key] = 'Not recorded'
            else:
                cleaned[key] = value  # Keep patientId always
    return cleaned

def _generate_observations_fallback(observations: List[Dict[str, Any]], demo: Dict[str, Any]) -> str:
    """Generate a structured fallback summary for observations when LLM fails"""
    if not observations:
        return f"**Clinical Observations Summary for {demo.get('name', 'Patient')}**\n\nNo clinical observations found in the system."
    
    # Import LOINC code mapper for handling NULL display names
    try:
        from .loinc_code_mapper import get_observation_display_from_code
    except ImportError:
        get_observation_display_from_code = None
    
    # Group observations by type for better organization
    vital_signs = []
    lab_results = []
    other_observations = []
    
    for obs in observations:
        display = obs.get('display', '')
        code = obs.get('code', '')
        
        # If display is NULL, use LOINC code mapper (fix for vital signs with NULL display)
        if not display and code and get_observation_display_from_code:
            display = get_observation_display_from_code(code) or ""
        
        display_lower = display.lower() if display else ""
        
        if any(keyword in display_lower for keyword in ['blood pressure', 'heart rate', 'temperature', 'respiratory', 'oxygen', 'pulse']):
            vital_signs.append(obs)
        elif any(keyword in display_lower for keyword in ['glucose', 'cholesterol', 'hemoglobin', 'protein', 'sodium', 'potassium', 'creatinine', 'bun', 'albumin', 'bilirubin', 'calcium', 'urea', 'carbon dioxide']):
            lab_results.append(obs)
        else:
            other_observations.append(obs)
    
    summary_parts = [f"**Clinical Observations Summary for {demo.get('name', 'Patient')}**\n"]
    
    if vital_signs:
        summary_parts.append("**Vital Signs:**")
        for obs in vital_signs[:8]:  # Increased limit
            value_str = ""
            if obs.get('valueNumber') is not None:
                value_str = f"{obs['valueNumber']}"
                if obs.get('unit'):
                    value_str += f" {obs['unit']}"
            elif obs.get('valueString'):
                value_str = obs['valueString']
            
            date_str = obs.get('effectiveDateTime', 'Unknown date')
            summary_parts.append(f"- {obs.get('display', 'Unknown')}: {value_str} ({date_str})")
        if len(vital_signs) > 8:
            summary_parts.append(f"  ... and {len(vital_signs) - 8} more vital signs")
        summary_parts.append("")
    
    if lab_results:
        summary_parts.append("**Laboratory Results:**")
        for obs in lab_results[:15]:  # Increased limit for lab results
            value_str = ""
            if obs.get('valueNumber') is not None:
                value_str = f"{obs['valueNumber']}"
                if obs.get('unit'):
                    value_str += f" {obs['unit']}"
            elif obs.get('valueString'):
                value_str = obs['valueString']
            
            date_str = obs.get('effectiveDateTime', 'Unknown date')
            summary_parts.append(f"- {obs.get('display', 'Unknown')}: {value_str} ({date_str})")
        if len(lab_results) > 15:
            summary_parts.append(f"  ... and {len(lab_results) - 15} more lab results")
        summary_parts.append("")
    
    if other_observations:
        summary_parts.append("**Other Observations:**")
        for obs in other_observations[:10]:  # Increased limit
            value_str = ""
            if obs.get('valueNumber') is not None:
                value_str = f"{obs['valueNumber']}"
                if obs.get('unit'):
                    value_str += f" {obs['unit']}"
            elif obs.get('valueString'):
                value_str = obs['valueString']
            
            date_str = obs.get('effectiveDateTime', 'Unknown date')
            summary_parts.append(f"- {obs.get('display', 'Unknown')}: {value_str} ({date_str})")
        if len(other_observations) > 10:
            summary_parts.append(f"  ... and {len(other_observations) - 10} more observations")
    
    summary_parts.append(f"\n*Total observations processed: {len(observations)}*")
    
    return "\n".join(summary_parts)

def _generate_observations_summary_with_counts(observations: List[Dict[str, Any]], demo: Dict[str, Any]) -> str:
    """Generate a comprehensive observations summary with counts and abnormal value detection"""
    if not observations:
        return f"**Clinical Observations Summary for {demo.get('name', 'Patient')}**\n\nNo clinical observations found in the system."
    
    # Analyze observations for abnormal values and trends
    vital_signs = []
    lab_results = []
    other_observations = []
    abnormal_values = []
    
    # Import LOINC code mapper for handling NULL display names
    try:
        from .loinc_code_mapper import get_observation_display_from_code
    except ImportError:
        get_observation_display_from_code = None
    
    for obs in observations:
        display = obs.get('display', '')
        code = obs.get('code', '')
        
        # If display is NULL, use LOINC code mapper (fix for vital signs with NULL display)
        if not display and code and get_observation_display_from_code:
            display = get_observation_display_from_code(code) or ""
        
        display_lower = display.lower() if display else ""
        value_num = obs.get('valueNumber')
        
        # Detect abnormal values based on common clinical ranges
        is_abnormal = False
        if value_num is not None:
            if 'glucose' in display_lower and value_num > 140:
                is_abnormal = True
            elif 'systolic' in display_lower and 'pressure' in display_lower and value_num > 130:
                is_abnormal = True
            elif 'diastolic' in display_lower and 'pressure' in display_lower and value_num > 80:
                is_abnormal = True
            elif 'creatinine' in display_lower and value_num > 1.2:
                is_abnormal = True
            elif 'heart rate' in display_lower and (value_num < 60 or value_num > 100):
                is_abnormal = True
        
        obs_with_status = {**obs, 'is_abnormal': is_abnormal}
        
        if is_abnormal:
            abnormal_values.append(obs_with_status)
        
        # Use display_lower (already processed with LOINC mapper if needed)
        if any(keyword in display_lower for keyword in ['blood pressure', 'heart rate', 'temperature', 'respiratory', 'oxygen', 'pulse']):
            vital_signs.append(obs_with_status)
        elif any(keyword in display_lower for keyword in ['glucose', 'cholesterol', 'hemoglobin', 'protein', 'sodium', 'potassium', 'creatinine', 'bun', 'albumin', 'bilirubin', 'calcium', 'urea', 'carbon dioxide']):
            lab_results.append(obs_with_status)
        else:
            other_observations.append(obs_with_status)
    
    summary_parts = [f"**Clinical Observations Summary for {demo.get('name', 'Patient')}**\n"]
    
    # Add summary statistics
    summary_parts.append(f"📊 **Summary Statistics:**")
    summary_parts.append(f"• Total Observations: {len(observations)}")
    summary_parts.append(f"• Vital Signs: {len(vital_signs)}")
    summary_parts.append(f"• Laboratory Results: {len(lab_results)}")
    summary_parts.append(f"• Other Observations: {len(other_observations)}")
    summary_parts.append(f"• Abnormal Values: {len(abnormal_values)}")
    summary_parts.append("")
    
    # Highlight abnormal values first
    if abnormal_values:
        summary_parts.append("🚨 **Abnormal Values Detected:**")
        for obs in abnormal_values[:10]:  # Show top 10 abnormal values
            value_str = ""
            if obs.get('valueNumber') is not None:
                value_str = f"{obs['valueNumber']}"
                if obs.get('unit'):
                    value_str += f" {obs['unit']}"
            elif obs.get('valueString'):
                value_str = obs['valueString']
            
            date_str = obs.get('effectiveDateTime', 'Unknown date')
            summary_parts.append(f"• {obs.get('display', 'Unknown')}: {value_str} ({date_str})")
        if len(abnormal_values) > 10:
            summary_parts.append(f"  ... and {len(abnormal_values) - 10} more abnormal values")
        summary_parts.append("")
    
    # Show key vital signs
    if vital_signs:
        summary_parts.append("💓 **Key Vital Signs:**")
        key_vitals = ['heart rate', 'blood pressure', 'temperature', 'respiratory']
        for keyword in key_vitals:
            matching_vitals = [v for v in vital_signs if keyword in v.get('display', '').lower()]
            if matching_vitals:
                latest = matching_vitals[0]  # Most recent
                value_str = ""
                if latest.get('valueNumber') is not None:
                    value_str = f"{latest['valueNumber']}"
                    if latest.get('unit'):
                        value_str += f" {latest['unit']}"
                elif latest.get('valueString'):
                    value_str = latest['valueString']
                
                status = "🚨" if latest.get('is_abnormal') else "✅"
                summary_parts.append(f"• {latest.get('display', 'Unknown')}: {value_str} {status}")
        summary_parts.append("")
    
    # Show key lab results
    if lab_results:
        summary_parts.append("🧪 **Key Laboratory Results:**")
        key_labs = ['glucose', 'creatinine', 'hemoglobin', 'protein', 'albumin']
        for keyword in key_labs:
            matching_labs = [l for l in lab_results if keyword in l.get('display', '').lower()]
            if matching_labs:
                latest = matching_labs[0]  # Most recent
                value_str = ""
                if latest.get('valueNumber') is not None:
                    value_str = f"{latest['valueNumber']}"
                    if latest.get('unit'):
                        value_str += f" {latest['unit']}"
                elif latest.get('valueString'):
                    value_str = latest['valueString']
                
                status = "🚨" if latest.get('is_abnormal') else "✅"
                summary_parts.append(f"• {latest.get('display', 'Unknown')}: {value_str} {status}")
        summary_parts.append("")
    
    # Add note about full data access
    summary_parts.append("💡 **Note:** This is a summary view. For complete data analysis and visualizations, use the chat interface.")
    summary_parts.append(f"📈 **Ready for Visualization:** {len(observations)} data points available for trend analysis and charts.")
    
    return "\n".join(summary_parts)

def _get_patient_data(patient_id: str, category: str = "default"):
    """Fetch all patient data from database with adaptive limits based on category"""
    
    # All categories use the same DB limits so every section sees the same data.
    # care_plans uses slightly reduced context to keep the prompt manageable.
    if category == "care_plans":
        max_conditions = 40
        max_observations = 60
        max_notes = 2
        max_note_chars = MAX_NOTE_CHARS
    else:
        max_conditions = MAX_CONDITIONS
        max_observations = MAX_OBSERVATIONS
        max_notes = MAX_NOTES
        max_note_chars = MAX_NOTE_CHARS
    
    with engine.connect() as conn:
        # Demographics
        sql_p = """
        SELECT enterprise_patient_id AS patient_id,
               COALESCE(CONCAT_WS(' ', NULLIF(TRIM(given_name),''), NULLIF(TRIM(family_name),'')), 'Not recorded') AS name,
               birth_date, gender, city, state, postal_code,
               visited_hospitals, data_sources
        FROM patients
        WHERE enterprise_patient_id = :pid
        LIMIT 1
        """
        p = conn.execute(text(sql_p), {"pid": patient_id}).mappings().first()
        if not p:
            raise HTTPException(status_code=404, detail="patient not found")
    # demographics query ends here — close MySQL connection before ES calls

    # ── Conditions: ES first (LOINC-resolved metadata), MySQL fallback ───────
    from .elasticsearch_client import es_client
    from .loinc_code_mapper import get_observation_display_from_code

    conditions: List[Dict[str, Any]] = []
    es_conds = es_client.get_all_patient_data_by_type(patient_id, "conditions", size=100)
    if es_conds:
        seen = set()
        for doc in es_conds:
            # ES condition docs use top-level fields (icd_code, content — no metadata wrapper)
            code = doc.get("icd_code") or doc.get("code") or ""
            display = doc.get("display") or doc.get("content") or ""
            key = f"{code}|{display}"
            if key in seen:
                continue
            seen.add(key)
            clinical_status = doc.get("clinical_status") or ""
            recorded = doc.get("onset_datetime") or doc.get("recorded_date") or doc.get("effective_date") or ""
            categorized = categorize_condition(code=code, display=display, clinical_status=clinical_status)
            conditions.append({
                "code": code, "display": display,
                "clinicalStatus": clinical_status,
                "recordedDate": str(recorded)[:10] if recorded else None,
                "category": categorized["category"],
                "priority": categorized["priority"],
                "normalizedName": categorized["name"],
            })
            if len(conditions) >= max_conditions:
                break
    else:
        # MySQL fallback — enterprise schema uses enterprise_patient_id
        with engine.connect() as conn:
            sql_c = """
            SELECT c.icd_code AS code, c.display, c.clinical_status,
                   COALESCE(c.onset_datetime, c.recorded_date) AS recordedDate
            FROM conditions c
            WHERE c.enterprise_patient_id = :pid
            ORDER BY COALESCE(c.onset_datetime, c.recorded_date, '1000-01-01') DESC, c.db_id DESC
            """
            rows_c = conn.execute(text(sql_c), {"pid": patient_id}).mappings().all()
        seen = set()
        for r in rows_c:
            key = f"{r['code']}|{r['display']}"
            if key in seen:
                continue
            seen.add(key)
            categorized = categorize_condition(
                code=r["code"], display=r["display"], clinical_status=r["clinical_status"]
            )
            conditions.append({
                "code": r["code"], "display": r["display"],
                "clinicalStatus": r["clinical_status"],
                "recordedDate": _iso(r["recordedDate"]),
                "category": categorized["category"],
                "priority": categorized["priority"],
                "normalizedName": categorized["name"],
            })
            if len(conditions) >= max_conditions:
                break

    # ── Observations: ES first (LOINC-resolved — no NULL-display collapse) ───
    # Chat uses ES-resolved data; summaries must use the same source for consistency.
    obs_groups: Dict[str, List[Dict[str, Any]]] = {}
    es_obs = es_client.get_all_patient_data_by_type(patient_id, "observations", size=300)
    if es_obs:
        for doc in es_obs:
            # ES observation docs use top-level fields (no metadata wrapper)
            display = doc.get("display") or None
            code = doc.get("code") or ""
            if not display and code:
                display = get_observation_display_from_code(code)
            display_key = (display or code or "Unknown").strip()

            raw_val = doc.get("value_numeric")
            value_number = None
            value_string = None
            if raw_val is not None:
                try:
                    value_number = float(raw_val)
                except (ValueError, TypeError):
                    value_string = str(raw_val)
            if value_number is None:
                value_string = doc.get("value_string") or value_string

            eff = doc.get("effective_datetime") or doc.get("effective_date")
            eff_str = str(eff)[:10] if eff else None  # keep as "YYYY-MM-DD"

            if display_key not in obs_groups:
                obs_groups[display_key] = []
            obs_groups[display_key].append({
                "code": code,
                "display": display or display_key,
                "valueNumber": value_number,
                "valueString": value_string,
                "unit": doc.get("unit"),
                "effectiveDateTime": eff_str,
            })
    else:
        # MySQL fallback — enterprise schema uses enterprise_patient_id
        with engine.connect() as conn:
            sql_o = """
            SELECT o.code, o.display, o.value_numeric AS valueNumber, o.value_string AS valueString,
                   o.unit,
                   COALESCE(o.effective_datetime, o.effective_date) AS effectiveDateTime,
                   o.value_numeric AS raw_num
            FROM observations o
            WHERE o.enterprise_patient_id = :pid
              AND (o.value_numeric IS NOT NULL OR o.value_string IS NOT NULL)
            ORDER BY COALESCE(o.effective_datetime, o.effective_date, '1000-01-01') DESC, o.db_id DESC
            LIMIT :limit
            """
            rows_o = conn.execute(text(sql_o), {"pid": patient_id, "limit": max_observations}).mappings().all()
        for r in rows_o:
            eff = r["effectiveDateTime"]
            if not eff and (r["code"] or "") == "67723-7":
                eff = _parse_numeric_date(r["raw_num"])
            value_number = r["valueNumber"]
            if value_number is not None:
                try:
                    value_number = float(value_number)
                except (ValueError, TypeError):
                    value_number = None
            display = r["display"]
            if not display and r["code"]:
                display = get_observation_display_from_code(r["code"])
            display_key = (display or r["code"] or "Unknown").strip()
            if display_key not in obs_groups:
                obs_groups[display_key] = []
            obs_groups[display_key].append({
                "code": r["code"],
                "display": display or display_key,
                "valueNumber": value_number,
                "valueString": r["valueString"],
                "unit": r["unit"],
                "effectiveDateTime": _iso(eff),
            })

    # Build aggregated observations list (trend analysis — same logic regardless of source)
    observations: List[Dict[str, Any]] = []
    for display_key, obs_list in obs_groups.items():
        if len(obs_list) == 1:
            observations.append(obs_list[0])
        else:
            numeric_values = [o["valueNumber"] for o in obs_list if o["valueNumber"] is not None]
            if len(numeric_values) >= 2:
                avg_value = sum(numeric_values) / len(numeric_values)
                min_value = min(numeric_values)
                max_value = max(numeric_values)
                latest_value = numeric_values[0]
                oldest_value = numeric_values[-1]
                trend = _compute_trend(obs_list)  # P5: scipy linregress, p<0.05, R²≥0.5, n≥3
                dates = [o["effectiveDateTime"] for o in obs_list if o["effectiveDateTime"]]
                date_range = f"{dates[-1]} to {dates[0]}" if len(dates) >= 2 else (dates[0] if dates else "unknown")
                measurement_count = len(numeric_values)
                if measurement_count == 2:
                    trend_desc = f"Trend: {trend} ({oldest_value:.2f} → {latest_value:.2f})"
                else:
                    trend_desc = f"Trend: {trend} over {measurement_count} measurements (Avg: {avg_value:.2f}, Range: {min_value:.2f}-{max_value:.2f})"
                observations.append({
                    "code": obs_list[0]["code"],
                    "display": obs_list[0]["display"],
                    "valueNumber": latest_value,
                    "valueString": trend_desc,
                    "unit": obs_list[0]["unit"],
                    "effectiveDateTime": date_range,
                    "measurement_count": measurement_count,
                })
            else:
                observations.append(obs_list[0])

    # Deduplicate by resolved display name
    seen_displays: set = set()
    deduplicated_observations = []
    for obs in observations:
        display_normalized = (obs.get("display") or "Unknown").strip().lower()
        if display_normalized not in seen_displays:
            seen_displays.add(display_normalized)
            deduplicated_observations.append(obs)
    observations = deduplicated_observations

    # P3: Sort by clinical priority — abnormal, recent, frequently-measured first.
    # This same sorted list is used for both the full LLM call and the OOM-fallback
    # slice (observations[:30]), ensuring both paths see the most important data.
    observations.sort(key=lambda o: -_clinical_priority_score(o))

    # ── Notes: ES first, MySQL fallback ──────────────────────────────────────
    es_notes = es_client.get_all_patient_data_by_type(patient_id, "notes", size=max_notes + 2)
    if es_notes:
        notes = []
        for doc in es_notes[:max_notes]:
            # ES note docs use top-level fields (note_date, content, source_hospital)
            text_val = doc.get("content", "")
            notes.append({
                "created": doc.get("note_date") or doc.get("effective_date"),
                "text": text_val[:max_note_chars] if text_val else None,
                "sourceType": doc.get("source_hospital") or doc.get("source_type"),
                "fileName": doc.get("note_filename") or doc.get("ccda_filename"),
                "baseKey": None,
            })
    else:
        # MySQL fallback — enterprise schema uses enterprise_patient_id
        with engine.connect() as conn:
            sql_n = """
            SELECT n.note_date AS created, n.content AS text,
                   n.source_hospital AS sourceType,
                   n.note_filename AS fileName
            FROM notes n
            WHERE n.enterprise_patient_id = :pid
            ORDER BY n.note_date DESC, n.db_id DESC
            LIMIT :limit
            """
            rows_n = conn.execute(text(sql_n), {"pid": patient_id, "limit": max_notes}).mappings().all()
        notes = [{
            "created": _iso(r["created"]),
            "text": r["text"][:max_note_chars] if r["text"] else None,
            "sourceType": r["sourceType"],
            "fileName": r["fileName"],
            "baseKey": None,
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
    
    # Clean demographics to remove nulls
    demo = _clean_demographics(demo)

    context_counts = {
        "conditions": len(conditions),
        "observations": len(observations),
        "notes": len(notes),
    }

    return demo, conditions, observations, notes, context_counts

# ---- routes ----
@router.get("/{patient_id}/all_summaries", response_model=AllSummariesResponse)
def generate_all_summaries(patient_id: str):
    """
    Generate all summaries for a patient at once and cache them.
    This endpoint generates: patient_summary, conditions, observations, demographics, notes
    
    Automatically detects patient switches and clears previous patient's session.
    """
    global _current_patient_id
    
    print(f"🔍 API Call - Generate All Summaries")
    print(f"🔍 Patient ID: {patient_id}")
    
    # Detect patient switch and clear previous patient's session
    if _current_patient_id and _current_patient_id != patient_id:
        print(f"🔄 Patient switch detected: {_current_patient_id} → {patient_id}")
        clear_patient_session(_current_patient_id)
    
    _current_patient_id = patient_id
    
    # Check cache first
    cache_key = f"{patient_id}_all"
    if cache_key in summary_cache:
        print(f"✅ Found in cache - returning cached summaries")
        cached_data = summary_cache[cache_key]
        return AllSummariesResponse(
            patientId=patient_id,
            model=cached_data["model"],
            summaries=cached_data["summaries"],
            contextCounts=cached_data["contextCounts"],
            generatedAt=cached_data["generatedAt"]
        )

    # Generate all summaries with error handling
    # Summaries are generated sequentially with GPU cache cleared between each
    # to prevent KV-cache from previous generation bleeding into next (OOM fix)
    print(f"🔍 Cache miss - generating all summaries...")
    categories = ["patient_summary", "conditions", "observations", "demographics", "notes", "care_plans"]
    summaries = {}
    context_counts = {}  # initialised here so it's defined even if all _get_patient_data calls fail

    for category in categories:
        try:
            print(f"Generating {category} summary for patient {patient_id}...")

            # Clear GPU KV-cache from previous generation before each new summary
            # This is the key fix for OOM on shared-GPU environments:
            # model weights stay loaded, but KV-cache (~1-3 GB) is released
            try:
                from app.core.llm import clear_gpu_memory_aggressive
                clear_gpu_memory_aggressive()
                time.sleep(2)  # Let CUDA fully release the cache before next generation
            except Exception as gpu_clear_err:
                logger.warning(f"GPU clear before {category} failed: {gpu_clear_err}")
            
            # Fetch data with category-specific limits (adaptive)
            demo, conditions, observations, notes, context_counts = _get_patient_data(patient_id, category)

            # MedRAG KG enrichment for patient_summary and observations
            kg_context = ""
            if category in ("patient_summary", "observations") and observations:
                try:
                    from .rag_service import USE_MEDRAG
                    from .medrag_knowledge_graph import kg_service
                    if USE_MEDRAG:
                        kg_retrieved = [
                            {
                                "content": f"{o.get('display', '')} {o.get('valueNumber', '')} {o.get('unit', '')}".strip(),
                                "metadata": o,
                            }
                            for o in observations[:50]
                        ]
                        kg_result = kg_service.run_kg_pipeline("patient summary", kg_retrieved)
                        kg_candidates = kg_result.get("candidate_diseases", [])
                        if kg_candidates:
                            matched = kg_result.get("matched_evidence", {})
                            kg_context = kg_service.build_kg_summary(kg_candidates, matched)
                except Exception as kg_err:
                    logger.warning("MedRAG KG injection failed for %s: %s", category, kg_err)

            if category == "demographics":
                # Pass conditions and obs count so demographics section shows clinical context
                try:
                    prompts = render_prompt(
                        category,
                        demo=demo,
                        conditions=conditions,
                        obs_count=len(observations),
                    )
                    summary_text = generate_chat(prompts["system"], prompts["user"], category=category).strip()
                    summaries[category] = summary_text
                    print(f"✓ {category} completed")
                except Exception as llm_error:
                    print(f"✗ {category} failed: {str(llm_error)[:100]}")
                    summaries[category] = f"Demographics summary is temporarily unavailable due to system constraints. Please refresh the page."
            
            elif category == "care_plans":
                # Care plans require all data types, so always use LLM (with reduced limits)
                try:
                    prompts = render_prompt(
                        category,
                        demo=demo,
                        conditions=conditions,
                        observations=observations,
                        notes=notes,
                    )
                    summary_text = generate_chat(prompts["system"], prompts["user"], category=category).strip()
                    summaries[category] = summary_text
                    print(f"✓ {category} completed")
                except Exception as care_plans_error:
                    print(f"✗ {category} failed: {str(care_plans_error)[:100]}")
                    summaries[category] = f"Care plan suggestions are temporarily unavailable due to system constraints. Please refresh the page."
            
            elif category == "observations":
                # Special handling for observations to prevent OOM
                try:
                    # Clear GPU memory before generating observations (often has most data)
                    from app.core.llm import clear_gpu_memory
                    clear_gpu_memory()
                    
                    # For observations, use ALL data but with a different prompt approach
                    # Create a summary-focused prompt instead of listing all observations
                    prompts = render_prompt(
                        category,
                        demo=demo,
                        conditions=conditions,
                        observations=observations,  # Use ALL observations
                        notes=notes,
                        kg_context=kg_context,
                    )
                    summary_text = generate_chat(prompts["system"], prompts["user"], category=category).strip()
                    # generate_chat returns error strings on OOM (no exception raised)
                    if "temporarily unavailable" in summary_text.lower():
                        raise RuntimeError("OOM detected via return value")
                    summaries[category] = summary_text
                    print(f"✓ {category} completed (full analysis)")

                    # Clear memory after generation
                    clear_gpu_memory()
                except Exception as llm_error:
                    error_type = type(llm_error).__name__
                    is_oom = (
                        "OOM detected" in str(llm_error)
                        or (torch is not None and
                            hasattr(torch.cuda, 'OutOfMemoryError') and
                            isinstance(llm_error, torch.cuda.OutOfMemoryError))
                    )

                    print(f"✗ {category} failed ({error_type}), retrying with reduced observations...")

                    # Clear memory on any error
                    try:
                        from app.core.llm import clear_gpu_memory_aggressive
                        clear_gpu_memory_aggressive()
                        time.sleep(3)
                    except:
                        pass

                    # Retry with reduced data (always, not just on OOM — error string also triggers this)
                    if True:
                        try:
                            # Retry with fewer observations
                            reduced_observations = observations[:30] if len(observations) > 30 else observations
                            prompts = render_prompt(
                                category,
                                demo=demo,
                                conditions=conditions,
                                observations=reduced_observations,
                                notes=notes,
                                kg_context=kg_context,
                            )
                            summary_text = generate_chat(prompts["system"], prompts["user"], category=category).strip()
                            summaries[category] = summary_text
                            print(f"✓ {category} completed (with reduced observations)")
                            # Clear memory after retry
                            try:
                                clear_gpu_memory()
                            except:
                                pass
                        except Exception as retry_error:
                            print(f"✗ {category} retry failed: {str(retry_error)[:100]}")
                            summaries[category] = f"Summary temporarily unavailable due to system memory constraints. Please refresh the page."
            
            elif category in ["conditions", "notes", "patient_summary"]:
                # Use LLM for other categories with error handling and retry logic
                max_retries = 2
                retry_count = 0
                summary_generated = False
                
                while retry_count <= max_retries and not summary_generated:
                    try:
                        # Clear GPU memory before generation (more aggressive)
                        from app.core.llm import clear_gpu_memory, clear_gpu_memory_aggressive
                        if retry_count > 0:
                            clear_gpu_memory_aggressive()
                            time.sleep(3)  # Wait longer on retry
                        else:
                            clear_gpu_memory()
                            time.sleep(1)
                        
                        # Reduce context on retry
                        if retry_count > 0:
                            # Reduce observations and notes on retry
                            observations_limited = observations[:min(50, len(observations))]
                            notes_limited = notes[:min(2, len(notes))]
                        else:
                            observations_limited = observations
                            notes_limited = notes
                        
                        prompts = render_prompt(
                            category,
                            demo=demo,
                            conditions=conditions,
                            observations=observations_limited,
                            notes=notes_limited,
                            kg_context=kg_context,
                        )
                        summary_text = generate_chat(prompts["system"], prompts["user"], category=category).strip()
                        
                        # Check if we got an error message
                        if "temporarily unavailable" not in summary_text.lower():
                            summaries[category] = summary_text
                            summary_generated = True
                            print(f"✓ {category} completed")
                        else:
                            # Got error message, retry
                            retry_count += 1
                            if retry_count <= max_retries:
                                print(f"⚠️  {category} got error message, retrying ({retry_count}/{max_retries})...")
                                continue
                            else:
                                summaries[category] = summary_text  # Use the error message as last resort
                                summary_generated = True
                        
                        # Clear memory after successful generation
                        if summary_generated:
                            clear_gpu_memory()
                    except Exception as llm_error:
                        retry_count += 1
                        print(f"✗ {category} failed (attempt {retry_count}/{max_retries + 1}): {type(llm_error).__name__}: {str(llm_error)[:100]}")
                        # Clear memory on error
                        try:
                            from app.core.llm import clear_gpu_memory_aggressive
                            clear_gpu_memory_aggressive()
                        except:
                            pass
                        
                        if retry_count > max_retries:
                            summaries[category] = f"Summary temporarily unavailable due to system constraints. Please refresh the page."
                            summary_generated = True
        except Exception as e:
            print(f"✗ {category} exception: {str(e)[:100]}")
            # If anything else fails, provide a basic fallback
            summaries[category] = f"Summary temporarily unavailable. Please refresh the page."

    # Cache the results
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    summary_cache[cache_key] = {
        "model": model_name(),
        "summaries": summaries,
        "contextCounts": context_counts,
        "generatedAt": current_time
    }
    
    # Limit cache size to prevent unbounded growth
    limit_cache_size()
    
    print(f"✅ All summaries generated and cached")
    print(f"🔍 Summary categories: {list(summaries.keys())}")
    print(f"✅ Response sent to client\n")

    return AllSummariesResponse(
        patientId=patient_id,
        model=model_name(),
        summaries=summaries,
        contextCounts=context_counts,
        generatedAt=current_time
    )

@router.get("/{patient_id}/llm_summary", response_model=LlmSummaryResponse)
def get_patient_llm_summary(patient_id: str, category: str = "patient_summary"):
    """
    Get a specific category summary for the selected patient.
    First checks cache, then generates if not available.
    """
    print(f"🔍 API Call - Get LLM Summary")
    print(f"🔍 Patient ID: {patient_id}")
    print(f"🔍 Category: {category}")
    
    # Check if we have all summaries cached
    cache_key = f"{patient_id}_all"
    if cache_key in summary_cache:
        print(f"✅ Found in cache - returning cached {category} summary")
        cached_data = summary_cache[cache_key]
        if category in cached_data["summaries"]:
            return LlmSummaryResponse(
                patientId=patient_id,
                model=cached_data["model"],
                summary=cached_data["summaries"][category],
                contextCounts=cached_data["contextCounts"]
            )

    # If not cached, fetch patient data and generate (with category-specific limits)
    print(f"🔍 Cache miss - generating {category} summary...")

    # Clear GPU KV-cache before generation (same as all_summaries does between sections)
    try:
        from app.core.llm import clear_gpu_memory_aggressive
        clear_gpu_memory_aggressive()
        time.sleep(1)
    except Exception:
        pass

    demo, conditions, observations, notes, context_counts = _get_patient_data(patient_id, category)
    print(f"🔍 Data retrieved - Conditions: {len(conditions)}, Observations: {len(observations)}, Notes: {len(notes)}")

    # Use LLM for all categories including demographics
    prompts = render_prompt(
        category,
        demo=demo,
        conditions=conditions,
        observations=observations,
        notes=notes,
    )
    print(f"🔍 Generating LLM summary for {category}...")
    summary_text = generate_chat(prompts["system"], prompts["user"], category=category).strip()
    print(f"✅ Summary generated ({len(summary_text)} characters)")
    print(f"✅ Response sent to client\n")

    return LlmSummaryResponse(
        patientId=patient_id,
        model=model_name(),
        summary=summary_text,
        contextCounts=context_counts,
    )

@router.get("/{patient_id}/summary", response_model=PatientSummary)
def get_patient_summary(patient_id: str):
    """
    Legacy endpoint - returns raw patient data without LLM processing
    """
    with engine.connect() as conn:
        # Demographics
        sql_p = """
        SELECT enterprise_patient_id AS patient_id,
               COALESCE(CONCAT_WS(' ', NULLIF(TRIM(given_name),''), NULLIF(TRIM(family_name),'')), 'Not recorded') AS name,
               birth_date, gender, city, state, postal_code,
               visited_hospitals, data_sources
        FROM patients
        WHERE enterprise_patient_id = :pid
        LIMIT 1
        """
        p = conn.execute(text(sql_p), {"pid": patient_id}).mappings().first()
        if not p:
            raise HTTPException(status_code=404, detail="patient not found")

        bdate = p["birth_date"]
        demographics = SummaryDemographics(
            patientId=p["patient_id"],
            name=p["name"],
            birthDate=_iso(bdate),
            ageYears=_age_years(bdate),
            gender=p["gender"] or None,
            city=p["city"] or None,
            state=p["state"] or None,
            postalCode=p["postal_code"] or None,
        )

        # Conditions (dedupe, newest first) — llm_ua_ai uses icd_code, onset_datetime, db_id
        sql_c = """
        SELECT c.icd_code AS code, c.display, c.clinical_status,
               COALESCE(c.onset_datetime, c.recorded_date) AS recordedDate
        FROM conditions c
        WHERE c.patient_id = :pid
        ORDER BY COALESCE(c.onset_datetime, c.recorded_date, '1000-01-01') DESC, c.db_id DESC
        """
        rows_c = conn.execute(text(sql_c), {"pid": patient_id}).mappings().all()
        seen = set()
        conditions: List[SummaryCondition] = []
        for r in rows_c:
            key = f"{r['code']}|{r['display']}"
            if key in seen:
                continue
            seen.add(key)
            conditions.append(SummaryCondition(
                code=r["code"], display=r["display"],
                clinicalStatus=r["clinical_status"],
                recordedDate=_iso(r["recordedDate"])
            ))
            if len(conditions) >= 30:
                break

        # Observations — llm_ua_ai uses effective_datetime/effective_date, db_id
        sql_o = """
        SELECT o.code, o.display, o.value_numeric, o.value_string, o.unit,
               COALESCE(o.effective_datetime, o.effective_date) AS effectiveDateTime,
               o.value_numeric AS raw_num
        FROM observations o
        WHERE o.patient_id = :pid
        ORDER BY COALESCE(o.effective_datetime, o.effective_date, '1000-01-01') DESC, o.db_id DESC
        """
        rows_o = conn.execute(text(sql_o), {"pid": patient_id}).mappings().all()
        latest_by_code: Dict[str, SummaryObservation] = {}
        for r in rows_o:
            code = r["code"] or ""
            if code in latest_by_code:
                continue
            eff = r["effectiveDateTime"]
            if not eff:
                if (r["code"] or "").startswith("67723-7") or (r["display"] or "").lower().startswith("date of health"):
                    eff = _parse_numeric_date(r["raw_num"])
            latest_by_code[code] = SummaryObservation(
                code=r["code"], display=r["display"],
                valueNumber=r["value_numeric"],
                valueString=r["value_string"],
                unit=r["unit"],
                effectiveDateTime=_iso(eff)
            )
            if len(latest_by_code) >= 50:
                break
        observations = list(latest_by_code.values())

        # Notes: most recent 10
        sql_n = """
        SELECT COALESCE(n.note_datetime, n.created_at) AS created,
               n.note_text AS text, n.source_type AS sourceType,
               n.filename_txt AS fileName, n.base_key AS baseKey
        FROM notes n
        WHERE n.patient_id = :pid
        ORDER BY COALESCE(n.note_datetime, n.created_at) DESC, n.id DESC
        LIMIT 10
        """
        rows_n = conn.execute(text(sql_n), {"pid": patient_id}).mappings().all()
        notes = [SummaryNote(
            created=_iso(r["created"]),
            text=r["text"],
            sourceType=r["sourceType"],
            fileName=r["fileName"],
            baseKey=r["baseKey"],
        ) for r in rows_n]

    return PatientSummary(
        patientId=patient_id,
        demographics=demographics,
        conditions=conditions,
        observations=observations,
        notes=notes,
        encounters=[],  # intentionally empty for now
    )

def clear_patient_cache(patient_id: str):
    """
    Clear cached summaries for a specific patient.
    """
    cache_key = f"{patient_id}_all"
    if cache_key in summary_cache:
        del summary_cache[cache_key]
        logger.info(f"✅ Cache cleared for patient {patient_id}")
        return {"message": f"Cache cleared for patient {patient_id}"}
    return {"message": f"No cache found for patient {patient_id}"}

def limit_cache_size(max_patients: int = MAX_CACHE_SIZE):
    """
    Limit cache size by removing oldest entries.
    Keeps only the most recent N patients to prevent unbounded memory growth.
    """
    if len(summary_cache) <= max_patients:
        return
    
    # Sort by generation time (oldest first)
    cache_items = []
    for key, value in summary_cache.items():
        generated_at = value.get("generatedAt", "")
        cache_items.append((key, generated_at))
    
    # Sort by time (oldest first)
    cache_items.sort(key=lambda x: x[1])
    
    # Remove oldest entries
    num_to_remove = len(summary_cache) - max_patients
    for i in range(num_to_remove):
        key, _ = cache_items[i]
        del summary_cache[key]
        logger.info(f"🗑️  Removed oldest cache entry: {key}")

def clear_patient_session(patient_id: str):
    """
    Clear all patient-specific data including cache.
    This should be called when switching patients to ensure clean state.
    GPU memory is automatically managed by generate_chat() cleanup.
    """
    # Clear cache
    clear_patient_cache(patient_id)
    
    # Limit cache size
    limit_cache_size()
    
    logger.info(f"🔧 Patient session cleared for patient {patient_id}")
    print(f"🔧 Patient session cleared for patient {patient_id}")

@router.delete("/{patient_id}/cache")
def clear_patient_cache_endpoint(patient_id: str):
    """
    API endpoint to clear cached summaries for a specific patient.
    """
    return clear_patient_cache(patient_id)

@router.post("/{patient_id}/clear-session")
def clear_patient_session_endpoint(patient_id: str):
    """
    API endpoint to clear patient session (cache + GPU memory).
    This is called automatically on patient switch, but can also be called manually.
    """
    clear_patient_session(patient_id)
    return {"message": f"Session cleared for patient {patient_id}"}