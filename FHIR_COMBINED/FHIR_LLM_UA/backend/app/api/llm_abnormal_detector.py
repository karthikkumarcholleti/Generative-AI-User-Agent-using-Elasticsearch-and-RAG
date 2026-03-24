"""
LLM-Based Abnormal Value Detection
Research-based approach: Uses LLM's medical knowledge to identify abnormal values
without hardcoded thresholds.
"""

from typing import List, Dict, Any, Optional
from ..core.llm import generate_chat
import json
import re
import logging

logger = logging.getLogger(__name__)

class LLMAbnormalDetector:
    """Uses LLM to identify abnormal clinical values using medical knowledge"""
    
    def __init__(self):
        self.system_prompt = """You are a medical AI assistant with extensive knowledge of clinical reference ranges and abnormal value detection.

Your task is to analyze patient observations and identify abnormal values using your medical knowledge.

IMPORTANT PRINCIPLES:
1. Use your medical training knowledge to determine normal ranges
2. Consider clinical context (age, gender if available)
3. Identify values that are clinically significant deviations from normal
4. Apply standard medical reference ranges from your training
5. Be conservative - only flag values that are clearly abnormal

Return your analysis in JSON format with clear reasoning for each abnormal value."""

    def detect_abnormal_values(self, patient_id: str, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use LLM to identify abnormal values from observations.
        
        Args:
            patient_id: Patient identifier
            observations: List of observation dictionaries with display, value, unit, date, code
            
        Returns:
            List of abnormal value dictionaries
        """
        if not observations:
            return []
        
        # Format observations for LLM
        obs_text = self._format_observations_for_llm(observations)
        
        user_prompt = f"""Analyze these patient observations and identify ALL abnormal values using your medical knowledge.

Patient ID: {patient_id}

Observations:
{obs_text}

CRITICAL INSTRUCTIONS:
1. Use standard clinical reference ranges from your medical training
2. Identify values that are CLINICALLY ABNORMAL (outside normal ranges)
3. Return ONLY valid JSON - no markdown, no explanations outside JSON
4. Include the "code" field from the observation if available

Return this EXACT JSON structure (complete it with actual abnormal values):
{{
    "abnormal_values": [
        {{
            "observation": "Glucose",
            "display": "GLUCOSE:MCNC:PT:SER/PLAS:QN::",
            "code": "2339-0",
            "value": 155.0,
            "unit": "mg/dL",
            "date": "2025-07-28",
            "reason": "High - above normal fasting range"
        }}
    ]
}}

Return ONLY the JSON object. Start with {{ and end with }}. No other text."""

        try:
            response_text = generate_chat(self.system_prompt, user_prompt, category="general").strip()
            
            # Clean response
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            response_text = response_text.strip()
            
            # Extract JSON - try multiple strategies
            json_str = None
            
            # Strategy 1: Find JSON object
            json_match = re.search(r'\{[^{}]*"abnormal_values"[^{}]*\[.*?\]\s*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Strategy 2: Find any JSON object
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
            
            if json_str:
                # Try to fix common JSON issues
                json_str = json_str.strip()
                # Remove trailing commas before closing braces/brackets
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                try:
                    result = json.loads(json_str)
                    abnormal_values = result.get("abnormal_values", [])
                    
                    if abnormal_values:
                        logger.info(f"LLM identified {len(abnormal_values)} abnormal values for patient {patient_id}")
                        return abnormal_values
                    else:
                        logger.warning("LLM returned empty abnormal_values array")
                        # Fallback: Use threshold-based detection
                        return self._fallback_threshold_detection(observations)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse LLM JSON response: {e}")
                    logger.debug(f"JSON string: {json_str[:500]}")
                    # Fallback: Use threshold-based detection
                    return self._fallback_threshold_detection(observations)
            else:
                logger.warning("No JSON found in LLM response")
                # Fallback: Use threshold-based detection
                return self._fallback_threshold_detection(observations)
                
        except Exception as e:
            logger.error(f"Error in LLM abnormal detection: {e}")
            return []
    
    def _format_observations_for_llm(self, observations: List[Dict[str, Any]]) -> str:
        """Format observations for LLM analysis"""
        lines = []
        for idx, obs in enumerate(observations, 1):
            display = obs.get("display", "Unknown")
            value = obs.get("value", obs.get("value_numeric", obs.get("value_string", "N/A")))
            unit = obs.get("unit", "")
            date = obs.get("date", obs.get("effectiveDateTime", "Unknown"))
            code = obs.get("code", "")
            
            line = f"{idx}. {display}"
            if value != "N/A":
                unit_str = f" {unit}" if unit else ""
                line += f": {value}{unit_str}"
            if date and date != "Unknown":
                date_str = str(date)[:10] if len(str(date)) >= 10 else str(date)
                line += f" (Date: {date_str})"
            if code:
                line += f" [Code: {code}]"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _fallback_threshold_detection(self, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback: Use threshold-based detection if LLM fails"""
        # This is a fallback for when LLM JSON parsing fails
        # Uses standard clinical thresholds as backup
        NORMAL_RANGES = {
            "systolic_bp": (90, 120),
            "diastolic_bp": (60, 80),
            "heart_rate": (60, 100),
            "temperature": (36.1, 37.2),
            "glucose": (70, 100),
            "creatinine": (0.6, 1.2),
            "hemoglobin": (12, 16),
            "sodium": (135, 145),
            "potassium": (3.5, 5.0),
            "chloride": (98, 107),
            "calcium": (8.5, 10.5),
            "bun": (7, 20),
        }
        
        def identify_type(display):
            if not display:
                return None
            display_lower = display.lower()
            if "systolic" in display_lower:
                return "systolic_bp"
            if "diastolic" in display_lower:
                return "diastolic_bp"
            if "heart rate" in display_lower or "pulse" in display_lower:
                return "heart_rate"
            if "temperature" in display_lower:
                return "temperature"
            if "glucose" in display_lower:
                return "glucose"
            if "creatinine" in display_lower:
                return "creatinine"
            if "hemoglobin" in display_lower and "a1c" not in display_lower:
                return "hemoglobin"
            if "sodium" in display_lower:
                return "sodium"
            if "potassium" in display_lower:
                return "potassium"
            if "chloride" in display_lower:
                return "chloride"
            if "calcium" in display_lower:
                return "calcium"
            if "urea nitrogen" in display_lower or "bun" in display_lower:
                return "bun"
            return None
        
        abnormal_values = []
        for obs in observations:
            display = obs.get("display", "")
            obs_type = identify_type(display)
            value = obs.get("value")
            
            if obs_type and obs_type in NORMAL_RANGES and value is not None:
                try:
                    value_num = float(value)
                    min_val, max_val = NORMAL_RANGES[obs_type]
                    if value_num < min_val or value_num > max_val:
                        abnormal_values.append({
                            "observation": display.split(":")[0] if ":" in display else display,
                            "display": display,
                            "code": obs.get("code", ""),
                            "value": value_num,
                            "unit": obs.get("unit", ""),
                            "date": str(obs.get("date", "")),
                            "reason": f"{'Low' if value_num < min_val else 'High'} - outside normal range ({min_val}-{max_val})"
                        })
                except (ValueError, TypeError):
                    continue
        
        logger.info(f"Fallback threshold detection found {len(abnormal_values)} abnormal values")
        return abnormal_values

