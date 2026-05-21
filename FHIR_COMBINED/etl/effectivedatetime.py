"""
Normalizes effectiveDateTime values found in FHIR data.

Three formats verified in All_Patients_Data:
  YYYYMMDD                 → date only (CCDA 38%)
  YYYYMMDDhhmmss±HHMM      → datetime with tz (CCDA 62%)
  NULL                     → parse from ORU filename, else NULL
  invalid (e.g. 20250200)  → returns None (caller should quarantine)
"""

import re
from datetime import datetime


def normalize_effective_dt(
    raw,
    filename: str | None = None,
    source_type: str | None = None,
) -> str | None:
    """Return ISO date or datetime string, or None if unresolvable."""
    if raw is None:
        if source_type == "oru" and filename:
            return _parse_from_filename(filename)
        return None

    raw = str(raw).strip()
    if not raw:
        return None

    # YYYYMMDD
    if re.match(r"^\d{8}$", raw):
        try:
            return datetime.strptime(raw, "%Y%m%d").date().isoformat()
        except ValueError:
            return None  # e.g. 20250200 (Feb 30)

    # HL7 YYYYMMDDhhmmss±HHMM (with seconds)
    if re.match(r"^\d{14}[+-]\d{4}$", raw):
        try:
            return datetime.strptime(raw, "%Y%m%d%H%M%S%z").isoformat()
        except ValueError:
            return None

    # HL7 YYYYMMDDhhmm±HHMM (without seconds — also found in data)
    if re.match(r"^\d{12}[+-]\d{4}$", raw):
        try:
            return datetime.strptime(raw, "%Y%m%d%H%M%z").isoformat()
        except ValueError:
            return None

    # HL7 YYYYMMDDhhmm (without seconds or timezone)
    if re.match(r"^\d{12}$", raw):
        try:
            return datetime.strptime(raw, "%Y%m%d%H%M").isoformat()
        except ValueError:
            return None

    # Already ISO or close enough — pass through
    return raw


def _parse_from_filename(filename: str) -> str | None:
    """Extract timestamp from ORU filename, e.g. TEST_OSF_LAB_2024-02-18-11-41-58-227_fhir.json."""
    basename = filename.split("/")[-1]
    m = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", basename)
    if m:
        p = m.group(1).split("-")
        return f"{p[0]}-{p[1]}-{p[2]}T{p[3]}:{p[4]}:{p[5]}"
    return None
