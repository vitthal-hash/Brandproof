"""Small text helpers shared by the engine."""
import re
import unicodedata

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)
LEET = {"a": "[a@4]", "e": "[e3]", "i": "[i1!l]", "o": "[o0]", "s": "[s$5]", "t": "[t7]"}
SEP = r"[\s.\-_*]{0,2}"
STOP = set("""a an the and or but if of to in on at for with from by is are was were be been being it its this that these those
our your their my we you they i he she as so than then there here do does did not no yes will can could should would may might
have has had get got just very more most new now all any each every up out over into about also""".split())


def strip_invisible(text: str) -> str:
    return unicodedata.normalize("NFKC", text).translate(ZERO_WIDTH)


def fuzzy_pattern(phrase: str) -> re.Pattern:
    """Regex that tolerates spacing tricks, separators between letters and leetspeak."""
    parts = []
    for ch in phrase.lower():
        if ch == " ":
            parts.append(r"[\s.\-_*]+")
        elif ch in LEET:
            parts.append(LEET[ch] + SEP)
        elif ch.isalnum():
            parts.append(re.escape(ch) + SEP)
        else:
            parts.append(re.escape(ch) + r"\s*")
    body = "".join(parts)
    body = re.sub(re.escape(SEP) + r"$", "", body)
    return re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])", re.IGNORECASE)


def plain_pattern(phrase: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(phrase) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def sentences(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of sentences / lines."""
    spans, start = [], 0
    for m in re.finditer(r"[.!?\n]+(?:\s+|$)", text):
        end = m.start() + (1 if text[m.start()] in ".!?" else 0)
        if text[start:end].strip():
            spans.append((start, end))
        start = m.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F'’-]*", text)


def keywords(text: str) -> set[str]:
    out = set()
    for w in words(text.lower()):
        if w in STOP or len(w) < 3:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(n, 1)


def flesch_reading_ease(text: str) -> float | None:
    ws = [w for w in words(text) if re.match(r"[A-Za-z]", w)]
    ss = max(len(sentences(text)), 1)
    if len(ws) < 40:
        return None
    syl = sum(syllables(w) for w in ws)
    return 206.835 - 1.015 * (len(ws) / ss) - 84.6 * (syl / len(ws))


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(round(c)) for c in rgb)


def _lin(c: float) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb) -> float:
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def rgb_to_lab(rgb):
    r, g, b = (_lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b) -> float:
    la, lb = rgb_to_lab(a), rgb_to_lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def is_neutral(rgb) -> bool:
    mx, mn = max(rgb), min(rgb)
    return (mx - mn) < 22


def apply_replacements(text: str, reps: list[tuple[int, int, str]]) -> str:
    """Apply non-overlapping span replacements right-to-left."""
    for s, e, new in sorted(reps, key=lambda r: -r[0]):
        text = text[:s] + new + text[e:]
    return text
