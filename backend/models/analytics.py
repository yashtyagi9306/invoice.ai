from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    total_invoices: int
    total_spend: float
    avg_invoice_amount: float
    vendor_count: int
    avg_risk_score: float
    approved_count: int
    flagged_count: int
    rejected_count: int
    failed_count: int
    validation_failure_count: int
    manual_review_count: int
    duplicate_invoice_count: int
    avg_processing_time_ms: float
    processing_success_rate: float


class VendorMetric(BaseModel):
    vendor: str
    invoice_count: int
    total_spend: float
    avg_invoice_size: float
    avg_risk_score: float
    high_risk_invoices: int


class RiskBucket(BaseModel):
    risk_bucket: str
    invoice_count: int


class RuleViolationFrequency(BaseModel):
    violation: str
    occurrences: int


class RiskMetrics(BaseModel):
    distribution: list[RiskBucket]
    avg_risk_score: float
    low_risk_pct: float
    medium_risk_pct: float
    high_risk_pct: float
    top_violations: list[RuleViolationFrequency]


class CurrencyMetric(BaseModel):
    currency: str
    invoice_count: int
    total_spend: float


class TrendPoint(BaseModel):
    period: str
    invoice_count: int
    total_spend: float
    total_tax: float
    total_discount: float


class FinancialMetrics(BaseModel):
    currency_distribution: list[CurrencyMetric]
    trends: list[TrendPoint]
