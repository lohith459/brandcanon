# Changes From Plan & Architectural Rationales

This document honestly reflects all architectural divergences and tactical decisions made during the BrandCanon MVP build, along with the technical rationale for each choice.

---

## 1. Relational Persistence: SQLite (SQLModel) instead of Postgres
- **Initial Notion**: Deploying a cloud Postgres instance or multi-tenant database.
- **Adopted Solution**: SQLModel with local SQLite database file (`brandcanon.db`) and in-memory static pools for tests (`sqlite:///:memory:`).
- **Rationale**: Eliminates external database network latencies, avoids cloud database connection limits on free tiers, allows instant 1-click single-container deployment on Render/Railway, and ensures `pytest` runs all 29 tests in under 2 seconds without external service dependencies.

---

## 2. Authentication: Client-Header Demo Role Switcher (`X-Demo-Role`) instead of JWT / OAuth
- **Initial Notion**: Standard user sign-up with email verification and JWT session tokens.
- **Adopted Solution**: A header-driven role switcher (`X-Demo-Role`) exposing four distinct personas: **Creator**, **Manager**, **Compliance Reviewer**, and **Admin**.
- **Rationale**: Hackathon judges evaluate apps in under 3 minutes with zero onboarding walkthroughs. A sign-in gate, email verification link, or empty dashboard scores zero on instant workflow capability. All role permissions are strictly validated server-side on every API endpoint, specifically enforcing that **Tier 3 critical compliance risks can only be approved by a Compliance Reviewer**.

---

## 3. Semantic Retrieval: BM25 Okapi instead of Heavy Vector Embeddings / pgvector
- **Initial Notion**: Generating text embeddings using PyTorch/SentenceTransformers or calling vector APIs.
- **Adopted Solution**: Lightweight BM25 Okapi retrieval (`rank-bm25`) over tokenized Rule text and Fact claim keywords.
- **Rationale**: Embeddings models add 500MB+ to Docker images, require extensive CPU/memory on container cold starts, and introduce non-deterministic retrieval rankings. BM25 is instantaneous, lightweight (8KB dependency), token-exact, and fully offline.

---

## 4. Frontend Architecture: Single-Page Vanilla JS + Tailwind CDN instead of React/Node Build
- **Initial Notion**: A separate Node.js / React / Next.js frontend build.
- **Adopted Solution**: A modern Single Page Application served directly by FastAPI using standard HTML5, modern vanilla JavaScript ES6 modules, and Tailwind CSS via CDN.
- **Rationale**: Eliminates multi-stage Node/NPM build pipelines, reduces container build time from 5 minutes to 30 seconds, avoids Node version mismatches, and simplifies deployment to a single container running a standard Python process.

---

## 5. Safe Backward Fix Application with Automatic Re-Review
- **Initial Notion**: Applying replacements in reading order (left-to-right).
- **Adopted Solution**: Sorting accepted findings descending by `span_start`, safely checking for overlapping spans, applying edits backwards to preserve earlier offsets, and immediately re-running Layer A + Layer D on the new version.
- **Rationale**: Left-to-right replacements mutate character offsets for later spans, causing offset drift or text corruption. Backward editing is mathematically immune to earlier offset shifts. Automatic re-review immediately shows whether the applied fixes resolved all violations or left residual issues.
