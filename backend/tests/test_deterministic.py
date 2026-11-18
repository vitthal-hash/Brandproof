from types import SimpleNamespace

from app.engine import review, textutil as tu
from app.engine.rules import Ctx, TEXT_METHODS
from conftest import ctx_for


def run(db, text, **kw):
    rules, facts, lib = ctx_for(db)
    import datetime as dt
    ctx = Ctx(library=lib, **kw)
    return review.analyze_text(text, rules, facts, ctx, None, dt.date(2026, 11, 17)).findings


def ids(fs):
    return {f.rule_id for f in fs}


def test_guarantee_and_hinglish_terms(dbs):
    assert "TERM-01" in ids(run(dbs, "Earn guaranteed returns today."))
    assert "TERM-01" in ids(run(dbs, "Paayein pakka returns aur 100% safe."))


def test_product_name_casing(dbs):
    fs = run(dbs, "Open Finora save now.")
    f = [x for x in fs if x.rule_id == "TERM-02"][0]
    assert f.extra["replace"][2] == "Finora Save"


def test_pressure_and_hinglish_pressure(dbs):
    assert "TONE-04" in ids(run(dbs, "Act now to save."))
    assert "TONE-04" in ids(run(dbs, "Abhi karo aur jaldi karo."))


def test_caps_and_exclamation(dbs):
    fs = ids(run(dbs, "SAVE MORE EVERY DAY! Great! Really!"))
    assert {"TONE-05", "TONE-06"} <= fs
    assert "TONE-06" not in ids(run(dbs, "One mark only!"))


def test_offer_needs_end_date(dbs):
    assert "MSG-07" in ids(run(dbs, "Get a special cashback offer today."))
    assert "MSG-07" not in ids(run(dbs, "Get a special offer valid until 31 Dec 2026."))


def test_rate_needs_disclaimer(dbs):
    assert "ASCI-02" in ids(run(dbs, "Earn up to 6.5% p.a."))
    assert "ASCI-02" not in ids(run(dbs, "Earn up to 6.5% p.a. T&C apply."))


def test_ai_label_only_when_flagged(dbs):
    assert "DISC-01" in ids(run(dbs, "Meet our new savings app.", ai_generated=True))
    assert "DISC-01" not in ids(run(dbs, "Meet our new savings app.", ai_generated=False))
    assert "DISC-01" not in ids(run(dbs, "Meet our app. Created with AI.", ai_generated=True))


def test_pii_detected(dbs):
    fs = run(dbs, "Mail a.b@x.com or call 9876543210. PAN ABCDE1234F.")
    kinds = {f.extra.get("pii") for f in fs if f.rule_id == "PRIV-01"}
    assert {"email", "phone", "pan"} <= kinds


def test_alt_text(dbs):
    assert "A11Y-02" in ids(run(dbs, "", kind="image", alt_text=""))
    assert "A11Y-02" not in ids(run(dbs, "", kind="image", alt_text="A blue savings banner"))


def test_reading_level_low_for_dense_text(dbs):
    dense = ("Notwithstanding the aforementioned contractual considerations, subscribers should comprehend that "
             "indemnification obligations necessitate comprehensive documentation of administrative authorisations " * 3)
    assert "A11Y-03" in ids(run(dbs, dense))
    simple = "Open the app. Tap save. Add money. It is easy. " * 12
    assert "A11Y-03" not in ids(run(dbs, simple))


def test_contrast_math():
    assert round(tu.contrast_ratio((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert tu.contrast_ratio((119, 119, 119), (255, 255, 255)) < 4.6


def test_fuzzy_pattern_catches_tricks():
    rx = tu.fuzzy_pattern("guaranteed returns")
    for s in ["g u a r a n t e e d returns", "gu4r4nt33d returns", "g.u.a.r.a.n.t.e.e.d returns", "guaranteed   returns"]:
        assert rx.search(s), s
    assert not rx.search("guarded returns")


def test_pdf_contrast_and_palette(dbs):
    from conftest import pdf_bytes
    from app.engine import trust
    data = pdf_bytes(lambda p, m: (p.draw_rect(m.Rect(0, 0, 595, 200), color=None, fill=(0.078, 0.129, 0.239)),
                                   p.insert_text((60, 90), "Low contrast copy", fontsize=13, color=(0.25, 0.30, 0.45)),
                                   p.draw_rect(m.Rect(40, 250, 300, 300), color=None, fill=(0.85, 0.1, 0.2))))
    tr = trust.analyze("pdf", data)
    rules, facts, lib = ctx_for(dbs)
    fs = review.file_checks(tr, rules, lib, Ctx())
    assert {"A11Y-01", "VIS-01"} <= {f.rule_id for f in fs}
    # on-palette navy fill alone is fine
    data2 = pdf_bytes(lambda p, m: (p.draw_rect(m.Rect(0, 0, 595, 200), color=None, fill=(0.078, 0.129, 0.239)),
                                    p.insert_text((60, 90), "Good contrast", fontsize=13, color=(1, 1, 1))))
    fs2 = review.file_checks(trust.analyze("pdf", data2), rules, lib, Ctx())
    assert not fs2


def test_disclaimer_fix_never_deletes_a_character(dbs):
    from app.engine.review import apply_fix
    for text in ["Earn up to 6.5% p.a. on Finora Save", "Earn up to 6.5% p.a. on Finora Save.", "Earn up to 6.5% p.a. on Finora Save!"]:
        f = [x for x in run(dbs, text) if x.rule_id == "ASCI-02"][0]
        s, e, rep = f.extra["replace"]
        fixed = apply_fix(text, s, e, rep)
        assert fixed.endswith("T&C apply.") and fixed.startswith("Earn up to 6.5% p.a. on Finora Save")


def test_removing_a_word_leaves_clean_punctuation():
    from app.engine.review import apply_fix
    assert apply_fix("Hurry, last chance to join.", 0, 5, "") == "Last chance to join."
    assert apply_fix("Open now, hurry.", 10, 15, "") == "Open now."
    assert apply_fix("Open Finora Save. Hurry, join us.", 18, 23, "") == "Open Finora Save. Join us."
