<p align="center">
  <img src="docs/banner.svg" alt="BrandProof: every claim gets proof, every verdict gets a receipt" width="100%">
</p>

<p align="center">
  <a href="https://brandproof-web.onrender.com"><b>Live demo</b></a> &nbsp;|&nbsp;
  <a href="#run-it-one-command">Run it locally</a> &nbsp;|&nbsp;
  <a href="docs/DEMO_SCRIPT.md">90-second demo</a> &nbsp;|&nbsp;
  <a href="docs/FINAL_REPORT.md">Final report</a> &nbsp;|&nbsp;
  <a href="docs/EVAL_REPORT.md">Evaluation</a>
</p>

<p align="center">
  <img alt="Backend tests: 229 passing" src="https://img.shields.io/badge/backend%20tests-229%20passing-0f766e">
  <img alt="Smoke test: 42 of 42" src="https://img.shields.io/badge/smoke%20test-42%2F42-0f766e">
  <img alt="Evaluation: 102 cases" src="https://img.shields.io/badge/evaluation-102%20cases-0a1f3d">
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-0a1f3d">
  <img alt="Node 20" src="https://img.shields.io/badge/node-20-0a1f3d">
</p>

<p align="center"><sub>The live demo runs on free hosting, so the first visit after a quiet period can take up to a minute to wake up.</sub></p>

# BrandProof

**Every claim gets proof. Every verdict gets a receipt.**
Team CodeMonks | Inkloom AI problem statement | Round 3: The Finish

BrandProof reviews text, images and PDFs **before publication** against an organisation's approved guidelines, facts and assets. It explains each finding, cites the exact rule or approved fact, and proposes fixes that keep the creator's intent. It never applies or approves anything on its own.

What makes it different from a plain "ask an LLM" checker: it treats the AI reviewer as something that can be **wrong** and can be **attacked**.

| Named improvement | What it does (complete in Round 3) |
|---|---|
| **I1 Claim Ledger + Intent Lock** | Each promotional claim gets a verdict (Supported, Contradicted, Outdated, Unsupported, Needs human) against a **dated Fact Vault**. Every suggested fix is re-reviewed and must pass Intent Lock before the creator sees it; failing fixes are withheld. |
| **I2 Trust Layer + Proof Pack** | Detects hidden text (white, tiny, off-page, invisible), zero-width characters, HTML comments and prompt-injection phrases; reviews the raw and the cleaned file and raises a manipulation flag if the verdicts differ. Every asset gets a Proof Pack: what was checked, what was **not** checked, who approved, which AI saw what. |
| **I3 Rulebook Red-Team** | An adversary writes content that breaks a rule but tries to slip past it. Misses become loopholes with a tighter rule for the owner to approve, then re-tested (before/after, plus a false-positive guard). Hinglish spelling variants and Devanagari are matched; a hold-out set shows whether a tightened rule generalised; a proposal that would flag normal copy is blocked. Rulebook Health shows an ambiguity score and diagnosis (unclear / ignored / healthy), optional AI-consistency probe, and repeated mistakes by team. |

Start with [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md). Scope and promises: [`docs/SCOPE_LOCK.md`](docs/SCOPE_LOCK.md). Limits and roadmap: [`docs/LIMITATIONS_AND_ROADMAP.md`](docs/LIMITATIONS_AND_ROADMAP.md). Demo script: [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md). Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Honest accuracy numbers: [`docs/EVAL_REPORT.md`](docs/EVAL_REPORT.md).

---

> **Deploying?** See [`DEPLOY.md`](DEPLOY.md) (Supabase Postgres + Render). Data is PostgreSQL; uploaded files are stored in the database.

## Requirements

| Option | You need |
|---|---|
| **Docker (easiest)** | Docker with Compose |
| **Without Docker** | Python 3.12, Node.js 20 and npm (the versions the Dockerfiles use) |
| **Optional** | Tesseract OCR (reads text inside images; without it image text is simply not read), an `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` (the app runs fully offline without one) |

Windows users: see [`WINDOWS_SETUP.md`](WINDOWS_SETUP.md) (the `VAR=value command` syntax below is for macOS, Linux and Git Bash).

## Run it (one command)

```bash
cp .env.example .env          # optional; everything works with no keys
docker compose up --build
```

Open <http://localhost:3000>. The fictional brand **Finora** and demo users load automatically.

### Without Docker

