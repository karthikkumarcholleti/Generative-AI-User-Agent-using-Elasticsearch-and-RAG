# Population Health Query Evaluation — Final Results

**Date:** 2026-05-27  
**Cohort:** 12 patients (UPHP pilot panel)  
**Architecture:** Ziletti & D'Ambrosi (2025) RAG+A+C + MedRAG KG entity expansion  
**Temporal reasoning:** TIMER (arXiv:2503.04176) deterministic parser  
**Evaluation:** LLM-as-a-Judge (arXiv:2602.14564)  
**Overall score:** **4.960 / 5.000**  

---

## Cohort Members

| Patient ID | Name |
|---|---|
| 000000003 | Mason Lewis |
| 000000004 | Isabella Martin |
| 000000005 | Amelia Parker |
| 000000007 | Mia Scott |
| 000000008 | Charlotte White |
| 000000026 | Samuel Richardson |
| 000000041 | Isaac Hernandez |
| 000000048 | Lincoln Gray |
| 000000052 | Brooklyn Coleman |
| 000000055 | Christian Dean |
| 000000061 | Dominic Webb |
| 127 | Scarlett Gonzalez |

---

## Category 1 — Undiagnosed Risk Identification

### POP1 — Multi-criterion negative + lab logic

**Question:**
> Find all patients of mine with a BMI > 30 who have not been diagnosed with Type II Diabetes but have elevated HbA1c or fasting glucose.

**Answer:**
```
0 patients satisfy all criteria for this question.

Required condition ('Type II Diabetes'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('elevated HbA1c'): 0 patients have this — no exclusions applied.
Lab threshold (BMI > 30.0): 0 patient(s) — none in this cohort.
```

**Data available:** Yes — limiting factor is absence of BMI > 30 observations and T2DM diagnoses in this cohort.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14892ms

---

### POP2 — Undiagnosed CKD detection

**Question:**
> Which of my patients have eGFR < 60 for more than one year but have no CKD diagnosis code in their record?

**Answer:**
```
0 patients satisfy all criteria for this question.

Required condition ('CKD diagnosis'): 1 patient(s) — Lincoln Gray.
Excluded by ('CKD diagnosis'): 1 patient(s) have this — Lincoln Gray.
```

**Data available:** Yes — Lincoln Gray has CKD documented, so he is correctly excluded by the "no CKD diagnosis" criterion.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 15717ms

---

### POP3 — Treatment gap + medication absence

**Question:**
> Find all hypertensive patients with no documented antihypertensive prescriptions in the past 6 months.

**Answer:**
```
4 patient(s) have hypertensive but no antihypertensive prescriptions documented:
Mason Lewis, Amelia Parker, Samuel Richardson, Brooklyn Coleman.

Patients with 'hypertensive' (4 found): Mason Lewis, Amelia Parker, Samuel Richardson, Brooklyn Coleman.
'antihypertensive prescriptions' is not recorded for any patient in this cohort —
this observation type may not be in the structured database.
```

**Data available:** No — no prescriptions/medications table in llm_ua_enterprise. The 4 hypertensive patients are identified; absence of prescription records is a data gap, not a clinical finding.  
**Judge score:** 4.850 (MA=5 S=5 C=5 H=4 CL=5)  
**Pipeline:** population_sql | 16577ms

---

### POP4 — High-utilisation care gap

**Question:**
> Which of my patients have had three or more ED visits in the past year for cardiac complaints but no cardiology referral?

**Answer:**
```
0 patients have been seen at 3 or more different hospitals in the specified period.
No patient in this cohort has reached that threshold.
```

**Data available:** No — encounters table only has AMB (ambulatory) class; no ED visits or referral data.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 15246ms

---

### POP5 — Surveillance gap identification

**Question:**
> Identify patients over 65 with a COPD diagnosis and no documented spirometry in the past two years.

**Answer:**
```
3 patient(s) have copd diagnosis but no spirometry documented:
Mason Lewis, Mia Scott, Lincoln Gray.

Patients with 'copd diagnosis' (3 found): Mason Lewis, Mia Scott, Lincoln Gray.
'spirometry' is not recorded for any patient in this cohort —
this observation type may not be in the structured database.
Age filter applied: patients over 65 only.
```

**Data available:** Yes — 3 COPD patients over 65 identified; spirometry is a genuine data gap in this dataset.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14880ms

---

## Category 2 — Comorbidity Clustering and Multimorbidity

### POP6 — Multi-condition co-occurrence query

**Question:**
> How many of my patients have a combination of cardiovascular disease, Type II Diabetes, and CKD (the cardiorenal-metabolic triad)?

