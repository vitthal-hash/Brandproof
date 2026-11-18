from conftest import login, make_asset


def test_redteam_finds_loopholes_and_proposes_tighter_rule(client):
    owner = login(client, "owner@finora.example")
    r = client.post("/api/redteam/run", headers=owner, json={"rule_id": "TERM-01"})
    assert r.status_code == 200
    run = r.json()
    assert run["summary"]["missed"] > 0 and run["summary"]["total"] >= 10
    missed = [x for x in run["results"] if not x["caught"]]
    assert missed and all("text" in x and "technique" in x for x in missed)
    p = run["proposal"]
    assert p["status"] == "pending" and p["rationale"]
    assert p["retest"]["after_caught"] > p["retest"]["before_caught"]
    assert p["retest"]["false_positives"] == []


def test_owner_approves_tighter_rule_and_retest_shows_before_after(client):
    owner, c = login(client, "owner@finora.example"), login(client)
    run = client.post("/api/redteam/run", headers=owner, json={"rule_id": "TONE-04"}).json()
    before = run["summary"]["caught"]
    pid = run["proposal"]["id"]
    # a creator can never change rules
    assert client.post(f"/api/redteam/proposals/{pid}/decision", headers=c, json={"action": "approve"}).status_code == 403
    r = client.post(f"/api/redteam/proposals/{pid}/decision", headers=owner, json={"action": "approve"})
    assert r.status_code == 200 and r.json()["proposal"]["status"] == "approved"
    rule = [x for x in client.get("/api/rules", headers=owner).json() if x["rule_id"] == "TONE-04"][0]
    assert rule["version"] == 2 and rule["params"]["normalize"] is True
    run2 = client.post("/api/redteam/run", headers=owner, json={"rule_id": "TONE-04"}).json()
    assert run2["summary"]["caught"] > before and run2["rule_version"] == 2
    assert run2["summary"]["missed"] == 0 and run2["proposal"] is None
    # the new rule now catches a real submission that used to slip through
    aid = make_asset(client, c, "A C T   N O W and save with Finora Save.")
    d = client.get(f"/api/assets/{aid}", headers=c).json()
    assert "TONE-04" in {f["rule_id"] for f in d["findings"]}
    # re-test endpoint reports live state
    rt = client.post(f"/api/redteam/proposals/{pid}/retest", headers=owner).json()["proposal"]["retest"]
    assert rt["after_caught"] == rt["total"]


def test_redteam_covers_each_eligible_rule(client):
    owner = login(client, "owner@finora.example")
    for rid in ("MSG-07", "ASCI-02"):
        run = client.post("/api/redteam/run", headers=owner, json={"rule_id": rid}).json()
        assert run["summary"]["missed"] > 0, rid
        assert run["proposal"]["retest"]["after_caught"] == run["proposal"]["retest"]["total"], rid
        assert run["proposal"]["retest"]["false_positives"] == [], rid


def test_redteam_limits(client):
    owner, c = login(client, "owner@finora.example"), login(client)
    assert client.post("/api/redteam/run", headers=owner, json={"rule_id": "PRIV-01"}).status_code == 422
    assert client.post("/api/redteam/run", headers=c, json={"rule_id": "TERM-01"}).status_code == 403


def test_tightened_rule_does_not_flag_normal_copy(client):
    from app.engine import redteam
    from app.seed import RULES
    from types import SimpleNamespace
    rid, title, cat, sev, method, params, desc = [r for r in RULES if r[0] == "TERM-01"][0]
    rule = SimpleNamespace(rule_id=rid, title=title, method=method, params=params, description=desc, severity=sev, version=1)
    res, _ = redteam.run_variants(rule)
    p, _ = redteam.propose(rule, res)
    assert redteam.false_positives(rule, p) == []


def test_rulebook_health_shows_overrides_and_ambiguity(client):
    c, owner = login(client), login(client, "owner@finora.example")
    for i in range(3):
        aid = make_asset(client, c, "Hurry, open Finora Save.", title=f"a{i}")
        f = [x for x in client.get(f"/api/assets/{aid}", headers=c).json()["findings"] if x["rule_id"] == "TONE-04"][0]
        client.post(f"/api/findings/{f['id']}/decision", headers=c, json={"action": "reject", "note": "playful tone"})
    rb = client.get("/api/rulebook", headers=owner).json()
    row = [r for r in rb["rules"] if r["rule_id"] == "TONE-04"][0]
    assert row["hits"] == 3 and row["rejected"] == 3 and row["override_rate"] == 1.0 and row["ambiguous"]
    assert any(x["rule_id"] == "TONE-04" and x["team"] == "Social" and x["assets"] == 3 for x in rb["repeated_by_team"])
    assert client.get("/api/insights", headers=owner).json()["status_counts"]["Auto-reviewed"] == 3
