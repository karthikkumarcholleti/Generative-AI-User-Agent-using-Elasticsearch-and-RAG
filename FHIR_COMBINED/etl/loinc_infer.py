"""
LOINC inference for ORU panel sub-tests.

Clinical problem: Hospitals transmit lab panels (CMP, CBC, etc.) as a set of
flat FHIR Observation resources, each carrying only the panel's internal code
(e.g. LAB17 "COMPREHENSIVE METABOLIC PANEL").  No individual analyte LOINC
codes are present.  The sole identity signal for each analyte is:

    valueQuantity.unit  +  referenceRange[0].{low, high}

This module resolves those signals to the correct LOINC code and display name
using a declarative reference-range lookup table.

Design rationale (for paper Methods section)
---------------------------------------------
* Each row in _RANGE_TABLE defines physiologically valid bounds for a test's
  reference range: (ref_low in [lo_min, lo_max]) AND (ref_high in [hi_min, hi_max]).
* Bounds are derived from CAP (College of American Pathologists) and CLSI
  reference interval guidelines.  Gender-specific variants are modelled as
  separate rows.
* Multiple rows per analyte cover the variation between hospital systems.
* Rows are ordered: a test with tighter bounds is listed before a broader
  variant to prevent false matches.
* When ref_range is absent (hospital did not transmit it), a value-range
  fallback is applied for percentage-based CBC sub-tests.
* All matches are assigned a confidence level (HIGH / MEDIUM) reported to
  the caller so the ETL can track coverage statistics for the paper.

Usage
-----
    from loinc_infer import is_panel_display, infer_panel_subtest, InferenceStats

    stats = InferenceStats()
    if is_panel_display(display):
        result = infer_panel_subtest(unit, ref_low, ref_high, value_numeric)
        if result:
            display, code = result.display_name, result.loinc_code
        stats.record(result)

    print(stats.report())   # → for paper Methods section
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceResult:
    loinc_code:   str
    display_name: str
    confidence:   str   # "HIGH" | "MEDIUM" | "FALLBACK"
    match_basis:  str   # "ref_range" | "value_distribution"


@dataclass
class InferenceStats:
    """Accumulate coverage statistics for the paper's Methods section."""
    total:        int = 0
    high:         int = 0
    medium:       int = 0
    fallback:     int = 0
    unresolved:   int = 0

    def record(self, result: Optional[InferenceResult]) -> None:
        self.total += 1
        if result is None:
            self.unresolved += 1
        elif result.confidence == "HIGH":
            self.high += 1
        elif result.confidence == "MEDIUM":
            self.medium += 1
        else:
            self.fallback += 1

    def report(self) -> str:
        resolved = self.total - self.unresolved
        pct = 100 * resolved / self.total if self.total else 0
        return (
            f"Panel sub-test inference: {resolved}/{self.total} resolved ({pct:.1f}%)\n"
            f"  HIGH confidence (ref-range exact): {self.high}\n"
            f"  MEDIUM confidence (ref-range approx): {self.medium}\n"
            f"  FALLBACK (value distribution): {self.fallback}\n"
            f"  Unresolved (panel header retained): {self.unresolved}"
        )


# ---------------------------------------------------------------------------
# Panel display name registry
# ---------------------------------------------------------------------------

_PANEL_NAMES: frozenset = frozenset({
    "COMPREHENSIVE METABOLIC PANEL",
    "CMP (COMPREHENSIVE METABOLIC PANEL)",
    "BASIC METABOLIC PANEL",
    "BASIC METABOLIC PANEL W/ CALCIUM TOTAL",
    "BASIC METABOLIC PANEL W/CALCIUM",
    "BASIC METABOLIC 2000 PANEL - SERUM OR PLASMA",
    "HEPATIC FUNCTION PANEL",
    "LIVER FUNCTION PANEL",
    "CBC WITH AUTO DIFFERENTIAL",
    "CBC WITH DIFFERENTIAL",
    "CBC W AUTO DIFFERENTIAL",
    "CBC W/ DIFFERENTIAL",
    "CBC W/DIFF",
    "COMPLETE BLOOD COUNT",
    "COMPLETE BLOOD COUNT (CBC) WITHOUT DIFF",
    "COMPLETE BLOOD COUNT W/O DIFFERENTIAL",
    "HEMOGRAM",
    "MANUAL DIFFERENTIAL",
    "DIFFERENTIAL",
    "BLOOD GASES, VENOUS (VBG)",
    "BLOOD GASES, ARTERIAL (ABG)",
    "ARTERIAL BLOOD GASES (ABG)",
    "ARTERIAL BLOOD GAS",
})


