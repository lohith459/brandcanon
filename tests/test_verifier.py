from sqlmodel import Session
from app.models.canon import Severity
from app.models.submission import Finding, FindingKind, RiskTier
from app.engine.layer_d import verify_and_ground_findings
from app.engine.tiering import calculate_risk_tier

def test_verifier_drops_ungrounded_and_hallucinated_findings(session: Session):
    text = "Join our community today and explore FinEdge Plus."
    
    findings = [
        # Valid finding: rule_id exists and quoted_text is present
        Finding(
            id="f1",
            version_id="v1",
            rule_id="TRM-011",
            quoted_text="FinEdge Plus",
            span_start=text.find("FinEdge Plus"),
            span_end=text.find("FinEdge Plus") + len("FinEdge Plus"),
            severity="medium",
            explanation="Valid rule citation."
        ),
        # Ungrounded finding: Nonexistent rule_id
        Finding(
            id="f2",
            version_id="v1",
            rule_id="FAKE-999",
            quoted_text="community",
            span_start=text.find("community"),
            span_end=text.find("community") + len("community"),
            severity="low",
            explanation="Hallucinated rule."
        ),
        # Hallucinated text finding: quoted_text not anywhere in draft
        Finding(
            id="f3",
            version_id="v1",
            rule_id="CMP-004",
            quoted_text="100% Guaranteed Bitcoins",
            span_start=0,
            span_end=10,
            severity="critical",
            explanation="Fabricated quote."
        )
    ]
    
    verified, dropped_count = verify_and_ground_findings(findings, text, session)
    assert len(verified) == 1
    assert verified[0].id == "f1"
    assert dropped_count == 2

def test_verifier_accepts_missing_disclaimer_anchored_to_whole_text(session: Session):
    """
    Requirement 3: Findings for missing required elements have no quoted text.
    They anchor to the whole text and must pass with a valid rule_id.
    """
    text = "We offer great portfolio tracking."
    disclaimer_finding = Finding(
        id="f-disc",
        version_id="v1",
        rule_id="DISC-002",
        quoted_text="",
        span_start=0,
        span_end=len(text),
        severity="high",
        explanation="Missing statutory disclaimer."
    )
    
    verified, dropped_count = verify_and_ground_findings([disclaimer_finding], text, session)
    assert len(verified) == 1
    assert verified[0].id == "f-disc"
    assert dropped_count == 0

def test_risk_tiering_logic():
    # 1. Critical finding -> Tier 3
    crit_finding = Finding(
        id="f-crit",
        version_id="v1",
        rule_id="CMP-004",
        severity=Severity.CRITICAL.value,
        explanation="Critical compliance breach."
    )
    assert calculate_risk_tier([crit_finding]) == RiskTier.TIER_3.value
    
    # 2. High finding (no critical) -> Tier 2
    high_finding = Finding(
        id="f-high",
        version_id="v1",
        rule_id="DISC-002",
        severity=Severity.HIGH.value,
        explanation="High severity disclaimer missing."
    )
    assert calculate_risk_tier([high_finding]) == RiskTier.TIER_2.value
    
    # 3. Only medium/low findings -> Tier 1
    med_finding = Finding(
        id="f-med",
        version_id="v1",
        rule_id="TON-003",
        severity=Severity.MEDIUM.value,
        explanation="Tone formatting."
    )
    assert calculate_risk_tier([med_finding]) == RiskTier.TIER_1.value
    assert calculate_risk_tier([]) == RiskTier.TIER_1.value
