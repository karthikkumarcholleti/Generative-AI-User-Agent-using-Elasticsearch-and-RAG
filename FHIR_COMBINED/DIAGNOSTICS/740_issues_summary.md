# Diagnostics: Patient 740 (FN2454 LN2454)

Date: 2026-04-27

This document captures the diagnostic findings discovered during interactive testing and review for patient `740` (FN2454 LN2454). It summarizes data quality issues, LLM/RAG concerns, visualization mismatches, likely causes, and recommended next steps. Do not modify code without explicit approval from the owner — these are investigation notes.

---

## High-priority issues (must fix before trusting summaries)

- Implausible blood-pressure statistics
  - Example: reported "average value 42.56" and range "0.07 - 257.00" across 50 measurements.
  - Likely causes: unit-mixing (mmHg vs kPa), wrong source field used during aggregation, numeric parsing bug, or corrupted records.
  - Impact: clinical conclusions about BP are invalid.

- Invalid / corrupted dates
  - Example: "20250200.0" as a date.
  - Likely causes: bad ETL/date parsing, numeric coercion of formatted dates, or malformed source values.
  - Impact: timeline reconstruction, encounter linking, and chart placement are unreliable.

- Missing units or inconsistent units
  - Observations often have "unit not recorded" (e.g., code 59408-5).
  - Likely causes: ingestion lost UCUM/unit fields or mapping from source codes failed.
  - Impact: unit normalization, dual-axis decisions, and interpretation could be wrong.

## Data completeness & cross-component inconsistencies

- Vitals reported as "No data available" while heart-rate chart exists
  - Symptoms: the summary page lists no vitals, yet the AI produced heart rate datapoints (2025-07-01, 2025-07-21).
  - Likely causes: different components query different indices/fields or use different filters (e.g., timeframe mismatch), or stale localStorage/state causes inconsistent presentation.

- Demographics contradicted across sections
  - Symptoms: demographics listed correctly in one block but another section shows "Age: value not recorded".
  - Likely causes: multiple canonical patient objects, race condition in restore logic, or inconsistent session state.

## LLM / RAG / presentation issues

- Claims without visible provenance
  - Symptoms: assertions such as "KG context for CHF/Afib is relevant" lack attached RAG sources in UI.
  - Likely causes: backend may return `sources` but frontend doesn't surface them, or the LLM output wasn't asked to include explicit citations.

- Formatting artifacts, duplicated/truncated sections
  - Symptoms: repeated demographics blocks, trailing orphan list items (e.g., "4."), and duplicated sections.
  - Likely causes: generation concatenation logic or partial retries producing merged output.

- Overconfident recommendations without qualification
  - LLM marks conditions as "HIGH PRIORITY" but sometimes without strong evidence links.
  - Mitigation: require RAG-backed statements and softening language when evidence is weak.

## Indexing / ingestion / schema issues

- Mixed data types
  - Dates or codes showing up as floats (e.g., `20250200.0`) suggest incorrect mapping in Elasticsearch or inconsistent ingestion pipelines.

- Observations mapped to wrong categories
  - Example: PHQ-9 appears under "Other" instead of Mental Health category.
  - Likely causes: missing/incorrect LOINC/Code-to-category mapping rules.

## Visualization / charting issues

- Charts generated but may be based on suspect values
  - If BP/HR/other numeric anomalies exist in the underlying documents, charts will reflect them incorrectly.
  - Reference bands or dual-axis logic may misuse units when units are absent or inconsistent.

## UX / state issues

- LocalStorage and minimization race conditions
  - Multiple components read/write `generativeAIState` and poll localStorage which can lead to inconsistent UI states across tabs.

---

## Immediate diagnostic checklist (no code changes)
These are recommended reads/queries to inspect data and prove root causes.

1. Raw observation documents for patient `740`
   - Retrieve all `Observation` docs in ES for this patient and filter for blood pressure and heart rate LOINCs and codes.
   - Check `value`, `unit`, and `effectiveDateTime` fields exactly as stored.

2. Search for corrupted dates
   - Query ES for documents containing values like `20250200` (as number or string) to find source docs.

3. Recompute aggregates locally from raw values
   - Compute min/max/mean for BP and HR from the raw docs to see whether weird numbers are present in the raw data.

4. Inspect ES mappings
   - Check index mapping for date fields and numeric fields (strings vs numbers) to confirm incorrect mappings.

5. Fetch a sample LLM response JSON for a few queries (e.g., heart rate trend, creatinine) and inspect whether `sources` are present in the response and whether `chart` payload contains `dualYAxis`, `data.datasets`, `referenceLines`.

6. Compare the queries used by the summary module vs the visualization module
   - Log/print the actual ES queries used by each component (or reproduce them manually) and compare filters/time windows.

---

## Recommended priority fixes (high-level)

1. Fix ingestion/date normalization and mapping
   - Normalize all dates to ISO-8601 at ingestion. Reject or flag malformed dates.
   - Enforce correct ES mappings for dates and numerics.

2. Ensure units/UCUM are preserved
   - During ingestion, store units using a standard UCUM field and a `unit_confidence` flag.
   - If units missing, mark observations as "unit unknown" and exclude them from automatic normalization unless manually validated.

3. Add validation for implausible aggregates
   - On aggregation, detect implausible values (BP < 20 or > 300) and either exclude them or surface them for manual review.

4. Surface RAG sources for every claim
   - Update prompts and UI rendering to always include `sources` from the LLM/agent responses alongside claims that affect care prioritization.

5. Centralize patient-demographics reads and reduce localStorage races
   - Use a single source of truth for patient metadata and simplify `generativeAIState` handling (avoid polling where possible).

6. Add tests and alerts
   - Add unit/integration tests that run on ingestion to detect malformed dates/units.
   - Add monitoring/alerts for spikes in invalid records.

---

## Next steps (proposed)

1. Authorize me to run the diagnostic checklist (ES queries and response inspection). I will not change code — only read and report offending document IDs and samples.
2. After diagnostics, prioritize fixes for ingestion/mapping and unit normalization.
3. Iteratively re-run the same test queries (for patient 740) until artifacts are resolved.

---

If you want this file committed and pushed to the repository, it has been created here for review. Approve and I will push it to `origin/main` (or I can push now if you want) — say "push diagnostics" to commit and push immediately.
