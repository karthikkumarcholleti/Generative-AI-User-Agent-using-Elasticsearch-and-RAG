# Population Health Questions — Evaluation Results

**Date:** 20260527_151011  
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
**Time:** 17040ms  

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
**Time:** 15247ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
0 patients satisfy all criteria for this question.

Required condition ('CKD diagnosis'): 1 patient(s) — Lincoln Gray.
Excluded by ('CKD diagnosis'): 1 patient(s) have this — Lincoln Gray.

**SQL / Query description:** `Condition present=['CKD diagnosis'], absent=['CKD diagnosis']`

---

## POP3 — Treatment gap + medication absence ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 15563ms  

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Response:**
4 patient(s) have hypertensive but no antihypertensive prescriptions documented: Mason Lewis, Amelia Parker, Samuel Richardson, Brooklyn Coleman.
'antihypertensive prescriptions' is not recorded for any patient in this cohort — this data type is not in the structured database.

**SQL / Query description:** `Absence check: cond=['hypertensive', 'hypertension'], obs_absent=['antihypertensive prescriptions'], date=>= DATE_SUB(NOW(), INTERVAL 6 MONTH)`

---

## POP4 — High-utilisation care gap ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB (ambulatory) class; no ED visits or referral data  
**Pipeline:** population_sql  
**Time:** 13664ms  

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Response:**
2 patient(s) satisfy all criteria: Samuel Richardson, Isaac Hernandez.

Required condition ('cardiac complaints'): 2 patient(s) — Samuel Richardson, Isaac Hernandez.
Excluded condition ('cardiology referral'): 0 patients have this — no exclusions applied.

**SQL / Query description:** `Condition present=['cardiac complaints'], absent=['cardiology referral']`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14191ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
3 patient(s) have copd diagnosis but no spirometry documented: Mason Lewis, Mia Scott, Lincoln Gray.
'spirometry' is not recorded for any patient in this cohort — this data type is not in the structured database.
All 3 patient(s) listed above are over 65 (7 of 12 total cohort members qualify).

**SQL / Query description:** `Absence check: cond=['copd diagnosis', 'copd'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14370ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - cardiovascular disease: 0 patients — not documented in this cohort's EHR (ES semantic search also tried related terms: disease of cardiovascular system (disorder), coronary artery disease, disease of artery (disorder) — condition is not present in this dataset)
  - type ii diabetes: 0 patients — not documented in this cohort's EHR (ES semantic search also tried related terms: diabetes mellitus type 2 (disorder), diabetes mellitus type 2 in obese (disorder), diabetes mellitus — condition is not present in this dataset)
  - ckd: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14855ms  

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
**Time:** 13023ms  

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
**Time:** 13245ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - heart failure: 0 patients — not documented in this cohort's EHR (ES semantic search also tried related terms: chronic heart failure (disorder), congestive heart failure, diastolic heart failure (disorder) — condition is not present in this dataset)
  - depression: 2 patient(s) — Brooklyn Coleman, Dominic Webb

Closest near-miss: Brooklyn Coleman, Dominic Webb each satisfy 1 of 2 conditions.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'depression']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14059ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
0 patients have 'diabetic' documented in this cohort's EHR (searched: 'diabetic', 'diabetes', 'diabetic patients', 'type 2 diabetes'). Stratification by glycaemic control cannot be performed.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic', 'diabetes']`

---

## POP11 — Drug-disease interaction surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 15159ms  

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Response:**
0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - nsaid: 0 patients — not documented in this cohort's EHR (ES semantic search also tried related terms: chronic adenoiditis, duodenitis, atopic dermatitis, unspecified — condition is not present in this dataset)
  - peptic ulcer disease: 0 patients — not documented in this cohort's EHR (ES semantic search also tried related terms: acute gastric ulcer (disorder), duodenal ulcer disease (disorder), disease of stomach (disorder) — condition is not present in this dataset)
  - chronic kidney disease: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.

