# backend/app/core/prompts.py

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

# ---------- Shared system prompt (used for all categories) ----------
SYSTEM_PROMPT = (
    "You are a clinical summarization assistant designed to help healthcare professionals review patient data.\n"
    "- Be concise and strictly factual. Only summarize the data provided.\n"
    "- Never invent, infer, speculate, or add information not explicitly in the data.\n"
    "- Never suggest potential conditions, risks, or concerns not mentioned in the records.\n"
    "- If a date or value is missing, write: 'date not recorded' or 'value not recorded'.\n"
    "- Preserve units. Do not change units. Do not round away meaning.\n"
    "- Do not diagnose, prescribe, or suggest clinical implications beyond the provided data.\n"
    "- IMPORTANT: This tool provides data summarization only. All clinical decisions must be made by qualified healthcare providers based on their professional judgment.\n"
    "- Write in clear, flowing paragraphs that are easy for clinicians to read.\n"
    "- Use natural language and complete sentences for most content.\n"
    "- For conditions lists, use numbered format (1, 2, 3) with brief explanations for better readability.\n"
    "- For observations, use bullet points with clinical interpretations (normal/high/low) for better readability.\n"
    "- ALWAYS start with the exact introductory sentence provided in the task instructions.\n"
    "- For demographics: 'Demographics of the patient based on their medical records:' followed by 'Patient Demographics:' and bullet points only\n"
    "- For observations: 'The patient's laboratory and clinical observations include:'\n"
    "- For conditions: 'Based on the patient's medical data, the patient has the following medical conditions:'\n"
    "- For care plans: 'Based on the documented clinical data, the following care considerations may be relevant for this patient:'\n"
    "- Structure your response as coherent paragraphs based only on the actual data provided.\n"
        "- If no relevant data is available for a section, state 'No data available' or 'Information not recorded'.\n"
        "- For observations, do not mention 'No other observations', 'No other data', or similar disclaimers - just summarize what is available.\n"
        "- For observations, only include entries with actual numeric or string values - exclude null, missing, or empty values.\n"
    "- Always complete your sentences properly - do not leave them truncated.\n"
)

# ---------- Helpers ----------
def _j(x: Any) -> str:
    """Stable, compact JSON for prompts."""
    return json.dumps(x, ensure_ascii=False)

def _header(title: str) -> str:
    return f"{title.upper()}:\n"

# ---------- Category user prompts ----------

def prompt_patient_summary(
    demo: Dict[str, Any],
    conditions: List[Dict[str, Any]],
    observations: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
) -> str:
    """
    Full patient summary: demographics + unique conditions + all observation rows
    (already capped by the API's budget logic) + recent notes.
    """
    # Group conditions by category for better organization
    from ..api.condition_categorizer import group_conditions_by_category
    
    grouped_conditions = group_conditions_by_category(conditions)
    
    # Build conditions section organized by category
    conditions_text = _header("Conditions (organized by medical category)")
    category_order = [
        "Cardiovascular", "Metabolic", "Respiratory", "Neurological",
        "Mental Health", "Musculoskeletal", "Gastrointestinal", "Renal",
        "Endocrine", "Oncology", "Acute", "Other"
    ]
    
    for category in category_order:
        if category in grouped_conditions:
            cat_conditions = grouped_conditions[category]
            sorted_conditions = sorted(
                cat_conditions,
                key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                reverse=True
            )
            conditions_text += f"\n{category}:\n"
            for cond in sorted_conditions:
                priority = cond.get("priority", "low")
                name = cond.get("normalizedName") or cond.get("display", "Unknown")
                status = cond.get("clinicalStatus", "unknown")
                conditions_text += f"  [{priority.upper()}]: {name} (Status: {status})\n"
    
    return (
        _header("Demographics") + _j(demo) + "\n\n"
        + conditions_text + "\n\n"
        + _header("Observations (rows, newest first)") + _j(observations) + "\n\n"
        + _header("Notes (most recent first)") + _j(notes) + "\n\n"
        "TASK:\n"
        "Summary of patient's medical records:\n"
        "Write a comprehensive summary based on demographics, conditions, observations, and notes. CRITICAL: Do NOT mention or include any category if data is not available. If notes are available, prioritize notes then consider other categories. Do NOT duplicate the observations category format. Structure your response as follows:\n\n1. Start with 'Summary of patient's medical records:' as the main heading\n2. When discussing conditions, organize by medical category (Cardiovascular, Metabolic, Respiratory, etc.) and highlight HIGH PRIORITY conditions first\n3. Provide a comprehensive summary synthesizing information from all available categories in paragraph format\n4. Do NOT list individual observations with values - instead, provide insights about key findings, trends, or patterns\n5. CRITICAL: Do NOT include sentences like 'No observations are available', 'No notes are available' - Simply skip those sections entirely if data is not available\n6. If patterns or trends are identified, include a section 'Clinical Insights:' with numbered points (1., 2., 3., etc.) - ONLY if meaningful insights can be derived from the data\n7. Do not mention 'normal range not specified' - use clinical interpretations (normal/high/low/abnormal) based on provided data\n8. Do not use phrases like 'Based on the patient's medical data' or 'The patient's laboratory and clinical observations include' - write in your own summary style\n9. Do NOT list individual observations with their values - focus on overall health status and key findings\n10. Emphasize high-priority conditions (Cardiovascular, Metabolic, Respiratory, Neurological) when present\n"
    )

