#!/usr/bin/env python3
"""
============================================================
RAG vs MedRAG Comparison Script  (v2 — research-grade)
============================================================
Fixes vs v1:
  P3-A  Randomized execution order per query per run — eliminates
        GPU warm-up / memory-fragmentation bias that systematically
        disadvantaged MedRAG when it always ran second.
  P3-A  Three runs per mode per query; reports median ± IQR
        (not mean) for robustness against single-run outliers.
  P3-B  ROUGE-L: response completeness vs. the other pipeline.
  P3-B  Consistency: ROUGE-L across 3 repeated runs of same query
        (intra-mode reproducibility).
  P3-B  Faithfulness: % of response sentences corroborated by
        at least one retrieved source (keyword-overlap proxy).
  P3-B  Wilcoxon signed-rank test on all paired latency samples.
  P3-E  Separate query sets: DDx-focused (default), generic info
        queries, and adversarial queries where flat RAG may excel.

Usage:
    cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
    python scripts/compare_rag_vs_medrag.py \\
        --patient_id 000000509 \\
        --output_dir scripts/comparison_results \\
        --runs 3 \\
        --query_set ddx          # ddx | generic | adversarial | all

    # Quick single-run smoke test:
    python scripts/compare_rag_vs_medrag.py \\
        --patient_id 000000509 --runs 1 --query_indices 0 1

NOTE: Backend must be running before launching this script.
============================================================
"""

import argparse
import json
import math
import os
import random
import re
import statistics
import sys
import time
import datetime
import requests
from itertools import combinations
from typing import Dict, List, Optional, Tuple

# ── Optional packages (ROUGE-L, Wilcoxon) ────────────────────────────────────
try:
    from rouge_score import rouge_scorer as _rouge_scorer
    _ROUGE_SCORER = _rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    _HAS_ROUGE = True
except ImportError:
    _HAS_ROUGE = False

try:
    from scipy.stats import wilcoxon as _wilcoxon
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
RANDOM_SEED = int(os.getenv("COMPARISON_SEED", "42"))

# ── Query sets ────────────────────────────────────────────────────────────────

DDX_QUERIES: List[str] = [
    "Based on this patient's conditions and observations, what is the most likely diagnosis and what alternatives should be considered?",
    "What do the patient's glucose and HbA1c values indicate about their metabolic status?",
    "Analyze the patient's blood pressure readings and explain what they suggest clinically.",
    "What do the patient's creatinine and kidney-related observations tell us?",
    "Does this patient show signs of cardiovascular disease? What is the supporting evidence?",
    "What are the risk values in this patient's observations that could affect their health?",
    "Summarize this patient's overall health status and highlight the most clinically significant findings.",
]

GENERIC_QUERIES: List[str] = [
    "What is this patient's most recent hemoglobin value?",
    "List all conditions recorded for this patient.",
    "What medications or diagnoses relate to the patient's heart?",
    "When was the patient's last recorded encounter?",
    "What is the patient's date of birth and gender?",
]

ADVERSARIAL_QUERIES: List[str] = [
    "What is the patient's exact sodium value from the most recent lab panel?",
    "List every observation recorded, in chronological order.",
    "Compare the patient's WBC counts across all recorded dates.",
    "What is the numeric value of the patient's eGFR?",
]

_ALL_QUERY_SETS = {
    "ddx":        DDX_QUERIES,
    "generic":    GENERIC_QUERIES,
    "adversarial": ADVERSARIAL_QUERIES,
    "all":        DDX_QUERIES + GENERIC_QUERIES + ADVERSARIAL_QUERIES,
}

# ── Metric helpers ────────────────────────────────────────────────────────────

def _rouge_l(hyp: str, ref: str) -> float:
    """ROUGE-L F1. Falls back to character-LCS ratio if package missing."""
    if not hyp or not ref:
        return 0.0
    if _HAS_ROUGE:
        scores = _ROUGE_SCORER.score(ref, hyp)
        return round(scores["rougeL"].fmeasure, 4)
    # Fallback: LCS length / max(len) as a rough proxy
    a, b = hyp.lower().split(), ref.lower().split()
    m, n = len(a), len(b)
    if m == 0 or n == 0:
        return 0.0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i-1][j-1] + 1 if a[i-1] == b[j-1] else max(dp[i-1][j], dp[i][j-1])
    lcs = dp[m][n]
    prec = lcs / m if m else 0
    rec  = lcs / n if n else 0
    return round(2 * prec * rec / (prec + rec), 4) if (prec + rec) else 0.0


