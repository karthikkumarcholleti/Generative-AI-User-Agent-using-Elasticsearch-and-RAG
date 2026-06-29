# Population Health Questions — Evaluation Results

**Date:** 20260526_181426  
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
**Time:** 21590ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
Based on the provided structured data, there are 0 patients who match the specified criteria. This means that none of the 12 patients in the cohort have a BMI > 30, have not been diagnosed with Type II Diabetes, but have elevated HbA1c or fasting glucose.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['BMI > 30']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20221ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
Based on the provided structured data, 0 patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record.

**SQL / Query description:** `Condition present=['CKD diagnosis'], absent=['CKD diagnosis']`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 23752ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
Based on the structured query results, there are 0 patients over 65 with a COPD diagnosis and no documented spirometry in the past two years. This is because all patients with COPD (Mason Lewis, Mia Scott, and Lincoln Gray) have documented spirometry within the past two years, as indicated by their presence in the "patients_with_observation_in_window" list.

**SQL / Query description:** `Absence check: cond=['copd diagnosis', 'copd'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20050ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). 

Patient 000000048 has CKD, but not the combination of all three conditions.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22692ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
Based on the structured query results, the most common two-condition comorbidity pair across my patient panel is "Chronic obstructive lung disease (disorder)" and "Hyperlipidemia (disorder)" with 3 patients (000000003, 000000048, 000000061) sharing this comorbidity pair.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21525ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 patients in the cohort have five or more documented active conditions. These patients are Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions), Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions), Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions), and Scarlett Gonzalez (5 conditions).

**SQL / Query description:** `Multimorbidity >= 5 conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19905ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
Based on the query results, there are 0 patients with heart failure. However, among the total cohort of 12 patients, 2 patients (000000052 and 000000061) have an active depression diagnosis. Since no patients have both conditions, the intersection count is 0.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'active depression diagnosis']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16967ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Based on the provided structured data, there are 0 patients with diabetes. The condition of diabetes is not documented in the query results.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic']`

---

## POP17 — Population BP control rate ✗ Error

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:**   
**Time:** 13543ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
_No response._

**Error:** HTTP 500: {"detail":"Population query failed: could not convert string to float: '130/80'"}

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17288ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
0 patients have a documented history of a previous MI.

**SQL / Query description:** `Absence check: cond=['previous mi'], obs_absent=['HbA1c', 'eGFR'], date=None`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16905ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
Based on the structured query results, 0 patients have been seen at more than three different hospitals in the consortium in the past two years.

**SQL / Query description:** `Cross-hospital: min_h=4, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16223ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
There are no patients in your panel whose diagnoses at one consortium hospital contradict diagnoses at another.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=True`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21714ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
Based on the provided structured query results, no patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years were found. This indicates that either no patients have heart failure or all patients with heart failure have had an echocardiogram recorded within the past two years.

**SQL / Query description:** `Absence check: cond=['heart failure', 'congestive heart failure'], obs_absent=['echocardiogram'], date=None`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 13 |
| Answered | 12 |
| No data in DB | 0 |
| Errors | 1 |
| Avg response time | 19413ms |
