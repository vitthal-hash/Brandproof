"""Business logic shared by the routes, the seed script and the tests."""
import difflib
import hashlib

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import audit, config, storage
from .db import (Asset, AssetVersion, Claim, Comment, Finding, LlmCall, ReviewRun, Setting, User, utcnow)
from .engine import review
from .engine import textutil as tu
from .llm.adapter import Gateway

OPEN_STATES = ("open", "rejected")


# ------------------------------------------------------------------ access
def can_view(user: User, asset: Asset) -> bool:
    if user.role in ("manager", "reviewer", "owner"):
        return True
    if asset.owner_id == user.id:
        return True
    if user.role == "creator":
        return asset.owner.team == user.team and user.team != ""
    return False


def get_asset(db: Session, user: User, asset_id: int) -> Asset:
    a = db.get(Asset, asset_id)
    if not a or not can_view(user, a):
        raise HTTPException(404, "Asset not found")
    return a


def latest_version(db: Session, asset: Asset) -> AssetVersion:
    return db.execute(select(AssetVersion).where(AssetVersion.asset_id == asset.id)
                      .order_by(AssetVersion.n.desc()).limit(1)).scalar_one()


def latest_run(db: Session, asset: Asset, version: AssetVersion | None = None) -> ReviewRun | None:
    q = select(ReviewRun).where(ReviewRun.asset_id == asset.id)
    if version is not None:
        q = q.where(ReviewRun.version_id == version.id)
    return db.execute(q.order_by(ReviewRun.id.desc()).limit(1)).scalar_one_or_none()


def findings_of(db: Session, run: ReviewRun | None) -> list[Finding]:
    if run is None:
        return []
    return db.execute(select(Finding).where(Finding.run_id == run.id).order_by(Finding.id)).scalars().all()


def compute_risk(db: Session, asset: Asset) -> str:
    run = latest_run(db, asset)
    for f in findings_of(db, run):
        if f.severity == "high" and f.status in OPEN_STATES:
            return "high"
    return "normal"


def blocking_findings(db: Session, asset: Asset) -> list[Finding]:
    run = latest_run(db, asset)
    return [f for f in findings_of(db, run)
            if (f.severity == "high" and f.status in OPEN_STATES) or (f.needs_human and f.status == "open")]


# ------------------------------------------------------------------ assets and versions
def _kind_for(mime: str, filename: str) -> str:
    n = (filename or "").lower()
    if mime == "application/pdf" or n.endswith(".pdf"):
        return "pdf"
    if mime.startswith("image/") or n.endswith((".png", ".jpg", ".jpeg")):
        return "image"
    return "text"


def _new_version(db: Session, asset: Asset, user: User, kind: str, text: str | None, data: bytes | None,
                 mime: str, note: str) -> AssetVersion:
    n = asset.current_version + 1
    path = ""
    if data is not None and kind in ("pdf", "image"):
        ext = ".pdf" if kind == "pdf" else (".png" if "png" in mime else ".jpg")
        path = storage.save(f"assets/{asset.id}/v{n}{ext}", data, db)
    digest = hashlib.sha256(data if data is not None else (text or "").encode()).hexdigest()
    v = AssetVersion(asset_id=asset.id, n=n, kind=kind, text_raw=text or "", text_clean="", file_path=path,
                     mime=mime, sha256=digest, note=note, created_by=user.email)
    db.add(v)
    asset.current_version = n
    asset.updated_at = utcnow()
    db.flush()
    return v


def _run(db: Session, asset: Asset, version: AssetVersion, user: User, gateway: Gateway | None = None):
    gw = gateway or Gateway(db)
    run = review.run_review(db, asset, version, user.email, gw)
    asset.risk = compute_risk(db, asset)
    return run


def create_asset(db: Session, user: User, title: str, intent: str, channel: str, ai_generated: bool, alt_text: str,
                 text: str | None = None, data: bytes | None = None, mime: str = "text/plain", filename: str = "",
                 gateway: Gateway | None = None) -> Asset:
    if not title.strip() or len(intent.strip()) < 5:
        raise HTTPException(422, "Title and a one-line intent are required")
    kind = _kind_for(mime, filename)
    if kind == "text" and not (text or "").strip():
        raise HTTPException(422, "Paste text or upload a file")
    if kind != "text" and not data:
        raise HTTPException(422, "Empty file")
    asset = Asset(title=title.strip(), intent=intent.strip(), channel=channel, owner_id=user.id, status="Draft",
                  ai_generated=ai_generated, alt_text=alt_text or "")
    db.add(asset)
    db.flush()
    asset.owner = user
    audit.log(db, user.email, "asset.create", "asset", asset.id, {"kind": kind, "title": asset.title})
    v = _new_version(db, asset, user, kind, text, data, mime, "Initial submission")
    audit.log(db, user.email, "version.create", "asset", asset.id, {"version": v.n, "sha256": v.sha256[:12]})
    _run(db, asset, v, user, gateway)
    asset.status = "Auto-reviewed"
    db.commit()
    return asset


