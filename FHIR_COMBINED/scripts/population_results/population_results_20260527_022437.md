# Population Health Questions — Evaluation Results

**Date:** 20260527_022437  
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
**Time:** 20214ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
0 patients. The limiting factor was the presence of Type II Diabetes, which was required but not found in any patients.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['Type II Diabetes']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19590ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
0 patients. The limiting factor was the presence of a CKD diagnosis code, which was excluded.

**SQL / Query description:** `Condition present=['CKD diagnosis'], absent=['CKD diagnosis']`

---

## POP3 — Treatment gap + medication absence ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 26150ms  

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Response:**
4 patients have the condition of being hypertensive. 0 patients have the observation of antihypertensive prescriptions documented in the past 6 months. 4 patients have the condition of being hypertensive but no matching observation on record. 

context_note: 4 patient(s) have the condition; 0 have the observation documented; 4 have the condition but no matching observation on record.

**SQL / Query description:** `Absence check: cond=['hypertensive', 'hypertension'], obs_absent=['antihypertensive prescriptions'], date=>= DATE_SUB(NOW(), INTERVAL 6 MONTH)`

---

## POP4 — High-utilisation care gap ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB (ambulatory) class; no ED visits or referral data  
**Pipeline:** population_sql  
**Time:** 13620ms  

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Response:**
0 patients have been seen at 3 or more different hospitals in the specified period. No patient in this cohort has reached that threshold.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 24878ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
3 patients have COPD and are over 65. 

The patients are Mason Lewis (000000003), Mia Scott (000000007), and Lincoln Gray (000000048).

No patients have documented spirometry in the past two years.

The context note is: 3 patient(s) have the condition; 0 have the observation documented; 3 have the condition but no matching observation on record.

**SQL / Query description:** `Absence check: cond=['copd', 'chronic obstructive'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 24300ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). 

- cardiovascular disease: this condition is not documented in this cohort's EHR
- type ii diabetes: this condition is not documented in this cohort's EHR
- ckd: 1 patient(s) — Lincoln Gray...

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22151ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
The most common two-condition comorbidity pair across the patient panel is 'Chronic obstructive lung disease (disorder)' and 'Hyperlipidemia (disorder)', co-occurring in 3 patient(s): Mason Lewis, Lincoln Gray, Dominic Webb.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17587ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 patients have 5 or more documented active conditions.

**SQL / Query description:** `Multimorbidity >= 5 conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20908ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
0 patients have both heart failure and an active depression diagnosis. The limiting factor was the absence of heart failure documentation in the cohort's EHR. 

Context note: This result is based on the structured data provided and may not reflect the actual clinical scenario.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'depression']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17464ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
0 patients. The limiting factor was the absence of 'condition_patients' data.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic']`

---

## POP11 — Drug-disease interaction surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23974ms  

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Response:**
0 patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD. The limiting factor was the lack of documentation for the 'peptic ulcer disease diagnosis' condition in this cohort's EHR. The patient with CKD, Lincoln Gray, does not meet the full criteria as they are not prescribed an NSAID.

**SQL / Query description:** `Intersection of conditions: ['nsaid prescription', 'peptic ulcer disease diagnosis', 'ckd']`

---

## POP12 — Preventive care gap for medication risk ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 19197ms  

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Response:**
0 patients meet the criteria. The limiting factor was the presence of osteoporosis diagnosis or DEXA scan on record, which was excluded.

**SQL / Query description:** `Condition present=['long-term corticosteroids'], absent=['osteoporosis']`

---

## POP13 — Polypharmacy safety alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 26138ms  

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Response:**
0 patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy. The limiting factor was the absence of patients with an antiplatelet agent prescription. 

Near-miss breakdown: 
- anticoagulant: 1 patient(s) — Mia Scott
- antiplatelet agent: 0 patients — this condition is not documented in this cohort's EHR

Closest near-miss: Mia Scott meets 1 of 2 criteria.

