# Research Paper Writing Guide
## Clinical Decision Support System using RAG and LLMs

---

## 📋 Paper Structure Overview

### Complete Paper Outline (Your Sections + Professor's Sections)

1. **Title** (Collaborate)
2. **Abstract** (Collaborate - write after all sections)
3. **Introduction** (Professor)
4. **Problem Statement** (Professor)
5. **Literature Review** (You - File 1)
6. **Methodology** (You - File 2)
7. **Results** (You - File 3)
8. **Discussion** (You - File 4 - "Description" you mentioned)
9. **Conclusion** (Collaborate)
10. **References** (Collaborate)
11. **Acknowledgments** (Collaborate)

---

## 🎯 Your Responsibilities (4 Sections)

### 1. Literature Review (`LITERATURE_REVIEW.md`)
- **Purpose:** Review existing work on RAG, LLMs in healthcare, clinical decision support
- **Length:** ~1500-2000 words
- **Key Topics:**
  - Retrieval Augmented Generation (RAG) in healthcare
  - Large Language Models for clinical applications
  - Clinical decision support systems
  - FHIR data integration
  - Semantic search in medical records

### 2. Methodology (`METHODOLOGY.md`)
- **Purpose:** Describe your system architecture, components, and approach
- **Length:** ~2000-2500 words
- **Key Topics:**
  - System architecture
  - RAG pipeline (query processing, retrieval, generation)
  - Intent classification (LLM-based, semantic)
  - Elasticsearch hybrid search
  - Visualization generation
  - Data flow and processing

### 3. Results (`RESULTS.md`)
- **Purpose:** Present evaluation results, performance metrics, case studies
- **Length:** ~1500-2000 words
- **Key Topics:**
  - Query response accuracy
  - Semantic detection effectiveness
  - Chart generation results
  - Case studies with example queries
  - Performance metrics

### 4. Discussion (`DISCUSSION.md`)
- **Purpose:** Interpret results, discuss implications, limitations, future work
- **Length:** ~1500-2000 words
- **Key Topics:**
  - Interpretation of results
  - Clinical implications
  - System strengths and limitations
  - Comparison with existing approaches
  - Future directions

---

## 📸 Screenshot Placement Guide

### Where to Place Screenshots in Your Sections

#### **METHODOLOGY Section:**
1. **System Architecture Diagram** (Figure 1)
   - Overall system flow
   - Components: Frontend, Backend, Elasticsearch, LLM, Database
   - Place after system overview, before detailed components

2. **RAG Pipeline Flow** (Figure 2)
   - Query → Intent → Retrieval → Generation → Response
   - Place in RAG pipeline subsection

3. **Intent Classification Examples** (Figure 3 - Optional)
   - Show example queries and their classified intents
   - Place in intent classification subsection

#### **RESULTS Section:**
1. **Example Query 1: Simple Observation Query** (Figure 4)
   - Query: "What is the patient's heart rate?"
   - Screenshot: Full AI interface showing response + chart
   - Caption: "Simple observation query with automatic chart generation"

2. **Example Query 2: Analysis Query (Semantic)** (Figure 5)
   - Query: "What are the risk values?" (no keyword "abnormal")
   - Screenshot: Response showing abnormal values detection
   - Caption: "Semantic analysis query detection without hardcoded keywords"

3. **Example Query 3: Synthesis Query** (Figure 6)
   - Query: "Summarize the patient's case"
   - Screenshot: Response showing comprehensive overview
   - Caption: "Synthesis query generating comprehensive patient overview"

4. **Example Query 4: Temporal Query** (Figure 7)
   - Query: "How has glucose changed over time?"
   - Screenshot: Response with trend chart
   - Caption: "Temporal query with trend visualization"

5. **Abnormal Values Chart** (Figure 8)
   - Screenshot: Abnormal values visualization
   - Caption: "Automated abnormal values detection and visualization"

6. **Sidebar Summaries** (Figure 9 - Optional)
   - Screenshot: All summary sections (Observations, Conditions, Notes, etc.)
   - Caption: "Automatically generated patient summaries in sidebar"

#### **DISCUSSION Section:**
1. **Comparison Table** (Table 1)
   - Compare your approach vs. traditional keyword-based systems
   - Place in comparison subsection

2. **Performance Metrics** (Table 2 - Optional)
   - Response times, accuracy metrics
   - Place in performance analysis

---

## 📝 Screenshot Requirements for US Publications

