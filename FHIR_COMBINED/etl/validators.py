"""
Plausibility checks for observation values before DB insertion.
Implausible values are quarantined, never silently dropped.
Thresholds match REFERENCE_RANGES in visualization_service.py (single source of truth principle).
"""

from decimal import Decimal, InvalidOperation

# (low_cutoff, high_cutoff) — values outside these ranges are physiologically impossible
_PLAUSIBILITY: dict[str, tuple[float, float]] = {
    # Lipids (mg/dL)
    "2093-3":   (10,  700),    # Cholesterol total
    "2085-9":   (10,  300),    # HDL
    "2089-1":   (10,  500),    # LDL
    "2571-8":   (10, 2000),    # Triglycerides
    # Metabolic
    "2160-0":   (0.05, 30),    # Creatinine (exclude if < 0.05 to allow eGFR ratios)
    "2345-7":   (0.5, 1500),   # Glucose
    "6299-2":   (1,   200),    # BUN
    # CBC
    "718-7":    (1,   25),     # Hemoglobin (exclude A1c ranges)
    "789-8":    (0.5, 15),     # RBC (M/uL)
    "777-3":    (20, 3000),    # Platelets (K/uL)
    "6690-2":   (0.1, 100),    # WBC (K/uL)
    # Vitals
    "8480-6":   (40,  280),    # Systolic BP (mmHg)
    "8462-4":   (20,  180),    # Diastolic BP (mmHg)
    "8867-4":   (20,  300),    # Heart rate (bpm)
    "59408-5":  (50,  100),    # O2 saturation (%)
    "8310-5":   (32,   45),    # Body temp (°C)
    "8302-2":   (50,  280),    # Height (cm)
    "29463-7":  (10,  500),    # Weight (kg)
}


def check_plausibility(code: str, value_numeric) -> tuple[bool, str | None]:
    """
    Returns (is_plausible: bool, error_detail: str | None).
    Values not in _PLAUSIBILITY are assumed plausible (no threshold defined).
    """
    if code not in _PLAUSIBILITY or value_numeric is None:
        return True, None
    try:
        v = float(value_numeric)
    except (TypeError, ValueError):
        return True, None  # non-numeric — not our job here

    low, high = _PLAUSIBILITY[code]
    if v < low or v > high:
        return False, f"value {v} outside plausible range [{low}, {high}] for LOINC {code}"
    return True, None


def parse_decimal(raw) -> Decimal | None:
    """Safely parse a value to Decimal, returning None on failure."""
    if raw is None:
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None
