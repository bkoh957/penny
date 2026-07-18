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

SCENE_RE = re.compile(r"^###\s+Scene\s+(\d+)(?:\s*[—-]\s*(.*))?$", re.MULTILINE)
# Any level-3 (or deeper level, but "###" is what the template uses) heading —
# used only to bound a scene's body; the last scene must stop before whatever
# trailing subsection follows it ("### Track Movement", "### Drafting Notes",
# "### Possible Line-Level Prompts", ...), not sweep it in as scene content.
ANY_H3_RE = re.compile(r"^###\s+.*$", re.MULTILINE)
BEAT_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
FIRSTLINE_RE = re.compile(r"^\s*-\s+\*\*First line:\*\*\s*(.*)$")
GRADE_RE = re.compile(r"^\[(cliffhanger|promise)\]\s*(.*)$", re.IGNORECASE)
TYPE_FLAG_RE = re.compile(r"\[type:\s*([a-z0-9-]+)\]", re.IGNORECASE)
LONG_FLAG_RE = re.compile(r"\[long:\s*([^\]]+)\]", re.IGNORECASE)

H3_HEADING_RE = re.compile(r"^###\s+(.*?)\s*$", re.MULTILINE)
BULLET_RE = re.compile(r"^\s*-\s+(.*\S)\s*$")


def chapter_block(text: str, num: int) -> str:
    """The raw `## Chapter NN` block — heading end to the next `##` or EOF."""
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = CHAPTER_RE.match(m.group(1))
        if cm and int(cm.group(1)) == num:
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[start:end].strip()
    return ""


def parse_packet_sections(block: str) -> dict[str, str]:
    """Packet-format `###` sections of one chapter block: heading -> body text.

    The packet-format block (spec 2026-07-18 §3) carries its authored content in
    named H3 sections (Chapter Purpose, Required Beats, Guardrails, ...). A
    `### Scene N` heading is NOT a packet section — scenes are the legacy format
    and parse_scenes owns them; both parsers reading one block must not fight.
    """
    sections: dict[str, str] = {}
    marks = [m for m in H3_HEADING_RE.finditer(block)
             if not SCENE_RE.match(m.group(0))]
    all_heads = sorted(m.start() for m in H3_HEADING_RE.finditer(block))
    for m in marks:
        start = m.end()
        end = len(block)
        for hs in all_heads:
            if hs > m.start():
                end = hs
                break
        sections[m.group(1)] = block[start:end].strip()
    return sections


def parse_required_beats(sections: dict[str, str]) -> list[str]:
    """The Required Beats list, in authored order. One line per beat — the
    1-based index into this list is the id a map's `Beats covered:` line uses,
    so ORDER IS CONTRACT: never sort, never dedupe."""
    body = sections.get("Required Beats", "")
    return [bm.group(1) for line in body.splitlines()
            if (bm := BULLET_RE.match(line))]


def split_id(value: str) -> tuple[str, str]:
    """'q-x — phrasing' -> ('q-x', 'phrasing'); 'q-x' -> ('q-x', '')."""
    parts = re.split(r"\s+[—-]\s+", value.strip(), maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def parse_scenes(block: str) -> list[dict]:
    """The `### Scene N` blocks of one chapter (the LEGACY outline shape), with
    their beat count and instruction mass. `weight` is always None — the
    scene-weight machinery is gone (packet/map redesign); the key survives only
    so legacy-block consumers need no shape change.

    `instruction_words` is the word count of the beat-flow text — the covert word
    budget the model actually obeys.
    """
    scenes: list[dict] = []
    marks = list(SCENE_RE.finditer(block))
    # Bound every scene at the next "###"-level heading of ANY name, not
    # merely the next "### Scene N" — otherwise the last scene's body runs to
    # the end of the whole chapter block and sweeps in trailing sections like
    # "### Drafting Notes", inflating beats/instruction_words with whatever
    # numbered list lives there.
    heading_starts = sorted(hm.start() for hm in ANY_H3_RE.finditer(block))
    for i, m in enumerate(marks):
        start = m.end()
        end = len(block)
        for hs in heading_starts:
            if hs >= start:
                end = hs
                break
        body = block[start:end]
        beats = [BEAT_RE.match(line) for line in body.splitlines()]
        beat_texts = [b.group(2) for b in beats if b]
        scenes.append({
            "num": int(m.group(1)),
            "title": (m.group(2) or "").strip(),
            "weight": None,
            "beats": len(beat_texts),
            "instruction_words": sum(len(t.split()) for t in beat_texts),
        })
    return scenes


def parse_wired_chapters(text: str) -> list[dict]:
    chapters: list[dict] = []
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        raw_title = (cm.group(2) or "").strip()
        tf = TYPE_FLAG_RE.search(raw_title)
        lf = LONG_FLAG_RE.search(raw_title)
        title = TYPE_FLAG_RE.sub("", raw_title)
        title = LONG_FLAG_RE.sub("", title).strip()
        ch = {"num": int(cm.group(1)), "title": title,
              "because": None, "because_ch": None, "opens": [], "closes": [],
              "carries": [], "hook_q": None, "hook_raw": None, "tracks": {},
              "scenes": parse_scenes(block), "first_line": None, "hook_grade": None,
              "sections": (sections := parse_packet_sections(block)),
              "required_beats": parse_required_beats(sections),
              "chapter_type": tf.group(1).lower() if tf else None,
              "long_waiver": lf.group(1).strip() if lf else None,
              "errors": []}
        for line in block.splitlines():
            flm = FIRSTLINE_RE.match(line)
            if flm:
                ch["first_line"] = flm.group(1).strip()
                continue
            fm = FIELD_RE.match(line)
            if fm:
                field, value = fm.group(1), fm.group(2).strip()
                if field == "Because":
                    ch["because"] = value
                    bm = _BECAUSE_CH_RE.match(value)
                    if bm:
                        ch["because_ch"] = int(bm.group(1))
                elif field == "Hook":
                    # The grade may lead the whole value (wired form:
                    # "[grade] q-id — text") or lead the phrasing (packet
                    # form: "q-id — [grade] text"). hook_raw must be clean
                    # of the bracket in BOTH positions — downstream consumers
                    # print it verbatim into drafter-facing prose.
                    gm = GRADE_RE.match(value)
                    if gm:
                        ch["hook_grade"] = gm.group(1).lower()
                        value = gm.group(2).strip()
                        qid, _ = split_id(value)
                    else:
                        qid, phrasing = split_id(value)
                        gm = GRADE_RE.match(phrasing)
                        if gm:
                            ch["hook_grade"] = gm.group(1).lower()
                            phrasing = gm.group(2).strip()
                            value = f"{qid} — {phrasing}" if phrasing else qid
                    ch["hook_raw"] = value
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


def parse_turning_points(text: str) -> dict:
    """Parse plot/turning-points.md: frontmatter total_chapters + one ## section
    per turning point carrying **Beat:** / **Chapter:** bold list fields."""
    fm = parse_frontmatter(text)
    total_raw = fm.get("total_chapters")
    total = int(total_raw) if isinstance(total_raw, str) and total_raw.strip().isdigit() else None
    points: list[dict] = []
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        point = {"title": m.group(1), "beat": None, "chapter": None}
        for line in text[start:end].splitlines():
            tm = TP_FIELD_RE.match(line)
            if not tm:
                continue
            field, value = tm.group(1), tm.group(2).strip()
            if field == "Beat":
                point["beat"] = value or None
            elif field == "Chapter" and value.isdigit():
                point["chapter"] = int(value)
        points.append(point)
    return {"total_chapters": total, "points": points}
