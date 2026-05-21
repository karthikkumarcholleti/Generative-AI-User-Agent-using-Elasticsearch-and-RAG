"""
Main ETL runner: All_Patients_Data/ → llm_ua_ai MySQL → Elasticsearch

Run from FHIR_COMBINED/:
    python3 etl/run_etl.py

Idempotent: already-processed files (status=success in ingestion_log) are skipped.
"""

import os
import sys
import traceback
import time

# Make parsers/loaders importable from the etl/ directory
sys.path.insert(0, os.path.dirname(__file__))

from display_resolver import DisplayResolver
from hospital_detector import get_hospital_key
from validators import check_plausibility
from parsers import adt_parser, ccda_parser, oru_parser, notes_parser
from loaders import mysql_loader as db
from loaders.es_loader import bulk_index_all

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(
    _BASE, "FHIR_LLM_UA", "Converted_Data", "All_Patients_Data"
)
ADT_DIR   = os.path.join(DATA_ROOT, "ADT")
CCDA_DIR  = os.path.join(DATA_ROOT, "CCDA")
ORU_DIR   = os.path.join(DATA_ROOT, "ORU")
NOTES_DIR = os.path.join(DATA_ROOT, "NOTES")

COMMIT_EVERY = 200  # rows between commits (keeps memory low)


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
class Stats:
    def __init__(self):
        self.files_ok = self.files_fail = self.files_skip = 0
        self.patients = self.conditions = self.encounters = 0
        self.observations = self.obs_skipped = self.quarantined = 0
        self.notes = 0

    def report(self):
        print(
            f"\n=== ETL Summary ===\n"
            f"  Files: {self.files_ok} OK | {self.files_fail} failed | {self.files_skip} skipped\n"
            f"  Patients   : {self.patients:,}\n"
            f"  Observations: {self.observations:,} inserted | {self.obs_skipped} dup | {self.quarantined} quarantined\n"
            f"  Conditions : {self.conditions:,}\n"
            f"  Encounters : {self.encounters:,}\n"
            f"  Notes      : {self.notes:,}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run():
    stats = Stats()
    t0 = time.time()

    print("Loading reference data...")
    resolver = DisplayResolver()
    resolver.load()

    print("Connecting to MySQL (llm_ua_admin)...")
    cx = db.connect()
    cur = cx.cursor()

    # ── 1. ADT ──────────────────────────────────────────────────────────────
    print(f"\n[1/4] Processing ADT files from {ADT_DIR}")
    adt_files = sorted(f for f in os.listdir(ADT_DIR) if f.endswith(".json"))
    print(f"      {len(adt_files):,} files found")

    for i, fn in enumerate(adt_files):
        filepath = os.path.join(ADT_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        hosp = get_hospital_key(fn)
        file_hash = db.sha256(filepath)
        rows_loaded = rows_skipped = 0
        err = None

        try:
            patient, conditions = adt_parser.parse_file(filepath, hosp)

            if patient and patient.get("patient_id"):
                db.upsert_patient(cur, patient)
                rows_loaded += 1
                stats.patients += 1

            for cond in conditions:
                if cond.get("patient_id"):
                    db.insert_condition(cur, cond)
                    rows_loaded += 1
                    stats.conditions += 1

            db.log_ingestion(cur, fn, file_hash, "adt",
                             patient["patient_id"] if patient else None,
                             rows_loaded, rows_skipped, "success")
            stats.files_ok += 1

        except Exception as e:
            err = str(e)
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "adt", None,
                                 rows_loaded, 0, "failed", err[:500])
            except Exception:
                pass

        if (i + 1) % COMMIT_EVERY == 0:
            cx.commit()
            print(f"      ... {i+1}/{len(adt_files)} ADT ({stats.files_ok} ok, {stats.files_fail} failed)")

    cx.commit()
    print(f"  ADT done: {stats.files_ok} ok, {stats.files_fail} failed, {stats.files_skip} skipped")

    # ── 2. CCDA ─────────────────────────────────────────────────────────────
    files_ok_before = stats.files_ok
    files_fail_before = stats.files_fail
    print(f"\n[2/4] Processing CCDA files from {CCDA_DIR}")
    ccda_files = sorted(f for f in os.listdir(CCDA_DIR) if f.endswith(".json"))
    print(f"      {len(ccda_files):,} files found")

    for i, fn in enumerate(ccda_files):
        filepath = os.path.join(CCDA_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        hosp = get_hospital_key(fn)
        file_hash = db.sha256(filepath)
        rows_loaded = rows_skipped = 0
        patient_id = None
        err = None

        try:
            patient, conditions, encounters, observations = ccda_parser.parse_file(
                filepath, hosp, resolver
            )

            if patient and patient.get("patient_id"):
                patient_id = patient["patient_id"]
                db.upsert_patient(cur, patient)
                rows_loaded += 1
                stats.patients += 1

            for cond in conditions:
                if cond.get("patient_id"):
                    db.insert_condition(cur, cond)
                    rows_loaded += 1
                    stats.conditions += 1

            for enc in encounters:
                if enc.get("patient_id"):
                    db.insert_encounter(cur, enc)
                    rows_loaded += 1
                    stats.encounters += 1

            for obs in observations:
                pid = obs.get("patient_id")
                if not pid:
                    rows_skipped += 1
                    continue

                # Plausibility check
                ok, detail = check_plausibility(obs.get("code", ""), obs.get("value_numeric"))
                if not ok:
                    db.quarantine_observation(cur, fn, pid, obs, "implausible_value", detail)
                    stats.quarantined += 1
                    rows_skipped += 1
                    continue

                inserted = db.insert_observation(cur, obs)
                if inserted:
                    rows_loaded += 1
                    stats.observations += 1
                else:
                    rows_skipped += 1
                    stats.obs_skipped += 1

            db.log_ingestion(cur, fn, file_hash, "ccda", patient_id,
                             rows_loaded, rows_skipped, "success")
            stats.files_ok += 1

        except Exception as e:
            err = str(e)
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "ccda", patient_id,
                                 rows_loaded, rows_skipped, "failed", err[:500])
            except Exception:
                pass

        if (i + 1) % COMMIT_EVERY == 0:
            cx.commit()
            ok_delta = stats.files_ok - files_ok_before
            fail_delta = stats.files_fail - files_fail_before
            print(f"      ... {i+1}/{len(ccda_files)} CCDA ({ok_delta} ok, {fail_delta} failed)")

    cx.commit()
    ok_delta = stats.files_ok - files_ok_before
    fail_delta = stats.files_fail - files_fail_before
    print(f"  CCDA done: {ok_delta} ok, {fail_delta} failed, {stats.files_skip} skipped total")

    # ── 3. ORU ──────────────────────────────────────────────────────────────
    files_ok_before = stats.files_ok
    files_fail_before = stats.files_fail
    print(f"\n[3/4] Processing ORU files from {ORU_DIR}")
    oru_files = sorted(f for f in os.listdir(ORU_DIR) if f.endswith(".json"))
    print(f"      {len(oru_files):,} files found")

    for i, fn in enumerate(oru_files):
        filepath = os.path.join(ORU_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        hosp = get_hospital_key(fn)
        file_hash = db.sha256(filepath)
        rows_loaded = rows_skipped = 0
        patient_id = None
        err = None

        try:
            patient, observations = oru_parser.parse_file(filepath, hosp, resolver)

            if patient and patient.get("patient_id"):
                patient_id = patient["patient_id"]
                db.upsert_patient(cur, patient)
                rows_loaded += 1
                stats.patients += 1

            for obs in observations:
                pid = obs.get("patient_id")
                if not pid:
                    rows_skipped += 1
                    continue

                ok, detail = check_plausibility(obs.get("code", ""), obs.get("value_numeric"))
                if not ok:
                    db.quarantine_observation(cur, fn, pid, obs, "implausible_value", detail)
                    stats.quarantined += 1
                    rows_skipped += 1
                    continue

                inserted = db.insert_observation(cur, obs)
                if inserted:
                    rows_loaded += 1
                    stats.observations += 1
                else:
                    rows_skipped += 1
                    stats.obs_skipped += 1

            db.log_ingestion(cur, fn, file_hash, "oru", patient_id,
                             rows_loaded, rows_skipped, "success")
            stats.files_ok += 1

        except Exception as e:
            err = str(e)
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "oru", patient_id,
                                 rows_loaded, rows_skipped, "failed", err[:500])
            except Exception:
                pass

        if (i + 1) % COMMIT_EVERY == 0:
            cx.commit()
            ok_delta = stats.files_ok - files_ok_before
            fail_delta = stats.files_fail - files_fail_before
            print(f"      ... {i+1}/{len(oru_files)} ORU ({ok_delta} ok, {fail_delta} failed)")

    cx.commit()
    ok_delta = stats.files_ok - files_ok_before
    fail_delta = stats.files_fail - files_fail_before
    print(f"  ORU done: {ok_delta} ok, {fail_delta} failed")

    # ── 4. NOTES ────────────────────────────────────────────────────────────
    files_ok_before = stats.files_ok
    files_fail_before = stats.files_fail
    print(f"\n[4/4] Processing NOTES from {NOTES_DIR}")
    note_files = sorted(
        f for f in os.listdir(NOTES_DIR)
        if f.lower().endswith(".txt") and "ed_note" in f.lower()
    )
    print(f"      {len(note_files):,} files found")

    # Build CCDA key → ccda_filename map once
    ccda_key_map = notes_parser.build_ccda_key_map(CCDA_DIR)

    for fn in note_files:
        filepath = os.path.join(NOTES_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        file_hash = db.sha256(filepath)
        hosp = get_hospital_key(fn)
        patient_id = None
        err = None

        try:
            note = notes_parser.parse_note_file(filepath)
            ccda_key = note.get("ccda_key", "")

            # Resolve ccda_filename and patient_id
            ccda_filename = ccda_key_map.get(ccda_key)
            if ccda_filename:
                patient_id = db.get_patient_id_for_ccda(cur, ccda_filename)

            if not patient_id:
                # Log as partial — note saved without patient link
                note_row = {
                    "patient_id":    None,
                    "note_filename": fn,
                    "ccda_filename": ccda_filename,
                    "note_date":     note.get("note_date"),
                    "content":       note.get("content"),
                    "source_hospital": hosp,
                }
                db.insert_note(cur, note_row)
                db.log_ingestion(cur, fn, file_hash, "notes", None,
                                 1, 0, "partial", "patient_id not resolved")
                stats.notes += 1
                stats.files_ok += 1
            else:
                note_row = {
                    "patient_id":    patient_id,
                    "note_filename": fn,
                    "ccda_filename": ccda_filename,
                    "note_date":     note.get("note_date"),
                    "content":       note.get("content"),
                    "source_hospital": hosp,
                }
                db.insert_note(cur, note_row)
                db.log_ingestion(cur, fn, file_hash, "notes", patient_id,
                                 1, 0, "success")
                stats.notes += 1
                stats.files_ok += 1

        except Exception as e:
            err = str(e)
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "notes", None,
                                 0, 0, "failed", err[:500])
            except Exception:
                pass

    cx.commit()
    ok_delta = stats.files_ok - files_ok_before
    fail_delta = stats.files_fail - files_fail_before
    print(f"  NOTES done: {ok_delta} ok, {fail_delta} failed")

    cx.close()

    # ── 5. ES bulk index ────────────────────────────────────────────────────
    print("\n[5/5] Indexing to Elasticsearch...")
    try:
        bulk_index_all(verbose=True)
    except Exception as e:
        print(f"  ERROR ES: {e} — MySQL data is intact, ES can be re-run separately")

    elapsed = time.time() - t0
    stats.report()
    print(f"\nTotal time: {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    run()
