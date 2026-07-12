"""Parser for the WIRED outline format (plot-book workshop spec §5).

Chapters keep their existing fields; wiring lines are bold list-item fields in
the same style as the template's own:

  - **Because:** ch 06 — reason        (or, chapter 1 only: opening)
  - **Opens:** q-slug — phrasing       (repeatable, one question per line)
  - **Closes:** q-slug                 (repeatable)
  - **Carries:** q-slug                (repeatable; deliberately open past book end)
  - **Hook:** q-slug — prose           (id required only on wired outlines)

Dependency-free (penny_meta only — never PyYAML). This module is THE wired-field
parser, shared by tension_check.py and plot_stage.py: no forked conventions.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter  # noqa: F401  (re-exported for callers)

HEADING_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)(?:\s*[—-]\s*(.*))?$")
FIELD_RE = re.compile(r"^\s*-\s+\*\*(Because|Opens|Closes|Carries|Hook):\*\*\s*(.*)$")
QID_RE = re.compile(r"^q-[a-z0-9][a-z0-9-]*$")
TRACK_RE = re.compile(r"^\s*-\s+\*\*([A-Z]):\*\*\s*(.*)$")
TP_FIELD_RE = re.compile(r"^\s*-\s+\*\*(Beat|Chapter|Breaks):\*\*\s*(.*)$")
_BECAUSE_CH_RE = re.compile(r"^ch\s*(\d+)\b")


def split_id(value: str) -> tuple[str, str]:
    """'q-x — phrasing' -> ('q-x', 'phrasing'); 'q-x' -> ('q-x', '')."""
    parts = re.split(r"\s+[—-]\s+", value.strip(), maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def parse_wired_chapters(text: str) -> list[dict]:
    chapters: list[dict] = []
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        ch = {"num": int(cm.group(1)), "title": (cm.group(2) or "").strip(),
              "because": None, "because_ch": None, "opens": [], "closes": [],
              "carries": [], "hook_q": None, "hook_raw": None, "tracks": {},
              "errors": []}
        for line in text[start:end].splitlines():
            fm = FIELD_RE.match(line)
            if fm:
                field, value = fm.group(1), fm.group(2).strip()
                if field == "Because":
                    ch["because"] = value
                    bm = _BECAUSE_CH_RE.match(value)
                    if bm:
                        ch["because_ch"] = int(bm.group(1))
                elif field == "Hook":
                    ch["hook_raw"] = value
                    qid, _ = split_id(value)
                    if QID_RE.match(qid):
                        ch["hook_q"] = qid
                else:  # Opens / Closes / Carries
                    qid, phrasing = split_id(value)
                    if not QID_RE.match(qid):
                        ch["errors"].append(f"{field}: bad question id {qid!r}")
                    elif field == "Opens":
                        ch["opens"].append((qid, phrasing))
                    else:
                        ch[field.lower()].append(qid)
                continue
            tm = TRACK_RE.match(line)
            if tm:
                ch["tracks"][tm.group(1)] = tm.group(2).strip()
        chapters.append(ch)
    chapters.sort(key=lambda c: c["num"])
    return chapters


def has_wiring(chapters: list[dict]) -> bool:
    """Spec §5: an outline has wiring iff any chapter carries Because or Opens."""
    return any(c["because"] is not None or c["opens"] for c in chapters)
