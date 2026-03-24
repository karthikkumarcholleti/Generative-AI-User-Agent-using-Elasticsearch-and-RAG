#!/usr/bin/env python3
"""
Test script to test different query types separately
Tests highlighting, fallback, and overall system behavior
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"
PATIENT_ID = "000000500"  # Test patient

# Test queries organized by type
TEST_QUERIES = [
    {
        "name": "Simple Query - Direct Question",
        "query": "What is the patient's heart rate?",
        "expected": "Should use highlighting, fast response"
    },
    {
        "name": "Simple Query - Specific Observation",
        "query": "Show me glucose values",
        "expected": "Should use highlighting, fast response"
    },
    {
        "name": "Simple Query - Chief Complaint",
        "query": "What is the chief complaint?",
        "expected": "Should use highlighting, extracts relevant snippets"
    },
    {
        "name": "Complex Query - Risk Factors (Analysis Intent)",
        "query": "What are the patient's risk factors?",
        "expected": "Should use highlighting (was working before), may fallback if no keyword matches"
    },
    {
        "name": "Complex Query - Abnormal Values (Analysis Intent)",
        "query": "What are the abnormal values?",
        "expected": "Should use highlighting, may fallback if no keyword matches"
    },
    {
        "name": "Abstract Query - Concern",
        "query": "What should we be concerned about?",
        "expected": "Semantic search finds docs, highlighting may fail, should fallback to full content"
    },
    {
        "name": "Abstract Query - Risk Values",
        "query": "What are the risk values that affect this patient?",
        "expected": "Semantic search finds docs, highlighting may fail, should fallback to full content"
    },
    {
        "name": "Synthesis Query - Overall Picture",
        "query": "What is the overall clinical picture?",
        "expected": "Semantic search finds docs, highlighting may fail, should fallback to full content"
    },
    {
        "name": "Notes Query",
        "query": "What is the patient's medical history?",
        "expected": "Should use highlighting if keywords match, otherwise fallback"
    }
]

def test_single_query(query_info, patient_id):
    """Test a single query and report results"""
    name = query_info["name"]
    query = query_info["query"]
    expected = query_info["expected"]
    
    print("\n" + "="*80)
    print(f"TEST: {name}")
    print("="*80)
    print(f"Query: '{query}'")
    print(f"Expected: {expected}")
    print("-"*80)
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/chat-agent/query",
            json={"patient_id": patient_id, "query": query},
            timeout=120
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", result.get("answer", ""))
            sources = result.get("sources", [])
            
            print(f"✅ Response received in {elapsed:.2f} seconds")
            print(f"\n📝 Answer (first 300 chars):")
            print(f"   {answer[:300]}...")
            
            print(f"\n📊 Sources: {len(sources)} documents")
            
            # Analyze source content lengths
            if sources:
                note_sources = [s for s in sources if s.get("type") == "notes"]
                if note_sources:
                    print(f"\n📋 Notes Analysis:")
                    for i, note in enumerate(note_sources[:3], 1):
                        desc = note.get("description", "")[:100]
                        print(f"   {i}. {desc}...")
            
            # Performance analysis
            if elapsed < 30:
                print(f"\n⚡ FAST RESPONSE ({elapsed:.2f}s)")
                print("   → Likely used highlighting (efficient)")
            elif elapsed < 60:
                print(f"\n⏱️  MODERATE RESPONSE ({elapsed:.2f}s)")
                print("   → May have used fallback (full documents)")
            else:
                print(f"\n🐌 SLOW RESPONSE ({elapsed:.2f}s)")
                print("   → May indicate issues")
            
            # Check for memory constraints
            if "temporarily unavailable" in answer.lower() or "memory constraints" in answer.lower():
                print(f"\n⚠️  WARNING: Memory constraint message detected")
            
            return {
                "success": True,
                "elapsed": elapsed,
                "answer_length": len(answer),
                "sources_count": len(sources),
                "has_memory_warning": "temporarily unavailable" in answer.lower() or "memory constraints" in answer.lower()
            }
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "elapsed": elapsed
            }
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 120 seconds")
        return {
            "success": False,
            "error": "Timeout",
            "elapsed": 120
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "elapsed": 0
        }

def main():
    """Run all test queries"""
    print("="*80)
    print("COMPREHENSIVE QUERY TESTING")
    print("="*80)
    print(f"Patient ID: {PATIENT_ID}")
    print(f"Base URL: {BASE_URL}")
    
    # Check backend health
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✅ Backend is healthy\n")
        else:
            print("❌ Backend health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure the backend is running on port 8001")
        return
    
    # Run tests
    results = []
    for i, query_info in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(TEST_QUERIES)}")
        print(f"{'='*80}")
        
        result = test_single_query(query_info, PATIENT_ID)
        result["name"] = query_info["name"]
        result["query"] = query_info["query"]
        results.append(result)
        
        # Small delay between queries
        if i < len(TEST_QUERIES):
            print(f"\n⏳ Waiting 3 seconds before next test...")
            time.sleep(3)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        avg_time = sum(r.get("elapsed", 0) for r in successful) / len(successful)
        print(f"\n⏱️  Average response time: {avg_time:.2f} seconds")
        
        fast_queries = [r for r in successful if r.get("elapsed", 0) < 30]
        slow_queries = [r for r in successful if r.get("elapsed", 0) > 60]
        
        print(f"⚡ Fast queries (< 30s): {len(fast_queries)}")
        print(f"🐌 Slow queries (> 60s): {len(slow_queries)}")
    
    if failed:
        print(f"\n❌ Failed Tests:")
        for r in failed:
            print(f"   - {r.get('name')}: {r.get('error', 'Unknown error')}")
    
    # Memory warnings
    memory_warnings = [r for r in results if r.get("has_memory_warning")]
    if memory_warnings:
        print(f"\n⚠️  Memory Warnings: {len(memory_warnings)} queries")
        for r in memory_warnings:
            print(f"   - {r.get('name')}")
    
    print("\n" + "="*80)
    print("💡 Check backend logs for:")
    print("   - 'Using Elasticsearch highlighting'")
    print("   - 'Highlighting quality check FAILED'")
    print("   - 'Fallback: Using full documents'")
    print("="*80)

if __name__ == "__main__":
    main()

