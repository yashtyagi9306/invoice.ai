from datetime import date
from typing import Any, Optional

from backend.database.connection import get_supabase
from backend.models.invoice import InvoiceCreate

TABLE = "invoices"


def create_invoice(invoice: InvoiceCreate) -> dict[str, Any]:
    payload = invoice.model_dump(mode="json")
    result = get_supabase().table(TABLE).insert(payload).execute()
    return result.data[0]


def get_invoice(invoice_id: str) -> Optional[dict[str, Any]]:
    result = get_supabase().table(TABLE).select("*").eq("id", invoice_id).execute()
    return result.data[0] if result.data else None


def list_invoices(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    result = (
        get_supabase()
        .table(TABLE)
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


def update_invoice(invoice_id: str, data: dict[str, Any]) -> dict[str, Any]:
    result = get_supabase().table(TABLE).update(data).eq("id", invoice_id).execute()
    return result.data[0]


def find_duplicate(vendor: str, invoice_number: str) -> Optional[dict[str, Any]]:
    result = (
        get_supabase()
        .table(TABLE)
        .select("*")
        .eq("vendor", vendor)
        .eq("invoice_number", invoice_number)
        .execute()
    )
    return result.data[0] if result.data else None


def find_by_hash(file_hash: str) -> Optional[dict[str, Any]]:
    result = get_supabase().table(TABLE).select("*").eq("file_hash", file_hash).execute()
    return result.data[0] if result.data else None


def find_similar(vendor: str, grand_total: float, invoice_date: date, tolerance: float = 0.01) -> list[dict[str, Any]]:
    result = (
        get_supabase()
        .table(TABLE)
        .select("*")
        .eq("vendor", vendor)
        .eq("invoice_date", invoice_date.isoformat())
        .execute()
    )
    return [
        row
        for row in result.data
        if row.get("grand_total") is not None and abs(float(row["grand_total"]) - grand_total) <= tolerance
    ]
