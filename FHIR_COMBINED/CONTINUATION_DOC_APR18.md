# MedRAG Research — Full Continuation Document
**Last updated:** 2026-04-18 (April 18 session complete)
**Branch:** `main` | Repo: `karthikkumarcholleti/Generative-AI-User-Agent-using-Elasticsearch-and-RAG`
**Patient used for all prior tests:** `000000509` (41 conditions, 200 observations)
**Services status:** STOPPED (were shut down cleanly after March 30 session)

---

## ⚡ START HERE — First Things To Do

### Step 1: Start Elasticsearch
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
bash start_all.sh
# Wait 30 seconds, then verify:
curl -s http://localhost:9200/_cluster/health | python3 -m json.tool | grep status
# Expected: "status": "green" or "yellow"
```

### Step 2: Start the backend
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/backend
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1 \
  > /tmp/backend.log 2>&1 &
echo $! | tee /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/backend.pid
sleep 60
curl -s http://localhost:8001/health
# Expected: {"status":"ok","db":"ok"}
```

### Step 3: Quick sanity checks
```bash
# Verify HbA1c aliases still work post-reindex (should be 30 hits)
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/backend
python3 -c "
from app.api.elasticsearch_client import es_client
for term in ['hemoglobin a1c', 'bun', 'cholesterol']:
    r = es_client.client.search(index='patient_data', body={
        'query': {'bool': {'must': [
            {'match': {'content': term}},
            {'term': {'patient_id': '000000509'}}
        ]}}
    })
    print(f'{term}: {r[\"hits\"][\"total\"][\"value\"]} hits')
# Expected: hemoglobin a1c:~30  bun:~12  cholesterol:~18
"

# Verify USE_MEDRAG is True
grep "USE_MEDRAG" app/api/rag_service.py | head -3

# Verify MAX_NEW_TOKENS is 1200
grep "MAX_NEW_TOKENS" app/core/llm.py | head -3

# Check latest comparison file exists
ls -lt /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/scripts/comparison_results/
# Latest file should be: comparison_20260330_232416.{json,md}
```

### Step 4: Where we left off — RESUME HERE
We were in the middle of **fixing 6 visualization gaps** to make charts production-ready for real UPHP clinicians. See Section 6 for the full gap list and Section 7 for the implementation plan.

**Recommended order to fix gaps:**
1. **Gap 6 — Unit normalization** (prevents misleading charts from mmol/L vs mg/dL mixing)
2. **Gap 1 — Reference range bands** (adds normal/abnormal color zones to all charts)
3. **Gap 3+4 — Combined disease charts with dual y-axis** (CKD, Diabetes, Liver, Lipids, Heart Failure)
4. **Gap 2 — Encounter context tooltip** (encounter type only — AMB/IMP/EMER — where available)
5. **Gap 5 — Clinical event annotations** (defer — encounter reason data too sparse)

---

## 1. Full System Architecture

| Component | Details |
|---|---|
| **LLM** | Llama 3.1 8B, 4-bit BitsAndBytes quantization, `device_map="auto"`, 2× Tesla T4 GPUs |
| **MAX_NEW_TOKENS** | 1200 (line 30 of `backend/app/core/llm.py`) |
| **GPU serialization** | `_gen_lock` in `llm.py` — serializes all GPU generation to prevent OOM |
| **Backend** | FastAPI + Uvicorn, port 8001, `app.main:app` |
| **Frontend** | Next.js, port 3000 |
| **Search** | Elasticsearch 8.14.0, index `patient_data`, hybrid BM25 + kNN |
| **Embedding model** | `all-MiniLM-L6-v2` (SentenceTransformers), 384 dimensions |
| **Database** | MySQL, database `llm_ua_clinical`, user `llm_ua_reader` / `P@ssw0rd` |
| **Total patients indexed** | 3,254 (full reindex completed March 30) |
| **USE_MEDRAG** | `True` (line 25 of `backend/app/api/rag_service.py`) |

### Data Flow (how a query is processed)
```
Clinician query
     ↓
Intent Classifier (classifies: observations / conditions / analysis / visualization / general)
     ↓
Elasticsearch hybrid search (BM25 + kNN) → top 100 documents, sorted by date DESC
     ↓
Context Assembly (deduplicate by display+date, implausibility filter, sort chronologically)
     ↓
[If USE_MEDRAG=True] KG Pipeline → match patient evidence → build DDx context block
     ↓
Query-type detection (_apply_ddx: full 5-step DDx OR compact direct-answer)
     ↓
LLM (Llama 3.1 8B) → response text
     ↓
Intelligent Visualization → auto-generate chart if numeric observations in retrieved data
     ↓
Response to clinician (text + optional chart)
```

### Two separate pipelines: LLM text vs Charts
**CRITICAL architectural fact**: Charts and LLM text answers are produced by completely independent pipelines:

