## 4. Results

### 4.1 Evaluation Setup

We conducted a qualitative feasibility evaluation of the proposed retrieval-augmented clinical assistant using longitudinal electronic health record data from three patients. A total of twenty natural language clinician-style queries were issued across these patients, covering a range of information needs including vital sign assessment, condition identification, symptom extraction from clinical notes, trend analysis, and care prioritization.

From these interactions, eight representative queries were selected for detailed analysis, as they best illustrate the system's core capabilities. The evaluation focuses on system behavior, including grounding in patient data, retrieval transparency, temporal reasoning, and automatic visualization, rather than clinical accuracy or outcome prediction.

**Note: This evaluation is intended as a systems-oriented feasibility study and not as a clinical validation.**

### 4.2 Dashboard-Level Interaction Overview

The system provides a clinician-facing dashboard that integrates patient selection, structured data summaries, and a natural language query interface. Clinicians can navigate patient demographics, observations, conditions, clinical notes, and care plans, and issue free-text queries without predefined templates.

AI-generated summaries and responses are presented alongside optional source inspection panels, enabling verification of retrieved evidence. This interface served as the primary interaction surface for evaluating system behavior under realistic clinical workflows.

**(Insert Figure 2 here)**

**Figure 2. Generative AI dashboard integrated within a FHIR-based analytics platform. The interface supports patient selection, section-based navigation, and a natural language chat interface for retrieval-augmented summaries and visualizations.**

### 4.3 Retrieval-Augmented Vital Sign Queries and Trend Analysis

#### 4.3.1 Multi-Document Retrieval and Evidence Aggregation

For each natural language query, the system retrieved multiple relevant documents using the hybrid retrieval-augmented generation (RAG) pipeline. Retrieved documents included structured FHIR observations and conditions as well as unstructured clinical notes spanning multiple encounters and time points.

Rather than relying on a single source, the system aggregated evidence across these retrieved documents to generate responses. This behavior was observed consistently across evaluated queries, including vital sign assessment, condition identification, symptom extraction, and care prioritization. The retrieval process surfaced multiple semantically relevant records, which were internally ranked and passed to the language model as contextual grounding.

Although the system exposes all retrieved documents and relevance scores through the interface, only one or two representative source screenshots are shown in this paper for clarity and space considerations. These screenshots are intended to illustrate retrieval transparency rather than exhaustively enumerate all retrieved evidence.

This design choice reflects standard practice in systems-oriented evaluations, where screenshots serve as representative examples while the full retrieval context is used internally for response generation.

#### 4.3.2 Vital Sign Queries and Trend Visualization

To evaluate grounding and temporal reasoning, we issued vital sign-related queries such as "What is the patient's heart rate?" and "How has the patient's blood pressure responded?". In response, the system accurately retrieved multiple temporally distinct observations encoded using standardized clinical codes and explicitly indicated when more than one relevant measurement was present.

For trend-oriented queries, the system automatically generated time-series visualizations based on semantic intent understanding, recognizing implicit visualization needs without requiring explicit visualization commands such as "show chart" or "visualize". For example, blood pressure queries resulted in retrieval of both systolic and diastolic measurements across encounters and the generation of a corresponding trend chart summarizing the observed decrease between visits.

Retrieved observations were accompanied by structured metadata, including timestamps and standardized codes, enabling transparent verification of the underlying patient data.

**(Insert Figure 3 here)**

**Figure 3. Example of grounded retrieval and automatic visualization for a vital sign query. The system retrieves temporally distinct observations and generates a time-series visualization, while exposing source records for verification.**

### 4.4 Condition Identification and Clinical Reasoning

Binary and summarization-based condition queries were used to assess the system's ability to reason over structured diagnoses and supporting observations. For example, when asked whether a patient had diabetes, the system correctly identified documented diagnoses and supported the response with relevant laboratory measurements.

