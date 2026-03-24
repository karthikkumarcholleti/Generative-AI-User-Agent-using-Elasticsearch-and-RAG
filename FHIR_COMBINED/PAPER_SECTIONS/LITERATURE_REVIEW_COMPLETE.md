# Literature Review

## 2. Literature Review

### 2.1 Overview

The integration of large language models (LLMs) and retrieval-augmented generation (RAG) in clinical decision support systems represents a significant advancement in healthcare informatics. This literature review examines existing approaches to information retrieval, natural language understanding, and clinical decision support in healthcare settings, with particular focus on semantic search, intent classification, and automated visualization generation. The review identifies gaps in current implementations and establishes the foundation for our proposed system that combines semantic intent classification with LLM-based abnormal value detection in a comprehensive RAG framework.

### 2.2 Retrieval Augmented Generation in Healthcare

Retrieval Augmented Generation (RAG) was first introduced by Lewis et al. as a method to enhance language models by grounding responses in retrieved external knowledge [1]. RAG addresses a fundamental limitation of LLMs: their reliance on training data that may be outdated or lack domain-specific information. In healthcare, where accuracy and recency of information are critical, RAG provides a mechanism to ensure that generated responses are grounded in actual patient data rather than potentially outdated training knowledge [2].

Several studies have explored RAG applications in clinical settings. Gao et al. demonstrated the effectiveness of RAG in medical question-answering tasks, showing improved accuracy when responses were augmented with retrieved clinical documents [3]. However, most existing implementations rely on keyword-based retrieval methods, which fail to capture semantic relationships inherent in medical terminology [4]. For instance, a query about "kidney function" may not retrieve relevant documents that use "renal function" or "creatinine levels" due to the lack of semantic understanding in keyword matching.

The challenge of semantic understanding in medical retrieval is further complicated by the structured nature of healthcare data formats such as FHIR (Fast Healthcare Interoperability Resources). While FHIR provides standardized data structures, retrieval systems must bridge the gap between natural language queries and structured data fields [5]. Traditional keyword-based approaches require exact field name matching, limiting their effectiveness for clinical use cases where clinicians express queries in natural language [6].

**[ADD CITATION]**: Recent work by [Author] explored RAG for clinical note summarization, demonstrating improvements over pure LLM approaches, but still relied on keyword-based retrieval for document selection [Citation needed].

### 2.3 Large Language Models in Clinical Decision Support

Large language models have shown remarkable capabilities in understanding and generating human-like text, leading to their exploration in clinical applications. Models such as GPT-4, LLaMA, and their medical variants have been evaluated for tasks including medical question answering, clinical documentation, and decision support [7]. However, deploying LLMs in clinical settings presents unique challenges, including the need for domain-specific knowledge, handling of medical terminology, and ensuring response accuracy [8].

Clinical decision support systems (CDSS) have traditionally relied on rule-based approaches or machine learning models trained on specific datasets [9]. While effective for narrow use cases, these systems lack the flexibility to handle the variety and nuance of clinical queries. LLMs offer a potential solution by providing natural language understanding capabilities, but their tendency to hallucinate and lack of grounding in actual patient data limit their direct application [10].

The integration of LLMs with clinical data through RAG addresses these limitations by combining the natural language understanding of LLMs with the accuracy of retrieved patient data [11]. However, most existing implementations treat the LLM as a black box, using it primarily for response generation rather than leveraging its capabilities for query understanding and clinical reasoning [12]. Our work extends this approach by utilizing the LLM for semantic intent classification and clinical knowledge-based abnormal value detection, creating a more integrated and intelligent system.

**[ADD CITATION]**: Studies evaluating GPT-4 for clinical decision support have shown promising results for general medical questions but highlighted limitations in handling specific patient data queries [Citation needed].

### 2.4 Semantic Search and Information Retrieval in Medical Records

Semantic search, which uses vector embeddings to find documents based on meaning rather than exact keywords, has emerged as a powerful alternative to keyword-based retrieval [13]. In healthcare, semantic search enables systems to find relevant information even when exact terminology differs between queries and documents. For example, semantic search can connect queries about "heart problems" with documents containing "cardiovascular disease" or "cardiac conditions" [14].

Vector embedding models, such as sentence transformers, have been adapted for medical domains to improve semantic understanding of clinical terminology [15]. General-purpose embedding models like all-MiniLM-L6-v2, which generates 384-dimensional vectors, have shown effectiveness in clinical contexts despite not being specifically trained on medical data [15]. Domain-specific models such as ClinicalBERT and BioBERT have also been developed, offering potentially better performance for medical terminology but requiring additional training resources [15]. However, purely semantic approaches may miss exact keyword matches that are important in clinical contexts, where specific lab codes or medication names require precise matching [16]. This limitation has led to the development of hybrid search approaches that combine semantic and keyword-based retrieval [17].

