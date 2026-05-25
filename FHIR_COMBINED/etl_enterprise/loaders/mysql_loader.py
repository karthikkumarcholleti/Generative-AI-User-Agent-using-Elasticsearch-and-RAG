"""
MySQL loader for llm_ua_enterprise database.

Key differences from etl/loaders/mysql_loader.py:
  - Connects to llm_ua_enterprise (not llm_ua_ai)
  - Every write includes enterprise_patient_id + local_patient_id + source_hospital
  - upsert_patient() keyed on enterprise_patient_id (not local patient_id)
  - upsert_identity_map() inserts into patient_identity_map table
  - ingestion_log tracks enterprise_patient_id + local_patient_id + source_hospital
"""

import hashlib
import json
import mysql.connector
from decimal import Decimal
from mysql.connector import Error as MySQLError

DB_CONFIG = {
    "host":       "127.0.0.1",
    "port":       3306,
    "user":       "llm_ua_admin",
    "password":   "P@ssw0rd",
    "database":   "llm_ua_enterprise",
    "charset":    "utf8mb4",
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


def already_processed(cur, filename: str) -> bool:
    cur.execute(
        "SELECT status FROM ingestion_log WHERE filename = %s",
        (filename,),
    )
    row = cur.fetchone()
    return row is not None and row[0] == "success"


# ---------------------------------------------------------------------------
# Patient upsert — keyed on enterprise_patient_id
# ---------------------------------------------------------------------------

def upsert_patient(cur, p: dict):
    """
    Insert patient row if new.
    On duplicate enterprise_patient_id: fill in NULL fields only (first-write wins).
    visited_hospitals and data_sources are updated every call via JSON_ARRAY_APPEND.
    """
    eid         = p["enterprise_patient_id"]
    source_hosp = p.get("source_hospital", "")
    source_type = p.get("source_type", "")

    cur.execute(
        "SELECT enterprise_patient_id FROM patients WHERE enterprise_patient_id = %s",
        (eid,),
    )
    exists = cur.fetchone()

    vh = json.dumps(sorted(p.get("visited_hospitals") or [source_hosp] if source_hosp else []))
    ds = json.dumps(sorted(p.get("data_sources") or [source_type] if source_type else []))

    if not exists:
        cur.execute(
            """
            INSERT INTO patients
              (enterprise_patient_id, given_name, family_name, birth_date, gender,
               street_address, city, state, postal_code, country, phone,
               match_confidence, visited_hospitals, data_sources)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                eid,
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
                p.get("match_confidence", "name_only"),
                vh,
                ds,
            ),
        )
    else:
        # Merge demographics (first non-NULL wins); update hospital/source lists
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
            WHERE enterprise_patient_id = %s
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
                source_type, source_type,
                eid,
            ),
        )


# ---------------------------------------------------------------------------
# Identity map — one row per (local_id, hospital, source_type)
# ---------------------------------------------------------------------------

def upsert_identity_map(cur, entry: dict):
    """Insert mapping row; silently ignore if already present (INSERT IGNORE)."""
    cur.execute(
        """
        INSERT IGNORE INTO patient_identity_map
          (enterprise_patient_id, local_patient_id, source_hospital, source_type,
           given_name, family_name, match_confidence)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            entry["enterprise_patient_id"],
            entry["local_patient_id"],
            entry["source_hospital"],
            entry["source_type"],
            entry.get("given_name"),
            entry.get("family_name"),
            entry.get("match_confidence", "name_only"),
        ),
    )


# ---------------------------------------------------------------------------
# Observation INSERT
# ---------------------------------------------------------------------------