def _iqr(values: List[float]) -> float:
    """Interquartile range."""
    if len(values) < 2:
        return 0.0
    s = sorted(values)
    n = len(s)
    q1 = s[n // 4]
    q3 = s[(3 * n) // 4]
    return round(q3 - q1, 3)


def _consistency(responses: List[str]) -> float:
    """Mean pairwise ROUGE-L across all response pairs from repeated runs."""
    pairs = list(combinations(responses, 2))
    if not pairs:
        return 1.0
    return round(statistics.mean(_rouge_l(a, b) for a, b in pairs), 4)


_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might shall can this that these those "
    "and or but not for in on at to of with from by about as".split()
)

# ── Faithfulness metric — 3-class sentence classification ────────────────────
# Class A (groundable facts): sentence has numeric lab value OR retrieved condition
#   name → forms the denominator; must cite [O-N] or [C-N] to be counted as grounded
# Class B (abstentions): "not present / not found / absent" → excluded from denominator
# Class C (reasoning / transitions): pure interpretation, no numeric anchor → excluded

_ABSTENTION = re.compile(
    r"(not present|not available|no .{0,40}(found|recorded|retrieved|present)|absent|not in the retrieved)",
    re.IGNORECASE,
)
_SPECULATIVE = re.compile(
    r"\b(may|might|could|possibly|perhaps|likely|probably)\b",
    re.IGNORECASE,
)
_CITATION = re.compile(r"\[O-\d+\]|\[C-\d+\]")
_NUMERIC_VALUE = re.compile(
    r"\b\d+\.?\d*\s*(mg/dl|mmol/l|g/dl|bpm|mmhg|meq/l|ng/ml|pg/ml|u/l|iu/l|%|µiu/ml|x10\^3)\b",
    re.IGNORECASE,
)


def _build_condition_pattern(sources: list):
    """Dynamically extract condition names from retrieved [C-N] sources."""
    names: set = set()
    for s in sources:
        if s.get("type") in ("condition", "conditions"):
            desc = s.get("description", "")
            raw = desc.split("|")[0]
            name = re.sub(r"(?i)condition\s*:", "", raw).strip().lower()
            if name and len(name) > 3:
                names.add(name)
                for word in name.split():
                    if len(word) >= 5:
                        names.add(word)
    if not names:
        return None
    pattern = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(pattern, re.IGNORECASE)


def _faithfulness(response: str, sources: List[Dict]) -> float:
    """
    Claim-level grounding metric (3-class sentence classification).

    Class A = sentence with numeric lab value OR retrieved condition name (dynamic).
    Class B (abstentions) and Class C (reasoning) are excluded from the denominator.
    Grounded = Class A sentence that contains an [O-N] or [C-N] citation.
    Returns grounded / len(class_A), or 0.0 if no Class A sentences exist.
    """
    if not response or not sources:
        return 0.0
    condition_pattern = _build_condition_pattern(sources)
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", response) if len(s.strip()) > 15]
    if not sentences:
        return 0.0

    class_a = []
    for s in sentences:
        if _ABSTENTION.search(s):
            continue  # Class B — excluded
        is_speculative = bool(_SPECULATIVE.search(s))
        has_numeric = bool(_NUMERIC_VALUE.search(s))
        has_condition = bool(condition_pattern and condition_pattern.search(s))
        has_citation = bool(_CITATION.search(s))
        if is_speculative and not has_numeric and not has_citation:
            continue  # Class C — speculative without concrete anchor
        if has_numeric or has_condition or (has_citation and not is_speculative):
            class_a.append(s)  # Class A — groundable fact
        # else: pure reasoning / transition → Class C, excluded

    if not class_a:
        return 0.0

    grounded = sum(1 for s in class_a if _CITATION.search(s))
    return round(grounded / len(class_a), 4)


# ── Grounded recall — query-relevant citation coverage ───────────────────────

_OBS_QUERY_TERMS = {
    "glucose":       ["glucose", "blood sugar", "2345-7", "27353-2"],
    "hba1c":         ["hba1c", "hemoglobin a1c", "4548-4", "17856-6"],
    "creatinine":    ["creatinine", "2160-0"],
    "bun":           ["bun", "blood urea nitrogen", "3094-0"],
    "egfr":          ["egfr", "glomerular filtration", "33914-3"],
    "cholesterol":   ["cholesterol", "2093-3", "2085-9", "2089-1"],
    "hemoglobin":    ["hemoglobin", "718-7"],
    "potassium":     ["potassium", "2823-3"],
    "sodium":        ["sodium", "2951-2"],
    "troponin":      ["troponin", "10839-9"],
    "bnp":           ["bnp", "brain natriuretic", "42637-9"],
    "tsh":           ["tsh", "thyroid", "3016-3"],
    "blood pressure":["blood pressure", "systolic", "diastolic", "55284-4"],
    "heart rate":    ["heart rate", "pulse", "8867-4"],
}


def _get_query_relevant_sources(sources: list, query: str) -> list:
    """
    Structured relevance first, keyword fallback.
    1. Check if query mentions known observation terms → match by display/code/content
    2. Check if query asks about conditions → match [C-N] sources by condition name
    3. Fallback: keyword overlap between query and source description
    """
    query_lower = query.lower()
    relevant = []

    # Step 1: structured observation matching
    matched_obs_terms: list = []
    for canonical, variants in _OBS_QUERY_TERMS.items():
        if any(v in query_lower for v in variants + [canonical]):
            matched_obs_terms.extend(variants)

    if matched_obs_terms:
        for s in sources:
            desc = (s.get("description", "") + " " + s.get("content", "")).lower()
            if any(t in desc for t in matched_obs_terms):
                relevant.append(s)

    # Step 2: condition name matching
    condition_kws = ["condition", "diagnosis", "diagnos", "disease", "disorder"]
    if any(kw in query_lower for kw in condition_kws):
        for s in sources:
            if s.get("type") in ("condition", "conditions"):
                relevant.append(s)

    # Step 3: keyword fallback if structured matching found nothing
    if not relevant:
        query_keywords = set(re.findall(r'\b[a-z]{4,}\b', query_lower)) - _STOPWORDS
        relevant = [
            s for s in sources
            if any(kw in (s.get("description", "") + s.get("content", "")).lower()
                   for kw in query_keywords)
        ]

    # Deduplicate by description
    seen_descs: set = set()
    deduped = []
    for s in relevant:
        k = s.get("description", "")
        if k not in seen_descs:
            seen_descs.add(k)
            deduped.append(s)
    return deduped


def _grounded_recall(response: str, sources: list, query: str) -> float:
    """
    Fraction of query-relevant retrieved items cited in the response.
    Denominator = query-relevant sources (structured matching, then keyword fallback).
    Numerator = unique [O-N]/[C-N] labels cited in the response.
    """
    query_relevant = _get_query_relevant_sources(sources, query)
    if not query_relevant:
        return 0.0
    cited_count = len(set(re.findall(r'\[(?:O|C)-\d+\]', response)))
    return round(min(cited_count / len(query_relevant), 1.0), 4)


# KG candidate diseases from DIAGNOSTIC_KG — used for DDx coverage metric
_KG_DISEASE_NAMES = [
    "Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus", "Steroid-Induced Hyperglycemia",
    "Essential Hypertension", "Secondary Hypertension", "Resistant Hypertension",
    "Congestive Heart Failure", "Coronary Artery Disease", "Atrial Fibrillation",
    "Chronic Kidney Disease", "CKD", "Acute Kidney Injury", "AKI", "Diabetic Nephropathy",
    "Hypertensive Nephrosclerosis", "Iron Deficiency Anemia", "Anemia of Chronic Disease",
    "B12/Folate Deficiency Anemia", "Hypothyroidism", "Hyperthyroidism",
    "Chronic Obstructive Pulmonary Disease", "COPD", "Asthma",
    "Major Depressive Disorder", "Generalized Anxiety Disorder",
    "Alzheimer", "Dementia", "Hypercholesterolemia",
]
_KG_DISEASE_PATTERN = re.compile(
    "|".join(re.escape(d) for d in sorted(_KG_DISEASE_NAMES, key=len, reverse=True)),
    re.IGNORECASE
)

# DDx intent keywords — mirrors rag_service.py logic so we can flag per-query
_DDX_KWS = [
    "differential diagnosis", "differential", "ddx", "most likely diagnosis",
    "what is the diagnosis", "possible diagnos", "probable diagnos",
    "overall assessment", "clinical assessment", "clinical summary",
    "health status", "signs of cardiovascular", "signs of kidney",
    "signs of diabetes", "signs of heart", "evidence of", "risk of",
    "show signs of", "does this patient",
]
_VALUE_OVERRIDES = [
    "what do the", "what does the", "what do ", "what does ",
    "tell me the", "show me the", "list the", "give me the",
    "what are the values", "what are the levels", "what are the results",
    "how high is", "how low is", "how does", "compare",
    "normal range for", "reference range for",
]


def _kg_fires(query: str) -> bool:
    """Mirrors rag_service.py _apply_ddx_early — True when KG pipeline would run."""
    q = query.lower()
    has_ddx = any(kw in q for kw in _DDX_KWS)
    is_value = any(kw in q for kw in _VALUE_OVERRIDES)
    return has_ddx and not is_value


def _ddx_coverage(response: str) -> float:
    """
    Fraction of KG disease names mentioned in the response.
    MedRAG should score higher than RAG because the KG context steers the LLM
    to name specific disease candidates it might otherwise skip.
    Not a grounding metric — just measures breadth of clinical vocabulary used.
    """
    if not response:
        return 0.0
    mentioned = set(m.group(0).lower() for m in _KG_DISEASE_PATTERN.finditer(response))
    return round(len(mentioned) / len(_KG_DISEASE_NAMES), 4)


def _wilcoxon_test(rag_vals: List[float], medrag_vals: List[float]) -> Dict:
    """
    Wilcoxon signed-rank test on paired (rag, medrag) latency samples.
    Requires at least 5 paired observations (ideally ≥10).
    """
    result = {
        "n_pairs": len(rag_vals),
        "statistic": None,
        "p_value": None,
        "significant_at_05": None,
        "note": "",
    }
    if not _HAS_SCIPY:
        result["note"] = "scipy not installed — install with: pip install scipy"
        return result
    if len(rag_vals) < 5 or len(rag_vals) != len(medrag_vals):
        result["note"] = f"Need ≥5 paired observations; got {len(rag_vals)}"
        return result
    diffs = [r - m for r, m in zip(rag_vals, medrag_vals)]
    if all(d == 0 for d in diffs):
        result["note"] = "All differences are zero — cannot compute test"
        return result
    try:
        stat, p = _wilcoxon(rag_vals, medrag_vals, alternative="two-sided")
        result["statistic"] = round(float(stat), 4)
        result["p_value"]   = round(float(p), 6)
        result["significant_at_05"] = bool(p < 0.05)
        result["note"] = "Wilcoxon signed-rank test (two-sided) on paired latency samples"
    except Exception as exc:
        result["note"] = f"Test failed: {exc}"
    return result


# ── Backend interaction ───────────────────────────────────────────────────────

def check_backend() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"  Backend healthy: status={data.get('status')}, db={data.get('db')}")
            return True
        print(f"  Backend returned HTTP {r.status_code}")
        return False
    except Exception as e:
        print(f"  Cannot reach backend at {BASE_URL}: {e}")
        return False


