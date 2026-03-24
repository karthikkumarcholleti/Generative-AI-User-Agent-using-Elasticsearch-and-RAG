# backend/app/api/conditions.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from ..core.database import engine

router = APIRouter(prefix="/patients", tags=["conditions"])

class Condition(BaseModel):
    id: int
    patientId: str
    code: Optional[str] = None
    display: Optional[str] = None
    clinicalStatus: Optional[str] = None
    recordedDate: Optional[str] = None  # from effectiveDateTime

class ConditionList(BaseModel):
    total: int
    items: List[Condition]

@router.get("/{patient_id}/conditions", response_model=ConditionList)
def list_conditions(
    patient_id: str,
    q: str = Query("", description="Optional search token"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    print(f"🔍 API Call - List Conditions")
    print(f"🔍 Patient ID: {patient_id}")
    print(f"🔍 Search query: '{q}'")
    print(f"🔍 Limit: {limit}, Offset: {offset}")
    
    has_q = 1 if q else 0
    like_q = f"%{q}%" if q else None

    sql = """
    SELECT
      c.id,
      c.patient_id      AS patientId,
      c.code            AS code,
      c.display         AS display,
      c.clinical_status AS clinicalStatus,
      c.effectiveDateTime AS recordedDate
    FROM conditions c
    WHERE c.patient_id = :pid
      AND (:has_q = 0 OR (c.display LIKE :like_q OR c.code LIKE :like_q))
    ORDER BY COALESCE(c.effectiveDateTime, '1000-01-01') DESC,
             c.id DESC
    LIMIT :limit OFFSET :offset
    """

    sql_count = """
    SELECT COUNT(*) AS n
    FROM conditions c
    WHERE c.patient_id = :pid
      AND (:has_q = 0 OR (c.display LIKE :like_q OR c.code LIKE :like_q))
    """

    params = {
        "pid": patient_id,
        "has_q": has_q,
        "like_q": like_q,
        "limit": limit,
        "offset": offset,
    }

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
    print(f"✅ Results: {len(rows)} conditions (total: {total_count})")
    print(f"✅ Response sent to client\n")

    items = [{
        "id": int(r["id"]),
        "patientId": str(r["patientId"]),
        "code": r["code"],
        "display": r["display"],
        "clinicalStatus": r["clinicalStatus"],
        "recordedDate": _iso(r["recordedDate"]),
    } for r in rows]

    return {"total": total_count, "items": items}
