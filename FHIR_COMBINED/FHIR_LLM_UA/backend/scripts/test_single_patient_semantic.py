#!/usr/bin/env python3
"""
Single Patient Test - Semantic Search First
Tests with detailed logging showing:
- Query asked
- Answer extracted from
- Patient ID
- Source information (file, part, location)
- Proof for clinicians
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['LLM_MODEL_PATH'] = '/home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/models/llama31-8b-bnb4'

from app.api.rag_service import RAGService
from app.api.elasticsearch_client import es_client
from app.core.database import engine
from sqlalchemy import text
from datetime import datetime

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_section(title, color=Colors.CYAN):
    """Print formatted section header"""
    print(f"\n{color}{'='*80}{Colors.ENDC}")
    print(f"{color}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{color}{'='*80}{Colors.ENDC}\n")

def print_info(label, value, color=Colors.BLUE):
    """Print formatted info line"""
    print(f"{color}{Colors.BOLD}{label:.<40}{Colors.ENDC} {value}")

def get_patient_actual_data(patient_id: str):
    """Get actual patient data from database for verification"""
    try:
        with engine.connect() as conn:
            # Get conditions
            cond_query = text("""
                SELECT code, display, clinical_status, effectiveDateTime
                FROM conditions
                WHERE patient_id = :pid
                ORDER BY effectiveDateTime DESC
                LIMIT 20
            """)
            conditions = conn.execute(cond_query, {"pid": patient_id}).mappings().all()
            
            # Get observations
            obs_query = text("""
                SELECT code, display, value_numeric, value_string, unit, effectiveDateTime
                FROM observations
                WHERE patient_id = :pid
                  AND (value_numeric IS NOT NULL OR value_string IS NOT NULL)
                ORDER BY effectiveDateTime DESC
                LIMIT 50
            """)
            observations = conn.execute(obs_query, {"pid": patient_id}).mappings().all()
            
            return {
                "conditions": [dict(c) for c in conditions],
                "observations": [dict(o) for o in observations]
            }
    except Exception as e:
        print(f"{Colors.RED}Error getting patient data: {e}{Colors.ENDC}")
        return {"conditions": [], "observations": []}

def test_query(rag_service, patient_id, query, expected_data_exists=True):
    """Test a single query with detailed logging"""
    
    print_section(f"TESTING QUERY", Colors.CYAN)
    print_info("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print_info("Patient ID", patient_id)
    print_info("Query", query)
    print_info("Expected Data", "EXISTS" if expected_data_exists else "DOES NOT EXIST")
    print()
    
    # Get actual patient data for verification
    actual_data = get_patient_actual_data(patient_id)
    
    print_section("ACTUAL PATIENT DATA (For Verification)", Colors.YELLOW)
    print(f"{Colors.BOLD}Conditions:{Colors.ENDC}")
    for cond in actual_data["conditions"][:5]:
        print(f"  - {cond.get('display', 'N/A')} (Status: {cond.get('clinical_status', 'N/A')})")
    if len(actual_data["conditions"]) > 5:
        print(f"  ... and {len(actual_data['conditions']) - 5} more")
    
    print(f"\n{Colors.BOLD}Sample Observations:{Colors.ENDC}")
    for obs in actual_data["observations"][:5]:
        display = obs.get('display', 'N/A')
        value = obs.get('value_numeric') or obs.get('value_string', 'N/A')
        unit = obs.get('unit', '')
        print(f"  - {display}: {value} {unit}")
    if len(actual_data["observations"]) > 5:
        print(f"  ... and {len(actual_data['observations']) - 5} more")
    print()
    
    # Process query through RAG
    print_section("RAG PROCESSING", Colors.BLUE)
    result = rag_service.process_chat_query(patient_id, query)
    
    # Extract detailed information
    sources = result.get("sources", [])
    response = result.get("response", "")
    retrieved_count = result.get("retrieved_count", 0)
    
    # Show sources with detailed proof
    print_section("SOURCE INFORMATION (PROOF FOR CLINICIANS)", Colors.GREEN)
    print_info("Total Documents Retrieved", retrieved_count)
    print()
    
    if sources:
        print(f"{Colors.BOLD}Detailed Source Breakdown:{Colors.ENDC}\n")
        for idx, source in enumerate(sources[:10], 1):  # Show top 10 sources
            source_type = source.get("type", "unknown")
            description = source.get("description", "")
            
            print(f"{Colors.CYAN}[{idx}] Source Type: {source_type}{Colors.ENDC}")
            print(f"    Description: {description}")
            print(f"    {Colors.GREEN}✓ This information was extracted from: {source_type} data{Colors.ENDC}")
            print()
    else:
        print(f"{Colors.YELLOW}⚠️  No sources retrieved{Colors.ENDC}\n")
    
    # Show LLM response
    print_section("LLM RESPONSE", Colors.MAGENTA if hasattr(Colors, 'MAGENTA') else Colors.CYAN)
    print(f"{Colors.BOLD}Generated Answer:{Colors.ENDC}\n")
    print(response)
    print()
    
    # Verification
    print_section("VERIFICATION", Colors.YELLOW)
    
    # Expected output for queries WITHOUT data (Research-grade standard):
    # - Should clearly state: "No [specific data] available" or "Not found"
    # - Should NOT hallucinate or make up information
    # - Should be professional and clinical
    # - Should NOT say "data exists" when it doesn't
    
    # Expected output for queries WITH data:
    # - Should clearly present the data found
    # - Should cite specific values/conditions
    # - Should be accurate and grounded in retrieved data
    
    # Check if response matches expected
    response_lower = response.lower()
    has_data_indicators = any(word in response_lower for word in [
        "has", "shows", "found", "indicates", "presents", "displays", "level is", "value is", "specifically"
    ])
    has_no_data_indicators = any(word in response_lower for word in [
        "no data", "not available", "couldn't find", "no information", "not found", 
        "not explicitly stated", "does not have", "no evidence", "unavailable"
    ])
    
    if expected_data_exists:
        if has_data_indicators and not has_no_data_indicators:
            print(f"{Colors.GREEN}✅ CORRECT: Response indicates data was found (as expected){Colors.ENDC}")
            verification_status = "PASS"
        elif has_no_data_indicators:
            print(f"{Colors.RED}❌ INCORRECT: Response says no data when data exists{Colors.ENDC}")
            verification_status = "FAIL"
        else:
            print(f"{Colors.YELLOW}⚠️  UNCLEAR: Response doesn't clearly indicate data availability{Colors.ENDC}")
            verification_status = "PARTIAL"
    else:
        if has_no_data_indicators:
            print(f"{Colors.GREEN}✅ CORRECT: Response correctly indicates no data available{Colors.ENDC}")
            verification_status = "PASS"
        elif has_data_indicators:
            print(f"{Colors.RED}❌ INCORRECT: Response suggests data exists when it doesn't (possible hallucination){Colors.ENDC}")
            verification_status = "FAIL"
        else:
            print(f"{Colors.YELLOW}⚠️  UNCLEAR: Response doesn't clearly indicate data unavailability{Colors.ENDC}")
            verification_status = "PARTIAL"
    
    print()
    print(f"{Colors.BOLD}Verification Status: {verification_status}{Colors.ENDC}")
    print()
    
    return {
        "query": query,
        "patient_id": patient_id,
        "expected_data_exists": expected_data_exists,
        "retrieved_count": retrieved_count,
        "sources": sources,
        "response": response,
        "verification_status": verification_status,
        "actual_data": actual_data
    }

def main():
    """Main test function"""
    print_section("SINGLE PATIENT SEMANTIC SEARCH TEST", Colors.HEADER)
    print_info("Test Type", "Single Patient - Detailed Verification")
    print_info("Search Priority", "Semantic Search First, then Keyword")
    print_info("Purpose", "Verify correct data extraction with proof for clinicians")
    print()
    
    # Initialize RAG service
    rag_service = RAGService()
    patient_id = "000000216"  # Test patient
    
    # Verify semantic search is enabled
    print_section("SYSTEM STATUS", Colors.BLUE)
    semantic_enabled = es_client.semantic_search_enabled
    print_info("Semantic Search", "✅ ENABLED" if semantic_enabled else "❌ DISABLED")
    print_info("Keyword Search", "✅ ENABLED")
    print_info("Search Priority", "Semantic → Keyword (Hybrid)")
    print()
    
    if not semantic_enabled:
        print(f"{Colors.YELLOW}⚠️  WARNING: Semantic search is disabled. Run reindexing script first.{Colors.ENDC}")
        print(f"{Colors.YELLOW}   For now, testing with keyword search only.{Colors.ENDC}\n")
    
    # Test queries with data that EXISTS in patient's records
    print_section("="*80, Colors.CYAN)
    print_section("PHASE 1: TESTING QUERIES WITH DATA THAT EXISTS", Colors.GREEN)
    print_section("="*80, Colors.CYAN)
    
    test_results = []
    
    # Query 1: Heart disease (should find hypertensive disorder)
    result1 = test_query(
        rag_service, patient_id,
        "Does this patient have heart disease?",
        expected_data_exists=True
    )
    test_results.append(result1)
    
    # Query 2: Hypertension (should find conditions)
    result2 = test_query(
        rag_service, patient_id,
        "Does this patient have hypertension?",
        expected_data_exists=True
    )
    test_results.append(result2)
    
    # Query 3: Blood pressure (should find observations)
    result3 = test_query(
        rag_service, patient_id,
        "What are the patient's blood pressure readings?",
        expected_data_exists=True
    )
    test_results.append(result3)
    
    # Query 4: Creatinine (check if exists)
    result4 = test_query(
        rag_service, patient_id,
        "What is the patient's creatinine level?",
        expected_data_exists=None  # Unknown
    )
    test_results.append(result4)
    
    # Test queries with data that DOES NOT EXIST
    print_section("="*80, Colors.CYAN)
    print_section("PHASE 2: TESTING QUERIES WITH DATA THAT DOES NOT EXIST", Colors.RED)
    print_section("="*80, Colors.CYAN)
    
    # Query 5: Diabetes (likely doesn't exist)
    result5 = test_query(
        rag_service, patient_id,
        "Is this patient diabetic?",
        expected_data_exists=False
    )
    test_results.append(result5)
    
    # Query 6: Cancer (likely doesn't exist)
    result6 = test_query(
        rag_service, patient_id,
        "Does this patient have cancer?",
        expected_data_exists=False
    )
    test_results.append(result6)
    
    # Final Summary
    print_section("FINAL TEST SUMMARY", Colors.HEADER)
    
    passed = sum(1 for r in test_results if r["verification_status"] == "PASS")
    failed = sum(1 for r in test_results if r["verification_status"] == "FAIL")
    partial = sum(1 for r in test_results if r["verification_status"] == "PARTIAL")
    
    print_info("Total Tests", len(test_results))
    print_info("Passed", f"{passed} ✅")
    print_info("Failed", f"{failed} ❌")
    print_info("Partial", f"{partial} ⚠️")
    print()
    
    print(f"{Colors.BOLD}Detailed Results:{Colors.ENDC}\n")
    for idx, result in enumerate(test_results, 1):
        status_icon = "✅" if result["verification_status"] == "PASS" else "❌" if result["verification_status"] == "FAIL" else "⚠️"
        print(f"{idx}. {status_icon} {result['query']}")
        print(f"   Retrieved: {result['retrieved_count']} documents")
        print(f"   Status: {result['verification_status']}")
        print()
    
    print_section("TEST COMPLETE", Colors.GREEN)
    print(f"{Colors.GREEN}All test results logged above with detailed source information.{Colors.ENDC}")
    print(f"{Colors.GREEN}Clinicians can verify each answer by checking the source information.{Colors.ENDC}")

if __name__ == "__main__":
    main()

