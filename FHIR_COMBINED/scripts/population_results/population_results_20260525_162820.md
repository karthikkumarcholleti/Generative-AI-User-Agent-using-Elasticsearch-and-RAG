# Population Health Questions — Evaluation Results

**Date:** 20260525_162820  
**Cohort:** 12 patients  
**Architecture:** Ziletti & D'Ambrosi (2025) two-step RAG + text-to-SQL  
**Temporal reasoning:** TIMER (arXiv:2503.04176) deterministic parser  

## Cohort Members

- Dominic Webb (000000061)
- Christian Dean (000000055)
- Brooklyn Coleman (000000052)
- Lincoln Gray (000000048)
- Isaac Hernandez (000000041)
- Scarlett Gonzalez (127)
- Samuel Richardson (000000026)
- Charlotte White (000000008)
- Mia Scott (000000007)
- Amelia Parker (000000005)
- Isabella Martin (000000004)
- Mason Lewis (000000003)

---

## POP1 — Multi-criterion negative + lab logic ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18371ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
Based on the structured query results, there are 0 patients who match the criteria of having a BMI > 30 and not being diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose. This condition is not documented in this cohort.

**SQL / Query description:** `Intersection of condition groups from: [['diabetes', 'type 2 diabetes', 'diabetes mellitus', 'type 2 diabetes mellitus']]`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 15370ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
Based on the provided structured data, 0 patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record.

**SQL / Query description:** `Condition present + absence filter applied`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 15222ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
4 patients over 65 with a COPD diagnosis were identified: Mason Lewis, Mia Scott, Lincoln Gray, and Dominic Webb.

**SQL / Query description:** `Intersection of condition groups from: [['copd', 'chronic obstructive', 'chronic obstructive pulmonary disease (copd)']]`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18794ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
Based on the provided data, 0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). This is because the intersection count is 0, indicating no patients have all three conditions. Additionally, Type II Diabetes is not documented in this cohort, as the search yielded 0 patients.

**SQL / Query description:** `Intersection of condition groups from: [['diabetes', 'type 2 diabetes', 'diabetes mellitus', 'type 2 diabetes mellitus'], ['chronic kidney disease', 'ckd', 'chronic kidney disease (ckd)']]`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19833ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
The most common two-condition comorbidity pair across the patient panel is "Chronic obstructive lung disease (disorder)" and "Hyperlipidemia (disorder)" with 3 patients (000000003, 000000048, 000000061) having this comorbidity pair.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20749ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 patients in the cohort have five or more documented active conditions. These patients are Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions), Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions), Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions), and Scarlett Gonzalez (5 conditions).

**SQL / Query description:** `Patients with >= 5 active conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18651ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
Based on the structured query results, there are no patients with both heart failure and active depression diagnosis. The condition "heart failure" was not documented in this cohort, as no patients were found to have this condition. However, two patients (000000052 and 000000061) have an active depression diagnosis.

**SQL / Query description:** `Intersection of condition groups from: [['heart failure', 'congestive heart failure'], ['depression', 'major depression', 'major depressive disorder']]`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13981ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Unfortunately, no patients in this cohort have diabetes as a documented condition.

**SQL / Query description:** `Stratification by observation: ['HbA1c']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 32456ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
Based on the provided data, all 12 patients have blood pressure readings available. However, the data does not specify whether these readings are the most recent ones. 

To answer the question, we need to know if the readings are the most recent ones, but since the data does not provide this information, we cannot determine if the blood pressure is controlled below 130/80 for these patients.

However, if we assume that the readings provided are the most recent ones, then we can see that all patients have diastolic blood pressure below 80 mmHg, which is below the target of 130/80.

**SQL / Query description:** `Latest observation values for terms: ['blood pressure']`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16591ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
Based on the structured query results, 1 patient with a previous MI has documented annual lipid panels. This patient is Isaac Hernandez (000000041).

**SQL / Query description:** `Intersection of condition groups from: [['Myocardial infarction (disorder)']]`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17605ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
Based on the structured query results, only 1 patient has been seen at more than three different hospitals in the consortium in the past two years. This patient is Amelia Parker (000000005), who has been seen at 3 different hospitals.

**SQL / Query description:** `Cross-hospital encounter analysis (>= 3 hospitals)`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 23274ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
Based on the structured query results, there are no patients whose diagnoses at one consortium hospital contradict diagnoses at another. The top pairs of diagnoses with discrepancies are:

- Chronic obstructive lung disease (disorder) and Hyperlipidemia (disorder) or At risk for falls (finding) or Gastroesophageal reflux disease (disorder) in 3 or 2 patients, respectively.
- At risk for falls (finding) and Chronic obstructive lung disease (disorder) or Hypertensive disorder, systemic arterial in 2 patients each.

However, these pairs do not necessarily indicate contradictory diagnoses.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17731ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
Based on the structured query results, there are no patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years. This is because the "patients_with_condition" list is empty, indicating that no patients match the specified condition.

**SQL / Query description:** `Condition present, observation absent. Date filter: None`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 13 |
| Answered | 13 |
| No data in DB | 0 |
| Errors | 0 |
| Avg response time | 19125ms |