def prompt_conditions(conditions: List[Dict[str, Any]]) -> str:
    # Group conditions by category
    from ..api.condition_categorizer import group_conditions_by_category
    
    grouped = group_conditions_by_category(conditions)
    
    # Build organized prompt by category
    prompt = _header("Conditions (organized by medical category)")
    
    # Sort categories by precedence (Cardiovascular first, then Metabolic, etc.)
    category_order = [
        "Cardiovascular", "Metabolic", "Respiratory", "Neurological",
        "Mental Health", "Musculoskeletal", "Gastrointestinal", "Renal",
        "Endocrine", "Oncology", "Acute", "Other"
    ]
    
    for category in category_order:
        if category in grouped:
            cat_conditions = grouped[category]
            # Sort by priority: high first, then medium, then low
            sorted_conditions = sorted(
                cat_conditions,
                key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                reverse=True
            )
            
            prompt += f"\n{category} ({len(cat_conditions)} condition{'s' if len(cat_conditions) != 1 else ''}):\n"
            for cond in sorted_conditions:
                priority = cond.get("priority", "low")
                priority_marker = "🔴 HIGH" if priority == "high" else "🟡 MEDIUM" if priority == "medium" else "🟢 LOW"
                name = cond.get("normalizedName") or cond.get("display", "Unknown")
                status = cond.get("clinicalStatus", "unknown")
                prompt += f"  {priority_marker}: {name} (Status: {status})\n"
    
    # Handle any remaining categories not in the precedence list
    for category, cat_conditions in grouped.items():
        if category not in category_order:
            sorted_conditions = sorted(
                cat_conditions,
                key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                reverse=True
            )
            prompt += f"\n{category} ({len(cat_conditions)} condition{'s' if len(cat_conditions) != 1 else ''}):\n"
            for cond in sorted_conditions:
                priority = cond.get("priority", "low")
                priority_marker = "🔴 HIGH" if priority == "high" else "🟡 MEDIUM" if priority == "medium" else "🟢 LOW"
                name = cond.get("normalizedName") or cond.get("display", "Unknown")
                status = cond.get("clinicalStatus", "unknown")
                prompt += f"  {priority_marker}: {name} (Status: {status})\n"
    
    prompt += "\n\nTASK:\n"
    prompt += "Write a comprehensive conditions summary organized by medical category:\n"
    prompt += "1. Start with HIGH PRIORITY conditions first (Cardiovascular, Metabolic, Respiratory, Neurological)\n"
    prompt += "2. Group conditions by their medical category (Cardiovascular, Metabolic, Respiratory, etc.)\n"
    prompt += "3. Within each category, list HIGH priority conditions first, then MEDIUM, then LOW\n"
    prompt += "4. For each condition, provide: [Condition name] - [brief one-sentence explanation]\n"
    prompt += "5. Mention clinical status (active, resolved, unknown) when available\n"
    prompt += "6. Use this format:\n"
    prompt += "   CARDIOVASCULAR:\n"
    prompt += "   1. [High priority condition] - [explanation] (Status: active)\n"
    prompt += "   2. [Medium priority condition] - [explanation] (Status: resolved)\n"
    prompt += "   METABOLIC:\n"
    prompt += "   1. [High priority condition] - [explanation] (Status: active)\n"
    prompt += "7. Do NOT include ICD codes, SNOMED codes, or any codes\n"
    prompt += "8. Do NOT add risk assessments, care considerations, or clinical implications not explicitly stated\n"
    prompt += "9. Focus on organizing by category and highlighting high-priority conditions\n"
    
    return prompt

