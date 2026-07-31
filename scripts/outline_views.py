"""Deterministic, read-only views over a book's outline (spec 2026-07-31 §3.2).

`outline.md` is a MACHINE INPUT: packet_assemble.py slices one chapter out of it
and each block must stand alone, so roughly a third of the file is repeated
furniture. The showrunner was never its audience. This module renders what they
should read instead, and NEVER writes to the source.

Three views, none of which makes an LLM judgement:
  glance   — every chapter's title + summary, in order
  strands  — one character's line through the whole book
  spine    — the active genre's structural-job worksheet
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import strip_frontmatter
from scripts.penny_wiring import CHAPTER_RE, HEADING_RE, parse_packet_sections


def iter_chapters(text: str) -> Iterator[tuple[int, str, str]]:
    """(number, title, block) for each `## Chapter NN — Title`, in file order."""
    body = strip_frontmatter(text)
    marks = list(HEADING_RE.finditer(body))
    for i, m in enumerate(marks):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        yield int(cm.group(1)), (cm.group(2) or "").strip(), body[start:end].strip()


def glance(text: str) -> str:
    """The whole story in order: title + summary per chapter, nothing else."""
    out = ["# The story at a glance", ""]
    for num, title, block in iter_chapters(text):
        summary = parse_packet_sections(block).get("Chapter Summary", "").strip()
        out.append(f"## {num:02d} — {title}" if title else f"## {num:02d}")
        out.append("")
        out.append(summary or "*(no summary)*")
        out.append("")
    return "\n".join(out)
