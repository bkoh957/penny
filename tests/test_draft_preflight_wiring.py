from pathlib import Path

import yaml

DRAFT_CMD = Path(".claude/commands/draft-chapter.md")
BOOK01 = Path("series/whodunit/book-01.yaml")


def test_draft_chapter_runs_preflight_gate():
    text = DRAFT_CMD.read_text(encoding="utf-8")
    assert "preflight.py draft" in text, "draft-chapter must gate on the draft pre-flight"


def test_book01_has_no_locked_field():
    data = yaml.safe_load(BOOK01.read_text(encoding="utf-8"))
    assert "locked" not in data, "the lock is an out-of-band file, not a yaml field"
