# backend/app/api/notes.py
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from ..core.database import engine

router = APIRouter(prefix="/patients", tags=["notes"])

class Note(BaseModel):
    patientId: str
    created: Optional[str] = None
    text: Optional[str] = None
    sourceType: Optional[str] = None
    fileName: Optional[str] = None
    baseKey: Optional[str] = None

class NoteList(BaseModel):
    total: int
    items: List[Note]

@router.get("/{patient_id}/notes", response_model=NoteList)
def list_notes(
    patient_id: str,
    q: str = Query("", description="Optional keyword filter (searches note_text, filename_txt, base_key)"),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) on note_datetime/created_at"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD, exclusive) on note_datetime/created_at"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    has_q = 1 if q else 0
    like_q = f"%{q}%" if q else None

    sql = """
    SELECT
      n.patient_id                         AS patientId,
      COALESCE(n.note_datetime, n.created_at) AS created,
      n.note_text                          AS text,
      n.source_type                        AS sourceType,
      n.filename_txt                       AS fileName,
      n.base_key                           AS baseKey
    FROM notes n
    WHERE n.patient_id = :pid
      AND (:has_q = 0 OR (
            n.note_text    LIKE :like_q OR
            n.filename_txt LIKE :like_q OR
            n.base_key     LIKE :like_q
      ))
      AND (:start IS NULL OR DATE(COALESCE(n.note_datetime, n.created_at)) >= :start)
      AND (:end   IS NULL OR DATE(COALESCE(n.note_datetime, n.created_at)) <  :end)
    ORDER BY COALESCE(n.note_datetime, n.created_at) DESC, n.id DESC
    LIMIT :limit OFFSET :offset
    """

    sql_count = """
    SELECT COUNT(*) AS n
    FROM notes n
    WHERE n.patient_id = :pid
      AND (:has_q = 0 OR (
            n.note_text    LIKE :like_q OR
            n.filename_txt LIKE :like_q OR
            n.base_key     LIKE :like_q
      ))
      AND (:start IS NULL OR DATE(COALESCE(n.note_datetime, n.created_at)) >= :start)
      AND (:end   IS NULL OR DATE(COALESCE(n.note_datetime, n.created_at)) <  :end)
    """

    params = {
        "pid": patient_id,
        "has_q": has_q,
        "like_q": like_q,
        "start": start,
        "end": end,
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

    items = [{
        "patientId": r["patientId"],
        "created": _iso(r["created"]),
        "text": r["text"],
        "sourceType": r["sourceType"],
        "fileName": r["fileName"],
        "baseKey": r["baseKey"],
    } for r in rows]

    total = int(cnt["n"]) if cnt and cnt.get("n") is not None else len(items)
    return {"total": total, "items": items}
