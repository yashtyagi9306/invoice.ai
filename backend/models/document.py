from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    DIRECT = "direct"
    OCR = "ocr"
    OCR_FALLBACK = "ocr_fallback"
    NONE = "none"


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ExtractionResult(BaseModel):
    document_type: DocumentType
    extraction_method: ExtractionMethod
    page_count: int
    extracted_text: str
    extraction_status: ExtractionStatus
    processing_time_ms: int
    warnings: list[str] = Field(default_factory=list)
