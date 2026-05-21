"""
Parses FHIR ADT bundles (TEST_ASPIRH_*, TEST_OSF_*, TEST_UPHSM_*, TEST_SCMH_*).

Returns:
  patient   : dict with demographics fields
  conditions: list of condition dicts
"""

import json
import re
from pathlib import Path

from patient_utils import get_patient_id


def parse_file(filepath: str, source_hospital: str) -> tuple[dict | None, list[dict]]:
    """Return (patient_dict, [condition_dict, ...]) from an ADT JSON file."""
    with open(filepath, encoding="utf-8") as f:
        bundle = json.load(f)

    patient = None
    conditions = []

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            patient = _parse_patient(resource, filepath, source_hospital)

        elif rtype == "Condition":
            cond = _parse_condition(resource, filepath, source_hospital)
            if cond:
                conditions.append(cond)

    return patient, conditions


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_patient(res: dict, filepath: str, source_hospital: str) -> dict:
    patient_id = get_patient_id(res)
    name = (res.get("name") or [{}])[0]
    given = (name.get("given") or [""])[0]
    family = name.get("family", "")

    address = (res.get("address") or [{}])[0]
    telecom = res.get("telecom") or []
    phone = next(
        (t.get("value") for t in telecom if t.get("system") == "phone"), None
    )

    return {
        "patient_id":         patient_id,
        "given_name":         given or None,
        "family_name":        family or None,
        "birth_date":         res.get("birthDate"),
        "gender":             _normalize_gender(res.get("gender")),
        "street_address":     (address.get("line") or [None])[0],
        "city":               address.get("city"),
        "state":              address.get("state"),
        "postal_code":        address.get("postalCode"),
        "country":            address.get("country") or "US",
        "phone":              phone,
        "first_source_hospital": source_hospital,
        "filename":           Path(filepath).name,
        "data_source":        "adt",
    }


def _parse_condition(res: dict, filepath: str, source_hospital: str) -> dict | None:
    codings = res.get("code", {}).get("coding", [])
    if not codings:
        return None

    coding = codings[0]
    raw_code = coding.get("code", "")
    raw_display = coding.get("display") or ""
    code_system = coding.get("system", "")

    # Parse caret format: "ICD_CODE^DISPLAY" or "ICD_CODE^DISPLAY^SECONDARY_CODE"
    # or "^DISPLAY" (no ICD code)
    icd_code = None
    display = None

    if "^" in raw_code:
        parts = raw_code.split("^")
        icd_part = parts[0].strip()
        disp_part = parts[1].strip() if len(parts) > 1 else ""
        # Validate ICD-10 format: letter + digits (e.g. F90.2, I10, Z86.69)
        if icd_part and re.match(r"^[A-Z]\d", icd_part):
            icd_code = icd_part
        display = disp_part or None
    elif raw_code and re.match(r"^[A-Z]\d", raw_code):
        icd_code = raw_code
        display = raw_display or None
    else:
        display = raw_display or None

    # Skip if neither code nor display
    if not icd_code and not display:
        return None

    # clinical status
    cs_codings = res.get("clinicalStatus", {}).get("coding", [])
    clinical_status = cs_codings[0].get("code") if cs_codings else None

    # onset / recorded
    onset_raw = res.get("onsetDateTime") or res.get("onsetPeriod", {}).get("start")
    recorded_raw = res.get("recordedDate")

    return {
        "condition_id":    res.get("id"),
        "patient_id":      _subject_id(res),
        "icd_code":        icd_code,
        "display":         display,
        "raw_display":     raw_display or None,
        "code_system":     code_system or None,
        "raw_fhir_code":   raw_code or None,
        "clinical_status": clinical_status,
        "onset_datetime":  onset_raw,
        "recorded_date":   recorded_raw,
        "source_type":     "adt",
        "source_hospital": source_hospital,
        "filename":        Path(filepath).name,
    }


def _subject_id(res: dict) -> str | None:
    ref = res.get("subject", {}).get("reference", "")
    return ref.split("/")[-1] if "/" in ref else ref or None


_GENDER_MAP = {
    # HL7 v2 single-char codes (uppercase, as transmitted)
    "m": "male", "f": "female", "o": "other", "u": "unknown", "a": "other",
    # FHIR R4 full strings
    "male": "male", "female": "female", "other": "other", "unknown": "unknown",
    # Variants
    "nb": "other", "nonbinary": "other", "non-binary": "other",
}

def _normalize_gender(g: str | None) -> str | None:
    if not g:
        return None
    return _GENDER_MAP.get(g.lower().strip(), "unknown")
