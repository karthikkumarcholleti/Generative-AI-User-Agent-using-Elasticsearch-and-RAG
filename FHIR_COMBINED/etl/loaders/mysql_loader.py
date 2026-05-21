"""
MySQL loader for llm_ua_ai database.
All write operations go through llm_ua_admin.
"""

import hashlib
import json
import mysql.connector
from mysql.connector import Error as MySQLError

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "llm_ua_admin",
    "password": "Admin@LLMUA2025!",
    "database": "llm_ua_ai",
    "charset":  "utf8mb4",
    "autocommit": False,
}


def connect() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(**DB_CONFIG)


def sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------

def already_processed(cur, filename: str) -> bool:
    cur.execute(
        "SELECT status FROM ingestion_log WHERE filename = %s",
        (filename,),
    )
    row = cur.fetchone()
    return row is not None and row[0] == "success"


def log_ingestion(
    cur,
    filename: str,
    file_hash: str,
    source_type: str,
    patient_id: str | None,
    rows_loaded: int,
    rows_skipped: int,
    status: str,
    error_message: str | None = None,
):
    cur.execute(
        """
        INSERT INTO ingestion_log
          (filename, file_hash, source_type, patient_id,
           rows_loaded, rows_skipped, status, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          file_hash     = VALUES(file_hash),
          rows_loaded   = VALUES(rows_loaded),
          rows_skipped  = VALUES(rows_skipped),
          status        = VALUES(status),
          error_message = VALUES(error_message),
          processed_at  = CURRENT_TIMESTAMP
        """,
        (
            filename, file_hash, source_type, patient_id,
            rows_loaded, rows_skipped, status, error_message,
        ),
    )


# ---------------------------------------------------------------------------
# Patient UPSERT
# ---------------------------------------------------------------------------

def upsert_patient(cur, p: dict):
    """Insert or merge patient demographics. visited_hospitals / data_sources are JSON arrays."""
    patient_id   = p["patient_id"]
    source_hosp  = p.get("first_source_hospital")
    data_source  = p.get("data_source", "adt")

    cur.execute(
        "SELECT patient_id FROM patients WHERE patient_id = %s",
        (patient_id,),
    )
    exists = cur.fetchone()

    if not exists:
        cur.execute(
            """
            INSERT INTO patients
              (patient_id, given_name, family_name, birth_date, gender,
               street_address, city, state, postal_code, country, phone,
               first_source_hospital, visited_hospitals, data_sources, filename)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                patient_id,
                p.get("given_name"),
                p.get("family_name"),
                p.get("birth_date"),
                p.get("gender"),
                p.get("street_address"),
                p.get("city"),
                p.get("state"),
                p.get("postal_code"),
                _trunc(p.get("country") or "US", 10),
                p.get("phone"),
                source_hosp,
                json.dumps([source_hosp] if source_hosp else []),
                json.dumps([data_source] if data_source else []),
                p.get("filename"),
            ),
        )
    else:
        # Merge: fill in missing fields; append to visited_hospitals / data_sources
        cur.execute(
            """
            UPDATE patients SET
              given_name     = COALESCE(given_name,     %s),
              family_name    = COALESCE(family_name,    %s),
              birth_date     = COALESCE(birth_date,     %s),
              gender         = COALESCE(gender,         %s),
              street_address = COALESCE(street_address, %s),
              city           = COALESCE(city,           %s),
              state          = COALESCE(state,          %s),
              postal_code    = COALESCE(postal_code,    %s),
              phone          = COALESCE(phone,          %s),
              visited_hospitals = IF(
                JSON_SEARCH(visited_hospitals, 'one', %s) IS NULL,
                JSON_ARRAY_APPEND(visited_hospitals, '$', %s),
                visited_hospitals
              ),
              data_sources = IF(
                JSON_SEARCH(data_sources, 'one', %s) IS NULL,
                JSON_ARRAY_APPEND(data_sources, '$', %s),
                data_sources
              )
            WHERE patient_id = %s
            """,
            (
                p.get("given_name"),
                p.get("family_name"),
                p.get("birth_date"),
                p.get("gender"),
                p.get("street_address"),
                p.get("city"),
                p.get("state"),
                p.get("postal_code"),
                p.get("phone"),
                source_hosp, source_hosp,
                data_source, data_source,
                patient_id,
            ),
        )


# ---------------------------------------------------------------------------
# Observation INSERT
# ---------------------------------------------------------------------------

def insert_observation(cur, obs: dict) -> bool:
    """
    Insert one observation. Returns True on success, False if duplicate (skipped).
    Quarantine must be handled by the caller before calling this.
    """
    try:
        cur.execute(
            """
            INSERT INTO observations
              (observation_id, panel_index, patient_id,
               code, code_system, display, raw_display,
               value_numeric, value_string, unit, unit_ucum,
               ref_range_low, ref_range_high, observation_note,
               effective_date, effective_datetime, status,
               data_type, source_type, source_hospital, filename)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                obs.get("observation_id"),
                obs.get("panel_index", 0),
                obs.get("patient_id"),
                obs.get("code"),
                obs.get("code_system"),
                _trunc(obs.get("display"), 65535),
                _trunc(obs.get("raw_display"), 65535),
                obs.get("value_numeric"),
                _trunc(obs.get("value_string"), 65535),
                _trunc(obs.get("unit"), 50),
                _trunc(obs.get("unit_ucum"), 50),
                obs.get("ref_range_low"),
                obs.get("ref_range_high"),
                _trunc(obs.get("observation_note"), 65535),
                obs.get("effective_date"),
                obs.get("effective_datetime"),
                obs.get("status"),
                obs.get("data_type", "observation"),
                obs.get("source_type"),
                obs.get("source_hospital"),
                obs.get("filename"),
            ),
        )
        return True
    except MySQLError as e:
        if e.errno == 1062:  # Duplicate entry
            return False
        raise


