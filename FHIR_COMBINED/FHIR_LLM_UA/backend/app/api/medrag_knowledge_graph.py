# backend/app/api/medrag_knowledge_graph.py
"""
=============================================================================
MedRAG Knowledge Graph (KG) Layer
=============================================================================
Based on: "MedRAG: Enhancing Retrieval-augmented Generation with Knowledge
Graph-Elicited Reasoning for Healthcare Copilot"
Zhao et al., WWW 2025 — https://dl.acm.org/doi/10.1145/3696410.3714782

PURPOSE:
    This module implements the 4-tier hierarchical diagnostic Knowledge Graph
    described in the MedRAG paper. It enables:
      1. Differential diagnosis (listing candidate diseases and their differences)
      2. KG-elicited reasoning (structured clinical evidence per candidate)
      3. Proactive follow-up question generation (identify missing information)

HOW IT PLUGS INTO rag_service.py:
    After Elasticsearch retrieval (Step 2), BEFORE LLM generation (Step 4):
      retrieved_data  ──→  [KG Query]  ──→  kg_context  ──→  LLM prompt

KNOWLEDGE GRAPH STRUCTURE (4-tier, per the paper):
    Tier 1: Broad Category       (e.g., "Metabolic Disease")
    Tier 2: Disease Family       (e.g., "Hyperglycemic Conditions")
    Tier 3: Specific Disease     (e.g., "Type 2 Diabetes")
    Tier 4: Distinguishing Feats (e.g., "HbA1c > 6.5%, BMI > 25, gradual onset")

COMPARE MODE (for paper):
    - STANDALONE RAG:  Elasticsearch retrieval → LLM (no KG)
    - MEDRAG:          Elasticsearch retrieval → KG query → LLM (with KG context)
    Toggle is in rag_service.py via USE_MEDRAG flag.
=============================================================================
"""

from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# TIER 1 → TIER 2 → TIER 3 → TIER 4: The Diagnostic Knowledge Graph
# Built from standard medical ontologies (SNOMED-CT, ICD-10, clinical guidelines)
# and mapped to the conditions/observations already present in your MySQL database.
# =============================================================================