### Technical Requirements:
- **Resolution:** Minimum 300 DPI (high quality)
- **Format:** PNG or TIFF (not JPEG for publications)
- **Size:** Fit within paper margins (usually max 6.5" width)
- **Captions:** Descriptive, explain what the figure shows
- **Numbering:** Figure 1, Figure 2, etc. (sequential)

### Content Requirements:
- **Clear and readable:** All text should be legible
- **Professional appearance:** Clean UI, no personal information visible
- **De-identified data:** Ensure no real patient identifiers
- **Consistent styling:** Use same UI state for related screenshots

---

## ✍️ Academic Writing Standards (US Publications)

### General Guidelines:
1. **Third Person:** Use "we", "the system", "the authors" (not "I")
2. **Past Tense:** Write methods and results in past tense
3. **Present Tense:** Use present tense for general statements and conclusions
4. **Active Voice:** Prefer active voice when possible
5. **Precise Language:** Avoid vague terms, be specific

### Citation Format:
- **IEEE format** is common for CS/Engineering papers
- **APA format** is common for Healthcare/Medical papers
- **Check journal requirements** (each journal has specific format)

### Key Phrases to Use:
- "We implemented..." (methodology)
- "The system achieved..." (results)
- "These results demonstrate..." (discussion)
- "Future work could explore..." (discussion)

### Avoid:
- First person singular ("I implemented")
- Casual language ("pretty good", "kind of")
- Claims without evidence
- Overstating results

---

## 📄 File Organization

```
RESEARCH_PAPER/
├── README.md (this file)
├── LITERATURE_REVIEW.md (your section 1)
├── METHODOLOGY.md (your section 2)
├── RESULTS.md (your section 3)
├── DISCUSSION.md (your section 4)
├── FIGURES/
│   ├── figure_1_system_architecture.png
│   ├── figure_2_rag_pipeline.png
│   ├── figure_4_simple_query.png
│   ├── figure_5_analysis_query.png
│   ├── figure_6_synthesis_query.png
│   ├── figure_7_temporal_query.png
│   └── figure_8_abnormal_chart.png
└── TABLES/
    └── table_1_comparison.csv (or .docx)
```

---

## 🔄 Collaboration Workflow

### Step 1: Write Your Sections
1. Write Literature Review (File 1)
2. Write Methodology (File 2)
3. Write Results (File 3)
4. Write Discussion (File 4)

### Step 2: Take Screenshots
- Use the queries from `RESEARCH_PAPER_TEST_QUERIES.md`
- Take high-quality screenshots
- Save with clear naming (figure_X_description.png)
- Add to FIGURES folder

### Step 3: Integrate with Professor's Sections
- Copy your sections into Word document
- Insert figures at appropriate locations
- Ensure consistent formatting
- Add captions and references

### Step 4: Final Review
- Check for consistency
- Verify all figures referenced in text
- Ensure proper citations
- Check journal-specific requirements

---

## 📋 Recommended Test Queries for Screenshots

Based on your `RESEARCH_PAPER_TEST_QUERIES.md`:

1. **Simple Query:** "What is the patient's heart rate?" (Patient 000000500)
2. **Analysis Query:** "What are the risk values?" (Patient 000000500)
3. **Synthesis Query:** "Summarize the patient's case" (Patient 000000500)
4. **Temporal Query:** "How has glucose changed over time?" (Patient 000000500)
5. **Notes Query:** "What is the patient's chief complaint?" (Patient 000001000)
6. **Abnormal Values:** Show abnormal values chart (Patient 000000500)

---

## ❓ Questions to Answer Before Writing

1. **Target Journal?** (This affects format, length, focus)
   - Healthcare Informatics journals?
   - AI/ML in Healthcare?
   - Clinical Decision Support journals?

2. **Paper Length?** (Usually specified by journal)
   - Typical: 8-12 pages for conferences, 10-15 for journals

3. **Evaluation Metrics?** (For Results section)
   - Response accuracy?
   - Response time?
   - User satisfaction? (if you have data)

4. **Baseline Comparison?** (For Discussion)
   - Traditional keyword-based systems?
   - Other RAG implementations?

---

## 🎯 Next Steps

1. **Decide on target journal/conference** (affects format and focus)
2. **Review journal requirements** (format, length, sections)
3. **Take screenshots** using recommended queries
4. **Start writing** with the provided templates
5. **Coordinate with professor** on integration points

---

## 💡 Tips for Master's Level + Professor Collaboration

1. **Write clearly and professionally** - match professor's level
2. **Be thorough in methodology** - show understanding of technical details
3. **Present results objectively** - don't overstate achievements
4. **Acknowledge limitations** - shows critical thinking
5. **Cite recent work** - shows familiarity with current research
6. **Use technical terminology correctly** - shows expertise

---

**Ready to start writing?** Let me know:
1. Target journal/conference (if decided)
2. Any specific requirements from professor
3. Which section to start with first

