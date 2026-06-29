# Population Health Questions — Evaluation Results

**Date:** 20260525_155500  
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
**Time:** 18874ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
Based on the structured query results, there are 0 patients with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose. This condition is not documented in this cohort.

**SQL / Query description:** `Intersection of condition groups from: [['diabetes', 'type 2 diabetes', 'diabetes mellitus', 'type 2 diabetes mellitus']]`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14586ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
0 patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record.

**SQL / Query description:** `Condition present + absence filter applied`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19632ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
4 patients have a COPD diagnosis. These patients are Mason Lewis (000000003), Mia Scott (000000007), Lincoln Gray (000000048), and Dominic Webb (000000061). However, the query does not provide information on spirometry in the past two years, so we cannot confirm if these patients have no documented spirometry in the past two years.

**SQL / Query description:** `Intersection of condition groups from: [['copd', 'chronic obstructive', 'chronic obstructive pulmonary disease (copd)']]`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18679ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
Based on the structured query results, 0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). This is because the intersection count is 0, indicating no patients have all three conditions. Additionally, Type II Diabetes is not documented in this cohort, as no patients were found with this condition.

**SQL / Query description:** `Intersection of condition groups from: [['diabetes', 'type 2 diabetes', 'diabetes mellitus', 'type 2 diabetes mellitus'], ['chronic kidney disease', 'ckd', 'chronic kidney disease (ckd)']]`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20284ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
Among the 12 patients in this cohort, the most common two-condition comorbidity pair is Chronic obstructive lung disease (disorder) and Hyperlipidemia (disorder), which is observed in 3 patients: 000000003, 000000048, and 000000061.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18504ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
Based on the structured query results, there are 0 patients with five or more active chronic conditions across at least three disease categories.

**SQL / Query description:** `Patients with >= 3 active conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19004ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
Based on the structured data provided, there are no patients with both heart failure and an active depression diagnosis. This is because the intersection count is 0, indicating no patients have both conditions. The condition "heart failure" was not documented in this cohort, as no patients were found to have this condition.

**SQL / Query description:** `Intersection of condition groups from: [['heart failure', 'congestive heart failure'], ['depression', 'major depression', 'major depressive disorder']]`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13345ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Unfortunately, there are no patients with diabetes documented in this cohort.

**SQL / Query description:** `Stratification by observation: ['glycaemic control']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 30566ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
Based on the provided data, all 12 patients have their blood pressure readings recorded. However, none of the patients have a diastolic blood pressure reading below 80 mmHg. The diastolic blood pressure readings for the patients are as follows: Amelia Parker (65 mmHg), Mia Scott (56 mmHg), Samuel Richardson (58 mmHg), Lincoln Gray (80 mmHg), Brooklyn Coleman (70 mmHg), Dominic Webb (67 mmHg), and Scarlett Gonzalez (55 mmHg).

**SQL / Query description:** `Latest observation values for terms: ['blood pressure']`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 15097ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
One patient, Isaac Hernandez (000000041), has a previous MI and documented annual lipid panels.

**SQL / Query description:** `Intersection of condition groups from: [['Myocardial infarction (disorder)']]`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 15918ms  

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
**Time:** 10242ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
There are no patients in this cohort whose diagnoses at one consortium hospital contradict diagnoses at another.

**SQL / Query description:** `Cross-hospital encounter analysis (>= 3 hospitals)`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16739ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
No patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years were found in this cohort.

**SQL / Query description:** `Condition present, observation absent. Date filter: None`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 13 |
| Answered | 13 |
| No data in DB | 0 |
| Errors | 0 |
| Avg response time | 17805ms |
