# Architectural & Implementation Decisions

This document records key technical decisions made during the design and implementation of **BrandCanon**, along with rationales and context.

---

## Decision Log

### 1. SQLite with SQLModel / SQLAlchemy for Persistence
- **Decision**: Use SQLite via SQLModel as the primary relational database.
- **Context**: The application must deploy cleanly to free hosting (Render / Railway / Hugging Face Spaces) without requiring an external managed Postgres instance or database connection credentials.
- **Rationale**: SQLModel combines SQLAlchemy with Pydantic type validation, enabling schema definition, fast migrations, in-memory testing (`sqlite:///:memory:`), and simple containerized storage.

### 2. Client-Header Demo Role Switcher (`X-Demo-Role`)
- **Decision**: Implement demo roles (Creator, Manager, Compliance Reviewer, Admin) via an HTTP request header (`X-Demo-Role`) and a UI dropdown in the header, rather than a full OAuth/JWT sign-in system.
- **Context**: Hackathon judges need to open the app with zero logins, no onboarding friction, and immediately test cross-role capabilities.
- **Rationale**: Real sign-in screens prevent immediate exploration and score zero on instant core workflow tests. Roles are validated server-side on every request and clearly labeled as "Demo Roles".

### 3. Layered Review Engine: Offline-First Deterministic + Evidence-or-Silence Verifier
- **Decision**: Build deterministic Layer A checks (regex, terminology, facts, disclaimers, tone, contrast) as the core engine, coupled with Layer D verifier, and make external LLM (Layer B) purely optional.
- **Context**: Requirement specifies that the platform must run with zero API keys and never crash if an external API call fails.
- **Rationale**: Brand compliance must be predictable, auditable, and repeatable. Deterministic rules provide guaranteed citations and exact character spans. Layer D ("evidence-or-silence") drops any finding lacking a verified rule/fact ID or whose quoted text cannot be found in the text. For missing required elements (e.g., missing disclaimer), findings anchor to the whole text while validating against an active rule ID.

### 4. Fact Model Keyword Linking
- **Decision**: Add a `keywords` list to `Fact` (e.g. `["users", "investors", "members", "customers"]`).
- **Context**: When scanning drafts for numeric claims (e.g. "Join 50,000+ investors"), the engine needs to reliably link extracted numbers to the corresponding brand fact (e.g. active users fact F-017).
- **Rationale**: Keyword proximity and semantic tokens allow high-precision linkage between draft claims and factual registry records without requiring heavy ML models.

### 5. Safe Backward Fix Application with Automatic Re-Review
- **Decision**: In `apply-fixes`, sort accepted findings by `span_start` descending (from end of document to beginning), detect and handle overlapping spans safely, create a new `Version` record, compute a word-level diff, and automatically re-run the review engine on the new version.
- **Context**: Replacing text spans from left to right mutates character offsets for subsequent spans, causing offset drift or text corruption.
- **Rationale**: Backward replacement preserves earlier character offsets. Automatic re-review immediately shows whether the applied fixes resolved the violations or introduced new ones.

### 6. PII Redaction & Confidential Mode
- **Decision**: Introduce deterministic regex-based PII redaction (email addresses, phone numbers) before passing any draft text to external AI adapters, along with a "Confidential Mode" toggle that completely suppresses outbound external calls.
- **Context**: Enterprise brand assets and pre-announcement drafts frequently contain sensitive customer or product data.
- **Rationale**: Guarantees zero leakage of customer data to third-party model providers while preserving local Layer A brand governance.

### 7. Pure Python Stack with Single-Page Frontend (Tailwind CDN + Vanilla JS)
- **Decision**: Serve frontend directly through FastAPI static files with Tailwind CSS via CDN and vanilla JavaScript, avoiding a separate Node.js build step or complex frontend framework.
- **Context**: Eliminates multi-stage Node/NPM build overhead, reduces Docker image size to under 300MB, ensures sub-second local reload, and enables immediate single-container deployment on free cloud tiers.