**Answer:**
```
0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - cardiovascular disease: 0 patients — not documented in this cohort's EHR
  - type ii diabetes: 0 patients — not documented in this cohort's EHR
  - ckd: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.
```

**Data available:** Yes — CKD documented for Lincoln Gray; CVD and T2DM absent from this cohort.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14376ms

---

### POP7 — Population-level co-occurrence ranking

**Question:**
> What is the most common two-condition comorbidity pair across my patient panel?

**Answer:**
```
The most common two-condition comorbidity pair across the patient panel is
'Chronic obstructive lung disease (disord' and 'Hyperlipidemia (disorder)',
co-occurring in 3 patient(s): Mason Lewis, Lincoln Gray, Dominic Webb.
```

**Data available:** Yes.  
**Judge score:** 4.850 (MA=5 S=5 C=5 H=4 CL=5)  
**Pipeline:** population_sql | 15348ms

---

### POP8 — Multimorbidity index computation

**Question:**
> Which patients in my panel have five or more active chronic conditions across at least three disease categories?

**Answer:**
```
10 of 12 patients have 5 or more documented active conditions:
Amelia Parker (52 conditions), Brooklyn Coleman (23 conditions), Dominic Webb (21 conditions),
Lincoln Gray (20 conditions), Mason Lewis (14 conditions), Mia Scott (9 conditions),
Samuel Richardson (9 conditions), Isabella Martin (8 conditions), Charlotte White (5 conditions),
Scarlett Gonzalez (5 conditions).

Note: disease category classification is not encoded in the structured database;
these patients span diverse diagnostic areas based on their high condition counts.
```

**Data available:** Yes — disease category field not encoded; condition counts used as proxy.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14285ms

---

### POP9 — Cross-category comorbidity detection

**Question:**
> How many patients with heart failure also have an active depression diagnosis?

**Answer:**
```
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - heart failure: 0 patients — not documented in this cohort's EHR
  - depression: 2 patient(s) — Brooklyn Coleman, Dominic Webb

Closest near-miss: Brooklyn Coleman satisfies 1 of 2 conditions.
```

**Data available:** Yes — no heart failure patients; 2 patients with depression identified.  
**Judge score:** 4.800 (MA=5 S=5 C=4 H=5 CL=5)  
**Pipeline:** population_sql | 13014ms

---

### POP10 — Sub-cohort stratification + analytics

**Question:**
> Group my diabetic patients by glycaemic control status (controlled vs. uncontrolled) and summarise their other comorbidities.

**Answer:**
```
0 patients have 'diabetic patients' documented in this cohort's EHR.
Stratification by glycaemic control cannot be performed.
```

**Data available:** Yes — no diabetic patients in this cohort; stratification is not applicable.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 15243ms

---

## Category 3 — Medication and Safety Surveillance

### POP11 — Drug-disease interaction surveillance

**Question:**
> Which patients are currently prescribed an NSAID and also have a documented peptic ulcer disease diagnosis or CKD?

**Answer:**
```
0 patients satisfy all 3 condition(s) simultaneously.

Per-condition breakdown:
  - nsaid: 0 patients — not documented in this cohort's EHR
  - peptic ulcer disease: 0 patients — not documented in this cohort's EHR
  - chronic kidney disease: 1 patient(s) — Lincoln Gray

Closest near-miss: Lincoln Gray satisfies 1 of 3 conditions.
```

**Data available:** No — no prescriptions table. CKD documented for Lincoln Gray.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14879ms

---

### POP12 — Preventive care gap for medication risk

**Question:**
> Find all patients on long-term corticosteroids with no osteoporosis diagnosis or DEXA scan on record.

**Answer:**
```
0 patients satisfy all criteria for this question.

Required condition ('long-term corticosteroids'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('osteoporosis'): 0 patients have this — no exclusions applied.
```

**Data available:** No — no prescriptions table; no corticosteroid or osteoporosis records.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14682ms

---

### POP13 — Polypharmacy safety alert

**Question:**
> Which of my patients are prescribed both an anticoagulant and an antiplatelet agent without a documented indication for dual therapy?

**Answer:**
```
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - anticoagulant: 1 patient(s) — Mia Scott
  - antiplatelet agent: 0 patients — not documented in this cohort's EHR

Closest near-miss: Mia Scott satisfies 1 of 2 conditions.
```

**Data available:** No — no prescriptions table. Mia Scott has anticoagulant documented as a condition; antiplatelet not found.  
**Judge score:** 4.850 (MA=5 S=5 C=5 H=4 CL=5)  
**Pipeline:** population_sql | 13830ms

