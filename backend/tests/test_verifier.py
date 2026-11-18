import datetime as dt

from app.engine import review
from app.engine.rules import Ctx
from conftest import ctx_for, login, make_asset

T = dt.date(2026, 11, 17)


def test_good_fix_is_verified_and_shown(client):
    h = login(client)
    aid = make_asset(client, h, "Earn guaranteed returns on our new savings account.")
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    f = [x for x in d["findings"] if x["rule_id"] == "TERM-01"][0]
    assert f["fix"]["status"] == "verified"
    assert f["fix"]["verification"]["intent_lock"]["passed"]
    assert f["fix"]["replacement"] == "competitive interest"


def test_nothing_is_applied_without_a_human_click(client):
    h = login(client)
    aid = make_asset(client, h, "Earn guaranteed returns on our new savings account.")
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    assert len(d["versions"]) == 1 and "guaranteed" in d["version"]["text"]
    assert all(f["status"] == "open" for f in d["findings"])


def test_fix_that_loses_creator_intent_is_withheld(client):
    h = login(client)
    aid = make_asset(client, h, "Enjoy our launch cashback this month. Open Finora Save today.",
                     intent="Announce the launch cashback offer")
    d = client.get(f"/api/assets/{aid}", headers=h).json()
    f = [x for x in d["findings"] if x["rule_id"] == "CLAIM-02"][0]
    assert f["fix"]["status"] == "withheld"
    assert "Intent Lock" in f["fix"]["reason"]
    assert d["run"]["summary"]["fixes"]["withheld"] >= 1


def test_fix_that_introduces_a_violation_is_withheld(dbs):
    rules, facts, lib = ctx_for(dbs)
    ctx = Ctx(library=lib)
    text = "Hurry to open Finora Save."
    ana = review.analyze_text(text, rules, facts, ctx, None, T)
    f = [x for x in ana.findings if x.rule_id == "TONE-04"][0]
    from collections import Counter
    before = Counter(x.sig() for x in ana.findings)
    bad = (f.start, f.end, "Guaranteed returns")  # replaces the pressure word with a guarantee
    ver = review.verify_fix(text, bad, f, "Open Finora Save", rules, facts, ctx, None, T, before)
    assert not ver["verified"] and "TERM-01" in ver["introduces"]


def test_fix_that_does_not_resolve_is_withheld(dbs):
    rules, facts, lib = ctx_for(dbs)
    ctx = Ctx(library=lib)
    text = "Hurry to open Finora Save."
    ana = review.analyze_text(text, rules, facts, ctx, None, T)
    f = [x for x in ana.findings if x.rule_id == "TONE-04"][0]
    from collections import Counter
    ver = review.verify_fix(text, (f.start, f.end, "Hurry"), f, "Open Finora Save", rules, facts, ctx, None, T,
                            Counter(x.sig() for x in ana.findings))
    assert not ver["resolved"] and not ver["verified"]


def test_intent_lock_unit():
    ok = review.intent_lock("Announce our new savings account", "Our new savings account is here.", "Our new savings account is here!")
    assert ok["passed"]
    bad = review.intent_lock("Announce our new savings account", "Our new savings account is here.", "Hello.")
    assert not bad["passed"] and bad["lost"]
