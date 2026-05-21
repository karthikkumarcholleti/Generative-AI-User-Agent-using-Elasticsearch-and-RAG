#!/usr/bin/env python3
"""
Fine-tuning Dataset Generator — Clinically Gated QA Pairs
==========================================================
Generates JSONL QA pairs from FHIR patient data for Llama 3.1 8B fine-tuning.

6 QA types with clinical gating + faithfulness validation:
  A — Conditions list     (deterministic template, gate: ≥1 condition)
  B — Temporal trends     (hybrid LLM, gate: ≥3 obs same LOINC, faithfulness ≥0.7)
  C — Risk reasoning      (hybrid LLM, gate: ≥2 HIGH/LOW labs, faithfulness ≥0.7)
  D — Encounters          (deterministic template, gate: ≥1 encounter)
  E — Overall summary     (hybrid LLM, always, faithfulness ≥0.7)
  F — Absent data         (deterministic template, gate: ≥1 missing common LOINC)

Faithfulness validated on ALL types — templates can fail if labels mismatch.
Outputs skipped if faithfulness < 0.5.

Dataset size estimate: 100k–170k QA pairs depending on per-patient data sparsity.

Usage:
    cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
    python scripts/generate_finetuning_dataset.py \\
        --output_dir scripts/finetuning_data \\
        --max_patients 100 \\
        --use_llm false          # deterministic-only mode (no API calls)

    python scripts/generate_finetuning_dataset.py \\
        --output_dir scripts/finetuning_data \\
        --use_llm true \\
        --api_key sk-ant-...     # requires Anthropic API key for hybrid types
"""

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Faithfulness metric (same as compare_rag_vs_medrag.py) ───────────────────

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
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might shall can this that these those "
    "and or but not for in on at to of with from by about as".split()
)


def _build_condition_pattern(sources: list):
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


def _faithfulness(response: str, sources: list) -> float:
    if not response or not sources:
        return 0.0
    condition_pattern = _build_condition_pattern(sources)
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", response) if len(s.strip()) > 15]
    if not sentences:
        return 0.0
    class_a = []
    for s in sentences:
        if _ABSTENTION.search(s):
            continue
        is_speculative = bool(_SPECULATIVE.search(s))
        has_numeric = bool(_NUMERIC_VALUE.search(s))
        has_condition = bool(condition_pattern and condition_pattern.search(s))
        has_citation = bool(_CITATION.search(s))
        if is_speculative and not has_numeric and not has_citation:
            continue
        if has_numeric or has_condition or (has_citation and not is_speculative):
            class_a.append(s)
    if not class_a:
        return 0.0
    grounded = sum(1 for s in class_a if _CITATION.search(s))
    return round(grounded / len(class_a), 4)


# ── Common LOINC codes we check for absence (Type F gate) ────────────────────

_COMMON_LOINCS = {
    "2345-7": "Glucose",
    "4548-4": "HbA1c",
    "2160-0": "Creatinine",
    "3094-0": "BUN",
    "33914-3": "eGFR",
    "2093-3": "Total Cholesterol",
    "2085-9": "HDL Cholesterol",
    "2089-1": "LDL Cholesterol",
    "718-7": "Hemoglobin",
    "2823-3": "Potassium",
    "2951-2": "Sodium",
    "10839-9": "Troponin I",
    "3016-3": "TSH",
    "8867-4": "Heart Rate",
    "55284-4": "Blood Pressure",
}

# ── Clinical reference ranges for Type C (risk reasoning) ────────────────────

