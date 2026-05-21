# backend/app/api/doctor_agent.py
"""
MedRAG Doctor Agent — LLM-as-Agent clinical reasoning system.

Architecture: tool-selection → multi-tool ES/KG retrieval → single doctor synthesis LLM call.

The agent selects clinical tools based on query intent, executes them against the existing
Elasticsearch + MedRAG Knowledge Graph infrastructure, then generates one doctor-quality
response with full evidence access.  A single GPU generation keeps memory pressure low on
the shared 2× Tesla T4 environment.

Available tools (backed by existing infrastructure):
  search_labs      → ES hybrid search, data_type=observations (lab focus)
  search_vitals    → ES hybrid search, data_type=observations (vitals focus)
  search_conditions → ES get_all by data_type=conditions
  run_kg_ddx       → MedRAG KG pipeline (find_candidate_diseases → match_evidence → build_kg_context)
  get_lab_trends   → ES all observations sorted ASC for time-series context
  get_notes        → ES get_all by data_type=notes
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .elasticsearch_client import es_client
from .medrag_knowledge_graph import kg_service
from .rag_service import DDX_INTENT_KEYWORDS, VALUE_LOOKUP_OVERRIDES
from ..core.llm import generate_chat
from .chat_agent import _write_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctor-agent", tags=["doctor-agent"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class DoctorQuery(BaseModel):
    patient_id: str
    query: str

class AgentStep(BaseModel):
    tool: str
    description: str
    result_summary: str

class DoctorResponse(BaseModel):
    response: str
    agent_steps: List[AgentStep]
    pipeline_mode: str
    sources: List[Dict[str, str]]
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool selection (deterministic — no extra LLM call)
# ---------------------------------------------------------------------------

# Lab-related observation keywords
_LAB_TERMS = [
    "lab", "blood", "creatinine", "glucose", "hemoglobin", "hematocrit",
    "wbc", "rbc", "platelet", "bun", "sodium", "potassium", "chloride",
    "calcium", "magnesium", "phosphate", "albumin", "bilirubin", "alt",
    "ast", "alp", "inr", "pt ", "aptt", "troponin", "bnp", "crp",
    "hba1c", "a1c", "cholesterol", "ldl", "hdl", "triglyceride",
    "thyroid", "tsh", "t3", "t4", "ferritin", "iron",
]

# Vital sign keywords
_VITAL_TERMS = [
    "vital", "blood pressure", "systolic", "diastolic", "heart rate",
    "pulse", "temperature", "respiratory rate", "oxygen", "spo2", "bmi",
    "weight", "height",
]

# Clinical note keywords
_NOTE_TERMS = [
    "note", "history", "report", "discharge", "summary", "what happened",
    "admission", "clinical finding", "narrative",
]

# Trend keywords
_TREND_TERMS = [
    "trend", "over time", "changed", "progression", "history of",
    "worsening", "improving", "stable", "trajectory",
]


def _select_tools(query: str) -> List[str]:
    """
    Deterministically pick which tools the agent should run for this query.
    Always includes conditions.  Adds lab/vital/note/trend tools based on
    keyword matching.  DDx is triggered by the same keywords as rag_service.
    """
    q = query.lower()
    tools: List[str] = ["search_conditions"]  # always fetch conditions

    has_lab = any(t in q for t in _LAB_TERMS)
    has_vital = any(t in q for t in _VITAL_TERMS)
    has_ddx = any(k in q for k in DDX_INTENT_KEYWORDS)
    has_value_lookup = any(v in q for v in VALUE_LOOKUP_OVERRIDES)

    # For broad queries ("overall assessment", "health status") fetch everything
    broad_query = any(w in q for w in ["overall", "health status", "summary", "assessment", "all"])

    if has_lab or broad_query:
        tools.append("search_labs")
    if has_vital or broad_query:
        tools.append("search_vitals")
    if any(t in q for t in _NOTE_TERMS) or broad_query:
        tools.append("get_notes")
    if any(t in q for t in _TREND_TERMS):
        tools.append("get_lab_trends")

    # Run DDx KG pipeline when diagnostic intent detected (same gate as rag_service)
    if has_ddx and not has_value_lookup:
        tools.append("run_kg_ddx")
    elif broad_query:
        tools.append("run_kg_ddx")  # always run KG for broad clinical queries

    # If none of the specific tools matched, at least fetch observations
    if "search_labs" not in tools and "search_vitals" not in tools:
        tools.append("search_labs")

    return tools


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------

def _run_search_labs(patient_id: str, query: str) -> List[Dict[str, Any]]:
    return es_client.search_patient_data(
        patient_id, query, data_types=["observations"], use_highlighting=False
    )[:40]


def _run_search_vitals(patient_id: str) -> List[Dict[str, Any]]:
    return es_client.search_patient_data(
        patient_id,
        "vital signs blood pressure heart rate temperature oxygen saturation",
        data_types=["observations"],
        use_highlighting=False,
    )[:20]


def _run_search_conditions(patient_id: str) -> List[Dict[str, Any]]:
    return es_client.get_all_patient_data_by_type(patient_id, "conditions", size=60)


def _run_get_notes(patient_id: str) -> List[Dict[str, Any]]:
    return es_client.get_all_patient_data_by_type(patient_id, "notes", size=5)


def _run_get_lab_trends(patient_id: str) -> List[Dict[str, Any]]:
    """Fetch observations sorted oldest→newest for trend context."""
    if not es_client.is_connected():
        return []
    try:
        resp = es_client.client.search(
            index="patient_data",
            body={
                "query": {"bool": {"must": [
                    {"term": {"patient_id": patient_id}},
                    {"term": {"data_type": "observations"}},
                ]}},
                "sort": [{"timestamp": {"order": "asc"}}],
                "size": 100,
            },
        )
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception as exc:
        logger.warning("get_lab_trends failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _format_observation(doc: Dict[str, Any]) -> str:
    meta = doc.get("metadata", {})
    display = meta.get("display") or meta.get("name") or "Unknown"
    value = meta.get("value", "")
    unit = meta.get("unit", "")
    date = (meta.get("date") or "")[:10]
    parts = [display]
    if value:
        parts.append(f"{value} {unit}".strip())
    if date:
        parts.append(date)
    return " | ".join(parts)


def _format_condition(doc: Dict[str, Any]) -> str:
    meta = doc.get("metadata", {})
    display = meta.get("display") or "Unknown condition"
    status = meta.get("clinicalStatus") or ""
    date = (meta.get("date") or "")[:10]
    line = display
    if status:
        line += f" ({status})"
    if date:
        line += f" — recorded {date}"
    return line


def _build_context(tool_results: Dict[str, List[Dict[str, Any]]]) -> str:
    sections: List[str] = []

    if tool_results.get("search_conditions"):
        conds = [_format_condition(d) for d in tool_results["search_conditions"][:30]]
        sections.append("DIAGNOSES / CONDITIONS:\n" + "\n".join(f"- {c}" for c in conds))

    obs_docs: List[Dict[str, Any]] = []
    for key in ("search_labs", "search_vitals", "get_lab_trends"):
        for doc in tool_results.get(key, []):
            obs_docs.append(doc)

    # Deduplicate by display+date
    seen: set = set()
    unique_obs: List[str] = []
    for doc in obs_docs:
        line = _format_observation(doc)
        if line not in seen:
            seen.add(line)
            unique_obs.append(line)

    if unique_obs:
        sections.append("OBSERVATIONS / LABS:\n" + "\n".join(f"- {o}" for o in unique_obs[:80]))

    if tool_results.get("get_notes"):
        note_parts = []
        for doc in tool_results["get_notes"][:3]:
            content = doc.get("content", "")[:500]
            if content:
                note_parts.append(content)
        if note_parts:
            sections.append("CLINICAL NOTES:\n" + "\n---\n".join(note_parts))

    return "\n\n".join(sections) if sections else "No patient data retrieved."


def _result_summary(tool: str, docs: List[Dict[str, Any]]) -> str:
    n = len(docs)
    if tool == "search_conditions":
        names = [d.get("metadata", {}).get("display", "?") for d in docs[:5]]
        return f"{n} conditions retrieved (top 5: {', '.join(names)})"
    if tool in ("search_labs", "search_vitals"):
        displays = [d.get("metadata", {}).get("display", "?") for d in docs[:5]]
        return f"{n} observations retrieved (e.g.: {', '.join(displays)})"
    if tool == "get_lab_trends":
        return f"{n} time-ordered observation records retrieved"
    if tool == "get_notes":
        return f"{n} clinical note(s) retrieved"
    return f"{n} documents retrieved"


# ---------------------------------------------------------------------------
# Doctor synthesis prompt
# ---------------------------------------------------------------------------

_DOCTOR_SYSTEM = """\
You are Dr. FHIR, a board-certified clinical AI physician agent powered by MedRAG. \
You have expertise in internal medicine, differential diagnosis, and EHR data analysis.

