# BrandProof architecture and main technical decisions

## 1. Big picture

```
Browser (Next.js 14, Tailwind)  --/api proxy-->  FastAPI (Python)
                                                  |
   upload --> TRUST LAYER --> DETERMINISTIC RULES --> CLAIM LEDGER --> JUDGMENT (LLM or heuristic)
              parse, find        terms, tone, caps,     claims vs the     must cite a rule and quote
              hidden text,       offer date, T&C,       dated Fact        real text, or abstain
              injection scan,    AI label, PII,         Vault
              redact             contrast, palette
                                                  |
                    FIX BUILDER --> VERIFIER (re-review + Intent Lock) --> findings stored
                                                  |
   humans: comments, accept/edit/reject, waive, risk-routed approval --> PROOF PACK + hash-chained AUDIT LOG
   owner:  guidelines, Fact Vault, library, RED-TEAM loop (loophole -> tighter rule -> approve -> re-test)

   SQLAlchemy (SQLite by default, Postgres via DATABASE_URL)   local file storage   optional LLM API (Anthropic / Gemini)
```

## 2. The hard problem and how each layer answers it

Producing verdicts a reviewer can trust from an AI that can hallucinate, misjudge colour and be manipulated by the content it reads.

| # | Line of defence | Where | What it stops |
|---|---|---|---|
| 1 | Deterministic checks first | `engine/rules.py`, `engine/review.py: file_checks` | Wrong answers on exact things (terms, caps, dates, WCAG contrast, colour distance) |
| 2 | Grounded output | `engine/judgment.py`, `engine/claims.py` | Every finding cites a rule id and/or fact id; AI quotes must exist in the text; unknown rule ids are dropped |
| 3 | Abstention | `config.CONFIDENCE_FLOOR`, `Finding.needs_human` | Low confidence becomes "Needs human" and blocks approval until a person decides |
| 4 | Verifier + Intent Lock | `review.verify_fix`, `review.intent_lock` | Fixes that do not resolve the finding, introduce new violations, or change what the creator meant are **withheld** and counted |
| 5 | Sanitiser + differential review | `engine/trust.py`, `review.differential` | Hidden text, zero-width tricks, HTML comments, prompt injection; raw vs cleaned verdict mismatch raises TRUST-02 |
| 6 | Evaluation + red-team | `backend/eval/`, `engine/redteam.py` | Silent failures and rule loopholes are measured and published |

## 3. Key technical decisions (and why)

1. **Verdicts come from code, not the model.** The Claim Ledger compares numbers, patterns and dates against structured Fact Vault entries (`claims.judge`). An LLM may only add claims or resolve "Needs human" ones, and only with confidence >= 0.8; it cannot override Contradicted or Outdated.
2. **LLM is optional and sandboxed.** `llm/adapter.py` redacts personal data in every prompt, wraps content in `<untrusted_content>` tags, validates JSON, logs every call and never raises into the pipeline. Without a key the product still runs and says so (provider `offline`, method badge `Heuristic`).
3. **Fixes are proposals that are re-reviewed.** `build_fix` creates a span replacement; `verify_fix` re-runs the offline analysis on the fixed text (finding gone, no new high/medium findings) and runs Intent Lock (intent keywords kept, text still similar; plus an LLM judge when available). Accepting a fix creates a **new version** and re-reviews it.
4. **Multiset signatures for before/after comparison.** Findings are compared as counted signatures; rule-level findings (T&C line, AI label) use a stable signature so a legitimate fix is not mistaken for a new problem.
5. **Differential review only when needed.** If raw and cleaned text are identical the review runs once. Otherwise both are analysed and the difference is reported in plain language.
6. **Roles are enforced on the server.** `service.py` and `security.require` check every action; the UI hides buttons but is not trusted.
7. **Tamper-evident audit log.** Each row stores `sha256(prev_hash + row)`. `GET /api/audit/verify` recomputes the chain; tests edit and delete rows and expect detection.
8. **Retention.** If the owner enables "delete after approval", files, text and finding quotes are purged; the Proof Pack, hashes and audit log remain.
9. **Database portability.** SQLAlchemy with portable column types. SQLite for zero-setup; set `DATABASE_URL` for Postgres (Supabase is Postgres). Auth is our own JWT (HS256) with PBKDF2 passwords.
10. **No vector database.** Facts and rules are small enough to be matched by keyword/pattern in code, which keeps verdicts explainable and repeatable.

## 4. Data model (tables)

`users` | `rules` (versioned: rule_id + version, `is_current`, `status` draft/approved) | `facts` (statement, keywords, patterns, numeric limit, rewrite, source, owner, valid_to) | `library` (terms, palette, competitors, logos) | `assets` | `asset_versions` (kind, text_raw, text_clean, sha256, file) | `review_runs` (provider, model, trust, differential, summary, not_checked) | `findings` (rule/fact citation, method, verdict, confidence, fix, status) | `claims` | `comments` | `audit` (hash chain) | `llm_calls` | `redteam_runs` | `rule_proposals` | `settings`.

## 5. Workflow and risk routing

States: Draft, Auto-reviewed, Changes requested, In review, Approved.

| Role | Can |
|---|---|
| Creator / External contributor | create assets, accept/edit/reject fixes on **own** assets, comment, submit. External sees only their own assets; creators see their team's |
| Brand manager | see all, comment, request changes, waive medium/low findings, approve **normal-risk** assets |
| Authorised reviewer | everything a manager can, plus waive **high-severity** findings and approve **high-risk** assets |
| Guideline owner | rules (versioned), imports, Fact Vault, library, red-team, settings; cannot submit content |

An asset is **high risk** while any high-severity finding is open or rejected. Approval is blocked until every high-risk finding and every open "Needs human" finding is fixed, waived (with a reason) or decided.

## 6. Hidden-text detection (PyMuPDF text trace)

Spans are classified hidden when: render mode is invisible; opacity < 5%; font size < 3 pt; the box lies outside the page; or the text colour is within contrast 1.25 of its background (background = topmost filled rectangle under the span, else white). Visible text with weak contrast is a separate WCAG finding. Not covered: text hidden behind images, in annotations/metadata, or inside images.

## 7. Limits we state openly

* Heuristic tone checks only know listed phrases (see held-out misses in `EVAL_REPORT.md`).
* Colour checks cover text colours, filled rectangles and flat image colours, not gradients or photos.
* Claims from facts in Hinglish are matched through phrase variants, not transliteration.
* One organisation per deployment; no SSO; local file storage.