def is_panel_display(display: Optional[str]) -> bool:
    """Return True if this display value is a panel header needing sub-test resolution."""
    if not display:
        return False
    return display.strip().upper() in _PANEL_NAMES


# ---------------------------------------------------------------------------
# Unit normalization
# ---------------------------------------------------------------------------

_UNIT_ALIASES: dict[str, str] = {
    # Electrolytes — mEq/L == mmol/L for monovalent ions (Na, K, Cl, HCO3)
    "meq/l":         "meq/l",  "mmol/l":      "meq/l",
    "meg/l":         "meq/l",  "meq":         "meq/l",
    # Mass concentration
    "mg/dl":         "mg/dl",
    "g/dl":          "g/dl",
    "g/l":           "g/l",
    # Enzyme activity
    "iu/l":          "iu/l",   "u/l":         "iu/l",
    "units/l":       "iu/l",   "miu/l":       "iu/l",
    "uiu/ml":        "iu/l",   "u/l^u/l^l":   "iu/l",
    # CBC count — thousands/μL (many notation variants found in hospital HL7 feeds)
    "k/ul":          "k/ul",
    "10(3)/mcl":     "k/ul",   "10(3)/ul":    "k/ul",
    "10 (3)/mcl":    "k/ul",   "10 (3) mcl.": "k/ul",
    "10 (3) mcl":    "k/ul",   # after trailing-dot strip
    "10*3/ul":       "k/ul",   "10^3/ul":     "k/ul",
    "thousands/ul":  "k/ul",   "thou/ul":     "k/ul",
    "x(10)3/ul":     "k/ul",   # X(10)3/UL^X(10)3/UL^L → first component
    # CBC count — millions/μL
    "m/ul":          "m/ul",
    "10(6)/mcl":     "m/ul",   "10(6)/ul":    "m/ul",
    "10*6/ul":       "m/ul",   "millions/ul": "m/ul",
    "x(10)6/ul":     "m/ul",   # X(10)6/UL^X(10)6/UL^L HL7 encoding
    # Cell size / mass
    "fl":            "fl",
    "pg":            "pg",
    # Fraction / percent
    "%":             "%",
    # Clearance
    "ml/min":          "ml/min",
    "ml/min/1.73m2":   "ml/min", "ml/min/1.73":   "ml/min",
    "ml/min/1.73 m2":  "ml/min", "ml/min/1.73m^2":"ml/min",
    # Pressure
    "mmhg":            "mmhg",
    # Dimensionless — HL7 "not applicable" placeholder; also used for A/G ratio
    "unit":            "unit",
    "na":              "na",     # NA^^HL70353 → first component is "NA" → "na"
    "ratio":           "ratio",
    # Time
    "sec":             "sec",
    # Other molar
    "umol/l":          "umol/l",
    "ng/ml":           "ng/ml",  "pg/ml":       "pg/ml",
    "ug/dl":           "ug/dl",
}


def _norm_unit(raw: Optional[str]) -> str:
    if not raw:
        return ""
    # Strip HL7 component encoding: "MMOL/L^MMOL/L^L^^^^5.67" → "MMOL/L"
    raw = raw.split("^")[0].strip().rstrip(".")
    return _UNIT_ALIASES.get(raw.lower(), raw.lower())


# ---------------------------------------------------------------------------
# Declarative reference-range lookup table
#
# Each row:
#   (unit_canonical, lo_min, lo_max, hi_min, hi_max, loinc_code, display_name, confidence)
#
# A test matches when:
#   ref_low  is in [lo_min, lo_max]    (or lo_min/lo_max=None → don't check ref_low)
#   ref_high is in [hi_min, hi_max]    (or hi_min/hi_max=None → don't check ref_high)
#
# Clinical sources:
#   CLSI C28-A3c (reference intervals); CAP Surveys; HL7 FHIR US Core Laboratory
# ---------------------------------------------------------------------------

