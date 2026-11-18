import io

from conftest import login, make_asset, pdf_bytes


def test_requires_login(client):
    assert client.get("/api/assets").status_code == 401
    assert client.get("/api/assets", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "creator@finora.example", "password": "wrong"}).status_code == 401


def test_findings_are_cited_explained_and_badged(client):
    h = login(client)
    aid = make_asset(client, h, "Earn guaranteed returns! Get 7.5% interest. Hurry.")
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    by = {(f["rule_id"], f["method"]): f for f in d["findings"]}
    assert ("TERM-01", "rule") in by and ("CLAIM-01", "claims") in by
    claim = [f for f in d["findings"] if f["verdict"] == "Contradicted" and "F-03" in f["citation"].get("facts", [])][0]
    assert claim["explanation"] and claim["citation"]["rules"][0].startswith("CLAIM-01@v")
    for f in d["findings"]:
        assert f["explanation"] and f["citation"].get("rules")
        assert 0 <= f["confidence"] <= 1


def test_accept_fix_creates_new_version_and_rereviews(client):
    h = login(client)
    aid = make_asset(client, h, "Earn guaranteed returns on our new savings account.")
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    f = [x for x in d["findings"] if x["rule_id"] == "TERM-01"][0]
    r = client.post(f"/api/findings/{f['id']}/decision", headers=h, json={"action": "accept_fix"})
    assert r.status_code == 200
    d2 = r.json()
    assert len(d2["versions"]) == 2 and d2["version"]["n"] == 2
    assert "guaranteed" not in d2["version"]["text"] and "competitive interest" in d2["version"]["text"]
    assert "TERM-01" not in {x["rule_id"] for x in d2["findings"]}
    diff = client.get(f"/api/assets/{aid}/diff?a=1&b=2", headers=h).json()
    assert any(x["op"] == "del" for x in diff) and any(x["op"] == "add" for x in diff)
    old = client.get(f"/api/assets/{aid}?n=1", headers=h).json()
    assert [x for x in old["findings"] if x["rule_id"] == "TERM-01"][0]["status"] == "accepted"


def test_edit_fix_uses_creators_own_words(client):
    h = login(client)
    aid = make_asset(client, h, "Earn guaranteed returns on our new savings account.")
    f = [x for x in client.get(f"/api/assets/{aid}", headers=h).json()["findings"] if x["rule_id"] == "TERM-01"][0]
    r = client.post(f"/api/findings/{f['id']}/decision", headers=h, json={"action": "edit_fix", "text": "steady interest"})
    assert "steady interest" in r.json()["version"]["text"]


def test_reject_needs_a_reason_and_is_recorded(client):
    h = login(client)
    aid = make_asset(client, h, "Hurry, open an account.")
    f = [x for x in client.get(f"/api/assets/{aid}", headers=h).json()["findings"] if x["rule_id"] == "TONE-04"][0]
    assert client.post(f"/api/findings/{f['id']}/decision", headers=h, json={"action": "reject"}).status_code == 422
    r = client.post(f"/api/findings/{f['id']}/decision", headers=h, json={"action": "reject", "note": "playful campaign"})
    g = [x for x in r.json()["findings"] if x["id"] == f["id"]][0]
    assert g["status"] == "rejected" and g["decided_note"] == "playful campaign"


def test_withheld_and_file_level_findings_cannot_be_accepted(client):
    h = login(client)
    aid = make_asset(client, h, "Enjoy our launch cashback this month.", intent="Announce the launch cashback offer")
    f = [x for x in client.get(f"/api/assets/{aid}", headers=h).json()["findings"] if x["rule_id"] == "CLAIM-02"][0]
    assert client.post(f"/api/findings/{f['id']}/decision", headers=h, json={"action": "accept_fix"}).status_code == 422
    pdf = pdf_bytes(lambda p, m: (p.draw_rect(m.Rect(0, 0, 595, 200), color=None, fill=(0.08, 0.13, 0.24)),
                                  p.insert_text((60, 90), "Dim text", fontsize=13, color=(0.25, 0.3, 0.45))))
    r = client.post("/api/assets", headers=h, data={"title": "p", "intent": "Poster for the launch"},
                    files={"file": ("p.pdf", pdf, "application/pdf")})
    d = client.get(f"/api/assets/{r.json()['id']}", headers=h).json()
    f = [x for x in d["findings"] if x["rule_id"] == "A11Y-01"][0]
    assert client.post(f"/api/findings/{f['id']}/decision", headers=h, json={"action": "accept_fix"}).status_code == 422


