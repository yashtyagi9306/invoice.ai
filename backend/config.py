from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

# Load .env from the backend/ directory regardless of where the app is started
# (uvicorn may be launched from the repo root with `backend.main:app`, in which
# case the relative `.env` would not be found). Using an absolute path keeps
# local dev, Railway, and tests consistent.
_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    # LLM provider switch — "ollama" (local), "groq" (free cloud), or "openai" (paid)
    llm_provider: str = "ollama"
    # OpenAI is optional (only used when LLM_PROVIDER=openai)
    openai_api_key: Optional[str] = None
    # Groq is optional (only used when LLM_PROVIDER=groq). Free tier at console.groq.com
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"
    # Ollama is optional (only used when LLM_PROVIDER=ollama)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:3b"
    high_value_threshold: float = 100000
    risk_score_threshold: int = 70
    backend_api_key: Optional[str] = None
    max_upload_size_mb: int = 15

    class Config:
        env_file = str(_BACKEND_DIR / ".env")
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
