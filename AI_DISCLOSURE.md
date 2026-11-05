# AI Disclosure & Transparency Statement

## 1. Development-Time AI Usage
In compliance with hackathon integrity guidelines:
- **Assisted Code & Documentation**: Code skeletons, regular expressions, test fixtures, and technical documentation were authored with assistance from Google Antigravity (powered by Google DeepMind's Gemini models) and Anthropic Claude models.
- **Human Verification**: All code, architecture, database schemas, test cases, and security boundary controls have been reviewed, tested with 29 automated test cases, and confirmed by the engineering team.

---

## 2. Runtime AI Architecture & Data Flows

BrandCanon is architected on an **offline-first, evidence-grounded philosophy**:

### Zero-Key Offline Core (Layer A + Layer D)
- By default, BrandCanon operates with **zero API keys**.
- The core governance engine relies exclusively on deterministic checks (regular expressions, terminology dictionary lookups, fact ceiling checks, and WCAG luminance formulas) and the Layer D Evidence-or-Silence Verifier.
- In this offline mode, **zero data** leaves the server or host environment.

### Optional External AI Layer (Layer B)
- If and only if `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` is provided in environment variables, an optional semantic review layer is enabled.
- **PII Redaction**: Before any draft text is dispatched to an external model endpoint (Google Gemini or Anthropic Claude), deterministic regex filters automatically strip email addresses (`[REDACTED_EMAIL]`) and phone numbers (`[REDACTED_PHONE]`).
- **Context Minimization**: Only the top-k (k=5) relevant rules and facts are retrieved via BM25 and sent in the prompt. The model is never sent internal audit logs, user identities, or other drafts.
- **Confidential Mode Override**: Users can toggle "Confidential Mode" directly in the UI header. When active, all external API calls are strictly suppressed, and the system defaults to 100% local deterministic review.
- **Human-in-the-Loop Constraint**: AI models never approve, publish, or automatically overwrite draft copy. All AI-suggested fixes are presented as advisory cards requiring explicit human review and approval.
