# Population Health Query Pipeline — Final Evaluation Report

**Date:** 2026-05-27
**Pipeline:** Ziletti & D'Ambrosi (2025) RAG+A+C + MedRAG KG entity expansion
**Model:** Llama 3.1 8B (4-bit quantized, 2x Tesla T4)
**Cohort:** 12 patients (UPHP enterprise dataset)
**Judge framework:** arXiv:2602.14564 (same model, deterministic do_sample=False)

## Judge Summary

| Dimension | Weight | Avg Score |
|---|---|---|
| Medical Accuracy | 30% | 4.760 |
| Safety | 25% | 5.000 |
| Completeness | 20% | 4.640 |
| Helpfulness | 15% | 4.840 |
| Clarity | 10% | 4.840 |
| **Weighted Total** | 100% | **4.816** |

> Note: POP10 (MA=1) and POP25 (MA=3) reflect judge bias against correct zero-result answers.
> Both are factually accurate: no T2DM patients in this cohort (confirmed by DB query);
> no imaging/radiology table exists in the dataset.

---

## Per-Question Results

### POP1
**Q:** Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**A:** 0 patients satisfy all criteria for this question.

Required condition ('Type II Diabetes'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('elevated HbA1c'): 0 patients have this — no exclusions applied.
Lab threshold (BMI > 30.0): 0 patient(s) — none in this cohort.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Correctly handled absent conditions

---

### POP2
**Q:** Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**A:** 0 patients satisfy all criteria for this question.

Required condition ('CKD diagnosis code'): 1 patient(s) — Lincoln Gray.
Excluded by ('CKD diagnosis code'): 1 patient(s) have this — Lincoln Gray.
Lab threshold (eGFR < 60 for more than one year > 60.0): 0 patient(s) — none in this cohort.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate and clear query response

---

### POP3
**Q:** Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**A:** 4 patient(s) have hypertensive but no antihypertensive prescriptions documented: Mason Lewis, Amelia Parker, Samuel Richardson, Brooklyn Coleman.
'antihypertensive prescriptions' is not recorded for any patient in this cohort — this data type is not in the structured database.

**Judge:** MA=5 S=5 C=3 H=5 CL=4 | Score=4.5 | Clear and concise patient list provided

---

### POP4
**Q:** Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**A:** 0 patients have been seen at 1 or more different hospitals in the specified period. No patient in this cohort has reached that threshold.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate and safe cohort identification

---

### POP5
**Q:** Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**A:** 3 patient(s) have copd but no spirometry documented: Mason Lewis, Mia Scott, Lincoln Gray.
'spirometry' is not recorded for any patient in this cohort — this data type is not in the structured database.
All 3 patient(s) listed above are over 65 (7 of 12 total cohort members qualify).

**Judge:** MA=5 S=5 C=4 H=5 CL=4 | Score=4.7 | Accurate patient list with clear explanation

---

### POP6
**Q:** How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**A:** 0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - cardiovascular disease: 0 patients — not documented in this cohort's EHR
  - type ii diabetes: 0 patients — not documented in this cohort's EHR
  - ckd: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate intersection of conditions reported

---

### POP7
**Q:** What is the most common two-condition comorbidity pair across my patient panel?

**A:** The most common two-condition comorbidity pair across the patient panel is 'Chronic obstructive lung disease (disorder)' and 'Hyperlipidemia (disorder)', co-occurring in 3 patient(s): Mason Lewis, Lincoln Gray, Dominic Webb.

**Judge:** MA=5 S=5 C=4 H=4 CL=5 | Score=4.65 | Correctly identified comorbidity pair

---

### POP8
**Q:** Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**A:** 10 of 12 patients have 5 or more documented active conditions: Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions), Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions), Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions), Scarlett Gonzalez (5 conditions). Note: disease category classification is not encoded in the structured database; these patients span diverse diagnostic areas based on their high condition counts.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Correctly identified patients with multimorbidity

---

### POP9
**Q:** How many patients with heart failure also have an active depression diagnosis?

**A:** 0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - heart failure: 0 patients — not documented in this cohort's EHR
  - depression: 2 patient(s) — Brooklyn Coleman, Dominic Webb

Closest near-miss: Brooklyn Coleman, Dominic Webb each satisfy 1 of 2 conditions.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate condition intersection result

---

### POP10
**Q:** Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**A:** 0 patients have 'diabetic' documented in this cohort's EHR (searched: 'diabetic', 'diabetes', 'diabetic patients', 'type 2 diabetes'). Stratification by glycaemic control cannot be performed.

**Judge:** MA=1 S=5 C=3 H=5 CL=4 | Score=3.3 | Incorrect search terms used

---

