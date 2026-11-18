"""Rulebook Red-Team (I3 v1). An adversary writes content that breaks a rule but tries to slip past it.
Every miss is a loophole. The tool proposes a tighter rule, the owner approves it, and the same
variants are re-tested (before/after), together with benign sentences to guard against false positives."""
import copy
import re
from types import SimpleNamespace

from . import textutil as tu
from . import trust
from .rules import TEXT_METHODS, Ctx

ELIGIBLE = {"TERM-01", "TONE-04", "MSG-07", "ASCI-02"}

# (text, phrase_to_add, technique). phrase None means the fix is a parameter change, not a new phrase.
HAND = {
    "TERM-01": [
        ("You simply cannot lose money with Finora Save.", "cannot lose money", "euphemism"),
        ("Your returns are locked in, forever.", "returns are locked in", "euphemism"),
        ("Enjoy assured income every month.", "assured income", "synonym"),
        ("Pakka munafa, bilkul safe.", "pakka munafa", "hinglish"),
        ("Garanteed returns on every deposit.", "garanteed returns", "misspelling"),
        ("Returns guaranteed* by us.", "returns guaranteed", "word order"),
    ],
    "TONE-04": [
        ("The offer disappears at midnight, so grab it now.", "grab it now", "euphemism"),
        ("Don't wait, this will not last.", "will not last", "euphemism"),
        ("Be quick, spots are running out!", "spots are running out", "euphemism"),
        ("Abhi hi karo, warna chhoot jayega.", "abhi hi karo", "hinglish"),
        ("Act  now and save.", None, "double space"),
        ("A C T   N O W and save.", None, "spaced letters"),
    ],
    "MSG-07": [
        ("Festive cashback offer ends in 3 days.", None, "relative time"),
        ("Special bonus offer, hurry, only 2 days left.", None, "relative time"),
        ("Limited offer valid while 100 slots remain.", None, "number but no date"),
        ("Exclusive discount for the next 50 customers.", None, "number but no date"),
    ],
    "ASCI-02": [
        ("Grow your money at 6.5 percent a year.", "percent", "spelled-out percent"),
        ("Earn 6.5 per cent every year with Finora Save.", "per cent", "spelled-out percent"),
        ("Get a yield you will love on Finora Save.", "yield", "synonym"),
        ("Your balance compounds every month at 6.5 pc.", "pc", "abbreviation"),
    ],
}
BENIGN = ["Open an account whenever you are ready.", "Your statement is available in the app.",
          "We are here to help, 9am to 9pm IST.", "Savings goals help you plan ahead.",
          "Download the Finora app from your app store."]
BENIGN_EXTRA = {"MSG-07": ["Refer a friend and earn a ₹200 referral bonus until 31 Dec 2026."],
                "ASCI-02": ["Earn interest up to 6.5% p.a. on Finora Save. T&C apply."]}


