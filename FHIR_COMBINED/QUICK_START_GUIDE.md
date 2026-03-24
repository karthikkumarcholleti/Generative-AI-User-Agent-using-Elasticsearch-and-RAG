# Quick Start Guide

## Starting All Services

The `start_all.sh` script is located in the `FHIR_COMBINED` directory.

### Option 1: Navigate to the directory first
```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED
./start_all.sh
```

### Option 2: Run from anywhere with full path
```bash
/home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED/start_all.sh
```

### Option 3: Make it executable (if needed)
```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED
chmod +x start_all.sh
./start_all.sh
```

## What it does

1. Starts Elasticsearch (port 9200)
2. Starts Backend API (port 8001)
3. Starts Frontend (port 3000)
4. Opens browser to dashboard

## After starting

- Backend logs: `FHIR_COMBINED/FHIR_LLM_UA/backend.log`
- Frontend logs: `FHIR_COMBINED/FHIR_dashboard/nextjs.log`
- Test queries: Use `test_queries_guide.py` or browser

## Stopping services

Press `Ctrl+C` in the terminal where you ran `start_all.sh`, or:
```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED
./stop_all.sh
```

