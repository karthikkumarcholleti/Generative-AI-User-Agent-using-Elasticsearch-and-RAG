# Population Health Questions — Evaluation Results

**Date:** 20260527_121922  
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
**Time:** 16644ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
0 patients satisfy all criteria for this question.

Required condition ('Type II Diabetes'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('BMI > 30'): 0 patients have this — no exclusions applied.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['BMI > 30']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14825ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
0 patients satisfy all criteria for this question.

Required condition ('CKD diagnosis code'): 1 patient(s) — Lincoln Gray.
Excluded by ('CKD diagnosis code'): 1 patient(s) have this — Lincoln Gray.
Lab threshold (eGFR < 60 for more than one year > 60.0): 0 patient(s) — none in this cohort.

**SQL / Query description:** `Condition present=['CKD diagnosis code'], absent=['CKD diagnosis code']`

---

## POP3 — Treatment gap + medication absence ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_no_data  
**Time:** 15096ms  

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Response:**
No medication prescription data exists in this database (no prescriptions table).
Clinical notes were searched — no matching drug mentions found for this cohort.

Patients with related conditions that may be relevant:
  - 'hypertensive': Mason Lewis, Amelia Parker, Samuel Richardson, Brooklyn Coleman

**SQL / Query description:** `Notes fallback: medication terms ['antihypertensive prescriptions', 'hypertensive', 'antihypertensive']`

---

## POP4 — High-utilisation care gap ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB (ambulatory) class; no ED visits or referral data  
**Pipeline:** population_sql  
**Time:** 13675ms  

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Response:**
0 patients have been seen at 1 or more different hospitals in the specified period. No patient in this cohort has reached that threshold.

**SQL / Query description:** `Cross-hospital: min_h=1, contradiction=False`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13674ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
3 patient(s) have copd but no spirometry documented: Mason Lewis, Mia Scott, Lincoln Gray.
'spirometry' is not recorded for any patient in this cohort — this data type is not in the structured database.
Age filter applied: 7 of 12 patients are over 65 in this cohort.

**SQL / Query description:** `Absence check: cond=['copd', 'chronic obstructive'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14034ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - cardiovascular disease: 0 patients — not documented in this cohort's EHR
  - type ii diabetes: 0 patients — not documented in this cohort's EHR
  - ckd: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13104ms  

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
**Time:** 12761ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 of 12 patients have 5 or more documented active conditions: Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions), Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions), Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions), Scarlett Gonzalez (5 conditions). Note: disease category classification is not encoded in the structured database; these patients span diverse diagnostic areas based on their high condition counts.

**SQL / Query description:** `Multimorbidity >= 5 conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13110ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - heart failure: 0 patients — not documented in this cohort's EHR
  - depression: 2 patient(s) — Brooklyn Coleman, Dominic Webb

Closest near-miss: Brooklyn Coleman, Dominic Webb each satisfy 1 of 2 conditions.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'depression']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13559ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
0 patients have 'diabetic patients' documented in this cohort's EHR. Stratification by glycaemic control cannot be performed.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic patients']`

---

## POP11 — Drug-disease interaction surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_no_data  
**Time:** 14873ms  

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Response:**
No medication prescription data exists in this database (no prescriptions table).
Clinical notes were searched — no matching drug mentions found for this cohort.

Patients with related conditions that may be relevant:
  - 'chronic kidney disease': Lincoln Gray

**SQL / Query description:** `Notes fallback: medication terms ['chronic kidney disease', 'nsaid', 'peptic ulcer disease']`

---

## POP12 — Preventive care gap for medication risk ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_no_data  
**Time:** 14113ms  

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Response:**
No medication prescription data exists in this database (no prescriptions table).
Clinical notes were searched — no matching drug mentions found for this cohort.
No patients in this cohort have related conditions documented that would indicate the medications in question are prescribed.

**SQL / Query description:** `Notes fallback: medication terms ['long-term corticosteroids', 'DEXA scan', 'corticosteroid']`

---

## POP13 — Polypharmacy safety alert ⚠ No data

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:**   
**Time:** 13709ms  

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Response:**
_No response._

**Error:** HTTP 500: {"detail":"Population query failed: unsupported operand type(s) for +: 'NoneType' and 'list'"}

---

## POP14 — Chronic opioid use surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Synthesis  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_no_data  
**Time:** 15898ms  

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Response:**
No medication prescription data exists in this database (no prescriptions table).
Clinical notes were searched — no matching drug mentions found for this cohort.
No patients in this cohort have related conditions documented that would indicate the medications in question are prescribed.

**SQL / Query description:** `Notes fallback: medication terms ['opioid', 'patients who have been prescribed opioids', 'opioids prescription duration']`

---

## POP15 — Guideline-based contraindication alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_no_data  
**Time:** 14828ms  

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Response:**
No medication prescription data exists in this database (no prescriptions table).
Clinical notes were searched — no matching drug mentions found for this cohort.
No patients in this cohort have related conditions documented that would indicate the medications in question are prescribed.

**SQL / Query description:** `Notes fallback: medication terms ['metformin', 'eGFR', 'currently on metformin']`

---

## POP16 — Quality measure gap (HEDIS DM-CE) ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_no_data  
**Time:** 14207ms  

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Response:**
No medication prescription data exists in this database (no prescriptions table).
Clinical notes were searched — no matching drug mentions found for this cohort.
No patients in this cohort have related conditions documented that would indicate the medications in question are prescribed.

**SQL / Query description:** `Notes fallback: medication terms ['statin', 'diabetic patients']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13843ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
5 of 12 patients (41%) have blood pressure < 130.0 based on their most recent recorded reading.
Patients meeting threshold: Mason Lewis, Isabella Martin, Mia Scott, Samuel Richardson, Scarlett Gonzalez.
Patients NOT meeting threshold (7): Amelia Parker, Charlotte White, Isaac Hernandez, Lincoln Gray, Brooklyn Coleman, Christian Dean, Dominic Webb.

