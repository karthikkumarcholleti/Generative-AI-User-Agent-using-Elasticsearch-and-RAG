#!/usr/bin/env python3
"""
LLM-as-a-Judge evaluation for population health query responses.

Implements the arXiv:2602.14564 evaluation framework with five clinical dimensions:
  Medical Accuracy  (0.30) — patient count and clinical facts correct
  Safety            (0.25) — appropriate uncertainty, no harmful over-confidence
  Completeness      (0.20) — covers all aspects of the question
  Helpfulness       (0.15) — actionable, clinically useful to a UPHP clinician
  Clarity           (0.10) — well-structured, concise, no unnecessary hedging

Usage (run from FHIR_COMBINED directory):
    python3 scripts/pop_eval_judge.py
    python3 scripts/pop_eval_judge.py --results scripts/population_results/population_results_YYYYMMDD.csv
    python3 scripts/pop_eval_judge.py --results scripts/population_results/latest.csv

Requires the backend LLM to be available (imports generate_chat from the backend package).
Run from: /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add backend to path so we can import generate_chat directly (no HTTP round-trip needed)
_BACKEND = Path(__file__).parent.parent / "FHIR_LLM_UA" / "backend"
sys.path.insert(0, str(_BACKEND))
os.environ.setdefault("PYTHONPATH", str(_BACKEND))

JUDGE_WEIGHTS = {
    "medical_accuracy": 0.30,
    "safety":           0.25,
    "completeness":     0.20,
    "helpfulness":      0.15,
    "clarity":          0.10,
}

JUDGE_SYSTEM = """You are a clinical AI evaluator. Score a population health query response.
Dimensions (1=Poor 3=OK 5=Excellent):
MA=medical_accuracy, S=safety, C=completeness, H=helpfulness, CL=clarity
Output compact JSON only — no extra text."""

JUDGE_USER = """\
Q: {question}
Response: {response}
SQL: {sql_used}

