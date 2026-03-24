"""
Condition Categorization Module
Ports the full-stack team's categorization logic to Python for use in LLM backend.
"""

from typing import Dict, Optional, Tuple
import re

# Code-based category mapping (SNOMED CT codes)
CONDITION_CATEGORIES: Dict[str, Dict[str, str]] = {
    # Diabetes & Metabolic
    "307496006": {"name": "Diabetes", "category": "Metabolic", "priority": "high"},
    "44054006": {"name": "Type 2 Diabetes", "category": "Metabolic", "priority": "high"},
    
    # Cardiovascular
    "38341003": {"name": "Hypertension", "category": "Cardiovascular", "priority": "high"},
    "56265001": {"name": "Heart Disease", "category": "Cardiovascular", "priority": "high"},
    "25064002": {"name": "Heart Failure", "category": "Cardiovascular", "priority": "high"},
    
    # Respiratory
    "195967001": {"name": "Asthma", "category": "Respiratory", "priority": "high"},
    "13645005": {"name": "COPD", "category": "Respiratory", "priority": "high"},
    "233604007": {"name": "Chronic Obstructive Pulmonary Disease", "category": "Respiratory", "priority": "high"},
    
    # Musculoskeletal
    "3723001": {"name": "Arthritis", "category": "Musculoskeletal", "priority": "medium"},
    "203082005": {"name": "Fibromyalgia", "category": "Musculoskeletal", "priority": "medium"},
    "64859006": {"name": "Osteoporosis", "category": "Musculoskeletal", "priority": "medium"},
    
    # Mental Health
    "35489007": {"name": "Depression", "category": "Mental Health", "priority": "medium"},
    "197480006": {"name": "Anxiety", "category": "Mental Health", "priority": "medium"},
    "55822004": {"name": "Major Depression", "category": "Mental Health", "priority": "high"},
    
    # Neurological
    "26929004": {"name": "Alzheimer's Disease", "category": "Neurological", "priority": "high"},
    "49049000": {"name": "Parkinson's Disease", "category": "Neurological", "priority": "high"},
    "24700007": {"name": "Multiple Sclerosis", "category": "Neurological", "priority": "high"},
    "230690007": {"name": "Stroke", "category": "Neurological", "priority": "high"},
    
    # Metabolic & Endocrine
    "414916001": {"name": "Obesity", "category": "Metabolic", "priority": "medium"},
    "709044004": {"name": "Chronic Kidney Disease", "category": "Renal", "priority": "high"},
    
    # Oncology
    "363346000": {"name": "Cancer", "category": "Oncology", "priority": "high"},
}

