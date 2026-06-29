# Population Health Questions — Evaluation Results

**Date:** 20260526_194435  
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
**Time:** 22131ms  

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Response:**
0 patients match the query criteria. The criterion that eliminated the most patients was the requirement for Type II Diabetes diagnosis, which none of the patients have.

**SQL / Query description:** `Condition present=['Type II Diabetes'], absent=['BMI > 30']`

---

## POP2 — Undiagnosed CKD detection ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 22417ms  

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Response:**
0 patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record. The criterion that eliminated the most patients was the presence of a CKD diagnosis code, which was found in patient 000000048.

**SQL / Query description:** `Condition present=['CKD'], absent=['CKD']`

---

## POP3 — Treatment gap + medication absence ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23396ms  

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Response:**
There are 0 patients with hypertension and no documented antihypertensive prescriptions in the past 6 months. This is because no patients have a recorded hypertension diagnosis and no patients have antihypertensive prescriptions in the past 6 months.

**SQL / Query description:** `Absence check: cond=['hypertensive', 'hypertension'], obs_absent=['antihypertensive prescriptions'], date=>= DATE_SUB(NOW(), INTERVAL 6 MONTH)`

---

## POP4 — High-utilisation care gap ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB (ambulatory) class; no ED visits or referral data  
**Pipeline:** population_sql  
**Time:** 22780ms  

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Response:**
0 patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral. This query could not be evaluated because the data is missing from the EHR - specifically, the 'cardiology_referral' and 'ED_visits' tables are not provided, which are necessary to determine the number of ED visits and whether a cardiology referral was made.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP5 — Surveillance gap identification ✓

**Category:** Undiagnosed Risk Identification  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 23368ms  

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Response:**
There are 0 patients over 65 with a COPD diagnosis and no documented spirometry in the past two years. This is because all patients with COPD (Mason Lewis, Mia Scott, and Lincoln Gray) have documented spirometry within the past two years, as indicated by the "patients_with_observation_in_window" list being empty.

**SQL / Query description:** `Absence check: cond=['copd', 'chronic obstructive'], obs_absent=['spirometry'], date=None`

---

## POP6 — Multi-condition co-occurrence query ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21436ms  

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Response:**
0 patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad). The criterion that eliminated the most patients was the presence of cardiovascular disease, as no patients were found to have this condition.

**SQL / Query description:** `Intersection of conditions: ['cardiovascular disease', 'type ii diabetes', 'ckd']`

---

## POP7 — Population-level co-occurrence ranking ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 21225ms  

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Response:**
The most common two-condition comorbidity pair across the patient panel is Chronic obstructive lung disease (disorder) and Hyperlipidemia (disorder), found in 3 patients: 000000003, 000000048, and 000000061.

**SQL / Query description:** `Pairwise condition co-occurrence across cohort`

---

## POP8 — Multimorbidity index computation ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 24284ms  

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Response:**
10 patients in the cohort have five or more active chronic conditions. These patients are Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions), Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions), Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions), and Scarlett Gonzalez (5 conditions).

**SQL / Query description:** `Multimorbidity >= 5 conditions`

---

## POP9 — Cross-category comorbidity detection ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 17562ms  

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Response:**
0 patients have both heart failure and active depression diagnosis. The condition "heart failure" is not documented in the EHR for any patient.

**SQL / Query description:** `Intersection of conditions: ['heart failure', 'depression']`

---

## POP10 — Sub-cohort stratification + analytics ✓

**Category:** Comorbidity Clustering and Multimorbidity  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 16418ms  

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Response:**
0 patients have diabetes.

**SQL / Query description:** `Stratification: obs=['glycaemic control'], cond=['diabetic patients']`

---

## POP11 — Drug-disease interaction surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 21615ms  

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Response:**
Based on the structured query results, 0 patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD. This is because no patients have all the conditions (intersection_count: 0). However, 1 patient has a documented CKD diagnosis (000000048).

**SQL / Query description:** `Intersection of conditions: ['nsaid prescription', 'peptic ulcer disease diagnosis', 'ckd']`

---

## POP12 — Preventive care gap for medication risk ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23118ms  

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Response:**
Based on the query results, 0 patients meet the criteria of being on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record. The criterion that eliminated the most patients was the presence of osteoporosis diagnosis or DEXA scan on record, which was not documented in any of the patients.

**SQL / Query description:** `Condition present=['long-term corticosteroids'], absent=['osteoporosis']`

---

## POP13 — Polypharmacy safety alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 24965ms  

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Response:**
Based on the query results, 0 patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy. This is because no patients in the cohort have both conditions ('patients_with_all_conditions' is empty). Additionally, no patients have a documented anticoagulant prescription ('anticoagulant' condition search found 0 patients) and no patients have a documented antiplatelet agent prescription ('antiplatelet agent' condition search found 0 patients).

**SQL / Query description:** `Intersection of conditions: ['anticoagulant', 'antiplatelet agent']`

---

## POP14 — Chronic opioid use surveillance ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Synthesis  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 24512ms  

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Response:**
Based on the query results, 0 patients have been prescribed opioids for more than 90 consecutive days in the past year. This is because all 12 patients in the cohort either do not have the required condition ("prescribed opioids") or do not have the excluded condition ("opioid prescription for more than 90 consecutive days").