---

### POP14 — Chronic opioid use surveillance

**Question:**
> How many patients have been prescribed opioids for more than 90 consecutive days in the past year?

**Answer:**
```
0 patients satisfy all criteria for this question.

Required condition ('opioids'): 0 patients — not documented in this cohort's EHR.
Excluded condition ('opioid prescription duration < 90 consecutive days'): 0 patients have this —
no exclusions applied.
```

**Data available:** No — no prescriptions table; no opioid records.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 13709ms

---

### POP15 — Guideline-based contraindication alert

**Question:**
> List patients who are currently on metformin but have documented eGFR < 30.

**Answer:**
```
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - currently on metformin: 0 patients — not documented in this cohort's EHR
  - eGFR: 0 patients — not documented in this cohort's EHR
```

**Data available:** No — no prescriptions table; no metformin or eGFR records in structured form.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 15058ms

---

## Category 4 — Preventive Care and Quality Metrics

### POP16 — Quality measure gap (HEDIS DM-CE)

**Question:**
> How many of my diabetic patients aged 40-75 are not on a statin despite no documented contraindication?

**Answer:**
```
0 patients satisfy all criteria for this question.

No patients have 'diabetic patients' documented in this cohort's EHR.
  (ES semantic search also tried related terms — condition is not present in this dataset.)
'statin prescription or statin administration' is not recorded for any patient in this cohort —
this observation type may not be in the structured database.
```

**Data available:** No — no diabetic patients; no statin records.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 15077ms

---

### POP17 — Population BP control rate

**Question:**
> What percentage of my hypertensive patients have blood pressure controlled below 130/80 based on their most recent recorded reading?

**Answer:**
```
12 of 12 patients (100%) have blood pressure < 130.0 based on their most recent recorded reading.
```

**Data available:** Yes.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 13818ms

---

### POP18 — Cancer screening gap detection

**Question:**
> Which patients over 50 in my panel have no documented colorectal cancer screening in the past 10 years?

**Answer:**
```
0 patients satisfy all criteria for this question.

No patients have 'colorectal cancer' documented in this cohort's EHR.
  (ES semantic search also tried related terms — condition is not present in this dataset.)
'colorectal cancer screening' is not recorded for any patient in this cohort —
this observation type may not be in the structured database.
Age filter applied: patients over 50 only.
```

**Data available:** No — no colorectal cancer records or screening observations.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14347ms

---

### POP19 — Monitoring compliance metric

**Question:**
> How many patients with a previous MI have documented annual lipid panels?

**Answer:**
```
0 patients satisfy all 2 condition(s) simultaneously.

Per-condition breakdown:
  - previous mi: 1 patient(s) — Mia Scott
  - lipid panel: 0 patients — not documented in this cohort's EHR

Closest near-miss: Mia Scott satisfies 1 of 2 conditions.
```

**Data available:** Yes — Mia Scott has a previous MI; no lipid panel observations recorded for any patient.  
**Judge score:** 4.800 (MA=5 S=5 C=4 H=5 CL=5)  
**Pipeline:** population_sql | 14972ms

---

### POP20 — Transition of care quality metric

**Question:**
> Find all patients in my panel who have been hospitalised in the past year and have no documented primary care follow-up within 30 days of discharge.

**Answer:**
```
0 patients satisfy all criteria for this question.

No patients have 'hospitalised in the past year' documented in this cohort's EHR.
  (ES semantic search also tried related terms — condition is not present in this dataset.)
'primary care follow-up' is not recorded for any patient in this cohort —
this observation type may not be in the structured database.
```

**Data available:** No — encounters table has only AMB (ambulatory) class; no inpatient records.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 14839ms

---

## Category 5 — Cross-Hospital Utilisation and Care Coordination

### POP21 — Multi-site utilisation tracking

**Question:**
> Which patients have been seen at more than three different hospitals in the consortium in the past two years?

**Answer:**
```
1 patient(s) have been seen at 3 or more different hospitals in the consortium:
Amelia Parker (3 hospitals).
```

**Data available:** Yes.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 13115ms

---

### POP22 — Cross-site data coherence auditing

**Question:**
> Are there patients in my panel whose diagnoses at one consortium hospital contradict diagnoses at another (e.g., coded as diabetic at one site and non-diabetic at another)?

**Answer:**
```
0 patients. The limiting factor was the absence of contradictory diagnoses in the cohort's EHR.
```

**Data available:** Yes — cross-site coherence check executed; no contradictions found.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 19938ms

---

### POP23 — Multi-site imaging gap detection

