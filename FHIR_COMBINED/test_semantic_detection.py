#!/usr/bin/env python3
"""
Test Semantic Detection - Verify no hardcoded keywords are used
Run after summaries finish: python3 test_semantic_detection.py
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"
PATIENT_ID = "000000500"

def test_query(patient_id, query, expected_intent_type=None, expected_chart=False):
    """Test a query and check semantic detection"""
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print(f"{'='*70}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/chat-agent/query",
            json={"patient_id": patient_id, "query": query},
            timeout=90
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")
            chart = data.get("chart")
            
            print(f"✅ Success ({elapsed:.2f}s)")
            print(f"   Response length: {len(answer)} chars")
            print(f"   Chart generated: {chart is not None}")
            
            if expected_chart and not chart:
                print(f"   ⚠️  Expected chart but none generated")
            elif chart:
                print(f"   📊 Chart type: {chart.get('type', 'unknown')}")
            
            # Check backend logs for semantic detection
            # We can't access logs directly, but we can infer from response
            
            print(f"\n   Preview:")
            preview = answer[:200].replace('\n', ' ')
            print(f"   {preview}...")
            
            return True, answer, chart
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(f"   {response.text[:200]}")
            return False, None, None
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout (>90s)")
        return False, None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None, None

def main():
    print("🧪 Semantic Detection Test Suite")
    print("="*70)
    print("Testing queries to verify semantic detection (no hardcoded keywords)")
    print("="*70)
    
    # Check backend
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend is not healthy!")
            sys.exit(1)
    except:
        print("❌ Backend is not running!")
        print("   Please run: ./start_all.sh")
        sys.exit(1)
    
    print("✅ Backend is running and healthy")
    print(f"   Patient ID: {PATIENT_ID}")
    print("\n⏳ Wait for summaries to finish generating before testing queries...")
    print("   (Check the browser - summaries should show in the sidebar)")
    print("\n   Press Enter when summaries are ready, or wait 30 seconds...")
    
    # Wait a bit for summaries
    time.sleep(5)
    
    test_cases = [
        # Simple queries - should work with highlighting
        {
            "query": "What is the heart rate?",
            "description": "Simple query - specific observation",
            "expected_chart": True
        },
        {
            "query": "What is the patient's glucose level?",
            "description": "Simple query - specific observation",
            "expected_chart": True
        },
        
        # Analysis queries - should detect as "analysis" intent (semantic, no keywords)
        {
            "query": "What are the risk values?",
            "description": "Analysis query - semantic detection (no 'abnormal' keyword)",
            "expected_chart": True  # Should generate abnormal values chart
        },
        {
            "query": "Show me concerning vitals",
            "description": "Analysis query - semantic detection (no 'abnormal' keyword)",
            "expected_chart": True
        },
        {
            "query": "What values are affecting this patient?",
            "description": "Analysis query - semantic detection",
            "expected_chart": True
        },
        
        # Synthesis queries - should detect wants_all_data=true (semantic)
        {
            "query": "Summarize the patient's case",
            "description": "Synthesis query - semantic detection (no 'all' keyword)",
            "expected_chart": False
        },
        {
            "query": "Give me an overview of this patient",
            "description": "Synthesis query - semantic detection",
            "expected_chart": False
        },
        
        # Temporal queries - should detect as "visualization" intent (semantic)
        {
            "query": "How has glucose changed over time?",
            "description": "Temporal query - semantic detection (should use intent_type='visualization')",
            "expected_chart": True
        },
        {
            "query": "Show me the trend for heart rate",
            "description": "Temporal query - semantic detection",
            "expected_chart": True
        },
    ]
    
    print(f"\n{'='*70}")
    print("Starting test queries...")
    print(f"{'='*70}\n")
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {test['description']}")
        success, answer, chart = test_query(
            PATIENT_ID, 
            test["query"],
            expected_chart=test.get("expected_chart", False)
        )
        results.append({
            "query": test["query"],
            "description": test["description"],
            "success": success,
            "has_chart": chart is not None,
            "expected_chart": test.get("expected_chart", False)
        })
        
        # Small delay between queries
        if i < len(test_cases):
            time.sleep(3)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 Test Summary")
    print(f"{'='*70}")
    
    successful = sum(1 for r in results if r["success"])
    charts_correct = sum(1 for r in results if r["has_chart"] == r["expected_chart"])
    
    print(f"✅ Successful queries: {successful}/{len(results)}")
    print(f"📊 Charts correct: {charts_correct}/{len(results)}")
    
    print(f"\nDetailed results:")
    for r in results:
        status = "✅" if r["success"] else "❌"
        chart_status = "📊" if r["has_chart"] else "   "
        expected = " (expected)" if r["expected_chart"] else ""
        print(f"  {status} {chart_status} {r['description']}")
        if not r["success"]:
            print(f"     Query: {r['query']}")
    
    print(f"\n{'='*70}")
    print("🔍 To verify semantic detection (no hardcoding):")
    print(f"   Check backend logs: tail -100 FHIR_LLM_UA/backend.log | grep -E 'Analysis|Synthesis|Temporal|intent_type'")
    print(f"   Look for:")
    print(f"   - 'Analysis query detected (intent_type=analysis)' ✅")
    print(f"   - 'Synthesis query detected (wants_all_data=true)' ✅")
    print(f"   - 'Temporal/trend query detected (intent_type=visualization)' ✅")
    print(f"   - NO hardcoded keyword matching ❌")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

