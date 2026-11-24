"""Trust Layer: parse files, find hidden text, scan for prompt injection, redact sensitive data.

Nothing leaves this module toward an LLM without going through redact()."""
import base64
import io
import re
import shutil
import subprocess
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from . import textutil as tu
from .rules import PII_PATTERNS

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above|earlier)\s+(instructions|rules|guidelines|prompts?)",
    r"disregard\s+(all\s+|any\s+|the\s+|your\s+)?(previous|prior|above)?\s*(rules|guidelines|instructions)",
    r"(mark|rate|approve|treat|classify|report|label|score)\s+(this|the|it)\s+(\w+\s+){0,2}(as\s+)?(compliant|approved|safe|passing|clean|on[- ]brand|fine)",
    r"(do\s+not|don'?t|never)\s+(flag|report|mention|raise|list)\s+(any|this|these|issues|violations|findings|problems)",
    r"(approve|pass)\s+this\s+(asset|content|document|submission|post|file)",
    r"you\s+are\s+(now\s+)?(an?\s+)?(ai|assistant|reviewer|language model|compliance)",
    r"(system|developer)\s+(prompt|message|instruction)",
    r"(output|return|respond\s+with)\s+(only\s+)?(\"|')?(approved|compliant|no\s+(issues|findings|violations))",
    r"\bai\s+(reviewer|checker|model|assistant)\b",
    r"no\s+(issues|violations|findings|problems)\s+(found|detected)",
    # Hinglish and Hindi phrasings of the same attacks
    r"(pichle|purane|sabhi|saare)\s+(nirdesh|niyam|instructions?|rules)\s+(ko\s+)?(ignore|bhool|andekha)",
    r"(is(se)?|ise)\s+(approve|pass|theek)\s+(kar|karo|kijiye)",
    r"koi\s+(issue|galti|problem)\s+(mat|na)\s+(batao|dikhao|batana)",
    r"पिछले\s+निर्देश|सभी\s+नियम\s+(अनदेखा|भूल)|इसे\s+(मंजूर|अप्रूव)\s+कर",
    r"(ignore|override)\s+(the\s+)?(brand\s+)?(guidelines|constitution|rulebook)",
]
INJECTION_RX = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


# ---------------------------------------------------------------- look-alike characters
# Cyrillic and Greek letters that read as Latin letters. A word that mixes them with real Latin letters
# ("guаranteed" with a Cyrillic а) slips past phrase rules. We fold such words to Latin for review and flag them.
_LOOK = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s", "һ": "h",
    "ԁ": "d", "ԛ": "q", "ԝ": "w", "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S", "У": "Y",
    "ο": "o", "α": "a", "ν": "v", "ι": "i", "κ": "k", "ρ": "p", "υ": "u", "Ο": "O", "Α": "A", "Β": "B", "Ε": "E",
    "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def fold_lookalikes(text: str) -> tuple[str, list[dict]]:
    """Fold look-alike letters to Latin inside words that also contain real Latin letters.
    Words written entirely in Cyrillic or Greek are genuine text in that language and are left alone."""
    found: list[dict] = []

    def fix(m: re.Match) -> str:
        w = m.group(0)
        if not any(ch in _LOOK for ch in w) or not any("a" <= ch.lower() <= "z" for ch in w):
            return w
        folded = "".join(_LOOK.get(ch, ch) for ch in w)
        chars = sorted({unicodedata.name(ch, "?").split(" ")[0].title() + " " + ch for ch in w if ch in _LOOK})
        found.append({"text": w, "folded": folded, "chars": chars})
        return folded
    return _WORD.sub(fix, text), found


# ---------------------------------------------------------------- local OCR (no data leaves the server)
_LANGS: str | None = None


def _ocr_langs(exe: str) -> str:
    global _LANGS
    if _LANGS is None:
        try:
            out = subprocess.run([exe, "--list-langs"], capture_output=True, timeout=10).stdout.decode("utf-8", "ignore")
            have = set(out.split())
            _LANGS = "eng+hin" if "hin" in have else "eng"
        except Exception:
            _LANGS = "eng"
    return _LANGS


