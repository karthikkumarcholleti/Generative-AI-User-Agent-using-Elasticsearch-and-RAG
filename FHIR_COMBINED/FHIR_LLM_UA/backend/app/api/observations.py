# backend/app/api/observations.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from ..core.database import engine
from .loinc_code_mapper import get_observation_display_from_code
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["observations"])

class Observation(BaseModel):
    patientId: str
    code: Optional[str] = None
    display: Optional[str] = None
    valueNumber: Optional[float] = None
    valueString: Optional[str] = None
    unit: Optional[str] = None
    effectiveDateTime: Optional[str] = None

class ObservationList(BaseModel):
    total: int
    items: List[Observation]

@router.get("/{patient_id}/observations", response_model=ObservationList)
def list_observations(
    patient_id: str,
    q: str = Query("", description="Optional search token (code/display/unit)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    print(f"🔍 API Call - List Observations")
    print(f"🔍 Patient ID: {patient_id}")
    print(f"🔍 Search query: '{q}'")
    print(f"🔍 Limit: {limit}, Offset: {offset}")
    
    has_q = 1 if q else 0
    like_q = f"%{q}%" if q else None

    sql = """
    SELECT
      o.patient_id     AS patientId,
      o.code           AS code,
      o.display        AS display,
      o.value_numeric  AS valueNumber,
      o.value_string   AS valueString,
      o.unit           AS unit,
      COALESCE(
        CASE
          WHEN o.code = '67723-7'
           AND o.value_numeric IS NOT NULL
           AND FLOOR(o.value_numeric) BETWEEN 10000101 AND 99991231
          THEN STR_TO_DATE(CAST(FLOOR(o.value_numeric) AS CHAR), '%Y%m%d')
          ELSE NULL
        END,
        o.effectiveDateTime
      ) AS effDate
    FROM observations o
    WHERE o.patient_id = :pid
      AND (:has_q = 0 OR (
            o.code LIKE :like_q OR
            o.display LIKE :like_q OR
            o.unit LIKE :like_q
      ))
    ORDER BY COALESCE(
               CASE
                 WHEN o.code = '67723-7'
                  AND o.value_numeric IS NOT NULL
                  AND FLOOR(o.value_numeric) BETWEEN 10000101 AND 99991231
                 THEN STR_TO_DATE(CAST(FLOOR(o.value_numeric) AS CHAR), '%Y%m%d')
                 ELSE NULL
               END,
               o.effectiveDateTime,
               '1000-01-01'
             ) DESC
    LIMIT :limit OFFSET :offset
    """

    sql_count = """
      SELECT COUNT(*) AS n
      FROM observations o
      WHERE o.patient_id = :pid
        AND (:has_q = 0 OR (
              o.code LIKE :like_q OR
              o.display LIKE :like_q OR
              o.unit LIKE :like_q
        ))
    """

    params = {"pid": patient_id, "has_q": has_q, "like_q": like_q, "limit": limit, "offset": offset}

    def _iso(v):
        try:
            return v.isoformat() if v else None
        except Exception:
            return str(v) if v else None

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        cnt  = conn.execute(text(sql_count), params).mappings().first()
    
    total_count = int(cnt["n"]) if cnt and cnt.get("n") is not None else len(rows)
    print(f"🔍 Query executed")
    print(f"✅ Results: {len(rows)} observations (total: {total_count})")
    print(f"✅ Response sent to client\n")

    items = [{
        "patientId": str(r["patientId"]),
        "code": r["code"],
        "display": r["display"] or get_observation_display_from_code(r["code"]),  # Use LOINC mapper when display is NULL
        "valueNumber": r["valueNumber"],
        "valueString": r["valueString"],
        "unit": r["unit"],
        "effectiveDateTime": _iso(r["effDate"]),
    } for r in rows]

    return {"total": total_count, "items": items}


# ── LOINC variant groups — known aliases for the same measurement ──────────────
_LOINC_VARIANTS: Dict[str, List[str]] = {
    "4548-4":  ["4548-4", "17856-6", "59261-8"],   # HbA1c
    "17856-6": ["4548-4", "17856-6", "59261-8"],
    "2345-7":  ["2345-7", "27353-2", "2339-0"],    # Glucose
    "27353-2": ["2345-7", "27353-2", "2339-0"],
    "2160-0":  ["2160-0", "38483-4"],              # Creatinine
    "38483-4": ["2160-0", "38483-4"],
    "2093-3":  ["2093-3"],                         # Cholesterol total
    "2085-9":  ["2085-9"],                         # HDL
    "2089-1":  ["2089-1"],                         # LDL
    "718-7":   ["718-7"],                          # Hemoglobin
    "3094-0":  ["3094-0"],                         # BUN
    "33914-3": ["33914-3"],                        # eGFR
    "2823-3":  ["2823-3"],                         # Potassium
    "2951-2":  ["2951-2"],                         # Sodium
    "10839-9": ["10839-9"],                        # Troponin I
    "42637-9": ["42637-9"],                        # BNP
    "3016-3":  ["3016-3"],                         # TSH
    "55284-4": ["55284-4", "8480-6", "8462-4"],   # Blood pressure
    "8867-4":  ["8867-4"],                         # Heart rate
    "59408-5": ["59408-5"],                        # O2 saturation
}


def _get_related_loinc_codes(loinc_code: str) -> List[str]:
    return _LOINC_VARIANTS.get(loinc_code, [loinc_code])


def _compute_scipy_trend(values: List[float], timestamps: List[str]) -> Dict[str, Any]:
    if len(values) < 3:
        return {"trend": "insufficient_data", "slope": None, "r_squared": None, "p_value": None}
    try:
        from scipy.stats import linregress
        from datetime import datetime

        def _parse(d: str):
            d_clean = d.replace("T", " ").split("+")[0].split("Z")[0].strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(d_clean[:len(d_clean)], fmt)
                except ValueError:
                    continue
            return None

        t0 = _parse(timestamps[0])
        if t0 is None:
            return {"trend": "error", "slope": None, "r_squared": None, "p_value": None}
        x = []
        for d in timestamps:
            parsed = _parse(d)
            if parsed is None:
                return {"trend": "error", "slope": None, "r_squared": None, "p_value": None}
            x.append((parsed - t0).days)

        slope, _, r_value, p_value, _ = linregress(x, values)
        r_sq = round(r_value ** 2, 3)
        p_val = round(p_value, 4)

        if p_val > 0.05 or r_sq < 0.5:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        return {"trend": direction, "slope": round(slope, 4), "r_squared": r_sq, "p_value": p_val}
    except Exception as e:
        logger.warning(f"[timeseries] trend error: {e}")
        return {"trend": "error", "slope": None, "r_squared": None, "p_value": None}


@router.get("/{patient_id}/observations/{loinc_code}/timeseries")
def get_observation_timeseries(patient_id: str, loinc_code: str):
    """
    Deterministic timeseries endpoint — no LLM dependency.
    Returns observed data points only (no interpolation).
    Applies IQR×3.0 outlier clipping for physiologically implausible values.
    Trend computed via scipy.stats.linregress (p < 0.05 and R² > 0.5 required).
    """
    from .elasticsearch_client import es_client
    from .visualization_service import REFERENCE_RANGES

    related_codes = _get_related_loinc_codes(loinc_code)

    body = {
        "query": {"bool": {"must": [
            {"term": {"patient_id": patient_id}},
            {"terms": {"code": related_codes}},
            {"term": {"data_type": "observation"}},
        ]}},
        "sort": [
            {"effective_date": {"order": "asc", "missing": "_last"}},
            {"effective_datetime.keyword": {"order": "asc", "missing": "_last"}},
        ],
        "size": 500,
    }

    try:
        hits = es_client.client.search(index="patient_data", body=body)["hits"]["hits"]
    except Exception as e:
        logger.error(f"[timeseries] ES query failed: {e}")
        hits = []

    timestamps: List[str] = []
    values: List[float] = []
    units: List[str] = []

    for h in hits:
        s = h["_source"]
        v = s.get("value_numeric")
        d = s.get("effective_datetime") or s.get("effective_date") or s.get("timestamp")
        u = str(s.get("unit", "") or "").strip()

        if v is None or not d:
            continue
        if u.lower() in ("unit", "", "none", "null"):
            u = ""

        try:
            timestamps.append(d)
            values.append(float(v))
            units.append(u)
        except (ValueError, TypeError):
            continue

    # IQR×3.0 outlier clipping — conservative; preserves clinical highs/lows
    if len(values) >= 4:
        try:
            import numpy as np
            arr = np.array(values)
            q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
            iqr = q3 - q1
            lo, hi = q1 - 3.0 * iqr, q3 + 3.0 * iqr
            filtered = [(t, v, u) for t, v, u in zip(timestamps, values, units) if lo <= v <= hi]
            if filtered:
                timestamps = [x[0] for x in filtered]
                values = [x[1] for x in filtered]
                units = [x[2] for x in filtered]
        except ImportError:
            pass  # numpy not available — skip clipping

    ref = REFERENCE_RANGES.get(loinc_code, {})
    trend = _compute_scipy_trend(values, timestamps)
    display_name = get_observation_display_from_code(loinc_code) or loinc_code

    return {
        "patient_id": patient_id,
        "loinc_code": loinc_code,
        "display": display_name,
        "count": len(values),
        "timestamps": timestamps,
        "values": values,
        "unit": units[0] if units else "",
        "reference_range": ref,
        "trend": trend,
        "interpolation": "none",
        "outlier_method": "IQR×3.0",
    }
