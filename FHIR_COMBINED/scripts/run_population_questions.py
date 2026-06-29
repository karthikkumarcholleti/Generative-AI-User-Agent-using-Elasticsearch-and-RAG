#!/usr/bin/env python3
"""
Run 25 population-level questions against the 12-patient cohort.

Architecture: Ziletti & D'Ambrosi (2025) two-step RAG + text-to-SQL
  Step 1 — MedRAG KG concept expansion + schema context (ontology retrieval)
  Step 2 — LLM intent extraction → Python parameterized SQL → MySQL
  Temporal reasoning — deterministic temporal_parser.py (TIMER arXiv:2503.04176)

Usage:
    python3 scripts/run_population_questions.py
    python3 scripts/run_population_questions.py --mode all      # all 25 questions (default)
    python3 scripts/run_population_questions.py --mode data     # only questions with data_available=true
    python3 scripts/run_population_questions.py --mode single --id POP9

Output:
    scripts/population_results/population_results_YYYYMMDD_HHMMSS.csv
    scripts/population_results/population_results_YYYYMMDD_HHMMSS.md
"""

import argparse
import csv
import json
import time
import sys
from datetime import datetime
from pathlib import Path

import requests

# ── Configuration ────────────────────────────────────────────────────────────

API_BASE = "http://localhost:8001"
POPULATION_ENDPOINT = f"{API_BASE}/chat-agent/population-query"
QUESTIONS_FILE = Path(__file__).parent / "population_questions.json"
OUTPUT_DIR = Path(__file__).parent / "population_results"

# The 12 evaluation patients (enterprise_patient_ids from llm_ua_enterprise)
COHORT_PATIENT_IDS = [
    "000000061",  # Dominic Webb
    "000000055",  # Christian Dean
    "000000052",  # Brooklyn Coleman
    "000000048",  # Lincoln Gray
    "000000041",  # Isaac Hernandez
    "127",        # Scarlett Gonzalez
    "000000026",  # Samuel Richardson
    "000000008",  # Charlotte White
    "000000007",  # Mia Scott
    "000000005",  # Amelia Parker
    "000000004",  # Isabella Martin
    "000000003",  # Mason Lewis
]

COHORT_NAMES = {
    "000000061": "Dominic Webb",
    "000000055": "Christian Dean",
    "000000052": "Brooklyn Coleman",
    "000000048": "Lincoln Gray",
    "000000041": "Isaac Hernandez",
    "127":        "Scarlett Gonzalez",
    "000000026": "Samuel Richardson",
    "000000008": "Charlotte White",
    "000000007": "Mia Scott",
    "000000005": "Amelia Parker",
    "000000004": "Isabella Martin",
    "000000003": "Mason Lewis",
}

SLEEP_BETWEEN_QUESTIONS = 3  # seconds — GPU breathing room


# ── Helpers ──────────────────────────────────────────────────────────────────

