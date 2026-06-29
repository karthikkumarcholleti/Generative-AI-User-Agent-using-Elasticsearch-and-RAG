# Population Health Questions — Evaluation Results

**Date:** 20260526_212046  
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
**Time:** 20406ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
0 patients meet the specified criteria. The limiting factor was the presence of Type II Diabetes, which is a required condition that none of the patients have.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['BMI > 30']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 25096ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
0 patients meet the criteria of having eGFR < 60 for more than one year but no CKD diagnosis code in their record. This is because all patients with the required condition (CKD diagnosis code) are also listed as having the excluded condition (CKD diagnosis code), meaning no patient meets the criteria. The limiting factor was the presence of the CKD diagnosis code, which was required but also excluded.

**SQL / Query description:** `Condition present=['CKD diagnosis code'], absent=['CKD diagnosis code']`

---

## POP3 — Treatment gap + medication absence ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 24298ms  

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Response:**
4 patients have documented hypertension. 4 patients have hypertension with no documented antihypertensive prescriptions in the past 6 months. The patients with this condition are Mason Lewis (000000003), Amelia Parker (000000005), Samuel Richardson (000000026), and Brooklyn Coleman (000000052).

**SQL / Query description:** `Absence check: cond=['hypertensive', 'hypertension'], obs_absent=['antihypertensive prescriptions'], date=>= DATE_SUB(NOW(), INTERVAL 6 MONTH)`

---

## POP4 — High-utilisation care gap ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB (ambulatory) class; no ED visits or referral data  
**Pipeline:** population_sql  
**Time:** 21570ms  

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Response:**
0 patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral. The limiting factor was the count of patients with three or more ED visits in the past year for cardiac complaints, as no patients met this criterion.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22710ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
There are 3 patients over 65 with a COPD diagnosis. The patients are Mason Lewis (000000003), Mia Scott (000000007), and Lincoln Gray (000000048). 

No patients over 65 with a COPD diagnosis have documented spirometry in the past two years.

**SQL / Query description:** `Absence check: cond=['copd diagnosis', 'copd'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 23477ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). The limiting factor was the absence of documentation for cardiovascular disease and Type II Diabetes in this cohort's EHR. However, there is 1 patient with CKD, which is Lincoln Gray.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 29056ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
The most common two-condition comorbidity pair across the patient panel is Chronic obstructive lung disease (disorder) and Hyperlipidemia (disorder), affecting 3 patients.

0 patients have all listed conditions.

The near-miss breakdown for the pair with the next highest count (At risk for falls (finding) and Chronic obstructive lung disease (disorder)) is as follows:
- At risk for falls (finding): 3 patients
- Chronic obstructive lung disease (disorder): 4 patients
- Closest near-miss patient: 000000048...

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 24745ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 patients in the cohort have 5 or more documented active conditions. The patients with 5 or more conditions are Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions), Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions), Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions), and Scarlett Gonzalez (5 conditions).

**SQL / Query description:** `Multimorbidity >= 5 conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 23438ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
There are 0 patients with heart failure who also have an active depression diagnosis. This is because no patients in the cohort have heart failure (the condition is not documented in this cohort's EHR), making it the limiting factor for the intersection count. The breakdown shows that 2 patients have depression, but neither of them has heart failure. The closest near-miss patient, Dominic Webb, meets only 1 of the 2 criteria.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'depression']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18136ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
Based on the provided structured query results, there are no patients with diabetes (glycaemic control status) documented in this cohort's EHR.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic patients']`

---

## POP11 — Drug-disease interaction surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 24953ms  

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Response:**
Based on the query results, there are 0 patients currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD. This is because no patients have a documented NSAID prescription, which is the limiting factor. The near-miss breakdown shows that Lincoln Gray is the closest near-miss patient, meeting 1 of the 3 criteria.

**SQL / Query description:** `Intersection of conditions: ['nsaid', 'peptic ulcer disease', 'chronic kidney disease']`

---

## POP12 — Preventive care gap for medication risk ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 22130ms  

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Response:**
There are 0 patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record in this cohort. The limiting factor was the absence of patients with the required condition "long-term corticosteroids", as there are no patients with this condition.

**SQL / Query description:** `Condition present=['long-term corticosteroids'], absent=['osteoporosis']`

---

## POP13 — Polypharmacy safety alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23686ms  

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Response:**
0 patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy. This is because neither anticoagulant nor antiplatelet agent is documented in this cohort's EHR, making it impossible to identify patients meeting this criterion.

Context note: This result may be due to the specific patient population or the data collection methods used in this study.

**SQL / Query description:** `Intersection of conditions: ['anticoagulant', 'antiplatelet agent']`

---

## POP14 — Chronic opioid use surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Synthesis  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 20501ms  

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Response:**
0 patients have been prescribed opioids for more than 90 consecutive days in the past year. The criterion "opioid prescription for more than 90 consecutive days" was the limiting factor, as no patients met this condition.

**SQL / Query description:** `Condition present=['prescribed opioids'], absent=['opioid prescription for more than 90 consecutive days']`

---

## POP15 — Guideline-based contraindication alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23902ms  

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Response:**
0 patients are currently on metformin and have documented eGFR < 30. The limiting factor was the absence of patients on metformin, as no patients in this cohort are taking metformin. The list of patients on metformin is empty. The context note provides additional information: No patients in this cohort have the required condition documented in the EHR.

**SQL / Query description:** `Absence check: cond=['currently on metformin'], obs_absent=['eGFR >= 30'], date=None`

---

## POP16 — Quality measure gap (HEDIS DM-CE) ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 19885ms  

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Response:**
0 patients are not on a statin despite no documented contraindication. The criterion "diabetic patients" was the limiting factor, as no patients in the cohort met this condition.

**SQL / Query description:** `Condition present=['diabetic patients'], absent=['statin']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 30683ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
Based on the structured query results, 100% (12/12) of the patients have blood pressure controlled below 130/80 based on their most recent recorded reading.

