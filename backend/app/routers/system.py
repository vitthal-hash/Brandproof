from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit, config, service
from ..db import Audit, LlmCall, User, get_db
from ..llm.adapter import Gateway
from ..security import current_user, require

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/insights")
def insights(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return service.insights(db)


@router.get("/audit")
def audit_list(limit: int = 200, user: User = Depends(require("manager", "reviewer", "owner")), db: Session = Depends(get_db)):
    rows = db.execute(select(Audit).order_by(Audit.id.desc()).limit(min(limit, 500))).scalars().all()
    return [{"id": a.id, "ts": a.ts, "actor": a.actor, "action": a.action, "entity": a.entity, "entity_id": a.entity_id,
             "detail": a.detail, "hash": a.hash[:16], "prev": a.prev_hash[:16]} for a in rows]


@router.get("/audit/verify")
def audit_verify(user: User = Depends(require("manager", "reviewer", "owner")), db: Session = Depends(get_db)):
    return audit.verify(db)


@router.get("/disclosure")
def disclosure(user: User = Depends(current_user), db: Session = Depends(get_db)):
    gw = Gateway(db)
    calls = db.execute(select(LlmCall).order_by(LlmCall.id.desc()).limit(50)).scalars().all()
    by_purpose = db.execute(select(LlmCall.purpose, func.count(), func.sum(LlmCall.redactions)).group_by(LlmCall.purpose)).all()
    services = [{"name": "FastAPI backend and PostgreSQL database (Supabase or self-hosted)", "data": "All content and review results", "external": False},
                {"name": "Local file storage", "data": "Uploaded PDFs and images (stored in the database)", "external": False}]
    if gw.enabled:
        services.append({"name": f"{gw.name} model API ({gw.model})",
                         "data": "Redacted text for claim extraction, tone/messaging judgment, Intent Lock and red-team variants. "
                                 "Emails, phones, Aadhaar, PAN and card numbers are replaced by tokens first.",
                         "external": True})
    return {"llm_enabled": gw.enabled, "provider": gw.name, "model": gw.model,
            "images_to_llm": service.get_setting(db, "llm_images", False),
            "retention_delete_after_approval": service.get_setting(db, "retention_delete_after_approval", False),
            "services": services,
            "ai_note": ("An external language model is used for some checks." if gw.enabled else
                        "No external AI service is configured. All checks run locally: deterministic rules plus a lexicon heuristic "
                        "that is labelled 'Heuristic' wherever it is used."),
            "calls_by_purpose": [{"purpose": p, "calls": n, "redactions": int(r or 0)} for p, n, r in by_purpose],
            "calls": [{"ts": c.ts.isoformat(timespec="seconds"), "provider": c.provider, "model": c.model, "purpose": c.purpose,
                       "asset_id": c.asset_id, "chars": c.input_chars, "redactions": c.redactions, "status": c.status,
                       "ms": c.latency_ms} for c in calls]}


class SettingsBody(BaseModel):
    retention_delete_after_approval: bool | None = None
    images_to_llm: bool | None = None


@router.put("/settings")
def settings(b: SettingsBody, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    if b.retention_delete_after_approval is not None:
        service.set_setting(db, "retention_delete_after_approval", b.retention_delete_after_approval)
        audit.log(db, user.email, "settings.update", "settings", "retention", {"value": b.retention_delete_after_approval})
    if b.images_to_llm is not None:
        service.set_setting(db, "llm_images", b.images_to_llm)
        audit.log(db, user.email, "settings.update", "settings", "llm_images", {"value": b.images_to_llm})
    db.commit()
    return {"ok": True}