def test_stale_finding_is_rejected(client):
    h = login(client)
    aid = make_asset(client, h, "Earn guaranteed returns. Hurry.")
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    f1 = [x for x in d["findings"] if x["rule_id"] == "TERM-01"][0]
    f2 = [x for x in d["findings"] if x["rule_id"] == "TONE-04"][0]
    client.post(f"/api/findings/{f1['id']}/decision", headers=h, json={"action": "accept_fix"})
    assert client.post(f"/api/findings/{f2['id']}/decision", headers=h, json={"action": "accept_fix"}).status_code == 409


def test_intent_and_title_required(client):
    h = login(client)
    r = client.post("/api/assets", headers=h, data={"title": "x", "intent": "", "text": "hello there"})
    assert r.status_code == 422
    r = client.post("/api/assets", headers=h, data={"title": "x", "intent": "Say hello to customers"})
    assert r.status_code == 422


def test_pdf_and_image_intake_and_preview(client):
    from PIL import Image
    h = login(client)
    pdf = pdf_bytes(lambda p, m: p.insert_text((60, 90), "Open Finora Save in about 5 minutes.", fontsize=14))
    r = client.post("/api/assets", headers=h, data={"title": "pdf", "intent": "Explain account opening"},
                    files={"file": ("a.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    aid = r.json()["id"]
    prev = client.get(f"/api/assets/{aid}/preview", headers=h)
    assert prev.status_code == 200 and prev.content[:4] == b"\x89PNG"
    buf = io.BytesIO()
    Image.new("RGB", (200, 100), (108, 53, 222)).save(buf, "PNG")
    r = client.post("/api/assets", headers=h, data={"title": "img", "intent": "Banner for the festive offer", "ai_generated": "true"},
                    files={"file": ("b.png", buf.getvalue(), "image/png")})
    d = client.get(f"/api/assets/{r.json()['id']}", headers=h).json()
    rules = {f["rule_id"] for f in d["findings"]}
    assert {"A11Y-02", "VIS-01", "DISC-01"} <= rules
    assert any("not read" in n for n in d["run"]["not_checked"])


def test_comments_anchor_to_findings(client):
    h = login(client)
    aid = make_asset(client, h, "Hurry, open an account.")
    f = client.get(f"/api/assets/{aid}", headers=h).json()["findings"][0]
    c = client.post(f"/api/assets/{aid}/comments", headers=h, json={"body": "Is this tone ok?", "finding_id": f["id"]})
    assert c.status_code == 200 and c.json()["finding_id"] == f["id"]
    assert client.get(f"/api/assets/{aid}/comments", headers=h).json()[0]["body"] == "Is this tone ok?"


def test_visibility_rules(client):
    creator, agency = login(client), login(client, "agency@nova.example")
    riya, manager = login(client, "riya@finora.example"), login(client, "manager@finora.example")
    a_ext = make_asset(client, agency, "Open Finora Save today.", title="agency asset")
    a_soc = make_asset(client, creator, "Open Finora Save today.", title="social asset")
    ids = lambda h: {a["id"] for a in client.get("/api/assets", headers=h).json()}
    assert ids(agency) == {a_ext}
    assert a_soc in ids(manager) and a_ext in ids(manager)
    assert a_ext not in ids(creator) and a_soc not in ids(riya)
    assert client.get(f"/api/assets/{a_soc}", headers=agency).status_code == 404
    assert client.get(f"/api/assets/{a_ext}/proofpack", headers=creator).status_code == 404


def test_owner_role_cannot_submit_content(client):
    owner = login(client, "owner@finora.example")
    r = client.post("/api/assets", headers=owner, data={"title": "x", "intent": "Say hello to customers", "text": "Hello"})
    assert r.status_code == 403


def test_demo_users_listing_is_off_when_seeding_is_off(client):
    assert client.get("/api/demo-users").json() == []  # tests run with BP_SEED=0, like production
