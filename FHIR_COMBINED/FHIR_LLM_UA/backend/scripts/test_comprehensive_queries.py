#!/usr/bin/env python3
"""
Comprehensive Query Testing Script
Tests the system with various queries to verify semantic search and identify problems
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.rag_service import rag_service
from app.api.elasticsearch_client import es_client
from datetime import datetime
import json

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    GRAY = '\033[90m'

def print_section(title, color=Colors.CYAN):
    """Print a formatted section header"""
    print(f"\n{color}{'='*80}{Colors.ENDC}")
    print(f"{color}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{color}{'='*80}{Colors.ENDC}\n")

def print_info(label, value, color=Colors.BLUE):
    """Print formatted info line"""
    print(f"{color}{Colors.BOLD}{label:.<40}{Colors.ENDC} {value}")

def print_data(label, data, color=Colors.GREEN):
    """Print formatted data line"""
    print(f"{color}  {label}:{Colors.ENDC} {data}")

def test_query(patient_id, query, query_type="general"):
    """Test a single query and return detailed results"""
    
    print_section(f"TESTING: {query_type.upper()}", Colors.CYAN)
    print_info("Query", query)
    print_info("Patient ID", patient_id)
    print_info("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        # Process query
        result = rag_service.process_chat_query(patient_id, query)
        
        # Extract information
        response = result.get("response", "")
        intent = result.get("intent", {})
        sources = result.get("sources", [])
        retrieved_count = result.get("retrieved_count", 0)
        data_found = result.get("data_found", False)
        chart = result.get("chart")
        
        # Display results
        print_info("Intent Type", intent.get("type", "unknown"))
        print_info("Data Types", ", ".join(intent.get("data_types", [])))
        print_info("Retrieved Documents", retrieved_count)
        print_info("Data Found", "✅ YES" if data_found else "❌ NO")
        print()
        
        # Show sources
        if sources:
            print_data("Sources Retrieved", f"{len(sources)} documents")
            print(f"{Colors.GRAY}  Top 3 sources:{Colors.ENDC}")
            for idx, source in enumerate(sources[:3], 1):
                source_type = source.get("type", "unknown")
                description = source.get("description", "")[:100]
                print(f"    {idx}. [{source_type}] {description}")
            if len(sources) > 3:
                print(f"    ... and {len(sources) - 3} more")
            print()
        else:
            print_data("Sources Retrieved", "0 documents")
            print()
        
        # Show response
        print_info("LLM Response", "")
        print(f"{Colors.GREEN}{response[:500]}{Colors.ENDC}")
        if len(response) > 500:
            print(f"{Colors.GRAY}  ... (truncated, total length: {len(response)} chars){Colors.ENDC}")
        print()
        
        # Show chart if generated
        if chart:
            print_info("Chart Generated", f"✅ YES - Type: {chart.get('type', 'unknown')}")
        else:
            print_info("Chart Generated", "❌ NO")
        print()
        
        # Analysis
        print_info("Analysis", "")
        issues = []
        if not data_found and retrieved_count == 0:
            issues.append("⚠️  No data retrieved - query may not match patient data")
        if retrieved_count > 0 and not data_found:
            issues.append("⚠️  Data retrieved but marked as not found - possible issue")
        if len(response) < 50:
            issues.append("⚠️  Response is very short - may be incomplete")
        if len(response) > 2000:
            issues.append("⚠️  Response is very long - may be too verbose")
        
        if issues:
            for issue in issues:
                print(f"  {Colors.YELLOW}{issue}{Colors.ENDC}")
        else:
            print(f"  {Colors.GREEN}✅ No obvious issues detected{Colors.ENDC}")
        print()
        
        return {
            "query": query,
            "query_type": query_type,
            "response": response,
            "retrieved_count": retrieved_count,
            "data_found": data_found,
            "intent": intent,
            "sources_count": len(sources),
            "has_chart": chart is not None,
            "issues": issues,
            "success": True
        }
        
    except Exception as e:
        print(f"{Colors.RED}❌ ERROR: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        print()
        
        return {
            "query": query,
            "query_type": query_type,
            "error": str(e),
            "success": False
        }

def main():
    """Main test function"""
    print_section("COMPREHENSIVE QUERY TESTING", Colors.HEADER)
    print_info("Purpose", "Test semantic search with various queries")
    print_info("Test Patient", "000000216 (or first available)")
    print()
    
    # Check system status
    print_section("SYSTEM STATUS", Colors.BLUE)
    semantic_enabled = es_client.semantic_search_enabled
    print_info("Semantic Search", "✅ ENABLED" if semantic_enabled else "❌ DISABLED")
    print_info("ElasticSearch", "✅ CONNECTED" if es_client.is_connected() else "❌ DISCONNECTED")
    print()
    
    if not semantic_enabled:
        print(f"{Colors.YELLOW}⚠️  WARNING: Semantic search is disabled. Results may be limited.{Colors.ENDC}\n")
    
    # Test patient
    patient_id = "000000216"
    
    # Test queries
    test_queries = [
        # Direct questions
        ("What is the latest heart rate?", "direct_observation"),
        ("What is the patient's creatinine level?", "direct_observation"),
        ("What is the patient's blood pressure?", "direct_observation"),
        
        # Condition questions (semantic search test)
        ("Does this patient have heart disease?", "condition_semantic"),
        ("Is this patient diabetic?", "condition_semantic"),
        ("Does this patient have hypertension?", "condition_semantic"),
        
        # Comprehensive questions
        ("What are all the patient's conditions?", "comprehensive"),
        ("Show me all observations", "comprehensive"),
        ("What is the patient's medical history?", "comprehensive"),
        
        # Analysis questions
        ("What are the abnormal values?", "analysis"),
        ("Are there any concerning observations?", "analysis"),
        
        # Questions that likely don't have data
        ("Does this patient have cancer?", "negative_test"),
        ("What is the patient's glucose level?", "unknown_data"),
    ]
    
    results = []
    
    # Run tests
    for query, query_type in test_queries:
        result = test_query(patient_id, query, query_type)
        results.append(result)
        
        # Small delay between queries
        import time
        time.sleep(1)
    
    # Summary
    print_section("TEST SUMMARY", Colors.HEADER)
    
    successful = sum(1 for r in results if r.get("success", False))
    failed = sum(1 for r in results if not r.get("success", False))
    
    print_info("Total Queries", len(results))
    print_info("Successful", f"{successful} ✅")
    print_info("Failed", f"{failed} ❌")
    print()
    
    # Group by query type
    print_info("Results by Query Type", "")
    type_counts = {}
    for r in results:
        qtype = r.get("query_type", "unknown")
        if qtype not in type_counts:
            type_counts[qtype] = {"total": 0, "success": 0, "retrieved": 0}
        type_counts[qtype]["total"] += 1
        if r.get("success"):
            type_counts[qtype]["success"] += 1
        if r.get("retrieved_count", 0) > 0:
            type_counts[qtype]["retrieved"] += 1
    
    for qtype, counts in type_counts.items():
        print(f"  {qtype}: {counts['success']}/{counts['total']} successful, {counts['retrieved']} retrieved data")
    print()
    
    # Issues found
    all_issues = []
    for r in results:
        if r.get("issues"):
            all_issues.extend(r["issues"])
    
    if all_issues:
        print_info("Issues Found", f"{len(set(all_issues))} unique issues")
        for issue in set(all_issues):
            print(f"  {Colors.YELLOW}{issue}{Colors.ENDC}")
    else:
        print_info("Issues Found", "✅ None")
    print()
    
    # Detailed results
    print_section("DETAILED RESULTS", Colors.BLUE)
    for idx, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        retrieved = result.get("retrieved_count", 0)
        data_found = result.get("data_found", False)
        
        print(f"{idx}. {status} {result['query']}")
        print(f"   Retrieved: {retrieved} docs | Data Found: {'✅' if data_found else '❌'}")
        if result.get("issues"):
            print(f"   Issues: {len(result['issues'])}")
        print()
    
    print_section("TEST COMPLETE", Colors.GREEN)
    
    # Save results to file
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"{Colors.GREEN}Results saved to: {output_file}{Colors.ENDC}")

if __name__ == "__main__":
    main()