def add_version(db: Session, user: User, asset: Asset, text: str | None = None, data: bytes | None = None,
                mime: str = "text/plain", filename: str = "", note: str = "", gateway: Gateway | None = None):
    if asset.owner_id != user.id and user.role not in ("manager",):
        raise HTTPException(403, "Only the owner can add a version")
    kind = _kind_for(mime, filename)
    v = _new_version(db, asset, user, kind, text, data, mime, note or "New version")
    audit.log(db, user.email, "version.create", "asset", asset.id, {"version": v.n, "sha256": v.sha256[:12]})
    _run(db, asset, v, user, gateway)
    asset.status = "Auto-reviewed"
    db.commit()
    return v


def rerun(db: Session, user: User, asset: Asset, gateway: Gateway | None = None):
    v = latest_version(db, asset)
    run = _run(db, asset, v, user, gateway)
    db.commit()
    return run


# ------------------------------------------------------------------ decisions
def decide(db: Session, user: User, f: Finding, action: str, text: str | None = None, note: str = "",
           gateway: Gateway | None = None) -> Finding:
    asset = get_asset(db, user, f.asset_id)
    if asset.status == "Approved":
        raise HTTPException(409, "Approved assets are locked; add a new version to reopen")
    latest = latest_version(db, asset)
    if f.version_id != latest.id:
        raise HTTPException(409, "This finding belongs to an older version")
    if f.status not in ("open", "rejected"):
        raise HTTPException(409, f"Finding already {f.status}")
    is_owner = asset.owner_id == user.id
    note = (note or "").strip()
    if action in ("accept_fix", "edit_fix"):
        if not is_owner:
            raise HTTPException(403, "Only the creator can accept or edit fixes")
        base = latest.text_clean
        if action == "edit_fix" and f.start < 0:
            raise HTTPException(422, "This finding is about the file itself; fix the design and upload a new version")
        if action == "accept_fix":
            fx = f.fix
            if not fx or fx.get("status") != "verified":
                raise HTTPException(422, "No verified fix is available for this finding")
            new = review.apply_fix(base, fx["start"], fx["end"], fx["replacement"])
        else:
            if text is None:
                raise HTTPException(422, "Provide the replacement text")
            new = review.apply_fix(base, f.start, f.end, text)
        f.status = "accepted" if action == "accept_fix" else "edited"
        f.decided_by, f.decided_note = user.email, note
        audit.log(db, user.email, "finding.decision", "finding", f.id,
                  {"action": action, "rule": f.rule_id, "asset": asset.id})
        v = _new_version(db, asset, user, "text", new, None, "text/plain",
                         f"{'Accepted' if action == 'accept_fix' else 'Edited'} fix for {f.rule_id} (finding #{f.id})")
        audit.log(db, user.email, "version.create", "asset", asset.id, {"version": v.n, "sha256": v.sha256[:12]})
        _run(db, asset, v, user, gateway)
        asset.status = "Auto-reviewed"
    elif action == "reject":
        if len(note) < 3:
            raise HTTPException(422, "A short reason is required to reject a finding")
        if not (is_owner or user.role in ("manager", "reviewer")):
            raise HTTPException(403, "Not allowed")
        f.status, f.decided_by, f.decided_note = "rejected", user.email, note
        audit.log(db, user.email, "finding.decision", "finding", f.id, {"action": action, "rule": f.rule_id, "asset": asset.id})
        asset.risk = compute_risk(db, asset)
    elif action == "waive":
        allowed = user.role == "reviewer" or (user.role == "manager" and f.severity != "high")
        if not allowed:
            raise HTTPException(403, "High-severity findings can only be waived by an authorised reviewer")
        if len(note) < 3:
            raise HTTPException(422, "A short reason is required to waive a finding")
        f.status, f.decided_by, f.decided_note = "waived", user.email, note
        audit.log(db, user.email, "finding.decision", "finding", f.id, {"action": action, "rule": f.rule_id, "asset": asset.id})
        asset.risk = compute_risk(db, asset)
    else:
        raise HTTPException(422, "Unknown action")
    asset.updated_at = utcnow()
    db.commit()
    return f