- **LLM text pipeline**: ES retrieves top 100 docs → context assembly → LLM → text answer
- **Chart pipeline**: Direct ES query with `size: 500`, `data_type=observations`, sorted by date ASC — completely bypasses the 100-doc LLM cap

This means charts are ALWAYS more complete than what the LLM text describes. If a patient has 15 heart rate records and the query is vague enough that only 10 appear in the top-100 ES results, the LLM text mentions 10 readings but the chart shows all 15.

---

## 2. Key Code Files and Their Roles

### `backend/app/api/rag_service.py` (2022 lines)
The central RAG + MedRAG pipeline file.

| Line(s) | What it does |
|---|---|
| Line 25 | `USE_MEDRAG = True` — toggle to switch between Standard RAG and MedRAG |
| Lines 561–589 | ES retrieval: top 100 docs, sorted newest first |
| Lines 652–662 | Group by data_type BEFORE limiting. Comment: "Do NOT limit observations/conditions — keep ALL" |
| Lines 759–808 | `unique_observations` dict: deduplicates by `(display, date)` key, then sorts chronologically |
| Lines 820–839 | **Fix A** — Implausibility filter: blocks Cholesterol<10, Creatinine<0.05, Glucose<0.5, Hemoglobin<1 from context |
| Lines 1105–1138 | Query-type detection: `_ddx_intent_keywords`, `_value_lookup_overrides`, `_apply_ddx` flag |
| Lines 1150–1210 | Two-branch prompt construction: DDx 5-step format vs non-DDx direct-answer format |
| Lines 1328–1347 | **Fix A** also applied in OOM-retry branch |

### `backend/app/api/medrag_knowledge_graph.py` (971 lines)
The MedRAG 4-tier Diagnostic Knowledge Graph.

| Line(s) | What it does |
|---|---|
| `DIAGNOSTIC_KG` dict | 4-tier hierarchy: Category → Family → Disease → Distinguishing Features. Built from SNOMED-CT/ICD-10 |
| Line ~695 | `match_patient_evidence()` — scans retrieved observations against KG disease criteria |
| Line ~695 | Implausibility guard in KG too — cholesterol<10, creatinine<0.1, glucose<1 blocked |
| Line ~737 | `patient_units` dict — tracks unit per observation type for KG display |
| Line ~800 | `build_kg_context()` — full DDx block with ? gaps labeled as "Diagnostic gaps per KG clinical guidelines" |
| Line ~872 | `build_kg_summary()` — compact KG for non-DDx queries: no ? gaps, only confirmed evidence |

### `backend/app/api/chat_agent.py` (1310 lines)
Main API endpoint handler.

| Line(s) | What it does |
|---|---|
| Line 111 | `get_patient_data_from_db(patient_id, for_indexing=False)` |
| Lines 123–126 | Runtime MySQL limits: conditions=50, observations=200, encounters=50, notes=10 |
| Line 530 | Chart visualization pipeline: `size: 500`, sorted by date ASC — independent of LLM pipeline |
| Lines 823–824, 878–879 | `for_indexing=True` → 10,000 limits (effectively unlimited, used during reindex) |

### `backend/app/api/elasticsearch_client.py` (807 lines)
ES indexing and hybrid search.

- Lines 200–400: All records indexed at index time with no cap
- Each FHIR record = one ES document (no chunking — FHIR records are atomic)
- `enhance_observation_content()` injects LOINC aliases into `content` field at index time

### `backend/app/api/loinc_code_mapper.py` (611 lines)
Maps raw LOINC display names to human-readable aliases for BM25 searchability.

- 54 LOINC codes mapped
- 46 `LOINC_DISPLAY_ALIASES` entries
- Key fix: `"HEMOGLOBIN A1C/HEMOGLOBIN.TOTAL:MFR:PT:BLD:QN:"` → injects `["hba1c", "a1c", "glycated hemoglobin", ...]`
- Result: HbA1c BM25 hits 0 → 30, BUN 0 → 12, Cholesterol 0 → 18

### `backend/app/api/intelligent_visualization.py` (937 lines — MODIFIED APR 18)
Determines whether to generate a chart and what type.

**April 18 changes made:**
1. `_identify_observation_type()` — expanded from 12 types to 50+ types (full clinical coverage)
2. `filter_observations_by_answer_relevance()` — expanded related-terms dict from 11 to 40+ types
3. `is_observation_query` trigger — now fires for ANY intent when numeric observations exist in retrieved data
4. `specific_observation_keywords` — expanded from 11 to 55 entries (all lab categories)
5. `condition_to_obs_map` — expanded from 6 to 35 condition → lab mappings

### `backend/app/api/visualization_service.py` (3454 lines — MODIFIED APR 18)
Chart data generator.

