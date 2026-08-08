from backend.database import analytics_repo
from backend.models.analytics import (
    CurrencyMetric,
    FinancialMetrics,
    OverviewMetrics,
    RiskBucket,
    RiskMetrics,
    RuleViolationFrequency,
    TrendPoint,
    VendorMetric,
)

EMPTY_OVERVIEW = {
    "total_invoices": 0,
    "total_spend": 0,
    "avg_invoice_amount": 0,
    "vendor_count": 0,
    "avg_risk_score": 0,
    "approved_count": 0,
    "flagged_count": 0,
    "rejected_count": 0,
    "failed_count": 0,
    "validation_failure_count": 0,
    "manual_review_count": 0,
    "duplicate_invoice_count": 0,
    "avg_processing_time_ms": 0,
    "processing_success_rate": 0,
}


def get_overview() -> OverviewMetrics:
    data = analytics_repo.fetch_overview() or EMPTY_OVERVIEW
    return OverviewMetrics(**data)


def get_vendor_analytics(limit: int = 10) -> list[VendorMetric]:
    return [VendorMetric(**row) for row in analytics_repo.fetch_vendor_summary(limit)]


def get_risk_analytics() -> RiskMetrics:
    distribution = [RiskBucket(**row) for row in analytics_repo.fetch_risk_distribution()]
    total = sum(b.invoice_count for b in distribution) or 1

    def pct(bucket: str) -> float:
        count = next((b.invoice_count for b in distribution if b.risk_bucket == bucket), 0)
        return round(count / total * 100, 2)

    overview = analytics_repo.fetch_overview() or EMPTY_OVERVIEW
    violations = [RuleViolationFrequency(**row) for row in analytics_repo.fetch_rule_violation_frequency()]

    return RiskMetrics(
        distribution=distribution,
        avg_risk_score=overview.get("avg_risk_score", 0),
        low_risk_pct=pct("low"),
        medium_risk_pct=pct("medium"),
        high_risk_pct=pct("high"),
        top_violations=violations,
    )


def get_financial_analytics(granularity: str = "month") -> FinancialMetrics:
    currency = [CurrencyMetric(**row) for row in analytics_repo.fetch_currency_distribution()]
    trends = [TrendPoint(**row) for row in analytics_repo.fetch_trends(granularity)]
    return FinancialMetrics(currency_distribution=currency, trends=trends)


def get_trends(granularity: str = "month") -> list[TrendPoint]:
    return [TrendPoint(**row) for row in analytics_repo.fetch_trends(granularity)]
