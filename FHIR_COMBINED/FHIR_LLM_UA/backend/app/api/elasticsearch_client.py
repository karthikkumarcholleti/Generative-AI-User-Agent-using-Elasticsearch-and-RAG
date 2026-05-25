# backend/app/api/elasticsearch_client.py

import os
import json
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, ConnectionError
import logging

logger = logging.getLogger(__name__)

# Import embedding service for semantic search
try:
    from .embedding_service import get_embedding_service
    EMBEDDING_SERVICE_AVAILABLE = True
except Exception as e:
    # Catch all exceptions to prevent backend crash if embedding service fails
    EMBEDDING_SERVICE_AVAILABLE = False
    logger.warning(f"Embedding service not available ({type(e).__name__}: {e}). Semantic search will be disabled.")
    logger.warning("Embedding service not available. Semantic search will be disabled.")

# Import LOINC code mapper for handling NULL display names
try:
    from .loinc_code_mapper import enhance_observation_content, get_observation_display_from_code
    LOINC_MAPPER_AVAILABLE = True
except ImportError:
    LOINC_MAPPER_AVAILABLE = False
    logger.warning("LOINC code mapper not available. NULL display names may not be handled optimally.")

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

class ElasticSearchClient:
    """ElasticSearch client for patient data indexing and retrieval with semantic search support"""
    
    def __init__(self):
        self.es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
        self.es_port = os.getenv("ELASTICSEARCH_PORT", "9200")
        self.es_username = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
        self.es_password = os.getenv("ELASTICSEARCH_PASSWORD", "P@ssw0rd")
        self.es_use_ssl = os.getenv("ELASTICSEARCH_USE_SSL", "false").lower() == "true"
        self.es_security_enabled = os.getenv("ELASTICSEARCH_SECURITY_ENABLED", "false").lower() == "true"
        
        # Use HTTP if security is disabled, HTTPS if enabled
        protocol = "https" if self.es_use_ssl else "http"
        self.es_url = f"{protocol}://{self.es_host}:{self.es_port}"
        
        # Initialize embedding service for semantic search
        self.embedding_service = None
        self.semantic_search_enabled = False
        if EMBEDDING_SERVICE_AVAILABLE:
            try:
                self.embedding_service = get_embedding_service()
                if self.embedding_service.is_available():
                    self.semantic_search_enabled = True
                    logger.info("Semantic search enabled with embedding service")
                else:
                    logger.warning("Embedding service not available. Semantic search disabled.")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding service: {e}. Semantic search disabled.")
        
        try:
            # Configure client based on security settings
            client_kwargs = {
                "hosts": [self.es_url],
                "request_timeout": 60,
                "max_retries": 3,
                "retry_on_timeout": True
            }
            
            # Add authentication only if security is enabled
            if self.es_security_enabled:
                client_kwargs["basic_auth"] = (self.es_username, self.es_password)
                if self.es_use_ssl:
                    client_kwargs["verify_certs"] = False
                    client_kwargs["ssl_show_warn"] = False
            
            self.client = Elasticsearch(**client_kwargs)
            
            # Test connection
            if self.client.ping():
                logger.info(f"Connected to ElasticSearch at {self.es_url} (security: {self.es_security_enabled})")
            else:
                logger.warning(f"ElasticSearch connection failed at {self.es_url}")
                self.client = None
        except Exception as e:
            logger.error(f"Failed to connect to ElasticSearch: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if ElasticSearch is connected"""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False
    
    def create_patient_index(self, index_name: str = "patient_data") -> bool:
        """Create ElasticSearch index for patient data"""
        if not self.is_connected():
            logger.error("ElasticSearch not connected")
            return False
        
        try:
            # Check if index exists
            if self.client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} already exists")
                return True
            
            # Get embedding dimension if semantic search is enabled
            embedding_dim = 384  # Default
            if self.semantic_search_enabled and self.embedding_service:
                embedding_dim = self.embedding_service.get_embedding_dimension()
            
            # Create index with mapping (including dense_vector for semantic search)
            # Set number_of_replicas to 0 for single-node cluster to avoid unassigned shards
            mapping = {
                "settings": {
                    "number_of_replicas": 0,  # Single node cluster - no replicas needed
                    "number_of_shards": 1     # Single shard for simplicity
                },
                "mappings": {
                    "properties": {
                        "enterprise_patient_id": {"type": "keyword"},
                        "patient_name": {"type": "text"},
                        "data_type": {"type": "keyword"},  # demographics, conditions, observations, notes
                        "content": {"type": "text"},
                        # Add dense_vector field for semantic search
                        "embedding": {
                            "type": "dense_vector",
                            "dims": embedding_dim,
                            "index": True,  # Enable kNN search
                            "similarity": "cosine"  # Use cosine similarity for semantic search
                        },
                        "metadata": {
                            "properties": {
                                "code": {"type": "keyword"},
                                "display": {"type": "text"},
                                "value": {"type": "text"},
                                "unit": {"type": "keyword"},
                                "date": {"type": "date"},
                                "status": {"type": "keyword"}
                            }
                        },
                        "timestamp": {"type": "date"}
                    }
                }
            }
            
            self.client.indices.create(index=index_name, body=mapping)
            logger.info(f"Created ElasticSearch index: {index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False
    
    def _add_embedding_to_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add embedding to document if semantic search is enabled.
        
        Args:
            doc: Document dictionary with 'content' field
            
        Returns:
            Document with 'embedding' field added if semantic search is enabled
        """
        if self.semantic_search_enabled and self.embedding_service and "content" in doc:
            try:
                embedding = self.embedding_service.generate_embedding(doc["content"])
                doc["embedding"] = embedding
            except Exception as e:
                logger.warning(f"Failed to generate embedding for document: {e}")
        return doc
    
    def index_patient_data(self, patient_id: str, patient_data: Dict[str, Any], index_name: str = "patient_data", generate_embeddings: bool = False) -> bool:
        """
        Index patient data into ElasticSearch with optional semantic search support.
        
        Args:
            patient_id: Patient ID
            patient_data: Patient data dictionary
            index_name: ElasticSearch index name
            generate_embeddings: If True, generate embeddings (slower but enables semantic search).
                                If False, index without embeddings (faster, like old setup).
        """
        if not self.is_connected():
            logger.error("ElasticSearch not connected")
            return False
        
        try:
            # Create index if it doesn't exist
            if not self.client.indices.exists(index=index_name):
                self.create_patient_index(index_name)
            
            # Collect all documents for bulk indexing
            bulk_docs = []
            patient_name = patient_data.get("demographics", {}).get("name", "Unknown")
            
            # Index demographics
            if "demographics" in patient_data:
                demo = patient_data["demographics"]
                doc = {
                    "enterprise_patient_id": patient_id,
                    "patient_name": patient_name,
                    "data_type": "demographics",
                    "content": f"Patient {patient_name} - Age: {demo.get('ageYears', 'Unknown')}, Gender: {demo.get('gender', 'Unknown')}, Location: {demo.get('city', 'Unknown')}, {demo.get('state', 'Unknown')}",
                    "metadata": {
                        "age": demo.get("ageYears"),
                        "gender": demo.get("gender"),
                        "city": demo.get("city"),
                        "state": demo.get("state"),
                        "postal_code": demo.get("postalCode")
                    },
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                if generate_embeddings:
                    doc = self._add_embedding_to_doc(doc)  # Add embedding only if requested
                bulk_docs.append({"index": {"_index": index_name}})
                bulk_docs.append(doc)
            
            # Index conditions
            if "conditions" in patient_data:
                for condition in patient_data["conditions"]:
                    doc = {
                        "enterprise_patient_id": patient_id,
                        "patient_name": patient_name,
                        "data_type": "conditions",
                        "content": f"Condition: {condition.get('display', 'Unknown')} - Status: {condition.get('clinicalStatus', 'Unknown')}",
                        "metadata": {
                            "code": condition.get("code"),
                            "display": condition.get("display"),
                            "status": condition.get("clinicalStatus"),
                            "date": condition.get("recordedDate")
                        },
                        "timestamp": condition.get("recordedDate", "2024-01-01T00:00:00Z")
                    }
                    if generate_embeddings:
                        doc = self._add_embedding_to_doc(doc)  # Add embedding only if requested
                    bulk_docs.append({"index": {"_index": index_name}})
                    bulk_docs.append(doc)
            
            # Index observations
            if "observations" in patient_data:
                for observation in patient_data["observations"]:
                    value_str = ""
                    if observation.get("valueNumber") is not None:
                        value_str = f"{observation['valueNumber']}"
                        if observation.get("unit"):
                            value_str += f" {observation['unit']}"
                    elif observation.get("valueString"):
                        value_str = observation["valueString"]
                    
                    # Enhanced content generation: handles NULL display names using LOINC codes
                    if LOINC_MAPPER_AVAILABLE:
                        content = enhance_observation_content(observation)
                        # Also enhance display in metadata if it's NULL
                        display = observation.get("display")
                        if not display and observation.get("code"):
                            display = get_observation_display_from_code(observation.get("code"))
                    else:
                        content = f"Observation: {observation.get('display', 'Unknown')} - Value: {value_str}"
                        display = observation.get("display")
                    
                    doc = {
                        "enterprise_patient_id": patient_id,
                        "patient_name": patient_name,
                        "data_type": "observations",
                        "content": content,
                        "metadata": {
                            "code": observation.get("code"),
                            "display": display,  # Enhanced display (from LOINC mapper if NULL)
                            "value": value_str,
                            "unit": observation.get("unit"),
                            "date": observation.get("effectiveDateTime")
                        },
                        "timestamp": observation.get("effectiveDateTime", "2024-01-01T00:00:00Z")
                    }
                    if generate_embeddings:
                        doc = self._add_embedding_to_doc(doc)  # Add embedding only if requested
                    bulk_docs.append({"index": {"_index": index_name}})
                    bulk_docs.append(doc)
            
            # Index notes
            if "notes" in patient_data:
                for note in patient_data["notes"]:
                    if note.get("text"):
                        doc = {
                            "enterprise_patient_id": patient_id,
                            "patient_name": patient_name,
                            "data_type": "notes",
                            "content": note.get('text', ''),  # Full note - no truncation (Hybrid Approach)
                            "metadata": {
                                "source_type": note.get("sourceType"),
                                "filename": note.get("fileName"),
                                "date": note.get("created")
                            },
                            "timestamp": note.get("created", "2024-01-01T00:00:00Z")
                        }
                        if generate_embeddings:
                            doc = self._add_embedding_to_doc(doc)  # Add embedding only if requested
                        bulk_docs.append({"index": {"_index": index_name}})
                        bulk_docs.append(doc)
            
            # Index encounters (available in cocm_db)
            if "encounters" in patient_data:
                for encounter in patient_data["encounters"]:
                    encounter_type = encounter.get("typeDisplay") or encounter.get("typeCode") or encounter.get("classDisplay") or encounter.get("classCode") or "Unknown"
                    date_str = ""
                    if encounter.get("date"):
                        date_str = f" on {encounter.get('date', '')[:10]}"
                    
                    doc = {
                        "enterprise_patient_id": patient_id,
                        "patient_name": patient_name,
                        "data_type": "encounters",
                        "content": f"Encounter: {encounter_type} - Class: {encounter.get('classDisplay', encounter.get('classCode', 'Unknown'))}{date_str}",
                        "metadata": {
                            "class_code": encounter.get("classCode"),
                            "class_display": encounter.get("classDisplay"),
                            "type_code": encounter.get("typeCode"),
                            "type_display": encounter.get("typeDisplay"),
                            "date": encounter.get("date"),
                            "admission_reason": encounter.get("admissionReason"),
                            "source_type": encounter.get("sourceType")
                        },
                        "timestamp": encounter.get("date", "2024-01-01T00:00:00Z")
                    }
                    if generate_embeddings:
                        doc = self._add_embedding_to_doc(doc)  # Add embedding only if requested
                    bulk_docs.append({"index": {"_index": index_name}})
                    bulk_docs.append(doc)
            
            # Index documents individually (like old setup - more reliable)
            # This matches your old working setup exactly
            indexed_count = 0
            failed_count = 0
            
            for i in range(0, len(bulk_docs), 2):
                if i + 1 < len(bulk_docs):
                    doc = bulk_docs[i + 1]
                    try:
                        self.client.index(index=index_name, body=doc)
                        indexed_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to index document {i//2 + 1} for patient {patient_id}: {e}")
            
            if failed_count > 0:
                logger.warning(f"Indexed {indexed_count} documents, {failed_count} failed for patient {patient_id}")
            else:
                logger.info(f"Indexed {indexed_count} documents for patient {patient_id} (embeddings: {generate_embeddings})")
            
            # Refresh index to make documents searchable
            self.client.indices.refresh(index=index_name)
            logger.info(f"Indexed data for patient {patient_id}")
            return indexed_count > 0
            
        except Exception as e:
            logger.error(f"Failed to index patient data for {patient_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    # REMOVED: Manual synonym expansion
    # Semantic search with vector embeddings automatically handles related concepts
    # No need for type-coded manual dictionaries - semantic search is more research-worthy
    
    def search_patient_data(self, patient_id: str, query: str, data_types: List[str] = None, index_name: str = "patient_data", use_highlighting: bool = True) -> List[Dict[str, Any]]:
        """
        Search patient data using ElasticSearch with hybrid approach:
        - Keyword search: Fuzzy matching, phrase matching, field boosting
        - Semantic search: Vector similarity using embeddings (kNN)
        
        This combines the best of both approaches for comprehensive retrieval.
        """
        if not self.is_connected():
            logger.error("ElasticSearch not connected")
            return []
        
        try:
            # Generate embedding for semantic search (if enabled)
            # Semantic search automatically finds related concepts - no manual synonyms needed!
            query_embedding = None
            if self.semantic_search_enabled and self.embedding_service:
                try:
                    query_embedding = self.embedding_service.generate_embedding(query)
                    logger.debug("Generated query embedding for semantic search")
                except Exception as e:
                    logger.warning(f"Failed to generate query embedding: {e}. Continuing with keyword search only.")
            
            # Build hybrid ElasticSearch query (keyword + semantic)
            # must  → hard filter: only this patient's documents
            # should → BM25 relevance scoring (optional — no minimum_should_match)
            #          Documents that keyword-match rank higher; all patient docs are eligible
            should_clauses = []
            if query and query.strip():
                should_clauses = [
                    # Exact phrase in content — highest boost
                    {"match_phrase": {"content": {"query": query, "boost": 5.0}}},
                    # Exact phrase in display field
                    {"match_phrase": {"display": {"query": query, "boost": 4.0}}},
                    # Multi-field fuzzy match across searchable text fields
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "content^3.0",
                                "display^2.5",
                                "code^1.5",
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                            "operator": "or",
                        }
                    },
                    # Phrase match across fields (terms must appear together)
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["content^3.0", "display^2.5"],
                            "type": "phrase",
                        }
                    },
                ]

                # LOINC code boosting: when query contains clinical terms like "creatinine",
                # boost docs by LOINC code so they rank high even if content tokenization fails.
                # The ES content field uses LOINC long names (e.g. "CREATININE:MCNC:PT:SER/PLAS:QN:")
                # which the English analyzer may not tokenize to match plain "creatinine".
                try:
                    from .loinc_code_mapper import get_loinc_codes_for_query
                    loinc_hits = get_loinc_codes_for_query(query)
                    if loinc_hits:
                        should_clauses.append({
                            "terms": {"code": loinc_hits, "boost": 8.0}
                        })
                        logger.debug(f"LOINC code boost applied for codes: {loinc_hits}")
                except ImportError:
                    pass

            search_body = {
                "query": {
                    "bool": {
                        # patient_id is the only hard requirement — every doc for this patient
                        # is a candidate; BM25 should clauses rank by relevance, not gate
                        "must": [{"term": {"enterprise_patient_id": patient_id}}],
                        "should": should_clauses,
                        # NO minimum_should_match — should clauses are scoring bonuses only.
                        # This ensures observations/notes with short content still surface.
                    }
                },
                "size": 150,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"effective_date": {"order": "desc", "missing": "_last", "unmapped_type": "date"}},
                    {"_doc": {"order": "asc"}},
                ],
            }
            
            # Add semantic search (kNN) if embeddings are available
            # Check if embedding field exists in index first
            if query_embedding:
                try:
                    # Check if index has embedding field
                    index_mapping = self.client.indices.get_mapping(index=index_name)
                    has_embedding_field = False
                    if index_name in index_mapping:
                        properties = index_mapping[index_name].get("mappings", {}).get("properties", {})
                        has_embedding_field = "embedding" in properties
                    
                    if has_embedding_field:
                        # Prioritize semantic search - higher boost and more results
                        search_body["knn"] = {
                            "field": "embedding",
                            "query_vector": query_embedding,
                            "k": 20,  # More nearest neighbors for semantic search
                            "num_candidates": 200,  # More candidates to consider
                            "boost": 5.0,  # Higher boost to prioritize semantic results over keyword
                            "filter": {
                                "term": {"enterprise_patient_id": patient_id}
                            }
                        }
                        # Add data type filter to kNN if specified
                        if data_types:
                            search_body["knn"]["filter"] = {
                                "bool": {
                                    "must": [
                                        {"term": {"enterprise_patient_id": patient_id}},
                                        {"terms": {"data_type": data_types}}
                                    ]
                                }
                            }
                        logger.debug("Added kNN semantic search to query")
                    else:
                        logger.warning("embedding field not found in index. Using keyword search only. Reindex data to enable semantic search.")
                except Exception as e:
                    logger.warning(f"Could not check index mapping for semantic search: {e}. Using keyword search only.")
            
            # Add data type filter if specified.
            # Normalize plural forms (legacy rag_service convention) → singular (index values).
            _PLURAL_TO_SINGULAR = {
                "conditions": "condition",
                "observations": "observation",
                "notes": "note",
                "encounters": "encounter",
                "demographics": "demographics",  # kept as-is (no plural form used)
            }
            if data_types:
                normalized = [_PLURAL_TO_SINGULAR.get(t, t) for t in data_types]
                if "filter" not in search_body["query"]["bool"]:
                    search_body["query"]["bool"]["filter"] = []
                search_body["query"]["bool"]["filter"].append(
                    {"terms": {"data_type": normalized}}
                )
            
            # Add highlighting to extract relevant snippets (Intelligent RAG - Hybrid Approach)
            # This makes RAG actually valuable - extracts relevant parts, not just dumps full documents
            # Can be disabled for fallback to full documents (old method)
            if use_highlighting and query and query.strip():  # Only highlight if enabled and there's a query
                search_body["highlight"] = {
                    "fields": {
                        "content": {
                            "fragment_size": 1000,        # Larger context (vs 500) - Hybrid Approach
                            "number_of_fragments": 5,     # More snippets (vs 3) - Hybrid Approach
                            "fragmenter": "sentence",     # Sentence-aware - keeps sentences intact
                            "boundary_scanner": "sentence", # Don't break sentences - Hybrid Approach
                            "type": "unified",            # Best highlighting algorithm
                            "pre_tags": [""],             # No HTML tags (clean text)
                            "post_tags": [""]
                        }
                    }
                }
            
            # Log the search query being executed
            import json
            query_str = json.dumps(search_body, indent=2)
            print(f"{Colors.GRAY}  ElasticSearch Query Body:{Colors.ENDC}")
            print(f"{Colors.GRAY}{query_str[:200]}...{Colors.ENDC}\n" if len(query_str) > 200 else f"{Colors.GRAY}{query_str}{Colors.ENDC}\n")
            
            response = self.client.search(index=index_name, body=search_body)
            
            results = []
            for hit in response["hits"]["hits"]:
                # Intelligent RAG: Use highlights (relevant snippets) if available and enabled
                # This makes RAG actually valuable - extracts relevant parts, not just dumps full documents
                # If highlighting is disabled (fallback mode), always use full content
                if use_highlighting:
                    highlights = hit.get("highlight", {}).get("content", [])
                    if highlights:
                        # Combine snippets with separator - RAG curates information
                        content = " ... ".join(highlights)
                        # Remove HTML highlighting tags if present (clean text)
                        content = content.replace("<em>", "").replace("</em>", "")
                    else:
                        # Fallback to full content if no highlights (e.g., empty query, short document)
                        content = hit.get("_source", {}).get("content", "")
                else:
                    # Highlighting disabled - use full content (old method, fallback)
                    content = hit.get("_source", {}).get("content", "")
                
                src = hit.get("_source", {})
                results.append({
                    "score": hit["_score"],
                    "data_type": src.get("data_type", "unknown"),
                    "content": content,
                    # Surface top-level fields so rag_service can build context
                    "display": src.get("display"),
                    "code": src.get("code"),
                    "value_numeric": src.get("value_numeric"),
                    "unit": src.get("unit"),
                    "ref_range_low": src.get("ref_range_low"),
                    "ref_range_high": src.get("ref_range_high"),
                    "clinical_status": src.get("clinical_status"),
                    "icd_code": src.get("icd_code"),
                    "source_hospital": src.get("source_hospital"),
                    "source_type": src.get("source_type"),
                    # timestamp field normalized to effective_date for rag_service sorting
                    "timestamp": src.get("effective_date") or src.get("note_date") or "",
                    "metadata": {},  # kept for compat; real data is now at top level
                })
            
            # Log search results summary
            total_hits = response["hits"]["total"]["value"] if isinstance(response["hits"]["total"], dict) else response["hits"]["total"]
            print(f"{Colors.GREEN}  ✓ ElasticSearch returned {total_hits} total hits, {len(results)} documents retrieved{Colors.ENDC}\n")
            
            logger.info(f"Found {len(results)} results for patient {patient_id} query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search patient data: {e}")
            return []
    
    def get_patient_summary(self, patient_id: str, index_name: str = "patient_data") -> Dict[str, Any]:
        """Get a comprehensive summary of all patient data"""
        if not self.is_connected():
            logger.error("ElasticSearch not connected")
            return {}
        
        try:
            # Get all data for the patient
            search_body = {
                "query": {"term": {"enterprise_patient_id": patient_id}},
                "size": 1000,
                "sort": [{"effective_date": {"order": "desc", "missing": "_last", "unmapped_type": "date"}}],
            }

            response = self.client.search(index=index_name, body=search_body)

            summary = {
                "enterprise_patient_id": patient_id,
                "total_documents": response["hits"]["total"]["value"],
                "data_types": {},
                "recent_observations": [],
                "conditions": [],
                "notes": [],
            }

            for hit in response["hits"]["hits"]:
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    continue
                data_type = source.get("data_type", "unknown")

                summary["data_types"][data_type] = summary["data_types"].get(data_type, 0) + 1

                if data_type == "observation" and len(summary["recent_observations"]) < 10:
                    summary["recent_observations"].append({
                        "display": source.get("display"),
                        "value": source.get("value_numeric"),
                        "unit": source.get("unit"),
                        "date": source.get("effective_date"),
                    })
                elif data_type == "condition":
                    summary["conditions"].append({
                        "display": source.get("content") or source.get("display"),
                        "status": source.get("clinical_status"),
                        "date": source.get("effective_date"),
                    })
                elif data_type == "note" and len(summary["notes"]) < 5:
                    summary["notes"].append({
                        "content": source.get("content"),
                        "source_type": source.get("source_type"),
                        "date": source.get("note_date") or source.get("effective_date"),
                    })
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get patient summary: {e}")
            return {}
    
    # ES indexes documents with singular data_type values; callers may pass plural.
    _DATA_TYPE_MAP = {
        "observations": "observation",
        "conditions": "condition",
        "notes": "note",
        "encounters": "encounter",
    }

    def get_all_patient_data_by_type(
        self,
        patient_id: str,
        data_type: str,
        size: int = 300,
        index_name: str = "patient_data",
    ) -> List[Dict[str, Any]]:
        """
        Fetch ALL ES documents of a specific data_type for a patient.
        Normalises plural caller names (observations → observation) and avoids
        sorting on nonexistent mapped fields; date ordering is done in Python.
        """
        if not self.is_connected():
            logger.warning("ES not connected — get_all_patient_data_by_type returning empty")
            return []
        # Normalise plural → singular (ES indexes use singular values)
        es_type = self._DATA_TYPE_MAP.get(data_type, data_type)
        try:
            body = {
                "query": {"bool": {"must": [
                    {"term": {"enterprise_patient_id": patient_id}},
                    {"term": {"data_type": es_type}},
                ]}},
                "size": size,
            }
            response = self.client.search(index=index_name, body=body)
            hits = response["hits"]["hits"]
            docs = [h["_source"] for h in hits]
            # Sort by date descending in Python (avoids ES fielddata issues on text fields)
            def _doc_date(d):
                return (d.get("effective_datetime") or d.get("effective_date") or
                        d.get("note_date") or d.get("onset_datetime") or "")
            docs.sort(key=_doc_date, reverse=True)
            logger.info(
                "get_all_patient_data_by_type: patient=%s type=%s(%s) → %d docs",
                patient_id, data_type, es_type, len(docs),
            )
            return docs
        except Exception as e:
            logger.error("get_all_patient_data_by_type failed: %s", e)
            return []

    def delete_patient_data(self, patient_id: str, index_name: str = "patient_data") -> bool:
        """Delete all data for a specific patient"""
        if not self.is_connected():
            logger.error("ElasticSearch not connected")
            return False
        
        try:
            # Delete by query
            delete_body = {
                "query": {
                    "term": {"enterprise_patient_id": patient_id}
                }
            }

            response = self.client.delete_by_query(index=index_name, body=delete_body)
            logger.info(f"Deleted {response['deleted']} documents for patient {patient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete patient data: {e}")
            return False
    
    def get_indexing_status(self, index_name: str = "patient_data") -> Dict[str, Any]:
        """
        Get indexing status: number of unique patients indexed, total documents, etc.
        
        Returns:
            Dict with:
            - index_exists: bool
            - total_documents: int
            - unique_patients: int
            - has_embeddings: bool (checks if index has embedding field)
        """
        if not self.is_connected():
            return {
                "index_exists": False,
                "total_documents": 0,
                "unique_patients": 0,
                "has_embeddings": False,
                "elasticsearch_connected": False
            }
        
        try:
            # Check if index exists
            index_exists = self.client.indices.exists(index=index_name)
            
            if not index_exists:
                return {
                    "index_exists": False,
                    "total_documents": 0,
                    "unique_patients": 0,
                    "has_embeddings": False,
                    "elasticsearch_connected": True
                }
            
            # Get total document count
            count_response = self.client.count(index=index_name)
            total_documents = count_response.get("count", 0)
            
            # Get unique patient count using terms aggregation (more accurate than cardinality)
            # Cardinality can have precision issues, terms gives exact count
            agg_body = {
                "size": 0,
                "aggs": {
                    "unique_patients_terms": {
                        "terms": {
                            "field": "enterprise_patient_id",
                            "size": 10000  # Get all unique patient IDs (supports up to 10k)
                        }
                    }
                }
            }
            
            agg_response = self.client.search(index=index_name, body=agg_body)
            # Count unique patient IDs from terms aggregation buckets (exact count)
            unique_patients_buckets = agg_response.get("aggregations", {}).get("unique_patients_terms", {}).get("buckets", [])
            unique_patients = len(unique_patients_buckets)
            
            # Check if index has embeddings field
            mapping = self.client.indices.get_mapping(index=index_name)
            has_embeddings = False
            if index_name in mapping:
                props = mapping[index_name].get("mappings", {}).get("properties", {})
                has_embeddings = "embedding" in props
            
            return {
                "index_exists": True,
                "total_documents": total_documents,
                "unique_patients": int(unique_patients),
                "has_embeddings": has_embeddings,
                "elasticsearch_connected": True
            }
            
        except Exception as e:
            logger.error(f"Failed to get indexing status: {e}")
            return {
                "index_exists": False,
                "total_documents": 0,
                "unique_patients": 0,
                "has_embeddings": False,
                "elasticsearch_connected": True,
                "error": str(e)
            }

# Global instance
es_client = ElasticSearchClient()