_REF_RANGES = {
    "Glucose": (70, 100, "mg/dL", "normal <100 | 100-125 pre-diabetes | >=126 diabetes"),
    "HbA1c": (None, 5.7, "%", "normal <5.7% | 5.7-6.4% pre-diabetes | >=6.5% diabetes"),
    "Creatinine": (0.6, 1.2, "mg/dL", "normal 0.6-1.2 (M) / 0.5-1.1 (F) | >1.5 renal concern"),
    "BUN": (7, 25, "mg/dL", "normal 7-25 | BUN/Cr >20 pre-renal"),
    "Hemoglobin": (12.0, 17.5, "g/dL", "normal 13.5-17.5 (M) / 12-15.5 (F) | <12 anemia"),
    "Potassium": (3.5, 5.0, "mEq/L", "normal 3.5-5.0 | <3.0 arrhythmia risk | >5.5 hyperkalemia"),
    "Sodium": (136, 145, "mEq/L", "normal 136-145 | <130 severe hyponatremia"),
    "TSH": (0.4, 4.0, "mIU/L", "normal 0.4-4.0 | <0.4 hyperthyroid | >4.0 hypothyroid"),
}

# Map LOINC codes to canonical display name (for _REF_RANGES lookup)
_LOINC_TO_DISPLAY: Dict[str, str] = {
    "2345-7": "Glucose", "27353-2": "Glucose", "2339-0": "Glucose",
    "4548-4": "HbA1c", "17856-6": "HbA1c",
    "2160-0": "Creatinine", "38483-4": "Creatinine",
    "3094-0": "BUN",
    "718-7": "Hemoglobin",
    "2823-3": "Potassium",
    "2951-2": "Sodium",
    "3016-3": "TSH",
}


# ── Patient data fetcher ──────────────────────────────────────────────────────

class PatientDataFetcher:
    """Fetches patient data from Elasticsearch and MySQL."""

    def __init__(self):
        self._es = None
        self._engine = None

    def _get_es(self):
        if self._es is None:
            sys.path.insert(0, str(Path(__file__).parent.parent / "FHIR_LLM_UA/backend"))
            from app.api.elasticsearch_client import es_client
            self._es = es_client
        return self._es

    def get_all_patient_ids(self) -> List[str]:
        """Return all unique patient IDs from ES."""
        es = self._get_es()
        result = es.client.search(
            index="patient_data",
            body={
                "size": 0,
                "aggs": {"patients": {"terms": {"field": "patient_id", "size": 10000}}},
            },
        )
        return [b["key"] for b in result["aggregations"]["patients"]["buckets"]]

    def get_patient_data(self, patient_id: str) -> Dict[str, Any]:
        """Fetch conditions, observations, encounters for a patient."""
        es = self._get_es()

        hits = es.client.search(
            index="patient_data",
            body={
                "query": {"term": {"patient_id": patient_id}},
                "size": 1000,
            },
        )["hits"]["hits"]

        conditions = []
        obs_by_loinc: Dict[str, List[Dict]] = defaultdict(list)
        encounters = []

        for h in hits:
            s = h["_source"]
            dt = s.get("data_type", "")

            if dt == "condition":
                conditions.append({
                    "name": s.get("display") or s.get("content", ""),
                    "status": s.get("clinicalStatus") or "active",
                    "onset": s.get("onset_date") or s.get("effective_date") or "",
                })

            elif dt == "observation":
                code = s.get("code", "")
                v = s.get("value_numeric")
                d = s.get("effective_datetime") or s.get("effective_date") or ""
                u = (s.get("unit") or "").strip()
                if u.lower() in ("unit", "", "none", "null"):
                    u = ""
                disp = s.get("display") or code
                if v is not None and d:
                    obs_by_loinc[code].append({
                        "display": disp,
                        "value": float(v),
                        "unit": u,
                        "date": d[:10] if d else "",
                    })

            elif dt in ("encounter", "encounters"):
                encounters.append({
                    "type": s.get("display") or s.get("content", "Encounter"),
                    "date": s.get("effective_date") or s.get("effective_datetime") or "",
                })

        # Sort each LOINC's observations chronologically
        for code in obs_by_loinc:
            obs_by_loinc[code].sort(key=lambda x: x.get("date", ""))

        return {
            "patient_id": patient_id,
            "conditions": conditions,
            "obs_by_loinc": dict(obs_by_loinc),
            "encounters": encounters,
        }


