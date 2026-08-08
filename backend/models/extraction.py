from typing import Optional

from pydantic import BaseModel, Field


class FieldExtraction(BaseModel):
    value: Optional[str] = None
    confidence: float = Field(ge=0, le=1)


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[str] = None
    unit_price: Optional[str] = None
    amount: Optional[str] = None


class InvoiceExtraction(BaseModel):
    vendor_name: FieldExtraction
    vendor_address: FieldExtraction
    invoice_number: FieldExtraction
    invoice_date: FieldExtraction
    due_date: FieldExtraction
    purchase_order_number: FieldExtraction
    gst_number: FieldExtraction
    currency: FieldExtraction
    subtotal: FieldExtraction
    tax: FieldExtraction
    discount: FieldExtraction
    grand_total: FieldExtraction
    payment_terms: FieldExtraction
    email_address: FieldExtraction
    phone_number: FieldExtraction
    invoice_reference: FieldExtraction
    line_items: list[LineItem] = Field(default_factory=list)
