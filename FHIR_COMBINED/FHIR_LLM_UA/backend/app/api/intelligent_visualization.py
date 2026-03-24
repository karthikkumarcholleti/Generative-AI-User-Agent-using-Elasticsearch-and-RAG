# backend/app/api/intelligent_visualization.py

"""
Intelligent Visualization Service
Automatically generates appropriate visualizations based on question intent and retrieved data
"""

from typing import List, Dict, Any, Optional, Tuple
from .visualization_service import visualization_service
import logging
import re

logger = logging.getLogger(__name__)

class IntelligentVisualizationService:
    """Service for intelligently determining and generating visualizations based on context"""
    
    def __init__(self):
        self.viz_service = visualization_service
    
    def scan_retrieved_data_for_numeric_observations(self, retrieved_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan retrieved_data and identify numeric observations that have actual values.
        Returns dict mapping observation_type -> list of observation items with numeric values.
        """
        observations = {}
        
        for item in retrieved_data:
            if item.get("data_type") != "observations":
                continue
            
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            
            value_str = metadata.get("value", "")
            if not value_str:
                continue
            
            # Check if value is numeric
            try:
                import re
                numbers = re.findall(r'-?\d+\.?\d*', str(value_str))
                if not numbers:
                    continue
                numeric_value = float(numbers[0])
            except (ValueError, TypeError):
                continue
            
            # Identify observation type
            display = metadata.get("display", "").lower() if metadata.get("display") else ""
            code = metadata.get("code", "").lower() if metadata.get("code") else ""
            
            obs_type = self._identify_observation_type(display, code)
            if not obs_type:
                continue
            
            # Only include if we have a valid numeric value
            if obs_type not in observations:
                observations[obs_type] = []
            observations[obs_type].append(item)
        
        return observations
    
    def _identify_observation_type(self, display: str, code: str) -> Optional[str]:
        """Identify observation type from display name and code"""
        if not display and not code:
            return None
        
        # Check for specific observation types
        if "creatinine" in display or "2160-0" in code or "33914-3" in code:
            return "creatinine"
        elif ("hemoglobin" in display and "a1c" not in display and "hba1c" not in display) or "718-7" in code:
            return "hemoglobin"
        elif "a1c" in display or "hba1c" in display or "hemoglobin a1c" in display or "4548-4" in code:
            return "a1c"
        elif "heart rate" in display or "pulse" in display or "hr" in display or "8867-4" in code:
            return "heart rate"
        elif "glucose" in display or "blood sugar" in display or "2339-0" in code:
            return "glucose"
        elif "blood pressure" in display or "systolic" in display or "diastolic" in display or "8480-6" in code or "8462-4" in code:
            return "blood pressure"
        elif "temperature" in display or "temp" in display or "8310-5" in code:
            return "temperature"
        elif "respiratory rate" in display or "9279-1" in code:
            return "respiratory rate"
        elif "oxygen saturation" in display or "spo2" in display or "2708-6" in code:
            return "oxygen saturation"
        elif "bmi" in display or "body mass index" in display or "39156-5" in code:
            return "bmi"
        elif "weight" in display or "29463-7" in code:
            return "weight"
        
        # Generic: extract main keyword from display
        if display:
            # Try to extract meaningful keyword
            words = display.split()
            for word in words:
                if len(word) > 3 and word not in ["observation", "value", "recorded", "date"]:
                    return word.lower()
        
        return None
    
    def filter_observations_by_answer_relevance(self, observations: Dict[str, List[Dict[str, Any]]], answer_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Filter observations to only include those mentioned/relevant in the answer.
        This ensures charts show only what the answer focuses on, not unrelated RAG results.
        """
        if not answer_text:
            return observations
        
        answer_lower = answer_text.lower()
        filtered = {}
        
        for obs_type, items in observations.items():
            # Check if observation type is mentioned in answer
            if obs_type in answer_lower:
                filtered[obs_type] = items
                continue
            
            # Check if any related terms are mentioned
            related_terms = {
                "creatinine": ["creatinine", "kidney", "renal"],
                "hemoglobin": ["hemoglobin", "hgb", "hb"],
                "a1c": ["a1c", "hba1c", "hemoglobin a1c", "glycated"],
                "heart rate": ["heart rate", "pulse", "hr", "heartbeat"],
                "glucose": ["glucose", "blood sugar", "sugar", "diabetes", "diabetic"],
                "blood pressure": ["blood pressure", "bp", "systolic", "diastolic", "hypertension"],
                "temperature": ["temperature", "temp", "fever"],
                "respiratory rate": ["respiratory", "breathing", "respiration"],
                "oxygen saturation": ["oxygen", "saturation", "spo2"],
                "bmi": ["bmi", "body mass", "weight"],
                "weight": ["weight", "kg", "pounds"]
            }
            
            terms = related_terms.get(obs_type, [obs_type])
            if any(term in answer_lower for term in terms):
                filtered[obs_type] = items
        
        return filtered
    
    def should_generate_visualization(self, query: str, intent: Dict[str, Any], retrieved_data: List[Dict[str, Any]], answer_text: Optional[str] = None) -> Tuple[bool, Optional[List[str]]]:
        """
        RAG-driven chart detection: Scan retrieved_data for numeric observations.
        Only generate charts if:
        1. Query is about observations (intent type == "observations" OR specific_observation != "none")
        2. Numeric observations exist in retrieved_data
        3. Observations are mentioned/relevant in answer_text (if provided)
        4. Observations have actual data points
        
        PHASE 2: Only generate charts for observation queries, no empty charts.
        
        Returns:
            (should_generate: bool, chart_types: Optional[List[str]])
        """
        # Safely handle None query
        if query is None:
            query = ""
        query_lower = query.lower() if query else ""
        
        # Get intent type FIRST
        # Intent can have either "type" or "intent_type" key (from different sources)
        intent_type = intent.get("type") or intent.get("intent_type", "")
        specific_observation = intent.get("specific_observation", "none")
        
        logger.info(f"should_generate_visualization called: query='{query[:50]}...', intent_type='{intent_type}', intent_keys={list(intent.keys())}")
        
        # PRIORITY 0: Check for abnormal/risk values queries FIRST (before any other checks)
        # RESEARCH-BASED: Use ONLY LLM intent classification (no keyword matching)
        # The LLM semantically understands queries like "risk values", "concerning vitals", etc.
        # IMPORTANT: Check this FIRST, because abnormal_values chart queries DB directly (doesn't need retrieved_data)
        if intent_type == "analysis":
            logger.info("LLM classified query as 'analysis' intent (abnormal/risk values) - generating abnormal_values chart")
            # Return immediately - abnormal_values chart doesn't need retrieved_data, it queries DB directly
            return True, ["abnormal_values"]
        
        # PHASE 2: Only generate charts for observation queries
        # Check if query is about observations
        is_observation_query = (
            intent_type == "observations" or 
            specific_observation != "none" or
            intent_type == "grouped_visualization" or
            intent_type == "visualization"
        )
        
        if not is_observation_query:
            logger.info(f"RAG-driven chart generation: Query is not about observations (intent: {intent_type}, specific_obs: {specific_observation}). Skipping chart generation.")
            return False, None
        
        # RAG-driven approach: Scan retrieved_data for numeric observations
        # Step 1: Scan retrieved_data for numeric observations
        numeric_observations = self.scan_retrieved_data_for_numeric_observations(retrieved_data)
        
        if not numeric_observations:
            # No numeric observations found - don't generate charts (PHASE 2: no empty charts)
            logger.info("RAG-driven chart generation: No numeric observations found in retrieved_data. Skipping chart generation to avoid empty charts.")
            return False, None
        
        logger.info(f"RAG-driven chart generation: Found {len(numeric_observations)} observation types from retrieved_data: {list(numeric_observations.keys())}")
        
        # PRIORITY 1: Check if query asks for "all vitals", "all observations", "vital signs", etc.
        # RESEARCH-BASED: Use LLM intent classification (wants_all_data, wants_grouped) instead of keywords
        if intent.get("wants_all_data", False) or intent.get("wants_grouped", False) or intent_type == "grouped_visualization":
            # For "all vitals" queries, generate comprehensive chart
            # Don't filter by answer relevance - show ALL observations found
            if len(numeric_observations) > 1:
                logger.info(f"'All vitals' query detected - generating comprehensive chart for {len(numeric_observations)} observation types")
                return True, ["all_observations"]
            elif len(numeric_observations) == 1:
                # Only one type, but user asked for "all" - still show it
                obs_type = list(numeric_observations.keys())[0]
                if obs_type == "heart rate":
                    return True, ["heart_rate_trend"]
                elif obs_type == "glucose":
                    return True, ["glucose_trend"]
                elif obs_type == "blood pressure":
                    return True, ["blood_pressure_trend"]
                else:
                    return True, [f"observation_trend:{obs_type}"]
        
        # Step 2: Filter by answer relevance (if answer_text provided)
        # This ensures we only show charts for observations mentioned in the answer
        # CRITICAL: If RAG retrieves unrelated observations, but answer only mentions specific ones,
        # charts show only those mentioned in the answer
        # EXCEPTION: For "vital signs" queries, don't filter by answer if we have numeric observations
        # This ensures charts are generated even if answer is truncated
        is_vital_signs_query = "vital sign" in query_lower or "vital signs" in query_lower
        if answer_text and not is_vital_signs_query:
            filtered_observations = self.filter_observations_by_answer_relevance(numeric_observations, answer_text)
            if not filtered_observations:
                logger.info("RAG-driven chart generation: No observations relevant to answer_text found after filtering.")
                return False, None
            logger.info(f"After Answer Filtering: {list(filtered_observations.keys())}")
            numeric_observations = filtered_observations
        elif is_vital_signs_query and numeric_observations:
            logger.info("Vital signs query detected - skipping answer filtering to ensure chart generation")
        
        # Step 3: Determine chart types based on query and filtered observations
        chart_types = []
        
        # Note: Analysis intent with abnormal keywords is already handled in PRIORITY 0 above
        
        # Prioritize explicit query requests
        specific_observation_keywords = {
            "creatinine": "creatinine", "hemoglobin": "hemoglobin", "a1c": "a1c",
            "heart rate": "heart rate", "glucose": "glucose", "blood pressure": "blood pressure",
            "temperature": "temperature", "respiratory rate": "respiratory rate",
            "oxygen saturation": "oxygen saturation", "bmi": "bmi", "weight": "weight"
        }
        
        for keyword, obs_type in specific_observation_keywords.items():
            if keyword in query_lower and obs_type in numeric_observations:
                if obs_type in ["heart rate", "glucose", "blood pressure"]:
                    chart_types.append(f"{obs_type.replace(' ', '_')}_trend")
                else:
                    chart_types.append(f"observation_trend:{obs_type}")
        
        # If no specific query match, but visualization keywords are present, or it's a general observation query
        if not chart_types:
            visualization_keywords = ["show", "display", "chart", "graph", "plot", "visual", "visualization", "trend", "pattern", "over time", "history", "timeline", "compare", "abnormal", "high", "low", "elevated", "concerning", "out of range"]
            
            intent_type_check = intent.get("type") or intent.get("intent_type", "")
            if any(keyword in query_lower for keyword in visualization_keywords) or intent_type_check == "observations" or intent.get("wants_visualization", False):
                # If multiple observation types are relevant, generate a categorized or all_observations chart
                if len(numeric_observations) > 1:
                    # Check if query asks for "all observations" or similar
                    if any(kw in query_lower for kw in ["all observations", "all data", "everything", "complete"]):
                        chart_types.append("all_observations")
                    else:
                        # Default to categorized if multiple types and no specific "all" request
                        chart_types.append("categorized_observations")
                elif len(numeric_observations) == 1:
                    # If only one type, generate a trend chart for that specific observation
                    obs_type = list(numeric_observations.keys())[0]
                    if obs_type in ["heart rate", "glucose", "blood pressure"]:
                        chart_types.append(f"{obs_type.replace(' ', '_')}_trend")
                    else:
                        chart_types.append(f"observation_trend:{obs_type}")
            
            # If still no chart types, and it's a condition query that might imply observations (e.g., "is diabetic?")
            intent_type_check = intent.get("type") or intent.get("intent_type", "")
            if not chart_types and intent_type_check == "conditions":
                # Check for conditions that imply specific observations (e.g., diabetes -> glucose, A1C)
                condition_to_obs_map = {
                    "diabetes": ["glucose", "a1c"],
                    "diabetic": ["glucose", "a1c"],
                    "hypertension": ["blood pressure"],
                    "high blood pressure": ["blood pressure"],
                    "kidney disease": ["creatinine"],
                    "heart disease": ["heart rate", "blood pressure"],
                }
                
                for condition_keyword, implied_obs_types in condition_to_obs_map.items():
                    if condition_keyword in query_lower:
                        for obs_type in implied_obs_types:
                            if obs_type in numeric_observations:
                                if obs_type in ["heart rate", "glucose", "blood pressure"]:
                                    chart_types.append(f"{obs_type.replace(' ', '_')}_trend")
                                else:
                                    chart_types.append(f"observation_trend:{obs_type}")
                        # Break after finding relevant charts for one condition keyword
                        if chart_types:
                            break
        
        if chart_types:
            logger.info(f"RAG-driven chart generation: Determined {len(chart_types)} chart types: {chart_types}")
            return True, chart_types
        
        return False, None
    
    def _determine_chart_type(self, query: str, intent: Dict[str, Any], retrieved_data: List[Dict[str, Any]]) -> str:
        """
        Dynamically determine the most appropriate chart type based on query and retrieved data.
        This function analyzes the retrieved data to find observation types and generates focused charts.
        """
        # Safely handle None query
        if query is None:
            query = ""
        query_lower = query.lower() if query else ""
        
        # PRIORITY 1: Check query for specific observation types FIRST (before checking data)
        # This ensures we generate focused charts for specific queries
        specific_observations = {
            "creatinine": "creatinine",
            "hemoglobin": "hemoglobin",
            "heart rate": "heart_rate",
            "pulse": "heart_rate",
            "hr": "heart_rate",
            "glucose": "glucose",
            "blood sugar": "glucose",
            "blood pressure": "blood_pressure",
            "bp": "blood_pressure",
            "systolic": "blood_pressure",
            "diastolic": "blood_pressure",
        }
        
        # Check if query mentions a specific observation
        for keyword, chart_type in specific_observations.items():
            if keyword in query_lower:
                # Verify this observation exists in retrieved_data before generating chart
                observation_found = False
                for item in retrieved_data:
                    if item.get("data_type") == "observations":
                        display = (item.get("metadata", {}).get("display") or "").lower()
                        code = (item.get("metadata", {}).get("code") or "").lower()
                        content = (item.get("content") or "").lower()
                        
                        # Check for match in display, code, or content
                        if keyword in display or keyword in code or keyword in content:
                            # For heart rate, check for specific terms
                            if keyword in ["heart rate", "pulse", "hr"]:
                                if "heart rate" in display or "pulse" in display or "hr" in display:
                                    observation_found = True
                                    break
                            # For blood pressure, check for specific terms
                            elif keyword in ["blood pressure", "bp", "systolic", "diastolic"]:
                                if "blood pressure" in display or "systolic" in display or "diastolic" in display:
                                    observation_found = True
                                    break
                            # For creatinine, check for specific terms
                            elif keyword == "creatinine":
                                if "creatinine" in display or "2160-0" in code or "33914-3" in code:
                                    observation_found = True
                                    break
                            # For other observations, check for keyword match
                            else:
                                observation_found = True
                                break
                
                # CRITICAL: If query mentions a specific observation, ALWAYS return that chart type
                # Even if not found in retrieved_data, we should still try to generate it
                # (data might exist in DB but not in retrieved_data due to RAG limits)
                # Since we're already in the loop where keyword in query_lower, always return
                logger.info(f"Query mentions '{keyword}', returning chart type: {chart_type}")
                # Return predefined chart type for special observations
                if chart_type in ["heart_rate", "glucose", "blood_pressure"]:
                    return f"{chart_type}_trend"
                # Return observation-specific chart for others (creatinine, hemoglobin, etc.)
                else:
                    return f"observation_trend:{chart_type}"
        
        # PRIORITY 2: Check for abnormal values queries
        if "abnormal" in query_lower or ("high" in query_lower and "blood pressure" not in query_lower) or ("low" in query_lower and "blood pressure" not in query_lower):
            return "abnormal_values"
        
        # PRIORITY 3: DYNAMIC DETECTION: Extract observation types from retrieved data
        # This allows us to detect ANY observation type, not just predefined ones
        observation_types_found = {}
        
        for item in retrieved_data:
            if item.get("data_type") == "observations":
                metadata = item.get("metadata", {})
                display = metadata.get("display") or ""
                display = display.lower() if display else ""
                
                # Extract the main observation keyword from display name
                # This works for ANY observation type found in the data
                observation_keyword = self._extract_observation_keyword(display, query_lower)
                
                if observation_keyword:
                    if observation_keyword not in observation_types_found:
                        observation_types_found[observation_keyword] = {
                            "count": 0,
                            "display": metadata.get("display", ""),
                            "has_numeric_value": False
                        }
                    observation_types_found[observation_keyword]["count"] += 1
                    
                    # Check if it has a numeric value (for charting)
                    value = metadata.get("value", "")
                    if value and any(char.isdigit() for char in str(value)):
                        observation_types_found[observation_keyword]["has_numeric_value"] = True
        
        # If we found a single, specific observation type with numeric values, create focused chart
        if len(observation_types_found) == 1:
            obs_keyword = list(observation_types_found.keys())[0]
            obs_info = observation_types_found[obs_keyword]
            
            # Only create chart if it has numeric values and at least one data point
            if obs_info["has_numeric_value"] and obs_info["count"] >= 1:
                # Return observation-specific chart type
                return f"observation_trend:{obs_keyword}"
        
        # If we found multiple observation types, check if query mentions a specific one
        if len(observation_types_found) > 1:
            # Check if query mentions a specific observation type
            for obs_keyword, obs_info in observation_types_found.items():
                if obs_keyword in query_lower and obs_info["has_numeric_value"]:
                    # User asked about this specific observation - create focused chart
                    return f"observation_trend:{obs_keyword}"
            
            # Multiple types found but no specific one mentioned - use all_observations
            return "all_observations"
        
        # Check retrieved data for predefined types (glucose, BP, HR)
        predefined_types = set()
        for item in retrieved_data:
            if item.get("data_type") == "observations":
                display = item.get("metadata", {}).get("display") or ""
                display_lower = display.lower() if display else ""
                if "glucose" in display_lower or "blood sugar" in display_lower:
                    predefined_types.add("glucose")
                elif "blood pressure" in display_lower or "systolic" in display_lower or "diastolic" in display_lower:
                    predefined_types.add("blood_pressure")
                elif "heart rate" in display_lower or "pulse" in display_lower or "hr" in display_lower:
                    predefined_types.add("heart_rate")
        
        # If multiple predefined types, use vitals dashboard
        if len(predefined_types) > 2:
            return "vitals_dashboard"
        
        # If specific predefined type found, use that
        if "glucose" in predefined_types:
            return "glucose_trend"
        if "blood_pressure" in predefined_types:
            return "blood_pressure_trend"
        if "heart_rate" in predefined_types:
            return "heart_rate_trend"
        
        # Default to all observations or abnormal values based on intent
        intent_type_check = intent.get("type") or intent.get("intent_type", "")
        if intent_type_check == "analysis" and "abnormal" in query_lower:
            return "abnormal_values"
        
        return "all_observations"
    
    def _extract_observation_keyword(self, display_name: str, query: str) -> Optional[str]:
        """
        Extract the main observation keyword from display name and query.
        This function intelligently identifies observation types from any display name.
        """
        # Safely handle None values
        if display_name is None:
            display_name = ""
        if query is None:
            query = ""
        display_lower = display_name.lower() if display_name else ""
        query_lower = query.lower() if query else ""
        
        # Common observation keywords to look for
        observation_keywords = [
            "creatinine", "hemoglobin", "gfr", "glomerular filtration", "cholesterol",
            "sodium", "potassium", "calcium", "bun", "albumin", "bilirubin",
            "temperature", "respiratory", "oxygen", "saturation", "bmi", "weight", "height",
            "glucose", "blood sugar", "blood pressure", "systolic", "diastolic",
            "heart rate", "pulse", "hr", "wbc", "rbc", "platelet", "hematocrit",
            "protein", "urea", "nitrogen", "phosphorus", "magnesium", "chloride",
            "triglyceride", "ldl", "hdl", "ast", "alt", "alkaline phosphatase"
        ]
        
        # First, check if query mentions a specific observation
        for keyword in observation_keywords:
            if keyword in query_lower:
                # Check if this keyword appears in the display name
                if keyword in display_lower:
                    return keyword
        
        # If no match in query, extract from display name
        # Look for the most specific observation keyword in display name
        for keyword in sorted(observation_keywords, key=len, reverse=True):  # Longer keywords first
            if keyword in display_lower:
                return keyword
        
        # If no keyword found, try to extract a meaningful word from display name
        # Remove common prefixes/suffixes and extract main term
        import re
        # Remove common FHIR prefixes
        clean_display = re.sub(r'^observation:\s*', '', display_lower, flags=re.IGNORECASE)
        clean_display = re.sub(r':[^:]*$', '', clean_display)  # Remove everything after last colon
        clean_display = re.sub(r'\s*\([^)]*\)', '', clean_display)  # Remove parentheses
        
        # Extract first meaningful word (usually the observation type)
        words = clean_display.split()
        if words:
            # Return the first significant word (skip common words)
            common_words = {"the", "a", "an", "of", "in", "on", "at", "for", "with", "by"}
            for word in words:
                if word not in common_words and len(word) > 2:
                    return word
        
        return None
    
    def generate_smart_visualization(self, patient_id: str, query: str, intent: Dict[str, Any], retrieved_data: List[Dict[str, Any]], answer_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Intelligently generate a visualization based on query context.
        Uses RAG-driven approach: extracts values directly from retrieved_data (same source as answer).
        
        Returns:
            Chart data dict if visualization should be generated, None otherwise
        """
        # Step 1: Determine if visualization should be generated and what chart types
        should_generate, chart_types = self.should_generate_visualization(query, intent, retrieved_data, answer_text)
        
        if not should_generate or not chart_types:
            logger.info("Visualization not needed or no chart types determined")
            return None
        
        # For now, generate and return only the first chart if multiple are detected.
        # Future enhancement: return a list of charts.
        chart_type = chart_types[0] if isinstance(chart_types, list) else chart_types
        
        logger.info(f"Attempting to generate chart of type: {chart_type}")
        
        try:
            # SPECIAL CASE: For abnormal_values chart, it queries DB directly (doesn't need retrieved_data)
            if chart_type == "abnormal_values":
                logger.info(f"Generating abnormal_values chart (queries DB directly, not from retrieved_data) for patient {patient_id}")
                try:
                    # RESEARCH MODE: Configurable for research vs. production
                    # For research publication: Use LLM-based to demonstrate semantic understanding
                    # For production: Use threshold-based for faster response
                    # Default: True (research mode) - change to False for production performance
                    import os
                    use_llm_for_research = os.getenv("USE_LLM_ABNORMAL_DETECTION", "True").lower() == "true"
                    chart_data = self.viz_service._generate_abnormal_values_chart(patient_id, use_llm_detection=use_llm_for_research)
                    logger.info(f"abnormal_values chart generation result: {chart_data is not None}")
                    if chart_data is None:
                        logger.warning(f"abnormal_values chart returned None for patient {patient_id}")
                except Exception as chart_error:
                    logger.error(f"Error generating abnormal_values chart: {chart_error}", exc_info=True)
                    chart_data = None
            else:
                # CRITICAL: Extract values directly from retrieved_data (same source as answer)
                # This ensures chart shows exactly what RAG retrieved and what the answer is based on
                chart_data = self.viz_service.generate_chart_data_from_retrieved(
                    patient_id, chart_type, retrieved_data
                )
            
            # Check if chart generation failed or returned None (PHASE 2: no empty charts)
            if chart_data is None:
                logger.warning(f"Chart generation returned None for {chart_type} (no data or empty chart)")
                return None
            
            # Check if chart generation failed or has no data
            if chart_data.get("error") or not chart_data.get("data", {}).get("datasets"):
                error_msg = chart_data.get("error", "No datasets")
                logger.warning(f"Chart generation failed or no data for {chart_type}: {error_msg}")
                return None
            
            # Verify chart has actual data points
            datasets = chart_data.get("data", {}).get("datasets", [])
            if datasets:
                # Check first dataset for valid data points
                first_dataset = datasets[0]
                data_points = first_dataset.get("data", [])
                # Filter out None values
                valid_data_points = [dp for dp in data_points if dp is not None]
                
                if not valid_data_points:
                    logger.warning(f"Chart generated but has no valid data points - returning None")
                    return None
                
                logger.info(f"Chart generated successfully with {len(valid_data_points)} data points")
            else:
                logger.warning(f"Chart generated but has no datasets - returning None")
                return None
            
            # Add metadata about why this chart was generated
            chart_data["auto_generated"] = True
            chart_data["generation_reason"] = self._get_generation_reason(query, chart_type)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Failed to generate smart visualization: {e}")
            return None
    
    def _observation_exists_in_data(self, retrieved_data: List[Dict[str, Any]], keywords: List[str]) -> bool:
        """
        Check if any of the given keywords match an observation in retrieved_data
        
        Args:
            retrieved_data: List of retrieved document items
            keywords: List of keywords to search for (e.g., ["glucose", "blood sugar"])
        
        Returns:
            True if observation exists, False otherwise
        """
        if not retrieved_data or not keywords:
            return False
        
        observation_data = [item for item in retrieved_data if item.get("data_type") == "observations"]
        if not observation_data:
            return False
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for item in observation_data:
                display = (item.get("metadata", {}).get("display") or "").lower()
                code = (item.get("metadata", {}).get("code") or "").lower()
                content = (item.get("content") or "").lower()
                
                # Special handling for A1C (must be exact match, not just hemoglobin)
                if keyword_lower in ["a1c", "hemoglobin a1c", "hba1c"]:
                    if "a1c" in display or "hemoglobin a1c" in display or "hba1c" in display:
                        return True
                # Special handling for blood type
                elif keyword_lower == "blood type":
                    if "blood type" in display or "blood group" in display:
                        return True
                # General keyword matching
                elif keyword_lower in display or keyword_lower in code or keyword_lower in content:
                    return True
        
        return False
    
    def _should_show_available_observations(self, query: str, retrieved_data: List[Dict[str, Any]]) -> bool:
        """Determine if we should show available observations when requested one is not found"""
        # Safely handle None query
        if query is None:
            query = ""
        query_lower = query.lower() if query else ""
        
        # Check if query is asking about a specific observation
        observation_keywords = [
            "creatinine", "hemoglobin", "gfr", "cholesterol", "sodium", "potassium",
            "calcium", "bun", "albumin", "bilirubin", "temperature", "respiratory",
            "oxygen", "saturation", "bmi", "weight", "height", "wbc", "rbc", "platelet",
            "glucose", "blood pressure", "heart rate", "pulse"
        ]
        
        # If query mentions a specific observation, we should show alternatives
        for keyword in observation_keywords:
            if keyword in query_lower:
                # Check if we have other observation data
                other_observations = []
                for item in retrieved_data:
                    if item.get("data_type") == "observations":
                        display = item.get("metadata", {}).get("display") or ""
                        display_lower = display.lower() if display else ""
                        if keyword not in display_lower:
                            other_observations.append(item)
                if other_observations:
                    return True
        
        return False
    
    def _generate_available_observations_chart(self, patient_id: str, query: str, retrieved_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Generate a chart showing available observations when requested one is not found.
        Intelligently decides between single multi-series chart or multiple charts.
        """
        # Get all available observations from retrieved data
        available_observations = [item for item in retrieved_data 
                                if item.get("data_type") == "observations"]
        
        if not available_observations:
            # No observations at all - return None (let LLM handle the message)
            return None
        
        # Group observations by type
        observation_groups = {}
        for item in available_observations:
            metadata = item.get("metadata", {})
            display = metadata.get("display", "Unknown")
            value = metadata.get("value", "")
            
            # Check if it has numeric value
            has_numeric = False
            if value:
                try:
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', str(value))
                    if numbers:
                        has_numeric = True
                except:
                    pass
            
            if has_numeric:
                # Clean display name for grouping
                clean_display = self.viz_service._clean_observation_name(display)
                if clean_display not in observation_groups:
                    observation_groups[clean_display] = []
                observation_groups[clean_display].append({
                    "date": metadata.get("date", ""),
                    "value": float(numbers[0]) if numbers else None,
                    "unit": metadata.get("unit", ""),
                    "display": display
                })
        
        if not observation_groups:
            # No numeric observations - return None
            return None
        
        # Decide visualization strategy based on number of observation types
        num_types = len(observation_groups)
        
        if num_types == 1:
            # Single observation type - create focused chart
            obs_name = list(observation_groups.keys())[0]
            return self.viz_service._generate_observation_trend_chart(patient_id, obs_name)
        elif num_types <= 5:
            # 2-5 observation types - single multi-series chart
            return self._generate_multi_observation_chart(patient_id, observation_groups, query)
        else:
            # More than 5 types - use all_observations chart (handles many types well)
            return self.viz_service._generate_all_observations_chart(patient_id)
    
    def _generate_multi_observation_chart(self, patient_id: str, observation_groups: Dict[str, List[Dict[str, Any]]], query: str) -> Dict[str, Any]:
        """
        Generate a multi-series chart showing multiple observation types.
        Used when 2-5 observation types are available.
        """
        # Collect all dates
        all_dates = set()
        for obs_list in observation_groups.values():
            for obs in obs_list:
                if obs.get("date"):
                    all_dates.add(obs["date"])
        
        sorted_dates = sorted([date for date in all_dates if date])
        
        if not sorted_dates:
            return {
                "type": "available_observations",
                "patient_id": patient_id,
                "data": {"labels": [], "datasets": []},
                "error": "No dates available",
                "summary": "Available observations found but no date information."
            }
        
        # Create datasets for each observation type
        datasets = []
        colors = [
            "#e74c3c", "#3498db", "#f39c12", "#9b59b6", "#1abc9c",
            "#34495e", "#e67e22", "#2ecc71", "#8e44ad", "#f1c40f"
        ]
        
        for idx, (obs_name, obs_list) in enumerate(observation_groups.items()):
            # Sort observations by date
            obs_list.sort(key=lambda x: x.get("date", ""))
            
            # Create data array matching sorted dates
            values = []
            unit = obs_list[0].get("unit", "") if obs_list else ""
            
            for date in sorted_dates:
                matching_obs = next((obs for obs in obs_list if obs.get("date") == date), None)
                values.append(matching_obs["value"] if matching_obs else None)
            
            # Only include if we have at least 1 non-null value
            non_null_values = [v for v in values if v is not None]
            if len(non_null_values) >= 1:
                datasets.append({
                    "label": f"{obs_name} ({unit})" if unit else obs_name,
                    "data": values,
                    "borderColor": colors[idx % len(colors)],
                    "backgroundColor": f"rgba({int(colors[idx % len(colors)][1:3], 16)}, {int(colors[idx % len(colors)][3:5], 16)}, {int(colors[idx % len(colors)][5:7], 16)}, 0.1)",
                    "tension": 0.4,
                    "borderWidth": 2,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                    "fill": False
                })
        
        if not datasets:
            return {
                "type": "available_observations",
                "patient_id": patient_id,
                "data": {"labels": [], "datasets": []},
                "error": "No valid data points",
                "summary": "Available observations found but no valid numeric values."
            }
        
        # Generate helpful summary
        obs_names = list(observation_groups.keys())
        summary = f"Showing available observations: {', '.join(obs_names[:3])}"
        if len(obs_names) > 3:
            summary += f" and {len(obs_names) - 3} more"
        
        return {
            "type": "available_observations",
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
                        "text": f"Available Observations - Patient {patient_id}",
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
                            "padding": 20,
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
            },
            "summary": summary,
            "auto_generated": True,
            "generation_reason": f"Requested observation not found. Showing available observations: {', '.join(obs_names[:5])}"
        }
    
    def _get_generation_reason(self, query: str, chart_type: str) -> str:
        """Generate a human-readable reason for why this chart was created"""
        # Safely handle None values
        if query is None:
            query = ""
        if chart_type is None:
            chart_type = "chart"
        
        query_lower = query.lower() if query else ""
        chart_type_str = str(chart_type) if chart_type else "chart"
        
        # Handle observation-specific charts
        if chart_type_str.startswith("observation_trend:"):
            observation_name = chart_type_str.split(":", 1)[1] if ":" in chart_type_str else chart_type_str
            return f"Auto-generated {observation_name.title()} trend chart based on your question about {observation_name}"
        
        if "abnormal" in query_lower or "high" in query_lower or "low" in query_lower:
            return f"Auto-generated {chart_type_str.replace('_', ' ')} chart to visualize abnormal values mentioned in your question"
        
        if "trend" in query_lower or "pattern" in query_lower or "over time" in query_lower:
            return f"Auto-generated {chart_type_str.replace('_', ' ')} chart to show trends and patterns over time"
        
        if "glucose" in query_lower or "blood sugar" in query_lower:
            return "Auto-generated glucose trend chart based on your question about glucose levels"
        
        if "blood pressure" in query_lower or "bp" in query_lower:
            return "Auto-generated blood pressure trend chart based on your question about blood pressure"
        
        if "heart rate" in query_lower or "pulse" in query_lower:
            return "Auto-generated heart rate trend chart based on your question about heart rate"
        
        return f"Auto-generated {chart_type_str.replace('_', ' ')} chart to better visualize the data related to your question"
    
    def enhance_response_with_visualization_context(self, response_text: str, chart_data: Optional[Dict[str, Any]]) -> str:
        """Enhance the LLM response text to mention the visualization"""
        if not chart_data:
            return response_text
        
        chart_type = chart_data.get("type") or chart_data.get("chart_type") or "chart"
        generation_reason = chart_data.get("generation_reason", "")
        
        # Safely handle chart_type - ensure it's a string
        if chart_type is None:
            chart_type = "chart"
        chart_type_str = str(chart_type).replace('_', ' ') if chart_type else "chart"
        
        # Add a note about the visualization at the end of the response
        visualization_note = f"\n\n📊 I've automatically generated a {chart_type_str} chart below to help visualize this data. {generation_reason}."
        
        return response_text + visualization_note

# Global instance
intelligent_viz_service = IntelligentVisualizationService()