def local_ocr(data: bytes, timeout: int = 25) -> str:
    """Read text from an image with the Tesseract program if it is installed. Returns '' if it is not."""
    exe = shutil.which("tesseract")
    if not exe or not data:
        return ""
    try:
        p = subprocess.run([exe, "stdin", "stdout", "-l", _ocr_langs(exe), "--psm", "6"], input=data,
                           capture_output=True, timeout=timeout)
        return p.stdout.decode("utf-8", "ignore").strip()
    except Exception:
        return ""


def local_ocr_faint(data: bytes, timeout: int = 20) -> str:
    """Second OCR pass for FAINT text. Tesseract binarises a whole image at one threshold, so text that is only a few
    shades away from its background vanishes as soon as the image also holds strong text. Here every pixel that
    differs a little from the dominant background becomes black on white, which makes faint text as readable as
    strong text. Returns '' if Tesseract is missing, the image is very large, or nothing can be read."""
    exe = shutil.which("tesseract")
    if not exe or not data:
        return ""
    try:
        from PIL import Image, ImageStat
        im = Image.open(io.BytesIO(data)).convert("L")
        if im.width * im.height > 8_000_000:
            return ""
        bg = ImageStat.Stat(im).median[0]
        boosted = im.point(lambda v: 0 if abs(v - bg) >= 6 else 255)
        buf = io.BytesIO()
        boosted.save(buf, "PNG")
        p = subprocess.run([exe, "stdin", "stdout", "-l", _ocr_langs(exe), "--psm", "6"], input=buf.getvalue(),
                           capture_output=True, timeout=timeout)
        return p.stdout.decode("utf-8", "ignore").strip()
    except Exception:
        return ""


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


@dataclass
class TrustResult:
    kind: str
    raw_text: str = ""
    clean_text: str = ""
    hidden: list = field(default_factory=list)       # {text, reason, page}
    injections: list = field(default_factory=list)   # {phrase, hidden, snippet}
    stripped: list = field(default_factory=list)     # notes on what the sanitiser removed
    features: dict = field(default_factory=dict)     # spans/colours for file-level checks
    notes: list = field(default_factory=list)
    lookalikes: list = field(default_factory=list)   # {text, folded, chars}

    def public(self) -> dict:
        return {"kind": self.kind, "hidden": self.hidden, "injections": self.injections,
                "stripped": self.stripped, "notes": self.notes,
                "has_hidden": bool(self.hidden), "differs": self.raw_text.strip() != self.clean_text.strip(),
                "lookalikes": self.lookalikes, "ocr": self.features.get("ocr", "")}


_SPACED = re.compile(r"(?<![A-Za-z])(?:[A-Za-z][ .\-_*]){3,}[A-Za-z](?![A-Za-z])")
_B64 = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{24,}={0,2}(?![A-Za-z0-9+/])")


def _variants(text: str) -> list[tuple[str, str]]:
    """The text as written, with spaced-out letters joined ("i g n o r e"), and any base64 blobs decoded."""
    out = [("", text)]
    joined = _SPACED.sub(lambda m: re.sub(r"[ .\-_*]", "", m.group(0)), text)
    # keep word breaks: "i g n o r e  previous" -> "ignore  previous"
    if joined != text:
        out.append(("spaced-out letters", joined))
    for m in _B64.finditer(text):
        try:
            dec = base64.b64decode(m.group(0) + "=" * (-len(m.group(0)) % 4), validate=False).decode("utf-8", "ignore")
        except Exception:
            continue
        if dec and sum(c.isprintable() for c in dec) / len(dec) > 0.9 and len(dec) >= 12:
            out.append(("base64", dec))
    return out


def scan_injection(text: str, hidden_texts: list[str] | None = None) -> list[dict]:
    found = []
    hidden_texts = hidden_texts or []
    for tag, body in _variants(text):
        for rx in INJECTION_RX:
            for m in rx.finditer(body):
                snippet = body[max(0, m.start() - 20): m.end() + 20].replace("\n", " ")
                is_hidden = any(m.group(0).lower() in h.lower() for h in hidden_texts) or bool(tag)
                found.append({"phrase": m.group(0), "hidden": is_hidden, "snippet": snippet,
                              **({"encoding": tag} if tag else {})})
    seen, out = set(), []
    for f in found:
        k = f["phrase"].lower()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


