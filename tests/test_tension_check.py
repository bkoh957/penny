from pathlib import Path

from scripts.tension_check import _closings_check, check_tension

FIX = Path("tests/fixtures/outlines")


def _predicates(result):
    return {b.split(":", 1)[0] for b in result["blocking"]}


def test_clean_wired_outline_has_no_findings():
    r = check_tension(FIX / "wired-clean.md")
    assert r["wired"] is True and r["blocking"] == []


def test_unwired_outline_is_skipped():
    r = check_tension(FIX / "well-formed.md")
    assert r["wired"] is False and r["blocking"] == []


def test_orphan_chapter():
    assert "orphan-chapter" in _predicates(check_tension(FIX / "wired-orphan.md"))


def test_dropped_question():
    assert "dropped-question" in _predicates(check_tension(FIX / "wired-dropped-question.md"))


def test_phantom_answer():
    assert "phantom-answer" in _predicates(check_tension(FIX / "wired-phantom-answer.md"))


def test_broken_hook_on_already_closed_question():
    assert "broken-hook" in _predicates(check_tension(FIX / "wired-broken-hook.md"))


def test_carried_question_stays_hookable():
    # wired-clean ch 06 carries q-elspeth-vale and hooks it: must NOT be broken-hook.
    r = check_tension(FIX / "wired-clean.md")
    assert not any(b.startswith("broken-hook") for b in r["blocking"])


BEATS = Path("tests/fixtures/plot/beat-sheet.yaml")
WHOD = Path("tests/fixtures/plot/whodunit-mini.yaml")


def test_dead_stretch_fires_before_reveal_proxy():
    r = check_tension(FIX / "wired-dead-stretch.md", beat_sheet_path=BEATS)
    assert "dead-stretch" in _predicates(r)


def test_starved_thread_fires_past_max_dark_gap():
    r = check_tension(FIX / "wired-starved-thread.md", beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_clean_outline_survives_curve_checks_with_real_reveal():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS, whodunit_path=WHOD)
    assert r["blocking"] == []


def test_curve_checks_skipped_without_beat_sheet():
    r = check_tension(FIX / "wired-starved-thread.md")
    assert "starved-thread" not in _predicates(r)


def test_carried_question_stays_open_for_dead_stretch_count():
    # wired-carry-midbook: ch 02 carries q-a (opened ch 01) and opens nothing
    # new. If carries were wrongly subtracted from the open-question count
    # (like closes), ch 02's open count would drop to 0 — below
    # min_open_before_reveal (1) and before the reveal (ch 05) — and
    # dead-stretch would fire. A carried question must stay OPEN, so the
    # clean outline must survive with zero blocking findings.
    r = check_tension(FIX / "wired-carry-midbook.md", beat_sheet_path=BEATS, whodunit_path=WHOD)
    assert r["blocking"] == []
    assert r["metrics"]["open_counts"][2] == 1


from scripts.tension_check import main as tension_main

TP_GOOD = Path("tests/fixtures/plot/turning-points-good.md")
TP_BAD = Path("tests/fixtures/plot/turning-points-offmark.md")


def test_off_mark_beat_fires():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=TP_BAD, whodunit_path=WHOD)
    assert "off-mark-beat" in _predicates(r)


def test_on_mark_beats_pass():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=TP_GOOD, whodunit_path=WHOD)
    assert r["blocking"] == []


def test_reveal_beat_checked_against_whodunit(tmp_path):
    bad_whod = Path("tests/fixtures/plot/whodunit-mini.yaml")  # reveal 5
    # TP_GOOD places reveal at 5 → clean; re-point at ch 4 via off-mark fixture logic:
    text = TP_GOOD.read_text(encoding="utf-8").replace(
        "## TP-4 — The kitchen truth\n- **Beat:** reveal\n- **Chapter:** 5",
        "## TP-4 — The kitchen truth\n- **Beat:** reveal\n- **Chapter:** 4")
    tp_path = tmp_path / "turning-points-reveal-mismatch.md"
    tp_path.write_text(text, encoding="utf-8")
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=tp_path, whodunit_path=bad_whod)
    assert "off-mark-beat" in _predicates(r)


