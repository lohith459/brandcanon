# Round 3 Improvements: Architectural Specifications

These three named architectural improvements have been architected and prepared during the Round 2 MVP, with production hooks and data collection paths already active.

---

## 1. Evidence-or-Silence Hardening
**Objective**: Guarantee zero hallucinated findings and deliver calibrated abstention for ambiguous claims.

### Design & Architectural Hooks in Place
- **Current Foundation**: The Layer D Verifier already enforces strict grounding: every finding must cite an existing database `rule_id` or `fact_id`, and its exact `quoted_text` must be confirmed in the draft (or anchored to the full document for missing disclaimers). Ungrounded findings are logged and dropped.
- **Round 3 Expansion**:
  - **100-Piece Benchmark Corpus**: Scale the current 30-piece evaluation corpus (`evaluation/corpus.json`) to a comprehensive 100-piece golden set including adversarial edge cases, double-negations, and subtle regulatory claims.
  - **Calibrated Abstention ("Needs Human Review")**: When finding confidence falls between 0.50 and 0.75, or when multiple facts partially match numeric claims, the engine abstains from asserting a direct violation and instead classifies the finding as `needs_human_review`, avoiding false positives while preventing compliance oversights.
  - **Automated Outdated-Fact Lifecycle Alarms**: Automated webhooks alerting brand managers 30 days prior to fact expiration dates (`expires_on`).

---

## 2. Intent Lock
**Objective**: Protect creative voice by ensuring that automated fixes do not compromise marketing goals, brand tonality, or call-to-action destinations.

### Design & Architectural Hooks in Place
- **Current Foundation**: The `Submission` schema already captures `intent_message` and `intent_cta` explicitly at submission time.
- **Round 3 Expansion**:
  - **Minimal-Edit Constraint**: Calculate Levenshtein edit distance and cosine semantic similarity between the draft and proposed rewrites. If the proposed edit deviates by more than 20% in semantic meaning, flag as excessive edit.
  - **CTA & Entity Preservation Verifier**: Automatically parse named entities and CTA verbs in the original draft vs the rewritten version. If the core CTA (e.g. "Join FinEdge Plus") or key entity references are lost during fix application, the rewrite is rejected and flagged as `"Needs Human Rewrite"`.
  - **Dual-Loop Re-Review**: Every rewrite automatically triggers a fresh run of Layer A checks to guarantee that fixing one violation does not inadvertently introduce a secondary violation.

---

## 3. Guideline Health Dashboard
**Objective**: Continuous feedback loop measuring which brand rules are effective, ambiguous, or frequently contested.

### Design & Architectural Hooks in Place
- **Current Foundation**: Every dismissal requires an explicit written reason (`decision_reason`), and every action is logged into an append-only `AuditLog` table with actor role and timestamp.
- **Round 3 Expansion**:
  - **Ambiguity Score per Rule**:
    $$\text{Ambiguity Score} = \frac{\text{Dismissals with Exception Reasons} + \text{Reviewer Disagreements}}{\text{Total Rule Invocations}}$$
    Rules with ambiguity scores $> 0.30$ are surfaced to Brand Admins with recommendations to clarify phrasing or adjust regex thresholds.
  - **Recurring Violation Heatmaps**: Aggregation of violations by publishing channel (e.g. Twitter vs LinkedIn) and team, identifying high-frequency training opportunities for content creators.
