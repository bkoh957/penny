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

import re
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


_STRAND_SECTIONS = ("Chapter Summary", "Required Beats")


def name_tokens(slug: str) -> list[str]:
    """'tara-marion' -> ['tara', 'marion']. A ledger slug is an id; the outline
    prose uses the plain names inside it, either of which identifies them."""
    return [t for t in slug.lower().split("-") if t]


def strand(text: str, slug: str) -> list[tuple[int, str]]:
    """(chapter_number, line) for every summary/beat line naming this character,
    in story order — their line through the whole book on one page.

    WHOLE-WORD matching is load-bearing: a substring match puts 'Simone' on
    Simon's page, which invents a hole rather than finding one.
    """
    tokens = name_tokens(slug)
    if not tokens:
        raise ValueError(f"strand: slug {slug!r} yields no name tokens")
    pat = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in tokens) + r")\b",
                     re.IGNORECASE)
    hits: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for num, _title, block in iter_chapters(text):
        sections = parse_packet_sections(block)
        for name in _STRAND_SECTIONS:
            for raw in sections.get(name, "").splitlines():
                line = raw.strip().lstrip("-").strip()
                if line and pat.search(line) and (num, line) not in seen:
                    seen.add((num, line))
                    hits.append((num, line))
    return hits


def render_strand(slug: str, hits: list[tuple[int, str]]) -> str:
    out = [f"# Strand — {slug}", ""]
    if not hits:
        out.append("*(this character is never named in a summary or beat)*")
        return "\n".join(out) + "\n"
    for num, line in hits:
        out.append(f"- **ch {num:02d}** — {line}")
    return "\n".join(out) + "\n"


def roster(book: str, root=None) -> list[str]:
    """Character slugs from the whodunit ledger: every alibi_grid suspect, plus
    the victim. PyYAML is correct here — the ledger is nested human-edited data.
    Returns [] when there is no readable ledger; the caller then needs --who."""
    import yaml

    from scripts import penny_paths
    path = penny_paths.series_path(f"series/whodunit/book-{book}.yaml", root=root)
    if not Path(path).is_file():
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    names: list[str] = []
    for entry in data.get("alibi_grid") or []:
        if isinstance(entry, dict) and entry.get("suspect"):
            names.append(str(entry["suspect"]))
    victim = data.get("victim")
    if victim and str(victim) not in names:
        names.append(str(victim))
    return names
