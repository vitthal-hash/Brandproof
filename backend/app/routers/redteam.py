from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit, service
from ..db import RedTeamRun, Rule, RuleProposal, User, get_db
from ..engine import redteam
from ..llm.adapter import Gateway
from ..security import current_user, require
from .common import need, ser_rule

router = APIRouter(prefix="/api")


def _current(db: Session, rule_id: str) -> Rule:
    return need(db.execute(select(Rule).where(Rule.rule_id == rule_id, Rule.is_current.is_(True))).scalar_one_or_none(), "Rule")


def ser_run(r: RedTeamRun, p: RuleProposal | None) -> dict:
    return {"id": r.id, "rule_id": r.rule_id, "rule_version": r.rule_version, "created_by": r.created_by,
            "created_at": r.created_at.isoformat(timespec="seconds"), "summary": r.summary, "results": r.results,
            "proposal": None if p is None else {"id": p.id, "status": p.status, "rationale": p.rationale,
                                                "base_version": p.base_version, "proposed_params": p.proposed_params,
                                                "retest": p.retest}}


class RunBody(BaseModel):
    rule_id: str


@router.post("/redteam/run")
def run(b: RunBody, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    if b.rule_id not in redteam.ELIGIBLE:
        raise HTTPException(422, f"Red-team v1 supports: {', '.join(sorted(redteam.ELIGIBLE))}")
    rule = _current(db, b.rule_id)
    results, summary = redteam.run_variants(rule, Gateway(db))
    row = RedTeamRun(rule_id=rule.rule_id, rule_version=rule.version, created_by=user.email,
                     source="+".join(summary["sources"]), variants=[], results=results, summary=summary)
    db.add(row)
    db.flush()
    prop = None
    if summary["missed"]:
        params, why = redteam.propose(rule, results)
        prop = RuleProposal(run_id=row.id, rule_id=rule.rule_id, base_version=rule.version, proposed_params=params, rationale=why)
        prop.retest = redteam.retest(rule, results, params)
        db.add(prop)
    audit.log(db, user.email, "redteam.run", "rule", rule.rule_id, {"missed": summary["missed"], "total": summary["total"]})
    db.commit()
    return ser_run(row, prop)


@router.get("/redteam/runs")
def runs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    for r in db.execute(select(RedTeamRun).order_by(RedTeamRun.id.desc()).limit(30)).scalars():
        p = db.execute(select(RuleProposal).where(RuleProposal.run_id == r.id)).scalar_one_or_none()
        out.append(ser_run(r, p))
    return out


class PropDecision(BaseModel):
    action: str  # approve | reject


@router.post("/redteam/proposals/{pid}/decision")
def decide(pid: int, b: PropDecision, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    p = need(db.get(RuleProposal, pid), "Proposal")
    if p.status != "pending":
        raise HTTPException(409, f"Proposal already {p.status}")
    if b.action == "reject":
        p.status = "rejected"
    elif b.action == "approve":
        cur = _current(db, p.rule_id)
        cur.is_current = False
        new = Rule(rule_id=cur.rule_id, version=cur.version + 1, title=cur.title, category=cur.category, severity=cur.severity,
                   description=cur.description, method=cur.method, params=p.proposed_params, status="approved",
                   is_current=True, source=cur.source, created_by=f"{user.email} (red-team proposal #{p.id})")
        db.add(new)
        p.status = "approved"
    else:
        raise HTTPException(422, "action must be approve or reject")
    audit.log(db, user.email, f"redteam.proposal.{b.action}", "rule", p.rule_id, {"proposal": p.id})
    db.commit()
    run_row = db.get(RedTeamRun, p.run_id)
    return ser_run(run_row, p)


@router.post("/redteam/proposals/{pid}/retest")
def retest_proposal(pid: int, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    p = need(db.get(RuleProposal, pid), "Proposal")
    run_row = need(db.get(RedTeamRun, p.run_id), "Run")
    rule = _current(db, p.rule_id)
    base = [{k: v for k, v in r.items() if k != "caught"} for r in run_row.results]
    before = redteam.evaluate(rule, base)  # against whatever is live now
    after = redteam.retest(rule, run_row.results, p.proposed_params)
    p.retest = {**after, "live_caught_now": sum(1 for r in before if r["caught"])}
    audit.log(db, user.email, "redteam.retest", "rule", p.rule_id, {"proposal": p.id, "after": after["after_caught"]})
    db.commit()
    return ser_run(run_row, p)


@router.get("/rulebook")
def rulebook(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ins = service.insights(db)
    latest: dict = {}
    for r in db.execute(select(RedTeamRun).order_by(RedTeamRun.id)).scalars():
        latest[r.rule_id] = {"run_id": r.id, "total": r.summary.get("total"), "missed": r.summary.get("missed"),
                             "caught": r.summary.get("caught"), "rule_version": r.rule_version}
    rules = {r.rule_id: r for r in db.execute(select(Rule).where(Rule.is_current.is_(True))).scalars()}
    rows = []
    seen = set()
    for x in ins["rules"]:
        seen.add(x["rule_id"])
        rows.append({**x, "redteam": latest.get(x["rule_id"]), "eligible": x["rule_id"] in redteam.ELIGIBLE,
                     "version": rules[x["rule_id"]].version if x["rule_id"] in rules else None})
    for rid in sorted(redteam.ELIGIBLE - seen):
        if rid in rules:
            rows.append({"rule_id": rid, "title": rules[rid].title, "hits": 0, "assets": 0, "decided": 0,
                         "override_rate": 0.0, "ambiguous": False, "accepted": 0, "edited": 0, "rejected": 0, "waived": 0,
                         "open": 0, "redteam": latest.get(rid), "eligible": True, "version": rules[rid].version})
    return {"rules": rows, "repeated_by_team": ins["repeated_by_team"]}
