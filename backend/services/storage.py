import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile

from backend.config import get_settings

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def save_upload_file(file: UploadFile) -> tuple[str, Path, str]:
    if not file.filename:
        raise ValueError("Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    max_bytes = get_settings().max_upload_size_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds maximum size of {get_settings().max_upload_size_mb}MB")

    file_hash = hashlib.sha256(content).hexdigest()

    file_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{file_id}{ext}"
    with dest.open("wb") as f:
        f.write(content)
    return file_id, dest, file_hash
