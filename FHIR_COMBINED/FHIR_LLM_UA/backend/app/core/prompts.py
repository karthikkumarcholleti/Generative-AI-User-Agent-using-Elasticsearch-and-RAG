# backend/app/core/prompts.py

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json

# ---------- Shared system prompt ----------
SYSTEM_PROMPT = (
    "You are a clinical summarization assistant helping healthcare professionals review patient data.\n"
    "- Be factual and base your response strictly on the data provided.\n"
    "- You MAY provide standard clinical interpretations of values (e.g., 'HbA1c of 8.5% indicates poor glycemic control'; "
    "'creatinine of 2.1 mg/dL suggests possible renal impairment'). Use well-established clinical thresholds.\n"
    "- Do NOT fabricate data, invent values, or add information not present in the records.\n"
    "- Do NOT diagnose or prescribe. Interpret values clinically, but note all decisions rest with the clinician.\n"
    "- Preserve units exactly. Do not convert or round away meaning.\n"
    "- If a field is null, None, or says 'value not recorded'/'date not recorded', write: 'not recorded'.\n"
    "- Write in clear, complete sentences. Never leave a sentence truncated.\n"
    "- Use bullet points for lists; paragraphs for narrative sections.\n"
    "- If no data is available for a section, write 'No data recorded' and stop — do not pad.\n"
    "- ALWAYS state the most critical findings first. If output is cut short, the highest-priority findings must already be stated.\n"
    "- ALWAYS complete your response before stopping. Do not start a point you cannot finish.\n"
    "Use retrieved patient data only. When stating a patient-specific fact (a lab value,\n"
    "a condition, or a diagnosis), cite the retrieved item using its [O-N] or [C-N] label.\n"
    "Do not invent patient facts. Reasoning and interpretation do not require citation labels.\n"
)

# ---------- Helpers ----------
def _j(x: Any) -> str:
    """Stable, compact JSON for prompts."""
    return json.dumps(x, ensure_ascii=False)

def _header(title: str) -> str:
    return f"{title.upper()}:\n"

def _demo_context(demo: Dict[str, Any]) -> str:
    """One-line patient context line for use inside section prompts."""
    name = demo.get("name", "Unknown")
    age = demo.get("ageYears", "")
    gender = demo.get("gender", "")
    parts = [p for p in [name, f"{age} y/o" if age and age != "value not recorded" else "", gender] if p]
    return f"Patient: {', '.join(parts)}" if parts else ""

# ---------- Category user prompts ----------

def prompt_patient_summary(
    demo: Dict[str, Any],
    conditions: List[Dict[str, Any]],
    observations: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
    kg_context: str = "",
) -> str:
    """
    Clinical handoff summary: all data, highlights critical findings.
    """
    from ..api.condition_categorizer import group_conditions_by_category

    grouped_conditions = group_conditions_by_category(conditions)

    conditions_text = _header("Conditions (by category, high priority first)")
    category_order = [
        "Cardiovascular", "Metabolic", "Respiratory", "Neurological",
        "Mental Health", "Musculoskeletal", "Gastrointestinal", "Renal",
        "Endocrine", "Oncology", "Acute", "Other"
    ]
    for category in category_order:
        if category in grouped_conditions:
            cat_conds = grouped_conditions[category]
            sorted_conds = sorted(
                cat_conds,
                key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                reverse=True
            )
            conditions_text += f"\n{category}:\n"
            for cond in sorted_conds:
                priority = cond.get("priority", "low")
                name = cond.get("normalizedName") or cond.get("display", "Unknown")
                status = cond.get("clinicalStatus", "unknown")
                conditions_text += f"  [{priority.upper()}] {name} (Status: {status})\n"

    return (
        _header("Demographics") + _j(demo) + "\n\n"
        + conditions_text + "\n\n"
        + _header("Observations (newest first, with trends)") + _j(observations) + "\n\n"
        + _header("Notes (most recent first)") + _j(notes) + "\n\n"
        + (kg_context + "\n\n" if kg_context else "")
        + "TASK: Write a clinical handoff summary for this patient.\n\n"
        "LEAD WITH ALERTS: Before all sections, if any value is critically abnormal, flag it:\n"
        "  [CRITICAL] HbA1c 11.2% — severely uncontrolled diabetes\n"
        "  [ELEVATED] Creatinine 2.4 mg/dL — possible renal impairment\n"
        "  [LOW] Hemoglobin 8.1 g/dL — anemia\n\n"
        "Structure:\n"
        "1. **Patient Overview** — one paragraph: name, age, gender. Include total active conditions count.\n"
        "2. **Active Conditions** — organized by system (Cardiovascular, Metabolic, etc.). "
        "HIGH priority conditions first with clinical status.\n"
        "3. **Key Lab and Vital Findings** — most clinically significant observations with actual values, "
        "units, and normal/elevated/low status. For trends: 'Creatinine rising: 1.8 → 2.1 → 2.4 mg/dL — monitor for CKD progression'.\n"
        "4. **Clinical Notes Highlights** — summarize the most recent clinical findings if notes exist.\n"
        "5. **Clinical Insights** — numbered monitoring priorities and care gaps derived from the data.\n\n"
        "- Include specific values with units for ALL abnormal findings.\n"
        "- Do NOT write sections for data categories that are genuinely empty.\n"
        "- Complete every sentence. Do not start a point you cannot finish.\n"
    )