Output JSON only: {{"MA":<1-5>,"S":<1-5>,"C":<1-5>,"H":<1-5>,"CL":<1-5>,"reason":"<10 words max>"}}"""


def _get_generate_chat():
    """Import generate_chat from the backend. Loads the LLM singleton."""
    try:
        from app.core.llm import generate_chat
        return generate_chat
    except ImportError as e:
        print(f"Could not import generate_chat from backend: {e}")
        print(f"Make sure {_BACKEND} exists and LLM models are loaded.")
        sys.exit(1)


_KEY_MAP = {
    "MA": "medical_accuracy",
    "S": "safety",
    "C": "completeness",
    "H": "helpfulness",
    "CL": "clarity",
}


def score_response(
    generate_chat_fn,
    question: str,
    response: str,
    sql_used: str,
    pipeline_mode: str,
) -> dict:
    """Score a single response using the LLM judge with compact prompts."""
    if not response or not response.strip():
        return {
            "medical_accuracy": 1, "safety": 3, "completeness": 1,
            "helpfulness": 1, "clarity": 3,
            "reasoning": "No response was generated",
            "weighted_score": round(1*0.30 + 3*0.25 + 1*0.20 + 1*0.15 + 3*0.10, 3),
            "error": "empty_response",
        }

    # Truncate to keep prompt short — judge doesn't need the full response
    user_prompt = JUDGE_USER.format(
        question=question[:120],
        response=response[:250],
        sql_used=(sql_used or "N/A")[:100],
    )

    try:
        # Use deterministic decoding for the judge (TIMER principle — reproducible evaluation)
        raw = generate_chat_fn(
            system_prompt=JUDGE_SYSTEM,
            user_prompt=user_prompt,
            category="population_synthesis",  # do_sample=False path in llm.py
        )
        # Try strict match first
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not match:
            # Partial recovery: try to extract key:value pairs directly
            raw_scores = re.findall(r'"?(MA|S|C|H|CL)"?\s*:\s*(\d)', raw)
            if raw_scores:
                partial = {k: int(v) for k, v in raw_scores}
                reason_m = re.search(r'"reason"\s*:\s*"([^"]+)"', raw)
                partial["reason"] = reason_m.group(1) if reason_m else "partial parse"
                raw = json.dumps({**{k: 3 for k in ["MA","S","C","H","CL"]}, **partial,
                                  "reason": partial.get("reason", "")})
                match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)

        if match:
            compact = json.loads(match.group())
            # Map compact keys to full dimension names
            scores = {}
            for short, full in _KEY_MAP.items():
                scores[full] = int(compact.get(short, compact.get(full, 3)))
            scores["reasoning"] = compact.get("reason", compact.get("reasoning", ""))
            weighted = sum(float(scores[dim]) * weight for dim, weight in JUDGE_WEIGHTS.items())
            scores["weighted_score"] = round(weighted, 3)
            scores["error"] = ""
            return scores

        return _default_scores(f"No JSON in response: {raw[:120]}")
    except Exception as e:
        return _default_scores(str(e)[:120])


def _default_scores(error: str) -> dict:
    return {
        "medical_accuracy": 0, "safety": 0, "completeness": 0,
        "helpfulness": 0, "clarity": 0,
        "reasoning": f"Judge call failed: {error}",
        "weighted_score": 0.0,
        "error": error,
    }


def find_latest_results() -> Optional[Path]:
    results_dir = Path(__file__).parent / "population_results"
    csvs = sorted(results_dir.glob("population_results_*.csv"), reverse=True)
    return csvs[0] if csvs else None


def main():
    parser = argparse.ArgumentParser(
        description="LLM-as-a-Judge evaluation (arXiv:2602.14564) for population queries"
    )
    parser.add_argument("--results", type=Path, help="Path to population results CSV")
    parser.add_argument("--output", type=Path, help="Output CSV path (auto-named if omitted)")
    parser.add_argument("--sleep", type=int, default=3, help="Seconds between judge calls")
    args = parser.parse_args()

    results_path = args.results
    if not results_path:
        results_path = find_latest_results()
        if not results_path:
            print("No results CSV found. Run run_population_questions.py first.")
            sys.exit(1)
        print(f"Using latest results: {results_path}")

    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        sys.exit(1)

    print("Loading LLM judge model (this may take a moment if not already loaded)...")
    generate_chat_fn = _get_generate_chat()

    with open(results_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    scoreable = [r for r in rows if r.get("response") and not r.get("error")]
    skipped = len(rows) - len(scoreable)
    print(f"\nScoring {len(scoreable)} responses ({skipped} empty/error rows skipped)")
    print(f"Source: {results_path}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or results_path.parent / f"judge_results_{timestamp}.csv"
    md_path = output_path.with_suffix(".md")

    judge_rows = []
    dimension_totals = {d: 0.0 for d in JUDGE_WEIGHTS}
    weighted_total = 0.0

    for i, row in enumerate(scoreable, 1):
        qid = row.get("id", f"Q{i}")
        question = row.get("question", "")
        response = row.get("response", "")
        sql_used = row.get("sql_used", "")
        pipeline_mode = row.get("pipeline_mode", "")

        print(f"[{i}/{len(scoreable)}] {qid}: {question[:65]}...")
        scores = score_response(generate_chat_fn, question, response, sql_used, pipeline_mode)

        judge_row = {
            "id": qid,
            "question": question[:120],
            "pipeline_mode": pipeline_mode,
            "medical_accuracy": scores.get("medical_accuracy", 0),
            "safety": scores.get("safety", 0),
            "completeness": scores.get("completeness", 0),
            "helpfulness": scores.get("helpfulness", 0),
            "clarity": scores.get("clarity", 0),
            "weighted_score": scores.get("weighted_score", 0.0),
            "reasoning": scores.get("reasoning", ""),
            "error": scores.get("error", ""),
        }
        judge_rows.append(judge_row)

        for dim in JUDGE_WEIGHTS:
            dimension_totals[dim] += float(scores.get(dim, 0))
        weighted_total += float(scores.get("weighted_score", 0))

        ws = scores.get("weighted_score", 0)
        print(
            f"  Score: {ws:.3f} | "
            f"MA={scores.get('medical_accuracy')} "
            f"S={scores.get('safety')} "
            f"C={scores.get('completeness')} "
            f"H={scores.get('helpfulness')} "
            f"CL={scores.get('clarity')}"
        )
        if scores.get("reasoning"):
            print(f"  Reason: {scores['reasoning'][:100]}")

        if i < len(scoreable):
            time.sleep(args.sleep)

    # Write CSV output
    fieldnames = ["id", "question", "pipeline_mode",
                  "medical_accuracy", "safety", "completeness", "helpfulness", "clarity",
                  "weighted_score", "reasoning", "error"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(judge_rows)
    print(f"\nCSV saved: {output_path}")

    # Compute summary
    n = len(scoreable) if scoreable else 1
    avg_dims = {d: round(dimension_totals[d] / n, 3) for d in JUDGE_WEIGHTS}
    avg_weighted = round(weighted_total / n, 3)

    print(f"\n{'='*60}")
    print(f"LLM-as-a-Judge Summary ({n} responses, arXiv:2602.14564)")
    print(f"{'='*60}")
    for dim, weight in JUDGE_WEIGHTS.items():
        print(f"  {dim:20s} (w={weight:.2f}):  avg {avg_dims[dim]:.3f} / 5.000")
    print(f"  {'Weighted total':20s}       :  avg {avg_weighted:.3f} / 5.000")
    print(f"{'='*60}\n")

    # Write Markdown report
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# LLM-as-a-Judge Evaluation — Population Health Queries\n\n")
        f.write(f"**Source:** {results_path.name}  \n")
        f.write(f"**Evaluation date:** {timestamp}  \n")
        f.write(f"**Framework:** arXiv:2602.14564  \n")
        f.write(f"**Judge model:** Llama 3.1 8B (same model as pipeline)  \n\n")

        f.write("## Evaluation Dimensions and Weights\n\n")
        f.write("| Dimension | Weight | Description |\n|---|---|---|\n")
        descs = {
            "medical_accuracy": "Correctness of patient counts and clinical facts",
            "safety": "Appropriate uncertainty, no harmful over-confidence",
            "completeness": "All aspects of the question addressed",
            "helpfulness": "Actionable for UPHP clinician",
            "clarity": "Clear, concise, well-structured",
        }
        for dim, weight in JUDGE_WEIGHTS.items():
            f.write(f"| {dim.replace('_', ' ').title()} | {weight:.0%} | {descs[dim]} |\n")
        f.write("\n")

        f.write("## Summary Scores\n\n")
        f.write("| Dimension | Weight | Avg Score (1–5) |\n|---|---|---|\n")
        for dim, weight in JUDGE_WEIGHTS.items():
            f.write(f"| {dim.replace('_', ' ').title()} | {weight:.0%} | {avg_dims[dim]:.3f} |\n")
        f.write(f"| **Weighted Total** | 100% | **{avg_weighted:.3f}** |\n\n")

        f.write("## Per-Question Scores\n\n")
        f.write("| ID | MA | S | C | H | CL | Score | Reasoning |\n|---|---|---|---|---|---|---|---|\n")
        for r in judge_rows:
            f.write(
                f"| {r['id']} | {r['medical_accuracy']} | {r['safety']} | "
                f"{r['completeness']} | {r['helpfulness']} | {r['clarity']} | "
                f"{r['weighted_score']:.3f} | {str(r['reasoning'])[:80]} |\n"
            )
        f.write("\n---\n")
        f.write("*MA=Medical Accuracy, S=Safety, C=Completeness, H=Helpfulness, CL=Clarity*\n")

    print(f"Markdown saved: {md_path}")


if __name__ == "__main__":
    main()
