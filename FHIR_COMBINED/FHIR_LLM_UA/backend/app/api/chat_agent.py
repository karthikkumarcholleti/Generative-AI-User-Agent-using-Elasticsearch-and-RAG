# backend/app/api/chat_agent.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
import logging
import time
import os

from .elasticsearch_client import es_client
from .rag_service import rag_service
from .visualization_service import visualization_service
from .observation_grouper import observation_grouper
from .summary import clear_patient_session
from ..core.database import engine
from ..core.llm import get_gpu_memory_status
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-agent", tags=["chat-agent"])

# Track current patient for chat queries
_chat_current_patient_id: Optional[str] = None

# ---- In-memory cache for chat messages ----
chat_messages_cache: Dict[str, List[Dict[str, Any]]] = {}  # patient_id -> list of messages
MAX_CHAT_CACHE_SIZE = int(os.getenv("LLM_MAX_CACHE_PATIENTS", "3"))  # Keep only last 3 patients

# Request/Response Models
class ChatQuery(BaseModel):
    patient_id: str
    query: str
    session_id: Optional[str] = None
    
    class Config:
        # Validate on assignment for research quality
        validate_assignment = True
    
    @validator('patient_id')
    def validate_patient_id(cls, v):
        """Validate patient_id format for security and data integrity"""
        if not v or not isinstance(v, str):
            raise ValueError("patient_id must be a non-empty string")
        v = v.strip()
        if not v:
            raise ValueError("patient_id cannot be empty or whitespace only")
        if len(v) > 100:  # Reasonable limit for patient IDs
            raise ValueError("patient_id too long (max 100 characters)")
        # Allow alphanumeric, hyphens, underscores (common in patient ID formats)
        if not all(c.isalnum() or c in ['-', '_', '.'] for c in v):
            raise ValueError("patient_id contains invalid characters")
        return v
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query for security and quality"""
        if not v or not isinstance(v, str):
            raise ValueError("query must be a non-empty string")
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty or whitespace only")
        if len(v) > 5000:  # Reasonable limit for queries
            raise ValueError("query too long (max 5000 characters)")
        return v

class ChatResponse(BaseModel):
    response: str
    follow_up_options: List[Dict[str, str]]
    intent: Dict[str, Any]
    data_found: bool
    retrieved_count: int
    session_id: Optional[str] = None
    sources: Optional[List[Dict[str, str]]] = []
    chart: Optional[Dict[str, Any]] = None  # Auto-generated chart data (single chart or categorized charts)

class VisualizationRequest(BaseModel):
    patient_id: str
    chart_type: str
    parameters: Optional[Dict[str, Any]] = None

class VisualizationResponse(BaseModel):
    chart_data: Dict[str, Any]
    chart_type: str
    patient_id: str
    success: bool
    error: Optional[str] = None

class ExportRequest(BaseModel):
    patient_id: str
    export_type: str  # pdf, html, json
    include_charts: bool = True
    include_conversation: bool = True

class ExportResponse(BaseModel):
    success: bool
    file_url: Optional[str] = None
    file_content: Optional[str] = None
    error: Optional[str] = None

class PatientContextResponse(BaseModel):
    patient_id: str
    patient_name: str
    data_summary: Dict[str, Any]
    indexed: bool
    last_updated: Optional[str] = None

# Helper function to get patient data from database
def get_patient_data_from_db(patient_id: str, for_indexing: bool = False) -> Dict[str, Any]:
    """
    Get patient data from database for indexing or API responses.
    
    Args:
        patient_id: Patient ID to fetch data for
        for_indexing: If True, removes limits to get ALL data (for complete indexing).
                     If False, uses reasonable limits for API responses (default).
    """
    # Set limits based on use case
    # For indexing: Get ALL data (very high limits)
    # For API: Use reasonable limits for performance
    max_conditions = 10000 if for_indexing else 50
    max_observations = 10000 if for_indexing else 200
    max_encounters = 10000 if for_indexing else 50
    max_notes = 10000 if for_indexing else 10
    
    with engine.connect() as conn:
        # Get demographics
        sql_p = """
        SELECT patient_id, CONCAT(given_name, ' ', family_name) AS name,
               birth_date, gender, city, state, postal_code
        FROM patients
        WHERE patient_id = :pid
        LIMIT 1
        """
        p = conn.execute(text(sql_p), {"pid": patient_id}).mappings().first()
        if not p:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Get conditions
        sql_c = """
        SELECT c.code, c.display, c.clinical_status, c.effectiveDateTime AS recordedDate
        FROM conditions c
        WHERE c.patient_id = :pid
        ORDER BY COALESCE(c.effectiveDateTime, '1000-01-01') DESC, c.id DESC
        LIMIT :limit
        """
        rows_c = conn.execute(text(sql_c), {"pid": patient_id, "limit": max_conditions}).mappings().all()
        conditions = [{
            "code": r["code"],
            "display": r["display"],
            "clinicalStatus": r["clinical_status"],
            "recordedDate": r["recordedDate"].isoformat() if r["recordedDate"] else None,
        } for r in rows_c]
        
        # Get observations
        sql_o = """
        SELECT o.code, o.display, o.value_numeric AS valueNumber, o.value_string AS valueString,
               o.unit, o.effectiveDateTime
        FROM observations o
        WHERE o.patient_id = :pid
          AND (o.value_numeric IS NOT NULL OR o.value_string IS NOT NULL)
        ORDER BY COALESCE(o.effectiveDateTime, '1000-01-01') DESC, o.id DESC
        LIMIT :limit
        """
        rows_o = conn.execute(text(sql_o), {"pid": patient_id, "limit": max_observations}).mappings().all()
        observations = [{
            "code": r["code"],
            "display": r["display"],
            "valueNumber": float(r["valueNumber"]) if r["valueNumber"] is not None else None,
            "valueString": r["valueString"],
            "unit": r["unit"],
            "effectiveDateTime": r["effectiveDateTime"].isoformat() if r["effectiveDateTime"] else None,
        } for r in rows_o]
        
        # Get notes (handle case where table doesn't exist)
        # First try cocm_db, then try llm_ua_reader if available
        notes = []
        
        # Try cocm_db first
        try:
            sql_n = """
            SELECT COALESCE(n.note_datetime, n.created_at) AS created,
                   n.note_text AS text, n.source_type AS sourceType,
                   n.filename_txt AS fileName, n.base_key AS baseKey
            FROM notes n
            WHERE n.patient_id = :pid
            ORDER BY COALESCE(n.note_datetime, n.created_at) DESC, n.id DESC
            LIMIT :limit
            """
            rows_n = conn.execute(text(sql_n), {"pid": patient_id, "limit": max_notes}).mappings().all()
            notes = [{
                "created": r["created"].isoformat() if r["created"] else None,
                "text": r["text"],
                "sourceType": r["sourceType"],
                "fileName": r["fileName"],
                "baseKey": r["baseKey"],
            } for r in rows_n]
        except Exception as e:
            # Table doesn't exist in cocm_db - try llm_ua_reader
            logger.debug(f"Notes table not in cocm_db, trying llm_ua_reader: {e}")
            notes = []
        
        # If no notes found in cocm_db, try llm_ua_reader database
        if not notes:
            try:
                # Create separate connection to llm_ua_reader
                import pymysql
                from app.core.database import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
                
                llm_conn = pymysql.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database='llm_ua_reader'
                )
                with llm_conn.cursor(pymysql.cursors.DictCursor) as cur:
                    cur.execute("""
                        SELECT COALESCE(note_datetime, created_at) AS created,
                               note_text AS text, source_type AS sourceType,
                               filename_txt AS fileName, base_key AS baseKey
                        FROM notes
                        WHERE patient_id = %s
                        ORDER BY COALESCE(note_datetime, created_at) DESC, id DESC
                        LIMIT %s
                    """, (patient_id, max_notes))
                    rows_n = cur.fetchall()
                    notes = [{
                        "created": r["created"].isoformat() if r["created"] else None,
                        "text": r["text"],
                        "sourceType": r["sourceType"],
                        "fileName": r["fileName"],
                        "baseKey": r["baseKey"],
                    } for r in rows_n]
                llm_conn.close()
                if notes:
                    logger.info(f"Found {len(notes)} notes from llm_ua_reader for patient {patient_id}")
            except Exception as e:
                # llm_ua_reader not accessible or doesn't exist - continue without notes
                logger.debug(f"Could not access notes from llm_ua_reader: {e}")
                notes = []
        
        # Get encounters (available in cocm_db)
        encounters = []
        try:
            sql_e = """
            SELECT e.class_code, e.class_display, e.type_code, e.type_display,
                   e.date, e.admission_reason, e.source_type
            FROM encounters e
            WHERE e.patient_id = :pid
            ORDER BY COALESCE(e.date, '1000-01-01') DESC, e.id DESC
            LIMIT :limit
            """
            rows_e = conn.execute(text(sql_e), {"pid": patient_id, "limit": max_encounters}).mappings().all()
            encounters = [{
                "classCode": r["class_code"],
                "classDisplay": r["class_display"],
                "typeCode": r["type_code"],
                "typeDisplay": r["type_display"],
                "date": r["date"].isoformat() if r["date"] else None,
                "admissionReason": r["admission_reason"],
                "sourceType": r["source_type"],
            } for r in rows_e]
        except Exception as e:
            # Table doesn't exist or other error - continue without encounters
            logger.debug(f"Encounters table not available or error fetching encounters: {e}")
            encounters = []
        
        return {
            "demographics": {
                "patientId": p["patient_id"],
                "name": p["name"],
                "birthDate": p["birth_date"].isoformat() if p["birth_date"] else None,
                "gender": p["gender"],
                "city": p["city"],
                "state": p["state"],
                "postalCode": p["postal_code"],
            },
            "conditions": conditions,
            "observations": observations,
            "notes": notes,
            "encounters": encounters
        }

# API Endpoints
@router.post("/query", response_model=ChatResponse)
def process_chat_query(request: ChatQuery):
    """
    Process a chat query for a specific patient using RAG.
    
    This endpoint validates input, processes the query using RAG, and returns
    a comprehensive response with sources and optional visualizations.
    
    Automatically detects patient switches and clears previous patient's session.
    
    Args:
        request: ChatQuery containing patient_id, query, and optional session_id
        
    Returns:
        ChatResponse with response text, follow-up options, intent, sources, and chart
        
    Raises:
        HTTPException: If patient not found, query processing fails, or validation errors
    """
    global _chat_current_patient_id
    
    print(f"🔍 API Call - Chat Query")
    print(f"🔍 Patient ID: {request.patient_id}")
    print(f"🔍 Query: {request.query}")
    print(f"🔍 Session ID: {request.session_id}")
    
    logger.info(f"Chat agent query received for patient: {request.patient_id}")
    logger.info(f"Query: {request.query}")
    
    # Detect patient switch and clear previous patient's session
    if _chat_current_patient_id and _chat_current_patient_id != request.patient_id:
        print(f"🔄 Patient switch detected in chat: {_chat_current_patient_id} → {request.patient_id}")
        clear_patient_session(_chat_current_patient_id)
    
    _chat_current_patient_id = request.patient_id
    
    # Additional validation for research quality
    if not request.patient_id or not request.patient_id.strip():
        logger.error("Empty patient_id received")
        raise HTTPException(status_code=400, detail="patient_id is required and cannot be empty")
    
    if not request.query or not request.query.strip():
        logger.error("Empty query received")
        raise HTTPException(status_code=400, detail="query is required and cannot be empty")
    
    try:
        # Check if this is a grouped visualization request
        # Safely handle None query
        query_lower = (request.query or "").lower()
        is_grouped_viz = any(keyword in query_lower for keyword in [
            "all observations grouped", "grouped observations", "by category", 
            "by group", "by type", "grouped visualization", "show all by"
        ])
        
        # Process the query using RAG service
        print(f"🔍 Processing query with RAG service...")
        result = rag_service.process_chat_query(request.patient_id, request.query)
        
        # Validate result structure for research quality
        if not isinstance(result, dict):
            logger.error(f"Invalid result type from RAG service: {type(result)}")
            raise HTTPException(status_code=500, detail="Invalid response format from query processor")
        
        # Ensure required fields are present
        required_fields = ['response', 'follow_up_options', 'intent', 'data_found', 'retrieved_count']
        missing_fields = [field for field in required_fields if field not in result]
        if missing_fields:
            logger.error(f"Missing required fields in RAG result: {missing_fields}")
            raise HTTPException(status_code=500, detail=f"Invalid response structure: missing {missing_fields}")
        
        # Add grouped visualization flag to intent if detected
        if is_grouped_viz:
            result["intent"]["type"] = "grouped_visualization"
            if "parameters" not in result["intent"]:
                result["intent"]["parameters"] = []
            result["intent"]["parameters"].append("grouped_visualization")
        
        # Enhanced logging for research quality
        retrieved_count = result.get('retrieved_count', 0)
        data_found = result.get('data_found', False)
        
        print(f"✅ Query processed successfully")
        print(f"🔍 Intent: {result.get('intent', {}).get('type', 'unknown')}")
        print(f"🔍 Data found: {data_found}")
        print(f"🔍 Retrieved count: {retrieved_count}")
        print(f"🔍 Response length: {len(result.get('response', ''))} characters")
        if result.get('chart'):
            print(f"📊 Chart generated: {result['chart'].get('type', 'unknown')}")
        
        # Log warning if data inconsistency detected
        if retrieved_count > 0 and not data_found:
            logger.warning(f"Data inconsistency: retrieved_count={retrieved_count} but data_found=False")
        elif retrieved_count == 0 and data_found:
            logger.warning(f"Data inconsistency: retrieved_count=0 but data_found=True")
        
        logger.info(f"Query processed: patient={request.patient_id}, retrieved={retrieved_count}, data_found={data_found}")
        print(f"✅ Response sent to client\n")
        
        return ChatResponse(
            response=result["response"],
            follow_up_options=result["follow_up_options"],
            intent=result["intent"],
            data_found=result["data_found"],
            retrieved_count=result["retrieved_count"],
            session_id=request.session_id,
            sources=result.get("sources", []),
            chart=result.get("chart")  # Include auto-generated chart
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 404) as-is
        raise
    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error in chat query: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except RuntimeError as e:
        # Check for OOM errors specifically
        error_str = str(e).lower()
        if 'out of memory' in error_str or 'cuda' in error_str:
            logger.error(f"OOM error in chat query: {e}", exc_info=True)
            # Clear GPU memory aggressively
            raise HTTPException(
                status_code=503,
                detail="The system is temporarily overloaded. Please try again in a moment or rephrase your query."
            )
        else:
            logger.error(f"Runtime error in chat query: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="An error occurred while processing your query. Please try again."
            )
    except Exception as e:
        # Enhanced error logging for research quality
        error_msg = f"Failed to process chat query for patient {request.patient_id}: {type(e).__name__}: {str(e)}"
        print(f"❌ Error processing chat query: {error_msg}")
        logger.error(error_msg, exc_info=True)
        # Provide more helpful error messages
        if "timeout" in str(e).lower():
            raise HTTPException(
                status_code=504,
                detail="The query took too long to process. Please try a simpler question or try again later."
            )
        # Don't expose internal error details to client for security
        raise HTTPException(
            status_code=500, 
            detail="An error occurred while processing your query. Please try again or contact support if the issue persists."
        )

@router.get("/source/{source_id}")
def get_source_detail(source_id: str):
    """
    Get detailed source information by source ID for verification.
    Allows clinicians to click on sources to see full proof and prevent hallucinations.
    
    Returns:
        - Full source content
        - Metadata (display, value, unit, code, date)
        - Relevance score
        - Data type
        - All available source information
    """
    try:
        source_detail = rag_service.get_source_detail(source_id)
        
        if not source_detail:
            raise HTTPException(status_code=404, detail=f"Source with ID {source_id} not found")
        
        # Return detailed source information
        return {
            "source_id": source_id,
            "data_type": source_detail.get("data_type", "unknown"),
            "display": source_detail.get("display", ""),
            "value": source_detail.get("value", ""),
            "unit": source_detail.get("unit", ""),
            "date": source_detail.get("date", ""),
            "code": source_detail.get("code", ""),
            "score": source_detail.get("score", 0),
            "timestamp": source_detail.get("timestamp", ""),
            "filename": source_detail.get("filename", ""),
            "source_type": source_detail.get("source_type", ""),
            "content": source_detail.get("content", ""),
            "description": source_detail.get("description", ""),
            "metadata": source_detail.get("metadata", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving source detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve source detail: {str(e)}")

@router.post("/visualize", response_model=VisualizationResponse)
def create_visualization(request: VisualizationRequest):
    """
    Generate visualization data for a specific chart type
    """
    logger.info(f"Visualization request received for patient: {request.patient_id}")
    logger.info(f"Chart type: {request.chart_type}")
    
    try:
        chart_data = visualization_service.generate_chart_data(
            request.patient_id, 
            request.chart_type
        )
        
        return VisualizationResponse(
            chart_data=chart_data,
            chart_type=request.chart_type,
            patient_id=request.patient_id,
            success=chart_data.get("error") is None,
            error=chart_data.get("error")
        )
        
    except Exception as e:
        logger.error(f"Failed to create visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create visualization: {str(e)}")

@router.post("/visualize/grouped")
def create_grouped_visualizations(patient_id: str):
    """
    Generate grouped visualizations for all observation categories
    Returns visualizations organized by clinical category (vital signs, lab values, etc.)
    Each group has its own chart with explanatory text
    """
    logger.info(f"Grouped visualization request received for patient: {patient_id}")
    
    try:
        # Get all observations for the patient from ElasticSearch
        if not es_client.is_connected():
            raise HTTPException(status_code=503, detail="ElasticSearch not available")
        
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"patient_id": patient_id}},
                        {"term": {"data_type": "observations"}}
                    ]
                }
            },
            "size": 500,
            "sort": [{"timestamp": {"order": "asc"}}]
        }
        
        response = es_client.client.search(index="patient_data", body=search_body)
        
        # Extract observations
        observations = []
        for hit in response["hits"]["hits"]:
            # Safely handle missing _source key
            source = hit.get("_source", {})
            if not isinstance(source, dict):
                continue
            # Safely handle missing metadata key
            metadata = source.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            observations.append({
                "display": metadata.get("display", ""),
                "value": metadata.get("value", ""),
                "unit": metadata.get("unit", ""),
                "date": metadata.get("date", ""),
                "code": metadata.get("code", "")
            })
        
        # Group observations by clinical category
        grouped_obs = observation_grouper.group_observations(observations)
        
        # Generate visualizations for each group (only if data exists)
        result = {
            "patient_id": patient_id,
            "groups": [],
            "total_categories": len(grouped_obs),
            "categories_with_data": 0
        }
        
        for category, obs_list in grouped_obs.items():
            # Skip empty categories
            if not obs_list or len(obs_list) == 0:
                continue
            
            group_name = observation_grouper.get_category_display_name(category)
            
            # Check if chart has valid data
            chart_data = create_group_chart(obs_list, group_name, patient_id)
            
            # Only add if chart has actual data points
            if chart_data is not None and chart_data.get("data", {}).get("datasets"):
                datasets = chart_data["data"]["datasets"]
                # Check if any dataset has valid data
                has_data = any(
                    dataset.get("data") and 
                    any(v is not None for v in dataset["data"])
                    for dataset in datasets
                )
                
                if has_data:
                    # Generate explanatory text
                    explanation = generate_group_explanation(obs_list, group_name)
                    
                    result["groups"].append({
                        "category": category,
                        "category_name": group_name,
                        "chart_data": chart_data,
                        "explanation": explanation,
                        "observation_count": len(obs_list)
                    })
                    result["categories_with_data"] += 1
        
        # Add summary message
        if result["categories_with_data"] == 0:
            result["message"] = "No observation data available for visualization."
        else:
            result["message"] = f"Generated {result['categories_with_data']} visualization(s) from {len(observations)} total observations."
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create grouped visualizations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create grouped visualizations: {str(e)}")

def create_group_chart(observations: List[Dict[str, Any]], group_name: str, patient_id: str) -> Optional[Dict[str, Any]]:
    """Create chart data for a group of observations"""
    # Group observations by type
    obs_by_type = {}
    for obs in observations:
        display = obs["display"]
        if display not in obs_by_type:
            obs_by_type[display] = []
        obs_by_type[display].append(obs)
    
    # Create datasets for each observation type
    datasets = []
    colors = [
        "#e74c3c", "#3498db", "#f39c12", "#9b59b6", "#1abc9c",
        "#34495e", "#e67e22", "#2ecc71", "#8e44ad", "#f1c40f"
    ]
    
    # Get all unique dates
    all_dates = sorted(set(obs["date"][:10] for obs in observations if obs["date"]))
    
    # Skip if no dates
    if not all_dates:
        return None
    
    for i, (obs_type, obs_list) in enumerate(obs_by_type.items()):
        # Extract numeric values
        values = []
        for date in all_dates:
            matching_obs = [o for o in obs_list if o["date"][:10] == date]
            if matching_obs:
                try:
                    value_str = matching_obs[0]["value"]
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', value_str)
                    values.append(float(numbers[0]) if numbers else None)
                except:
                    values.append(None)
            else:
                values.append(None)
        
        # Only add dataset if it has valid data
        if any(v is not None for v in values):
            datasets.append({
                "label": obs_type,
                "data": values,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)] + "33",
                "borderWidth": 2
            })
    
    # Return None if no valid datasets
    if not datasets:
        return None
    
    return {
        "type": "line",
        "data": {
            "labels": all_dates,
            "datasets": datasets
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {
                    "display": True,
                    "text": f"{group_name} - Patient {patient_id}"
                }
            }
        }
    }

def generate_group_explanation(observations: List[Dict[str, Any]], group_name: str) -> str:
    """Generate a one-line explanation for a group of observations"""
    if not observations:
        return f"No {group_name} data available."
    
    obs_by_type = {}
    for obs in observations:
        display = obs["display"]
        if display not in obs_by_type:
            obs_by_type[display] = []
        obs_by_type[display].append(obs)
    
    if len(obs_by_type) == 1:
        # Single observation type
        obs_type = list(obs_by_type.keys())[0]
        obs_list = obs_by_type[obs_type]
        if len(obs_list) == 1:
            # Single value
            value = obs_list[0]["value"]
            unit = obs_list[0]["unit"]
            return f"{obs_type}: {value} {unit}"
        else:
            # Multiple values - show trend
            first_val = obs_list[0]["value"]
            last_val = obs_list[-1]["value"]
            unit = obs_list[0]["unit"]
            return f"{obs_type} trends from {first_val} to {last_val} {unit}"
    else:
        # Multiple observation types
        return f"{group_name}: {len(obs_by_type)} different measurements with {len(observations)} total readings."

@router.get("/patient/{patient_id}/context", response_model=PatientContextResponse)
def get_patient_context(patient_id: str):
    """
    Get patient context and check if data is indexed in ElasticSearch
    """
    try:
        # Get patient data from database
        patient_data = get_patient_data_from_db(patient_id)
        
        # Check if data is indexed
        indexed = False
        if es_client.is_connected():
            summary = es_client.get_patient_summary(patient_id)
            indexed = summary.get("total_documents", 0) > 0
        
        return PatientContextResponse(
            patient_id=patient_id,
            patient_name=patient_data["demographics"]["name"],
            data_summary={
                "conditions_count": len(patient_data["conditions"]),
                "observations_count": len(patient_data["observations"]),
                "notes_count": len(patient_data["notes"])
            },
            indexed=indexed,
            last_updated="2024-01-01T00:00:00Z"  # You might want to track actual timestamps
        )
        
    except Exception as e:
        logger.error(f"Failed to get patient context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get patient context: {str(e)}")

@router.post("/index-all-patients")
async def index_all_patients():
    """
    Index all patients from the database into ElasticSearch with embeddings for semantic search.
    This will check if indexing is needed and only index missing patients.
    """
    try:
        from sqlalchemy import text
        
        # Check current indexing status
        indexing_status = es_client.get_indexing_status()
        indexed_patients = indexing_status.get("unique_patients", 0)
        
        # Get all unique patient IDs from the database
        with engine.connect() as conn:
            patient_query = text("SELECT DISTINCT patient_id FROM patients ORDER BY patient_id")
            result = conn.execute(patient_query)
            patient_ids = [row[0] for row in result.fetchall()]
        
        total_patients = len(patient_ids)
        
        # Check if we need to re-index everything or just missing patients
        needs_full_reindex = (
            not indexing_status.get("index_exists", False) or
            not indexing_status.get("has_embeddings", False) or
            indexed_patients < total_patients * 0.5  # If less than 50% indexed, do full reindex
        )
        
        if needs_full_reindex:
            logger.info(f"Starting full reindexing: {total_patients} patients with embeddings for semantic search")
            logger.info("Reason: Index missing or missing embeddings or less than 50% indexed")
        else:
            logger.info(f"Indexing status: {indexed_patients}/{total_patients} patients already indexed")
            logger.info(f"Will index remaining {total_patients - indexed_patients} patients")
        
        # If index doesn't exist or doesn't have embeddings, recreate it
        if needs_full_reindex and (not indexing_status.get("index_exists", False) or not indexing_status.get("has_embeddings", False)):
            logger.info("Recreating index with embeddings support...")
            if indexing_status.get("index_exists", False):
                # Delete old index if it exists but doesn't have embeddings
                es_client.client.indices.delete(index="patient_data")
            es_client.create_patient_index("patient_data")
        
        logger.info(f"Starting to index patients with embeddings for semantic search")
        
        indexed_count = 0
        errors = []
        
        # If doing full reindex, process all patients
        # Otherwise, check which patients need indexing
        patients_to_index = patient_ids
        if not needs_full_reindex:
            # Get list of already indexed patients
            try:
                agg_body = {
                    "size": 0,
                    "aggs": {
                        "indexed_patients": {
                            "terms": {
                                "field": "patient_id",
                                "size": 10000  # Get all unique patient IDs
                            }
                        }
                    }
                }
                agg_response = es_client.client.search(index="patient_data", body=agg_body)
                indexed_patient_ids = set([
                    bucket["key"] 
                    for bucket in agg_response.get("aggregations", {}).get("indexed_patients", {}).get("buckets", [])
                ])
                # Only index patients that aren't already indexed
                patients_to_index = [pid for pid in patient_ids if pid not in indexed_patient_ids]
                logger.info(f"Skipping {len(indexed_patient_ids)} already indexed patients, indexing {len(patients_to_index)} remaining")
            except Exception as e:
                logger.warning(f"Could not check indexed patients, will index all: {e}")
                patients_to_index = patient_ids
        
        for i, patient_id in enumerate(patients_to_index):
            try:
                # Get patient data with all data (for_indexing=True)
                patient_data = get_patient_data_from_db(patient_id, for_indexing=True)
                
                if not patient_data:
                    errors.append(f"Patient {patient_id}: No data found")
                    continue
                
                # Index with embeddings enabled for semantic search
                if es_client.is_connected():
                    success = es_client.index_patient_data(patient_id, patient_data, generate_embeddings=True)
                    if success:
                        indexed_count += 1
                    else:
                        errors.append(f"Patient {patient_id}: Indexing failed")
                else:
                    errors.append(f"Patient {patient_id}: ElasticSearch not connected")
                
                # Log progress every 100 patients
                if (i + 1) % 100 == 0:
                    logger.info(f"Progress: {i + 1}/{len(patients_to_index)} patients indexed ({indexed_count} successful, {len(errors)} errors)")
                    
            except Exception as e:
                errors.append(f"Patient {patient_id}: {str(e)}")
                logger.warning(f"Error indexing patient {patient_id}: {e}")
        
        # Get final status
        final_status = es_client.get_indexing_status()
        final_indexed = final_status.get("unique_patients", 0)
        
        logger.info(f"Indexing complete: {indexed_count} new patients indexed, {final_indexed} total patients now indexed")
        
        return {
            "success": True,
            "message": f"Indexed {indexed_count} patients successfully. Total indexed: {final_indexed}/{total_patients}",
            "total_patients": total_patients,
            "indexed_count": indexed_count,
            "total_indexed": final_indexed,
            "was_full_reindex": needs_full_reindex,
            "error_count": len(errors),
            "errors": errors[:10]  # Only return first 10 errors to avoid huge response
        }
        
    except Exception as e:
        logger.error(f"Failed to index all patients: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/patient/{patient_id}/index")
def index_patient_data(patient_id: str):
    """
    Index patient data into ElasticSearch for RAG with embeddings for semantic search
    """
    try:
        # Get patient data from database with all data (for_indexing=True)
        patient_data = get_patient_data_from_db(patient_id, for_indexing=True)
        
        # Index into ElasticSearch with embeddings enabled for semantic search
        if es_client.is_connected():
            success = es_client.index_patient_data(patient_id, patient_data, generate_embeddings=True)
            if success:
                return {"message": f"Successfully indexed data for patient {patient_id} with embeddings for semantic search"}
            else:
                raise HTTPException(status_code=500, detail="Failed to index patient data")
        else:
            raise HTTPException(status_code=503, detail="ElasticSearch not available")
        
    except Exception as e:
        logger.error(f"Failed to index patient data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to index patient data: {str(e)}")

@router.delete("/patient/{patient_id}/index")
def delete_patient_data(patient_id: str):
    """
    Delete patient data from ElasticSearch
    """
    try:
        if es_client.is_connected():
            success = es_client.delete_patient_data(patient_id)
            if success:
                return {"message": f"Successfully deleted data for patient {patient_id}"}
            else:
                raise HTTPException(status_code=500, detail="Failed to delete patient data")
        else:
            raise HTTPException(status_code=503, detail="ElasticSearch not available")
        
    except Exception as e:
        logger.error(f"Failed to delete patient data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete patient data: {str(e)}")

@router.get("/patient/{patient_id}/conversation")
def get_conversation_history(patient_id: str):
    """
    Get conversation history for a patient
    """
    try:
        history = rag_service.get_conversation_history(patient_id)
        return {"patient_id": patient_id, "conversation_history": history}
        
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")

@router.delete("/patient/{patient_id}/conversation")
def clear_conversation_history(patient_id: str):
    """
    Clear conversation history for a patient
    """
    try:
        success = rag_service.clear_conversation_history(patient_id)
        if success:
            return {"message": f"Successfully cleared conversation history for patient {patient_id}"}
        else:
            return {"message": f"No conversation history found for patient {patient_id}"}
        
    except Exception as e:
        logger.error(f"Failed to clear conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear conversation history: {str(e)}")

# ---- Chat Messages Cache Endpoints ----

class ChatMessagesRequest(BaseModel):
    messages: List[Dict[str, Any]]

class ChatMessagesResponse(BaseModel):
    patient_id: str
    messages: List[Dict[str, Any]]

def limit_chat_cache_size(max_patients: int = MAX_CHAT_CACHE_SIZE):
    """
    Limit chat cache size by removing oldest entries.
    Keeps only the most recent N patients to prevent unbounded memory growth.
    """
    if len(chat_messages_cache) <= max_patients:
        return
    
    # Simple LRU: remove oldest entries (first in dict)
    num_to_remove = len(chat_messages_cache) - max_patients
    keys_to_remove = list(chat_messages_cache.keys())[:num_to_remove]
    for key in keys_to_remove:
        del chat_messages_cache[key]
        logger.info(f"🗑️  Removed oldest chat cache entry for patient: {key}")

@router.get("/patient/{patient_id}/messages", response_model=ChatMessagesResponse)
def get_chat_messages(patient_id: str):
    """
    Get cached chat messages for a patient.
    Returns empty list if no messages cached.
    """
    try:
        messages = chat_messages_cache.get(patient_id, [])
        return ChatMessagesResponse(
            patient_id=patient_id,
            messages=messages
        )
    except Exception as e:
        logger.error(f"Failed to get chat messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat messages: {str(e)}")

@router.post("/patient/{patient_id}/messages", response_model=ChatMessagesResponse)
def save_chat_messages(patient_id: str, request: ChatMessagesRequest):
    """
    Save chat messages to cache for a patient.
    Limits to last 75 messages to prevent memory issues.
    """
    try:
        # Limit to last 75 messages
        messages_to_save = request.messages[-75:] if len(request.messages) > 75 else request.messages
        
        # Save to cache
        chat_messages_cache[patient_id] = messages_to_save
        
        # Limit cache size
        limit_chat_cache_size()
        
        logger.info(f"✅ Saved {len(messages_to_save)} messages to cache for patient {patient_id}")
        return ChatMessagesResponse(
            patient_id=patient_id,
            messages=messages_to_save
        )
    except Exception as e:
        logger.error(f"Failed to save chat messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save chat messages: {str(e)}")

@router.delete("/patient/{patient_id}/messages")
def clear_chat_messages(patient_id: str):
    """
    Clear cached chat messages for a patient.
    """
    try:
        if patient_id in chat_messages_cache:
            del chat_messages_cache[patient_id]
            logger.info(f"✅ Cleared chat messages cache for patient {patient_id}")
            return {"message": f"Successfully cleared chat messages for patient {patient_id}"}
        else:
            return {"message": f"No chat messages found for patient {patient_id}"}
    except Exception as e:
        logger.error(f"Failed to clear chat messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear chat messages: {str(e)}")

@router.get("/charts/types")
def get_available_chart_types():
    """
    Get list of available chart types
    """
    try:
        chart_types = visualization_service.get_available_chart_types()
        return {"chart_types": chart_types}
        
    except Exception as e:
        logger.error(f"Failed to get chart types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chart types: {str(e)}")

@router.post("/export", response_model=ExportResponse)
def export_patient_report(request: ExportRequest):
    """
    Export patient clinical report
    """
    try:
        # Get patient data
        patient_data = get_patient_data_from_db(request.patient_id)
        
        # Get conversation history
        conversation_history = rag_service.get_conversation_history(request.patient_id)
        
        # Generate report content
        report_content = generate_clinical_report(
            patient_data, 
            conversation_history, 
            request.include_charts,
            request.include_conversation
        )
        
        if request.export_type == "html":
            return ExportResponse(
                success=True,
                file_content=report_content,
                file_url=None
            )
        elif request.export_type == "json":
            import json
            return ExportResponse(
                success=True,
                file_content=json.dumps({
                    "patient_data": patient_data,
                    "conversation_history": conversation_history,
                    "generated_at": "2024-01-01T00:00:00Z"
                }, indent=2),
                file_url=None
            )
        else:
            return ExportResponse(
                success=False,
                error=f"Export type {request.export_type} not supported yet"
            )
        
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")

def generate_clinical_report(patient_data: Dict[str, Any], conversation_history: List[Dict[str, Any]], include_charts: bool, include_conversation: bool) -> str:
    """Generate HTML clinical report"""
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Clinical Report - Patient {patient_data['demographics']['patientId']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
            .section {{ margin-bottom: 30px; }}
            .section h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
            .vital-sign {{ display: inline-block; margin: 10px; padding: 15px; background: #ecf0f1; border-radius: 8px; }}
            .abnormal {{ background: #e74c3c; color: white; }}
            .normal {{ background: #27ae60; color: white; }}
            .conversation {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            .user-message {{ background: #3498db; color: white; padding: 10px; border-radius: 5px; margin: 5px 0; }}
            .agent-message {{ background: #ecf0f1; padding: 10px; border-radius: 5px; margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Clinical Report</h1>
            <p><strong>Patient:</strong> {patient_data['demographics']['name']}</p>
            <p><strong>Patient ID:</strong> {patient_data['demographics']['patientId']}</p>
            <p><strong>Generated:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="section">
            <h2>Patient Demographics</h2>
            <p><strong>Name:</strong> {patient_data['demographics']['name']}</p>
            <p><strong>Gender:</strong> {patient_data['demographics'].get('gender', 'Not specified')}</p>
            <p><strong>Location:</strong> {patient_data['demographics'].get('city', 'Not specified')}, {patient_data['demographics'].get('state', 'Not specified')}</p>
        </div>
        
        <div class="section">
            <h2>Medical Conditions</h2>
            <ul>
    """
    
    for condition in patient_data['conditions']:
        html_content += f"<li>{condition['display']} - {condition['clinicalStatus']}</li>"
    
    html_content += """
            </ul>
        </div>
        
        <div class="section">
            <h2>Key Observations</h2>
    """
    
    # Add key observations
    for obs in patient_data['observations'][:10]:  # Show top 10
        value_str = ""
        if obs.get('valueNumber') is not None:
            value_str = f"{obs['valueNumber']}"
            if obs.get('unit'):
                value_str += f" {obs['unit']}"
        elif obs.get('valueString'):
            value_str = obs['valueString']
        
        html_content += f"<p><strong>{obs.get('display', 'Unknown')}:</strong> {value_str}</p>"
    
    html_content += """
        </div>
    """
    
    if include_conversation and conversation_history:
        html_content += """
        <div class="section">
            <h2>AI Assistant Conversation</h2>
        """
        
        for conv in conversation_history:
            html_content += f"""
            <div class="conversation">
                <div class="user-message"><strong>User:</strong> {conv['query']}</div>
                <div class="agent-message"><strong>AI Assistant:</strong> {conv['response']}</div>
            </div>
            """
        
        html_content += """
        </div>
        """
    
    html_content += """
        <div class="section">
            <h2>Report Summary</h2>
            <p>This report was generated using AI-powered analysis of patient data. 
            All information should be verified by qualified healthcare professionals.</p>
        </div>
    </body>
    </html>
    """
    
    return html_content

