"""An offer claim is judged against the offer fact it actually matches, not the first offer fact that shares a word."""
from conftest import login


def _claims(client, h, text):
    r = client.post("/api/assets", headers=h, data={"title": "t", "intent": "Announce the offer", "channel": "social", "text": text})
    assert r.status_code == 200, r.text
    return client.get(f"/api/assets/{r.json()['id']}", headers=h).json()["claims"]


def test_festive_bonus_is_checked_against_the_festive_fact(client):
    h = login(client)
    c = [x for x in _claims(client, h, "Festive bonus: \u20b9100 on your first deposit. Terms apply.") if "bonus" in (x.get("text") or x.get("quote") or "").lower()]
    assert c and c[0]["fact_id"] == "F-21" and c[0]["verdict"] == "Supported"


def test_wrong_festive_amount_is_still_contradicted(client):
    h = login(client)
    c = [x for x in _claims(client, h, "Festive bonus: \u20b9500 on your first deposit. Terms apply.") if "bonus" in (x.get("text") or x.get("quote") or "").lower()]
    assert c and c[0]["fact_id"] == "F-21" and c[0]["verdict"] == "Contradicted"


def test_referral_bonus_still_matches_the_referral_fact(client):
    h = login(client)
    c = [x for x in _claims(client, h, "Earn a referral bonus of \u20b9500 per referral. Terms apply.") if "referral" in (x.get("text") or x.get("quote") or "").lower()]
    assert c and c[0]["fact_id"] in ("F-20", "F-17") and c[0]["verdict"] == "Contradicted"
