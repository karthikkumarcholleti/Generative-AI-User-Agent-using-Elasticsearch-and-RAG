# VISUALIZATION GAPS — Continuation Document
**Last updated:** April 19, 2026  
**Author:** GitHub Copilot + Karthik  
**Purpose:** Complete record of all visualization gap work so any session can pick up exactly where we left off.

---

## TABLE OF CONTENTS
1. [System Architecture](#1-system-architecture)
2. [Services & How to Start](#2-services--how-to-start)
3. [Gap Fix Summary](#3-gap-fix-summary)
4. [Detailed Changes Per File](#4-detailed-changes-per-file)
5. [What Was Tested & How](#5-what-was-tested--how)
6. [Known Data Limitations](#6-known-data-limitations)
7. [Remaining Work](#7-remaining-work)
8. [Key Commands Reference](#8-key-commands-reference)
9. [Important Patient IDs for Testing](#9-important-patient-ids-for-testing)

---

## 1. SYSTEM ARCHITECTURE

```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐
│   Frontend       │    │   Backend (LLM)  │    │ Elasticsearch │
│   Next.js :3000  │◄──►│   FastAPI :8001   │◄──►│   8.14 :9200  │
│   Recharts       │    │   Llama 3.1 8B   │    │ index:         │
│                  │    │   2× Tesla T4    │    │ patient_data   │
└─────────────────┘    └──────────────────┘    └───────────────┘
```

- **LLM**: Llama 3.1 8B, 4-bit quantization, MAX_NEW_TOKENS=1200
- **Frontend**: Next.js with **Recharts** (NOT Chart.js) for all visualizations
- **Backend**: FastAPI, entry point `app.main:app`
- **ES index**: `patient_data` — contains patients, observations, encounters, conditions, etc.
- **Chat API**: `POST /chat-agent/query` with body `{"patient_id": "...", "query": "..."}`
- **Pipeline**: MedRAG + Knowledge Graph — RAG-based (no model training/fine-tuning)
- **59 unique observation types** in ES (confirmed via aggregation)

### Key Directories
```
fhir_karthik/FHIR_COMBINED/
├── FHIR_LLM_UA/                          # Backend
│   ├── venv/                              # Python virtual env
│   └── backend/
│       └── app/
│           └── api/
│               ├── visualization_service.py      # ← HEAVILY MODIFIED (all gaps)
│               ├── intelligent_visualization.py  # ← MODIFIED (Gap 3+4 routing)
│               └── ...
├── FHIR_dashboard/
│   └── backend/
│       └── frontend/                      # Next.js app
│           ├── components/
│           │   ├── RechartsVisualization.tsx      # ← MODIFIED (all frontend gaps)
│           │   └── ConditionsAndComorbiditiesTable.tsx  # ← FIXED type error
│           ├── pages/
│           │   ├── generative-ai.tsx              # Main AI chat page (1956 lines)
│           │   └── generative-ai-NEW.tsx.bak      # Renamed temp scratch file
│           └── services/
│               └── llmApi.ts                      # TypeScript interfaces
└── VISUALIZATION_GAPS_CONTINUATION.md     # THIS FILE
```

---

## 2. SERVICES & HOW TO START

### Elasticsearch
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/elasticsearch-8.14.0
./bin/elasticsearch -d  # starts in background
# Verify:
curl -s http://localhost:9200/_cluster/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"
# Should print: green
```

### Backend (FastAPI + LLM)
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA
source venv/bin/activate
cd backend
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &
# Verify:
curl -s http://localhost:8001/health
# Should return: {"status":"ok","db":"ok"}
```

### Frontend (Next.js)
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_dashboard/backend/frontend
nohup npx next dev -p 3000 > /tmp/frontend.log 2>&1 &
# Verify:
curl -s http://localhost:3000 | head -1
```

### Stop Everything
```bash
pkill -f "uvicorn.*8001"
pkill -f "next"
pkill -f elasticsearch
```

---

## 3. GAP FIX SUMMARY

| Gap | Description | Status | Notes |
|-----|-------------|--------|-------|
| **Gap 6** | Unit Normalization | ✅ COMPLETE | Code correct, currently no-op (all ES data uses US-standard units with placeholder `"unit": "unit"`) |
| **Gap 1** | Reference Range Bands | ✅ COMPLETE | 58/59 observation types covered (all except UNKNOWN). Green normal zone + red critical lines |
| **Gap 3+4** | Combined Disease Progression + Dual Y-Axis | ✅ COMPLETE | 9 disease panels. Dual y-axis when value scales differ. ES fallback for missing labs |
| **Gap 2** | Encounter Context Tooltip | ✅ COMPLETE | Backend matches encounters by date ±1 day. Custom tooltip renders encounter info. Zero overhead when data unavailable |
| **Gap 5** | Clinical Event Annotations | ❌ DEFERRED | Not started. Was agreed to defer |

### Build Status
- **Frontend**: `npx next build` passes cleanly ✅ (as of April 19, 2026)
- **Backend**: No Python errors in our files (3 pre-existing `sqlalchemy` import warnings in unused code paths)

---

## 4. DETAILED CHANGES PER FILE

### 4.1 `visualization_service.py`
**Path**: `FHIR_LLM_UA/backend/app/api/visualization_service.py`  
**Size**: ~4,140 lines after all changes

#### A. Unit Normalization (Gap 6) — ~lines 80-160
- **`UNIT_CONVERSIONS`** dict: 12 observation types with conversion rules
  - glucose: mmol/L → mg/dL (×18.018)
  - creatinine: µmol/L → mg/dL (×0.01131)
  - hemoglobin: g/L → g/dL (×0.1)
  - calcium, sodium, potassium, chloride, magnesium, phosphorus, bilirubin, albumin, BUN
- **`normalize_units()`** function: Called at end of both `extract_observation_data()` and `extract_observation_data_from_retrieved()`. Fast-paths when all units are identical.
- **Current state**: No-op because all ES observations have `"unit": "unit"` (placeholder). Will activate automatically if real mixed-unit data is ever indexed.

#### B. Reference Ranges (Gap 1) — ~lines 160-370
- **`REFERENCE_RANGES`** dict: 58 observation types organized by clinical category:
  - Vitals (6): body temperature, heart rate, systolic BP, diastolic BP, respiratory rate, oxygen saturation
  - Metabolic (3): glucose (serum + blood), cholesterol, triglycerides
  - Renal (4): creatinine, BUN, GFR, BUN:Cr ratio
  - Hematology (16): hemoglobin, hematocrit, WBC, RBC, platelets, neutrophils, lymphocytes (%), lymphocytes (absolute), monocytes, eosinophils (%), eosinophils (absolute), basophils, MCV, MCH, MCHC, RDW, MPV, nucleated RBCs, metamyelocytes
  - Electrolytes (7): sodium, potassium, chloride, calcium, calcium ionized, magnesium, phosphate, CO2, anion gap
  - Liver (5): ALT, AST, ALP, bilirubin (total + indirect), albumin
  - Coagulation (5): PT, aPTT, INR, fibrinogen, D-dimer
  - Cardiac (2): troponin/BNP, CRP, lactate
  - Urine (3): WBC, pH, specific gravity
  - Other (3): lipase, vancomycin, total protein
- **`get_reference_lines()`** function: Takes observation display name, matches against REFERENCE_RANGES via substring, returns list of `{y, label, color, dash}` dicts for the frontend.
- **Injection points**: `referenceLines` added to chart payloads in 4 chart generators:
  1. `_generate_observation_trend_chart_from_retrieved` (RAG path)
  2. `generate_chart_from_extracted_values` (answer extraction path)
  3. `_generate_observation_trend_chart` (direct ES path)
  4. `_generate_combined_disease_chart_from_retrieved` (disease panels)

#### C. Disease Progression Panels (Gap 3+4) — ~lines 370-480
- **`DISEASE_PROGRESSION_PANELS`** dict: 9 panels, each with labs assigned to left/right y-axis:
  - `ckd`: Creatinine+Potassium (left), BUN+Calcium (right)
  - `diabetes`: Glucose (left), Potassium+Creatinine (right)
  - `liver`: ALT+AST+ALP (left), Bilirubin+Albumin (right)
  - `heart_failure`: NT-proBNP (left), Sodium+Potassium+Creatinine (right)
  - `anemia`: Hemoglobin+Hematocrit (left), RBC+MCV (right)
  - `lipid`: Cholesterol+Triglycerides (left), HDL+LDL (right)
  - `electrolytes`: Sodium+Chloride (left), Potassium+CO2+Calcium (right)
  - `coagulation`: PT+aPTT (left), INR+Fibrinogen (right)
  - `sepsis`: WBC+Platelets (left), Lactate+CRP (right)
- **`_CONDITION_TO_PANEL`** dict: 25+ keyword aliases → panel key (e.g., "kidney disease" → "ckd", "hepatitis" → "liver")
- **`_generate_combined_disease_chart_from_retrieved()`** method:
  - Extracts each lab from RAG retrieved_data first
  - Falls back to direct ES query for any labs not found
  - Builds dual-axis datasets with `yAxisID: "left"|"right"`
  - Emits `dualYAxis` payload with axis labels
  - Adds reference lines for the primary (first) lab
- **Route**: `combined_progression:X` handled in `generate_chart_data_from_retrieved()`

#### D. Encounter Context (Gap 2) — ~lines 485-580
- **`_encounter_cache`**: Per-patient encounter cache dict on VisualizationService
- **`_get_patient_encounters()`**: Fetches encounters from ES (up to 200), caches by patient_id
- **`_match_encounter_context()`**: For each observation date label, finds closest encounter within ±1 day. Returns `{encounter, reason, type}` or None.
- **Injection points**: `encounterContext` array added to chart payloads in 4 generators (same as reference lines). Only included when at least one match exists (zero overhead otherwise).

### 4.2 `intelligent_visualization.py`
**Path**: `FHIR_LLM_UA/backend/app/api/intelligent_visualization.py`  
**Size**: ~1,181 lines

#### Changes (Gap 3+4 routing):
- **In `should_generate_visualization()`**, disease panel check inserted **BEFORE** the generic visualization keywords check (~line 443):
  - Imports `_CONDITION_TO_PANEL` from `visualization_service`
  - Checks query words against `_CONDITION_TO_PANEL` keys
  - If matched → returns `combined_progression:{panel_key}` chart type
  - **CRITICAL**: This check MUST be before the visualization keywords block, otherwise queries like "kidney disease labs" get routed to `categorized_observations` by the generic keywords

### 4.3 `RechartsVisualization.tsx`
**Path**: `FHIR_dashboard/backend/frontend/components/RechartsVisualization.tsx`  
**Size**: ~540 lines

#### Changes:
- **Imports**: Added `ReferenceLine`, `ReferenceArea`, `Label` from Recharts
- **Data conversion** (`convertToRechartsData`): Attaches `_encounter` property from `encounterContext` array to each data point
- **`CustomTooltip` component** (Gap 2): Custom React tooltip that:
  - Shows formatted date
  - Lists each series value with color
  - Shows 🏥 encounter context section when `_encounter` is present
- **Reference lines** (Gap 1): In LineChart section:
  - `<ReferenceLine>` for each ref line (green dashed = normal, red dashed = critical) with `<Label>` on right side
  - `<ReferenceArea>` light green shaded zone between Low Normal and High Normal, with `yAxisId="left"`
- **Dual Y-Axis** (Gap 3+4):
  - Left `<YAxis yAxisId="left">` always rendered (with optional label when dual)
  - Right `<YAxis yAxisId="right" orientation="right">` conditionally rendered when `dualYAxis` payload exists
  - Wider right margin when dual axis active
  - `<Line>` components use `yAxisId={(dataset as any).yAxisID || 'left'}`
- **`<Tooltip>`**: Replaced with `<Tooltip content={<CustomTooltip />} />` in LineChart section

### 4.4 `ConditionsAndComorbiditiesTable.tsx`
**Path**: `FHIR_dashboard/backend/frontend/components/ConditionsAndComorbiditiesTable.tsx`
- Line 73: `group.conditions.length` → `(group.conditions?.length ?? 0)` — TypeScript "possibly undefined" fix

### 4.5 `generative-ai-NEW.tsx`
- **Renamed to `.bak`** — 31-line temp scratch file, no imports/exports. All content already in `generative-ai.tsx`.

---

## 5. WHAT WAS TESTED & HOW

### Gap 1 (Reference Ranges) — Coverage Test
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA
source venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'backend')
from app.api.visualization_service import get_reference_lines
# Tested all 59 observation display names from ES
# Result: 58/58 covered (UNKNOWN is the only miss — intentional)
"
```

### Gap 1 — API Test
```bash
curl -s -X POST http://localhost:8001/chat-agent/query \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"10","query":"Show me creatinine trend"}' | \
  python3 -c "import sys,json; c=json.load(sys.stdin).get('chart',{}); print('Ref lines:', len(c.get('referenceLines',[])))"
# Expected: Ref lines: 3 (Low Normal 0.6, High Normal 1.2, Critical High 4.0)
```

### Gap 3+4 (Disease Panels) — Kidney
```bash
curl -s -X POST http://localhost:8001/chat-agent/query \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"10","query":"Show me kidney disease labs"}' | \
  python3 -c "
import sys,json
chart = json.load(sys.stdin).get('chart')
if chart:
    print('Dual Y-Axis:', json.dumps(chart.get('dualYAxis')))
    for ds in chart['data']['datasets']:
        vals = [v for v in ds['data'] if v is not None]
        print(f'  {ds[\"label\"]}: {len(vals)} pts, yAxisID={ds.get(\"yAxisID\")}')
"
# Expected: 4 datasets (Creatinine, BUN, Potassium, Calcium), dual y-axis
```

### Gap 3+4 — Electrolytes
```bash
# Same pattern with query "Show me electrolyte panel trends"
# Expected: Sodium+Chloride (left), Potassium+Calcium (right), dual y-axis
```

### Frontend Build
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_dashboard/backend/frontend
npx next build
# Result: Compiled successfully ✅, all pages: /, /404, /conditions, /generative-ai, /metrics
```

---

## 6. KNOWN DATA LIMITATIONS

1. **All observations have `"unit": "unit"`** — no real units. Gap 6 normalize_units() is correct but currently a no-op fast-path.
2. **Most encounters have `date: null`** — only ~22 have dates, and those have `reason: null`. Gap 2 encounter context rarely activates.
3. **Values are US-standard** — glucose 53-1068 (mg/dL), creatinine 0.1-112.2, hemoglobin 6.9-17.0, sodium 124-148.
4. **Patient 10** has 1 data point per observation type (all from 2024-08-18) — trend charts show single dots.
5. **3 pre-existing `sqlalchemy` import errors** in `visualization_service.py` (~lines 3354, 3376, 3506) — in abnormal values chart methods that use SQL. Not related to our changes.

---

## 7. REMAINING WORK

### Completed
- ✅ Gap 6: Unit Normalization
- ✅ Gap 1: Reference Range Bands
- ✅ Gap 3+4: Combined Disease Progression + Dual Y-Axis
- ✅ Gap 2: Encounter Context Tooltip
- ✅ Frontend build passes cleanly

### Not Started
- ❌ **Gap 5: Clinical Event Annotations** — Deferred. Would overlay medication changes, procedure dates, diagnosis dates on charts as vertical annotation lines. Blocked by encounters/conditions having mostly null dates.

### Optional Improvements
- Add `referenceLines`, `dualYAxis`, `encounterContext` to TypeScript `ChartPayload` interface in `llmApi.ts` (currently accessed via `as any`)
- Find test patients with multiple timepoint observations for better trend demonstrations
- `USE_LLM_ABNORMAL_DETECTION` env var controls LLM vs threshold abnormal detection

---

## 8. KEY COMMANDS REFERENCE

### Quick Health Check
```bash
curl -s http://localhost:9200/_cluster/health | python3 -c "import sys,json; print('ES:', json.load(sys.stdin)['status'])"
curl -s http://localhost:8001/health
curl -s http://localhost:3000 | head -1 | grep -q "DOCTYPE" && echo "Frontend: UP"
```

### Test a Query
```bash
curl -s -X POST http://localhost:8001/chat-agent/query \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"10","query":"YOUR QUERY HERE"}' | python3 -m json.tool
```

### Restart Backend After Code Changes
```bash
pkill -f "uvicorn.*8001"; sleep 2
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA
source venv/bin/activate && cd backend
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &
```

---

## 9. IMPORTANT PATIENT IDS FOR TESTING

| Patient ID | Notes |
|------------|-------|
| `10` | Primary test patient. Creatinine, BUN, Potassium, Calcium, Sodium, Chloride, Albumin, Glucose + more. 1 pt per obs. Encounter has no date. |
| `103` | Has encounter with date (2025-03-20) — good for encounter context testing |
| `104` | Has encounter with date (2025-03-20) |
| `100` | Has encounter with date (2025-03-19) |

### Queries That Trigger Each Feature
| Query | Feature Triggered |
|-------|-----------------|
| `"Show me creatinine trend"` | Single obs chart + reference lines (Gap 1) |
| `"Show me kidney disease labs"` | Combined CKD panel + dual y-axis (Gap 3+4) |
| `"Show me electrolyte panel trends"` | Combined electrolyte panel + dual y-axis (Gap 3+4) |
| `"Show me liver function trends"` | Combined liver panel (Gap 3+4) |
| `"What are the risk values?"` | Abnormal values chart (pre-existing) |
| `"Show me all vitals"` | All observations chart (pre-existing) |

---

*End of continuation document. All services should be stopped before closing the session.*
