#!/usr/bin/env python3
"""
Quick Test After Summaries - Verify semantic detection works
Run this once summaries finish generating in the browser
"""

import requests
import time

BASE_URL = "http://localhost:8001"
PATIENT_ID = "000000500"

# Test queries to verify semantic detection
test_queries = [
    ("What is the heart rate?", "Simple query"),
    ("What are the risk values?", "Analysis query - semantic (no 'abnormal' keyword)"),
    ("Summarize the patient's case", "Synthesis query - semantic"),
    ("How has glucose changed over time?", "Temporal query - semantic"),
]

print("🧪 Testing Semantic Detection")
print("="*70)

for query, description in test_queries:
    print(f"\n{description}: '{query}'")
    try:
        response = requests.post(
            f"{BASE_URL}/chat-agent/query",
            json={"patient_id": PATIENT_ID, "query": query},
            timeout=90
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Success - Response: {len(data.get('response', ''))} chars, Chart: {data.get('chart') is not None}")
        else:
            print(f"  ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    time.sleep(2)

print("\n" + "="*70)
print("Check backend logs for semantic detection messages:")
print("  tail -100 FHIR_LLM_UA/backend.log | grep -E 'Analysis|Synthesis|Temporal|intent_type'")