# ------------------------------------------------------------------ workflow
def workflow(db: Session, user: User, asset: Asset, action: str, note: str = "") -> Asset:
    note = (note or "").strip()
    if action == "submit":
        if asset.owner_id != user.id:
            raise HTTPException(403, "Only the creator can submit")
        if asset.status not in ("Auto-reviewed", "Changes requested"):
            raise HTTPException(409, f"Cannot submit from '{asset.status}'")
        asset.status = "In review"
    elif action == "request_changes":
        if user.role not in ("manager", "reviewer"):
            raise HTTPException(403, "Only managers and reviewers can request changes")
        if asset.status != "In review":
            raise HTTPException(409, "Only assets in review can be sent back")
        if len(note) < 3:
            raise HTTPException(422, "Say what needs to change")
        asset.status = "Changes requested"
        db.add(Comment(asset_id=asset.id, author=user.email, role=user.role, body=f"Changes requested: {note}"))
    elif action == "approve":
        if user.role not in ("manager", "reviewer"):
            raise HTTPException(403, "Only managers and reviewers can approve")
        if asset.status != "In review":
            raise HTTPException(409, "Only assets in review can be approved")
        asset.risk = compute_risk(db, asset)
        if asset.risk == "high" and user.role != "reviewer":
            raise HTTPException(403, "This asset has high-risk findings: an authorised reviewer must approve it")
        block = blocking_findings(db, asset)
        if block:
            raise HTTPException(409, f"{len(block)} finding(s) must be fixed, waived or decided first: "
                                + ", ".join(f"#{f.id} {f.rule_id}" for f in block[:6]))
        asset.status = "Approved"
        audit.log(db, user.email, "asset.approve", "asset", asset.id, {"role": user.role, "note": note})
        _retention(db, asset, user)
    else:
        raise HTTPException(422, "Unknown action")
    if action != "approve":
        audit.log(db, user.email, f"asset.{action}", "asset", asset.id, {"note": note})
    asset.updated_at = utcnow()
    db.commit()
    return asset


def get_setting(db: Session, key: str, default):
    row = db.get(Setting, key)
    return row.value.get("value", default) if row else default


def set_setting(db: Session, key: str, value):
    row = db.get(Setting, key)
    if row:
        row.value = {"value": value}
    else:
        db.add(Setting(key=key, value={"value": value}))


def _retention(db: Session, asset: Asset, user: User):
    if not get_setting(db, "retention_delete_after_approval", False):
        return
    for v in db.execute(select(AssetVersion).where(AssetVersion.asset_id == asset.id)).scalars():
        if v.file_path:
            storage.delete(v.file_path, db)
        v.file_path, v.text_raw, v.text_clean, v.purged = "", "", "", True
    for f in db.execute(select(Finding).where(Finding.asset_id == asset.id)).scalars():
        f.quote, f.fix = "[purged]", None
    run_ids = [r.id for r in db.execute(select(ReviewRun).where(ReviewRun.asset_id == asset.id)).scalars()]
    for c in db.execute(select(Claim).where(Claim.run_id.in_(run_ids))).scalars():
        c.text = "[purged]"
    audit.log(db, user.email, "retention.purge", "asset", asset.id, {"reason": "delete after approval"})


# ------------------------------------------------------------------ views
def diff_versions(db: Session, asset: Asset, a: int, b: int) -> list[dict]:
    va = db.execute(select(AssetVersion).where(AssetVersion.asset_id == asset.id, AssetVersion.n == a)).scalar_one_or_none()
    vb = db.execute(select(AssetVersion).where(AssetVersion.asset_id == asset.id, AssetVersion.n == b)).scalar_one_or_none()
    if not va or not vb:
        raise HTTPException(404, "Version not found")
    out = []
    for line in difflib.ndiff(va.text_clean.splitlines() or [""], vb.text_clean.splitlines() or [""]):
        if line[:2] in ("+ ", "- ", "  "):
            out.append({"op": {"+": "add", "-": "del", " ": "same"}[line[0]], "text": line[2:]})
    return out


