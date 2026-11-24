"""Deterministic rule evaluators. Each rule method maps to one function returning Hit objects."""
import re
from dataclasses import dataclass, field

from . import textutil as tu
from . import translit


@dataclass
class Hit:
    start: int
    end: int
    quote: str
    explanation: str
    replacement: str | None = None  # span replacement for fixes; None means no automatic fix
    confidence: float = 1.0
    extra: dict = field(default_factory=dict)


@dataclass
class Ctx:
    """Everything a rule may need about the asset beyond the text."""
    intent: str = ""
    ai_generated: bool = False
    alt_text: str = ""
    kind: str = "text"
    image_count: int = 0
    library: dict = field(default_factory=dict)   # {"term": [...], "palette": [...], "competitor": [...]}
    today: object = None


DATE_RX = re.compile(
    r"\b(\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(\s+\d{2,4})?"
    r"|(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(st|nd|rd|th)?(,?\s+\d{2,4})?"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
OFFER_RX = re.compile(r"\b(offer|discount|cashback|bonus|deal|limited[- ]time|special price|promo)\b", re.IGNORECASE)
RATE_RX = re.compile(r"\b(interest|returns?|p\.?a\.?|per annum|apy|apr)\b|\d+(\.\d+)?\s*%(?!\s*(safe|secure|protected|guaranteed|sure))", re.IGNORECASE)
DISCLAIMER_RX = re.compile(r"(t\s*&\s*c|terms\s*(and|&)\s*conditions)\s*apply|\*\s*t\s*&\s*c|subject to change", re.IGNORECASE)
AI_LABEL_RX = re.compile(r"(ai[- ]generated|created (with|using) ai|made (with|using) ai|generated (with|using) ai|ai[- ]created)", re.IGNORECASE)

PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "aadhaar": re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "card": re.compile(r"(?<!\d)(?:\d[ -]?){14,15}\d(?!\d)"),
    "phone": re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),   # 9876543210, 98765 43210, +91 98765-43210
}


def phrase_matches(text: str, params: dict):
    """Yield (start, end, phrase) for every banned/required phrase hit."""
    out = []
    pats = []
    fuzzy = params.get("normalize", False)
    for ph in params.get("phrases", []):
        pats.append((ph, tu.fuzzy_pattern(ph) if fuzzy else tu.plain_pattern(ph)))
    for rx in params.get("regex", []):
        pats.append((rx, re.compile(rx, re.IGNORECASE)))
    taken = []
    for ph, p in pats:
        for m in p.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            out.append((m.start(), m.end(), ph))
    for ph in params.get("translit_phrases", []):  # Hinglish spelling variants and Devanagari
        for s, e in translit.find(text, ph):
            if any(s < te and ts < e for ts, te in taken):
                continue
            taken.append((s, e))
            out.append((s, e, ph))
    return sorted(out)


def _repl_for(phrase_hit: str, params: dict) -> str | None:
    reps = params.get("replacements", {})
    if phrase_hit in reps:
        return reps[phrase_hit]
    low = phrase_hit.lower()
    for k, v in reps.items():
        if k.lower() == low:
            return v
    return reps.get("*")


def eval_phrase(rule, text: str, ctx: Ctx) -> list[Hit]:
    p = rule.params
    hits = []
    for s, e, ph in phrase_matches(text, p):
        rep = _repl_for(ph, p)
        hits.append(Hit(s, e, text[s:e], p.get("message", rule.description) or rule.title, rep))
    return hits


def eval_product_name(rule, text: str, ctx: Ctx) -> list[Hit]:
    name = rule.params.get("name", "Finora Save")
    base = name.split()[0]
    rest = name.split()[1]
    rx = re.compile(rf"\b{base}\s*{rest}\b", re.IGNORECASE)
    hits = []
    for m in rx.finditer(text):
        if m.group(0) != name:
            hits.append(Hit(m.start(), m.end(), m.group(0),
                            f"The product is always written '{name}'.", name))
    return hits


def eval_preferred_term(rule, text: str, ctx: Ctx) -> list[Hit]:
    hits = []
    for bad, good in rule.params.get("map", {}).items():
        for m in tu.plain_pattern(bad).finditer(text):
            hits.append(Hit(m.start(), m.end(), m.group(0), f"Prefer '{good}' over '{bad}'.", good))
    return hits


