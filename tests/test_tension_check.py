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