def insert_observation(cur, obs: dict) -> bool:
    """Returns True if inserted, False if duplicate (skipped)."""
    try:
        cur.execute(
            """
            INSERT INTO observations
              (enterprise_patient_id, local_patient_id, source_hospital, source_type,
               observation_id, panel_index,
               code, code_system, display, raw_display,
               value_numeric, value_string, unit, unit_ucum,
               ref_range_low, ref_range_high, observation_note,
               effective_date, effective_datetime, status, data_type, filename)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                obs.get("enterprise_patient_id"),
                obs.get("local_patient_id"),
                obs.get("source_hospital"),
                obs.get("source_type"),
                obs.get("observation_id"),
                obs.get("panel_index", 0),
                obs.get("code"),
                obs.get("code_system"),
                _trunc(obs.get("display"),          65535),
                _trunc(obs.get("raw_display"),      65535),
                obs.get("value_numeric"),
                _trunc(obs.get("value_string"),     65535),
                _trunc(obs.get("unit"),             50),
                _trunc(obs.get("unit_ucum"),        50),
                obs.get("ref_range_low"),
                obs.get("ref_range_high"),
                _trunc(obs.get("observation_note"), 65535),
                obs.get("effective_date"),
                obs.get("effective_datetime"),
                obs.get("status"),
                obs.get("data_type", "observation"),
                obs.get("filename"),
            ),
        )
        return True
    except MySQLError as e:
        if e.errno == 1062:   # Duplicate entry
            return False
        raise


# ---------------------------------------------------------------------------
# Condition INSERT
# ---------------------------------------------------------------------------

def insert_condition(cur, cond: dict):
    cur.execute(
        """
        INSERT INTO conditions
          (enterprise_patient_id, local_patient_id, source_hospital, source_type,
           condition_id, icd_code, display, raw_display,
           code_system, raw_fhir_code, clinical_status,
           onset_datetime, recorded_date, filename)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            cond.get("enterprise_patient_id"),
            cond.get("local_patient_id"),
            cond.get("source_hospital"),
            cond.get("source_type"),
            cond.get("condition_id"),
            cond.get("icd_code"),
            _trunc(cond.get("display"),       65535),
            _trunc(cond.get("raw_display"),   65535),
            cond.get("code_system"),
            _trunc(cond.get("raw_fhir_code"), 65535),
            cond.get("clinical_status"),
            cond.get("onset_datetime"),
            cond.get("recorded_date"),
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
          (enterprise_patient_id, local_patient_id, source_hospital, source_type,
           encounter_id, status, class_code, class_display,
           type_code, type_display, period_start, period_end,
           service_provider, reason_text, filename)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            enc.get("enterprise_patient_id"),
            enc.get("local_patient_id"),
            enc.get("source_hospital"),
            enc.get("source_type"),
            enc.get("encounter_id"),
            enc.get("status"),
            enc.get("class_code"),
            enc.get("class_display"),
            enc.get("type_code"),
            _trunc(enc.get("type_display"),  255),
            enc.get("period_start"),
            enc.get("period_end"),
            enc.get("service_provider"),
            _trunc(enc.get("reason_text"),   65535),
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
          (enterprise_patient_id, local_patient_id, source_hospital,
           note_filename, ccda_filename, note_date, content)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            note.get("enterprise_patient_id"),
            note.get("local_patient_id"),
            note.get("source_hospital"),
            note.get("note_filename"),
            note.get("ccda_filename"),
            note.get("note_date"),
            note.get("content"),
        ),
    )


# ---------------------------------------------------------------------------
# Quarantine INSERT
# ---------------------------------------------------------------------------

def quarantine_observation(
    cur,
    filename: str,
    enterprise_patient_id: str | None,
    local_patient_id: str | None,
    source_hospital: str | None,
    fhir_resource: dict,
    error_code: str,
    error_detail: str,
):
    def _default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError(f"Not serializable: {type(o)}")

    cur.execute(
        """
        INSERT INTO observation_quarantine
          (filename, enterprise_patient_id, local_patient_id, source_hospital,
           fhir_resource, error_code, error_detail)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            filename,
            enterprise_patient_id,
            local_patient_id,
            source_hospital,
            json.dumps(fhir_resource, default=_default),
            error_code,
            _trunc(error_detail, 500),
        ),
    )


# ---------------------------------------------------------------------------
# Ingestion log
# ---------------------------------------------------------------------------

def log_ingestion(
    cur,
    filename: str,
    file_hash: str,
    source_type: str,
    enterprise_patient_id: str | None,
    local_patient_id: str | None,
    source_hospital: str | None,
    rows_loaded: int,
    rows_skipped: int,
    status: str,
    error_message: str | None = None,
):
    cur.execute(
        """
        INSERT INTO ingestion_log
          (filename, file_hash, source_type,
           enterprise_patient_id, local_patient_id, source_hospital,
           rows_loaded, rows_skipped, status, error_message)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
          file_hash             = VALUES(file_hash),
          enterprise_patient_id = VALUES(enterprise_patient_id),
          rows_loaded           = VALUES(rows_loaded),
          rows_skipped          = VALUES(rows_skipped),
          status                = VALUES(status),
          error_message         = VALUES(error_message),
          processed_at          = CURRENT_TIMESTAMP
        """,
        (
            filename, file_hash, source_type,
            enterprise_patient_id, local_patient_id, source_hospital,
            rows_loaded, rows_skipped, status, error_message,
        ),
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _trunc(val, max_len: int):
    if val is None:
        return None
    s = str(val)
    return s[:max_len] if len(s) > max_len else s