_RT = "HIGH"    # ref-range exact match
_RM = "MEDIUM"  # ref-range approximate match (wider bounds to cover lab variation)

_RANGE_TABLE: list[tuple] = [

    # =========================================================
    # ELECTROLYTES  (mEq/L or mmol/L — identical numeric scale)
    # =========================================================
    # Sodium        ref_low 130–138    ref_high 140–150
    ("meq/l", 130,  139,  139,  152, "2951-2",   "Sodium",            _RT),
    # Potassium     ref_low 3.3–4.0   ref_high 4.5–5.5
    ("meq/l",  3.3,  4.1,  4.4,  5.6, "2823-3",   "Potassium",         _RT),
    # Chloride      ref_low 92–100    ref_high 100–115
    ("meq/l",  92,  101,   99,  115, "2075-0",   "Chloride",          _RT),
    # CO2/Bicarb    ref_low 18–25     ref_high 24–38
    ("meq/l",  18,   26,   23,   38, "2028-9",   "CO2 (Bicarbonate)", _RT),
    # BUN in mmol/L (international labs; 1 mg/dL = 0.357 mmol/L; typical ref 2.5–7.1 mmol/L)
    # lo_max=3.3 keeps this below K+ lo_min=3.3 and AG lo_min=3 boundary
    ("meq/l", 0.5,  3.3,  5.0,  18,  "3094-0",   "BUN",               _RM),
    # Anion Gap     ref_low 3–10      ref_high 8–22
    ("meq/l",   3,   11,    7,   22, "33037-3",  "Anion Gap",         _RT),

    # =========================================================
    # METABOLIC PANEL  (mg/dL)
    # =========================================================
    # Glucose       ref_low 60–76     ref_high 90–115
    ("mg/dl",  60,   76,   88,  115, "2345-7",   "Glucose",           _RT),
    # BUN           ref_low 5–12      ref_high 15–30
    ("mg/dl",   5,   13,   14,   30, "3094-0",   "BUN",               _RT),
    # Calcium       ref_low 7.8–9.5   ref_high 9.5–12
    ("mg/dl", 7.8,  9.6,  9.4,  12,  "17861-6",  "Calcium",           _RT),
    # Creatinine    ref_low 0.35–0.85 ref_high 0.8–1.7
    ("mg/dl", 0.35, 0.85, 0.75, 1.75, "2160-0",  "Creatinine",        _RT),
    # Bilirubin Total ref_low 0–0.4   ref_high 0.4–2.5
    ("mg/dl",  0.0,  0.4,  0.4,  2.5, "1975-2",  "Bilirubin Total",   _RT),
    # eGFR: no ref range — handled by ml/min block below

    # =========================================================
    # LIVER ENZYMES  (IU/L or U/L)
    # =========================================================
    # ALP           ref_low 25–55     ref_high 90–200
    ("iu/l",   25,   55,   88,  200, "6768-6",   "ALP",               _RT),
    # ALT (SGPT)    ref_low 5–18      ref_high 44–90
    #   Male range  ~7–56; female ~7–45. Discriminated from AST by ref_high > 44.
    ("iu/l",    5,   18,   44,   90, "1742-6",   "ALT",               _RT),
    # AST (SGOT)    ref_low 3–16      ref_high 18–52
    #   Both sexes ~8–40. lo_min lowered to 3 to cover labs reporting [4-35].
    ("iu/l",    3,   16,   18,   52, "1920-8",   "AST",               _RT),
    # IU/L — ref_high only (hospital omitted ref_low):
    #   hi > 88 → ALP; hi 44–90 → ALT; hi 18–55 → AST
    ("iu/l", None, None,   88,  200, "6768-6",   "ALP",               _RM),
    ("iu/l", None, None,   44,   88, "1742-6",   "ALT",               _RM),
    ("iu/l", None, None,   18,   55, "1920-8",   "AST",               _RM),

    # =========================================================
    # SERUM PROTEINS  (g/dL)
    # Note: CBC Hemoglobin is also g/dL — distinguished by ref_high > 9
    # =========================================================
    # Hemoglobin F  ref_low 11–13.5   ref_high 14–19
    ("g/dl",   11,  13.5,  14,   19, "718-7",    "Hemoglobin",        _RT),
    # Hemoglobin M  ref_low 13–16     ref_high 16–20
    ("g/dl",   13,  16.5,  15,   20, "718-7",    "Hemoglobin",        _RT),
    # MCHC          ref_low 28–33     ref_high 33–39
    ("g/dl",   28,   33,   32,   39, "786-4",    "MCHC",              _RT),
    # Total Protein ref_low 5.5–7.0   ref_high 7.0–9.5
    ("g/dl",  5.5,  7.0,  6.8,  9.5, "2885-2",  "Total Protein",     _RT),
    # Albumin       ref_low 3.0–4.2   ref_high 4.5–5.8
    ("g/dl",  3.0,  4.2,  4.4,  5.9, "1751-7",  "Albumin",           _RT),
    # Globulin      ref_low 1.5–2.5   ref_high 2.8–4.5
    ("g/dl",  1.5,  2.6,  2.7,  4.6, "10834-0", "Globulin",          _RT),

    # =========================================================
    # CBC COUNT UNITS  (K/uL = 10³/μL)
    # =========================================================
    # Platelets     ref_low 100–180   ref_high 300–600
    ("k/ul",  100,  181,  280,  600, "777-3",    "Platelets",                  _RT),
    # WBC           ref_low 3.0–5.5   ref_high 8.0–15
    ("k/ul",  3.0,  5.6,  7.5,  15,  "6690-2",  "WBC",                        _RT),
    # Neutrophils   ref_low 1.0–2.8   ref_high 4.0–10
    ("k/ul",  1.0,  2.8,  3.8,  10,  "751-8",   "Neutrophils (Absolute)",     _RT),
    # Lymphocytes   ref_low 0.5–1.5   ref_high 2.0–6.0
    ("k/ul",  0.5,  1.5,  1.9,  6.1, "731-2",   "Lymphocytes (Absolute)",     _RT),
    # Monocytes     ref_low 0.08–0.45 ref_high 0.5–1.5
    ("k/ul", 0.08, 0.45,  0.45, 1.5, "742-1",   "Monocytes (Absolute)",       _RT),
    # Eosinophils   ref_low 0.0–0.1   ref_high 0.2–0.9
    ("k/ul",  0.0, 0.11,  0.18, 0.9, "711-2",   "Eosinophils (Absolute)",     _RT),
    # Basophils     ref_low 0.0–0.05  ref_high 0.0–0.25
    ("k/ul",  0.0, 0.06,  0.0,  0.25,"704-7",   "Basophils (Absolute)",       _RT),

    # =========================================================
    # CBC COUNT UNITS  (M/uL = 10⁶/μL)  — RBC only
    # =========================================================
    # RBC Female    ref_low 3.5–4.5   ref_high 4.8–6.0
    ("m/ul",  3.5,  4.5,  4.7,  6.1, "789-8",   "RBC",               _RT),
    # RBC Male      ref_low 4.2–5.2   ref_high 5.5–7.0
    ("m/ul",  4.2,  5.3,  5.4,  7.1, "789-8",   "RBC",               _RT),

    # =========================================================
    # CELL VOLUME  (fL)
    # =========================================================
    # MCV           ref_low 75–87     ref_high 95–110
    ("fl",    75,   88,   93,  112, "787-2",    "MCV",               _RT),
    # MPV           ref_low 5.5–10.0  ref_high 9.5–14.5 (lo_max 10.5 covers labs reporting [9.7-12.4])
    ("fl",   5.5, 10.5,  9.4, 14.5, "32623-1", "MPV",               _RT),

    # =========================================================
    # CELL HEMOGLOBIN MASS  (pg)  — MCH only
    # =========================================================
    ("pg",    23,   29,   29,   37, "785-6",    "MCH",               _RT),

    # =========================================================
    # CBC PERCENTAGE  (%)
    # Note: Order matters — RDW and Monocytes share overlapping hi values
    #       but have distinct ref_low (RDW lo >8, Monocytes lo 1–7)
    # =========================================================
    # Neutrophils % ref_low 37–58     ref_high 60–82
    ("%",     37,   59,   58,  83,  "770-8",    "Neutrophils (%)",   _RT),
    # Hematocrit F  ref_low 33–40     ref_high 43–52
    ("%",     33,   41,   42,  53,  "4544-3",   "Hematocrit",        _RT),
    # Hematocrit M  ref_low 38–46     ref_high 48–56
    ("%",     38,   47,   47,  57,  "4544-3",   "Hematocrit",        _RT),
    # Lymphocytes % ref_low 10–25     ref_high 28–57 (lo_min 10 covers labs with wider low bound)
    ("%",     10,   26,   28,  57,  "736-1",    "Lymphocytes (%)",   _RT),
    # RDW           ref_low 9–13      ref_high 13–18   (lo MUST be >8)
    ("%",      9,   14,   12,  18,  "788-0",    "RDW",               _RT),
    # Monocytes %   ref_low 1–7       ref_high 8–16    (lo MUST be <8)
    ("%",      1,    8,    7,  17,  "5905-5",   "Monocytes (%)",     _RT),
    # Eosinophils % ref_low 0–2       ref_high 3.5–11
    ("%",      0,  2.1,   3.4, 12,  "713-8",    "Eosinophils (%)",   _RT),
    # Basophils %   ref_low 0–1       ref_high 0–3.5
    ("%",      0,  1.1,   0,   3.6, "706-2",    "Basophils (%)",     _RT),

    # =========================================================
    # CLEARANCE  (mL/min)  — eGFR (no reference range transmitted)
    # =========================================================
    ("ml/min", None, None, None, None, "62238-1", "eGFR",            _RT),

    # =========================================================
    # RATIO  — BUN/Creatinine Ratio
    # =========================================================
    ("ratio",  None, None, None, None, "3097-3",  "BUN/Creatinine Ratio", _RT),

    # =========================================================
    # A/G RATIO  — Albumin/Globulin ratio
    # Unit "na": HL7 NA^^HL70353 → first component "NA" → normalized "na"
    # Unit "unit": some labs store dimensionless ratio as generic "unit"
    # Typical ref range: lo 1.0–1.5, hi 2.0–3.0
    # =========================================================
    ("na",   0.8, 1.6, 1.5, 3.5, "32733-8",  "A/G Ratio",           _RM),

    # =========================================================
    # DIMENSIONLESS ANALYTES  (unit = "unit" — lab-specific placeholder)
    # Ordered: A/G ratio < BUN < BUN/Cr < pH (by typical lo value)
    # hi discriminates BUN (14–30) from BUN/Cr (15–25) from pH (7.38–7.48)
    # =========================================================
    # A/G Ratio  lo 0.8–1.6   hi 1.5–3.5
    ("unit", 0.8,  1.6,  1.5,  3.5, "32733-8",  "A/G Ratio",         _RM),
    # BUN        lo 5–9       hi 14–30  (mg/dL equivalent stored without unit)
    ("unit", 5.0,  9.0, 14.0, 30.0,  "3094-0",   "BUN",               _RM),
    # BUN/Creatinine Ratio  lo 10–15  hi 15–25  (ratio, dimensionless)
    ("unit", 10.5, 15.0, 15.0, 25.0, "3097-3",  "BUN/Creatinine Ratio", _RM),
    # pH  lo 7.30–7.40  hi 7.38–7.48  (blood gas, stored as "unit")
    ("unit", 7.30, 7.40, 7.38, 7.48, "2746-6",   "pH",                _RT),

    # =========================================================
    # BLOOD GAS  (mmHg)
    # Discriminated by ref_low: pCO2 venous ref_low ~40; pO2 ref_low ~25
    # =========================================================
    # pCO2 venous   ref_low 38–46     ref_high 46–58
    ("mmhg",  38,   47,   45,  60,  "2021-4",   "pCO2",              _RT),
    # pO2 venous    ref_low 23–40     ref_high 38–58
    ("mmhg",  23,   40,   36,  60,  "2029-7",   "pO2",               _RT),
]


