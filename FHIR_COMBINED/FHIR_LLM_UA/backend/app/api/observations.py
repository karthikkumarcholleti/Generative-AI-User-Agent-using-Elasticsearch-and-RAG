# backend/app/api/observations.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from ..core.database import engine
from .loinc_code_mapper import get_observation_display_from_code

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
