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
  notes    — a check that COULD NOT RUN, and why (no genre beat sheet resolves
             at all; one resolves but declares no obligations.max_per_chapter,
             no tracks.max_dark_gap or no closings.max_same_kind_run; no
             turning points resolve; the whodunit ledger cannot be read).
             Never a traceback out of a working command, never a silent
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
  overloaded-chapter a chapter's obligation load — required beats + clues
                     planted + questions opened/closed + tracks advanced —
                     exceeds the genre beat sheet's obligations.max_per_chapter.
                     A PLOT property (too many stops for the length), caught
                     before a word is drafted (spec §6). Runs on any outline
                     carrying Required Beats anywhere; an outline with none
                     (the legacy scenes/weights shape) is never checked.
  monotonous-closings a run of chapters longer than the genre beat sheet's
                     closings.max_same_kind_run all ending on the same kind
                     (from each chapter's ### Closing section, spec
                     2026-08-12 §5.2). A BOOK property, not a per-chapter one.
                     Runs on any outline carrying a Closing section anywhere,
                     wired or not; an outline with none (the legacy shape) is
                     never checked.

  python3 scripts/tension_check.py NN            # a 1-2 digit book number
  python3 scripts/tension_check.py input/book-NN/outline.md \
      [--beat-sheet P] [--turning-points P] [--whodunit P]

The BOOK-NUMBER form resolves the same four inputs `preflight lock-mystery`
resolves, through the same `resolve_inputs` below. Handed only a bare outline
path, `beat_sheet_path` is None and FIVE of the ten checks silently do not run
(dead-stretch, starved-thread, off-mark-beat, overloaded-chapter,
monotonous-closings) — so a showrunner reading the findings BEFORE the lock got
half a report with no signal that it was half. The path form is unchanged and
is what preflight and existing callers use.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter
from scripts.penny_wiring import has_wiring, parse_wired_chapters
from scripts.story_cut import CLOSING_KINDS


def _load_yaml(path):
    import yaml  # PyYAML: beat sheet + whodunit are genuinely nested human data
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


# A 1-2 digit book number, as opposed to an outline path (the other CLI form).
_BOOK_RE = re.compile(r"^\d{1,2}$")

# The five checks a missing beat sheet takes out of the report, in ONE spelling.
# `preflight lock-mystery` imports this rather than keeping its own sentence:
# the report and the gate exist to predict each other, so a pair that named
# different subsets of the same skip would be the one place a discrepancy is
# guaranteed to mislead. (The last two also raise their own "could not run" note
# through the notes channel, which preflight records on the certificate; this
# line is what a showrunner reads on stdout.)
BEAT_SHEET_DEPENDENT = ("dead-stretch", "starved-thread", "off-mark-beat",
                        "overloaded-chapter", "monotonous-closings")
NO_BEAT_SHEET_NOTE = ("no beat sheet resolved; curve/beat checks ("
                      + ", ".join(BEAT_SHEET_DEPENDENT) + ") skipped")

# The two of the five that raise their OWN "could not run" note, from inside
# their own check, whether or not the outline is wired. Noting them again in
# check_tension's wired branch would double-record them on the certificate.
_SELF_NOTING = ("overloaded-chapter", "monotonous-closings")
# ...leaving the three that had no note of their own: `_curve_checks` and
# `_beat_checks` were simply not called, so the check vanished with no finding,
# no note and no `skipped:` line while the lock still stamped
# `validated: fairplay+lexicon+tension` (spec 2026-09-10). DERIVED from
# BEAT_SHEET_DEPENDENT rather than re-listed: the report and the gate exist to
# predict each other, and two hand-kept lists of the same ids is the one place
# a discrepancy is guaranteed to mislead.
CURVE_BEAT_CHECKS = tuple(c for c in BEAT_SHEET_DEPENDENT if c not in _SELF_NOTING)


def _first_file(*paths):
    """First candidate that actually exists, else None.

    Deliberately a local reimplementation of `preflight._first_file` and NOT an
    import: preflight imports `check_tension` from this module, so importing
    back would be a cycle.
    """
    for p in paths:
        if p is not None and Path(p).is_file():
            return p
    return None


