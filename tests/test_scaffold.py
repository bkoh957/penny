from pathlib import Path

import pytest

REQUIRED_INPUT_FILES = [
    "input/series/series-bible.md",
    "series/arc-ledger.md",
    "input/series/style-sheet.md",
    "input/series/whodunit-ledger.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_INPUT_FILES)
def test_input_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


REQUIRED_INPUT_BOOK_FILES = [
    "input/book-01/outline.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_INPUT_BOOK_FILES)
def test_input_book_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


REQUIRED_CONFIG_FILES = [
    "config/run-config.md",
    "config/genre-pack/cozy-mystery.md",
    "config/voice-pack/voice-pack.md",
    "config/voice-pack/ai-tics-detection.md",        # Tier A (already present)
    "config/self-audit/self-audit-checklist.md",     # Tier B (already present)
    "config/review-rubrics/ai-prose-taste-flags.md", # Tier C (already present)
    "config/setting-pack/coastal-victoria-au.md",
    "config/setting-pack/lexicon.md",
    "config/length-profile.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_CONFIG_FILES)
def test_config_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


REQUIRED_CLAUDE_FILES = [
    ".claude/agents/_TEMPLATE.md",
    ".claude/agents/drafter.md",
    ".claude/commands/draft-chapter.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_CLAUDE_FILES)
def test_claude_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


def test_draft_chapter_writes_current_stage():
    text = Path(".claude/commands/draft-chapter.md").read_text(encoding="utf-8")
    assert ".penny/current-stage" in text, (
        "draft-chapter must document writing the harness state marker (design §11)"
    )