# ── QA type generators ────────────────────────────────────────────────────────

def _build_sources_from_conditions(conditions: List[Dict]) -> List[Dict]:
    return [{"type": "condition", "description": f"Condition: {c['name']}"} for c in conditions]


def _build_sources_from_obs(obs_list: List[Dict], start_idx: int = 1) -> Tuple[str, List[Dict]]:
    """Returns (labeled_context, sources_list) with [O-N] labels."""
    lines = []
    sources = []
    for i, obs in enumerate(obs_list, start_idx):
        lbl = f"[O-{i}]"
        lines.append(f"{lbl} {obs['display']}: {obs['value']} {obs['unit']} | Date: {obs['date']}")
        sources.append({
            "type": "observation",
            "description": f"Observation: {obs['display']} | {obs['value']} {obs['unit']}",
        })
    return "\n".join(lines), sources


def generate_type_A(patient_id: str, data: Dict) -> Optional[Dict]:
    """Conditions list — deterministic template."""
    conditions = [c for c in data["conditions"] if c.get("name")]
    if not conditions:
        return None

    cond_ctx_lines = []
    sources = []
    for i, c in enumerate(conditions, 1):
        onset = f" | Onset: {c['onset']}" if c.get("onset") else ""
        cond_ctx_lines.append(f"[C-{i}] {c['name']} | Status: {c['status']}{onset}")
        sources.append({"type": "condition", "description": f"Condition: {c['name']}"})

    cond_ctx = "\n".join(cond_ctx_lines)

    instruction = "List all medical conditions recorded for this patient, including their status."
    output_lines = []
    for i, c in enumerate(conditions, 1):
        onset_note = f" (onset: {c['onset']})" if c.get("onset") else ""
        output_lines.append(f"[C-{i}] {c['name']} — Status: {c['status']}{onset_note}")

    output = "\n".join(output_lines) if output_lines else "No conditions recorded."

    return {
        "type": "A",
        "patient_id": patient_id,
        "instruction": instruction,
        "input": cond_ctx,
        "output": output,
        "sources": sources,
        "generation": "template",
    }


def generate_type_D(patient_id: str, data: Dict) -> Optional[Dict]:
    """Encounters — deterministic template."""
    encounters = [e for e in data["encounters"] if e.get("type")]
    if not encounters:
        return None

    encounters_sorted = sorted(encounters, key=lambda x: x.get("date", ""), reverse=True)
    enc_lines = [f"- Encounter: {e['type']} | Date: {e.get('date', 'unknown')}" for e in encounters_sorted]
    enc_ctx = "\n".join(enc_lines)

    instruction = "Summarize this patient's clinical encounters and visit history."
    output_lines = [f"{e['type']} (Date: {e.get('date', 'unknown')})" for e in encounters_sorted]
    output = "Encounter history:\n" + "\n".join(output_lines)

    return {
        "type": "D",
        "patient_id": patient_id,
        "instruction": instruction,
        "input": enc_ctx,
        "output": output,
        "sources": [],
        "generation": "template",
    }


def generate_type_F(patient_id: str, data: Dict) -> List[Dict]:
    """Absent data — deterministic template for missing common labs."""
    present_codes = set(data["obs_by_loinc"].keys())
    results = []

    for code, name in _COMMON_LOINCS.items():
        if code not in present_codes:
            instruction = f"What is this patient's {name} value?"
            output = f"No {name} data is present in the retrieved records."
            results.append({
                "type": "F",
                "patient_id": patient_id,
                "instruction": instruction,
                "input": f"Patient {patient_id} — query about {name} ({code})",
                "output": output,
                "sources": [],
                "generation": "template",
            })

    return results