You have retrieved comprehensive patient data using multiple clinical tools and, where \
applicable, a structured Knowledge Graph (KG) differential diagnosis. Your task is to \
reason like a physician presenting at clinical rounds.

CRITICAL RULES:
- ONLY use the data explicitly provided in the context below. NEVER invent values.
- NEVER use asterisks (*) or bold (**text**) formatting. Use numbered lists only.
- Always lead with what IS present in the records — never open with an absence.
- Cite specific lab values, dates, and condition names from the data.
- If KG context is present, use it to anchor your differential diagnosis.
- Do NOT diagnose or prescribe — provide clinical reasoning for the care team.
- All final clinical decisions must be made by qualified healthcare providers.
"""

_DOCTOR_USER_TEMPLATE = """\
Patient Query: "{query}"

{kg_section}

RETRIEVED PATIENT DATA:
{context}

CLINICAL REASONING TASK:
Provide a thorough, physician-quality clinical assessment. Structure your response as follows:

1. Clinical Assessment: Your primary impression based on all available evidence. State the \
most likely diagnosis or clinical picture first, with supporting findings.

2. Key Findings: The most clinically significant data points (values, units, dates). Flag \
abnormal values explicitly.

3. Differential Diagnosis: 2-3 alternative diagnoses with brief reasoning for each, \
referencing specific patient data where possible.

