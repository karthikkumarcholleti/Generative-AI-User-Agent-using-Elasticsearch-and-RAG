# Clinical Decision Support System - User Guide
## AI-Powered Patient Data Analysis for Healthcare Providers

---

## 📋 What is This System?

This system helps you quickly find and understand patient information by asking questions in plain English. Instead of searching through multiple screens and reports, you can simply ask:

- "What is the patient's creatinine level?"
- "Is the patient diabetic?"
- "Show me all vital signs for this patient"

The system uses artificial intelligence to:
- **Find** the right information from patient records
- **Explain** it in clear, clinical language
- **Show** relevant charts automatically
- **Provide** sources so you can verify the information

---

## 🎯 Key Features

### 1. **Natural Language Queries**
Ask questions the way you would ask a colleague. No need to learn special commands or codes.

**Example Queries:**
- "What is the patient's heart rate?"
- "Give me all vitals available for this patient"
- "What is the patient's respiratory rate?"
- "Is the patient diabetic?"

### 2. **Intelligent Search**
The system understands medical terminology and finds related information:
- "Kidney function" → finds creatinine, GFR, renal function
- "Heart problem" → finds cardiac, cardiovascular, heart disease
- "Blood sugar" → finds glucose, diabetes, A1C

### 3. **Automatic Charts**
When you ask about measurements (like lab values or vital signs), the system automatically creates charts showing:
- **Trends over time** - See how values change
- **All related values** - Complete picture of patient data
- **Only relevant data** - Charts show only what your question is about

### 4. **Source Transparency**
Every answer includes:
- **Source documents** - Where the information came from
- **Relevance scores** - How closely each source matches your question
- **Clickable details** - See full source information

---

## 🔍 How It Works

### Step 1: Ask Your Question
Type your question in natural language, just like talking to a colleague.

**[SCREENSHOT PLACEHOLDER 1: Main chat interface showing query input box]**

### Step 2: System Finds Information
The system searches through patient records using:
- **Keyword matching** - Finds exact terms
- **Semantic search** - Finds related concepts (e.g., "kidney" finds "creatinine")
- **Relevance scoring** - Ranks results by how well they match your question

**[SCREENSHOT PLACEHOLDER 2: RAG sources section showing retrieved documents with scores]**

### Step 3: AI Generates Response
The system creates a clear, clinical answer based on the found information.

**[SCREENSHOT PLACEHOLDER 3: LLM response text with formatted answer]**

### Step 4: Automatic Chart (if applicable)
If your question is about measurements, a chart is automatically generated showing the data over time.

**[SCREENSHOT PLACEHOLDER 4: Generated chart visualization]**

### Step 5: Review Sources
Click on any source to see:
- Full document content
- Date recorded
- Relevance score
- Additional metadata

**[SCREENSHOT PLACEHOLDER 5: Source detail modal showing full source information]**

---

## 📊 Understanding Relevance Scores

Each source document has a **relevance score** showing how well it matches your question:

- **High Score (150-200):** Exact match - directly answers your question
- **Medium Score (50-150):** Related information - relevant but not exact
- **Lower Score (20-50):** Partial match - may contain some relevant information

**Why This Matters:**
- Higher scores = more reliable for your specific question
- You can verify answers by checking high-scoring sources
- Multiple high-scoring sources = stronger evidence

**[SCREENSHOT PLACEHOLDER 6: Sources list showing different relevance scores]**

---

## 💡 Common Use Cases

### Use Case 1: Check a Specific Lab Value
**Question:** "What is the patient's creatinine level?"

**What You Get:**
- Current creatinine value
- Date recorded
- Unit of measurement
- Trend chart showing creatinine over time
- Source documents with relevance scores

**[SCREENSHOT PLACEHOLDER 7: Creatinine query with chart and sources]**

### Use Case 2: Get All Vital Signs
**Question:** "Give me all vitals available for this patient"

**What You Get:**
- Complete list of all vital signs
- Values with dates
- Comprehensive chart showing all vitals together
- Organized by type (heart rate, blood pressure, temperature, etc.)