def prompt_conditions(
    conditions: List[Dict[str, Any]],
    demo: Optional[Dict[str, Any]] = None,
) -> str:
    from ..api.condition_categorizer import group_conditions_by_category

    grouped = group_conditions_by_category(conditions)
    category_order = [
        "Cardiovascular", "Metabolic", "Respiratory", "Neurological",
        "Mental Health", "Musculoskeletal", "Gastrointestinal", "Renal",
        "Endocrine", "Oncology", "Acute", "Other"
    ]

    context_line = _demo_context(demo) if demo else ""

    prompt = ""
    if context_line:
        prompt += context_line + "\n\n"

    prompt += _header("Conditions (by medical category)")

    for category in category_order:
        if category in grouped:
            cat_conds = grouped[category]
            sorted_conds = sorted(
                cat_conds,
                key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                reverse=True
            )
            prompt += f"\n{category} ({len(cat_conds)} condition{'s' if len(cat_conds) != 1 else ''}):\n"
            for cond in sorted_conds:
                priority = cond.get("priority", "low")
                marker = "HIGH" if priority == "high" else "MED" if priority == "medium" else "LOW"
                name = cond.get("normalizedName") or cond.get("display", "Unknown")
                status = cond.get("clinicalStatus", "unknown")
                prompt += f"  [{marker}] {name} (Status: {status})\n"

    for category, cat_conds in grouped.items():
        if category not in category_order:
            sorted_conds = sorted(
                cat_conds,
                key=lambda c: {"high": 3, "medium": 2, "low": 1}.get(c.get("priority", "low"), 1),
                reverse=True
            )
            prompt += f"\n{category} ({len(cat_conds)} condition{'s' if len(cat_conds) != 1 else ''}):\n"
            for cond in sorted_conds:
                priority = cond.get("priority", "low")
                marker = "HIGH" if priority == "high" else "MED" if priority == "medium" else "LOW"
                name = cond.get("normalizedName") or cond.get("display", "Unknown")
                status = cond.get("clinicalStatus", "unknown")
                prompt += f"  [{marker}] {name} (Status: {status})\n"

    prompt += (
        "\n\nTASK: Write a clinical conditions summary organized by medical category.\n\n"
        "Based on the patient's medical data, the patient has the following medical conditions:\n\n"
        "1. List HIGH priority conditions first within each category.\n"
        "2. For each condition provide: condition name — brief one-sentence clinical explanation.\n"
        "3. Mention clinical status (active/resolved/unknown).\n"
        "4. Format:\n"
        "   CARDIOVASCULAR:\n"
        "   1. [Condition] — [explanation] (Status: active)\n"
        "5. Do NOT include ICD/SNOMED codes.\n"
        "6. Do NOT add risk assessments or care recommendations not in the data.\n"
        "7. Complete every sentence. Do not start an entry you cannot finish.\n"
    )
    return prompt


