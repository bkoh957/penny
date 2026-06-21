from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_finalize_command_exists_and_wires_the_tail():
    text = (ROOT / ".claude/commands/finalize-chapter.md").read_text(encoding="utf-8").lower()
    assert "preflight.py finalize" in text          # gate guard step 0
    assert "ledger_markers.py" in text              # markers step
    assert "line-editor" in text and "copy-editor" in text and "ledger-updater" in text
    assert "--commit" in text                       # resume path documented
    assert "ledger-review" in text                  # the review pause stage


def test_finalize_refuses_rerun_without_commit_flag():
    text = (ROOT / ".claude/commands/finalize-chapter.md").read_text(encoding="utf-8").lower()
    # the no-flag refusal guard must be described
    assert "refus" in text and "ledger-review" in text


def test_review_chapter_roster_uses_real_marker_and_treats_null_silent():
    text = (ROOT / ".claude/commands/review-chapter.md").read_text(encoding="utf-8").lower()
    assert "last_advanced_chapter" in text
    assert "unknown" not in text or "null" in text  # no longer the unknown placeholder
    assert "null" in text                           # null = no liveness flag


def test_thread_seed_has_marker_field():
    text = (ROOT / "series/continuity/threads/the-inheritance.md").read_text(encoding="utf-8")
    assert "last_advanced_chapter" in text


def test_draft_preamble_refreshed():
    text = (ROOT / ".claude/commands/draft-chapter.md").read_text(encoding="utf-8").lower()
    assert "no review bus yet" not in text
