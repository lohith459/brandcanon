from typing import List, Tuple
from app.models.submission import Finding

def apply_accepted_fixes(
    original_text: str,
    accepted_findings: List[Finding]
) -> Tuple[str, int, int]:
    """
    Applies fixes from accepted findings:
    - User Requirement 4: Applies from end of text backwards to preserve earlier offsets.
    - Safely detects and skips overlapping spans to prevent corrupting text.
    - Handles missing elements (empty quoted_text, anchored to full text) by cleanly appending to end.
    
    Returns:
        (transformed_text, applied_count, skipped_overlap_count)
    """
    if not accepted_findings:
        return original_text, 0, 0

    # Separate missing-element findings (anchored to whole text) from span replacements
    whole_text_append_fixes: List[str] = []
    span_findings: List[Finding] = []

    for f in accepted_findings:
        if not f.suggested_fix:
            continue
        if not f.quoted_text and f.span_start == 0 and f.span_end == len(original_text):
            whole_text_append_fixes.append(f.suggested_fix)
        else:
            span_findings.append(f)

    # Sort span findings backwards by span_start descending
    # If equal span_start, sort by span_end descending
    span_findings.sort(key=lambda x: (x.span_start, x.span_end), reverse=True)

    result_text = original_text
    applied_count = 0
    skipped_overlap = 0
    last_modified_start = float("inf")

    for f in span_findings:
        # Check for overlap with already replaced segment
        if f.span_end > last_modified_start:
            # Overlapping span detected: skip to guarantee safe non-corrupting edit
            skipped_overlap += 1
            continue

        start = max(0, f.span_start)
        end = min(len(result_text), f.span_end)
        fix = f.suggested_fix or ""

        # Perform replacement
        result_text = result_text[:start] + fix + result_text[end:]
        last_modified_start = start
        applied_count += 1

    # Apply whole text appends (e.g. missing disclaimers)
    for append_fix in whole_text_append_fixes:
        clean_fix = append_fix.strip()
        if clean_fix not in result_text:
            result_text = result_text.rstrip() + "\n\n" + clean_fix
            applied_count += 1

    return result_text, applied_count, skipped_overlap
