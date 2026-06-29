# Population Health Questions — Evaluation Results

**Date:** 20260525_153617  
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
**Time:** 17522ms  

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
**Time:** 17538ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
Unfortunately, none of the patients in this cohort have eGFR < 60 for more than one year without a CKD diagnosis code. This is because the structured query results show that 0 patients matched the specified criteria, indicating that no patients in the cohort meet this condition.

**SQL / Query description:** `Condition present + absence filter applied`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19937ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
Based on the structured query results, there are 4 patients who meet the criteria of being over 65 with a COPD diagnosis. These patients are Mason Lewis (000000003), Mia Scott (000000007), Lincoln Gray (000000048), and Dominic Webb (000000061).

**SQL / Query description:** `Intersection of condition groups from: [['copd', 'chronic obstructive', 'chronic obstructive pulmonary disease (copd)']]`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21359ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
Based on the structured query results, 0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). This is because the intersection count is 0, indicating no patients have all three conditions. Additionally, Type II Diabetes is not documented in this cohort, as the search yielded 0 patients.

**SQL / Query description:** `Intersection of condition groups from: [['diabetes', 'type 2 diabetes', 'diabetes mellitus', 'type 2 diabetes mellitus'], ['chronic kidney disease', 'ckd', 'chronic kidney disease (ckd)']]`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18092ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
The most common two-condition comorbidity pair across the patient panel is "Chronic obstructive lung disease (disorder)" and "Hyperlipidemia (disorder)" with 3 patients, specifically patients 000000003, 000000048, and 000000061.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17948ms  

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
**Time:** 18356ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
Based on the structured query results, there are no patients with both heart failure and active depression diagnosis. The condition "heart failure" was not documented in this cohort, as no patients were found to have this condition.

**SQL / Query description:** `Intersection of condition groups from: [['heart failure', 'congestive heart failure'], ['depression', 'major depression', 'major depressive disorder']]`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17540ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Based on the provided structured data, there are 0 patients with diabetes. Therefore, we cannot determine the glycaemic control status or summarise their comorbidities.

**SQL / Query description:** `Stratification by observation: ['glycaemic control status']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20900ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
Unfortunately, the structured data provided does not contain the necessary information to answer the question. The table needed to answer this question would be the "latest_values" table, which is currently empty. This table should contain the most recent recorded blood pressure readings for each patient. Without this data, we cannot determine the percentage of hypertensive patients with controlled blood pressure.

**SQL / Query description:** `Latest observation values for terms: ['blood pressure']`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14902ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
2 patients, Samuel Richardson (000000026) and Isaac Hernandez (000000041), have a documented previous myocardial infarction (MI).

**SQL / Query description:** `Intersection of condition groups from: [['Myocardial infarction']]`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17020ms  

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
**Time:** 26236ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
Based on the structured query results, there are patients in your panel whose diagnoses at one consortium hospital contradict diagnoses at another. Specifically, patients 000000003, 000000048, and 000000005 have contradictory diagnoses for the following conditions: 

- At risk for falls (finding) vs. Chronic obstructive lung disease (disorder) vs. Hypertensive disorder, systemic arterial (in two different pairs).
- At risk for falls (finding) vs. Hyperlipidemia (disorder) (in two different pairs).

These patients have a total of 7 instances where their diagnoses contradict each other across different pairs.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19023ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
Based on the structured query results, there are no patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years. This is because the "patients_with_condition" list is empty, indicating that no patients have the specified condition.

**SQL / Query description:** `Condition present, observation absent. Date filter: None`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 13 |
| Answered | 13 |
| No data in DB | 0 |
| Errors | 0 |
| Avg response time | 18951ms |