# Pattern-based category mapping (text patterns)
CONDITION_PATTERNS: Dict[str, Dict[str, str]] = {
    # Diabetes & Metabolic variations
    "diabetes": {"category": "Metabolic", "priority": "high"},
    "diabetic": {"category": "Metabolic", "priority": "high"},
    "dm": {"category": "Metabolic", "priority": "high"},
    "diabetes mellitus": {"category": "Metabolic", "priority": "high"},
    "type 2 diabetes": {"category": "Metabolic", "priority": "high"},
    "type 1 diabetes": {"category": "Metabolic", "priority": "high"},
    
    # Hypertension variations
    "hypertension": {"category": "Cardiovascular", "priority": "high"},
    "htn": {"category": "Cardiovascular", "priority": "high"},
    "high blood pressure": {"category": "Cardiovascular", "priority": "high"},
    "essential hypertension": {"category": "Cardiovascular", "priority": "high"},
    
    # Heart conditions
    "heart": {"category": "Cardiovascular", "priority": "high"},
    "cardiac": {"category": "Cardiovascular", "priority": "high"},
    "coronary": {"category": "Cardiovascular", "priority": "high"},
    "myocardial": {"category": "Cardiovascular", "priority": "high"},
    "heart disease": {"category": "Cardiovascular", "priority": "high"},
    "heart failure": {"category": "Cardiovascular", "priority": "high"},
    "congestive heart failure": {"category": "Cardiovascular", "priority": "high"},
    
    # Respiratory conditions
    "copd": {"category": "Respiratory", "priority": "high"},
    "asthma": {"category": "Respiratory", "priority": "high"},
    "pneumonia": {"category": "Respiratory", "priority": "high"},
    "bronchitis": {"category": "Respiratory", "priority": "medium"},
    "bronchial asthma": {"category": "Respiratory", "priority": "high"},
    "chronic obstructive": {"category": "Respiratory", "priority": "high"},
    
    # Mental health
    "depression": {"category": "Mental Health", "priority": "medium"},
    "anxiety": {"category": "Mental Health", "priority": "medium"},
    "bipolar": {"category": "Mental Health", "priority": "high"},
    "ptsd": {"category": "Mental Health", "priority": "high"},
    "major depression": {"category": "Mental Health", "priority": "high"},
    "depressive": {"category": "Mental Health", "priority": "medium"},
    
    # Neurological
    "stroke": {"category": "Neurological", "priority": "high"},
    "epilepsy": {"category": "Neurological", "priority": "high"},
    "seizure": {"category": "Neurological", "priority": "high"},
    "dementia": {"category": "Neurological", "priority": "high"},
    "alzheimer": {"category": "Neurological", "priority": "high"},
    "parkinson": {"category": "Neurological", "priority": "high"},
    "multiple sclerosis": {"category": "Neurological", "priority": "high"},
    "ms": {"category": "Neurological", "priority": "high"},
    
    # Musculoskeletal
    "arthritis": {"category": "Musculoskeletal", "priority": "medium"},
    "osteoarthritis": {"category": "Musculoskeletal", "priority": "medium"},
    "rheumatoid": {"category": "Musculoskeletal", "priority": "high"},
    "fibromyalgia": {"category": "Musculoskeletal", "priority": "medium"},
    "osteoporosis": {"category": "Musculoskeletal", "priority": "medium"},
    "bone disease": {"category": "Musculoskeletal", "priority": "medium"},
    
    # Gastrointestinal
    "crohn": {"category": "Gastrointestinal", "priority": "high"},
    "colitis": {"category": "Gastrointestinal", "priority": "high"},
    "ibd": {"category": "Gastrointestinal", "priority": "high"},
    "ibs": {"category": "Gastrointestinal", "priority": "medium"},
    "gastroenteritis": {"category": "Gastrointestinal", "priority": "medium"},
    
    # Renal
    "kidney": {"category": "Renal", "priority": "high"},
    "renal": {"category": "Renal", "priority": "high"},
    "ckd": {"category": "Renal", "priority": "high"},
    "chronic kidney": {"category": "Renal", "priority": "high"},
    "nephropathy": {"category": "Renal", "priority": "high"},
    
    # Metabolic & Endocrine
    "obesity": {"category": "Metabolic", "priority": "medium"},
    "obese": {"category": "Metabolic", "priority": "medium"},
    "thyroid": {"category": "Endocrine", "priority": "medium"},
    "hypothyroid": {"category": "Endocrine", "priority": "medium"},
    "hyperthyroid": {"category": "Endocrine", "priority": "medium"},
    
    # Oncology
    "cancer": {"category": "Oncology", "priority": "high"},
    "tumor": {"category": "Oncology", "priority": "high"},
    "malignancy": {"category": "Oncology", "priority": "high"},
    "neoplasm": {"category": "Oncology", "priority": "high"},
    
    # Common ICD-10 patterns
    "e86": {"category": "Metabolic", "priority": "medium"},  # Dehydration
    "e87": {"category": "Metabolic", "priority": "medium"},  # Electrolyte imbalance
    "g43": {"category": "Neurological", "priority": "medium"},  # Migraine
    "k52": {"category": "Gastrointestinal", "priority": "medium"},  # Gastroenteritis
    "i10": {"category": "Cardiovascular", "priority": "high"},  # Essential hypertension
    "e11": {"category": "Metabolic", "priority": "high"},  # Type 2 diabetes
    "j44": {"category": "Respiratory", "priority": "high"},  # COPD
    "j45": {"category": "Respiratory", "priority": "high"},  # Asthma
}

# Category precedence order (for sorting)
CATEGORY_PRECEDENCE = [
    "Cardiovascular",
    "Metabolic",
    "Respiratory",
    "Neurological",
    "Mental Health",
    "Musculoskeletal",
    "Gastrointestinal",
    "Renal",
    "Endocrine",
    "Oncology",
    "Infectious",
    "Pregnancy",
    "Therapy",
    "Symptoms",
    "Acute",
    "Other"
]