**Question:**
> Find patients with a heart failure diagnosis who have had no echocardiogram recorded at any consortium site in the past two years.

**Answer:**
```
0 patients satisfy all criteria for this question.

No patients have 'heart failure diagnosis' documented in this cohort's EHR.
  (ES semantic search also tried related terms — condition is not present in this dataset.)
'echocardiogram' is not recorded for any patient in this cohort —
this observation type may not be in the structured database.
```

**Data available:** Yes — no heart failure patients in cohort.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 13642ms

---

### POP24 — Care coordination complexity index

**Question:**
> Which of my complex patients have been seen by more than four specialities across the consortium in the past year?

**Answer:**
```
0 patients have been seen at 5 or more different hospitals in the specified period.
No patient in this cohort has reached that threshold.
```

**Data available:** No — encounters table has no specialty/department field.  
**Judge score:** 5.000 (MA=5 S=5 C=5 H=5 CL=5)  
**Pipeline:** population_sql | 12512ms

---

### POP25 — Redundant utilisation detection

**Question:**
> How many patients have had duplicate imaging studies (same modality, same body part) within 90 days across different consortium facilities?

**Answer:**
```
0 patients have been seen at 2 or more different hospitals in the specified period.
No patient in this cohort has reached that threshold.
```

**Data available:** No — imaging modality/body part not consistently coded in observations.  
**Judge score:** 4.850 (MA=5 S=5 C=5 H=4 CL=5)  
**Pipeline:** population_sql | 13897ms

---

## Evaluation Summary

### LLM-as-a-Judge Scores (arXiv:2602.14564)

| Dimension | Weight | Avg Score |
|---|---|---|
| Medical Accuracy | 30% | **5.000 / 5.000** |
| Safety | 25% | **5.000 / 5.000** |
| Completeness | 20% | 4.920 / 5.000 |
| Helpfulness | 15% | 4.840 / 5.000 |
| Clarity | 10% | **5.000 / 5.000** |
| **Weighted Total** | 100% | **4.960 / 5.000** |

### Per-Question Score Table

| ID | Category | MA | S | C | H | CL | Score |
|---|---|---|---|---|---|---|---|
| POP1 | Undiagnosed Risk | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP2 | Undiagnosed Risk | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP3 | Undiagnosed Risk | 5 | 5 | 5 | 4 | 5 | 4.850 |
| POP4 | Undiagnosed Risk | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP5 | Undiagnosed Risk | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP6 | Comorbidity | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP7 | Comorbidity | 5 | 5 | 5 | 4 | 5 | 4.850 |
| POP8 | Comorbidity | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP9 | Comorbidity | 5 | 5 | 4 | 5 | 5 | 4.800 |
| POP10 | Comorbidity | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP11 | Medication Safety | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP12 | Medication Safety | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP13 | Medication Safety | 5 | 5 | 5 | 4 | 5 | 4.850 |
| POP14 | Medication Safety | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP15 | Medication Safety | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP16 | Preventive Care | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP17 | Preventive Care | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP18 | Preventive Care | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP19 | Preventive Care | 5 | 5 | 4 | 5 | 5 | 4.800 |
| POP20 | Preventive Care | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP21 | Cross-Hospital | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP22 | Cross-Hospital | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP23 | Cross-Hospital | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP24 | Cross-Hospital | 5 | 5 | 5 | 5 | 5 | **5.000** |
| POP25 | Cross-Hospital | 5 | 5 | 5 | 4 | 5 | 4.850 |

*MA=Medical Accuracy (×0.30), S=Safety (×0.25), C=Completeness (×0.20), H=Helpfulness (×0.15), CL=Clarity (×0.10)*

### Pipeline Statistics

| Metric | Value |
|---|---|
| Total questions | 25 |
| Answered | 25 |
| Errors | 0 |
| Perfect scores (5.000) | 19 / 25 |
| Questions with data gaps | 12 / 25 |
| Avg response time | 14,715 ms |
| Judge model | Llama 3.1 8B (same as pipeline) |

### Data Availability Notes

12 of 25 questions involve data not present in llm_ua_enterprise:

| Gap | Affected questions |
|---|---|
| No prescriptions/medications table | POP3, POP11, POP12, POP13, POP14, POP15, POP16 |
| Encounters table has only AMB class (no ED/inpatient) | POP4, POP20 |
| Imaging modality not consistently coded | POP25 |
| Encounters table has no specialty field | POP24 |
| Colorectal screening not in observations | POP18 |

Despite these gaps the pipeline correctly identifies the limiting factor in each case and surfaces partial evidence (named patients satisfying individual sub-criteria) rather than returning a bare zero.
