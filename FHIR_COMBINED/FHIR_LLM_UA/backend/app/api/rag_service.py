# backend/app/api/rag_service.py

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from .elasticsearch_client import es_client
from .intelligent_visualization import intelligent_viz_service
from .intent_classifier import intent_classifier
from ..core.llm import generate_chat
import logging
from datetime import datetime

# =============================================================================
# MEDRAG TOGGLE — Switch between Standard RAG and MedRAG + KG pipeline
# =============================================================================
# Reference: "MedRAG: Enhancing Retrieval-augmented Generation with Knowledge
#             Graph-Elicited Reasoning for Healthcare Copilot"
#             Zhao et al., ACM WWW 2025 — https://dl.acm.org/doi/10.1145/3696410.3714782
#
# USE_MEDRAG = True  → Run MedRAG pipeline (KG-augmented, differential diagnosis)
# USE_MEDRAG = False → Run Standard RAG pipeline (Elasticsearch only, no KG)
#
# Set at startup via environment variable:
#   USE_MEDRAG=true  uvicorn app.main:app ...   → MedRAG mode
#   USE_MEDRAG=false uvicorn app.main:app ...   → Standard RAG mode
#
# Switch at runtime (no restart) via:
#   POST /compare/set-mode  {"use_medrag": true/false}
# =============================================================================
import os as _os
USE_MEDRAG = _os.environ.get("USE_MEDRAG", "true").strip().lower() != "false"

def set_use_medrag(enabled: bool) -> None:
    """Runtime toggle for the MedRAG pipeline (no restart required).
    Called by the /compare/set-mode API endpoint during A/B comparison runs."""
    global USE_MEDRAG
    USE_MEDRAG = enabled
    logger_name = "rag_service"
    import logging as _logging
    _logging.getLogger(logger_name).info(
        "Pipeline mode changed → %s",
        "MedRAG + KG" if enabled else "Standard RAG"
    )

from .medrag_knowledge_graph import kg_service  # MedRAG KG singleton

logger = logging.getLogger(__name__)

# DDx intent keywords — exported for the debug endpoint
DDX_INTENT_KEYWORDS = [
    "differential diagnosis", "differential", "ddx",
    "most likely diagnosis", "what is the diagnosis",
    "possible diagnos", "probable diagnos",
    "what could this be", "what conditions could",
    "overall assessment", "clinical assessment",
    "clinical summary",
    "health status",
    "signs of cardiovascular", "signs of kidney", "signs of diabetes",
    "signs of heart", "signs of liver", "signs of infection",
    "evidence of", "risk of", "risk for",
    "show signs of", "does this patient",
]

VALUE_LOOKUP_OVERRIDES = [
    "what do the", "what does the",
    "what do ", "what does ",
    "tell me the", "show me the",
    "list the", "give me the",
    "what are the values", "what are the levels",
    "what are the results", "what are the readings",
    "how high is", "how low is",
    "how does", "compare",
    "normal range for", "reference range for",
]

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GRAY = '\033[90m'

def log_section(title: str, color: str = Colors.CYAN):
    """Print a formatted section header"""
    print(f"\n{color}{'='*80}{Colors.ENDC}")
    print(f"{color}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{color}{'='*80}{Colors.ENDC}\n")

def log_info(label: str, value: Any, color: str = Colors.BLUE):
    """Print formatted info line"""
    print(f"{color}{Colors.BOLD}{label:.<30}{Colors.ENDC} {value}")

def log_data(label: str, data: Any, color: str = Colors.GREEN):
    """Print formatted data line"""
    print(f"{color}  {label}:{Colors.ENDC} {data}")

# ── Unit normalization for RAG context text ───────────────────────────────────
# Converts non-standard units to canonical clinical units so the LLM never
# sees mixed representations of the same measurement in the same context
# (e.g. glucose 5.0 mmol/L alongside glucose 90 mg/dL).
# Mirrors the UNIT_CONVERSIONS table in visualization_service.py.
_CONTEXT_UNIT_CONVERSIONS: Dict[str, Dict[str, Any]] = {
    "glucose":      {"mmol/l": {"factor": 18.018, "target": "mg/dL"}},
    "creatinine":   {
        "µmol/l":  {"factor": 0.01131, "target": "mg/dL"},
        "μmol/l":  {"factor": 0.01131, "target": "mg/dL"},
        "umol/l":  {"factor": 0.01131, "target": "mg/dL"},
        "micromol/l": {"factor": 0.01131, "target": "mg/dL"},
    },
    "urea nitrogen": {"mmol/l": {"factor": 2.801, "target": "mg/dL"}},
    "bun":           {"mmol/l": {"factor": 2.801, "target": "mg/dL"}},
    "cholesterol":   {"mmol/l": {"factor": 38.67, "target": "mg/dL"}},
    "ldl":           {"mmol/l": {"factor": 38.67, "target": "mg/dL"}},
    "hdl":           {"mmol/l": {"factor": 38.67, "target": "mg/dL"}},
    "triglycerides": {"mmol/l": {"factor": 88.57, "target": "mg/dL"}},
    "hemoglobin":    {
        "g/l":    {"factor": 0.1,    "target": "g/dL"},
        "mmol/l": {"factor": 1.6113, "target": "g/dL"},
    },
    "calcium":  {"mmol/l": {"factor": 4.008, "target": "mg/dL"}},
    "sodium":   {"mmol/l": {"factor": 1.0,   "target": "mEq/L"}},
    "potassium": {"mmol/l": {"factor": 1.0,  "target": "mEq/L"}},
}

def _normalize_context_value(display: str, value: float, unit: str) -> Tuple[float, str]:
    """Return (normalized_value, canonical_unit) for a RAG context observation.
    If no conversion applies, returns (value, unit) unchanged."""
    disp_l = display.lower()
    unit_l = (unit or "").lower().strip()
    for obs_key, unit_map in _CONTEXT_UNIT_CONVERSIONS.items():
        if obs_key in disp_l:
            if unit_l in unit_map:
                rule = unit_map[unit_l]
                return round(value * rule["factor"], 2), rule["target"]
            break  # matched obs type but unit is already canonical — stop
    return value, unit