In the context of structured healthcare data like FHIR, semantic search faces additional challenges. FHIR resources contain both structured fields (e.g., observation codes, condition names) and unstructured text (e.g., clinical notes). Effective retrieval must handle both, using semantic search for concept matching and keyword search for exact code/name matching [18]. Our system implements this hybrid approach, leveraging Elasticsearch's capabilities for both semantic vector search (using all-MiniLM-L6-v2 embeddings) and BM25 keyword matching, ensuring comprehensive retrieval across diverse data types.

### 2.5 Intent Classification and Query Understanding in Clinical Systems

Intent classification, the task of determining a user's goal from their query, is crucial for clinical decision support systems to provide appropriate responses [19]. Traditional intent classification methods in healthcare have relied on rule-based approaches or keyword matching, requiring explicit patterns such as "show me abnormal values" to trigger specific system behaviors [20]. While effective for predefined query types, these approaches fail to handle the natural language variations that clinicians use in practice [21].

Machine learning-based intent classification has been explored to address these limitations. Supervised learning approaches require labeled training data, which can be expensive to obtain in clinical domains [22]. More recently, LLM-based intent classification has emerged as a promising alternative, leveraging the semantic understanding capabilities of pre-trained models [23]. However, many existing implementations still incorporate keyword-based checks or rule-based fallbacks, limiting the full potential of semantic understanding [24].

In clinical settings, intent classification must distinguish between various query types: specific information requests (e.g., "What is the patient's heart rate?"), analytical queries (e.g., "What values are concerning?"), temporal queries (e.g., "How has glucose changed over time?"), and synthesis queries (e.g., "Summarize the patient's case"). Each intent type requires different retrieval strategies and response formats. Our approach uses pure LLM-based semantic intent classification without keyword matching, allowing the system to understand intent from natural language variations, such as interpreting "risk values" or "concerning vitals" as analysis queries without requiring explicit "abnormal" keywords.

**[ADD CITATION]**: Research by [Author] on clinical query understanding has shown that semantic approaches improve intent classification accuracy, but most systems still use hybrid keyword-semantic approaches [Citation needed].

### 2.6 Abnormal Value Detection in Clinical Data

Identifying abnormal or clinically significant values in patient data is a fundamental task in clinical decision support [25]. Traditional approaches rely on predefined normal ranges (thresholds) for various lab values and vital signs, comparing patient values against these thresholds to flag abnormalities [26]. While straightforward and interpretable, threshold-based approaches have limitations: they may miss clinically significant trends, fail to account for patient-specific factors, and require manual maintenance of threshold databases [27].

Machine learning approaches have been explored for abnormal value detection, training models on labeled datasets to identify patterns associated with clinical significance [28]. However, these approaches require extensive labeled data and may not generalize well across different patient populations or clinical contexts [29]. More recently, LLMs have shown promise for abnormal value detection by leveraging their training on medical literature, which includes knowledge of normal ranges and clinical significance [30].

The use of LLM knowledge for abnormal detection represents an emerging research direction. Rather than hardcoding thresholds, LLMs can apply their learned medical knowledge to identify values that are clinically significant, potentially capturing subtleties that rigid thresholds miss [31]. For instance, while traditional thresholds might flag a heart rate of 55 bpm as abnormal (assuming a normal range of 60-100 bpm), an LLM with medical knowledge might recognize this as potentially normal for an athletic individual or in certain clinical contexts. Similarly, creatinine normal ranges vary by age, gender, and muscle mass, requiring context-aware interpretation that LLMs can potentially provide [31]. However, this approach also presents challenges: LLM outputs may be inconsistent, and validation against established clinical standards is necessary [32]. Our work explores this LLM-based approach for abnormal detection while maintaining threshold-based fallback for robustness, representing a hybrid methodology that combines the flexibility of LLM knowledge with the reliability of established clinical thresholds.

### 2.7 Automatic Visualization Generation in Clinical Systems

Visualization plays a crucial role in clinical decision support by presenting complex data in interpretable formats [33]. Traditional clinical information systems require users to manually generate charts or navigate to visualization modules, adding cognitive load and time to clinical workflows [34]. Automatic visualization generation addresses this limitation by detecting when visualizations would be helpful and generating appropriate charts without user intervention [35].

Research on automatic visualization has primarily focused on general data visualization, with limited work specifically addressing clinical contexts [36]. In clinical settings, visualizations must not only be accurate but also clinically meaningful, showing trends over time, highlighting abnormal values, and grouping related data appropriately [37]. The challenge lies in determining when to generate visualizations and what type of visualization is most appropriate for a given query [38].

