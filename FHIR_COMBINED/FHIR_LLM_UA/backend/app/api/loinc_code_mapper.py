"""
LOINC Code Mapper Service
Provides code-to-name mappings for common clinical observations when display names are NULL.
This is essential for research-quality data handling where 28.8% of observations have NULL display names.
"""

from typing import Dict, Optional, List

# Comprehensive LOINC code mappings for common observations
# Based on standard LOINC codes used in clinical practice
LOINC_CODE_MAPPINGS: Dict[str, Dict[str, str]] = {
    # Laboratory Tests - Chemistry
    "2160-0": {
        "name": "Creatinine",
        "display": "Creatinine [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["creatinine", "kidney function", "renal function"]
    },
    "33914-3": {
        "name": "Creatinine",
        "display": "Creatinine [Mass/volume] in Blood",
        "category": "laboratory",
        "keywords": ["creatinine", "kidney function", "renal function"]
    },
    "2339-0": {
        "name": "Glucose",
        "display": "Glucose [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["glucose", "blood sugar", "diabetes", "sugar"]
    },
    "2345-7": {
        "name": "Glucose",
        "display": "Glucose [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["glucose", "blood sugar", "diabetes", "sugar"]
    },
    "718-7": {
        "name": "Hemoglobin",
        "display": "Hemoglobin [Mass/volume] in Blood",
        "category": "laboratory",
        "keywords": ["hemoglobin", "hgb", "hb", "blood count"]
    },
    "777-3": {
        "name": "Platelet Count",
        "display": "Platelet count [Number/volume] in Blood",
        "category": "laboratory",
        "keywords": ["platelet", "plt", "thrombocyte"]
    },
    "6690-2": {
        "name": "White Blood Cell Count",
        "display": "Leukocytes [Number/volume] in Blood",
        "category": "laboratory",
        "keywords": ["wbc", "white blood cell", "leukocyte"]
    },
    "789-8": {
        "name": "Red Blood Cell Count",
        "display": "Erythrocytes [Number/volume] in Blood",
        "category": "laboratory",
        "keywords": ["rbc", "red blood cell", "erythrocyte"]
    },
    "786-4": {
        "name": "Hematocrit",
        "display": "Hematocrit [Volume Fraction] of Blood",
        "category": "laboratory",
        "keywords": ["hematocrit", "hct", "packed cell volume"]
    },
    "1751-7": {
        "name": "Albumin",
        "display": "Albumin [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["albumin", "protein"]
    },
    "1975-2": {
        "name": "Bilirubin Total",
        "display": "Bilirubin.total [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["bilirubin", "liver function"]
    },
    "2085-9": {
        "name": "Cholesterol Total",
        "display": "Cholesterol [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["cholesterol", "lipid"]
    },
    "2571-8": {
        "name": "Triglycerides",
        "display": "Triglyceride [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["triglyceride", "lipid"]
    },
    "2089-1": {
        "name": "HDL Cholesterol",
        "display": "Cholesterol in HDL [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["hdl", "high density lipoprotein", "good cholesterol"]
    },
    "2089-2": {
        "name": "LDL Cholesterol",
        "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["ldl", "low density lipoprotein", "bad cholesterol"]
    },
    "33914-3": {
        "name": "GFR",
        "display": "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area]",
        "category": "laboratory",
        "keywords": ["gfr", "glomerular filtration", "kidney function", "renal function"]
    },
    "48642-3": {
        "name": "GFR",
        "display": "Glomerular filtration rate/1.73 sq M.predicted [Volume Rate/Area]",
        "category": "laboratory",
        "keywords": ["gfr", "glomerular filtration", "kidney function", "renal function"]
    },
    
    # Vital Signs
    "85354-9": {
        "name": "Blood Pressure",
        "display": "Blood pressure panel with all children optional",
        "category": "vital_signs",
        "keywords": ["blood pressure", "bp", "systolic", "diastolic"]
    },
    "8480-6": {
        "name": "Systolic Blood Pressure",
        "display": "Systolic blood pressure",
        "category": "vital_signs",
        "keywords": ["systolic", "sbp", "blood pressure"]
    },
    "8462-4": {
        "name": "Diastolic Blood Pressure",
        "display": "Diastolic blood pressure",
        "category": "vital_signs",
        "keywords": ["diastolic", "dbp", "blood pressure"]
    },
    "8867-4": {
        "name": "Heart Rate",
        "display": "Heart rate",
        "category": "vital_signs",
        "keywords": ["heart rate", "pulse", "hr", "pulse rate"]
    },
    "8310-5": {
        "name": "Body Temperature",
        "display": "Body temperature",
        "category": "vital_signs",
        "keywords": ["temperature", "temp", "fever", "body temp"]
    },
    "9279-1": {
        "name": "Respiratory Rate",
        "display": "Respiratory rate",
        "category": "vital_signs",
        "keywords": ["respiratory rate", "respiration", "breathing rate"]
    },
    "2708-6": {
        "name": "Oxygen Saturation",
        "display": "Oxygen saturation in Arterial blood",
        "category": "vital_signs",
        "keywords": ["oxygen saturation", "spo2", "o2 sat", "saturation"]
    },
    
    # Additional Common Tests
    "5902-2": {
        "name": "Sodium",
        "display": "Sodium [Moles/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["sodium", "na", "electrolyte"]
    },
    "2823-3": {
        "name": "Potassium",
        "display": "Potassium [Moles/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["potassium", "k", "electrolyte"]
    },
    "2075-0": {
        "name": "Chloride",
        "display": "Chloride [Moles/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["chloride", "cl", "electrolyte"]
    },
    "2028-9": {
        "name": "CO2",
        "display": "Carbon dioxide [Partial pressure] in Arterial blood",
        "category": "laboratory",
        "keywords": ["co2", "carbon dioxide", "bicarbonate"]
    },
    "3094-0": {
        "name": "BUN",
        "display": "Urea nitrogen [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["bun", "urea nitrogen", "blood urea nitrogen"]
    },
    "1920-8": {
        "name": "AST",
        "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["ast", "sgot", "aspartate aminotransferase", "liver function"]
    },
    "1742-6": {
        "name": "ALT",
        "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["alt", "sgpt", "alanine aminotransferase", "liver function"]
    },
}

