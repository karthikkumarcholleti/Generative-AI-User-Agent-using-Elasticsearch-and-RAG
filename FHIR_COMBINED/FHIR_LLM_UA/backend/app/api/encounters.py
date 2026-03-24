# backend/app/api/encounters.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from ..core.database import engine

router = APIRouter(prefix="/patients", tags=["encounters"])

class Encounter(BaseModel):
    id: int
    patientId: str
    klass: Optional[str] = None
    type: Optional[str] = None
    reason: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    locationId: Optional[int] = None

@router.get("/{patient_id}/encounters", response_model=List[Encounter])
def list_encounters(
    patient_id: str,
    start: Optional[str] = Query(None, description="YYYY-MM-DD (inclusive)"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD (inclusive)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    where = ["e.patient_id = :pid"]
    params = {"pid": patient_id, "limit": limit, "offset": offset}

    # Filter by window on the single 'date' column (your table schema)
    if start:
        where.append("e.date >= :start")
        params["start"] = start
    if end:
        where.append("e.date < DATE_ADD(:end, INTERVAL 1 DAY)")  # inclusive end
        params["end"] = end

    sql = f"""
        SELECT
          e.id,
          e.patient_id AS patientId,
          COALESCE(e.class_display, e.class_code) AS klass,
          COALESCE(e.type_display,  e.type_code)  AS type,
          e.admission_reason AS reason,
          e.date AS startDate,
          NULL   AS endDate,
          e.location_id AS locationId
        FROM encounters e
        WHERE {" AND ".join(where)}
        ORDER BY e.date DESC, e.id DESC
        LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    def _iso(d):
        try:
            return d.isoformat() if d else None
        except Exception:
            return str(d) if d else None

    out: List[Encounter] = []
    for r in rows:
        out.append(Encounter(
            id=int(r["id"]),
            patientId=str(r["patientId"]),
            klass=r["klass"],
            type=r["type"],
            reason=r["reason"],
            startDate=_iso(r["startDate"]),
            endDate=None,
            locationId=r["locationId"],
        ))
    return out