DIAGNOSTIC_KG: Dict[str, Any] = {

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Metabolic Disease
    # ─────────────────────────────────────────────────────────────────────────
    "Metabolic Disease": {
        "Hyperglycemic Conditions": {
            "Type 2 Diabetes Mellitus": {
                "symptoms":   ["fatigue", "polyuria", "polydipsia", "blurred vision", "weight gain", "slow wound healing"],
                "observations": ["glucose", "hba1c", "a1c", "fasting glucose", "blood sugar"],
                "distinguishing": [
                    "HbA1c >= 6.5% (ADA diagnostic criterion)",
                    "Fasting glucose >= 126 mg/dL",
                    "Gradual onset over months/years",
                    "BMI > 25 (overweight/obese) common",
                    "Family history of T2DM",
                    "Responds to metformin and lifestyle changes",
                    "No ketoacidosis at onset (vs T1DM)"
                ],
                "against": [
                    "No autoimmune markers (vs T1DM)",
                    "Not steroid-induced (no corticosteroid use)"
                ],
                "snomed_codes": ["44054006", "73211009"],
                "loinc_codes":  ["4548-4", "2339-0", "2345-7"]
            },
            "Type 1 Diabetes Mellitus": {
                "symptoms":   ["rapid onset", "polyuria", "polydipsia", "weight loss", "ketoacidosis"],
                "observations": ["glucose", "hba1c", "ketones", "c-peptide"],
                "distinguishing": [
                    "Autoimmune: positive anti-GAD, anti-islet cell antibodies",
                    "Low or absent C-peptide",
                    "Ketoacidosis at onset",
                    "Young age onset (< 30 years)",
                    "Requires insulin from diagnosis",
                    "Rapid onset (days to weeks)"
                ],
                "against": [
                    "Not typically overweight",
                    "No family history of T2DM"
                ],
                "snomed_codes": ["46635009"],
                "loinc_codes":  ["4548-4", "2339-0"]
            },
            "Steroid-Induced Hyperglycemia": {
                "symptoms":   ["elevated glucose after steroid use", "no prior diabetes history"],
                "observations": ["glucose", "cortisol"],
                "distinguishing": [
                    "Active corticosteroid medication (prednisone, dexamethasone, etc.)",
                    "Glucose elevation correlates with steroid dosing schedule",
                    "Peaks in afternoon/evening (vs T2DM: morning fasting high)",
                    "Reversible when steroids tapered",
                    "HbA1c may be normal or mildly elevated"
                ],
                "against": [
                    "No prior diabetes history",
                    "No family history"
                ],
                "snomed_codes": ["hyperglycemia-steroid"],
                "loinc_codes":  ["2339-0"]
            },
            "Cushing's Syndrome": {
                "symptoms":   ["weight gain", "moon face", "hypertension", "fatigue", "glucose elevation"],
                "observations": ["cortisol", "glucose", "blood pressure"],
                "distinguishing": [
                    "Elevated cortisol (24h urine or serum)",
                    "Moon face, buffalo hump, central obesity",
                    "Purple striae on abdomen",
                    "Hypertension co-present",
                    "Proximal muscle weakness",
                    "Exogenous steroid use OR pituitary/adrenal tumor"
                ],
                "against": [
                    "No steroid use + normal cortisol rules out"
                ],
                "snomed_codes": ["47270006"],
                "loinc_codes":  ["2339-0"]
            }
        },
        "Dyslipidemia": {
            "Hypercholesterolemia": {
                "symptoms":   ["usually asymptomatic", "xanthomas", "family history"],
                "observations": ["cholesterol", "ldl", "hdl", "triglycerides"],
                "distinguishing": [
                    "Total cholesterol > 200 mg/dL",
                    "LDL > 130 mg/dL",
                    "Familial form: very high LDL (> 190), tendon xanthomas",
                    "Risk factor for cardiovascular disease"
                ],
                "against": [],
                "snomed_codes": ["13644009"],
                "loinc_codes":  ["2093-3", "2089-1", "2085-9"]
            }
        }
    },

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Cardiovascular Disease
    # ─────────────────────────────────────────────────────────────────────────
    "Cardiovascular Disease": {
        "Hypertensive Conditions": {
            "Essential Hypertension": {
                "symptoms":   ["headache", "dizziness", "elevated blood pressure", "often asymptomatic"],
                "observations": ["systolic blood pressure", "diastolic blood pressure", "blood pressure"],
                "distinguishing": [
                    "Sustained SBP >= 130 mmHg or DBP >= 80 mmHg (ACC/AHA 2017)",
                    "No identifiable secondary cause",
                    "Often asymptomatic (silent hypertension)",
                    "Family history of hypertension",
                    "Associated with obesity, high salt intake, stress",
                    "Responds to lifestyle changes and antihypertensives"
                ],
                "against": [
                    "No renal artery stenosis (vs secondary HTN)",
                    "No pheochromocytoma"
                ],
                "snomed_codes": ["38341003", "59621000"],
                "loinc_codes":  ["8480-6", "8462-4"]
            },
            "Secondary Hypertension": {
                "symptoms":   ["resistant to treatment", "young age onset", "sudden onset"],
                "observations": ["blood pressure", "creatinine", "potassium", "cortisol"],
                "distinguishing": [
                    "Identifiable cause: renal artery stenosis, hyperaldosteronism, pheochromocytoma",
                    "Resistant to 3+ antihypertensives",
                    "Young age < 30 without family history",
                    "Hypokalemia (hyperaldosteronism)",
                    "Episodic palpitations and sweating (pheochromocytoma)"
                ],
                "against": [],
                "snomed_codes": ["secondary-htn"],
                "loinc_codes":  ["8480-6", "8462-4", "2160-0"]
            }
        },
        "Heart Failure Conditions": {
            "Congestive Heart Failure": {
                "symptoms":   ["dyspnea", "orthopnea", "edema", "fatigue", "reduced exercise tolerance"],
                "observations": ["bnp", "nt-probnp", "heart rate", "blood pressure", "oxygen saturation"],
                "distinguishing": [
                    "BNP > 100 pg/mL or NT-proBNP > 300 pg/mL",
                    "Reduced ejection fraction < 40% (HFrEF) or preserved EF (HFpEF)",
                    "Bilateral leg edema",
                    "Crackles on lung auscultation",
                    "Chest X-ray: cardiomegaly, pulmonary edema",
                    "History of MI, hypertension, or valvular disease"
                ],
                "against": [],
                "snomed_codes": ["84114007", "42343007"],
                "loinc_codes":  ["8867-4", "8480-6", "59408-5"]
            },
            "Coronary Artery Disease": {
                "symptoms":   ["chest pain", "angina", "dyspnea on exertion", "radiating arm pain"],
                "observations": ["troponin", "heart rate", "blood pressure"],
                "distinguishing": [
                    "Chest pain: exertional, relieved by rest/nitroglycerin",
                    "Elevated troponin (in acute MI)",
                    "ECG changes: ST elevation or depression",
                    "Risk factors: diabetes, hypertension, hyperlipidemia, smoking",
                    "Positive stress test"
                ],
                "against": [],
                "snomed_codes": ["53741008"],
                "loinc_codes":  ["troponin-loinc"]
            }
        },
        "Arrhythmia": {
            "Atrial Fibrillation": {
                "symptoms":   ["palpitations", "irregular pulse", "dyspnea", "dizziness"],
                "observations": ["heart rate", "blood pressure"],
                "distinguishing": [
                    "Irregularly irregular pulse",
                    "Heart rate typically 100-160 bpm during AF",
                    "ECG: absent P waves, irregular RR intervals",
                    "Risk factors: age > 65, hypertension, heart failure, valvular disease"
                ],
                "against": [],
                "snomed_codes": ["49436004"],
                "loinc_codes":  ["8867-4"]
            }
        }
    },

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Renal Disease
    # ─────────────────────────────────────────────────────────────────────────
    "Renal Disease": {
        "Chronic Kidney Conditions": {
            "Chronic Kidney Disease (CKD)": {
                "symptoms":   ["fatigue", "edema", "decreased urine output", "nausea", "hypertension"],
                "observations": ["creatinine", "gfr", "bun", "potassium", "phosphorus", "hemoglobin"],
                "distinguishing": [
                    "eGFR < 60 mL/min/1.73m² for >= 3 months (KDIGO criteria)",
                    "Elevated creatinine: > 1.3 mg/dL (male), > 1.1 mg/dL (female)",
                    "Proteinuria (urine albumin-creatinine ratio > 30 mg/g)",
                    "Hyperkalemia (K+ > 5.0 mEq/L)",
                    "Anemia (normocytic) — reduced EPO production",
                    "Metabolic acidosis",
                    "Staging: CKD 1-5 based on eGFR and proteinuria"
                ],
                "against": [],
                "snomed_codes": ["709044004", "431857002"],
                "loinc_codes":  ["2160-0", "33914-3", "3094-0"]
            },
            "Acute Kidney Injury (AKI)": {
                "symptoms":   ["sudden rise in creatinine", "oliguria", "fluid overload"],
                "observations": ["creatinine", "bun", "urine output", "potassium"],
                "distinguishing": [
                    "Acute rise in creatinine >= 0.3 mg/dL within 48 hours",
                    "Or >= 1.5x baseline within 7 days",
                    "Often reversible with treatment of underlying cause",
                    "Causes: dehydration (pre-renal), obstruction (post-renal), nephrotoxins (intrinsic)"
                ],
                "against": [
                    "Duration < 3 months (vs CKD)"
                ],
                "snomed_codes": ["14669001"],
                "loinc_codes":  ["2160-0", "3094-0"]
            }
        }
    },

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Respiratory Disease
    # ─────────────────────────────────────────────────────────────────────────
    "Respiratory Disease": {
        "Obstructive Conditions": {
            "Chronic Obstructive Pulmonary Disease (COPD)": {
                "symptoms":   ["chronic cough", "dyspnea", "sputum production", "wheezing"],
                "observations": ["oxygen saturation", "respiratory rate", "fev1"],
                "distinguishing": [
                    "FEV1/FVC < 0.70 post-bronchodilator (GOLD criteria)",
                    "History of smoking (> 10 pack-years) or occupational exposure",
                    "Chronic symptoms > 3 months/year, > 2 consecutive years",
                    "Progressive, not fully reversible airflow obstruction",
                    "SpO2 < 95% at rest in severe cases",
                    "Barrel chest on exam"
                ],
                "against": [
                    "No eosinophilia (vs asthma typically)",
                    "Onset > 40 years age"
                ],
                "snomed_codes": ["13645005", "233604007"],
                "loinc_codes":  ["59408-5", "9279-1"]
            },
            "Asthma": {
                "symptoms":   ["episodic wheezing", "chest tightness", "cough", "dyspnea"],
                "observations": ["oxygen saturation", "respiratory rate"],
                "distinguishing": [
                    "Reversible airflow obstruction (improves with bronchodilators)",
                    "Episodic symptoms, often triggered (allergens, exercise, cold air)",
                    "Eosinophilia or elevated IgE",
                    "Younger age onset (childhood)",
                    "Normal spirometry between episodes"
                ],
                "against": [
                    "No smoking history (vs COPD)",
                    "Not progressive"
                ],
                "snomed_codes": ["195967001"],
                "loinc_codes":  ["59408-5"]
            }
        }
    },

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Neurological Disease
    # ─────────────────────────────────────────────────────────────────────────
    "Neurological Disease": {
        "Cognitive Disorders": {
            "Alzheimer's Disease": {
                "symptoms":   ["memory loss", "confusion", "disorientation", "personality changes"],
                "observations": ["cognitive assessment"],
                "distinguishing": [
                    "Gradual onset over years",
                    "Episodic memory impairment first (recent > remote)",
                    "Biomarkers: amyloid PET, CSF amyloid/tau",
                    "Age > 65 (typical onset)",
                    "No acute onset or fluctuation (vs delirium, Lewy body)"
                ],
                "against": [],
                "snomed_codes": ["26929004"],
                "loinc_codes":  []
            },
            "Vascular Dementia": {
                "symptoms":   ["stepwise decline", "focal neurological signs", "history of stroke"],
                "observations": ["blood pressure"],
                "distinguishing": [
                    "Stepwise cognitive decline (vs gradual in Alzheimer's)",
                    "History of stroke or TIA",
                    "Focal neurological signs",
                    "MRI: white matter hyperintensities, lacunar infarcts",
                    "Vascular risk factors: HTN, diabetes, AF"
                ],
                "against": [],
                "snomed_codes": ["429998004"],
                "loinc_codes":  []
            }
        }
    },

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Mental Health
    # ─────────────────────────────────────────────────────────────────────────
    "Mental Health": {
        "Mood Disorders": {
            "Major Depressive Disorder": {
                "symptoms":   ["depressed mood", "anhedonia", "fatigue", "sleep disturbance", "cognitive impairment"],
                "observations": ["thyroid", "vitamin d", "hemoglobin"],
                "distinguishing": [
                    "DSM-5: >= 5 symptoms for >= 2 weeks",
                    "Depressed mood OR anhedonia MUST be present",
                    "Not due to substance or medical condition",
                    "Rule out hypothyroidism, anemia, vitamin D deficiency as medical causes"
                ],
                "against": [],
                "snomed_codes": ["35489007", "370143000"],
                "loinc_codes":  []
            },
            "Bipolar Disorder": {
                "symptoms":   ["depressive episodes", "manic episodes", "elevated mood", "decreased sleep need"],
                "observations": [],
                "distinguishing": [
                    "History of manic/hypomanic episodes (vs MDD: only depressive)",
                    "Manic episode: elevated/irritable mood >= 1 week",
                    "Decreased need for sleep during mania",
                    "Grandiosity, racing thoughts, impulsive behavior"
                ],
                "against": [],
                "snomed_codes": ["13746004"],
                "loinc_codes":  []
            }
        },
        "Anxiety Disorders": {
            "Generalized Anxiety Disorder": {
                "symptoms":   ["excessive worry", "restlessness", "fatigue", "poor concentration", "muscle tension"],
                "observations": ["heart rate", "blood pressure"],
                "distinguishing": [
                    "DSM-5: excessive anxiety >= 6 months",
                    "Difficult to control the worry",
                    "Not limited to one topic (vs phobia)",
                    "May cause tachycardia, hypertension during episodes"
                ],
                "against": [],
                "snomed_codes": ["197480006"],
                "loinc_codes":  []
            }
        }
    },

    # ─────────────────────────────────────────────────────────────────────────
    # TIER 1: Hematological Disease
    # ─────────────────────────────────────────────────────────────────────────
    "Hematological Disease": {
        "Anemia": {
            "Iron Deficiency Anemia": {
                "symptoms":   ["fatigue", "pallor", "dyspnea", "pica", "brittle nails"],
                "observations": ["hemoglobin", "hematocrit", "ferritin", "iron", "mcv"],
                "distinguishing": [
                    "Hemoglobin < 12 g/dL (women), < 13 g/dL (men)",
                    "Low MCV (microcytic anemia < 80 fL)",
                    "Low ferritin < 12 ng/mL (most specific for iron deficiency)",
                    "Low serum iron, high TIBC",
                    "Common causes: chronic blood loss (GI, menorrhagia), poor diet"
                ],
                "against": [
                    "Normal ferritin rules out iron deficiency"
                ],
                "snomed_codes": ["87522002"],
                "loinc_codes":  ["718-7", "786-4", "2276-4"]
            },
            "Anemia of Chronic Disease": {
                "symptoms":   ["fatigue", "pallor", "associated with chronic illness"],
                "observations": ["hemoglobin", "ferritin", "crp", "esr"],
                "distinguishing": [
                    "Hemoglobin mildly reduced (9-12 g/dL)",
                    "Normal or elevated ferritin (vs iron deficiency)",
                    "Elevated inflammatory markers: CRP, ESR",
                    "Associated with CKD, rheumatoid arthritis, cancer, chronic infection",
                    "MCV normal or slightly low (normocytic or mildly microcytic)"
                ],
                "against": [
                    "Normal ferritin (not low like iron deficiency)"
                ],
                "snomed_codes": ["271737000"],
                "loinc_codes":  ["718-7", "786-4"]
            },
            "B12/Folate Deficiency Anemia": {
                "symptoms":   ["fatigue", "glossitis", "neurological symptoms", "macrocytic anemia"],
                "observations": ["hemoglobin", "mcv", "b12", "folate"],
                "distinguishing": [
                    "High MCV (macrocytic anemia > 100 fL)",
                    "Low serum B12 (< 200 pg/mL) or folate",
                    "Hypersegmented neutrophils on blood smear",
                    "Neurological: subacute combined degeneration (B12 only)",
                    "Causes: veganism, pernicious anemia, malabsorption"
                ],
                "against": [],
                "snomed_codes": ["271737000"],
                "loinc_codes":  ["718-7", "786-4"]
            }
        }
    }
}


