# Population Health Questions — Evaluation Results

**Date:** 20260526_201349  
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
**Time:** 23064ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
Based on the provided structured query results, there are 0 patients who meet the specified criteria. The criteria breakdown indicates that no patients have the required condition of Type II Diabetes, which eliminated all potential patients.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['BMI > 30']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 24807ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
Based on the structured query results, there are no patients who meet the criteria of having eGFR < 60 for more than one year but have no CKD diagnosis code in their record. The breakdown shows that the patient "000000048" meets both the required condition (CKD) and the excluded condition (CKD), indicating that this patient has a CKD diagnosis code in their record.

**SQL / Query description:** `Condition present=['CKD'], absent=['CKD']`

---

## POP3 — Treatment gap + medication absence ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23248ms  

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Response:**
There are 4 patients with hypertension and no documented antihypertensive prescriptions in the past 6 months. These patients are Mason Lewis (000000003), Amelia Parker (000000005), Samuel Richardson (000000026), and Brooklyn Coleman (000000052).

**SQL / Query description:** `Absence check: cond=['hypertensive', 'hypertension'], obs_absent=['antihypertensive prescriptions'], date=>= DATE_SUB(NOW(), INTERVAL 6 MONTH)`

---

## POP4 — High-utilisation care gap ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB (ambulatory) class; no ED visits or referral data  
**Pipeline:** population_sql  
**Time:** 19599ms  

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Response:**
Unfortunately, the structured data provided does not contain the necessary information to answer the question. The query results indicate that no patients match the specified criteria.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22125ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
There are 3 patients over 65 with a COPD diagnosis and no documented spirometry in the past two years. These patients are Mason Lewis (000000003), Mia Scott (000000007), and Lincoln Gray (000000048).

**SQL / Query description:** `Absence check: cond=['copd', 'chronic obstructive'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 23155ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
Based on the query results, 0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). 

Cardiovascular disease is not documented in the EHR for any patients. 
CKD is documented in the EHR for patient 000000048.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20836ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
The most common two-condition comorbidity pair across my patient panel is Chronic obstructive lung disease (disorder) and Hyperlipidemia (disorder), found in 3 patients.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22603ms  

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
**Time:** 19165ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
Based on the query results, there are 0 patients with both heart failure and an active depression diagnosis. This is confirmed by the "intersection_count" being 0 and the "patients_with_all_conditions" list being empty.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'active depression diagnosis']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16911ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Based on the provided data, there are 0 patients with diabetes.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic patients']`

---

## POP11 — Drug-disease interaction surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 21508ms  

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Response:**
Based on the query results, 0 patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD. The condition 'peptic ulcer disease diagnosis' is not documented in the EHR for any patient in the cohort.

**SQL / Query description:** `Intersection of conditions: ['nsaid prescription', 'peptic ulcer disease diagnosis', 'ckd']`

---

## POP12 — Preventive care gap for medication risk ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 21723ms  

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Response:**
No patients in the cohort of 12 are on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record. This is because the criteria breakdown shows that there are no patients with the required condition of long-term corticosteroids.

**SQL / Query description:** `Condition present=['long-term corticosteroids'], absent=['osteoporosis']`

---

## POP13 — Polypharmacy safety alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 18793ms  

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Response:**
0 patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy.

**SQL / Query description:** `Intersection of conditions: ['anticoagulant', 'antiplatelet agent']`

---

## POP14 — Chronic opioid use surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Synthesis  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 22005ms  

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Response:**
Based on the structured query results, 0 patients have been prescribed opioids for more than 90 consecutive days in the past year. The criteria breakdown indicates that no patients met the required condition of having an opioid prescription, and no patients were excluded due to having an opioid prescription for less than 90 consecutive days.

**SQL / Query description:** `Condition present=['opioid prescription'], absent=['opioid prescription for <= 90 consecutive days']`

---

