# Methodology - Copy-Paste Ready Version (Research Paper)

## 3. Methodology

### 3.1 System Architecture Overview

The proposed clinical decision support system is built on a three-tier architecture consisting of a frontend web application, a backend API service, and integrated data processing components. The system integrates multiple technologies to enable semantic query understanding, intelligent information retrieval, and context-aware response generation.

**Figure 1: System Architecture Diagram** (Place diagram here showing: Frontend → Backend API → Data Layer → AI Services)

The frontend is implemented using Next.js (React/TypeScript) and provides a user interface for clinicians to interact with the system through natural language queries. The backend is built using FastAPI (Python 3.x) and serves as the core orchestration layer, managing query processing, data retrieval, and LLM interactions. The data layer consists of MySQL for structured patient data storage and Elasticsearch 8.14.0 for hybrid semantic-keyword search capabilities.

The system employs a Retrieval-Augmented Generation (RAG) architecture where user queries are processed through an intent classification stage, followed by hybrid retrieval from patient data, and finally response generation using a large language model. The entire pipeline is designed to ground responses in actual patient data while leveraging semantic understanding for flexible query interpretation.

### 3.2 Technology Stack

#### 3.2.1 Backend Framework
The backend is implemented using FastAPI, a modern Python web framework that provides asynchronous request handling and automatic API documentation. The API exposes RESTful endpoints for patient data retrieval, query processing, summary generation, and chat interactions. Key backend components include FastAPI application running on port 8001, SQLAlchemy ORM for MySQL interactions, Pydantic models for data validation and serialization, and CORS middleware for cross-origin requests.

#### 3.2.2 Frontend Framework
The frontend is built using Next.js 13+ with React and TypeScript, providing a modern, responsive user interface. Key frontend features include server-side rendering for improved performance, client-side state management using React hooks for real-time UI updates, Axios HTTP client with 15-minute timeout for long-running LLM operations, Recharts visualization library for generating clinical charts, and Framer Motion for smooth UI transitions.

#### 3.2.3 Database and Search Engine
**MySQL Database**: Stores structured patient data in FHIR-compliant format, including patient demographics, observations (laboratory results and vital signs), conditions (diagnoses and medical conditions), encounters (clinical visits and hospitalizations), and clinical notes (unstructured clinical documentation).

**Elasticsearch 8.14.0**: Provides hybrid search capabilities with full-text indexing using BM25 algorithm for keyword-based retrieval, dense vector fields with 384-dimensional embeddings for semantic search, hybrid search that combines semantic and keyword search results, and highlighting that extracts relevant snippets from documents based on query semantics.

#### 3.2.4 Large Language Model
The system uses **Llama 3.1 8B** (Meta), configured with 4-bit quantization via BitsAndBytesConfig for memory efficiency, automatic GPU allocation with fallback strategies, token limits of 800 max new tokens for response generation (configurable by category), temperature of 0.3 for deterministic clinical responses, and a threading-based priority system for query prioritization over background tasks.

#### 3.2.5 Embedding Model
For semantic search, the system employs **all-MiniLM-L6-v2** (sentence-transformers), a lightweight embedding model that generates 384-dimensional vector embeddings, provides fast inference suitable for real-time search, and demonstrates effectiveness in clinical contexts despite not being domain-specific.

### 3.3 Data Sources and Processing

#### 3.3.1 FHIR Data Structure
Patient data is organized according to FHIR (Fast Healthcare Interoperability Resources) standards. The system processes four primary FHIR resource types:

**Observations**: Laboratory results and vital signs, including LOINC codes for standardized identification, numeric values with units, effective dates for temporal tracking, and display names with fallback to LOINC mapper when NULL.

**Conditions**: Medical diagnoses and conditions, including ICD-10 codes for standardized classification, clinical status (active, resolved, etc.), recorded dates, and category-based grouping (Cardiovascular, Respiratory, etc.).

**Clinical Notes**: Unstructured clinical documentation, including full-text clinical narratives, chief complaints, clinical assessments, treatment plans, and source type metadata.

**Encounters**: Clinical visit information, including visit dates, encounter types, and healthcare facility information.

#### 3.3.2 Data Indexing Pipeline
The indexing process transforms raw FHIR data from MySQL into a searchable Elasticsearch index through data extraction using SQLAlchemy ORM, content preparation that combines display names, values, units, and dates into searchable content, embedding generation using all-MiniLM-L6-v2 to create 384-dimensional embeddings, and indexing in Elasticsearch with text fields for BM25 keyword search and dense vector fields for semantic search.

#### 3.3.3 LOINC Code Mapping
To address data quality issues where 28.8% of observations have NULL display names, the system implements a comprehensive LOINC code mapper that maps 50+ common LOINC codes to human-readable names, categorizes observations (laboratory, vital signs, etc.), provides keyword associations for semantic search, and ensures consistent display across the system.

### 3.4 Query Processing Pipeline

