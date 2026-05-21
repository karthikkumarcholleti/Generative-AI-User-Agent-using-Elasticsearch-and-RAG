"""
Parses FHIR CCDA bundles (fhir_output_TEST_ccd_* and fhir_output_TEST_{OSF,UPHSM,SCMH}_MEDREC_*).

Returns:
  patient     : dict (name only for CCD network; fuller for MEDREC)
  conditions  : list of condition dicts
  encounters  : list of encounter dicts
  observations: list of observation dicts
"""

import json
from pathlib import Path

from patient_utils import get_patient_id
from effectivedatetime import normalize_effective_dt
from parsers.adt_parser import _normalize_gender, _subject_id

# CCDA structural metadata codes that carry no clinical value
_SKIP_CODES = {
    "8716-3",   # Vital signs
    "8653-8",   # Physician attending note
    "10210-3",  # Physical findings of General status
    "47519-4",  # History of Procedures
    "11369-6",  # History of immunization narrative
    "11450-4",  # Problem list
    "46240-8",  # Encounters
    "18776-5",  # Treatment plan
    "51848-0",  # Assessment note
    "69730-0",  # Instructions
    "48765-2",  # Allergies
    "30954-2",  # Relevant diagnostic tests
}


def parse_file(
    filepath: str,
    source_hospital: str,
    resolver=None,  # DisplayResolver instance, optional
) -> tuple[dict | None, list[dict], list[dict], list[dict]]:
    """Return (patient, conditions, encounters, observations)."""
    with open(filepath, encoding="utf-8") as f:
        bundle = json.load(f)

    filename = Path(filepath).name
    patient = None
    conditions = []
    encounters = []
    observations = []

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            patient = _parse_patient(resource, filepath, source_hospital)

        elif rtype == "Condition":
            cond = _parse_condition(resource, filepath, source_hospital, resolver)
            if cond:
                conditions.append(cond)

        elif rtype == "Encounter":
            enc = _parse_encounter(resource, filepath, source_hospital)
            if enc:
                encounters.append(enc)

        elif rtype == "Observation":
            obs = _parse_observation(resource, filename, source_hospital, resolver)
            if obs:
                observations.append(obs)

    return patient, conditions, encounters, observations


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
        "patient_id":            patient_id,
        "given_name":            given or None,
        "family_name":           family or None,
        "birth_date":            res.get("birthDate"),
        "gender":                _normalize_gender(res.get("gender")),
        "street_address":        (address.get("line") or [None])[0],
        "city":                  address.get("city"),
        "state":                 address.get("state"),
        "postal_code":           address.get("postalCode"),
        "country":               address.get("country") or "US",
        "phone":                 phone,
        "first_source_hospital": source_hospital,
        "filename":              Path(filepath).name,
        "data_source":           "ccda",
    }


def _parse_condition(res: dict, filepath: str, source_hospital: str, resolver) -> dict | None:
    codings = res.get("code", {}).get("coding", [])
    if not codings:
        return None

    coding = codings[0]
    raw_code = (coding.get("code") or "").strip()
    raw_display = (coding.get("display") or "").strip() or None
    code_system = (coding.get("system") or "").strip()

    # Resolve display if missing
    display = None
    if resolver:
        display = resolver.resolve(raw_code, raw_display, code_system)
    else:
        display = raw_display

    # ICD code: only if system says ICD-10
    icd_code = None
    if "icd-10" in code_system.lower() or "icd10" in code_system.lower():
        if raw_code:
            icd_code = raw_code

    # Keep record if we have any code OR display — quarantine only if both are absent
    if not icd_code and not display and not raw_code:
        return None

    cs_codings = res.get("clinicalStatus", {}).get("coding", [])
    clinical_status = cs_codings[0].get("code") if cs_codings else None

    onset_raw = res.get("onsetDateTime") or res.get("onsetPeriod", {}).get("start")
    recorded_raw = res.get("recordedDate")

    return {
        "condition_id":    res.get("id"),
        "patient_id":      _subject_id(res),
        "icd_code":        icd_code,
        "display":         display,
        "raw_display":     raw_display,
        "code_system":     code_system or None,
        "raw_fhir_code":   raw_code or None,
        "clinical_status": clinical_status,
        "onset_datetime":  normalize_effective_dt(onset_raw),
        "recorded_date":   recorded_raw,
        "source_type":     "ccda",
        "source_hospital": source_hospital,
        "filename":        Path(filepath).name,
    }


