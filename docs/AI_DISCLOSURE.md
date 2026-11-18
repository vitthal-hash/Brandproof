# AI, models, libraries and services used (Round 2 disclosure)

## 1. AI assistance in building this project (required disclosure)

**The source code, tests, evaluation set, seed data and documentation in this repository were generated with Anthropic's Claude (Claude Sonnet 5.5, via the claude.ai chat interface) at the direction of Team CodeMonks**, working from the team's Round 1 plan. The Round 1 submission PDF was also drafted with Claude's help. Team members are responsible for reviewing, running, understanding and explaining everything here.

Generated components include: the FastAPI backend, the Trust Layer, claim engine, verifier, red-team engine, the Next.js frontend, the Finora brand pack, the 52-item seeded set and 16-item held-out probe, and all files under `docs/`.

## 2. AI models used by the running product

| Model | When | Data it receives |
|---|---|---|
| None (default) | Deterministic rules, claim engine, lexicon heuristic | Nothing leaves the server |
| Anthropic Claude, model set by `BP_ANTHROPIC_MODEL` (default `claude-sonnet-5-5`), only if `ANTHROPIC_API_KEY` is set | Claim extraction, tone/messaging judgment, Intent Lock judge, red-team variants, optional image text reading | **Redacted** text only (emails, phones, Aadhaar, PAN, card numbers replaced by tokens). Images only if the guideline owner enables it |
| Google Gemini, `BP_GEMINI_MODEL` (default `gemini-2.0-flash`), only if `GEMINI_API_KEY` is set and no Anthropic key | Same as above | Same as above |

Every call is recorded (time, model, purpose, characters sent, items redacted, status) and listed on the in-app **AI disclosure** page and in each Proof Pack.

## 3. Libraries and licences

| Library | Use | Licence |
|---|---|---|
| FastAPI, Starlette, Uvicorn | API server | MIT / BSD |
| SQLAlchemy | Database layer | MIT |
| Pydantic | Request validation | MIT |
| PyJWT | Auth tokens | MIT |
| python-multipart | Uploads | Apache-2.0 |
| httpx | LLM HTTP calls | BSD-3 |
| **PyMuPDF** | PDF parsing, hidden-text detection, page preview | **AGPL-3.0** (or commercial): see note |
| Pillow | Image colours, test images | HPND |
| pytest | Tests | MIT |
| Next.js, React | Frontend | MIT |
| Tailwind CSS, PostCSS, Autoprefixer | Styling | MIT |
| TypeScript | Types | Apache-2.0 |
| Playwright (test only, `e2e/`) | Browser test | Apache-2.0 |

*Note on PyMuPDF:* its AGPL licence applies if this software is distributed or offered as a network service. This repository is published for evaluation. For commercial use, replace it (for example with pypdf/pdfminer, losing some hidden-text signals) or obtain a commercial licence.

## 4. Datasets, templates and services

* **No external datasets.** The fictional brand "Finora", its 22 rules, 24 facts, demo users and demo assets, and the evaluation sets are synthetic and were written for this project (with Claude).
* **No templates or boilerplate** beyond what `create-next-app`-style configuration requires (hand-written config files). Fonts: system fonts only.
* **External services:** none by default. Optionally Anthropic API and Google Gemini API (see section 2). Hosting is the team's choice (Render or any Docker host).
* Regulatory material (ASCI guidelines, IT Rules) was used only to shape the style of the example rule pack; it is **not legal advice**, and rules are illustrative.