**[SCREENSHOT PLACEHOLDER 8: All vitals query with comprehensive chart]**

### Use Case 3: Check for a Condition
**Question:** "Is the patient diabetic?"

**What You Get:**
- Condition analysis (diabetes status)
- Related lab values (glucose, A1C if available)
- Charts for related observations
- Source documents from conditions and observations

**[SCREENSHOT PLACEHOLDER 9: Condition query with related charts]**

### Use Case 4: Trend Analysis
**Question:** "How has the patient's heart rate changed?"

**What You Get:**
- Heart rate values over time
- Trend analysis
- Heart rate trend chart
- All recorded heart rate measurements

**[SCREENSHOT PLACEHOLDER 10: Trend analysis query with chart]**

---

## ✅ What Makes This System Reliable

### 1. **Source-Backed Answers**
Every answer comes from actual patient records. You can always check the sources.

### 2. **Relevance Scoring**
The system shows you how well each source matches your question, so you know which information is most relevant.

### 3. **Chart-Answer Alignment**
Charts show exactly the same values mentioned in the answer - no discrepancies.

### 4. **Comprehensive Search**
The system finds related information you might not have thought to search for (e.g., "kidney function" finds creatinine even if you didn't mention it).

---

## 🎨 Understanding the Charts

### Chart Types

1. **Observation Trend Charts**
   - Shows a single measurement over time
   - Example: Creatinine trend, Hemoglobin trend
   - Includes: Values, dates, units

2. **Vital Signs Charts**
   - Shows vital signs over time
   - Example: Heart rate, Blood pressure, Respiratory rate
   - May show multiple related measurements

3. **All Observations Chart**
   - Shows multiple measurements together
   - Useful for comprehensive view
   - Different colors for different measurements

4. **Condition-Related Charts**
   - Automatically generated when asking about conditions
   - Example: Diabetes query → Glucose and A1C charts
   - Shows relevant observations for the condition

### Chart Features
- **Interactive:** Hover to see exact values
- **Time-based:** Shows chronological progression
- **Color-coded:** Different measurements have different colors
- **Accurate:** Values match exactly with the answer text

**[SCREENSHOT PLACEHOLDER 11: Interactive chart with hover tooltip showing values]**

---

## 🔐 Data Security and Privacy

- **Patient-Specific:** All searches are limited to the selected patient
- **Source Tracking:** Every piece of information is traceable to its source
- **No Data Modification:** The system only reads data - never modifies records
- **Audit Trail:** All queries and sources are logged for review

---

## 📱 How to Use

### Getting Started

1. **Select a Patient**
   - Choose patient from the patient list
   - System loads patient data

2. **Ask Your Question**
   - Type your question in natural language
   - Click send or press Enter

3. **Review the Response**
   - Read the AI-generated answer
   - Check the sources (click to see details)
   - Review any generated charts

4. **Ask Follow-Up Questions**
   - Use suggested follow-up questions
   - Or ask your own questions
   - System maintains context

**[SCREENSHOT PLACEHOLDER 12: Complete workflow showing patient selection, query, response, and chart]**

---

## 💬 Tips for Best Results

### ✅ Do:
- Ask specific questions: "What is the patient's creatinine level?"
- Use medical terminology: "heart rate", "blood pressure", "glucose"
- Ask for trends: "How has the creatinine changed?"
- Request comprehensive views: "Show me all vitals"

### ❌ Avoid:
- Very vague questions: "Tell me everything"
- Non-medical questions: "What's the weather?"
- Questions about other patients in the same query

---

## 🎯 Key Benefits for Clinicians

1. **Time Savings**
   - Get answers in seconds instead of searching multiple screens
   - Automatic chart generation saves manual work

2. **Better Insights**
   - System finds related information you might miss
   - Shows trends and patterns automatically

3. **Source Verification**
   - Always know where information came from
   - Can verify any answer by checking sources

4. **Comprehensive View**
   - See all related data together
   - Charts show complete picture at a glance

---

## 📞 Support and Questions

If you have questions about:
- **How to use the system:** Refer to this guide
- **Technical issues:** Contact IT support
- **Data accuracy:** Always verify using source documents
- **Feature requests:** Contact the development team

---

## 📸 Screenshot Placement Guide

### Where to Add Screenshots:

1. **Main Interface (Placeholder 1)**
   - Location: After "Step 1: Ask Your Question"
   - Content: Full browser view showing the chat interface with query input box
   - Highlight: Query input field, patient selection dropdown

2. **RAG Sources (Placeholder 2)**
   - Location: After "Step 2: System Finds Information"
   - Content: Sources section showing retrieved documents with relevance scores
   - Highlight: Multiple sources with different scores visible

3. **LLM Response (Placeholder 3)**
   - Location: After "Step 3: AI Generates Response"
   - Content: Formatted answer text in the chat interface
   - Highlight: Well-formatted clinical answer with numbered lists

4. **Generated Chart (Placeholder 4)**
   - Location: After "Step 4: Automatic Chart"
   - Content: Chart visualization below the answer
   - Highlight: Line chart or bar chart with data points

5. **Source Detail Modal (Placeholder 5)**
   - Location: After "Step 5: Review Sources"
   - Content: Modal popup showing detailed source information
   - Highlight: Full source content, metadata, relevance score

6. **Sources with Scores (Placeholder 6)**
   - Location: After "Understanding Relevance Scores"
   - Content: Sources list showing different score ranges
   - Highlight: Multiple sources with scores like 182.5, 145.3, 89.2

7. **Creatinine Query Example (Placeholder 7)**
   - Location: After "Use Case 1: Check a Specific Lab Value"
   - Content: Complete view of creatinine query with answer, chart, and sources
   - Highlight: Answer mentions creatinine value, chart shows trend, sources visible

8. **All Vitals Query (Placeholder 8)**
   - Location: After "Use Case 2: Get All Vital Signs"
   - Content: All vitals query showing comprehensive list and multi-series chart
   - Highlight: List of all vitals, comprehensive chart with multiple lines

9. **Condition Query (Placeholder 9)**
   - Location: After "Use Case 3: Check for a Condition"
   - Content: Diabetes query showing condition analysis and related charts
   - Highlight: Condition answer, glucose/A1C charts if available

10. **Trend Analysis (Placeholder 10)**
    - Location: After "Use Case 4: Trend Analysis"
    - Content: Heart rate trend query with trend analysis and chart
    - Highlight: Trend description, heart rate chart over time

11. **Interactive Chart (Placeholder 11)**
    - Location: After "Chart Features"
    - Content: Chart with hover tooltip showing exact values
    - Highlight: Mouse hover showing data point values and dates

12. **Complete Workflow (Placeholder 12)**
    - Location: After "How to Use" section
    - Content: Multi-panel view or annotated screenshot showing full workflow
    - Highlight: Patient selection → Query → Response → Chart → Sources

### Screenshot Best Practices:
- Use high-resolution screenshots (at least 1920x1080)
- Annotate important elements with arrows or highlights
- Show realistic patient data (anonymized if needed)
- Include the full context (not just cropped sections)
- Use consistent styling across all screenshots

---

## 📝 Quick Reference

### Common Questions and What to Expect:

| Question Type | What You Get |
|--------------|--------------|
| Specific lab value | Value + date + unit + trend chart |
| All vitals | Complete list + comprehensive chart |
| Condition check | Condition status + related observations + charts |
| Trend analysis | Trend description + trend chart |
| Multiple observations | All values + multi-series chart |

### Chart Types by Query:

| Query Contains | Chart Type Generated |
|----------------|---------------------|
| "creatinine", "hemoglobin" | Observation trend chart |
| "heart rate", "pulse" | Heart rate trend chart |
| "blood pressure", "BP" | Blood pressure trend chart |
| "all vitals", "all observations" | All observations chart |
| "diabetes", "diabetic" | Glucose/A1C charts (if available) |

---

**Document Version:** 1.0  
**Last Updated:** Current Session  
**Target Audience:** Healthcare Providers and Clinicians