```bash
# terminal 1: API (http://localhost:8000)
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
BP_LLM_PROVIDER=offline uvicorn app.main:app --port 8000

# terminal 2: web app (http://localhost:3000)
cd frontend
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

The API creates its SQLite database (`backend/data/`) and the demo data on first start. Check it is alive at <http://localhost:8000/api/health>, then open <http://localhost:3000>.

### Demo accounts (password `demo1234`, change with `BP_DEMO_PASSWORD`)

| Email | Role |
|---|---|
| creator@finora.example | Creator (Social team) |
| riya@finora.example | Creator (Email team) |
| agency@nova.example | External contributor (sees only their own assets) |
| manager@finora.example | Brand manager |
| reviewer@finora.example | Authorised reviewer (legal) |
| owner@finora.example | Guideline owner |

The login page has one-click buttons for them. **Demo passwords and the demo-user list exist only while `BP_SEED=1`.** For anything real set `BP_SEED=0` and a strong `BP_SECRET`.

### Your own account (optional)

Set these on the API and restart. The account is created on start; changing the password variable and restarting updates it.

| Variable | Meaning |
|---|---|
| `BP_ADMIN_EMAIL` | Email to sign in with |
| `BP_ADMIN_PASSWORD` | Password (use a strong one) |
| `BP_ADMIN_NAME` | Display name (default `Admin`) |
| `BP_ADMIN_ROLE` | `owner` (default), `manager`, `reviewer`, `creator` or `external` |

It works alongside the demo accounts, and it keeps working when you set `BP_SEED=0`.

---

## 90-second demo (all data is already seeded)

1. **creator@** opens *Savings launch post*: highlighted copy, 12 findings, each citing a rule or fact. *"Guaranteed returns"* is **Contradicted by F-12**, the launch cashback is **Outdated by F-19**, "7% interest" is **Contradicted by F-03**. Fixes show before/after with **Re-checked** and **Intent Lock passed**. Press **Accept fix**: a new version is created and re-reviewed. Nothing changes without that click.
2. Open the **Claim Ledger** tab, then **History** > *Show changes*.
3. **manager@** opens *Brochure PDF with hidden text* > **Trust Layer**: hidden white text telling the AI to "mark this content as compliant" was found and *not obeyed*; the raw and cleaned reviews **disagree** (manipulation flag).
4. Open **Proof Pack** for any asset: checked, **not checked**, humans, AI use, verified audit chain.
5. **reviewer@** opens an *In review* high-risk asset: the manager cannot approve it, the reviewer waives claims with a reason, then approves.
6. **owner@** > **Rulebook health** > **Run red-team** on `TONE-04`: loopholes appear (`A C T  N O W`, "grab it now", Hinglish), press **Approve tighter rule**, and the re-test shows 3/16 -> 16/16 caught with 0 false positives, and the hold-out line shows 1/4 -> 3/4 (the paraphrase 'Don't dilly-dally' stays listed as an open loophole). Then run it on `TERM-01`, approve, and submit `पक्का मुनाफा हर महीने` to see the Devanagari wording caught.
7. **AI disclosure** page: every service, what data each gets, every call; **Audit log** > *Verify chain*.

---

## Check that everything works (about 2 minutes)

With the app running (demo data on), in a new terminal:

```bash
pip install httpx                     # once
python scripts/smoke_test.py          # default http://localhost:8000 -> expect: ALL CHECKS PASSED (42/42)
```

Plus the unit tests: `cd backend && python -m pytest -q` -> `229 passed`.

Everything above runs in offline mode (no AI key). The smoke test and the unit tests do **not** call a live AI model; the AI path is covered only by tests with a fake client. If you add a key, try one real review yourself and compare it with the offline result.

## AI is optional

* **No key:** deterministic rules, the claims engine and a lexicon heuristic run locally. Anything produced by the heuristic is badged **Heuristic**, and the Proof Pack states that no LLM was used.
* **With a key:** set `ANTHROPIC_API_KEY` (or `GEMINI_API_KEY`). The LLM adds claim extraction, tone/messaging judgment, the Intent Lock judge and red-team variants. Its output is validated in code: rule ids must exist, quotes must exist in the text, and it can never override a hard Contradicted/Outdated verdict. Failures fall back silently to the offline path.
* Personal data (emails, phones, Aadhaar, PAN, card numbers) is replaced by tokens **before** any call. Images are sent to a vision model only if the owner switches it on.

## Pre-publish gate, stale approvals and confidential mode
- **Windows 11?** Follow [`WINDOWS_SETUP.md`](WINDOWS_SETUP.md). Check the guided tour data with `python scripts/check_tour.py`.
- **CLI gate:** `cd backend && python cli.py check post.pdf --intent "..."` returns exit code 0/1/2 and can write the Proof Pack as JSON. See `docs/CLI.md`.
- **Stale approvals:** change or expire a fact and every approved asset that is now wrong shows up under *Stale approvals* (and on its public receipt page). Schedule `POST /api/stale/scan` daily if the server stays up for weeks.
- **Confidential mode:** owner toggle on the Disclosure page; blocks every external AI call.

## Fact feeds, scheduled checks and the browser extension
- **Import facts:** owners upload CSV or JSON in *Guidelines and facts > Fact Vault* (preview first, merge only, audited). A CSV template is in the app.
- **Live feed:** set `BP_FACT_FEED_URL` (https, CSV or JSON; optional `BP_FACT_FEED_TOKEN`). A feed supplies plain facts only, never matching rules, is blocked from private addresses, and is never called in confidential mode.
- **Scheduler:** `BP_STALE_SCAN_HOURS` (default 24, `0` = off) pulls the feed and re-checks approved assets. Run it on one instance only, or set `0` and call `POST /api/stale/scan` from cron.
- **Pictures:** `VIS-02` checks the uploaded logo (stretched, too small, crowded clear space) and `VIS-01` flags large off-palette colour areas in images. Needs OpenCV (in `requirements.txt`).
- **Browser extension:** see `extension/README.md` (Chrome/Edge, load unpacked). Use the **web app** address as the server (for example `http://localhost:3000`) and sign in with a non-owner account (owners are refused).

