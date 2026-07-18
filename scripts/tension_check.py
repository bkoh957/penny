"""Dramatic-wiring checker (deterministic; plot-book workshop spec §6).

Named checks over the wired outline format — causality graph, open-question
ledger, hook chain, chapter coverage (this task), plus curve/beat checks
against the genre beat sheet (Tasks 5–6). No LLM judgment: every check is
arithmetic over the wiring. An outline without wiring is SKIPPED (wired:
False, exit 0) — book 1 stays valid.

`overloaded-chapter` is the one check that reads REQUIRED BEATS rather than
wiring, so it is deliberately outside that skip: the beats live in the
packet-format chapter block (`### Required Beats`), which need carry no
wiring at all. A chapter with no Required Beats gives it nothing to do, and
an outline with none anywhere (the pre-packet/legacy scene shape) is skipped
exactly as before.

Two result channels, and nothing is ever silent:
  blocking — findings. They stop the lock unless waived, and the waiver's
             reason is recorded in the certificate.
  notes    — a check that COULD NOT RUN, and why (the genre beat sheet
             declares no obligations.max_per_chapter, or the whodunit ledger
             cannot be read). Never a traceback out of a working command,
             never a silent `return`: preflight prints them and stamps them
             on the lock as `skipped: <check-id> — <why>`, so the certificate
             cannot claim coverage it does not have.

Checks (ids are the waiver handles):
  orphan-chapter    a chapter's Because is missing, names a nonexistent
                     chapter, or points forward/self
  dropped-question  a question is opened and never closed or carried
  phantom-answer    a chapter closes/carries a question no earlier chapter opened
  broken-hook       a chapter's hook names an already-closed or unknown question
  chapter-coverage  the chapter numbers present are not exactly contiguous
                     1..total_chapters (gaps, dupes, or extras) — the seam
                     failure mode of the chapters stage's per-gap dispatches
  dead-stretch      open-question count drops below the beat sheet's
                     min_open_before_reveal before the reveal chapter
  starved-thread    a genre-declared track (from the beat sheet's
                     tracks.max_dark_gap keys) is dark — including chapters
                     with no Track Movement row for it at all — for more than
                     its max_dark_gap
  off-mark-beat     a turning point's beat sits outside the beat sheet's
                     position window (or, for the reveal beat, off the
                     whodunit ledger's reveal_chapter)
  overloaded-chapter a chapter's obligation load — required beats + clues
                     planted + questions opened/closed + tracks advanced —
                     exceeds the genre beat sheet's obligations.max_per_chapter.
                     A PLOT property (too many stops for the length), caught
                     before a word is drafted (spec §6). Runs on any outline
                     carrying Required Beats anywhere; an outline with none
                     (the legacy scenes/weights shape) is never checked.

  python3 scripts/tension_check.py input/book-NN/outline-skeleton.md \
      [--beat-sheet P] [--turning-points P] [--whodunit P]
"""
from __future__ import annotations

import argparse
import math
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
            # FINAL REVIEW FINDING 4: a chapter with no Track Movement row at
            # all for this track must count as DARK, not as advancing. Only
            # the weave pass is required to emit Track Movement rows (the fill
            # pass isn't), so a weave pass that quietly drops a track across
            # half the book must not read as zero findings — the exact
            # failure mode this deterministic check exists to catch.
            dark = val is None or (isinstance(val, str) and val.strip().lower().startswith("none"))
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


def _beat_window(beat: dict, total: int):
    if "by_fraction" in beat:
        return 1, math.ceil(float(beat["by_fraction"]) * total)
    if "at_fraction" in beat:
        f, tol = float(beat["at_fraction"]), float(beat.get("tolerance", 0.05))
        return max(1, math.floor((f - tol) * total)), math.ceil((f + tol) * total)
    if "window" in beat:
        a, b = beat["window"]
        return max(1, math.floor(float(a) * total)), math.ceil(float(b) * total)
    return None


