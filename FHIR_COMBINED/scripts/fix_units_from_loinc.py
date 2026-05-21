"""
Phase 2A — Populate unit_ucum in MySQL observations from LOINC 2.82 EXAMPLE_UCUM_UNITS.

Reads the full Loinc.csv (40-column release), builds a {loinc_code → ucum_unit} map,
then UPDATEs observations in batches by LOINC code.

Run from FHIR_COMBINED root:
  python3 scripts/fix_units_from_loinc.py
"""

import csv
import os
import sys
import pymysql

LOINC_CSV = os.path.join(os.path.dirname(__file__), "../etl/reference_data/Loinc.csv")
DB_CONF = dict(host="127.0.0.1", user="llm_ua_admin",
               password="Admin@LLMUA2025!", database="llm_ua_ai")


def load_ucum_map(loinc_csv: str) -> dict:
    ucum = {}
    with open(loinc_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("LOINC_NUM", "").strip().strip('"')
            unit = row.get("EXAMPLE_UCUM_UNITS", "").strip().strip('"')
            if code and unit:
                ucum[code] = unit
    print(f"  Loaded {len(ucum):,} LOINC→UCUM mappings from {loinc_csv}")
    return ucum


def main():
    print("=== Phase 2A: Populate unit_ucum from LOINC 2.82 ===")

    if not os.path.exists(LOINC_CSV):
        sys.exit(f"ERROR: Loinc.csv not found at {LOINC_CSV}\n"
                 "Run: cp FHIR_LLM_UA/Converted_Data/All_Patients_Data/Loinc_2.82/LoincTable/Loinc.csv etl/reference_data/Loinc.csv")

    ucum_map = load_ucum_map(LOINC_CSV)

    conn = pymysql.connect(**DB_CONF, autocommit=False)
    cur = conn.cursor()

    # Get distinct LOINC codes present in observations that have bad/missing units
    cur.execute("""
        SELECT DISTINCT code
        FROM observations
        WHERE code IS NOT NULL AND code != ''
          AND (unit IN ('unit','') OR unit IS NULL)
    """)
    codes_with_bad_units = {row[0] for row in cur.fetchall()}
    print(f"  Distinct LOINC codes with bad units in DB: {len(codes_with_bad_units):,}")

    # Find intersection with LOINC UCUM map
    fixable = {c: ucum_map[c] for c in codes_with_bad_units if c in ucum_map}
    print(f"  Codes with a known UCUM unit: {len(fixable):,}")

    if not fixable:
        print("  Nothing to update.")
        conn.close()
        return

    total_updated = 0
    batch_size = 50
    codes_list = list(fixable.items())

    for i in range(0, len(codes_list), batch_size):
        batch = codes_list[i:i + batch_size]
        for code, ucum in batch:
            cur.execute("""
                UPDATE observations
                SET unit_ucum = %s
                WHERE code = %s
                  AND (unit IN ('unit','') OR unit IS NULL)
                  AND (unit_ucum IS NULL OR unit_ucum = '')
            """, (ucum, code))
            total_updated += cur.rowcount
        conn.commit()
        done = min(i + batch_size, len(codes_list))
        print(f"  [{done}/{len(codes_list)} codes] running total updated: {total_updated:,}")

    # Also update observations where unit is already set (non-placeholder)
    # but unit_ucum is still NULL — use UCUM as canonical reference
    cur.execute("""
        SELECT DISTINCT code
        FROM observations
        WHERE code IS NOT NULL AND code != ''
          AND (unit_ucum IS NULL OR unit_ucum = '')
    """)
    remaining_codes = {row[0] for row in cur.fetchall()}
    remaining_fixable = {c: ucum_map[c] for c in remaining_codes if c in ucum_map}
    print(f"\n  Additional codes with non-bad unit but missing ucum: {len(remaining_fixable):,}")

    extra_updated = 0
    for code, ucum in remaining_fixable.items():
        cur.execute("""
            UPDATE observations
            SET unit_ucum = %s
            WHERE code = %s
              AND (unit_ucum IS NULL OR unit_ucum = '')
        """, (ucum, code))
        extra_updated += cur.rowcount
    conn.commit()
    print(f"  Extra rows updated: {extra_updated:,}")
    total_updated += extra_updated

    # Final verification
    cur.execute("SELECT COUNT(*) FROM observations WHERE unit_ucum IS NOT NULL AND unit_ucum != ''")
    final_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    total = cur.fetchone()[0]

    conn.close()

    print(f"\n=== Done ===")
    print(f"  Rows with unit_ucum populated: {final_count:,} / {total:,} ({100*final_count/total:.1f}%)")
    print(f"  Total rows updated this run:   {total_updated:,}")


if __name__ == "__main__":
    main()
