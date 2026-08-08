from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from backend.models.validation import ValidationReport


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SuggestedAction(str, Enum):
    APPROVE = "approve"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"
    NEEDS_MORE_INFO = "needs_more_info"


class RiskAssessment(BaseModel):
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    reasoning: str
    suggested_action: SuggestedAction
    confidence: float = Field(ge=0, le=1)


class OverallStatus(str, Enum):
    APPROVED = "approved"
    FLAGGED = "flagged"
    REJECTED = "rejected"


class UnifiedRiskReport(BaseModel):
    overall_status: OverallStatus
    validation: ValidationReport
    risk_assessment: Optional[RiskAssessment] = None
