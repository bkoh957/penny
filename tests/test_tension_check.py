from pathlib import Path

from scripts.tension_check import check_tension

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
