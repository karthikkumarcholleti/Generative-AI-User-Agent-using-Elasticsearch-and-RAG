# Quick Start Guide

## Current Status

✅ **Backend is already running on port 8001**

## To Start Everything (including frontend):

Since backend is already running, you have two options:

### Option 1: Use start_all.sh (Recommended)
The script will detect backend is running and skip starting it:

```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED
./start_all.sh
```

**What it does:**
- Checks if backend is running (will skip if already running)
- Starts frontend on port 3000
- Starts Elasticsearch if needed
- Opens browser automatically

### Option 2: Start Frontend Only

If you just want to start the frontend:

```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED/FHIR_dashboard/backend/frontend
npm run dev
```

Then open browser manually: http://localhost:3000/generative-ai

## Access URLs

- **Frontend**: http://localhost:3000/generative-ai
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## Test Patient

**Patient ID: 000000500** (FN272 LN272)
- 107 observations
- 32 conditions

## Test Queries

See `BROWSER_TEST_QUERIES.md` for complete list.

Quick test:
1. "What are the abnormal values?" → Should show chart
2. "What is the patient's heart rate?" → Should show chart
3. Check sidebar "Patient Summary" → Should generate

