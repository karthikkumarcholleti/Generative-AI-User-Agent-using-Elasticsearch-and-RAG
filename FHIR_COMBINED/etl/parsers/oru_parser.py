"""
Parses FHIR ORU (lab) bundles.

Each file contains one Patient and N Observations.
Multiple observations with the same resource.id = panel sub-tests.
panel_index is the sequential position within each observation_id group.
effectiveDateTime is always NULL in ORU — parsed from filename instead.
"""

import json
from collections import defaultdict
from pathlib import Path

from patient_utils import get_patient_id
from effectivedatetime import normalize_effective_dt
from parsers.adt_parser import _normalize_gender, _subject_id
from validators import parse_decimal


def parse_file(
    filepath: str,
    source_hospital: str,
    resolver=None,
) -> tuple[dict | None, list[dict]]:
    """Return (patient_dict, [observation_dict, ...])."""
    with open(filepath, encoding="utf-8") as f:
        bundle = json.load(f)

    filename = Path(filepath).name
    patient = None
    raw_obs = []

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        rtype = resource.get("resourceType")

        if rtype == "Patient":
            patient = _parse_patient(resource, filepath, source_hospital)
        elif rtype == "Observation":
            raw_obs.append(resource)

    # Assign panel_index: observations sharing the same id = panel sub-tests
    # Encounter them in bundle order; index resets per observation_id.
    id_counter: dict[str, int] = defaultdict(int)
    observations = []
    for res in raw_obs:
        obs = _parse_observation(res, filename, source_hospital, resolver)
        if obs:
            obs_id = obs["observation_id"] or ""
            obs["panel_index"] = id_counter[obs_id]
            id_counter[obs_id] += 1
            observations.append(obs)

    return patient, observations


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
        "data_source":           "oru",
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

    # Skip NM (nuclear medicine) noise
    if code == "NM":
        return None

    display = resolver.resolve(code, raw_display, code_system) if resolver else raw_display

    # UCUM unit from LOINC CSV
    unit_ucum = resolver.get_loinc_ucum(code) if resolver else None

    # Value — ORU always has valueQuantity
    value_numeric = None
    value_string = None
    unit = None
    data_type = "observation"

    vq = res.get("valueQuantity")
    if vq:
        raw_val = vq.get("value")
        value_numeric = parse_decimal(raw_val)
        unit = vq.get("unit") or vq.get("code")
        if unit == "unit" and value_numeric is None:
            data_type = "panel_header"
    elif "valueString" in res:
        value_string = str(res["valueString"]).strip() or None

    # Reference range (Aspirus/OSF/Baraga provide it)
    ref_low = None
    ref_high = None
    rr_list = res.get("referenceRange") or []
    if rr_list:
        rr = rr_list[0]
        ref_low = parse_decimal(rr.get("low", {}).get("value"))
        ref_high = parse_decimal(rr.get("high", {}).get("value"))

    # effectiveDateTime is always NULL in ORU — parse from filename
    eff_norm = normalize_effective_dt(None, filename, "oru")
    effective_date = None
    effective_datetime = None
    if eff_norm:
        if "T" in eff_norm:
            effective_datetime = eff_norm
        else:
            effective_date = eff_norm

    note_text = None
    if "note" in res:
        notes = res["note"]
        if notes:
            note_text = notes[0].get("text")

    return {
        "observation_id":    res.get("id"),
        "panel_index":       0,  # will be overwritten by caller
        "patient_id":        _subject_id(res),
        "code":              code or None,
        "code_system":       code_system or None,
        "display":           display,
        "raw_display":       raw_display,
        "value_numeric":     value_numeric,
        "value_string":      value_string,
        "unit":              unit,
        "unit_ucum":         unit_ucum,
        "ref_range_low":     ref_low,
        "ref_range_high":    ref_high,
        "observation_note":  note_text,
        "effective_date":    effective_date,
        "effective_datetime": effective_datetime,
        "status":            res.get("status"),
        "data_type":         data_type,
        "source_type":       "oru",
        "source_hospital":   source_hospital,
        "filename":          filename,
    }
