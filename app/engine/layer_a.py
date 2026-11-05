import re
import uuid
from typing import List, Optional, Tuple
from sqlmodel import Session, select

from app.models.canon import Rule, Fact, Term, Severity
from app.models.submission import Finding, FindingKind, FindingSource, FindingDecision

# Standard financial and technical acronyms exempt from ALL-CAPS tone checks
ACRONYM_WHITELIST = {
    "SEC", "RIA", "AUM", "CTA", "SLA", "Q1", "Q2", "Q3", "Q4",
    "URL", "API", "HTML", "CSS", "UI", "ID", "USD", "INR", "EUR", "GBP"
}

def clean_numeric_str(val: str) -> Optional[float]:
    """Parse numeric values from strings like '50,000', '12%', '38400', '145M'."""
    val = val.strip().replace(",", "").replace("+", "").replace("%", "")
    multiplier = 1.0
    if val.endswith("k") or val.endswith("K"):
        multiplier = 1_000.0
        val = val[:-1]
    elif val.endswith("m") or val.endswith("M"):
        multiplier = 1_000_000.0
        val = val[:-1]
    elif val.endswith("b") or val.endswith("B"):
        multiplier = 1_000_000_000.0
        val = val[:-1]
    try:
        return float(val) * multiplier
    except ValueError:
        return None

def check_terminology(text: str, session: Session, version_id: str) -> List[Finding]:
    """Scans text for forbidden terminology and maps to preferred brand terms."""
    findings: List[Finding] = []
    terms = session.exec(select(Term)).all()
    
    for term in terms:
        for forbidden in term.forbidden:
            if not forbidden:
                continue
            # Match whole phrase or word boundary
            escaped = re.escape(forbidden)
            pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
            for m in pattern.finditer(text):
                matched = m.group(0)
                findings.append(Finding(
                    id=f"fnd-{uuid.uuid4().hex[:10]}",
                    version_id=version_id,
                    rule_id=term.id if term.id.startswith("TRM") else "TRM-011",
                    fact_id=None,
                    span_start=m.start(),
                    span_end=m.end(),
                    quoted_text=matched,
                    severity=Severity.MEDIUM.value,
                    kind=FindingKind.TERM.value,
                    explanation=f"'{matched}' is a deprecated or forbidden term. Use approved brand term '{term.preferred}'. {term.note}".strip(),
                    suggested_fix=term.preferred,
                    confidence=1.0,
                    source=FindingSource.DETERMINISTIC.value,
                    decision=FindingDecision.PENDING.value
                ))
    return findings

def check_rule_patterns(text: str, session: Session, version_id: str) -> List[Finding]:
    """Evaluates active rules with configured regex patterns."""
    findings: List[Finding] = []
    rules = session.exec(select(Rule).where(Rule.active == True)).all()
    
    for rule in rules:
        if not rule.pattern:
            continue
        try:
            pattern = re.compile(rule.pattern, re.IGNORECASE)
        except re.error:
            continue
            
        for m in pattern.finditer(text):
            matched = m.group(0)
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id=rule.id,
                fact_id=None,
                span_start=m.start(),
                span_end=m.end(),
                quoted_text=matched,
                severity=rule.severity,
                kind=FindingKind.RULE.value,
                explanation=f"{rule.text} (Violation: '{matched}')",
                suggested_fix=rule.fix_hint or rule.good_example or None,
                confidence=1.0,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))
    return findings