def prompt_observations_summary(observations: List[Dict[str, Any]]) -> str:
    """Observations summary focused on analysis rather than listing all individual values"""
    obs_count = len(observations)
    return (
        _header("Observations (all data for comprehensive analysis)") + _j(observations) + "\n\n"
        "TASK:\n"
        "The patient's laboratory and clinical observations include:\n\n"
        f"Analyze ALL {obs_count} observations and provide a comprehensive summary focusing on:\n\n"
        "1. Key Findings: Highlight the most important abnormal values and their clinical significance\n"
        "2. Trends: Identify patterns, changes over time, and stability of values\n"
        "3. Categories: Group observations by type (Vital Signs, Blood Chemistry, etc.)\n"
        "4. Clinical Interpretation: Provide clinical context for abnormal values based on the data provided\n\n"
        "Format:\n"
        "- Use bullet points with clinical interpretations (normal/high/low/abnormal)\n"
        "- Group by category: Vital Signs, Blood Chemistry, Blood Counts, etc.\n"
        "- Include trend information when available (stable/increasing/decreasing)\n"
        "- Focus on clinically significant findings rather than listing every single value\n"
        "- Use common abbreviations: BP, HR, Temp. Spell out all other terms\n"
        "- Include ranges and averages when available in the data\n"
        "- Do NOT use bold formatting or asterisks in your response\n\n"
        "Examples:\n"
        "Vital Signs:\n"
        "• Heart rate: 98.0 /min - normal, stable over 5 measurements (Avg: 98.80, Range: 94.00-102.00)\n"
        "• Systolic blood pressure: 129.0 mmHg - high, stable over 5 measurements (Avg: 121.80, Range: 103.00-152.00)\n\n"
        "Blood Chemistry:\n"
        "• Glucose: 155.0 mg/dL - high, indicating possible diabetes or impaired glucose regulation\n"
        "• Creatinine: 0.9 mg/dL - normal, stable over measurements\n\n"
        "CRITICAL: Provide a comprehensive analysis of ALL observations, not just a subset. Focus on clinical significance and patterns. Only use data explicitly provided in the observations above."
    )

def prompt_observations(observations: List[Dict[str, Any]]) -> str:
    obs_count = len(observations)
    return (
        _header("Observations (aggregated with trends when available)") + _j(observations) + "\n\n"
        "TASK:\n"
        "List ALL patient observations with trend details:\n\n"
        f"CRITICAL: Include ALL {obs_count} observations. No exceptions. No duplicates.\n\n"
        "Format depends on trend data available:\n"
        "- If valueString contains trend with 'Avg' and 'Range': • [Name]: [value] [unit] - [status], [trend] over N measurements (Avg: X, Range: Y-Z)\n"
        "- If valueString has simple trend (X → Y): • [Name]: [value] [unit] - [status], [trend] (X → Y)\n"
        "- If no trend: • [Name]: [value] [unit] - [status]\n\n"
        "Examples:\n"
        "  • Heart rate: 98.0 /min - normal, stable over 5 measurements (Avg: 98.80, Range: 94.00-102.00)\n"
        "  • Systolic BP: 129.0 mmHg - high, stable over 5 measurements (Avg: 121.80, Range: 103.00-152.00)\n"
        "  • Diastolic BP: 86.0 mmHg - high, increasing over 5 measurements (Avg: 71.00, Range: 64.00-86.00)\n"
        "  • Glucose: 155.0 mg/dL - high, decreasing (160.0 → 155.0)\n"
        "  • Albumin: 3.8 g/dL - normal\n\n"
        "Rules:\n"
        "1. Use ONLY common abbreviations: BP, HR, Temp. Spell out all other terms.\n"
        "2. One line per observation - NO DUPLICATES (do not list same observation twice)\n"
        "3. Keep Systolic BP and Diastolic BP separate - do NOT combine as '129.0 /90.0'\n"
        "4. Include trend statistics from valueString when available\n"
        "5. Status: normal/high/low based on clinical ranges\n"
        "6. Group by category: Vital Signs, Blood Chemistry, Blood Counts, etc.\n"
        "7. NO dates in the output\n"
        "8. Fix units: use 'mmHg' not '/mmHg', use '/min' not '/ min'\n\n"
        "COMPLETE THE ENTIRE LIST. Do not truncate. Finish all observations.\n"
    )

def prompt_notes(notes: List[Dict[str, Any]]) -> str:
    return (
        _header("Notes (most recent first)") + _j(notes) + "\n\n"
        "TASK:\n"
        "Write a comprehensive notes summary in paragraph format using only the provided data:\n"
        "Start with a professional introductory sentence about the patient's clinical notes. Summarize only the clinical narrative that is explicitly documented in the notes, including key events, decisions, transfers, and follow-ups with dates when present in the records. Describe only the symptoms and responses that have been explicitly documented. Use this format: 'The patient's clinical notes document: [clinical narrative].' Write in flowing, well-structured paragraphs that synthesize the information from the actual notes provided. Do not add interpretations, clinical assessments, or implications beyond what is explicitly stated in the source notes.\n"
    )

