# Code_work.md — How to Run This System (Step-by-Step with Expected Output)

This document walks through every operational step: starting services, querying patients, switching
pipelines, running comparisons, and checking audit logs. Each step shows the exact command and what
you should see if it is working correctly.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Starting All Services](#2-starting-all-services)
3. [Verifying Everything Is Running](#3-verifying-everything-is-running)
4. [Using the Frontend (Browser)](#4-using-the-frontend-browser)
5. [Patient-Level Queries (API)](#5-patient-level-queries-api)
6. [Switching Between RAG and MedRAG](#6-switching-between-rag-and-medrag)
7. [Population-Level Queries](#7-population-level-queries)
8. [Running RAG vs MedRAG Comparison](#8-running-rag-vs-medrag-comparison)
9. [Audit Logging — Viewing and Testing](#9-audit-logging--viewing-and-testing)
10. [Re-indexing Patient Data into Elasticsearch](#10-re-indexing-patient-data-into-elasticsearch)
11. [Stopping All Services](#11-stopping-all-services)
12. [Common Errors and Fixes](#12-common-errors-and-fixes)

---

## 1. Prerequisites

Ensure these are satisfied before starting:

- **MySQL** is running and `llm_ua_enterprise` + `llm_ua_ai` databases exist.
- **Elasticsearch** is either already running (check `localhost:9200`) or will be started below.
- **Llama 3.1 8B model** weights exist at `FHIR_LLM_UA/models/` (~5.4 GB).
- Python environment: `/home/kchollet/miniconda3/bin/python3`
- All working directories are under: `/mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/`

```bash
# Quick prerequisite check
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_enterprise -e "SELECT COUNT(*) FROM patients;" 2>/dev/null
# Expected: a number like 3254

curl -s http://localhost:9200/_cluster/health | python3 -m json.tool | grep status
# Expected: "status": "green" or "yellow"

ls /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/models/
# Expected: model config files and .gguf or .bin weights present
```

---

## 2. Starting All Services

Open **two terminals**.

### Terminal 1 — Elasticsearch (always start this first)

First check if it is already running:
```bash
curl -s http://localhost:9200/_cluster/health | grep status
```

- If you see `"status":"green"` or `"status":"yellow"` — **already running, skip to Terminal 2.**
- If you get "connection refused" — start it:

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./elasticsearch-8.14.0/bin/elasticsearch
```

Leave this terminal open — closing it stops Elasticsearch. Wait 20–30 seconds, then confirm:

```bash
curl -s http://localhost:9200/_cluster/health?pretty | grep status
```

Expected: `"status" : "green"` — do not proceed until you see this.

### Terminal 2 — Backend + Frontend

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./start_all.sh
```

The Llama model takes **60–120 seconds** to load. The script will tell you when everything is ready. To monitor the backend loading in detail:

```bash
tail -f /tmp/backend.log
```

Look for: `INFO:     Application startup complete.`

Then open: **http://localhost:3000**

---

## 3. Verifying Everything Is Running

Run these checks from any terminal:

```bash
# 1. Backend health
curl -s http://localhost:8001/health
```
**Expected:** `{"status":"ok","db":"ok"}`

```bash
# 2. Elasticsearch health
curl -s http://localhost:9200/_cluster/health?pretty | grep status
```
**Expected:** `"status" : "green"`

```bash
# 3. Patient list (first 3 patients)
curl -s http://localhost:8001/patients | python3 -m json.tool | head -30
```
**Expected:**
```json
[
  {
    "enterprise_patient_id": "000000001",
    "first_name": "...",
    "last_name": "...",
    "date_of_birth": "1965-03-12"
  },
  ...
]
```

```bash
# 4. Current AI mode
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./check_mode.sh
```
**Expected:** `{"use_medrag": true, "mode": "MedRAG + KG"}` (default is MedRAG ON)

---

## 4. Using the Frontend (Browser)

Open: **http://localhost:3000**

### Steps in the UI:

1. Click **"Generative AI"** in the left sidebar.
2. Select a patient from the dropdown (e.g., patient `000000509`).
3. Wait for the patient summary to load (takes 30–120 seconds on first load).
4. In the chat box, type a question and press Enter.

### Sample Queries to Try:

| Query | What You Should See |
|-------|---------------------|
| `Show me heart rate trend` | Chat response + a line chart of heart rate over time |
| `What is this patient's glucose trend?` | Chat response + glucose trend chart |
| `What is the differential diagnosis?` | 5-step DDx format: Diagnosis / Evidence / Alternatives / Gaps / Recommendation |
| `What are the most recent lab values?` | Table-style response listing recent labs |
| `Show all vital signs` | Multi-series chart with all vitals |

### Expected Chat Response Format (MedRAG + KG mode):

```
Primary Diagnosis: Type 2 Diabetes (High Confidence)
Evidence: HbA1c 8.2% (above 7.0% threshold), Fasting glucose 156 mg/dL
Alternative Diagnoses: Pre-diabetes, Stress hyperglycemia
Data Gaps: Recent lipid panel missing
Recommendation: Schedule follow-up HbA1c in 3 months

Sources: [1] [2] [3]
```

---

## 5. Patient-Level Queries (API)

You can query the system directly via API without the UI.

### Get patient info:
```bash
curl -s "http://localhost:8001/patients/000000509" | python3 -m json.tool
```

### Send a chat query (MedRAG mode):
```bash
curl -s -X POST "http://localhost:8001/chat-agent/query" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "000000509",
    "query": "What is the differential diagnosis for this patient?"
  }' | python3 -m json.tool | head -60
```

**Expected response structure:**
```json
{
  "response": "Primary Diagnosis: ...\nEvidence: ...",
  "sources": [
    {"id": "uuid-1234", "display": "Hemoglobin A1c", "date": "2024-10-01", "value": "8.2%"},
    ...
  ],
  "chart": {
    "type": "observation_trend",
    "data": {...}
  },
  "follow_up_options": ["What medications address this?", "Show HbA1c trend", ...],
  "pipeline_mode": "MedRAG + KG",
  "intent": "analysis",
  "elapsed_ms": 45230
}
```

### Get patient summaries:
```bash
curl -s "http://localhost:8001/patients/000000509/all_summaries" | python3 -m json.tool | head -50
```

### Get observation timeseries (chart data, no LLM):
```bash
# Heart rate (LOINC 8867-4)
curl -s "http://localhost:8001/patients/000000509/observations/8867-4/timeseries" | python3 -m json.tool
```

**Expected:**
```json
{
  "loinc_code": "8867-4",
  "display": "Heart rate",
  "unit": "beats/min",
  "data_points": [
    {"date": "2024-01-15", "value": 72},
    {"date": "2024-03-22", "value": 68},
    ...
  ],
  "reference_range": {"low": 60, "high": 100},
  "trend": "stable"
}
```

### Doctor Agent query (deepest reasoning):
```bash
curl -s -X POST "http://localhost:8001/doctor-agent/query" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "000000509",
    "query": "What are the cardiovascular risk factors for this patient?"
  }' | python3 -m json.tool | head -80
```

**Expected:** Longer response with `agent_steps` showing which tools were called (search_labs, search_vitals, run_kg_ddx, etc.)

---

## 6. Switching Between RAG and MedRAG

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED

# Check current mode
./check_mode.sh
# Output: {"use_medrag": true, "mode": "MedRAG + KG"}

# Switch to Standard RAG
./use_rag.sh
# Output: {"message": "Switched to Standard RAG", "use_medrag": false}

# Switch back to MedRAG + KG
./use_medrag.sh
# Output: {"message": "Switched to MedRAG + KG", "use_medrag": true}
```

**No restart required.** The change takes effect on the next query.

### What changes between modes:

| Aspect | Standard RAG | MedRAG + KG |
|--------|-------------|-------------|
| Context assembly | Flat list of relevant documents | Knowledge Graph DDx injected above documents |
| Response format | Direct answer | 5-step differential diagnosis structure |
| Follow-up options | Generic data-driven suggestions | KG-derived diagnostic questions |
| `pipeline_mode` in response | `"Standard RAG"` | `"MedRAG + KG"` |

---

## 7. Population-Level Queries

Population queries answer questions across a cohort of patients using SQL — not individual RAG.

```bash
curl -s -X POST "http://localhost:8001/chat-agent/population-query" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_ids": [
      "000000509", "000000036", "000000100", "000000200",
      "000000300", "000000400", "000000500"
    ],
    "query": "How many patients in this cohort have diabetes?"
  }' | python3 -m json.tool
```

**Expected output:**
```json
{
  "response": "Out of 7 patients in this cohort, 3 have a documented diagnosis of diabetes...",
  "sql_used": "SELECT COUNT(DISTINCT p.enterprise_patient_id) FROM patients p JOIN conditions c ...",
  "patient_count": 7,
  "elapsed_ms": 8450,
  "pipeline_mode": "population_sql"
}
```

### Sample population questions:
- `"What is the average HbA1c across this cohort?"`
- `"Which patients have both hypertension and diabetes?"`
- `"How many patients had an encounter in the last 6 months?"`
- `"What are the most common diagnoses in this group?"`

---

## 8. Running RAG vs MedRAG Comparison

This script runs the same queries through both pipelines and produces a side-by-side report.

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED

/home/kchollet/miniconda3/bin/python3 scripts/compare_rag_vs_medrag.py \
  --patient_id 000000509 \
  --output_dir scripts/comparison_results \
  --query_indices 0 1 2 3
```

**Expected runtime:** 20–60 minutes (each query runs twice, once per pipeline).

**Output files created:**
```
scripts/comparison_results/
├── comparison_YYYYMMDD_HHMMSS.json   # Raw data
└── comparison_YYYYMMDD_HHMMSS.md     # Human-readable report
```

**Report format (excerpt):**
```markdown
## Query: "What is the differential diagnosis for this patient?"

### Standard RAG (elapsed: 34.2s)
The patient presents with...

### MedRAG + KG (elapsed: 41.8s)
**Primary Diagnosis:** Type 2 Diabetes (High Confidence)
**Evidence:** HbA1c 8.2%, Fasting glucose 156 mg/dL
...

### Source Counts: Standard RAG: 12 | MedRAG: 18
```

Best existing result: `scripts/comparison_results/comparison_20260330_232416.md`

---

## 9. Audit Logging — Viewing and Testing

Every patient query is recorded in the `llm_ua_ai.clinical_audit_log` table before the response
is returned. This is a HIPAA compliance requirement.

### What is logged per query:

| Column | Description |
|--------|-------------|
| `id` | Auto-increment row ID |
| `timestamp` | When the query was received |
| `patient_id` | Which patient was queried |
| `query` | The clinician's full question |
| `pipeline_mode` | `"MedRAG + KG"` or `"Standard RAG"` |
| `retrieved_count` | How many documents Elasticsearch returned |
| `llm_response` | The full LLM answer |
| `sources_used` | JSON list of source documents cited |
| `intent_classified` | Detected intent (observations, conditions, analysis, etc.) |
| `elapsed_ms` | Total response time in milliseconds |
| `oom_triggered` | Whether GPU out-of-memory fallback activated |
| `session_id` | Browser session identifier |

### View the latest 10 queries:

```bash
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai -e "
SELECT id, timestamp, patient_id, LEFT(query, 50) AS query, pipeline_mode, elapsed_ms
FROM clinical_audit_log
ORDER BY timestamp DESC
LIMIT 10;"
```

**Expected output:**
```
+-----+---------------------+-------------+------------------------------------+--------------+------------+
| id  | timestamp           | patient_id  | query                              | pipeline_mode| elapsed_ms |
+-----+---------------------+-------------+------------------------------------+--------------+------------+
| 539 | 2026-06-28 22:08:07 | 000000036   | Show all vital signs               | MedRAG + KG  |      52188 |
| 538 | 2026-06-28 22:07:08 | 000000036   | Show all vital signs               | MedRAG + KG  |     227843 |
| 537 | 2026-06-28 22:03:57 | 000000036   | What is this patient glucose trend?| MedRAG + KG  |     212928 |
+-----+---------------------+-------------+------------------------------------+--------------+------------+
```

### Count total queries logged:

```bash
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai -e "
SELECT COUNT(*) AS total_queries,
       MIN(timestamp) AS first_query,
       MAX(timestamp) AS last_query
FROM clinical_audit_log;"
```

### Queries by pipeline mode:

```bash
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai -e "
SELECT pipeline_mode, COUNT(*) AS query_count, AVG(elapsed_ms) AS avg_ms
FROM clinical_audit_log
GROUP BY pipeline_mode;"
```

### See full LLM response for a specific query:

```bash
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai -e "
SELECT id, timestamp, patient_id, query, pipeline_mode, elapsed_ms,
       LEFT(llm_response, 500) AS response_preview
FROM clinical_audit_log
WHERE id = 539\G"
```

### Find all queries for a specific patient:

```bash
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai -e "
SELECT id, timestamp, query, pipeline_mode, elapsed_ms, oom_triggered
FROM clinical_audit_log
WHERE patient_id = '000000509'
ORDER BY timestamp DESC
LIMIT 20;"
```

### Test audit logging is working (send a query and immediately check the log):

```bash
# Step 1: Send a query
curl -s -X POST "http://localhost:8001/chat-agent/query" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "000000509", "query": "audit log test query"}' > /dev/null &

# Step 2: After ~30 seconds, check the latest log entry
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_ai -e "
SELECT id, timestamp, patient_id, query, pipeline_mode, elapsed_ms
FROM clinical_audit_log
ORDER BY timestamp DESC LIMIT 1;"
```

You should see your `"audit log test query"` appear as the most recent row.

### Where in the code this happens:

File: `FHIR_LLM_UA/backend/app/api/chat_agent.py`

The audit log write happens inside the `/chat-agent/query` endpoint handler:
```python
# Writes to llm_ua_ai.clinical_audit_log
conn.execute(text("""
    INSERT INTO llm_ua_ai.clinical_audit_log
      (timestamp, patient_id, query, pipeline_mode, retrieved_count,
       llm_response, sources_used, intent_classified, elapsed_ms, oom_triggered, session_id)
    VALUES (NOW(), :patient_id, :query, :pipeline_mode, :retrieved_count,
            :llm_response, :sources_used, :intent, :elapsed_ms, :oom, :session_id)
""", {...})
```

This write is wrapped in `try/except` — a logging failure will not block the clinical response.

---

## 10. Re-indexing Patient Data into Elasticsearch

Required when new patients are added to MySQL, or if the ES index is corrupted/empty.

### Index a single patient:

```bash
curl -s -X POST "http://localhost:8001/chat-agent/index-patient" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "000000509"}'
```

**Expected:** `{"status": "success", "patient_id": "000000509", "documents_indexed": 847}`

### Index all patients (runs in background, non-blocking):

```bash
curl -s -X POST "http://localhost:8001/chat-agent/index-all-patients"
```

**Expected:** `{"status": "started", "message": "Indexing all patients in background"}`

Monitor progress:
```bash
tail -f /tmp/backend.log | grep -i "index"
```

### Verify ES index health:

```bash
# Check document count
curl -s "http://localhost:9200/patient_data/_count" | python3 -m json.tool
# Expected: {"count": 150000+, "_shards": {...}}

# Verify a specific patient's data is indexed
curl -s "http://localhost:9200/patient_data/_search" \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"enterprise_patient_id": "000000509"}}}' \
  | python3 -m json.tool | grep '"total"'
# Expected: "value": 847 (or similar)
```

---

## 11. Stopping All Services

### Stop Backend + Frontend (safe, automatic)

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./stop_all.sh
```

This stops the backend and frontend. It intentionally **does not stop Elasticsearch** because ES may be shared with other users.

### Stop Elasticsearch (manually, when needed)

First find the ES process ID:
```bash
ps aux | grep elasticsearch | grep -v grep | grep java | awk '{print $2}'
```

Before killing, confirm it belongs to you (`kchollet`):
```bash
ps -o user,pid,cmd -p <PID_FROM_ABOVE> | head -2
```

If it says `kchollet` in the user column, kill it:
```bash
kill <PID_FROM_ABOVE>
```

Confirm it stopped:
```bash
curl -s http://localhost:9200/_cluster/health 2>/dev/null || echo "Elasticsearch is stopped"
```

### Stop everything in one go (all three)

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED

# 1. Backend + Frontend
./stop_all.sh

# 2. Elasticsearch — get PID first, verify it's yours, then kill
ES_PID=$(ps aux | grep elasticsearch | grep java | grep -v grep | awk '{print $2}' | head -1)
echo "ES PID: $ES_PID — owned by: $(ps -o user= -p $ES_PID 2>/dev/null)"
# Only run the next line if the owner is kchollet:
kill $ES_PID
```

> **Shared server rule:** Always verify the process owner before killing. Never kill processes owned by other users (e.g., `ckadirim`, `hembroff`).

### Verify everything is stopped

```bash
curl -s http://localhost:8001/health 2>/dev/null || echo "Backend: stopped"
curl -s http://localhost:9200 2>/dev/null || echo "Elasticsearch: stopped"
curl -s http://localhost:3000 2>/dev/null | head -1 || echo "Frontend: stopped"
```

---

## 12. Common Errors and Fixes

### Backend won't start / connection refused on port 8001

```bash
# Check if already running
ps aux | grep uvicorn | grep -v grep

# Check the log for errors
tail -50 /tmp/backend.log

# If GPU OOM, wait for other users' processes to finish
nvidia-smi
```

### `chart: null` in query response

The system should always return a chart for visualization queries. If you see `null`:
1. Verify ES is running: `curl -s localhost:9200/_cluster/health | grep status`
2. Check patient data is indexed: run index-patient for that patient_id
3. Check backend log for exceptions: `tail -100 /tmp/backend.log | grep ERROR`

### `{"status":"ok","db":"error"}` on health check

MySQL connection failed. Verify:
```bash
mysql -u llm_ua_reader -p'P@ssw0rd' llm_ua_enterprise -e "SELECT 1;"
```

If it fails, check if MySQL is running:
```bash
systemctl status mysqld 2>/dev/null || service mysql status 2>/dev/null
```

### LLM response is empty or truncated

GPU may be out of memory. Check:
```bash
nvidia-smi
```

If VRAM is full with someone else's process, wait or contact that user. Do not kill other users' processes.

### Audit log query returns "Access denied"

The `llm_ua_reader` user needs SELECT on `llm_ua_ai`:
```bash
mysql -u root -p -e "GRANT SELECT ON llm_ua_ai.* TO 'llm_ua_reader'@'localhost';"
```

### Elasticsearch disk space warning

```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./scripts/fix_elasticsearch_disk_space.sh
```
