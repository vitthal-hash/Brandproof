"""Tamper-evident audit log: each row stores the hash of the previous row."""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Audit, utcnow

GENESIS = "0" * 64


def _digest(prev: str, ts: str, actor: str, action: str, entity: str, entity_id: str, detail: dict) -> str:
    body = json.dumps([prev, ts, actor, action, entity, entity_id, detail], sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def log(db: Session, actor: str, action: str, entity: str = "", entity_id="", detail: dict | None = None) -> Audit:
    detail = detail or {}
    last = db.execute(select(Audit).order_by(Audit.id.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else GENESIS
    ts = utcnow().isoformat(timespec="seconds")
    row = Audit(ts=ts, actor=actor, action=action, entity=entity, entity_id=str(entity_id),
                detail=detail, prev_hash=prev,
                hash=_digest(prev, ts, actor, action, entity, str(entity_id), detail))
    db.add(row)
    db.flush()
    return row


def verify(db: Session) -> dict:
    prev = GENESIS
    rows = db.execute(select(Audit).order_by(Audit.id)).scalars().all()
    for r in rows:
        expect = _digest(prev, r.ts, r.actor, r.action, r.entity, r.entity_id, r.detail)
        if r.prev_hash != prev or r.hash != expect:
            return {"ok": False, "entries": len(rows), "first_bad_id": r.id, "head": prev}
        prev = r.hash
    return {"ok": True, "entries": len(rows), "first_bad_id": None, "head": prev}