def eval_caps(rule, text: str, ctx: Ctx) -> list[Hit]:
    hits = []
    n = rule.params.get("min_words", 3)
    for m in re.finditer(rf"\b(?:[A-Z]{{3,}}\s+){{{n - 1},}}[A-Z]{{3,}}\b", text):
        hits.append(Hit(m.start(), m.end(), m.group(0), "Avoid shouting in capital letters.",
                        m.group(0).capitalize()))
    return hits


def eval_exclaim(rule, text: str, ctx: Ctx) -> list[Hit]:
    limit = rule.params.get("max", 1)
    # Count characters, not groups: "!!" is two exclamation marks.
    marks = [m for m in re.finditer(r"!", text)]
    if len(marks) <= limit:
        return []
    return [Hit(m.start(), m.end(), "!", f"Use at most {limit} exclamation mark(s).", "") for m in marks[limit:]]


def eval_offer_end_date(rule, text: str, ctx: Ctx) -> list[Hit]:
    m = OFFER_RX.search(text)
    loose = False if rule.params.get("require_date") else bool(re.search(r"\b(valid|ends?|till|until|expires?)\b.*\b\d", text, re.I))
    if m and not DATE_RX.search(text) and not loose:
        return [Hit(m.start(), m.end(), m.group(0),
                    "Time-limited offers must state an explicit end date.", None, extra={"stable_sig": True})]
    return []


def _append_span(text: str, add: str) -> list:
    """Insertion point at the end of the text, never deleting a character."""
    s = text.rstrip()
    if s.endswith((".", "!", "?")):
        return [len(s) - 1, len(s), s[-1] + add]
    return [len(s), len(s), add]


def eval_disclaimer(rule, text: str, ctx: Ctx) -> list[Hit]:
    m = RATE_RX.search(text)
    for term in rule.params.get("extra_terms", []):
        if not m:
            m = tu.plain_pattern(term).search(text)
    if m and not DISCLAIMER_RX.search(text):
        return [Hit(m.start(), m.end(), m.group(0), "Rate or return claims need 'T&C apply'.", None,
                    extra={"replace_override": _append_span(text, " T&C apply."), "stable_sig": True})]
    return []


def eval_ai_label(rule, text: str, ctx: Ctx) -> list[Hit]:
    if ctx.ai_generated and not AI_LABEL_RX.search(text):
        extra = {"stable_sig": True, **({"replace_override": _append_span(text, " Created with AI.")} if text.strip() else {})}
        return [Hit(-1, -1, "", "AI-generated content must carry a visible AI label.", None, extra=extra)]
    return []


def eval_pii(rule, text: str, ctx: Ctx) -> list[Hit]:
    hits, taken = [], []
    for kind, rx in PII_PATTERNS.items():
        for m in rx.finditer(text):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            hits.append(Hit(m.start(), m.end(), m.group(0), f"Looks like a personal {kind} number or address.",
                            "[removed]", extra={"pii": kind}))
    return sorted(hits, key=lambda h: h.start)


def eval_reading_level(rule, text: str, ctx: Ctx) -> list[Hit]:
    score = tu.flesch_reading_ease(text)
    floor = rule.params.get("min_ease", 50)
    if score is not None and score < floor:
        return [Hit(0, min(len(text), 120), text[:120],
                    f"Reading ease is {score:.0f} (target {floor}+). Shorter sentences and simpler words help.",
                    None, extra={"score": round(score, 1), "stable_sig": True})]
    return []


def eval_alt_text(rule, text: str, ctx: Ctx) -> list[Hit]:
    needs = ctx.kind == "image" or ctx.image_count > 0
    if needs and len((ctx.alt_text or "").strip()) < 5:
        return [Hit(-1, -1, "", "Images need alt text for screen-reader users.", None)]
    return []


# Methods evaluated on text. File-level checks (contrast, palette) live in trust/file checks.
TEXT_METHODS = {
    "phrase": eval_phrase, "product_name": eval_product_name, "preferred_term": eval_preferred_term,
    "caps": eval_caps, "exclaim": eval_exclaim, "offer_end_date": eval_offer_end_date,
    "disclaimer": eval_disclaimer, "ai_label": eval_ai_label, "pii": eval_pii,
    "reading_level": eval_reading_level, "alt_text": eval_alt_text,
}