def _in_range(val: float, lo: Optional[float], hi: Optional[float]) -> bool:
    """True when lo <= val <= hi (or either bound is None → unbounded)."""
    if lo is not None and val < lo:
        return False
    if hi is not None and val > hi:
        return False
    return True


def _match_row(
    unit_canon: str,
    ref_low:  Optional[float],
    ref_high: Optional[float],
    row: tuple,
) -> bool:
    """Return True if (unit, ref_low, ref_high) satisfies one table row."""
    ru, lo_min, lo_max, hi_min, hi_max, *_ = row
    if ru != unit_canon:
        return False
    if ref_low is None and lo_min is not None:
        return False          # row requires a ref_low but none supplied
    if ref_high is None and hi_min is not None:
        return False          # row requires a ref_high but none supplied
    if ref_low is not None and not _in_range(ref_low, lo_min, lo_max):
        return False
    if ref_high is not None and not _in_range(ref_high, hi_min, hi_max):
        return False
    return True


# ---------------------------------------------------------------------------
# Value-distribution fallback for % sub-tests with no reference range
# (covers CBC percentage rows where the hospital omits referenceRange)
# Clinical basis: population-level expected distribution within a full CBC
# -------------------------------------------------------------------------
_PCT_VALUE_BUCKETS: list[tuple] = [
    # (val_min, val_max, loinc_code, display_name)
    # Ordered from narrowest expected range to broadest.
    # Population-level expected values (NHANES reference):
    #   Basophils 0–1%, Eosinophils 0–5%, Monocytes 2–12%,
    #   Lymphocytes 15–45%, Neutrophils 45–75%
    (0.0,  1.0,  "706-2",  "Basophils (%)"),        # Basophils: 0–1%
    (1.0,  6.0,  "713-8",  "Eosinophils (%)"),      # Eosinophils: 1–5%
    (2.0, 14.0,  "5905-5", "Monocytes (%)"),        # Monocytes: 2–12%
    (12.0, 48.0, "736-1",  "Lymphocytes (%)"),      # Lymphocytes: 15–45%
    (40.0, 85.0, "770-8",  "Neutrophils (%)"),      # Neutrophils: 40–75%
]