# =============================================================================
# Symptom → Disease Mapping (for fast lookup when symptoms appear in query)
# =============================================================================

SYMPTOM_TO_DISEASES: Dict[str, List[str]] = {
    "fatigue":           ["Type 2 Diabetes Mellitus", "Chronic Kidney Disease (CKD)", "Iron Deficiency Anemia", "Major Depressive Disorder", "Hypothyroidism"],
    "polyuria":          ["Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus", "Chronic Kidney Disease (CKD)"],
    "polydipsia":        ["Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus"],
    "elevated glucose":  ["Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus", "Steroid-Induced Hyperglycemia", "Cushing's Syndrome"],
    "high blood pressure": ["Essential Hypertension", "Secondary Hypertension", "Cushing's Syndrome"],
    "hypertension":      ["Essential Hypertension", "Secondary Hypertension", "Cushing's Syndrome", "Chronic Kidney Disease (CKD)"],
    "edema":             ["Congestive Heart Failure", "Chronic Kidney Disease (CKD)"],
    "dyspnea":           ["Congestive Heart Failure", "COPD", "Asthma", "Anemia"],
    "chest pain":        ["Coronary Artery Disease", "Congestive Heart Failure"],
    "palpitations":      ["Atrial Fibrillation", "Generalized Anxiety Disorder"],
    "elevated creatinine": ["Chronic Kidney Disease (CKD)", "Acute Kidney Injury (AKI)"],
    "low hemoglobin":    ["Iron Deficiency Anemia", "Anemia of Chronic Disease", "B12/Folate Deficiency Anemia", "Chronic Kidney Disease (CKD)"],
    "memory loss":       ["Alzheimer's Disease", "Vascular Dementia"],
    "wheezing":          ["Asthma", "Chronic Obstructive Pulmonary Disease (COPD)"],
    "weight gain":       ["Type 2 Diabetes Mellitus", "Cushing's Syndrome", "Hypothyroidism"],
    "weight loss":       ["Type 1 Diabetes Mellitus", "Cancer"],
    "depressed mood":    ["Major Depressive Disorder", "Bipolar Disorder"],
    "anxiety":           ["Generalized Anxiety Disorder", "Bipolar Disorder"],
}