def prompt_observations_summary(
    observations: List[Dict[str, Any]],
    demo: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    kg_context: str = "",
) -> str:
    """Observations summary with actual values, clinical interpretation, and trends."""
    obs_count = len(observations)
    context_line = _demo_context(demo) if demo else ""

    # Build a short conditions context so the LLM can interpret lab values in clinical context
    cond_context = ""
    if conditions:
        high_conds = [
            (c.get("normalizedName") or c.get("display", ""))
            for c in conditions
            if c.get("priority") == "high" and c.get("clinicalStatus") != "resolved"
        ][:6]
        if high_conds:
            cond_context = f"Key active conditions: {', '.join(high_conds)}.\n"

    header = ""
    if context_line:
        header += context_line + "\n"
    if cond_context:
        header += cond_context
    if header:
        header += "\n"

    return (
        header
        + _header(f"Observations ({obs_count} total, newest first, with trends)") + _j(observations) + "\n\n"
        + (kg_context + "\n\n" if kg_context else "")
        + "TASK:\n"
        "The patient's laboratory and clinical observations include:\n\n"
        f"Analyze ALL {obs_count} observations and write a structured clinical observations summary.\n\n"
        "Structure:\n"
        "1. **Vital Signs** — list each with value, unit, status (normal/elevated/low), and trend if available.\n"
        "2. **Blood Chemistry** — glucose, creatinine, BUN, electrolytes, liver enzymes, etc.\n"
        "3. **Hematology** — CBC values: Hgb, WBC, platelets, etc.\n"
        "4. **Endocrine / Metabolic** — HbA1c, cholesterol, thyroid, etc.\n"
        "5. **Other** — any remaining observations.\n\n"
        "For each observation:\n"
        "  - Show the actual value with units.\n"
        "  - State whether it is normal, elevated, or low using standard clinical ranges.\n"
        "  - Include trend summary if available (e.g., 'stable over 5 measurements, Avg: X, Range: Y-Z').\n"
        "  - Provide brief clinical interpretation for abnormal values.\n\n"
        "Abnormal value flagging — prefix the line with the appropriate tag:\n"
        "  [CRITICAL] — life-threatening (e.g., K+ <2.5, Hgb <7, glucose >500)\n"
        "  [ELEVATED] — above normal range (e.g., HbA1c >7%, creatinine >1.2 mg/dL, systolic BP >140)\n"
        "  [LOW]      — below normal range (e.g., Hgb <12 g/dL, sodium <135 mEq/L)\n\n"
        "Rules:\n"
        "- Include ALL observations — do not skip any.\n"
        "- Only use sections that have data; skip empty sections.\n"
        "- Use standard abbreviations: BP, HR, Hgb, WBC, BUN, HbA1c.\n"
        "- Do NOT include dates.\n"
        "- Complete every line. Do not start an entry you cannot finish.\n"
    )


def prompt_observations(observations: List[Dict[str, Any]]) -> str:
    """Detailed observation listing with full trend data (kept for compatibility)."""
    obs_count = len(observations)
    return (
        _header("Observations (aggregated with trends)") + _j(observations) + "\n\n"
        "TASK:\n"
        "The patient's laboratory and clinical observations include:\n\n"
        f"List ALL {obs_count} observations. No exceptions. No duplicates.\n\n"
        "Format:\n"
        "  - If trend available: [Name]: [value] [unit] - [status], [trend] over N measurements (Avg: X, Range: Y-Z)\n"
        "  - If no trend: [Name]: [value] [unit] - [status]\n\n"
        "Rules:\n"
        "1. Abbreviations: BP, HR, Temp. Spell out everything else.\n"
        "2. One line per observation — no duplicates.\n"
        "3. Status: normal/elevated/low based on clinical ranges.\n"
        "4. Group by: Vital Signs, Blood Chemistry, Blood Counts, Other.\n"
        "5. No dates in output.\n"
        "6. Complete every line. Do not start an entry you cannot finish.\n"
    )


def prompt_notes(
    notes: List[Dict[str, Any]],
    demo: Optional[Dict[str, Any]] = None,
) -> str:
    context_line = _demo_context(demo) if demo else ""
    header = (context_line + "\n\n") if context_line else ""
    return (
        header
        + _header("Notes (most recent first)") + _j(notes) + "\n\n"
        "TASK:\n"
        "Write a comprehensive clinical notes summary in paragraph format.\n"
        "Summarize the clinical narrative documented in the notes: key events, clinical decisions, "
        "transfers, procedures, and follow-up actions with dates when present. "
        "Describe only what is explicitly documented. "
        "Write in flowing, well-structured paragraphs. "
        "Do not add interpretations or clinical implications beyond what is stated in the notes. "
        "Complete every sentence. Do not start a sentence you cannot finish.\n"
    )


def prompt_demographics(
    demo: Dict[str, Any],
    conditions: Optional[List[Dict[str, Any]]] = None,
    obs_count: Optional[int] = None,
) -> str:
    # Build a brief clinical context summary for richer demographics section
    cond_summary = ""
    if conditions:
        active = [c for c in conditions if c.get("clinicalStatus") not in ("resolved", "inactive")]
        high = [c for c in active if c.get("priority") == "high"]
        cond_summary = (
            f"\nClinical context: {len(conditions)} documented conditions "
            f"({len(active)} active, {len(high)} high-priority)."
        )
    obs_summary = f" {obs_count} observations on record." if obs_count else ""

    return (
        _header("Patient Demographics") + _j(demo)
        + (cond_summary + obs_summary + "\n" if (cond_summary or obs_summary) else "")
        + "\n\nTASK:\n"
        "Demographics of the patient based on their medical records:\n\n"
        "Provide a demographic summary using ONLY the data above. Use this exact format:\n\n"
        "Patient Demographics:\n"
        "- Name: [full name]\n"
        "- Patient ID: [id]\n"
        "- Age: [age] years  (write 'not recorded' if missing)\n"
        "- Gender: [gender]  (write 'not recorded' if missing)\n"
        "- Date of Birth: [date]  (write 'not recorded' if missing)\n"
        "- Location: [city, state postal_code]  (write 'not recorded' if missing)\n"
        + (
            "\nClinical Summary:\n"
            "- Documented conditions: [total] ([active] active, [high-priority] high-priority)\n"
            "- Observations on record: [count]\n"
            if (cond_summary or obs_summary) else ""
        )
        + "\nDo not add introductory text, narrative paragraphs, or clinical implications. "
        "Start directly with 'Patient Demographics:'. "
        "If a field is null, None, missing, or says 'value not recorded'/'date not recorded', write 'not recorded'.\n"
    )


