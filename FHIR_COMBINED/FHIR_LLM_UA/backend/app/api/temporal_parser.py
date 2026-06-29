"""
Deterministic temporal constraint extractor for population health queries.

Based on TIMER (arXiv:2503.04176): LLMs systematically fail at temporal reasoning.
This module converts natural language time expressions to SQL fragments without LLM involvement.

Returns a TemporalConstraint dict consumed by population_query_service.py.
"""

import re
from typing import Optional


def extract_temporal_constraints(query: str) -> dict:
    """
    Parse temporal expressions from a natural language clinical query.

    Returns:
        {
          "date_filter":  str | None   — SQL fragment for WHERE clause, e.g. ">= DATE_SUB(NOW(), INTERVAL 2 YEAR)"
          "negation":     bool         — True when question asks about ABSENCE ("no documented", "without")
          "recency":      bool         — True when "most recent" / "latest" phrasing is present
          "years":        int | None   — numeric year window extracted (used by caller for display)
          "months":       int | None   — numeric month window extracted
          "days":         int | None   — numeric day window extracted
          "age_filter":   str | None   — SQL fragment for patient age, e.g. "DATEDIFF(NOW(), birth_date)/365 > 65"
          "age_min":      int | None
          "age_max":      int | None
          "consecutive_days": int | None  — for "more than N consecutive days" queries
        }
    """
    q = query.lower()

    result = {
        "date_filter": None,
        "negation": False,
        "recency": False,
        "years": None,
        "months": None,
        "days": None,
        "age_filter": None,
        "age_min": None,
        "age_max": None,
        "consecutive_days": None,
    }

    # ── Negation / absence detection ─────────────────────────────────────
    negation_patterns = [
        r"\bno documented\b",
        r"\bnot documented\b",
        r"\bno recorded\b",
        r"\bwithout\b",
        r"\bno .{0,20} on record\b",
        r"\bno .{0,20} in their record\b",
        r"\bno .{0,20} diagnosis\b",
        r"\bnot been diagnosed\b",
        r"\bnever diagnosed\b",
        r"\bhave not been\b",
        r"\bhas not been\b",
        r"\bhave no\b",
        r"\bhas no\b",
        r"\bnot on\b",
        r"\bwithout a\b",
    ]
    for pat in negation_patterns:
        if re.search(pat, q):
            result["negation"] = True
            break

    # ── Recency ──────────────────────────────────────────────────────────
    if re.search(r"\b(most recent|latest|last recorded|current)\b", q):
        result["recency"] = True

    # ── Time windows ─────────────────────────────────────────────────────
    # "past N year(s)" / "last N year(s)"
    m = re.search(r"\b(?:past|last|previous|in the past)\s+(\d+)\s+years?\b", q)
    if m:
        n = int(m.group(1))
        result["years"] = n
        result["date_filter"] = f">= DATE_SUB(NOW(), INTERVAL {n} YEAR)"

    # "past N month(s)" / "last N month(s)"
    m = re.search(r"\b(?:past|last|previous|in the past)\s+(\d+)\s+months?\b", q)
    if m:
        n = int(m.group(1))
        result["months"] = n
        result["date_filter"] = f">= DATE_SUB(NOW(), INTERVAL {n} MONTH)"

    # "past N day(s)" / "within N day(s)"
    m = re.search(r"\b(?:past|last|within|in the past)\s+(\d+)\s+days?\b", q)
    if m:
        n = int(m.group(1))
        result["days"] = n
        result["date_filter"] = f">= DATE_SUB(NOW(), INTERVAL {n} DAY)"

    # "within N day(s) of discharge" (transition of care pattern)
    m = re.search(r"within\s+(\d+)\s+days?\s+of\b", q)
    if m:
        n = int(m.group(1))
        result["days"] = n
        result["date_filter"] = f">= DATE_SUB(NOW(), INTERVAL {n} DAY)"

    # "more than N consecutive days"
    m = re.search(r"more than\s+(\d+)\s+consecutive\s+days?\b", q)
    if m:
        result["consecutive_days"] = int(m.group(1))

    # "for more than N year(s)" (duration, not window) — treat as window
    m = re.search(r"for more than\s+(\d+)\s+years?\b", q)
    if m and result["date_filter"] is None:
        n = int(m.group(1))
        result["years"] = n
        result["date_filter"] = f">= DATE_SUB(NOW(), INTERVAL {n} YEAR)"

    # "in the past year" / "over the past year" (no number)
    if result["date_filter"] is None and re.search(r"\b(in the past year|over the past year|in the last year)\b", q):
        result["years"] = 1
        result["date_filter"] = ">= DATE_SUB(NOW(), INTERVAL 1 YEAR)"

    # "in the past 10 years" already caught above; "past decade" edge case
    if result["date_filter"] is None and re.search(r"\bpast decade\b", q):
        result["years"] = 10
        result["date_filter"] = ">= DATE_SUB(NOW(), INTERVAL 10 YEAR)"

    # ── Age filters ───────────────────────────────────────────────────────
    # "over N" / "older than N" / "above N" / "> N"
    m = re.search(r"\b(?:over|older than|above|aged?\s*>)\s*(\d+)\b", q)
    if m:
        n = int(m.group(1))
        result["age_min"] = n
        result["age_filter"] = f"TIMESTAMPDIFF(YEAR, birth_date, NOW()) > {n}"

    # "aged N–M" / "aged N to M" / "between N and M"
    m = re.search(r"\baged?\s+(\d+)\s*(?:–|-|to)\s*(\d+)\b", q)
    if not m:
        m = re.search(r"\bbetween\s+(\d+)\s+and\s+(\d+)\b", q)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        result["age_min"] = lo
        result["age_max"] = hi
        result["age_filter"] = f"TIMESTAMPDIFF(YEAR, birth_date, NOW()) BETWEEN {lo} AND {hi}"

    # "under N" / "younger than N" / "< N years old"
    m = re.search(r"\b(?:under|younger than|below)\s+(\d+)\b", q)
    if m and result["age_filter"] is None:
        n = int(m.group(1))
        result["age_max"] = n
        result["age_filter"] = f"TIMESTAMPDIFF(YEAR, birth_date, NOW()) < {n}"

    return result
