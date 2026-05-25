"""
Enterprise ETL runner: All_Patients_Data/ → llm_ua_enterprise MySQL

Run from FHIR_COMBINED/:
    python3 etl_enterprise/run_etl_enterprise.py

What is different from etl/run_etl.py:
  1. IdentityResolver scans all files first and assigns one enterprise_patient_id
     per unique patient name (5 proven merge rules).
  2. Every clinical record written with enterprise_patient_id + local_patient_id
     + source_hospital + source_type.
  3. patient_identity_map table records every local MRN → enterprise_patient_id.
  4. Writes to llm_ua_enterprise (not llm_ua_ai).

Idempotent: files already logged as status='success' are skipped.
"""

import os
import sys
import time
import traceback

# ── Import path setup ────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_ETL_DIR = os.path.join(os.path.dirname(_HERE), "etl")

# etl_enterprise/ first (for our new modules)
sys.path.insert(0, _HERE)
# original etl/ second (for parsers, hospital_detector, validators, display_resolver)
sys.path.insert(1, _ETL_DIR)

from identity_resolver import IdentityResolver
from hospital_detector import get_hospital_key
from validators import check_plausibility
from display_resolver import DisplayResolver
from parsers import adt_parser, ccda_parser, oru_parser, notes_parser
from loaders import mysql_loader as db

# ── Data paths ───────────────────────────────────────────────────────────────
_BASE     = os.path.dirname(_HERE)
DATA_ROOT = os.path.join(_BASE, "FHIR_LLM_UA", "Converted_Data", "All_Patients_Data")
ADT_DIR   = os.path.join(DATA_ROOT, "ADT")
CCDA_DIR  = os.path.join(DATA_ROOT, "CCDA")
ORU_DIR   = os.path.join(DATA_ROOT, "ORU")
NOTES_DIR = os.path.join(DATA_ROOT, "NOTES")

COMMIT_EVERY = 200


# ── Counters ─────────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.files_ok = self.files_fail = self.files_skip = 0
        self.patients = self.identity_rows = 0
        self.conditions = self.encounters = 0
        self.observations = self.obs_skipped = self.quarantined = 0
        self.notes = 0

    def report(self):
        print(
            f"\n=== Enterprise ETL Summary ===\n"
            f"  Files  : {self.files_ok} ok | {self.files_fail} failed | {self.files_skip} skipped\n"
            f"  Patients            : {self.patients:,}\n"
            f"  Identity map rows   : {self.identity_rows:,}\n"
            f"  Observations        : {self.observations:,} inserted | "
            f"{self.obs_skipped} dup | {self.quarantined} quarantined\n"
            f"  Conditions          : {self.conditions:,}\n"
            f"  Encounters          : {self.encounters:,}\n"
            f"  Notes               : {self.notes:,}"
        )


# ── Helpers ───────────────────────────────────────────────────────────────────
def _enrich(records: list[dict], eid: str, local_pid: str,
            hosp: str, source_type: str) -> list[dict]:
    """
    Add enterprise_patient_id + local_patient_id + source_hospital + source_type
    to every clinical record returned by a parser.
    Parser stores the local id in record['patient_id'] — rename it.
    """
    for r in records:
        r["enterprise_patient_id"] = eid
        r["local_patient_id"]      = r.pop("patient_id", local_pid)
        r["source_hospital"]       = hosp
        r["source_type"]           = source_type
    return records


def _patient_row(patient: dict, eid: str, local_pid: str,
                 hosp: str, source_type: str, resolver: IdentityResolver) -> dict:
    """Build the patients table row from parser output + identity resolver."""
    return {
        "enterprise_patient_id": eid,
        "given_name":     patient.get("given_name"),
        "family_name":    patient.get("family_name"),
        "birth_date":     patient.get("birth_date"),
        "gender":         patient.get("gender"),
        "street_address": patient.get("street_address"),
        "city":           patient.get("city"),
        "state":          patient.get("state"),
        "postal_code":    patient.get("postal_code"),
        "country":        patient.get("country", "US"),
        "phone":          patient.get("phone"),
        "match_confidence":  resolver.get_confidence(eid),
        "visited_hospitals": resolver.get_visited_hospitals(eid),
        "data_sources":      resolver.get_data_sources(eid),
        "source_hospital":   hosp,
        "source_type":       source_type,
    }