def set_medrag_mode(enabled: bool) -> bool:
    try:
        r = requests.post(
            f"{BASE_URL}/chat-agent/compare/set-mode",
            json={"use_medrag": enabled},
            timeout=10,
        )
        if r.status_code == 200:
            return True
    except Exception:
        pass
    # File-based fallback
    path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), "..",
        "FHIR_LLM_UA", "backend", "app", "api", "rag_service.py"
    ))
    try:
        text = open(path).read()
        new_text = text.replace(
            f"USE_MEDRAG = {'False' if enabled else 'True'}",
            f"USE_MEDRAG = {'True' if enabled else 'False'}",
        )
        if new_text == text:
            return True  # already correct
        open(path, "w").write(new_text)
        print(f"  rag_service.py updated — restart backend and press ENTER to continue...")
        input()
        return True
    except Exception as e:
        print(f"  Could not toggle mode: {e}")
        return False


def run_single_query(patient_id: str, query: str, mode_label: str) -> Dict:
    """Execute one query against the backend and return a result dict."""
    start = time.time()
    try:
        r = requests.post(
            f"{BASE_URL}/chat-agent/query",
            json={"patient_id": patient_id, "query": query},
            timeout=600,
        )
        elapsed = round(time.time() - start, 3)
        if r.status_code == 200:
            data = r.json()
            return {
                "mode": mode_label,
                "query": query,
                "response": data.get("response", ""),
                "elapsed_seconds": elapsed,
                "retrieved_count": data.get("retrieved_count", 0),
                "sources": data.get("sources", []),
                "has_chart": data.get("chart") is not None,
                "intent_type": data.get("intent", {}).get("type", "unknown"),
                "pipeline_mode_confirmed": data.get("pipeline_mode", mode_label),
                "error": None,
            }
        return {"mode": mode_label, "query": query, "response": "",
                "elapsed_seconds": elapsed, "retrieved_count": 0,
                "sources": [], "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"mode": mode_label, "query": query, "response": "",
                "elapsed_seconds": round(time.time() - start, 3),
                "retrieved_count": 0, "sources": [], "error": str(e)}


