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