### POP11
**Q:** Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**A:** 0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - nsaid: 0 patients — not documented in this cohort's EHR
  - peptic ulcer disease: 0 patients — not documented in this cohort's EHR
  - chronic kidney disease: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate and safe query response

---

### POP12
**Q:** Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**A:** 0 patients satisfy all criteria for this question.

Required condition ('long-term corticosteroids'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('osteoporosis'): 0 patients have this — no exclusions applied.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate and safe query response

---

### POP13
**Q:** Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**A:** 0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - anticoagulant: 1 patient(s) — Mia Scott
  - antiplatelet agent: 0 patients — not documented in this cohort's EHR

Closest near-miss: Mia Scott satisfies 1 of 2 conditions.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate and clear patient data analysis

---

### POP14
**Q:** How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**A:** 0 patients satisfy all criteria for this question.

Required condition ('prescribed opioids'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('opioid prescription for more than 90 consecutive days'): 0 patients have this — no exclusions applied.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Clear and accurate response with no false positives

---

### POP15
**Q:** List patients who are currently on metformin but have documented eGFR < 30.

**A:** 0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - currently on metformin: 0 patients — not documented in this cohort's EHR
  - eGFR: 0 patients — not documented in this cohort's EHR

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate count of non-existent patients

---

### POP16
**Q:** How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**A:** 0 patients satisfy all criteria for this question.

No patients have 'diabetic' documented in this cohort's EHR.
'documented' is not recorded for any patient in this cohort — this data type is not in the structured database.

**Judge:** MA=5 S=5 C=4 H=5 CL=5 | Score=4.8 | Accurate absence check with clear explanation

---

### POP17
**Q:** What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**A:** 5 of 12 patients (41%) have blood pressure < 130.0 based on their most recent recorded reading.
Patients meeting threshold: Mason Lewis, Isabella Martin, Mia Scott, Samuel Richardson, Scarlett Gonzalez.
Patients NOT meeting threshold (7): Amelia Parker, Charlotte White, Isaac Hernandez, Lincoln Gray, Brooklyn Coleman, Christian Dean, Dominic Webb.

**Judge:** MA=5 S=5 C=5 H=4 CL=5 | Score=4.85 | Accurate BP control data provided

---

### POP18
**Q:** Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**A:** 9 patient(s) are over 50 in this cohort: Mason Lewis, Amelia Parker, Mia Scott, Samuel Richardson, Isaac Hernandez, Lincoln Gray, Brooklyn Coleman, Christian Dean, Dominic Webb.
No 'colorectal cancer screening' is documented for any of them — this screening type is not recorded in the structured database.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate patient list with clear details

---

### POP19
**Q:** How many patients with a previous MI have documented annual lipid panels?

**A:** 0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - previous mi: 1 patient(s) — Mia Scott
  - lipid panel: 2 patient(s) — Samuel Richardson, Isaac Hernandez

Closest near-miss: Mia Scott, Samuel Richardson, Isaac Hernandez each satisfy 1 of 2 conditions.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate count with condition breakdown

---

### POP20
**Q:** Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**A:** 0 patients satisfy all criteria for this question.

12 patient(s) have encounters recorded (18 total, all ambulatory class). No inpatient hospitalisations found — this dataset contains only outpatient visits.
'primary care follow-up within 30 days of discharge' is not recorded for any patient in this cohort — this data type is not in the structured database.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate response to query

---

### POP21
**Q:** Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**A:** 1 patient(s) have been seen at 3 or more different hospitals in the consortium: Amelia Parker (3 hospitals).

**Judge:** MA=5 S=5 C=5 H=4 CL=5 | Score=4.85 | Accurate and clear results provided

---

### POP22
**Q:** Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**A:** 0 patients. The limiting factor was the absence of contradictions in diagnoses between consortium hospitals.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate diagnosis comparison result

---

### POP23
**Q:** Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**A:** 0 patients satisfy all criteria for this question.

No patients have 'heart failure' documented in this cohort's EHR.
'echocardiogram' is not recorded for any patient in this cohort — this data type is not in the structured database.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate absence check with clear explanation

---

### POP24
**Q:** Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**A:** 0 patients have been seen at 5 or more different hospitals in the specified period. No patient in this cohort has reached that threshold.

**Judge:** MA=5 S=5 C=5 H=5 CL=5 | Score=5.0 | Accurate and clear result provided

---

### POP25
**Q:** How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**A:** No imaging/radiology data exists in this database. The dataset contains structured conditions, observations (labs and vitals), encounters, and notes — but no radiology orders, imaging study records, or DICOM-linked procedures. Duplicate imaging detection requires a radiology information system (RIS) or procedure table that is not present in this cohort's EHR extract.

**Judge:** MA=3 S=5 C=3 H=4 CL=4 | Score=3.75 | Insufficient data, no imaging table

---
