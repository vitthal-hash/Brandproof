# Test report (Round 3, final)

Generated from the repository as submitted. Re-run every command below; do not trust this file over a fresh run.

## Automated tests: 241 passed

`cd backend && python -m pytest -q` (about 30 seconds)

| File | Tests | What it proves |
|---|---|---|
| test_deterministic.py | 15 | each rule fires and stays quiet when it should; fuzzy matching of spacing/leetspeak tricks; WCAG contrast maths; PDF contrast and palette checks |
| test_claims.py | 17 | every verdict; fact expiry; Fact Vault edits change verdicts; fake AI quotes dropped |
| test_verifier.py | 6 | bad fixes are withheld; nothing applied without a human click |
| test_intent_lock.py | 8 | element-by-element Intent Lock; AI elements must quote real text |
| test_fact_requests.py | 7 | request a fact, owner approves or declines, old database gets the new column |
| test_trust.py | 8 | hidden text by reason, injection flags, raw-vs-clean manipulation flag, redaction |
| test_trust_layer_v2.py | 17 | text under images, annotations, metadata, look-alike letters, OCR, false-positive fixes |
| test_trust_suite.py | 3 | scoreboard: attacks caught, controls clean, declared gaps reported |
| test_receipts.py | 10 | signed receipt, tamper detection, public verify, PDF export |
| test_redteam.py | 6 | loophole -> tighter rule -> approve -> re-test |
| test_redteam_v2.py | 27 | transliteration, train/hold-out, false-positive guard, stale proposals, AI variants, ambiguity score |
| test_stale_cli_confidential.py | 14 | stale alerts, CLI exit codes, confidential mode blocks external calls |
| test_hardening.py | 17 | upload limits, content sniffing, rate limits, secret checks, headers |
| test_ai_adapter.py | 9 | mocked model API: validation, redaction before every call, call log, fallback |
| test_api_flow.py | 13 | login, citations, accept/edit/reject, PDF and image intake, visibility rules |
| test_workflow.py | 7 | risk routing, waivers, state machine, locking, retention purge |
| test_audit.py | 4 | hash chain verifies; edited and deleted rows detected |
| test_rules.py | 7 | versioning, import to drafts, approval gate |
| test_eval_results.py | 2 | the blind set keeps its misses; evaluation endpoint needs login |
| test_round3_finish.py | 11 | future-dated facts, `!!` counted as two marks, comments stay inside their asset, PDF page and image megapixel caps, logo and guideline file limits, fact snapshots (edited, deleted, pre-snapshot runs, column migration) |

## Live smoke test: 42/42

With the API running (`BP_SEED=1`): `python scripts/smoke_test.py` -> `ALL CHECKS PASSED (42/42)`.

## Guided tour check

`python scripts/check_tour.py` -> TOUR CHECK PASSED (47 steps, 6 chapters). It is a static check of routes, click targets and controls; no browser was available to click through it.

## Type check

`cd frontend && npx tsc --noEmit` -> clean. `npm run build` could not run in the authoring sandbox (it cannot download Google Fonts); see `PRE_SUBMISSION_CHECKLIST.md`.

## Real-browser test (last run in Round 2; re-run after deploying)

`e2e/ui_flow.py` (Playwright/Chromium) signs in as each role and exercises: dashboard, review workspace, accepting a fix, Claim Ledger, history diff, Proof Pack, Trust Layer on a hidden-text PDF, audit verification, red-team run and approval, governance, disclosure, and a 390 px mobile layout. Result: all steps passed with no console errors. Screenshots: `docs/screenshots/`.

## Evaluation (see `EVAL_REPORT.md`, regenerate with `python -m eval.run_eval`)

| Set | Items | Precision | Recall | Claim accuracy | Attacks caught | Clean controls |
|---|---|---|---|---|---|---|
| Seeded (written with the engine) | 52 | 100% | 100% | 100% | 7/7 | 12/12 |
| **Held-out probe** (written after the freeze; HO9 later fixed as a bug, so partly tuned) | 16 | 88% | 88% | 100% | 3/3 | 2/2 |
| **Blind set v1** (written after the freeze; engine not changed after) | 34 | 82% (CI 62-93%) | 67% (CI 48-81%) | 2 labelled claims, not meaningful | 5/5 | 7/8 |

Trust Layer scoreboard (`/trust`): 23 of 25 attacks caught, 2 declared gaps, 8 of 8 clean controls.

Fixes across the seeded set: 34 proposed, 31 verified, 3 withheld.

**Honest reading:** the seeded set was written alongside the engine, so its near-perfect numbers show regression safety, not independent accuracy. The held-out probe is the better estimate: it still misses 2 expected findings (semantic pressure wording and a Hinglish pressure phrase); a third, a double exclamation mark, was fixed as a counting bug, listed in `EVAL_REPORT.md`. These are known limitations, not hidden.

## Not tested here

* Docker images were not built in the authoring environment (no Docker available); the services were run directly with `uvicorn` and `next start`, and the Dockerfiles follow Next.js standalone and FastAPI conventions. Run `docker compose up --build` once to confirm on your machine.
* Live calls to the Anthropic and Gemini APIs were not made (no keys); that path is tested against a mocked API only.
* User testing with real volunteers is a team activity: protocol in `USER_TESTING.md`.
