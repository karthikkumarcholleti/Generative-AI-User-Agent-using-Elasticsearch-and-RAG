# 📖 FHIR LLM Dashboard - User Guide

## 🎯 Overview

The FHIR LLM Dashboard is a clinical data analysis system that generates AI-powered summaries of patient data using the Llama 3.1 8B model.

---

## 🚀 Getting Started

### **Access the Dashboard**
1. Start the servers (see SETUP.md)
2. Open your browser to: `http://localhost:5173`
3. Select a patient from the dropdown
4. All summaries generate automatically

---

## 📊 Dashboard Features

### **Patient Selection**
- **Search Box**: Type patient ID or name to filter
- **Dropdown**: Browse all available patients
- **Status Indicator**: Shows "⏳" while generating, then updates to "✓"

### **Clinical Categories**

The dashboard provides 6 types of summaries:

#### **1. Patient Summary** 📋
- Comprehensive overview of all patient data
- Includes demographics, conditions, observations, and notes
- Best for: Complete patient overview

#### **2. Demographics** 👤
- Basic patient information
- Name, age, gender, location
- Best for: Quick patient identification

#### **3. Conditions** 🩺
- Medical conditions and their status
- Active and historical conditions
- Best for: Diagnoses and health status

#### **4. Observations** 📊
- Clinical observations, vitals, and lab results
- Trend analysis over time
- Best for: Monitoring patient health

#### **5. Notes** 📝
- Clinical notes and documentation
- Recent medical records
- Best for: Detailed clinical history

#### **6. Generative AI** 🤖
- AI-powered chat interface
- Ask questions about patient data
- Generate visualizations
- Best for: Interactive analysis

---

## 🤖 Using the AI Features

### **Generative AI Chat**

**Access:**
1. Select a patient
2. Click "Generative AI" in the left sidebar

**Example Questions:**
- "What are the abnormal values for this patient?"
- "What are the trends in vital signs?"
- "Show me the latest lab results"
- "Generate visualizations for glucose levels"
- "What conditions does this patient have?"

**Features:**
- Context-aware responses
- Follow-up suggestions
- Chart generation
- Abnormal value detection

### **Chat Panel (Right Sidebar)**

**Access:**
- Click "💬 Open AI Chat" button in sidebar
- Panel slides out from the right

**Features:**
- General medical help (2-sentence answers)
- Medical terminology explanations
- Normal range information
- Quick question buttons

**Example Questions:**
- "What is normal blood pressure?"
- "What does creatinine mean?"
- "Normal glucose range?"

---

## 📈 Understanding the Summaries

### **Summary Format**

All summaries follow this structure:
```
Introduction about the patient
[Category-specific content]
[Clinical findings]
[Recommendations (if applicable)]
```

### **Example - Patient Summary**
```
**Patient Summary**

[Patient Name] is a [age]-year-old [gender] presenting with...

**Active Conditions:**
1. Diabetes mellitus type 2 - well controlled
2. Hypertension - stable on medication
3. Hyperlipidemia - managed with statin

**Recent Observations:**
- Blood pressure: 128/82 mmHg (2024-12-15)
- Glucose: 142 mg/dL (2024-12-15)
- Heart rate: 72 bpm (2024-12-15)

**Clinical Notes:**
- Recent visit focused on medication adjustments
- Patient reports good compliance
- No adverse effects noted
```

---

## 🔄 Caching System

### **How Caching Works**

1. **First Time**: Selecting a patient generates all summaries (30-60 seconds)
2. **Subsequent Accesses**: Summaries load instantly from cache
3. **Cache Duration**: Until server restart or manual cache clear

### **Cache Management**

**Clear Cache for a Patient:**
```bash
curl -X DELETE "http://localhost:8000/patients/{patient_id}/cache"
```

**Cache is Automatically Cleared:**
- When you select a different patient
- When you refresh the browser and select a new patient
- When backend server restarts

---

## 🎨 UI Tips

### **Patient Search**
- Type patient ID for exact match (highlighted in blue)
- Type patient name for partial matches
- Dropdown auto-expands to show filtered results
- Click outside to collapse

### **Category Navigation**
- Active category is highlighted
- Hover for smooth transition effects
- Click any category to switch instantly
- Status indicator shows generation progress

### **Typing Animation**
- Text types out character-by-character
- Speed: 5ms per character
- Provides visual feedback
- Can be disabled in code (search for `typingSpeed`)

---

## ⚡ Quick Actions

### **Generate All Summaries**
Select any patient → All summaries generate automatically

### **View Specific Category**
Click category in sidebar → Summary displays immediately

### **Ask AI Question**
1. Select patient
2. Click "Generative AI"
3. Type your question
4. Get instant analysis

### **Generate Chart**
1. Go to Generative AI category
2. Ask: "Generate visualizations for [metric]"
3. Chart displays below response

---

## 📱 Features Summary

| Feature | Description | Access |
|---------|-------------|--------|
| **Patient Search** | Filter by ID or name | Search box in sidebar |
| **Batch Generation** | All summaries at once | Automatic on patient select |
| **Smart Caching** | Instant loading | Built-in |
| **AI Chat** | Ask questions | Generative AI category |
| **Charts** | Visualize data | Ask in Generative AI |
| **Status Indicators** | Real-time progress | Category sidebar |
| **Follow-up Options** | Suggested questions | AI responses |
| **Typing Animation** | Visual feedback | Text display |
| **Error Handling** | User-friendly messages | Built-in |
| **Responsive Design** | Mobile-friendly | All devices |

---

## 🧪 Testing the Dashboard

### **Test 1: Patient Selection**
1. Open dashboard
2. Type "740" in search
3. Dropdown shows patient 740
4. Click to select
5. Verify summaries generate

### **Test 2: Category Switching**
1. Select any patient
2. Wait for generation
3. Click "Patient Summary"
4. Click "Conditions"
5. Click "Observations"
6. Verify instant switching

### **Test 3: AI Chat**
1. Select patient
2. Click "Generative AI"
3. Ask: "What are the abnormal values?"
4. Verify response with data
5. Check follow-up options

### **Test 4: Visualization**
1. In Generative AI
2. Ask: "Generate glucose trend chart"
3. Verify chart displays
4. Check chart interactivity

---

## 🆘 Common Issues

### **"Summary temporarily unavailable"**
- **Cause**: GPU memory constraints
- **Solution**: Wait and try again, or refresh page

### **"Generating all summaries..." (stuck)**
- **Cause**: LLM processing time
- **Solution**: Wait 60 seconds, normal for complex patients

### **Chart not displaying**
- **Cause**: JavaScript error
- **Solution**: Check browser console (F12), refresh page

### **Search not working**
- **Cause**: Patient data not loaded
- **Solution**: Check backend is running: `curl http://localhost:8000/health`

---

**Last Updated:** December 19, 2024