# ---------------------------------------------------------------------------
# Condition INSERT
# ---------------------------------------------------------------------------

def insert_condition(cur, cond: dict):
    cur.execute(
        """
        INSERT INTO conditions
          (condition_id, patient_id, icd_code, display, raw_display,
           code_system, raw_fhir_code, clinical_status,
           onset_datetime, recorded_date,
           source_type, source_hospital, filename)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            cond.get("condition_id"),
            cond.get("patient_id"),
            cond.get("icd_code"),
            _trunc(cond.get("display"), 65535),
            _trunc(cond.get("raw_display"), 65535),
            cond.get("code_system"),
            _trunc(cond.get("raw_fhir_code"), 65535),
            cond.get("clinical_status"),
            cond.get("onset_datetime"),
            cond.get("recorded_date"),
            cond.get("source_type"),
            cond.get("source_hospital"),
            cond.get("filename"),
        ),
    )


# ---------------------------------------------------------------------------
# Encounter INSERT
# ---------------------------------------------------------------------------

def insert_encounter(cur, enc: dict):
    cur.execute(
        """
        INSERT INTO encounters
          (encounter_id, patient_id, status,
           class_code, class_display, type_code, type_display,
           period_start, period_end, service_provider, reason_text,
           source_type, source_hospital, filename)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            enc.get("encounter_id"),
            enc.get("patient_id"),
            enc.get("status"),
            enc.get("class_code"),
            enc.get("class_display"),
            enc.get("type_code"),
            _trunc(enc.get("type_display"), 255),
            enc.get("period_start"),
            enc.get("period_end"),
            enc.get("service_provider"),
            _trunc(enc.get("reason_text"), 65535),
            enc.get("source_type"),
            enc.get("source_hospital"),
            enc.get("filename"),
        ),
    )


# ---------------------------------------------------------------------------
# Note INSERT
# ---------------------------------------------------------------------------

def insert_note(cur, note: dict):
    cur.execute(
        """
        INSERT INTO notes
          (patient_id, note_filename, ccda_filename,
           note_date, content, source_hospital)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            note.get("patient_id"),
            note.get("note_filename"),
            note.get("ccda_filename"),
            note.get("note_date"),
            note.get("content"),
            note.get("source_hospital"),
        ),
    )


# ---------------------------------------------------------------------------
# Quarantine INSERT
# ---------------------------------------------------------------------------

def quarantine_observation(cur, filename: str, patient_id: str | None, fhir_resource: dict,
                           error_code: str, error_detail: str):
    from decimal import Decimal
    def _default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError(f"Not serializable: {type(o)}")
    cur.execute(
        """
        INSERT INTO observation_quarantine
          (filename, patient_id, fhir_resource, error_code, error_detail)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (filename, patient_id, json.dumps(fhir_resource, default=_default), error_code, error_detail),
    )


# ---------------------------------------------------------------------------
# Patient_id lookup from ingestion_log (for notes)
# ---------------------------------------------------------------------------

def get_patient_id_for_ccda(cur, ccda_filename: str) -> str | None:
    cur.execute(
        "SELECT patient_id FROM ingestion_log WHERE filename = %s AND status = 'success'",
        (ccda_filename,),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _trunc(val, max_len: int):
    if val is None:
        return None
    s = str(val)
    return s[:max_len] if len(s) > max_len else s
