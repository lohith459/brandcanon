import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import httpx
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.config import settings
from app.models.canon import Rule, Fact, Severity
from app.models.submission import Finding, FindingKind, FindingSource, FindingDecision
from app.core.pii import redact_pii
from app.engine.retrieval import retrieve_top_k_canon

logger = logging.getLogger(__name__)

class AIFindingSchema(BaseModel):
    rule_id: Optional[str] = None
    fact_id: Optional[str] = None
    quoted_text: str = ""
    explanation: str
    suggested_fix: Optional[str] = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    severity: str = "medium"

class AIReviewResponseSchema(BaseModel):
    findings: List[AIFindingSchema] = Field(default_factory=list)

class AIProviderAdapter(ABC):
    @abstractmethod
    def analyze(self, text: str, rules: List[Rule], facts: List[Fact]) -> List[AIFindingSchema]:
        """Analyzes text against retrieved brand rules and facts."""
        pass

class GeminiProviderAdapter(AIProviderAdapter):
    """Google Gemini REST API implementation using standard httpx."""
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or settings.GEMINI_MODEL
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def analyze(self, text: str, rules: List[Rule], facts: List[Fact]) -> List[AIFindingSchema]:
        prompt = self._build_prompt(text, rules, facts)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(self.url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            validated = AIReviewResponseSchema.model_validate(parsed if isinstance(parsed, dict) else {"findings": parsed})
            return validated.findings

    def _build_prompt(self, text: str, rules: List[Rule], facts: List[Fact]) -> str:
        rules_text = "\n".join([f"- [{r.id}] ({r.severity}) {r.text}" for r in rules])
        facts_text = "\n".join([f"- [{f.id}] {f.claim}: {f.value} (Keywords: {', '.join(f.keywords)})" for f in facts])
        return (
            "You are a strict brand-governance AI reviewer. Analyze the draft text ONLY against the provided rules and facts.\n"
            "Requirements:\n"
            "1. Grounding: You must cite an exact rule_id or fact_id from the provided list. Do not invent citations.\n"
            "2. Quoted text: quoted_text must be an exact substring from the draft text.\n"
            "3. Return strict JSON matching this schema: {\"findings\": [{\"rule_id\": \"...\", \"quoted_text\": \"...\", \"explanation\": \"...\", \"suggested_fix\": \"...\", \"confidence\": 0.9, \"severity\": \"medium\"}]}\n\n"
            f"BRAND RULES:\n{rules_text}\n\n"
            f"BRAND FACTS:\n{facts_text}\n\n"
            f"DRAFT COPY:\n{text}\n"
        )

class AnthropicProviderAdapter(AIProviderAdapter):
    """Anthropic Claude REST API implementation using standard httpx."""
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or settings.ANTHROPIC_MODEL
        self.url = "https://api.anthropic.com/v1/messages"

    def analyze(self, text: str, rules: List[Rule], facts: List[Fact]) -> List[AIFindingSchema]:
        prompt = self._build_prompt(text, rules, facts)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": 1000,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}]
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(self.url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Anthropic API returned HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            raw_text = data["content"][0]["text"]
            # Extract JSON block if wrapped
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw_text)
            validated = AIReviewResponseSchema.model_validate(parsed if isinstance(parsed, dict) else {"findings": parsed})
            return validated.findings

    def _build_prompt(self, text: str, rules: List[Rule], facts: List[Fact]) -> str:
        rules_text = "\n".join([f"- [{r.id}] ({r.severity}) {r.text}" for r in rules])
        facts_text = "\n".join([f"- [{f.id}] {f.claim}: {f.value}" for f in facts])
        return (
            "Analyze the draft text strictly against the provided brand rules and facts. Output ONLY valid JSON matching "
            "{\"findings\": [{\"rule_id\": \"...\", \"quoted_text\": \"...\", \"explanation\": \"...\", \"suggested_fix\": \"...\", \"confidence\": 0.9, \"severity\": \"medium\"}]}.\n\n"
            f"RULES:\n{rules_text}\n\nFACTS:\n{facts_text}\n\nDRAFT:\n{text}"
        )

def get_ai_adapter() -> Optional[AIProviderAdapter]:
    """Returns active AI provider adapter based on configured environment variables."""
    if settings.GEMINI_API_KEY:
        return GeminiProviderAdapter(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    elif settings.ANTHROPIC_API_KEY:
        return AnthropicProviderAdapter(settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_MODEL)
    return None

def run_layer_b_review(
    text: str,
    session: Session,
    version_id: str,
    confidential_mode: bool = False
) -> Tuple[List[Finding], str]:
    """
    Executes optional Layer B AI review:
    1. Checks confidential mode -> suppresses external calls if active.
    2. Performs PII redaction before sending.
    3. Retrieves top-k rules/facts via BM25.
    4. Calls AI adapter with strict JSON output schema.
    5. Graceful fallback on any failure with notice.
    
    Returns:
        (ai_findings, status_notice)
    """
    if confidential_mode:
        return [], "Confidential Mode active: External AI inspection suppressed. 100% deterministic local checks executed."

    adapter = get_ai_adapter()
    if not adapter:
        return [], "Offline Mode: 100% deterministic local rules executed. (No GEMINI_API_KEY or ANTHROPIC_API_KEY configured)."

    # Redact PII before sending
    sanitized_text, redactions = redact_pii(text)

    # BM25 Retrieval of top-k rules and facts
    all_rules = session.exec(select(Rule).where(Rule.active == True)).all()
    all_facts = session.exec(select(Fact)).all()
    context_rules, context_facts = retrieve_top_k_canon(sanitized_text, all_rules, all_facts, k=5)

    try:
        raw_ai_findings = adapter.analyze(sanitized_text, context_rules, context_facts)
        findings: List[Finding] = []
        for af in raw_ai_findings:
            span_start = 0
            span_end = len(text)
            if af.quoted_text and af.quoted_text in text:
                span_start = text.find(af.quoted_text)
                span_end = span_start + len(af.quoted_text)

            findings.append(Finding(
                id=f"fnd-ai-{uuid.uuid4().hex[:8]}",
                version_id=version_id,
                rule_id=af.rule_id,
                fact_id=af.fact_id,
                span_start=span_start,
                span_end=span_end,
                quoted_text=af.quoted_text,
                severity=af.severity or "medium",
                kind=FindingKind.TONE.value if (af.rule_id and "TON" in af.rule_id) else FindingKind.RULE.value,
                explanation=af.explanation,
                suggested_fix=af.suggested_fix,
                confidence=af.confidence or 0.85,
                source=FindingSource.AI.value,
                decision=FindingDecision.PENDING.value
            ))

        notice = f"AI review completed using {'Gemini' if isinstance(adapter, GeminiProviderAdapter) else 'Anthropic'} ({len(findings)} suggestions generated; {redactions} PII items redacted)."
        return findings, notice

    except Exception as e:
        logger.warning(f"Optional Layer B AI call failed gracefully: {str(e)}")
        return [], f"AI Layer Fallback Notice: External provider call encountered issue ({str(e)}). Fallen back to local deterministic checks."