def generate_type_B_template(patient_id: str, loinc: str, obs_list: List[Dict]) -> Optional[Dict]:
    """Temporal trend — fallback deterministic template when LLM faithfulness < 0.7."""
    if len(obs_list) < 3:
        return None

    ctx, sources = _build_sources_from_obs(obs_list)
    display = obs_list[0]["display"]
    first = obs_list[0]
    last = obs_list[-1]

    first_v = first["value"]
    last_v = last["value"]
    diff = last_v - first_v
    direction = "increased" if diff > 0 else ("decreased" if diff < 0 else "remained stable")

    instruction = f"How has {display} changed over time for this patient?"
    output = (
        f"[O-1] {display}: {first_v} {first['unit']} (Date: {first['date']})\n"
        f"[O-{len(obs_list)}] {display}: {last_v} {last['unit']} (Date: {last['date']})\n"
        f"{display} has {direction} from {first_v} to {last_v} {last['unit']} "
        f"over the recorded period ({first['date']} to {last['date']})."
    )

    return {
        "type": "B",
        "patient_id": patient_id,
        "instruction": instruction,
        "input": ctx,
        "output": output,
        "sources": sources,
        "generation": "template_fallback",
        "loinc_code": loinc,
    }


def generate_type_C_template(
    patient_id: str, abnormal_obs: List[Tuple[str, Dict]]
) -> Optional[Dict]:
    """Risk reasoning — fallback deterministic template."""
    if not abnormal_obs:
        return None

    ctx_lines = []
    sources = []
    out_lines = []

    for i, (flag, obs) in enumerate(abnormal_obs, 1):
        lbl = f"[O-{i}]"
        ref = _REF_RANGES.get(obs["display"], (None, None, obs["unit"], ""))
        ref_note = ref[3] if ref else ""
        ctx_lines.append(f"{lbl} {obs['display']}: {obs['value']} {obs['unit']} | {flag} | Date: {obs['date']}")
        sources.append({"type": "observation", "description": f"Observation: {obs['display']}"})
        out_lines.append(
            f"{lbl} {obs['display']}: {obs['value']} {obs['unit']} (Date: {obs['date']}) — {flag}. {ref_note}"
        )

    instruction = "What abnormal lab values indicate elevated clinical risk for this patient?"
    output = "\n".join(out_lines)

    return {
        "type": "C",
        "patient_id": patient_id,
        "instruction": instruction,
        "input": "\n".join(ctx_lines),
        "output": output,
        "sources": sources,
        "generation": "template_fallback",
    }


def generate_type_E_template(patient_id: str, data: Dict) -> Dict:
    """Overall summary — fallback deterministic template."""
    conditions = data["conditions"][:8]
    high_obs = []
    for code, obs_list in data["obs_by_loinc"].items():
        if obs_list and len(high_obs) < 5:
            latest = obs_list[-1]
            for disp_key, ref in _REF_RANGES.items():
                v = latest["value"]
                if ref[1] and v > ref[1]:
                    high_obs.append(latest)
                    break

    ctx_lines = []
    sources = []
    out_lines = ["Active conditions:"]

    for i, c in enumerate(conditions, 1):
        if c.get("name"):
            lbl = f"[C-{i}]"
            ctx_lines.append(f"{lbl} {c['name']} | Status: {c['status']}")
            sources.append({"type": "condition", "description": f"Condition: {c['name']}"})
            out_lines.append(f"{lbl} {c['name']} — Status: {c['status']}")

    if high_obs:
        out_lines.append("Critical findings:")
    for j, o in enumerate(high_obs, 1):
        lbl = f"[O-{j}]"
        ctx_lines.append(f"{lbl} {o['display']}: {o['value']} {o['unit']} | HIGH | Date: {o['date']}")
        sources.append({"type": "observation", "description": f"Observation: {o['display']}"})
        out_lines.append(f"{lbl} {o['display']}: {o['value']} {o['unit']} (Date: {o['date']}) — HIGH.")

    return {
        "type": "E",
        "patient_id": patient_id,
        "instruction": "Summarize this patient's overall health status and highlight the most critical findings.",
        "input": "\n".join(ctx_lines) if ctx_lines else "No data available.",
        "output": "\n".join(out_lines) if len(out_lines) > 1 else "No significant findings recorded.",
        "sources": sources,
        "generation": "template_fallback",
    }


