from sqlmodel import Session, select
from app.core.pii import redact_pii
from app.engine.retrieval import retrieve_top_k_canon
from app.engine.layer_b import run_layer_b_review, GeminiProviderAdapter, AIFindingSchema
from app.models.canon import Rule, Fact
from app.engine.layer_d import verify_and_ground_findings
from app.models.submission import Finding

def test_pii_redaction():
    """Confirms emails and phone numbers are stripped before external AI calls."""
    raw_text = "Contact our lead advisor at sarah.connor@finedge.com or call +1-415-555-0199 for VIP onboarding."
    redacted, count = redact_pii(raw_text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "sarah.connor@finedge.com" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "+1-415-555-0199" not in redacted
    assert count == 2

def test_bm25_retrieval(session: Session):
    """Verifies BM25 ranks relevant rules and facts given a query draft."""
    all_rules = session.exec(select(Rule)).all()
    all_facts = session.exec(select(Fact)).all()
    
    query = "Guaranteed returns for 50,000 investors on our new app"
    top_rules, top_facts = retrieve_top_k_canon(query, all_rules, all_facts, k=3)
    
    assert len(top_rules) > 0
    # Guaranteed returns should pull CMP-004 to top
    rule_ids = [r.id for r in top_rules]
    assert "CMP-004" in rule_ids
    
    assert len(top_facts) > 0
    fact_ids = [f.id for f in top_facts]
    # Investors/users should pull F-017 to top
    assert "F-017" in fact_ids

def test_confidential_mode_suppresses_external_ai(session: Session):
    """Confidential mode guarantees zero outbound LLM calls."""
    draft = "Confidential pre-launch internal draft."
    findings, notice = run_layer_b_review(draft, session, version_id="ver-conf", confidential_mode=True)
    assert len(findings) == 0
    assert "Confidential Mode active" in notice

def test_offline_fallback_when_no_api_keys(session: Session):
    """When no API keys are present, gracefully returns offline notice without error."""
    draft = "Start your wealth journey with FinEdge Plus."
    findings, notice = run_layer_b_review(draft, session, version_id="ver-off", confidential_mode=False)
    # Since neither GEMINI_API_KEY nor ANTHROPIC_API_KEY is configured in test env
    assert len(findings) == 0
    assert "Offline Mode" in notice or "100% deterministic" in notice

def test_ai_findings_must_pass_verifier_grounding(session: Session):
    """Even if an AI provider hallucinates a rule ID, Layer D Verifier drops it."""
    text = "Join our community today."
    fake_ai_finding = Finding(
        id="fnd-ai-hallucinated",
        version_id="v1",
        rule_id="NONEXISTENT-RULE-999",
        quoted_text="community",
        span_start=text.find("community"),
        span_end=text.find("community") + len("community"),
        severity="high",
        explanation="Hallucinated rule from AI."
    )
    verified, dropped = verify_and_ground_findings([fake_ai_finding], text, session)
    assert len(verified) == 0
    assert dropped == 1
