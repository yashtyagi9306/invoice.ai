from typing import Optional

from pydantic import BaseModel, Field


class RuleViolation(BaseModel):
    code: str
    message: str
    meta: Optional[dict] = None


class ValidationReport(BaseModel):
    passed: bool
    violations: list[RuleViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duplicate_matches: list[dict] = Field(default_factory=list)
