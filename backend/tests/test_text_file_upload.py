"""A .txt or .md file uploaded through the form is reviewed as text (the file picker accepts these types)."""
from conftest import login


def _rules(client, h, aid):
    return {f["rule_id"].split("@")[0] for f in client.get(f"/api/assets/{aid}", headers=h).json()["findings"]}


def test_txt_file_upload_is_reviewed_as_text(client):
    h = login(client)
    body = "Finora Save gives guaranteed returns. Hurry, act now!".encode()
    r = client.post("/api/assets", headers=h, data={"title": "Text file", "intent": "Announce the savings account", "channel": "social"},
                    files={"file": ("copy.txt", body, "text/plain")})
    assert r.status_code == 200, r.text
    assert "TERM-01" in _rules(client, h, r.json()["id"])


def test_md_file_upload_keeps_zero_width_characters(client):
    h = login(client)
    body = "Earn\u200b guar\u200banteed returns.\u200b\u200b".encode("utf-8")
    r = client.post("/api/assets", headers=h, data={"title": "Md file", "intent": "Announce the savings account", "channel": "social"},
                    files={"file": ("copy.md", body, "text/markdown")})
    assert r.status_code == 200, r.text
    assert "TRUST-01" in _rules(client, h, r.json()["id"])


def test_empty_txt_file_is_still_refused(client):
    h = login(client)
    r = client.post("/api/assets", headers=h, data={"title": "Empty", "intent": "Announce the savings account", "channel": "social"},
                    files={"file": ("empty.txt", b"   \n", "text/plain")})
    assert r.status_code == 422


def test_pasted_text_still_wins_over_file(client):
    h = login(client)
    r = client.post("/api/assets", headers=h, data={"title": "Both", "intent": "Announce the savings account", "channel": "social", "text": "Open your Finora Save account today. Terms apply."},
                    files={"file": ("copy.txt", b"guaranteed returns", "text/plain")})
    assert r.status_code == 200
    assert "TERM-01" not in _rules(client, h, r.json()["id"])
