#!/usr/bin/env python3
"""
Script to identify unmapped LOINC codes in the database.
This helps identify which codes should be added to the LOINC mapper.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'FHIR_LLM_UA/backend'))

from app.api.loinc_code_mapper import LOINC_CODE_MAPPINGS
from app.api.db import get_db_connection

def get_all_observation_codes():
    """Get all unique observation codes from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT DISTINCT code, display, COUNT(*) as count
    FROM observations
    WHERE code IS NOT NULL
    GROUP BY code, display
    ORDER BY count DESC
    LIMIT 100
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return results

def identify_unmapped_codes():
    """Identify codes that are not in the LOINC mapper"""
    print("=" * 100)
    print("IDENTIFYING UNMAPPED CODES IN DATABASE")
    print("=" * 100)
    print()
    
    mapped_codes = set(LOINC_CODE_MAPPINGS.keys())
    print(f"Codes in LOINC mapper: {len(mapped_codes)}")
    print()
    
    try:
        observation_codes = get_all_observation_codes()
        print(f"Total unique codes in database: {len(observation_codes)}")
        print()
        
        unmapped = []
        mapped = []
        
        for code, display, count in observation_codes:
            if code not in mapped_codes:
                unmapped.append((code, display, count))
            else:
                mapped.append((code, display, count))
        
        print(f"✅ Mapped codes: {len(mapped)}")
        print(f"❌ Unmapped codes: {len(unmapped)}")
        print()
        
        if unmapped:
            print("=" * 100)
            print("UNMAPPED CODES (sorted by frequency):")
            print("=" * 100)
            print()
            print(f"{'Code':<15} {'Display':<50} {'Count':<10}")
            print("-" * 100)
            
            for code, display, count in sorted(unmapped, key=lambda x: x[2], reverse=True)[:50]:
                display_str = (display or "NULL")[:48]
                print(f"{code:<15} {display_str:<50} {count:<10}")
            
            print()
            print("=" * 100)
            print("RECOMMENDATION:")
            print("=" * 100)
            print()
            print("Top unmapped codes (by frequency) should be added to LOINC mapper.")
            print("However, semantic search can handle these automatically.")
            print()
            print("Priority: Add codes with high frequency and NULL display names")
            print("  - These benefit most from mapper (better display names)")
            print("  - Semantic search handles the rest")
        else:
            print("✅ All codes are mapped!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    identify_unmapped_codes()