**April 18 changes made:**
1. Added module-level `OBSERVATION_COLOR_MAP` dict (64 entries covering all clinical types)
2. Added `_get_obs_color(observation_name)` helper function
3. Replaced all 4 inline `color_map` dicts throughout the file with calls to `_get_obs_color()`
4. Colors now consistent across all chart types (vitals, metabolic, renal, hematology, electrolytes, liver, cardiac, thyroid)

### `backend/app/api/observation_categorizer.py` (280 lines — MODIFIED APR 18)
Groups observations into clinical categories for display.

**April 18 changes made:**
1. Added 5 new categories: `cardiac_markers`, `thyroid`, `coagulation`, `diabetes_markers`
2. Updated `CATEGORY_PRECEDENCE` list to include the new categories in clinical priority order

---

## 3. All v7 Code Fixes (Status: ALL COMPLETE as of March 30)

### Fix A — Context-level Implausibility Filter ✅
**Problem**: Cholesterol=1.0 mg/dL was appearing in LLM context and on charts, making the LLM say "cholesterol is dangerously low". This was a hospital data entry error (value stored in wrong unit).

**Solution applied**: Added filter in `rag_service.py` at lines 820–839 (main context path) and lines ~1330–1347 (OOM-retry path). The filter runs AFTER ES retrieval but BEFORE context string assembly.

```python
# What the filter blocks:
("cholesterol" in display_lower and value < 10)          # Real cholesterol is 100-300 mg/dL
("creatinine" in display_lower and value < 0.05)         # Real creatinine is 0.5-10 mg/dL
("glucose" in display_lower and value < 0.5)             # Real glucose is 70-500 mg/dL
("hemoglobin" in display_lower and "a1c" not in display_lower and value < 1)  # Real Hgb is 7-18 g/dL
```

**What it does NOT block**: Values that are too HIGH (e.g., glucose=9999). This is a known gap — not fixed yet.

**Guard for ratios**: `"ratio" not in display_lower` ensures creatinine/creatinine-ratio (which can be a small decimal) is not blocked.

### Fix B — Top-15 Cap for Non-DDx Queries ✅
**Problem**: For specific lab queries like "what are the creatinine values?", the top-100 ES results included CBC (white blood cells, erythrocytes, etc.) which scored similarly to creatinine in ES. This filled the LLM prompt with irrelevant observations.

**Solution applied**: In `rag_service.py` lines 1128–1138. When `_apply_ddx=False` (non-DDx queries), retrieved docs are sorted by ES score and trimmed to top 15 before context assembly. DDx queries still use all 100 docs (they need broad context to reason across conditions).

### Fix C — Plain-text DDx Format (No Bold) ✅
**Problem**: LLM was generating `**bold text**` in responses, which looks wrong in the clinical UI.

**Solution applied**: The DDx user prompt now explicitly begins with:
```
STRICT RULES — failure to follow ANY of these will be marked as incorrect:
- PLAIN TEXT ONLY. No asterisks (*). No double-asterisks (**). No bold. No markdown headers.
```
And uses the numbered format `1. Most likely diagnosis: [...]` instead of bold headers.

### Fix D — Tightened Value-Lookup Override ✅
**Problem**: The phrase `"what is the"` was in `_value_lookup_overrides`, which blocked Q3 CVD DDx query ("What is the supporting evidence?") from triggering the DDx format.

**Solution applied**: Removed `"what is the"` from the overrides list. Now only strong leading-phrase overrides are in the list:
```python
_value_lookup_overrides = [
    "what do the", "what does the",
    "what do ", "what does ",
    "tell me the", "show me the",
    "list the", "give me the",
    "what are the values", "what are the levels",
    "what are the results", "what are the readings",
]
```

---

## 4. Comparison Results Summary

### Best results: v7 — file `scripts/comparison_results/comparison_20260330_232416.{json,md}`

| Query | Winner | Key Reason |
|---|---|---|
| Q0: DDx (most likely diagnosis) | MedRAG | Structured 5-step DDx, opens with "Essential Hypertension", no bold |
| Q1: Glucose/HbA1c metabolic status | MedRAG slightly | More complete glucose trend + KG T2DM note |
| Q2: Creatinine/kidney | Tie (RAG slightly cleaner) | Both found BUN, both correct. MedRAG adds some CBC items |
| Q3: CVD signs | MedRAG decisively | DDx correctly fires, opens with CHF, no Cholesterol=1.0, targeted follow-up |
| Q4: General health summary | MedRAG | Comprehensive with structured reasoning |

**Remaining minor issues (acceptable for paper)**:
- Q2 MedRAG still lists some CBC items alongside kidney labs (CBC scores similarly in ES for kidney queries)
- Q2 MedRAG truncates at "Monocytes/100 Leukocytes: 4." — hits MAX_NEW_TOKENS=1200 during long observation list

