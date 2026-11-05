"""Konfigurasi aplikasi dari environment variable."""
import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "datasets-raw")

FRONTEND_ORIGINS = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_provider = os.getenv("AI_PROVIDER", "").lower().strip()
if not _provider:
    _provider = "gemini" if GEMINI_API_KEY else ("openai" if OPENAI_API_KEY else "none")
AI_PROVIDER = _provider  # gemini | openai | none

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "50"))
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "8"))
ASK_RATE_LIMIT_PER_MIN = int(os.getenv("ASK_RATE_LIMIT_PER_MIN", "20"))