# =============================================================================
# Observation (LOINC code / display name) → Disease Mapping
# =============================================================================

OBSERVATION_TO_DISEASES: Dict[str, List[str]] = {
    # Metabolic
    "glucose":           ["Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus", "Steroid-Induced Hyperglycemia", "Cushing's Syndrome"],
    "hba1c":             ["Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus"],
    "a1c":               ["Type 2 Diabetes Mellitus", "Type 1 Diabetes Mellitus"],
    "cholesterol":       ["Hypercholesterolemia"],
    "ldl":               ["Hypercholesterolemia"],
    "hdl":               ["Hypercholesterolemia"],
    "triglycerides":     ["Hypercholesterolemia"],
    # Cardiovascular
    "systolic blood pressure":  ["Essential Hypertension", "Secondary Hypertension", "Congestive Heart Failure"],
    "diastolic blood pressure": ["Essential Hypertension", "Secondary Hypertension"],
    "blood pressure":    ["Essential Hypertension", "Secondary Hypertension", "Congestive Heart Failure"],
    "heart rate":        ["Atrial Fibrillation", "Congestive Heart Failure", "Generalized Anxiety Disorder"],
    "bnp":               ["Congestive Heart Failure"],
    "troponin":          ["Coronary Artery Disease"],
    # Renal
    "creatinine":        ["Chronic Kidney Disease (CKD)", "Acute Kidney Injury (AKI)"],
    "gfr":               ["Chronic Kidney Disease (CKD)", "Acute Kidney Injury (AKI)"],
    "bun":               ["Chronic Kidney Disease (CKD)", "Acute Kidney Injury (AKI)"],
    "potassium":         ["Chronic Kidney Disease (CKD)", "Secondary Hypertension"],
    # Respiratory
    "oxygen saturation": ["Chronic Obstructive Pulmonary Disease (COPD)", "Asthma", "Congestive Heart Failure"],
    "respiratory rate":  ["Chronic Obstructive Pulmonary Disease (COPD)", "Asthma", "Congestive Heart Failure"],
    # Hematology
    "hemoglobin":        ["Iron Deficiency Anemia", "Anemia of Chronic Disease", "B12/Folate Deficiency Anemia", "Chronic Kidney Disease (CKD)"],
    "hematocrit":        ["Iron Deficiency Anemia", "Anemia of Chronic Disease"],
    "mcv":               ["Iron Deficiency Anemia", "B12/Folate Deficiency Anemia"],
    "ferritin":          ["Iron Deficiency Anemia", "Anemia of Chronic Disease"],
}


