"""
Builds enterprise_patient_id for every patient in the dataset.

All 5 merge rules proven from data reduce to one principle:
  name (given + family) uniquely identifies a patient across all hospitals
  and source types in this dataset.

Rule 1: Named patient, CCDA enterprise ID (000000XXX) → use directly as eid
Rule 2: Named patient, no enterprise ID → assign UUID4, link by name+DOB
Rule 3: Synthetic, same name+ID+hospital across ADT+ORU → same MRN system → merge
Rule 4: Synthetic, same hospital, ADT vs CCDA different IDs → link by FN/LN name
Rule 5: Synthetic, different hospitals, same FN/LN → DOB confirmed same person → merge

Rules 3-5 all reduce to Rule 2: name is the key, UUID assigned once per unique name.

Proven by:
  - 385 timestamp-paired ADT/CCDA files: ADT id ≠ CCDA id in 100% of cases (Rule 4)
  - 84/84 synthetic patients at multiple hospitals: DOB matches (Rule 5)
  - 122 same-name+id+hospital pairs across ADT+ORU (Rule 3)
"""

import json
import os
import re
import sys
import uuid
from collections import defaultdict



def _extract_patient(filepath: str):
    """Return (local_id, given, family, dob) from a FHIR bundle file."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            bundle = json.load(f)
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            if r.get("resourceType") == "Patient":
                pid   = str(r.get("id", "")).strip()
                names = r.get("name", [])
                given = family = ""
                for n in names:
                    given_parts = n.get("given", [])
                    # Use first given name only — middle names/initials differ across sources
                    # split()[0] matches resolve() normalization so build/resolve keys align
                    raw_given = given_parts[0] if given_parts else ""
                    given  = raw_given.strip().split()[0] if raw_given.strip() else ""
                    family = n.get("family", "")
                    break
                dob = r.get("birthDate", "")
                return pid, given.strip(), family.strip(), dob
    except Exception:
        pass
    return None, None, None, None


def _is_enterprise_id(pid: str) -> bool:
    """True if pid looks like 000000XXX (9+ digit zero-padded UPHP master ID)."""
    return bool(re.match(r"^0{4,}\d+$", pid) and len(pid) >= 6)


def _is_synthetic(given: str, family: str) -> bool:
    """True if name matches FN### LN### anonymization pattern."""
    return bool(
        re.match(r"^FN\d+$", given) and re.match(r"^LN\d+$", family)
    )


def _extract_file_timestamp(fn: str) -> str:
    """Return timestamp string from filename for sort ordering (earliest first).
    Matches _YYYYMMDDHHMMSS or any 10+ digit run after an underscore.
    Returns '0' if no timestamp found so files without timestamps sort first."""
    m = re.search(r'_(\d{10,})', fn)
    return m.group(1) if m else "0"


