import os
from pathlib import Path
from dotenv import load_dotenv

# Try loading backend .env first
backend_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(backend_env_path)

# Fallback: check frontend .env.local if SUPABASE_URL or SUPABASE_ANON_KEY missing
frontend_env_path = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env.local"
if frontend_env_path.exists():
    load_dotenv(frontend_env_path)

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
SUPABASE_URL: str = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

configured_cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip() and origin.strip().rstrip("/") != "*"
]

CORS_ORIGINS: list[str] = list(dict.fromkeys(DEFAULT_CORS_ORIGINS + configured_cors_origins))
