import logging
import time
from pathlib import Path

from backend.models.document import (
    DocumentType,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
)
from backend.services.ocr_utils import ocr_image_file, ocr_images
from backend.services.pdf_utils import convert_pdf_to_images, extract_pdf_text
from backend.utils.text_normalizer import normalize_text

logger = logging.getLogger(__name__)

MIN_CHARS_PER_PAGE = 20
MAX_OCR_PAGES = 25


def process_document(path: Path) -> ExtractionResult:
    start = time.perf_counter()
    ext = path.suffix.lower()
    logger.info("Processing started: type=%s", ext or "unknown")

    try:
        if ext == ".pdf":
            result = _process_pdf(path, start)
        elif ext in {".png", ".jpg", ".jpeg"}:
            result = _process_image(path, start)
        else:
            result = ExtractionResult(
                document_type=DocumentType.UNKNOWN,
                extraction_method=ExtractionMethod.NONE,
                page_count=0,
                extracted_text="",
                extraction_status=ExtractionStatus.FAILED,
                processing_time_ms=_elapsed(start),
                warnings=[f"Unsupported file type: {ext}"],
            )
    except Exception as exc:  # noqa: BLE001 - never crash the backend
        logger.warning("Processing failed: %s", type(exc).__name__)
        return ExtractionResult(
            document_type=DocumentType.PDF if ext == ".pdf" else DocumentType.IMAGE,
            extraction_method=ExtractionMethod.NONE,
            page_count=0,
            extracted_text="",
            extraction_status=ExtractionStatus.FAILED,
            processing_time_ms=_elapsed(start),
            warnings=[str(exc)],
        )

    logger.info(
        "Processing completed: method=%s status=%s pages=%s",
        result.extraction_method.value,
        result.extraction_status.value,
        result.page_count,
    )
    return result


def _process_pdf(path: Path, start: float) -> ExtractionResult:
    warnings: list[str] = []

    try:
        text, page_count = extract_pdf_text(path)
    except Exception as exc:  # noqa: BLE001 - e.g. encrypted/corrupted PDF
        warnings.append(f"Direct extraction failed: {exc}")
        text, page_count = "", 0

    if text.strip():
        logger.info("Text extraction method: direct")
        return ExtractionResult(
            document_type=DocumentType.PDF,
            extraction_method=ExtractionMethod.DIRECT,
            page_count=page_count,
            extracted_text=normalize_text(text),
            extraction_status=ExtractionStatus.SUCCESS,
            processing_time_ms=_elapsed(start),
            warnings=warnings,
        )

    warnings.append("Low/no selectable text — falling back to OCR")
    logger.info("OCR fallback triggered")
    try:
        images = convert_pdf_to_images(path)
        if len(images) > MAX_OCR_PAGES:
            warnings.append(f"PDF truncated to first {MAX_OCR_PAGES} pages for OCR")
            images = images[:MAX_OCR_PAGES]
        ocr_text = ocr_images(images)
        page_count = page_count or len(images)
    except Exception as exc:  # noqa: BLE001 - e.g. missing poppler/tesseract
        warnings.append(f"OCR fallback failed: {exc}")
        return ExtractionResult(
            document_type=DocumentType.PDF,
            extraction_method=ExtractionMethod.NONE,
            page_count=page_count,
            extracted_text="",
            extraction_status=ExtractionStatus.FAILED,
            processing_time_ms=_elapsed(start),
            warnings=warnings,
        )

    status = ExtractionStatus.SUCCESS if ocr_text.strip() else ExtractionStatus.PARTIAL
    if status == ExtractionStatus.PARTIAL:
        warnings.append("OCR returned little or no text")

    return ExtractionResult(
        document_type=DocumentType.PDF,
        extraction_method=ExtractionMethod.OCR_FALLBACK,
        page_count=page_count,
        extracted_text=normalize_text(ocr_text),
        extraction_status=status,
        processing_time_ms=_elapsed(start),
        warnings=warnings,
    )


def _process_image(path: Path, start: float) -> ExtractionResult:
    warnings: list[str] = []
    text = ocr_image_file(path)
    status = ExtractionStatus.SUCCESS if text.strip() else ExtractionStatus.PARTIAL
    if status == ExtractionStatus.PARTIAL:
        warnings.append("OCR returned little or no text")

    return ExtractionResult(
        document_type=DocumentType.IMAGE,
        extraction_method=ExtractionMethod.OCR,
        page_count=1,
        extracted_text=normalize_text(text),
        extraction_status=status,
        processing_time_ms=_elapsed(start),
        warnings=warnings,
    )


def _elapsed(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