#### 3.4.1 Query Input and Preprocessing
User queries are received as natural language text through the frontend interface. The system performs minimal preprocessing, preserving the original query structure to enable semantic understanding. Query validation ensures non-empty input and handles edge cases.

#### 3.4.2 Intent Classification (LLM-Based Semantic Understanding)
**Key Innovation**: The system employs pure LLM-based intent classification without keyword matching, enabling semantic understanding of clinician queries.

The intent classifier uses Llama 3.1 8B with a specialized system prompt to classify queries into one of five intent types: (1) **General**: Direct information requests (e.g., "What is the patient's heart rate?"), (2) **Visualization**: Requests for charts or trends (e.g., "How has glucose changed over time?"), (3) **Analysis**: Queries about abnormal or concerning values (e.g., "What are the risk values that affect this patient?"), (4) **Comparison**: Requests to compare data points, and (5) **Grouped Visualization**: Requests for all observations grouped by category.

The LLM returns a structured JSON response containing intent_type, data_types, wants_all_data, wants_grouped, wants_visualization, specific_observation, parameters, and confidence score. The system interprets queries semantically, such as understanding "risk values that affect this patient" as an analysis intent without requiring explicit "abnormal" keywords.

#### 3.4.3 Hybrid Retrieval Strategy
Once intent is classified, the system performs hybrid retrieval combining semantic and keyword-based search:

**Semantic Search (Vector Similarity)**: The query is converted to a 384-dimensional embedding using all-MiniLM-L6-v2, then k-Nearest Neighbors (kNN) search is performed in Elasticsearch's dense vector field using cosine similarity scoring for relevance ranking.

**Keyword Search (BM25)**: Traditional full-text search using BM25 algorithm with exact term matching for structured identifiers (LOINC codes, medication names), fuzzy matching for typographical variations, and field boosting (metadata.display^3.0, content^2.5, metadata.code^2.0).

**Hybrid Fusion**: Both search methods execute in parallel, results are combined and re-ranked based on semantic similarity scores, BM25 relevance scores, and recency, with top-ranked documents selected based on query intent and data type requirements. Result limiting varies by query type: general queries retrieve top 50 documents, analysis queries retrieve top 15 documents for OOM prevention, and complex queries retrieve top 30 documents with retry logic.

#### 3.4.4 Context Extraction and Highlighting
**Elasticsearch Highlighting**: For retrieved documents, the system uses Elasticsearch highlighting with fragment size of 1000 characters per snippet, 5 snippets per document, sentence-aware fragmenting that preserves sentence boundaries, and unified highlighting algorithm optimized for medical text.

**Smart Note Limiting**: For clinical notes, the system implements intelligent limiting where notes-specific queries include up to 5 notes, general queries include up to 2 notes, and content extraction uses hierarchical semantic extraction with context preservation: first 300 characters for chief complaint and initial context, last 300 characters for diagnosis and conclusion, and middle section containing top N semantically similar sentences (up to 1400 characters), with a total maximum of 2000 characters per note.

**Highlighting Quality Check**: The system includes a fallback mechanism where if more than 50% of notes have content less than 200 characters (indicating poor highlighting), the system re-fetches documents with highlighting disabled and returns full document content for comprehensive context.

**Context Building**: Retrieved documents are grouped by data type and formatted for LLM context, with observations formatted as display name, value, unit, and date; conditions formatted as display name, status, and recorded date; notes as extracted relevant snippets or full content; and metadata including source information, relevance scores, and dates.

### 3.5 Retrieval-Augmented Generation (RAG) Pipeline

#### 3.5.1 Context Assembly
The RAG service assembles retrieved documents into a structured context by grouping documents by data type (observations, conditions, notes, encounters), formatting each document with metadata (date, source, relevance score), ordering documents by date (most recent first) and relevance, and managing context size based on query intent to prevent OOM errors.

#### 3.5.2 LLM Response Generation
The LLM generates responses using a two-prompt system. The system prompt provides instructions for clinical accuracy requirements, source attribution expectations, response format guidelines, medical knowledge application, and natural understanding of abnormal values without explicit filtering rules. The user prompt contains the original user query, formatted context from retrieved documents, patient identification, and query-specific instructions based on intent.

Generation parameters include max tokens of 800 (configurable by category: intent=200, compression=2000), temperature of 0.3 for deterministic clinical responses, top-p of 0.9 for nucleus sampling, and priority system where queries have higher priority than background summary generation.

#### 3.5.3 Source Attribution
Each response includes source attribution with source documents and relevance scores, clickable source details, full document content on demand, and date and metadata for verification.

### 3.6 Abnormal Value Detection

#### 3.6.1 LLM-Based Detection
The system implements a research-grade approach using LLM medical knowledge for abnormal value detection. The LLMAbnormalDetector module formats observations for LLM analysis, uses the LLM's medical training to identify abnormal values, applies clinical reference ranges from the LLM's knowledge base, and returns structured JSON with observation name and code, value and unit, date, and reasoning for abnormality. Advantages include no hardcoded thresholds required, context-aware interpretation, handling of edge cases (e.g., athletic heart rates, age-specific ranges), and leveraging the LLM's exposure to medical literature.

