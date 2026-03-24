# backend/app/api/observation_grouper.py

from typing import List, Dict, Any
import re

class ObservationGrouper:
    """Group observations by clinical categories"""
    
    def __init__(self):
        # Define observation category mappings
        self.category_keywords = {
            "vital_signs": {
                "keywords": [
                    "heart rate", "pulse", "hr", "bpm", 
                    "blood pressure", "systolic", "diastolic", "bp", "mean blood pressure",
                    "temperature", "temp", "body temp",
                    "respiratory rate", "respiration", "rr",
                    "oxygen saturation", "spo2", "o2 sat",
                    "body height", "height",
                    "body weight", "weight",
                    "bmi", "body mass index"
                ],
                "display_name": "Vital Signs"
            },
            "laboratory": {
                "keywords": [
                    "glucose", "blood sugar",
                    "creatinine",
                    "protein", "albumin",
                    "sodium", "na",
                    "potassium", "k",
                    "chloride", "cl",
                    "carbon dioxide", "co2", "bicarbonate", "hco3",
                    "urea nitrogen", "bun",
                    "magnesium", "mg",
                    "calcium", "ca",
                    "anion gap",
                    "lactate"
                ],
                "display_name": "Basic Metabolic Panel"
            },
            "liver_function": {
                "keywords": [
                    "alanine aminotransferase", "alt", "sgpt",
                    "aspartate aminotransferase", "ast", "sgot",
                    "alkaline phosphatase", "alp",
                    "bilirubin",
                    "albumin/globulin", "a/g ratio"
                ],
                "display_name": "Liver Function Tests"
            },
            "lipid_panel": {
                "keywords": [
                    "cholesterol",
                    "triglyceride",
                    "hdl",
                    "ldl"
                ],
                "display_name": "Lipid Panel"
            },
            "blood_count_rbc": {
                "keywords": [
                    "erythrocytes", "red blood cell", "rbc",
                    "hematocrit", "hct",
                    "mcv", "mean corpuscular volume",
                    "mch", "mean corpuscular hemoglobin",
                    "mchc", "mean corpuscular hemoglobin concentration",
                    "erythrocyte distribution width", "rdw"
                ],
                "display_name": "Complete Blood Count - Red Blood Cells"
            },
            "blood_count_wbc": {
                "keywords": [
                    "leukocytes", "white blood cell", "wbc",
                    "neutrophils", "lymphocytes", "monocytes", 
                    "eosinophils", "basophils",
                    "neutrophils/leukocytes", "lymphocytes/leukocytes",
                    "monocytes/leukocytes", "eosinophils/leukocytes", "basophils/leukocytes",
                    "neutrophils/100", "lymphocytes/100", "monocytes/100",
                    "eosinophils/100", "basophils/100"
                ],
                "display_name": "Complete Blood Count - White Blood Cells"
            },
            "blood_count_platelets": {
                "keywords": [
                    "platelets", "platelet",
                    "platelet mean volume"
                ],
                "display_name": "Complete Blood Count - Platelets"
            },
            "hemoglobin_measurements": {
                "keywords": [
                    "hemoglobin", "hgb", "hb",
                    "hemoglobin a1c", "hba1c", "glycated hemoglobin",
                    "hemoglobin a1c/hemoglobin"
                ],
                "display_name": "Hemoglobin & Diabetes Monitoring"
            },
            "kidney_function": {
                "keywords": [
                    "gfr", "glomerular filtration rate",
                    "urea nitrogen/creatinine"
                ],
                "display_name": "Kidney Function"
            },
            "cardiac_markers": {
                "keywords": [
                    "troponin", "troponin i", "troponin i cardiac"
                ],
                "display_name": "Cardiac Markers"
            },
            "hormones": {
                "keywords": [
                    "thyrotropin", "tsh", "thyroid stimulating hormone"
                ],
                "display_name": "Hormones"
            },
            "coagulation": {
                "keywords": [
                    "coagulation", "inr", "international normalized ratio",
                    "tissue factor", "surface induced",
                    "heparin"
                ],
                "display_name": "Coagulation Studies"
            },
            "therapeutic_drugs": {
                "keywords": [
                    "vancomycin", "heparin"
                ],
                "display_name": "Therapeutic Drug Monitoring"
            },
            "enzymes": {
                "keywords": [
                    "triacylglycerol lipase", "lipase"
                ],
                "display_name": "Enzymes & Metabolic Tests"
            },
            "urine": {
                "keywords": [
                    "urine", "ph of urine", "urine ph",
                    "specific gravity", "urine specific gravity",
                    "urobilinogen", "urine test",
                    "urine by test strip"
                ],
                "display_name": "Urine Analysis"
            },
            "behavioral": {
                "keywords": [
                    "cigarette", "smoking", "pack-years",
                    "phq-9", "phq9", "depression",
                    "social activity", "how many times",
                    "moved where you were living",
                    "talk on the telephone"
                ],
                "display_name": "Behavioral Assessments"
            },
            "other": {
                "keywords": [],
                "display_name": "Other Observations"
            }
        }
    
    def categorize_observation(self, observation_display: str) -> str:
        """Categorize a single observation based on its display name"""
        display_lower = observation_display.lower()
        
        for category, info in self.category_keywords.items():
            if category == "other":
                continue
            for keyword in info["keywords"]:
                if keyword in display_lower:
                    return category
        
        return "other"
    
    def group_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group observations by clinical category"""
        grouped = {}
        
        for obs in observations:
            display = obs.get("display", "")
            category = self.categorize_observation(display)
            
            if category not in grouped:
                grouped[category] = []
            
            grouped[category].append(obs)
        
        return grouped
    
    def get_category_display_name(self, category: str) -> str:
        """Get display name for a category"""
        return self.category_keywords.get(category, {}).get("display_name", category.capitalize())
    
    def summarize_group(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary for a group of observations"""
        if not observations:
            return {"count": 0, "latest_date": None, "unique_types": []}
        
        # Get unique observation types
        unique_types = list(set(obs.get("display", "") for obs in observations))
        
        # Find latest date
        dates = [obs.get("effectiveDateTime") or obs.get("date", "") for obs in observations]
        dates = [d for d in dates if d]
        latest_date = max(dates) if dates else None
        
        return {
            "count": len(observations),
            "latest_date": latest_date,
            "unique_types": unique_types,
            "sample": observations[0] if observations else None
        }

# Global instance
observation_grouper = ObservationGrouper()
