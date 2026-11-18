# Team contributions

Team CodeMonks | Vishwakarma Institute of Technology, Pune

## How this baseline was produced

The first complete implementation of BrandProof (code, tests, seed data, evaluation harness, documentation) was **generated with Claude** at the team's direction (see `AI_DISCLOSURE.md`). Individual contributions must be described accurately: the table below lists each member's **area of ownership from the Round 1 plan**. The authoritative record of who changed what after this baseline is the Git history:

```bash
git shortlog -sn --all          # commits per author
git log --author="<name>" --stat
```

If a member's real work differs from the plan below, edit this file to match the commit history before submitting.

## Ownership (from the Round 1 plan)

| Member | Role | Areas of ownership in the repository |
|---|---|---|
| Vitthal Bhanudas More | AI and backend lead | `backend/app/engine/` (review pipeline, claims, judgment, verifier), `backend/app/llm/`, prompts, evaluation harness |
| Anandi Raju More | Frontend and UX lead | `frontend/` (screens, annotated viewer, accessibility), wireframes |
| Mugdha Amod Deshpande (team lead) | Security, data and quality lead | `backend/app/security.py`, `audit.py`, `engine/trust.py`, `backend/tests/`, CI, deployment files |
| Atharv Ramchandra Mane | Product, research and delivery lead | `backend/app/seed.py` brand pack, `docs/`, `docs/USER_TESTING.md` sessions, demo script, README |

## Team tasks for the build window

* Run the project, read the code of your area, and be ready to explain it and demonstrate a feature (judges may ask any member).
* Push the repository to GitHub, deploy it (see README), and run the 3-5 user sessions in `docs/USER_TESTING.md`.
