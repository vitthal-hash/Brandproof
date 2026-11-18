"""Trust Layer: parse files, find hidden text, scan for prompt injection, redact sensitive data.

Nothing leaves this module toward an LLM without going through redact()."""
import io
import re
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
]
INJECTION_RX = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


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

    def public(self) -> dict:
        return {"kind": self.kind, "hidden": self.hidden, "injections": self.injections,
                "stripped": self.stripped, "notes": self.notes,
                "has_hidden": bool(self.hidden), "differs": self.raw_text.strip() != self.clean_text.strip()}


def scan_injection(text: str, hidden_texts: list[str] | None = None) -> list[dict]:
    found = []
    hidden_texts = hidden_texts or []
    for rx in INJECTION_RX:
        for m in rx.finditer(text):
            snippet = text[max(0, m.start() - 20): m.end() + 20].replace("\n", " ")
            is_hidden = any(m.group(0).lower() in h.lower() for h in hidden_texts)
            found.append({"phrase": m.group(0), "hidden": is_hidden, "snippet": snippet})
    seen, out = set(), []
    for f in found:
        k = f["phrase"].lower()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


# ---------------------------------------------------------------- text
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
    zw = sum(1 for ch in clean if ord(ch) in tu.ZERO_WIDTH)
    if zw:
        hidden.append({"text": f"{zw} zero-width character(s)", "reason": "zero-width characters", "page": None})
        res.stripped.append(f"{zw} zero-width character(s) removed")
    clean = tu.strip_invisible(clean)
    res.clean_text = clean
    res.hidden = hidden
    res.injections = scan_injection(text, [h["text"] for h in hidden])
    return res


# ---------------------------------------------------------------- pdf
def analyze_pdf(data: bytes) -> TrustResult:
    import pymupdf
    res = TrustResult(kind="pdf")
    doc = pymupdf.open(stream=data, filetype="pdf")
    raw_lines, clean_lines = [], []
    visible_spans, fills = [], Counter()
    hidden = []
    image_count = 0
    for pno, page in enumerate(doc, start=1):
        image_count += len(page.get_images(full=True))
        prect = page.rect
        rects = [(d["rect"], d["fill"]) for d in page.get_drawings() if d.get("fill") is not None]
        for r, f in rects:
            area = abs(r.width * r.height)
            if area > 400 and not (r.width >= prect.width * 0.98 and r.height >= prect.height * 0.98 and f == (1.0, 1.0, 1.0)):
                fills[tu.rgb_to_hex([c * 255 for c in f[:3]])] += int(area)
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
            elif ratio < 1.25:
                reason = "same colour as its background"
            newline = last_y is not None and abs(cy - last_y) > sp["size"] * 0.6
            last_y = cy
            sep = "\n" if newline else (" " if raw_buf else "")
            raw_buf += sep + text
            if reason:
                hidden.append({"text": text, "reason": reason, "page": pno})
            else:
                clean_buf += sep + text
                visible_spans.append({"text": text, "size": sp["size"], "bold": bool(sp["flags"] & 16) if "flags" in sp else False,
                                      "fg": tu.rgb_to_hex(fg), "bg": tu.rgb_to_hex(bg), "ratio": round(ratio, 2), "page": pno})
        raw_lines.append(raw_buf)
        clean_lines.append(clean_buf)
    res.raw_text = "\n\n".join(raw_lines).strip()
    res.clean_text = "\n\n".join(clean_lines).strip()
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
    if image_count:
        res.notes.append(f"{image_count} embedded image(s): text inside images and background images are not analysed")
    return res


# ---------------------------------------------------------------- image
def analyze_image(data: bytes, ocr_text: str = "") -> TrustResult:
    from PIL import Image
    res = TrustResult(kind="image", raw_text=ocr_text, clean_text=ocr_text)
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
    res.features = {"width": w, "height": h, "dominant": dominant, "image_count": 1}
    if not ocr_text:
        res.notes.append("text inside the image was not read (no vision model configured)")
    res.injections = scan_injection(ocr_text)
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
