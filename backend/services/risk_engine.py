import logging
from typing import Optional

from backend.ai.openai_service import analyze_risk
from backend.config import get_settings
from backend.models.extraction import InvoiceExtraction
from backend.models.risk import OverallStatus, RiskAssessment, UnifiedRiskReport
from backend.models.validation import ValidationReport
from backend.services.rule_engine import validate_invoice

logger = logging.getLogger(__name__)


def build_risk_report(invoice: InvoiceExtraction, file_hash: Optional[str] = None) -> UnifiedRiskReport:
    logger.info("Validation started")
    validation = validate_invoice(invoice, file_hash)
    logger.info("Rule violations: %s", len(validation.violations))
    logger.info("Duplicate matches: %s", len(validation.duplicate_matches))

    if not validation.passed:
        logger.info("Skipping AI risk analysis - deterministic validation failed")
        return UnifiedRiskReport(
            overall_status=OverallStatus.REJECTED, validation=validation, risk_assessment=None
        )

    logger.info("AI risk analysis started")
    try:
        assessment = analyze_risk(invoice, _summarize(validation))
        logger.info("AI risk analysis completed, score=%s", assessment.risk_score)
    except Exception as exc:  # noqa: BLE001 - AI unavailable shouldn't crash the pipeline
        logger.warning("AI risk analysis unavailable: %s", type(exc).__name__)
        return UnifiedRiskReport(
            overall_status=OverallStatus.FLAGGED, validation=validation, risk_assessment=None
        )

    return UnifiedRiskReport(
        overall_status=_resolve_status(assessment), validation=validation, risk_assessment=assessment
    )


def _resolve_status(assessment: RiskAssessment) -> OverallStatus:
    if assessment.suggested_action.value == "reject":
        return OverallStatus.REJECTED
    if assessment.risk_score >= get_settings().risk_score_threshold:
        return OverallStatus.FLAGGED
    if assessment.suggested_action.value == "approve":
        return OverallStatus.APPROVED
    return OverallStatus.FLAGGED


def _summarize(validation: ValidationReport) -> str:
    if not validation.warnings and not validation.duplicate_matches:
        return "No warnings or duplicate matches."
    parts = []
    if validation.warnings:
        parts.append("Warnings: " + "; ".join(validation.warnings))
    if validation.duplicate_matches:
        parts.append(f"Potential duplicates found: {len(validation.duplicate_matches)}")
    return " | ".join(parts)