def resolve_inputs(book: str, repo_root=None) -> dict:
    """The four inputs `check_tension` needs, resolved for one book.

    ONE home, called by both `preflight lock-mystery` and this module's CLI: a
    second copy would let the showrunner's report and the lock's gate disagree
    about which checks ran, and the report exists precisely to predict the gate.

    The three non-outline keys are named exactly as `check_tension`'s keyword
    arguments so a caller can splat them; `outline` is separate because it is
    positional.

    A path that does not exist resolves to None, never to a non-existent Path.
    That matters most for the beat sheet: `config_path()` always returns SOME
    path (falling back to the plugin default location even when nothing exists
    there), so an unnormalised miss would be passed through as real and the
    named "could not run" note the certificate records as
    `skipped: <check-id> — <why>` would never fire.

    The beat sheet resolves THROUGH the active genre's `genre.yaml` `beat_sheet:`
    key (`penny_genre.beat_sheet`), never a hardcoded filename — a genre pack
    naming its file differently must not silently lose the curve/beat checks.
    An undeclared genre yields None there, which is not an error: this checker
    runs over any wired outline, including one with no genre context.
    """
    from scripts import penny_genre, penny_paths

    raw = str(book).strip()
    nn = f"{int(raw):02d}" if raw.isdigit() else raw

    beat_sheet_path = penny_genre.beat_sheet(root=repo_root)
    if beat_sheet_path is not None and not Path(beat_sheet_path).is_file():
        beat_sheet_path = None

    def _inp(rel_nn: str, rel_raw: str):
        # The zero-padded name is the contract; the literal one is a fallback so
        # a caller that already passed an unpadded number behaves as it did.
        return _first_file(penny_paths.input_path(rel_nn, root=repo_root),
                           penny_paths.input_path(rel_raw, root=repo_root))

    return {
        "outline": _inp(f"book-{nn}/outline.md", f"book-{raw}/outline.md"),
        "beat_sheet_path": beat_sheet_path,
        "turning_points_path": _inp(f"book-{nn}/plot/turning-points.md",
                                    f"book-{raw}/plot/turning-points.md"),
        "whodunit_path": _first_file(
            penny_paths.series_path(f"whodunit/book-{nn}.yaml", root=repo_root),
            penny_paths.series_path(f"whodunit/book-{raw}.yaml", root=repo_root)),
    }


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


def _curve_checks(chapters, beat_sheet, reveal_ch, blocking, notes):
    """dead-stretch + starved-thread, against a beat sheet that DID resolve.

    The thresholds are genre numbers and the two checks treat a missing one
    differently, on purpose. `min_open_before_reveal` has a defensible default
    (1) and is applied below, so dead-stretch genuinely runs whatever the sheet
    says. `tracks.max_dark_gap` has none — the tracks it names ARE the roster
    being checked — so a sheet declaring none leaves the loop nothing to
    iterate, and starved-thread would otherwise pass silently while the
    certificate stamped `validated: …+tension`. That is the same over-claim one
    level in, so it is a named note, exactly as `_closings_check` does for its
    own absent threshold.
    """
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
    gaps = (beat_sheet.get("tracks") or {}).get("max_dark_gap") or {}
    if not gaps:
        notes.append(
            "starved-thread — the check could not run: the genre's beat sheet "
            "declares no tracks.max_dark_gap")
    for track, limit in sorted(gaps.items()):
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


