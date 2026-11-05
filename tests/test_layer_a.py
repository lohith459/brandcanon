from sqlmodel import Session
from app.engine.layer_a import (
    run_layer_a_checks,
    check_terminology,
    check_rule_patterns,
    check_facts_and_claims,
    check_required_disclaimers,
    check_tone,
    check_accessibility
)
from app.models.submission import FindingKind

def test_bad_worked_example_triggers_expected_findings(session: Session):
    """
    Test the exact worked example from the master prompt:
    'Guaranteed 12% returns!! Join 50,000+ investors on FinEdge Pro. It's FREE forever!'
    """
    bad_draft = "Guaranteed 12% returns!! Join 50,000+ investors on FinEdge Pro. It's FREE forever!"
    findings = run_layer_a_checks(bad_draft, session, version_id="ver-test-01")
    
    # 1. Guaranteed returns (CMP-004)
    cmp_findings = [f for f in findings if f.rule_id == "CMP-004"]
    assert len(cmp_findings) >= 1
    assert "guaranteed" in cmp_findings[0].quoted_text.lower()
    assert cmp_findings[0].severity == "critical"
    
    # 2. Fact contradiction (F-017 via 'investors' keyword: 50,000 > 38,400)
    fact_findings = [f for f in findings if f.fact_id == "F-017"]
    assert len(fact_findings) >= 1
    assert "50,000" in fact_findings[0].quoted_text
    assert fact_findings[0].kind == FindingKind.FACT_CONTRADICTED.value
    
    # 3. Retired terminology (TRM-011: FinEdge Pro -> FinEdge Plus)
    term_findings = [f for f in findings if "FinEdge Pro" in f.quoted_text]
    assert len(term_findings) >= 1
    assert term_findings[0].suggested_fix == "FinEdge Plus"
    
    # 4. Free forever scope / claim unsupported (F-022 / MSG-001)
    free_findings = [f for f in findings if "free forever" in f.quoted_text.lower()]
    assert len(free_findings) >= 1
    
    # 5. Tone violations: Exclamation marks !! and ALL-CAPS FREE (TON-003)
    tone_findings = [f for f in findings if f.rule_id == "TON-003"]
    assert len(tone_findings) >= 2  # at least !! and FREE
    
    # 6. Missing required disclaimer (DISC-002)
    disc_findings = [f for f in findings if f.rule_id == "DISC-002"]
    assert len(disc_findings) == 1
    assert disc_findings[0].quoted_text == ""
    assert disc_findings[0].span_start == 0
    assert disc_findings[0].span_end == len(bad_draft)

def test_clean_draft_has_zero_critical_findings(session: Session):
    """Compliant clean draft should have no critical or high compliance violations."""
    clean_draft = (
        "Disciplined investing starts with systematic rebalancing. "
        "Over 38,000 investors use FinEdge Plus to keep their target asset allocations on track. "
        "Explore how smart portfolios simplify long-term financial health. "
        "Investments are subject to market risks."
    )
    findings = run_layer_a_checks(clean_draft, session, version_id="ver-test-02")
    critical_findings = [f for f in findings if f.severity in ("critical", "high")]
    assert len(critical_findings) == 0

def test_accessibility_missing_alt_detected(session: Session):
    """Verifies that <img> missing alt attribute is flagged under ACC-001."""
    text_with_img = "Take a look at our mobile interface: <img src='app.png'>. It gives you instant overview."
    findings = check_accessibility(text_with_img, session, version_id="ver-test-03")
    assert len(findings) == 1
    assert findings[0].rule_id == "ACC-001"
    assert "<img" in findings[0].quoted_text