def _identity_map_row(eid: str, local_pid: str, hosp: str,
                      source_type: str, patient: dict, resolver: IdentityResolver) -> dict:
    return {
        "enterprise_patient_id": eid,
        "local_patient_id":      local_pid,
        "source_hospital":       hosp,
        "source_type":           source_type,
        "given_name":            patient.get("given_name"),
        "family_name":           patient.get("family_name"),
        "match_confidence":      resolver.get_confidence(eid),
    }


# ── Main ─────────────────────────────────────────────────────────────────────
def run():
    stats = Stats()
    t0    = time.time()

    # ── Step 0: Build identity resolver ─────────────────────────────────────
    print("Building enterprise identity map (scanning all FHIR files)...")
    resolver = IdentityResolver()
    resolver.build(ADT_DIR, CCDA_DIR, ORU_DIR)
    print()

    # ── Load LOINC display resolver ──────────────────────────────────────────
    print("Loading LOINC reference data...")
    display_resolver = DisplayResolver()
    display_resolver.load()

    # ── Connect to llm_ua_enterprise ────────────────────────────────────────
    print("Connecting to MySQL (llm_ua_enterprise)...")
    cx  = db.connect()
    cur = cx.cursor()

    # ════════════════════════════════════════════════════════════════════════
    # 1. ADT
    # ════════════════════════════════════════════════════════════════════════
    print(f"\n[1/4] ADT — {ADT_DIR}")
    adt_files = sorted(f for f in os.listdir(ADT_DIR) if f.endswith(".json"))
    print(f"      {len(adt_files):,} files")

    for i, fn in enumerate(adt_files):
        filepath = os.path.join(ADT_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        hosp      = get_hospital_key(fn)
        file_hash = db.sha256(filepath)
        rows_loaded = rows_skipped = 0
        eid = local_pid = None

        try:
            patient, conditions = adt_parser.parse_file(filepath, hosp)

            if patient and patient.get("patient_id"):
                local_pid = patient["patient_id"]
                given  = patient.get("given_name", "")
                family = patient.get("family_name", "")
                eid    = resolver.resolve(given, family, local_pid, hosp, "adt")

                if eid:
                    db.upsert_patient(cur,
                        _patient_row(patient, eid, local_pid, hosp, "adt", resolver))
                    db.upsert_identity_map(cur,
                        _identity_map_row(eid, local_pid, hosp, "adt", patient, resolver))
                    rows_loaded += 1
                    stats.patients      += 1
                    stats.identity_rows += 1
                else:
                    print(f"  [WARN] ADT resolve failed: {fn} given={given!r} family={family!r} pid={local_pid}")

            for cond in _enrich(conditions, eid, local_pid, hosp, "adt"):
                if cond.get("enterprise_patient_id"):
                    db.insert_condition(cur, cond)
                    rows_loaded   += 1
                    stats.conditions += 1

            db.log_ingestion(cur, fn, file_hash, "adt", eid, local_pid, hosp,
                             rows_loaded, rows_skipped, "success")
            stats.files_ok += 1

        except Exception as e:
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "adt", eid, local_pid, hosp,
                                 rows_loaded, 0, "failed", str(e)[:500])
            except Exception:
                pass

        if (i + 1) % COMMIT_EVERY == 0:
            cx.commit()
            print(f"      ... {i+1}/{len(adt_files)} ({stats.files_ok} ok, {stats.files_fail} fail)")

    cx.commit()
    print(f"  ADT done: {stats.files_ok} ok | {stats.files_fail} failed | {stats.files_skip} skipped")

    # ════════════════════════════════════════════════════════════════════════
    # 2. CCDA
    # ════════════════════════════════════════════════════════════════════════
    ok0 = stats.files_ok; fail0 = stats.files_fail
    print(f"\n[2/4] CCDA — {CCDA_DIR}")
    ccda_files = sorted(f for f in os.listdir(CCDA_DIR) if f.endswith(".json"))
    print(f"      {len(ccda_files):,} files")

    for i, fn in enumerate(ccda_files):
        filepath = os.path.join(CCDA_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        hosp      = get_hospital_key(fn)
        file_hash = db.sha256(filepath)
        rows_loaded = rows_skipped = 0
        eid = local_pid = None

        try:
            patient, conditions, encounters, observations = ccda_parser.parse_file(
                filepath, hosp, display_resolver
            )

            if patient and patient.get("patient_id"):
                local_pid = patient["patient_id"]
                given  = patient.get("given_name", "")
                family = patient.get("family_name", "")
                eid    = resolver.resolve(given, family, local_pid, hosp, "ccda")

                if eid:
                    db.upsert_patient(cur,
                        _patient_row(patient, eid, local_pid, hosp, "ccda", resolver))
                    db.upsert_identity_map(cur,
                        _identity_map_row(eid, local_pid, hosp, "ccda", patient, resolver))
                    rows_loaded += 1
                    stats.patients      += 1
                    stats.identity_rows += 1
                else:
                    print(f"  [WARN] CCDA resolve failed: {fn} given={given!r} family={family!r} pid={local_pid}")

            for cond in _enrich(conditions, eid, local_pid, hosp, "ccda"):
                if cond.get("enterprise_patient_id"):
                    db.insert_condition(cur, cond)
                    rows_loaded      += 1
                    stats.conditions += 1

            for enc in _enrich(encounters, eid, local_pid, hosp, "ccda"):
                if enc.get("enterprise_patient_id"):
                    db.insert_encounter(cur, enc)
                    rows_loaded      += 1
                    stats.encounters += 1

            for obs in _enrich(observations, eid, local_pid, hosp, "ccda"):
                if not obs.get("enterprise_patient_id"):
                    rows_skipped += 1
                    continue
                ok, detail = check_plausibility(obs.get("code", ""), obs.get("value_numeric"))
                if not ok:
                    db.quarantine_observation(
                        cur, fn, eid, local_pid, hosp, obs, "implausible_value", detail)
                    stats.quarantined += 1
                    rows_skipped += 1
                    continue
                inserted = db.insert_observation(cur, obs)
                if inserted:
                    rows_loaded          += 1
                    stats.observations   += 1
                else:
                    rows_skipped         += 1
                    stats.obs_skipped    += 1

            db.log_ingestion(cur, fn, file_hash, "ccda", eid, local_pid, hosp,
                             rows_loaded, rows_skipped, "success")
            stats.files_ok += 1

        except Exception as e:
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "ccda", eid, local_pid, hosp,
                                 rows_loaded, rows_skipped, "failed", str(e)[:500])
            except Exception:
                pass

        if (i + 1) % COMMIT_EVERY == 0:
            cx.commit()
            print(f"      ... {i+1}/{len(ccda_files)} "
                  f"({stats.files_ok-ok0} ok, {stats.files_fail-fail0} fail)")

    cx.commit()
    print(f"  CCDA done: {stats.files_ok-ok0} ok | {stats.files_fail-fail0} failed")

    # ════════════════════════════════════════════════════════════════════════
    # 3. ORU
    # ════════════════════════════════════════════════════════════════════════
    ok0 = stats.files_ok; fail0 = stats.files_fail
    print(f"\n[3/4] ORU — {ORU_DIR}")
    oru_files = sorted(f for f in os.listdir(ORU_DIR) if f.endswith(".json"))
    print(f"      {len(oru_files):,} files")

    for i, fn in enumerate(oru_files):
        filepath = os.path.join(ORU_DIR, fn)
        if db.already_processed(cur, fn):
            stats.files_skip += 1
            continue

        hosp      = get_hospital_key(fn)
        file_hash = db.sha256(filepath)
        rows_loaded = rows_skipped = 0
        eid = local_pid = None

        try:
            patient, observations = oru_parser.parse_file(filepath, hosp, display_resolver)

            if patient and patient.get("patient_id"):
                local_pid = patient["patient_id"]
                given  = patient.get("given_name", "")
                family = patient.get("family_name", "")
                eid    = resolver.resolve(given, family, local_pid, hosp, "oru")

                if eid:
                    db.upsert_patient(cur,
                        _patient_row(patient, eid, local_pid, hosp, "oru", resolver))
                    db.upsert_identity_map(cur,
                        _identity_map_row(eid, local_pid, hosp, "oru", patient, resolver))
                    rows_loaded += 1
                    stats.patients      += 1
                    stats.identity_rows += 1
                else:
                    print(f"  [WARN] ORU resolve failed: {fn} given={given!r} family={family!r} pid={local_pid}")

            for obs in _enrich(observations, eid, local_pid, hosp, "oru"):
                if not obs.get("enterprise_patient_id"):
                    rows_skipped += 1
                    continue
                ok, detail = check_plausibility(obs.get("code", ""), obs.get("value_numeric"))
                if not ok:
                    db.quarantine_observation(
                        cur, fn, eid, local_pid, hosp, obs, "implausible_value", detail)
                    stats.quarantined += 1
                    rows_skipped += 1
                    continue
                inserted = db.insert_observation(cur, obs)
                if inserted:
                    rows_loaded        += 1
                    stats.observations += 1
                else:
                    rows_skipped       += 1
                    stats.obs_skipped  += 1

            db.log_ingestion(cur, fn, file_hash, "oru", eid, local_pid, hosp,
                             rows_loaded, rows_skipped, "success")
            stats.files_ok += 1

        except Exception as e:
            stats.files_fail += 1
            try:
                db.log_ingestion(cur, fn, file_hash, "oru", eid, local_pid, hosp,
                                 rows_loaded, rows_skipped, "failed", str(e)[:500])
            except Exception:
                pass

        if (i + 1) % COMMIT_EVERY == 0:
            cx.commit()
            print(f"      ... {i+1}/{len(oru_files)} "
                  f"({stats.files_ok-ok0} ok, {stats.files_fail-fail0} fail)")

    cx.commit()
    print(f"  ORU done: {stats.files_ok-ok0} ok | {stats.files_fail-fail0} failed")

    # ════════════════════════════════════════════════════════════════════════
    # 4. NOTES
    # ════════════════════════════════════════════════════════════════════════
    ok0 = stats.files_ok; fail0 = stats.files_fail
    print(f"\n[4/4] NOTES — {NOTES_DIR}")

    if not os.path.isdir(NOTES_DIR):
        print("  NOTES directory not found — skipping")
    else:
        note_files = sorted(
            f for f in os.listdir(NOTES_DIR)
            if f.lower().endswith(".txt") and "ed_note" in f.lower()
        )
        print(f"      {len(note_files):,} files")

        # Build ccda_key → ccda_filename map (same as original ETL)
        ccda_key_map = notes_parser.build_ccda_key_map(CCDA_DIR)

        for fn in note_files:
            filepath = os.path.join(NOTES_DIR, fn)
            if db.already_processed(cur, fn):
                stats.files_skip += 1
                continue

            file_hash = db.sha256(filepath)
            hosp      = get_hospital_key(fn)
            eid = local_pid = None

            try:
                note       = notes_parser.parse_note_file(filepath)
                ccda_key   = note.get("ccda_key", "")
                ccda_fname = ccda_key_map.get(ccda_key)

                # Look up enterprise_patient_id from the CCDA file via identity map
                if ccda_fname:
                    # The ccda_filename without extension is the ccda_key;
                    # find the patient in our resolver's records
                    from identity_resolver import _extract_patient
                    ccda_path = os.path.join(CCDA_DIR, ccda_fname)
                    if os.path.exists(ccda_path):
                        c_pid, c_given, c_family, _ = _extract_patient(ccda_path)
                        if c_given and c_family:
                            local_pid = c_pid
                            eid = resolver.resolve(c_given, c_family, c_pid, hosp, "ccda")

                note_row = {
                    "enterprise_patient_id": eid,
                    "local_patient_id":      local_pid,
                    "source_hospital":       hosp,
                    "note_filename":         fn,
                    "ccda_filename":         ccda_fname,
                    "note_date":             note.get("note_date"),
                    "content":               note.get("content"),
                }
                db.insert_note(cur, note_row)

                status = "success" if eid else "partial"
                msg    = None if eid else "enterprise_patient_id not resolved"
                db.log_ingestion(cur, fn, file_hash, "notes", eid, local_pid, hosp,
                                 1, 0, status, msg)
                stats.notes    += 1
                stats.files_ok += 1

            except Exception as e:
                stats.files_fail += 1
                try:
                    db.log_ingestion(cur, fn, file_hash, "notes", None, None, hosp,
                                     0, 0, "failed", str(e)[:500])
                except Exception:
                    pass

        cx.commit()
        print(f"  NOTES done: {stats.files_ok-ok0} ok | {stats.files_fail-fail0} failed")

    cx.close()

    elapsed = time.time() - t0
    stats.report()
    print(f"\nTotal time: {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    run()
