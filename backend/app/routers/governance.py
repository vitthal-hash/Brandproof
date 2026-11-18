import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit, storage
from ..db import Fact, LibraryItem, Rule, User, get_db
from ..engine import importer
from ..security import current_user, require
from .common import need, ser_fact, ser_item, ser_rule

router = APIRouter(prefix="/api")
METHODS = {"phrase", "product_name", "preferred_term", "caps", "exclaim", "offer_end_date", "disclaimer", "ai_label",
           "pii", "reading_level", "alt_text", "contrast", "palette", "judgment", "claims", "trust"}


# ------------------------------------------------------------------ rules
class RuleBody(BaseModel):
    rule_id: str | None = None
    title: str
    category: str = "messaging"
    severity: str = "medium"
    description: str = ""
    method: str = "judgment"
    params: dict = {}


def _check_rule(b: RuleBody):
    if b.severity not in ("low", "medium", "high"):
        raise HTTPException(422, "severity must be low, medium or high")
    if b.method not in METHODS:
        raise HTTPException(422, f"unknown method '{b.method}'")
    if not b.title.strip():
        raise HTTPException(422, "title is required")


@router.get("/rules")
def list_rules(include: str = "current", user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Rule).order_by(Rule.rule_id, Rule.version.desc())
    rows = db.execute(q).scalars().all()
    if include != "all":
        rows = [r for r in rows if r.is_current or r.status == "draft"]
    return [ser_rule(r) for r in rows]


