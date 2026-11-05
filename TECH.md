# Technical Architecture & Stack Specification

BrandCanon is an intelligent pre-publication brand governance platform designed for high-precision verification, rapid containerized deployment, and strict offline operation.

---

## 1. Tech Stack Overview

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Runtime & Language** | Python | 3.11+ (Tested on 3.13) | Core application execution. |
| **Web Framework** | FastAPI | >= 0.110.0 | High-performance asynchronous HTTP routing and OpenAPI docs. |
| **Data Modeling** | SQLModel | >= 0.0.16 | Blends SQLAlchemy ORM with Pydantic type validation. |
| **Database Engine** | SQLite 3 | Embedded | Local file-based relational persistence with in-memory test isolation. |
| **Document Parsers** | `python-docx`, `pypdf`, `beautifulsoup4` | Pinned | Secure extraction of text from Word, PDF, HTML, and Markdown documents. |
| **Semantic Retrieval** | `rank-bm25` (BM25Okapi) | >= 0.2.2 | Token-exact, low-latency relevance ranking over Canon guidelines and facts. |
| **Frontend Framework** | Plain HTML5 + Vanilla JS | ES6 | Zero-build single-page application served directly from FastAPI static files. |
| **CSS Framework** | Tailwind CSS CDN + Custom CSS | Modern | Responsive UI, WCAG AA contrast colors, and non-color-reliant visual indicators. |
| **Testing Suite** | `pytest` + `httpx` TestClient | >= 8.1.0 | 29 automated unit, integration, and security tests. |
| **Deployment** | Docker | 3.11-slim | Production container with dynamic `$PORT` binding, auto-seeding, and `/health`. |

---

## 2. Review Engine Architecture

```
[Draft Copy / Document]
           │
           ▼
┌────────────────────────────────────────┐
│     Layer A: Deterministic Checks      │
│  - Terminology (forbidden -> approved) │
│  - Regex & Rules (CMP-004, CMP-001)    │
│  - Facts & Claims (Fact.keywords link) │
│  - Outdated Fact Checker (expires_on)  │
│  - Required Disclaimers (DISC-002)     │
│  - Tone & Readability (TON-003, TON-002│
│  - Accessibility (<img> missing alt)   │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│  Layer B: Optional AI Layer (Optional) │
│  - Gated by Confidential Mode Toggle   │
│  - Deterministic PII Redaction         │
│  - BM25 Retrieval of top-k Rules/Facts │
│  - Gemini / Claude Provider Adapter    │
│  - Strict Pydantic JSON Validation     │
│  - Graceful Fallback on any failure    │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│   Layer D: The Verifier (Mandatory)    │
│      "Evidence-or-Silence Policy"      │
│  - Verifies cited rule_id or fact_id   │
│  - Verifies exact quoted_text presence │
│  - Validates full-document anchors     │
│  - Drops ungrounded/hallucinated items │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│       Risk Tiering Calculator          │
│  - Tier 3: Critical compliance breach  │
│  - Tier 2: High severity / fact error  │
│  - Tier 1: Low / Medium formatting     │
└──────────────────┬─────────────────────┘
                   │
                   ▼
       [Verified Finding Cards]
```

---

## 3. Detailed Component Mechanics

### Layer A: Deterministic Checks
1. **Terminology Dictionary**: Evaluates all forbidden phrases across the `Term` registry using word-boundary regular expressions (`\b... \b`). Exact character offsets are recorded, and `term.preferred` is assigned as the suggested replacement.
2. **Fact Registry Linkage**: Claims containing numeric quantities (`50,000+`, `145M`, `25`) are parsed and linked to `Fact` records using `Fact.keywords` (e.g. `["users", "investors", "members"]`). If the claimed number exceeds the verified factual ceiling, a `fact_contradicted` violation is generated.
3. **Outdated Fact Detection**: Compares the fact's `expires_on` timestamp against today's date. If expired, flags a high-severity `fact_outdated` finding.
4. **Required Disclaimers**: If content mentions investments, yields, or returns, the engine checks for the exact presence of `Investments are subject to market risks.`. If absent, a finding is anchored to the full document `[0, len(text)]` with empty quoted text.
5. **Tone & Readability**: Counts total exclamation marks (flags `!!` or multiple `!`) and finds uppercase words of 3+ letters outside the acronym whitelist (`SEC`, `RIA`, `AUM`, etc.).

### Layer B: Optional AI Layer
- Operates via an abstract `AIProviderAdapter` pattern.
- Implements `GeminiProviderAdapter` (using Gemini 1.5 Flash via REST) and `AnthropicProviderAdapter` (using Claude 3 Haiku via REST).
- **PII Scrubbing**: Strips email addresses and phone numbers before any outbound transmission.
- **BM25 Pruning**: Queries the Brand Canon using Okapi BM25 and injects only the top 5 most relevant rules and facts into the prompt, reducing token overhead and hallucination surface.

### Layer D: The Evidence-or-Silence Verifier
- Acts as a zero-trust gatekeeper.
- Validates that every finding cites a registered database entity (`Rule.id` or `Fact.id`).
- For text findings, verifies that `quoted_text` exists within the draft. For missing elements (disclaimers), validates that `span_start == 0 and span_end == len(text)` with a valid rule ID.
- Dropped findings are counted and logged.

### Safe Backward Fix Application
- When a user accepts suggested fixes, `apply_accepted_fixes` sorts findings descending by `span_start` (from end of text to beginning).
- Detects and skips overlapping spans safely to prevent text corruption.
- Generates a new `Version` record and automatically executes a fresh review run on the resulting text.

### WCAG Contrast Ratio Calculator
- Implements the official W3C WCAG 2.1 relative luminance formula:
  $$L = 0.2126 \times R_{\text{lin}} + 0.7152 \times G_{\text{lin}} + 0.0722 \times B_{\text{lin}}$$
- Computes contrast ratio:
  $$\text{Ratio} = \frac{L_1 + 0.05}{L_2 + 0.05}$$
- Evaluates against the 4.5:1 standard for normal text and 3.0:1 for large text.
