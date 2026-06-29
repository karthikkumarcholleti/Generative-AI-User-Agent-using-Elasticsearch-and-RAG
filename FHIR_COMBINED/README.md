# Clinical LLM System — UPHP / FHIR-Based EHR Intelligence

**Research Project:** *Large Language Model Implementation over Longitudinal Patient Records  
for Clinical Decision Modeling using Elasticsearch and RAG/MedRAG*

**Institution:** University of the Prairie / United Healthcare of the Prairie (UPHP)  
**Model:** Llama 3.1 8B (4-bit quantized) — 2× Tesla T4 GPUs  
**Stack:** FastAPI · Next.js · Elasticsearch 8.14 · MySQL · FHIR R4

---

## What This System Does

This system enables UPHP clinicians to query longitudinal patient EHR data using natural language. It supports two AI retrieval pipelines that can be compared side-by-side:

| Mode | Pipeline | What It Does |
|------|----------|--------------|
| **Standard RAG** | Elasticsearch BM25+kNN → LLM | Flat document retrieval, direct answer |
| **MedRAG + KG** | Elasticsearch + Knowledge Graph → LLM | Diagnostic reasoning with SNOMED-CT / ICD-10 differential diagnosis |

A third **population-level** pipeline (Ziletti & D'Ambrosi 2025, RAG+A+C) answers cohort analytics questions using LLM-generated SQL over the enterprise MySQL database.

---

## Repository Structure

```
FHIR_COMBINED/
├── FHIR_LLM_UA/
│   ├── backend/app/           # FastAPI application (port 8001)
│   │   ├── main.py            # Entry point
│   │   ├── core/              # llm.py, database.py, prompts.py
│   │   └── api/               # All route handlers and service modules
│   ├── models/                # Llama 3.1 8B quantized weights (~5.4 GB)
│   └── sql/                   # MySQL schema definitions
├── FHIR_dashboard/
│   └── backend/frontend/      # Next.js frontend (port 3000)
├── elasticsearch-8.14.0/      # Bundled Elasticsearch instance
├── scripts/
│   ├── compare_rag_vs_medrag.py    # RAG vs MedRAG benchmark runner
│   ├── comparison_results/          # Best comparison outputs (v7 canonical)
│   ├── population_results/          # Population query evaluation outputs
│   ├── pop_query_kb.json            # Population-level query knowledge base
│   └── population_questions.json    # 25 test cohort analytics questions
├── DIAGNOSTICS/               # Known data-quality issues (patient 740)
├── PAPER_SECTIONS/            # Research paper content (literature, methods, results)
├── etl/                       # Single-hospital FHIR ETL pipeline
├── etl_enterprise/            # 29-hospital enterprise ETL pipeline
├── README.md                  # This file
├── Code_work.md               # Step-by-step usage guide with expected output
├── KNOWLEDGE_TRANSFER.md      # Full system knowledge transfer document
├── CLAUDE.md                  # Architecture reference for AI-assisted development
├── check_mode.sh              # Show current RAG/MedRAG mode
├── use_rag.sh                 # Switch to Standard RAG
└── use_medrag.sh              # Switch to MedRAG + KG
```

---

## Quick Start

> **Prerequisite:** MySQL and Elasticsearch must already be populated. See `Code_work.md` for full setup.

**Terminal 1 — Elasticsearch:**
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./elasticsearch-8.14.0/bin/elasticsearch
```
Wait for `started` in the output, then verify: `curl -s http://localhost:9200/_cluster/health | grep status`

**Terminal 2 — Backend:**
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/backend
nohup /home/kchollet/miniconda3/bin/python3 -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8001 --workers 1 > /tmp/backend.log 2>&1 &
tail -f /tmp/backend.log
```
Wait for `Application startup complete.`, then verify: `curl -s http://localhost:8001/health`

**Terminal 3 — Frontend:**
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_dashboard/backend/frontend
npm run dev
```
Open: **http://localhost:3000**

---

## Access Points

| Service | URL |
|---------|-----|
| Frontend (Next.js) | http://localhost:3000 |
| Backend API | http://localhost:8001 |
| Swagger / API Docs | http://localhost:8001/docs |
| Elasticsearch | http://localhost:9200 |

---

## Pipeline Toggle

```bash
./check_mode.sh    # Show current mode: "Standard RAG" or "MedRAG + KG"
./use_rag.sh       # Switch to Standard RAG (no restart needed)
./use_medrag.sh    # Switch to MedRAG + Knowledge Graph
```

---

## Key Design Principles

1. **Charts never depend on the LLM** — visualization queries hit Elasticsearch directly; GPU OOM does not break charts.
2. **Summaries are deterministic** — generated with `do_sample=False` (greedy decoding), same input always produces same output.
3. **Every query is audit-logged** — written to `llm_ua_ai.clinical_audit_log` before response is returned.
4. **Five independent pipelines** — Visualization, Summary, Standard RAG, MedRAG+KG, Doctor Agent. Failure in one does not cascade.
5. **Single source of truth for reference ranges** — `REFERENCE_RANGES` in `visualization_service.py` is used by all abnormality scoring, plausibility checks, and clinical priority scoring.

---

## Primary Test Patient

Patient ID: `000000509` — 41 conditions, 200+ observations. Used for all benchmark comparisons.

```bash
curl -s http://localhost:8001/patients/000000509 | python3 -m json.tool | head -20
```

---

## Research Paper

Best comparison result: `scripts/comparison_results/comparison_20260330_232416.md`
Population-level final results: `scripts/population_results/population_results_final_20260527_v2.md`
Paper content: `PAPER_SECTIONS/`
