# Grouped Visualization Feature

## Overview

The grouped visualization feature automatically organizes all patient observations into clinical categories and generates separate charts for each category with explanatory text.

## Features

### ✅ Automatic Categorization
Observations are automatically grouped into **17 clinical categories**:
1. **Vital Signs** - Heart rate, blood pressure, temperature, oxygen saturation, BMI, etc.
2. **Basic Metabolic Panel** - Glucose, creatinine, electrolytes (Na, K, Cl, CO2), kidney function, etc.
3. **Liver Function Tests** - ALT, AST, alkaline phosphatase, bilirubin, albumin/globulin
4. **Lipid Panel** - Cholesterol (total, HDL, LDL), triglycerides, cholesterol ratios
5. **Complete Blood Count - Red Blood Cells** - RBC, hemoglobin, hematocrit, MCV, MCH, MCHC, RDW
6. **Complete Blood Count - White Blood Cells** - WBC, neutrophils, lymphocytes, monocytes, eosinophils, basophils
7. **Complete Blood Count - Platelets** - Platelet count, platelet mean volume
8. **Hemoglobin & Diabetes Monitoring** - Hemoglobin, HbA1c (glycated hemoglobin)
9. **Kidney Function** - GFR, urea nitrogen/creatinine ratio
10. **Cardiac Markers** - Troponin I (heart attack marker)
11. **Hormones** - TSH (thyroid stimulating hormone)
12. **Coagulation Studies** - INR, coagulation times, heparin
13. **Therapeutic Drug Monitoring** - Vancomycin levels, heparin levels
14. **Enzymes & Metabolic Tests** - Lipase, lactate
15. **Urine Analysis** - pH, specific gravity, urobilinogen
16. **Behavioral Assessments** - PHQ-9, smoking history, social activity
17. **Other Observations** - Any observations not fitting the above categories

### ✅ Smart Explanations

**For Single Values:**
- Shows: `Observation Name: Value Unit`
- Example: `Glucose: 95 mg/dL`

**For Multiple Values:**
- Shows: `Observation Name trends from X to Y Unit`
- Example: `Heart rate trends from 72 to 85 bpm`

**For Multiple Observation Types:**
- Shows: `Category Name: X different measurements with Y total readings`
- Example: `Vital Signs: 5 different measurements with 23 total readings`

### ✅ Separate Charts Per Group

Each clinical category gets its own chart showing:
- All related observations on one graph
- Color-coded by observation type
- Time-series data with dates
- Professional medical styling

---

## Usage

### API Endpoint

```
POST /chat-agent/visualize/grouped?patient_id={patient_id}
```

### Example Request

```bash
curl -X POST "http://localhost:8000/chat-agent/visualize/grouped?patient_id=740"
```

### Example Response

```json
{
  "patient_id": "740",
  "groups": [
    {
      "category": "vital_signs",
      "category_name": "Vital Signs",
      "observation_count": 23,
      "explanation": "Vital Signs: 5 different measurements with 23 total readings",
      "chart_data": {
        "type": "line",
        "data": {
          "labels": ["2025-07-16", "2025-07-17"],
          "datasets": [
            {
              "label": "Heart rate",
              "data": [89, 92],
              "borderColor": "#e74c3c",
              "borderWidth": 2
            },
            {
              "label": "Body temperature",
              "data": [98.6, 98.7],
              "borderColor": "#3498db",
              "borderWidth": 2
            }
          ]
        },
        "options": {
          "responsive": true,
          "plugins": {
            "title": {
              "display": true,
              "text": "Vital Signs - Patient 740"
            }
          }
        }
      }
    },
    {
      "category": "laboratory",
      "category_name": "Laboratory Values",
      "observation_count": 45,
      "explanation": "Laboratory Values: 12 different measurements with 45 total readings",
      "chart_data": { /* chart data */ }
    }
  ]
}
```

---

## Integration with Chat

### Ask the Chat Agent

You can now ask:

1. **"Show me all observations grouped by category"**
2. **"Display observations by type"**
3. **"Visualize all lab values and vital signs separately"**
4. **"Create grouped charts for all patient data"**

The chat agent will:
1. Detect your intent
2. Call the grouped visualization endpoint
3. Return all groups with charts and explanations
4. Display each group in a separate chart in the UI

---

## Clinical Categories (17 Total)

### 1. Vital Signs
- Heart rate / Pulse
- Blood pressure (systolic, diastolic, mean)
- Body temperature
- Respiratory rate
- Oxygen saturation
- Body height, weight, BMI

### 2. Basic Metabolic Panel
- Glucose / Blood sugar
- Creatinine
- Protein, Albumin
- Electrolytes: Sodium, Potassium, Chloride, Carbon dioxide
- Magnesium, Calcium
- Urea nitrogen (BUN)
- Anion gap
- Lactate