# ---------------------------------------------------------------- text
_HIDDEN_HTML = re.compile(
    r"<(?P<tag>[a-z][a-z0-9]*)\b(?=[^>]*(?:\bhidden\b(?!\s*=\s*[\"']?false)|style\s*=\s*[\"'][^\"']*"
    r"(?:display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0|opacity\s*:\s*0|color\s*:\s*(?:#fff(?:fff)?\b|white\b))))"
    r"[^>]*>(?P<inner>.*?)</(?P=tag)>", re.IGNORECASE | re.DOTALL)


def analyze_plain_text(text: str) -> TrustResult:
    res = TrustResult(kind="text", raw_text=text)
    clean = text
    hidden = []
    for m in re.finditer(r"<!--(.*?)-->", clean, re.DOTALL):
        hidden.append({"text": m.group(1).strip(), "reason": "HTML comment", "page": None})
    if hidden:
        res.stripped.append(f"{len(hidden)} HTML comment(s) removed")
    clean = re.sub(r"<!--.*?-->", "", clean, flags=re.DOTALL)
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    # elements a browser would not show: display:none, visibility:hidden, zero font, white or transparent text, hidden attribute
    for m in list(_HIDDEN_HTML.finditer(clean)):
        inner = re.sub(r"<[^>]+>", " ", m.group("inner")).strip()
        if inner:
            hidden.append({"text": inner[:300], "reason": "HTML element hidden by style", "page": None})
    n_html = len(_HIDDEN_HTML.findall(clean))
    if n_html:
        res.stripped.append(f"{n_html} hidden HTML element(s) removed")
        clean = _HIDDEN_HTML.sub("", clean)
    zw = sum(1 for ch in clean if ord(ch) in tu.ZERO_WIDTH)
    if zw:
        hidden.append({"text": f"{zw} zero-width character(s)", "reason": "zero-width characters", "page": None})
        res.stripped.append(f"{zw} zero-width character(s) removed")
    clean = tu.strip_invisible(clean)
    clean, res.lookalikes = fold_lookalikes(clean)
    if res.lookalikes:
        res.stripped.append(f"{len(res.lookalikes)} word(s) with look-alike letters folded to Latin")
    res.clean_text = clean
    res.hidden = hidden
    res.injections = scan_injection(text, [h["text"] for h in hidden])
    return res


# ---------------------------------------------------------------- pdf
def _text_image_layers(page) -> tuple[list, list]:
    """(covered, on_image): text boxes a LATER image is drawn over (hidden from the reader), and text boxes
    drawn ON TOP of an earlier image (its real background is the picture, so the page-colour test does not apply)."""
    import pymupdf
    try:
        log = page.get_bboxlog()
    except Exception:
        return [], []
    covered, on_image = [], []
    for i, (cmd, rect) in enumerate(log):
        if cmd != "fill-text":
            continue
        tr = pymupdf.Rect(rect)
        area = abs(tr.width * tr.height)
        if area <= 0:
            continue

        def share(r2):
            inter = tr & pymupdf.Rect(r2)
            return 0 if inter.is_empty else abs(inter.width * inter.height) / area
        if any(c2 == "fill-image" and share(r2) >= 0.9 for c2, r2 in log[i + 1:]):
            covered.append(tr)
        elif any(c2 == "fill-image" and share(r2) >= 0.5 for c2, r2 in log[:i]):
            on_image.append(tr)
    return covered, on_image


def _is_covered(bbox, covered) -> bool:
    area = abs(bbox.width * bbox.height)
    if area <= 0:
        return False
    for c in covered:
        inter = bbox & c
        if not inter.is_empty and abs(inter.width * inter.height) / area >= 0.8:
            return True
    return False


_ANNOT_HIDDEN = 2 | 32   # PDF flags: Hidden, NoView
_META_KEYS = ("title", "author", "subject", "keywords", "creator")


