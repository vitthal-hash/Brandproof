# Pre-submission checklist (things only the team can do)

Tick each box. Items marked **required** are promised somewhere in our documents.

## Run and verify (30 minutes)

- [ ] **required** `docker compose up --build` works from a clean clone (Docker was never run in the authoring environment).
- [ ] **required** `cd frontend && npm ci && npm run build` succeeds (could not run in the authoring sandbox because it blocks Google Fonts; `tsc --noEmit` passes).
- [ ] `cd backend && python -m pytest -q` -> 241 passed.
- [ ] `python scripts/smoke_test.py` against the running app -> 42/42.
- [ ] Click through the whole guided tour once as each role (Back, Next, End tour, Esc, Finish); `python scripts/check_tour.py` only checks it statically.
- [ ] `python e2e/ui_flow.py` (Playwright) passes against the deployed or local app; it was last run in Round 2.
- [ ] `python -m eval.run_eval` regenerates `docs/EVAL_REPORT.md` with the same numbers.
- [ ] Confirm the numbers in `FINAL_REPORT.md` still match after any change you make. If a number changes, edit the report.

## Deploy

- [ ] Deploy with `render.yaml` or Docker; set `BP_ENV=production`, a `BP_SECRET` of 32+ characters, `BP_PUBLIC_URL`, and `BP_CORS_ORIGINS`. Rebuild the API image so Tesseract is present.
- [ ] Keep `BP_SEED=1` on the judges' demo instance (it creates the demo users); never on anything real.
- [ ] Open the live link in a private window, on a phone, and from another network.
- [ ] Schedule a daily call to `POST /api/stale/scan` if the instance stays up for weeks.
- [ ] Optional: add `ANTHROPIC_API_KEY`, then run the AI-disagreement probe once and **measure** the blind set with the key before saying anything about LLM accuracy.

## Accessibility and mobile (required: the plan promises WCAG AA basics)

- [ ] Work through `docs/UI_CHECKLIST.md` (light and dark mode, phone, keyboard, axe, tour per role).

- [ ] Run axe (browser extension) on Dashboard, New submission, Asset, Rulebook, Evaluation, Trust and Verify. Save screenshots or exports in `docs/`.
- [ ] Keyboard-only pass: tab through New submission and an asset; confirm focus is visible and highlighted text opens by Space and Enter.
- [ ] Check a 390 px wide screen on the dashboard, asset and verify pages.
- [ ] Fix or list what you find in `LIMITATIONS_AND_ROADMAP.md`.

## Evidence we have not invented

- [ ] **required** Run 3 to 5 real sessions with `docs/USER_TESTING.md` and fill the log and the results summary. If you cannot, say so in the final report. Never fill the table with made-up rows.
- [ ] Record the demo video from `docs/DEMO_SCRIPT.md`.
- [ ] Update `docs/CONTRIBUTIONS.md` to match what each member actually did (see `git shortlog -sn`).

## Rules and honesty

- [ ] **required** Round 3 build window: Mon 23 Nov 10:00 to Thu 26 Nov 10:00. Your Round 1 declaration says product code is built only inside official windows. Be ready to explain which work was done between rounds and which was done inside the window, and keep commit timestamps accurate. Do not rewrite history.
- [ ] Every member can open the code of their area and demo it.
- [ ] `docs/AI_DISCLOSURE.md` is still true: the code was generated with Claude at your direction; add any other tools you used.
- [ ] No real customer data, passwords or API keys in the repository (`git log -p | grep -i key` to check); `.env` is not committed.
- [ ] Public repo pushed; deployed link, video link and report link added to the submission form.
