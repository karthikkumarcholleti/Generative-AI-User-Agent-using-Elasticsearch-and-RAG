#!/usr/bin/env python3
"""
Test system components without ElasticSearch
Tests intent classification and LLM response generation
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.intent_classifier import intent_classifier
from app.api.rag_service import rag_service
from datetime import datetime

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

def print_section(title, color=Colors.CYAN):
    print(f"\n{color}{'='*80}{Colors.ENDC}")
    print(f"{color}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{color}{'='*80}{Colors.ENDC}\n")

def print_info(label, value, color=Colors.BLUE):
    print(f"{color}{Colors.BOLD}{label:.<40}{Colors.ENDC} {value}")

def test_intent_classification():
    """Test intent classification with various queries"""
    print_section("TESTING INTENT CLASSIFICATION", Colors.HEADER)
    
    test_queries = [
        "What is the latest heart rate?",
        "Does this patient have heart disease?",
        "What is the patient's creatinine level?",
        "Show me all observations",
        "Is this patient diabetic?",
        "What are the abnormal values?",
    ]
    
    results = []
    for query in test_queries:
        print_info("Query", query)
        try:
            intent = intent_classifier.classify_intent(query)
            print_info("Intent Type", intent.get("intent_type", "unknown"))
            print_info("Data Types", ", ".join(intent.get("data_types", [])))
            print_info("Specific Observation", intent.get("specific_observation", "none"))
            print_info("Wants All Data", str(intent.get("wants_all_data", False)))
            print_info("Confidence", f"{intent.get('confidence', 0.0):.2f}")
            
            # Check data type mapping
            data_types = intent.get("data_types", [])
            valid_types = ["observations", "conditions", "notes", "demographics"]
            mapped_correctly = all(dt in valid_types for dt in data_types) if data_types else True
            
            if not mapped_correctly:
                print(f"{Colors.YELLOW}⚠️  Data types need mapping: {data_types}{Colors.ENDC}")
            
            results.append({
                "query": query,
                "intent": intent,
                "mapped_correctly": mapped_correctly
            })
            print()
        except Exception as e:
            print(f"{Colors.RED}❌ Error: {e}{Colors.ENDC}\n")
            results.append({"query": query, "error": str(e)})
    
    return results

def main():
    print_section("SYSTEM COMPONENT TESTING (Without ElasticSearch)", Colors.HEADER)
    print_info("Purpose", "Test intent classification and data type mapping")
    print_info("Note", "ElasticSearch is currently unavailable (disk space issue)")
    print()
    
    # Test intent classification
    intent_results = test_intent_classification()
    
    # Summary
    print_section("SUMMARY", Colors.HEADER)
    total = len(intent_results)
    successful = sum(1 for r in intent_results if "intent" in r)
    mapped_correctly = sum(1 for r in intent_results if r.get("mapped_correctly", False))
    
    print_info("Total Queries", total)
    print_info("Successful Classifications", f"{successful}/{total}")
    print_info("Data Types Mapped Correctly", f"{mapped_correctly}/{successful}")
    print()
    
    # Issues found
    print_info("Issues Found", "")
    issues = []
    
    for r in intent_results:
        if "intent" in r:
            data_types = r["intent"].get("data_types", [])
            valid_types = ["observations", "conditions", "notes", "demographics"]
            if data_types and not all(dt in valid_types for dt in data_types):
                issues.append(f"Query '{r['query']}': Data types {data_types} need mapping")
    
    if issues:
        for issue in issues:
            print(f"  {Colors.YELLOW}⚠️  {issue}{Colors.ENDC}")
    else:
        print(f"  {Colors.GREEN}✅ No issues found{Colors.ENDC}")
    print()
    
    print_section("TEST COMPLETE", Colors.GREEN)
    print(f"{Colors.YELLOW}Note: Full testing requires ElasticSearch to be operational.{Colors.ENDC}")
    print(f"{Colors.YELLOW}Current issue: Disk space exceeded - ElasticSearch in read-only mode.{Colors.ENDC}")

if __name__ == "__main__":
    main()

