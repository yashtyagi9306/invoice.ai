from typing import Optional

from fastapi import Header, HTTPException

from backend.config import get_settings


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    configured_key = get_settings().backend_api_key
    if configured_key and x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
