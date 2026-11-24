# BrandProof: Final report (Round 3)

Team CodeMonks | Vishwakarma Institute of Technology, Pune | Inkloom AI problem statement

**Every claim gets proof. Every verdict gets a receipt.**

## 1. The problem we chose

Review capacity has not kept up with content volume, and teams that add an AI checker inherit a new risk: a verdict that is confident, unexplained and possibly manipulated by the very file it reviews. We did not set out to build "an LLM that lists issues". We set out to build a reviewer a human can **trust and later prove**. Our one-line difference: others check the content; we check the checker, and the rulebook.

## 2. What we built

A pre-publication review platform for one organisation (fictional brand Finora) covering text, images and PDFs, with roles, comments, risk-routed approvals, version history and a hash-chained audit log. A human always makes the final decision; nothing is applied or approved automatically.

| Round 1 promise | What exists now | Check it |
|---|---|---|
| **I1 Claim Ledger + Intent Lock** | Claims judged Supported / Contradicted / Outdated / Unsupported / Needs human against a dated Fact Vault. Structured must-keep intent elements; every fix is re-reviewed and checked element by element; failing fixes are withheld. Evidence view per claim. "Request a fact" workflow for unsupported claims. | Claim Ledger tab; Governance > Fact requests |
| **I2 Trust Layer + Proof Pack** | Hidden text (white, tiny, off-page, invisible, under images, in annotations and metadata), zero-width and look-alike characters, injection phrases in several encodings, local OCR. Raw and cleaned file reviewed separately; a different verdict raises a manipulation flag. Proof Pack with checked / not checked / humans / AI use, signed receipt, PDF export, public verify page. | Trust tab; `/trust` scoreboard; `/verify/CODE` |
| **I3 Rulebook Red-Team** | Adversary variants (hand-written, mutation-generated, optional LLM) split into train and hold-out; tighter rule for the owner to approve; before/after re-test; false-positive guard; ambiguity score from overrides, reviewer split and AI self-disagreement; Hinglish and Devanagari matching. | Rulebook Health |
| Core F1-F8 | Guideline import, Fact Vault, intake, hybrid review, cited findings, fixes, roles and audit, redaction and disclosure page | `docs/SCOPE_LOCK.md` |

Added beyond the plan, each because it strengthens the central idea: **stale-approval alerts** (a receipt stays honest when a fact later changes), a **`brandproof check` CLI gate**, **confidential mode** (blocks every external AI call), and an in-app **Evaluation page**.

## 3. How we measure it, misses included

| Set | Items | Rule precision | Rule recall | Notes |
|---|---|---|---|---|
| Seeded (written with the engine) | 52 | 100% | 100% | Regression safety only. Not independent accuracy. |
| Held-out probe | 16 | 88% | 88% | Written after the engine froze; 2 misses. A third (a double exclamation mark) was fixed as a bug, so this set is partly tuned |
| **Blind set v1** | 34 | **82%** (95% CI 62-93%) | **67%** (95% CI 48-81%) | Written after the freeze; engine **not** changed after seeing results |
| Trust Layer scoreboard | 25 attacks, 8 controls | | | 23 attacks caught, 2 declared gaps, 8 of 8 controls clean |

All numbers are **offline mode** (no LLM key). Four of the nine blind-set misses (B10 to B13) are tone cases that need an AI judge, so recall may rise with a key, but we have **not measured that** and do not claim it. The other five (B3, B5, B7, B14, B19) are phrasing gaps in the claim, term and privacy rules that a key would not fix. The misses and false positives are listed in `docs/EVAL_REPORT.md` and on the `/evaluation` page.

Red-team on the seeded rulebook (hold-out generalisation, offline): TERM-01 0 -> 3 of 5, TONE-04 1 -> 3 of 4, MSG-07 3 -> 4 of 4, ASCI-02 0 -> 2 of 4. Five hold-out variants stay open as loopholes that need a human rewrite; the report lists them instead of claiming 100%.

Engineering checks: **241 backend tests pass**, **42/42 live smoke checks pass**, TypeScript type-check clean.

## 4. Responsible AI

- **Human oversight:** humans alone approve; high-severity claims need an authorised reviewer; fixes are never auto-applied; stale alerts change nothing automatically.
- **Privacy:** emails, phones, Aadhaar, PAN and card numbers are replaced by tokens before any model call; confidential mode blocks all external calls; retention can purge files after approval; external contributors see only their own assets.
- **Transparency:** disclosure page lists every model and service and every call; each Proof Pack states AI use; Proof Pack lists what was **not** checked.
- **Security:** uploads are untrusted (size, type and content-sniffing limits, rate limits, security headers, secret checks); hash-chained audit log. See `docs/SECURITY.md`.
- **Our own use of AI:** the code was generated with Claude at the team's direction. See `docs/AI_DISCLOSURE.md` and `docs/CONTRIBUTIONS.md`.

## 5. Honest limits (full list: `LIMITATIONS_AND_ROADMAP.md`)

1. Evaluation sets are small and team-written; the intervals are wide for that reason.
2. Offline tone checks are a lexicon heuristic and miss subtle tone; we have not measured the LLM path against a live model.
3. Receipts are signed with the server's secret, not a public key; they prove "this server issued it and the log contains it", not third-party offline verification.
4. Paraphrased injections and words made only of look-alike letters are known gaps.
5. No live accessibility audit, penetration test or real-user result is included yet.
6. English and Hinglish only; one organisation per deployment.

## 6. Deviations from the Round 1 plan

SQLAlchemy with SQLite by default and PostgreSQL via `DATABASE_URL` (instead of Supabase Auth and Storage); own JWT auth; local OCR through Tesseract (the plan used a vision model); Pillow only (no OpenCV); LLM optional. Reasons are in `docs/SCOPE_LOCK.md`.

## 7. Where to start as a judge

`README.md` (one-command run and the 90-second demo) -> `docs/DEMO_SCRIPT.md` -> `/evaluation` and `/trust` in the app -> `docs/EVAL_REPORT.md` -> `docs/SCOPE_LOCK.md`.