def _beat_checks(points, beat_sheet, total, reveal_ch, blocking):
    defs = {b["id"]: b for b in (beat_sheet.get("beats") or []) if isinstance(b, dict) and "id" in b}
    for p in points:
        bid, ch = p.get("beat"), p.get("chapter")
        if not bid or ch is None:
            continue
        beat = defs.get(bid)
        if beat is None:
            blocking.append(f"off-mark-beat: turning point tags unknown beat id {bid!r}")
        elif beat.get("from") == "whodunit":
            if reveal_ch is not None and ch != reveal_ch:
                blocking.append(
                    f"off-mark-beat: {bid} at ch {ch:02d} but whodunit reveal_chapter is {reveal_ch}")
        else:
            w = _beat_window(beat, total)
            if w and not (w[0] <= ch <= w[1]):
                blocking.append(
                    f"off-mark-beat: {bid} at ch {ch:02d} outside window ch {w[0]:02d}–{w[1]:02d}")


def _clues_by_chapter(whodunit_path, notes):
    """{chapter number: [clue ids]} from the locked ledger — the clues this
    chapter must PLANT, one term of its obligation load. A ledger the
    engine cannot read is a named note, never a traceback out of a checker."""
    if whodunit_path is None or not Path(whodunit_path).is_file():
        return {}
    from scripts.penny_whodunit import clues_by_chapter
    try:
        return clues_by_chapter(whodunit_path)
    except ValueError as e:
        notes.append(
            f"overloaded-chapter — the obligation half of the check could not run: {e}")
        return {}


def _obligation_load(ch, clue_map) -> tuple[int, str]:
    """What the chapter's word band must pay for: required beats + clues planted,
    questions opened and closed, tracks advanced (spec §6 names all of these). A
    pure count of declared fields — no prose read, no LLM judgment."""
    beats = ch["required_beats"]
    clues = clue_map.get(ch["num"], [])
    tracks = [t for t, v in ch["tracks"].items()
              if v and not v.strip().lower().startswith("none")]
    count = len(beats) + len(clues) + len(ch["opens"]) + len(ch["closes"]) + len(tracks)
    parts = (f"{len(beats)} required beat(s), {len(clues)} clue(s) to plant, "
             f"{len(ch['opens'])} question(s) opened, {len(ch['closes'])} closed, "
             f"{len(tracks)} track(s) advanced")
    return count, parts


def _overload_check(chapters, blocking, notes, *, cap=None, clue_map=None):
    """A chapter doing too much IN CONTENT — a plot property, visible before a word
    is drafted. Spec §6: the chapter's obligation load — required beats + clues
    planted + questions opened/closed + tracks advanced — exceeds the genre beat
    sheet's `obligations.max_per_chapter`. Most obligations are discharged inside
    the anchor in a sentence; past the cap they stop being sentences and start
    being stops.

    Never silently loses the signal — the anti-pattern this function has already
    been fixed for twice. An absent cap is a NAMED NOTE (the check could not run,
    and why), recorded on the lock certificate. Never a bare `return`.
    """
    clue_map = clue_map or {}
    if cap is None:
        notes.append(
            "overloaded-chapter — the obligation half of the check could not run: the "
            "genre's beat sheet declares no obligations.max_per_chapter")
    for ch in chapters:
        if cap is not None:
            load, parts = _obligation_load(ch, clue_map)
            if load > int(cap):
                blocking.append(
                    f"overloaded-chapter: ch {ch['num']} carries an obligation load of "
                    f"{load} ({parts}) against the genre's cap of {cap} — a chapter that "
                    f"opens, closes, plants and advances this much will run long no matter "
                    f"how well it is written")


def check_overload(chapters, *, beat_sheet_path=None, whodunit_path=None) -> dict:
    """The ninth check, standalone and WIRING-INDEPENDENT.

    Required Beats live in the packet-format chapter block
    (`### Required Beats`); an outline that carries none anywhere (the
    legacy scenes/weights shape) has nothing for this check to do.

    Returns {"applicable": bool, "blocking": [...], "notes": [...]}: findings
    block the lock (waivable, recorded); notes say the check could not run and
    why, and the lock certificate records them as `skipped:` lines. An outline
    with no Required Beats anywhere has no notes to give either — it is
    skipped entirely, exactly as an unweighted outline was before it.
    """
    if not any(ch["required_beats"] for ch in chapters):
        return {"applicable": False, "blocking": [], "notes": []}
    blocking: list[str] = []
    notes: list[str] = []
    cap = None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        sheet = _load_yaml(beat_sheet_path)
        obl = sheet.get("obligations")
        if isinstance(obl, dict) and obl.get("max_per_chapter") is not None:
            cap = int(obl["max_per_chapter"])
    _overload_check(chapters, blocking, notes,
                    cap=cap, clue_map=_clues_by_chapter(whodunit_path, notes))
    return {"applicable": True, "blocking": blocking, "notes": notes}