Broader condition summarization queries (e.g., "Summarize the important medical conditions of this patient in brief") produced comprehensive lists of chronic and acute conditions spanning multiple organ systems. Conditions were grounded in standardized diagnostic codes and linked to underlying source records, demonstrating reliable aggregation without hallucinating unsupported diagnoses.

### 4.5 Symptom Extraction from Unstructured Clinical Notes

Open-ended symptom-related queries (e.g., "What is the patient complaining about?") were used to evaluate retrieval-augmented summarization over unstructured clinical notes. In these cases, the system successfully retrieved relevant encounter notes and extracted patient-reported complaints such as recent falls, pain, infections, and gastrointestinal symptoms.

The system aggregated information across multiple notes and encounters and presented a structured summary of complaints. Count-based note limiting (up to 5 notes for notes-specific queries) preserved full clinical context while preventing computational overload. Source inspection panels enabled verification of extracted content, supporting transparency and explainability.

**(Optional: Insert Figure 4 here or move to Appendix)**

**Figure 4. Retrieval-augmented summarization over unstructured clinical notes. The system extracts patient complaints from multiple encounter notes and provides traceable source evidence.**

### 4.6 Care Prioritization and Abnormality Awareness

Queries focused on care prioritization (e.g., "Give me the important clinical conditions that need special care") prompted the system to surface high-risk and chronic conditions requiring attention. The system's LLM-based semantic intent classifier correctly interpreted these queries without requiring explicit keywords such as "abnormal" or "concerning," demonstrating natural language understanding capabilities.

When relevant laboratory data were present, the system automatically generated abnormal-value visualizations using LLM-based detection, leveraging the LLM's medical knowledge to identify clinically significant deviations from normal ranges rather than relying solely on hardcoded thresholds. This approach enables context-aware interpretation and handling of edge cases (e.g., age-specific ranges, athletic heart rates).

Responses remained descriptive rather than prescriptive, presenting prioritized clinical information without issuing treatment recommendations. This behavior aligns with appropriate clinical decision support boundaries.

### 4.7 Retrieval Transparency and Explainability

Across all evaluated queries, responses were generated from multiple retrieved documents, including both structured records and unstructured clinical notes. Retrieved sources were ranked using hybrid semantic and keyword-based relevance scoring (combining semantic vector similarity with BM25 keyword matching) and made available through the interface for inspection.

Each query response included source attribution displaying retrieved documents with their data type (observations, conditions, notes, encounters), formatted descriptions summarizing key information, and clickable source details. When users clicked on source entries, the system displayed comprehensive source information including display name, standardized codes (LOINC for observations, ICD-10 for conditions), value with unit, recorded date, relevance score (calculated from Elasticsearch's combined semantic and keyword search scores), filename (for notes), and full content for verification.

While only a subset of retrieved sources is illustrated in the figures, all responses were grounded in the full retrieved context. This approach ensures robustness against incomplete or noisy individual records and enables explainable aggregation of evidence across longitudinal patient data.

This source attribution mechanism enabled clinicians to verify the grounding of LLM responses in actual patient data, with relevance scores indicating the strength of match between queries and retrieved documents.

### 4.8 Summary of Findings

Overall, the evaluation demonstrates that the proposed system can:

- Retrieve and summarize longitudinal patient data using natural language queries.

- Understand queries semantically without keyword matching requirements, enabling natural language interaction.

- Integrate structured FHIR data and unstructured clinical notes within a unified retrieval-augmented pipeline.

- Leverage LLM medical knowledge for abnormal value detection, providing context-aware interpretation.

- Automatically generate intent-driven visualizations for trend-based queries without requiring explicit visualization commands.

- Provide transparent source attribution to support verification and explainability, with comprehensive source details including standardized codes, values, dates, and relevance scores.

These results indicate that the system effectively supports clinician-style information needs and serves as a robust foundation for future large-scale and quantitative evaluation.

---

**Word Count**: ~1,250 words (within target range for Results section)
**Ready for copy-paste into research paper**

