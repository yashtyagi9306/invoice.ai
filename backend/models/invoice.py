from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FLAGGED = "flagged"
    REJECTED = "rejected"
    FAILED = "failed"


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceBase(BaseModel):
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    gst_number: Optional[str] = None
    purchase_order: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    discount: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)


class InvoiceCreate(InvoiceBase):
    attachment_path: Optional[str] = None
    file_hash: Optional[str] = None
    rule_violations: list[str] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    ai_summary: Optional[str] = None
    risk_score: Optional[int] = None
    risk_reason: Optional[str] = None
    suggested_action: Optional[str] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING


class InvoiceInDB(InvoiceCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
