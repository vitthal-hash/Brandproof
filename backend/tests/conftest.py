import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("BP_STORAGE_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("BP_TODAY", "2026-11-17")
    monkeypatch.setenv("BP_LLM_PROVIDER", "offline")
    monkeypatch.setenv("BP_SEED", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app import db, seed
    db.init_engine()
    s = db.session()
    seed.seed_brand(s)
    s.close()
    yield tmp_path


@pytest.fixture
def client(env):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def dbs(env):
    from app import db
    s = db.session()
    yield s
    s.close()


def login(client, email="creator@finora.example", pw="demo1234"):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def make_asset(client, h, text, intent="Announce our new savings account", title="Test asset", **extra):
    data = {"title": title, "intent": intent, "channel": "social", "text": text, **extra}
    r = client.post("/api/assets", data=data, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def pdf_bytes(draw):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    draw(page, pymupdf)
    return doc.tobytes()


def ctx_for(db_session):
    from app.engine import review
    rules, facts, lib = review.load_context(db_session)
    return rules, facts, lib
