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
    # LLM provider switch — "ollama" (default, runs locally) or "openai"
    llm_provider: str = "ollama"
    # OpenAI fields are optional because Ollama users won't have a key
    openai_api_key: Optional[str] = None
    # Ollama fields
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
