from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cozy"


# Series-specific input data: no plugin-side default. Task 6 hides these live
# repo-root paths (series/, input/), so they are checked against the
# self-contained cozy fixture rather than this repo's own live series data.
REQUIRED_FIXTURE_INPUT_FILES = [
    "input/series/series-bible.md",
    "series/arc-ledger.md",
    "input/series/style-sheet.md",
    "input/series/whodunit-ledger.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_FIXTURE_INPUT_FILES)
def test_fixture_input_file_exists_and_nonempty(relpath):
    path = FIXTURE / relpath
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


# Per-book input data lives only in the series folder (hidden by Task 6), so the
# book outline is checked against the fixture too.
REQUIRED_FIXTURE_INPUT_BOOK_FILES = [
    "input/book-01/outline.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_FIXTURE_INPUT_BOOK_FILES)
def test_fixture_input_book_file_exists_and_nonempty(relpath):
    path = FIXTURE / relpath
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


# Engine-default config: these ship with the plugin and stay at repo root even
# after Task 6 hides the series/genre overrides.
REQUIRED_CONFIG_FILES = [
    "config/self-audit/self-audit-checklist.md",     # Tier B (already present)
    "config/review-rubrics/ai-prose-taste-flags.md", # Tier C (already present)
]


@pytest.mark.parametrize("relpath", REQUIRED_CONFIG_FILES)
def test_config_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


# Series/genre config overrides hidden by Task 6 (config/genre-pack,
# config/voice-pack, config/setting-pack, config/length-profile.md,
# config/run-config.md) — checked against the cozy fixture, not repo root.
REQUIRED_FIXTURE_CONFIG_FILES = [
    "config/run-config.md",
    "config/genre-pack/cozy-mystery.md",
    "config/voice-pack/voice-pack.md",
    "config/voice-pack/ai-tics-detection.md",
    "config/setting-pack/coastal-victoria-au.md",
    "config/setting-pack/lexicon.md",
    "config/length-profile.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_FIXTURE_CONFIG_FILES)
def test_fixture_config_file_exists_and_nonempty(relpath):
    path = FIXTURE / relpath
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


REQUIRED_CLAUDE_FILES = [
    "agents/_TEMPLATE.md",
    "agents/drafter.md",
    "commands/draft-chapter.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_CLAUDE_FILES)
def test_claude_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


def test_draft_chapter_writes_current_stage():
    text = Path("commands/draft-chapter.md").read_text(encoding="utf-8")
    assert ".penny/current-stage" in text, (
        "draft-chapter must document writing the harness state marker (design §11)"
    )