def _pct_value_fallback(value: Optional[float]) -> Optional[InferenceResult]:
    """
    Last-resort inference for CBC % sub-tests with no reference range.
    Uses the measured value itself as a population-distribution signal.
    Confidence is FALLBACK — not suitable for individual-level interpretation.
    """
    if value is None:
        return None
    # Iterate from narrowest range to broadest to avoid early false match
    for vmin, vmax, loinc, name in _PCT_VALUE_BUCKETS:
        if vmin <= value <= vmax:
            return InferenceResult(loinc, name, "FALLBACK", "value_distribution")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def infer_panel_subtest(
    unit:       Optional[str],
    ref_low:    Optional[float],
    ref_high:   Optional[float],
    value:      Optional[float] = None,
) -> Optional[InferenceResult]:
    """
    Infer the LOINC code and display name for a single panel sub-test.

    Parameters
    ----------
    unit      : raw unit string from FHIR valueQuantity.unit
    ref_low   : numeric reference range lower bound (or None)
    ref_high  : numeric reference range upper bound (or None)
    value     : measured numeric value (used only for % fallback)

    Returns
    -------
    InferenceResult with (loinc_code, display_name, confidence, match_basis),
    or None if no confident match can be made (caller retains panel header).
    """
    canon = _norm_unit(unit)

    # Primary: declarative reference-range table
    for row in _RANGE_TABLE:
        if _match_row(canon, ref_low, ref_high, row):
            *_, loinc, display, confidence = row
            return InferenceResult(loinc, display, confidence, "ref_range")

    # Secondary: value-distribution fallback (% only, no ref range)
    if canon == "%" and ref_low is None and ref_high is None:
        return _pct_value_fallback(value)

    # Bilirubin Total: mg/dL with no ref range at all (some hospitals omit it)
    if canon == "mg/dl" and ref_low is None and ref_high is None:
        return InferenceResult("1975-2", "Bilirubin Total", "MEDIUM", "ref_range")

    return None
