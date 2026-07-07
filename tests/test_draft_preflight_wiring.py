from pathlib import Path

DRAFT_CMD = Path("commands/draft-chapter.md")


def test_draft_chapter_runs_preflight_gate():
    text = DRAFT_CMD.read_text(encoding="utf-8")
    assert "scripts/preflight.py" in text and "preflight.py\" draft" in text, (
        "draft-chapter must gate on the draft pre-flight"
    )
