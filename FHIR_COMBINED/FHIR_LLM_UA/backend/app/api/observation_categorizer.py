"""
Observation Categorization Module
Categorizes observations into clinical categories similar to conditions.
Used for organizing observations when displaying "all observations".
"""

from typing import Dict, Optional, List, Tuple, Any
import re

# Observation category patterns (text-based matching)
OBSERVATION_CATEGORIES: Dict[str, Dict[str, any]] = {
    # Vital Signs
    "vital_signs": {
        "keywords": [
            "heart rate", "pulse", "hr", "bpm",
            "blood pressure", "systolic", "diastolic", "bp", "mean arterial",
            "temperature", "temp", "body temp", "body temperature",
            "respiratory rate", "respiration", "rr", "respiratory",
            "oxygen saturation", "spo2", "o2 sat", "oxygen",
            "body height", "height",
            "body weight", "weight",
            "bmi", "body mass index"
        ],
        "display_name": "Vital Signs",
        "color": "bg-blue-50 border-blue-200 text-blue-800",
        "priority": "high"
    },
    
    # Cardiovascular
    "cardiovascular": {
        "keywords": [
            "heart rate", "pulse", "hr", "bpm",
            "blood pressure", "systolic", "diastolic", "bp",
            "troponin", "cardiac", "bnp", "nt-probnp",
            "mean arterial", "map"
        ],
        "display_name": "Cardiovascular",
        "color": "bg-red-50 border-red-200 text-red-800",
        "priority": "high"
    },
    
    # Metabolic
    "metabolic": {
        "keywords": [
            "glucose", "blood sugar", "blood glucose",
            "cholesterol", "total cholesterol",
            "ldl", "low density lipoprotein",
            "hdl", "high density lipoprotein",
            "triglyceride", "triglycerides",
            "lipid", "lipids"
        ],
        "display_name": "Metabolic",
        "color": "bg-yellow-50 border-yellow-200 text-yellow-800",
        "priority": "high"
    },
    
    # Renal
    "renal": {
        "keywords": [
            "creatinine",
            "gfr", "glomerular filtration", "glomerular filtration rate",
            "bun", "urea nitrogen", "urea",
            "urine", "urinalysis"
        ],
        "display_name": "Renal",
        "color": "bg-cyan-50 border-cyan-200 text-cyan-800",
        "priority": "high"
    },
    
    # Hematology
    "hematology": {
        "keywords": [
            "hemoglobin", "hgb", "hgb a1c",
            "hematocrit", "hct",
            "rbc", "red blood cell", "erythrocyte", "erythrocytes",
            "wbc", "white blood cell", "leukocyte", "leukocytes",
            "platelet", "platelets",
            "lymphocyte", "lymphocytes",
            "monocyte", "monocytes",
            "neutrophil", "neutrophils",
            "eosinophil", "eosinophils",
            "basophil", "basophils",
            "mcv", "mean corpuscular volume",
            "mch", "mean corpuscular hemoglobin",
            "mchc", "mean corpuscular hemoglobin concentration",
            "rdw", "red cell distribution width"
        ],
        "display_name": "Hematology",
        "color": "bg-pink-50 border-pink-200 text-pink-800",
        "priority": "high"
    },
    
    # Electrolytes
    "electrolytes": {
        "keywords": [
            "sodium", "na",
            "potassium", "k",
            "calcium", "ca",
            "magnesium", "mg",
            "chloride", "cl",
            "phosphorus", "phosphate", "phos",
            "bicarbonate", "hco3", "co2", "carbon dioxide",
            "anion gap"
        ],
        "display_name": "Electrolytes",
        "color": "bg-green-50 border-green-200 text-green-800",
        "priority": "medium"
    },
    
    # Liver Function
    "liver_function": {
        "keywords": [
            "alt", "alanine aminotransferase", "sgpt",
            "ast", "aspartate aminotransferase", "sgot",
            "alkaline phosphatase", "alp",
            "bilirubin", "total bilirubin", "direct bilirubin", "indirect bilirubin",
            "albumin",
            "protein", "total protein",
            "a/g ratio", "albumin/globulin",
            "pt", "prothrombin time", "inr", "international normalized ratio"
        ],
        "display_name": "Liver Function",
        "color": "bg-orange-50 border-orange-200 text-orange-800",
        "priority": "high"
    },
    
    # Respiratory
    "respiratory": {
        "keywords": [
            "oxygen saturation", "spo2", "o2 sat", "oxygen",
            "respiratory rate", "respiration", "rr",
            "fio2", "fraction of inspired oxygen",
            "peep", "positive end expiratory pressure"
        ],
        "display_name": "Respiratory",
        "color": "bg-indigo-50 border-indigo-200 text-indigo-800",
        "priority": "high"
    },
    
    # Anthropometric
    "anthropometric": {
        "keywords": [
            "bmi", "body mass index",
            "weight", "body weight",
            "height", "body height",
            "body surface area", "bsa"
        ],
        "display_name": "Anthropometric",
        "color": "bg-purple-50 border-purple-200 text-purple-800",
        "priority": "low"
    },
    
    # Other (default category)
    "other": {
        "keywords": [],
        "display_name": "Other",
        "color": "bg-gray-50 border-gray-200 text-gray-800",
        "priority": "low"
    }
}

