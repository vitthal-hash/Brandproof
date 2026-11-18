# User testing protocol and log (Round 2)

Goal: test the assumptions from the Round 1 plan with 3-5 volunteers (marketers, students running a social account, agency staff). Sessions take about 20 minutes. Use the demo data; never use real customer information.

## Setup

Open the deployed link (or `docker compose up`). Give the volunteer the **creator@finora.example** login. Ask for consent to take notes; record only first names and roles.

## Tasks (read aloud, do not help)

1. "Open *Savings launch post* and tell me what is wrong with it. How do you know?"
2. "Fix the copy so it is safe to publish. Keep the message: announce our new savings account."
3. "Imagine your manager asks why this was approved. What would you show?" (observe whether they find the Proof Pack)
4. *(Reviewer/manager volunteers)* "Open *Brochure PDF with hidden text*. Would you approve it? Why?"

## Questions after the tasks

* Which finding did you trust least? Why?
* Did any suggested fix change what you meant?
* What was missing or confusing?
* Would you use this before publishing? What would stop you?

## Measure (per session)

Time to understand the first finding; fixes accepted / edited / rejected; confusion points; whether they found the Claim Ledger, Trust tab and Proof Pack unaided; manual baseline (how long the volunteer takes to review the same post without the tool).

## Log (fill in after each session; one row per volunteer)

| # | Role (no surname) | Date | Manual baseline (min) | With BrandProof (min) | Accepted / edited / rejected | Biggest confusion | Quote | Change we made |
|---|---|---|---|---|---|---|---|---|
|   |   |   |   |   |   |   |   |   |

Assumptions under test: (1) reviewers cannot easily show why an asset was approved; (2) unsupported claims are the riskiest and least-checked items; (3) creators accept fixes that keep their intent; (4) rules often contain loopholes; (5) reviewers trust a Proof Pack more than a score.
