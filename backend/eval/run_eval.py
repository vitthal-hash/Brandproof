"""Run the seeded set through the real pipeline (offline mode, pinned date) and write docs/EVAL_REPORT.md.
Usage: python -m eval.run_eval   (from backend/)"""
import json
import os
import sys
import tempfile
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def main(write=True):
    tmp = tempfile.mkdtemp()
    os.environ.update(DATABASE_URL=f"sqlite:///{tmp}/eval.db", BP_STORAGE_DIR=f"{tmp}/files", BP_TODAY="2026-11-17",
                      BP_LLM_PROVIDER="offline", BP_SEED="0")
    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    from app import db, seed, service
    from app.db import Claim, User
    from sqlalchemy import select
    from eval.seeded_set import ITEMS, HELDOUT, INTENT

    db.init_engine()
    s = db.session()
    seed.seed_brand(s)
    user = s.execute(select(User).where(User.email == "creator@finora.example")).scalar_one()

    def evaluate(items):
        cat = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0, "items": 0})
        claim_total = claim_ok = 0
        claim_misses, rule_misses, false_pos = [], [], []
        findings_total = abstained = 0
        fixes = {"proposed": 0, "verified": 0, "withheld": 0}
        attacks = attacks_ok = 0
        clean_items = clean_ok = 0
        times = []
        for iid, category, kind, payload, ex in items:
            t0 = time.time()
            data = text = None
            mime, fname = "text/plain", ""
            if kind == "text":
                text = payload
            else:
                data = payload()
                mime, fname = ("application/pdf", "x.pdf") if kind == "pdf" else ("image/png", "x.png")
            a = service.create_asset(s, user, f"eval {iid}", INTENT, "social", ex.get("ai_generated", False),
                                     ex.get("alt_text", ""), text=text, data=data, mime=mime, filename=fname)
            times.append((time.time() - t0) * 1000)
            run = service.latest_run(s, a)
            fs = service.findings_of(s, run)
            flagged = {f.rule_id for f in fs}
            expect, ok = set(ex.get("expect", [])), set(ex.get("also_ok", []))
            c = cat[category]
            c["items"] += 1
            c["tp"] += len(expect & flagged)
            for r in expect - flagged:
                c["fn"] += 1
                rule_misses.append(f"{iid}: expected {r}")
            for r in flagged - expect - ok:
                c["fp"] += 1
                false_pos.append(f"{iid}: unexpected {r}")
            findings_total += len(fs)
            abstained += sum(1 for f in fs if f.needs_human)
            for f in fs:
                if f.fix:
                    fixes["proposed"] += 1
                    fixes[f.fix["status"]] += 1
            if ex.get("clean"):
                clean_items += 1
                clean_ok += (not fs)
            for frag, want in ex.get("expect_claims", {}).items():
                cl = s.execute(select(Claim).where(Claim.run_id == run.id)).scalars().all()
                got = [x.verdict for x in cl if frag.lower() in x.text.lower()]
                claim_total += 1
                if got and want in got:
                    claim_ok += 1
                else:
                    claim_misses.append(f"{iid}: '{frag}' expected {want}, got {got or 'no claim found'}")
            if ex.get("attack"):
                attacks += 1
                attacks_ok += expect <= flagged

        def pr(c):
            tp, fp, fn = c["tp"], c["fp"], c["fn"]
            return (tp / (tp + fp) if tp + fp else 1.0), (tp / (tp + fn) if tp + fn else 1.0)
        tot = {"tp": sum(c["tp"] for c in cat.values()), "fp": sum(c["fp"] for c in cat.values()), "fn": sum(c["fn"] for c in cat.values())}
        P, R = pr(tot)
        return {"items": len(items), "precision": round(P, 3), "recall": round(R, 3),
                "claim_verdict_accuracy": round(claim_ok / claim_total, 3) if claim_total else None, "claims_checked": claim_total,
                "injection_resistance": f"{attacks_ok}/{attacks}", "clean_controls_with_zero_findings": f"{clean_ok}/{clean_items}",
                "abstention_rate": round(abstained / max(findings_total, 1), 3), "fixes": fixes,
                "avg_review_ms": round(sum(times) / len(times)),
                "by_category": {k: {**v, "precision": round(pr(v)[0], 2), "recall": round(pr(v)[1], 2)} for k, v in cat.items()},
                "misses": rule_misses, "false_positives": false_pos, "claim_misses": claim_misses}

    res = evaluate(ITEMS)
    held = evaluate(HELDOUT)
    # red-team on the four eligible rules
    from app.engine import redteam
    from app.seed import RULES
    from types import SimpleNamespace
    rt_rows = []
    for rid, title, cat_, sev, method, params, desc in RULES:
        if rid in redteam.ELIGIBLE:
            rule = SimpleNamespace(rule_id=rid, title=title, method=method, params=params, description=desc, severity=sev, version=1)
            rres, summ = redteam.run_variants(rule)
            p, why = redteam.propose(rule, rres)
            rt = redteam.retest(rule, rres, p)
            rt_rows.append((rid, summ["total"], rt["before_caught"], rt["after_caught"], len(rt["false_positives"])))
    s.close()

    res["redteam"] = [{"rule": r, "variants": t, "caught_before": b, "caught_after_tightening": a_, "false_positives": f} for r, t, b, a_, f in rt_rows]
    res["heldout"] = held
    if write:
        with open(os.path.join(HERE, "results.json"), "w") as f:
            json.dump(res, f, indent=2)
        write_report(res)
    return res


