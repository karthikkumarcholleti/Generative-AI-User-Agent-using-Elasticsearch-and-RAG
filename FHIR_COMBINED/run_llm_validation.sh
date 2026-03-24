#!/bin/bash
# Quick script to run LLM validation tests

echo "🔍 LLM Validation Test Suite"
echo "============================"
echo ""

# Check if API is running
echo "Checking if LLM API is running..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ LLM API is running on port 8000"
else
    echo "❌ LLM API is not running on port 8000"
    echo "Please start it with:"
    echo "  cd FHIR_LLM_UA/backend"
    echo "  source ../venv/bin/activate"
    echo "  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

echo ""
echo "Running validation tests..."
echo ""

# Activate venv and run tests
cd "$(dirname "$0")"
if [ -d "FHIR_LLM_UA/venv" ]; then
    source FHIR_LLM_UA/venv/bin/activate
    python test_llm_validation.py "$@"
else
    echo "❌ Virtual environment not found at FHIR_LLM_UA/venv"
    exit 1
fi


