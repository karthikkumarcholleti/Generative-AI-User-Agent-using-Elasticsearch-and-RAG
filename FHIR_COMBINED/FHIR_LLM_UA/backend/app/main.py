# backend/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .core.database import engine

from contextlib import asynccontextmanager
import threading

@asynccontextmanager
async def lifespan(app):
    # Pre-load model at startup so the first user request isn't blocked by a 2-3 min load.
    # This prevents concurrent requests from piling up during lazy load and causing OOM.
    def _preload():
        try:
            from .core.llm import _load
            print("🚀 Pre-loading LLM model at startup...")
            _load()
            print("✅ LLM model ready")
        except Exception as e:
            print(f"⚠️ LLM pre-load failed (will retry on first request): {e}")
    threading.Thread(target=_preload, daemon=True).start()
    yield

app = FastAPI(title="FHIR LLM_UA API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health ---
class Health(BaseModel):
    status: str
    db: str

@app.get("/health", response_model=Health)
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return {"status": "ok", "db": f"error: {e.__class__.__name__}: {str(e)[:200]}"}

# --- Routers ---
from .api.patients import router as patients_router
from .api.encounters import router as encounters_router
from .api.conditions import router as conditions_router
from .api.observations import router as observations_router
from .api.notes import router as notes_router
from .api.summary import router as summary_router
from .api.llm import router as llm_router
from .api.general_medical_help import router as general_medical_help_router
from .api.chat_agent import router as chat_agent_router
from .api.doctor_agent import router as doctor_agent_router

app.include_router(patients_router)
app.include_router(encounters_router)
app.include_router(conditions_router)
app.include_router(observations_router)
app.include_router(notes_router)
app.include_router(summary_router)
app.include_router(llm_router)
app.include_router(general_medical_help_router)
app.include_router(chat_agent_router)
app.include_router(doctor_agent_router)