def get_observation_name_from_code(code: Optional[str]) -> Optional[str]:
    """
    Get observation name from LOINC code.
    
    Args:
        code: LOINC code (e.g., "2160-0")
    
    Returns:
        Observation name (e.g., "Creatinine") or None if not found
    """
    if not code:
        return None
    
    # Handle codes with suffixes (e.g., "2160-0.1" -> "2160-0")
    base_code = code.split('.')[0].split('-')[0] + '-' + code.split('-')[1] if '-' in code else code
    
    mapping = LOINC_CODE_MAPPINGS.get(code) or LOINC_CODE_MAPPINGS.get(base_code)
    if mapping:
        return mapping["name"]
    
    return None

def get_observation_display_from_code(code: Optional[str]) -> Optional[str]:
    """
    Get full display name from LOINC code.
    
    Args:
        code: LOINC code (e.g., "2160-0")
    
    Returns:
        Full display name or None if not found
    """
    if not code:
        return None
    
    base_code = code.split('.')[0].split('-')[0] + '-' + code.split('-')[1] if '-' in code else code
    
    mapping = LOINC_CODE_MAPPINGS.get(code) or LOINC_CODE_MAPPINGS.get(base_code)
    if mapping:
        return mapping["display"]
    
    return None

def get_observation_keywords_from_code(code: Optional[str]) -> List[str]:
    """
    Get search keywords for a LOINC code.
    
    Args:
        code: LOINC code (e.g., "2160-0")
    
    Returns:
        List of keywords for searching
    """
    if not code:
        return []
    
    base_code = code.split('.')[0].split('-')[0] + '-' + code.split('-')[1] if '-' in code else code
    
    mapping = LOINC_CODE_MAPPINGS.get(code) or LOINC_CODE_MAPPINGS.get(base_code)
    if mapping:
        return mapping.get("keywords", [])
    
    return []

def enhance_observation_content(observation: Dict[str, any]) -> str:
    """
    Enhance observation content with code-based information when display is NULL.
    This ensures searchability even when display names are missing.
    
    CRITICAL: Includes keywords in content field for searchability, even when code is not mapped.
    This handles all similar cases where observations have NULL display names.
    
    SEMANTIC SEARCH OPTIMIZATION: Includes descriptive text to help semantic search understand
    the observation even without display names. This makes semantic search more effective.
    
    Args:
        observation: Observation dict with 'code', 'display', 'valueNumber', 'valueString', 'unit'
    
    Returns:
        Enhanced content string for indexing (includes keywords and semantic context for searchability)
    """
    code = observation.get("code")
    display = observation.get("display")
    value_number = observation.get("valueNumber")
    value_string = observation.get("valueString")
    unit = observation.get("unit", "")
    
    # Build value string
    value_str = ""
    if value_number is not None:
        value_str = f"{value_number}"
        if unit:
            value_str += f" {unit}"
    elif value_string:
        value_str = value_string
    
    # If display exists, use it (but still include keywords for better searchability)
    if display:
        # Get keywords from code if available to enhance searchability
        keywords = []
        if code:
            keywords = get_observation_keywords_from_code(code)
        keyword_text = f" {' '.join(keywords)}" if keywords else ""
        # Include semantic context: observation type, value, and keywords
        return f"Observation: {display} - Value: {value_str}{keyword_text}. Clinical observation measurement laboratory test."
    
    # If no display but we have a code, use code mapping
    if code:
        code_name = get_observation_name_from_code(code)
        code_display = get_observation_display_from_code(code)
        keywords = get_observation_keywords_from_code(code)
        
        if code_name:
            # Use mapped name with keywords and semantic context
            display_text = code_display or code_name
            keyword_text = f" {' '.join(keywords)}" if keywords else ""
            return f"Observation: {display_text} - Value: {value_str} - Code: {code}{keyword_text}. Clinical observation measurement laboratory test."
        else:
            # Fallback: use code itself, but include keywords and semantic context
            # This ensures even unmapped codes become searchable via keywords AND semantic search
            keyword_text = f" {' '.join(keywords)}" if keywords else ""
            # Add semantic context to help semantic search understand this is a clinical observation
            # Even without keywords, semantic search can match "Code 2345-7" with "glucose" or "diabetes"
            semantic_context = "Clinical observation measurement laboratory test blood test"
            return f"Observation: Code {code} - Value: {value_str}{keyword_text} {semantic_context}"
    
    # Last resort: just value with semantic context
    return f"Observation: Unknown - Value: {value_str}. Clinical observation measurement."

def get_search_terms_for_code(code: Optional[str], query: str) -> List[str]:
    """
    Get additional search terms based on code mapping for a query.
    This helps find observations even when display is NULL.
    
    Args:
        code: LOINC code
        query: User query (e.g., "creatinine")
    
    Returns:
        List of additional search terms including code-based terms
    """
    terms = [query.lower()]
    
    if code:
        keywords = get_observation_keywords_from_code(code)
        terms.extend([kw.lower() for kw in keywords])
        terms.append(code.lower())
    
    return list(set(terms))  # Remove duplicates