def prompt_care_plans(
    demo: Dict[str, Any],
    conditions: List[Dict[str, Any]],
    observations: List[Dict[str, Any]],
    notes: List[Dict[str, Any]],
) -> str:
    age_str = f"Age: {demo.get('ageYears')}" if demo.get('ageYears') not in (None, 'value not recorded') else ""
    gender_str = f"Gender: {demo.get('gender')}" if demo.get('gender') not in (None, 'value not recorded') else ""
    demographics_summary = f"Patient: {demo.get('name', 'Unknown')} (ID: {demo.get('patientId', 'Unknown')}). {age_str} {gender_str}".strip()

    # Include all conditions, not just 10
    conditions_summary = [
        f"{c.get('display', 'Unknown condition')} [{c.get('clinicalStatus', 'unknown')}]"
        for c in conditions
    ]
    # Include abnormal observations
    obs_items = []
    for o in observations[:20]:
        val = o.get('valueNumber', o.get('valueString', 'N/A'))
        display = o.get('display', 'Unknown')
        unit = o.get('unit', '')
        obs_items.append(f"{display}: {val} {unit}".strip())

    return (
        "CLINICAL CONTEXT FOR CARE PLANNING:\n\n"
        f"{demographics_summary}\n\n"
        f"Conditions ({len(conditions_summary)} total):\n"
        + "\n".join(f"  - {c}" for c in conditions_summary) + "\n\n"
        + "Recent Observations:\n"
        + "\n".join(f"  - {o}" for o in obs_items) + "\n\n"
        "TASK:\n"
        "Based on the documented clinical data, the following care considerations may be relevant for this patient:\n\n"
        "Write a numbered list of care considerations (1., 2., 3., ...). Each should be:\n"
        "- Specific and tied to the data above (cite the condition or observation).\n"
        "- Brief (1-2 sentences).\n"
        "- Focused on monitoring, management, or follow-up.\n\n"
        "Rules:\n"
        "- Do NOT repeat the demographics, conditions list, or observations list.\n"
        "- Start DIRECTLY with '1.'\n"
        "- Only include considerations supported by the data.\n"
        "- End after the last consideration — no disclaimers or concluding paragraphs.\n"
        "- Complete every sentence. Do not start an entry you cannot finish.\n"
    )


# ---------- Registry ----------
def render_prompt(
    category: str,
    *,
    demo: Optional[Dict[str, Any]] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    observations: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[List[Dict[str, Any]]] = None,
    obs_count: Optional[int] = None,
    kg_context: str = "",
) -> Dict[str, str]:
    """
    Returns {'system': SYSTEM_PROMPT, 'user': user_prompt_text}
    """
    cat = category.lower().strip()

    if cat == "patient_summary":
        return {
            "system": SYSTEM_PROMPT,
            "user": prompt_patient_summary(
                demo or {}, conditions or [], observations or [], notes or [],
                kg_context=kg_context,
            ),
        }
    if cat == "conditions":
        return {"system": SYSTEM_PROMPT, "user": prompt_conditions(conditions or [], demo=demo)}
    if cat == "observations":
        return {
            "system": SYSTEM_PROMPT,
            "user": prompt_observations_summary(
                observations or [], demo=demo, conditions=conditions, kg_context=kg_context
            ),
        }
    if cat == "notes":
        return {"system": SYSTEM_PROMPT, "user": prompt_notes(notes or [], demo=demo)}
    if cat == "demographics":
        _obs_count = obs_count if obs_count is not None else (len(observations) if observations else None)
        return {
            "system": SYSTEM_PROMPT,
            "user": prompt_demographics(demo or {}, conditions=conditions, obs_count=_obs_count),
        }
    if cat == "care_plans":
        return {
            "system": SYSTEM_PROMPT,
            "user": prompt_care_plans(demo or {}, conditions or [], observations or [], notes or []),
        }

    raise ValueError(f"Unknown category: {category}")
