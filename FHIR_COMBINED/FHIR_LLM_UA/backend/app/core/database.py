# backend/app/core/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from dotenv import load_dotenv

# Load root .env (repo root, not backend/.env)
# Path from: backend/app/core/database.py -> FHIR_COMBINED/ (root)
ROOT_DIR = Path(__file__).resolve().parents[4]  # Go up 4 levels to repo root
load_dotenv(ROOT_DIR / ".env")

# --- DB env ---
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "llm_ua_clinical")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SOCKET = os.getenv("DB_SOCKET")  # optional; leave empty if not using socket

# Build SQLAlchemy URL safely
if DB_SOCKET:
    database_url = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        query={"unix_socket": DB_SOCKET},
    )
else:
    database_url = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )

engine = create_engine(database_url, pool_pre_ping=True)
