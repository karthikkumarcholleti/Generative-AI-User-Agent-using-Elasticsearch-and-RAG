## 🔍 Supported Data Types

### Vitals:
- ✅ Heart Rate / Pulse
- ✅ Blood Pressure (Systolic & Diastolic)
- ✅ Temperature
- ✅ Respiratory Rate
- ✅ Oxygen Saturation

### Laboratory Values:
- ✅ Glucose / Blood Sugar
- ✅ Creatinine
- ✅ Hemoglobin
- ✅ Protein
- ✅ Albumin
- ✅ Sodium
- ✅ Potassium
- ✅ Carbon Dioxide
- ✅ Urea
- ✅ Bilirubin
- ✅ Calcium
- ✅ Cholesterol
- ✅ GFR

### Special Tests:
- ✅ GFR (Glomerular Filtration Rate)
- ✅ Cholesterol
- ✅ Other lab values

---

## 🔄 Generic Observation Detection

### **Auto-Discovery Capability:**

The system can **automatically find and visualize ANY observation type** present in ElasticSearch, even if not explicitly listed above.

**How it works:**

1. **ElasticSearch Search Strategy:**
   - When a specific observation type is requested, the system searches ElasticSearch
   - For recognized types (heart rate, glucose, etc.), it uses specific search patterns
   - For unknown types, it falls back to **generic text search** across observation metadata

2. **Fallback Search (Lines 68-76):**
   ```python
   else:
       # Generic search for other types
       search_queries = [
           {"multi_match": {
               "query": observation_type,
               "fields": ["metadata.display", "content"],
               "type": "best_fields"
           }}
       ]
   ```

3. **What This Means:**
   - ✅ You can request visualization for **any observation type**
   - ✅ The system searches ElasticSearch by the observation name
   - ✅ If found, it extracts and visualizes the data
   - ✅ Works with any medical parameter in your database

4. **Example Unknown Types:**
   - HDL Cholesterol
   - LDL Cholesterol  
   - Triglycerides
   - White Blood Cell Count
   - Red Blood Cell Count
   - Platelet Count
   - BNP (Brain Natriuretic Peptide)
   - C-reactive Protein
   - TSH (Thyroid Stimulating Hormone)
   - Vitamin D levels
   - Hemoglobin A1C
   - INNR (International Normalized Ratio)
   - Any other medical observation in your dataset

5. **How to Use:**
   - In chat: "Show me visualization for [any observation name]"
   - Example: "Generate triglyceride chart"
   - Example: "Visualize BNP levels"
   - Example: "Show me platelet count trends"

**Important:** The generic search uses ElasticSearch `multi_match` across the `display` and `content` fields, so it will find any observation that contains your search term in its name or description.

---

## 📈 Chart Configuration

**Last Updated:** December 19, 2024
**Total Visualization Types:** 7
**Data Source:** ElasticSearch (244,945+ documents)
**Chart Library:** Chart.js
