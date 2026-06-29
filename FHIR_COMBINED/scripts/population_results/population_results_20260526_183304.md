# Population Health Questions — Evaluation Results

**Date:** 20260526_183304  
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
**Time:** 20897ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
Based on the structured query results, 0 patients match the specified criteria. This means that none of the 12 patients in the cohort have a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['BMI > 30']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20116ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
Based on the provided structured data, 0 patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record. This indicates that no patients in the cohort meet this specific condition.

**SQL / Query description:** `Condition present=['CKD diagnosis'], absent=['CKD diagnosis']`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21403ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
Based on the structured query results, there are 3 patients over 65 with a COPD diagnosis: Mason Lewis, Mia Scott, and Lincoln Gray. However, none of these patients have documented spirometry in the past two years.

**SQL / Query description:** `Absence check: cond=['copd', 'chronic obstructive'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20921ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
Based on the structured query results, 0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). This is because the "patients_with_all_conditions" list is empty, indicating zero patients matched all three conditions.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22485ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
Among the 12 patients in the cohort, the most common two-condition comorbidity pair is Chronic obstructive lung disease (disorder) and Hyperlipidemia (disorder), found in 3 patients: 000000003, 000000048, and 000000061.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19049ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 patients in the cohort have five or more documented active conditions. These patients are Amelia Parker, Brooklyn Coleman, Dominic Webb, Lincoln Gray, Mason Lewis, Mia Scott, Samuel Richardson, Isabella Martin, Charlotte White, and Scarlett Gonzalez.

**SQL / Query description:** `Multimorbidity >= 5 conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18261ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
Based on the structured query results, there are 0 patients with heart failure who also have an active depression diagnosis. This is because the intersection count is 0, indicating no patients have both conditions.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'depression']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18160ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Based on the structured data provided, it appears that no patients have diabetes or glycaemic control status documented. Therefore, I cannot group the diabetic patients by glycaemic control status.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 37619ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
Based on the provided data, all 12 patients have blood pressure readings available. However, none of the patients have a diastolic blood pressure below 80 mmHg. The diastolic blood pressure readings are as follows:

- Amelia Parker: 65 mmHg
- Mia Scott: 56 mmHg
- Samuel Richardson: 58 mmHg
- Lincoln Gray: 80 mmHg
- Brooklyn Coleman: 70 mmHg
- Dominic Webb: 67 mmHg
- Scarlett Gonzalez: 55 mmHg

Therefore, the percentage of patients with controlled blood pressure (diastolic < 80 mmHg) is 0%.

**SQL / Query description:** `Latest observation: ['blood pressure'], threshold: <130.0`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17725ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
Based on the provided data, there are 0 patients with a previous MI who have documented annual lipid panels.

**SQL / Query description:** `Absence check: cond=['previous mi'], obs_absent=['HbA1c'], date=None`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17453ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
One patient, Amelia Parker (000000005), has been seen at more than three different hospitals in the consortium in the past two years.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18098ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
There are no patients in your panel whose diagnoses at one consortium hospital contradict diagnoses at another. This suggests that all 12 patients have consistent diagnoses across both hospitals.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=True`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18937ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
Based on the provided structured query results, there are 0 patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**SQL / Query description:** `Absence check: cond=['heart failure diagnosis', 'heart failure'], obs_absent=['echocardiogram'], date=None`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 13 |
| Answered | 13 |
| No data in DB | 0 |
| Errors | 0 |
| Avg response time | 20855ms |