def _closings_check(chapters, blocking, notes, *, max_run=None):
    """The tenth check: a run of identical chapter endings (spec 2026-08-12 §5.2).

    Five cliffhangers running is a fact about the BOOK, not a defect in any one
    chapter — which is why it lives here and not among story_cut's per-chapter
    findings. The threshold is a genre number, so an absent key is a named note
    on the certificate, never a silent pass.

    An outline carrying no ### Closing anywhere is the legacy shape and is
    skipped entirely — it has no note to give, exactly as an outline with no
    Required Beats is skipped by the overload check.

    A chapter with no Closing of its own (a mixed legacy/hand-authored/
    scaffolded outline outside Task 2's all-or-nothing rule — exactly what
    this check meets in the wild) BREAKS the run rather than being invisible
    to it: skipping it outright would let two runs either side of the gap
    silently concatenate into one that never actually happened on the page.

    This check is aimed squarely at hand-authored/scaffolded outlines — the
    ones `story_cut.check_story`'s `unknown-closing-kind` never sees, because
    that finding guards cut plans only. So a `### Closing` reading free prose
    ("She leaves the shed.") must not be treated as a real "kind": that would
    let this check measure prose that can never literally repeat, and quietly
    skip the "could not run" note it owes the lock certificate. Any extracted
    kind not in CLOSING_KINDS is therefore treated as ABSENT — same as no
    Closing at all, which already breaks a run correctly (see above). If NO
    chapter yields a recognised kind, that is worth a named note (the check
    could not measure anything); but an outline with NO Closing section
    ANYWHERE is a different case and stays a silent skip, exactly as before —
    collapsing the two would turn every legacy outline's silence into a
    spurious note.
    """
    raw_present = any((ch.get("sections") or {}).get("Closing", "")
                       for ch in chapters)
    if not raw_present:
        return
    kinds = []
    for ch in chapters:
        raw = (ch.get("sections") or {}).get("Closing", "")
        kind = raw.split("—")[0].strip().lower()
        kinds.append((ch["num"], kind if kind in CLOSING_KINDS else ""))
    if not any(k for _, k in kinds):
        notes.append(
            "monotonous-closings — the check could not run: no chapter's "
            "### Closing names a recognised kind "
            f"({', '.join(CLOSING_KINDS)})")
        return
    if max_run is None:
        notes.append(
            "monotonous-closings — the check could not run: the genre's beat sheet "
            "declares no closings.max_same_kind_run")
        return
    run_kind, run_len = None, 0
    for num, kind in kinds:
        if not kind:
            run_kind, run_len = None, 0
            continue
        run_len = run_len + 1 if kind == run_kind else 1
        run_kind = kind
        if run_len > int(max_run):
            blocking.append(
                f"monotonous-closings: ch {num:02d} is the {run_len}th chapter in a "
                f"row ending on {run_kind}, against the genre's run cap of {max_run} "
                f"— a book whose endings stop varying reads as machinery no matter "
                f"how good each one is")


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
    max_run = None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        closings = _load_yaml(beat_sheet_path).get("closings")
        if isinstance(closings, dict) and closings.get("max_same_kind_run") is not None:
            max_run = int(closings["max_same_kind_run"])
    _closings_check(chapters, over["blocking"], over["notes"], max_run=max_run)
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
    # outline only ever runs through tension_check.py). Model on
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
    # These three notes belong to the WIRED branch only. On an unwired outline
    # the curve/beat checks are NOT APPLICABLE rather than unrunnable — they all
    # read wiring — and `validated:` correctly stays `fairplay+lexicon`, so
    # noting them there would turn every legacy outline's correct silence into
    # certificate noise (the trap `_closings_check` documents for an outline
    # with no Closing section anywhere).
    notes = list(over["notes"])
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        beat_sheet = _load_yaml(beat_sheet_path)
        metrics["open_counts"] = _curve_checks(chapters, beat_sheet, reveal_ch,
                                               blocking, notes)
        if turning_points_path is not None and Path(turning_points_path).is_file():
            from scripts.penny_wiring import parse_turning_points
            tp = parse_turning_points(Path(turning_points_path).read_text(encoding="utf-8"))
            _beat_checks(tp["points"], beat_sheet, total, reveal_ch, blocking)
        else:
            # The nested door: the beat sheet resolved, so the curve checks ran,
            # but the beat check has no turning points to measure.
            # Names no path, as door 1 names no file: the turning points may
            # have been passed explicitly, and reporting a resolved default the
            # caller never used would send them looking in the wrong place. The
            # book is identified by the certificate's own `book:` line above.
            notes.append(
                "off-mark-beat — the check could not run: no turning points "
                "resolved for this book")
    else:
        for check in CURVE_BEAT_CHECKS:
            notes.append(
                f"{check} — the check could not run: no genre beat sheet resolved")
    blocking += over["blocking"]
    return {"wired": True, "blocking": blocking, "notes": notes, "metrics": metrics}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny dramatic-wiring checker.")
    ap.add_argument("outline", metavar="OUTLINE-PATH|NN",
                    help="an outline path, or a 1-2 digit book number to resolve "
                         "the same four inputs `preflight lock-mystery` resolves")
    ap.add_argument("--beat-sheet", dest="beat_sheet")
    ap.add_argument("--turning-points", dest="turning_points")
    ap.add_argument("--whodunit", dest="whodunit")
    args = ap.parse_args(argv)
    outline = args.outline
    beat_sheet = args.beat_sheet
    turning_points = args.turning_points
    whodunit = args.whodunit
    if _BOOK_RE.match(str(outline).strip()):
        # The book-number form. Explicit flags still win per-flag: the
        # resolution is a default, not an override.
        got = resolve_inputs(outline)
        if got["outline"] is None:
            print(f"tension_check: no outline for book {str(outline).strip()} "
                  f"(expected input/book-{int(str(outline).strip()):02d}/outline.md)",
                  file=sys.stderr)
            return 2
        outline = got["outline"]
        if beat_sheet is None:
            beat_sheet = got["beat_sheet_path"]
        if turning_points is None:
            turning_points = got["turning_points_path"]
        if whodunit is None:
            whodunit = got["whodunit_path"]
        # Through _first_file, not merely `is None`: check_tension guards every
        # beat-sheet use with .is_file(), so an EXPLICIT --beat-sheet naming a
        # file that does not exist skips the identical five checks. Reported the
        # same way, or the note has a hole exactly the shape of the bug it
        # exists to close.
        beat_sheet = _first_file(beat_sheet)
        if beat_sheet is None:
            # Never silent about half a report: the five beat-sheet-dependent
            # checks are exactly what the bare path form loses.
            print(f"tension_check: note — {NO_BEAT_SHEET_NOTE}")
    result = check_tension(outline, beat_sheet_path=beat_sheet,
                           turning_points_path=turning_points,
                           whodunit_path=whodunit)
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
