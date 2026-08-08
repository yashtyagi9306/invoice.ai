import re
from datetime import date
from typing import Optional

from backend.config import get_settings
from backend.database import crud
from backend.models.extraction import InvoiceExtraction, FieldExtraction
from backend.models.validation import RuleViolation, ValidationReport
from backend.utils.parsing import parse_date, parse_float

GST_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP", "AUD", "CAD", "SGD", "AED"}
MAX_REASONABLE_TAX_RATE = 0.35
TOTAL_TOLERANCE = 1.0


def validate_invoice(invoice: InvoiceExtraction, file_hash: Optional[str] = None) -> ValidationReport:
    violations: list[RuleViolation] = []
    warnings: list[str] = []

    vendor = _val(invoice.vendor_name)
    invoice_number = _val(invoice.invoice_number)
    invoice_date = parse_date(_val(invoice.invoice_date))
    due_date = parse_date(_val(invoice.due_date))
    subtotal = parse_float(_val(invoice.subtotal))
    tax = parse_float(_val(invoice.tax))
    discount = parse_float(_val(invoice.discount))
    grand_total = parse_float(_val(invoice.grand_total))
    gst = _val(invoice.gst_number)
    currency = _val(invoice.currency)
    po_number = _val(invoice.purchase_order_number)

    if not invoice_number:
        violations.append(_violation("missing_invoice_number", "Invoice number is missing"))
    if not vendor:
        violations.append(_violation("missing_vendor", "Vendor name is missing"))
    if grand_total is None:
        violations.append(_violation("missing_total", "Grand total is missing"))

    if not _val(invoice.invoice_date):
        violations.append(_violation("missing_invoice_date", "Invoice date is missing"))
    elif invoice_date is None:
        violations.append(_violation("invalid_invoice_date", "Invoice date could not be parsed"))
    elif invoice_date > date.today():
        violations.append(_violation("future_invoice_date", "Invoice date is in the future"))

    if _val(invoice.due_date) and due_date is None:
        violations.append(_violation("invalid_due_date", "Due date could not be parsed"))

    if subtotal is not None and subtotal < 0:
        violations.append(_violation("negative_subtotal", "Subtotal is negative"))
    if tax is not None and tax < 0:
        violations.append(_violation("negative_tax", "Tax is negative"))
    if grand_total is not None and grand_total < 0:
        violations.append(_violation("negative_total", "Grand total is negative"))

    if gst and not GST_PATTERN.match(gst):
        violations.append(_violation("invalid_gst", "GST number format is invalid"))

    if currency and currency.upper() not in VALID_CURRENCIES:
        violations.append(_violation("invalid_currency", f"Unrecognized currency: {currency}"))

    if not po_number:
        warnings.append("Purchase order number is missing")

    if grand_total is not None and grand_total > get_settings().high_value_threshold:
        warnings.append("Invoice exceeds configured high-value threshold")

    if subtotal and tax is not None and subtotal > 0 and tax / subtotal > MAX_REASONABLE_TAX_RATE:
        violations.append(
            _violation("unreasonable_tax_rate", "Tax exceeds a reasonable percentage of subtotal")
        )

    if None not in (subtotal, tax, grand_total):
        expected_total = subtotal + tax - (discount or 0)
        if abs(expected_total - grand_total) > TOTAL_TOLERANCE:
            violations.append(
                _violation(
                    "inconsistent_totals",
                    f"Grand total ({grand_total}) does not match subtotal + tax - discount "
                    f"({expected_total:.2f})",
                )
            )

    duplicates = _check_duplicates(vendor, invoice_number, grand_total, invoice_date, file_hash)
    for dup in duplicates:
        violations.append(_violation("duplicate_invoice", dup["reason"], meta=dup))

    return ValidationReport(
        passed=len(violations) == 0,
        violations=violations,
        warnings=warnings,
        duplicate_matches=duplicates,
    )


def _check_duplicates(
    vendor: Optional[str],
    invoice_number: Optional[str],
    grand_total: Optional[float],
    invoice_date: Optional[date],
    file_hash: Optional[str],
) -> list[dict]:
    results: list[dict] = []
    try:
        if vendor and invoice_number:
            match = crud.find_duplicate(vendor, invoice_number)
            if match:
                results.append(
                    {
                        "type": "invoice_number",
                        "reason": "Same vendor + invoice number already exists",
                        "invoice_id": match["id"],
                    }
                )
        if file_hash:
            match = crud.find_by_hash(file_hash)
            if match:
                results.append(
                    {
                        "type": "file_hash",
                        "reason": "Identical file already processed",
                        "invoice_id": match["id"],
                    }
                )
        if vendor and grand_total is not None and invoice_date:
            for m in crud.find_similar(vendor, grand_total, invoice_date):
                results.append(
                    {
                        "type": "vendor_amount_date",
                        "reason": "Same vendor, amount, and date as an existing invoice",
                        "invoice_id": m["id"],
                    }
                )
    except Exception as exc:  # noqa: BLE001 - DB unavailable shouldn't crash validation
        results.append({"type": "duplicate_check_error", "reason": f"Duplicate check failed: {exc}"})
    return results


def _val(field: FieldExtraction) -> Optional[str]:
    return field.value if field and field.value else None


def _violation(code: str, message: str, meta: Optional[dict] = None) -> RuleViolation:
    return RuleViolation(code=code, message=message, meta=meta)
