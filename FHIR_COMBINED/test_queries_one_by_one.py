#!/usr/bin/env python3
"""
Test Queries One by One - Verify semantic detection
Run after backend starts and summaries finish generating
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"
PATIENT_ID = "000000500"

def test_single_query(patient_id, query, description):
    """Test a single query and print detailed results"""
    print(f"\n{'='*80}")
    print(f"🧪 Test: {description}")
    print(f"📝 Query: '{query}'")
    print(f"{'='*80}")
    
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
            sources = data.get("sources", [])
            
            print(f"✅ SUCCESS ({elapsed:.2f} seconds)")
            print(f"   Response length: {len(answer)} characters")
            print(f"   Chart generated: {'✅ YES' if chart else '❌ NO'}")
            print(f"   Sources: {len(sources)} documents")
            
            if chart:
                chart_type = chart.get("type", "unknown")
                print(f"   📊 Chart type: {chart_type}")
            
            print(f"\n   Response preview:")
            preview = answer[:300].replace('\n', ' ')
            print(f"   {preview}...")
            
            print(f"\n   ✅ Test PASSED")
            return True, answer, chart
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return False, None, None
    except requests.exceptions.Timeout:
        print(f"⏱️  TIMEOUT (>90 seconds)")
        return False, None, None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, None, None

def check_backend():
    """Check if backend is running and healthy"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def main():
    print("🧪 Semantic Detection Test Suite - One by One")
    print("="*80)
    print("Testing queries to verify semantic detection (no hardcoded keywords)")
    print("="*80)
    
    # Check backend
    if not check_backend():
        print("\n❌ Backend is not running or not healthy!")
        print("   Please start backend first: ./start_all.sh")
        sys.exit(1)
    
    print("\n✅ Backend is running and healthy")
    print(f"   Patient ID: {PATIENT_ID}")
    print("\n⏳ Make sure summaries have finished generating in the browser first!")
    print("   (Check the sidebar - all summary sections should be loaded)")
    print("\n   Press Enter when ready to start testing, or wait 5 seconds...")
    time.sleep(5)
    
    # Test queries in order - one by one
    test_cases = [
        {
            "query": "What is the heart rate?",
            "description": "Simple Query - Specific Observation",
            "expected_chart": True
        },
        {
            "query": "What is the patient's glucose level?",
            "description": "Simple Query - Specific Observation",
            "expected_chart": True
        },
        {
            "query": "What are the risk values?",
            "description": "Analysis Query - Semantic (no 'abnormal' keyword)",
            "expected_chart": True  # Should generate abnormal values chart
        },
        {
            "query": "Show me concerning vitals",
            "description": "Analysis Query - Semantic (no 'abnormal' keyword)",
            "expected_chart": True
        },
        {
            "query": "Summarize the patient's case",
            "description": "Synthesis Query - Semantic (no 'all' keyword)",
            "expected_chart": False
        },
        {
            "query": "How has glucose changed over time?",
            "description": "Temporal Query - Semantic (should use intent_type='visualization')",
            "expected_chart": True
        },
    ]
    
    print(f"\n{'='*80}")
    print(f"Starting {len(test_cases)} test queries...")
    print(f"{'='*80}\n")
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}]")
        success, answer, chart = test_single_query(
            PATIENT_ID,
            test["query"],
            test["description"]
        )
        
        results.append({
            "query": test["query"],
            "description": test["description"],
            "success": success,
            "has_chart": chart is not None,
            "expected_chart": test.get("expected_chart", False)
        })
        
        # Wait between tests
        if i < len(test_cases):
            print(f"\n⏳ Waiting 3 seconds before next test...")
            time.sleep(3)
    
    # Final summary
    print(f"\n{'='*80}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r["success"])
    charts_correct = sum(1 for r in results if r["has_chart"] == r["expected_chart"])
    
    print(f"\n✅ Successful queries: {successful}/{len(results)}")
    print(f"📊 Charts correct: {charts_correct}/{len(results)}")
    
    print(f"\n📋 Detailed Results:")
    for r in results:
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        chart_status = "📊" if r["has_chart"] else "   "
        print(f"  {status} {chart_status} {r['description']}")
        print(f"      Query: '{r['query']}'")
        if not r["success"]:
            print(f"      ⚠️  Query failed")
        elif r["has_chart"] != r["expected_chart"]:
            expected = "expected" if r["expected_chart"] else "not expected"
            print(f"      ⚠️  Chart {expected} but {'generated' if r['has_chart'] else 'not generated'}")
    
    print(f"\n{'='*80}")
    print("🔍 Next Steps:")
    print(f"   1. Check backend logs for semantic detection:")
    print(f"      tail -200 /tmp/backend_test.log | grep -E 'Analysis|Synthesis|Temporal|intent_type|wants_all_data'")
    print(f"   2. Verify NO hardcoded keyword matching in logs")
    print(f"   3. Look for semantic detection messages:")
    print(f"      - 'Analysis query detected (intent_type=analysis)' ✅")
    print(f"      - 'Synthesis query detected (wants_all_data=true)' ✅")
    print(f"      - 'Temporal/trend query detected (intent_type=visualization)' ✅")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