def proofpack(db: Session, asset: Asset) -> dict:
    v = latest_version(db, asset)
    run = latest_run(db, asset, v)
    fs = findings_of(db, run)
    claims = db.execute(select(Claim).where(Claim.run_id == (run.id if run else -1)).order_by(Claim.start)).scalars().all()
    calls = db.execute(select(LlmCall).where(LlmCall.asset_id == asset.id)).scalars().all()
    ev = db.execute(select(audit.Audit).where(audit.Audit.entity_id == str(asset.id), audit.Audit.entity == "asset")
                    .order_by(audit.Audit.id)).scalars().all()
    versions = db.execute(select(AssetVersion).where(AssetVersion.asset_id == asset.id).order_by(AssetVersion.n)).scalars().all()
    waived = [f for f in fs if f.status == "waived"]
    return {
        "asset": {"id": asset.id, "title": asset.title, "intent": asset.intent, "status": asset.status,
                  "channel": asset.channel, "ai_generated": asset.ai_generated, "creator": asset.owner.email,
                  "team": asset.owner.team},
        "version": {"n": v.n, "kind": v.kind, "sha256": v.sha256, "created_at": v.created_at.isoformat(timespec="seconds"),
                    "purged": v.purged},
        "trust": (run.trust if run else {}), "differential": (run.differential if run else {}),
        "checks": (run.summary.get("checks") if run else {}), "summary": (run.summary if run else {}),
        "claim_ledger": [{"label": c.label, "text": c.text, "kind": c.kind, "verdict": c.verdict, "fact": c.fact_id,
                          "confidence": c.confidence} for c in claims],
        "findings": [{"id": f.id, "rule": f"{f.rule_id}@v{f.rule_version}", "severity": f.severity, "method": f.method,
                      "title": f.title, "status": f.status, "needs_human": f.needs_human, "decided_by": f.decided_by,
                      "note": f.decided_note, "facts": f.citation.get("facts", [])} for f in fs],
        "waived": [f"#{f.id} {f.rule_id} by {f.decided_by}: {f.decided_note}" for f in waived],
        "not_checked": (run.not_checked if run else []),
        "humans": [{"ts": a.ts, "actor": a.actor, "action": a.action, "detail": a.detail} for a in ev
                   if a.action in ("asset.submit", "asset.request_changes", "asset.approve", "finding.decision")],
        "comments": [{"author": c.author, "role": c.role, "body": c.body, "ts": c.created_at.isoformat(timespec="seconds")}
                     for c in db.execute(select(Comment).where(Comment.asset_id == asset.id).order_by(Comment.id)).scalars()],
        "ai_use": {"provider": run.provider if run else "offline", "model": run.model if run else "",
                   "calls": len(calls), "redactions": sum(c.redactions for c in calls),
                   "note": "Only redacted text is sent to an external model. Images are sent only if the owner enabled it."},
        "versions": [{"n": x.n, "note": x.note, "by": x.created_by, "sha256": x.sha256[:12]} for x in versions],
        "audit_chain": audit.verify(db),
        "generated_at": utcnow().isoformat(timespec="seconds"),
    }


def insights(db: Session) -> dict:
    assets = db.execute(select(Asset)).scalars().all()
    status_counts: dict = {}
    for a in assets:
        status_counts[a.status] = status_counts.get(a.status, 0) + 1
    rules: dict = {}
    by_team: dict = {}
    for a in assets:
        run = latest_run(db, a)
        for f in findings_of(db, run):
            if f.method == "trust":
                continue
            r = rules.setdefault(f.rule_id, {"rule_id": f.rule_id, "title": f.title if f.method == "rule" else f.rule_id,
                                             "hits": 0, "assets": set(), "accepted": 0, "edited": 0, "rejected": 0,
                                             "waived": 0, "open": 0})
            r["hits"] += 1
            r["assets"].add(a.id)
            r[f.status if f.status in r else "open"] += 1
            t = by_team.setdefault((a.owner.team or "-", f.rule_id), set())
            t.add(a.id)
    from .db import Rule
    titles = {r.rule_id: r.title for r in db.execute(select(Rule).where(Rule.is_current.is_(True))).scalars()}
    out_rules = []
    for rid, r in rules.items():
        decided = r["accepted"] + r["edited"] + r["rejected"] + r["waived"]
        overridden = r["rejected"] + r["waived"]
        rate = round(overridden / decided, 2) if decided else 0.0
        out_rules.append({**{k: v for k, v in r.items() if k != "assets"}, "title": titles.get(rid, rid),
                          "assets": len(r["assets"]), "decided": decided, "override_rate": rate,
                          "ambiguous": decided >= 3 and rate >= 0.34})
    out_rules.sort(key=lambda r: -r["hits"])
    repeated = [{"team": t, "rule_id": rid, "assets": len(ids), "title": titles.get(rid, rid)}
                for (t, rid), ids in by_team.items() if len(ids) >= 2]
    repeated.sort(key=lambda r: -r["assets"])
    return {"status_counts": status_counts, "total_assets": len(assets), "rules": out_rules, "repeated_by_team": repeated}
