# backend/app/api/answer_parser.py

"""
Extract observation values from LLM-generated answer text.
This ensures charts show exactly what the answer mentions.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class AnswerParser:
    """Parse LLM answers to extract observation values for chart generation"""
    
    def extract_observation_values_from_answer(self, answer_text: str, observation_type: str) -> List[Dict[str, Any]]:
        """
        Extract observation values from the answer text.
        
        Examples:
        - "The patient's creatinine level is 1.09 unit (recorded on 2025-07-16)"
        - "The patient's heart rate is 88.0 bpm (recorded on 2025-07-01) and 89.0 bpm (recorded on 2025-07-21)"
        - "1. Heart rate - 88.0 bpm (recorded on 2025-07-01)"
        
        Returns:
            List of data points with date, value, unit, display
        """
        observation_type_lower = observation_type.lower()
        data_points = []
        
        # Pattern 1: "The patient's [observation] is [value] [unit] (recorded on [date])"
        # Also handles: "The patient's [observation] is [value] [unit] and [value] [unit] (recorded on [date])"
        pattern1 = re.compile(
            r'(?:the\s+patient\'?s?\s+)?' + 
            re.escape(observation_type_lower) + 
            r'[^\d]*?is\s+([\d.]+)\s*([^\s(,)]+)?(?:\s+and\s+([\d.]+)\s*([^\s(,)]+)?)?\s*(?:\(recorded\s+on\s+([\d-]+)\)|\(on\s+([\d-]+)\)|recorded\s+on\s+([\d-]+))',
            re.IGNORECASE
        )
        
        # Pattern 2: "[value] [unit] (recorded on [date])" - multiple values in sentence
        pattern2 = re.compile(
            r'([\d.]+)\s*([^\s(,)]+)?\s*(?:\(recorded\s+on\s+([\d-]+)\)|\(on\s+([\d-]+)\)|recorded\s+on\s+([\d-]+))',
            re.IGNORECASE
        )
        
        # Pattern 3: Numbered list format "1. [observation] - [value] [unit] (recorded on [date])"
        pattern3 = re.compile(
            r'\d+\.\s*[^\d]*?' + 
            re.escape(observation_type_lower) + 
            r'[^\d]*?[-:]\s*([\d.]+)\s*([^\s(,)]+)?\s*(?:\(recorded\s+on\s+([\d-]+)\)|\(on\s+([\d-]+)\)|recorded\s+on\s+([\d-]+))',
            re.IGNORECASE
        )
        
        # Pattern 4: "is [value] [unit] (recorded on [date]) and [value] [unit] (recorded on [date])"
        pattern4 = re.compile(
            r'is\s+([\d.]+)\s*([^\s(,)]+)?\s*(?:\(recorded\s+on\s+([\d-]+)\)|\(on\s+([\d-]+)\)|recorded\s+on\s+([\d-]+))\s+and\s+([\d.]+)\s*([^\s(,)]+)?\s*(?:\(recorded\s+on\s+([\d-]+)\)|\(on\s+([\d-]+)\)|recorded\s+on\s+([\d-]+))',
            re.IGNORECASE
        )
        
        # Try pattern 4 first (handles "is X and Y" format)
        matches = pattern4.findall(answer_text)
        if matches:
            for match in matches:
                # Match format: value1, unit1, date1a, date1b, date1c, value2, unit2, date2a, date2b, date2c
                value1_str, unit1, date1a, date1b, date1c, value2_str, unit2, date2a, date2b, date2c = match
                try:
                    value1 = float(value1_str)
                    value2 = float(value2_str)
                    unit1 = unit1.strip() if unit1 else ""
                    unit2 = unit2.strip() if unit2 else unit1
                    date1 = date1a or date1b or date1c or ""
                    date2 = date2a or date2b or date2c or ""
                    if value1 and date1:
                        data_points.append({
                            "date": date1,
                            "value": value1,
                            "unit": unit1,
                            "display": observation_type.title()
                        })
                    if value2 and date2:
                        data_points.append({
                            "date": date2,
                            "value": value2,
                            "unit": unit2,
                            "display": observation_type.title()
                        })
                except (ValueError, TypeError):
                    continue
        
        # Try pattern 1 (single value)
        if not data_points:
            matches = pattern1.findall(answer_text)
            if matches:
                for match in matches:
                    # Match format: value1, unit1, value2, unit2, date1, date2, date3
                    value1_str, unit1, value2_str, unit2, date1, date2, date3 = match
                    try:
                        value1 = float(value1_str)
                        unit1 = unit1.strip() if unit1 else ""
                        date = date1 or date2 or date3 or ""
                        if value1 and date:
                            data_points.append({
                                "date": date,
                                "value": value1,
                                "unit": unit1,
                                "display": observation_type.title()
                            })
                        # Handle second value if present
                        if value2_str:
                            try:
                                value2 = float(value2_str)
                                unit2 = unit2.strip() if unit2 else unit1
                                if value2 and date:
                                    data_points.append({
                                        "date": date,
                                        "value": value2,
                                        "unit": unit2,
                                        "display": observation_type.title()
                                    })
                            except (ValueError, TypeError):
                                pass
                    except (ValueError, TypeError):
                        continue
        
        # Try pattern 3 (numbered list)
        if not data_points:
            matches = pattern3.findall(answer_text)
            for match in matches:
                value_str, unit, date1, date2 = match
                try:
                    value = float(value_str)
                    unit = unit.strip() if unit else ""
                    date = date1 or date2 or ""
                    if value and date:
                        data_points.append({
                            "date": date,
                            "value": value,
                            "unit": unit,
                            "display": observation_type.title()
                        })
                except (ValueError, TypeError):
                    continue
        
        # Try pattern 2 (multiple values in one sentence)
        if not data_points:
            # Look for sentences with multiple values
            sentences = re.split(r'[.!?]\s+', answer_text)
            for sentence in sentences:
                if observation_type_lower in sentence.lower():
                    matches = pattern2.findall(sentence)
                    for match in matches:
                        # Match format: value, unit, date1, date2, date3
                        value_str, unit, date1, date2, date3 = match
                        try:
                            value = float(value_str)
                            unit = unit.strip() if unit else ""
                            date = date1 or date2 or date3 or ""
                            if value and date:
                                data_points.append({
                                    "date": date,
                                    "value": value,
                                    "unit": unit,
                                    "display": observation_type.title()
                                })
                        except (ValueError, TypeError):
                            continue
        
        # Remove duplicates (same date + value)
        seen = set()
        unique_points = []
        for point in data_points:
            key = (point["date"], point["value"])
            if key not in seen:
                seen.add(key)
                unique_points.append(point)
        
        # Sort by date
        unique_points.sort(key=lambda x: x.get("date", ""))
        
        logger.info(f"Extracted {len(unique_points)} {observation_type} values from answer text")
        for point in unique_points:
            logger.info(f"  - {point['value']} {point['unit']} on {point['date']}")
        
        return unique_points
    
    def extract_all_observation_values_from_answer(self, answer_text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all observation values mentioned in the answer.
        
        Returns:
            Dict mapping observation_type -> list of data points
        """
        # Common observation types to look for
        observation_types = [
            "creatinine", "hemoglobin", "heart rate", "glucose", "blood pressure",
            "temperature", "respiratory rate", "systolic", "diastolic", "pulse"
        ]
        
        extracted = {}
        for obs_type in observation_types:
            values = self.extract_observation_values_from_answer(answer_text, obs_type)
            if values:
                extracted[obs_type] = values
        
        return extracted

