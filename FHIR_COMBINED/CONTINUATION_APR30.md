# Continuation Doc — April 30, 2026

## How to Resume
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0
npx @anthropic-ai/claude-code --continue
```
Then say: **"Continue the implementation from CONTINUATION_APR30.md"**

---

## What We Were Doing

Implementing a full system fix across 6 files. The changes fix:
- Bug 1: Demographics "no data" while other sections show same patient
- Bug 2: Observations summary drops vitals (28.8% NULL display names in MySQL) — fix is to use ES instead of MySQL for obs/conditions/notes
- Bug 3: Mid-sentence truncation in all summary sections
- Bug 4: Chat returns 3–5 readings when 15+ exist
- Architecture: MedRAG KG extended to summary sections; intent debug endpoint

---

## Files Changed — COMPLETED ✅

### 1. `FHIR_LLM_UA/backend/app/api/elasticsearch_client.py` ✅
- Line ~514: `"size": 150` (was 50)
- Added new method `get_all_patient_data_by_type()` just before `delete_patient_data()` (around line 701):
  ```python
  def get_all_patient_data_by_type(self, patient_id, data_type, size=300, index_name="patient_data"):
      """Fetch ALL docs of a data_type for a patient, date-DESC, no relevance ranking."""
  ```

### 2. `FHIR_LLM_UA/backend/app/api/loinc_code_mapper.py` ✅
- Added entry at end of `LOINC_CODE_MAPPINGS` dict (after the last `}` before the closing `}`):
  ```python
  "67723-7": {"name": "Date", "display": "Date (numeric encoded YYYYMMDD)", "category": "administrative", "keywords": ["date", "encounter date", "record date", "event date"]},
  ```

### 3. `FHIR_LLM_UA/backend/app/core/llm.py` ✅
- `_LIMITS` dict updated: patient_summary→2200, conditions→1800, demographics→1000, notes→900, care_plans→1200
- Runtime memory caps updated: 92%→400, 82%→600, 72%→900 (were 90%→150, 80%→300, 70%→500, 60%→700)
- Fallback heuristic updated: demographics→1000, notes→900

### 4. `FHIR_LLM_UA/backend/app/core/prompts.py` — PARTIALLY DONE ⚠️
- ✅ `SYSTEM_PROMPT`: Added null/None handling; added "state critical findings first"
- ✅ `prompt_patient_summary`: Added LEAD WITH ALERTS block (`[CRITICAL]`/`[ELEVATED]`/`[LOW]` tags); trimmed Rules block; added trend-based monitoring format
- ❌ NOT YET DONE: `prompt_observations_summary` — remove Examples block (lines ~211–216); add abnormal value flagging instruction
- ❌ NOT YET DONE: `prompt_care_plans` — remove "All clinical decisions rest with qualified healthcare providers" from LLM output (move to UI)
- ❌ NOT YET DONE: `prompt_demographics` — improve null handling instructions

---

## Files NOT YET CHANGED — TODO ❌

### 5. `FHIR_LLM_UA/backend/app/core/prompts.py` — remaining changes

**a) `prompt_observations_summary` (around line 195)**:
Remove the 5-line Examples block and add abnormal flagging:
```python
# REMOVE this block (~lines 211-216):
"Examples:\n"
"  - Heart rate: 98 /min — normal, stable over 5 measurements (Avg: 98.8, Range: 94-102)\n"
"  - Systolic BP: 129 mmHg — elevated, stable (Avg: 121.8, Range: 103-152)\n"
"  - HbA1c: 8.5% — elevated, indicating poor glycemic control\n"
"  - Creatinine: 2.1 mg/dL — elevated, may indicate renal impairment\n\n"

# REPLACE with:
"Flag abnormal values: [CRITICAL] for life-threatening, [ELEVATED] for above normal, [LOW] for below normal.\n"
"Use standard clinical thresholds (e.g., HbA1c >7% elevated; creatinine >1.2 mg/dL elevated).\n\n"
```

**b) `prompt_care_plans` (around line 346)**:
```python
# REMOVE this line from LLM output:
"- All clinical decisions rest with qualified healthcare providers.\n"
# (Keep it in the UI footer instead — not LLM output)
```

**c) `prompt_demographics` (around line 302)**:
```python
# CHANGE the last instruction line from:
"If a field says 'value not recorded' or 'date not recorded', write 'not recorded' for that field.\n"
# TO:
"If a field is null, None, missing, or says 'value not recorded'/'date not recorded', write 'not recorded'.\n"
```

---

### 6. `FHIR_LLM_UA/backend/app/api/summary.py` — FULL REWRITE OF `_get_patient_data()`

This is the biggest change. The core fix is: **replace MySQL observation/condition/notes queries with ES calls** so summaries use LOINC-resolved data (same as chat).

**a) Fix Bug 1 — CONCAT_WS for patient name (line ~375)**:
```python
# CHANGE:
SELECT patient_id, CONCAT(given_name, ' ', family_name) AS name,
# TO:
SELECT patient_id,
       COALESCE(CONCAT_WS(' ', NULLIF(TRIM(given_name),''), NULLIF(TRIM(family_name),'')), 'Not recorded') AS name,
