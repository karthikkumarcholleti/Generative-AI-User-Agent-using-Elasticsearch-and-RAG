# backend/app/api/patients.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import text
from ..core.database import engine

router = APIRouter(prefix="/patients", tags=["patients"])

class PatientLite(BaseModel):
    id: int
    patientId: str
    displayName: str
    dob: Optional[str] = None
    gender: Optional[str] = None

class Demographics(BaseModel):
    id: int
    patientId: str
    name: str
    birthDate: Optional[str] = None
    ageYears: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None

def _iso(v):
    try:
        return v.isoformat() if v else None
    except Exception:
        return str(v) if v else None

@router.get("", response_model=List[PatientLite])
def search_patients(query: str = Query(""), limit: int = 5000):
    print(f"🔍 API Call - Search Patients")
    print(f"🔍 Query: '{query}'")
    print(f"🔍 Limit: {limit}")
    
    q = (query or "").strip()
    isnum = 1 if q.isdigit() else 0
    q_len = len(q)

    # Name tokens and helpers
    tokens = q.split()
    t1 = f"%{tokens[0]}%" if tokens else "%"
    t2 = f"%{tokens[1]}%" if len(tokens) > 1 else None
    nameprefix = f"{q}%" if q else "%"
    q_lower = q.lower()

    # Build SQL conditionally to avoid NULL parameter issues
    if isnum == 1:
        # Numeric search
        sql = """
        SELECT
          p.patient_id AS patientId,
          CONCAT(p.given_name, ' ', p.family_name) AS displayName,
          p.birth_date AS dob,
          p.gender AS gender
        FROM patients p
        WHERE p.patient_id = :q
           OR p.patient_id LIKE :pidprefix
           OR RIGHT(p.patient_id, :q_len) = :q
           OR p.patient_id REGEXP CONCAT('^0*', :q, '$')
        ORDER BY
          CASE
            WHEN p.patient_id = :q THEN 0
            WHEN p.patient_id REGEXP CONCAT('^0*', :q, '$') THEN 1
            WHEN p.patient_id LIKE :pidprefix THEN 2
            WHEN RIGHT(p.patient_id, :q_len) = :q THEN 3
            ELSE 4
          END,
          p.created_at DESC,
          p.patient_id DESC
        LIMIT :limit
        """
        params = {
            "q": q,
            "q_len": q_len,
            "pidprefix": f"{q}%",
            "limit": limit,
        }
    else:
        # Name search
        if t2:
            sql = """
            SELECT
              p.patient_id AS patientId,
              CONCAT(p.given_name, ' ', p.family_name) AS displayName,
              p.birth_date AS dob,
              p.gender AS gender
            FROM patients p
            WHERE p.given_name LIKE :t1
               OR p.family_name LIKE :t1
               OR CONCAT(p.given_name, ' ', p.family_name) LIKE :t1
               OR p.given_name LIKE :t2
               OR p.family_name LIKE :t2
               OR CONCAT(p.given_name, ' ', p.family_name) LIKE :t2
            ORDER BY
              CASE
                WHEN LOWER(CONCAT(p.given_name, ' ', p.family_name)) = :q_lower THEN 0
                WHEN CONCAT(p.given_name, ' ', p.family_name) LIKE :nameprefix THEN 1
                ELSE 4
              END,
              p.created_at DESC,
              p.patient_id DESC
            LIMIT :limit
            """
            params = {
                "t1": t1,
                "t2": t2,
                "nameprefix": nameprefix,
                "q_lower": q_lower,
                "limit": limit,
            }
        else:
            sql = """
            SELECT
              p.patient_id AS patientId,
              CONCAT(p.given_name, ' ', p.family_name) AS displayName,
              p.birth_date AS dob,
              p.gender AS gender
            FROM patients p
            WHERE p.given_name LIKE :t1
               OR p.family_name LIKE :t1
               OR CONCAT(p.given_name, ' ', p.family_name) LIKE :t1
            ORDER BY
              CASE
                WHEN LOWER(CONCAT(p.given_name, ' ', p.family_name)) = :q_lower THEN 0
                WHEN CONCAT(p.given_name, ' ', p.family_name) LIKE :nameprefix THEN 1
                ELSE 4
              END,
              p.created_at DESC,
              p.patient_id DESC
            LIMIT :limit
            """
            params = {
                "t1": t1,
                "nameprefix": nameprefix,
                "q_lower": q_lower,
                "limit": limit,
            }

    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        
        print(f"🔍 Query executed")
        print(f"✅ Results: {len(rows)} patients found")
        print(f"✅ Response sent to client\n")

        # Generate id from patientId hash for API compatibility (cocm_db_unified doesn't have id column)
        return [
            {
                "id": hash(r["patientId"]) % (10**9),  # Generate numeric id from patientId hash
                "patientId": r["patientId"],
                "displayName": r["displayName"],
                "dob": _iso(r["dob"]),
                "gender": r["gender"],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"❌ Error in search_patients: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{patient_id}/demographics", response_model=Demographics)
def get_demographics(patient_id: str):
    print(f"🔍 API Call - Get Demographics")
    print(f"🔍 Patient ID: {patient_id}")
    
    sql_p = """
      SELECT p.patient_id AS patientId,
             CONCAT(p.given_name, ' ', p.family_name) AS name,
             p.birth_date AS birthDate,
             p.gender, p.city, p.state, p.postal_code AS postalCode
      FROM patients p
      WHERE p.patient_id = :pid
      LIMIT 1
    """
    with engine.connect() as conn:
        prow = conn.execute(text(sql_p), {"pid": patient_id}).mappings().first()

    if not prow:
        print(f"❌ Patient not found: {patient_id}")
        raise HTTPException(status_code=404, detail="patient not found")
    
    print(f"✅ Patient found: {prow.get('name', 'Unknown')}")
    print(f"✅ Response sent to client\n")

    def _age_years(d):
        if not d:
            return None
        from datetime import date as _date
        today = _date.today()
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))

    bdate = prow["birthDate"]
    # Generate id from patientId hash for API compatibility (cocm_db_unified doesn't have id column)
    return Demographics(
        id=hash(str(prow["patientId"])) % (10**9),  # Generate numeric id from patientId hash
        patientId=str(prow["patientId"]),
        name=str(prow["name"]),
        birthDate=_iso(bdate),
        ageYears=_age_years(bdate),
        gender=(prow["gender"] or None),
        city=(prow["city"] or None),
        state=(prow["state"] or None),
        postalCode=(prow["postalCode"] or None),
    )
