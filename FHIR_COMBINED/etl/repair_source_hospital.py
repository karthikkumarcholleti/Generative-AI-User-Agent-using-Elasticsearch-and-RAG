"""
Repair source_hospital = 'unknown' records in MySQL.

Uses hospital_detector.get_hospital_key() against the stored filename column
to back-fill the correct facility key without re-running the full ETL.

Tables repaired: observations, conditions, encounters
Also repairs first_source_hospital in patients.

Run from: FHIR_COMBINED/etl/
"""

import sys
import os
import mysql.connector
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from hospital_detector import get_hospital_key

DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "llm_ua_admin",
    "password": "Admin@LLMUA2025!",
    "database": "llm_ua_ai",
    "charset":  "utf8mb4",
}

TABLES = [
    ("observations", "source_hospital", "filename"),
    ("conditions",   "source_hospital", "filename"),
    ("encounters",   "source_hospital", "filename"),
]

# Notes use ccda_filename as the hospital-identity field
NOTES_FILENAME_COL = "ccda_filename"


def _repair_table(cx, table: str, hospital_col: str, filename_col: str) -> dict:
    cur = cx.cursor(dictionary=True)

    # Collect every unique filename that currently maps to 'unknown'
    cur.execute(f"""
        SELECT {filename_col} AS fn, COUNT(*) AS cnt
        FROM {table}
        WHERE {hospital_col} = 'unknown' AND {filename_col} IS NOT NULL
        GROUP BY {filename_col}
    """)
    rows = cur.fetchall()
    cur.close()

    if not rows:
        print(f"  {table}: nothing to repair")
        return {"resolved": 0, "still_unknown": 0}

    # Resolve each filename
    mapping: dict[str, str] = {}
    for row in rows:
        fn = row["fn"]
        key = get_hospital_key(fn)
        mapping[fn] = key

    still_unknown = [fn for fn, key in mapping.items() if key == "unknown"]
    to_fix = {fn: key for fn, key in mapping.items() if key != "unknown"}

    resolved_rows = 0
    cur = cx.cursor()
    for fn, key in to_fix.items():
        cur.execute(
            f"UPDATE {table} SET {hospital_col} = %s WHERE {filename_col} = %s AND {hospital_col} = 'unknown'",
            (key, fn),
        )
        resolved_rows += cur.rowcount
    cx.commit()
    cur.close()

    if still_unknown:
        print(f"  {table}: {resolved_rows} rows repaired. "
              f"Still unknown ({len(still_unknown)} filenames): "
              + ", ".join(still_unknown[:5])
              + ("..." if len(still_unknown) > 5 else ""))
    else:
        print(f"  {table}: {resolved_rows} rows repaired — no unknowns remain")

    return {"resolved": resolved_rows, "still_unknown": len(still_unknown)}


def _repair_patients(cx) -> None:
    """Repair first_source_hospital in patients table."""
    cur = cx.cursor(dictionary=True)
    cur.execute("""
        SELECT patient_id, filename
        FROM patients
        WHERE first_source_hospital = 'unknown' AND filename IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("  patients: nothing to repair")
        return

    fixed = 0
    cur = cx.cursor()
    for row in rows:
        key = get_hospital_key(row["filename"])
        if key != "unknown":
            cur.execute(
                "UPDATE patients SET first_source_hospital = %s WHERE patient_id = %s",
                (key, row["patient_id"]),
            )
            fixed += cur.rowcount
    cx.commit()
    cur.close()
    print(f"  patients: {fixed} rows repaired")


def main():
    print("Connecting to MySQL...")
    cx = mysql.connector.connect(**DB_CONFIG)

    print("\nRepairing source_hospital across tables:")
    totals = {"resolved": 0, "still_unknown": 0}
    for table, hcol, fcol in TABLES:
        result = _repair_table(cx, table, hcol, fcol)
        totals["resolved"]      += result["resolved"]
        totals["still_unknown"] += result["still_unknown"]

    print("\nRepairing notes.source_hospital:")
    result = _repair_table(cx, "notes", "source_hospital", NOTES_FILENAME_COL)
    totals["resolved"]      += result["resolved"]
    totals["still_unknown"] += result["still_unknown"]

    print("\nRepairing patients.first_source_hospital:")
    _repair_patients(cx)

    cx.close()

    print(f"\nDone. Total rows repaired: {totals['resolved']}")
    if totals["still_unknown"]:
        print(f"Filenames still unresolvable: {totals['still_unknown']} "
              "(no matching pattern — add to hospital_detector.py if needed)")


if __name__ == "__main__":
    main()