def prompt_demographics(demo: Dict[str, Any]) -> str:
    return (
        _header("Patient Demographics") + _j(demo) + "\n\n"
        "TASK:\n"
        "Write a comprehensive demographic summary in paragraph format using only the provided data:\n"
        "Demographics of the patient based on their medical records:\n"
        "Provide a demographic summary in bullet-point format including only the basic patient information that is explicitly documented such as name, patient ID, age, and gender. Include contact information and location when available in the records. Use this exact format: 'Patient Demographics:\n- Name: [name]\n- Patient ID: [id]\n- Age: [age] years\n- Gender: [gender]\n- Birth Date: [date]\n- Location: [location]'. If a value says 'value not recorded', omit the word 'years' (e.g., write 'Age: value not recorded' not 'Age: value not recorded years'). Do not add any introductory sentences, paragraphs, or explanatory text - start directly with 'Patient Demographics:'. Do not add clinical relevance assessments or implications beyond what is explicitly stated in the data.\n"
    )

def prompt_care_plans(demo: Dict[str, Any], conditions: List[Dict[str, Any]], observations: List[Dict[str, Any]], notes: List[Dict[str, Any]]) -> str:
    # Summarize key data points instead of dumping full JSON to reduce tokens and confusion
    age_str = f"Age: {demo.get('ageYears', 'unknown')}" if demo.get('ageYears') != 'value not recorded' else ""
    gender_str = f"Gender: {demo.get('gender', 'unknown')}" if demo.get('gender') != 'value not recorded' else ""
    demographics_summary = f"Patient: {demo.get('name', 'Unknown')} (ID: {demo.get('patientId', 'Unknown')}). {age_str} {gender_str}".strip()
    
    conditions_summary = [f"{c.get('display', 'Unknown condition')}" for c in conditions[:10]]  # Top 10 only
    observations_summary = [f"{o.get('display', 'Unknown')}: {o.get('valueNumber', o.get('valueString', 'N/A'))}" for o in observations[:15]]  # Top 15 only
    
    return (
        "CLINICAL CONTEXT FOR CARE PLANNING:\n\n"
        f"Patient: {demographics_summary}\n\n"
        f"Key Conditions: {', '.join(conditions_summary) if conditions_summary else 'None documented'}\n\n"
        f"Recent Key Observations: {', '.join(observations_summary[:10]) if observations_summary else 'None documented'}\n\n"
        "TASK:\n"
        "Based on the documented clinical data, the following care considerations may be relevant for this patient:\n\n"
        "Write ONLY care considerations as a numbered list (1., 2., 3., etc.). Each consideration should be:\n"
        "- Specific and data-driven\n"
        "- Based on the documented conditions or observations\n"
        "- Brief (1-2 sentences maximum per consideration)\n"
        "- Focused on monitoring, management, or follow-up areas\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Do NOT repeat demographics, conditions list, or observations list\n"
        "- Do NOT start with 'Demographics of the patient' or similar\n"
        "- Start DIRECTLY with numbered care considerations\n"
        "- Only include considerations you can support with the data provided\n"
        "- If no meaningful considerations can be made, write: 'No specific care considerations available based on current data.'\n"
        "- End immediately after the last consideration - no disclaimers or concluding statements\n"
        "- IMPORTANT: These are data-driven observations only. All clinical decisions must be made by qualified healthcare providers based on their professional judgment.\n"
    )

# ---------- Registry ----------
def render_prompt(
    category: str,
    *,
    demo: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    observations: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    Returns {'system': SYSTEM_PROMPT, 'user': user_prompt_text}
    """
    cat = category.lower().strip()

    if cat == "patient_summary":
        return {
            "system": SYSTEM_PROMPT,
            "user": prompt_patient_summary(
                demo or {}, conditions or [], observations or [], notes or []
            ),
        }
    if cat == "conditions":
        return {"system": SYSTEM_PROMPT, "user": prompt_conditions(conditions or [])}
    if cat == "observations":
        return {"system": SYSTEM_PROMPT, "user": prompt_observations_summary(observations or [])}
    if cat == "notes":
        return {"system": SYSTEM_PROMPT, "user": prompt_notes(notes or [])}
    if cat == "demographics":
        return {"system": SYSTEM_PROMPT, "user": prompt_demographics(demo or {})}
    if cat == "care_plans":
        return {"system": SYSTEM_PROMPT, "user": prompt_care_plans(demo or {}, conditions or [], observations or [], notes or [])}

    raise ValueError(f"Unknown category: {category}")