@router.get("/status")
def get_chat_agent_status():
    """
    Get chat agent service status including indexing information
    """
    try:
        es_connected = es_client.is_connected()
        
        # Get indexing status
        indexing_status = es_client.get_indexing_status() if es_connected else {
            "index_exists": False,
            "total_documents": 0,
            "unique_patients": 0,
            "has_embeddings": False
        }
        
        # Get total patients from database for comparison
        total_patients_in_db = 0
        indexing_needed = False
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                count_query = text("SELECT COUNT(DISTINCT patient_id) as count FROM patients")
                count_result = conn.execute(count_query)
                total_patients_in_db = count_result.fetchone()[0]
            
            # Check if indexing is needed
            indexed_patients = indexing_status.get("unique_patients", 0)
            indexing_needed = (
                not indexing_status.get("index_exists", False) or
                indexed_patients < total_patients_in_db * 0.9  # If less than 90% indexed, suggest re-indexing
            )
        except Exception as e:
            logger.warning(f"Could not get patient count from database: {e}")
        
        return {
            "elasticsearch_connected": es_connected,
            "elasticsearch_url": es_client.es_url if es_client else None,
            "indexing": {
                "index_exists": indexing_status.get("index_exists", False),
                "total_documents": indexing_status.get("total_documents", 0),
                "indexed_patients": indexing_status.get("unique_patients", 0),
                "total_patients_in_db": total_patients_in_db,
                "has_embeddings": indexing_status.get("has_embeddings", False),
                "indexing_needed": indexing_needed,
                "indexing_complete": not indexing_needed and indexing_status.get("index_exists", False)
            },
            "services": {
                "rag_service": "active",
                "visualization_service": "active",
                "elasticsearch_client": "active" if es_connected else "inactive"
            },
            "gpu_memory": get_gpu_memory_status(),
            "current_patient": _chat_current_patient_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return {
            "error": str(e),
            "gpu_memory": get_gpu_memory_status(),
            "current_patient": _chat_current_patient_id
        }

@router.get("/gpu-memory")
def get_gpu_memory():
    """
    Get current GPU memory status across all devices.
    Useful for monitoring memory usage and debugging OOM issues.
    """
    try:
        return get_gpu_memory_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")