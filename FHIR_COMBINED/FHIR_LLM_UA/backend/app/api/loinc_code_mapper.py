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
        "name": "HDL Cholesterol",
        "display": "Cholesterol in HDL [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["hdl", "hdl cholesterol", "high density lipoprotein", "good cholesterol"]
    },
    "2089-1": {
        "name": "HDL Cholesterol",
        "display": "Cholesterol in HDL [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["hdl", "hdl cholesterol", "high density lipoprotein", "good cholesterol"]
    },
    "2089-2": {
        "name": "LDL Cholesterol",
        "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["ldl", "ldl cholesterol", "low density lipoprotein", "bad cholesterol"]
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

    # ── Critical codes commonly present in hospital LOINC data ──────────────

    # HbA1c — glycated hemoglobin (key diabetes marker)
    "4548-4": {
        "name": "HbA1c",
        "display": "Hemoglobin A1c/Hemoglobin.total in Blood",
        "category": "laboratory",
        "keywords": ["hba1c", "hemoglobin a1c", "a1c", "glycated hemoglobin",
                     "glycohemoglobin", "diabetes", "blood sugar control"]
    },
    # Total Cholesterol
    "2093-3": {
        "name": "Cholesterol Total",
        "display": "Cholesterol [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["cholesterol", "total cholesterol", "lipid panel", "lipid"]
    },
    # LDL Cholesterol
    "2089-1": {
        "name": "LDL Cholesterol",
        "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["ldl", "ldl cholesterol", "low density lipoprotein", "bad cholesterol", "lipid"]
    },
    # Estimated Average Glucose (from HbA1c)
    "27353-2": {
        "name": "Estimated Average Glucose",
        "display": "Glucose mean value in Blood estimated from Hemoglobin A1c",
        "category": "laboratory",
        "keywords": ["estimated average glucose", "eag", "average glucose", "hba1c derived", "diabetes"]
    },
    # CRP — C-Reactive Protein
    "1988-5": {
        "name": "C-Reactive Protein",
        "display": "C reactive protein [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["crp", "c reactive protein", "c-reactive protein", "inflammation", "inflammatory marker"]
    },
    # TSH — Thyroid Stimulating Hormone
    "11579-0": {
        "name": "TSH",
        "display": "Thyrotropin [Units/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["tsh", "thyroid stimulating hormone", "thyrotropin", "thyroid function"]
    },
    # Free T4 — Thyroxine
    "3024-7": {
        "name": "Free T4",
        "display": "Thyroxine (T4) free [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["free t4", "t4 free", "thyroxine", "ft4", "thyroid function"]
    },
    # Calcium
    "17861-6": {
        "name": "Calcium",
        "display": "Calcium [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["calcium", "ca", "electrolyte", "serum calcium"]
    },
    # Magnesium
    "19123-9": {
        "name": "Magnesium",
        "display": "Magnesium [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["magnesium", "mg", "electrolyte"]
    },
    # Phosphate
    "2777-1": {
        "name": "Phosphate",
        "display": "Phosphate [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["phosphate", "phosphorus", "phos", "electrolyte"]
    },
    # Sodium (serum) — 2951-2 is the correct LOINC for serum sodium
    "2951-2": {
        "name": "Sodium",
        "display": "Sodium [Moles/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["sodium", "na", "electrolyte", "serum sodium"]
    },
    # Alkaline Phosphatase
    "6768-6": {
        "name": "Alkaline Phosphatase",
        "display": "Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["alk phos", "alp", "alkaline phosphatase", "liver function"]
    },
    # BNP / proBNP — heart failure marker
    "33762-6": {
        "name": "NT-proBNP",
        "display": "Natriuretic peptide B prohormone [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["bnp", "proBNP", "nt-probnp", "natriuretic peptide",
                     "heart failure", "cardiac marker"]
    },
    # Troponin I
    "10839-9": {
        "name": "Troponin I",
        "display": "Troponin I.cardiac [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["troponin", "troponin i", "cardiac troponin", "myocardial infarction", "acs", "heart attack"]
    },
    # Creatine Kinase
    "2157-6": {
        "name": "Creatine Kinase",
        "display": "Creatine kinase [Enzymatic activity/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["creatine kinase", "ck", "cpk", "cardiac enzyme", "muscle enzyme"]
    },
    # Lactate
    "2524-7": {
        "name": "Lactate",
        "display": "Lactate [Moles/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["lactate", "lactic acid", "sepsis marker"]
    },
    # Vitamin B12 / Cobalamins
    "2132-9": {
        "name": "Vitamin B12",
        "display": "Cobalamins [Mass/volume] in Serum",
        "category": "laboratory",
        "keywords": ["vitamin b12", "cobalamin", "b12", "cyanocobalamin"]
    },
    # Folate
    "2284-8": {
        "name": "Folate",
        "display": "Folate [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["folate", "folic acid", "vitamin b9", "b9"]
    },
    # Urine Protein/Creatinine ratio
    "2890-2": {
        "name": "Urine Protein/Creatinine Ratio",
        "display": "Protein/Creatinine [Mass ratio] in Urine",
        "category": "laboratory",
        "keywords": ["protein creatinine ratio", "pcr", "urine protein", "proteinuria", "kidney function"]
    },
    # Vitamin D
    "62290-2": {
        "name": "25-OH Vitamin D",
        "display": "25-hydroxyvitamin D3 [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["vitamin d", "25-oh vitamin d", "25-hydroxyvitamin d", "vit d"]
    },
    # Ammonia
    "1839-0": {
        "name": "Ammonia",
        "display": "Ammonia [Moles/volume] in Blood",
        "category": "laboratory",
        "keywords": ["ammonia", "liver failure", "hepatic encephalopathy"]
    },
    # Oxygen Saturation (calculated)
    "59408-5": {
        "name": "Oxygen Saturation",
        "display": "Oxygen saturation in Arterial blood by Pulse oximetry",
        "category": "vital_signs",
        "keywords": ["oxygen saturation", "spo2", "o2 sat", "saturation", "pulse ox"]
    },
    # BMI
    "39156-5": {
        "name": "BMI",
        "display": "Body mass index (BMI) [Ratio]",
        "category": "vital_signs",
        "keywords": ["bmi", "body mass index", "obesity", "weight"]
    },
    # Body Weight
    "29463-7": {
        "name": "Body Weight",
        "display": "Body weight",
        "category": "vital_signs",
        "keywords": ["weight", "body weight", "kg", "pounds"]
    },
    # Body Height
    "8302-2": {
        "name": "Body Height",
        "display": "Body height",
        "category": "vital_signs",
        "keywords": ["height", "body height", "stature"]
    },
    # Pain Severity
    "72514-3": {
        "name": "Pain Score",
        "display": "Pain severity - 0-10 verbal numeric rating [Score]",
        "category": "vital_signs",
        "keywords": ["pain", "pain score", "pain severity", "numeric pain rating"]
    },

    # ── CBC Differential (previously missing — caused NULL display + wrong aggregation) ──
    "26515-7": {
        "name": "Platelet Count (automated)",
        "display": "Platelets [#/volume] in Blood by Automated count",
        "category": "laboratory",
        "keywords": ["platelet", "plt", "thrombocyte", "blood count"]
    },
    "4544-3": {
        "name": "Hematocrit (automated)",
        "display": "Hematocrit [Volume Fraction] of Blood by Automated count",
        "category": "laboratory",
        "keywords": ["hematocrit", "hct", "blood count"]
    },
    "787-2": {
        "name": "MCV",
        "display": "MCV [Entitic volume] by Automated count",
        "category": "laboratory",
        "keywords": ["mcv", "mean corpuscular volume", "blood count"]
    },
    "785-6": {
        "name": "MCH",
        "display": "MCH [Entitic mass] by Automated count",
        "category": "laboratory",
        "keywords": ["mch", "mean corpuscular hemoglobin", "blood count"]
    },
    "788-0": {
        "name": "MCHC",
        "display": "MCHC [Mass/volume] by Automated count",
        "category": "laboratory",
        "keywords": ["mchc", "mean corpuscular hemoglobin concentration", "blood count"]
    },
    "770-8": {
        "name": "MCHC (automated)",
        "display": "MCHC [Mass/volume] by Automated count",
        "category": "laboratory",
        "keywords": ["mchc", "mean corpuscular hemoglobin concentration", "blood count"]
    },
    "32623-1": {
        "name": "Platelet Mean Volume",
        "display": "Platelet mean volume [Entitic volume] by Automated count",
        "category": "laboratory",
        "keywords": ["platelet volume", "mpv", "mean platelet volume"]
    },
    "751-8": {
        "name": "Neutrophils %",
        "display": "Neutrophils/100 leukocytes in Blood",
        "category": "laboratory",
        "keywords": ["neutrophil", "neutrophils", "differential", "blood count"]
    },
    "731-0": {
        "name": "Lymphocytes %",
        "display": "Lymphocytes/100 leukocytes in Blood",
        "category": "laboratory",
        "keywords": ["lymphocyte", "lymphocytes", "differential", "blood count"]
    },
    "736-9": {
        "name": "Lymphocytes Count",
        "display": "Lymphocytes [#/volume] in Blood by Automated count",
        "category": "laboratory",
        "keywords": ["lymphocyte", "lymphocytes", "differential", "blood count"]
    },
    "742-7": {
        "name": "Monocytes %",
        "display": "Monocytes/100 leukocytes in Blood",
        "category": "laboratory",
        "keywords": ["monocyte", "monocytes", "differential", "blood count"]
    },
    "713-8": {
        "name": "Eosinophils %",
        "display": "Eosinophils/100 leukocytes in Blood",
        "category": "laboratory",
        "keywords": ["eosinophil", "eosinophils", "differential", "blood count"]
    },
    "711-2": {
        "name": "Eosinophils Count",
        "display": "Eosinophils [#/volume] in Blood by Automated count",
        "category": "laboratory",
        "keywords": ["eosinophil", "eosinophils", "differential", "blood count"]
    },
    "704-7": {
        "name": "Basophils %",
        "display": "Basophils/100 leukocytes in Blood",
        "category": "laboratory",
        "keywords": ["basophil", "basophils", "differential", "blood count"]
    },
    "706-2": {
        "name": "Basophils Count",
        "display": "Basophils [#/volume] in Blood by Automated count",
        "category": "laboratory",
        "keywords": ["basophil", "basophils", "differential", "blood count"]
    },

    # ── Metabolic / Chemistry (previously missing) ───────────────────────────
    "33037-3": {
        "name": "Anion Gap",
        "display": "Anion gap 3 in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["anion gap", "electrolyte", "acid base", "metabolic acidosis"]
    },
    "2885-2": {
        "name": "Total Protein",
        "display": "Protein [Mass/volume] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["total protein", "protein", "albumin", "nutrition"]
    },
    "3097-3": {
        "name": "BUN/Creatinine Ratio",
        "display": "Urea nitrogen/Creatinine [Mass Ratio] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["bun creatinine ratio", "urea creatinine ratio", "kidney function", "renal"]
    },
    "1759-0": {
        "name": "AST/ALT Ratio",
        "display": "Aspartate aminotransferase/Alanine aminotransferase [Enzymatic activity ratio] in Serum or Plasma",
        "category": "laboratory",
        "keywords": ["ast alt ratio", "liver function", "hepatic"]
    },

    # ── Urinalysis (previously missing) ─────────────────────────────────────
    "5811-5": {
        "name": "Urine Specific Gravity",
        "display": "Specific gravity of Urine by Test strip",
        "category": "laboratory",
        "keywords": ["urine specific gravity", "urinalysis", "urine", "renal"]
    },
    "5803-2": {
        "name": "Urine pH",
        "display": "pH of Urine by Test strip",
        "category": "laboratory",
        "keywords": ["urine ph", "urinalysis", "urine", "acid base"]
    },
    "20405-7": {
        "name": "Urine Nitrite",
        "display": "Nitrite [Presence] in Urine by Test strip",
        "category": "laboratory",
        "keywords": ["urine nitrite", "urinalysis", "uti", "infection"]
    },

    # ── Body Composition ─────────────────────────────────────────────────────
    "5905-5": {
        "name": "Body Fat Percentage",
        "display": "Body fat [Mass fraction]",
        "category": "vital_signs",
        "keywords": ["body fat", "fat percentage", "adiposity", "obesity", "bmi"]
    },

    # ── Mental Health / Functional Assessments ───────────────────────────────
    "44261-6": {
        "name": "PHQ-9 Score",
        "display": "PHQ-9 total score [Reported.PHQ]",
        "category": "mental_health",
        "keywords": ["phq-9", "phq9", "depression", "patient health questionnaire", "mental health"]
    },
    "76508-1": {
        "name": "Social Activity Frequency",
        "display": "In a typical week, how many times do you talk on the phone or video chat with family or friends",
        "category": "mental_health",
        "keywords": ["social activity", "social isolation", "mental health", "functional assessment"]
    },
    "98977-2": {
        "name": "Healthcare Visit Frequency",
        "display": "In the past 12 months, how many times have you seen a doctor",
        "category": "mental_health",
        "keywords": ["healthcare visits", "doctor visits", "functional assessment"]
    },

    # ── Other / Ranking ──────────────────────────────────────────────────────
    "263486008": {
        "name": "Rank",
        "display": "Rank",
        "category": "other",
        "keywords": ["rank", "order", "priority"]
    },
}

