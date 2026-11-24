# BrandProof: Scope Lock (Round 2 baseline, updated for Round 3)

Team CodeMonks | Inkloom AI problem statement | Rounds 2 and 3

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

- Ambiguity score from repeated-judgment disagreement between AI runs. **Done in Round 3, step 3.**
- LLM-driven red-team tuning and larger adversarial sets. **Done in Round 3, step 3** (fresh AI variants, hold-out set, false-positive guard).
- Proof Pack PDF export. **Done in Round 3, step 2.**
- Hinglish transliteration matching beyond the variant lists. **Done in Round 3, step 3.**
- Simple API/CLI hook. **Done in Round 3, step 5** (`backend/cli.py`). Browser extension, video and audio stay on the roadmap.
- Confidential mode. **Done in Round 3, step 5** as a block on all external calls; a local model stays on the roadmap.
- Stale-approval alerts (added in Round 3, step 5).

## 4. Round 3 final scope (what is complete)

| ID | Round 1 promise | Complete in Round 3 | Where to verify |
|----|-----------------|---------------------|-----------------|
| I1 | Claim Ledger, verified fixes, Intent Lock | Structured intent elements, Intent Lock v2, evidence view per claim, request-a-fact workflow | `tests/test_intent_lock.py`, `tests/test_fact_requests.py`, Claim Ledger tab |
| I2 | Trust Layer and Proof Pack | Wider hidden-content and injection detection, look-alike letters, local OCR, signed receipts, public verify page, Proof Pack PDF, `/trust` scoreboard (23/25 attacks, 2 declared gaps, 8/8 controls) | `tests/test_trust_layer_v2.py`, `tests/test_receipts.py`, `tests/test_trust_suite.py` |
| I3 | Rulebook Red-Team, ambiguity, repeated mistakes | Train/hold-out split, false-positive guard, AI adversary, ambiguity score, Hinglish and Devanagari matching | `tests/test_redteam_v2.py`, Rulebook Health |
| Stretch | Proof Pack PDF export; transliteration; CLI hook | All three built | see above, `docs/CLI.md` |
| Evaluation | Publish precision and recall, misses included | Seeded 52, held-out 16, blind 34, Wilson 95% intervals, `/evaluation` page | `docs/EVAL_REPORT.md`, `tests/test_eval_results.py` |
| Added | Not in Round 1 | Stale-approval alerts, confidential mode, hardening (upload, rate and secret limits) | `tests/test_stale_cli_confidential.py`, `tests/test_hardening.py` |

Final checks: 241 backend tests, 42/42 smoke checks, TypeScript type-check clean.

### Round 3 deviations and changes to the section 2 table

| Round 1 plan | Round 3 reality |
|---|---|
| Vision-model OCR with Tesseract fallback | Tesseract is now the **default** local OCR (Round 2 had none). A vision model is used only if the owner enables it |
| "Core if time allows": alt-text and reading-level checks | Shipped in Round 2 |
| Round 2 said OCR "not checked" without a key | Superseded: OCR runs locally; the Proof Pack lists what OCR did not cover |
| Proof Pack "receipt" | An HMAC-signed receipt, not a public-key signature (stated in the limits) |
| Left from Round 1 | Cut line was never needed; nothing in F1-F8 or I1-I3 was cut |

Still not built: video and audio review, other Indian languages, DAM and design-tool connectors, SSO and multi-tenancy, C2PA signing. See `LIMITATIONS_AND_ROADMAP.md`.

## 5. Submission checklist (Rounds 2 and 3)

| Required item | Where it is |
|---------------|-------------|
| Functional product | `docker compose up` (see README) |
| Public repository | the team pushes this folder to GitHub |
| Deployed link | the team deploys with `render.yaml` or Docker (see README) |
| Architecture and main technical decisions | `docs/ARCHITECTURE.md` |
| APIs, models, datasets, libraries, services, AI-generated components | `docs/AI_DISCLOSURE.md` |
| Evidence of user testing | protocol in `docs/USER_TESTING.md`; the team records its own sessions there. **None recorded yet** |
| Final report, limits, roadmap | `docs/FINAL_REPORT.md`, `docs/LIMITATIONS_AND_ROADMAP.md` |
| Demo video | script in `docs/DEMO_SCRIPT.md`; the team records it |
| Things only the team can do | `docs/PRE_SUBMISSION_CHECKLIST.md` |
| Each member's contribution | `docs/CONTRIBUTIONS.md` |
