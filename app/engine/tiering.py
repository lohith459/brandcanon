from typing import List
from app.models.canon import Severity
from app.models.submission import Finding, RiskTier

def calculate_risk_tier(findings: List[Finding]) -> str:
    """
    Computes risk tier based on finding severities:
    - Tier 3: Any critical finding (e.g. CMP-004 guaranteed returns).
              Requires Compliance Reviewer sign-off before approval.
    - Tier 2: Any high finding (e.g. DISC-002 missing disclaimer, Fact contradiction).
    - Tier 1: Low risk (only medium or low findings, or zero findings).
    """
    has_critical = any(f.severity == Severity.CRITICAL.value for f in findings)
    if has_critical:
        return RiskTier.TIER_3.value
        
    has_high = any(f.severity == Severity.HIGH.value for f in findings)
    if has_high:
        return RiskTier.TIER_2.value
        
    return RiskTier.TIER_1.value