---

## 5. Explanation of Core Mechanisms (for understanding before continuing)

### How the Implausibility Filter Works (detailed)
See Section 3 Fix A above. In plain language:
1. The pipeline retrieves observations from ES
2. For EACH observation, it tries to parse the value as a float number
3. It lowercases the display name of the observation
4. It applies threshold rules — if the number is below a physiologically impossible floor for that lab type, the observation is silently discarded
5. The observation never appears in the LLM prompt and never appears on a chart

**Example**: `Total Cholesterol: 1.0 mg/dL` — real cholesterol is 100–300 mg/dL. Value 1.0 is either a unit error (should be mmol/L = ~38.6 mg/dL) or a data entry error. Either way, it is blocked.

**What it does NOT cover yet (future fix needed)**:
- Values above a physiological ceiling (e.g., glucose=99999)
- Unit mismatch without implausibility (e.g., glucose stored in mmol/L when system expects mg/dL — value of 5.0 mmol/L is valid but will be plotted wrong if mixed with mg/dL values of 90)

### How Condition → Lab Mapping Works (detailed)
The mapping in `intelligent_visualization.py → should_generate_visualization()` answers: "given a disease keyword in the query, which labs should be auto-charted?"

**Mechanism**:
1. Intent classifier returns `intent_type = "conditions"` (or general/analysis)
2. Query text is scanned for 35 disease keyword entries in `condition_to_obs_map`
3. For each matched disease, the list of associated lab types is retrieved
4. The code checks: do those lab types actually exist in the current patient's retrieved_data?
5. If yes → generates a chart for each found lab type
6. If no → no chart (the "no empty charts" rule)

**Complete mapping table (implemented April 18)**:
```
Metabolic:
  diabetes / diabetic / hyperglycemia / insulin → [glucose, a1c]

Cardiovascular:
  hypertension / high blood pressure → [blood pressure]
  heart failure → [bnp, troponin, sodium, potassium]
  coronary → [troponin, cholesterol, ldl]
  myocardial → [troponin, bnp]
  atrial fibrillation → [heart rate, inr]
  cholesterol / dyslipidemia / lipid → [cholesterol, ldl, hdl, triglycerides]

Renal:
  kidney disease / ckd / renal / nephropathy → [creatinine, gfr, bun]
  dialysis → [creatinine, bun, potassium, phosphorus]

Liver:
  liver → [alt, ast, bilirubin, albumin, alp]
  hepatitis → [alt, ast, bilirubin]
  cirrhosis → [alt, ast, albumin, bilirubin, inr]
  jaundice → [bilirubin, alt, ast]

Hematology / Oncology:
  anemia → [hemoglobin, hematocrit, rbc, mcv]
  bleeding → [platelets, inr, hemoglobin]
  leukemia → [wbc, platelets, hemoglobin]
  infection / sepsis → [wbc, neutrophils]

Electrolytes:
  electrolyte → [sodium, potassium, calcium, magnesium, chloride, bicarbonate]
  hyponatremia → [sodium]
  hyperkalemia / hypokalemia → [potassium]
  acidosis → [bicarbonate, anion gap]

Thyroid:
  thyroid / hypothyroid / hyperthyroid → [tsh, t4]

Respiratory:
  copd / asthma / pneumonia → [oxygen saturation, respiratory rate]

Nutrition:
  obesity → [bmi, weight, glucose, cholesterol]
  malnutrition → [albumin, weight, total protein]
```

---

## 6. The 6 Visualization Gaps — Full Analysis

These were identified April 18 as the gaps preventing production use by real UPHP clinicians.

### Gap 1 — No Reference Range Bands on Charts 🔴 CRITICAL / NOT YET FIXED

**The problem in detail**:
Charts show raw trend lines and dots. There are no visual zones indicating what is normal vs. borderline vs. abnormal. A clinician looking at creatinine values of `[0.9, 1.1, 1.4, 1.8, 2.3]` across dates cannot instantly see when the values crossed from normal into CKD stage 2 without mentally doing math.

**What real clinical systems do (Epic, Cerner, Meditech)**:
- Green shaded band for normal range (e.g., creatinine 0.6–1.2 mg/dL)
- Yellow/orange zone for borderline (e.g., 1.2–1.5)
- Red zone for clinically significant elevation (e.g., >1.5)

**Patient safety risk**: Without reference bands, a clinician might glance at an upward-trending line and not register the severity. For UPHP production use, this is a clinical safety gap.

**Implementation approach**:
- Add a `REFERENCE_RANGES` dictionary in `visualization_service.py` with min/max normal values for all 50+ observation types
- For each chart, add Chart.js annotation plugin annotations (horizontal lines + shaded regions) marking the normal range
- Color the actual data points: green if in range, yellow if borderline, red if outside range