## POP15 — Guideline-based contraindication alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 21788ms  

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Response:**
Based on the provided structured query results, there are 0 patients who are currently on metformin and have documented eGFR < 30. This is because the 'answer_count' is 0, indicating no patients meet the specified criteria.

**SQL / Query description:** `Absence check: cond=['currently on metformin'], obs_absent=['eGFR >= 30'], date=None`

---

## POP16 — Quality measure gap (HEDIS DM-CE) ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 20876ms  

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Response:**
Unfortunately, the structured data provided does not contain information about the patients' diabetic status, age, statin use, or contraindications. Therefore, I am unable to provide a direct clinical answer based on the given data.

**SQL / Query description:** `Absence check: cond=['diabetic'], obs_absent=['statin prescription'], date=None`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 27024ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
All 12 patients in the cohort have blood pressure readings recorded. 12 patients (100%) have blood pressure controlled below 130/80 based on their most recent recorded reading.

**SQL / Query description:** `Latest observation: ['blood pressure'], threshold: <130.0`

---

## POP18 — Cancer screening gap detection ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Colorectal cancer screening not documented in observations table  
**Pipeline:** population_sql  
**Time:** 22058ms  

**Question:**
> Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**Response:**
Based on the structured query results, there are 0 patients over 50 in the panel with no documented colorectal cancer screening in the past 10 years. This is because the 'answer_count' is 0, indicating no patients meet the specified criteria.

**SQL / Query description:** `Absence check: cond=['colorectal cancer'], obs_absent=['colorectal cancer screening'], date=>= DATE_SUB(NOW(), INTERVAL 10 YEAR)`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18745ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
No patients with a previous MI have documented annual lipid panels. This is because the query results show an "answer_count" of 0, indicating no patients met the specified criteria.

**SQL / Query description:** `Absence check: cond=['previous mi'], obs_absent=['lipid panel'], date=None`

---

## POP20 — Transition of care quality metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB class; no inpatient/hospitalisation data  
**Pipeline:** population_sql  
**Time:** 22874ms  

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Response:**
Based on the structured query results, there are no patients in the cohort who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge. The answer count is 0, and the list of patients who meet this criterion is empty.

**SQL / Query description:** `Absence check: cond=['hospitalised in the past year'], obs_absent=['primary care follow-up'], date=>= DATE_SUB(NOW(), INTERVAL 30 DAY)`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17205ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
0 patients have been seen at more than three different hospitals in the consortium in the past two years.

**SQL / Query description:** `Cross-hospital: min_h=4, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18702ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
There are no patients in your panel whose diagnoses at one consortium hospital contradict diagnoses at another. The query results show that the count of such contradictions is 0.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=True`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20252ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
There are no patients in the cohort with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years. This is because the 'answer_count' is 0, indicating no patients meet the specified criteria.

**SQL / Query description:** `Absence check: cond=['heart failure', 'congestive heart failure'], obs_absent=['echocardiogram'], date=None`

---

## POP24 — Care coordination complexity index ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** No — Encounters table has no specialty/department field  
**Pipeline:** population_sql  
**Time:** 19445ms  

**Question:**
> Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**Response:**
Based on the provided structured query results, it appears that no patients have been seen by more than four specialities across the consortium in the past year. The 'count' is 0, indicating that there are no patients meeting this criterion.

**SQL / Query description:** `Cross-hospital: min_h=5, contradiction=False`

---

## POP25 — Redundant utilisation detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** No — Imaging modality/body part not consistently coded in observations  
**Pipeline:** population_sql  
**Time:** 19645ms  

**Question:**
> How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**Response:**
Based on the provided structured query results, no patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities. This is indicated by the 'count' field being 0.

**SQL / Query description:** `Cross-hospital: min_h=2, contradiction=False`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 25 |
| Answered | 25 |
| No data in DB | 12 |
| Errors | 0 |
| Avg response time | 21126ms |