```

**b) Fix Bug 1 — _clean_demographics name fallback (line ~134)**:
```python
# CHANGE the else fallthrough:
else:
    cleaned[key] = value  # Keep patientId and name always
# TO:
elif key == 'name':
    cleaned[key] = 'Not recorded'
else:
    cleaned[key] = value  # Keep patientId always
```

**c) Fix Bug 2 — ES-backed observations/conditions/notes**:

In `_get_patient_data()`, after the demographics SQL query (which stays as MySQL), replace the three MySQL queries (observations, conditions, notes) with ES calls:

```python
# At top of function, add import:
from .elasticsearch_client import es_client

# REPLACE the entire observations SQL block (lines ~421-528) with:
# ── Observations from ES (LOINC-resolved display names) ──────────────────
es_obs = es_client.get_all_patient_data_by_type(patient_id, "observations", size=300)
obs_groups: Dict[str, List[Dict[str, Any]]] = {}
if es_obs:
    for doc in es_obs:
        meta = doc.get("metadata", {})
        display = meta.get("display") or meta.get("name") or None
        code = meta.get("code") or ""
        # ES already has LOINC-resolved names — use them directly
        if not display and code:
            from .loinc_code_mapper import get_observation_display_from_code
            display = get_observation_display_from_code(code)
        display_key = (display or code or "Unknown").strip()
        
        raw_val = meta.get("value")
        value_number = None
        value_string = None
        if raw_val is not None:
            try:
                value_number = float(raw_val)
            except (ValueError, TypeError):
                value_string = str(raw_val)
        
        if display_key not in obs_groups:
            obs_groups[display_key] = []
        obs_groups[display_key].append({
            "code": code,
            "display": display or display_key,
            "valueNumber": value_number,
            "valueString": value_string,
            "unit": meta.get("unit"),
            "effectiveDateTime": meta.get("date"),
        })
else:
    # Fallback to MySQL if ES not connected / patient not indexed
    rows_o = conn.execute(text(sql_o), {"pid": patient_id, "limit": max_observations}).mappings().all()
    for r in rows_o:
        # ... (existing MySQL grouping logic, but with LOINC fallback for NULL display)
        from .loinc_code_mapper import get_observation_display_from_code
        display = r["display"]
        if not display and r["code"]:
            display = get_observation_display_from_code(r["code"])
        display_key = (display or r["code"] or "Unknown").strip()
        # rest of existing logic...

# [Trend aggregation logic stays the same — apply to obs_groups]
# [Deduplication logic stays the same]
```

**d) Fix Bug 2 — ES-backed conditions**:
```python
# REPLACE conditions SQL block with ES call:
es_conds = es_client.get_all_patient_data_by_type(patient_id, "conditions", size=100)
if es_conds:
    conditions = []
    seen = set()
    for doc in es_conds:
        meta = doc.get("metadata", {})
        key = f"{meta.get('code','')!s}|{meta.get('display','')!s}"
        if key in seen: continue
        seen.add(key)
        categorized = categorize_condition(code=meta.get("code"), display=meta.get("display"), clinical_status=meta.get("clinicalStatus"))
        conditions.append({
            "code": meta.get("code"), "display": meta.get("display"),
            "clinicalStatus": meta.get("clinicalStatus"),
            "recordedDate": meta.get("date"),
            "category": categorized["category"],
            "priority": categorized["priority"],
            "normalizedName": categorized["name"],
        })
        if len(conditions) >= max_conditions: break
else:
    # fallback to existing MySQL query
```

**e) Fix Bug 2 — ES-backed notes**:
```python
es_notes = es_client.get_all_patient_data_by_type(patient_id, "notes", size=5)
if es_notes:
    notes = []
    for doc in es_notes[:max_notes]:
        meta = doc.get("metadata", {})
        text_val = doc.get("content", "")
        notes.append({
            "created": meta.get("date"),
            "text": text_val[:max_note_chars] if text_val else None,
            "sourceType": meta.get("sourceType"),
            "fileName": meta.get("fileName"),
            "baseKey": meta.get("baseKey"),
        })
else:
    # fallback to existing MySQL query
```

**f) Add MedRAG KG injection for patient_summary + observations**:
In `generate_all_summaries()`, for `patient_summary` and `observations` categories, after fetching data add:
```python
from app.api.medrag_knowledge_graph import kg_service
from app.api.rag_service import USE_MEDRAG

