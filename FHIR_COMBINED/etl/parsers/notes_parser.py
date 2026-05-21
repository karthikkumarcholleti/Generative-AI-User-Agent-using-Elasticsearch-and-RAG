"""
Parses ED note .txt files and links them to their CCDA patient_id.

Note filename:  TEST_ccd_{facility}_{timestamp}[ ({n})]_ed_note.txt
CCDA filename:  fhir_output_TEST_ccd_{facility}_{timestamp}[ ({n})].json

Link key: strip "fhir_output_" prefix and ".json" suffix from CCDA filename
          = strip "_ed_note.txt" suffix from note filename
"""

import re
from pathlib import Path


def parse_note_file(filepath: str) -> dict:
    """Read note content and return metadata dict (patient_id resolved by caller)."""
    path = Path(filepath)
    filename = path.name

    # Derive the CCDA key from note filename
    # e.g. "TEST_ccd_uphieaspirus_20250701000000 (1)_ed_note.txt"
    #   →  "TEST_ccd_uphieaspirus_20250701000000 (1)"
    ccda_key = re.sub(r"_ed_note\.txt$", "", filename, flags=re.IGNORECASE)

    # Extract date from timestamp in filename if present
    note_date = None
    m = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
    if m:
        note_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    content = path.read_text(encoding="utf-8", errors="replace").strip()

    return {
        "note_filename": filename,
        "ccda_key":      ccda_key,        # used by run_etl.py to look up ccda_filename + patient_id
        "note_date":     note_date,
        "content":       content or None,
    }


def build_ccda_key_map(ccda_dir: str) -> dict[str, tuple[str, str | None]]:
    """
    Scan the CCDA directory and build a map:
      ccda_key → (ccda_filename, patient_id_from_ingestion_log)

    patient_id is resolved by the caller from the ingestion_log after CCDA parsing.
    Here we just return the ccda_filename so the loader can look it up.

    Returns:
      { "TEST_ccd_uphieaspirus_20250701000000 (1)": "fhir_output_TEST_ccd_uphieaspirus_20250701000000 (1).json" }
    """
    result = {}
    for p in Path(ccda_dir).iterdir():
        if not p.suffix == ".json":
            continue
        name = p.name
        if name.startswith("fhir_output_"):
            key = re.sub(r"^fhir_output_", "", name)
            key = re.sub(r"\.json$", "", key)
            result[key] = name
    return result