def check_facts_and_claims(text: str, session: Session, version_id: str) -> List[Finding]:
    """
    Extracts numeric claims in text and links them to brand facts via Fact.keywords.
    Flags contradicted numbers and expired facts.
    """
    findings: List[Finding] = []
    facts = session.exec(select(Fact)).all()
    
    # Pattern to find numbers and their immediate surrounding context
    # Matches e.g. "50,000+ investors", "145M AUM", "25 brokerages"
    num_pattern = re.compile(r"(\b\d[\d,]*(?:\.\d+)?(?:\s*[+%kKmMbB])?)\s+([a-zA-Z\s_-]{2,30})\b")
    
    for m in num_pattern.finditer(text):
        full_match = m.group(0)
        num_str = m.group(1)
        trailing_text = m.group(2).lower()
        claimed_val = clean_numeric_str(num_str)
        if claimed_val is None:
            continue
            
        # Match against facts using keywords
        for fact in facts:
            fact_num = clean_numeric_str(fact.value)
            if fact_num is None:
                continue
                
            # Check if any keyword appears in the context or trailing words
            matched_keyword = None
            for kw in fact.keywords:
                if kw.lower() in trailing_text or kw.lower() in text.lower():
                    # Prioritize match if keyword is near the number
                    if kw.lower() in trailing_text:
                        matched_keyword = kw
                        break
            
            if matched_keyword:
                # Check for numerical contradiction (e.g. 50,000 claimed vs 38,400 approved)
                if claimed_val > fact_num:
                    findings.append(Finding(
                        id=f"fnd-{uuid.uuid4().hex[:10]}",
                        version_id=version_id,
                        rule_id=None,
                        fact_id=fact.id,
                        span_start=m.start(),
                        span_end=m.end(),
                        quoted_text=full_match,
                        severity=Severity.HIGH.value,
                        kind=FindingKind.FACT_CONTRADICTED.value,
                        explanation=f"Claimed number '{num_str}' contradicts approved Fact {fact.id} ('{fact.claim}'). Approved ceiling is {fact.value}.",
                        suggested_fix=f"{fact.value} {matched_keyword}",
                        confidence=0.95,
                        source=FindingSource.DETERMINISTIC.value,
                        decision=FindingDecision.PENDING.value
                    ))
                
                # Check for expired fact citation
                if fact.is_expired():
                    findings.append(Finding(
                        id=f"fnd-{uuid.uuid4().hex[:10]}",
                        version_id=version_id,
                        rule_id=None,
                        fact_id=fact.id,
                        span_start=m.start(),
                        span_end=m.end(),
                        quoted_text=full_match,
                        severity=Severity.HIGH.value,
                        kind=FindingKind.FACT_OUTDATED.value,
                        explanation=f"Metric references Fact {fact.id} which expired on {fact.expires_on}. Current metrics must be re-verified.",
                        suggested_fix=None,
                        confidence=0.90,
                        source=FindingSource.DETERMINISTIC.value,
                        decision=FindingDecision.PENDING.value
                    ))
    
    # Also check specific qualitative facts (like F-022 free tier basic tracking scope)
    f_022 = session.get(Fact, "F-022")
    if f_022:
        free_pattern = re.compile(r"(?i)\b(free\s+forever|unlimited\s+free)\b")
        for m in free_pattern.finditer(text):
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id="MSG-001",
                fact_id="F-022",
                span_start=m.start(),
                span_end=m.end(),
                quoted_text=m.group(0),
                severity=Severity.HIGH.value,
                kind=FindingKind.CLAIM_UNSUPPORTED.value,
                explanation=f"'{m.group(0)}' contradicts Fact F-022: FinEdge free tier is scoped to basic tracking only.",
                suggested_fix="Free basic tracking",
                confidence=1.0,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))
            
    return findings

def check_required_disclaimers(text: str, session: Session, version_id: str) -> List[Finding]:
    """
    Checks for required statutory disclaimers (e.g. DISC-002: 'Investments are subject to market risks.').
    If missing, anchors finding to the whole text [0, len(text)] with empty quoted_text.
    """
    findings: List[Finding] = []
    
    # Triggers when post mentions returns or investing
    investment_trigger = re.search(r"(?i)\b(returns?|invest(?:ing|ors?|ments?)?|yields?|portfolio)\b", text)
    if investment_trigger:
        disclaimer_text = "Investments are subject to market risks."
        if disclaimer_text.lower() not in text.lower():
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id="DISC-002",
                fact_id=None,
                span_start=0,
                span_end=len(text),
                quoted_text="",  # Empty quoted text for missing elements
                severity=Severity.HIGH.value,
                kind=FindingKind.RULE.value,
                explanation="Missing mandatory compliance disclaimer: 'Investments are subject to market risks.' required on any investment or returns content.",
                suggested_fix=f"\n\n{disclaimer_text}",
                confidence=1.0,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))
    return findings

