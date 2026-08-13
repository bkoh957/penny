#!/usr/bin/env python3
"""Cut input/series/background-history.md into derived continuity entries and
the setting pack (spec 2026-08-13).

Pure functions take text and return findings; all IO lives in main(). The cut
never writes canon-core.md, continuity/characters/, or any whodunit ledger —
those have their own owners (spec §6).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import penny_meta, penny_paths  # noqa: E402

PART_HEADINGS = ("Stance", "Town", "Characters", "Relationships", "Secrets")
KIND_BY_PART = {
    "Town": "town",
    "Characters": "character",
    "Relationships": "relationship",
    "Secrets": "secret",
}

_EM_DASH = "—"
_HEADING_RE = re.compile(r"^(?P<hashes>#{2,})\s+(?P<title>.+?)\s*$")
_AND_RE = re.compile(r"\s+and\s+", re.IGNORECASE)


def slug(title: str) -> str:
    """Truncate at the first em dash, then lowercase with non-alphanumerics
    collapsed to single hyphens."""
    head = title.split(_EM_DASH, 1)[0]
    out = re.sub(r"[^a-z0-9]+", "-", head.strip().lower())
    return out.strip("-")


def relationship_slug(title: str) -> "str | None":
    """`Maggie and Cal` -> `cal--maggie`. None when there is no ` and `."""
    parts = _AND_RE.split(title.split(_EM_DASH, 1)[0].strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    left, right = slug(parts[0]), slug(parts[1])
    if not left or not right:
        return None
    return "--".join(sorted((left, right)))


def parse_background(text: str) -> dict:
    """Split the source on its heading contract (spec §3)."""
    stance_lines: list[str] = []
    entries: list[dict] = []
    unknown_parts: list[str] = []
    deep_headings: list[str] = []

    part: "str | None" = None
    current: "dict | None" = None
    buf: list[str] = []

    def flush():
        nonlocal current, buf
        if current is not None:
            current["body"] = "\n".join(buf).strip()
            entries.append(current)
        current, buf = None, []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if not m:
            if current is not None:
                buf.append(line)
            elif part == "Stance":
                stance_lines.append(line)
            continue

        level, title = len(m.group("hashes")), m.group("title")
        if level == 2:
            flush()
            part = title if title in PART_HEADINGS else None
            if title not in PART_HEADINGS:
                unknown_parts.append(title)
            continue
        if level >= 4:
            deep_headings.append(title)
            continue
        # level == 3
        flush()
        if part is None or part == "Stance":
            continue
        kind = KIND_BY_PART[part]
        s = relationship_slug(title) if kind == "relationship" else slug(title)
        current = {"part": part, "kind": kind, "title": title, "slug": s}

    flush()
    return {
        "stance": "\n".join(stance_lines).strip(),
        "entries": entries,
        "unknown_parts": unknown_parts,
        "deep_headings": deep_headings,
    }
