from pathlib import Path

from scripts.reset_reviews import reset_reviews, main


def _populated(tmp_path):
    d = tmp_path / "output" / "book-01" / "chapters" / "ch-07.reviews"
    d.mkdir(parents=True)
    (d / "inspector-voice.md").write_text("BLOCKING: stale from run 1\n", encoding="utf-8")
    (d / "voice-drift.md").write_text("- evidence\n", encoding="utf-8")
    (d.parent / "ch-07.gate.md").write_text("gate: HOLD\n", encoding="utf-8")
    return d


def test_reset_clears_verdicts_and_stale_gate(tmp_path):
    d = _populated(tmp_path)
    reset_reviews(d)
    assert d.is_dir()  # dir kept, emptied
    assert list(d.glob("*.md")) == []
    assert not (d.parent / "ch-07.gate.md").exists()


def test_reset_absent_dir_is_noop(tmp_path):
    # Must not error if the chapter was never reviewed before.
    reset_reviews(tmp_path / "output" / "book-01" / "chapters" / "ch-09.reviews")


def test_main_returns_zero(tmp_path):
    d = _populated(tmp_path)
    assert main([str(d)]) == 0
    assert list(d.glob("*.md")) == []