### 3. Liver Function Tests
- ALT (Alanine Aminotransferase)
- AST (Aspartate Aminotransferase)
- Alkaline Phosphatase
- Bilirubin (total, non-glucuronidated)
- Albumin/Globulin Ratio

### 4. Lipid Panel
- Cholesterol (total, HDL, LDL)
- Triglycerides
- Cholesterol ratios

### 5. Complete Blood Count - Red Blood Cells
- Red blood cells (RBC / Erythrocytes)
- Hemoglobin
- Hematocrit
- MCV, MCH, MCHC
- Erythrocyte Distribution Width (RDW)

### 6. Complete Blood Count - White Blood Cells
- White blood cells (WBC / Leukocytes)
- Neutrophils (absolute and %)
- Lymphocytes (absolute and %)
- Monocytes (absolute and %)
- Eosinophils (absolute and %)
- Basophils (absolute and %)

### 7. Complete Blood Count - Platelets
- Platelets
- Platelet Mean Volume

### 8. Hemoglobin & Diabetes Monitoring
- Hemoglobin (Hgb)
- Hemoglobin A1C (HbA1c - glycated hemoglobin)
- Hemoglobin A1C/Hemoglobin ratio

### 9. Kidney Function
- GFR (Glomerular Filtration Rate)
- Urea Nitrogen/Creatinine ratio

### 10. Cardiac Markers
- Troponin I (cardiac)
- Used for heart attack detection

### 11. Hormones
- TSH (Thyroid Stimulating Hormone)

### 12. Coagulation Studies
- INR (International Normalized Ratio)
- Coagulation times
- Heparin levels

### 13. Therapeutic Drug Monitoring
- Vancomycin levels (peak)
- Heparin levels

### 14. Enzymes & Metabolic Tests
- Triacylglycerol lipase
- Lactate

### 15. Urine Analysis
- Urine pH
- Specific gravity
- Urobilinogen

### 16. Behavioral Assessments
- Smoking history (pack-years, cigarettes/day)
- PHQ-9 Depression score
- Social activity questions

### 17. Other Observations
- Any observations not fitting the above categories

---

## Benefits

### For Healthcare Providers:
- ✅ **Organized View**: All related observations in one place
- ✅ **Clinical Context**: Grouped by medical categories
- ✅ **Quick Analysis**: See trends at a glance
- ✅ **Easy Comparison**: Related measurements on same chart

### For Patients:
- ✅ **Clear Understanding**: Simple explanations for each group
- ✅ **Visual Trends**: See how values change over time
- ✅ **No Overwhelm**: Separate charts prevent information overload

---

## Technical Details

### Files Created/Modified:

1. **`backend/app/api/observation_grouper.py`** (NEW)
   - Groups observations by clinical category
   - Defines category keywords
   - Generates summaries

2. **`backend/app/api/chat_agent.py`** (MODIFIED)
   - Added `/visualize/grouped` endpoint
   - Added helper functions for chart generation
   - Added explanation generation logic

### Key Functions:

1. `observation_grouper.group_observations()` - Groups observations
2. `create_grouped_visualizations()` - Main endpoint handler
3. `create_group_chart()` - Generates chart data
4. `generate_group_explanation()` - Creates one-line explanations

---

## Future Enhancements

### Planned Features:
- ✅ Support for custom category definitions
- ✅ Ability to compare multiple patients
- ✅ Export grouped visualizations as PDF
- ✅ Interactive drill-down into specific groups
- ✅ AI-generated clinical insights per group

---

## Example Queries

### In Chat:
1. **"Show me all observations"**
   → Returns all observations in separate charts by category

2. **"Visualize vital signs"**
   → Returns just the vital signs chart

3. **"Display lab values with explanations"**
   → Returns lab values chart with descriptive text

4. **"Create grouped charts for patient 740"**
   → Returns all groups with charts and explanations

---

## Testing

### Test the Endpoint:

```bash
# Test with patient 740
curl -X POST "http://localhost:8000/chat-agent/visualize/grouped?patient_id=740"

# Test with another patient
curl -X POST "http://localhost:8000/chat-agent/visualize/grouped?patient_id=741"
```

### Expected Result:
- Returns JSON with patient_id
- Contains "groups" array
- Each group has:
  - category, category_name
  - chart_data (Chart.js format)
  - explanation (one-line text)
  - observation_count

---

## Summary

This feature provides:
- ✅ **Automatic categorization** of observations
- ✅ **Separate charts** for each clinical category
- ✅ **Smart explanations** (single value vs trends vs multiple types)
- ✅ **Clinical organization** by medical category
- ✅ **Easy to understand** for both providers and patients

**Result:** Better visualization, better understanding, better patient care!