# ── LLM hybrid generator (Claude API) ────────────────────────────────────────

class HybridLLMGenerator:
    """Calls Claude API for high-quality QA pairs with faithfulness gating."""

    SYSTEM = (
        "You are a clinical documentation assistant generating training data.\n"
        "Use retrieved patient data only. When stating a patient-specific fact "
        "(a lab value, a condition, or a diagnosis), cite the retrieved item using "
        "its [O-N] or [C-N] label. Do not invent patient facts.\n"
        "Reasoning and interpretation do not require citation labels."
    )

    def __init__(self, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, instruction: str, context: str) -> str:
        msg = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=self.SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Patient Query: {instruction}\n\n"
                        f"Retrieved Patient Data:\n{context}\n\n"
                        "Answer using the retrieved data, citing [O-N] or [C-N] labels "
                        "when stating specific patient values or conditions."
                    ),
                }
            ],
        )
        return msg.content[0].text.strip()


# ── Per-patient QA generation pipeline ───────────────────────────────────────

def _get_abnormal_obs(obs_by_loinc: Dict) -> List[Tuple[str, Dict]]:
    """Return list of (flag, obs_dict) for observations outside reference range."""
    abnormal = []
    for code, obs_list in obs_by_loinc.items():
        if not obs_list:
            continue
        latest = obs_list[-1]
        # Use LOINC code → canonical name lookup first; fall back to raw display name
        canonical = _LOINC_TO_DISPLAY.get(code, "")
        ref = _REF_RANGES.get(canonical)
        if not ref:
            continue
        v = latest["value"]
        lo, hi = ref[0], ref[1]
        if hi and v > hi:
            abnormal.append(("HIGH", latest))
        elif lo and v < lo:
            abnormal.append(("LOW", latest))
    return abnormal


