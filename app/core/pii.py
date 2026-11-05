import re
from typing import Tuple

# Robust regex patterns for emails and international/domestic phone numbers
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|"  # standard 10-digit
    r"\b(?:\+91|0)?[6-9]\d{9}\b"                                      # Indian 10-digit mobile
)

def redact_pii(text: str) -> Tuple[str, int]:
    """
    Redacts personal identifiable information (emails, phone numbers)
    from draft text before sending to any external AI provider.
    
    Returns:
        (redacted_text, count_of_redactions)
    """
    redaction_count = 0

    def email_repl(match):
        nonlocal redaction_count
        redaction_count += 1
        return "[REDACTED_EMAIL]"

    def phone_repl(match):
        nonlocal redaction_count
        redaction_count += 1
        return "[REDACTED_PHONE]"

    redacted = EMAIL_REGEX.sub(email_repl, text)
    redacted = PHONE_REGEX.sub(phone_repl, redacted)

    return redacted, redaction_count