# ── Core comparison logic ─────────────────────────────────────────────────────

def run_comparison(
    patient_id: str,
    queries: List[str],
    runs_per_mode: int,
    rng: random.Random,
    verbose: bool = True,
) -> List[Dict]:
    """
    For each query, execute `runs_per_mode` rounds.
    In each round, randomly choose which pipeline (RAG or MedRAG) runs first,
    toggle the mode, execute, toggle again, execute. This interleaved design
    controls for GPU warm-up and memory fragmentation bias.

    Returns a list of per-query result dicts.
    """
    query_results = []

    for q_idx, query in enumerate(queries):
        if verbose:
            short_q = query[:70] + "..." if len(query) > 70 else query
            print(f"\n  Query {q_idx + 1}/{len(queries)}: {short_q}")

        rag_runs: List[Dict] = []
        medrag_runs: List[Dict] = []

        for run_num in range(1, runs_per_mode + 1):
            order = rng.choice(["rag_first", "medrag_first"])
            if verbose:
                print(f"    Run {run_num}/{runs_per_mode} [order={order}]")

            if order == "rag_first":
                set_medrag_mode(False); time.sleep(1)
                r1 = run_single_query(patient_id, query, "Standard RAG")
                r1["execution_order"] = 1
                if verbose:
                    print(f"      RAG    : {r1['elapsed_seconds']}s | {len(r1['response'])} chars"
                          + (f" | ERR: {r1['error']}" if r1['error'] else ""))
                set_medrag_mode(True); time.sleep(1)
                r2 = run_single_query(patient_id, query, "MedRAG + KG")
                r2["execution_order"] = 2
                if verbose:
                    print(f"      MedRAG : {r2['elapsed_seconds']}s | {len(r2['response'])} chars"
                          + (f" | ERR: {r2['error']}" if r2['error'] else ""))
                rag_runs.append(r1)
                medrag_runs.append(r2)
            else:
                set_medrag_mode(True); time.sleep(1)
                r1 = run_single_query(patient_id, query, "MedRAG + KG")
                r1["execution_order"] = 1
                if verbose:
                    print(f"      MedRAG : {r1['elapsed_seconds']}s | {len(r1['response'])} chars"
                          + (f" | ERR: {r1['error']}" if r1['error'] else ""))
                set_medrag_mode(False); time.sleep(1)
                r2 = run_single_query(patient_id, query, "Standard RAG")
                r2["execution_order"] = 2
                if verbose:
                    print(f"      RAG    : {r2['elapsed_seconds']}s | {len(r2['response'])} chars"
                          + (f" | ERR: {r2['error']}" if r2['error'] else ""))
                medrag_runs.append(r1)
                rag_runs.append(r2)

        # ── Per-query metrics ─────────────────────────────────────────────────
        rag_latencies    = [r["elapsed_seconds"] for r in rag_runs    if not r.get("error")]
        medrag_latencies = [r["elapsed_seconds"] for r in medrag_runs if not r.get("error")]

        rag_responses    = [r["response"] for r in rag_runs    if r.get("response")]
        medrag_responses = [r["response"] for r in medrag_runs if r.get("response")]

        # Representative response = run with median latency (or first if only 1)
        def _median_response(runs: List[Dict]) -> str:
            valid = [r for r in runs if r.get("response") and not r.get("error")]
            if not valid:
                return ""
            if len(valid) == 1:
                return valid[0]["response"]
            sorted_r = sorted(valid, key=lambda x: x["elapsed_seconds"])
            return sorted_r[len(sorted_r) // 2]["response"]

        rag_repr    = _median_response(rag_runs)
        medrag_repr = _median_response(medrag_runs)

        # All sources from all runs, deduplicated
        all_rag_sources    = []
        all_medrag_sources = []
        seen = set()
        for r in rag_runs:
            for s in r.get("sources", []):
                k = s.get("description", "")
                if k not in seen:
                    seen.add(k); all_rag_sources.append(s)
        seen = set()
        for r in medrag_runs:
            for s in r.get("sources", []):
                k = s.get("description", "")
                if k not in seen:
                    seen.add(k); all_medrag_sources.append(s)

        kg_fired = _kg_fires(query)
        metrics = {
            "kg_fired": kg_fired,
            "latency": {
                "standard_rag": {
                    "median":  round(statistics.median(rag_latencies), 3)    if rag_latencies    else None,
                    "iqr":     _iqr(rag_latencies),
                    "values":  rag_latencies,
                },
                "medrag_kg": {
                    "median":  round(statistics.median(medrag_latencies), 3) if medrag_latencies else None,
                    "iqr":     _iqr(medrag_latencies),
                    "values":  medrag_latencies,
                },
            },
            "rouge_l_vs_each_other": _rouge_l(rag_repr, medrag_repr),
            "consistency": {
                "standard_rag": _consistency(rag_responses),
                "medrag_kg":    _consistency(medrag_responses),
            },
            "faithfulness": {
                "standard_rag": _faithfulness(rag_repr, all_rag_sources),
                "medrag_kg":    _faithfulness(medrag_repr, all_medrag_sources),
            },
            "grounded_recall": {
                "standard_rag": _grounded_recall(rag_repr, all_rag_sources, query),
                "medrag_kg":    _grounded_recall(medrag_repr, all_medrag_sources, query),
            },
            "ddx_coverage": {
                "standard_rag": _ddx_coverage(rag_repr),
                "medrag_kg":    _ddx_coverage(medrag_repr),
                "note": "Fraction of KG disease names mentioned — MedRAG should score higher on DDx queries",
            },
        }

        if verbose:
            m = metrics
            kg_label = "[KG ACTIVE]" if kg_fired else "[KG skipped]"
            print(f"    {kg_label}")
            print(f"    Latency  — RAG: {m['latency']['standard_rag']['median']}s "
                  f"± {m['latency']['standard_rag']['iqr']} IQR  |  "
                  f"MedRAG: {m['latency']['medrag_kg']['median']}s "
                  f"± {m['latency']['medrag_kg']['iqr']} IQR")
            print(f"    ROUGE-L (RAG↔MedRAG): {m['rouge_l_vs_each_other']}")
            print(f"    Consistency  — RAG: {m['consistency']['standard_rag']}  "
                  f"MedRAG: {m['consistency']['medrag_kg']}")
            print(f"    Faithfulness — RAG: {m['faithfulness']['standard_rag']}  "
                  f"MedRAG: {m['faithfulness']['medrag_kg']}")
            print(f"    Grnd.Recall  — RAG: {m['grounded_recall']['standard_rag']}  "
                  f"MedRAG: {m['grounded_recall']['medrag_kg']}")
            print(f"    DDx Coverage — RAG: {m['ddx_coverage']['standard_rag']}  "
                  f"MedRAG: {m['ddx_coverage']['medrag_kg']}")

        query_results.append({
            "query_index": q_idx,
            "query": query,
            "runs": {
                "standard_rag": rag_runs,
                "medrag_kg":    medrag_runs,
            },
            "representative_responses": {
                "standard_rag": rag_repr,
                "medrag_kg":    medrag_repr,
            },
            "metrics": metrics,
        })

    return query_results


# ── Global statistics ─────────────────────────────────────────────────────────

def compute_global_stats(query_results: List[Dict]) -> Dict:
    """Pool all paired latency samples and run statistical tests."""
    all_rag_latencies    = []
    all_medrag_latencies = []
    rouge_l_scores       = []
    consistency_rag      = []
    consistency_medrag   = []
    faithfulness_rag     = []
    faithfulness_medrag  = []
    grounded_recall_rag    = []
    grounded_recall_medrag = []
    ddx_coverage_rag       = []
    ddx_coverage_medrag    = []
    kg_fired_count         = 0

    for qr in query_results:
        m = qr["metrics"]
        rag_vals    = m["latency"]["standard_rag"]["values"]
        medrag_vals = m["latency"]["medrag_kg"]["values"]
        for rv, mv in zip(rag_vals, medrag_vals):
            all_rag_latencies.append(rv)
            all_medrag_latencies.append(mv)

        if m["rouge_l_vs_each_other"] is not None:
            rouge_l_scores.append(m["rouge_l_vs_each_other"])
        if m["consistency"]["standard_rag"] is not None:
            consistency_rag.append(m["consistency"]["standard_rag"])
        if m["consistency"]["medrag_kg"] is not None:
            consistency_medrag.append(m["consistency"]["medrag_kg"])
        if m["faithfulness"]["standard_rag"] is not None:
            faithfulness_rag.append(m["faithfulness"]["standard_rag"])
        if m["faithfulness"]["medrag_kg"] is not None:
            faithfulness_medrag.append(m["faithfulness"]["medrag_kg"])
        if m.get("grounded_recall", {}).get("standard_rag") is not None:
            grounded_recall_rag.append(m["grounded_recall"]["standard_rag"])
        if m.get("grounded_recall", {}).get("medrag_kg") is not None:
            grounded_recall_medrag.append(m["grounded_recall"]["medrag_kg"])
        if m.get("ddx_coverage", {}).get("standard_rag") is not None:
            ddx_coverage_rag.append(m["ddx_coverage"]["standard_rag"])
        if m.get("ddx_coverage", {}).get("medrag_kg") is not None:
            ddx_coverage_medrag.append(m["ddx_coverage"]["medrag_kg"])
        if m.get("kg_fired"):
            kg_fired_count += 1

    wilcoxon = _wilcoxon_test(all_rag_latencies, all_medrag_latencies)

    def _safe_mean(lst):
        return round(statistics.mean(lst), 4) if lst else None

    return {
        "wilcoxon_latency": wilcoxon,
        "n_paired_samples": len(all_rag_latencies),
        "overall_latency": {
            "standard_rag_median": round(statistics.median(all_rag_latencies), 3) if all_rag_latencies else None,
            "medrag_kg_median":    round(statistics.median(all_medrag_latencies), 3) if all_medrag_latencies else None,
        },
        "mean_rouge_l":                  _safe_mean(rouge_l_scores),
        "mean_consistency_rag":          _safe_mean(consistency_rag),
        "mean_consistency_medrag":       _safe_mean(consistency_medrag),
        "mean_faithfulness_rag":         _safe_mean(faithfulness_rag),
        "mean_faithfulness_medrag":      _safe_mean(faithfulness_medrag),
        "mean_grounded_recall_rag":      _safe_mean(grounded_recall_rag),
        "mean_grounded_recall_medrag":   _safe_mean(grounded_recall_medrag),
        "mean_ddx_coverage_rag":         _safe_mean(ddx_coverage_rag),
        "mean_ddx_coverage_medrag":      _safe_mean(ddx_coverage_medrag),
        "kg_fired_count":                kg_fired_count,
        "kg_fired_pct":                  round(kg_fired_count / max(len(query_results), 1), 4),
    }


# ── Markdown report ───────────────────────────────────────────────────────────

def build_markdown_report(
    patient_id: str,
    query_results: List[Dict],
    global_stats: Dict,
    runs_per_mode: int,
    seed: int,
) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    lines += [
        "# RAG vs MedRAG Comparison Report (v2 — Research Grade)",
        "",
        f"**Patient ID:** `{patient_id}`  ",
        f"**Generated:** {now}  ",
        f"**Queries:** {len(query_results)}  ",
        f"**Runs per mode per query:** {runs_per_mode}  ",
        f"**Random seed:** `{seed}`  ",
        f"**Execution order:** randomized per run (controls GPU warm-up bias)  ",
        "",
        "---",
        "",
        "## Global Statistics",
        "",
        "### Latency (seconds) — all runs pooled",
        "",
        f"| | Median | Note |",
        f"|---|---|---|",
    ]

    ol = global_stats["overall_latency"]
    lines.append(f"| Standard RAG  | {ol['standard_rag_median']} s | |")
    lines.append(f"| MedRAG + KG   | {ol['medrag_kg_median']} s  | |")
    lines.append("")

    wil = global_stats["wilcoxon_latency"]
    if wil.get("p_value") is not None:
        sig = "YES (p < 0.05)" if wil["significant_at_05"] else "NO (p ≥ 0.05)"
        lines += [
            "### Wilcoxon Signed-Rank Test (paired latency)",
            "",
            f"- N paired samples: {wil['n_pairs']}",
            f"- Statistic: {wil['statistic']}",
            f"- p-value: {wil['p_value']}",
            f"- Significant at α=0.05: **{sig}**",
            f"- _{wil['note']}_",
            "",
        ]
    else:
        lines += [
            "### Wilcoxon Signed-Rank Test",
            f"- _{wil.get('note', 'Not computed')}_",
            "",
        ]

    lines += [
        "### Response Quality Metrics (mean across all queries)",
        "",
        "| Metric | Standard RAG | MedRAG + KG | Interpretation |",
        "|---|---|---|---|",
        f"| ROUGE-L (RAG↔MedRAG) | {global_stats['mean_rouge_l']} | — | 1.0 = identical responses |",
        f"| Consistency (intra-mode) | {global_stats['mean_consistency_rag']} | {global_stats['mean_consistency_medrag']} | ROUGE-L across repeated runs |",
        f"| DDx Coverage | {global_stats['mean_ddx_coverage_rag']} | {global_stats['mean_ddx_coverage_medrag']} | KG disease names mentioned (MedRAG should be higher) |",
        f"| Faithfulness ([O-N]/[C-N]) | {global_stats['mean_faithfulness_rag']} | {global_stats['mean_faithfulness_medrag']} | fraction of Class A claims with citation |",
        f"| Grounded Recall | {global_stats['mean_grounded_recall_rag']} | {global_stats['mean_grounded_recall_medrag']} | query-relevant sources cited in response |",
        "",
        "> **Faithfulness:** 3-class sentence classification. Class A = sentences with numeric",
        "> lab values or retrieved condition names. Faithfulness = fraction of Class A sentences",
        "> that contain an [O-N] or [C-N] citation label. Class B (abstentions) and Class C",
        "> (reasoning) are excluded from the denominator. Clinician annotation is gold standard.",
        "",
        "---",
        "",
        "## Per-Query Results",
        "",
    ]

    for qr in query_results:
        q = qr["query"]
        m = qr["metrics"]
        i = qr["query_index"]
        rag_repr    = qr["representative_responses"]["standard_rag"]
        medrag_repr = qr["representative_responses"]["medrag_kg"]

        rag_lat  = m["latency"]["standard_rag"]
        med_lat  = m["latency"]["medrag_kg"]

        lines += [
            f"### Query {i+1}",
            "",
            f"> {q}",
            "",
            "**Latency (seconds):**",
            "",
            "| | Median | IQR | All values |",
            "|---|---|---|---|",
            f"| Standard RAG  | {rag_lat['median']} | {rag_lat['iqr']} | {rag_lat['values']} |",
            f"| MedRAG + KG   | {med_lat['median']} | {med_lat['iqr']} | {med_lat['values']} |",
            "",
            "**Response quality:**",
            "",
            "| Metric | Standard RAG | MedRAG + KG |",
            "|---|---|---|",
            f"| Consistency    | {m['consistency']['standard_rag']} | {m['consistency']['medrag_kg']} |",
            f"| Faithfulness   | {m['faithfulness']['standard_rag']} | {m['faithfulness']['medrag_kg']} |",
            f"| Grnd. Recall   | {m.get('grounded_recall', {}).get('standard_rag', 'n/a')} | {m.get('grounded_recall', {}).get('medrag_kg', 'n/a')} |",
            f"| ROUGE-L (vs. other pipeline) | {m['rouge_l_vs_each_other']} | ← same pair |",
            "",
            "**Standard RAG response** _(median-latency run)_:",
            "",
            rag_repr or "_No response_",
            "",
            "**MedRAG + KG response** _(median-latency run)_:",
            "",
            medrag_repr or "_No response_",
            "",
            "---",
            "",
        ]

    lines += [
        "## Methodological Notes (for paper Methods section)",
        "",
        "1. **Execution order:** For each run of each query, the pipeline order",
        "   (RAG-first vs. MedRAG-first) was chosen uniformly at random to prevent",
        f"   GPU warm-up bias. Seed: `{seed}`.",
        "",
        f"2. **Repetitions:** Each query was run {runs_per_mode}× per pipeline.",
        "   Median latency (not mean) is reported; IQR characterises variability.",
        "",
        "3. **ROUGE-L:** Computed between the median-run response of Standard RAG",
        "   and MedRAG for the same query. Lower scores indicate greater divergence",
        "   in response content (expected for DDx queries).",
        "",
        "4. **Consistency:** Pairwise ROUGE-L across all repeated runs of the same",
        "   query+pipeline combination. A score of 1.0 indicates identical outputs",
        "   across runs; lower scores indicate non-determinism.",
        "",
        "5. **Faithfulness:** Fraction of response sentences (>20 chars) where at",
        "   least 2 content words (≥4 chars, non-stopword) appear in the retrieved",
        "   source descriptions. Proxy metric — not NLI-based entailment.",
        "",
        "6. **Statistical test:** Wilcoxon signed-rank test (two-sided) on all",
        f"   {global_stats['n_paired_samples']} paired (RAG, MedRAG) latency samples.",
        "   Non-parametric; appropriate for small, non-normal latency distributions.",
        "",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Research-grade RAG vs MedRAG comparison with randomized order, "
                    "3× repetition, and ROUGE-L / Wilcoxon / faithfulness metrics."
    )
    parser.add_argument("--patient_id", required=True)
    parser.add_argument("--output_dir", default="scripts/comparison_results")
    parser.add_argument("--runs", type=int, default=3,
                        help="Runs per mode per query (default: 3; use 1 for quick smoke test)")
    parser.add_argument("--query_set", default="ddx",
                        choices=list(_ALL_QUERY_SETS.keys()),
                        help="Which query set to use (default: ddx)")
    parser.add_argument("--query_indices", nargs="*", type=int, default=None,
                        help="Zero-based indices into the selected query set")
    parser.add_argument("--custom_queries", nargs="*", default=None)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED,
                        help=f"Random seed for execution-order randomization (default: {RANDOM_SEED})")
    parser.add_argument("--backend_url", default=None)
    parser.add_argument("--quiet", action="store_true", help="Suppress per-run output")
    args = parser.parse_args()

    global BASE_URL
    if args.backend_url:
        BASE_URL = args.backend_url

    rng = random.Random(args.seed)

    # Resolve query list
    if args.custom_queries:
        queries = args.custom_queries
    else:
        pool = _ALL_QUERY_SETS[args.query_set]
        if args.query_indices is not None:
            queries = [pool[i] for i in args.query_indices if i < len(pool)]
        else:
            queries = pool

    if not queries:
        print("No queries selected. Check --query_indices or --custom_queries.")
        sys.exit(1)

    output_dir = (
        os.path.join(os.path.dirname(__file__), "..", args.output_dir)
        if not os.path.isabs(args.output_dir) else args.output_dir
    )
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("  RAG vs MedRAG Comparison — Research Grade")
    print("=" * 70)
    print(f"  Patient      : {args.patient_id}")
    print(f"  Query set    : {args.query_set} ({len(queries)} queries)")
    print(f"  Runs/mode    : {args.runs}")
    print(f"  Total calls  : {len(queries) * args.runs * 2}")
    print(f"  Random seed  : {args.seed}")
    print(f"  Output dir   : {output_dir}")
    print("=" * 70)

    if not check_backend():
        sys.exit(1)

    print(f"\nRunning comparison (randomized order, {args.runs} runs/mode)...")
    query_results = run_comparison(
        patient_id=args.patient_id,
        queries=queries,
        runs_per_mode=args.runs,
        rng=rng,
        verbose=not args.quiet,
    )

    global_stats = compute_global_stats(query_results)

    # ── Save outputs ──────────────────────────────────────────────────────────
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    json_data = {
        "metadata": {
            "patient_id":  args.patient_id,
            "generated_at": timestamp,
            "backend_url":  BASE_URL,
            "query_set":    args.query_set,
            "query_count":  len(queries),
            "runs_per_mode": args.runs,
            "random_seed":  args.seed,
            "rouge_available":   _HAS_ROUGE,
            "scipy_available":   _HAS_SCIPY,
        },
        "global_stats": global_stats,
        "query_results": query_results,
    }
    json_path = os.path.join(output_dir, f"comparison_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"\n  JSON saved : {json_path}")

    md_report = build_markdown_report(
        args.patient_id, query_results, global_stats, args.runs, args.seed
    )
    md_path = os.path.join(output_dir, f"comparison_{timestamp}.md")
    with open(md_path, "w") as f:
        f.write(md_report)
    print(f"  Markdown   : {md_path}")

    # ── Terminal summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    gs = global_stats
    ol = gs["overall_latency"]
    print(f"  Latency  — RAG median: {ol['standard_rag_median']}s  "
          f"MedRAG median: {ol['medrag_kg_median']}s")
    wil = gs["wilcoxon_latency"]
    if wil.get("p_value") is not None:
        print(f"  Wilcoxon p={wil['p_value']}  "
              f"significant={'YES' if wil['significant_at_05'] else 'NO'} (n={wil['n_pairs']} pairs)")
    print(f"  Mean ROUGE-L (RAG vs MedRAG): {gs['mean_rouge_l']}")
    print(f"  Mean consistency — RAG: {gs['mean_consistency_rag']}  "
          f"MedRAG: {gs['mean_consistency_medrag']}")
    print(f"  Mean faithfulness — RAG: {gs['mean_faithfulness_rag']}  "
          f"MedRAG: {gs['mean_faithfulness_medrag']}")
    print(f"  Mean grnd.recall — RAG: {gs['mean_grounded_recall_rag']}  "
          f"MedRAG: {gs['mean_grounded_recall_medrag']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