**SQL / Query description:** `Latest observation: ['blood pressure'], threshold: <130.0`

---

## POP18 — Cancer screening gap detection ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Colorectal cancer screening not documented in observations table  
**Pipeline:** population_sql  
**Time:** 14282ms  

**Question:**
> Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**Response:**
9 patient(s) are over 50 in this cohort: Mason Lewis, Amelia Parker, Mia Scott, Samuel Richardson, Isaac Hernandez, Lincoln Gray, Brooklyn Coleman, Christian Dean, Dominic Webb.
No 'colorectal cancer screening' is documented for any of them — this screening type is not recorded in the structured database.

**SQL / Query description:** `Absence check: cond=['colorectal cancer'], obs_absent=['colorectal cancer screening'], date=>= DATE_SUB(NOW(), INTERVAL 10 YEAR)`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13229ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - previous mi: 1 patient(s) — Mia Scott
  - lipid panel: 2 patient(s) — Samuel Richardson, Isaac Hernandez

Closest near-miss: Mia Scott, Samuel Richardson, Isaac Hernandez each satisfy 1 of 2 conditions.

**SQL / Query description:** `Intersection of conditions: ['previous mi', 'lipid panel']`

---

## POP20 — Transition of care quality metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB class; no inpatient/hospitalisation data  
**Pipeline:** population_sql  
**Time:** 14538ms  

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Response:**
0 patients satisfy all criteria for this question.

12 patient(s) have encounters recorded (18 total, all ambulatory class). No inpatient hospitalisations found — this dataset contains only outpatient visits.
'primary care follow-up' is not recorded for any patient in this cohort — this data type is not in the structured database.

**SQL / Query description:** `Absence check: cond=['hospitalised'], obs_absent=['primary care follow-up'], date=>= DATE_SUB(NOW(), INTERVAL 30 DAY)`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13559ms  

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
**Time:** 18131ms  

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
**Time:** 13456ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
0 patients satisfy all criteria for this question.

No patients have 'heart failure diagnosis' documented in this cohort's EHR.
'echocardiogram' is not recorded for any patient in this cohort — this data type is not in the structured database.

**SQL / Query description:** `Absence check: cond=['heart failure diagnosis', 'heart failure'], obs_absent=['echocardiogram'], date=None`

---

## POP24 — Care coordination complexity index ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** No — Encounters table has no specialty/department field  
**Pipeline:** population_sql  
**Time:** 13281ms  

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
**Pipeline:** population_no_data  
**Time:** 13452ms  

**Question:**
> How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**Response:**
No imaging/radiology data exists in this database. The dataset contains structured conditions, observations (labs and vitals), encounters, and notes — but no radiology orders, imaging study records, or DICOM-linked procedures. Duplicate imaging detection requires a radiology information system (RIS) or procedure table that is not present in this cohort's EHR extract.

**SQL / Query description:** `No imaging table`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 25 |
| Answered | 24 |
| No data in DB | 12 |
| Errors | 1 |
| Avg response time | 14235ms |
