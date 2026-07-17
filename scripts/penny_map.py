"""Parser for the prose map (spec 2026-07-18 §4) — the Pass-1 artifact that
replaced the brief. The machine parses ONLY: `## Scene N — Title`, `Target:`,
`Weight:`, `Beats covered:`, and `Clue:`. Every other field name (Desire /
Pressure / Action / Turn / ...) is open vocabulary for the drafter, used
selectively, and deliberately not parsed. Dependency-free (penny_meta only).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter
from scripts.penny_paths import input_path

MAP_SCENE_RE = re.compile(r"^##\s+Scene\s+(\d+)(?:\s*[—-]\s*(.*))?\s*$",
                          re.MULTILINE)
TARGET_RE = re.compile(r"^Target:\s*([\d,]+)\s*[–—-]\s*([\d,]+)\s*words?\s*$",
                       re.MULTILINE | re.IGNORECASE)
WEIGHT_LINE_RE = re.compile(r"^Weight:\s*(.+?)\s*$", re.MULTILINE)
BEATS_COVERED_RE = re.compile(r"^Beats covered:\s*([\d,\s]+?)\s*$",
                              re.MULTILINE | re.IGNORECASE)
# A `Clue:` field body runs until the next `Word:`-shaped field line, the next
# scene heading, or EOF — clue guidance is often multi-line, and (as here) can
# itself contain a trailing `[whodunit: ...]` tag line that must stay part of
# the clue body ("[" is not a field-name start, so it never terminates). The
# second lookahead alternative (`^\w[\w '’-]*:\s`) matters: it terminates
# before an INLINE field like `Result: The room laughs.`, not only before a
# bare `Turn:`-style label line.
CLUE_FIELD_RE = re.compile(
    r"^Clue:\s*\n?(.*?)(?=^\w[\w '’-]*:\s*$|^\w[\w '’-]*:\s|\Z|^##\s)",
    re.MULTILINE | re.DOTALL)


def map_path(book: str, chapter: str, repo_root=None) -> Path:
    return input_path(
        f"book-{str(book).zfill(2)}/maps/ch-{str(chapter).zfill(2)}.md",
        repo_root)


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def parse_map(text: str) -> dict:
    fm = parse_frontmatter(text)
    stamp = fm.get("built_from_packet")
    scenes: list[dict] = []
    marks = list(MAP_SCENE_RE.finditer(text))
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[start:end]
        tm = TARGET_RE.search(body)
        wm = WEIGHT_LINE_RE.search(body)
        bm = BEATS_COVERED_RE.search(body)
        cm = CLUE_FIELD_RE.search(body)
        clue = cm.group(1).strip() if cm and cm.group(1).strip() else None
        scenes.append({
            "num": int(m.group(1)),
            "title": (m.group(2) or "").strip(),
            "target": (_int(tm.group(1)), _int(tm.group(2))) if tm else None,
            "weight": wm.group(1) if wm else None,
            "beats_covered": [int(x) for x in bm.group(1).replace(",", " ").split()]
                             if bm else [],
            "clue_text": clue,
        })
    return {"stamp": stamp if isinstance(stamp, str) else None, "scenes": scenes}