def categorize_condition(
    code: Optional[str] = None,
    display: Optional[str] = None,
    clinical_status: Optional[str] = None
) -> Dict[str, str]:
    """
    Categorize a condition based on code and/or display text.
    
    Args:
        code: SNOMED CT code or ICD-10 code
        display: Display name of the condition
        clinical_status: Clinical status (active, inactive, unknown)
    
    Returns:
        Dictionary with keys: name, category, priority, status, originalDisplay, code
    """
    clean_code = (code or "").strip()
    clean_display = (display or "").strip()
    clean_status = (clinical_status or "").strip() or "unknown"
    search_text = f"{clean_code} {clean_display}".lower()
    
    # First, try exact code match (SNOMED CT codes)
    if clean_code and clean_code in CONDITION_CATEGORIES:
        category_info = CONDITION_CATEGORIES[clean_code]
        priority = category_info["priority"]
        
        # Adjust priority based on clinical status
        if clean_status == "active" and priority == "low":
            priority = "medium"
        elif clean_status == "unknown" and priority == "high":
            priority = "medium"
        
        return {
            "name": category_info["name"],
            "category": category_info["category"],
            "priority": priority,
            "status": clean_status,
            "originalDisplay": clean_display,
            "code": clean_code
        }
    
    # Handle ICD-10 codes (like E86.0, G43.909, K52.9)
    if clean_code and re.match(r"^[A-Z]\d{2}(\.\d+)?", clean_code):
        icd10_pattern = clean_code[:3].lower()
        if icd10_pattern in CONDITION_PATTERNS:
            pattern_info = CONDITION_PATTERNS[icd10_pattern]
            priority = pattern_info["priority"]
            
            if clean_status == "active" and priority == "low":
                priority = "medium"
            
            return {
                "name": clean_display or clean_code,
                "category": pattern_info["category"],
                "priority": priority,
                "status": clean_status,
                "originalDisplay": clean_display,
                "code": clean_code
            }
    
    # Try pattern matching on display text
    for pattern, pattern_info in CONDITION_PATTERNS.items():
        if pattern in search_text:
            # Clean up the display name (remove ICD codes, clean formatting)
            clean_name = clean_display
            if clean_name:
                # Remove ICD-10 codes from display names (e.g., "E86.0^Dehydration^ICD10" -> "Dehydration")
                clean_name = re.sub(r"\^[^^]*\^ICD10$", "", clean_name)
                clean_name = re.sub(r"^\w+\.\d+\^", "", clean_name)
                # Remove extra formatting
                clean_name = clean_name.replace("^", " ").strip()
            
            priority = pattern_info["priority"]
            if clean_status == "active" and priority == "low":
                priority = "medium"
            
            return {
                "name": clean_name or pattern.capitalize(),
                "category": pattern_info["category"],
                "priority": priority,
                "status": clean_status,
                "originalDisplay": clean_display,
                "code": clean_code
            }
    
    # Handle common medical terms
    if "acute" in search_text or "infection" in search_text:
        return {
            "name": clean_display or "Acute Condition",
            "category": "Acute",
            "priority": "low",
            "status": clean_status,
            "originalDisplay": clean_display,
            "code": clean_code
        }
    
    # Handle drug therapy and long-term conditions
    if "drug therapy" in search_text or "long term" in search_text:
        return {
            "name": clean_display or "Long-term Drug Therapy",
            "category": "Therapy",
            "priority": "low",
            "status": clean_status,
            "originalDisplay": clean_display,
            "code": clean_code
        }
    
    # Handle weakness and general symptoms
    if "weakness" in search_text or "fatigue" in search_text:
        return {
            "name": clean_display or "General Weakness",
            "category": "Symptoms",
            "priority": "low",
            "status": clean_status,
            "originalDisplay": clean_display,
            "code": clean_code
        }
    
    # Default fallback
    final_name = clean_display or clean_code or "Unknown Condition"
    return {
        "name": final_name,
        "category": "Other",
        "priority": "low",
        "status": clean_status,
        "originalDisplay": clean_display,
        "code": clean_code
    }


def group_conditions_by_category(conditions: list) -> Dict[str, list]:
    """
    Group a list of conditions by category.
    
    Args:
        conditions: List of condition dictionaries with category field
    
    Returns:
        Dictionary mapping category names to lists of conditions
    """
    grouped = {}
    for condition in conditions:
        category = condition.get("category", "Other")
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(condition)
    
    # Sort categories by precedence
    sorted_categories = sorted(
        grouped.items(),
        key=lambda x: (
            CATEGORY_PRECEDENCE.index(x[0]) if x[0] in CATEGORY_PRECEDENCE else 999,
            -len(x[1])  # Secondary sort by count (descending)
        )
    )
    
    return dict(sorted_categories)


def get_category_color(category: str) -> str:
    """
    Get Tailwind CSS color class for a category.
    
    Args:
        category: Category name
    
    Returns:
        Tailwind CSS class string
    """
    colors = {
        "Cardiovascular": "bg-red-50 border-red-200 text-red-800",
        "Respiratory": "bg-blue-50 border-blue-200 text-blue-800",
        "Mental Health": "bg-purple-50 border-purple-200 text-purple-800",
        "Neurological": "bg-indigo-50 border-indigo-200 text-indigo-800",
        "Musculoskeletal": "bg-orange-50 border-orange-200 text-orange-800",
        "Gastrointestinal": "bg-green-50 border-green-200 text-green-800",
        "Renal": "bg-cyan-50 border-cyan-200 text-cyan-800",
        "Endocrine": "bg-pink-50 border-pink-200 text-pink-800",
        "Metabolic": "bg-yellow-50 border-yellow-200 text-yellow-800",
        "Oncology": "bg-rose-50 border-rose-200 text-rose-800",
        "Acute": "bg-yellow-50 border-yellow-200 text-yellow-800",
        "Other": "bg-gray-50 border-gray-200 text-gray-800"
    }
    return colors.get(category, "bg-gray-50 border-gray-200 text-gray-800")


def get_priority_color(priority: str) -> str:
    """
    Get Tailwind CSS color class for a priority level.
    
    Args:
        priority: Priority level (high, medium, low)
    
    Returns:
        Tailwind CSS class string
    """
    colors = {
        "high": "bg-red-100 text-red-800 border-red-200",
        "medium": "bg-yellow-100 text-yellow-800 border-yellow-200",
        "low": "bg-green-100 text-green-800 border-green-200"
    }
    return colors.get(priority, "bg-gray-100 text-gray-800 border-gray-200")