@router.get("/rules/{rule_id}/history")
def rule_history(rule_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [ser_rule(r) for r in db.execute(select(Rule).where(Rule.rule_id == rule_id).order_by(Rule.version.desc())).scalars()]


@router.post("/rules")
def create_rule(b: RuleBody, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    _check_rule(b)
    rid = (b.rule_id or "").strip().upper()
    if not rid:
        n = db.execute(select(func.count()).select_from(Rule)).scalar() + 1
        rid = f"RULE-{n:03d}"
    if db.execute(select(Rule).where(Rule.rule_id == rid)).first():
        raise HTTPException(409, "Rule id already exists; edit it to create a new version")
    r = Rule(rule_id=rid, version=1, title=b.title, category=b.category, severity=b.severity, description=b.description,
             method=b.method, params=b.params, status="approved", is_current=True, source="owner", created_by=user.email)
    db.add(r)
    audit.log(db, user.email, "rule.create", "rule", rid, {"version": 1})
    db.commit()
    return ser_rule(r)


@router.put("/rules/{rule_id}")
def edit_rule(rule_id: str, b: RuleBody, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    _check_rule(b)
    cur = db.execute(select(Rule).where(Rule.rule_id == rule_id, Rule.is_current.is_(True))).scalar_one_or_none()
    need(cur, "Rule")
    cur.is_current = False
    new = Rule(rule_id=rule_id, version=cur.version + 1, title=b.title, category=b.category, severity=b.severity,
               description=b.description, method=b.method, params=b.params, status="approved", is_current=True,
               source=cur.source, created_by=user.email)
    db.add(new)
    audit.log(db, user.email, "rule.version", "rule", rule_id, {"version": new.version})
    db.commit()
    return ser_rule(new)


class RuleDecision(BaseModel):
    action: str  # approve | reject


@router.post("/rules/{pk}/decision")
def rule_decision(pk: int, b: RuleDecision, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    r = need(db.get(Rule, pk), "Rule")
    if r.status != "draft":
        raise HTTPException(409, "Only draft rules can be approved or rejected")
    if b.action == "approve":
        r.status, r.is_current = "approved", True
    elif b.action == "reject":
        r.status, r.is_current = "rejected", False
    else:
        raise HTTPException(422, "action must be approve or reject")
    audit.log(db, user.email, f"rule.{b.action}", "rule", r.rule_id, {"version": r.version})
    db.commit()
    return ser_rule(r)


@router.post("/guidelines/import")
async def import_guidelines(text: str = Form(""), file: UploadFile | None = File(None),
                            user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    data = await file.read() if file is not None and file.filename else None
    fname = file.filename if file is not None else ""
    body = importer.extract_text(data, fname or "", text or None)
    cands = importer.candidates(body)
    if not cands:
        raise HTTPException(422, "No rule-like sentences found. Rules usually contain words like must, never, always or avoid.")
    taken = {r[0] for r in db.execute(select(Rule.rule_id)).all()}
    out, n = [], 0
    for c in cands:
        rid = c["rule_id"]
        while rid in taken:
            n += 1
            rid = f"IMP-{100 + n:03d}"
        taken.add(rid)
        r = Rule(rule_id=rid, version=1, title=c["title"], category=c["category"], severity=c["severity"],
                 description=c["description"], method=c["method"], params=c["params"], status="draft", is_current=False,
                 source=f"import:{fname or 'pasted text'}", created_by=user.email)
        db.add(r)
        out.append(r)
    audit.log(db, user.email, "guidelines.import", "rule", "-", {"draft_rules": len(out), "source": fname or "pasted"})
    db.commit()
    return [ser_rule(r) for r in out]


# ------------------------------------------------------------------ facts
class FactBody(BaseModel):
    id: str
    statement: str
    kind: str = "general"
    keywords: list[str] = []
    supports: list[str] = []
    contradicts: list[str] = []
    numeric: dict = {}
    qualifier: str = ""
    rewrite: list[dict] = []
    source: str = ""
    owner: str = ""
    valid_from: str | None = None
    valid_to: str | None = None


def _date(s):
    try:
        return dt.date.fromisoformat(s) if s else None
    except ValueError:
        raise HTTPException(422, "Dates must look like 2026-12-31")


@router.get("/facts")
def facts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [ser_fact(f) for f in db.execute(select(Fact).order_by(Fact.id)).scalars()]


@router.put("/facts/{fact_id}")
def upsert_fact(fact_id: str, b: FactBody, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    if not b.statement.strip() or not b.source.strip() or not b.owner.strip():
        raise HTTPException(422, "statement, source and owner are required")
    f = db.get(Fact, fact_id)
    new = f is None
    if new:
        f = Fact(id=fact_id)
        db.add(f)
    f.statement, f.kind, f.keywords, f.supports, f.contradicts = b.statement, b.kind, b.keywords, b.supports, b.contradicts
    f.numeric, f.qualifier, f.rewrite, f.source, f.owner = b.numeric, b.qualifier, b.rewrite, b.source, b.owner
    f.valid_from, f.valid_to = _date(b.valid_from), _date(b.valid_to)
    audit.log(db, user.email, "fact.create" if new else "fact.update", "fact", fact_id, {"valid_to": b.valid_to})
    db.commit()
    return ser_fact(f)


@router.delete("/facts/{fact_id}")
def delete_fact(fact_id: str, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    f = need(db.get(Fact, fact_id), "Fact")
    db.delete(f)
    audit.log(db, user.email, "fact.delete", "fact", fact_id, {})
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ library
class ItemBody(BaseModel):
    kind: str
    name: str
    value: dict = {}


@router.get("/library")
def library(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [ser_item(i) for i in db.execute(select(LibraryItem).order_by(LibraryItem.kind, LibraryItem.name)).scalars()]


@router.post("/library")
def add_item(b: ItemBody, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    if b.kind not in ("term", "palette", "competitor"):
        raise HTTPException(422, "kind must be term, palette or competitor")
    if b.kind == "palette":
        hx = str(b.value.get("hex", ""))
        if len(hx) != 7 or not hx.startswith("#"):
            raise HTTPException(422, "palette items need a hex colour like #0E7C7B")
    i = LibraryItem(kind=b.kind, name=b.name.strip(), value=b.value)
    db.add(i)
    audit.log(db, user.email, "library.add", "library", b.kind, {"name": b.name})
    db.commit()
    return ser_item(i)


@router.post("/library/logo")
async def add_logo(name: str = Form(...), file: UploadFile = File(...), user: User = Depends(require("owner")),
                   db: Session = Depends(get_db)):
    data = await file.read()
    path = storage.save(f"library/{name.strip().replace(' ', '_')}-{file.filename}", data, db)
    i = LibraryItem(kind="logo", name=name.strip(), value={"mime": file.content_type}, file_path=path)
    db.add(i)
    audit.log(db, user.email, "library.add", "library", "logo", {"name": name})
    db.commit()
    return ser_item(i)


@router.delete("/library/{item_id}")
def delete_item(item_id: int, user: User = Depends(require("owner")), db: Session = Depends(get_db)):
    i = need(db.get(LibraryItem, item_id), "Item")
    if i.file_path:
        storage.delete(i.file_path, db)
    db.delete(i)
    audit.log(db, user.email, "library.delete", "library", item_id, {})
    db.commit()
    return {"ok": True}
