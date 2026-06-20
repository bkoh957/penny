"""Shared prose text primitives for Penny's voice-related checkers.

The quote layer is split deliberately: this module exposes WHERE the quotes are
(`quote_spans`, added in a later task) and the segmentation helpers that operate
over prose. Each caller applies its own policy on top — voice_drift only avoids
splitting a sentence mid-quote; lexicon_check removes dialogue entirely. Putting a
strip policy in here would force it on every caller, so it stays out.
"""
from __future__ import annotations

import re

_ABBREV = {"mr", "mrs", "ms", "dr", "st", "mt", "rev", "prof", "sr", "jr"}


def strip_frontmatter(text: str) -> str:
    """Remove a leading ---...--- block only; keep all prose. No crash if absent."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return text


def _is_prose_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):                       # markdown heading
        return False
    if re.fullmatch(r"[-*]{3,}|(\* )+\*?", s):   # rule / scene-break (---, ***, * * *)
        return False
    return True


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def segment_sentences(text: str) -> list[str]:
    """Heuristic, dependency-free sentence splitter. Known failure modes: it is a
    heuristic over messy prose; abbreviations outside _ABBREV, nested quotes, and
    decimal numbers can mis-split. Counts are signal, not gospel."""
    prose = " ".join(l.strip() for l in strip_frontmatter(text).splitlines() if _is_prose_line(l))
    sentences: list[str] = []
    buf = ""
    i = 0
    quote_depth = 0
    while i < len(prose):
        ch = prose[i]
        buf += ch
        if ch in '"“”"':
            quote_depth = 0 if quote_depth else 1
        if ch == "." and prose[i:i + 3] == "...":
            buf += ".."
            i += 3
            continue
        if ch in ".!?":
            if quote_depth:
                i += 1
                continue
            m = re.search(r"(\w+)\.$", buf)
            if ch == "." and m and m.group(1).lower() in _ABBREV:
                i += 1
                continue
            rest = prose[i + 1:].lstrip()
            if rest == "" or rest[0].isupper() or rest[0] in '"""':
                sentences.append(buf.strip())
                buf = ""
        i += 1
    if buf.strip():
        sentences.append(buf.strip())
    return [s for s in sentences if s]