# ── LOINC display-name → human alias mapping ─────────────────────────────────
# Handles the case where hospital data stores raw LOINC names (e.g.,
# "HEMOGLOBIN A1C/HEMOGLOBIN.TOTAL:MFR:PT:BLD:QN::") as display values.
# These substrings are matched against the display field to inject aliases.
LOINC_DISPLAY_ALIASES: Dict[str, List[str]] = {
    "HEMOGLOBIN A1C":        ["hba1c", "hemoglobin a1c", "a1c", "glycated hemoglobin", "diabetes marker"],
    "GLYCATED HEMOGLOBIN":   ["hba1c", "hemoglobin a1c", "a1c", "glycated hemoglobin"],
    "UREA NITROGEN":         ["bun", "blood urea nitrogen", "urea nitrogen", "kidney function"],
    "CREATININE":            ["creatinine", "kidney function", "renal function"],
    "GLUCOSE":               ["glucose", "blood sugar", "blood glucose", "diabetes"],
    "CHOLESTEROL.IN HDL":    ["hdl", "hdl cholesterol", "high density lipoprotein"],
    "CHOLESTEROL.IN LDL":    ["ldl", "ldl cholesterol", "low density lipoprotein"],
    "CHOLESTEROL":           ["cholesterol", "total cholesterol", "lipid"],
    "TRIGLYCERIDE":          ["triglycerides", "triglyceride", "lipid"],
    "C REACTIVE PROTEIN":    ["crp", "c-reactive protein", "inflammation"],
    "THYROTROPIN":           ["tsh", "thyroid stimulating hormone", "thyroid"],
    "THYROXINE.FREE":        ["free t4", "ft4", "thyroxine", "thyroid"],
    "TROPONIN":              ["troponin", "cardiac enzyme", "heart attack", "myocardial"],
    "NATRIURETIC PEPTIDE.B": ["bnp", "nt-probnp", "heart failure", "cardiac"],
    "LACTATE DEHYDROGENASE": ["ldh", "lactate dehydrogenase", "liver"],
    "ALANINE AMINOTRANSFER": ["alt", "sgpt", "liver function"],
    "ASPARTATE AMINOTRANSFER": ["ast", "sgot", "liver function"],
    "ALKALINE PHOSPHATASE":  ["alp", "alk phos", "liver function"],
    "BILIRUBIN":             ["bilirubin", "liver function", "jaundice"],
    "ALBUMIN":               ["albumin", "protein", "liver function", "nutrition"],
    "SODIUM":                ["sodium", "na", "electrolyte"],
    "POTASSIUM":             ["potassium", "k", "electrolyte"],
    "CHLORIDE":              ["chloride", "cl", "electrolyte"],
    "CALCIUM":               ["calcium", "ca", "electrolyte"],
    "MAGNESIUM":             ["magnesium", "mg", "electrolyte"],
    "PHOSPHATE":             ["phosphate", "phosphorus", "electrolyte"],
    "BICARBONATE":           ["bicarbonate", "hco3", "electrolyte", "acid base"],
    "COAGULATION":           ["coagulation", "clotting", "pt", "inr"],
    "HEMOGLOBIN":            ["hemoglobin", "hgb", "hb", "blood count"],
    "HEMATOCRIT":            ["hematocrit", "hct", "blood count"],
    "LEUKOCYTES":            ["white blood cell", "wbc", "leukocyte", "blood count"],
    "ERYTHROCYTES":          ["red blood cell", "rbc", "erythrocyte", "blood count"],
    "PLATELET":              ["platelet", "plt", "thrombocyte", "blood count"],
    "OXYGEN":               ["oxygen", "o2", "saturation", "respiratory"],
    "CREATINE KINASE":       ["ck", "cpk", "creatine kinase", "muscle enzyme"],
    "LACTATE":               ["lactate", "lactic acid", "sepsis"],
    "CORTISOL":              ["cortisol", "stress hormone", "adrenal"],
    "COBALAMINS":            ["vitamin b12", "b12", "cobalamin"],
    "FOLATE":                ["folate", "folic acid", "vitamin b9"],
    "PROTEIN/CREATININE":    ["protein creatinine ratio", "pcr", "proteinuria"],
    "AMMONIA":               ["ammonia", "hepatic"],
    "BLOOD PRESSURE":        ["blood pressure", "bp", "hypertension"],
    "HEART RATE":            ["heart rate", "pulse", "hr"],
    "BODY MASS INDEX":       ["bmi", "obesity", "weight"],
    "BODY WEIGHT":           ["weight", "bmi"],
    "BODY HEIGHT":           ["height", "stature"],
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

def _get_display_aliases(display: str) -> List[str]:
    """
    Match a raw LOINC display name (e.g., 'HEMOGLOBIN A1C/HEMOGLOBIN.TOTAL:...')
    against LOINC_DISPLAY_ALIASES and return any matching human-readable aliases.
    This is crucial for BM25 searchability of hospital LOINC-coded display names.
    """
    if not display:
        return []
    display_upper = display.upper()
    found: List[str] = []
    for pattern, aliases in LOINC_DISPLAY_ALIASES.items():
        if pattern in display_upper:
            for a in aliases:
                if a not in found:
                    found.append(a)
    return found


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
        # Also get aliases by matching the raw display name against known LOINC patterns
        # This handles hospital data where display = "HEMOGLOBIN A1C/HEMOGLOBIN.TOTAL:MFR:PT:BLD:QN::"
        display_aliases = _get_display_aliases(display)
        all_keywords = list(dict.fromkeys(keywords + display_aliases))  # deduplicated
        keyword_text = f" {' '.join(all_keywords)}" if all_keywords else ""
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

