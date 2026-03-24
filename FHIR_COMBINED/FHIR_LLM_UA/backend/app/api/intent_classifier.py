"""
LLM-Based Intent Classification Service
Uses the LLM to intelligently classify user queries instead of fixed keyword matching.
This provides more robust, flexible, and research-worthy intent detection.
"""

from typing import Dict, Any, List
from ..core.llm import generate_chat
import json
import logging
import re

logger = logging.getLogger(__name__)

class IntentClassifier:
    """LLM-based intent classification for user queries"""
    
    def __init__(self):
        self.system_prompt = """You are a medical query intent classifier. Analyze user queries and return ONLY valid JSON.

Return this JSON structure (keep it short):
{"intent_type":"general|visualization|analysis|comparison|grouped_visualization","data_types":["observations"],"wants_all_data":true,"wants_grouped":true,"wants_visualization":true,"specific_observation":"none","parameters":["all","observations"],"confidence":0.95}

Intent types:
- grouped_visualization: "all observations", "show all", "list every", "all vitals", "all vital signs"
- visualization: "trend", "chart", "graph", "how has X changed"
- observations: "vital signs", "vitals", "what are the patient's vitals", "show vitals"
- analysis: "abnormal", "high", "low", "elevated", "risk values", "concerning values", "values that affect patient", "problematic values", "worrisome values", "values of concern", "critical values"
- comparison: "compare", "versus", "difference"
- general: everything else

CRITICAL: For "analysis" intent, understand semantic meaning:
- "risk values" = analysis (abnormal values)
- "values that affect patient" = analysis (abnormal values)
- "concerning vitals" = analysis (abnormal values)
- "problematic lab results" = analysis (abnormal values)
- "worrisome values" = analysis (abnormal values)
- "critical values" = analysis (abnormal values)
- "values of concern" = analysis (abnormal values)
- Any query asking about values that are problematic, risky, concerning, or affecting patient health = analysis

Examples:
"show all observations" → {"intent_type":"grouped_visualization","data_types":["observations"],"wants_all_data":true,"wants_grouped":true,"wants_visualization":true,"specific_observation":"none","parameters":["all","observations"],"confidence":0.95}
"what is creatinine level?" → {"intent_type":"general","data_types":["observations"],"wants_all_data":false,"wants_grouped":false,"wants_visualization":false,"specific_observation":"creatinine","parameters":["creatinine"],"confidence":0.9}
"how has glucose changed?" → {"intent_type":"visualization","data_types":["observations"],"wants_all_data":false,"wants_grouped":false,"wants_visualization":true,"specific_observation":"glucose","parameters":["glucose","trend"],"confidence":0.88}

Return ONLY the JSON, no other text.

Intent Types:
- "general": General information request
- "visualization": Request for charts/graphs
- "analysis": Request for analysis (abnormal values, trends)
- "comparison": Request to compare data
- "grouped_visualization": Request for all observations grouped by category

Examples:
Query: "show all observations"
Response: {"intent_type": "grouped_visualization", "data_types": ["observations"], "wants_all_data": true, "wants_grouped": true, "wants_visualization": true, "specific_observation": "none", "parameters": ["all", "observations"], "confidence": 0.95}

Query: "what is the patient's creatinine level?"
Response: {"intent_type": "general", "data_types": ["observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": false, "specific_observation": "creatinine", "parameters": ["creatinine"], "confidence": 0.9}

Query: "display all observation data"
Response: {"intent_type": "grouped_visualization", "data_types": ["observations"], "wants_all_data": true, "wants_grouped": true, "wants_visualization": true, "specific_observation": "none", "parameters": ["all", "display", "observations"], "confidence": 0.92}

Query: "how has the glucose changed over time?"
Response: {"intent_type": "visualization", "data_types": ["observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": true, "specific_observation": "glucose", "parameters": ["glucose", "trend", "time"], "confidence": 0.88}

Query: "list every observation for this patient"
Response: {"intent_type": "grouped_visualization", "data_types": ["observations"], "wants_all_data": true, "wants_grouped": true, "wants_visualization": false, "specific_observation": "none", "parameters": ["all", "list", "observations"], "confidence": 0.9}

Query: "What are the patient's vital signs?"
Response: {"intent_type": "observations", "data_types": ["observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": true, "specific_observation": "none", "parameters": ["vital", "signs"], "confidence": 0.9}

Query: "is this patient diabetic?"
Response: {"intent_type": "general", "data_types": ["conditions", "observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": false, "specific_observation": "glucose", "parameters": ["diabetes", "diabetic"], "confidence": 0.85}

Query: "What are the risk values of vitals that affect this patient?"
Response: {"intent_type": "analysis", "data_types": ["observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": false, "specific_observation": "none", "parameters": ["risk", "vitals", "affect"], "confidence": 0.9}

Query: "Show me values that are concerning for patient health"
Response: {"intent_type": "analysis", "data_types": ["observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": false, "specific_observation": "none", "parameters": ["concerning", "health"], "confidence": 0.92}

Query: "What vitals are problematic?"
Response: {"intent_type": "analysis", "data_types": ["observations"], "wants_all_data": false, "wants_grouped": false, "wants_visualization": false, "specific_observation": "none", "parameters": ["problematic", "vitals"], "confidence": 0.88}

IMPORTANT:
- Return ONLY valid JSON, no additional text
- Be flexible with synonyms (e.g., "show" = "display" = "list" = "view")
- Understand context (e.g., "all data" in medical context usually means all observations)
- If query is ambiguous, set confidence lower (< 0.7)
- "wants_all_data" should be true if query asks for "all", "every", "complete", "everything"
- "wants_grouped" should be true if query asks for "all observations", "grouped", "by category", "by type"
"""

    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user query intent using LLM
        
        Args:
            query: User's query string
            
        Returns:
            Dictionary with intent classification
        """
        try:
            user_prompt = f"Classify this medical query: '{query}'\n\nReturn ONLY the JSON object, no additional text."
            
            # Get LLM response with category="intent" to get appropriate token limit
            response_text = generate_chat(self.system_prompt, user_prompt, category="intent").strip()
            
            # Clean response - remove markdown code blocks if present
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()
            
            # Try to extract JSON from response (handle incomplete JSON)
            json_match = re.search(r'\{.*', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                
                # Try to fix incomplete JSON by closing it
                if not json_str.rstrip().endswith('}'):
                    # Count open braces
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    missing = open_braces - close_braces
                    
                    # Try to complete the JSON intelligently
                    if missing > 0:
                        json_str_stripped = json_str.rstrip()
                        last_char = json_str_stripped[-1] if json_str_stripped else ''
                        
                        # Case 1: Ends with incomplete number (e.g., "confidence":0. or "confidence":0)
                        if last_char == '.' or (last_char.isdigit() and '"confidence"' in json_str[-30:]):
                            # Look for incomplete confidence value
                            confidence_match = re.search(r'"confidence"\s*:\s*(\d+\.?)\s*$', json_str_stripped)
                            if confidence_match:
                                # Complete confidence with a reasonable default (0.95)
                                if json_str_stripped.endswith('"confidence":0.'):
                                    json_str = json_str_stripped + '95}'
                                elif json_str_stripped.endswith('"confidence":0'):
                                    json_str = json_str_stripped + '.95}'
                                else:
                                    # Remove the incomplete part and add complete value
                                    json_str = json_str_stripped.rstrip('.') + '0.95}'
                            elif '"confidence"' in json_str[-30:]:
                                # Confidence field exists but incomplete - complete it
                                if json_str_stripped.endswith('"confidence":'):
                                    json_str = json_str_stripped + '0.95}'
                                elif json_str_stripped.endswith('"confidence":0'):
                                    json_str = json_str_stripped + '.95}'
                                elif json_str_stripped.endswith('"confidence":0.'):
                                    json_str = json_str_stripped + '95}'
                                else:
                                    # Fallback: remove incomplete and add complete value
                                    json_str = json_str_stripped.rstrip('.') + '0.95}'
                            else:
                                # Some other incomplete number - just close it
                                json_str = json_str_stripped + '0}'
                        # Case 2: Ends with quote (incomplete string)
                        elif last_char == '"':
                            json_str = json_str_stripped + '}'
                        # Case 3: Ends with comma (incomplete field)
                        elif last_char == ',':
                            json_str = json_str_stripped.rstrip(',') + '}'
                        # Case 4: Ends with colon (incomplete value)
                        elif last_char == ':':
                            # Check if it's confidence field
                            if '"confidence"' in json_str[-30:]:
                                json_str = json_str_stripped + '0.95}'
                            else:
                                json_str = json_str_stripped + '"none"}'
                        else:
                            # Try to find last field and close it properly
                            last_comma = json_str_stripped.rfind(',')
                            if last_comma > 0:
                                # Check what the last field was
                                last_field = json_str_stripped[last_comma:].strip()
                                if '"confidence"' in last_field:
                                    # Complete confidence field
                                    json_str = json_str_stripped[:last_comma] + ',"confidence":0.95}'
                                else:
                                    # Remove incomplete last field
                                    json_str = json_str_stripped[:last_comma] + '}'
                            else:
                                # No comma found, just close it
                                json_str = json_str_stripped + '}'
                
                response_text = json_str
            
            # Parse JSON
            intent = json.loads(response_text)
            
            # Validate and set defaults
            intent = self._validate_intent(intent)
            
            logger.info(f"Intent classified: {intent['intent_type']} (confidence: {intent.get('confidence', 0.0)})")
            
            return intent
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}. Response: {response_text[:200] if 'response_text' in locals() else 'N/A'}")
            # Fallback to keyword-based detection
            return self._fallback_classification(query)
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to keyword-based detection
            return self._fallback_classification(query)
    
    def _validate_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and set defaults for intent dictionary"""
        # Set defaults
        default_intent = {
            "intent_type": "general",
            "data_types": [],
            "wants_all_data": False,
            "wants_grouped": False,
            "wants_visualization": False,
            "specific_observation": "none",
            "parameters": [],
            "confidence": 0.5,
            "follow_up_needed": False,
            "follow_up_options": []
        }
        
        # Merge with provided intent
        validated = {**default_intent, **intent}
        
        # Ensure data_types is a list
        if not isinstance(validated["data_types"], list):
            validated["data_types"] = []
        
        # Ensure parameters is a list
        if not isinstance(validated["parameters"], list):
            validated["parameters"] = []
        
        # Set follow_up_needed based on intent type
        if validated["intent_type"] in ["visualization", "grouped_visualization", "analysis"]:
            validated["follow_up_needed"] = True
        
        # Generate follow-up options
        validated["follow_up_options"] = self._generate_follow_up_options(validated)
        
        return validated
    
    def _generate_follow_up_options(self, intent: Dict[str, Any]) -> List[str]:
        """Generate follow-up options based on intent"""
        options = []
        
        if intent["intent_type"] == "grouped_visualization":
            options.extend([
                "📊 View all observations grouped by category",
                "📈 Analyze comprehensive observation patterns by type",
                "📋 Export complete grouped observations report"
            ])
        elif intent["intent_type"] == "visualization":
            if intent["specific_observation"] != "none":
                obs_name = intent["specific_observation"].replace("_", " ").title()
                options.extend([
                    f"📊 View {obs_name} trend over time",
                    f"📈 Analyze {obs_name} patterns",
                    f"📋 Detailed {obs_name} report"
                ])
            else:
                options.extend([
                    "📊 Create trend chart",
                    "📈 Generate pattern analysis",
                    "📋 Historical data summary"
                ])
        elif intent["intent_type"] == "analysis":
            options.extend([
                "📊 Generate abnormal values chart",
                "📈 Create trend analysis",
                "📋 Detailed abnormal values report"
            ])
        
        return options
    
    def _fallback_classification(self, query: str) -> Dict[str, Any]:
        """
        Fallback to enhanced keyword-based classification if LLM fails
        This is a safety net, but more comprehensive than before
        """
        # Safely handle None query
        query_lower = (query or "").lower()
        
        intent = {
            "intent_type": "general",
            "data_types": [],
            "wants_all_data": False,
            "wants_grouped": False,
            "wants_visualization": False,
            "specific_observation": "none",
            "parameters": [],
            "confidence": 0.5,
            "follow_up_needed": False,
            "follow_up_options": []
        }
        
        # Enhanced keyword fallback (more comprehensive for better coverage)
        
        # Check for "all observations" variations
        # Be more specific to avoid false positives
        all_obs_keywords = [
            "all observations", "all observation", "every observation", "complete observations",
            "all observation data", "all observation values", "all patient observations",
            "all lab results", "all lab data", "all test results",
            "list all observations", "show all observations", "display all observations",
            "what observations", "which observations", "patient observations",
            "complete data", "all values",
            "show me all", "display all", "list all", "all of the",
            "grouped by category", "by category", "by type", "grouped observations",
            "complete observation", "all the observations", "all the observation",
            "show all", "can i see all", "show me all",
            "complete observation data", "display complete observation", "display complete"
        ]
        
        # "all data" and "everything" are ambiguous - only trigger if context suggests observations
        if "all data" in query_lower or "everything" in query_lower:
            # Only trigger if query mentions observations, lab, or test
            if any(kw in query_lower for kw in ["observation", "lab", "test", "result", "value"]):
                intent["intent_type"] = "grouped_visualization"
                intent["data_types"] = ["observations"]
                intent["wants_all_data"] = True
                intent["wants_grouped"] = True
                intent["wants_visualization"] = True
                intent["confidence"] = 0.6
        
        # Also check for "lab results" = observations
        if "lab results" in query_lower and "all" in query_lower:
            intent["intent_type"] = "grouped_visualization"
            intent["data_types"] = ["observations"]
            intent["wants_all_data"] = True
            intent["wants_grouped"] = True
            intent["wants_visualization"] = True
            intent["confidence"] = 0.6
        
        # Only trigger grouped_visualization if query is about observations, not conditions
        if any(kw in query_lower for kw in all_obs_keywords):
            # Don't trigger if query is about conditions
            if "condition" not in query_lower:
                intent["intent_type"] = "grouped_visualization"
                intent["data_types"] = ["observations"]
                intent["wants_all_data"] = True
                intent["wants_grouped"] = True
                intent["wants_visualization"] = True
                intent["confidence"] = 0.6  # Lower confidence for fallback
        
        # Check for visualization requests
        viz_keywords = ["chart", "graph", "plot", "visual", "visualization", "trend", "pattern", "over time", "changed", "change"]
        if any(kw in query_lower for kw in viz_keywords):
            intent["wants_visualization"] = True
            if intent["intent_type"] == "general":
                intent["intent_type"] = "visualization"
        
        # Check for "show me" + observation = visualization
        if "show me" in query_lower and any(obs in query_lower for obs in ["glucose", "creatinine", "hemoglobin", "values", "results"]):
            intent["wants_visualization"] = True
            if intent["intent_type"] == "general":
                intent["intent_type"] = "visualization"
        
        # Check for "how has" = trend/visualization
        if "how has" in query_lower or "how have" in query_lower:
            intent["wants_visualization"] = True
            if intent["intent_type"] == "general":
                intent["intent_type"] = "visualization"
        
        # Check for specific observations
        if "glucose" in query_lower or "blood sugar" in query_lower:
            intent["specific_observation"] = "glucose"
            intent["data_types"] = ["observations"]
        elif "creatinine" in query_lower:
            intent["specific_observation"] = "creatinine"
            intent["data_types"] = ["observations"]
        elif "blood pressure" in query_lower or "bp" in query_lower:
            intent["specific_observation"] = "blood_pressure"
            intent["data_types"] = ["observations"]
        elif "heart rate" in query_lower or "pulse" in query_lower or "hr" in query_lower:
            intent["specific_observation"] = "heart_rate"
            intent["data_types"] = ["observations"]
        elif "hemoglobin" in query_lower:
            intent["specific_observation"] = "hemoglobin"
            intent["data_types"] = ["observations"]
        
        # RESEARCH-BASED: Removed keyword matching for abnormal values
        # LLM-based classification should handle this semantically
        # Only use fallback for basic intent detection if LLM completely fails
        
        # Check for comparison
        if any(kw in query_lower for kw in ["compare", "versus", "vs", "difference", "between"]):
            intent["intent_type"] = "comparison"
            intent["data_types"] = ["observations"]
        
        # Check for conditions
        if any(kw in query_lower for kw in ["condition", "diagnosis", "disease", "diabetic", "diabetes"]):
            intent["data_types"].append("conditions")
        
        # Default data types
        if not intent["data_types"]:
            intent["data_types"] = ["observations"]
        
        return intent

# Global instance
intent_classifier = IntentClassifier()