# =============================================================================
# Condition display name → Disease node in KG (for existing patient conditions)
# =============================================================================

CONDITION_TO_KG_NODE: Dict[str, str] = {
    "diabetes":                        "Type 2 Diabetes Mellitus",
    "type 2 diabetes":                 "Type 2 Diabetes Mellitus",
    "type 1 diabetes":                 "Type 1 Diabetes Mellitus",
    "diabetes mellitus":               "Type 2 Diabetes Mellitus",
    "hypertension":                    "Essential Hypertension",
    "essential hypertension":          "Essential Hypertension",
    "hypertensive disorder":           "Essential Hypertension",
    "heart failure":                   "Congestive Heart Failure",
    "congestive heart failure":        "Congestive Heart Failure",
    "coronary artery disease":         "Coronary Artery Disease",
    "atrial fibrillation":             "Atrial Fibrillation",
    "copd":                            "Chronic Obstructive Pulmonary Disease (COPD)",
    "chronic obstructive":             "Chronic Obstructive Pulmonary Disease (COPD)",
    "asthma":                          "Asthma",
    "chronic kidney disease":          "Chronic Kidney Disease (CKD)",
    "ckd":                             "Chronic Kidney Disease (CKD)",
    "alzheimer":                       "Alzheimer's Disease",
    "dementia":                        "Alzheimer's Disease",
    "depression":                      "Major Depressive Disorder",
    "major depression":                "Major Depressive Disorder",
    "anxiety":                         "Generalized Anxiety Disorder",
    "anemia":                          "Iron Deficiency Anemia",
    "iron deficiency anemia":          "Iron Deficiency Anemia",
    "hypercholesterolemia":            "Hypercholesterolemia",
    "high cholesterol":                "Hypercholesterolemia",
}


