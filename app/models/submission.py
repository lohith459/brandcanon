from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class DemoRole(str, Enum):
    CREATOR = "Creator"
    MANAGER = "Manager"
    COMPLIANCE = "Compliance Reviewer"
    ADMIN = "Admin"

class SubmissionStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    REJECTED = "rejected"

class RiskTier(str, Enum):
    TIER_1 = "Tier 1"  # Low risk (only low/medium findings)
    TIER_2 = "Tier 2"  # Medium risk (any high severity finding)
    TIER_3 = "Tier 3"  # Critical compliance risk (requires Compliance Reviewer sign-off)

class FindingKind(str, Enum):
    RULE = "rule"
    TERM = "term"
    FACT_CONTRADICTED = "fact_contradicted"
    FACT_OUTDATED = "fact_outdated"
    CLAIM_UNSUPPORTED = "claim_unsupported"
    TONE = "tone"
    ACCESSIBILITY = "accessibility"

class FindingDecision(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    DISMISSED = "dismissed"

class FindingSource(str, Enum):
    DETERMINISTIC = "deterministic"
    AI = "ai"

class Submission(SQLModel, table=True):
    __tablename__ = "submissions"
    
    id: str = Field(primary_key=True)
    title: str
    channel: str = "web"
    audience: str = "general"
    intent_message: str = ""
    intent_cta: str = ""
    risk_tier: str = Field(default=RiskTier.TIER_1.value, index=True)
    status: str = Field(default=SubmissionStatus.DRAFT.value, index=True)
    created_by_role: str = Field(default=DemoRole.CREATOR.value)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class Version(SQLModel, table=True):
    __tablename__ = "versions"
    
    id: str = Field(primary_key=True)
    submission_id: str = Field(foreign_key="submissions.id", index=True)
    number: int = Field(default=1)
    text: str
    created_at: datetime = Field(default_factory=utc_now)

class Finding(SQLModel, table=True):
    __tablename__ = "findings"
    
    id: str = Field(primary_key=True)
    version_id: str = Field(foreign_key="versions.id", index=True)
    rule_id: Optional[str] = Field(default=None, index=True)
    fact_id: Optional[str] = Field(default=None, index=True)
    span_start: int = 0
    span_end: int = 0
    quoted_text: str = ""
    severity: str = Field(default="medium", index=True)
    kind: str = Field(default=FindingKind.RULE.value, index=True)
    explanation: str
    suggested_fix: Optional[str] = None
    confidence: float = 1.0
    source: str = Field(default=FindingSource.DETERMINISTIC.value)
    decision: str = Field(default=FindingDecision.PENDING.value, index=True)
    decision_reason: Optional[str] = None

class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    
    id: str = Field(primary_key=True)
    submission_id: str = Field(foreign_key="submissions.id", index=True)
    role: str
    text: str
    created_at: datetime = Field(default_factory=utc_now)

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    
    id: str = Field(primary_key=True)
    submission_id: str = Field(foreign_key="submissions.id", index=True)
    actor_role: str
    action: str  # created, reviewed, fix_applied, submitted_for_approval, approved, changes_requested, rejected, finding_decision
    detail: str = ""
    created_at: datetime = Field(default_factory=utc_now)
