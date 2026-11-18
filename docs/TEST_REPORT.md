# Test report (Round 2)

Generated with the repository as submitted.

## Automated tests: 92 passed

`cd backend && python -m pytest -q`

| File | Tests | What it proves |
|---|---|---|
| test_deterministic.py | 15 | each rule fires and stays quiet when it should; fuzzy matching of spacing/leetspeak tricks; WCAG contrast maths; PDF contrast and palette checks; fixes never delete characters |
| test_trust.py | 8 | hidden text found by reason (white, tiny, off-page, invisible); injection phrases flagged and marked hidden; differential review raises a manipulation flag; hidden fake disclaimer caught; redaction |
| test_claims.py | 17 | every verdict (Supported, Contradicted, Outdated, Unsupported, Needs human); fact expiry; Fact Vault edits change verdicts; fake AI quotes dropped; only the owner edits facts |
| test_verifier.py | 6 | good fixes verified; fixes that lose intent, introduce violations or do not resolve are **withheld**; nothing is applied without a human click |
| test_api_flow.py | 13 | login, citations and badges, accept/edit/reject, stale findings, PDF and image intake, preview, comments, visibility rules |
| test_workflow.py | 7 | risk routing (manager cannot approve high risk), reviewer waivers, state machine, locking after approval, retention purge |
| test_audit.py | 4 | hash chain verifies; edited and deleted rows are detected |
| test_rules.py | 7 | rule versioning, guideline import to drafts, approval gate, library, seeded brand pack |
| test_redteam.py | 6 | loophole -> tighter rule -> approve -> re-test; no false positives; rulebook health and ambiguity |
| test_ai_adapter.py | 9 | mocked Anthropic API: validation of AI output, redaction before every call, call log, fallback on failure, Intent Lock judge, image OCR gated by owner setting |

## Real-browser test

`e2e/ui_flow.py` (Playwright/Chromium) signs in as each role and exercises: dashboard, review workspace, accepting a fix, Claim Ledger, history diff, Proof Pack, Trust Layer on a hidden-text PDF, audit verification, red-team run and approval, governance, disclosure, and a 390 px mobile layout. Result: all steps passed with no console errors. Screenshots: `docs/screenshots/`.

## Type check and build

`cd frontend && npx tsc --noEmit && npm run build`: passes.

## Seeded evaluation (see `EVAL_REPORT.md`)

| Set | Items | Precision | Recall | Claim accuracy | Attacks caught | Clean controls |
|---|---|---|---|---|---|---|
| Seeded (written with the engine) | 52 | 100% | 100% | 100% | 7/7 | 12/12 |
| **Held-out probe** (not used for tuning) | 16 | 87% | 81% | 100% | 3/3 | 2/2 |

Fixes across the seeded set: 34 proposed, 31 verified, 3 withheld.

**Honest reading:** the seeded set was written alongside the engine, so its near-perfect numbers show regression safety, not independent accuracy. The held-out probe is the better estimate: it missed 3 expected findings (semantic pressure wording, a Hinglish variant, and a double exclamation mark), listed in `EVAL_REPORT.md`. These are known limitations, not hidden.

## Not tested here

* Docker images were not built in the authoring environment (no Docker available); the services were run directly with `uvicorn` and `next start`, and the Dockerfiles follow Next.js standalone and FastAPI conventions. Run `docker compose up --build` once to confirm on your machine.
* Live calls to the Anthropic and Gemini APIs were not made (no keys); that path is tested against a mocked API only.
* User testing with real volunteers is a team activity: protocol in `USER_TESTING.md`.