**SQL / Query description:** `Condition present=['prescribed opioids'], absent=['opioid prescription for more than 90 consecutive days']`

---

## POP15 — Guideline-based contraindication alert ✓

**Category:** Medication and Safety Surveillance  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 21991ms  

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Response:**
0 patients are currently on metformin and have documented eGFR < 30. The criterion that eliminated the most patients was the requirement to be on metformin, as no patients in the cohort have this condition documented.

**SQL / Query description:** `Condition present=['currently on metformin'], absent=['diabetes diagnosis']`

---

## POP16 — Quality measure gap (HEDIS DM-CE) ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — No prescriptions/medications table in llm_ua_enterprise  
**Pipeline:** population_sql  
**Time:** 23204ms  

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Response:**
Based on the query results, none of the 12 patients in the cohort are diabetic patients not on a statin despite no documented contraindication. The criteria breakdown indicates that all 12 patients either do not meet the required conditions (diabetic patients) or do not have data to evaluate the excluded condition (statin).

**SQL / Query description:** `Condition present=['diabetic patients'], absent=['statin']`

---

## POP17 — Population BP control rate ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 26901ms  

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Response:**
Based on the most recent recorded blood pressure readings, all 12 patients in the cohort have a diastolic blood pressure below 130/80 mmHg.

**SQL / Query description:** `Latest observation: ['blood pressure'], threshold: <130.0`

---

## POP18 — Cancer screening gap detection ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Colorectal cancer screening not documented in observations table  
**Pipeline:** population_sql  
**Time:** 19838ms  

**Question:**
> Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**Response:**
0 patients have no documented colorectal cancer screening in the past 10 years. The age criterion eliminated all patients, as none of the patients in the cohort are over 50 years old.

**SQL / Query description:** `Absence check: cond=['colorectal cancer'], obs_absent=['colorectal cancer screening'], date=>= DATE_SUB(NOW(), INTERVAL 10 YEAR)`

---

## POP19 — Monitoring compliance metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 19470ms  

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Response:**
0 patients have a documented previous MI and annual lipid panels. The 'patients_with_condition' list is empty, indicating that no patients have a documented previous MI.

**SQL / Query description:** `Absence check: cond=['previous mi'], obs_absent=['HbA1c'], date=None`

---

## POP20 — Transition of care quality metric ✓

**Category:** Preventive Care and Quality Metrics  
**Complexity:** Inference  
**Data available:** No — Encounters table only has AMB class; no inpatient/hospitalisation data  
**Pipeline:** population_sql  
**Time:** 22596ms  

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Response:**
0 patients have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge. The criterion that eliminated the most patients is the hospitalisation condition, as no patients in the cohort have been hospitalised in the past year.

**SQL / Query description:** `Absence check: cond=['hospitalised in the past year'], obs_absent=['within 30 days of discharge'], date=>= DATE_SUB(NOW(), INTERVAL 30 DAY)`

---

## POP21 — Multi-site utilisation tracking ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18882ms  

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Response:**
One patient, Amelia Parker (000000005), has been seen at more than three different hospitals in the consortium in the past two years. This patient has a documented history of visits to 3 hospitals.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=False`

---

## POP22 — Cross-site data coherence auditing ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 18183ms  

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Response:**
There are no patients in your panel whose diagnoses at one consortium hospital contradict diagnoses at another. 0 patients.

**SQL / Query description:** `Cross-hospital: min_h=3, contradiction=True`

---

## POP23 — Multi-site imaging gap detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** Yes  
**Pipeline:** population_sql  
**Time:** 20892ms  

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Response:**
Based on the query results, 0 patients have a heart failure diagnosis and no echocardiogram recorded at any consortium site in the past two years. This is because the "patients_with_condition" list is empty, indicating no patients have a heart failure diagnosis.

**SQL / Query description:** `Absence check: cond=['heart failure', 'congestive heart failure'], obs_absent=['echocardiogram'], date=None`

---

## POP24 — Care coordination complexity index ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Synthesis  
**Data available:** No — Encounters table has no specialty/department field  
**Pipeline:** population_sql  
**Time:** 22857ms  

**Question:**
> Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**Response:**
Based on the structured query results, 0 patients have been seen by more than four specialities across the consortium in the past year. This is because the 'count' is 0, indicating no patients matched the criteria. The'min_hospitals' value of 5 suggests that the query was looking for patients seen in at least 5 different hospitals, which may have contributed to the lack of matches.

**SQL / Query description:** `Cross-hospital: min_h=5, contradiction=False`

---

## POP25 — Redundant utilisation detection ✓

**Category:** Cross-Hospital Utilisation and Care Coordination  
**Complexity:** Inference  
**Data available:** No — Imaging modality/body part not consistently coded in observations  
**Pipeline:** population_sql  
**Time:** 18849ms  

**Question:**
> How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**Response:**
0 patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities. This is because the query found 0 patients.

**SQL / Query description:** `Cross-hospital: min_h=2, contradiction=False`

---

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 25 |
| Answered | 25 |
| No data in DB | 12 |
| Errors | 0 |
| Avg response time | 21715ms |