**Example reference ranges needed**:
```python
REFERENCE_RANGES = {
    "creatinine":        {"min": 0.6,  "max": 1.2,  "unit": "mg/dL",  "critical_high": 4.0},
    "glucose":           {"min": 70,   "max": 100,  "unit": "mg/dL",  "critical_high": 400},
    "a1c":               {"min": 4.0,  "max": 5.6,  "unit": "%",      "critical_high": 9.0},
    "hemoglobin":        {"min": 12.0, "max": 17.5, "unit": "g/dL",   "critical_low": 7.0},
    "sodium":            {"min": 136,  "max": 145,  "unit": "mEq/L",  "critical_low": 120},
    "potassium":         {"min": 3.5,  "max": 5.0,  "unit": "mEq/L",  "critical_high": 6.0},
    "bun":               {"min": 7,    "max": 25,   "unit": "mg/dL",  "critical_high": 100},
    "gfr":               {"min": 60,   "max": 120,  "unit": "mL/min", "critical_low": 15},
    # ... all 50+ types
}
```

---

### Gap 2 — No Encounter Context on Data Points 🔴 IMPORTANT / PARTIALLY FEASIBLE

**The problem in detail**:
Chart labels show dates like `2024-03-15`. A creatinine spike from 1.2 → 2.8 on that date means very different things depending on what was happening clinically:
- Day after starting NSAIDs → drug-induced AKI (urgent!)
- During sepsis hospitalization → expected, resolve when sepsis resolves
- Routine follow-up → newly detected CKD requiring workup

**What data is actually available (honest assessment)**:
| Data | Available | Reliable |
|---|---|---|
| Observation date | ✅ Always | ✅ Yes |
| Encounter date | ✅ Usually | ✅ Yes |
| Encounter type code (AMB/IMP/EMER) | ⚠️ Often present | ⚠️ Generic codes only |
| Encounter reason text | ❌ Rarely populated | ❌ Often NULL in Synthea data |
| Medication change on that date | ❌ Not indexed | ❌ No |

**What we CAN implement (honest scope)**:
- Show encounter type code (AMB=ambulatory, IMP=inpatient, EMER=emergency) on chart tooltip where available
- Use different point shapes for encounter types (circle=outpatient, triangle=inpatient, diamond=emergency)
- For data points without encounter info: just show the date, no fabrication

