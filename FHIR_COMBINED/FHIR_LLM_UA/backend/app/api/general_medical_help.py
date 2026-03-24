# backend/app/api/general_medical_help.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..core.llm import generate_general_medical_help
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class GeneralMedicalHelpRequest(BaseModel):
    question: str

class GeneralMedicalHelpResponse(BaseModel):
    response: str

@router.post("/general-medical-help", response_model=GeneralMedicalHelpResponse)
def get_general_medical_help(request: GeneralMedicalHelpRequest):
    """
    Provide general medical help for medical terms and normal ranges.
    This is for general medical knowledge, not patient-specific data.
    """
    try:
        logger.info(f"General medical help request: {request.question}")
        
        # Generate concise medical help response (2 sentences max)
        response = generate_general_medical_help(request.question)
        
        return GeneralMedicalHelpResponse(response=response)
        
    except Exception as e:
        logger.error(f"Error in general medical help: {e}")
        raise HTTPException(status_code=500, detail=str(e))