def test_cli_exit_codes(capsys):
    assert tension_main([str(FIX / "wired-clean.md"), "--beat-sheet", str(BEATS),
                         "--whodunit", str(WHOD)]) == 0
    assert tension_main([str(FIX / "wired-orphan.md")]) == 1
    assert "orphan-chapter" in capsys.readouterr().out


def test_cli_unwired_skips_exit_zero(capsys):
    assert tension_main([str(FIX / "well-formed.md")]) == 0
    assert "no wiring" in capsys.readouterr().out


# --- FINAL REVIEW FINDING 2: chapter-coverage — the chapters-stage failure
# mode (N separate chapter-weaver dispatches, one per turning-point gap) is
# gaps/dupes at the seams; nothing compared the chapter set to total_chapters.

def test_chapter_coverage_fires_on_gap():
    r = check_tension(FIX / "wired-chapter-gap.md")
    assert _predicates(r) == {"chapter-coverage"}


def test_chapter_coverage_fires_on_total_chapters_mismatch(tmp_path):
    # The finding's own reproduction: total_chapters declares more than the
    # skeleton actually has (chapters 1-22 of a declared 24).
    text = (FIX / "wired-clean.md").read_text(encoding="utf-8").replace(
        "total_chapters: 6", "total_chapters: 8")
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    assert "chapter-coverage" in _predicates(check_tension(p))


def test_chapter_coverage_quiet_on_clean_outline():
    r = check_tension(FIX / "wired-clean.md")
    assert "chapter-coverage" not in _predicates(r)


def test_chapter_coverage_waivable_like_every_other_check(tmp_path):
    # Waivability is automatic via the check-id prefix convention
    # (preflight._parse_waivers / cmd_lock_mystery splits on the first ":").
    r = check_tension(FIX / "wired-chapter-gap.md")
    assert all(f.split(":", 1)[0] == "chapter-coverage" for f in r["blocking"])


# --- FINAL REVIEW FINDING 4: starved-thread must fail CLOSED on a MISSING
# Track Movement row, not silently count it as advancing. -------------------