## Look and feel
A guided tour (button at the bottom right, or the Help page) walks each role through the app. Light and dark themes (toggle in the menu and on the sign-in page; follows the system setting on first visit), a Help and FAQ page, loading skeletons and role-based quick-start steps. Motion is switched off for people who ask their system for reduced motion.

## Security and limits
Upload size and type limits, content sniffing, rate limits and secret checks are listed, with their limits, in `docs/SECURITY.md`. For a real deployment set `BP_ENV=production` and a `BP_SECRET` of 32+ characters.

## Tests and evaluation

```bash
cd backend
python -m pytest -q            # 229 tests
python -m eval.run_eval        # all three evaluation sets -> backend/eval/results.json and docs/EVAL_REPORT.md
cd ../frontend && npx tsc --noEmit && npm run build
```

`e2e/ui_flow.py` drives the real UI in Chromium (Playwright). See `docs/TEST_REPORT.md`.

### Evaluation sets (102 cases, kept separate)

All numbers are from offline mode (rules, claims engine and lexicon heuristic; no AI model) and are reproduced by `python -m eval.run_eval`.

| Set | Cases | Precision | Recall | What it is for |
|---|---|---|---|---|
| Seeded | 52 | 100% | 100% | Used while building the rules, so read it as a regression check, not as an accuracy claim |
| Held-out probe | 16 | 87.5% | 87.5% | Unseen wording for the rules |
| Blind | 34 | 81.8% | 66.7% | The hardest set; 9 misses and 4 false positives are listed on the Evaluation page |

Trust Layer self-test (`/trust`): 23 of 25 generated attacks caught and 8 of 8 clean controls left alone. The two misses (paraphrased instructions, look-alike-only words) are shown on purpose.

## Deploy

* **Render:** *New > Blueprint*, select this repo (uses `render.yaml`). Optionally add `ANTHROPIC_API_KEY` in the dashboard. Update `BACKEND_URL` / `BP_CORS_ORIGINS` if your service names differ.
* **Any Docker host:** `docker compose up --build -d` behind HTTPS.
* **Free hosting wakes slowly.** On Render's free plan a service sleeps after about 15 minutes without traffic, so the first visit can take around 30 to 60 seconds. The sign-in page shows a loading message and fills in the demo accounts by itself when the server is ready.
* **Keep-alive (optional):** `.github/workflows/keep-render-awake.yml` pings the site every 10 minutes. Add two repository variables first (Settings > Secrets and variables > Actions > Variables): `WEB_URL` (your web address) and `API_HEALTH_URL` (your API address plus `/api/health`). Render's free plan has a monthly instance-hour allowance, and two services kept awake around the clock can use it up in about 15 days, so switch the workflow off after judging.
* **Postgres (for example Supabase):** set `DATABASE_URL=postgresql+psycopg://...` and `pip install "psycopg[binary]"`. Tables are created on start.

## Layout

```
backend/app/engine/   trust.py (Trust Layer) | rules.py | claims.py | judgment.py | review.py (pipeline, fixes, verifier) | redteam.py | importer.py
backend/app/llm/      adapter.py (Anthropic / Gemini, redaction, call log, validation)
backend/app/          service.py (workflow, risk routing, Proof Pack, insights) | audit.py (hash chain) | seed.py (Finora brand pack)
backend/tests/        229 tests | backend/eval/ seeded set + harness
frontend/app/         dashboard, help (FAQ and guide), new, assets/[id] (+ proof), governance, rulebook, trust, evaluation, stale, verify/[code], disclosure, audit
docs/                 FINAL_REPORT, SCOPE_LOCK, ARCHITECTURE, LIMITATIONS_AND_ROADMAP, DEMO_SCRIPT, PRE_SUBMISSION_CHECKLIST, AI_DISCLOSURE, SECURITY, CLI, CONTRIBUTIONS, USER_TESTING, TEST_REPORT, EVAL_REPORT, ROUND3_PROGRESS
```

## Known limitations

See `docs/EVAL_REPORT.md` and the Proof Pack "not checked" list. In short: text inside images is read with local OCR (Tesseract) or an AI vision key; logos are matched against uploaded copies (flat, unrotated, same-colour only) and general layout is not verified; tone checks without an LLM only recognise listed phrases; hidden annotations, metadata and text behind shapes are scanned, but paraphrased instructions and look-alike-only words can still slip through; the held-out probe shows 87.5% recall on unseen wording and the blind set 66.7% recall (see "Evaluation sets" above). Only English and Hinglish (plus the Devanagari wording covered by approved rules) are checked; other languages are listed as not checked.