def check_backend():
    """Verify backend is running before starting."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        if r.status_code == 200:
            print(f"✓ Backend healthy: {r.json()}")
            return True
    except Exception as e:
        print(f"✗ Backend not reachable at {API_BASE}: {e}")
        print("  Start the backend first: cd FHIR_LLM_UA/backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001")
    return False


def run_question(q: dict, timeout: int = 120) -> dict:
    """POST a single question to the population-query endpoint."""
    payload = {
        "patient_ids": COHORT_PATIENT_IDS,
        "query": q["question"],
    }
    t0 = time.time()
    try:
        resp = requests.post(POPULATION_ENDPOINT, json=payload, timeout=timeout)
        elapsed = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "id": q["id"],
                "category": q.get("category", ""),
                "question": q["question"],
                "complexity": q.get("complexity", ""),
                "key_challenge": q.get("key_challenge", ""),
                "data_available": q.get("data_available", True),
                "data_gap": q.get("data_gap", ""),
                "response": data.get("response", ""),
                "sql_used": data.get("sql_used", ""),
                "pipeline_mode": data.get("pipeline_mode", ""),
                "elapsed_ms": elapsed,
                "error": "",
            }
        else:
            return {**_empty_row(q), "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "elapsed_ms": int((time.time() - t0) * 1000)}
    except requests.Timeout:
        return {**_empty_row(q), "error": f"Timeout after {timeout}s",
                "elapsed_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {**_empty_row(q), "error": str(e),
                "elapsed_ms": int((time.time() - t0) * 1000)}


def _empty_row(q: dict) -> dict:
    return {
        "id": q["id"],
        "category": q.get("category", ""),
        "question": q["question"],
        "complexity": q.get("complexity", ""),
        "key_challenge": q.get("key_challenge", ""),
        "data_available": q.get("data_available", True),
        "data_gap": q.get("data_gap", ""),
        "response": "",
        "sql_used": "",
        "pipeline_mode": "",
        "elapsed_ms": 0,
        "error": "",
    }


def save_csv(rows: list, path: Path):
    fieldnames = [
        "id", "category", "question", "complexity", "key_challenge",
        "data_available", "data_gap", "response", "sql_used",
        "pipeline_mode", "elapsed_ms", "error"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✓ CSV saved: {path}")


def save_markdown(rows: list, path: Path, timestamp: str):
    lines = [
        f"# Population Health Questions — Evaluation Results",
        f"",
        f"**Date:** {timestamp}  ",
        f"**Cohort:** 12 patients  ",
        f"**Architecture:** Ziletti & D'Ambrosi (2025) two-step RAG + text-to-SQL  ",
        f"**Temporal reasoning:** TIMER (arXiv:2503.04176) deterministic parser  ",
        f"",
        f"## Cohort Members",
        f"",
    ]
    for pid, name in COHORT_NAMES.items():
        lines.append(f"- {name} ({pid})")
    lines += ["", "---", ""]

    for row in rows:
        status = "✓" if not row["error"] and row["response"] else ("⚠ No data" if not row["data_available"] else "✗ Error")
        lines += [
            f"## {row['id']} — {row['key_challenge']} {status}",
            f"",
            f"**Category:** {row['category']}  ",
            f"**Complexity:** {row['complexity']}  ",
            f"**Data available:** {'Yes' if row['data_available'] else 'No — ' + row.get('data_gap', '')}  ",
            f"**Pipeline:** {row['pipeline_mode']}  ",
            f"**Time:** {row['elapsed_ms']}ms  ",
            f"",
            f"**Question:**",
            f"> {row['question']}",
            f"",
            f"**Response:**",
            f"{row['response'] or '_No response._'}",
            f"",
        ]
        if row["sql_used"]:
            lines += [f"**SQL / Query description:** `{row['sql_used']}`", ""]
        if row["error"]:
            lines += [f"**Error:** {row['error']}", ""]
        lines.append("---")
        lines.append("")

    # Summary table
    total = len(rows)
    answered = sum(1 for r in rows if r["response"] and not r["error"])
    no_data = sum(1 for r in rows if not r["data_available"])
    errors = sum(1 for r in rows if r["error"])
    avg_ms = int(sum(r["elapsed_ms"] for r in rows if r["elapsed_ms"]) / max(1, total))

    lines += [
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total questions | {total} |",
        f"| Answered | {answered} |",
        f"| No data in DB | {no_data} |",
        f"| Errors | {errors} |",
        f"| Avg response time | {avg_ms}ms |",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✓ Markdown saved: {path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run population health questions evaluation")
    parser.add_argument("--mode", choices=["all", "data", "single"], default="all",
                        help="all=all 25, data=only data_available=true, single=one question")
    parser.add_argument("--id", help="Question ID for --mode single (e.g. POP9)")
    parser.add_argument("--timeout", type=int, default=120, help="Seconds per question (default 120)")
    args = parser.parse_args()

    if not QUESTIONS_FILE.exists():
        print(f"✗ Questions file not found: {QUESTIONS_FILE}")
        sys.exit(1)

    if not check_backend():
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    questions = json.loads(QUESTIONS_FILE.read_text())

    # Filter questions
    if args.mode == "data":
        questions = [q for q in questions if q.get("data_available", True)]
        print(f"Running {len(questions)} questions with data_available=true")
    elif args.mode == "single":
        if not args.id:
            print("--id required for --mode single")
            sys.exit(1)
        questions = [q for q in questions if q["id"] == args.id]
        if not questions:
            print(f"Question ID '{args.id}' not found")
            sys.exit(1)
    else:
        print(f"Running all {len(questions)} population questions")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []

    print(f"\n{'='*60}")
    print(f"Cohort: {len(COHORT_PATIENT_IDS)} patients")
    print(f"Endpoint: {POPULATION_ENDPOINT}")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions, 1):
        data_flag = "" if q.get("data_available", True) else " [NO DATA IN DB]"
        print(f"[{i}/{len(questions)}] {q['id']}: {q['question'][:70]}...{data_flag}")
        row = run_question(q, timeout=args.timeout)
        results.append(row)

        if row["error"]:
            print(f"  ✗ Error: {row['error']}")
        else:
            preview = row["response"][:120].replace("\n", " ") if row["response"] else "(empty)"
            print(f"  ✓ {row['elapsed_ms']}ms | {row['pipeline_mode']} | {preview}...")

        if i < len(questions):
            time.sleep(SLEEP_BETWEEN_QUESTIONS)

    # Save outputs
    csv_path = OUTPUT_DIR / f"population_results_{timestamp}.csv"
    md_path = OUTPUT_DIR / f"population_results_{timestamp}.md"
    save_csv(results, csv_path)
    save_markdown(results, md_path, timestamp)

    answered = sum(1 for r in results if r["response"] and not r["error"])
    print(f"\n{'='*60}")
    print(f"Done: {answered}/{len(results)} questions answered")
    print(f"CSV:  {csv_path}")
    print(f"MD:   {md_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
