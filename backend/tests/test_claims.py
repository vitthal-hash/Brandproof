import datetime as dt

from app.engine import claims as cl
from conftest import ctx_for, login

T = dt.date(2026, 11, 17)


def ledger(dbs, text):
    _, facts, _ = ctx_for(dbs)
    return {c.kind + ":" + c.text.lower(): c for c in cl.ledger(text, facts, T)}


def verdicts(dbs, text):
    return [(c.text, c.verdict, c.fact_id) for c in cl.ledger(text, ctx_for(dbs)[1], T)]


def test_supported_rate_with_ceiling_wording(dbs):
    v = verdicts(dbs, "Earn up to 6.5% p.a. on Finora Save.")
    assert ("up to 6.5% p.a", "Supported", "F-03") in [(t.rstrip("."), a, b) for t, a, b in v]


def test_contradicted_rate(dbs):
    c = [x for x in cl.ledger("Get 7.5% interest.", ctx_for(dbs)[1], T) if x.kind == "rate"][0]
    assert c.verdict == cl.CONTRADICTED and c.fact_id == "F-03"


def test_ceiling_without_up_to_needs_human(dbs):
    c = [x for x in cl.ledger("Earn 6.5% interest.", ctx_for(dbs)[1], T) if x.kind == "rate"][0]
    assert c.verdict == cl.NEEDS_HUMAN


def test_guarantee_contradicted_by_f12(dbs):
    c = cl.ledger("Earn guaranteed returns.", ctx_for(dbs)[1], T)[0]
    assert (c.verdict, c.fact_id) == (cl.CONTRADICTED, "F-12")


def test_outdated_offer_from_expired_fact(dbs):
    c = [x for x in cl.ledger("Enjoy our launch cashback this month.", ctx_for(dbs)[1], T) if x.kind == "offer"][0]
    assert (c.verdict, c.fact_id) == (cl.OUTDATED, "F-19")


def test_outdated_offer_from_own_date(dbs):
    c = [x for x in cl.ledger("Special discount ends 10 Oct 2026.", ctx_for(dbs)[1], T) if x.kind == "offer"][0]
    assert c.verdict == cl.OUTDATED


def test_offer_amount_contradicted(dbs):
    c = [x for x in cl.ledger("Get a ₹500 referral bonus until 31 Dec 2026.", ctx_for(dbs)[1], T) if x.kind == "offer"][0]
    assert (c.verdict, c.fact_id) == (cl.CONTRADICTED, "F-20")


def test_offer_supported_and_clean(dbs):
    c = [x for x in cl.ledger("Earn a ₹200 referral bonus until 31 Dec 2026.", ctx_for(dbs)[1], T) if x.kind == "offer"][0]
    assert c.verdict == cl.SUPPORTED


def test_superlative_unsupported(dbs):
    c = [x for x in cl.ledger("India's best savings account.", ctx_for(dbs)[1], T) if x.kind == "superlative"][0]
    assert c.verdict == cl.UNSUPPORTED


def test_safety_and_regulator_claims(dbs):
    f = ctx_for(dbs)[1]
    assert cl.ledger("Your money is 100% safe.", f, T)[0].verdict == cl.CONTRADICTED
    assert cl.ledger("We are RBI approved.", f, T)[0].verdict == cl.CONTRADICTED
    assert cl.ledger("Deposits insured up to ₹5 lakh per depositor.", f, T)[0].verdict == cl.SUPPORTED


def test_speed_hours_and_fees(dbs):
    f = ctx_for(dbs)[1]
    assert [c for c in cl.ledger("Open in 2 minutes.", f, T) if c.kind == "speed"][0].verdict == cl.CONTRADICTED
    assert [c for c in cl.ledger("Open in about 5 minutes.", f, T) if c.kind == "speed"][0].verdict == cl.SUPPORTED
    assert cl.ledger("Support 24/7.", f, T)[0].verdict == cl.CONTRADICTED
    assert [c for c in cl.ledger("Zero charges on everything.", f, T) if c.kind == "fee"][0].verdict == cl.CONTRADICTED
    assert [c for c in cl.ledger("No monthly maintenance fee.", f, T) if c.kind == "fee"][0].verdict == cl.SUPPORTED


def test_hinglish_guarantee(dbs):
    assert cl.ledger("Paayein pakka returns.", ctx_for(dbs)[1], T)[0].verdict == cl.CONTRADICTED


def test_fact_expiry_makes_claims_outdated(dbs):
    f = ctx_for(dbs)[1]
    f10 = [x for x in f if x.id == "F-10"][0]
    f10.valid_to = dt.date(2026, 11, 1)
    c = [x for x in cl.ledger("Over 2 million customers trust us.", f, T) if x.kind == "count"][0]
    assert c.verdict == cl.OUTDATED


def test_ai_added_claim_with_fake_quote_is_dropped(dbs):
    class Gw:
        enabled = True

        def call_json(self, *a, **k):
            return {"claims": [{"quote": "this text is not in the content", "kind": "rate", "verdict": "Supported", "confidence": 0.99}]}
    out = cl.ledger("Hello there.", ctx_for(dbs)[1], T, Gw())
    assert out == []


def test_vault_edit_changes_verdict_via_api(client):
    owner = login(client, "owner@finora.example")
    h = login(client)
    r = client.post("/api/assets", headers=h, data={"title": "t", "intent": "Announce our new savings account", "text": "Earn up to 6.5% p.a. T&C apply."})
    aid = r.json()["id"]
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    assert all(c["verdict"] == "Supported" for c in d["claims"] if c["kind"] == "rate")
    f3 = [f for f in client.get("/api/facts", headers=owner).json() if f["id"] == "F-03"][0]
    f3["numeric"] = {"unit": "%", "op": "<=", "value": 5.0}
    assert client.put("/api/facts/F-03", headers=owner, json=f3).status_code == 200
    d = client.post(f"/api/assets/{aid}/rerun", headers=h).json()
    assert [c["verdict"] for c in d["claims"] if c["kind"] == "rate"] == ["Contradicted"]


def test_only_owner_edits_facts(client):
    h = login(client)
    f = client.get("/api/facts", headers=h).json()[0]
    assert client.put(f"/api/facts/{f['id']}", headers=h, json=f).status_code == 403


def test_fact_requires_source_and_owner(client):
    owner = login(client, "owner@finora.example")
    r = client.put("/api/facts/F-99", headers=owner, json={"id": "F-99", "statement": "x", "source": "", "owner": ""})
    assert r.status_code == 422
