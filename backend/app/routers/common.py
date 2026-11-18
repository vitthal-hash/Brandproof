from fastapi import HTTPException

from ..db import Asset, Claim, Comment, Fact, Finding, LibraryItem, ReviewRun, Rule


def ser_finding(f: Finding) -> dict:
    return {"id": f.id, "rule_id": f.rule_id, "rule_version": f.rule_version, "category": f.category,
            "severity": f.severity, "method": f.method, "verdict": f.verdict, "title": f.title,
            "explanation": f.explanation, "quote": f.quote, "start": f.start, "end": f.end,
            "confidence": f.confidence, "citation": f.citation, "fix": f.fix, "needs_human": f.needs_human,
            "status": f.status, "decided_by": f.decided_by, "decided_note": f.decided_note,
            "version_id": f.version_id}


def ser_claim(c: Claim) -> dict:
    return {"label": c.label, "text": c.text, "start": c.start, "end": c.end, "kind": c.kind, "verdict": c.verdict,
            "fact_id": c.fact_id, "confidence": c.confidence, "explanation": c.explanation}


def ser_run(r: ReviewRun | None) -> dict | None:
    if r is None:
        return None
    return {"id": r.id, "created_at": r.created_at.isoformat(timespec="seconds"), "provider": r.provider,
            "model": r.model, "trust": r.trust, "differential": r.differential, "summary": r.summary,
            "not_checked": r.not_checked}


def ser_asset(a: Asset) -> dict:
    return {"id": a.id, "title": a.title, "intent": a.intent, "channel": a.channel, "status": a.status,
            "risk": a.risk, "ai_generated": a.ai_generated, "alt_text": a.alt_text, "owner": a.owner.name,
            "owner_email": a.owner.email, "team": a.owner.team, "current_version": a.current_version,
            "updated_at": a.updated_at.isoformat(timespec="seconds")}


def ser_rule(r: Rule) -> dict:
    return {"pk": r.pk, "rule_id": r.rule_id, "version": r.version, "title": r.title, "category": r.category,
            "severity": r.severity, "description": r.description, "method": r.method, "params": r.params,
            "status": r.status, "is_current": r.is_current, "source": r.source, "created_by": r.created_by}


def ser_fact(f: Fact) -> dict:
    return {"id": f.id, "statement": f.statement, "kind": f.kind, "keywords": f.keywords, "supports": f.supports,
            "contradicts": f.contradicts, "numeric": f.numeric, "qualifier": f.qualifier, "rewrite": f.rewrite,
            "source": f.source, "owner": f.owner, "valid_from": f.valid_from.isoformat() if f.valid_from else None,
            "valid_to": f.valid_to.isoformat() if f.valid_to else None}


def ser_item(i: LibraryItem) -> dict:
    return {"id": i.id, "kind": i.kind, "name": i.name, "value": i.value, "has_file": bool(i.file_path)}


def ser_comment(c: Comment) -> dict:
    return {"id": c.id, "finding_id": c.finding_id, "author": c.author, "role": c.role, "body": c.body,
            "created_at": c.created_at.isoformat(timespec="seconds")}


def need(obj, what="Item"):
    if obj is None:
        raise HTTPException(404, f"{what} not found")
    return obj
