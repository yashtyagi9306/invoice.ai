from typing import Optional

from backend.models.extraction import FieldExtraction, InvoiceExtraction
from backend.models.invoice import InvoiceCreate, LineItem, ProcessingStatus
from backend.models.risk import OverallStatus, UnifiedRiskReport
from backend.utils.parsing import parse_date, parse_float

STATUS_MAP = {
    OverallStatus.APPROVED: ProcessingStatus.PROCESSED,
    OverallStatus.FLAGGED: ProcessingStatus.FLAGGED,
    OverallStatus.REJECTED: ProcessingStatus.REJECTED,
}


def build_invoice_record(
    extraction: InvoiceExtraction,
    risk_report: UnifiedRiskReport,
    attachment_path: str,
    file_hash: Optional[str] = None,
    processing_time_ms: Optional[int] = None,
) -> InvoiceCreate:
    line_items = [
        LineItem(
            description=li.description or "",
            quantity=parse_float(li.quantity) or 0,
            unit_price=parse_float(li.unit_price) or 0,
            amount=parse_float(li.amount) or 0,
        )
        for li in extraction.line_items
    ]

    risk = risk_report.risk_assessment

    return InvoiceCreate(
        vendor=_val(extraction.vendor_name),
        invoice_number=_val(extraction.invoice_number),
        invoice_date=parse_date(_val(extraction.invoice_date)),
        due_date=parse_date(_val(extraction.due_date)),
        currency=_val(extraction.currency),
        gst_number=_val(extraction.gst_number),
        purchase_order=_val(extraction.purchase_order_number),
        subtotal=parse_float(_val(extraction.subtotal)),
        tax=parse_float(_val(extraction.tax)),
        discount=parse_float(_val(extraction.discount)),
        grand_total=parse_float(_val(extraction.grand_total)),
        payment_terms=_val(extraction.payment_terms),
        line_items=line_items,
        attachment_path=attachment_path,
        file_hash=file_hash,
        rule_violations=[v.code for v in risk_report.validation.violations],
        processing_time_ms=processing_time_ms,
        ai_summary=risk.reasoning if risk else None,
        risk_score=risk.risk_score if risk else None,
        risk_reason=risk.reasoning if risk else None,
        suggested_action=risk.suggested_action.value if risk else None,
        processing_status=STATUS_MAP.get(risk_report.overall_status, ProcessingStatus.FLAGGED),
    )


def _val(field: FieldExtraction) -> Optional[str]:
    return field.value if field and field.value else None