def check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None,
                  whodunit_path=None) -> dict:
    path = Path(outline_path)
    if not path.is_file():
        return {"wired": False, "blocking": [f"wiring-parse: outline not found: {path}"],
                "notes": [], "metrics": {}}
    text = path.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    # The overload check reads REQUIRED BEATS, not wiring, so it runs whether
    # or not this outline is wired. (An outline with no Required Beats gives
    # it nothing to do, so a legacy outline is untouched.)
    over = check_overload(chapters, beat_sheet_path=beat_sheet_path,
                          whodunit_path=whodunit_path)
    if not has_wiring(chapters):
        return {"wired": False, "blocking": over["blocking"], "notes": over["notes"],
                "metrics": {"chapters": len(chapters)}}
    blocking: list[str] = []
    qmaps = _graph_checks(chapters, blocking)
    fm = parse_frontmatter(text)
    total_raw = fm.get("total_chapters")
    total = int(total_raw) if isinstance(total_raw, str) and total_raw.strip().isdigit() else len(chapters)
    metrics = {"chapters": len(chapters), "total_chapters": total,
               "questions": sorted(qmaps["open_ch"])}
    # FINAL REVIEW FINDING 2: the chapters stage is N separate chapter-weaver
    # dispatches (one per turning-point gap) — gaps and duplicated boundary
    # chapters at the seams are THE failure mode of that design, and nothing
    # before this compared the chapter set to total_chapters (outline_check.py
    # does this for the shape-only door, but /plot-book's machine-written
    # skeleton only ever runs through tension_check.py). Model on
    # outline_check.py's outline-chapters-contiguous.
    nums = sorted(c["num"] for c in chapters)
    if nums != list(range(1, total + 1)):
        blocking.append(
            f"chapter-coverage: chapter headings {nums} are not a contiguous "
            f"1..{total} (gaps/dupes/extras)")
    reveal_ch = None
    if whodunit_path is not None and Path(whodunit_path).is_file():
        rc = _load_yaml(whodunit_path).get("reveal_chapter")
        reveal_ch = int(rc) if isinstance(rc, int) or (isinstance(rc, str) and rc.isdigit()) else None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        beat_sheet = _load_yaml(beat_sheet_path)
        metrics["open_counts"] = _curve_checks(chapters, beat_sheet, reveal_ch, blocking)
        if turning_points_path is not None and Path(turning_points_path).is_file():
            from scripts.penny_wiring import parse_turning_points
            tp = parse_turning_points(Path(turning_points_path).read_text(encoding="utf-8"))
            _beat_checks(tp["points"], beat_sheet, total, reveal_ch, blocking)
    blocking += over["blocking"]
    return {"wired": True, "blocking": blocking, "notes": over["notes"], "metrics": metrics}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny dramatic-wiring checker.")
    ap.add_argument("outline")
    ap.add_argument("--beat-sheet", dest="beat_sheet")
    ap.add_argument("--turning-points", dest="turning_points")
    ap.add_argument("--whodunit", dest="whodunit")
    args = ap.parse_args(argv)
    result = check_tension(args.outline, beat_sheet_path=args.beat_sheet,
                           turning_points_path=args.turning_points,
                           whodunit_path=args.whodunit)
    for line in result.get("notes", []):
        print(f"tension_check: note — {line}")
    if not result["wired"] and not result["blocking"]:
        print("tension_check: no wiring detected — skipped (book is un-wired; see spec §5)")
        return 0
    for line in result["blocking"]:
        print(f"tension_check: {line}")
    return 1 if result["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