def analyze_pdf(data: bytes) -> TrustResult:
    import pymupdf
    res = TrustResult(kind="pdf")
    doc = pymupdf.open(stream=data, filetype="pdf")
    raw_lines, clean_lines = [], []
    visible_spans, fills = [], Counter()
    hidden = []
    image_count = 0
    extra_raw: list[str] = []
    annot_notes = 0
    for key in _META_KEYS:  # document properties are read by many text extractors but never shown to a reader
        val = (doc.metadata or {}).get(key) or ""
        if val and (scan_injection(val) or len(val) > 200):
            hidden.append({"text": val[:300], "reason": f"PDF metadata ({key})", "page": None})
            extra_raw.append(val)
    for pno, page in enumerate(doc, start=1):
        image_count += len(page.get_images(full=True))
        prect = page.rect
        rects = [(d["rect"], d["fill"]) for d in page.get_drawings() if d.get("fill") is not None]
        for r, f in rects:
            area = abs(r.width * r.height)
            if area > 400 and not (r.width >= prect.width * 0.98 and r.height >= prect.height * 0.98 and f == (1.0, 1.0, 1.0)):
                fills[tu.rgb_to_hex([c * 255 for c in f[:3]])] += int(area)
        covered, on_image = _text_image_layers(page)
        # annotations: only hidden, off-page or instruction-bearing ones count as concealed content
        n_notes = 0
        for an in (page.annots() or []):
            note = (an.info.get("content") or "").strip()
            if not note:
                continue
            kind_name = an.type[1]
            conceal = bool(an.flags & _ANNOT_HIDDEN) or not an.rect.intersects(prect) or bool(scan_injection(note))
            if conceal:
                hidden.append({"text": note[:300], "reason": f"PDF annotation ({kind_name}) not shown on the page", "page": pno})
                extra_raw.append(note)
            else:
                n_notes += 1
        annot_notes += n_notes
        last_y, raw_buf, clean_buf = None, "", ""
        for sp in page.get_texttrace():
            text = "".join(chr(c[0]) for c in sp["chars"]).strip("\x00")
            if not text.strip():
                continue
            bbox = pymupdf.Rect(sp["bbox"])
            fg = tuple(int(round(c * 255)) for c in sp["color"][:3]) if isinstance(sp["color"], (tuple, list)) else (0, 0, 0)
            cx, cy = (bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2
            bg = (255, 255, 255)
            for r, f in rects:
                if r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1:
                    bg = tuple(int(round(c * 255)) for c in f[:3])
            reason = None
            ratio = tu.contrast_ratio(fg, bg)
            if sp.get("type") == 3:
                reason = "invisible text render mode"
            elif sp.get("opacity", 1.0) < 0.05:
                reason = "fully transparent text"
            elif sp["size"] < 3:
                reason = f"tiny font ({sp['size']:.1f} pt)"
            elif not bbox.intersects(prect):
                reason = "positioned off the page"
            elif ratio < 1.25 and not _is_covered(bbox, on_image):
                reason = "same colour as its background"
            elif _is_covered(bbox, covered):
                reason = "covered by an image"
            newline = last_y is not None and abs(cy - last_y) > sp["size"] * 0.6
            last_y = cy
            sep = "\n" if newline else (" " if raw_buf else "")
            raw_buf += sep + text
            if reason:
                hidden.append({"text": text, "reason": reason, "page": pno})
            else:
                ftext, lk = fold_lookalikes(text)
                res.lookalikes.extend(lk)
                clean_buf += sep + ftext
                visible_spans.append({"text": ftext, "size": sp["size"], "bold": bool(sp["flags"] & 16) if "flags" in sp else False,
                                      "fg": tu.rgb_to_hex(fg), "bg": tu.rgb_to_hex(bg), "ratio": round(ratio, 2), "page": pno})
        raw_lines.append(raw_buf)
        clean_lines.append(clean_buf)
    # text inside embedded pictures, read locally (nothing leaves the server)
    ocr_texts = []
    if image_count and ocr_available():
        seen = set()
        for page in doc:
            for im in page.get_images(full=True):
                xref = im[0]
                if xref in seen or len(seen) >= 4:
                    continue
                seen.add(xref)
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.width < 200 or pix.height < 60:
                        continue
                    if pix.n - pix.alpha >= 4:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    t = local_ocr(pix.tobytes("png"))
                except Exception:
                    continue
                if t:
                    ocr_texts.append(t)
    res.raw_text = "\n\n".join(raw_lines + extra_raw + ocr_texts).strip()
    res.clean_text = "\n\n".join(clean_lines + ocr_texts).strip()
    if ocr_texts:
        res.features["ocr"] = "local"
    res.hidden = hidden
    if hidden:
        res.stripped.append(f"{len(hidden)} hidden text span(s) removed before review")
    res.injections = scan_injection(res.raw_text, [h["text"] for h in hidden])
    colors = Counter()
    for s in visible_spans:
        colors[s["fg"]] += len(s["text"])
    res.features = {"spans": visible_spans, "text_colors": dict(colors), "fill_colors": dict(fills),
                    "page_count": len(doc)}
    res.features["image_count"] = image_count
    res.features["annotation_notes"] = annot_notes
    res.features["embedded_files"] = doc.embfile_count()
    if ocr_texts:
        res.features["ocr"] = "local"
        res.notes.append(f"{len(ocr_texts)} embedded image(s) read with local OCR; very small or low-contrast text may be missed")
    elif image_count:
        res.notes.append(f"{image_count} embedded image(s): text inside images and background images are not analysed")
    if res.features["embedded_files"]:
        res.notes.append(f"{res.features['embedded_files']} embedded file attachment(s) are not analysed")
    if res.lookalikes:
        res.stripped.append(f"{len(res.lookalikes)} word(s) with look-alike letters folded to Latin")
    return res


# ---------------------------------------------------------------- image
def analyze_image(data: bytes, ocr_text: str = "") -> TrustResult:
    from PIL import Image
    ocr_kind = "llm" if ocr_text else ""
    if not ocr_text:
        ocr_text, ocr_kind = local_ocr(data), "local"
        if not ocr_text:
            ocr_kind = ""
    ocr_text, lk = fold_lookalikes(ocr_text)
    res = TrustResult(kind="image", raw_text=ocr_text, clean_text=ocr_text, lookalikes=lk)
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    small = im.copy()
    small.thumbnail((160, 160))
    from collections import Counter as C
    exact = C(small.getdata())
    total = sum(exact.values())
    dominant = []
    for rgb, n in exact.most_common(12):
        if n / total >= 0.06:  # flat design colours show up exactly
            dominant.append({"hex": tu.rgb_to_hex(rgb), "share": round(n / total, 3)})
    if sum(d["share"] for d in dominant) < 0.5:  # photo-like image: fall back to quantised colours
        q = small.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[: 6 * 3]
        total = sum(c for c, _ in q.getcolors())
        dominant = [{"hex": tu.rgb_to_hex(tuple(pal[i * 3: i * 3 + 3])), "share": round(c / total, 3)}
                    for c, i in sorted(q.getcolors(), reverse=True)]
    res.features = {"width": w, "height": h, "dominant": dominant, "image_count": 1, "ocr": ocr_kind}
    if not ocr_text:
        res.notes.append("text inside the image was not read (no vision model and no local OCR available)")
    elif ocr_kind == "local":
        res.notes.append("text inside the image was read with local OCR; very small or low-contrast text may be missed")
    res.injections = scan_injection(ocr_text)
    if ocr_kind == "local":
        known = {i["phrase"].lower() for i in res.injections}
        for inj in scan_injection(local_ocr_faint(data)):
            if inj["phrase"].lower() not in known:   # readable only after boosting the contrast: someone made it faint on purpose
                known.add(inj["phrase"].lower())
                res.hidden.append({"text": inj["snippet"], "reason": "faint text in the image (very low contrast)", "page": 1})
                res.injections.append({**inj, "hidden": True})
    return res


def analyze(kind: str, data: bytes | None, text: str = "", ocr_text: str = "") -> TrustResult:
    if kind == "pdf":
        return analyze_pdf(data or b"")
    if kind == "image":
        return analyze_image(data or b"", ocr_text)
    return analyze_plain_text(text)


# ---------------------------------------------------------------- redaction
REDACT_ORDER = ["email", "card", "aadhaar", "pan", "phone"]


def redact(text: str) -> tuple[str, dict, int]:
    """Replace personal data by tokens. Returns (text, mapping, count)."""
    mapping, count = {}, 0
    for kind in REDACT_ORDER:
        rx = PII_PATTERNS[kind]

        def sub(m, kind=kind):
            nonlocal count
            count += 1
            tok = f"[{kind.upper()}_{count}]"
            mapping[tok] = m.group(0)
            return tok
        text = rx.sub(sub, text)
    return text, mapping, count