**SQL / Query description:** `Intersection of conditions: ['anticoagulant', 'antiplatelet agent']`

---

## POP14 — Chronic opioid use surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Synthesis  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 20469ms  

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Response:**
0 patients have been prescribed opioids for more than 90 consecutive days in the past year. The limiting factor was the count_matching field, which indicates that no patients met this criterion.

**SQL / Query description:** `Latest observation: ['duration of opioid prescription'], threshold: NoneNone`

---

## POP15 — Guideline-based contraindication alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 20638ms  

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Response:**
0 patients are currently on metformin and have documented eGFR < 30. This is because no patients in the cohort are currently on metformin, which was the limiting factor.

**SQL / Query description:** `Absence check: cond=['currently on metformin'], obs_absent=['eGFR >= 30'], date=None`

---

## POP16 — Quality measure gap (HEDIS DM-CE) ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 19711ms  

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Response:**
0 patients. The criterion 'patients_with_required_conditions' was the limiting factor, as no patients in the cohort have the required condition 'diabetic'.

**SQL / Query description:** `Condition present=['diabetic'], absent=['statin']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 27630ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
100% of patients (12/12) have blood pressure controlled below 130/80 based on their most recent recorded reading.

Context note: All patients in this cohort have a recorded blood pressure measurement.

**SQL / Query description:** `Latest observation: ['blood pressure'], threshold: <130.0`

---

## POP18 — Cancer screening gap detection ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Colorectal cancer screening not documented in observations table  
**Pipeline:** population_sql  
**Time:** 19591ms  

**Question:**
> Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**Response:**
0 patients have no documented colorectal cancer screening in the past 10 years. The limiting factor was the absence of any patients in the cohort.

**SQL / Query description:** `Absence check: cond=['colorectal cancer'], obs_absent=['colorectal cancer screening'], date=>= DATE_SUB(NOW(), INTERVAL 10 YEAR)`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18705ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
0 patients have a previous MI and documented annual lipid panels. The limiting factor was the lack of documented annual lipid panels.

**SQL / Query description:** `Absence check: cond=['previous mi'], obs_absent=['lipid panel'], date=None`

---

## POP20 — Transition of care quality metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB class; no inpatient/hospitalisation data  
**Pipeline:** population_sql  
**Time:** 20577ms  

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Response:**
0 patients. The limiting factor was the criterion of having no documented primary care follow-up within 30 days of discharge.

**SQL / Query description:** `Absence check: cond=['hospitalised in the past year'], obs_absent=['primary care follow-up within 30 days of discharge'], date=>= DATE_SUB(NOW(), INTERVAL 30 DAY)`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13142ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
1 patient(s) have been seen at 3 or more different hospitals in the consortium: Amelia Parker (3 hospitals).

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17753ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
0 patients. The limiting factor was the absence of contradictions in the diagnoses.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=True`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19072ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
0 patients have a heart failure diagnosis and no echocardiogram recorded at any consortium site in the past two years. The limiting factor was the absence of patients with a heart failure diagnosis.

**SQL / Query description:** `Absence check: cond=['heart failure diagnosis', 'heart failure'], obs_absent=['echocardiogram'], date=None`

---

## POP24 — Care coordination complexity index ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** No — Encounters table has no specialty/department field  
**Pipeline:** population_sql  
**Time:** 12721ms  

**Question:**
> Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**Response:**
0 patients have been seen at 5 or more different hospitals in the specified period. No patient in this cohort has reached that threshold.

**SQL / Query description:** `Cross-hospital: min_h=5, contradiction=False`

---

## POP25 — Redundant utilisation detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** No — Imaging modality/body part not consistently coded in observations  
**Pipeline:** population_sql  
**Time:** 13660ms  

**Question:**
> How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**Response:**
0 patients have been seen at 3 or more different hospitals in the specified period. No patient in this cohort has reached that threshold.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 25 |
| Answered | 25 |
| No data in DB | 12 |
| Errors | 0 |
| Avg response time | 19993ms |