class RAGService:
    """Retrieval Augmented Generation service for chat agent"""
    
    def __init__(self):
        self.es_client = es_client
        self.conversation_context = {}  # Store conversation context per patient
        self.source_storage = {}  # Store detailed source information by source_id
    
    def _determine_is_notes_query(self, query: str, intent: Dict[str, Any], retrieved_data: List[Dict[str, Any]]) -> bool:
        """
        Intelligently determine if query is about notes using semantic understanding.
        Uses intent classifier + semantic search results, not hardcoded keywords.
        Research-grade approach.
        """
        # Method 1: Check intent type (LLM-based, semantic)
        if intent.get("type") == "notes":
            return True
        
        # Method 2: Check data_types (LLM-based, semantic)
        if "notes" in intent.get("data_types", []):
            return True
        
        # Method 3: Check semantic search results (intelligent detection)
        if retrieved_data:
            notes_count = sum(1 for item in retrieved_data if item.get("data_type") == "notes")
            total_count = len(retrieved_data)
            
            # If >50% of results are notes, it's likely a notes query
            if total_count > 0 and notes_count / total_count > 0.5:
                return True
        
        # Default: Not a notes query
        return False
    
    def _extract_relevant_parts_from_note(self, note_content: str, query: str, query_embedding: List[float], max_chars: int = 2000) -> str:
        """
        Research-Grade Note Extraction: Hierarchical Semantic Extraction with Context Preservation.
        
        Strategy (Data Science Approach):
        1. Preserve Context: First 300 chars (chief complaint, initial context) + Last 300 chars (diagnosis, conclusion)
        2. Semantic Extraction: Extract top N semantically similar sentences from middle section (up to 1400 chars)
        3. Combine: Context + Semantic extraction = Complete, relevant information (max 2000 chars)
        
        This ensures:
        - No data loss (critical sections always included)
        - Most relevant information extracted (semantic similarity)
        - OOM prevention (2000 chars max per note)
        - Research-grade quality
        """
        if not note_content:
            return ""
        
        # If note is already short, return as-is
        if len(note_content) <= max_chars:
            return note_content
        
        # Step 1: Preserve critical context (always include)
        CONTEXT_SIZE = 300  # First and last 300 chars for context
        first_context = note_content[:CONTEXT_SIZE]  # Chief complaint, initial assessment
        last_context = note_content[-CONTEXT_SIZE:]  # Diagnosis, disposition, plan
        
        # Calculate available space for semantic extraction
        available_for_semantic = max_chars - (CONTEXT_SIZE * 2)  # 2000 - 600 = 1400 chars
        
        # Step 2: Extract middle section for semantic analysis
        middle_section = note_content[CONTEXT_SIZE:-CONTEXT_SIZE] if len(note_content) > (CONTEXT_SIZE * 2) else ""
        
        # If middle section is small, just combine context
        if len(middle_section) <= available_for_semantic:
            return f"{first_context}{middle_section}{last_context}"[:max_chars]
        
        # Step 3: Semantic extraction from middle section (if embeddings available)
        if query_embedding:
            try:
                from .embedding_service import EmbeddingService
                import numpy as np
                
                embedding_service = EmbeddingService()
                if embedding_service.is_available():
                    # Split middle section into sentences
                    sentences = re.split(r'[.!?]\s+', middle_section)
                    sentences = [s.strip() for s in sentences if s.strip()]
                    
                    if sentences:
                        # Generate embeddings for each sentence
                        sentence_embeddings = []
                        for sentence in sentences:
                            try:
                                embedding = embedding_service.generate_embedding(sentence)
                                sentence_embeddings.append(embedding)
                            except Exception:
                                sentence_embeddings.append(None)
                        
                        # Calculate similarity with query
                        similarities = []
                        query_embedding_np = np.array(query_embedding)
                        for embedding in sentence_embeddings:
                            if embedding is not None:
                                embedding_np = np.array(embedding)
                                # Cosine similarity
                                similarity = np.dot(query_embedding_np, embedding_np) / (
                                    np.linalg.norm(query_embedding_np) * np.linalg.norm(embedding_np)
                                )
                                similarities.append(similarity)
                            else:
                                similarities.append(0.0)
                        
                        # Get top sentences (sorted by similarity)
                        top_sentences = sorted(
                            zip(sentences, similarities),
                            key=lambda x: x[1],
                            reverse=True
                        )
                        
                        # Extract top sentences up to available_for_semantic chars
                        extracted_middle = []
                        total_chars = 0
                        for sentence, similarity in top_sentences:
                            if total_chars + len(sentence) <= available_for_semantic:
                                extracted_middle.append(sentence)
                                total_chars += len(sentence)
                            else:
                                break
                        
                        # Combine: Context + Semantic extraction + Conclusion
                        if extracted_middle:
                            middle_text = " ... ".join(extracted_middle)
                            result = f"{first_context} ... {middle_text} ... {last_context}"
                            return result[:max_chars]  # Final safety limit
            except Exception as e:
                logger.warning(f"Semantic extraction failed: {e}. Using context + middle section.")
        
        # Fallback: Use context + first part of middle section
        # This ensures we always preserve context even if semantic extraction fails
        remaining_space = available_for_semantic
        middle_text = middle_section[:remaining_space] if remaining_space > 0 else ""
        result = f"{first_context} ... {middle_text} ... {last_context}"
        return result[:max_chars]  # Final safety limit
    
    def _check_highlighting_quality(self, retrieved_data: List[Dict[str, Any]], original_query: str = "") -> bool:
        """
        Check if highlighting worked well or if we should fallback to full documents.
        
        Highlighting might fail if:
        1. No highlights found (Elasticsearch couldn't find keyword matches)
           - Already handled in elasticsearch_client.py (falls back to full content automatically)
        2. Highlights are too short (insufficient information)
           - Notes with content < 200 chars likely means highlighting found very little
        3. Highlights are missing for important documents
           - If semantic search found documents but highlighting found nothing
        4. Highlights don't match query intent
           - Hard to detect, but very short highlights suggest this
        
        Detection Strategy:
        - Check if notes have very short content (< 200 chars) - suggests highlighting found little
        - Check if we have notes but all have very short content - suggests highlighting failed
        - For observations/conditions: They're naturally short, so short content is OK
        
        Args:
            retrieved_data: List of retrieved documents with content from highlighting
            original_query: Original user query (for potential future use)
            
        Returns:
            True if highlighting worked well, False if we should use full documents (fallback)
        """
        if not retrieved_data:
            return True  # No data, can't check quality
        
        # Focus on notes (they're the long documents where highlighting matters)
        notes_with_short_content = 0
        total_notes = 0
        
        for item in retrieved_data:
            if item.get("data_type") == "notes":
                total_notes += 1
                content = item.get("content", "")
                
                # Detection Logic:
                # Full notes are usually 1000+ characters
                # If highlighting worked, we should get 500-2000 chars (multiple snippets)
                # If highlighting failed, we might get:
                #   - < 200 chars (very short snippets or no highlights)
                #   - Full content (elasticsearch_client already fell back)
                
                # If note content is very short (< 200 chars), highlighting likely found very little
                # This could mean:
                # 1. No keyword matches found (highlighting returned empty, fell back to full but full was also short - unlikely)
                # 2. Only tiny snippets found (highlighting worked but found minimal matches)
                # 3. Document itself is short (unlikely for notes, but possible)
                
                if len(content) < 200:
                    notes_with_short_content += 1
        
        # Decision Logic:
        # If we have notes and >50% have very short content, highlighting likely failed
        # This suggests highlighting couldn't find good matches
        if total_notes > 0:
            short_content_ratio = notes_with_short_content / total_notes
            
            if short_content_ratio > 0.5:
                logger.warning(
                    f"Highlighting quality check FAILED: {notes_with_short_content}/{total_notes} notes "
                    f"({short_content_ratio*100:.1f}%) have very short content (< 200 chars). "
                    f"This suggests highlighting found insufficient matches. Falling back to full documents."
                )
                return False
            else:
                logger.info(
                    f"Highlighting quality check PASSED: {total_notes - notes_with_short_content}/{total_notes} notes "
                    f"have sufficient content. Highlighting appears to have worked."
                )
        
        # Highlighting seems to have worked
        return True
    
    def _get_full_documents_fallback(self, patient_id: str, query: str, intent: Dict[str, Any], retrieved_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback method: Get full documents instead of highlighted snippets.
        This is the old method (before highlighting) where LLM gets full documents.
        
        Args:
            patient_id: Patient ID
            query: User query
            intent: Intent classification
            retrieved_data: Current retrieved data (with highlights)
            
        Returns:
            List of documents with full content (old method)
        """
        logger.info("Fallback: Using full documents (old method before highlighting)")
        
        # Get document IDs from current retrieval
        doc_ids = []
        for item in retrieved_data:
            # Try to identify documents by content hash or metadata
            metadata = item.get("metadata", {})
            data_type = item.get("data_type", "")
            # We'll re-fetch with full content
        
        # Re-fetch from Elasticsearch WITHOUT highlighting (get full content - old method)
        # This is the fallback: use full documents like before highlighting was implemented
        full_results = self.es_client.search_patient_data(
            patient_id=patient_id,
            query=query,  # Keep same query
            data_types=intent.get("data_types") if intent.get("data_types") else None,
            use_highlighting=False  # Disable highlighting to get full content
        )
        
        if full_results:
            logger.info(f"Fallback: Retrieved {len(full_results)} full documents (old method)")
            return full_results
        else:
            logger.warning("Fallback: No full documents retrieved, using original data")
            return retrieved_data
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine intent and required data types.
        Uses LLM-based intent classification for robust, research-worthy detection.
        """
        log_section("INTENT CLASSIFICATION", Colors.CYAN)
        log_info("Query", query, Colors.BLUE)
        
        # Use LLM-based intent classifier
        llm_intent = intent_classifier.classify_intent(query)
        
        log_info("Intent Type", llm_intent.get("intent_type", "unknown"), Colors.GREEN)
        log_info("Data Types", ", ".join(llm_intent.get("data_types", [])), Colors.GREEN)
        log_info("Wants All Data", str(llm_intent.get("wants_all_data", False)), Colors.GREEN)
        log_info("Wants Grouped", str(llm_intent.get("wants_grouped", False)), Colors.GREEN)
        log_info("Wants Visualization", str(llm_intent.get("wants_visualization", False)), Colors.GREEN)
        log_info("Confidence", f"{llm_intent.get('confidence', 0.0):.2f}", Colors.GREEN)
        
        # Convert LLM intent format to legacy format for compatibility
        intent = {
            "type": llm_intent.get("intent_type", "general"),
            "data_types": llm_intent.get("data_types", []),
            "parameters": llm_intent.get("parameters", []),
            "follow_up_needed": llm_intent.get("follow_up_needed", False),
            "follow_up_options": llm_intent.get("follow_up_options", []),
            # Add new fields for enhanced functionality
            "wants_all_data": llm_intent.get("wants_all_data", False),
            "wants_grouped": llm_intent.get("wants_grouped", False),
            "wants_visualization": llm_intent.get("wants_visualization", False),
            "specific_observation": llm_intent.get("specific_observation", "none"),
            "confidence": llm_intent.get("confidence", 0.5)
        }
        
        # Map LLM data types to system data types
        # LLM may return categories like "vital signs", "lab values" - map to actual data types
        data_type_mapping = {
            "vital signs": "observations",
            "lab values": "observations",
            "lab results": "observations",
            "test results": "observations",
            "medical conditions": "conditions",
            "diagnoses": "conditions",
            "diseases": "conditions",
            "clinical notes": "notes",
            "notes": "notes",
            "demographics": "demographics",
            "patient info": "demographics"
        }
        
        # Map data types
        mapped_data_types = []
        for dt in intent["data_types"]:
            # Check if it's already a valid system data type
            if dt in ["observations", "conditions", "notes", "demographics"]:
                mapped_data_types.append(dt)
            # Otherwise, try to map it
            elif dt.lower() in data_type_mapping:
                mapped_type = data_type_mapping[dt.lower()]
                if mapped_type not in mapped_data_types:
                    mapped_data_types.append(mapped_type)
            # If specific observation is mentioned, it's likely observations
            elif intent.get("specific_observation") != "none":
                if "observations" not in mapped_data_types:
                    mapped_data_types.append("observations")
        
        intent["data_types"] = mapped_data_types if mapped_data_types else intent["data_types"]
        
        # Handle grouped visualization detection
        if intent["wants_all_data"] and intent["wants_grouped"]:
            intent["type"] = "grouped_visualization"
            intent["parameters"].append("all_observations")
            intent["parameters"].append("grouped_visualization")
        
        # If no specific data types identified, use all
        if not intent["data_types"]:
            intent["data_types"] = ["demographics", "conditions", "observations", "notes"]
        
        log_data("Final Intent", intent, Colors.CYAN)
        
        return intent
    
    def retrieve_relevant_data(self, patient_id: str, query: str, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve relevant patient data using ElasticSearch"""
        if not self.es_client.is_connected():
            print(f"{Colors.RED}✗ ElasticSearch not connected, using fallback{Colors.ENDC}")
            logger.warning("ElasticSearch not connected, using fallback")
            return []
        
        try:
            # Use semantic search for all queries - no hard-coding needed!
            # Semantic search with embeddings automatically finds related concepts across all data types
            # This handles conditions, observations, encounters, notes, and all other data types
            
            # For condition-related queries, prioritize conditions but search all types
            # Semantic search will find related information automatically
            data_types = intent.get("data_types", [])
            query_lower = query.lower()
            
            # If query is about a condition, prioritize conditions but search all types
            # Semantic search will find related observations, notes, encounters automatically
            if data_types and "conditions" in data_types:
                log_info("Search Strategy", f"Prioritizing conditions, but searching all data types via semantic search")
                # Search all types - semantic search will find related info
                # First search with condition priority, then comprehensive search
                results = self.es_client.search_patient_data(
                    patient_id=patient_id,
                    query=query,
                    data_types=["conditions"]  # Start with conditions
                )
                
                # Then do comprehensive search across all types
                # Semantic search will automatically find related observations, notes, encounters
                all_results = self.es_client.search_patient_data(
                    patient_id=patient_id,
                    query=query,
                    data_types=None  # Search all types: conditions, observations, encounters, notes, demographics
                )
                
                # Combine results, prioritizing conditions but including all related data
                if all_results:
                    existing_ids = set()
                    for r in results:
                        content = r.get("content", "")
                        data_type = r.get("data_type", "")
                        existing_ids.add(f"{data_type}:{content[:50]}")
                    
                    # Add all related results from other data types
                    for r in all_results:
                        content = r.get("content", "")
                        data_type = r.get("data_type", "")
                        result_id = f"{data_type}:{content[:50]}"
                        if result_id not in existing_ids:
                            results.append(r)
                            existing_ids.add(result_id)
            else:
                # For non-condition queries, search all data types
                if data_types:
                    log_info("Search Strategy", f"Filtered search for: {', '.join(data_types)}")
                else:
                    log_info("Search Strategy", "Comprehensive search across all data types (semantic search enabled)")
                
                log_info("ElasticSearch Query", query if query else "(empty - retrieving all patient data)")
                print()
                
                results = self.es_client.search_patient_data(
                    patient_id=patient_id,
                    query=query,
                    data_types=intent["data_types"] if intent.get("data_types") else None
                )
            
            if results:
                log_info("Initial Results", f"✓ Found {len(results)} documents")
            else:
                log_info("Initial Results", "✗ No results - trying comprehensive search across all data types...")
            
            # Comprehensive multi-source retrieval: Get ALL related information
            # Semantic search automatically finds related concepts across all data types
            # Search across all data types: conditions, observations, encounters, notes, demographics
            if not results or len(results) < 10:  # If few results, search more comprehensively
                log_info("Comprehensive Search Strategy", "Searching ALL data types (conditions, observations, encounters, notes, demographics) via semantic search")
                
                # Search all data types without filter - semantic search will find related info
                all_results = self.es_client.search_patient_data(
                    patient_id=patient_id,
                    query=query,
                    data_types=None  # Search all types: conditions, observations, encounters, notes, demographics
                )
                
                if all_results:
                    # Combine with existing results (avoid duplicates)
                    existing_ids = set()
                    for r in results:
                        # Create unique ID from content + data_type
                        content = r.get("content", "")
                        data_type = r.get("data_type", "")
                        existing_ids.add(f"{data_type}:{content[:50]}")
                    
                    # Add new results that aren't duplicates
                    new_results = []
                    for r in all_results:
                        content = r.get("content", "")
                        data_type = r.get("data_type", "")
                        result_id = f"{data_type}:{content[:50]}"
                        if result_id not in existing_ids:
                            new_results.append(r)
                            existing_ids.add(result_id)
                    
                    if new_results:
                        results.extend(new_results)
                        log_info("Comprehensive Results", f"✓ Added {len(new_results)} additional documents from all data types (conditions, observations, encounters, notes, demographics)")
                        log_info("Total Documents", f"✓ Now have {len(results)} documents from multiple sources")
                
                if results:
                    log_info("Comprehensive Search", f"✓ Found {len(results)} total documents from multiple sources (semantic search enabled)")
            
            # If no results, try broader search
            if not results:
                log_info("Fallback Strategy", "Removing data type filters")
                results = self.es_client.search_patient_data(
                    patient_id=patient_id,
                    query=query
                )
                if results:
                    log_info("Fallback Results", f"✓ Found {len(results)} documents")
            
            # If still no results, try searching all data types for this patient
            if not results:
                log_info("Final Strategy", "Retrieving all patient data")
                results = self.es_client.search_patient_data(
                    patient_id=patient_id,
                    query="",
                    data_types=["demographics", "conditions", "observations", "notes"]
                )
                if results:
                    log_info("Final Results", f"✓ Found {len(results)} documents")
            
            if not results:
                print(f"{Colors.YELLOW}⚠️  No data retrieved after all search attempts{Colors.ENDC}\n")
                return []
            
            # CRITICAL FIX: Add consistent sorting by date DESC (newest first) after retrieval
            # This ensures consistent results across different queries, regardless of semantic search relevance scoring
            def get_timestamp(item):
                """Extract timestamp for sorting, handling various date formats"""
                timestamp = item.get("timestamp", "")
                if not timestamp:
                    # Try metadata.date for observations
                    metadata = item.get("metadata", {})
                    timestamp = metadata.get("date", "")
                if not timestamp:
                    return "1000-01-01T00:00:00Z"  # Default to very old date
                return timestamp
            
            # Sort by timestamp DESC (newest first) for consistency
            results.sort(key=get_timestamp, reverse=True)
            
            # Apply consistent limit: Top 100 most recent documents (Research-Grade: No hardcoding)
            # NOTE: This limits TOTAL documents, but we'll keep ALL observations/conditions after grouping
            # Only NOTES will be limited by count (not content) to prevent OOM
            # This ensures no data loss for observations/conditions while preventing OOM
            
            # Use intent classifier to determine query complexity (semantic understanding, no hardcoding)
            # Intent classifier already understands semantic meaning (e.g., "risk values" = analysis)
            intent_type = intent.get("type", "")
            wants_all_data = intent.get("wants_all_data", False)
            wants_grouped = intent.get("wants_grouped", False)
            
            # Determine if complex query using intent classifier (semantic, not hardcoded keywords)
            is_complex_query = (
                wants_all_data or  # Query asks for "all", "every", "complete", "everything"
                wants_grouped or   # Query asks for grouped data
                intent_type == "analysis" or  # Analysis queries need comprehensive data
                intent_type == "grouped_visualization"  # Grouped visualization needs all data
            )
            
            # Cap at 50 docs to keep prompts under ~4000 tokens and prevent generation OOM.
            # 50 docs yields ~3500-4000 chars which is ~900-1000 tokens — safe for T4 GPUs.
            if is_complex_query:
                max_results = 50
            else:
                max_results = 50
            if len(results) > max_results:
                results = results[:max_results]
                log_info("Results Limited", f"✓ Limited to top {max_results} most recent documents (from {len(results) + max_results} total)")
                log_info("Note", "After grouping, ALL observations/conditions will be kept. Only NOTES will be limited by count.")
            
            log_info("Final Results", f"✓ Returning {len(results)} documents, sorted by date DESC (newest first)")
            
            return results
            
        except Exception as e:
            print(f"{Colors.RED}✗ Error retrieving data: {str(e)}{Colors.ENDC}\n")
            logger.error(f"Failed to retrieve data: {e}")
            return []
    
    def generate_contextual_response(self, patient_id: str, query: str, retrieved_data: List[Dict[str, Any]], intent: Dict[str, Any], context_hint: str = "") -> str:
        """
        Generate contextual response using retrieved data.
        Uses highlighting by default, with fallback to full documents (old method) if highlighting fails.
        """
        
        # Handle clarification requests
        if intent.get("type") == "clarification_needed":
            return (
                "I found patient observations for this patient. "
                "How would you like to view them?\n\n"
                "Please choose from the options below to proceed."
            )
        
        # Intent-based method selection (Research-Grade Approach)
        # Use full documents for inference queries, highlighting for specific queries
        intent_type = intent.get("type", "")
        is_analysis_query = intent_type == "analysis"
        
        # For analysis queries (inference needed) → Use full documents (skip highlighting)
        if is_analysis_query:
            logger.info("Analysis query detected (intent_type=analysis) - using full documents (needs inference from all values)")
            retrieved_data = self._get_full_documents_fallback(patient_id, query, intent, retrieved_data)
        # For general queries with synthesis → Use full documents (Research-Grade: No hardcoding)
        # Use intent classifier's wants_all_data field (semantic understanding, not hardcoded keywords)
        elif intent_type == "general" and intent.get("wants_all_data", False):
            # If query asks for "all data" or "complete view", it's a synthesis query
            # Intent classifier already identified this semantically (e.g., "summarize", "overview", "complete history")
            logger.info("Synthesis query detected (wants_all_data=true) - using full documents (needs comprehensive view)")
            retrieved_data = self._get_full_documents_fallback(patient_id, query, intent, retrieved_data)
        # For temporal/trend queries → Use full documents (Research-Grade: No hardcoding)
        # Use intent classifier's wants_visualization field (semantic understanding, not hardcoded keywords)
        elif intent_type == "visualization" and intent.get("wants_visualization", False):
            # Temporal queries (e.g., "how has glucose changed?", "trend over time") are classified as "visualization"
            # Intent classifier already identified this semantically
            logger.info("Temporal/trend query detected (intent_type=visualization, wants_visualization=true) - using full documents (needs chronological context)")
            retrieved_data = self._get_full_documents_fallback(patient_id, query, intent, retrieved_data)
        # For specific queries → Try highlighting first
        else:
            # Check if highlighting worked well
            highlighting_worked = self._check_highlighting_quality(retrieved_data)
            
            if not highlighting_worked:
                # Fallback: Use full documents (old method before highlighting)
                logger.info("Highlighting may have failed - using fallback: full documents (old method)")
                retrieved_data = self._get_full_documents_fallback(patient_id, query, intent, retrieved_data)
            else:
                logger.info("Using Elasticsearch highlighting (default method)")
        
        # Build context from retrieved data
        context_parts = []
        
        # Group data by type BEFORE limiting (to preserve observations/conditions)
        # Normalize singular ES values to the plural form the context builder expects.
        _TYPE_NORM = {
            "observation": "observations",
            "condition": "conditions",
            "note": "notes",
            "encounter": "encounters",
        }
        data_by_type = {}
        for item in retrieved_data:
            data_type = _TYPE_NORM.get(item.get("data_type", "unknown"), item.get("data_type", "unknown"))
            if data_type not in data_by_type:
                data_by_type[data_type] = []
            data_by_type[data_type].append(item)
        
        # CRITICAL: Do NOT limit observations/conditions - keep ALL for research-grade completeness
        # Only limit NOTES count (not content) to prevent OOM
        # This ensures no data loss while preventing OOM issues
        
        # Build context
        for data_type, items in data_by_type.items():
            if data_type == "demographics":
                context_parts.append("**Patient Demographics:**")
                for item in items:
                    # Safely handle missing content key
                    content = item.get("content", "")
                    if content:
                        context_parts.append(f"- {content}")
            
            elif data_type == "conditions":
                # Group and prioritize conditions by category
                from .condition_categorizer import group_conditions_by_category
                
                # Extract condition data with categorization and DEDUPLICATE
                conditions_list = []
                seen_conditions = set()  # Track seen conditions to avoid duplicates
                
                for item in items:
                    metadata = item.get("metadata", {})
                    # Read from top-level fields (new ETL index); fall back to legacy metadata.*
                    code = item.get("code") or metadata.get("code", "")
                    display = (item.get("display")
                               or item.get("content")
                               or metadata.get("display", ""))
                    # Strip SNOMED semantic-tag suffixes so clinicians see clean names
                    if display:
                        display = re.sub(
                            r'\s*\((?:disorder|finding|situation|observable entity|procedure|body structure|qualifier value)\)\s*$',
                            '', display, flags=re.IGNORECASE
                        ).strip()
                    clinical_status = (item.get("clinical_status")
                                       or metadata.get("clinicalStatus", "unknown"))

                    normalized_display = display.lower().strip() if display else ""
                    unique_key = f"{code}_{normalized_display}"

                    if unique_key in seen_conditions:
                        continue
                    seen_conditions.add(unique_key)

                    condition_data = {
                        "code": code,
                        "display": display,
                        "clinicalStatus": clinical_status,
                        "content": item.get("content", ""),
                    }
                    if "category" in metadata:
                        condition_data["category"] = metadata["category"]
                        condition_data["priority"] = metadata.get("priority", "low")
                        condition_data["normalizedName"] = metadata.get("normalizedName", display)
                    conditions_list.append(condition_data)
                
                # Group by category
                grouped = group_conditions_by_category(conditions_list)
                
                # Build context organized by category with priority
                _cond_idx = 1
                context_parts.append("\n== RETRIEVED CONDITIONS — cite as [C-N] ==")
                category_order = [
                    "Cardiovascular", "Metabolic", "Respiratory", "Neurological",
                    "Mental Health", "Musculoskeletal", "Gastrointestinal", "Renal",
                    "Endocrine", "Oncology", "Acute", "Other"
                ]

                for category in category_order:
                    if category in grouped:
                        cat_conditions = grouped[category]
                        # Sort by priority: high first
                        sorted_conditions = sorted(
                            cat_conditions,
                            key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                            reverse=True
                        )
                        context_parts.append(f"\n**{category}:**")
                        for cond in sorted_conditions:
                            name = cond.get("normalizedName") or cond.get("display", "Unknown")
                            status = cond.get("clinicalStatus") or "active"
                            onset_date = cond.get("onsetDateTime", "") or cond.get("onset", "unknown")
                            context_parts.append(
                                f"[C-{_cond_idx}] {name} | Status: {status} | Onset: {onset_date}"
                            )
                            _cond_idx += 1

                # Handle any remaining categories (including "Other" where SNOMED conditions land)
                for category, cat_conditions in grouped.items():
                    if category not in category_order:
                        context_parts.append(f"\n**{category}:**")
                        for cond in cat_conditions:
                            name   = cond.get("normalizedName") or cond.get("display") or cond.get("content", "Unknown")
                            status = cond.get("clinicalStatus") or "active"
                            onset_date = cond.get("onsetDateTime", "") or cond.get("onset", "unknown")
                            context_parts.append(
                                f"[C-{_cond_idx}] {name} | Status: {status} | Onset: {onset_date}"
                            )
                            _cond_idx += 1
            
            elif data_type == "observations":
                context_parts.append("**Clinical Observations:**")
                
                # Deduplicate observations based on display name and value
                unique_observations = {}
                for item in items:
                    metadata = item.get("metadata", {})
                    # Read from top-level fields (new ETL index); fall back to legacy metadata.*
                    display = (item.get("display")
                               or metadata.get("display", ""))
                    code    = item.get("code") or metadata.get("code", "")
                    # value: prefer numeric top-level field; legacy metadata stored strings
                    raw_val = item.get("value_numeric")
                    value   = str(raw_val) if raw_val is not None else metadata.get("value", "")
                    unit    = item.get("unit") or metadata.get("unit", "") or ""
                    ref_lo  = item.get("ref_range_low")
                    ref_hi  = item.get("ref_range_high")
                    date    = (item.get("timestamp")        # normalized to effective_date in ES client
                               or metadata.get("date", ""))
                    date_str = date[:10] if date else ""

                    # Skip purely structural CCDA metadata entries that carry no clinical value
                    _STRUCTURAL = {
                        "diagnosis", "problem", "assertion", "diagnosis status",
                        "severity observation", "criticality", "functional status",
                        "observation name", "unknown",
                    }
                    if not display or display.lower().strip() in _STRUCTURAL:
                        continue

                    # Handle NULL display: try LOINC lookup
                    if not display or display.strip() == "Observation Name":
                        try:
                            from .loinc_code_mapper import get_observation_display_from_code
                            display = get_observation_display_from_code(code) or (f"Code {code}" if code else "")
                        except ImportError:
                            display = f"Code {code}" if code else ""
                    if not display:
                        continue

                    # Clean raw LOINC technical strings so the LLM and clinician see
                    # readable names: "CREATININE:MCNC:PT:SER/PLAS:QN::" → "Creatinine"
                    if display and ':' in display and display[:3].isupper():
                        try:
                            from .loinc_code_mapper import get_clean_display_for_code
                            display = get_clean_display_for_code(code, display)
                        except ImportError:
                            pass

                    unique_key = f"{display.lower().strip()}_{value}_{date_str}"
                    if unique_key not in unique_observations:
                        unique_observations[unique_key] = {
                            "display": display,
                            "code": code,
                            "value": value,
                            "unit": unit,
                            "ref_lo": ref_lo,
                            "ref_hi": ref_hi,
                            "date": date_str,
                            "content": item.get("content", ""),
                        }
                
                # Add unique observations to context with proper formatting
                # Sort by date to show chronological order
                sorted_observations = sorted(
                    unique_observations.values(),
                    key=lambda x: (x.get("date", ""), x.get("display", ""))
                )

                _obs_idx = 1
                context_parts.append("\n== RETRIEVED OBSERVATIONS — cite as [O-N] ==")
                for obs in sorted_observations:
                    value    = obs.get("value", "")
                    display  = obs.get("display", "")
                    date_str = obs.get("date", "")
                    ref_lo   = obs.get("ref_lo")
                    ref_hi   = obs.get("ref_hi")

                    # Fallback: if ES has no reference range, look up by LOINC code
                    if ref_lo is None or ref_hi is None:
                        obs_code_for_ref = obs.get("code", "")
                        if obs_code_for_ref:
                            try:
                                from .loinc_code_mapper import get_reference_range_for_code
                                _rlo, _rhi = get_reference_range_for_code(obs_code_for_ref)
                                if _rlo is not None:
                                    ref_lo = _rlo
                                    ref_hi = _rhi
                            except ImportError:
                                pass

                    if not (value and display):
                        continue

                    value_str = str(value).strip()
                    unit      = (obs.get("unit") or "").strip()
                    display   = str(display)

                    # ── Implausibility filter ──────────────────────────────
                    try:
                        _num    = float(value_str.split()[0])
                        _disp_l = display.lower()
                        _is_ratio = "ratio" in _disp_l
                        _implausible = (
                            ("cholesterol" in _disp_l and (_num < 10 or _num > 700)) or
                            ("creatinine"  in _disp_l and not _is_ratio and (_num < 0.05 or _num > 30)) or
                            ("glucose"     in _disp_l and (_num < 0.5 or _num > 1500)) or
                            ("hemoglobin"  in _disp_l and "a1c" not in _disp_l and (_num < 1 or _num > 25)) or
                            ("blood pressure" in _disp_l and _num > 300) or
                            ("heart rate"     in _disp_l and (_num < 10 or _num > 350)) or
                            ("body temperature" in _disp_l and (_num < 25 or _num > 46))
                        )
                        if _implausible:
                            logger.warning(f"[Context filter] Skipping implausible: {display}={_num} unit={unit}")
                            continue
                    except (ValueError, TypeError, IndexError):
                        pass
                    # ────────────────────────────────────────────────────────

                    # ── Unit normalization ────────────────────────────────
                    try:
                        _raw_num = float(value_str.split()[0])
                        _norm_num, _norm_unit = _normalize_context_value(display, _raw_num, unit)
                        if _norm_unit != unit:
                            value_str = str(_norm_num)
                            unit = _norm_unit
                    except (ValueError, TypeError, IndexError):
                        pass
                    # ────────────────────────────────────────────────────────

                    # Strip placeholder unit label; look up canonical unit from LOINC mapper
                    if unit == "unit" or not unit:
                        obs_code = obs.get("code", "")
                        canonical = ""
                        if obs_code:
                            try:
                                from .loinc_code_mapper import get_canonical_unit_for_code
                                canonical = get_canonical_unit_for_code(obs_code)
                            except ImportError:
                                pass
                        unit = canonical  # "" if code not in canonical unit map
                    if value_str.endswith(" unit"):
                        value_str = value_str[:-5].strip()

                    unit_text = f" {unit}" if unit and unit not in value_str else ""

                    # ── Abnormality flag from reference range ─────────────
                    flag = ""
                    try:
                        _v = float(value_str)
                        if ref_lo is not None and ref_hi is not None:
                            ref_text = f" (ref: {ref_lo}-{ref_hi}{unit_text})"
                            if _v > float(ref_hi):
                                flag = " [HIGH]"
                            elif _v < float(ref_lo):
                                flag = " [LOW]"
                            else:
                                flag = " [normal]"
                        else:
                            ref_text = ""
                    except (ValueError, TypeError):
                        ref_text = ""
                    # ────────────────────────────────────────────────────────

                    flag_label = "HIGH" if flag == " [HIGH]" else ("LOW" if flag == " [LOW]" else "normal")
                    context_parts.append(
                        f"[O-{_obs_idx}] {display}: {value_str}{unit_text} | {flag_label} | Date: {date_str}"
                    )
                    _obs_idx += 1
            
            elif data_type == "notes":
                context_parts.append("**Clinical Notes:**")
                
                # Intelligent notes query detection (Research-Grade Approach)
                # Use intent classifier + semantic search results, not hardcoded keywords
                is_notes_query = self._determine_is_notes_query(query, intent, retrieved_data)
                
                max_notes = 5 if is_notes_query else 2  # More for notes queries, fewer for general
                notes_to_include = items[:max_notes]
                
                logger.info(f"Smart note limiting: {len(items)} notes available, including {len(notes_to_include)} (is_notes_query: {is_notes_query})")
                
                # Generate query embedding for semantic extraction (if available)
                query_embedding = None
                try:
                    from .embedding_service import EmbeddingService
                    embedding_service = EmbeddingService()
                    if embedding_service.is_available():
                        query_embedding = embedding_service.generate_embedding(query)
                except Exception as e:
                    logger.debug(f"Could not generate query embedding for semantic extraction: {e}")
                
                for item in notes_to_include:
                    # Safely handle missing content key
                    content = item.get("content", "")
                    if content:
                        # CRITICAL: Always limit note content to prevent OOM (like before: 518 chars, but better: 2000 chars)
                        # Even if semantic extraction fails, we MUST limit content size
                        # This matches the previous approach (518 chars) but with more context (2000 chars)
                        if len(content) > 2000:
                            # Try semantic extraction first (if available)
                            if query_embedding:
                                try:
                                    relevant_parts = self._extract_relevant_parts_from_note(
                                        content, query, query_embedding, max_chars=2000
                                    )
                                    context_parts.append(f"- {relevant_parts}")
                                except Exception as e:
                                    logger.warning(f"Semantic extraction failed, using first 2000 chars: {e}")
                                    # Fallback: Use first 2000 chars (better than 518, but still limited)
                                    context_parts.append(f"- {content[:2000]}...")
                            else:
                                # No embedding available: Use first 2000 chars (like before used 518)
                                context_parts.append(f"- {content[:2000]}...")
                        else:
                            # Short note: Use full content (already < 2000 chars)
                            context_parts.append(f"- {content}")
        
        context = "\n".join(context_parts)

        # Inject structured clinician context hint into retrieval block (P6)
        # Injected ONLY here — never into system_prompt — to prevent prompt injection
        if context_hint:
            context = context_hint + "\n" + context

        # ── DDx intent detection (must precede system prompt so prompt adapts) ──
        _query_lower_early = query.lower()
        _has_ddx_intent_early = any(kw in _query_lower_early for kw in DDX_INTENT_KEYWORDS)
        _is_value_lookup_early = any(kw in _query_lower_early for kw in VALUE_LOOKUP_OVERRIDES)
        _apply_ddx_early = _has_ddx_intent_early and not _is_value_lookup_early

        # =====================================================================
        # [STANDARD RAG — STEP 4a] System Prompt (no KG layer)
        # To revert to Standard RAG: set USE_MEDRAG = True at the top of this file.
        # The block below runs when USE_MEDRAG = True.
        # =====================================================================
        # system_prompt = """You are a clinical AI assistant helping healthcare professionals
        # analyze patient data. You have access to the patient's medical records and can provide
        # insights, analysis, and data-driven observations.
        # ... (standard RAG prompt — no differential diagnosis, no KG context) ...
        # """
        # =====================================================================

        if not USE_MEDRAG:
            # ─────────────────────────────────────────────────────────────────
            # [STANDARD RAG — STEP 4a] System prompt — flat patient context,
            # no knowledge graph, no differential diagnosis ranking.
            # Uncomment USE_MEDRAG = True at top of file to activate this path.
            # ─────────────────────────────────────────────────────────────────
            system_prompt = """You are a clinical AI assistant helping healthcare professionals analyze patient data.
You have access to a subset of the patient's medical records retrieved by semantic search.

CORE RULES:
- ONLY use values and findings that appear verbatim in the context provided below.
- NEVER invent, estimate, or assume any lab value, measurement, or date not in the context.
- NEVER list tests or measurements that are absent — do not write "not explicitly mentioned" or similar. Simply omit them.
- NEVER use bold formatting (**text**) or asterisks (*).
- Use clean numbered lists. Complete every sentence.

ANSWERING RULES:
- ALWAYS lead with what IS present — never open with an absence statement.
- Report every condition listed in Medical Conditions. Report every observation that has a value.
- Values flagged [HIGH] or [LOW] are abnormal — highlight those first.
- If specific queried data is absent: acknowledge in ONE sentence and move on. Do not enumerate all other absent types.
- For diagnosis questions: state the most likely diagnosis FIRST, then evidence from the records.

MEDICAL TERM MAPPING:
- "CREATININE:MCNC:PT:SER/PLAS:QN::" = creatinine
- "UREA NITROGEN:..." = BUN / blood urea nitrogen
- "HEMOGLOBIN A1C/..." = HbA1c
- "Hypertensive disorder" = hypertension; "Diabetes mellitus" = diabetes; "CKD" = chronic kidney disease
- Map LOINC/SNOMED technical codes to plain clinical terms when presenting data.

All clinical decisions must be made by qualified healthcare providers.
Use retrieved patient data only. When stating a patient-specific fact (a lab value,
a condition, or a diagnosis), cite the retrieved item using its [O-N] or [C-N] label.
Do not invent patient facts. Reasoning and interpretation do not require citation labels.
"""
        else:
            # ─────────────────────────────────────────────────────────────────
            # [MEDRAG — STEP 4a] System prompt — adapts based on DDx intent.
            # DDx queries: KG-augmented differential diagnosis reasoning.
            # Non-DDx queries: same flat-retrieval prompt as Standard RAG
            #   (prevents DDx framing from polluting direct value lookups).
            # Based on: Zhao et al., ACM WWW 2025 (MedRAG paper)
            # Active when USE_MEDRAG = True (default).
            # ─────────────────────────────────────────────────────────────────
            if _apply_ddx_early:
                system_prompt = """You are a clinical AI assistant (powered by MedRAG) helping healthcare professionals analyze patient data and perform differential diagnosis.

You have access to:
  1. The patient's EHR records (demographics, conditions, observations, clinical notes)
  2. A structured Knowledge Graph (KG) differential diagnosis section (if present in the context)

The KG section lists candidate diagnoses ranked by evidence found in the patient's records,
with distinguishing features from clinical guidelines for each candidate disease.

MEDRAG DIFFERENTIAL DIAGNOSIS GUIDELINES:
- When a KG differential diagnosis section is present, USE IT to structure your reasoning
- Identify the most likely diagnosis based on patient evidence + KG features
- Explicitly mention 1-3 alternative diagnoses that cannot yet be ruled out
- Note any missing data (marked with "?") that would help confirm or exclude a diagnosis
- Provide clinically sound reasoning, not just a list of values

CRITICAL GUIDELINES - FOLLOW EXACTLY:
- ONLY use values and findings that appear verbatim in the context below.
- NEVER invent, estimate, or assume a lab value, measurement, or date that is not in the context.
- NEVER list tests or measurements that are absent — do not say "not explicitly mentioned". Silence is correct for absent data.
- If a specific data point is missing, acknowledge it in at most ONE sentence, then move on.
- NEVER open a response with an absence statement — always lead with what IS present.
- Lead with the diagnosis, not a data dump. Cite only the 3-5 most clinically significant findings that support or refute it.
- Highlight abnormal values ([HIGH]/[LOW]) that are directly relevant to the differential.
- NEVER use bold formatting (**text**) or asterisks (*).
- Use clean numbered lists. Complete every sentence.
- KG "?" diagnostic gaps are clinical guideline criteria — do NOT report them as absent from patient records.

MEDRAG RESPONSE STRUCTURE (when KG context is present):
1. Most Likely Diagnosis — state it clearly with supporting evidence
2. Supporting Evidence — key observations/conditions from patient records
3. Alternative Diagnoses — 1-2 alternatives with brief reasoning
4. Missing Data — what additional tests/data would help narrow the diagnosis
5. Clinical Recommendation — actionable next step for the clinician

MEDICAL TERM RECOGNITION:
- "Hypertensive disorder" = "hypertension" = "high blood pressure"
- "Diabetes mellitus" = "diabetes" = "diabetic"
- "Chronic kidney disease" = "CKD" = "renal disease"
- Always map technical LOINC/SNOMED codes to readable clinical terms

IMPORTANT: This tool provides data analysis and KG-elicited reasoning only.
All clinical decisions must be made by qualified healthcare providers.
Use retrieved patient data only. When stating a patient-specific fact (a lab value,
a condition, or a diagnosis), cite the retrieved item using its [O-N] or [C-N] label.
Do not invent patient facts. Reasoning and interpretation do not require citation labels.
"""
            else:
                # Non-DDx MedRAG: KG-aware direct-answer prompt.
                # Unlike Standard RAG, this tells the LLM to use the KG Clinical Context
                # block (injected in the user prompt) to enrich its clinical interpretation.
                system_prompt = """You are a clinical AI assistant (powered by MedRAG) helping healthcare professionals interpret patient data.

You have access to:
  1. The patient's EHR records retrieved by semantic search
  2. A KG Clinical Context block (when present) summarizing which condition profiles the patient's labs match

CORE RULES:
- ONLY use values that appear verbatim in the context. Never invent or estimate.
- NEVER use bold (**text**) or asterisks (*). Use plain numbered lists.
- Complete every sentence. Do not truncate.

ANSWERING RULES:
- Answer the specific question directly. Cite the retrieved value with its [O-N] or [C-N] label.
- After answering, add 1-2 sentences of clinical interpretation using the KG Clinical Context — connect the finding to the patient's broader condition profile.
- Example: "[O-13] Creatinine: 2.2 mg/dL — HIGH. This is consistent with the patient's CKD Stage 3b profile (75% evidence match), alongside elevated BUN and low hemoglobin indicating CKD-related anemia."
- If the queried value is absent from the records: say so in one sentence, then stop.
- Do NOT list every lab value — answer what was asked, then add clinical context.

MEDICAL TERM MAPPING:
- "Hypertensive disorder" = hypertension | "Diabetes mellitus" = diabetes | "CKD" = chronic kidney disease
- Map all LOINC/SNOMED codes to plain clinical terms.

All clinical decisions must be made by qualified healthcare providers.
Cite [O-N] or [C-N] for patient-specific facts. Reasoning does not need citation labels."""
        
        # =====================================================================
        # [STANDARD RAG — STEP 4b] User Prompt (no KG injection)
        # Active when USE_MEDRAG = True.
        # =====================================================================
        # user_prompt = f"""Patient Query: "{query}"
        #
        # Patient Data Context:
        # {context}
        #
        # [... standard RAG user prompt with no KG differential diagnosis ...]
        # """
        # =====================================================================

        if not USE_MEDRAG:
            # ─────────────────────────────────────────────────────────────────
            # [STANDARD RAG — STEP 4b] User prompt — patient EHR context only.
            # No KG differential diagnosis. Flat retrieval → LLM.
            # Activate: set USE_MEDRAG = True at top of file.
            # ─────────────────────────────────────────────────────────────────
            user_prompt = f"""Patient Query: "{query}"

Patient Data Context:
{context}

Before answering: identify the relevant [O-N] and [C-N] items in the data above.
When you state a specific patient value or condition, include its label.

FORMAT:
- Lead with the specific retrieved value: "[O-N] [Observation]: [Value] [Unit] (Date: YYYY-MM-DD) — [HIGH/LOW/normal]"
- Follow naturally with 1-2 sentences of clinical interpretation. Interpretation sentences do not need labels.
- If the asked-about value does NOT appear in any record: state "No [test name] found in retrieved data." once, then stop.
- Do NOT repeat the same value. If multiple records show the same test, report only the most recent non-null entry.
- Do NOT open with an absence — always list present values first.
- Do NOT use asterisks (*) or bold formatting (**text**).
- Complete every sentence — do not truncate mid-list.

CLINICAL REFERENCE RANGES:
  Glucose (fasting): <100 normal | 100-125 pre-diabetes | >=126 diabetes
  HbA1c: <5.7% normal | 5.7-6.4% pre-diabetes | >=6.5% diabetes | >9% poorly controlled
  Creatinine: 0.6-1.2 mg/dL (M) | 0.5-1.1 (F) | >1.5 renal concern
  BUN: 7-25 mg/dL | BUN/Cr >20 pre-renal | <10 hepatic/malnutrition
  eGFR: >=60 normal | 45-59 CKD 3a | 30-44 CKD 3b | 15-29 CKD 4 | <15 failure
  Troponin I: <0.04 ng/mL normal | >0.4 MI
  BNP: <100 pg/mL normal | >400 CHF likely
  Total cholesterol: <200 desirable | >=240 high
  LDL: <100 optimal | >=160 high | >=190 very high
  HDL: >60 protective | <40 (M)/<50 (F) low
  Triglycerides: <150 normal | >=500 pancreatitis risk
  Hemoglobin: 13.5-17.5 g/dL (M) | 12-15.5 (F) | <12 anemia
  WBC: 4.5-11.0 x10^3/uL | >11 infection | <4.5 immunosuppression
  Sodium: 136-145 mEq/L | <130 severe hyponatremia
  Potassium: 3.5-5.0 mEq/L | <3.0 arrhythmia risk | >5.5 hyperkalemia
  ALT: 7-56 U/L | AST: 10-40 U/L | >3x ULN = liver injury
  TSH: 0.4-4.0 mIU/L | <0.4 hyperthyroid | >4.0 hypothyroid
  Blood Pressure: <120/80 normal | >=130/80 HTN stage 1 | >=140/90 HTN stage 2
  Heart Rate: 60-100 bpm | <60 bradycardia | >100 tachycardia
  O2 Saturation: >=95% normal | <90% severe hypoxia
  BMI: <18.5 underweight | 18.5-24.9 normal | 25-29.9 overweight | >=30 obese
  Platelets: 150-400 x10^3/uL | <150 thrombocytopenia
  MCV: 80-100 fL | <80 microcytic | >100 macrocytic
  Albumin: 3.5-5.0 g/dL | <3.5 malnutrition/liver disease
  Uric acid: 3.5-7.2 mg/dL (M) | 2.6-6.0 (F) | >7.2 gout risk

All clinical decisions must be made by qualified healthcare providers.
"""
        else:
            # ─────────────────────────────────────────────────────────────────
            # [MEDRAG — STEP 4b] User prompt — EHR context + KG differential
            # diagnosis context injected BEFORE the LLM call.
            # Based on: Zhao et al., ACM WWW 2025 — KG-elicited reasoning.
            # Active when USE_MEDRAG = True (default).
            # ─────────────────────────────────────────────────────────────────

            # DDx intent was detected above (before system prompt) — reuse result.
            _apply_ddx = _apply_ddx_early

            # ── Gate KG pipeline: run ONLY for DDx queries ─────────────────────
            kg_context_block = ""
            kg_candidates: list = []
            if _apply_ddx:
                kg_result = kg_service.run_kg_pipeline(query, retrieved_data)
                kg_context_block = kg_result.get("kg_context", "")
                kg_candidates = kg_result.get("candidate_diseases", [])
                kg_chart_hints = kg_result.get("chart_observation_hints", [])
                if kg_chart_hints:
                    intent["ddx_chart_hints"] = kg_chart_hints
                logger.info(f"[MedRAG DDx] KG found {len(kg_candidates)} candidates: {kg_candidates}")
            else:
                # Non-DDx: run KG to get compact clinical context (build_kg_summary)
                # This adds clinical interpretation value even for value-lookup queries.
                kg_result = kg_service.run_kg_pipeline(query, retrieved_data)
                kg_context_block = kg_result.get("kg_summary", "")
                kg_candidates = kg_result.get("candidate_diseases", [])
                logger.info(f"[MedRAG] Non-DDx query — KG summary for {len(kg_candidates)} candidates")

            # retrieved_data is used in OOM fallback (line ~1440). Keep full list
            # so that OOM retry has the same data as the primary attempt.
            # ES already caps at 150 docs upstream — no need to truncate further.

            # ── Select KG block to inject ───────────────────────────────────────
            _kg_inject = kg_context_block  # always inject: full DDx block or compact summary

            # Build the MedRAG user prompt
            if _apply_ddx:
                user_prompt = f"""Patient Query: "{query}"

{'=' * 70}
PATIENT EHR RECORDS (retrieved via Elasticsearch)
{'=' * 70}
{context}

{_kg_inject}

DIFFERENTIAL DIAGNOSIS (based only on the retrieved values above):
Use the KG section above as a REASONING GUIDE — it tells you which disease families fit the pattern.
The KG "Key features" are clinical guideline thresholds, not patient records — do not cite them as patient findings.

1. Most likely diagnosis: [name]
   Support with specific retrieved values — cite [O-N] or [C-N] for each patient finding.

2. Supporting evidence: 2-4 retrieved findings that most strongly support this diagnosis.

3. Alternative diagnoses: 1-2 conditions the KG identified as possible. State what retrieved evidence rules each in or out.

4. Missing data: At most 1 test absent from records that would confirm or exclude the top diagnosis.

5. Clinical recommendation: One actionable step based on the most abnormal retrieved finding.

RULES:
- For patient-specific facts (lab values, conditions): cite [O-N] or [C-N].
- Interpretation, reasoning, and KG-derived alternatives do NOT require citation labels.
- PLAIN TEXT ONLY — no asterisks, no bold, no markdown.
- Do not fabricate values. Do not reference tests not in the retrieved data.

CLINICAL REFERENCE RANGES:
  Glucose (fasting): <100 normal | 100-125 pre-diabetes | >=126 diabetes
  HbA1c: <5.7% normal | 5.7-6.4% pre-diabetes | >=6.5% diabetes | >9% poorly controlled
  Creatinine: 0.6-1.2 mg/dL (M) | 0.5-1.1 (F) | >1.5 renal concern
  BUN: 7-25 mg/dL | BUN/Cr >20 pre-renal | <10 hepatic/malnutrition
  eGFR: >=60 normal | 45-59 CKD 3a | 30-44 CKD 3b | 15-29 CKD 4 | <15 failure
  Troponin I: <0.04 ng/mL normal | >0.4 MI
  BNP: <100 pg/mL normal | >400 CHF likely
  Total cholesterol: <200 desirable | >=240 high
  LDL: <100 optimal | >=160 high | >=190 very high
  HDL: >60 protective | <40 (M)/<50 (F) low
  Triglycerides: <150 normal | >=500 pancreatitis risk
  Hemoglobin: 13.5-17.5 g/dL (M) | 12-15.5 (F) | <12 anemia
  WBC: 4.5-11.0 x10^3/uL | >11 infection | <4.5 immunosuppression
  Sodium: 136-145 mEq/L | <130 severe hyponatremia
  Potassium: 3.5-5.0 mEq/L | <3.0 arrhythmia risk | >5.5 hyperkalemia
  ALT: 7-56 U/L | AST: 10-40 U/L | >3x ULN = liver injury
  TSH: 0.4-4.0 mIU/L | <0.4 hyperthyroid | >4.0 hypothyroid
  Blood Pressure: <120/80 normal | >=130/80 HTN stage 1 | >=140/90 HTN stage 2
  Heart Rate: 60-100 bpm | <60 bradycardia | >100 tachycardia
  O2 Saturation: >=95% normal | <90% severe hypoxia
  BMI: <18.5 underweight | 18.5-24.9 normal | 25-29.9 overweight | >=30 obese
  Platelets: 150-400 x10^3/uL | <150 thrombocytopenia
  MCV: 80-100 fL | <80 microcytic | >100 macrocytic
  Albumin: 3.5-5.0 g/dL | <3.5 malnutrition/liver disease
  Uric acid: 3.5-7.2 mg/dL (M) | 2.6-6.0 (F) | >7.2 gout risk

All clinical decisions must be made by qualified healthcare providers.
"""
            else:
                # Non-DDx: value lookup or specific clinical question
                # Inject KG compact summary above EHR context for clinical context
                _kg_hint = f"\n{_kg_inject}\n" if _kg_inject else ""
                user_prompt = f"""Patient Query: "{query}"
{_kg_hint}
{'=' * 70}
PATIENT EHR RECORDS (retrieved via Elasticsearch)
{'=' * 70}
{context}

Before answering: identify the relevant [O-N] and [C-N] items in the data above.
When you state a specific patient value or condition, include its label.

FORMAT:
- Lead with the specific retrieved value: "[O-N] [Observation]: [Value] [Unit] (Date: YYYY-MM-DD) — [HIGH/LOW/normal]"
- Follow with 1-2 sentences of clinical interpretation. Use the KG Clinical Context block above to connect the finding to the patient's condition profile. Interpretation sentences do not need labels.
- If a KG Clinical Context block is present above: synthesize it into your interpretation (e.g. "This is consistent with the patient's CKD Stage 3b profile (75% match)."). Do NOT copy the KG block verbatim.
- If the asked-about value does NOT appear in any record: state "No [test name] found in retrieved data." once, then stop.
- Do NOT list every lab value — answer the specific question, then add context.
- Do NOT open with an absence — always list present values first.
- Do NOT use bold formatting (**text**) or asterisks (*).
- Do NOT repeat the same value more than once.

CLINICAL REFERENCE RANGES:
  Glucose (fasting): <100 normal | 100-125 pre-diabetes | >=126 diabetes
  HbA1c: <5.7% normal | 5.7-6.4% pre-diabetes | >=6.5% diabetes | >9% poorly controlled
  Creatinine: 0.6-1.2 mg/dL (M) | 0.5-1.1 (F) | >1.5 renal concern
  BUN: 7-25 mg/dL | BUN/Cr >20 pre-renal | <10 hepatic/malnutrition
  eGFR: >=60 normal | 45-59 CKD 3a | 30-44 CKD 3b | 15-29 CKD 4 | <15 failure
  Troponin I: <0.04 ng/mL normal | >0.4 MI
  BNP: <100 pg/mL normal | >400 CHF likely
  Total cholesterol: <200 desirable | >=240 high
  LDL: <100 optimal | >=160 high | >=190 very high
  HDL: >60 protective | <40 (M)/<50 (F) low
  Triglycerides: <150 normal | >=500 pancreatitis risk
  Hemoglobin: 13.5-17.5 g/dL (M) | 12-15.5 (F) | <12 anemia
  WBC: 4.5-11.0 x10^3/uL | >11 infection | <4.5 immunosuppression
  Sodium: 136-145 mEq/L | <130 severe hyponatremia
  Potassium: 3.5-5.0 mEq/L | <3.0 arrhythmia risk | >5.5 hyperkalemia
  ALT: 7-56 U/L | AST: 10-40 U/L | >3x ULN = liver injury
  TSH: 0.4-4.0 mIU/L | <0.4 hyperthyroid | >4.0 hypothyroid
  Blood Pressure: <120/80 normal | >=130/80 HTN stage 1 | >=140/90 HTN stage 2
  Heart Rate: 60-100 bpm | <60 bradycardia | >100 tachycardia
  O2 Saturation: >=95% normal | <90% severe hypoxia
  BMI: <18.5 underweight | 18.5-24.9 normal | 25-29.9 overweight | >=30 obese
  Platelets: 150-400 x10^3/uL | <150 thrombocytopenia
  MCV: 80-100 fL | <80 microcytic | >100 macrocytic
  Albumin: 3.5-5.0 g/dL | <3.5 malnutrition/liver disease
  Uric acid: 3.5-7.2 mg/dL (M) | 2.6-6.0 (F) | >7.2 gout risk

All clinical decisions must be made by qualified healthcare providers.
"""

        try:
            # generate_chat() already handles GPU cleanup after generation (in llm.py)
            # No need to clear again here - this could interfere with summaries that are waiting
            response = generate_chat(system_prompt, user_prompt, category="chat").strip()
            return response
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Failed to generate LLM response: {error_type}: {error_msg}", exc_info=True)
            # Note: generate_chat() handles GPU cleanup internally, even on errors
            # No need to clear here - could interfere with summaries waiting to generate
            print(f"❌ LLM generation failed in RAG service: {error_type}: {error_msg}")
            
            # Provide more specific error messages based on error type
            if "OutOfMemory" in error_type or "OOM" in error_msg or "out of memory" in error_msg.lower():
                # Try retry with reduced observations (same pattern as summary.py)
                # Summary.py retry: reduces observations to 30, keeps all conditions
                # This matches the working pattern that successfully generates summaries
                try:
                    # Rebuild context with reduced observations (limit to 30, same as summary.py)
                    # Keep all conditions, only reduce observations
                    context_parts = []
                    data_by_type = {}
                    for item in retrieved_data:
                        data_type = item.get("data_type", "unknown")
                        if data_type not in data_by_type:
                            data_by_type[data_type] = []
                        data_by_type[data_type].append(item)
                    
                    # Rebuild context with same logic as above, but limit observations to 30
                    for data_type, items in data_by_type.items():
                        if data_type == "demographics":
                            context_parts.append("**Patient Demographics:**")
                            for item in items:
                                content = item.get("content", "")
                                if content:
                                    context_parts.append(f"- {content}")
                        
                        elif data_type == "conditions":
                            # Keep ALL conditions (same as summary.py retry pattern)
                            from .condition_categorizer import group_conditions_by_category
                            conditions_list = []
                            seen_conditions = set()
                            
                            for item in items:
                                metadata = item.get("metadata", {})
                                code = item.get("code") or metadata.get("code", "")
                                display = (item.get("display")
                                           or item.get("content")
                                           or metadata.get("display", ""))
                                if display:
                                    display = re.sub(
                                        r'\s*\((?:disorder|finding|situation|observable entity|procedure|body structure|qualifier value)\)\s*$',
                                        '', display, flags=re.IGNORECASE
                                    ).strip()
                                normalized_display = display.lower().strip() if display else ""
                                unique_key = f"{code}_{normalized_display}"

                                if unique_key in seen_conditions:
                                    continue
                                seen_conditions.add(unique_key)

                                condition_data = {
                                    "code": code,
                                    "display": display,
                                    "clinicalStatus": (item.get("clinical_status")
                                                       or metadata.get("clinicalStatus", "unknown")),
                                    "content": item.get("content", "")
                                }
                                if "category" in metadata:
                                    condition_data["category"] = metadata["category"]
                                    condition_data["priority"] = metadata.get("priority", "low")
                                    condition_data["normalizedName"] = metadata.get("normalizedName", condition_data["display"])
                                conditions_list.append(condition_data)
                            
                            grouped = group_conditions_by_category(conditions_list)
                            context_parts.append("**Medical Conditions (organized by category):**")
                            category_order = [
                                "Cardiovascular", "Metabolic", "Respiratory", "Neurological",
                                "Mental Health", "Musculoskeletal", "Gastrointestinal", "Renal",
                                "Endocrine", "Oncology", "Acute", "Other"
                            ]
                            
                            for category in category_order:
                                if category in grouped:
                                    cat_conditions = grouped[category]
                                    sorted_conditions = sorted(
                                        cat_conditions,
                                        key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                                        reverse=True
                                    )
                                    context_parts.append(f"\n**{category}:**")
                                    for cond in sorted_conditions:
                                        priority = cond.get("priority", "low")
                                        priority_marker = "🔴 HIGH" if priority == "high" else "🟡 MEDIUM" if priority == "medium" else "🟢 LOW"
                                        name = cond.get("normalizedName") or cond.get("display", "Unknown")
                                        status = cond.get("clinicalStatus", "unknown")
                                        context_parts.append(f"  {priority_marker}: {name} (Status: {status})")
                            
                            for category, cat_conditions in grouped.items():
                                if category not in category_order:
                                    context_parts.append(f"\n**{category}:**")
                                    for cond in cat_conditions:
                                        priority = cond.get("priority", "low")
                                        priority_marker = "🔴 HIGH" if priority == "high" else "🟡 MEDIUM" if priority == "medium" else "🟢 LOW"
                                        name = cond.get("normalizedName") or cond.get("display", "Unknown")
                                        status = cond.get("clinicalStatus", "unknown")
                                        context_parts.append(f"  {priority_marker}: {name} (Status: {status})")
                        
                        elif data_type == "observations":
                            # Limit observations to 30 (same as summary.py retry pattern)
                            context_parts.append("**Observations:**")
                            limited_observations = items[:30] if len(items) > 30 else items
                            
                            for item in limited_observations:
                                metadata = item.get("metadata", {})
                                display = metadata.get("display", "Unknown")
                                value_str = metadata.get("value", "")
                                unit = metadata.get("unit", "")
                                date_str = str(metadata.get("date", ""))[:10] if metadata.get("date") else ""

                                # Implausibility guard (identical to main context path)
                                try:
                                    _nv = float(str(value_str).split()[0])
                                    _dl = (display or "").lower()
                                    _ir = "ratio" in _dl
                                    if (
                                        ("cholesterol" in _dl and _nv < 10) or
                                        ("creatinine" in _dl and not _ir and _nv < 0.05) or
                                        ("glucose" in _dl and _nv < 0.5) or
                                        ("hemoglobin" in _dl and "a1c" not in _dl and _nv < 1) or
                                        ("cholesterol" in _dl and _nv > 700) or
                                        ("creatinine" in _dl and not _ir and _nv > 30) or
                                        ("glucose" in _dl and _nv > 1500) or
                                        ("hemoglobin" in _dl and "a1c" not in _dl and _nv > 25) or
                                        ("blood pressure" in _dl and _nv > 300) or
                                        ("heart rate" in _dl and (_nv < 10 or _nv > 350)) or
                                        ("body temperature" in _dl and (_nv < 25 or _nv > 46))
                                    ):
                                        continue
                                except (ValueError, TypeError, IndexError):
                                    pass

                                if value_str:
                                    if date_str:
                                        context_parts.append(f"- {display}: {value_str} {unit} (recorded on {date_str})")
                                    else:
                                        context_parts.append(f"- {display}: {value_str} {unit}")
                        
                        elif data_type == "notes":
                            context_parts.append("**Clinical Notes:**")
                            for item in items:
                                content = item.get("content", "")
                                if content:
                                    context_parts.append(f"- {content}")
                    
                    reduced_context = "\n".join(context_parts)
                    user_prompt = f"""Patient Query: "{query}"

Patient Data Context:
{reduced_context}

CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:
- Answer ONLY the specific question asked - do NOT mention unrelated information
- Only use the data provided above
- Do not generate or assume any data that is not explicitly shown
- If a specific value is requested and found in the data, state it clearly without disclaimers
- Do NOT list unrelated observations, conditions, or notes that don't answer the question
- Focus on answering the exact question asked - nothing more, nothing less"""
                    
                    # Retry with reduced observations (same pattern as summary.py)
                    logger.info(f"OOM detected, retrying with reduced observations (30 instead of {len([i for i in retrieved_data if i.get('data_type') == 'observations'])}), keeping all conditions")
                    response = generate_chat(system_prompt, user_prompt, category="chat")
                    logger.info("Retry with reduced observations succeeded")
                    return response.strip()
                except Exception as retry_error:
                    logger.warning(f"Retry with reduced observations also failed: {retry_error}")
                    return "I found relevant patient data but the system is temporarily out of memory. Please wait a moment and try again, or refresh the page."
            elif "timeout" in error_msg.lower():
                return "I found relevant patient data but the response is taking longer than expected. Please try again with a simpler query."
            elif "CUDA" in error_type or "cuda" in error_msg.lower():
                return "I found relevant patient data but encountered a GPU error. Please wait a moment and try again."
            else:
                return f"I found relevant patient data but encountered an issue generating a response ({error_type}). Please try again."
    
    def generate_follow_up_options(self, intent: Dict[str, Any], retrieved_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate contextual follow-up options based on intent and data"""
        options = []
        
        # Add intent-based options
        if intent["follow_up_options"]:
            for option in intent["follow_up_options"]:
                if "📊" in option:
                    options.append({
                        "text": option,
                        "type": "visualization",
                        "action": "create_chart"
                    })
                elif "📈" in option:
                    options.append({
                        "text": option,
                        "type": "analysis",
                        "action": "analyze_patterns"
                    })
                elif "📋" in option:
                    options.append({
                        "text": option,
                        "type": "report",
                        "action": "generate_report"
                    })
        
        # Add data-driven options based on retrieved data
        observation_types = set()
        for item in retrieved_data:
            # Safely handle missing data_type key
            data_type = item.get("data_type", "")
            if data_type == "observations":
                # Safely handle None metadata
                metadata = item.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                display = (metadata.get("display") or "").lower()
                if "glucose" in display:
                    observation_types.add("glucose")
                elif "blood pressure" in display or "systolic" in display or "diastolic" in display:
                    observation_types.add("blood_pressure")
                elif "heart rate" in display or "pulse" in display:
                    observation_types.add("heart_rate")
                elif "temperature" in display:
                    observation_types.add("temperature")
                elif "respiratory" in display:
                    observation_types.add("respiratory_rate")
        
        # Add specific visualization options
        for obs_type in observation_types:
            if obs_type == "glucose":
                options.append({
                    "text": "📊 Create glucose trend chart",
                    "type": "visualization",
                    "action": "create_glucose_chart"
                })
            elif obs_type == "blood_pressure":
                options.append({
                    "text": "📊 Create blood pressure monitoring chart",
                    "type": "visualization",
                    "action": "create_bp_chart"
                })
            elif obs_type == "heart_rate":
                options.append({
                    "text": "📊 Create heart rate trend chart",
                    "type": "visualization",
                    "action": "create_hr_chart"
                })
        
        # Add general options
        options.extend([
            {
                "text": "📊 Create comprehensive vital signs dashboard",
                "type": "visualization",
                "action": "create_vitals_dashboard"
            },
            {
                "text": "📋 Generate detailed patient report",
                "type": "report",
                "action": "generate_patient_report"
            },
            {
                "text": "🔄 Refresh patient data",
                "type": "action",
                "action": "refresh_data"
            }
        ])
        
        return options[:6]  # Limit to 6 options
    
    def process_chat_query(self, patient_id: str, query: str, context_hint: str = "") -> Dict[str, Any]:
        """Main method to process chat query and generate response"""
        
        # Log query received
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_section("🔍 RAG QUERY RECEIVED", Colors.CYAN)
        log_info("Timestamp", timestamp)
        log_info("Patient ID", patient_id)
        log_info("User Query", query)
        log_info("Pipeline Mode", "MedRAG + KG" if USE_MEDRAG else "Standard RAG")
        print()
        
        # =====================================================================
        # STEP 1 — INTENT ANALYSIS
        # ─────────────────────────────────────────────────────────────────────
        # [STANDARD RAG — STEP 1] LLM-based intent classification.
        #   Purpose: Classify query into type, data_types, wants_visualization, etc.
        #   Runs in BOTH modes (intent is needed for visualization + follow-up logic).
        #
        # [MEDRAG — STEP 1] Same intent classification (preserved for compatibility),
        #   PLUS: the KG pipeline adds clinical feature decomposition inside
        #   generate_contextual_response() at Step 4 (kg_service.run_kg_pipeline).
        #   Toggle: controlled by USE_MEDRAG flag in generate_contextual_response.
        # =====================================================================
        log_section("📊 STEP 1 — INTENT ANALYSIS", Colors.BLUE)
        log_info("Mode", "Standard RAG" if not USE_MEDRAG else "MedRAG (intent preserved for viz/follow-up)")
        intent = self.analyze_query_intent(query)
        log_info("Intent Type", intent.get("type", "unknown"))
        log_info("Data Types Needed", ", ".join(intent.get("data_types", [])) if intent.get("data_types") else "All")
        log_info("Parameters", ", ".join(intent.get("parameters", [])) if intent.get("parameters") else "None")
        print()
        
        # =====================================================================
        # STEP 2 — ELASTICSEARCH RETRIEVAL
        # ─────────────────────────────────────────────────────────────────────
        # [STANDARD RAG — STEP 2] Hybrid BM25 + kNN semantic search.
        #   Returns flat ranked list of patient data documents.
        #   The LLM receives this directly as context.
        #
        # [MEDRAG — STEP 2] Same Elasticsearch retrieval (unchanged).
        #   The retrieved_data is THEN passed through the KG pipeline in Step 4
        #   to find candidate diseases, extract distinguishing features, and
        #   build a structured differential diagnosis block for the LLM prompt.
        #   Toggle: USE_MEDRAG controls what happens AFTER retrieval (Step 4).
        # =====================================================================
        log_section(f"🔎 STEP 2 — ELASTICSEARCH RETRIEVAL ({'Standard RAG' if not USE_MEDRAG else 'MedRAG — same retrieval, KG augments in Step 4'})", Colors.YELLOW)
        retrieved_data = self.retrieve_relevant_data(patient_id, query, intent)

        # Enhanced logging for research quality - track retrieval success
        if retrieved_data:
            logger.info(f"Successfully retrieved {len(retrieved_data)} documents for patient {patient_id}")
        else:
            logger.warning(f"No documents retrieved for patient {patient_id}, query: '{query}'")

        # ── Secondary targeted ES query for observation-specific queries ─────────
        # When the user asks about a specific vital/lab metric (e.g., "all heart rate
        # values"), the main hybrid search returns top-150 mixed across all types,
        # leaving only a handful of the named metric. We supplement with ALL readings
        # of the specific metric so the LLM can enumerate them completely.
        _targeted_obs_term: str = ""
        _total_targeted: int = 0
        _obs_terms = [
            "heart rate", "blood pressure", "systolic", "diastolic", "glucose",
            "hba1c", "hemoglobin a1c", "hemoglobin", "creatinine", "cholesterol",
            "bun", "sodium", "potassium", "weight", "bmi", "oxygen saturation",
            "temperature", "respiratory rate", "pulse",
        ]
        if intent.get("type") == "observations":
            _query_lower_obs = query.lower()
            _matched_obs_term = next(
                (t for t in _obs_terms if t in _query_lower_obs), None
            )
            if _matched_obs_term:
                try:
                    from .elasticsearch_client import es_client as _es_client
                    _all_obs = _es_client.get_all_patient_data_by_type(
                        patient_id, "observations", size=200
                    )
                    _targeted = [
                        doc for doc in _all_obs
                        if _matched_obs_term in (doc.get("metadata", {}).get("display") or "").lower()
                        or _matched_obs_term in (doc.get("content") or "").lower()
                    ]
                    if _targeted:
                        _total_targeted = len(_targeted)
                        _targeted_obs_term = _matched_obs_term
                        _existing_contents = {r.get("content", "") for r in retrieved_data}
                        for _doc in _targeted:
                            if _doc.get("content", "") not in _existing_contents:
                                retrieved_data.append(_doc)
                                _existing_contents.add(_doc.get("content", ""))
                        logger.info(
                            "Targeted obs supplement: term='%s' total=%d added=%d",
                            _matched_obs_term, _total_targeted,
                            sum(1 for d in _targeted if d.get("content", "") in _existing_contents),
                        )
                except Exception as _te:
                    logger.warning("Targeted obs supplement failed: %s", _te)
        # ─────────────────────────────────────────────────────────────────────────
        
        # =====================================================================
        # STEP 3 — SOURCE EXTRACTION
        # ─────────────────────────────────────────────────────────────────────
        # [STANDARD RAG — STEP 3] Flat source metadata extraction.
        #   Assigns UUIDs to each source for clickable citations in the UI.
        #   Sources are ranked by Elasticsearch relevance score.
        #
        # [MEDRAG — STEP 3] Same extraction (unchanged).
        #   Sources are still extracted and stored — they serve as the patient
        #   EHR tier that the KG pipeline reads in Step 4 to find candidate
        #   diseases and extract distinguishing features.
        #   The KG does NOT replace sources; it adds a second knowledge layer.
        # =====================================================================
        log_section(f"📋 STEP 3 — SOURCE EXTRACTION ({'Standard RAG' if not USE_MEDRAG else 'MedRAG — same extraction, sources feed KG in Step 4'})", Colors.GREEN)
        sources = []
        if retrieved_data:
            log_info("Total Documents Retrieved", len(retrieved_data))
            
            # Group sources by data type and extract key information
            sources_by_type = {}
            for item in retrieved_data:
                data_type = item.get("data_type", "unknown")
                if data_type not in sources_by_type:
                    sources_by_type[data_type] = []
                
                metadata = item.get("metadata", {})
                # Read from top-level ES fields first (current schema); fall back to legacy metadata.*
                _raw_num = item.get("value_numeric")
                source_info = {
                    "data_type": data_type,
                    "display": item.get("display") or metadata.get("display", ""),
                    "value": (str(_raw_num) if _raw_num is not None
                              else item.get("value_string") or metadata.get("value", "")),
                    "unit": item.get("unit") or metadata.get("unit", ""),
                    "date": (item.get("effective_datetime") or item.get("effective_date")
                             or item.get("note_date") or item.get("timestamp")
                             or metadata.get("date", "")),
                    "code": item.get("code") or metadata.get("code", ""),
                    "score": item.get("score", 0),
                    "timestamp": item.get("timestamp", ""),
                    "filename": item.get("note_filename") or metadata.get("filename", ""),
                    "source_type": item.get("source_hospital") or metadata.get("source_type", ""),
                    "content": item.get("content", ""),
                    "metadata": metadata
                }
                sources_by_type[data_type].append(source_info)
            
            # Log sources by type with detailed proof information
            for data_type, items in sources_by_type.items():
                log_info(f"{data_type.capitalize()} Documents", len(items))
                # Show top 5 most relevant with detailed proof
                items_sorted = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
                for idx, item in enumerate(items_sorted[:5], 1):
                    display = item.get("display", "N/A")
                    value = item.get("value", "N/A")
                    unit = item.get("unit", "")
                    code = item.get("code", "")
                    date = item.get("date", "")
                    score = item.get("score", 0)
                    
                    # Format detailed source information
                    source_details = []
                    if display and display != "N/A":
                        source_details.append(f"Display: {display}")
                    if value and value != "N/A":
                        unit_str = f" {unit}" if unit else ""
                        source_details.append(f"Value: {value}{unit_str}")
                    if code:
                        source_details.append(f"Code: {code}")
                    if date:
                        source_details.append(f"Date: {date[:10]}")
                    source_details.append(f"Relevance Score: {score:.2f}")
                    
                    log_data(f"  [{idx}] {data_type.upper()}", " | ".join(source_details))
                    print(f"      {Colors.GREEN}✓ Extracted from: {data_type} data{Colors.ENDC}")
                    if code:
                        print(f"      {Colors.GREEN}✓ Source Code: {code}{Colors.ENDC}")
                    if date:
                        print(f"      {Colors.GREEN}✓ Recorded Date: {date[:10]}{Colors.ENDC}")
                    print()
                if len(items) > 5:
                    log_data("  ...", f"{len(items) - 5} more {data_type} documents")
                print()
            
            # Create enriched sources with unique IDs (limit to top 10 most relevant)
            for data_type, items in sources_by_type.items():
                # Sort by score (relevance)
                items_sorted = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
                for item in items_sorted[:10]:  # Top 10 per data type
                    # Generate unique source ID
                    source_id = str(uuid.uuid4())
                    
                    # Create enriched source detail for storage
                    source_detail = {
                        "id": source_id,
                        "data_type": data_type,
                        "display": item.get("display", ""),
                        "value": item.get("value", ""),
                        "unit": item.get("unit", ""),
                        "date": item.get("date", ""),
                        "code": item.get("code", ""),
                        "score": item.get("score", 0),
                        "timestamp": item.get("timestamp", ""),
                        "filename": item.get("filename", ""),
                        "source_type": item.get("source_type", ""),
                        "content": item.get("content", ""),
                        "metadata": item.get("metadata", {}) if "metadata" in item else {},
                        "description": self._format_source_description(item)
                    }
                    
                    # Store full source detail for retrieval
                    self.source_storage[source_id] = source_detail
                    
                    # Create source entry for response (with ID for clickable functionality)
                    source_entry = {
                        "id": source_id,
                        "type": data_type,
                        "description": self._format_source_description(item),
                        "content": (item.get("content", "") or "")[:400],
                    }
                    sources.append(source_entry)
        else:
            log_info("Documents Retrieved", "0 (No data found)")
            print(f"{Colors.RED}⚠️  Warning: No data retrieved from ElasticSearch{Colors.ENDC}\n")
        
        # =====================================================================
        # STEP 4 — LLM RESPONSE GENERATION
        # ─────────────────────────────────────────────────────────────────────
        # [STANDARD RAG — STEP 4] Flat context → LLM.
        #   system_prompt: generic clinical assistant instructions
        #   user_prompt:   patient EHR context (demographics, conditions, obs, notes)
        #   LLM generates a direct answer — no differential diagnosis structure.
        #
        # [MEDRAG — STEP 4] KG-augmented context → LLM.
        #   Step 4a (system_prompt): MedRAG-specific instructions guiding differential
        #               diagnosis reasoning using the KG context block.
        #   Step 4b (user_prompt):   patient EHR context + KG differential diagnosis
        #               block injected ABOVE the LLM prompt (KG-elicited reasoning).
        #   The KG block contains: candidate diseases, supporting evidence per disease,
        #   distinguishing features (Tier 4), and missing data gaps → proactive questions.
        #   LLM is instructed to output: Most Likely Dx → Evidence → Alternatives →
        #               Missing Data → Clinical Recommendation.
        #   Toggle: set USE_MEDRAG = True/False at top of this file.
        # =====================================================================
        log_section(f"🤖 STEP 4 — LLM RESPONSE GENERATION ({'Standard RAG — flat context' if not USE_MEDRAG else 'MedRAG — KG-augmented context + differential diagnosis'})", Colors.CYAN)
        if retrieved_data:
            log_info("Context Size", f"{len(retrieved_data)} documents")
            log_info("Pipeline", "Standard RAG (Elasticsearch → LLM)" if not USE_MEDRAG else "MedRAG (Elasticsearch → KG → LLM)")
            log_info("Status", "Generating response...")
            print()
            response_text = self.generate_contextual_response(patient_id, query, retrieved_data, intent, context_hint=context_hint)
            log_info("Response Generated", "✓ Success")
            log_data("Response Preview", response_text[:150] + "..." if len(response_text) > 150 else response_text)
        else:
            log_info("Status", "No context available - generating fallback response")
            print()
            # Check if we can retrieve all available observations for this patient
            all_observations = self._get_all_available_observations(patient_id)
            if all_observations:
                obs_list = ", ".join(all_observations[:5])
                more_text = f" and {len(all_observations) - 5} more" if len(all_observations) > 5 else ""
                response_text = f"I couldn't find specific data related to '{query}' for this patient. However, the patient has the following observation data available: {obs_list}{more_text}. Would you like to see a visualization of these available observations?"
            else:
                # Extract the specific data type from query for clearer message
                query_lower = query.lower()
                data_type_keywords = {
                    "glucose": "glucose level",
                    "a1c": "hemoglobin A1C",
                    "hemoglobin a1c": "hemoglobin A1C",
                    "blood type": "blood type",
                    "creatinine": "creatinine level",
                    "blood pressure": "blood pressure",
                    "heart rate": "heart rate"
                }
                
                specific_data = None
                for keyword, label in data_type_keywords.items():
                    if keyword in query_lower:
                        specific_data = label
                        break
                
                if specific_data:
                    response_text = f"No {specific_data} data is available for this patient in the medical records."
                else:
                    response_text = f"No data related to your query is available for this patient in the medical records."
        
        # Append "N total readings" note when a targeted obs supplement was done
        if _targeted_obs_term and _total_targeted > 15:
            response_text += (
                f"\n\n[Note: {_total_targeted} total {_targeted_obs_term} readings in record"
                " — full timeline visible in the chart above.]"
            )

        # =====================================================================
        # STEP 5 — INTELLIGENT VISUALIZATION
        # ─────────────────────────────────────────────────────────────────────
        # [STANDARD RAG — STEP 5] Unchanged in both modes.
        #   Uses intent + response text to decide if a chart should be generated.
        #
        # [MEDRAG — STEP 5] Same visualization logic (unchanged).
        #   The MedRAG paper does not define a visualization component; this is
        #   a unique contribution of the FHIR dashboard system. Kept as-is.
        # =====================================================================
        log_section(f"📊 STEP 5 — INTELLIGENT VISUALIZATION (same in both RAG and MedRAG)", Colors.YELLOW)
        auto_chart = None
        # Pass answer_text to filter observations by relevance
        log_info("Intent for Visualization", f"type={intent.get('type')}, intent_type={intent.get('intent_type', 'N/A')}", Colors.CYAN)
        should_generate, chart_types = intelligent_viz_service.should_generate_visualization(query, intent, retrieved_data, answer_text=response_text)
        log_info("Should Generate", f"{should_generate}", Colors.CYAN)
        log_info("Chart Types", f"{chart_types}", Colors.CYAN)
        
        multi_charts: list = []  # additional DDx evidence charts (MedRAG only)

        if should_generate and chart_types:
            log_info("Visualization Detected", "✓ Yes")
            all_types = chart_types if isinstance(chart_types, list) else [chart_types]
            log_info("Chart Types", ", ".join(all_types))
            log_info("Status", "Generating visualization from retrieved_data...")
            print()

            # For MedRAG DDx hints, generate all hinted charts (primary + extras).
            # For all other cases, generate only the first chart type.
            ddx_hints = intent.get("ddx_chart_hints", [])
            types_to_generate = all_types if ddx_hints else all_types[:1]

            for idx, ct in enumerate(types_to_generate):
                try:
                    single_intent = dict(intent)
                    single_intent["ddx_chart_hints"] = [ct.split(":", 1)[1]] if ct.startswith("observation_trend:") and ddx_hints else []
                    logger.info(f"Attempting chart {idx+1}/{len(types_to_generate)}: {ct}")
                    chart_candidate = intelligent_viz_service.generate_smart_visualization(
                        patient_id, query, single_intent, retrieved_data, answer_text=response_text
                    )
                    if chart_candidate:
                        if idx == 0:
                            auto_chart = chart_candidate
                            log_info("Primary Chart", f"✓ {chart_candidate.get('type', 'unknown')}")
                            log_data("Data Points", len(chart_candidate.get("data", {}).get("datasets", [{}])[0].get("data", [])) if chart_candidate.get("data", {}).get("datasets") else 0)
                            log_data("Generation Reason", chart_candidate.get("generation_reason", "N/A"))
                            response_text = intelligent_viz_service.enhance_response_with_visualization_context(
                                response_text, auto_chart
                            )
                            if auto_chart.get("type") == "available_observations":
                                obs_names = auto_chart.get("generation_reason", "").split(": ")[-1] if ":" in auto_chart.get("generation_reason", "") else ""
                                if obs_names:
                                    response_text = f"I couldn't find the specific observation you asked about. However, I've found and visualized the following available observations for this patient: {obs_names}. The chart below shows these values over time."
                        else:
                            multi_charts.append(chart_candidate)
                            log_info(f"Extra Chart {idx}", f"✓ {chart_candidate.get('type', 'unknown')}")
                    else:
                        logger.warning(f"Chart generation returned None for type={ct}")
                        if idx == 0 and intent.get("type") == "analysis":
                            logger.error(f"CRITICAL: Analysis intent chart generation failed! Query: {query}, Chart types: {chart_types}")
                except Exception as e:
                    logger.error(f"Failed to generate chart type={ct}: {e}", exc_info=True)
                    if idx == 0 and intent.get("type") == "analysis" and "abnormal_values" in ct:
                        logger.warning("Retrying abnormal_values chart after error")
                        try:
                            auto_chart = intelligent_viz_service.viz_service._generate_abnormal_values_chart(patient_id, use_llm_detection=False)
                            if auto_chart:
                                logger.info("Successfully generated abnormal_values chart on retry")
                        except Exception as retry_error:
                            logger.error(f"Retry also failed: {retry_error}", exc_info=True)
        else:
            log_info("Visualization Detected", "✗ No (not needed for this query)")
            logger.info(f"Visualization not generated: should_generate={should_generate}, chart_types={chart_types}")
        
        print()
        
        # =====================================================================
        # STEP 6 — FOLLOW-UP OPTIONS
        # ─────────────────────────────────────────────────────────────────────
        # [STANDARD RAG — STEP 6] Generic follow-up options derived from intent
        #   and observed data types (e.g., "create glucose chart", "generate report").
        #   No clinical reasoning — options are data-type driven.
        #
        # [MEDRAG — STEP 6] KG-driven proactive diagnostic questions.
        #   If candidate diseases were identified, the KG generates targeted
        #   follow-up questions for MISSING observations needed to confirm or
        #   exclude each candidate diagnosis (Section 3.4 of the MedRAG paper).
        #   These are prepended to the standard follow-up options so the
        #   clinician is proactively guided toward closing diagnostic gaps.
        #   Toggle: USE_MEDRAG controls whether KG questions are included.
        # =====================================================================
        log_section(f"💡 STEP 6 — FOLLOW-UP OPTIONS ({'Standard RAG — generic options' if not USE_MEDRAG else 'MedRAG — KG proactive diagnostic questions + generic options'})", Colors.GRAY)

        if USE_MEDRAG:
            # ─────────────────────────────────────────────────────────────────
            # [MEDRAG — STEP 6] Proactive diagnostic questioning from KG.
            # Re-run the KG pipeline (lightweight — same data, no extra LLM call)
            # to get the follow-up questions based on missing evidence gaps.
            # ─────────────────────────────────────────────────────────────────
            try:
                kg_result_for_followup = kg_service.run_kg_pipeline(query, retrieved_data)
                kg_followup_questions = kg_result_for_followup.get("followup_questions", [])
                kg_candidates_for_followup = kg_result_for_followup.get("candidate_diseases", [])

                # Build KG-driven follow-up options (proactive diagnostic questions)
                kg_followup_options = []
                for q in kg_followup_questions[:3]:
                    kg_followup_options.append({
                        "text": f"🔬 {q}",
                        "type": "diagnostic_question",
                        "action": "kg_proactive_question"
                    })

                # Add standard follow-up options
                standard_followup = self.generate_follow_up_options(intent, retrieved_data)

                # Prepend KG questions so they appear first (most clinically important)
                follow_up_options = kg_followup_options + standard_followup

                if kg_candidates_for_followup:
                    log_info("KG Candidate Diseases", ", ".join(kg_candidates_for_followup[:3]))
                    log_info("KG Proactive Questions", len(kg_followup_options))
                    for idx, opt in enumerate(kg_followup_options, 1):
                        log_data(f"  KG-Q[{idx}]", opt.get("text", "")[:80])
            except Exception as kg_err:
                logger.warning(f"[MedRAG] KG follow-up generation failed: {kg_err} — falling back to standard follow-up")
                follow_up_options = self.generate_follow_up_options(intent, retrieved_data)
        else:
            # ─────────────────────────────────────────────────────────────────
            # [STANDARD RAG — STEP 6] Generic intent-based follow-up options.
            # No KG, no proactive diagnostic reasoning.
            # ─────────────────────────────────────────────────────────────────
            follow_up_options = self.generate_follow_up_options(intent, retrieved_data)

        log_info("Options Generated", len(follow_up_options))
        for idx, option in enumerate(follow_up_options[:3], 1):
            log_data(f"  [{idx}]", option.get("text", "")[:60] + "..." if len(option.get("text", "")) > 60 else option.get("text", ""))
        if len(follow_up_options) > 3:
            log_data("  ...", f"{len(follow_up_options) - 3} more options")
        print()
        
        # Store conversation context
        if patient_id not in self.conversation_context:
            self.conversation_context[patient_id] = []
        
        self.conversation_context[patient_id].append({
            "query": query,
            "intent": intent,
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
        
        # Final summary
        log_section("✅ QUERY COMPLETE", Colors.GREEN)
        data_found = len(retrieved_data) > 0
        retrieved_count = len(retrieved_data)
        
        log_info("Data Found", "✓ Yes" if data_found else "✗ No")
        log_info("Retrieved Count", retrieved_count)
        log_info("Sources Count", len(sources))
        log_info("Response Length", f"{len(response_text)} characters")
        log_info("Visualization Included", "✓ Yes" if auto_chart else "✗ No")
        if auto_chart:
            log_data("Chart Type", auto_chart.get("type", "unknown"))
        if multi_charts:
            log_info("Extra DDx Charts", len(multi_charts))
        print(f"{Colors.GREEN}{'='*80}{Colors.ENDC}\n")

        # Enhanced logging for research quality - ensure data integrity
        logger.info(f"Query complete for patient {patient_id}: retrieved_count={retrieved_count}, data_found={data_found}, sources={len(sources)}")

        # Validate that retrieved_count matches actual data
        if retrieved_count != len(retrieved_data):
            logger.error(f"DATA INTEGRITY ERROR: retrieved_count ({retrieved_count}) != len(retrieved_data) ({len(retrieved_data)})")
            retrieved_count = len(retrieved_data)

        return {
            "response": response_text,
            "follow_up_options": follow_up_options,
            "intent": intent,
            "data_found": data_found,
            "retrieved_count": retrieved_count,
            "sources": sources,
            "chart": auto_chart,                   # primary chart (always single dict or None)
            "multi_chart": multi_charts or None,   # extra DDx evidence charts (MedRAG only)
            "pipeline_mode": "MedRAG + KG" if USE_MEDRAG else "Standard RAG"  # A/B comparison label
        }
    
    def _format_source_description(self, item: Dict[str, Any]) -> str:
        """Format a source item into a readable description with proof information"""
        data_type = item.get("data_type", "unknown")
        display = item.get("display", "")
        value = item.get("value", "")
        unit = item.get("unit", "")
        date = item.get("date", "")
        code = item.get("code", "")
        filename = item.get("filename", "")  # For notes
        
        # Build detailed proof description
        parts = []
        
        if data_type in ("observation", "observations"):
            if display:
                parts.append(f"Observation: {display}")
            if value:
                unit_str = f" {unit}" if unit and unit != "unit" else ""
                parts.append(f"Value: {value}{unit_str}")
            if code:
                parts.append(f"Code: {code}")
            if date:
                parts.append(f"Date: {str(date)[:10]}")
            if not parts:
                parts.append("Observation data")

        elif data_type in ("condition", "conditions"):
            if display:
                parts.append(f"Condition: {display}")
            if code:
                parts.append(f"Code: {code}")
            if date:
                parts.append(f"Date: {str(date)[:10]}")
            if not parts:
                parts.append("Condition data")

        elif data_type in ("note", "notes"):
            parts.append("Clinical Note")
            if filename:
                parts.append(f"File: {filename}")
            if date:
                parts.append(f"Date: {str(date)[:10]}")

        elif data_type == "demographics":
            parts.append("Patient Demographics")
            if display:
                parts.append(display)
        else:
            parts.append(f"{data_type} data")
        
        return " | ".join(parts)
    
    def get_conversation_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a patient"""
        return self.conversation_context.get(patient_id, [])
    
    def _get_all_available_observations(self, patient_id: str) -> List[str]:
        """Get list of all available observation types for a patient"""
        if not self.es_client.is_connected():
            return []
        
        try:
            # Search for all observations for this patient
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"patient_id": patient_id}},
                            {"term": {"data_type": "observations"}}
                        ]
                    }
                },
                "size": 100,
                "_source": ["metadata.display"]
            }
            
            response = self.es_client.client.search(index="patient_data", body=search_body)
            
            observation_types = set()
            for hit in response["hits"]["hits"]:
                # Safely handle missing _source key
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    continue
                metadata = source.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                display = metadata.get("display", "")
                if display:
                    # Clean up display name
                    clean_display = display.replace("Observation: ", "").split(":")[0].strip()
                    if clean_display and len(clean_display) > 2:
                        observation_types.add(clean_display)
            
            return sorted(list(observation_types))
            
        except Exception as e:
            logger.error(f"Failed to get available observations: {e}")
            return []
    
    def clear_conversation_history(self, patient_id: str) -> bool:
        """Clear conversation history for a patient"""
        if patient_id in self.conversation_context:
            del self.conversation_context[patient_id]
            return True
        return False
    
    def get_source_detail(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed source information by source ID for verification"""
        return self.source_storage.get(source_id)
    
    def cleanup_old_sources(self, max_age_hours: int = 24):
        """Clean up old source storage entries (optional, for memory management)"""
        # This can be called periodically to clean up old sources
        # For now, we keep all sources (can be enhanced later if needed)
        pass

# Global instance
rag_service = RAGService()
