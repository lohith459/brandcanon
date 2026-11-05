from datetime import date
from enum import Enum
from typing import List, Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON

class RuleCategory(str, Enum):
    TONE = "tone"
    TERMINOLOGY = "terminology"
    MESSAGING = "messaging"
    VISUAL = "visual"
    ACCESSIBILITY = "accessibility"
    COMPLIANCE = "compliance"

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AssetType(str, Enum):
    COLOR = "color"
    LOGO = "logo"
    FONT = "font"

class Rule(SQLModel, table=True):
    __tablename__ = "rules"
    
    id: str = Field(primary_key=True)
    category: str = Field(index=True)  # RuleCategory
    text: str
    severity: str = Field(index=True)  # Severity
    good_example: str = ""
    bad_example: str = ""
    pattern: Optional[str] = None  # optional regex pattern
    fix_hint: Optional[str] = None
    active: bool = Field(default=True, index=True)

class Fact(SQLModel, table=True):
    __tablename__ = "facts"
    
    id: str = Field(primary_key=True)
    claim: str
    value: str
    keywords: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    evidence_url: str = ""
    owner: str = ""
    valid_from: str = ""   # YYYY-MM-DD
    expires_on: str = ""   # YYYY-MM-DD
    
    def is_expired(self, current_date: Optional[date] = None) -> bool:
        if not self.expires_on:
            return False
        ref = current_date or date.today()
        try:
            exp = date.fromisoformat(self.expires_on)
            return ref > exp
        except ValueError:
            return False

class Term(SQLModel, table=True):
    __tablename__ = "terms"
    
    id: str = Field(primary_key=True)
    preferred: str
    forbidden: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    note: str = ""

class Asset(SQLModel, table=True):
    __tablename__ = "assets"
    
    id: str = Field(primary_key=True)
    type: str = Field(index=True)  # AssetType
    name: str
    value: str  # hex color, file path/svg, font family
    usage_rule: str = ""
