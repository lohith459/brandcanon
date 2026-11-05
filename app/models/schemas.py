from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Health Check Schemas
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    ai_mode: str
    rules_count: int
    facts_count: int
    terms_count: int

# WCAG Contrast Schemas
class ContrastRequest(BaseModel):
    foreground_hex: str
    background_hex: str

class ContrastResponse(BaseModel):
    foreground_hex: str
    background_hex: str
    ratio: float
    wcag_aa_normal_pass: bool
    wcag_aa_large_pass: bool
    wcag_aaa_normal_pass: bool
    explanation: str

# Submission & Workflow Schemas
class SubmissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    channel: str = "web"
    audience: str = "general"
    intent_message: Optional[str] = ""
    intent_cta: Optional[str] = ""
    confidential_mode: bool = False

class FindingDecisionRequest(BaseModel):
    decision: str  # "accepted", "edited", "dismissed"
    decision_reason: Optional[str] = None
    edited_fix: Optional[str] = None

class WorkflowActionRequest(BaseModel):
    action: str  # "approved", "changes_requested", "rejected"
    comment: Optional[str] = None

class CommentCreate(BaseModel):
    text: str = Field(min_length=1)

# Canon Schemas
class RuleCreate(BaseModel):
    id: str
    category: str
    text: str
    severity: str
    good_example: Optional[str] = ""
    bad_example: Optional[str] = ""
    pattern: Optional[str] = None
    fix_hint: Optional[str] = None
    active: bool = True

class FactCreate(BaseModel):
    id: str
    claim: str
    value: str
    keywords: List[str] = Field(default_factory=list)
    evidence_url: Optional[str] = ""
    owner: Optional[str] = ""
    valid_from: Optional[str] = ""
    expires_on: Optional[str] = ""

class TermCreate(BaseModel):
    id: str
    preferred: str
    forbidden: List[str] = Field(default_factory=list)
    note: Optional[str] = ""

class AssetCreate(BaseModel):
    id: str
    type: str
    name: str
    value: str
    usage_rule: Optional[str] = ""