def _parse_encounter(res: dict, filepath: str, source_hospital: str) -> dict | None:
    cls = res.get("class", {})
    type_list = res.get("type") or [{}]
    type_codings = (type_list[0] if type_list else {}).get("coding") or [{}]
    type_coding = type_codings[0] if type_codings else {}

    period = res.get("period") or {}
    provider_ref = (res.get("serviceProvider") or {}).get("display")

    reason_list = res.get("reasonCode") or []
    reason_text = None
    if reason_list:
        rc = (reason_list[0].get("coding") or [{}])[0]
        reason_text = rc.get("display") or (reason_list[0].get("text"))

    return {
        "encounter_id":    res.get("id"),
        "patient_id":      _subject_id(res),
        "status":          res.get("status"),
        "class_code":      cls.get("code"),
        "class_display":   cls.get("display"),
        "type_code":       type_coding.get("code"),
        "type_display":    type_coding.get("display"),
        "period_start":    normalize_effective_dt(period.get("start")),
        "period_end":      normalize_effective_dt(period.get("end")),
        "service_provider": provider_ref,
        "reason_text":     reason_text,
        "source_type":     "ccda",
        "source_hospital": source_hospital,
        "filename":        Path(filepath).name,
    }


def _parse_observation(
    res: dict,
    filename: str,
    source_hospital: str,
    resolver,
) -> dict | None:
    codings = res.get("code", {}).get("coding", [])
    if not codings:
        return None

    coding = codings[0]
    code = (coding.get("code") or "").strip()
    raw_display = (coding.get("display") or "").strip() or None
    code_system = (coding.get("system") or "").strip()

    # Skip structural CCDA metadata codes
    if code in _SKIP_CODES:
        return None

    display = resolver.resolve(code, raw_display, code_system) if resolver else raw_display

    # Value
    value_numeric = None
    value_string = None
    unit = None
    data_type = "observation"

    vq = res.get("valueQuantity")
    if vq:
        value_numeric = vq.get("value")
        unit = vq.get("unit") or vq.get("code")
        if unit == "unit" and value_numeric is None:
            data_type = "panel_header"
    elif "valueString" in res:
        value_string = str(res["valueString"]).strip() or None
    elif "valueCodeableConcept" in res:
        vcc_codings = res["valueCodeableConcept"].get("coding") or [{}]
        value_string = vcc_codings[0].get("display") or res["valueCodeableConcept"].get("text")

    # effectiveDateTime
    eff_raw = res.get("effectiveDateTime") or res.get("effectivePeriod", {}).get("start")
    eff_norm = normalize_effective_dt(eff_raw, filename, "ccda")

    effective_date = None
    effective_datetime = None
    if eff_norm:
        if "T" in eff_norm:
            effective_datetime = eff_norm
        else:
            effective_date = eff_norm

    # unit="unit" + no numeric value → panel header
    if unit == "unit" and value_numeric is None and value_string is None:
        data_type = "panel_header"

    note_text = None
    if "note" in res:
        notes = res["note"]
        if notes:
            note_text = notes[0].get("text")

    return {
        "observation_id":    res.get("id"),
        "patient_id":        _subject_id(res),
        "code":              code or None,
        "code_system":       code_system or None,
        "display":           display,
        "raw_display":       raw_display,
        "value_numeric":     value_numeric,
        "value_string":      value_string,
        "unit":              unit,
        "unit_ucum":         None,
        "ref_range_low":     None,
        "ref_range_high":    None,
        "observation_note":  note_text,
        "effective_date":    effective_date,
        "effective_datetime": effective_datetime,
        "status":            res.get("status"),
        "data_type":         data_type,
        "source_type":       "ccda",
        "source_hospital":   source_hospital,
        "filename":          filename,
    }