def write_report(r):
    docs = os.path.join(os.path.dirname(os.path.dirname(HERE)), "docs")
    os.makedirs(docs, exist_ok=True)
    L = ["# BrandProof evaluation report (Round 2)", "",
         "Generated by `python -m eval.run_eval` on the seeded set (`backend/eval/seeded_set.py`), offline mode (deterministic rules, claims engine, "
         "lexicon heuristic; no LLM), date pinned to 2026-11-17. Re-run it to reproduce these numbers.", "",
         "## Headline numbers", "",
         f"| Metric | Result |", "|---|---|",
         f"| Items | {r['items']} |", f"| Rule-level precision | {r['precision']:.0%} |", f"| Rule-level recall | {r['recall']:.0%} |",
         f"| Claim-verdict accuracy | {r['claim_verdict_accuracy']:.0%} ({r['claims_checked']} labelled claims) |",
         f"| Injection / hidden-text attacks fully caught | {r['injection_resistance']} |",
         f"| Clean controls with zero findings | {r['clean_controls_with_zero_findings']} |",
         f"| Abstention rate (findings routed to a human as Needs human) | {r['abstention_rate']:.0%} |",
         f"| Fixes proposed / verified / withheld | {r['fixes']['proposed']} / {r['fixes']['verified']} / {r['fixes']['withheld']} |",
         f"| Average review time per item | {r['avg_review_ms']} ms |", "",
         "## By category", "", "| Category | Items | TP | FP | FN | Precision | Recall |", "|---|---|---|---|---|---|---|"]
    for k, v in r["by_category"].items():
        L.append(f"| {k} | {v['items']} | {v['tp']} | {v['fp']} | {v['fn']} | {v['precision']:.0%} | {v['recall']:.0%} |")
    L += ["", "## Misses and false positives (published, not hidden)", ""]
    for title, rows in (("Missed rules", r["misses"]), ("False positives", r["false_positives"]), ("Claim verdict misses", r["claim_misses"])):
        L.append(f"**{title}:** " + ("none in this set." if not rows else ""))
        L += [f"- {x}" for x in rows]
        L.append("")
    L += ["## Rulebook Red-Team (variants the reviewer should catch)", "",
          "| Rule | Variants | Caught before | Caught after tightening | False positives on benign copy |", "|---|---|---|---|---|"]
    for x in r["redteam"]:
        L.append(f"| {x['rule']} | {x['variants']} | {x['caught_before']} | {x['caught_after_tightening']} | {x['false_positives']} |")
    L += ["", "## How to read these numbers (limitations)", "",
          "- The seeded set was written by the team alongside the engine, so these numbers show regression safety and coverage, **not independent accuracy**. "
          "Expect lower results on real content.",
          "- Precision counts any finding outside `expect` and `also_ok` as a false positive. `also_ok` lists co-triggered findings that are legitimately correct for the text.",
          "- Tone and messaging use a lexicon heuristic when no LLM key is set. It only recognises listed phrases, so subtle tone problems are missed by design.",
          "- Red-team variants are partly hand-written and partly mechanical. The tightened rules were derived from the same variants they are re-tested on, so the "
          "'after' column shows the loop works, not that the rule is now complete. Run it again with a new variant set to find new loopholes.",
          "- Hidden-text detection covers white, same-colour-as-background, tiny, off-page, invisible and transparent text, HTML comments and zero-width characters. "
          "Text hidden behind images, in annotations or in images is not covered.",
          "- Image text is not read without an LLM vision key, so wording inside images is listed as not checked."]
    with open(os.path.join(docs, "EVAL_REPORT.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    out = main()
    print(json.dumps({k: v for k, v in out.items() if k not in ("by_category",)}, indent=1, ensure_ascii=False))