# Category precedence order (for sorting)
CATEGORY_PRECEDENCE = [
    "vital_signs",
    "cardiovascular",
    "metabolic",
    "renal",
    "hematology",
    "electrolytes",
    "liver_function",
    "respiratory",
    "anthropometric",
    "other"
]

def categorize_observation(display: str, code: Optional[str] = None) -> Dict[str, str]:
    """
    Categorize an observation based on its display name and/or code.
    Uses LOINC code mapper when display is NULL to ensure proper categorization.
    
    Args:
        display: Display name of the observation
        code: Observation code (optional)
    
    Returns:
        Dictionary with keys: category, display_name, color, priority
    """
    # If display is NULL, use LOINC code mapper (fix for vital signs with NULL display)
    if not display and code:
        try:
            from .loinc_code_mapper import get_observation_display_from_code
            display = get_observation_display_from_code(code) or ""
        except ImportError:
            pass
    
    if not display:
        return {
            "category": "other",
            "display_name": "Other",
            "color": OBSERVATION_CATEGORIES["other"]["color"],
            "priority": "low"
        }
    
    display_lower = display.lower()
    search_text = f"{code or ''} {display_lower}".lower()
    
    # Check each category (in precedence order)
    for category_key in CATEGORY_PRECEDENCE:
        if category_key == "other":
            continue  # Skip "other" - it's the fallback
        
        category_info = OBSERVATION_CATEGORIES[category_key]
        keywords = category_info["keywords"]
        
        # Check if any keyword matches
        for keyword in keywords:
            if keyword in search_text:
                return {
                    "category": category_key,
                    "display_name": category_info["display_name"],
                    "color": category_info["color"],
                    "priority": category_info["priority"]
                }
    
    # Default to "other"
    return {
        "category": "other",
        "display_name": "Other",
        "color": OBSERVATION_CATEGORIES["other"]["color"],
        "priority": "low"
    }

def group_observations_by_category(observations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group a list of observations by their category.
    
    Args:
        observations: List of observation dictionaries with 'display' and optionally 'code' keys
    
    Returns:
        Dictionary mapping category keys to lists of categorized observations
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    
    for obs in observations:
        display = obs.get("display", "")
        code = obs.get("code")
        
        category_info = categorize_observation(display, code)
        category_key = category_info["category"]
        
        # Add category info to observation
        obs_with_category = {**obs, **category_info}
        
        if category_key not in grouped:
            grouped[category_key] = []
        grouped[category_key].append(obs_with_category)
    
    # Sort categories by precedence
    sorted_grouped = {}
    for cat in CATEGORY_PRECEDENCE:
        if cat in grouped:
            sorted_grouped[cat] = grouped[cat]
    
    # Add any remaining categories not in precedence list
    for cat in grouped:
        if cat not in sorted_grouped:
            sorted_grouped[cat] = grouped[cat]
    
    return sorted_grouped

def get_category_color(category: str) -> str:
    """Returns Tailwind CSS classes for category background and text color."""
    return OBSERVATION_CATEGORIES.get(category, OBSERVATION_CATEGORIES["other"])["color"]

def get_category_display_name(category: str) -> str:
    """Returns the display name for a category."""
    return OBSERVATION_CATEGORIES.get(category, OBSERVATION_CATEGORIES["other"])["display_name"]

