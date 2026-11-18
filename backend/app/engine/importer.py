"""Guideline import (F1): turn a guideline document into DRAFT rules that a human approves."""
import io
import re

DIRECTIVE = re.compile(r"\b(must not|must|never|always|do not|don't|avoid|should not|should|shall|required|prohibited|only)\b", re.I)
NEGATIVE = re.compile(r"\b(never|do not|don't|avoid|must not|should not|prohibited)\b", re.I)
HIGH = re.compile(r"\b(never|must not|prohibited|illegal|forbidden)\b", re.I)
MEDIUM = re.compile(r"\b(must|always|required|do not|don't|shall)\b", re.I)
CATS = [("accessibility", r"contrast|alt text|accessib|screen reader|reading level"), ("visual", r"colou?r|logo|font|palette|imagery|layout"),
        ("claims", r"claim|fact|guarantee|substantiat|evidence|statistic"), ("tone", r"tone|voice|friendly|formal|aggressive|pressure"),
        ("disclosure", r"disclos|label|disclaimer|t&c|terms"), ("terminology", r"term|word|say |spell|capitali|name")]


def extract_text(data: bytes | None, filename: str, text: str | None) -> str:
    if text:
        return text
    if data is None:
        return ""
    if filename.lower().endswith(".pdf"):
        import pymupdf
        doc = pymupdf.open(stream=data, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)
    return data.decode("utf-8", errors="ignore")


def candidates(text: str) -> list[dict]:
    out, n = [], 0
    for raw in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9•\-])", text):
        line = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s*", "", raw).strip()
        if not (15 <= len(line) <= 300) or not DIRECTIVE.search(line):
            continue
        n += 1
        sev = "high" if HIGH.search(line) else "medium" if MEDIUM.search(line) else "low"
        cat = next((c for c, rx in CATS if re.search(rx, line, re.I)), "messaging")
        quotes = [q for q in re.findall(r"[\"“‘'](.{3,40}?)[\"”’']", line) if len(q.split()) <= 5]
        if quotes and NEGATIVE.search(line):
            method, params = "phrase", {"phrases": [q.lower() for q in quotes], "replacements": {}, "message": line}
        else:
            method, params = "judgment", {}
        out.append({"rule_id": f"IMP-{n:03d}", "title": line[:120], "description": line, "category": cat,
                    "severity": sev, "method": method, "params": params})
    return out
