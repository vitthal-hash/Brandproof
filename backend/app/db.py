"""Database models. PostgreSQL (Supabase or the bundled container). SQLite only when DATABASE_URL says so."""
import datetime as dt
from sqlalchemy import (JSON, LargeBinary, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        create_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from . import config


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(30))  # creator|external|manager|reviewer|owner
    team: Mapped[str] = mapped_column(String(100), default="")
    pw_hash: Mapped[str] = mapped_column(String(300))


class StoredFile(Base):
    """File bytes kept in the database (used when BP_STORAGE=db, so hosts with no disk keep uploads)."""
    __tablename__ = "stored_files"
    path: Mapped[str] = mapped_column(String(500), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary)


class Rule(Base):
    __tablename__ = "rules"
    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))  # low|medium|high
    description: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(String(30))  # see engine/rules.py
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    examples: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="approved")  # draft|approved|rejected
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(200), default="seed")
    created_by: Mapped[str] = mapped_column(String(200), default="system")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Fact(Base):
    __tablename__ = "facts"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    statement: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    supports: Mapped[list] = mapped_column(JSON, default=list)
    contradicts: Mapped[list] = mapped_column(JSON, default=list)
    numeric: Mapped[dict] = mapped_column(JSON, default=dict)
    qualifier: Mapped[str] = mapped_column(String(60), default="")
    rewrite: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(300), default="")
    owner: Mapped[str] = mapped_column(String(100), default="")
    valid_from: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[dt.date | None] = mapped_column(Date, nullable=True)


class LibraryItem(Base):
    __tablename__ = "library"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # term|palette|competitor|logo
    name: Mapped[str] = mapped_column(String(200))
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    file_path: Mapped[str] = mapped_column(String(500), default="")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    intent: Mapped[str] = mapped_column(String(500))
    channel: Mapped[str] = mapped_column(String(60), default="social")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="Draft")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    alt_text: Mapped[str] = mapped_column(String(500), default="")
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    risk: Mapped[str] = mapped_column(String(10), default="normal")  # normal|high
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    owner: Mapped["User"] = relationship()


class AssetVersion(Base):
    __tablename__ = "asset_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    n: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(10))  # text|pdf|image
    text_raw: Mapped[str] = mapped_column(Text, default="")
    text_clean: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[str] = mapped_column(String(500), default="")
    mime: Mapped[str] = mapped_column(String(100), default="text/plain")
    sha256: Mapped[str] = mapped_column(String(64), default="")
    note: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    purged: Mapped[bool] = mapped_column(Boolean, default=False)


class ReviewRun(Base):
    __tablename__ = "review_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("asset_versions.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    provider: Mapped[str] = mapped_column(String(40), default="offline")
    model: Mapped[str] = mapped_column(String(80), default="")
    trust: Mapped[dict] = mapped_column(JSON, default=dict)
    differential: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    not_checked: Mapped[list] = mapped_column(JSON, default=list)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("asset_versions.id"), index=True)
    rule_id: Mapped[str] = mapped_column(String(40))
    rule_version: Mapped[int] = mapped_column(Integer, default=1)
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(10))
    method: Mapped[str] = mapped_column(String(20))  # rule|claims|ai|heuristic|trust|file
    verdict: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(300))
    explanation: Mapped[str] = mapped_column(Text, default="")
    quote: Mapped[str] = mapped_column(Text, default="")
    start: Mapped[int] = mapped_column(Integer, default=-1)
    end: Mapped[int] = mapped_column(Integer, default=-1)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    citation: Mapped[dict] = mapped_column(JSON, default=dict)
    fix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|accepted|edited|rejected|waived
    decided_by: Mapped[str] = mapped_column(String(200), default="")
    decided_note: Mapped[str] = mapped_column(Text, default="")


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("review_runs.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("asset_versions.id"), index=True)
    label: Mapped[str] = mapped_column(String(10))  # C-1, C-2 ...
    text: Mapped[str] = mapped_column(Text)
    start: Mapped[int] = mapped_column(Integer, default=-1)
    end: Mapped[int] = mapped_column(Integer, default=-1)
    kind: Mapped[str] = mapped_column(String(20))
    verdict: Mapped[str] = mapped_column(String(20))
    fact_id: Mapped[str] = mapped_column(String(20), default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    explanation: Mapped[str] = mapped_column(Text, default="")


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    finding_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(30))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(40), default="")
    entity_id: Mapped[str] = mapped_column(String(40), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class LlmCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(String(60))
    asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_chars: Mapped[int] = mapped_column(Integer, default=0)
    redactions: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="ok")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)


class RedTeamRun(Base):
    __tablename__ = "redteam_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(40))
    rule_version: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    source: Mapped[str] = mapped_column(String(40), default="handwritten+mutation")
    variants: Mapped[list] = mapped_column(JSON, default=list)
    results: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)


class RuleProposal(Base):
    __tablename__ = "rule_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer)
    rule_id: Mapped[str] = mapped_column(String(40))
    base_version: Mapped[int] = mapped_column(Integer)
    proposed_params: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|approved|rejected
    retest: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


_engine = None
_Session = None


def init_engine(url: str | None = None):
    global _engine, _Session
    url = url or config.database_url()
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" not in url:
            path = url.replace("sqlite:///", "", 1)
            import os
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if not url.startswith("sqlite"):
        kwargs.setdefault("pool_pre_ping", True)  # hosted databases drop idle connections
    _engine = create_engine(url, **kwargs)
    _Session = sessionmaker(bind=_engine, expire_on_commit=False)
    Base.metadata.create_all(_engine)
    return _engine


def session():
    if _Session is None:
        init_engine()
    return _Session()


def get_db():
    s = session()
    try:
        yield s
    finally:
        s.close()