if USE_MEDRAG and category in ("patient_summary", "observations"):
    # Build lightweight retrieved_data list from observations for KG
    kg_retrieved = [
        {"content": f"{o.get('display','')} {o.get('valueNumber','')} {o.get('unit','')}", "metadata": o}
        for o in observations[:50]
    ]
    kg_result = kg_service.run_kg_pipeline("patient summary", kg_retrieved)
    kg_candidates = kg_result.get("candidate_diseases", [])
    if kg_candidates:
        matched = kg_result.get("matched_evidence", {})
        kg_block = kg_service.build_kg_summary(kg_candidates, matched)
        # Inject kg_block into prompts by adding it to the user prompt text
        # Pass as extra kwarg or prepend to observations in render_prompt
```
The cleanest way: add an optional `kg_context` parameter to `render_prompt()` and inject it just before the TASK line in each prompt function.

---

### 7. `FHIR_LLM_UA/backend/app/api/rag_service.py`

**a) Secondary targeted ES query for observation-specific chat queries**:
After the main `retrieved_data = es_client.search_patient_data(...)` call, check if intent is observations and query names a specific metric. If yes, supplement with all readings of that metric:

```python
# After main ES retrieval, around line ~660:
if intent == "observations":
    # Check if query targets a specific observation type
    from .loinc_code_mapper import LOINC_CODE_MAPPINGS
    query_lower = query.lower()
    # Common vital/lab terms to detect
    obs_terms = ["heart rate", "blood pressure", "systolic", "diastolic", "glucose",
                 "hba1c", "hemoglobin", "creatinine", "cholesterol", "bun", "sodium",
                 "potassium", "weight", "bmi", "oxygen", "temperature", "respiratory"]
    matched_term = next((t for t in obs_terms if t in query_lower), None)
    if matched_term:
        all_obs = es_client.get_all_patient_data_by_type(patient_id, "observations", size=200)
        targeted = [
            doc for doc in all_obs
            if matched_term in (doc.get("metadata", {}).get("display") or "").lower()
            or matched_term in (doc.get("content") or "").lower()
        ]
        if targeted:
            # Merge: add targeted hits not already in retrieved_data (by content dedup)
            existing_contents = {r.get("content","") for r in retrieved_data}
            for doc in targeted:
                if doc.get("content","") not in existing_contents:
                    retrieved_data.append(doc)
                    existing_contents.add(doc.get("content",""))
            # Note how many total readings exist
            total_for_type = len(targeted)
```

**b) Append "N total readings" note to chat response**:
After LLM generates response text, if a targeted supplement was done:
```python
if matched_term and total_for_type > 15:
    response_text += f"\n\n[Note: {total_for_type} total {matched_term} readings in record — full timeline visible in chart above.]"
```

**c) Add intent debug endpoint** (in `chat_agent.py` or a new router):
```python
@router.post("/chat-agent/debug-intent")
def debug_intent(body: dict):
    """Test intent detection without running the full LLM pipeline."""
    query = body.get("query", "")
    patient_id = body.get("patient_id", "")
    from .intent_classifier import intent_classifier
    intent = intent_classifier.classify(query)
    # Also check DDx flags from rag_service
    from .rag_service import _ddx_intent_keywords, _value_lookup_overrides
    query_lower = query.lower()
    has_ddx = any(kw in query_lower for kw in _ddx_intent_keywords)
    is_lookup = any(kw in query_lower for kw in _value_lookup_overrides)
    return {
        "query": query,
        "intent": intent,
        "has_ddx_intent": has_ddx,
        "is_value_lookup": is_lookup,
        "apply_ddx": has_ddx and not is_lookup,
    }
```

---

## Commit Strategy
After all changes are implemented, commit as one logical unit:
```
git -C /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik commit -m \
  "Fix summary bugs: ES-backed data, token limits, MedRAG in summaries, intent debug endpoint"
```

---

## Test After Implementation
```bash
# 1. Start services
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED && ./start_all.sh

# 2. Test demographics (should never show blank name)
curl -s "http://localhost:8001/patients/000000509/all_summaries" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['summaries']['demographics'])"

# 3. Test observations (should list named vitals, not 'Unknown')
curl -s "http://localhost:8001/patients/000000509/all_summaries" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['summaries']['observations'])" | grep -c "Unknown"
# Expected: 0

# 4. Test intent debug endpoint
curl -s -X POST http://localhost:8001/chat-agent/debug-intent \
  -H "Content-Type: application/json" \
  -d '{"query": "show me all heart rate values", "patient_id": "000000509"}'

# 5. Test chat completeness
curl -s -X POST http://localhost:8001/chat-agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "list all heart rate values", "patient_id": "000000509"}' \
  | python3 -m json.tool | grep -i "heart rate" | wc -l
# Should be 10+

# 6. Test patient 740 (previously all "no data")
curl -s "http://localhost:8001/patients/000000740/all_summaries" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['summaries']['patient_summary'][:500])"
```

---

## Key File Paths (all relative to repo root `fhir_karthik/`)
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/api/elasticsearch_client.py`
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/api/loinc_code_mapper.py`
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/api/summary.py`
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/api/rag_service.py`
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/api/chat_agent.py`
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/core/llm.py`
- `FHIR_COMBINED/FHIR_LLM_UA/backend/app/core/prompts.py`
