"""
Extracts the patient_id from a FHIR bundle entry.
Raw resource.id is stored as-is — no stripping of leading zeros.
"000000001" and "1" are different patient records.
"""


def get_patient_id(resource: dict) -> str | None:
    """Return the raw FHIR Patient resource.id as a string, or None if absent."""
    pid = resource.get("id")
    if pid is None:
        return None
    return str(pid).strip() or None