**What we CANNOT implement (data doesn't exist)**:
- Reason for encounter (too sparse in Synthea-generated data)
- Medication changes as vertical line annotations (medications not linked to observation dates in the current schema)

---

### Gap 3 — No Correlated Multi-Metric Disease Progression Charts 🟡 HIGH / NOT YET FIXED

**The problem in detail**:
Current code generates one chart per observation type. But disease progression requires seeing multiple correlated metrics together. Three separate charts for creatinine, GFR, and BUN require the clinician to mentally align dates across panels — this increases cognitive load and can cause them to miss the correlation.

**Which diseases need combined charts (and why)**:

**CKD (Chronic Kidney Disease)**:
- Creatinine (rises as kidneys fail) + GFR (falls as kidneys fail) + BUN (rises)
- These three move in concert — creatinine up, GFR down, BUN up = progressive CKD
- Combined chart shows the correlation immediately; three separate charts hide it

**Diabetes**:
- Glucose (snapshot blood sugar, day-to-day variability) + HbA1c (3-month average)
- Together they show: is the glucose trend consistent with the A1c? Are there unexplained spikes?
- Separate charts miss the validation that A1c provides for the glucose trend

**Liver Disease**:
- ALT + AST (liver inflammation markers, both in U/L — same scale, can share y-axis)
- Bilirubin (bile processing, mg/dL — different scale, needs separate y-axis)
- Albumin (protein synthesis, falls when liver fails, g/dL)
- ALT/AST rising + albumin falling = liver is both inflamed and losing function (much worse picture)

**Cardiovascular Risk (Lipid Panel)**:
- Total Cholesterol + LDL + HDL + Triglycerides (all in mg/dL, overlapping ranges — share y-axis fine)
- Seeing LDL going down while HDL goes up confirms the statin and lifestyle changes are working

**Heart Failure**:
- BNP (heart failure marker) + Troponin (heart muscle damage)
- Sodium + Potassium (electrolyte shifts in heart failure)

---

### Gap 4 — Y-Axis Scaling Problem for Multi-Unit Charts 🟡 HIGH / SOLVED WITH GAP 3

**The problem in detail**:
If two observations with very different value ranges are plotted on the same y-axis, the smaller-scale values appear almost flat even if they are changing significantly.

**Examples of incompatible scales**:
- Sodium (135–145 mEq/L) and Creatinine (0.6–10 mg/dL) — sodium dominates, creatinine appears flat
- Glucose (70–400 mg/dL) and HbA1c (4–14%) — glucose scale swamps A1c changes
- GFR (0–120 mL/min) and Creatinine (0–10 mg/dL) — can share axis with care since both change together

**Solution**: Chart.js dual y-axis — left y-axis for one group (e.g., GFR 0–120), right y-axis for another (e.g., creatinine 0–10). In Chart.js this is done with:
```javascript
datasets: [
  { label: "GFR", yAxisID: "y" },
  { label: "Creatinine", yAxisID: "y1" }
],
scales: {
  y: { position: "left", title: { text: "GFR (mL/min)" } },
  y1: { position: "right", title: { text: "Creatinine (mg/dL)" } }
}
```

**This is resolved as part of implementing Gap 3** — when building the combined disease charts, each dataset is assigned to the appropriate y-axis based on the unit compatibility rules.

---

### Gap 5 — No Clinical Event Annotations 🟡 MEDIUM / DEFERRED

**The problem in detail**:
A creatinine spike on a specific date has no annotation saying "Started NSAIDs" or "Admitted for sepsis". Without this context, the clinician cannot interpret the cause of changes.

**Why we defer this**:
- Medication start/stop dates are not systematically linked to observation dates in the current schema
- Encounter reason text is NULL for most records in Synthea-generated data
- This would require a separate data linkage pipeline that exceeds the current project scope

**What could be done in a future version**:
- Link observations to encounters by date range (±3 days)
- Show encounter type on a secondary bar chart below the trend line
- Pull medication changes from FHIR MedicationRequest resources and overlay as vertical markers

---

### Gap 6 — No Unit Consistency Validation 🟡 HIGH / NOT YET FIXED

**The problem in detail**:
The same lab test can appear in different units in different records in the database. If a patient's records span two lab systems (e.g., hospital uses mg/dL, clinic uses mmol/L), the chart will show both values on the same line with the wrong y-scale, making it appear as if there was a dramatic change that did not happen.

**Concrete dangerous example**:
- Record 1: Glucose = 90 mg/dL (normal)
- Record 2: Glucose = 5.0 mmol/L (same patient, different lab system — also normal, equals ~90 mg/dL)
- Chart shows: 90 → 5.0 — a dramatic apparent drop from 90 to 5 that looks like hypoglycemia

**Unit conversion table needed**:
```python
UNIT_CONVERSIONS = {
    "glucose": {
        "mmol/L": {"factor": 18.018, "target_unit": "mg/dL"},  # multiply by 18.018
    },
    "creatinine": {
        "µmol/L": {"factor": 0.01131, "target_unit": "mg/dL"},  # multiply by 0.01131
        "umol/L": {"factor": 0.01131, "target_unit": "mg/dL"},
    },
    "urea": {
        "mmol/L": {"factor": 2.801, "target_unit": "mg/dL"},
    },
    "cholesterol": {
        "mmol/L": {"factor": 38.67, "target_unit": "mg/dL"},
    },
    "hemoglobin": {
        "g/L": {"factor": 0.1, "target_unit": "g/dL"},
        "mmol/L": {"factor": 1.6113, "target_unit": "g/dL"},
    },
    "calcium": {
        "mmol/L": {"factor": 4.0, "target_unit": "mg/dL"},
    },
    "sodium": {
        "mmol/L": {"factor": 1.0, "target_unit": "mEq/L"},  # mmol/L = mEq/L for sodium
    },
    # ... etc.
}
```

**How the fix works**:
1. For each chart type, define a canonical target unit (e.g., glucose → mg/dL)
2. Before plotting, check each data point's unit field
3. If unit differs from canonical, apply conversion factor
4. If unit is unrecognized, log a warning but still plot (don't discard data)
5. Label the chart y-axis with the canonical unit

---

## 7. Implementation Plan — Where We Left Off

We completed the **analysis phase** on April 18. We have NOT yet started coding any of the 6 gap fixes. The implementation plan agreed upon:

### Phase 1: Gap 6 — Unit Normalization (DO THIS FIRST)
**Why first**: A misleading chart (wrong unit) is worse than no chart at all. This is a data integrity fix that must happen before any visual improvements.

**Files to modify**:
- `backend/app/api/visualization_service.py` — add `UNIT_CONVERSIONS` dict and `normalize_units()` function
- Call `normalize_units()` inside `extract_observation_data()` and `extract_observation_data_from_retrieved()` before data points are added to the list

**Test plan**:
1. Find a patient in the DB with observations in mixed units (or manually insert one)
2. Run a chart query and verify values are all in consistent units
3. Verify the y-axis label shows the canonical unit

---

### Phase 2: Gap 1 — Reference Range Bands
**Why second**: This adds the most immediate clinical value after unit correctness is guaranteed.

**Files to modify**:
- `backend/app/api/visualization_service.py` — add `REFERENCE_RANGES` dict and reference band annotations to all chart generators
- `backend/app/api/intelligent_visualization.py` — pass reference range info to chart generators

**How Chart.js reference bands work**:
```javascript
// In the chart options object:
plugins: {
  annotation: {
    annotations: {
      normalBand: {
        type: "box",
        yMin: 0.6, yMax: 1.2,  // for creatinine
        backgroundColor: "rgba(0, 255, 0, 0.1)",
        borderColor: "rgba(0, 200, 0, 0.3)"
      },
      criticalLine: {
        type: "line",
        yMin: 1.5, yMax: 1.5,
        borderColor: "rgba(255, 0, 0, 0.5)",
        borderDash: [5, 5]
      }
    }
  }
}
```

**Color point data points by range**:
- Normal: green dot
- Borderline: yellow dot
- Abnormal: red dot
- Critical: red dot with alert marker

---

### Phase 3: Gap 3+4 — Combined Disease Charts with Dual Y-Axis
**Why third**: Biggest clinical value for disease progression tracking.

**New chart types to implement in `visualization_service.py`**:
1. `ckd_progression` — creatinine (left y-axis, 0–10 mg/dL) + GFR (right y-axis, 0–120 mL/min) + BUN (right y-axis)
2. `diabetes_control` — glucose (left y-axis, 0–400 mg/dL) + A1c (right y-axis, 4–14%)
3. `liver_panel` — ALT + AST (left y-axis, 0–200 U/L, same scale) + bilirubin (right y-axis, 0–20 mg/dL)
4. `lipid_panel` — total cholesterol + LDL + HDL + triglycerides (all mg/dL, shared y-axis)
5. `heart_failure_markers` — BNP (left y-axis) + Troponin (right y-axis)

**New entries to add to `condition_to_obs_map` and `should_generate_visualization()`**:
```python
"ckd": "ckd_progression"      # instead of separate creatinine/gfr/bun charts
"diabetes": "diabetes_control" # instead of separate glucose/a1c charts
"liver": "liver_panel"         # instead of separate alt/ast/bilirubin charts
```

---

### Phase 4: Gap 2 — Encounter Context Tooltip (HONEST SCOPE)
**What we actually implement** (not what we wish we could):
- Pull encounter records for the patient from ES: `data_type=encounters`, filter by date range
- Match observation dates to nearest encounter (within ±1 day)
- Add encounter type (AMB/IMP/EMER) to chart point tooltip
- Use different point shapes for encounter types
- Gracefully omit where encounter data is missing — no fabrication

---

## 8. ROUGE, BLEU, and Clinical F1 — Evaluation Metrics Discussion

This topic was discussed April 18 as part of validating system accuracy. Summary:

### ROUGE
Measures word overlap between LLM answer and a reference (human-written) answer.
- `ROUGE-1`: matching single words
- `ROUGE-2`: matching two-word sequences
- Best for: summarization questions, general clinical descriptions
- Weakness: penalizes correct paraphrases ("elevated" vs "high")

### BLEU
Measures precision — how many n-grams in the LLM answer appear in the reference.
- Best for: detecting hallucinations (invented values not in the reference)
- Weakness: penalizes correct paraphrases

### Clinical F1 (RECOMMENDED for this project)
Define a set of expected clinical facts (e.g., `{creatinine: 2.3, gfr: 45, bun: 28}`), extract facts from LLM answer, compute:
- Precision: of facts LLM stated, what fraction are correct?
- Recall: of all expected facts, what fraction did LLM mention?
- F1 = 2 × (Precision × Recall) / (Precision + Recall)

**Why Clinical F1 is best for the paper**:
- ROUGE/BLEU borrowed from NLP — clinical reviewers question validity
- Clinical F1 directly measures what matters: did the LLM identify the right values?
- The MedRAG vs Standard RAG comparison is strongest when measured on clinical factual completeness

**Concrete implementation plan (not done yet)**:
1. Pick 20 representative queries (the 7 comparison queries × 3 patient variants)
2. Write ground-truth answers manually (~2 hours work)
3. Run the system, extract numeric values from responses using regex
4. Compare extracted values vs. ground truth → compute F1 per query, average across queries
5. Report: Standard RAG F1 = X.XX, MedRAG F1 = X.XX, improvement = +Y.Y%

---

## 9. Research Paper Status

### Paper thesis
MedRAG + KG augmentation demonstrably improves differential diagnosis quality over standalone RAG:
1. Structured DDx reasoning (Most Likely → Alternatives → Evidence hierarchy)
2. Proactive diagnostic gap questioning (KG-driven follow-up questions)
3. Retrieval gap compensation (KG adds clinical criteria even when ES doesn't retrieve specific values)

### Paper sections status
- `PAPER_SECTIONS/LITERATURE_REVIEW_COMPLETE.md` — ✅ written
- `PAPER_SECTIONS/METHODOLOGY_COPY_PASTE.md` — ✅ written
- `PAPER_SECTIONS/RESULTS_COPY_PASTE.md` — ✅ written (based on v7 results)
- `PAPER_SECTIONS/DESCRIPTION_COPY_PASTE.md` — ✅ written

### Strongest evidence for paper (from v7 results)
- Q0: MedRAG 1146 chars (structured DDx) vs RAG 128 chars (gave up) → Gap compensation working
- Q3 CVD: MedRAG lists full cardiovascular history + risk factors; RAG abandoned query due to missing cholesterol → KG layer adds value beyond raw retrieval
- ES alias fix measurable impact: HbA1c BM25 hits 0 → 30 (a concrete engineering contribution)
- KG layer adds zero GPU cost (pure Python in-memory dict) — both modes use same Llama 3.1 8B

---

## 10. Visualization Improvement — Real-World Clinical Justification

This topic was discussed extensively April 18. Summary of why each gap matters for UPHP clinicians:

**The architecture is correct** (raw ES data → charts, bypassing LLM 100-doc cap).

**But the current implementation is incomplete for production** because:

1. **Without reference bands (Gap 1)**: A clinician could miss that creatinine=1.8 is abnormal if there is no visual zone showing that normal is 0.6–1.2. In a time-pressured ER or clinic, this is a real risk.

2. **Without unit normalization (Gap 6)**: A chart mixing mg/dL and mmol/L values for the same lab will show a false dramatic change. A glucose value jumping from 90 to 5 on the chart (because one lab uses mg/dL and another uses mmol/L) could trigger unnecessary clinical action.

3. **Without combined disease charts (Gap 3+4)**: Seeing creatinine, GFR, and BUN as three separate charts forces the clinician to mentally align dates across panels. A single CKD progression chart shows the correlation pattern instantly, which is how nephrologists actually reason about kidney disease progression.

4. **Encounter context (Gap 2)**: Even just knowing "this reading was taken during an inpatient stay" vs "this was a routine outpatient visit" changes clinical interpretation. The data (AMB/IMP/EMER codes) exists for most records and is easy to surface.

---

## 11. Quick Reference — File Locations

```
Project root:
/mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/

Key source files:
FHIR_LLM_UA/backend/app/api/rag_service.py              ← Central RAG/MedRAG pipeline
FHIR_LLM_UA/backend/app/api/medrag_knowledge_graph.py   ← KG DDx engine
FHIR_LLM_UA/backend/app/api/chat_agent.py               ← API endpoints
FHIR_LLM_UA/backend/app/api/elasticsearch_client.py     ← ES indexing + search
FHIR_LLM_UA/backend/app/api/loinc_code_mapper.py        ← LOINC alias injection
FHIR_LLM_UA/backend/app/api/intelligent_visualization.py ← Auto-chart logic (APR18 expanded)
FHIR_LLM_UA/backend/app/api/visualization_service.py    ← Chart generators (APR18 expanded)
FHIR_LLM_UA/backend/app/api/observation_categorizer.py  ← Category grouping (APR18 expanded)
FHIR_LLM_UA/backend/app/core/llm.py                     ← LLM wrapper, MAX_NEW_TOKENS

Comparison results:
scripts/comparison_results/comparison_20260330_232416.json  ← BEST (v7)
scripts/comparison_results/comparison_20260330_232416.md    ← BEST (v7) human-readable

Paper sections:
PAPER_SECTIONS/LITERATURE_REVIEW_COMPLETE.md
PAPER_SECTIONS/METHODOLOGY_COPY_PASTE.md
PAPER_SECTIONS/RESULTS_COPY_PASTE.md
PAPER_SECTIONS/DESCRIPTION_COPY_PASTE.md

This document:
CONTINUATION_DOC.md                    ← original (March 30 state)
CONTINUATION_DOC_APR18.md             ← THIS FILE (April 18 state — most current)
```

---

## 12. Next Session — Exact Steps to Resume

When you come back:

1. Read Section "START HERE" at the top of this file
2. Start ES + backend (commands in Section START HERE)
3. Run quick sanity checks (Section START HERE Step 3)
4. Start with **Gap 6 — Unit Normalization** (Section 7 Phase 1)
5. In `visualization_service.py`, add the `UNIT_CONVERSIONS` dict and `normalize_units()` function
6. Test with patient `000000509`
7. Then proceed to Gap 1 (reference bands), then Gap 3+4 (combined disease charts)

**If you want to test the current system first before fixing gaps**:
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
python scripts/compare_rag_vs_medrag.py \
  --patient_id 000000509 \
  --output_dir scripts/comparison_results \
  --query_indices 0 1 2 3
```
This will regenerate the v7 comparison and let you verify everything is still working after the April 18 code changes.
