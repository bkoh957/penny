"""Dramatic-wiring checker (deterministic; plot-book workshop spec §6).

Named checks over the wired outline format — causality graph, open-question
ledger, hook chain, chapter coverage (this task), plus curve/beat checks
against the genre beat sheet (Tasks 5–6). No LLM judgment: every check is
arithmetic over the wiring. An outline without wiring is SKIPPED (wired:
False, exit 0) — book 1 stays valid.

`overloaded-chapter` is the one check that reads SCENE WEIGHTS rather than
wiring, so it is deliberately outside that skip: the weights live in the
expanded outline (`input/book-NN/outline.md`), which on the /plot-book path
is a different file from the wired skeleton the other eight checks read, and
which need carry no wiring at all. An UNWEIGHTED outline gives it nothing to
do and is skipped exactly as before.

Two result channels, and nothing is ever silent:
  blocking — findings. They stop the lock unless waived, and the waiver's
             reason is recorded in the certificate.
  notes    — a check that COULD NOT RUN, and why (no length profile, one the
             engine cannot parse, no min_<class>_words floor, no obligation
             cap). Never a traceback out of a working command, never a silent
             `return`: preflight prints them and stamps them on the lock as
             `skipped: <check-id> — <why>`, so the certificate cannot claim
             coverage it does not have.

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
  overloaded-chapter a chapter's SCENES plus its OBLIGATIONS exceed what its
                     word band can hold — a PLOT property (too many stops for
                     the length), caught before a word is drafted (spec §6).
                     Scenes: any scene the band cannot pay its class's
                     min_<class>_words floor (a starved SUPPORT scene counts
                     exactly as a starved connective one). Obligations: clues
                     planted + questions opened/closed + tracks advanced,
                     against the beat sheet's obligations.max_per_chapter.
                     Runs on any WEIGHTED outline, wired or not; an unweighted
                     outline (book 1's shape) is never checked. A chapter whose
                     weight table the profile can't resolve (a missing weight_*
                     key) still gets a finding naming why it couldn't be
                     budgeted — never a silent skip.
  undeclared-scene-weight  a chapter declares a weight for some scenes but not
                     others — brief_render.check_briefs' own vocabulary for
                     the same silent-default problem, raised here too so the
                     overload check never guesses "support" instead of asking.

  python3 scripts/tension_check.py input/book-NN/outline-skeleton.md \
      [--beat-sheet P] [--turning-points P] [--whodunit P] [--profile P]
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
    chapter must PLANT, which is half of its obligation load. A ledger the
    engine cannot read is a named note, never a traceback out of a checker."""
    if whodunit_path is None or not Path(whodunit_path).is_file():
        return {}
    from scripts.brief_render import clues_by_chapter
    try:
        return clues_by_chapter(whodunit_path)
    except ValueError as e:
        notes.append(
            f"overloaded-chapter — the obligation half of the check could not run: {e}")
        return {}


def _obligation_load(ch, clue_map) -> tuple[int, str]:
    """What the chapter's word band must pay for besides its scenes: clues planted,
    questions opened and closed, tracks advanced (spec §6 names all three). A pure
    count of declared fields — no prose read, no LLM judgment."""
    clues = clue_map.get(ch["num"], [])
    tracks = [t for t, v in ch["tracks"].items()
              if v and not v.strip().lower().startswith("none")]
    count = len(clues) + len(ch["opens"]) + len(ch["closes"]) + len(tracks)
    parts = (f"{len(clues)} clue(s) to plant, {len(ch['opens'])} question(s) opened, "
             f"{len(ch['closes'])} closed, {len(tracks)} track(s) advanced")
    return count, parts