def _obfuscate(phrase: str) -> list[tuple[str, str]]:
    first, _, rest = phrase.partition(" ")
    tail = (" " + rest) if rest else ""
    out = []
    if len(first) >= 4:
        out.append((" ".join(first) + tail, "spaced letters"))
        out.append((".".join(first) + tail, "dotted letters"))
    leet = first.translate(str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"}))
    if leet != first:
        out.append((leet + tail, "leetspeak"))
    return out


def mutations(rule) -> list[dict]:
    """Mechanical rewrites of phrases already in the rule (keyword-evasion tricks)."""
    out = []
    phrases = [p for p in rule.params.get("phrases", []) if re.fullmatch(r"[a-z' -]+", p) and len(p) >= 5][:4]
    for ph in phrases:
        for text, tech in _obfuscate(ph)[:2] + _obfuscate(ph)[2:3]:
            out.append({"text": f"Finora Save: {text}.", "phrase": None, "technique": tech, "source": "mutation"})
    return out


def handwritten(rule_id: str) -> list[dict]:
    return [{"text": t, "phrase": ph, "technique": tech, "source": "handwritten"} for t, ph, tech in HAND.get(rule_id, [])]


def llm_variants(rule, gateway, asset_id=None) -> list[dict]:
    if gateway is None or not gateway.enabled:
        return []
    system = "You are a red-team tester for a brand rulebook. Reply with JSON only."
    user = (f"Rule {rule.rule_id}: {rule.title}. {rule.description}\nCurrent phrases: {rule.params.get('phrases', [])}\n"
            'Write 8 short marketing sentences that clearly break this rule in spirit but are worded to evade keyword matching '
            '(euphemisms, Hinglish, misspellings, spacing). Return {"variants":[{"text":"...","core_phrase":"the exact words that break the rule, copied from text","technique":"..."}]}.')
    data = gateway.call_json("redteam_variants", system, user, asset_id=asset_id, max_tokens=1200)
    out = []
    variants = (data or {}).get("variants", [])
    for v in (variants if isinstance(variants, list) else [])[:10]:
        if not isinstance(v, dict):
            continue
        text, core = str(v.get("text", "")).strip(), str(v.get("core_phrase", "")).strip()
        if text:
            out.append({"text": text, "phrase": core if core and core.lower() in text.lower() else None,
                        "technique": str(v.get("technique", "llm")), "source": "llm"})
    return out


def _as_rule(rule, params=None):
    return SimpleNamespace(rule_id=rule.rule_id, method=rule.method, params=params if params is not None else rule.params,
                           description=getattr(rule, "description", ""), title=getattr(rule, "title", ""),
                           severity=getattr(rule, "severity", "medium"), version=getattr(rule, "version", 1))


def caught(rule_like, text: str, ai_generated=False) -> bool:
    clean = trust.analyze_plain_text(text).clean_text
    fn = TEXT_METHODS[rule_like.method]
    return bool(fn(rule_like, clean, Ctx(ai_generated=ai_generated)))


def evaluate(rule, variants, params=None) -> list[dict]:
    rl = _as_rule(rule, params)
    return [{**v, "caught": caught(rl, v["text"])} for v in variants]


def false_positives(rule, params=None) -> list[str]:
    rl = _as_rule(rule, params)
    return [t for t in BENIGN + BENIGN_EXTRA.get(rule.rule_id, []) if caught(rl, t)]


def propose(rule, results: list[dict]) -> tuple[dict, str]:
    """Tighter params and a plain-language reason, from the missed variants."""
    p = copy.deepcopy(rule.params)
    missed = [r for r in results if not r["caught"]]
    notes = []
    if rule.method == "phrase":
        add = []
        for r in missed:
            if r.get("phrase") and r["phrase"].lower() not in [x.lower() for x in p.get("phrases", [])]:
                add.append(r["phrase"].lower())
        if any(r["technique"] in ("spaced letters", "dotted letters", "leetspeak", "double space", "misspelling") for r in missed):
            if not p.get("normalize"):
                p["normalize"] = True
                notes.append("turn on spacing/leetspeak-tolerant matching")
        if add:
            p["phrases"] = list(p.get("phrases", [])) + sorted(set(add))
            notes.append(f"add {len(set(add))} phrase(s): " + ", ".join(sorted(set(add))))
    elif rule.method == "offer_end_date":
        p["require_date"] = True
        notes.append("require a real calendar date; 'in 3 days' or '100 slots' no longer count")
    elif rule.method == "disclaimer":
        terms = sorted({r["phrase"] for r in missed if r.get("phrase")})
        p["extra_terms"] = sorted(set(p.get("extra_terms", [])) | set(terms))
        notes.append("also treat these words as a rate claim: " + ", ".join(terms))
    return p, "; ".join(notes) or "no automatic change available"


def run_variants(rule, gateway=None, asset_id=None) -> tuple[list[dict], dict]:
    variants = handwritten(rule.rule_id) + mutations(rule) + llm_variants(rule, gateway, asset_id)
    results = evaluate(rule, variants)
    total = len(results)
    n_caught = sum(1 for r in results if r["caught"])
    return results, {"total": total, "caught": n_caught, "missed": total - n_caught,
                     "catch_rate": round(n_caught / total, 2) if total else 0.0,
                     "sources": sorted({r["source"] for r in results})}


def retest(rule, results: list[dict], params: dict) -> dict:
    after = evaluate(rule, [{k: v for k, v in r.items() if k != "caught"} for r in results], params)
    before_c = sum(1 for r in results if r["caught"])
    after_c = sum(1 for r in after if r["caught"])
    return {"total": len(results), "before_caught": before_c, "after_caught": after_c,
            "still_missed": [r["text"] for r in after if not r["caught"]],
            "false_positives": false_positives(rule, params)}