# =============================================================================
# KnowledgeGraphService — the main class used by rag_service.py
# =============================================================================

class KnowledgeGraphService:
    """
    MedRAG Knowledge Graph Service.

    Implements the 3 core MedRAG KG operations described in the paper:
      1. find_candidate_diseases()   — Tier 3 matching from patient data
      2. get_distinguishing_features() — Tier 4 differential features
      3. generate_followup_questions()  — Proactive question generation
    """

    def __init__(self):
        self.kg = DIAGNOSTIC_KG
        self.symptom_map = SYMPTOM_TO_DISEASES
        self.observation_map = OBSERVATION_TO_DISEASES
        self.condition_map = CONDITION_TO_KG_NODE

    # ─────────────────────────────────────────────────────────────────────────
    # Step A: Find candidate diseases from retrieved patient data
    # ─────────────────────────────────────────────────────────────────────────

    def find_candidate_diseases(
        self,
        query: str,
        retrieved_data: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Given a user query and retrieved patient data, find candidate diseases
        from the KG that are relevant to this patient's situation.

        Strategy (matching the MedRAG paper's "voting mechanism"):
          1. Extract observation types from retrieved_data → look up OBSERVATION_TO_DISEASES
          2. Extract condition names from retrieved_data → look up CONDITION_TO_KG_NODE
          3. Extract keywords from query → look up SYMPTOM_TO_DISEASES
          4. Score by vote count → return top-N candidates

        Returns:
            List of disease names (Tier 3 KG nodes), ranked by relevance votes
        """
        vote_counts: Dict[str, int] = {}

        def vote(disease_name: str, weight: int = 1):
            vote_counts[disease_name] = vote_counts.get(disease_name, 0) + weight

        # --- Source 1: observations in retrieved_data (strongest signal, weight=3) ---
        for item in retrieved_data:
            if item.get("data_type") != "observations":
                continue
            meta = item.get("metadata", {})
            display = (meta.get("display") or "").lower().strip()
            code = (meta.get("code") or "").lower().strip()

            for obs_key, diseases in self.observation_map.items():
                if obs_key in display or obs_key in code:
                    for d in diseases:
                        vote(d, weight=3)

        # --- Source 2: conditions already recorded for patient (weight=4, highest) ---
        for item in retrieved_data:
            if item.get("data_type") != "conditions":
                continue
            meta = item.get("metadata", {})
            display = (meta.get("display") or "").lower().strip()
            content = (item.get("content") or "").lower().strip()

            for cond_key, kg_node in self.condition_map.items():
                if cond_key in display or cond_key in content:
                    vote(kg_node, weight=4)

        # --- Source 3: query keywords → symptom map (weight=2) ---
        query_lower = query.lower()
        for symptom_key, diseases in self.symptom_map.items():
            if symptom_key in query_lower:
                for d in diseases:
                    vote(d, weight=2)

        # --- Source 4: query directly mentions an observation (weight=2) ---
        for obs_key, diseases in self.observation_map.items():
            if obs_key in query_lower:
                for d in diseases:
                    vote(d, weight=2)

        # Sort by votes descending, return top 5 candidates
        ranked = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        top_candidates = [disease for disease, _ in ranked[:5] if _ > 0]

        logger.info(f"[MedRAG KG] Candidate diseases: {top_candidates}")
        return top_candidates

    # ─────────────────────────────────────────────────────────────────────────
    # Step B: Get distinguishing features for candidates (Tier 4)
    # ─────────────────────────────────────────────────────────────────────────

    def get_distinguishing_features(
        self,
        candidate_diseases: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        For each candidate disease, extract its Tier 4 distinguishing features.
        These are the critical differences used for differential diagnosis.

        Returns:
            Dict mapping disease_name → {distinguishing, against, observations, symptoms}
        """
        features: Dict[str, Dict[str, Any]] = {}

        for category_data in self.kg.values():
            for family_data in category_data.values():
                for disease_name, disease_data in family_data.items():
                    if disease_name in candidate_diseases:
                        features[disease_name] = {
                            "distinguishing": disease_data.get("distinguishing", []),
                            "against":        disease_data.get("against", []),
                            "key_observations": disease_data.get("observations", []),
                            "symptoms":       disease_data.get("symptoms", [])
                        }

        logger.info(f"[MedRAG KG] Extracted features for {len(features)} diseases")
        return features

    # ─────────────────────────────────────────────────────────────────────────
    # Step C: Match patient data against distinguishing features
    # ─────────────────────────────────────────────────────────────────────────

    def match_patient_evidence(
        self,
        candidate_diseases: List[str],
        disease_features: Dict[str, Dict[str, Any]],
        retrieved_data: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Cross-reference each candidate disease's distinguishing features
        against the actual patient data retrieved from Elasticsearch.

        For each disease, determine:
          - supporting_evidence: features found in patient data
          - missing_evidence:    features NOT found (gaps → follow-up questions)
          - confidence:          simple ratio of evidence found

        Returns:
            Dict mapping disease_name → {supporting, missing, confidence}
        """
        # Build a flat searchable set of patient data keywords
        patient_obs_keys: set = set()
        patient_condition_keys: set = set()
        patient_values: Dict[str, str] = {}  # display → value

        for item in retrieved_data:
            meta = item.get("metadata", {})
            display = (meta.get("display") or "").lower()
            value = str(meta.get("value") or "")
            content = (item.get("content") or "").lower()

            if item.get("data_type") == "observations":
                patient_obs_keys.add(display)
                if display:
                    patient_values[display] = value
                # Also add individual words for partial matching
                for word in display.split():
                    if len(word) > 3:
                        patient_obs_keys.add(word)

            elif item.get("data_type") == "conditions":
                patient_condition_keys.add(display)
                for word in display.split():
                    if len(word) > 3:
                        patient_condition_keys.add(word)
                for word in content.split():
                    if len(word) > 3:
                        patient_condition_keys.add(word)

        all_patient_keys = patient_obs_keys | patient_condition_keys

        matched: Dict[str, Dict[str, Any]] = {}

        for disease in candidate_diseases:
            feats = disease_features.get(disease, {})
            key_obs = feats.get("key_observations", [])

            found_obs = []
            missing_obs = []

            for obs in key_obs:
                obs_lower = obs.lower()
                if any(obs_lower in pk or pk in obs_lower for pk in patient_obs_keys):
                    # Find value if available
                    val = ""
                    for pk, pv in patient_values.items():
                        if obs_lower in pk or pk in obs_lower:
                            val = pv
                            break
                    found_obs.append(f"{obs}: {val}" if val else obs)
                else:
                    missing_obs.append(obs)

            total = len(key_obs) if key_obs else 1
            confidence = round(len(found_obs) / total, 2)

            matched[disease] = {
                "supporting_observations": found_obs,
                "missing_observations":    missing_obs,
                "confidence":              confidence,
                "distinguishing_features": feats.get("distinguishing", []),
                "against_features":        feats.get("against", [])
            }

        logger.info(f"[MedRAG KG] Evidence matching complete for {len(matched)} diseases")
        return matched

    # ─────────────────────────────────────────────────────────────────────────
    # Step D: Generate proactive follow-up questions (KG-driven)
    # ─────────────────────────────────────────────────────────────────────────

    def generate_followup_questions(
        self,
        matched_evidence: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        Based on MISSING observations for the top candidate diseases,
        generate targeted follow-up questions to help narrow the diagnosis.

        This is the "proactive diagnostic questioning" mechanism described
        in the MedRAG paper (Section 3.4).
        """
        questions: List[str] = []
        seen: set = set()

        for disease, evidence in matched_evidence.items():
            for missing_obs in evidence.get("missing_observations", []):
                question = f"Do you have {missing_obs} data for this patient? (needed to evaluate {disease})"
                if question not in seen:
                    questions.append(question)
                    seen.add(question)

        return questions[:5]  # Return top 5 questions

    # ─────────────────────────────────────────────────────────────────────────
    # Step E: Build KG context string for LLM prompt injection
    # ─────────────────────────────────────────────────────────────────────────

    def build_kg_context(
        self,
        candidate_diseases: List[str],
        matched_evidence: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Format the KG differential diagnosis information into a structured
        text block that will be injected into the LLM prompt alongside
        patient records.

        This is the "KG-elicited reasoning" step from the MedRAG paper.
        """
        if not candidate_diseases:
            return ""

        lines = [
            "=" * 70,
            "KNOWLEDGE GRAPH — DIFFERENTIAL DIAGNOSIS (MedRAG KG Layer)",
            "=" * 70,
            "",
            f"Based on this patient's data, the following {len(candidate_diseases)} candidate",
            "diagnos(es) have been identified from the medical knowledge graph.",
            "Use these structured differences to reason about the most likely diagnosis.",
            ""
        ]

        for rank, disease in enumerate(candidate_diseases, 1):
            evidence = matched_evidence.get(disease, {})
            confidence = evidence.get("confidence", 0.0)
            supporting = evidence.get("supporting_observations", [])
            missing = evidence.get("missing_observations", [])
            distinguishing = evidence.get("distinguishing_features", [])
            against = evidence.get("against_features", [])

            lines.append(f"[{rank}] {disease}  (Evidence found: {int(confidence * 100)}%)")
            lines.append("-" * 50)

            if supporting:
                lines.append("  Patient data supporting this diagnosis:")
                for obs in supporting:
                    lines.append(f"    ✓ {obs}")

            if distinguishing:
                lines.append("  Key distinguishing features (from KG):")
                for feat in distinguishing[:4]:  # Top 4 features
                    lines.append(f"    • {feat}")

            if against:
                lines.append("  Evidence against this diagnosis:")
                for feat in against[:2]:
                    lines.append(f"    ✗ {feat}")

            if missing:
                lines.append("  Data needed but not found in records:")
                for obs in missing[:3]:
                    lines.append(f"    ? {obs}")

            lines.append("")

        lines += [
            "=" * 70,
            "INSTRUCTION TO LLM:",
            "Use the above KG differential diagnosis context to:",
            "1. Reason about which diagnosis best fits the patient evidence",
            "2. Highlight the most likely diagnosis with supporting evidence",
            "3. Mention alternative diagnoses that cannot be ruled out",
            "4. Note any missing data that would help confirm/exclude diagnoses",
            "=" * 70,
            ""
        ]

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # Master method: Full MedRAG KG pipeline for a single query
    # ─────────────────────────────────────────────────────────────────────────

    def run_kg_pipeline(
        self,
        query: str,
        retrieved_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run the complete MedRAG KG pipeline and return all outputs:
          - candidate_diseases
          - matched_evidence (with confidence scores)
          - kg_context (ready to inject into LLM prompt)
          - followup_questions

        Called from rag_service.py inside process_chat_query().
        """
        # Step A: Find candidates
        candidates = self.find_candidate_diseases(query, retrieved_data)

        if not candidates:
            logger.info("[MedRAG KG] No candidate diseases found — KG context will be empty")
            return {
                "candidate_diseases": [],
                "matched_evidence": {},
                "kg_context": "",
                "followup_questions": []
            }

        # Step B: Get Tier 4 distinguishing features
        features = self.get_distinguishing_features(candidates)

        # Step C: Match patient evidence against features
        matched = self.match_patient_evidence(candidates, features, retrieved_data)

        # Step D: Generate proactive follow-up questions
        followups = self.generate_followup_questions(matched)

        # Step E: Build KG context string for LLM
        kg_context = self.build_kg_context(candidates, matched)

        return {
            "candidate_diseases":  candidates,
            "matched_evidence":    matched,
            "kg_context":          kg_context,
            "followup_questions":  followups
        }


# Global singleton
kg_service = KnowledgeGraphService()
