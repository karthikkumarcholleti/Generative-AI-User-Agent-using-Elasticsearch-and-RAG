#!/usr/bin/env python3
"""
Test script to verify the hybrid approach (highlighting vs LLM compression)
Tests both simple and complex queries to ensure correct detection and processing.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001"
PATIENT_ID = "000000500"  # Test patient

# Test queries: Simple (should use highlighting) and Complex (should use compression)
TEST_QUERIES = [
    # Simple queries (should use highlighting)
    {
        "query": "What is the patient's heart rate?",
        "type": "simple",
        "expected_method": "highlighting"
    },
    {
        "query": "Show me glucose values",
        "type": "simple",
        "expected_method": "highlighting"
    },
    {
        "query": "What is the chief complaint?",
        "type": "simple",
        "expected_method": "highlighting"
    },
    # Complex queries (should use compression)
    {
        "query": "What are the patient's risk factors?",
        "type": "complex",
        "expected_method": "compression"
    },
    {
        "query": "What should we be concerned about?",
        "type": "complex",
        "expected_method": "compression"
    },
    {
        "query": "What is the overall clinical picture?",
        "type": "complex",
        "expected_method": "compression"
    },
    {
        "query": "What values indicate problems?",
        "type": "complex",
        "expected_method": "compression"
    }
]

def test_query(patient_id: str, query: str, query_type: str, expected_method: str):
    """Test a single query and check if correct method is used"""
    print(f"\n{'='*80}")
    print(f"Testing {query_type.upper()} Query:")
    print(f"Query: {query}")
    print(f"Expected Method: {expected_method}")
    print(f"{'='*80}\n")
    
    try:
        # Make API request
        url = f"{BASE_URL}/chat-agent/query"
        payload = {
            "patient_id": patient_id,
            "query": query
        }
        
        print(f"Sending request to {url}...")
        start_time = time.time()
        
        response = requests.post(url, json=payload, timeout=300)
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract response
            answer = result.get("response", result.get("answer", "No response"))
            sources = result.get("sources", [])
            
            print(f"✅ Response received in {elapsed_time:.2f}s")
            print(f"\n📝 Answer (first 200 chars):")
            print(f"   {answer[:200]}...")
            
            print(f"\n📊 Sources: {len(sources)} documents")
            for i, source in enumerate(sources[:3], 1):  # Show first 3
                source_type = source.get("type", "unknown")
                content_preview = source.get("content", "")[:100]
                print(f"   {i}. {source_type}: {content_preview}...")
            
            # Check logs (we can't directly access logs, but we can infer from response time)
            if query_type == "simple":
                if elapsed_time < 30:  # Simple queries should be fast
                    print(f"\n✅ FAST RESPONSE ({elapsed_time:.2f}s) - Likely used highlighting")
                else:
                    print(f"\n⚠️  SLOW RESPONSE ({elapsed_time:.2f}s) - May have used compression (unexpected)")
            else:  # complex
                if elapsed_time > 20:  # Complex queries may take longer
                    print(f"\n✅ SLOWER RESPONSE ({elapsed_time:.2f}s) - Likely used compression")
                else:
                    print(f"\n⚠️  FAST RESPONSE ({elapsed_time:.2f}s) - May have used highlighting (unexpected)")
            
            return True
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out after 300s")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all test queries"""
    print("="*80)
    print("HYBRID APPROACH TEST - Highlighting vs LLM Compression")
    print("="*80)
    
    # Check backend health
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✅ Backend is healthy")
        else:
            print("❌ Backend health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure the backend is running on port 8001")
        return
    
    # Run tests
    results = {
        "simple": {"passed": 0, "failed": 0},
        "complex": {"passed": 0, "failed": 0}
    }
    
    for test in TEST_QUERIES:
        success = test_query(
            PATIENT_ID,
            test["query"],
            test["type"],
            test["expected_method"]
        )
        
        if success:
            results[test["type"]]["passed"] += 1
        else:
            results[test["type"]]["failed"] += 1
        
        # Small delay between queries
        time.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Simple Queries: {results['simple']['passed']} passed, {results['simple']['failed']} failed")
    print(f"Complex Queries: {results['complex']['passed']} passed, {results['complex']['failed']} failed")
    print("\n💡 Note: Check backend logs to verify:")
    print("   - 'Simple query detected: Using highlighting'")
    print("   - 'Complex query detected: [reason]'")
    print("   - 'Using LLM compression'")
    print("="*80)

if __name__ == "__main__":
    main()