#### 3.6.2 Threshold-Based Fallback
For robustness and comparison, the system maintains threshold-based detection with hardcoded reference ranges for 24 common lab values including vital signs (heart rate 60-100 bpm, blood pressure SBP 90-120/DBP 60-80, temperature 36.1-37.2°C) and laboratory values (glucose 70-100 mg/dL, creatinine 0.6-1.2 mg/dL, hemoglobin 12-16 g/dL). Fallback logic ensures that if LLM detection fails or returns no results, the system uses threshold-based detection to ensure no abnormal values are missed and provides consistent, interpretable results. The hybrid approach allows the system to use either method, with research mode using LLM-based detection and production mode using threshold-based detection for speed and reliability.

### 3.7 Intent-Driven Automatic Visualization

#### 3.7.1 Visualization Detection
The system automatically determines when to generate visualizations based on intent type (visualization, analysis, or grouped_visualization intents trigger charts), retrieved data (numeric observations in retrieved data), and query semantics (implicit visualization needs such as "trend", "over time", "how has"). Visualization generation is triggered semantically, not through keyword detection.

#### 3.7.2 Chart Generation
The Intelligent Visualization Service scans retrieved data for numeric observations and generates appropriate charts. Chart types include single observation trends (line charts for individual observations over time), abnormal values charts (grouped bar charts showing abnormal values with normal range indicators), grouped observations (categorized charts showing observations by clinical category), and vital signs vs. lab values (separate charts for different observation types).

Chart data is generated directly from database queries, bypassing LLM context limitations to ensure accuracy and completeness, prevent data loss from context truncation, and enable comprehensive visualization even when LLM response is truncated. The frontend uses Recharts for rendering responsive charts, interactive tooltips, color-coded categories, and normal range indicators for abnormal values charts.

### 3.8 GPU Memory Management

#### 3.8.1 Model Loading Strategy
The LLM is loaded with 4-bit quantization using BitsAndBytesConfig with initial strategy of device_map="auto" for automatic GPU allocation, and fallback strategy where if GPU memory error occurs, multi-GPU systems use device_map="balanced" (split across GPUs) and single GPU systems use device_map={"": 0} (all layers on GPU 0). CPU offloading is prevented as 4-bit quantization does not support CPU offloading.

#### 3.8.2 Memory Clearing
The system implements aggressive GPU memory management with torch.cuda.empty_cache() and gc.collect() called after each generation, progressive token reduction where if GPU memory exceeds 90%, max tokens are reduced to 150, and error handling that catches torch.cuda.OutOfMemoryError and returns informative messages.

#### 3.8.3 Priority System
A threading-based priority system ensures queries are not blocked by background tasks using threading lock (_gen_lock) to serialize LLM generation, condition variable (_query_waiting) to manage priority queue, query priority where queries skip ahead of summary generation, summary generation running in background with lower priority, and GPU cleanup ensuring clean GPU state before releasing priority.

### 3.9 Frontend Integration

#### 3.9.1 Real-Time Updates
The frontend provides real-time updates for summary generation progress, query processing status, chart rendering, and source document display.

#### 3.9.2 State Management
React hooks manage application state including patient selection, active section (summaries, chat, etc.), chat message history, minimized/maximized states, and LocalStorage persistence for session restoration.

#### 3.9.3 User Experience Features
The system includes auto-selection prevention (no auto-selection on fresh page load, waits for user selection), session restoration (restores previous session if summaries were already generated), notification system with visual indicators for minimized sections, timeout handling with 15-minute timeout for long-running LLM operations, and error handling with graceful error messages and retry mechanisms.

### 3.10 Implementation Details

#### 3.10.1 Error Handling and Robustness
The system implements retry logic where OOM errors trigger retry with reduced context (top 30 documents, 30 observations), multiple fallback layers (LLM → keyword, highlighting → full documents), input validation at API boundaries, and comprehensive logging for debugging and monitoring.

#### 3.10.2 Performance Optimizations
Performance optimizations include summary cache for recently accessed patients (max 3 patients), batch processing for embedding generation (32 texts per batch), connection pooling for database and Elasticsearch connection reuse, and async operations with non-blocking API endpoints for concurrent requests.

#### 3.10.3 Security and Privacy
Security measures include configurable CORS for development and production, query validation and sanitization, no sensitive data in error responses, and local deployment where all processing occurs locally with no external API calls for patient data.

---

**Word Count**: ~2,400 words  
**Target**: 2000-2500 words ✅  
**Ready for copy-paste into research paper**

---

## 📝 Notes:
- **Figure 1**: Reference the detailed diagram specifications in `FIGURE_1_ARCHITECTURE_DIAGRAM.md`
- **Citations**: Add citations where you reference related work or methodologies
- **Technical Details**: All technical specifications match your actual implementation

