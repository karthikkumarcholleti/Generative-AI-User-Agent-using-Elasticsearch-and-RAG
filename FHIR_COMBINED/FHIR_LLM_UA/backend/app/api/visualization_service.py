# backend/app/api/visualization_service.py

import json
from typing import List, Dict, Any, Optional
from .elasticsearch_client import es_client
from .observation_categorizer import group_observations_by_category, categorize_observation, get_category_display_name
import logging

logger = logging.getLogger(__name__)

class VisualizationService:
    """Service for generating chart data and visualizations"""
    
    def __init__(self):
        self.es_client = es_client
    
    def extract_observation_data(self, patient_id: str, observation_type: str) -> List[Dict[str, Any]]:
        """Extract observation data for a specific type"""
        if not self.es_client.is_connected():
            logger.warning("ElasticSearch not connected")
            return []
        
        # Safely handle None observation_type
        if not observation_type or not isinstance(observation_type, str):
            logger.warning(f"Invalid observation_type: {observation_type}")
            return []
        
        try:
            # Build more specific search queries based on observation type
            search_queries = []
            # Safely handle None observation_type
            observation_type = observation_type or ""
            observation_type_lower = observation_type.lower() if isinstance(observation_type, str) else ""
            
            if observation_type_lower == "heart rate":
                # Unified multi-field search
                search_queries = [
                    {
                        "multi_match": {
                            "query": "heart rate",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "multi_match": {
                            "query": "pulse",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields"
                        }
                    },
                    {"term": {"metadata.code": "8867-4"}}  # LOINC code for heart rate
                ]
            elif observation_type_lower == "blood pressure":
                # Unified multi-field search
                search_queries = [
                    {
                        "multi_match": {
                            "query": "blood pressure",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "multi_match": {
                            "query": "systolic",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields"
                        }
                    },
                    {
                        "multi_match": {
                            "query": "diastolic",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields"
                        }
                    },
                    {"term": {"metadata.code": "8480-6"}},  # Systolic BP
                    {"term": {"metadata.code": "8462-4"}}   # Diastolic BP
                ]
            elif observation_type_lower == "temperature":
                search_queries = [
                    {"match_phrase": {"metadata.display": "temperature"}},
                    {"match_phrase": {"metadata.display": "temp"}},
                    {"match_phrase": {"content": "temperature"}}
                ]
            elif observation_type_lower == "glucose":
                # Unified multi-field search
                search_queries = [
                    {
                        "multi_match": {
                            "query": "glucose",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "multi_match": {
                            "query": "blood sugar",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {"term": {"metadata.code": "2339-0"}}  # LOINC code for glucose
                ]
            elif observation_type_lower == "creatinine":
                # Unified multi-field search: searches display, code, AND content simultaneously
                # This finds creatinine in: observations with display names, observations with NULL display (via code),
                # and notes/other content that mentions creatinine
                search_queries = [
                    {
                        "multi_match": {
                            "query": "creatinine",
                            "fields": [
                                "metadata.display^3.0",  # High boost for display (when exists)
                                "content^2.5",           # High boost for content (notes, enhanced content)
                                "metadata.code^2.0"       # Boost for codes (handles NULL display)
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                            "operator": "or"
                        }
                    },
                    # Also include specific LOINC codes for comprehensive coverage
                    {"term": {"metadata.code": "2160-0"}},  # LOINC code for creatinine
                    {"term": {"metadata.code": "33914-3"}}  # Alternative creatinine code
                ]
            elif observation_type_lower == "hemoglobin":
                # Unified multi-field search
                search_queries = [
                    {
                        "multi_match": {
                            "query": "hemoglobin",
                            "fields": [
                                "metadata.display^3.0",
                                "content^2.5",
                                "metadata.code^2.0"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {"term": {"metadata.code": "718-7"}}  # LOINC code for hemoglobin
                ]
            elif observation_type_lower == "glomerular filtration":
                search_queries = [
                    {"match": {"metadata.display": "glomerular filtration"}},
                    {"match": {"metadata.display": "GFR"}},
                    {"match": {"content": "glomerular filtration"}}
                ]
            else:
                # Generic unified multi-field search for other observation types
                # Searches display, code, AND content simultaneously
                search_queries = [
                    {
                        "multi_match": {
                            "query": observation_type,
                            "fields": [
                                "metadata.display^3.0",  # High boost for display (when exists)
                                "content^2.5",           # High boost for content (notes, enhanced content)
                                "metadata.code^2.0"      # Boost for codes (handles NULL display)
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                            "operator": "or"
                        }
                    }
                ]
            
            # Build search body with specific queries
            # Use semantic search if available for better results
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"patient_id": patient_id}},
                            {"term": {"data_type": "observations"}},
                            {"bool": {"should": search_queries}}
                        ]
                    }
                },
                "size": 500,  # Increased to get more data points
                "sort": [{"timestamp": {"order": "asc"}}]
            }
            
            # Add semantic search (kNN) if embeddings are available
            # This helps find observations even with NULL display names or unmapped codes
            if self.es_client.semantic_search_enabled and self.es_client.embedding_service:
                try:
                    # Generate embedding for the observation type query
                    query_embedding = self.es_client.embedding_service.generate_embedding(observation_type)
                    
                    # Check if index has content_embedding field
                    index_mapping = self.es_client.client.indices.get_mapping(index="patient_data")
                    has_embedding_field = False
                    if "patient_data" in index_mapping:
                        properties = index_mapping["patient_data"].get("mappings", {}).get("properties", {})
                        has_embedding_field = "content_embedding" in properties
                    
                    if has_embedding_field and query_embedding:
                        # Add semantic search to complement keyword search
                        search_body["knn"] = {
                            "field": "content_embedding",
                            "query_vector": query_embedding,
                            "k": 50,  # Get more candidates for visualization
                            "num_candidates": 200,
                            "boost": 3.0,  # Good boost but not too high (keyword still important)
                            "filter": {
                                "bool": {
                                    "must": [
                                        {"term": {"patient_id": patient_id}},
                                        {"term": {"data_type": "observations"}}
                                    ]
                                }
                            }
                        }
                        logger.debug(f"Added semantic search to observation extraction for: {observation_type}")
                except Exception as e:
                    logger.warning(f"Could not add semantic search to observation extraction: {e}. Using keyword search only.")
            
            response = self.es_client.client.search(index="patient_data", body=search_body)
            
            data_points = []
            # Create a filter function to verify the observation actually matches the requested type
            def matches_observation_type(display: str, code: str, observation_type_lower: str) -> bool:
                """Verify that the observation actually matches the requested type"""
                if not display and not code:
                    return False
                
                display_lower = (display or "").lower()
                code_lower = (code or "").lower()
                
                # Exact matches
                if observation_type_lower in display_lower:
                    return True
                
                # Specific mappings for common observations
                if observation_type_lower == "creatinine":
                    return ("creatinine" in display_lower or 
                            "2160-0" in code_lower or 
                            "33914-3" in code_lower or
                            "CREATININE" in display.upper())
                
                elif observation_type_lower == "hemoglobin":
                    # Exclude hemoglobin A1C when searching for regular hemoglobin
                    return ("hemoglobin" in display_lower and 
                            "a1c" not in display_lower and 
                            "hba1c" not in display_lower and
                            ("718-7" in code_lower or "hemoglobin" in display_lower))
                
                elif observation_type_lower == "heart rate":
                    return ("heart rate" in display_lower or 
                            "pulse" in display_lower or 
                            "hr" in display_lower or
                            "8867-4" in code_lower)
                
                elif observation_type_lower == "glucose":
                    return ("glucose" in display_lower or 
                            "blood sugar" in display_lower or
                            "2339-0" in code_lower)
                
                elif observation_type_lower == "temperature":
                    return ("temperature" in display_lower or 
                            "temp" in display_lower)
                
                elif observation_type_lower == "blood pressure":
                    return ("blood pressure" in display_lower or 
                            "systolic" in display_lower or 
                            "diastolic" in display_lower)
                
                # Generic match for other types
                return observation_type_lower in display_lower
            
            for hit in response["hits"]["hits"]:
                # Safely handle missing _source key
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    continue
                # Safely handle missing metadata key
                metadata = source.get("metadata", {})
                if not isinstance(metadata, dict):
                    continue
                
                # CRITICAL: Filter to only include observations that actually match the requested type
                display = metadata.get("display", "")
                code = metadata.get("code", "")
                
                if not matches_observation_type(display, code, observation_type_lower):
                    continue  # Skip observations that don't match
                
                # Extract numeric value
                value_str = metadata.get("value", "")
                numeric_value = None
                
                try:
                    # Try to extract numeric value from string
                    if value_str:
                        # Remove units and extract number
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', value_str)
                        if numbers:
                            numeric_value = float(numbers[0])
                except (ValueError, TypeError):
                    pass
                
                if numeric_value is not None:
                    data_points.append({
                        "date": metadata.get("date", ""),
                        "value": numeric_value,
                        "unit": metadata.get("unit", ""),
                        "display": metadata.get("display", "")
                    })
            
            return data_points
            
        except Exception as e:
            logger.error(f"Failed to extract observation data: {e}")
            return []
    
    def generate_chart_data(self, patient_id: str, chart_type: str, retrieved_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate chart data for different visualization types
        
        Args:
            patient_id: Patient ID
            chart_type: Type of chart to generate
            retrieved_data: Optional RAG retrieved data - if provided, uses this instead of Elasticsearch search
        """
        
        # If retrieved_data is provided, use it (same source as the answer)
        if retrieved_data:
            return self.generate_chart_data_from_retrieved(patient_id, chart_type, retrieved_data)
        
        # Otherwise, use the original method (separate Elasticsearch search)
        # Safely handle None chart_type
        if chart_type is None:
            chart_type = "unknown"
        chart_type = str(chart_type) if chart_type else "unknown"
        
        chart_data = {
            "type": chart_type,
            "patient_id": patient_id,
            "data": {},
            "options": {},
            "error": None,
            "summary": None
        }
        
        try:
            # Check if it's an observation-specific trend chart (format: "observation_trend:creatinine")
            if chart_type and chart_type.startswith("observation_trend:"):
                observation_name = chart_type.split(":", 1)[1]
                chart_data = self._generate_observation_trend_chart(patient_id, observation_name)
            elif chart_type == "glucose_trend":
                chart_data = self._generate_glucose_chart(patient_id)
            elif chart_type == "blood_pressure_trend":
                chart_data = self._generate_blood_pressure_chart(patient_id)
            elif chart_type == "heart_rate_trend":
                chart_data = self._generate_heart_rate_chart(patient_id)
            elif chart_type == "vitals_dashboard":
                chart_data = self._generate_vitals_dashboard(patient_id)
            elif chart_type == "professional_vitals_dashboard":
                chart_data = self._generate_professional_vitals_dashboard(patient_id)
            elif chart_type == "abnormal_values":
                chart_data = self._generate_abnormal_values_chart(patient_id)
            elif chart_type == "all_observations":
                chart_data = self._generate_all_observations_chart(patient_id)
            elif chart_type == "categorized_observations":
                chart_data = self._generate_categorized_observations_charts(patient_id)
            else:
                chart_data["error"] = f"Unknown chart type: {chart_type}"
        
        except Exception as e:
            logger.error(f"Failed to generate chart data: {e}")
            chart_data["error"] = str(e)
        
        return chart_data
    
    def extract_observation_data_from_retrieved(self, retrieved_data: List[Dict[str, Any]], observation_type: str) -> List[Dict[str, Any]]:
        """Extract observation data from RAG retrieved_data (same source as the answer)
        
        This ensures chart values match exactly what the LLM used in its response.
        
        Args:
            retrieved_data: RAG retrieved data
            observation_type: Type of observation to extract (e.g., "creatinine", "heart rate")
        
        Returns:
            List of observation data points with date, value, unit, display
        """
        observation_type_lower = (observation_type or "").lower()
        data_points = []
        
        logger.info(f"Extracting {observation_type} from {len(retrieved_data)} retrieved items")
        
        # Filter function to verify observation matches requested type
        def matches_observation_type(display: str, code: str, observation_type_lower: str) -> bool:
            """Verify that the observation actually matches the requested type"""
            if not display and not code:
                return False
            
            display_lower = (display or "").lower()
            code_lower = (code or "").lower()
            
            # Exact matches
            if observation_type_lower in display_lower:
                return True
            
            # Specific mappings for common observations
            if observation_type_lower == "creatinine":
                return ("creatinine" in display_lower or 
                        "2160-0" in code_lower or 
                        "33914-3" in code_lower or
                        "CREATININE" in display.upper())
            
            elif observation_type_lower == "hemoglobin":
                # Exclude hemoglobin A1C when searching for regular hemoglobin
                return ("hemoglobin" in display_lower and 
                        "a1c" not in display_lower and 
                        "hba1c" not in display_lower and
                        ("718-7" in code_lower or "hemoglobin" in display_lower))
            
            elif observation_type_lower == "heart rate":
                return ("heart rate" in display_lower or 
                        "pulse" in display_lower or 
                        "hr" in display_lower or
                        "8867-4" in code_lower)
            
            elif observation_type_lower == "glucose":
                return ("glucose" in display_lower or 
                        "blood sugar" in display_lower or
                        "2339-0" in code_lower)
            
            elif observation_type_lower == "temperature":
                return ("temperature" in display_lower or 
                        "temp" in display_lower)
            
            elif observation_type_lower == "blood pressure":
                return ("blood pressure" in display_lower or 
                        "systolic" in display_lower or 
                        "diastolic" in display_lower)
            
            # Generic match for other types
            return observation_type_lower in display_lower
        
        # Extract observations from retrieved_data
        observation_count = 0
        for item in retrieved_data:
            if item.get("data_type") != "observations":
                continue
            
            observation_count += 1
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            
            display = metadata.get("display", "")
            code = metadata.get("code", "")
            
            # Filter to only include observations that match the requested type
            if not matches_observation_type(display, code, observation_type_lower):
                logger.debug(f"Skipping observation: {display} (code: {code}) - doesn't match {observation_type}")
                continue
            
            logger.info(f"Found matching observation: {display} (code: {code}) for {observation_type}")
            
            # Extract numeric value
            value_str = metadata.get("value", "")
            numeric_value = None
            
            try:
                # Try to extract numeric value from string
                if value_str:
                    # Remove units and extract number
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', str(value_str))
                    if numbers:
                        numeric_value = float(numbers[0])
            except (ValueError, TypeError):
                pass
            
            if numeric_value is not None:
                data_points.append({
                    "date": metadata.get("date", ""),
                    "value": numeric_value,
                    "unit": metadata.get("unit", ""),
                    "display": metadata.get("display", "")
                })
        
        # Sort by date (chronological order)
        data_points.sort(key=lambda x: x.get("date", ""))
        
        logger.info(f"Extracted {len(data_points)} data points for {observation_type} from {observation_count} observations in retrieved_data")
        
        return data_points
    
    def generate_chart_data_from_retrieved(self, patient_id: str, chart_type: str, retrieved_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate chart data from RAG retrieved_data (same source as the answer)
        
        This ensures chart values match exactly what the LLM used in its response.
        
        Args:
            patient_id: Patient ID
            chart_type: Type of chart to generate
            retrieved_data: RAG retrieved data (same as used for answer generation)
        """
        
        # Safely handle None chart_type
        if chart_type is None:
            chart_type = "unknown"
        chart_type = str(chart_type) if chart_type else "unknown"
        
        chart_data = {
            "type": chart_type,
            "patient_id": patient_id,
            "data": {},
            "options": {},
            "error": None,
            "summary": None
        }
        
        try:
            # Check if it's an observation-specific trend chart (format: "observation_trend:creatinine")
            if chart_type and chart_type.startswith("observation_trend:"):
                observation_name = chart_type.split(":", 1)[1]
                chart_data = self._generate_observation_trend_chart_from_retrieved(patient_id, observation_name, retrieved_data)
            elif chart_type == "glucose_trend":
                chart_data = self._generate_glucose_chart_from_retrieved(patient_id, retrieved_data)
            elif chart_type == "blood_pressure_trend":
                chart_data = self._generate_blood_pressure_chart_from_retrieved(patient_id, retrieved_data)
            elif chart_type == "heart_rate_trend":
                chart_data = self._generate_heart_rate_chart_from_retrieved(patient_id, retrieved_data)
            elif chart_type == "all_observations":
                chart_data = self._generate_all_observations_chart_from_retrieved(patient_id, retrieved_data)
            elif chart_type == "abnormal_values":
                # RESEARCH-BASED: Use LLM-based detection (primary), fallback to thresholds if LLM fails
                # Try LLM first (research approach), then fallback to thresholds
                chart_data = self._generate_abnormal_values_chart(patient_id, use_llm_detection=True)
                # If LLM fails, use threshold-based as fallback
                if chart_data is None or chart_data.get("error"):
                    logger.info("LLM-based detection failed, using threshold-based fallback")
                    chart_data = self._generate_abnormal_values_chart(patient_id, use_llm_detection=False)
            else:
                # For other chart types, fall back to original method
                return self.generate_chart_data(patient_id, chart_type, retrieved_data=None)
        
        except Exception as e:
            logger.error(f"Failed to generate chart data from retrieved: {e}")
            chart_data["error"] = str(e)
        
        return chart_data
    
    def _generate_observation_trend_chart_from_retrieved(self, patient_id: str, observation_name: str, retrieved_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate observation trend chart from retrieved_data (same source as answer)"""
        observation_data = self.extract_observation_data_from_retrieved(retrieved_data, observation_name)
        
        if not observation_data:
            return {
                "type": f"observation_trend:{observation_name}",
                "patient_id": patient_id,
                "data": {
                    "labels": ["No Data"],
                    "datasets": []
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"No {observation_name.title()} Data Available - Patient {patient_id}",
                            "font": {
                                "size": 16,
                                "weight": "bold"
                            }
                        },
                        "legend": {
                            "display": False
                        }
                    },
                    "scales": {
                        "y": {
                            "display": False
                        },
                        "x": {
                            "display": False
                        }
                    }
                },
                "summary": f"No {observation_name} data available for patient {patient_id}.",
                "error": f"No {observation_name} data found"
            }
        
        # Get unit from first data point
        unit = observation_data[0].get("unit", "")
        display_name = observation_data[0].get("display", observation_name.title())
        
        # Clean up display name
        display_name_safe = display_name or ""
        clean_display = self._clean_observation_name(display_name_safe)
        if not clean_display or clean_display == "Unknown":
            observation_name_safe = observation_name or "Unknown"
            clean_display = observation_name_safe.title() if isinstance(observation_name_safe, str) else "Unknown"
        
        # Determine chart color based on observation type
        color_map = {
            "creatinine": "#e74c3c",
            "hemoglobin": "#3498db",
            "gfr": "#2ecc71",
            "glomerular filtration": "#2ecc71",
            "cholesterol": "#f39c12",
            "sodium": "#9b59b6",
            "potassium": "#1abc9c",
            "calcium": "#34495e",
            "bun": "#e67e22",
            "albumin": "#8e44ad",
            "bilirubin": "#f1c40f",
            "temperature": "#e91e63",
            "respiratory": "#00bcd4",
            "oxygen": "#4caf50",
            "saturation": "#4caf50",
            "bmi": "#ff9800",
            "weight": "#795548",
            "height": "#607d8b"
        }
        
        observation_name_safe = (observation_name or "").lower() if observation_name else ""
        chart_color = color_map.get(observation_name_safe, "#3498db")
        
        # Convert hex to rgba for background
        r = int(chart_color[1:3], 16)
        g = int(chart_color[3:5], 16)
        b = int(chart_color[5:7], 16)
        bg_color = f"rgba({r}, {g}, {b}, 0.1)"
        
        chart_data = {
            "type": f"observation_trend:{observation_name}",
            "patient_id": patient_id,
            "data": {
                "labels": [],
                "datasets": [{
                    "label": f"{clean_display} ({unit})" if unit else clean_display,
                    "data": [],
                    "borderColor": chart_color,
                    "backgroundColor": bg_color,
                    "tension": 0.4,
                    "borderWidth": 3,
                    "pointBackgroundColor": chart_color,
                    "pointBorderColor": chart_color,
                    "pointRadius": 6,
                    "pointHoverRadius": 8,
                    "fill": True
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": f"{clean_display} ({unit})" if unit else clean_display,
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{clean_display} Trend - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        }
                    },
                    "legend": {
                        "display": True
                    }
                }
            },
            "summary": self._generate_chart_summary(observation_data, f"observation_trend:{observation_name}", patient_id)
        }
        
        # Add data points
        for point in observation_data:
            chart_data["data"]["labels"].append(point["date"])
            chart_data["data"]["datasets"][0]["data"].append(point["value"])
        
        return chart_data
    
    def generate_chart_from_extracted_values(self, patient_id: str, chart_type: str, extracted_values: List[Dict[str, Any]], observation_type: str) -> Dict[str, Any]:
        """Generate chart from values extracted from answer text
        
        This ensures the chart shows exactly what the answer mentioned.
        
        Args:
            patient_id: Patient ID
            chart_type: Type of chart (e.g., "observation_trend:creatinine", "heart_rate_trend")
            extracted_values: Values extracted from answer text
            observation_type: Type of observation (e.g., "creatinine", "heart rate")
        """
        if chart_type.startswith("observation_trend:"):
            return self._generate_observation_trend_chart_from_values(patient_id, observation_type, extracted_values)
        elif chart_type == "heart_rate_trend":
            return self._generate_heart_rate_chart_from_values(patient_id, extracted_values)
        elif chart_type == "glucose_trend":
            return self._generate_glucose_chart_from_values(patient_id, extracted_values)
        else:
            # Fall back to retrieved_data method
            return self.generate_chart_data_from_retrieved(patient_id, chart_type, [])
    
    def _generate_observation_trend_chart_from_values(self, patient_id: str, observation_name: str, values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate observation chart from extracted values"""
        if not values:
            return {
                "type": f"observation_trend:{observation_name}",
                "patient_id": patient_id,
                "data": {"labels": ["No Data"], "datasets": []},
                "options": {},
                "error": "No values extracted from answer",
                "summary": f"No {observation_name} values found in answer text"
            }
        
        # Get unit from first value
        unit = values[0].get("unit", "")
        display_name = values[0].get("display", observation_name.title())
        
        # Determine chart color
        color_map = {
            "creatinine": "#e74c3c",
            "hemoglobin": "#3498db",
            "heart rate": "#2ecc71",
            "glucose": "#f39c12",
        }
        chart_color = color_map.get(observation_name.lower(), "#3498db")
        
        # Convert hex to rgba
        r = int(chart_color[1:3], 16)
        g = int(chart_color[3:5], 16)
        b = int(chart_color[5:7], 16)
        bg_color = f"rgba({r}, {g}, {b}, 0.1)"
        
        chart_data = {
            "type": f"observation_trend:{observation_name}",
            "patient_id": patient_id,
            "data": {
                "labels": [v["date"] for v in values],
                "datasets": [{
                    "label": f"{display_name} ({unit})" if unit else display_name,
                    "data": [v["value"] for v in values],
                    "borderColor": chart_color,
                    "backgroundColor": bg_color,
                    "tension": 0.4,
                    "borderWidth": 3,
                    "pointRadius": 6,
                    "pointHoverRadius": 8,
                    "fill": True
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": f"{display_name} ({unit})" if unit else display_name
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{display_name} Trend - Patient {patient_id}"
                    }
                }
            },
            "summary": f"Chart generated from {len(values)} values extracted from answer text"
        }
        
        return chart_data
    
    def _generate_heart_rate_chart_from_values(self, patient_id: str, values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate heart rate chart from extracted values"""
        if not values:
            return {
                "type": "heart_rate_trend",
                "patient_id": patient_id,
                "data": {"labels": ["No Data"], "datasets": []},
                "options": {},
                "error": "No values extracted from answer",
                "summary": "No heart rate values found in answer text"
            }
        
        chart_data = {
            "type": "heart_rate_trend",
            "patient_id": patient_id,
            "data": {
                "labels": [v["date"] for v in values],
                "datasets": [{
                    "label": "Heart Rate (bpm)",
                    "data": [v["value"] for v in values],
                    "borderColor": "#2ecc71",
                    "backgroundColor": "rgba(46, 204, 113, 0.1)",
                    "tension": 0.4,
                    "borderWidth": 3,
                    "pointRadius": 6
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "min": 40,
                        "max": 120,
                        "title": {
                            "display": True,
                            "text": "Heart Rate (bpm)"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Heart Rate Trend - Patient {patient_id}"
                    }
                }
            },
            "summary": f"Chart generated from {len(values)} heart rate values extracted from answer text"
        }
        
        return chart_data
    
    def _generate_glucose_chart_from_values(self, patient_id: str, values: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate glucose chart from extracted values"""
        return self._generate_observation_trend_chart_from_values(patient_id, "glucose", values)
    
    def _generate_heart_rate_chart_from_retrieved(self, patient_id: str, retrieved_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate heart rate chart from retrieved_data (same source as answer)"""
        hr_data = self.extract_observation_data_from_retrieved(retrieved_data, "heart rate")
        
        chart_data = {
            "type": "heart_rate_trend",
            "patient_id": patient_id,
            "data": {
                "labels": [],
                "datasets": [{
                    "label": "Heart Rate (bpm)",
                    "data": [],
                    "borderColor": "#2ecc71",
                    "backgroundColor": "rgba(46, 204, 113, 0.1)",
                    "tension": 0.4
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "min": 40,
                        "max": 120,
                        "title": {
                            "display": True,
                            "text": "Heart Rate (bpm)"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Heart Rate Trend - Patient {patient_id}"
                    },
                    "legend": {
                        "display": True
                    }
                }
            }
        }
        
        # Add data points
        for point in hr_data:
            chart_data["data"]["labels"].append(point["date"])
            chart_data["data"]["datasets"][0]["data"].append(point["value"])
        
        # Generate summary
        chart_data["summary"] = self._generate_chart_summary(hr_data, "heart_rate_trend", patient_id)
        
        return chart_data
    
    def _generate_glucose_chart_from_retrieved(self, patient_id: str, retrieved_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate glucose chart from retrieved_data (same source as answer)"""
        glucose_data = self.extract_observation_data_from_retrieved(retrieved_data, "glucose")
        
        # Similar structure to heart_rate_chart_from_retrieved
        # Implementation would follow same pattern
        return self._generate_observation_trend_chart_from_retrieved(patient_id, "glucose", retrieved_data)
    
    def _generate_blood_pressure_chart_from_retrieved(self, patient_id: str, retrieved_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate blood pressure chart from retrieved_data (same source as answer)"""
        # For now, fall back to original method for BP (more complex with systolic/diastolic)
        return self._generate_blood_pressure_chart(patient_id)
    
    def _generate_all_observations_chart_from_retrieved(self, patient_id: str, retrieved_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate all observations chart from retrieved_data (same source as answer)"""
        # Extract all observations from retrieved_data
        all_observations = []
        for item in retrieved_data:
            if item.get("data_type") == "observations":
                metadata = item.get("metadata", {})
                if not isinstance(metadata, dict):
                    continue
                
                # Extract numeric value
                value_str = metadata.get("value", "")
                numeric_value = None
                
                try:
                    if value_str:
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', str(value_str))
                        if numbers:
                            numeric_value = float(numbers[0])
                except (ValueError, TypeError):
                    pass
                
                if numeric_value is not None:
                    display = metadata.get("display", "")
                    if not display or display.strip() == "Unknown":
                        code = metadata.get("code", "")
                        display = f"Code {code}" if code else "Unknown"
                    
                    all_observations.append({
                        "date": metadata.get("date", ""),
                        "value": numeric_value,
                        "unit": metadata.get("unit", ""),
                        "display": display
                    })
        
        if not all_observations:
            return {
                "type": "all_observations",
                "patient_id": patient_id,
                "data": {
                    "labels": ["No Data"],
                    "datasets": []
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"No Observations Data Available - Patient {patient_id}",
                            "font": {
                                "size": 16,
                                "weight": "bold"
                            }
                        },
                        "legend": {
                            "display": False
                        }
                    },
                    "scales": {
                        "y": {
                            "display": False
                        },
                        "x": {
                            "display": False
                        }
                    }
                },
                "summary": f"No observations data available for patient {patient_id}.",
                "error": "No observations data found"
            }
        
        # Group observations by display name
        obs_by_display = {}
        for obs in all_observations:
            display = obs["display"]
            if display not in obs_by_display:
                obs_by_display[display] = []
            obs_by_display[display].append(obs)
        
        # Sort by date
        for display in obs_by_display:
            obs_by_display[display].sort(key=lambda x: x.get("date", ""))
        
        # Get all unique dates
        all_dates = set()
        for obs_list in obs_by_display.values():
            for obs in obs_list:
                all_dates.add(obs["date"])
        all_dates = sorted(list(all_dates))
        
        # Create datasets for each observation type
        datasets = []
        colors = [
            "#0EA5E9", "#10B981", "#F59E0B", "#8B5CF6", "#EF4444",
            "#06B6D4", "#EC4899", "#6366F1", "#F97316", "#14B8A6"
        ]
        
        for idx, (display, obs_list) in enumerate(obs_by_display.items()):
            unit = obs_list[0].get("unit", "")
            label = f"{display} ({unit})" if unit else display
            
            # Create data array aligned with all_dates
            data = []
            obs_dict = {obs["date"]: obs["value"] for obs in obs_list}
            for date in all_dates:
                data.append(obs_dict.get(date, None))
            
            datasets.append({
                "label": label,
                "data": data,
                "borderColor": colors[idx % len(colors)],
                "backgroundColor": colors[idx % len(colors)],
                "tension": 0.4,
                "borderWidth": 2,
                "pointRadius": 4,
                "pointHoverRadius": 6
            })
        
        return {
            "type": "all_observations",
            "patient_id": patient_id,
            "data": {
                "labels": all_dates,
                "datasets": datasets
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": "Value"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"All Observations - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        }
                    },
                    "legend": {
                        "display": True
                    }
                }
            },
            "summary": f"Showing {len(datasets)} observation types with {len(all_dates)} data points"
        }
    
    def _generate_chart_summary(self, data_points: List[Dict[str, Any]], chart_type: str, patient_id: str) -> str:
        """Generate a one-line summary for the chart"""
        # Handle None chart_type
        if chart_type is None:
            chart_type = "chart"
        chart_type_str = str(chart_type).replace('_', ' ') if chart_type else "chart"
        
        if not data_points:
            return f"No {chart_type_str} data available for patient {patient_id}."
        
        # Sort data points by date
        sorted_data = sorted(data_points, key=lambda x: x.get("date", ""))
        
        if len(sorted_data) == 1:
            value = sorted_data[0]["value"]
            unit = sorted_data[0].get("unit", "")
            return f"Single {chart_type_str} reading: {value} {unit}."
        
        # Calculate trend
        first_value = sorted_data[0]["value"]
        last_value = sorted_data[-1]["value"]
        unit = sorted_data[0].get("unit", "")
        
        if last_value > first_value:
            trend = "increased"
            change = last_value - first_value
            change_text = f"+{change:.1f}"
        elif last_value < first_value:
            trend = "decreased"
            change = first_value - last_value
            change_text = f"-{change:.1f}"
        else:
            trend = "remained stable"
            change = 0
            change_text = "0"
        
        if change > 0:
            return f"{chart_type_str.title()} {trend} from {first_value} to {last_value} {unit} (change: {change_text} {unit})."
        else:
            return f"{chart_type_str.title()} {trend} at {last_value} {unit}."
    
    def _generate_glucose_chart(self, patient_id: str) -> Dict[str, Any]:
        """Generate glucose trend chart data"""
        glucose_data = self.extract_observation_data(patient_id, "glucose")
        
        chart_data = {
            "type": "glucose_trend",
            "patient_id": patient_id,
            "data": {
                "labels": [],
                "datasets": [{
                    "label": "Glucose (mg/dL)",
                    "data": [],
                    "borderColor": "#e74c3c",
                    "backgroundColor": "rgba(231, 76, 60, 0.1)",
                    "tension": 0.4,
                    "borderWidth": 3,
                    "pointBackgroundColor": "#e74c3c",
                    "pointBorderColor": "#c0392b",
                    "pointRadius": 6,
                    "pointHoverRadius": 8
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "min": 50,
                        "max": 300,
                        "title": {
                            "display": True,
                            "text": "Glucose (mg/dL)",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Glucose Trend - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        },
                        "color": "#2c3e50"
                    },
                    "legend": {
                        "display": True,
                        "position": "top",
                        "labels": {
                            "font": {
                                "size": 12
                            }
                        }
                    },
                    "annotation": {
                        "annotations": {
                            "normalRange": {
                                "type": "box",
                                "yMin": 70,
                                "yMax": 140,
                                "backgroundColor": "rgba(46, 204, 113, 0.1)",
                                "borderColor": "rgba(46, 204, 113, 0.5)",
                                "borderWidth": 1,
                                "label": {
                                    "content": "Normal Range",
                                    "enabled": True
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Add data points
        for point in glucose_data:
            chart_data["data"]["labels"].append(point["date"])
            chart_data["data"]["datasets"][0]["data"].append(point["value"])
        
        # Generate summary
        chart_data["summary"] = self._generate_chart_summary(glucose_data, "glucose_trend", patient_id)
        
        return chart_data
    
    def _generate_blood_pressure_chart(self, patient_id: str) -> Dict[str, Any]:
        """Generate blood pressure trend chart data"""
        systolic_data = self.extract_observation_data(patient_id, "systolic")
        diastolic_data = self.extract_observation_data(patient_id, "diastolic")
        
        chart_data = {
            "type": "blood_pressure_trend",
            "patient_id": patient_id,
            "data": {
                "labels": [],
                "datasets": [
                    {
                        "label": "Systolic BP (mmHg)",
                        "data": [],
                        "borderColor": "#e74c3c",
                        "backgroundColor": "rgba(231, 76, 60, 0.1)",
                        "tension": 0.4
                    },
                    {
                        "label": "Diastolic BP (mmHg)",
                        "data": [],
                        "borderColor": "#3498db",
                        "backgroundColor": "rgba(52, 152, 219, 0.1)",
                        "tension": 0.4
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "min": 50,
                        "max": 200,
                        "title": {
                            "display": True,
                            "text": "Blood Pressure (mmHg)"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Blood Pressure Trend - Patient {patient_id}"
                    },
                    "legend": {
                        "display": True
                    }
                }
            }
        }
        
        # Add systolic data
        for point in systolic_data:
            chart_data["data"]["labels"].append(point["date"])
            chart_data["data"]["datasets"][0]["data"].append(point["value"])
        
        # Add diastolic data (assuming same dates)
        for point in diastolic_data:
            if point["date"] not in chart_data["data"]["labels"]:
                chart_data["data"]["labels"].append(point["date"])
                chart_data["data"]["datasets"][1]["data"].append(point["value"])
            else:
                chart_data["data"]["datasets"][1]["data"].append(point["value"])
        
        # Generate summary for blood pressure
        if systolic_data and diastolic_data:
            systolic_summary = self._generate_chart_summary(systolic_data, "systolic_bp", patient_id)
            diastolic_summary = self._generate_chart_summary(diastolic_data, "diastolic_bp", patient_id)
            chart_data["summary"] = f"Systolic: {systolic_summary} Diastolic: {diastolic_summary}"
        elif systolic_data:
            chart_data["summary"] = self._generate_chart_summary(systolic_data, "systolic_bp", patient_id)
        elif diastolic_data:
            chart_data["summary"] = self._generate_chart_summary(diastolic_data, "diastolic_bp", patient_id)
        else:
            chart_data["summary"] = f"No blood pressure data available for patient {patient_id}."
        
        return chart_data
    
    def _generate_heart_rate_chart(self, patient_id: str) -> Dict[str, Any]:
        """Generate heart rate trend chart data"""
        hr_data = self.extract_observation_data(patient_id, "heart rate")
        
        chart_data = {
            "type": "heart_rate_trend",
            "patient_id": patient_id,
            "data": {
                "labels": [],
                "datasets": [{
                    "label": "Heart Rate (bpm)",
                    "data": [],
                    "borderColor": "#2ecc71",
                    "backgroundColor": "rgba(46, 204, 113, 0.1)",
                    "tension": 0.4
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "min": 40,
                        "max": 120,
                        "title": {
                            "display": True,
                            "text": "Heart Rate (bpm)"
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date"
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Heart Rate Trend - Patient {patient_id}"
                    },
                    "legend": {
                        "display": True
                    }
                }
            }
        }
        
        # Add data points
        for point in hr_data:
            chart_data["data"]["labels"].append(point["date"])
            chart_data["data"]["datasets"][0]["data"].append(point["value"])
        
        # Generate summary
        chart_data["summary"] = self._generate_chart_summary(hr_data, "heart_rate_trend", patient_id)
        
        return chart_data
    
    def _generate_observation_trend_chart(self, patient_id: str, observation_name: str) -> Dict[str, Any]:
        """Generate a focused trend chart for a specific observation type (e.g., creatinine, hemoglobin)"""
        observation_data = self.extract_observation_data(patient_id, observation_name)
        
        if not observation_data:
            return {
                "type": f"observation_trend:{observation_name}",
                "patient_id": patient_id,
                "data": {
                    "labels": ["No Data"],
                    "datasets": []
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"No {observation_name.title()} Data Available - Patient {patient_id}",
                            "font": {
                                "size": 16,
                                "weight": "bold"
                            }
                        },
                        "legend": {
                            "display": False
                        }
                    },
                    "scales": {
                        "y": {
                            "display": False
                        },
                        "x": {
                            "display": False
                        }
                    }
                },
                "summary": f"No {observation_name} data available for patient {patient_id}.",
                "error": f"No {observation_name} data found"
            }
        
        # Get unit from first data point
        unit = observation_data[0].get("unit", "")
        display_name = observation_data[0].get("display", observation_name.title())
        
        # Clean up display name
        # Safely handle None display_name
        display_name_safe = display_name or ""
        clean_display = self._clean_observation_name(display_name_safe)
        if not clean_display or clean_display == "Unknown":
            # Safely handle None observation_name
            observation_name_safe = observation_name or "Unknown"
            clean_display = observation_name_safe.title() if isinstance(observation_name_safe, str) else "Unknown"
        
        # Determine chart color based on observation type
        color_map = {
            "creatinine": "#e74c3c",
            "hemoglobin": "#3498db",
            "gfr": "#2ecc71",
            "glomerular filtration": "#2ecc71",
            "cholesterol": "#f39c12",
            "sodium": "#9b59b6",
            "potassium": "#1abc9c",
            "calcium": "#34495e",
            "bun": "#e67e22",
            "albumin": "#8e44ad",
            "bilirubin": "#f1c40f",
            "temperature": "#e91e63",
            "respiratory": "#00bcd4",
            "oxygen": "#4caf50",
            "saturation": "#4caf50",
            "bmi": "#ff9800",
            "weight": "#795548",
            "height": "#607d8b"
        }
        
        # Safely handle None observation_name
        observation_name_safe = (observation_name or "").lower() if observation_name else ""
        chart_color = color_map.get(observation_name_safe, "#3498db")
        
        # Convert hex to rgba for background
        r = int(chart_color[1:3], 16)
        g = int(chart_color[3:5], 16)
        b = int(chart_color[5:7], 16)
        bg_color = f"rgba({r}, {g}, {b}, 0.1)"
        
        chart_data = {
            "type": f"observation_trend:{observation_name}",
            "patient_id": patient_id,
            "data": {
                "labels": [],
                "datasets": [{
                    "label": f"{clean_display} ({unit})" if unit else clean_display,
                    "data": [],
                    "borderColor": chart_color,
                    "backgroundColor": bg_color,
                    "tension": 0.4,
                    "borderWidth": 3,
                    "pointBackgroundColor": chart_color,
                    "pointBorderColor": chart_color,
                    "pointRadius": 6,
                    "pointHoverRadius": 8,
                    "fill": True
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": f"{clean_display} ({unit})" if unit else clean_display,
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"{clean_display} Trend - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        },
                        "color": "#2c3e50"
                    },
                    "legend": {
                        "display": True,
                        "position": "top",
                        "labels": {
                            "font": {
                                "size": 12
                            }
                        }
                    }
                }
            }
        }
        
        # Add data points
        for point in observation_data:
            date_str = point.get("date", "")
            if date_str:
                # Format date for display (just date part)
                chart_data["data"]["labels"].append(date_str[:10] if len(date_str) > 10 else date_str)
                chart_data["data"]["datasets"][0]["data"].append(point["value"])
        
        # Generate summary
        chart_data["summary"] = self._generate_chart_summary(observation_data, observation_name, patient_id)
        
        return chart_data
    
    def _generate_vitals_dashboard(self, patient_id: str) -> Dict[str, Any]:
        """Generate comprehensive vitals dashboard as Chart.js compatible data"""
        glucose_data = self.extract_observation_data(patient_id, "glucose")
        bp_data = self.extract_observation_data(patient_id, "blood pressure")
        hr_data = self.extract_observation_data(patient_id, "heart rate")
        temp_data = self.extract_observation_data(patient_id, "temperature")
        
        # If no traditional vital signs, try to get any available lab data
        if not any([glucose_data, bp_data, hr_data, temp_data]):
            # Get some common lab values that might be available
            lab_data = self.extract_observation_data(patient_id, "lab")
            creatinine_data = self.extract_observation_data(patient_id, "creatinine")
            hemoglobin_data = self.extract_observation_data(patient_id, "hemoglobin")
            
            # If we have lab data, create a lab values chart instead
            if lab_data or creatinine_data or hemoglobin_data:
                return self._generate_lab_values_chart(patient_id)
        
        # Combine all data points with timestamps
        all_data = []
        labels = []
        
        # Process glucose data
        for point in glucose_data:
            all_data.append({
                "date": point["date"],
                "type": "glucose",
                "value": point["value"],
                "unit": "mg/dL"
            })
            labels.append(point["date"][:10])  # Date only
        
        # Process blood pressure data
        for point in bp_data:
            all_data.append({
                "date": point["date"],
                "type": "blood_pressure",
                "value": point["value"],
                "unit": "mmHg"
            })
        
        # Process heart rate data
        for point in hr_data:
            all_data.append({
                "date": point["date"],
                "type": "heart_rate",
                "value": point["value"],
                "unit": "bpm"
            })
        
        # Process temperature data
        for point in temp_data:
            all_data.append({
                "date": point["date"],
                "type": "temperature",
                "value": point["value"],
                "unit": "°C"
            })
        
        # Sort by date
        all_data.sort(key=lambda x: x["date"])
        
        # If no data at all, return empty chart with message
        if not all_data:
            return {
                "type": "vitals_dashboard",
                "patient_id": patient_id,
                "data": {
                    "labels": ["No Data"],
                    "datasets": []
                },
                "options": {
                    "responsive": True,
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"No Vital Signs Data Available - Patient {patient_id}",
                            "font": {
                                "size": 16,
                                "weight": "bold"
                            }
                        },
                        "legend": {
                            "display": False
                        }
                    },
                    "scales": {
                        "y": {
                            "display": False
                        },
                        "x": {
                            "display": False
                        }
                    }
                },
                "summary": f"No vital signs data available for patient {patient_id}."
            }
        
        # Create Chart.js format
        chart_data = {
            "type": "vitals_dashboard",
            "patient_id": patient_id,
            "data": {
                "labels": list(set(labels)),  # All unique dates
                "datasets": [
                    {
                        "label": "Glucose (mg/dL)",
                        "data": [point["value"] for point in all_data if point["type"] == "glucose"],
                        "borderColor": "#e74c3c",
                        "backgroundColor": "rgba(231, 76, 60, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    },
                    {
                        "label": "Heart Rate (bpm)",
                        "data": [point["value"] for point in all_data if point["type"] == "heart_rate"],
                        "borderColor": "#3498db",
                        "backgroundColor": "rgba(52, 152, 219, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    },
                    {
                        "label": "Temperature (°C)",
                        "data": [point["value"] for point in all_data if point["type"] == "temperature"],
                        "borderColor": "#f39c12",
                        "backgroundColor": "rgba(243, 156, 18, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": "Values",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Vital Signs Dashboard - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        }
                    },
                    "legend": {
                        "display": True,
                        "position": "top"
                    }
                }
            }
        }
        
        # Generate summary for vitals dashboard
        summary_parts = []
        if glucose_data:
            glucose_summary = self._generate_chart_summary(glucose_data, "glucose", patient_id)
            summary_parts.append(f"Glucose: {glucose_summary}")
        if hr_data:
            hr_summary = self._generate_chart_summary(hr_data, "heart_rate", patient_id)
            summary_parts.append(f"Heart Rate: {hr_summary}")
        if temp_data:
            temp_summary = self._generate_chart_summary(temp_data, "temperature", patient_id)
            summary_parts.append(f"Temperature: {temp_summary}")
        
        if summary_parts:
            chart_data["summary"] = " | ".join(summary_parts)
        else:
            chart_data["summary"] = f"Vital signs dashboard generated for patient {patient_id}."
        
        return chart_data
    
    def _generate_lab_values_chart(self, patient_id: str) -> Dict[str, Any]:
        """Generate chart from available lab values when vital signs are not available"""
        # Get various lab values that might be available
        creatinine_data = self.extract_observation_data(patient_id, "creatinine")
        hemoglobin_data = self.extract_observation_data(patient_id, "hemoglobin")
        glucose_data = self.extract_observation_data(patient_id, "glucose")
        gfr_data = self.extract_observation_data(patient_id, "glomerular filtration")
        
        # Combine all available lab data
        all_data = []
        labels = []
        
        # Process creatinine data
        for point in creatinine_data:
            all_data.append({
                "date": point["date"],
                "type": "creatinine",
                "value": point["value"],
                "unit": "mg/dL"
            })
            labels.append(point["date"][:10])
        
        # Process hemoglobin data
        for point in hemoglobin_data:
            all_data.append({
                "date": point["date"],
                "type": "hemoglobin",
                "value": point["value"],
                "unit": "g/dL"
            })
            labels.append(point["date"][:10])
        
        # Process glucose data
        for point in glucose_data:
            all_data.append({
                "date": point["date"],
                "type": "glucose",
                "value": point["value"],
                "unit": "mg/dL"
            })
            labels.append(point["date"][:10])
        
        # Process GFR data
        for point in gfr_data:
            all_data.append({
                "date": point["date"],
                "type": "gfr",
                "value": point["value"],
                "unit": "mL/min/1.73m²"
            })
            labels.append(point["date"][:10])
        
        # Sort by date
        all_data.sort(key=lambda x: x["date"])
        
        # Create Chart.js format
        chart_data = {
            "type": "lab_values_chart",
            "patient_id": patient_id,
            "data": {
                "labels": list(set(labels)),  # All unique dates
                "datasets": [
                    {
                        "label": "Creatinine (mg/dL)",
                        "data": [point["value"] for point in all_data if point["type"] == "creatinine"],
                        "borderColor": "#e74c3c",
                        "backgroundColor": "rgba(231, 76, 60, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    },
                    {
                        "label": "Hemoglobin (g/dL)",
                        "data": [point["value"] for point in all_data if point["type"] == "hemoglobin"],
                        "borderColor": "#3498db",
                        "backgroundColor": "rgba(52, 152, 219, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    },
                    {
                        "label": "Glucose (mg/dL)",
                        "data": [point["value"] for point in all_data if point["type"] == "glucose"],
                        "borderColor": "#f39c12",
                        "backgroundColor": "rgba(243, 156, 18, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    },
                    {
                        "label": "GFR (mL/min/1.73m²)",
                        "data": [point["value"] for point in all_data if point["type"] == "gfr"],
                        "borderColor": "#9b59b6",
                        "backgroundColor": "rgba(155, 89, 182, 0.1)",
                        "tension": 0.4,
                        "borderWidth": 2
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": "Lab Values",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Laboratory Values Dashboard - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        }
                    },
                    "legend": {
                        "display": True,
                        "position": "top"
                    }
                }
            }
        }
        
        return chart_data
    
    def _generate_all_observations_chart(self, patient_id: str) -> Dict[str, Any]:
        """Generate comprehensive chart showing all available observations"""
        if not self.es_client.is_connected():
            logger.warning("ElasticSearch not connected")
            return {
                "type": "all_observations",
                "patient_id": patient_id,
                "data": {"labels": [], "datasets": []},
                "options": {"error": "ElasticSearch not connected"},
                "error": "ElasticSearch not connected"
            }
        
        try:
            # Get all observations for the patient
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"patient_id": patient_id}},
                            {"term": {"data_type": "observations"}}
                        ]
                    }
                },
                "size": 200,  # Get more observations
                "sort": [{"timestamp": {"order": "asc"}}]
            }
            
            response = self.es_client.client.search(index="patient_data", body=search_body)
            
            # Group observations by type and extract numeric values
            observation_groups = {}
            all_dates = set()
            
            for hit in response["hits"]["hits"]:
                # Safely handle missing _source key
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    continue
                # Safely handle missing metadata key
                metadata = source.get("metadata", {})
                if not isinstance(metadata, dict):
                    continue
                
                # Extract numeric value
                value_str = metadata.get("value", "")
                numeric_value = None
                
                try:
                    if value_str:
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', value_str)
                        if numbers:
                            numeric_value = float(numbers[0])
                except (ValueError, TypeError):
                    continue
                
                if numeric_value is not None:
                    display_name = metadata.get("display", "Unknown")
                    date = metadata.get("date", "")
                    
                    # Clean up display name for better readability
                    # Safely handle None display_name
                    display_name_safe = display_name or ""
                    clean_name = self._clean_observation_name(display_name_safe)
                    
                    if clean_name and clean_name not in observation_groups:
                        observation_groups[clean_name] = []
                    
                    observation_groups[clean_name].append({
                        "date": date,
                        "value": numeric_value,
                        "unit": metadata.get("unit", ""),
                        "original_name": display_name
                    })
                    
                    if date:
                        all_dates.add(date)
            
                # Sort dates, filtering out empty dates
                sorted_dates = sorted([date for date in all_dates if date])  # All available dates
            
            # Create datasets for Chart.js
            datasets = []
            colors = [
                "#e74c3c", "#3498db", "#f39c12", "#9b59b6", "#1abc9c",
                "#34495e", "#e67e22", "#2ecc71", "#8e44ad", "#f1c40f",
                "#e91e63", "#00bcd4", "#4caf50", "#ff9800", "#795548"
            ]
            
            for i, (obs_name, data_points) in enumerate(observation_groups.items()):
                if len(data_points) > 1:  # Only include observations with multiple data points
                    # Sort data points by date, filtering out empty dates
                    data_points.sort(key=lambda x: x["date"] if x["date"] else "")
                    
                    # Create data array matching the sorted dates
                    values = []
                    for date in sorted_dates:
                        matching_point = next((p for p in data_points if p["date"] == date), None)
                        values.append(matching_point["value"] if matching_point else None)
                    
                    # Only include if we have at least 2 non-null values
                    non_null_values = [v for v in values if v is not None]
                    if len(non_null_values) >= 2:
                        datasets.append({
                            "label": f"{obs_name} ({data_points[0]['unit']})",
                            "data": values,
                            "borderColor": colors[i % len(colors)],
                            "backgroundColor": colors[i % len(colors)].replace("rgb", "rgba").replace(")", ", 0.1)"),
                            "tension": 0.4,
                            "borderWidth": 2,
                            "pointRadius": 4,
                            "pointHoverRadius": 6
                        })
            
            # If no datasets with trends, create a summary chart
            if not datasets:
                return self._generate_observations_summary_chart(patient_id, observation_groups)
            
            chart_data = {
                "type": "all_observations",
                "patient_id": patient_id,
                "data": {
                    "labels": [date[:10] for date in sorted_dates],  # Date only
                    "datasets": datasets
                },
                "options": {
                    "responsive": True,
                    "scales": {
                        "y": {
                            "beginAtZero": False,
                            "title": {
                                "display": True,
                                "text": "Values",
                                "font": {
                                    "size": 14,
                                    "weight": "bold"
                                }
                            },
                            "grid": {
                                "color": "rgba(0,0,0,0.1)",
                                "lineWidth": 1
                            }
                        },
                        "x": {
                            "title": {
                                "display": True,
                                "text": "Date",
                                "font": {
                                    "size": 14,
                                    "weight": "bold"
                                }
                            },
                            "grid": {
                                "color": "rgba(0,0,0,0.1)",
                                "lineWidth": 1
                            }
                        }
                    },
                    "plugins": {
                        "title": {
                            "display": True,
                            "text": f"All Observations Trends - Patient {patient_id}",
                            "font": {
                                "size": 16,
                                "weight": "bold"
                            }
                        },
                        "legend": {
                            "display": True,
                            "position": "top",
                            "labels": {
                                "usePointStyle": True,
                                "padding": 20
                            }
                        }
                    },
                    "interaction": {
                        "intersect": False,
                        "mode": "index"
                    }
                }
            }
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Failed to generate all observations chart: {e}")
            return {
                "type": "all_observations",
                "patient_id": patient_id,
                "data": {"labels": [], "datasets": []},
                "options": {"error": str(e)},
                "error": str(e)
            }
    
    def _clean_observation_name(self, name: str) -> str:
        """Clean observation names for better readability"""
        # Safely handle None or empty names
        if not name or not isinstance(name, str):
            return "Unknown"
        
        # Remove common prefixes and suffixes
        clean_name = name.replace("Observation: ", "")
        clean_name = clean_name.replace(":VRAT:PT:SER/PLAS:QN:", "")
        clean_name = clean_name.replace(":QN:", "")
        clean_name = clean_name.replace(":PT:", "")
        clean_name = clean_name.replace(":BLD:", "")
        clean_name = clean_name.replace(":AUTOMATED COUNT", "")
        clean_name = clean_name.replace(":CREATININE-BASED FORMULA (MDRD)", "")
        clean_name = clean_name.replace(":PREDICTED.BLACK", "")
        clean_name = clean_name.replace(":PREDICTED", "")
        clean_name = clean_name.replace(":NFR:", "")
        clean_name = clean_name.replace(":NCNC:", "")
        
        # Truncate very long names
        if len(clean_name) > 30:
            clean_name = clean_name[:30] + "..."
        
        return clean_name
    
    def _generate_observations_summary_chart(self, patient_id: str, observation_groups: dict) -> Dict[str, Any]:
        """Generate a summary chart when there are no trends (single values)"""
        # Create a bar chart showing latest values for each observation type
        labels = []
        values = []
        colors = []
        
        color_palette = [
            "#e74c3c", "#3498db", "#f39c12", "#9b59b6", "#1abc9c",
            "#34495e", "#e67e22", "#2ecc71", "#8e44ad", "#f1c40f"
        ]
        
        for i, (obs_name, data_points) in enumerate(observation_groups.items()):
            if data_points:
                # Get the latest value, filtering out empty dates
                valid_points = [p for p in data_points if p["date"]]
                if valid_points:
                    latest_point = max(valid_points, key=lambda x: x["date"])
                    labels.append(f"{obs_name}\n({latest_point['unit']})")
                    values.append(latest_point["value"])
                    colors.append(color_palette[i % len(color_palette)])
        
        chart_data = {
            "type": "observations_summary",
            "patient_id": patient_id,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Latest Values",
                    "data": values,
                    "backgroundColor": colors,
                    "borderColor": colors,
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": True,
                        "title": {
                            "display": True,
                            "text": "Values",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Observations",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"All Observations Summary - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        }
                    },
                    "legend": {
                        "display": False
                    }
                }
            }
        }
        
        return chart_data
    
    def _generate_categorized_observations_charts(self, patient_id: str) -> Dict[str, Any]:
        """
        Generate categorized observations charts - one chart per category.
        Only includes trend-capable observations (multiple values).
        Returns a special structure with multiple charts.
        """
        if not self.es_client.is_connected():
            logger.warning("ElasticSearch not connected")
            return {
                "type": "categorized_observations",
                "patient_id": patient_id,
                "charts": [],
                "single_value_observations": [],
                "error": "ElasticSearch not connected"
            }
        
        try:
            # Get all observations for the patient
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"patient_id": patient_id}},
                            {"term": {"data_type": "observations"}}
                        ]
                    }
                },
                "size": 500,  # Get more observations for categorization
                "sort": [{"timestamp": {"order": "asc"}}]
            }
            
            response = self.es_client.client.search(index="patient_data", body=search_body)
            
            # Extract and categorize observations
            observation_data_points = {}  # Track data points per observation type
            
            for hit in response["hits"]["hits"]:
                # Safely handle missing _source key
                source = hit.get("_source", {})
                if not isinstance(source, dict):
                    continue
                # Safely handle missing metadata key
                metadata = source.get("metadata", {})
                if not isinstance(metadata, dict):
                    continue
                if not isinstance(metadata, dict):
                    metadata = {}
                
                display = metadata.get("display", "Unknown")
                code = metadata.get("code", "")
                value_str = metadata.get("value", "")
                date = metadata.get("date", "")
                unit = metadata.get("unit", "")
                
                # Extract numeric value
                numeric_value = None
                if value_str:
                    try:
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', str(value_str))
                        if numbers:
                            numeric_value = float(numbers[0])
                    except (ValueError, TypeError):
                        pass
                
                # Categorize observation
                category_info = categorize_observation(display, code)
                
                obs_key = f"{display}|{code}"
                if obs_key not in observation_data_points:
                    observation_data_points[obs_key] = {
                        "display": display,
                        "code": code,
                        "category": category_info["category"],
                        "category_display": category_info["display_name"],
                        "color": category_info["color"],
                        "data_points": [],
                        "unit": unit
                    }
                
                if numeric_value is not None and date:
                    observation_data_points[obs_key]["data_points"].append({
                        "date": date,
                        "value": numeric_value,
                        "unit": unit
                    })
            
            # Separate trend-capable vs single-value observations
            trend_capable_by_category = {}
            single_value_observations = []
            
            for obs_key, obs_info in observation_data_points.items():
                data_points = obs_info["data_points"]
                category = obs_info["category"]
                
                # Check if trend-capable (has multiple values with dates)
                unique_dates = set([dp["date"] for dp in data_points if dp.get("date")])
                if len(unique_dates) >= 2:
                    # Trend-capable - add to category
                    if category not in trend_capable_by_category:
                        trend_capable_by_category[category] = []
                    trend_capable_by_category[category].append(obs_info)
                elif len(data_points) == 1:
                    # Single value - add to summary list
                    single_value_observations.append({
                        "display": obs_info["display"],
                        "value": data_points[0]["value"],
                        "unit": obs_info["unit"],
                        "date": data_points[0]["date"],
                        "category": obs_info["category_display"]
                    })
            
            # Generate one chart per category
            category_charts = []
            colors = [
                "#e74c3c", "#3498db", "#f39c12", "#9b59b6", "#1abc9c",
                "#34495e", "#e67e22", "#2ecc71", "#8e44ad", "#f1c40f",
                "#e91e63", "#00bcd4", "#4caf50", "#ff9800", "#795548"
            ]
            
            for category, obs_list in sorted(trend_capable_by_category.items(), 
                                           key=lambda x: get_category_display_name(x[0])):
                # Collect all dates for this category
                all_dates = set()
                for obs in obs_list:
                    for dp in obs["data_points"]:
                        if dp.get("date"):
                            all_dates.add(dp["date"])
                
                sorted_dates = sorted([date for date in all_dates if date])
                
                if not sorted_dates:
                    continue
                
                # Create datasets for each observation in this category
                datasets = []
                for idx, obs in enumerate(obs_list):
                    display = obs.get("display") or ""
                    clean_name = self._clean_observation_name(display)
                    if not clean_name or clean_name == "Unknown":
                        clean_name = display[:30] if display else "Unknown"
                    
                    # Create data array matching sorted dates
                    values = []
                    for date in sorted_dates:
                        matching_point = next(
                            (dp for dp in obs["data_points"] if dp.get("date") == date),
                            None
                        )
                        values.append(matching_point["value"] if matching_point else None)
                    
                    # Only include if we have at least 2 non-null values
                    non_null_values = [v for v in values if v is not None]
                    if len(non_null_values) >= 2:
                        datasets.append({
                            "label": f"{clean_name} ({obs['unit']})" if obs.get("unit") else clean_name,
                            "data": values,
                            "borderColor": colors[idx % len(colors)],
                            "backgroundColor": f"rgba({int(colors[idx % len(colors)][1:3], 16)}, {int(colors[idx % len(colors)][3:5], 16)}, {int(colors[idx % len(colors)][5:7], 16)}, 0.1)",
                            "tension": 0.4,
                            "borderWidth": 2,
                            "pointRadius": 4,
                            "pointHoverRadius": 6,
                            "fill": False
                        })
                
                if datasets:
                    category_charts.append({
                        "category": category,
                        "category_display": get_category_display_name(category),
                        "chart": {
                            "type": f"category_{category}",
                            "patient_id": patient_id,
                            "data": {
                                "labels": [date[:10] for date in sorted_dates],
                                "datasets": datasets
                            },
                            "options": {
                                "responsive": True,
                                "scales": {
                                    "y": {
                                        "beginAtZero": False,
                                        "title": {
                                            "display": True,
                                            "text": "Values",
                                            "font": {
                                                "size": 14,
                                                "weight": "bold"
                                            }
                                        },
                                        "grid": {
                                            "color": "rgba(0,0,0,0.1)",
                                            "lineWidth": 1
                                        }
                                    },
                                    "x": {
                                        "title": {
                                            "display": True,
                                            "text": "Date",
                                            "font": {
                                                "size": 14,
                                                "weight": "bold"
                                            }
                                        },
                                        "grid": {
                                            "color": "rgba(0,0,0,0.1)",
                                            "lineWidth": 1
                                        }
                                    }
                                },
                                "plugins": {
                                    "title": {
                                        "display": True,
                                        "text": f"{get_category_display_name(category)} - Patient {patient_id}",
                                        "font": {
                                            "size": 16,
                                            "weight": "bold"
                                        },
                                        "color": "#2c3e50"
                                    },
                                    "legend": {
                                        "display": True,
                                        "position": "top",
                                        "labels": {
                                            "usePointStyle": True,
                                            "padding": 15,
                                            "font": {
                                                "size": 11
                                            }
                                        }
                                    }
                                },
                                "interaction": {
                                    "intersect": False,
                                    "mode": "index"
                                }
                            }
                        },
                        "observation_count": len(obs_list)
                    })
            
            return {
                "type": "categorized_observations",
                "patient_id": patient_id,
                "charts": category_charts,
                "single_value_observations": single_value_observations,
                "summary": f"Generated {len(category_charts)} category chart(s) with {len(single_value_observations)} single-value observation(s)"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate categorized observations charts: {e}")
            return {
                "type": "categorized_observations",
                "patient_id": patient_id,
                "charts": [],
                "single_value_observations": [],
                "error": str(e)
            }
    
    def _identify_observation_type_from_display(self, display: str, code: Optional[str] = None) -> Optional[str]:
        """Identify observation type from display name and code (class method)"""
        if not display:
            display = ""
        display_lower = display.lower()
        code_str = str(code) if code else ""
        
        # Blood pressure
        if "systolic" in display_lower or "8480-6" in code_str:
            return "systolic_bp"
        if "diastolic" in display_lower or "8462-4" in code_str:
            return "diastolic_bp"
        if "blood pressure" in display_lower:
            return "blood_pressure"
        
        # Heart rate
        if "heart rate" in display_lower or "pulse" in display_lower or "8867-4" in code_str:
            return "heart_rate"
        
        # Temperature
        if "temperature" in display_lower or "temp" in display_lower or "8310-5" in code_str:
            return "temperature"
        
        # Respiratory
        if "respiratory" in display_lower or "9279-1" in code_str:
            return "respiratory_rate"
        
        # Glucose
        if "glucose" in display_lower or "blood sugar" in display_lower or "2339-0" in code_str or "2345-7" in code_str:
            return "glucose"
        
        # Creatinine
        if "creatinine" in display_lower or "2160-0" in code_str:
            return "creatinine"
        
        # Hemoglobin
        if ("hemoglobin" in display_lower and "a1c" not in display_lower) or "718-7" in code_str:
            return "hemoglobin"
        
        # Sodium
        if "sodium" in display_lower or "2951-2" in code_str:
            return "sodium"
        
        # Potassium
        if "potassium" in display_lower or "2823-3" in code_str:
            return "potassium"
        
        # Chloride
        if "chloride" in display_lower or "2075-0" in code_str:
            return "chloride"
        
        # Calcium
        if "calcium" in display_lower or "17861-6" in code_str:
            return "calcium"
        
        # BUN
        if "urea nitrogen" in display_lower or "bun" in display_lower or "3094-0" in code_str:
            return "bun"
        
        # WBC
        if ("white blood cell" in display_lower or "wbc" in display_lower or 
            "leukocyte" in display_lower or "6690-2" in code_str):
            return "wbc"
        
        # RBC
        if ("red blood cell" in display_lower or "rbc" in display_lower or 
            ("erythrocyte" in display_lower and "count" in display_lower) or "789-8" in code_str):
            return "rbc"
        
        # Platelets
        if ("platelet" in display_lower or "thrombocyte" in display_lower or "777-3" in code_str):
            return "platelets"
        
        # Hematocrit
        if ("hematocrit" in display_lower or "hct" in display_lower or "4544-3" in code_str):
            return "hematocrit"
        
        # ALT
        if ("alanine aminotransferase" in display_lower or "alt" in display_lower or 
            "sgot" in display_lower or "1742-6" in code_str):
            return "alt"
        
        # AST
        if ("aspartate aminotransferase" in display_lower or "ast" in display_lower or 
            "sgpt" in display_lower or "1920-8" in code_str):
            return "ast"
        
        # Bilirubin
        if ("bilirubin" in display_lower and "total" in display_lower or 
            "1975-2" in code_str):
            return "bilirubin"
        
        # Albumin
        if ("albumin" in display_lower and "serum" in display_lower or 
            "1751-7" in code_str):
            return "albumin"
        
        # Cholesterol
        if ("cholesterol" in display_lower and "total" in display_lower or 
            "2093-3" in code_str):
            return "cholesterol"
        
        # HDL
        if ("hdl" in display_lower or "high density lipoprotein" in display_lower or 
            "2085-9" in code_str):
            return "hdl"
        
        # LDL
        if ("ldl" in display_lower or "low density lipoprotein" in display_lower or 
            "2089-1" in code_str):
            return "ldl"
        
        # Triglycerides
        if ("triglyceride" in display_lower or "2571-8" in code_str):
            return "triglycerides"
        
        # Magnesium
        if ("magnesium" in display_lower or "2592-6" in code_str):
            return "magnesium"
        
        # Phosphate
        if ("phosphate" in display_lower or "2777-1" in code_str):
            return "phosphate"
        
        # TSH
        if ("tsh" in display_lower or "thyrotropin" in display_lower or 
            "thyroid stimulating" in display_lower or "3016-3" in code_str):
            return "tsh"
        
        return None
    
    def _generate_abnormal_values_chart(self, patient_id: str, use_llm_detection: bool = True) -> Dict[str, Any]:
        """
        RESEARCH-BASED: Generate chart highlighting ALL abnormal values.
        
        Two approaches:
        1. LLM-based detection (default): Uses LLM's medical knowledge to identify abnormal values
        2. Threshold-based (fallback): Uses hardcoded normal ranges for comparison
        
        Args:
            patient_id: Patient identifier
            use_llm_detection: If True, use LLM-based detection (research approach)
                              If False, use threshold-based detection (for comparison)
        """
        from ..core.database import engine
        from sqlalchemy import text
        
        if use_llm_detection:
            # RESEARCH-BASED: Use LLM to detect abnormal values
            return self._generate_abnormal_values_chart_llm(patient_id)
        else:
            # THRESHOLD-BASED: Use hardcoded thresholds (for comparison/evaluation)
            return self._generate_abnormal_values_chart_thresholds(patient_id)
    
    def _generate_abnormal_values_chart_llm(self, patient_id: str) -> Dict[str, Any]:
        """
        RESEARCH-BASED: Use LLM to identify abnormal values using medical knowledge.
        No hardcoded thresholds - pure LLM intelligence.
        
        This is the core research contribution: demonstrating that LLMs can identify
        clinically abnormal values using their inherent medical knowledge without
        explicit threshold definitions.
        
        For research/publication: This method demonstrates semantic understanding
        and medical reasoning capabilities of LLMs.
        """
        from ..core.database import engine
        from sqlalchemy import text
        from .llm_abnormal_detector import LLMAbnormalDetector
        
        # Get all observations from database
        observations = []
        try:
            with engine.connect() as conn:
                sql = """
                SELECT code, display, value_numeric, value_string, unit, effectiveDateTime
                FROM observations
                WHERE patient_id = :pid
                  AND (value_numeric IS NOT NULL OR value_string IS NOT NULL)
                ORDER BY effectiveDateTime DESC
                """
                
                rows = conn.execute(text(sql), {"pid": patient_id}).mappings().all()
                
                for row in rows:
                    display = row.get("display", "")
                    code = row.get("code", "")
                    value_num = row.get("value_numeric")
                    value_str = row.get("value_string")
                    unit = row.get("unit", "")
                    date = row.get("effectiveDateTime", "")
                    
                    value = value_num if value_num is not None else (float(value_str) if value_str and value_str.replace('.','').replace('-','').isdigit() else None)
                    
                    if value is not None:
                        observations.append({
                            "display": display,
                            "code": code,
                            "value": value,
                            "unit": unit,
                            "date": date
                        })
        except Exception as e:
            logger.error(f"Error fetching observations: {e}")
            return None
        
        if not observations:
            return None
        
        # Use LLM to detect abnormal values
        try:
            detector = LLMAbnormalDetector()
            abnormal_values = detector.detect_abnormal_values(patient_id, observations)
            
            if not abnormal_values:
                logger.info(f"LLM found no abnormal values for patient {patient_id}, using threshold fallback")
                # Fallback to threshold-based detection
                return self._generate_abnormal_values_chart_thresholds(patient_id)
        except Exception as e:
            logger.error(f"Error in LLM abnormal detection: {e}, using threshold fallback")
            import traceback
            traceback.print_exc()
            # Fallback to threshold-based detection
            return self._generate_abnormal_values_chart_thresholds(patient_id)
        
        # Group abnormal values by type for chart
        abnormal_by_type = {}
        for abn_val in abnormal_values:
            # Extract observation type from display and code
            display = abn_val.get("display", "")
            code = abn_val.get("code", "")
            obs_type = self._identify_observation_type_from_display(display, code)
            
            if obs_type:
                if obs_type not in abnormal_by_type:
                    abnormal_by_type[obs_type] = []
                abnormal_by_type[obs_type].append({
                    "display": display,
                    "value": abn_val.get("value"),
                    "unit": abn_val.get("unit", ""),
                    "date": abn_val.get("date", "")
                })
            else:
                # Unknown type - still include it with generic name
                generic_type = display.split(":")[0] if ":" in display else display[:30]
                if generic_type not in abnormal_by_type:
                    abnormal_by_type[generic_type] = []
                abnormal_by_type[generic_type].append({
                    "display": display,
                    "value": abn_val.get("value"),
                    "unit": abn_val.get("unit", ""),
                    "date": abn_val.get("date", "")
                })
        
        # Generate chart using existing chart generation logic
        if not abnormal_by_type:
            return None
        
        # Group by scale: vital signs vs lab values
        vital_signs_types = ["systolic_bp", "diastolic_bp", "heart_rate", "temperature", "respiratory_rate"]
        lab_values_types = [
            "glucose", "creatinine", "hemoglobin", "sodium", "potassium", "chloride", "calcium", "bun",
            "wbc", "rbc", "platelets", "hematocrit", "alt", "ast", "bilirubin", "albumin",
            "cholesterol", "hdl", "ldl", "triglycerides", "magnesium", "phosphate", "tsh"
        ]
        
        vital_signs_abnormal = {k: v for k, v in abnormal_by_type.items() if k in vital_signs_types}
        lab_values_abnormal = {k: v for k, v in abnormal_by_type.items() if k in lab_values_types}
        
        # Generate charts
        charts = []
        if vital_signs_abnormal:
            chart = self._generate_abnormal_values_chart_for_group(
                patient_id, vital_signs_abnormal, {}, "Vital Signs", "vital_signs"
            )
            if chart:
                charts.append(chart)
        
        if lab_values_abnormal:
            chart = self._generate_abnormal_values_chart_for_group(
                patient_id, lab_values_abnormal, {}, "Lab Values", "lab_values"
            )
            if chart:
                charts.append(chart)
        
        if charts:
            if len(charts) == 2:
                return self._combine_abnormal_charts(charts[0], charts[1], patient_id)
            return charts[0]
        return None
    
    def _generate_abnormal_values_chart_thresholds(self, patient_id: str) -> Dict[str, Any]:
        """
        THRESHOLD-BASED: Use hardcoded normal ranges (for comparison/evaluation).
        This is the original implementation using thresholds.
        """
        from ..core.database import engine
        from sqlalchemy import text
        
        # Normal ranges for checking
        # Expanded to include common lab values
        NORMAL_RANGES = {
            # Vital Signs
            "systolic_bp": (90, 120),
            "diastolic_bp": (60, 80),
            "heart_rate": (60, 100),
            "temperature": (36.1, 37.2),
            "respiratory_rate": (12, 20),
            # Basic Metabolic Panel
            "glucose": (70, 100),  # Fasting
            "creatinine": (0.6, 1.2),
            "sodium": (135, 145),
            "potassium": (3.5, 5.0),
            "chloride": (98, 107),
            "calcium": (8.5, 10.5),
            "bun": (7, 20),
            # Complete Blood Count
            "hemoglobin": (12, 16),  # Women (default)
            "wbc": (4.0, 11.0),  # White Blood Cell count (x10^3/μL)
            "rbc": (4.0, 5.5),  # Red Blood Cell count (x10^6/μL) - women
            "platelets": (150, 450),  # Platelet count (x10^3/μL)
            "hematocrit": (36, 46),  # Hematocrit (%) - women
            # Liver Function Tests
            "alt": (7, 56),  # Alanine Aminotransferase (U/L)
            "ast": (10, 40),  # Aspartate Aminotransferase (U/L)
            "bilirubin": (0.1, 1.2),  # Total Bilirubin (mg/dL)
            "albumin": (3.5, 5.0),  # Albumin (g/dL)
            # Lipid Panel
            "cholesterol": (0, 200),  # Total Cholesterol (mg/dL) - <200 optimal
            "hdl": (40, 100),  # HDL Cholesterol (mg/dL) - >40 for men, >50 for women
            "ldl": (0, 100),  # LDL Cholesterol (mg/dL) - <100 optimal
            "triglycerides": (0, 150),  # Triglycerides (mg/dL) - <150 normal
            # Other Common Labs
            "magnesium": (1.7, 2.2),  # Magnesium (mg/dL)
            "phosphate": (2.5, 4.5),  # Phosphate (mg/dL)
            "tsh": (0.4, 4.0),  # Thyroid Stimulating Hormone (mIU/L)
        }
        
        def identify_observation_type(display, code):
            """Identify observation type from display name and code"""
            if not display:
                display = ""
            display_lower = display.lower()
            code_str = str(code) if code else ""
            
            # Blood pressure
            if "systolic" in display_lower or "8480-6" in code_str:
                return "systolic_bp"
            if "diastolic" in display_lower or "8462-4" in code_str:
                return "diastolic_bp"
            if "blood pressure" in display_lower:
                return "blood_pressure"
            
            # Heart rate
            if "heart rate" in display_lower or "pulse" in display_lower or "8867-4" in code_str:
                return "heart_rate"
            
            # Temperature
            if "temperature" in display_lower or "temp" in display_lower or "8310-5" in code_str:
                return "temperature"
            
            # Respiratory
            if "respiratory" in display_lower or "9279-1" in code_str:
                return "respiratory_rate"
            
            # Glucose
            if "glucose" in display_lower or "blood sugar" in display_lower or "2339-0" in code_str or "2345-7" in code_str:
                return "glucose"
            
            # Creatinine
            if "creatinine" in display_lower or "2160-0" in code_str:
                return "creatinine"
            
            # Hemoglobin
            if ("hemoglobin" in display_lower and "a1c" not in display_lower) or "718-7" in code_str:
                return "hemoglobin"
            
            # Sodium
            if "sodium" in display_lower or "2951-2" in code_str:
                return "sodium"
            
            # Potassium
            if "potassium" in display_lower or "2823-3" in code_str:
                return "potassium"
            
            # Chloride
            if "chloride" in display_lower or "2075-0" in code_str:
                return "chloride"
            
            # Calcium
            if "calcium" in display_lower or "17861-6" in code_str:
                return "calcium"
            
            # BUN
            if "urea nitrogen" in display_lower or "bun" in display_lower or "3094-0" in code_str:
                return "bun"
            
            # WBC (White Blood Cell count)
            if ("white blood cell" in display_lower or "wbc" in display_lower or 
                "leukocyte" in display_lower or "6690-2" in code_str):
                return "wbc"
            
            # RBC (Red Blood Cell count)
            if ("red blood cell" in display_lower or "rbc" in display_lower or 
                "erythrocyte" in display_lower and "count" in display_lower or "789-8" in code_str):
                return "rbc"
            
            # Platelets
            if ("platelet" in display_lower or "thrombocyte" in display_lower or "777-3" in code_str):
                return "platelets"
            
            # Hematocrit
            if ("hematocrit" in display_lower or "hct" in display_lower or "4544-3" in code_str):
                return "hematocrit"
            
            # ALT (Alanine Aminotransferase)
            if ("alanine aminotransferase" in display_lower or "alt" in display_lower or 
                "sgot" in display_lower or "1742-6" in code_str):
                return "alt"
            
            # AST (Aspartate Aminotransferase)
            if ("aspartate aminotransferase" in display_lower or "ast" in display_lower or 
                "sgpt" in display_lower or "1920-8" in code_str):
                return "ast"
            
            # Bilirubin
            if ("bilirubin" in display_lower and "total" in display_lower or 
                "1975-2" in code_str):
                return "bilirubin"
            
            # Albumin
            if ("albumin" in display_lower and "serum" in display_lower or 
                "1751-7" in code_str):
                return "albumin"
            
            # Cholesterol
            if ("cholesterol" in display_lower and "total" in display_lower or 
                "2093-3" in code_str):
                return "cholesterol"
            
            # HDL
            if ("hdl" in display_lower or "high density lipoprotein" in display_lower or 
                "2085-9" in code_str):
                return "hdl"
            
            # LDL
            if ("ldl" in display_lower or "low density lipoprotein" in display_lower or 
                "2089-1" in code_str):
                return "ldl"
            
            # Triglycerides
            if ("triglyceride" in display_lower or "2571-8" in code_str):
                return "triglycerides"
            
            # Magnesium
            if ("magnesium" in display_lower or "2592-6" in code_str):
                return "magnesium"
            
            # Phosphate
            if ("phosphate" in display_lower or "2777-1" in code_str):
                return "phosphate"
            
            # TSH (Thyroid Stimulating Hormone)
            if ("tsh" in display_lower or "thyrotropin" in display_lower or 
                "thyroid stimulating" in display_lower or "3016-3" in code_str):
                return "tsh"
            
            return None
        
        def is_abnormal(obs_type, value):
            """Check if value is abnormal"""
            if obs_type not in NORMAL_RANGES or value is None:
                # Unknown type - can't determine if abnormal without threshold
                # Return False to exclude from chart (only show known types)
                # Alternative: Could use LLM-based detection here, but for now exclude
                return False
            
            try:
                value_num = float(value)
                min_val, max_val = NORMAL_RANGES[obs_type]
                return value_num < min_val or value_num > max_val
            except:
                return False
        
        def collect_unknown_observations(display, code, value, unit, date):
            """Collect observations that don't match known types for potential LLM-based detection"""
            # This could be used to show "other observations" that might be abnormal
            # For now, we'll just log them
            if value is not None:
                logger.debug(f"Unknown observation type: {display} (code: {code}) = {value} {unit}")
        
        # Get all observations from database
        abnormal_by_type = {}
        all_observations = {}
        
        try:
            with engine.connect() as conn:
                sql = """
                SELECT code, display, value_numeric, value_string, unit, effectiveDateTime
                FROM observations
                WHERE patient_id = :pid
                  AND (value_numeric IS NOT NULL OR value_string IS NOT NULL)
                ORDER BY effectiveDateTime DESC
                """
                
                rows = conn.execute(text(sql), {"pid": patient_id}).mappings().all()
                
                for row in rows:
                    display = row.get("display", "")
                    code = row.get("code", "")
                    value_num = row.get("value_numeric")
                    value_str = row.get("value_string")
                    unit = row.get("unit", "")
                    date = row.get("effectiveDateTime", "")
                    
                    # Identify observation type
                    obs_type = identify_observation_type(display, code)
                    
                    value = value_num if value_num is not None else (float(value_str) if value_str and value_str.replace('.','').replace('-','').isdigit() else None)
                    
                    if obs_type:
                        # Known type - check for abnormal
                        if obs_type not in all_observations:
                            all_observations[obs_type] = []
                        
                        if value is not None:
                            all_observations[obs_type].append({
                                "display": display,
                                "value": value,
                                "unit": unit,
                                "date": date
                            })
                            
                            # Check if abnormal
                            if is_abnormal(obs_type, value):
                                if obs_type not in abnormal_by_type:
                                    abnormal_by_type[obs_type] = []
                                abnormal_by_type[obs_type].append({
                                    "display": display,
                                    "value": value,
                                    "unit": unit,
                                    "date": date
                                })
                    elif value is not None:
                        # Unknown type - log for potential future expansion
                        collect_unknown_observations(display, code, value, unit, date)
        except Exception as e:
            logger.error(f"Error fetching abnormal values from database: {e}")
            return {
            "type": "abnormal_values",
            "patient_id": patient_id,
                "data": {"labels": [], "datasets": []},
                "options": {},
                "error": str(e)
            }
        
        # If no abnormal values, return None (PHASE 2: no empty charts)
        if not abnormal_by_type:
            logger.info(f"No abnormal values found for patient {patient_id}")
            return None
        
        # Group by scale: vital signs vs lab values
        vital_signs_types = ["systolic_bp", "diastolic_bp", "heart_rate", "temperature", "respiratory_rate"]
        lab_values_types = [
            "glucose", "creatinine", "hemoglobin", "sodium", "potassium", "chloride", "calcium", "bun",
            "wbc", "rbc", "platelets", "hematocrit", "alt", "ast", "bilirubin", "albumin",
            "cholesterol", "hdl", "ldl", "triglycerides", "magnesium", "phosphate", "tsh"
        ]
        
        vital_signs_abnormal = {k: v for k, v in abnormal_by_type.items() if k in vital_signs_types}
        lab_values_abnormal = {k: v for k, v in abnormal_by_type.items() if k in lab_values_types}
        
        # Generate chart(s) - combine both groups into single chart if both exist
        charts = []
        
        # Generate vital signs chart if has abnormal values
        if vital_signs_abnormal:
            chart = self._generate_abnormal_values_chart_for_group(
                patient_id, vital_signs_abnormal, NORMAL_RANGES, "Vital Signs", "vital_signs"
            )
            if chart:
                charts.append(chart)
        
        # Generate lab values chart if has abnormal values
        if lab_values_abnormal:
            chart = self._generate_abnormal_values_chart_for_group(
                patient_id, lab_values_abnormal, NORMAL_RANGES, "Lab Values", "lab_values"
            )
            if chart:
                charts.append(chart)
        
        # Return chart(s)
        if charts:
            # If both groups have data, combine into single chart
            if len(charts) == 2:
                # Combine both charts
                combined_chart = self._combine_abnormal_charts(charts[0], charts[1], patient_id)
                return combined_chart
            else:
                # Return single chart
                return charts[0]
        else:
            # PHASE 2: No empty charts - return None if no data
            return None
    
    def _combine_abnormal_charts(self, chart1, chart2, patient_id):
        """Combine two abnormal values charts (vital signs + lab values) into one"""
        # Merge datasets and labels
        labels1 = set(chart1.get("data", {}).get("labels", []))
        labels2 = set(chart2.get("data", {}).get("labels", []))
        all_labels = sorted(list(labels1.union(labels2)))
        
        datasets1 = chart1.get("data", {}).get("datasets", [])
        datasets2 = chart2.get("data", {}).get("datasets", [])
        
        # Combine datasets
        combined_datasets = datasets1 + datasets2
        
        # Create combined chart
        combined_chart = {
            "type": "abnormal_values",
            "patient_id": patient_id,
            "group": "combined",
            "group_name": "All Abnormal Values",
            "data": {
                "labels": all_labels,
                "datasets": combined_datasets
            },
            "options": chart1.get("options", {}).copy(),  # Use first chart's options as base
            "summary": f"Showing {len(datasets1)} vital signs and {len(datasets2)} lab values abnormal observation types."
        }
        
        # Update title
        if "plugins" in combined_chart["options"] and "title" in combined_chart["options"]["plugins"]:
            combined_chart["options"]["plugins"]["title"]["text"] = f"All Abnormal Values - Patient {patient_id}"
        
        return combined_chart
    
    def _generate_abnormal_values_chart_for_group(self, patient_id: str, abnormal_by_type: Dict[str, List[Dict]], normal_ranges: Dict, group_name: str, group_id: str) -> Dict[str, Any]:
        """Generate chart for a group of abnormal values (vital signs or lab values) with red zones"""
        
        # Prepare datasets for each observation type
        datasets = []
        all_labels = set()
        
        # Color map matching current design
        color_map = {
            "systolic_bp": "#e74c3c",
            "diastolic_bp": "#c0392b",
            "heart_rate": "#2ecc71",
            "temperature": "#e91e63",
            "respiratory_rate": "#00bcd4",
            "glucose": "#e74c3c",
            "creatinine": "#3498db",
            "hemoglobin": "#3498db",
            "sodium": "#9b59b6",
            "potassium": "#1abc9c",
            "chloride": "#1abc9c",
            "calcium": "#34495e",
            "bun": "#e67e22",
        }
        
        # Display name mapping
        display_names = {
            "systolic_bp": "Systolic BP",
            "diastolic_bp": "Diastolic BP",
            "heart_rate": "Heart Rate",
            "temperature": "Temperature",
            "respiratory_rate": "Respiratory Rate",
            "glucose": "Glucose",
            "creatinine": "Creatinine",
            "hemoglobin": "Hemoglobin",
            "sodium": "Sodium",
            "potassium": "Potassium",
            "chloride": "Chloride",
            "calcium": "Calcium",
            "bun": "BUN",
        }
        
        for obs_type, values in abnormal_by_type.items():
            if not values:
                continue
            
            # Sort by date
            values_sorted = sorted(values, key=lambda x: x.get("date", ""))
            
            # Get color
            color = color_map.get(obs_type, "#3498db")
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            bg_color = f"rgba({r}, {g}, {b}, 0.1)"
            
            # Prepare data points
            data_points = []
            labels = []
            for val in values_sorted:
                date_val = val.get("date", "")
                if date_val:
                    # Format date for display
                    try:
                        from datetime import datetime
                        # Handle both string and datetime objects
                        if isinstance(date_val, str):
                            dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        elif isinstance(date_val, datetime):
                            dt = date_val
                        else:
                            dt = datetime.fromisoformat(str(date_val).replace('Z', '+00:00'))
                        date_label = dt.strftime("%Y-%m-%d")
                        labels.append(date_label)
                        all_labels.add(date_label)
                    except Exception as e:
                        # Fallback: use string representation
                        date_str = str(date_val)
                        date_label = date_str[:10] if len(date_str) >= 10 else date_str
                        labels.append(date_label)
                        all_labels.add(date_label)
                else:
                    labels.append("Unknown")
                    all_labels.add("Unknown")
                
                data_points.append(val.get("value"))
            
            # Get unit from first value
            unit = values_sorted[0].get("unit", "")
            display_name = display_names.get(obs_type, obs_type.replace("_", " ").title())
            
            dataset = {
                "label": f"{display_name} ({unit})" if unit else display_name,
                "data": data_points,
                "borderColor": color,
                "backgroundColor": bg_color,
                "tension": 0.4,
                "borderWidth": 3,
                "pointBackgroundColor": color,
                "pointBorderColor": color,
                "pointRadius": 6,
                "pointHoverRadius": 8,
                "fill": True
            }
            
            datasets.append(dataset)
        
        if not datasets:
            return None
        
        # Sort labels chronologically
        sorted_labels = sorted(list(all_labels))
        
        # Get normal range for annotations (use first observation type's range)
        first_obs_type = list(abnormal_by_type.keys())[0]
        normal_min, normal_max = normal_ranges.get(first_obs_type, (0, 100))
        
        # Generate chart matching current design style
        chart_data = {
            "type": "abnormal_values",
            "patient_id": patient_id,
            "group": group_id,
            "group_name": group_name,
            "data": {
                "labels": sorted_labels,
                "datasets": datasets
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": False,
                        "title": {
                            "display": True,
                            "text": f"{group_name} Values",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    },
                    "x": {
                        "title": {
                            "display": True,
                            "text": "Date",
                            "font": {
                                "size": 14,
                                "weight": "bold"
                            }
                        },
                        "grid": {
                            "color": "rgba(0,0,0,0.1)",
                            "lineWidth": 1
                        },
                        "ticks": {
                            "font": {
                                "size": 12
                            }
                        }
                    }
                },
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Abnormal {group_name} - Patient {patient_id}",
                        "font": {
                            "size": 16,
                            "weight": "bold"
                        },
                        "color": "#2c3e50"
                    },
                    "legend": {
                        "display": True,
                        "position": "top",
                        "labels": {
                            "font": {
                                "size": 12
                            }
                        }
                    },
                    "annotation": {
                        "annotations": {}
                    }
                }
            },
            "summary": f"Showing {len(abnormal_by_type)} abnormal {group_name.lower()} observation types with {sum(len(v) for v in abnormal_by_type.values())} total abnormal values."
        }
        
        return chart_data
    
    def _generate_professional_vitals_dashboard(self, patient_id: str) -> Dict[str, Any]:
        """Generate professional medical dashboard with multiple vital signs"""
        glucose_data = self.extract_observation_data(patient_id, "glucose")
        bp_data = self.extract_observation_data(patient_id, "blood pressure")
        hr_data = self.extract_observation_data(patient_id, "heart rate")
        temp_data = self.extract_observation_data(patient_id, "temperature")
        
        dashboard_data = {
            "type": "professional_vitals_dashboard",
            "patient_id": patient_id,
            "data": {
                "glucose": {
                    "latest": glucose_data[-1]["value"] if glucose_data else None,
                    "unit": "mg/dL",
                    "normal_range": "70-140",
                    "status": "high" if glucose_data and glucose_data[-1]["value"] > 140 else "normal",
                    "trend": "stable"
                },
                "blood_pressure": {
                    "systolic": bp_data[-1]["value"] if bp_data else None,
                    "diastolic": bp_data[-1]["value"] if bp_data else None,
                    "unit": "mmHg",
                    "normal_range": "<130/<80",
                    "status": "high" if bp_data and bp_data[-1]["value"] > 130 else "normal",
                    "trend": "stable"
                },
                "heart_rate": {
                    "latest": hr_data[-1]["value"] if hr_data else None,
                    "unit": "bpm",
                    "normal_range": "60-100",
                    "status": "normal",
                    "trend": "stable"
                },
                "temperature": {
                    "latest": temp_data[-1]["value"] if temp_data else None,
                    "unit": "°C",
                    "normal_range": "36.1-37.2",
                    "status": "normal",
                    "trend": "stable"
                }
            },
            "charts": {
                "glucose_trend": self._generate_glucose_chart(patient_id),
                "bp_trend": self._generate_blood_pressure_chart(patient_id),
                "hr_trend": self._generate_heart_rate_chart(patient_id)
            },
            "summary": {
                "total_abnormal_values": 0,
                "critical_alerts": [],
                "recommendations": []
            }
        }
        
        # Calculate summary statistics
        abnormal_count = 0
        alerts = []
        recommendations = []
        
        if dashboard_data["data"]["glucose"]["status"] == "high":
            abnormal_count += 1
            alerts.append("Elevated glucose levels detected")
            recommendations.append("Consider diabetes screening")
        
        if dashboard_data["data"]["blood_pressure"]["status"] == "high":
            abnormal_count += 1
            alerts.append("Elevated blood pressure detected")
            recommendations.append("Monitor blood pressure regularly")
        
        dashboard_data["summary"]["total_abnormal_values"] = abnormal_count
        dashboard_data["summary"]["critical_alerts"] = alerts
        dashboard_data["summary"]["recommendations"] = recommendations
        
        return dashboard_data

    def get_available_chart_types(self) -> List[Dict[str, str]]:
        """Get list of available chart types"""
        return [
            {"type": "glucose_trend", "name": "Glucose Trend", "description": "Show glucose levels over time"},
            {"type": "blood_pressure_trend", "name": "Blood Pressure Trend", "description": "Show systolic and diastolic BP over time"},
            {"type": "heart_rate_trend", "name": "Heart Rate Trend", "description": "Show heart rate over time"},
            {"type": "vitals_dashboard", "name": "Vitals Dashboard", "description": "Comprehensive vital signs overview"},
            {"type": "professional_vitals_dashboard", "name": "Professional Medical Dashboard", "description": "Clinical-grade vital signs dashboard with alerts"},
            {"type": "abnormal_values", "name": "Abnormal Values", "description": "Highlight abnormal clinical values"}
        ]

# Global instance
visualization_service = VisualizationService()