def check_tone(text: str, session: Session, version_id: str) -> List[Finding]:
    """
    Checks tone guidelines:
    - TON-003: at most one exclamation mark per post
    - TON-003: no ALL-CAPS emphasis
    - TON-002: sentence length under 35 words
    """
    findings: List[Finding] = []
    
    # 1. Exclamation marks count
    excl_matches = list(re.finditer(r"!+", text))
    total_excl = sum(len(m.group(0)) for m in excl_matches)
    if total_excl > 1:
        for m in excl_matches:
            if len(m.group(0)) > 1:
                findings.append(Finding(
                    id=f"fnd-{uuid.uuid4().hex[:10]}",
                    version_id=version_id,
                    rule_id="TON-003",
                    fact_id=None,
                    span_start=m.start(),
                    span_end=m.end(),
                    quoted_text=m.group(0),
                    severity=Severity.MEDIUM.value,
                    kind=FindingKind.TONE.value,
                    explanation="Multiple consecutive exclamation marks violate professional tone rule TON-003.",
                    suggested_fix=".",
                    confidence=1.0,
                    source=FindingSource.DETERMINISTIC.value,
                    decision=FindingDecision.PENDING.value
                ))
            elif total_excl > 1 and m == excl_matches[-1]:
                # Flag the excessive exclamation
                findings.append(Finding(
                    id=f"fnd-{uuid.uuid4().hex[:10]}",
                    version_id=version_id,
                    rule_id="TON-003",
                    fact_id=None,
                    span_start=m.start(),
                    span_end=m.end(),
                    quoted_text=m.group(0),
                    severity=Severity.MEDIUM.value,
                    kind=FindingKind.TONE.value,
                    explanation="Post contains more than one exclamation mark, violating TON-003.",
                    suggested_fix=".",
                    confidence=0.95,
                    source=FindingSource.DETERMINISTIC.value,
                    decision=FindingDecision.PENDING.value
                ))

    # 2. ALL-CAPS words check
    for m in re.finditer(r"\b[A-Z]{3,}\b", text):
        word = m.group(0)
        if word not in ACRONYM_WHITELIST:
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id="TON-003",
                fact_id=None,
                span_start=m.start(),
                span_end=m.end(),
                quoted_text=word,
                severity=Severity.MEDIUM.value,
                kind=FindingKind.TONE.value,
                explanation=f"ALL-CAPS emphasis '{word}' violates professional brand tone rule TON-003.",
                suggested_fix=word.lower(),
                confidence=1.0,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))
            
    # 3. Sentence length check (TON-002: > 35 words)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    offset = 0
    for s in sentences:
        words = s.split()
        if len(words) > 35:
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id="TON-002",
                fact_id=None,
                span_start=offset,
                span_end=offset + len(s),
                quoted_text=s[:60] + "...",
                severity=Severity.LOW.value,
                kind=FindingKind.TONE.value,
                explanation=f"Sentence length ({len(words)} words) exceeds recommended 35-word limit for readability.",
                suggested_fix="Consider breaking this compound sentence into shorter statements.",
                confidence=0.90,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))
        offset += len(s) + 1

    return findings

def check_accessibility(text: str, session: Session, version_id: str) -> List[Finding]:
    """
    Checks accessibility standards:
    - ACC-001: <img> elements missing descriptive alt text in HTML or Markdown.
    """
    findings: List[Finding] = []
    
    # HTML <img> tags
    for m in re.finditer(r"<img\b([^>]*)>", text, re.IGNORECASE):
        tag_content = m.group(1)
        alt_match = re.search(r'alt=["\'](.*?)["\']', tag_content, re.IGNORECASE)
        if not alt_match or not alt_match.group(1).strip():
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id="ACC-001",
                fact_id=None,
                span_start=m.start(),
                span_end=m.end(),
                quoted_text=m.group(0),
                severity=Severity.MEDIUM.value,
                kind=FindingKind.ACCESSIBILITY.value,
                explanation="Image tag is missing descriptive alt text attribute required by WCAG AA standard ACC-001.",
                suggested_fix="<img alt=\"Descriptive chart summary\" ...>",
                confidence=1.0,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))

    # Markdown images: ![alt](url)
    for m in re.finditer(r"!\[(.*?)\]\((.*?)\)", text):
        alt_text = m.group(1).strip()
        if not alt_text:
            findings.append(Finding(
                id=f"fnd-{uuid.uuid4().hex[:10]}",
                version_id=version_id,
                rule_id="ACC-001",
                fact_id=None,
                span_start=m.start(),
                span_end=m.end(),
                quoted_text=m.group(0),
                severity=Severity.MEDIUM.value,
                kind=FindingKind.ACCESSIBILITY.value,
                explanation="Markdown image syntax has empty alt text bracket ![].",
                suggested_fix="![Descriptive graphic caption](...)",
                confidence=1.0,
                source=FindingSource.DETERMINISTIC.value,
                decision=FindingDecision.PENDING.value
            ))

    return findings

def run_layer_a_checks(text: str, session: Session, version_id: str) -> List[Finding]:
    """Runs all Layer A deterministic checks in sequence and returns aggregated findings."""
    all_findings: List[Finding] = []
    all_findings.extend(check_terminology(text, session, version_id))
    all_findings.extend(check_rule_patterns(text, session, version_id))
    all_findings.extend(check_facts_and_claims(text, session, version_id))
    all_findings.extend(check_required_disclaimers(text, session, version_id))
    all_findings.extend(check_tone(text, session, version_id))
    all_findings.extend(check_accessibility(text, session, version_id))
    return all_findings
