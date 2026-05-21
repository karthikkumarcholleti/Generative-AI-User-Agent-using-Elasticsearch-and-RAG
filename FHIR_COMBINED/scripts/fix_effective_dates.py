"""
Phase 2B — Populate effective_date from effective_datetime in MySQL observations.

effective_datetime is a DATETIME column (36% of rows populated).
effective_date is a DATE column (93% NULL).

Simple fix: SET effective_date = DATE(effective_datetime)
WHERE effective_date IS NULL AND effective_datetime IS NOT NULL.

Run from FHIR_COMBINED root:
  python3 scripts/fix_effective_dates.py
"""

import pymysql
import sys

DB_CONF = dict(host="127.0.0.1", user="llm_ua_admin",
               password="Admin@LLMUA2025!", database="llm_ua_ai")


def main():
    print("=== Phase 2B: Populate effective_date from effective_datetime ===")

    conn = pymysql.connect(**DB_CONF, autocommit=False)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM observations WHERE effective_date IS NULL")
    before_null = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations")
    total = cur.fetchone()[0]
    print(f"  Before: {before_null:,} / {total:,} observations have NULL effective_date")

    # Populate effective_date from effective_datetime for all rows where it's missing
    cur.execute("""
        UPDATE observations
        SET effective_date = DATE(effective_datetime)
        WHERE effective_date IS NULL
          AND effective_datetime IS NOT NULL
    """)
    updated = cur.rowcount
    conn.commit()
    print(f"  Rows updated: {updated:,}")

    # Verify
    cur.execute("SELECT COUNT(*) FROM observations WHERE effective_date IS NULL")
    after_null = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM observations WHERE effective_date IS NOT NULL")
    after_have = cur.fetchone()[0]

    conn.close()

    print(f"\n=== Done ===")
    print(f"  effective_date populated: {after_have:,} / {total:,} ({100*after_have/total:.1f}%)")
    print(f"  Still NULL: {after_null:,} (rows with no datetime at all)")


if __name__ == "__main__":
    main()