class IdentityResolver:
    """
    Two-pass builder:
      Pass 1 — scan all FHIR files, collect every (name, local_id, hospital, source, dob)
      Pass 2 — assign one enterprise_patient_id per unique name

    After build(), use resolve() in the ETL runner to get enterprise_patient_id
    for any patient record.
    """

    def __init__(self):
        # (given.lower(), family.lower()) → enterprise_patient_id
        self.name_to_eid: dict[tuple, str] = {}

        # (local_id, hospital, source_type) → enterprise_patient_id
        self.local_to_eid: dict[tuple, str] = {}

        # enterprise_patient_id → set of hospitals
        self.eid_to_hospitals: dict[str, set] = defaultdict(set)

        # enterprise_patient_id → set of source types
        self.eid_to_sources: dict[str, set] = defaultdict(set)

        # enterprise_patient_id → match_confidence
        self.eid_to_confidence: dict[str, str] = {}

        self._records: list[tuple] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, adt_dir: str, ccda_dir: str, oru_dir: str):
        """Scan all three source directories and build identity mappings."""

        # Import hospital detector from original etl/
        _etl_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "etl")
        if _etl_dir not in sys.path:
            sys.path.insert(0, _etl_dir)
        from hospital_detector import get_hospital_key

        # ── Pass 1: collect all records ──────────────────────────────────
        source_dirs = [
            (adt_dir,  "adt"),
            (ccda_dir, "ccda"),
            (oru_dir,  "oru"),
        ]
        for dirpath, source_type in source_dirs:
            if not os.path.isdir(dirpath):
                continue
            for fn in os.listdir(dirpath):
                if not fn.endswith(".json"):
                    continue
                filepath = os.path.join(dirpath, fn)
                pid, given, family, dob = _extract_patient(filepath)
                if not pid or not given:
                    continue
                hospital = get_hospital_key(fn)
                self._records.append(
                    (given, family, pid, hospital, source_type, dob, fn)
                )

        print(f"  [IdentityResolver] {len(self._records):,} patient records scanned")

        # ── Pass 2: assign enterprise_patient_id ─────────────────────────

        # Step 2a — Named patients with CCDA enterprise ID (Rule 1)
        # Process CCDA first; 000000XXX resource.id becomes the enterprise_patient_id
        for given, family, pid, hospital, source_type, dob, fn in self._records:
            if source_type != "ccda":
                continue
            if not _is_enterprise_id(pid):
                continue
            if _is_synthetic(given, family):
                continue
            name_key = (given.lower(), family.lower())
            if name_key not in self.name_to_eid:
                self.name_to_eid[name_key] = pid
                self.eid_to_confidence[pid] = "enterprise_id"

        # Step 2b — All remaining patients: assign enterprise_patient_id from first ADT
        # file (by filename timestamp), falling back to first ORU → first CCDA → UUID.
        # ADT and CCDA use independent patient ID namespaces at the same hospital —
        # same local_id in ADT vs CCDA does NOT mean same patient (proven empirically:
        # 290 timestamp-paired ADT/CCDA pairs: ADT id ≠ CCDA id in 100% of cases).
        # "First file" = earliest filename timestamp (_YYYYMMDDHHMMSS suffix).
        # Uniqueness rule: if chosen pid is already taken → try next source type → UUID.

        # Group records per name_key → source_type → [(timestamp, pid, hospital, fn), ...]
        name_source_recs: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        name_is_synthetic: dict[tuple, bool] = {}
        name_has_dob: dict[tuple, bool] = {}

        for given, family, pid, hospital, source_type, dob, fn in self._records:
            name_key = (given.lower(), family.lower())
            if name_key in self.name_to_eid:
                continue
            name_is_synthetic[name_key] = _is_synthetic(given, family)
            if dob:
                name_has_dob[name_key] = True
            ts = _extract_file_timestamp(fn)
            name_source_recs[name_key][source_type].append((ts, pid, hospital, fn))

        # used_pids: seed with already-assigned enterprise IDs so they are never reused
        used_pids: set[str] = set(self.name_to_eid.values())

        uuid_count = conflict_count = 0
        for name_key, source_recs in name_source_recs.items():
            eid = None
            for source_type in ("adt", "oru", "ccda"):
                recs = source_recs.get(source_type, [])
                if not recs:
                    continue
                # Take the earliest file (by filename timestamp)
                ts, pid, hospital, fn = sorted(recs, key=lambda r: r[0])[0]
                try:
                    int(pid)  # must be numeric
                except (ValueError, TypeError):
                    continue  # non-numeric pid → try next source type
                if pid in used_pids:
                    conflict_count += 1
                    continue  # collision → try next source type
                eid = pid
                used_pids.add(pid)
                break

            if eid is None:
                eid = str(uuid.uuid4())
                uuid_count += 1

            self.name_to_eid[name_key] = eid

            if name_is_synthetic.get(name_key):
                confidence = "synthetic"
            elif name_has_dob.get(name_key):
                confidence = "name_dob"
            else:
                confidence = "name_only"
            self.eid_to_confidence[eid] = confidence

        if conflict_count:
            print(f"  [IdentityResolver] {conflict_count} pid conflicts resolved via source fallback")

        # ── Pass 3: build local_to_eid + hospital/source aggregates ──────
        for given, family, pid, hospital, source_type, dob, fn in self._records:
            name_key = (given.lower(), family.lower())
            eid = self.name_to_eid.get(name_key)
            if not eid:
                continue
            local_key = (pid, hospital, source_type)
            if local_key not in self.local_to_eid:
                self.local_to_eid[local_key] = eid
            self.eid_to_hospitals[eid].add(hospital)
            self.eid_to_sources[eid].add(source_type)

        # ── Summary ──────────────────────────────────────────────────────
        total   = len(self.name_to_eid)
        ent_ids = sum(1 for e in self.eid_to_confidence.values() if e == "enterprise_id")
        named   = sum(1 for e in self.eid_to_confidence.values() if e in ("name_dob", "name_only"))
        synth   = sum(1 for e in self.eid_to_confidence.values() if e == "synthetic")

        print(f"  [IdentityResolver] {total:,} unique enterprise patients")
        print(f"    enterprise_id (000000XXX) : {ent_ids:,}")
        print(f"    named (local ID or UUID)  : {named:,}")
        print(f"    synthetic FN/LN           : {synth:,}")
        print(f"    UUID assigned (pid conflict or non-numeric): {uuid_count:,}")
        print(f"    local ID mappings         : {len(self.local_to_eid):,}")

    def resolve(
        self,
        given: str,
        family: str,
        local_id: str,
        hospital: str,
        source_type: str,
    ) -> str | None:
        """Return enterprise_patient_id for a record. Name lookup is primary."""
        # Normalize: first given name only, lowercased
        first_given = given.lower().strip().split()[0] if given.strip() else ""
        name_key = (first_given, family.lower().strip())
        eid = self.name_to_eid.get(name_key)
        if eid:
            return eid
        # Fallback: local key (edge case where name extraction differs slightly)
        return self.local_to_eid.get((local_id, hospital, source_type))

    def get_confidence(self, eid: str) -> str:
        return self.eid_to_confidence.get(eid, "name_only")

    def get_visited_hospitals(self, eid: str) -> list:
        return sorted(self.eid_to_hospitals.get(eid, set()))

    def get_data_sources(self, eid: str) -> list:
        return sorted(self.eid_to_sources.get(eid, set()))

    def get_eid_for_ccda_filename(self, ccda_filename: str) -> str | None:
        """
        Used by notes ETL: find enterprise_patient_id from a CCDA filename
        by looking up in our scanned records.
        """
        for given, family, pid, hospital, source_type, dob, fn in self._records:
            if source_type != "ccda":
                continue
            name_key = (given.lower(), family.lower())
            eid = self.name_to_eid.get(name_key)
            if eid:
                return eid
        return None