**SQL / Query description:** `Intersection of conditions: ['nsaid', 'peptic ulcer disease', 'chronic kidney disease']`

---

## POP12 — Preventive care gap for medication risk ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 14099ms  

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Response:**
0 patients satisfy all criteria for this question.

Required condition ('long-term corticosteroids'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('osteoporosis'): 0 patients have this — no exclusions applied.

**SQL / Query description:** `Condition present=['long-term corticosteroids'], absent=['osteoporosis']`

---

## POP13 — Polypharmacy safety alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 13968ms  

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Response:**
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - anticoagulant: 1 patient(s) — Mia Scott
  - antiplatelet agent: 0 patients — not documented in this cohort's EHR (ES semantic search also tried related terms: antiphospholipid syndrome (disorder), anemia caused by antineoplastic agent, chromhidrosis (disorder) — condition is not present in this dataset)

Closest near-miss: Mia Scott satisfies 1 of 2 conditions.

**SQL / Query description:** `Intersection of conditions: ['anticoagulant', 'antiplatelet agent']`

---

## POP14 — Chronic opioid use surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Synthesis  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 14255ms  

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Response:**
0 patients satisfy all criteria for this question.

Required condition ('prescribed opioids'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('opioid prescription for more than 90 consecutive days'): 0 patients have this — no exclusions applied.

**SQL / Query description:** `Condition present=['prescribed opioids'], absent=['opioid prescription for more than 90 consecutive days']`

---

## POP15 — Guideline-based contraindication alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 14846ms  

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Response:**
0 patients satisfy all criteria for this question.

Required condition ('currently on metformin'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('diabetes diagnosis'): 0 patients have this — no exclusions applied.
Lab threshold (eGFR < 30.0): 0 patient(s) — none in this cohort.

**SQL / Query description:** `Condition present=['currently on metformin'], absent=['diabetes diagnosis']`

---

## POP16 — Quality measure gap (HEDIS DM-CE) ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 16269ms  

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Response:**
0 patients satisfy all criteria for this question.

No patients have 'diabetic' documented in this cohort's EHR.
'contraindication to statin therapy' is not recorded for any patient in this cohort — this data type is not in the structured database.

**SQL / Query description:** `Absence check: cond=['diabetic', 'diabetes'], obs_absent=['contraindication to statin therapy'], date=None`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 14205ms  

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
**Time:** 14382ms  

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
**Time:** 13473ms  

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
**Time:** 16237ms  

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Response:**
0 patients satisfy all criteria for this question.

12 patient(s) have encounters recorded (18 total, all ambulatory class): Mason Lewis, Isabella Martin, Amelia Parker, Mia Scott, Charlotte White, Samuel Richardson, Isaac Hernandez, Lincoln Gray, Brooklyn Coleman, Christian Dean, Dominic Webb, Scarlett Gonzalez. No inpatient hospitalisations found — this dataset contains only outpatient visits.
'primary care follow-up within 30 days of discharge' is not recorded for any patient in this cohort — this data type is not in the structured database.

**SQL / Query description:** `Absence check: cond=['hospitalised in the past year'], obs_absent=['primary care follow-up within 30 days of discharge'], date=>= DATE_SUB(NOW(), INTERVAL 30 DAY)`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 13678ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
1 patient(s) have been seen at 4 or more different hospitals in the consortium: Amelia Parker (5 hospitals).

**SQL / Query description:** `Cross-hospital: min_h=4, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17550ms  

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
**Time:** 14439ms  

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
**Time:** 13256ms  

**Question:**
> Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**Response:**
1 patient(s) have been seen at 5 or more different hospitals in the consortium: Amelia Parker (5 hospitals).

**SQL / Query description:** `Cross-hospital: min_h=5, contradiction=False`

---

## POP25 — Redundant utilisation detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** No — Imaging modality/body part not consistently coded in observations  
**Pipeline:** population_no_data  
**Time:** 13250ms  

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
| Answered | 25 |
| No data in DB | 12 |
| Errors | 0 |
| Avg response time | 14572ms |
