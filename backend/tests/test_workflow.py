import os

from sqlalchemy import select

from conftest import login, make_asset

BAD = "Earn guaranteed returns on our new savings account."
CLEAN = "Open Finora Save in about 5 minutes."


def to_review(client, h, text):
    aid = make_asset(client, h, text)
    r = client.post(f"/api/assets/{aid}/workflow", headers=h, json={"action": "submit"})
    assert r.status_code == 200 and r.json()["asset"]["status"] == "In review"
    return aid


def test_high_risk_needs_a_reviewer_and_waivers(client):
    c, m, rv = login(client), login(client, "manager@finora.example"), login(client, "reviewer@finora.example")
    aid = to_review(client, c, BAD)
    assert client.get(f"/api/assets/{aid}", headers=c).json()["asset"]["risk"] == "high"
    r = client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "approve"})
    assert r.status_code == 403 and "reviewer" in r.json()["detail"]
    q = client.get("/api/queue", headers=m).json()
    assert q[0]["route"] == "needs reviewer"
    # reviewer cannot approve until every high finding is dealt with
    r = client.post(f"/api/assets/{aid}/workflow", headers=rv, json={"action": "approve"})
    assert r.status_code == 409
    highs = [f for f in client.get(f"/api/assets/{aid}", headers=rv).json()["findings"] if f["severity"] == "high"]
    for f in highs:
        assert client.post(f"/api/findings/{f['id']}/decision", headers=m, json={"action": "waive", "note": "ok by legal"}).status_code == 403
        assert client.post(f"/api/findings/{f['id']}/decision", headers=rv, json={"action": "waive", "note": "claim reviewed by legal"}).status_code == 200
    # medium/low "needs human" items may also block; waive anything still blocking
    while True:
        r = client.post(f"/api/assets/{aid}/workflow", headers=rv, json={"action": "approve"})
        if r.status_code == 200:
            break
        assert r.status_code == 409
        d = client.get(f"/api/assets/{aid}", headers=rv).json()
        left = [f for f in d["findings"] if f["needs_human"] and f["status"] == "open"]
        assert left
        for f in left:
            client.post(f"/api/findings/{f['id']}/decision", headers=rv, json={"action": "waive", "note": "checked"})
    assert r.json()["asset"]["status"] == "Approved"
    pack = client.get(f"/api/assets/{aid}/proofpack", headers=rv).json()
    assert pack["waived"] and any(h["action"] == "asset.approve" for h in pack["humans"])


def test_manager_approves_normal_items_and_creator_cannot(client):
    c, m = login(client), login(client, "manager@finora.example")
    aid = to_review(client, c, CLEAN)
    assert client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "approve"}).status_code == 403
    r = client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "approve"})
    assert r.status_code == 200 and r.json()["asset"]["status"] == "Approved"


def test_request_changes_needs_a_note_and_returns_to_creator(client):
    c, m = login(client), login(client, "manager@finora.example")
    aid = to_review(client, c, CLEAN)
    assert client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "request_changes"}).status_code == 422
    r = client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "request_changes", "note": "shorten it"})
    assert r.json()["asset"]["status"] == "Changes requested"
    assert any("shorten it" in x["body"] for x in client.get(f"/api/assets/{aid}/comments", headers=c).json())
    assert client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "submit"}).status_code == 200


def test_only_owner_submits_and_state_machine_is_enforced(client):
    c, riya = login(client), login(client, "riya@finora.example")
    aid = make_asset(client, c, CLEAN)
    assert client.post(f"/api/assets/{aid}/workflow", headers=riya, json={"action": "submit"}).status_code in (403, 404)
    assert client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "approve"}).status_code == 403
    client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "submit"})
    assert client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "submit"}).status_code == 409


def test_approved_assets_lock_until_new_version(client):
    c, m = login(client), login(client, "manager@finora.example")
    aid = to_review(client, c, CLEAN)
    client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "approve"})
    assert client.post(f"/api/assets/{aid}/rerun", headers=c).status_code == 409
    r = client.post(f"/api/assets/{aid}/versions", headers=c, data={"text": CLEAN + " Free UPI transfers.", "note": "tweak"})
    assert r.status_code == 200 and r.json()["asset"]["status"] == "Auto-reviewed"


def test_unresolved_needs_human_blocks_approval(client):
    c, m = login(client), login(client, "manager@finora.example")
    aid = to_review(client, c, "Earn 6.5% interest on Finora Save. T&C apply.")  # ceiling wording -> Needs human
    d = client.get(f"/api/assets/{aid}", headers=c).json()
    nh = [f for f in d["findings"] if f["needs_human"]]
    assert nh
    r = client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "approve"})
    assert r.status_code == 409
    for f in nh:
        assert client.post(f"/api/findings/{f['id']}/decision", headers=m, json={"action": "waive", "note": "wording ok"}).status_code == 200
    assert client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "approve"}).status_code == 200


def test_retention_deletes_content_after_approval(client, env):
    from app import db
    from app.db import AssetVersion
    owner, c, m = login(client, "owner@finora.example"), login(client), login(client, "manager@finora.example")
    assert client.put("/api/settings", headers=owner, json={"retention_delete_after_approval": True}).status_code == 200
    from conftest import pdf_bytes
    pdf = pdf_bytes(lambda p, mm: p.insert_text((60, 90), "Open Finora Save in about 5 minutes.", fontsize=14))
    r = client.post("/api/assets", headers=c, data={"title": "pdf", "intent": "Explain account opening"},
                    files={"file": ("a.pdf", pdf, "application/pdf")})
    aid = r.json()["id"]
    client.post(f"/api/assets/{aid}/workflow", headers=c, json={"action": "submit"})
    assert client.post(f"/api/assets/{aid}/workflow", headers=m, json={"action": "approve"}).status_code == 200
    s = db.session()
    v = s.execute(select(AssetVersion).where(AssetVersion.asset_id == aid)).scalars().first()
    assert v.purged and v.text_clean == "" and v.file_path == ""
    assert not os.path.exists(os.path.join(str(env), "files", f"assets/{aid}/v1.pdf"))
    s.close()
    pack = client.get(f"/api/assets/{aid}/proofpack", headers=m).json()
    assert pack["version"]["purged"] and pack["version"]["sha256"]
    assert client.get("/api/audit/verify", headers=m).json()["ok"]
