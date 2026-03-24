#!/bin/bash
# Script to run tests and monitor progress

cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED

echo "================================================================================="
echo "RUNNING COMPREHENSIVE SEMANTIC SEARCH TESTS"
echo "================================================================================="
echo ""
echo "This will test 5 key scenarios across different patients"
echo "Estimated time: 15-20 minutes (each query takes ~3-4 minutes)"
echo ""
echo "Starting tests..."
echo ""

# Run the quick test suite
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="test_results_${TIMESTAMP}.log"

python3 test_semantic_search_quick.py 2>&1 | tee "$LOG_FILE"

echo ""
echo "================================================================================="
echo "TESTS COMPLETED"
echo "================================================================================="
echo ""
echo "Results saved to:"
echo "  - Log: $LOG_FILE"
echo "  - JSON: quick_test_results_*.json"
echo ""
echo "View results:"
echo "  cat $LOG_FILE"
echo "  cat quick_test_results_*.json | python3 -m json.tool"
echo ""

