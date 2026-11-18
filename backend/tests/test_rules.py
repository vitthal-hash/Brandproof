from conftest import login, make_asset


def test_editing_a_rule_makes_a_new_version_and_engine_uses_it(client):
    owner, c = login(client, "owner@finora.example"), login(client)
    r = [x for x in client.get("/api/rules", headers=owner).json() if x["rule_id"] == "TERM-01"][0]
    assert r["version"] == 1
    body = {k: r[k] for k in ("title", "category", "severity", "description", "method", "params")}
    body["params"] = {**r["params"], "phrases": r["params"]["phrases"] + ["can't lose"]}
    new = client.put("/api/rules/TERM-01", headers=owner, json={**body, "rule_id": "TERM-01"})
    assert new.status_code == 200 and new.json()["version"] == 2
    hist = client.get("/api/rules/TERM-01/history", headers=owner).json()
    assert [h["version"] for h in hist] == [2, 1] and [h["is_current"] for h in hist] == [True, False]
    aid = make_asset(client, c, "You can't lose with Finora Save.")
    d = client.get(f"/api/assets/{aid}", headers=c).json()
    f = [x for x in d["findings"] if x["rule_id"] == "TERM-01"][0]
    assert f["citation"]["rules"] == ["TERM-01@v2"]


def test_only_owner_changes_rules(client):
    c = login(client)
    r = client.get("/api/rules", headers=c).json()[0]
    body = {k: r[k] for k in ("title", "category", "severity", "description", "method", "params")}
    assert client.put(f"/api/rules/{r['rule_id']}", headers=c, json=body).status_code == 403
    assert client.post("/api/rules", headers=c, json=body).status_code == 403


def test_rule_validation(client):
    owner = login(client, "owner@finora.example")
    bad = {"title": "x", "severity": "extreme", "method": "phrase"}
    assert client.post("/api/rules", headers=owner, json=bad).status_code == 422
    assert client.post("/api/rules", headers=owner, json={"title": "x", "method": "nonsense"}).status_code == 422


GUIDE = """Finora Voice Guide
1. We must never use the words "free money" or "get rich" in any copy.
2. Always write the product name in full.
3. Avoid talking down to readers; keep a friendly tone.
Our company was founded in 2020.
"""


def test_guideline_import_creates_drafts_that_need_approval(client):
    owner, c = login(client, "owner@finora.example"), login(client)
    r = client.post("/api/guidelines/import", headers=owner, data={"text": GUIDE})
    assert r.status_code == 200
    drafts = r.json()
    assert len(drafts) == 3 and all(d["status"] == "draft" and not d["is_current"] for d in drafts)
    phrase = [d for d in drafts if d["method"] == "phrase"][0]
    assert set(phrase["params"]["phrases"]) == {"free money", "get rich"} and phrase["severity"] == "high"
    # not enforced before approval
    aid = make_asset(client, c, "Get rich with free money from Finora Save.")
    assert "free money" not in str([f["quote"] for f in client.get(f"/api/assets/{aid}", headers=c).json()["findings"]]).lower()
    assert client.post(f"/api/rules/{phrase['pk']}/decision", headers=owner, json={"action": "approve"}).status_code == 200
    d = client.post(f"/api/assets/{aid}/rerun", headers=c).json()
    assert phrase["rule_id"] in {f["rule_id"] for f in d["findings"]}
    # judgment rules without an AI judge are reported as not checked, never silently skipped
    client.post(f"/api/rules/{[x for x in drafts if x['method'] == 'judgment'][0]['pk']}/decision", headers=owner, json={"action": "approve"})
    d = client.post(f"/api/assets/{aid}/rerun", headers=c).json()
    assert any("need an AI judge" in n for n in d["run"]["not_checked"])


def test_import_pdf_and_empty_text(client):
    from conftest import pdf_bytes
    owner = login(client, "owner@finora.example")
    pdf = pdf_bytes(lambda p, m: p.insert_text((50, 80), 'Never use the phrase "best ever" in headlines.', fontsize=12))
    r = client.post("/api/guidelines/import", headers=owner, files={"file": ("guide.pdf", pdf, "application/pdf")})
    assert r.status_code == 200 and r.json()[0]["params"]["phrases"] == ["best ever"]
    assert client.post("/api/guidelines/import", headers=owner, data={"text": "Hello world."}).status_code == 422


def test_library_and_palette_drive_the_visual_check(client):
    owner = login(client, "owner@finora.example")
    assert client.post("/api/library", headers=owner, json={"kind": "palette", "name": "Bad", "value": {"hex": "red"}}).status_code == 422
    r = client.post("/api/library", headers=owner, json={"kind": "competitor", "name": "NewBank"})
    assert r.status_code == 200
    items = client.get("/api/library", headers=owner).json()
    assert {"palette", "term", "competitor", "logo"} <= {i["kind"] for i in items}
    assert len([i for i in items if i["kind"] == "palette"]) == 4
    assert client.delete(f"/api/library/{r.json()['id']}", headers=owner).status_code == 200


def test_seeded_brand_pack_is_complete(client):
    h = login(client)
    rules = client.get("/api/rules", headers=h).json()
    facts = client.get("/api/facts", headers=h).json()
    assert len(rules) == 22 and len(facts) == 24
    assert all(f["source"] and f["owner"] for f in facts)
    assert {"ASCI-02", "DISC-01", "CLAIM-01"} <= {r["rule_id"] for r in rules}
    assert any("pakka" in str(r["params"]) for r in rules)
