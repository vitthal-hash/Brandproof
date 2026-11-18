from sqlalchemy import select

from conftest import login, make_asset


def test_chain_verifies_and_covers_actions(client):
    c = login(client)
    aid = make_asset(client, c, "Open Finora Save today.")
    client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "submit"})
    m = login(client, "manager@finora.example")
    v = client.get("/api/audit/verify", headers=m).json()
    assert v["ok"] and v["entries"] >= 4
    actions = {a["action"] for a in client.get("/api/audit", headers=m).json()}
    assert {"asset.create", "version.create", "review.run", "asset.submit"} <= actions


def test_tampering_is_detected(client, env):
    from app import db
    from app.db import Audit
    c = login(client)
    make_asset(client, c, "Open Finora Save today.")
    m = login(client, "manager@finora.example")
    assert client.get("/api/audit/verify", headers=m).json()["ok"]
    s = db.session()
    row = s.execute(select(Audit).where(Audit.action == "asset.create")).scalars().first()
    row.actor = "someone.else@evil.example"
    s.commit()
    bad_id = row.id
    s.close()
    v = client.get("/api/audit/verify", headers=m).json()
    assert not v["ok"] and v["first_bad_id"] == bad_id


def test_deleting_a_row_is_detected(client, env):
    from app import db
    from app.db import Audit
    c = login(client)
    make_asset(client, c, "Open Finora Save today.")
    m = login(client, "manager@finora.example")
    s = db.session()
    rows = s.execute(select(Audit).order_by(Audit.id)).scalars().all()
    s.delete(rows[len(rows) // 2])
    s.commit()
    s.close()
    assert not client.get("/api/audit/verify", headers=m).json()["ok"]


def test_audit_is_not_visible_to_creators(client):
    assert client.get("/api/audit", headers=login(client)).status_code == 403
