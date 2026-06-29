# Knowledge Transfer Document
## Clinical LLM System — UPHP / FHIR-Based EHR Intelligence

**Prepared by:** Karthik Kumar Cholleti  
**Date:** June 2026  
**Research Title:** *Large Language Model Implementation over Longitudinal Patient Records  
for Clinical Decision Modeling using Elasticsearch and RAG/MedRAG*  
**Contact:** karthikkumarcholleti.02@gmail.com

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Hardware and Environment](#2-hardware-and-environment)
3. [System Architecture — Five Pipelines](#3-system-architecture--five-pipelines)
4. [Data Layer](#4-data-layer)
5. [Key Source Files — What Each Does](#5-key-source-files--what-each-does)
6. [How the AI Pipelines Work](#6-how-the-ai-pipelines-work)
7. [Population-Level Pipeline (Ziletti 2025)](#7-population-level-pipeline-ziletti-2025)
8. [Audit Logging — HIPAA Compliance](#8-audit-logging--hipaa-compliance)
9. [Clinical Safety Decisions](#9-clinical-safety-decisions)
10. [Known Problems (Prioritized)](#10-known-problems-prioritized)
11. [Research Evaluation — What Still Needs to Be Done](#11-research-evaluation--what-still-needs-to-be-done)
12. [ETL Pipelines — How Patient Data Enters the System](#12-etl-pipelines--how-patient-data-enters-the-system)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Shell Scripts Reference](#14-shell-scripts-reference)
15. [Database Schema Summary](#15-database-schema-summary)
16. [Continuation Priorities for Next Team](#16-continuation-priorities-for-next-team)

---

## 1. Project Summary

This system was built as a research platform for comparing two AI retrieval strategies for
clinical decision support at UPHP (United Healthcare of the Prairie):

**Research Question:** Does adding a biomedical Knowledge Graph (MedRAG) to standard
Retrieval-Augmented Generation (RAG) improve clinical decision support quality when
working with FHIR-standardized longitudinal EHR data?

**What was built:**
- A FastAPI backend that loads Llama 3.1 8B in 4-bit quantization and exposes REST endpoints
- An Elasticsearch hybrid search index (BM25 + kNN vector) over FHIR patient data
- A MedRAG Knowledge Graph using SNOMED-CT and ICD-10 for differential diagnosis
- A Next.js clinical dashboard with chat, visualization, and patient summary panels
- A population-level cohort analytics pipeline (text-to-SQL via LLM)
- HIPAA-required audit logging of every clinician query

**Data source:** HL7/CCDA hospital feeds from 29 hospitals → FHIR R4 → MySQL + Elasticsearch  
**Primary test patient:** `000000509` — 41 conditions, 200+ observations

---

## 2. Hardware and Environment

| Resource | Details |
|----------|---------|
| Server | Shared Linux server (4.18.0 kernel) |
| GPUs | 2× NVIDIA Tesla T4 (16 GB VRAM each, shared with other users) |
| Python | `/home/kchollet/miniconda3/bin/python3` (must use this path) |
| Model | Llama 3.1 8B, 4-bit quantized, ~5.4 GB, loaded into VRAM at startup |
| MySQL | Port 3306, user: `llm_ua_reader`, password: `P@ssw0rd` |
| Elasticsearch | Port 9200, bundled at `elasticsearch-8.14.0/` |
| Frontend | Next.js 14, port 3000 (sometimes 3001 if busy) |
| Backend | FastAPI, port 8001, 1 worker (LLM is singleton, must be 1 worker) |

**Critical shared-server rule:** Never kill GPU processes owned by other users (e.g., `ckadirim`
runs Jupyter on the GPUs). Always check `ps -o user,pid -p <PID>` before killing anything.

**Starting services — three terminals, in order:**

```bash
# Terminal 1 — Elasticsearch (leave this terminal open)
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./elasticsearch-8.14.0/bin/elasticsearch

# Terminal 2 — Backend (Llama loads in 60–120 seconds)
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/backend
/home/kchollet/miniconda3/bin/python3 -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8001 --workers 1
# Wait for "Application startup complete." — leave terminal open, Ctrl+C to stop

# Terminal 3 — Frontend
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_dashboard/backend/frontend
npm run dev
```

**Stopping services:**

- **Terminal 1 (Elasticsearch):** Ctrl+C
- **Terminal 2 (Backend):** Ctrl+C
- **Terminal 3 (Frontend):** Ctrl+C

Stop Elasticsearch only when needed — verify owner first:
```bash
ES_PID=$(ps aux | grep elasticsearch | grep java | grep -v grep | awk '{print $2}' | head -1)
ps -o user,pid -p $ES_PID  # must say kchollet before killing
kill $ES_PID
```

---

## 3. System Architecture — Five Pipelines

These five pipelines are architecturally independent. A failure in any one must not cascade to others.

```
Pipeline 1 — VISUALIZATION      (no LLM, direct ES query → chart data)
Pipeline 2 — SUMMARY GENERATION (LLM, do_sample=False, deterministic)
Pipeline 3 — STANDARD RAG CHAT  (LLM, flat ES context, USE_MEDRAG=False)
Pipeline 4 — MEDRAG+KG CHAT     (LLM, KG-augmented context, USE_MEDRAG=True)
Pipeline 5 — DOCTOR AGENT       (LLM, multi-tool retrieval + single synthesis call)
```

### Pipeline 1: Visualization (No LLM)

- Endpoint: `GET /patients/{id}/observations/{loinc_code}/timeseries`
- Queries Elasticsearch directly for `data_type: "observation"` documents
- Returns timestamps, values, units, reference ranges, trend direction
- Trend is computed with `scipy.stats.linregress` (p < 0.05, R² > 0.5 required)
- **The LLM is never involved in chart data.** Charts always work even when GPU is saturated.

### Pipeline 2: Summary Generation

- Endpoint: `GET /patients/{id}/all_summaries`
- Sections: demographics, conditions, observations, notes, care_plans, patient_summary
- Uses `do_sample=False` (greedy decoding) — deterministic, same input → same output
- Results cached in-memory for 3 patients (LRU)
- MedRAG KG is injected into the `patient_summary` and `observations` sections

### Pipelines 3 & 4: RAG Chat

- Endpoint: `POST /chat-agent/query`
- Both modes run identical Elasticsearch retrieval (top 150 docs, hybrid BM25+kNN)
- Mode is controlled by `USE_MEDRAG` flag in `rag_service.py` (toggleable at runtime)
- Standard RAG: flat context → LLM
- MedRAG: KG DDx pipeline runs first → KG context injected above patient data → LLM

### Pipeline 5: Doctor Agent

- Endpoint: `POST /doctor-agent/query`
- Deterministic tool selection (keyword-based): always calls `search_conditions`, optionally
  `search_labs`, `search_vitals`, `get_notes`, `get_lab_trends`, `run_kg_ddx`
- All tools execute against ES in parallel
- Single LLM synthesis call with physician-quality prompt
- Returns `agent_steps` trace showing which tools were called

---

## 4. Data Layer

### MySQL Databases

| Database | Purpose |
|----------|---------|
| `llm_ua_enterprise` | Primary patient data: patients, observations, conditions, notes, encounters, care_plans |
| `llm_ua_ai` | Audit log only: `clinical_audit_log` table |

Key field name: `enterprise_patient_id` (not `patient_id`) is the primary key in the enterprise schema.

### Elasticsearch Index: `patient_data`

Top-level fields (not nested under `metadata` — this is critical):

| Field | Type | Description |
|-------|------|-------------|
| `enterprise_patient_id` | keyword | Patient identifier |
| `data_type` | keyword | `"observation"`, `"condition"`, `"encounter"`, `"note"` (singular) |
| `display` | text | Human-readable name (e.g., "Hemoglobin A1c") |
| `code` | keyword | LOINC or ICD-10 code |
| `value_numeric` | float | Numeric lab value |
| `unit` | keyword | Unit of measurement |
| `effective_date` | date | Observation date |
| `effective_datetime` | date | Full datetime (fallback when effective_date is null) |
| `content` | text | Full text blob for BM25 search (includes LOINC aliases) |
| `embedding` | dense_vector | 384-dim vector for kNN search |
| `timestamp` | date | Derived: `effective_date ?? effective_datetime ?? note_date` |

**Why `timestamp` matters:** The retrieval pipeline sorts by `timestamp DESC` and takes the top 50
documents. If `effective_date` is null (common for lab results) and `effective_datetime` is not
checked as fallback, those documents get an empty timestamp and sort to the bottom — resulting in
no chart data. This bug was fixed in `elasticsearch_client.py`.

### LOINC Alias Injection

At index time, `loinc_code_mapper.py` injects human-readable aliases into the `content` field:
- "2160-0" → content includes "creatinine", "serum creatinine", "kidney function"
- "4548-4" → content includes "hba1c", "hemoglobin a1c", "glycated hemoglobin", "a1c"

This makes BM25 text search work for natural language queries without semantic embeddings.

---

## 5. Key Source Files — What Each Does

| File | Lines | Role |
|------|-------|------|
| `api/rag_service.py` | ~2200 | Central RAG + MedRAG pipeline; intent classification; ES retrieval; implausibility filter; source UUID storage; DDx intent detection |
| `api/medrag_knowledge_graph.py` | ~981 | 4-tier Diagnostic KG (SNOMED-CT/ICD-10); disease matching; DDx context builder |
| `api/chat_agent.py` | ~1370 | API route handler for `/chat-agent/query`; audit log writer; source citation endpoints |
| `api/doctor_agent.py` | ~350 | Doctor Agent multi-tool endpoint |
| `api/elasticsearch_client.py` | ~810 | ES index management; hybrid BM25+kNN search; LOINC alias injection at index time |
| `api/intelligent_visualization.py` | ~1190 | Decides whether to generate a chart; routes to chart type; scans retrieved data for numeric observations |
| `api/visualization_service.py` | ~4160 | Chart data generators; `REFERENCE_RANGES` (58 lab types); `UNIT_CONVERSIONS`; encounter context |
| `api/loinc_code_mapper.py` | ~785 | 54+ LOINC codes mapped to aliases |
| `api/observation_categorizer.py` | ~354 | 15 clinical categories (cardiac, thyroid, diabetes, mental health, etc.) |
| `api/summary.py` | ~1135 | Per-section summary generation; MedRAG KG injection; retry + OOM recovery; 3-patient LRU cache |
| `api/population_query_service.py` | ~1904 | Population-level RAG+A+C pipeline (Ziletti 2025); text-to-SQL; self-healing SQL execution |
| `api/temporal_parser.py` | ~300 | Temporal constraint extraction for population queries ("last 6 months", "between 2023-2024") |
| `api/embedding_service.py` | ~200 | Sentence-BERT embeddings on GPU; used for kNN search and population query matching |
| `core/llm.py` | ~595 | Singleton Llama 3.1 8B loader; `_gen_lock` serialization; OOM recovery; `clear_gpu_memory()` |
| `core/prompts.py` | ~404 | All LLM prompt templates organized by summary section and query type |
| `core/database.py` | ~80 | SQLAlchemy engine with connection pool: `pool_size=5`, `pool_recycle=3600`, `pool_pre_ping=True` |

---

## 6. How the AI Pipelines Work

### Intent Classification

Every chat query goes through `IntentClassifier` in `rag_service.py`:
- Detected intents: `observations`, `conditions`, `analysis`, `visualization`, `grouped_visualization`, `general`
- This determines: what ES query to run, whether to generate a chart, and which prompt template to use

### DDx Intent Detection

On top of intent classification, a separate DDx check fires for clinical reasoning queries:
- **Trigger keywords** (`DDX_INTENT_KEYWORDS`): "most likely diagnosis", "differential", "overall assessment", "risk of", "evidence of", "signs of cardiovascular", etc.
- **Suppression keywords** (`VALUE_LOOKUP_OVERRIDES`): "what is the", "list the", "give me the", "how high is", "compare"
- When `_apply_ddx = True`: 5-step format (Diagnosis / Evidence / Alternatives / Gaps / Recommendation)
- **Known weakness:** "What is the sign of kidney disease" is incorrectly suppressed by "what is the" prefix. Fix: move DDx detection into `IntentClassifier` as a semantic classification (not keyword-based).

### MedRAG Knowledge Graph

`medrag_knowledge_graph.py` implements a 4-tier diagnostic pipeline:
1. `find_candidate_diseases()` — scores diseases by voting: conditions (4×), observations (3×), demographics (2×), notes (1×)
2. `match_patient_evidence()` — matches patient data against each candidate disease's known markers
3. `build_kg_context()` — formats DDx context block injected into LLM system prompt
4. `build_kg_summary()` — for non-DDx queries, builds a compact clinical context summary

**Anchoring bias warning:** Existing diagnoses are weighted 4× in voting. A patient with documented
diabetes will always score diabetes very high — even for unrelated queries. This is a research
validity concern and must be addressed before paper submission (see Known Problems, #10).

### GPU Memory Management

- One generation at a time: `_gen_lock = threading.Lock()` in `core/llm.py`
- OOM fallback: `clear_gpu_memory()` (frees cache) then `clear_gpu_memory_aggressive()` (deletes tensor pools)
- Summaries use `do_sample=False`; chat uses `do_sample=True, temperature=0.3`
- Token limits by task type (set in `core/llm.py` `_LIMITS` dict): chat=1400, doctor_agent=1600, patient_summary=2200, observations=2500

### Implausibility Filter

Runs in `rag_service.py` before assembling LLM context. Blocks physiologically impossible values:

| Lab | Minimum | Maximum |
|-----|---------|---------|
| Cholesterol | 10 mg/dL | 700 mg/dL |
| Creatinine | 0.05 mg/dL | 30 mg/dL |
| Glucose | 0.5 mg/dL | 1500 mg/dL |
| Hemoglobin | 1 g/dL | 25 g/dL |

Implausible values are treated as missing (not dropped), so the KG asks for accurate data.

---

## 7. Population-Level Pipeline (Ziletti 2025)

**Reference:** Ziletti & D'Ambrosi, 2025 — RAG+A+C methodology (arXiv:2503.04176 for temporal constraints / TIMER)

**Endpoint:** `POST /chat-agent/population-query`

**Input:** `{"patient_ids": [...], "query": "How many patients have diabetes?"}`

### How it works (RAG+A+C steps):

**Step 1 — RAG+A (Query Normalization):**
Entity masking removes patient-specific terms from the query. The masked query is embedded
with Sentence-BERT and matched against `pop_query_kb.json` (25 curated template queries) using
cosine similarity. The top match provides SQL structure guidance.

**Step 2 — RAG+C (Schema Context + Temporal Constraints):**
The full MySQL schema for `llm_ua_enterprise` is injected into the prompt.
`temporal_parser.py` extracts time expressions ("last 6 months", "between 2023 and 2024")
and converts them to SQL date constraints.

**Step 3 — LLM Text-to-SQL:**
Llama 3.1 8B generates a MySQL query using the schema context + temporal constraints + query KB guidance. Uses `do_sample=False` for deterministic SQL generation.

**Step 4 — Self-Healing Execution:**
The generated SQL is executed against MySQL. On syntax errors, the error message is fed back
to the LLM for one auto-correction attempt.

**Step 5 — LLM Synthesis:**
The SQL result rows are passed to the LLM for a natural language answer. Uses `do_sample=False`.

**Evaluation:** `scripts/pop_eval_judge.py` runs LLM-as-judge evaluation.
Best results: `scripts/population_results/population_results_final_20260527_v2.md`

**Frontend status:** The population toggle is live. On the Generative AI page, there's a **Patient Level / Population Level** button in the header. Switching to Population opens a cohort selector (search + checkboxes + select all) and a chat panel that calls this endpoint directly.

---

## 8. Audit Logging — HIPAA Compliance

### What it is

Every query sent to `/chat-agent/query` or `/doctor-agent/query` is recorded in an
append-only MySQL table before the response is returned.

### Database location

```
Database: llm_ua_ai
Table:     clinical_audit_log
```

### Schema

```sql
CREATE TABLE clinical_audit_log (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    timestamp         DATETIME NOT NULL,
    patient_id        VARCHAR(50) NOT NULL,
    query             TEXT NOT NULL,
    pipeline_mode     VARCHAR(20),      -- "MedRAG + KG" or "Standard RAG"
    retrieved_count   INT,              -- docs from ES
    llm_response      TEXT,             -- full LLM answer
    sources_used      JSON,             -- list of cited source documents
    intent_classified VARCHAR(50),      -- detected intent
    elapsed_ms        INT,              -- total response time
    oom_triggered     TINYINT DEFAULT 0,-- 1 if GPU OOM fallback ran
    session_id        VARCHAR(100)      -- browser session
);
```

### How to query it

```bash
# All queries
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai \
  -e "SELECT id, timestamp, patient_id, LEFT(query,60), pipeline_mode, elapsed_ms FROM clinical_audit_log ORDER BY timestamp DESC LIMIT 20;"

# Count by pipeline
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai \
  -e "SELECT pipeline_mode, COUNT(*) FROM clinical_audit_log GROUP BY pipeline_mode;"

# OOM incidents
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai \
  -e "SELECT * FROM clinical_audit_log WHERE oom_triggered=1 ORDER BY timestamp DESC LIMIT 10;"

# Average response time by mode
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai \
  -e "SELECT pipeline_mode, AVG(elapsed_ms)/1000 AS avg_seconds FROM clinical_audit_log GROUP BY pipeline_mode;"
```

### Where in the code

`FHIR_LLM_UA/backend/app/api/chat_agent.py` — inside the route handler for `POST /chat-agent/query`.
The write uses a dedicated connection (not the main pool) and is wrapped in `try/except` so
a database failure never blocks the clinical response.

---

## 9. Clinical Safety Decisions

These decisions were made deliberately and must not be reversed without review:

| Decision | Why |
|----------|-----|
| Charts never call the LLM | Trends shown to clinicians must be statistical, not LLM-derived. LLM output is non-deterministic. |
| Summaries use `do_sample=False` | Clinicians compare summaries across visits. Non-deterministic output is clinically dangerous. |
| Trend direction requires p < 0.05 AND R² > 0.5 AND n >= 3 | A wrong trend direction (e.g., "glucose is decreasing" when it is increasing) is a patient safety issue. |
| Implausible values are treated as missing, not dropped | A dropped observation could be a real value and a missed diagnosis. |
| `USE_MEDRAG` toggle must remain functional | Core of research methodology. Both modes must always work. |
| Audit log write happens before response is returned | If logging fails silently, the compliance record is incomplete. The try/except ensures the query still completes. |
| All SQL uses SQLAlchemy `text()` with named params | No string interpolation of patient input. SQL injection prevention. |

---

## 10. Known Problems (Prioritized)

These were identified in a full architectural review and must be addressed before UPHP production:

| Priority | Problem | Location | Impact |
|----------|---------|---------|--------|
| P1 | No audit logging for Doctor Agent queries | `doctor_agent.py` | HIPAA gap — Doctor Agent queries are not logged |
| P2 | ETL has no validation layer | `etl_enterprise/` | Every new patient batch repeats same date, unit, plausibility bugs |
| P3 | DDx suppression is keyword-based | `rag_service.py` `VALUE_LOOKUP_OVERRIDES` | "What is the sign of kidney disease" incorrectly suppresses DDx |
| P4 | MedRAG KG has anchoring bias | `medrag_knowledge_graph.py` `find_candidate_diseases()` | Existing diagnoses weighted 4× — biases DDx toward known conditions |
| P5 | Comparison script has order effect | `scripts/compare_rag_vs_medrag.py` | Standard RAG always runs first; MedRAG runs on warmer GPU — timing is confounded |
| P6 | Source UUIDs are ephemeral | `rag_service.py` `source_storage` dict | Server restart invalidates all citation links; clinicians get 404 |
| P7 | ~~Frontend is a 1960-line monolith~~ | ~~`generative-ai.tsx`~~ | **Done** — decomposed into components/hooks/services |
| P8 | LOINC coverage is ~100 codes | `loinc_code_mapper.py` | ~40% of observations appear as "Other" in grouped view |
| P9 | ~~No population toggle in frontend~~ | ~~Missing UI component~~ | **Done** — Patient Level / Population Level toggle is live |
| P10 | GPU concurrency uses polling | `core/llm.py` | Unreliable under multi-user load; should use `threading.PriorityQueue` |

---

## 11. Research Evaluation — What Still Needs to Be Done

For the peer-reviewed paper to be accepted, the following must be completed:

### Automated Metrics (add to `scripts/compare_rag_vs_medrag.py`)

- **ROUGE-L** — response completeness vs reference answers
- **Faithfulness** — % of LLM claims traceable to retrieved source documents
- **Consistency** — cosine similarity of 3 repeated runs (same patient, same query)
- **Fix order effect** — randomize which pipeline runs first per query
- **Run each query 3 times** — report median ± IQR, not mean elapsed time
- **Wilcoxon signed-rank test** — for paired statistical significance between pipelines

### Human Evaluation (required, no substitute)

5–10 anonymized patient cases sent to UPHP clinicians for structured rating:
- Clinical accuracy (1–5)
- Actionability of recommendation (1–5)
- Completeness of differential diagnosis (1–5)
- Safety — did it hallucinate a finding not supported by the record? (yes/no)

### MedRAG De-biasing (fix before paper)

In `find_candidate_diseases()`, down-weight conditions already in the patient record when the
query asks about them directly. The current 4× weight creates confirmation bias, not true DDx.

---

## 12. ETL Pipelines — How Patient Data Enters the System

### Single-Hospital ETL (`etl/`)

Processes HL7/CCDA feeds from one hospital source:
- Parses FHIR R4 resources (Patient, Observation, Condition, Encounter, CarePlan, DocumentReference)
- Normalizes units using LOINC canonical units
- Writes to `llm_ua_enterprise` MySQL

### Enterprise ETL (`etl_enterprise/`)

29-hospital schema with identity resolution:
- Matches patients across hospitals using probabilistic identity linking (`identity_resolver.py`)
- Assigns `enterprise_patient_id` as the canonical key
- Handles schema differences between hospital systems

### Known Data Quality Issues (all patients)

- **~28% of observations have `"unit": "unit"`** — ETL placeholder; unit normalization is a no-op for these
- **NULL display names** — LOINC mapper covers ~100 codes; others show as "Other"
- **Corrupted dates as floats** — e.g., `20250200.0` (Feb 30); partially handled by `_parse_numeric_date()` in `summary.py`
- **`effective_date` null with `effective_datetime` set** — fixed in `elasticsearch_client.py` (timestamp fallback)

### Patient 740 — Specific Issues

See `DIAGNOSTICS/740_issues_summary.md` for full details. Do not draw clinical conclusions
from patient 740. Key issues: implausible blood pressure aggregates, corrupted dates, missing units.

---

## 13. Frontend Architecture

### Current State

- **Framework:** Next.js 14, TypeScript
- **Location:** `FHIR_dashboard/backend/frontend/`
- **API clients:** `services/llmApi.ts` (patient queries), `services/populationApi.ts` (cohort queries)

The old 1960-line monolith (`generative-ai.tsx`) has been decomposed into a proper component structure:

```
pages/generative-ai/
└── index.tsx                    # Layout + mode toggle only (~220 lines)

components/
├── patient/
│   ├── PatientSelector.tsx      # Search + scrollable patient list
│   ├── SummaryPanel.tsx         # Section summaries with typing animation
│   └── ChatPanel.tsx            # Messages, charts, sources, follow-ups, input
├── population/
│   ├── CohortSelector.tsx       # Search + checkboxes + Select All
│   └── PopulationChat.tsx       # Cohort query UI with sample questions + SQL viewer
└── shared/
    └── LLMResponseFormatter.tsx # Shared LLM text renderer

hooks/
├── usePatients.ts               # Fetch patient list
├── usePatientSummary.ts         # Summary generation + auto-refresh
├── usePatientChat.ts            # Chat messages, send, follow-ups, source modal, backend cache sync
└── usePopulationQuery.ts        # Population cohort query
```

### What the frontend does

- Loads patient list from `GET /patients`
- Fetches all summaries from `GET /patients/{id}/all_summaries` (can take 2–5 minutes)
- Sends patient chat queries to `POST /chat-agent/query`
- Sends population queries to `POST /chat-agent/population-query`
- Displays charts using `recharts` based on chart payload in responses
- Shows clickable source citations via `GET /chat-agent/source/{id}`
- Patient Level / Population Level mode toggle in the header

### What the frontend does NOT do yet

- No Observation Explorer with independent timeseries charts (would call `/timeseries` directly, no LLM)
- No Doctor Agent mode in the UI (backend endpoint exists at `POST /doctor-agent/query`)
- No session-based audit trail visible to clinicians in the UI

---

## 14. Shell Scripts Reference

All scripts run from `/mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/`

| Script | Purpose |
|--------|---------|
| `check_mode.sh` | Print current RAG/MedRAG mode |
| `use_rag.sh` | Switch to Standard RAG (no restart needed) |
| `use_medrag.sh` | Switch to MedRAG + KG (no restart needed) |
| `setup_elasticsearch.sh` | Initialize/configure Elasticsearch index mapping |
| `scripts/fix_and_reindex_all.sh` | Delete ES index and reindex all patients from MySQL |
| `scripts/fix_elasticsearch_disk_space.sh` | Clear ES disk warning (sets flood stage watermark) |

Services (Elasticsearch, backend, frontend) are started and stopped with explicit terminal
commands — see Section 2 above and `Code_work.md` for the full step-by-step sequence.

---

## 15. Database Schema Summary

### `llm_ua_enterprise.patients`

```sql
enterprise_patient_id VARCHAR(50) PRIMARY KEY
first_name, last_name, date_of_birth, gender
address, city, state, zip, phone
insurance_id, insurance_type
created_at, updated_at
```

### `llm_ua_enterprise.observations`

```sql
id INT PRIMARY KEY
enterprise_patient_id VARCHAR(50)
code VARCHAR(50)          -- LOINC code
display VARCHAR(500)      -- human name
value_numeric DECIMAL     -- numeric result
unit VARCHAR(100)
effective_date DATE
effective_datetime DATETIME
status VARCHAR(50)
source_hospital VARCHAR(100)
```

### `llm_ua_enterprise.conditions`

```sql
id INT PRIMARY KEY
enterprise_patient_id VARCHAR(50)
code VARCHAR(50)          -- ICD-10 code
display VARCHAR(500)
onset_date DATE
abatement_date DATE
clinical_status VARCHAR(50)
```

### `llm_ua_ai.clinical_audit_log`

See Section 8 above for full schema.

---

## 16. What's Done and What's Next

### Already working

- Patient-level chat: Standard RAG and MedRAG+KG, toggle without restart
- AI summaries for all patient sections (deterministic, greedy decoding)
- Population-level cohort analysis — UI toggle + CohortSelector + PopulationChat
- Audit logging on every `/chat-agent/query` call
- Clickable source citations (RAG sources in chat)
- Frontend decomposed into clean components and hooks
- Doctor Agent endpoint (backend only — no UI yet)

### Before any UPHP clinician sees this

1. **Doctor Agent audit logging** — add `_write_audit_log()` call in `doctor_agent.py` (same pattern as `chat_agent.py`). Right now Doctor Agent queries are completely unlogged, which is a HIPAA gap.
2. **ETL validation** — add a `FHIRObservationValidator` that checks date format, unit plausibility, and required fields before writing to MySQL. Currently every new patient batch silently repeats the same bugs (corrupted dates, `"unit": "unit"` placeholders, impossible values).
3. **Encrypt PHI in audit log** — `patient_id`, `query`, and `llm_response` in `clinical_audit_log` should be encrypted at rest before production.

### Before paper submission

4. **Fix comparison script** (`scripts/compare_rag_vs_medrag.py`) — randomize which pipeline runs first per query, run each query 3 times, report median ± IQR instead of mean, add Wilcoxon signed-rank test. The current setup always runs Standard RAG first, which artificially makes MedRAG look slower.
5. **Add ROUGE-L and response consistency metrics** to the comparison script output.
6. **De-bias MedRAG KG** — in `medrag_knowledge_graph.py` `find_candidate_diseases()`, down-weight conditions already in the patient record when the query is specifically about those conditions. The 4× weight causes confirmation bias, not real differential diagnosis.
7. **Clinician annotation** — send 5–10 anonymized cases to UPHP clinicians for structured rating (accuracy, actionability, completeness, safety). This is required for the paper and can't be automated.

### Before production deployment

8. **Persist source UUIDs** — move `source_storage` dict in `rag_service.py` to an Elasticsearch `source_cache` index with a 7-day TTL. Right now citation links break on every server restart.
9. **Add Observation Explorer to frontend** — a tab with independent timeseries charts calling `GET /patients/{id}/observations/{loinc_code}/timeseries` directly (no LLM). The backend endpoint already exists; just needs a UI component.
10. **Add Doctor Agent mode to frontend** — a toggle or button that routes the chat to `POST /doctor-agent/query` instead of `/chat-agent/query`. The backend is fully implemented.
11. **Replace LOINC mapper** with the full LOINC CSV from Regenstrief Institute. Currently ~100 codes are mapped manually; the rest show as "Other". The full database has 100,000+ codes and is free to download.
12. **Move DDx detection to semantic classification** — the current keyword list in `VALUE_LOOKUP_OVERRIDES` incorrectly suppresses DDx for queries like "What is the sign of kidney disease". Fix: add "ddx" as a first-class intent in `IntentClassifier`.
13. **Upgrade GPU concurrency** — replace the current polling approach in `core/llm.py` with `threading.PriorityQueue` (Priority 0 = chat, Priority 1 = summaries). The polling is unreliable under concurrent load.

---

## Final Notes

The system is research-grade and working end-to-end. The core comparison (MedRAG + KG vs Standard RAG) is demonstrable. Best comparison result: `scripts/comparison_results/comparison_20260330_232416.md` (v7). Population pipeline results: `scripts/population_results/population_results_final_20260527_v2.md`.

The three items that matter most before anyone outside the research team uses this are: Doctor Agent logging, ETL validation, and PHI encryption in the audit log. Everything else is important but those three are non-negotiable for a clinical setting.

For the paper, fix the comparison script order effect first — that's the one a reviewer will immediately flag.
frontend UI yet — it represents Ziletti & D'Ambrosi (2025) RAG+A+C applied to cohort analytics.

The biggest risks before UPHP deployment are: (1) no ETL validation means new patient data
will have the same bugs, (2) source UUIDs are lost on restart, and (3) the frontend monolith
makes adding new features dangerous.

All code is committed to git. Run `git log --oneline` for history.