This is because all 12 patients have a diastolic blood pressure below 130 mmHg, with values ranging from 55 to 80 mmHg.

**SQL / Query description:** `Latest observation: ['blood pressure'], threshold: <130.0`

---

## POP18 — Cancer screening gap detection ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Colorectal cancer screening not documented in observations table  
**Pipeline:** population_sql  
**Time:** 23115ms  

**Question:**
> Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**Response:**
Based on the provided structured query results, there are 0 patients over 50 in the panel with no documented colorectal cancer screening in the past 10 years. The limiting factor was the absence of any patients with the required condition documented in the EHR, as indicated by the empty 'answer_patients' list and the presence of the 'context_note'.

**SQL / Query description:** `Absence check: cond=['colorectal cancer'], obs_absent=['colorectal cancer screening'], date=>= DATE_SUB(NOW(), INTERVAL 10 YEAR)`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20524ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
0 patients have documented annual lipid panels. The limiting factor was the absence of patients with a previous MI, as no patients in this cohort have this condition documented in the EHR.

**SQL / Query description:** `Absence check: cond=['previous mi'], obs_absent=['HbA1c'], date=None`

---

## POP20 — Transition of care quality metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB class; no inpatient/hospitalisation data  
**Pipeline:** population_sql  
**Time:** 25846ms  

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Response:**
Based on the query results, there are 0 patients in the cohort who have been hospitalized in the past year and have no documented primary care follow-up within 30 days of discharge.

The limiting factor for this count was the criterion of "no documented primary care follow-up within 30 days of discharge", as the cohort size is 12 patients and the query results indicate that no patients meet this condition.

No patients in this cohort have the required condition documented in the EHR.

**SQL / Query description:** `Absence check: cond=['hospitalised'], obs_absent=['within 30 days of discharge'], date=>= DATE_SUB(NOW(), INTERVAL 30 DAY)`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18651ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
0 patients have been seen at more than three different hospitals in the consortium in the past two years. The limiting factor was the minimum number of hospitals seen, which was 4.

**SQL / Query description:** `Cross-hospital: min_h=4, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20155ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
There are 0 patients in the cohort whose diagnoses at one consortium hospital contradict diagnoses at another. The limiting factor for this count is the empty 'contradictions' list, indicating that no contradictions were found.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=True`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21878ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
There are 0 patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years. The limiting factor was the absence of patients with a heart failure diagnosis, as no patients in this cohort have the required condition documented in the EHR.

**SQL / Query description:** `Absence check: cond=['heart failure', 'congestive heart failure'], obs_absent=['echocardiogram'], date=None`

---

## POP24 — Care coordination complexity index ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** No — Encounters table has no specialty/department field  
**Pipeline:** population_sql  
**Time:** 18750ms  

**Question:**
> Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**Response:**
0 patients have been seen by more than four specialities across the consortium in the past year. The limiting factor was the minimum number of hospitals a patient had to visit, which was 5.

**SQL / Query description:** `Cross-hospital: min_h=5, contradiction=False`

---

## POP25 — Redundant utilisation detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** No — Imaging modality/body part not consistently coded in observations  
**Pipeline:** population_sql  
**Time:** 20636ms  

**Question:**
> How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**Response:**
0 patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities. The limiting factor was the'min_hospitals' criterion, which required at least 2 hospitals to be involved. The 'count' field directly indicates that no patients met this criterion.

**SQL / Query description:** `Cross-hospital: min_h=2, contradiction=False`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 25 |
| Answered | 25 |
| No data in DB | 12 |
| Errors | 0 |
| Avg response time | 22729ms |
