#!/usr/bin/env python3
"""
Test Queries Guide - Run queries and verify semantic detection
Run after start_all.sh: python3 test_queries_guide.py
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"

def test_query(patient_id, query, description):
    """Test a single query and print results"""
    print(f"\n{'='*70}")
    print(f"Test: {description}")
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
            sources = data.get("sources", [])
            
            print(f"✅ Success ({elapsed:.2f}s)")
            print(f"   Response length: {len(answer)} chars")
            print(f"   Has chart: {chart is not None}")
            print(f"   Sources: {len(sources)} documents")
            print(f"\n   Preview:")
            print(f"   {answer[:300]}...")
            
            if chart:
                print(f"\n   📊 Chart type: {chart.get('type', 'unknown')}")
            
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

def check_backend():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def main():
    print("🧪 Test Queries Guide")
    print("="*70)
    
    # Check backend
    if not check_backend():
        print("❌ Backend is not running!")
        print("   Please run: ./start_all.sh")
        sys.exit(1)
    
    print("✅ Backend is running")
    
    patient_id = "000000500"
    
    # Test queries
    test_cases = [
        # Simple queries
        ("What is the heart rate?", "Simple query - specific observation"),
        ("What is the patient's glucose level?", "Simple query - specific observation"),
        
        # Analysis queries (semantic - should detect as "analysis" intent)
        ("What are the risk values?", "Analysis query - semantic (no keywords)"),
        ("What are the abnormal values?", "Analysis query - semantic"),
        ("Show me concerning vitals", "Analysis query - semantic"),
        ("What values are affecting this patient?", "Analysis query - semantic"),
        
        # Synthesis queries (semantic - should detect wants_all_data=true)
        ("Summarize the patient's case", "Synthesis query - semantic"),
        ("Give me an overview of this patient", "Synthesis query - semantic"),
        ("What is the complete picture?", "Synthesis query - semantic"),
        
        # Temporal queries (semantic - should detect as "visualization" intent)
        ("How has glucose changed over time?", "Temporal query - semantic"),
        ("Show me the trend for heart rate", "Temporal query - semantic"),
        ("How is the patient's condition trending?", "Temporal query - semantic"),
    ]
    
    results = []
    for query, description in test_cases:
        success, answer, chart = test_query(patient_id, query, description)
        results.append({
            "query": query,
            "description": description,
            "success": success,
            "has_chart": chart is not None
        })
        time.sleep(2)  # Small delay between queries
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 Test Summary")
    print(f"{'='*70}")
    successful = sum(1 for r in results if r["success"])
    with_charts = sum(1 for r in results if r.get("has_chart"))
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"📊 With charts: {with_charts}/{len(results)}")
    print(f"\nFailed tests:")
    for r in results:
        if not r["success"]:
            print(f"  ❌ {r['description']}: {r['query']}")

if __name__ == "__main__":
    main()