4. Diagnostic Gaps: What tests or data are missing that would confirm or exclude a diagnosis.

5. Clinical Recommendation: Specific, actionable next steps for the care team.
"""


# ---------------------------------------------------------------------------
# Main agent class
# ---------------------------------------------------------------------------

class DoctorAgent:
    """MedRAG Doctor Agent — tool-based retrieval with a single synthesis LLM call."""

    def run(self, patient_id: str, query: str) -> DoctorResponse:
        # 1. Select tools
        tools = _select_tools(query)
        logger.info("[DoctorAgent] patient=%s tools=%s", patient_id, tools)

        # 2. Execute tools
        tool_results: Dict[str, List[Dict[str, Any]]] = {}
        agent_steps: List[AgentStep] = []

        for tool in tools:
            if tool == "search_labs":
                docs = _run_search_labs(patient_id, query)
                tool_results[tool] = docs
                agent_steps.append(AgentStep(
                    tool="search_labs",
                    description="Searched Elasticsearch for laboratory observations relevant to query",
                    result_summary=_result_summary(tool, docs),
                ))
            elif tool == "search_vitals":
                docs = _run_search_vitals(patient_id)
                tool_results[tool] = docs
                agent_steps.append(AgentStep(
                    tool="search_vitals",
                    description="Retrieved vital signs from Elasticsearch",
                    result_summary=_result_summary(tool, docs),
                ))
            elif tool == "search_conditions":
                docs = _run_search_conditions(patient_id)
                tool_results[tool] = docs
                agent_steps.append(AgentStep(
                    tool="search_conditions",
                    description="Retrieved all diagnosed conditions from Elasticsearch",
                    result_summary=_result_summary(tool, docs),
                ))
            elif tool == "get_notes":
                docs = _run_get_notes(patient_id)
                tool_results[tool] = docs
                agent_steps.append(AgentStep(
                    tool="get_notes",
                    description="Retrieved clinical notes from Elasticsearch",
                    result_summary=_result_summary(tool, docs),
                ))
            elif tool == "get_lab_trends":
                docs = _run_get_lab_trends(patient_id)
                tool_results[tool] = docs
                agent_steps.append(AgentStep(
                    tool="get_lab_trends",
                    description="Retrieved time-ordered observations for trend analysis",
                    result_summary=_result_summary(tool, docs),
                ))

        # 3. Build patient context
        context = _build_context(tool_results)

        # 4. Run MedRAG KG pipeline (DDx)
        kg_context = ""
        if "run_kg_ddx" in tools:
            obs_docs = (
                tool_results.get("search_labs", [])
                + tool_results.get("search_vitals", [])
                + tool_results.get("get_lab_trends", [])
            )
            # KG pipeline expects list of {content, metadata} dicts
            kg_input = [
                {
                    "content": d.get("content", ""),
                    "metadata": d.get("metadata", {}),
                    "data_type": d.get("data_type", "observations"),
                }
                for d in obs_docs[:60]
            ]
            kg_result = kg_service.run_kg_pipeline(query, kg_input)
            candidates = kg_result.get("candidate_diseases", [])
            if candidates:
                matched = kg_result.get("matched_evidence", {})
                kg_context = kg_service.build_kg_context(candidates, matched)
                agent_steps.append(AgentStep(
                    tool="run_kg_ddx",
                    description="Ran MedRAG Knowledge Graph differential diagnosis pipeline",
                    result_summary=(
                        f"KG identified {len(candidates)} candidate diagnoses: "
                        + ", ".join(c.get("name", "?") for c in candidates[:4])
                    ),
                ))
            else:
                agent_steps.append(AgentStep(
                    tool="run_kg_ddx",
                    description="Ran MedRAG Knowledge Graph differential diagnosis pipeline",
                    result_summary="No candidate diseases matched in KG for this query.",
                ))

        # 5. Assemble doctor synthesis prompt
        kg_section = (
            f"MEDRAG KNOWLEDGE GRAPH — DIFFERENTIAL DIAGNOSIS CONTEXT:\n{kg_context}\n"
            if kg_context else ""
        )
        user_prompt = _DOCTOR_USER_TEMPLATE.format(
            query=query,
            kg_section=kg_section,
            context=context,
        )

        # 6. LLM synthesis
        response_text = generate_chat(
            system_prompt=_DOCTOR_SYSTEM,
            user_prompt=user_prompt,
            category="doctor_agent",
        ).strip()

        # 7. Build sources list (top observations used)
        sources: List[Dict[str, str]] = []
        for tool in ("search_labs", "search_vitals", "search_conditions"):
            for doc in tool_results.get(tool, [])[:5]:
                meta = doc.get("metadata", {})
                display = meta.get("display") or meta.get("name") or ""
                date = (meta.get("date") or "")[:10]
                dtype = doc.get("data_type", tool)
                if display:
                    sources.append({
                        "id": str(uuid.uuid4()),
                        "type": dtype,
                        "description": f"{display} ({date})" if date else display,
                    })

        return DoctorResponse(
            response=response_text,
            agent_steps=agent_steps,
            pipeline_mode="MedRAG Doctor Agent",
            sources=sources[:15],
        )


doctor_agent = DoctorAgent()


# ---------------------------------------------------------------------------
# FastAPI routes
# ---------------------------------------------------------------------------

@router.post("/query", response_model=DoctorResponse)
def doctor_query(request: DoctorQuery):
    """
    MedRAG Doctor Agent endpoint.

    Runs multi-tool clinical retrieval (labs, vitals, conditions, KG DDx) and
    generates a physician-quality clinical assessment using a single LLM call
    with all evidence assembled.
    """
    logger.info("[DoctorAgent] query patient=%s", request.patient_id)
    if not request.patient_id or not request.query:
        raise HTTPException(status_code=400, detail="patient_id and query are required")
    _start = time.time()
    try:
        result = doctor_agent.run(request.patient_id, request.query)
        _write_audit_log(
            patient_id=request.patient_id,
            query=request.query,
            pipeline_mode="MedRAG Doctor Agent",
            intent_type="doctor_agent",
            retrieved_count=len(result.sources),
            data_found=bool(result.response),
            elapsed_ms=int((time.time() - _start) * 1000),
        )
        return result
    except Exception as exc:
        logger.error("[DoctorAgent] error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
