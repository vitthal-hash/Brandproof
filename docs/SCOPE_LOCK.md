# BrandProof: Round 2 Scope Lock

Team CodeMonks | Inkloom AI problem statement | Round 2: The Build

This file freezes what we promised in Round 1 and what ships in Round 2. Anything not listed here is not part of Round 2. Every row names the place where it can be checked (test file, endpoint or screen).

## 1. Locked deliverables

### Core workflow (must ship)

| ID | Round 1 promise | What ships in Round 2 | Where to verify |
|----|-----------------|-----------------------|-----------------|
| F1 | Guideline import to approved, versioned rules (ID, category, severity, examples), ASCI-style claims and AI-label rule pack, Hinglish term variants as data | Import text/PDF/Markdown guideline into **draft** rules; owner edits, approves or rejects; each edit makes a new rule version; seeded Brand Constitution of 22 rules incl. ASCI-style pack and Hinglish variants | `tests/test_rules.py`, Governance > Rules / Import |
| F2 | Fact Vault (fact, source, owner, expiry) and asset library (terms, palette, logos) | 24 dated facts with source, owner, valid-until; library for approved terms, palette colours, competitor names, logo files | `tests/test_claims.py`, Governance > Facts / Library |
| F3 | Text, image and PDF intake with one-line creator intent | Paste text or upload .txt/.md/.pdf/.png/.jpg; intent required; channel; AI-generated flag; alt text | `tests/test_api_flow.py`, New submission |
| F4 | Hybrid review: deterministic first, then AI that cites or abstains | Deterministic: terminology, product-name casing, pressure phrases, caps, exclamation, offer end date, disclaimer, AI label, PII, reading level, alt text, WCAG contrast, palette. Then claims, then tone/messaging checks by an LLM (if a key is set) or an offline heuristic fallback that is labelled as such | `tests/test_deterministic.py`, `tests/test_ai_adapter.py` |
| F5 | Explainable findings with rule/fact citation, method badge, confidence | Every finding stores rule id and version and/or fact id, method badge (Rule, Claims, AI, Heuristic, Trust), confidence, explanation, exact quote | Asset review screen |
| F6 | Suggested fixes, never auto-applied | Fix is shown as before/after; creator accepts, edits or rejects; accepting creates a new version and re-reviews; nothing applies without a human click | `tests/test_api_flow.py` |
| F7 | Roles, comments, risk-routed approvals, version history, tamper-evident audit log | 5 roles (creator, external contributor, manager, reviewer, guideline owner); comments anchored to findings; high-risk items need an authorised reviewer; version history with diff; hash-chained audit log with verify endpoint | `tests/test_workflow.py`, `tests/test_audit.py` |
| F8 | Redaction before external calls; visible AI/external-service disclosure page | Emails, phones, Aadhaar, PAN and card numbers are replaced by tokens before any LLM call; every call is logged; Disclosure page lists services, data sent, calls and retention setting | `tests/test_trust.py`, Disclosure screen |

### Three named improvements (first versions)

| ID | Round 1 promise | Round 2 first version | Where to verify |
|----|-----------------|-----------------------|-----------------|
| I1 | Claim Ledger with verified fixes, Intent Lock | Claims extracted; each judged Supported / Contradicted / Outdated / Unsupported / Needs human against the dated Fact Vault; every fix is re-reviewed by the verifier and passes Intent Lock before the creator sees it; failing fixes are withheld and counted | `tests/test_claims.py`, `tests/test_verifier.py`, Claim Ledger tab |
| I2 | Trust Layer (sanitiser, hidden-text and injection detection, differential review) and Proof Pack | PDF hidden-text detection (white/invisible/tiny/off-page), zero-width and HTML-comment stripping, injection-phrase scan, redaction, raw-vs-clean differential review with manipulation flag, Proof Pack screen and JSON for every asset including what was **not** checked | `tests/test_trust.py`, Trust tab, Proof Pack screen |
| I3 | Rulebook Red-Team, repeated mistakes, ambiguity flags | Red-Team v1: hand-written and mutation-generated rule-dodging variants (plus LLM variants when a key is set); misses become loopholes; tighter rule proposal for the owner; approve; re-test before/after. Rulebook Health: hits, override rate, loopholes and ambiguity flag from overrides, repeated mistakes by rule and team | `tests/test_redteam.py`, Rulebook Health screen |

### Also shipped in Round 2

- Dashboard v1: status counts, queue, repeated mistakes by rule and team.
- Seeded fictional brand pack (Finora) with demo users and 7 demo assets, including a hidden-text PDF, a low-contrast PDF and an off-palette AI-generated image.
- Seeded evaluation set of 52 items plus a 16-item held-out probe (written after the engine was frozen), with a runnable harness and a generated report (`docs/EVAL_REPORT.md`).
- README, architecture notes, AI/service disclosure, contribution log, test report, user-testing protocol.
- Docker Compose and Render configuration for deployment.

## 2. Deviations from the Round 1 plan (stated openly)

| Round 1 plan | Round 2 reality | Why |
|--------------|-----------------|-----|
| Supabase Postgres, Auth, Storage | SQLAlchemy with SQLite by default; set `DATABASE_URL` to a Postgres/Supabase URL to switch. Own JWT auth with roles; local file storage | Runs with one command and no external accounts; judges can start it anywhere |
| Pillow / OpenCV | Pillow only | Pillow was enough for colour distance and contrast |
| Vision-model OCR with Tesseract fallback | Text inside images is read only when an LLM key is configured; otherwise the Proof Pack lists it as **not checked** | Honest limitation; no silent guessing |
| Hosted LLM mandatory | LLM optional. Without a key the app runs on deterministic checks plus a labelled heuristic fallback | Keeps the product working during quota or network problems (Round 1 risk table) |
| python-docx | Not used | Scope is text, image and PDF only |

## 3. Explicitly not in Round 2 (moved to Round 3)

- Ambiguity score from repeated-judgment disagreement between AI runs.
- LLM-driven red-team tuning and larger adversarial sets.
- Proof Pack PDF export (the Proof Pack screen is printable).
- Hinglish transliteration matching beyond the variant lists.
- Simple API/CLI hook; browser extension; video and audio.
- Local-model confidential mode.

## 4. Round 2 submission checklist

| Required item | Where it is |
|---------------|-------------|
| Functional product | `docker compose up` (see README) |
| Public repository | the team pushes this folder to GitHub |
| Deployed link | the team deploys with `render.yaml` or Docker (see README) |
| Architecture and main technical decisions | `docs/ARCHITECTURE.md` |
| APIs, models, datasets, libraries, services, AI-generated components | `docs/AI_DISCLOSURE.md` |
| Evidence of user testing | protocol in `docs/USER_TESTING.md`; the team records its own sessions there |
| Each member's contribution | `docs/CONTRIBUTIONS.md` |
