"""Dramatic-wiring checker (deterministic; plot-book workshop spec §6).

Named checks over the wired outline format — causality graph, open-question
ledger, hook chain (this task), plus curve/beat checks against the genre beat
sheet (Tasks 5–6). No LLM judgment: every check is arithmetic over the wiring.
An outline without wiring is SKIPPED (wired: False, exit 0) — book 1 stays valid.

  python3 scripts/tension_check.py input/book-NN/outline-skeleton.md \
      [--beat-sheet P] [--turning-points P] [--whodunit P]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter
from scripts.penny_wiring import has_wiring, parse_wired_chapters


def _load_yaml(path):
    import yaml  # PyYAML: beat sheet + whodunit are genuinely nested human data
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _graph_checks(chapters: list[dict], blocking: list[str]) -> dict:
    """Causality + question ledger + hook chain. Returns the question maps
    (open/closed/carried chapter indices) for the curve checks."""
    nums = {c["num"] for c in chapters}
    open_ch: dict[str, int] = {}
    for c in chapters:
        for qid, _ in c["opens"]:
            open_ch.setdefault(qid, c["num"])
    closed_ch: dict[str, int] = {}
    carried: set[str] = set()
    for c in chapters:
        for err in c["errors"]:
            blocking.append(f"wiring-parse: ch {c['num']:02d} — {err}")
        val = (c["because"] or "").strip()
        if not val:
            blocking.append(f"orphan-chapter: ch {c['num']:02d} has no Because line")
        elif val.lower() == "opening":
            if c["num"] != 1:
                blocking.append(
                    f"orphan-chapter: ch {c['num']:02d} claims 'opening' but is not chapter 1")
        elif c["because_ch"] is None:
            blocking.append(
                f"orphan-chapter: ch {c['num']:02d} Because names no chapter: {val!r}")
        elif c["because_ch"] not in nums:
            blocking.append(
                f"orphan-chapter: ch {c['num']:02d} Because names nonexistent ch {c['because_ch']:02d}")
        elif c["because_ch"] >= c["num"]:
            blocking.append(
                f"orphan-chapter: ch {c['num']:02d} Because points forward/self (ch {c['because_ch']:02d})")
        for qid in c["closes"] + c["carries"]:
            if open_ch.get(qid) is None or open_ch[qid] > c["num"]:
                blocking.append(
                    f"phantom-answer: ch {c['num']:02d} closes/carries {qid} which no earlier chapter opened")
            elif qid in c["carries"]:
                carried.add(qid)
            else:
                closed_ch.setdefault(qid, c["num"])
    for qid, oc in sorted(open_ch.items()):
        if qid not in closed_ch and qid not in carried:
            blocking.append(
                f"dropped-question: {qid} (opened ch {oc:02d}) is never closed or carried")
    for c in chapters:
        if c["hook_q"] is None:
            blocking.append(
                f"broken-hook: ch {c['num']:02d} Hook does not lead with a question id")
        elif open_ch.get(c["hook_q"]) is None or open_ch[c["hook_q"]] > c["num"]:
            blocking.append(
                f"broken-hook: ch {c['num']:02d} hook names unknown/not-yet-open question {c['hook_q']}")
        elif c["hook_q"] in closed_ch and closed_ch[c["hook_q"]] <= c["num"]:
            blocking.append(
                f"broken-hook: ch {c['num']:02d} hook names {c['hook_q']}, already closed by ch "
                f"{closed_ch[c['hook_q']]:02d}")
    return {"open_ch": open_ch, "closed_ch": closed_ch, "carried": carried}


def _curve_checks(chapters, beat_sheet, reveal_ch, blocking):
    min_open = int((beat_sheet.get("questions") or {}).get("min_open_before_reveal", 1))
    open_now: set[str] = set()
    counts: dict[int, int] = {}
    for c in chapters:
        open_now.update(q for q, _ in c["opens"])
        open_now.difference_update(c["closes"])  # carries stay open past book end
        counts[c["num"]] = len(open_now)
    last = reveal_ch if reveal_ch else max(counts, default=0)
    for n in sorted(counts):
        if n < last and counts[n] < min_open:
            blocking.append(
                f"dead-stretch: ch {n:02d} ends with {counts[n]} open question(s) "
                f"(< {min_open}) before the reveal (ch {last:02d})")
    for track, limit in sorted(((beat_sheet.get("tracks") or {}).get("max_dark_gap") or {}).items()):
        run, run_start = 0, None
        for c in chapters:
            val = c["tracks"].get(track)
            dark = isinstance(val, str) and val.strip().lower().startswith("none")
            if dark:
                run += 1
                run_start = run_start if run_start is not None else c["num"]
                if run == int(limit) + 1:
                    blocking.append(
                        f"starved-thread: track {track} dark for more than {limit} "
                        f"consecutive chapters (from ch {run_start:02d})")
            else:
                run, run_start = 0, None
    return counts


def check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None,
                  whodunit_path=None) -> dict:
    path = Path(outline_path)
    if not path.is_file():
        return {"wired": False,
                "blocking": [f"wiring-parse: outline not found: {path}"], "metrics": {}}
    text = path.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_wiring(chapters):
        return {"wired": False, "blocking": [], "metrics": {"chapters": len(chapters)}}
    blocking: list[str] = []
    qmaps = _graph_checks(chapters, blocking)
    fm = parse_frontmatter(text)
    total_raw = fm.get("total_chapters")
    total = int(total_raw) if isinstance(total_raw, str) and total_raw.strip().isdigit() else len(chapters)
    metrics = {"chapters": len(chapters), "total_chapters": total,
               "questions": sorted(qmaps["open_ch"])}
    reveal_ch = None
    if whodunit_path is not None and Path(whodunit_path).is_file():
        rc = _load_yaml(whodunit_path).get("reveal_chapter")
        reveal_ch = int(rc) if isinstance(rc, int) or (isinstance(rc, str) and rc.isdigit()) else None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        beat_sheet = _load_yaml(beat_sheet_path)
        metrics["open_counts"] = _curve_checks(chapters, beat_sheet, reveal_ch, blocking)
        # off-mark-beat (Task 6) hooks in here with the same beat_sheet/reveal_ch.
    return {"wired": True, "blocking": blocking, "metrics": metrics}
