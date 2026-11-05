from typing import List, Tuple
from sqlmodel import Session
from app.models.canon import Rule, Fact
from app.models.submission import Finding

def verify_and_ground_findings(
    findings: List[Finding],
    text: str,
    session: Session
) -> Tuple[List[Finding], int]:
    """
    Layer D: Evidence-or-Silence Verifier.
    
    Drops any finding that:
    1. Does not cite an existing rule_id or fact_id in the Brand Canon database.
    2. Has quoted_text that cannot be verified in the draft text.
    
    Special case (User Requirement 3):
    Findings for missing required elements (e.g. missing disclaimer) have empty quoted_text ("").
    These are anchored to the whole text [0, len(text)] and pass if they cite a valid rule_id.
    
    Returns:
        (verified_findings, dropped_count)
    """
    verified: List[Finding] = []
    dropped_count = 0
    seen_spans = set()
    
    for f in findings:
        # 1. Evidence Citation Check: Must cite a valid Rule or Fact
        has_valid_citation = False
        if f.rule_id:
            rule = session.get(Rule, f.rule_id)
            if rule is not None:
                has_valid_citation = True
        if not has_valid_citation and f.fact_id:
            fact = session.get(Fact, f.fact_id)
            if fact is not None:
                has_valid_citation = True
                
        if not has_valid_citation:
            dropped_count += 1
            continue

        # 2. Quoted Text Grounding Check
        if not f.quoted_text:
            # Missing element check: Must be anchored to full text with valid rule
            if f.span_start == 0 and f.span_end == len(text) and f.rule_id:
                # Valid missing element finding
                pass
            else:
                dropped_count += 1
                continue
        else:
            # Finding has quoted text: Verify it exists in the draft
            if f.quoted_text not in text:
                dropped_count += 1
                continue
                
            # Check span accuracy: If text at [span_start:span_end] doesn't match quoted_text,
            # safely recalibrate span_start and span_end to actual text location
            actual_span_text = text[f.span_start:f.span_end]
            if actual_span_text != f.quoted_text:
                found_idx = text.find(f.quoted_text)
                if found_idx != -1:
                    f.span_start = found_idx
                    f.span_end = found_idx + len(f.quoted_text)
                else:
                    dropped_count += 1
                    continue

        # 3. Deduplication: Avoid duplicate findings for exact same span and rule/fact
        key = (f.span_start, f.span_end, f.rule_id or f.fact_id, f.kind)
        if key in seen_spans:
            dropped_count += 1
            continue
            
        seen_spans.add(key)
        verified.append(f)

    return verified, dropped_count
