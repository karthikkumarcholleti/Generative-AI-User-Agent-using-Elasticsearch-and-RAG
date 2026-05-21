"""
Resolves a human-readable display name for a clinical code.
Priority: raw FHIR display → LOINC CSV → ICD-10 file → SNOMED API → None

Load once at ETL startup:
    from display_resolver import DisplayResolver
    resolver = DisplayResolver()
    resolver.load()
"""

import csv
import os
import requests

_REF = os.path.join(os.path.dirname(__file__), "reference_data")
LOINC_PATH = os.path.join(_REF, "Loinc.csv")  # Full LOINC 2.82 — 40 cols incl. EXAMPLE_UCUM_UNITS
ICD10_PATH = os.path.join(_REF, "icd10cm_order_2026.txt")

SNOMED_API = "https://cts.nlm.nih.gov/fhir/CodeSystem/$lookup"


class DisplayResolver:
    def __init__(self):
        self.loinc: dict[str, dict] = {}
        self.icd10: dict[str, str] = {}
        self._snomed_cache: dict[str, str | None] = {}

    def load(self):
        self._load_loinc()
        self._load_icd10()
        print(f"  LOINC: {len(self.loinc):,} codes loaded")
        print(f"  ICD-10: {len(self.icd10):,} codes loaded")

    def _load_loinc(self):
        with open(LOINC_PATH, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                code = row.get("LOINC_NUM", "").strip()
                if code:
                    self.loinc[code] = {
                        "display": row.get("LONG_COMMON_NAME", "").strip(),
                        "class":   row.get("CLASS", "").strip(),
                        "ucum":    row.get("EXAMPLE_UCUM_UNITS", "").strip(),
                    }

    def _load_icd10(self):
        # Fixed-width: seq(5) space code(7) space level(1) space long_desc  short_desc
        with open(ICD10_PATH, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(None, 3)
                if len(parts) >= 4:
                    code = parts[1]
                    # long_desc and short_desc are separated by two or more spaces
                    long_desc = parts[3].split("  ")[0].strip()
                    self.icd10[code] = long_desc

    def resolve(self, code: str, raw_display: str | None, code_system: str | None) -> str | None:
        """Return best available display string, or None."""
        # 1. Trust the raw FHIR display if it looks substantive
        if raw_display and len(raw_display.strip()) > 2:
            return raw_display.strip()

        if not code:
            return None

        code = code.strip()
        cs = (code_system or "").lower()

        # 2. LOINC
        if "loinc" in cs or cs == "http://loinc.org":
            entry = self.loinc.get(code)
            if entry and entry["display"]:
                return entry["display"]

        # 3. ICD-10
        if "icd" in cs or "icd-10" in cs or "icd10" in cs:
            display = self.icd10.get(code)
            if display:
                return display

        # 4. SNOMED — live API, cached
        if "snomed" in cs or "sct" in cs:
            return self._snomed_lookup(code)

        return None

    def get_loinc_ucum(self, code: str) -> str | None:
        entry = self.loinc.get(code.strip(), {})
        return entry.get("ucum") or None

    def get_loinc_class(self, code: str) -> str | None:
        entry = self.loinc.get(code.strip(), {})
        return entry.get("class") or None

    def _snomed_lookup(self, code: str) -> str | None:
        if code in self._snomed_cache:
            return self._snomed_cache[code]
        try:
            r = requests.get(
                SNOMED_API,
                params={"system": "http://snomed.info/sct", "code": code},
                timeout=5,
            )
            if r.ok:
                for param in r.json().get("parameter", []):
                    if param.get("name") == "display":
                        display = param.get("valueString")
                        self._snomed_cache[code] = display
                        return display
        except Exception:
            pass
        self._snomed_cache[code] = None
        return None
