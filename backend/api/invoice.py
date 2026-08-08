import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.ai.openai_service import extract_invoice_data
from backend.api.security import verify_api_key
from backend.database.crud import create_invoice
from backend.models.document import ExtractionStatus
from backend.services.document_processor import process_document
from backend.services.persistence import build_invoice_record
from backend.services.risk_engine import build_risk_report
from backend.services.storage import save_upload_file

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/process-invoice")
async def process_invoice(
    file: UploadFile = File(...),
    sender: str = Form(...),
    subject: str = Form(...),
    received_at: Optional[str] = Form(default=None),
):
    try:
        file_id, path, file_hash = save_upload_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = process_document(path)

    invoice_data = None
    risk_report = None
    ai_error = None
    invoice_id = None

    if document.extraction_status != ExtractionStatus.FAILED and document.extracted_text:
        extraction = None
        try:
            extraction = extract_invoice_data(document.extracted_text)
            invoice_data = extraction.model_dump()
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI extraction failed: %s", type(exc).__name__)
            ai_error = "AI extraction failed"

        if extraction is not None:
            try:
                report = build_risk_report(extraction, file_hash)
                risk_report = report.model_dump()

                record = build_invoice_record(
                    extraction, report, str(path), file_hash, document.processing_time_ms
                )
                saved = create_invoice(record)
                invoice_id = saved["id"]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Risk scoring or persistence failed: %s", type(exc).__name__)
                ai_error = "Risk scoring or storage failed"
    else:
        logger.info("Skipping AI stage - document extraction status: %s", document.extraction_status)

    return {
        "status": "received",
        "id": file_id,
        "invoice_id": invoice_id,
        "filename": file.filename,
        "sender": sender,
        "subject": subject,
        "received_at": received_at or datetime.utcnow().isoformat(),
        "document": document.model_dump(),
        "invoice_data": invoice_data,
        "risk_report": risk_report,
        "ai_error": ai_error,
    }
