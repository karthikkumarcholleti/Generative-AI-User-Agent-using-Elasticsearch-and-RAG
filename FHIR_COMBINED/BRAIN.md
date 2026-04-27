# BRAIN — Project Master Plan & Knowledge Transfer

Version: 2026-04-27
Owner: Karthik (karthikkumarcholleti)

This single-file "brain" captures the project's master plan, current status, important mistakes and diagnostics discovered so far, operational playbook, and concise instructions to transfer this context into another assistant (for example, Claude.ai). Treat this as the canonical handoff / onboarding brief.

---

## 1) One-line purpose
Build a FHIR-based RAG dashboard that generates clinician-friendly summaries and interactive visualizations (time-series charts, reference bands, encounter context) using Elasticsearch and an LLM agent for reasoning and visualization suggestions.

## 2) Quick-start summary (what to read first)
- `VISUALIZATION_GAPS_CONTINUATION.md` — high-level handoff and what changed.
- `DIAGNOSTICS/740_issues_summary.md` — patient-740 diagnosis and data-quality checklist.
- `start_all.sh` / `stop_all.sh` — how to bring the stack up and down.
- `FHIR_COMBINED/FHIR_LLM_UA` — backend source for the chat-agent endpoints.
- `FHIR_COMBINED/FHIR_dashboard/backend/frontend` — Next.js frontend that renders the UI.

## 3) Master research plan (milestones)
Short-term (now → 2 weeks)
- Stabilize data quality: detect and fix invalid dates / units ingestion.
- Add unit-normalization validation and exclusion rules for suspect measurements.
- Surface RAG sources in all LLM claims (backend + UI changes).

Medium (2–8 weeks)
- Implement Gap 5: clinical event annotations on timeline (events, meds, procedures).
- Improve disease-progression combined panels and automatic multi-series grouping.
- Add comprehensive tests for ingestion and mapping.

Long-term (2–6 months)
- Integrate model-selection and on-prem LLM orchestration with GPU monitoring.
- Run prospective clinical validation (sample of patient charts, clinician feedback).

Research deliverables
- Peer-review-ready documentation of RAG prompt design and evaluation metrics.
- A reproducible dataset sampling and validation suite.

## 4) What we have implemented (status)
- Unit normalization for labs (Gap 6) — implemented in visualization service.
- Reference range bands in charts (Gap 1) — rendered by RechartsVisualization & backend chart payloads.
- Combined disease progression + dual Y-axis for multi-lab panels (Gaps 3+4) — backend now emits `dualYAxis` metadata.
- Encounter context tooltip for data points (Gap 2) — backend stores encounter snippets, frontend tooltip shows them.
- CI / build fixes: removed stray `generative-ai-NEW.tsx` temp file that broke the build; TypeScript optional chaining fixes.

## 5) Pending / Deferred
- Gap 5 — clinical event annotations: deferred due to sparse event dates and inconsistent encounter timestamps.
- Some TypeScript typings for new chart fields still missing (recommended improvement, low-risk).

## 6) Known mistakes, bugs, and data issues (critical)
These were observed during interactive testing and are documented in `DIAGNOSTICS/740_issues_summary.md`. Key items:
- Implausible blood-pressure aggregates (e.g., avg 42.56, range 0.07–257.00) — likely ingestion/units/aggregation bug.
- Corrupted dates (e.g., `20250200.0`) — ETL/date parsing problem.
- Missing units on many observations — ingestion lost UCUM unit fields or mapping failed.
- Mismatched component state (vitals reported as "No data" but charts exist) — inconsistent queries across modules or stale UI state.
- LLM presenting claims without visible RAG sources in UI — fix UI to always show `sources` or ensure backend includes them.

## 7) Diagnostics checklist (read-only investigative steps)
If you want to validate issues quickly, perform the following (no code changes required):
1. Query Elasticsearch for raw `Observation` docs for patient 740 and inspect `value`, `unit`, and `effectiveDateTime`.
2. Search ES for values that look like malformed dates (e.g., `20250200`) and list offending doc IDs.
3. Recompute aggregates in a short Python script from raw values to verify whether anomalies come from raw data or from the aggregation layer.
4. Request `/chat-agent/query` responses and inspect the JSON to confirm whether `sources` and `chart` payloads are present.
5. Compare the ES queries produced by the summary generator vs the visualization generator (or rerun the queries manually) and confirm they are pulling the same time windows and filters.

## 8) Operational playbook — start/stop & quick checks
Start everything from project root `FHIR_COMBINED`:
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./start_all.sh
```
Health checks:
```bash
curl -s http://localhost:9200/_cluster/health?pretty
curl -s http://localhost:8001/health
curl -s http://localhost:8001/patients | jq '.[0:5]'
```
Notes:
- Frontend default port 3000; if busy, we run it on 3001. Check logs: `FHIR_COMBINED/nextjs.log`.
- GPU: LLM inference may require GPUs. If GPUs are occupied by other users, coordinate or ask admin; do not kill other users' jobs without approval.

## 9) How to transfer this brain to Claude.ai (or any other assistant)
Follow these steps for a reliable transfer:
1. Open a new Claude/assistant chat.
2. Paste this file content (or a condensed version) as the system/context prompt. You may want to split it into sections to avoid message length limits.
3. Immediately after pasting, give these short instructions to the assistant:
   - "You are now the project's knowledge base. Ask clarifying questions if any detail is ambiguous. When I ask a question later, reference this file by section name (e.g., 'Diagnostics', 'Operational playbook')." 
4. Provide the assistant with these important file pointers to read next:
   - `VISUALIZATION_GAPS_CONTINUATION.md`
   - `DIAGNOSTICS/740_issues_summary.md`
   - `FHIR_COMBINED/FHIR_LLM_UA` (backend)
   - `FHIR_COMBINED/FHIR_dashboard/backend/frontend` (frontend)
5. If Claude supports memory or saved context, save a short label: "FHIR Dashboard — project brain (2026-04-27)".

Transfer prompt example (paste to Claude):
```
I will paste a project brain. After you ingest it, confirm you understand and ask one question if anything ambiguous. Then keep this context available for future queries. Tag this context as: 'FHIR Dashboard — project brain (2026-04-27)'.

--PASTE START--
[paste the content of this BRAIN.md]
--PASTE END--

Now respond 'READY' if you understood, and ask one clarifying question if needed.
```

## 10) Communication and ownership
- Owner / lead: Karthik (karthikkumarcholleti). Use GitHub issues/PRs for code changes.
- Operational contact: whoever manages the host machine (for GPU scheduling).

## 11) Change-log (short)
- 2026-04-25: Completed Gaps 1,2,3,4,6; pushed multiple fixes; documented continuation and committed progress.
- 2026-04-27: Added diagnostic notes for patient 740 and created this `BRAIN.md` for knowledge transfer.

## 12) Next immediate tasks (pick one to start)
1. Authorize read-only diagnostics (ES queries + response sampling) so we can list offending doc IDs (recommended first step).
2. If you prefer code work first: I can prepare a PR that adds ingestion validation (date/unit validation) and automated tests.
3. Improve UI to always display `sources` when LLM makes a claim — I can propose exact backend & frontend changes.

---

If you want this condensed into a short briefing to paste into a new chat or saved as a one-paragraph summary, say "condense brain" and I will produce a ready-to-copy brief.