def _overload_check(chapters, profile, blocking, notes, *, cap=None, clue_map=None):
    """A chapter doing too much IN CONTENT — a plot property, visible before a word
    is drafted. Spec §6: *scenes plus obligations* exceed what the chapter's word
    band can hold. Two halves, each with its own config:

      scenes      — any scene the band cannot pay its class's `min_<class>_words`
                    floor (length-profile.md). A starved SUPPORT scene counts
                    exactly as a starved connective one does: twelve supports at
                    153 words apiece is the same overload as twenty connectives
                    at 80.
      obligations — clues planted + questions opened/closed + tracks advanced,
                    against the genre beat sheet's `obligations.max_per_chapter`.
                    Most obligations are discharged inside the anchor in a
                    sentence; past the cap they stop being sentences and start
                    being stops.

    Never silently loses the signal — the anti-pattern this function has already
    been fixed for twice. A missing floor, an unparseable profile, or an absent cap
    is a NAMED NOTE (the check could not run, and why), recorded on the lock
    certificate; a chapter the profile cannot budget is a NAMED, waivable FINDING.
    Neither is ever a bare `return`.
    """
    from scripts import penny_length
    from scripts.penny_wiring import undeclared_scene_weight
    clue_map = clue_map or {}
    floors = (profile or {}).get("floors") or {}
    if profile is not None and not floors:
        notes.append(
            "overloaded-chapter — the scene half of the check could not run: the "
            "length profile declares no min_<class>_words floor (e.g. "
            "min_connective_words: 100), so no scene can be called starved")
    if cap is None:
        notes.append(
            "overloaded-chapter — the obligation half of the check could not run: the "
            "genre's beat sheet declares no obligations.max_per_chapter")
    for ch in chapters:
        scenes = ch["scenes"]
        weighted = [s for s in scenes if s["weight"]]
        if weighted and len(weighted) < len(scenes):
            blocking.append(
                undeclared_scene_weight(ch["num"], [s for s in scenes if not s["weight"]]))
        elif weighted and profile is not None and floors:
            band = penny_length.band_for(profile, ch["chapter_type"])
            try:
                budgets = penny_length.scene_budgets(
                    profile, band, [s["weight"] for s in scenes])
            except ValueError as e:
                blocking.append(
                    f"overloaded-chapter: ch {ch['num']} could not be budgeted — {e} — "
                    f"the overload check could not run for this chapter")
                budgets = []
            for s, b in zip(scenes, budgets):
                floor = floors.get(s["weight"])
                if floor and b < floor:
                    blocking.append(
                        f"overloaded-chapter: ch {ch['num']} has {len(scenes)} scenes; at band "
                        f"{band[0]}–{band[1]} {s['weight']} scene {s['num']} '{s['title']}' can "
                        f"only be paid {b} words against a {floor}-word floor — the chapter is "
                        f"doing too much to fit its length")
                    break
        if cap is not None:
            load, parts = _obligation_load(ch, clue_map)
            if load > int(cap):
                blocking.append(
                    f"overloaded-chapter: ch {ch['num']} carries an obligation load of "
                    f"{load} ({parts}) against the genre's cap of {cap} — a chapter that "
                    f"opens, closes, plants and advances this much will run long no matter "
                    f"how well it is written")


def check_overload(chapters, *, profile_path=None, beat_sheet_path=None,
                   whodunit_path=None) -> dict:
    """The ninth check, standalone and WIRING-INDEPENDENT.

    Weights live in the expanded outline (`input/book-NN/outline.md`), written by
    /expand-outline and weighed by /build-briefs; the wiring lives in the skeleton
    the workshop writes. Those are two different files on the /plot-book path, and
    the expanded one need carry no wiring at all — so an overload check that hid
    behind `has_wiring` could never fire on the only artifact that has scenes in it.

    Returns {"weighted": bool, "blocking": [...], "notes": [...]}: findings block the
    lock (waivable, recorded); notes say the check could not run and why, and the
    lock certificate records them as `skipped:` lines. An UNWEIGHTED outline (book 1's
    shape) has no scenes to price and no notes to give — it is skipped entirely,
    exactly as before.
    """
    from scripts.penny_wiring import has_weights
    if not has_weights(chapters):
        return {"weighted": False, "blocking": [], "notes": []}
    blocking: list[str] = []
    notes: list[str] = []
    profile = None
    if profile_path is None or not Path(profile_path).is_file():
        notes.append(
            "overloaded-chapter — the scene half of the check could not run: this "
            "series has no config/length-profile.md, so a chapter's word band is unknown")
    else:
        from scripts import penny_length
        try:
            profile = penny_length.parse_profile(
                Path(profile_path).read_text(encoding="utf-8"))
        except ValueError as e:
            # C1: the live series' profile predates the band/weight schema. An
            # unusable profile means the scene half of the check cannot run —
            # it must NOT mean an uncaught ValueError out of `lock-mystery`,
            # which is a working command taking a traceback for a config file
            # it never used to read.
            notes.append(
                f"overloaded-chapter — the scene half of the check could not run: {e}")
    cap = None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        sheet = _load_yaml(beat_sheet_path)
        obl = sheet.get("obligations")
        if isinstance(obl, dict) and obl.get("max_per_chapter") is not None:
            cap = int(obl["max_per_chapter"])
    _overload_check(chapters, profile, blocking, notes,
                    cap=cap, clue_map=_clues_by_chapter(whodunit_path, notes))
    return {"weighted": True, "blocking": blocking, "notes": notes}


def check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None,
                  whodunit_path=None, profile_path=None) -> dict:
    path = Path(outline_path)
    if not path.is_file():
        return {"wired": False, "blocking": [f"wiring-parse: outline not found: {path}"],
                "notes": [], "metrics": {}}
    text = path.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    # The overload check reads SCENE WEIGHTS, not wiring, so it runs whether or
    # not this outline is wired — an expanded outline carries scenes and may
    # carry no wiring at all. (An unweighted outline gives it nothing to do, so
    # book 1 is untouched.)
    over = check_overload(chapters, profile_path=profile_path,
                          beat_sheet_path=beat_sheet_path, whodunit_path=whodunit_path)
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
    ap.add_argument("--profile", dest="profile")
    args = ap.parse_args(argv)
    result = check_tension(args.outline, beat_sheet_path=args.beat_sheet,
                           turning_points_path=args.turning_points,
                           whodunit_path=args.whodunit,
                           profile_path=args.profile)
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