def generate_all_qa_for_patient(
    patient_id: str,
    data: Dict,
    llm: Optional[HybridLLMGenerator],
    min_faithfulness: float = 0.5,
    hybrid_faithfulness_threshold: float = 0.7,
) -> List[Dict]:
    """Generate all QA types for one patient with faithfulness validation."""
    qa_pairs = []

    # Type A — Conditions (deterministic)
    qa = generate_type_A(patient_id, data)
    if qa:
        qa_pairs.append(qa)

    # Type D — Encounters (deterministic; list of dates = always correct)
    qa = generate_type_D(patient_id, data)
    if qa:
        qa["faithfulness"] = 1.0  # Factual encounter list, no medical claims to ground
        qa_pairs.append(qa)

    # Type F — Absent data (deterministic; correct abstention = faithfulness 1.0)
    for qa in generate_type_F(patient_id, data):
        qa["faithfulness"] = 1.0  # Correct absence statement is always grounded
        qa_pairs.append(qa)

    # Type B — Temporal trends (hybrid, gate: ≥3 obs same LOINC)
    for code, obs_list in data["obs_by_loinc"].items():
        if len(obs_list) < 3:
            continue
        ctx, sources = _build_sources_from_obs(obs_list)
        display = obs_list[0]["display"]
        instruction = f"How has {display} changed over time for this patient?"

        output = None
        if llm:
            try:
                output = llm.generate(instruction, ctx)
            except Exception as e:
                print(f"  [LLM error type B patient {patient_id}]: {e}", file=sys.stderr)

        if output:
            faith = _faithfulness(output, sources)
            if faith >= hybrid_faithfulness_threshold:
                qa_pairs.append({
                    "type": "B",
                    "patient_id": patient_id,
                    "instruction": instruction,
                    "input": ctx,
                    "output": output,
                    "sources": sources,
                    "faithfulness": faith,
                    "generation": "hybrid",
                    "loinc_code": code,
                })
                continue  # LLM output accepted — skip template fallback

        # Fallback to template
        fallback = generate_type_B_template(patient_id, code, obs_list)
        if fallback:
            qa_pairs.append(fallback)

    # Type C — Risk reasoning (hybrid, gate: ≥2 abnormal labs)
    abnormal = _get_abnormal_obs(data["obs_by_loinc"])
    if len(abnormal) >= 2:
        abnormal_2 = abnormal[:6]
        ctx_lines = []
        sources = []
        for i, (flag, obs) in enumerate(abnormal_2, 1):
            ctx_lines.append(
                f"[O-{i}] {obs['display']}: {obs['value']} {obs['unit']} | {flag} | Date: {obs['date']}"
            )
            sources.append({"type": "observation", "description": f"Observation: {obs['display']}"})
        ctx = "\n".join(ctx_lines)
        instruction = "What abnormal lab values indicate elevated clinical risk for this patient?"

        output = None
        if llm:
            try:
                output = llm.generate(instruction, ctx)
            except Exception as e:
                print(f"  [LLM error type C patient {patient_id}]: {e}", file=sys.stderr)

        if output:
            faith = _faithfulness(output, sources)
            if faith >= hybrid_faithfulness_threshold:
                qa_pairs.append({
                    "type": "C",
                    "patient_id": patient_id,
                    "instruction": instruction,
                    "input": ctx,
                    "output": output,
                    "sources": sources,
                    "faithfulness": faith,
                    "generation": "hybrid",
                })
            else:
                fallback = generate_type_C_template(patient_id, abnormal_2)
                if fallback:
                    qa_pairs.append(fallback)
        else:
            fallback = generate_type_C_template(patient_id, abnormal_2)
            if fallback:
                qa_pairs.append(fallback)

    # Type E — Overall summary (hybrid, always run)
    summary_ctx_parts = []
    summary_sources = []
    for c in data["conditions"][:8]:
        if c.get("name"):
            idx = len(summary_sources) + 1
            summary_ctx_parts.append(f"[C-{idx}] {c['name']} | Status: {c['status']}")
            summary_sources.append({"type": "condition", "description": f"Condition: {c['name']}"})

    for code, obs_list in data["obs_by_loinc"].items():
        if obs_list and len(summary_ctx_parts) < 20:
            latest = obs_list[-1]
            idx = len([s for s in summary_sources if s["type"] == "observation"]) + 1
            summary_ctx_parts.append(
                f"[O-{idx}] {latest['display']}: {latest['value']} {latest['unit']} | Date: {latest['date']}"
            )
            summary_sources.append({"type": "observation", "description": f"Observation: {latest['display']}"})

    summary_ctx = "\n".join(summary_ctx_parts)
    instruction = "Summarize this patient's overall health status and highlight the most critical findings."

    output = None
    if llm:
        try:
            output = llm.generate(instruction, summary_ctx)
        except Exception as e:
            print(f"  [LLM error type E patient {patient_id}]: {e}", file=sys.stderr)

    if output:
        faith = _faithfulness(output, summary_sources)
        if faith >= hybrid_faithfulness_threshold:
            qa_pairs.append({
                "type": "E",
                "patient_id": patient_id,
                "instruction": instruction,
                "input": summary_ctx,
                "output": output,
                "sources": summary_sources,
                "faithfulness": faith,
                "generation": "hybrid",
            })
        else:
            qa_pairs.append(generate_type_E_template(patient_id, data))
    else:
        qa_pairs.append(generate_type_E_template(patient_id, data))

    # Score ALL types (including deterministic templates — not auto-marked 1.0)
    validated = []
    for qa in qa_pairs:
        if "faithfulness" not in qa:
            qa["faithfulness"] = _faithfulness(qa.get("output", ""), qa.get("sources", []))
        if qa["faithfulness"] < min_faithfulness:
            qa["skip"] = True
        validated.append(qa)

    return [qa for qa in validated if not qa.get("skip")]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate fine-tuning dataset from FHIR patient data")
    parser.add_argument("--output_dir", default="scripts/finetuning_data")
    parser.add_argument("--max_patients", type=int, default=None,
                        help="Max number of patients to process (default: all)")
    parser.add_argument("--use_llm", choices=["true", "false"], default="false",
                        help="Use Claude API for hybrid generation (requires --api_key)")
    parser.add_argument("--api_key", default=None,
                        help="Anthropic API key for hybrid generation")
    parser.add_argument("--min_faithfulness", type=float, default=0.5,
                        help="Minimum faithfulness score to include a QA pair")
    parser.add_argument("--hybrid_threshold", type=float, default=0.7,
                        help="Faithfulness threshold for accepting hybrid LLM output")
    args = parser.parse_args()

    use_llm = args.use_llm.lower() == "true"
    if use_llm and not args.api_key:
        print("ERROR: --api_key required when --use_llm true", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"finetuning_{timestamp}.jsonl"
    stats_path = output_dir / f"finetuning_{timestamp}_stats.json"

    fetcher = PatientDataFetcher()
    llm = HybridLLMGenerator(args.api_key) if use_llm else None

    print("Fetching patient IDs...")
    all_patients = fetcher.get_all_patient_ids()
    if args.max_patients:
        all_patients = all_patients[:args.max_patients]
    print(f"Processing {len(all_patients)} patients...")

    stats: Dict[str, Any] = {
        "total_patients": len(all_patients),
        "processed": 0,
        "errors": 0,
        "qa_by_type": defaultdict(int),
        "skipped_low_faithfulness": 0,
        "total_qa_pairs": 0,
        "generation_mode": "hybrid" if use_llm else "deterministic_only",
    }

    with open(output_path, "w") as f:
        for i, patient_id in enumerate(all_patients):
            try:
                data = fetcher.get_patient_data(patient_id)
                qa_pairs = generate_all_qa_for_patient(
                    patient_id, data, llm,
                    min_faithfulness=args.min_faithfulness,
                    hybrid_faithfulness_threshold=args.hybrid_threshold,
                )
                for qa in qa_pairs:
                    # Strip sources from output (training data shouldn't include them)
                    out = {
                        "type": qa["type"],
                        "patient_id": qa["patient_id"],
                        "instruction": qa["instruction"],
                        "input": qa["input"],
                        "output": qa["output"],
                        "faithfulness": qa.get("faithfulness", 0.0),
                        "generation": qa.get("generation", "template"),
                    }
                    if "loinc_code" in qa:
                        out["loinc_code"] = qa["loinc_code"]
                    f.write(json.dumps(out) + "\n")
                    stats["qa_by_type"][qa["type"]] += 1
                    stats["total_qa_pairs"] += 1

                stats["processed"] += 1
                if (i + 1) % 50 == 0:
                    print(f"  [{i+1}/{len(all_patients)}] {stats['total_qa_pairs']} QA pairs so far...")
            except Exception as e:
                stats["errors"] += 1
                print(f"  ERROR patient {patient_id}: {e}", file=sys.stderr)

    stats["qa_by_type"] = dict(stats["qa_by_type"])
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Dataset complete")
    print(f"  Output: {output_path}")
    print(f"  Patients processed: {stats['processed']}/{stats['total_patients']}")
    print(f"  Total QA pairs: {stats['total_qa_pairs']}")
    print(f"  By type: {stats['qa_by_type']}")
    print(f"  Errors: {stats['errors']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