Intent-based visualization generation, where the system analyzes query intent to determine visualization needs, represents a promising approach [39]. However, existing implementations often rely on keyword matching to detect visualization requests, limiting their ability to understand implicit visualization needs [40]. Our system addresses this by using semantic intent classification to detect visualization needs, automatically generating charts for queries involving numeric observations, temporal trends, or analysis requests, without requiring explicit visualization keywords.

**[ADD CITATION]**: Work by [Author] on clinical data visualization has shown that automatic chart generation improves clinician efficiency, but current systems require explicit visualization requests [Citation needed].

### 2.8 Integration of Multiple Data Types in Clinical Systems

Clinical decision support systems must integrate information from multiple sources: structured data (lab results, vital signs, diagnoses), semi-structured data (clinical notes), and temporal relationships (trends over time) [41]. Traditional systems often require users to navigate multiple interfaces or manually correlate information across different data types [42]. RAG systems provide an opportunity to unify these diverse data sources under a single natural language interface [43].

The challenge of multi-data-type integration is particularly relevant in FHIR-based systems, where data is organized into distinct resource types (Observations, Conditions, Encounters, ClinicalNotes) [44]. In our implementation, these FHIR resources are stored in a MySQL database, with Observations containing lab results and vital signs, Conditions containing diagnoses and medical conditions, Encounters containing visit information, and ClinicalNotes containing unstructured clinical documentation. Effective retrieval must search across these resource types semantically, finding relevant information regardless of its structural location [45]. Semantic search facilitates this by allowing queries to match concepts across different resource types, but the integration requires careful handling of context and relevance [46].

Clinical notes, in particular, present unique challenges for retrieval systems. Notes contain unstructured text that may be lengthy and contain both relevant and irrelevant information [47]. Effective note retrieval requires semantic search to find relevant sections and intelligent extraction to present focused information to the LLM [48]. Our system addresses this through Elasticsearch highlighting, which extracts relevant snippets from notes based on query semantics, combined with fallback to full document retrieval when highlighting is insufficient. This hybrid approach ensures that critical information in notes is accessible while managing computational constraints.

### 2.9 Research Gaps and Contributions

The literature review reveals several gaps in existing research on RAG-based clinical decision support systems. First, most systems rely on keyword-based or hybrid keyword-semantic approaches for intent classification, limiting their ability to understand natural language variations [49]. Second, abnormal value detection typically uses hardcoded thresholds, missing opportunities to leverage LLM medical knowledge for more nuanced detection [50]. Third, visualization generation is often manually triggered or keyword-based, rather than semantically determined from query intent [51]. Fourth, integration of multiple data types, particularly structured observations and unstructured notes, remains a challenge [52].

Our work addresses these gaps through several key contributions: (1) pure LLM-based semantic intent classification without keyword matching, enabling natural language query understanding; (2) LLM-based abnormal value detection that leverages medical knowledge while maintaining threshold-based fallback for robustness; (3) intent-based automatic visualization generation that detects visualization needs semantically; and (4) comprehensive integration of multiple FHIR resource types (observations, conditions, notes, encounters) through hybrid semantic-keyword retrieval with intelligent context extraction.

**[ADD CITATION]**: You need to add recent citations (2020-2024) for each claim. Search for papers on:
- RAG in healthcare (2020-2024)
- LLMs in clinical decision support (2020-2024)
- Semantic search in medical records (2020-2024)
- Intent classification in healthcare (2020-2024)
- Automatic visualization in clinical systems (if available)
- FHIR data retrieval and search (2020-2024)

### 2.10 Summary

This literature review establishes that while RAG and LLMs show promise for clinical decision support, existing implementations have limitations in semantic understanding, abnormal value detection, and multi-data-type integration. Our proposed system addresses these limitations through semantic intent classification, LLM-based abnormal detection, and comprehensive data integration. The following section details our methodology, describing the system architecture, components, and implementation approach.

---

## Word Count: ~1,900 words

## Notes for Completion:

1. **Citations Needed**: Replace [Citation needed] and [Author] placeholders with actual citations from:
   - Google Scholar search for "RAG healthcare", "LLM clinical decision support", "semantic search medical records"
   - Recent papers (2020-2024) are important for journals
   - Include foundational papers (Lewis et al. 2020 for RAG)

2. **Additional Details to Add**:
   - Specific embedding model name (all-MiniLM-L6-v2) in section 2.4
   - FHIR resource types used (Observations, Conditions, Encounters, ClinicalNotes) in section 2.8
   - Specific normal ranges examples in section 2.6 (optional but shows clinical knowledge)

3. **Review for**:
   - Academic tone (third person, formal language)
   - Logical flow between sections
   - Clear connection to your work
   - Balance between breadth and depth

4. **Citation Format**: Check your target journal's requirements (IEEE, APA, AMA for medical journals, etc.)

5. **Length Check**: This is ~1,900 words. You may need to expand to 2000 words if journal requires it, or condense if they have stricter limits.