def test_starved_thread_fires_on_missing_track_rows():
    r = check_tension(FIX / "wired-starved-thread-missing-rows.md", beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_starved_thread_fires_when_track_movement_section_entirely_absent(tmp_path):
    # A chapter with NO track rows at all (not even the ones that DO advance)
    # must still be caught — the original bug was `dark` only True when the
    # row exists AND starts with "none", so an absent row read as advancing.
    text = """---
book: 01
total_chapters: 3
---

## Chapter 01 — One

### Chapter Structure
- **Hook:** q-a — first?
- **Because:** opening
- **Opens:** q-a — first?

## Chapter 02 — Two

### Chapter Structure
- **Hook:** q-a — still?
- **Because:** ch 01 — follows.

## Chapter 03 — Three

### Chapter Structure
- **Hook:** q-a — still?
- **Because:** ch 02 — follows.
- **Closes:** q-a
"""
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = check_tension(p, beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_starved_thread_still_quiet_when_rows_present_and_advancing():
    # Regression guard: the fix must not make every track look starved —
    # wired-clean's chapters all carry real Track Movement rows.
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS)
    assert "starved-thread" not in _predicates(r)


# --- Task 7: overloaded-chapter, re-based onto Required Beats --------------
#
# The check used to read SCENE WEIGHTS (a length-profile.md band/floor
# budget). It now reads REQUIRED BEATS (packet format, spec-v3): the
# obligation load a chapter carries is its beats + clues to plant + questions
# opened/closed + tracks advanced, against the genre beat sheet's
# `obligations.max_per_chapter`. A legacy outline (scenes/weights, no
# Required Beats sections) is skipped entirely — the stop-everything
# invariant that lets an unmigrated book keep locking exactly as before.

from scripts.tension_check import check_overload
from scripts.penny_wiring import parse_wired_chapters

PACKET = FIX / "packet-format.md"


def test_overload_fires_on_beat_heavy_chapter(tmp_path):
    # Packet-format ch 05: 10 Required Beats, 1 open, 1 close, 2 live tracks
    # (M, R) — plus 1 clue scheduled here in a fixture ledger built for this
    # test. Load = 10 + 1 + 1 + 1 + 2 = 15 against a cap of 12: blocking.
    chapters = parse_wired_chapters(PACKET.read_text(encoding="utf-8"))
    whodunit = tmp_path / "book-01.yaml"
    whodunit.write_text(
        "reveal_chapter: 6\nclue_schedule:\n"
        "  - {id: c-death, plant_chapter: 5}\n", encoding="utf-8")
    beat_sheet = tmp_path / "beat-sheet.yaml"
    beat_sheet.write_text("obligations:\n  max_per_chapter: 12\n", encoding="utf-8")
    result = check_overload(chapters, beat_sheet_path=beat_sheet, whodunit_path=whodunit)
    assert result["applicable"] is True
    finding = next((b for b in result["blocking"] if b.startswith("overloaded-chapter")), None)
    assert finding is not None
    assert "ch 5" in finding
    assert "10 required beat(s)" in finding


def test_overload_skips_by_name_without_required_beats(tmp_path):
    # A legacy outline (scenes, weights, no Required Beats sections) must be
    # skipped entirely — applicable False, no blocking, and NO notes. Any
    # note here would mean the un-migrated shape is no longer "exactly as
    # before", which is the whole point of the gate.
    chapters = parse_wired_chapters((FIX / "wired-clean.md").read_text(encoding="utf-8"))
    beat_sheet = tmp_path / "beat-sheet.yaml"
    beat_sheet.write_text("obligations:\n  max_per_chapter: 1\n", encoding="utf-8")
    result = check_overload(chapters, beat_sheet_path=beat_sheet)
    assert result == {"applicable": False, "blocking": [], "notes": []}


def test_overload_counts_beats_plus_obligations(tmp_path):
    # Same chapter, same load (15), but a cap of 20: clean.
    chapters = parse_wired_chapters(PACKET.read_text(encoding="utf-8"))
    whodunit = tmp_path / "book-01.yaml"
    whodunit.write_text(
        "reveal_chapter: 6\nclue_schedule:\n"
        "  - {id: c-death, plant_chapter: 5}\n", encoding="utf-8")
    beat_sheet = tmp_path / "beat-sheet.yaml"
    beat_sheet.write_text("obligations:\n  max_per_chapter: 20\n", encoding="utf-8")
    result = check_overload(chapters, beat_sheet_path=beat_sheet, whodunit_path=whodunit)
    assert result["applicable"] is True
    assert result["blocking"] == []


def test_overload_missing_cap_is_named_note():
    # A beat-heavy outline with no beat sheet (or one without
    # obligations.max_per_chapter) can't be capped at all: a named note, not
    # a silent skip and not a crash.
    chapters = parse_wired_chapters(PACKET.read_text(encoding="utf-8"))
    result = check_overload(chapters)
    assert result["applicable"] is True
    assert result["blocking"] == []
    notes = " ".join(result["notes"])
    assert "overloaded-chapter" in notes
    assert "obligations.max_per_chapter" in notes


def _ch(num, kind):
    return {"num": num,
            "sections": {"Closing": f"{kind} — something happens"} if kind else {}}


def test_a_run_longer_than_the_cap_fires():
    chapters = [_ch(n, "Cliffhanger") for n in range(1, 5)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert any(b.startswith("monotonous-closings:") and "ch 04" in b
               for b in blocking)


def test_a_run_exactly_at_the_cap_does_not_fire():
    chapters = [_ch(n, "Cliffhanger") for n in range(1, 4)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []


def test_a_varied_book_does_not_fire():
    chapters = [_ch(1, "Cliffhanger"), _ch(2, "Irony"),
                _ch(3, "Cliffhanger"), _ch(4, "Promise of action")]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []


def test_absent_genre_key_is_a_named_note_never_a_silent_pass():
    chapters = [_ch(n, "Cliffhanger") for n in range(1, 6)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=None)
    assert blocking == []
    assert any(n.startswith("monotonous-closings —") for n in notes)


def test_an_outline_with_no_closings_is_skipped_entirely():
    chapters = [_ch(n, None) for n in range(1, 6)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == [] and notes == []


BEATS_WITH_CLOSINGS = Path("tests/fixtures/plot/beat-sheet-with-closings.yaml")


def test_monotonous_closings_reaches_blocking_through_check_tension_wired():
    # Integration coverage for the glue in check_tension() itself: the
    # beat-sheet-path guard, the _load_yaml(...).get("closings") read, and
    # the call site on the WIRED return path — not just _closings_check in
    # isolation. wired-monotonous-closings.md is wired-clean.md (which is
    # independently pinned findings-clean) plus four chapters in a row
    # closing on Cliffhanger against this fixture's cap of 3.
    r = check_tension(FIX / "wired-monotonous-closings.md",
                       beat_sheet_path=BEATS_WITH_CLOSINGS, whodunit_path=WHOD)
    assert r["wired"] is True
    assert "monotonous-closings" in _predicates(r)


def test_monotonous_closings_reaches_blocking_through_check_tension_unwired():
    # Same glue, but through the UNWIRED early-return path — the check must
    # still run on a book with no Because/Opens wiring at all (legacy/
    # hand-authored/scaffolded outlines are exactly this check's real-world
    # input, per the review finding).
    r = check_tension(FIX / "unwired-monotonous-closings.md",
                       beat_sheet_path=BEATS_WITH_CLOSINGS)
    assert r["wired"] is False
    assert "monotonous-closings" in _predicates(r)


def test_a_chapter_with_no_closing_breaks_the_run_rather_than_hiding_it():
    # 1,2 = cliffhanger, 3 = no Closing at all, 4,5 = cliffhanger. The real
    # longest run on the page is 2, not 4 — ch 03 does not end on a
    # cliffhanger, so it must not be silently skipped as if it were never
    # there. Review finding: filtering ch 03 out before counting made the
    # check report a false 4-chapter run at ch 05.
    chapters = [_ch(1, "Cliffhanger"), _ch(2, "Cliffhanger"), _ch(3, None),
                _ch(4, "Cliffhanger"), _ch(5, "Cliffhanger")]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []


# --- Final review, Important 2: an unrecognised "kind" must not be measured -

def test_unrecognized_closing_kind_is_treated_as_absent_and_breaks_the_run():
    # ch 03's Closing is free prose ("Freeform"), not one of CLOSING_KINDS —
    # exactly what a hand-authored/scaffolded ### Closing looks like, since
    # story_cut's unknown-closing-kind only guards cut plans. Treated as
    # absent, it must break the run the same way a missing Closing does
    # (see the test above), not silently keep it going as if "freeform" were
    # a real, repeatable kind.
    chapters = [_ch(1, "Cliffhanger"), _ch(2, "Cliffhanger"), _ch(3, "Freeform"),
                _ch(4, "Cliffhanger"), _ch(5, "Cliffhanger")]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []
    assert notes == []


def test_all_unrecognized_kinds_produce_the_named_note_not_a_silent_return():
    # Every chapter HAS a ### Closing (so this is not the no-Closing-anywhere
    # case below), but none of them names a recognised kind — the check has
    # nothing to measure and must say so by name, not return silently.
    chapters = [_ch(n, "Freeform") for n in range(1, 5)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []
    assert any(n.startswith("monotonous-closings —") for n in notes)


def test_no_closing_anywhere_still_stays_a_silent_skip():
    # The other half of the same distinction: an outline with NO ### Closing
    # section at all (the legacy shape) must still produce neither a finding
    # nor a note — collapsing this into the "unrecognised kind" case above
    # would turn every legacy outline's silence into a spurious note.
    chapters = [_ch(n, None) for n in range(1, 5)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == [] and notes == []


# --- The book-number form: one resolution, shared with the lock -------------
#
# `check_tension` takes an outline PATH, while `preflight lock-mystery`
# resolves FOUR inputs for it. Handed a bare path, `beat_sheet_path` is None
# and five of the ten checks silently do not run (dead-stretch,
# starved-thread, off-mark-beat, overloaded-chapter, monotonous-closings), so
# a showrunner reading the findings BEFORE the lock got half a report with no
# signal that it was half. One resolver, called by both: two copies would let
# the report and the gate disagree about what was checked.

PLOT = Path(__file__).resolve().parent / "fixtures" / "plot"
COZY = Path(__file__).resolve().parent / "fixtures" / "cozy"


def _series_with_book_01(tmp_path, *, genre="cozy-mystery", write_outline=True,
                         outline_fixture="packet-format.md",
                         turning_points="turning-points-good.md",
                         reveal_chapter=22):
    """A minimal series tree: `.penny/` marker, a series.yaml declaring a
    genre, book 01's outline, its turning points, and its whodunit ledger."""
    root = tmp_path / "series-tmp"
    (root / ".penny").mkdir(parents=True)
    if genre is not None:
        (root / "series.yaml").write_text(
            f"series: Tmp Series\ngenre: {genre}\n", encoding="utf-8")
    plot = root / "input" / "book-01" / "plot"
    plot.mkdir(parents=True)
    if write_outline:
        (root / "input" / "book-01" / "outline.md").write_text(
            (Path(__file__).resolve().parent / "fixtures" / "outlines"
             / outline_fixture).read_text(encoding="utf-8"), encoding="utf-8")
    (plot / "turning-points.md").write_text(
        (PLOT / turning_points).read_text(encoding="utf-8"), encoding="utf-8")
    wd = root / "series" / "whodunit"
    wd.mkdir(parents=True)
    (wd / "book-01.yaml").write_text(
        f"book: '01'\nreveal_chapter: {reveal_chapter}\n", encoding="utf-8")
    return root


def test_resolve_inputs_finds_all_four(tmp_path):
    """The book-number form must resolve what preflight resolves — a missing
    beat sheet silently disables five of the ten checks (spec §3a.1)."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    got = tension_check.resolve_inputs("01", repo_root=root)

    assert set(got) == {"outline", "beat_sheet_path", "turning_points_path",
                        "whodunit_path"}
    assert got["outline"] is not None and got["outline"].name == "outline.md"
    assert got["turning_points_path"] is not None
    assert got["whodunit_path"] is not None
    # The beat sheet resolves through the genre overlay, not a hardcoded name.
    assert got["beat_sheet_path"] is not None and got["beat_sheet_path"].is_file()


def test_resolve_inputs_keys_splat_into_check_tension(tmp_path):
    """The three non-outline keys are named exactly as check_tension's keyword
    arguments so a caller can splat them; `outline` is separate because it is
    positional. If a key is ever renamed, this raises TypeError."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    got = tension_check.resolve_inputs("01", repo_root=root)
    res = tension_check.check_tension(
        got["outline"], **{k: v for k, v in got.items() if k != "outline"})
    assert "blocking" in res and "notes" in res


def test_resolve_inputs_normalises_a_missing_beat_sheet_to_none(tmp_path, monkeypatch):
    """`config_path()` always returns SOME path, even when nothing exists
    there. An unnormalised miss would be passed to check_tension as a live
    path and the named 'could not run' note that the lock certificate records
    as `skipped: <check-id>` would never fire."""
    from scripts import penny_genre, tension_check

    root = _series_with_book_01(tmp_path)
    ghost = root / "config" / "no-such-beat-sheet.yaml"
    monkeypatch.setattr(penny_genre, "beat_sheet", lambda root=None: ghost)

    assert not ghost.exists()
    assert tension_check.resolve_inputs("01", repo_root=root)["beat_sheet_path"] is None


def test_resolve_inputs_beat_sheet_is_none_without_a_declared_genre(tmp_path):
    """No series.yaml/genre — the beat sheet cannot be resolved at all, and
    the checks that depend on it must report themselves skipped rather than
    crash on a dead path."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, genre=None)
    assert tension_check.resolve_inputs("01", repo_root=root)["beat_sheet_path"] is None


def test_resolve_inputs_returns_none_for_a_book_with_no_outline(tmp_path):
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, write_outline=False)
    assert tension_check.resolve_inputs("01", repo_root=root)["outline"] is None


def test_resolve_inputs_returns_none_for_absent_turning_points_and_ledger(tmp_path):
    """A path that does not exist resolves to None, never to a non-existent
    Path — the same normalisation the beat sheet gets."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    (root / "input/book-01/plot/turning-points.md").unlink()
    (root / "series/whodunit/book-01.yaml").unlink()
    got = tension_check.resolve_inputs("01", repo_root=root)
    assert got["turning_points_path"] is None
    assert got["whodunit_path"] is None


def test_resolve_inputs_zero_pads_a_one_digit_book(tmp_path):
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    got = tension_check.resolve_inputs("1", repo_root=root)
    assert got["outline"] is not None and "book-01" in str(got["outline"])
    assert got["whodunit_path"] is not None


def test_cli_accepts_a_book_number(tmp_path, monkeypatch, capsys):
    """`tension_check.py 01` from a series folder must behave as the lock does."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    monkeypatch.chdir(root)
    rc = tension_check.main(["01"])
    out = capsys.readouterr().out

    assert rc in (0, 1)                       # 0 clean, 1 findings — never a usage error
    assert "usage:" not in out
    # "01" must have been RESOLVED to the book's outline, not read as a path:
    # a bare path form treats it as a missing file and reports wiring-parse.
    assert "wiring-parse" not in out


def test_cli_book_number_runs_the_beat_sheet_dependent_checks(tmp_path, monkeypatch, capsys):
    """THE point of the book-number form. The same outline read as a bare path
    cannot report dead-stretch at all (no beat sheet); read as a book number it
    does, because the genre's beat sheet is resolved for it."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, outline_fixture="wired-dead-stretch.md")

    monkeypatch.chdir(root)
    assert tension_check.main(["01"]) == 1
    with_number = capsys.readouterr().out
    # The FINDING line, not the "skipped" note — the note names the same five
    # check ids, so a bare substring match here would pass either way.
    assert "tension_check: dead-stretch:" in with_number

    tension_check.main([str(root / "input/book-01/outline.md")])
    with_path = capsys.readouterr().out
    assert "tension_check: dead-stretch:" not in with_path


def test_cli_book_number_passes_the_resolved_turning_points(tmp_path, monkeypatch, capsys):
    """off-mark-beat needs the turning points AND the beat sheet. The bare path
    form has neither; the book-number form resolves both."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, outline_fixture="wired-clean.md",
                                turning_points="turning-points-offmark.md",
                                reveal_chapter=5)
    monkeypatch.chdir(root)
    tension_check.main(["01"])
    out = capsys.readouterr().out
    assert "tension_check: off-mark-beat: inciting-death" in out

    tension_check.main([str(root / "input/book-01/outline.md")])
    # The FINDING line, not the "could not run" note — the bare path form now
    # NAMES off-mark-beat as skipped (spec 2026-09-10), so a bare substring
    # match here would pass whether or not the check actually ran.
    assert "tension_check: off-mark-beat:" not in capsys.readouterr().out


def test_cli_book_number_passes_the_resolved_whodunit(tmp_path, monkeypatch, capsys):
    """The reveal beat is checked against the LEDGER's reveal_chapter. With no
    whodunit resolved, reveal_ch is None and that comparison never happens."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, outline_fixture="wired-clean.md",
                                turning_points="turning-points-good.md",
                                reveal_chapter=4)   # the turning point says ch 5
    monkeypatch.chdir(root)
    tension_check.main(["01"])
    out = capsys.readouterr().out
    assert "whodunit reveal_chapter is 4" in out

    tension_check.main(["01", "--whodunit", str(root / "nope.yaml")])
    assert "whodunit reveal_chapter" not in capsys.readouterr().out


def test_cli_names_the_skipped_checks_for_an_UNUSABLE_explicit_beat_sheet(
        tmp_path, monkeypatch, capsys):
    """The same hole through the other door. `check_tension` guards every beat
    sheet use with `.is_file()`, so an explicit --beat-sheet pointing at a file
    that does not exist skips the identical five checks as no beat sheet at
    all — and must be reported the identical way, or the module's promise that
    it never hands back half a report silently is false."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, outline_fixture="wired-dead-stretch.md")
    ghost = root / "no-such-beat-sheet.yaml"
    assert not ghost.exists()
    monkeypatch.chdir(root)
    tension_check.main(["01", "--beat-sheet", str(ghost)])
    out = capsys.readouterr().out

    assert "no beat sheet resolved" in out
    for check in ("dead-stretch", "starved-thread", "off-mark-beat",
                  "overloaded-chapter", "monotonous-closings"):
        assert check in out                             # the note names all five
    assert "tension_check: dead-stretch:" not in out    # ...and none of them ran


def test_cli_still_accepts_an_outline_path(tmp_path):
    """The path form is what preflight and existing callers use — unchanged."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    rc = tension_check.main([str(root / "input/book-01/outline.md")])
    assert rc in (0, 1)


def test_cli_book_number_fails_by_name_when_the_outline_is_missing(tmp_path, monkeypatch, capsys):
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, write_outline=False)
    monkeypatch.chdir(root)
    rc = tension_check.main(["01"])
    assert rc == 2
    assert "no outline" in capsys.readouterr().err.lower()


def test_cli_explicit_flags_beat_the_book_number_form(tmp_path, monkeypatch, capsys):
    """An explicit --beat-sheet must still win: the book-number resolution is
    a default, not an override."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, outline_fixture="wired-dead-stretch.md")
    monkeypatch.chdir(root)
    # A beat sheet path that does not exist disables the curve checks again.
    rc = tension_check.main(["01", "--beat-sheet", str(root / "nope.yaml")])
    out = capsys.readouterr().out
    assert rc in (0, 1)
    assert "wiring-parse" not in out                     # the outline still resolved
    assert "tension_check: dead-stretch:" not in out     # the override disabled it


def test_preflight_lock_mystery_resolves_through_resolve_inputs(tmp_path, monkeypatch):
    """The drift guard. preflight must not keep its own copy of the
    resolution: a second copy would let the showrunner's report and the lock's
    gate disagree about which checks ran."""
    import shutil

    from scripts import preflight, tension_check

    calls = []
    real = tension_check.resolve_inputs

    def spy(book, repo_root=None):
        calls.append((book, repo_root))
        return real(book, repo_root=repo_root)

    monkeypatch.setattr(tension_check, "resolve_inputs", spy)

    fixture = Path(__file__).resolve().parent / "fixtures" / "cozy"
    (tmp_path / "config/setting-pack").mkdir(parents=True)
    shutil.copy(fixture / "config/run-config.md", tmp_path / "config/run-config.md")
    shutil.copy(fixture / "config/setting-pack/lexicon.yaml",
                tmp_path / "config/setting-pack/lexicon.yaml")
    (tmp_path / "series/continuity/characters").mkdir(parents=True)
    shutil.copy(fixture / "series/continuity/canon-core.md",
                tmp_path / "series/continuity/canon-core.md")
    for cid in ("margaret", "thomas", "edwin-tilley"):
        (tmp_path / f"series/continuity/characters/{cid}.md").write_text(
            "---\nid: x\n---\n", encoding="utf-8")
    (tmp_path / "series/whodunit").mkdir(parents=True)
    shutil.copy(Path(preflight.REPO) / "tests/fixtures/ledgers/fair.yaml",
                tmp_path / "series/whodunit/book-01.yaml")
    shutil.copy(fixture / "series.yaml", tmp_path / "series.yaml")

    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    assert calls and calls[0][0] == "01"


# --- spec 2026-09-10: a check that CANNOT RUN says so through the notes
# channel, so `preflight lock-mystery` can stamp it on the certificate as
# `skipped: <check-id> — <why>`. `_curve_checks` and `_beat_checks` were the
# two guards with no note of their own: they simply did not run, and the
# certificate still read `validated: fairplay+lexicon+tension`. -----------

def _noted(result, check):
    return [n for n in result["notes"] if n.startswith(f"{check} — ")]


def test_wired_without_a_beat_sheet_notes_all_three_curve_beat_checks():
    """Door one: wired outline, no resolvable beat sheet."""
    r = check_tension(FIX / "wired-clean.md")
    assert r["wired"] is True
    for check in ("dead-stretch", "starved-thread", "off-mark-beat"):
        assert _noted(r, check), f"{check} vanished with no note: {r['notes']}"
        assert "beat sheet" in _noted(r, check)[0]


def test_wired_with_a_beat_sheet_but_no_turning_points_notes_off_mark_beat_alone():
    """Door two, nested inside door one's success case."""
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS)
    assert _noted(r, "off-mark-beat"), r["notes"]
    assert "turning point" in _noted(r, "off-mark-beat")[0]
    # The two checks that DID run must not be noted as skipped.
    assert not _noted(r, "dead-stretch") and not _noted(r, "starved-thread")


def test_a_ran_beat_check_leaves_no_note():
    """The converse at module level: with both inputs present, nothing is noted."""
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=Path("tests/fixtures/plot/turning-points-good.md"))
    assert r["notes"] == []


def test_an_unwired_outline_notes_none_of_them():
    """Explicitly NOT changed (spec §3). On an unwired outline these three are
    NOT APPLICABLE rather than unrunnable — they all need wiring — so noting
    them would turn every legacy outline's correct silence into certificate
    noise, the same trap `_closings_check` documents for an outline with no
    Closing section anywhere."""
    r = check_tension(FIX / "well-formed.md")
    assert r["wired"] is False
    for check in ("dead-stretch", "starved-thread", "off-mark-beat"):
        assert not _noted(r, check), r["notes"]


def test_no_beat_sheet_notes_each_dependent_check_exactly_once(tmp_path):
    """The drift guard, pinned to something OUTSIDE the constants.

    An earlier version of this test asserted the notes named exactly
    `CURVE_BEAT_CHECKS` — but that set is derived from `_SELF_NOTING`, so both
    sides of the comparison moved together and a stale `_SELF_NOTING` was
    invisible to it. The observable property is the PARTITION itself: with no
    beat sheet resolvable, every beat-sheet-dependent check must be noted
    exactly ONCE — once by its own check (`overloaded-chapter`,
    `monotonous-closings`) or once by the wired branch. A check missing from
    `_SELF_NOTING` that self-notes is then a DUPLICATE `skipped:` line, and one
    wrongly listed there vanishes from the certificate entirely. Both fail here.

    The outline needs Required Beats and a Closing for the two self-noting
    checks to be applicable at all, which no committed wired fixture carries —
    hence the splice.
    """
    from collections import Counter

    from scripts import tension_check

    src = (FIX / "wired-clean.md").read_text(encoding="utf-8")
    spliced = src.replace(
        "\n## Chapter 02 — The Cake Tin",
        "\n### Required Beats\n- Maggie finds the kitchen door open.\n"
        "\n### Closing\ncliffhanger — the light upstairs is on.\n"
        "\n## Chapter 02 — The Cake Tin", 1)
    assert spliced != src                     # the splice landed
    outline = tmp_path / "outline.md"
    outline.write_text(spliced, encoding="utf-8")

    r = check_tension(outline)                # no beat sheet resolvable
    counted = Counter(n.split(" — ", 1)[0] for n in r["notes"])
    assert counted == Counter(tension_check.BEAT_SHEET_DEPENDENT), r["notes"]


# --- fix round 1: the third door, one level inside door 1's success case.
# A beat sheet that RESOLVES but declares no tracks.max_dark_gap leaves
# `_curve_checks`'s track loop nothing to iterate — starved-thread produced no
# finding and no note while the certificate stamped `validated: …+tension`.
# Latent while cozy-mystery declares all four tracks; a new genre pack is
# exactly what trips it. -------------------------------------------------

def test_a_beat_sheet_with_no_max_dark_gap_notes_starved_thread(tmp_path):
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("questions:\n  min_open_before_reveal: 1\n", encoding="utf-8")
    r = check_tension(FIX / "wired-dead-stretch.md", beat_sheet_path=sheet)
    assert _noted(r, "starved-thread"), r["notes"]
    assert "tracks.max_dark_gap" in _noted(r, "starved-thread")[0]
    # ...and ONLY starved-thread: dead-stretch defaults its own threshold and
    # genuinely ran, which the finding below proves.
    assert not _noted(r, "dead-stretch")
    assert "dead-stretch" in _predicates(r)


def test_a_beat_sheet_declaring_max_dark_gap_notes_nothing(tmp_path):
    """The converse — the note must not fire on a sheet that does declare it."""
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=Path("tests/fixtures/plot/turning-points-good.md"))
    assert not _noted(r, "starved-thread"), r["notes"]


def test_the_door_two_note_names_no_path(tmp_path):
    """`--turning-points` may be passed explicitly, so naming the resolved
    default the caller never used would send them looking in the wrong place.
    Door 1 names no file either."""
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=tmp_path / "nope.md")
    note = _noted(r, "off-mark-beat")[0]
    assert "turning points" in note
    assert "input/book-" not in note and ".md" not in note
