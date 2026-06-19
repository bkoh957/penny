from pathlib import Path

import pytest

REQUIRED_SERIES_FILES = [
    "series/series-bible.md",
    "series/arc-ledger.md",
    "series/style-sheet.md",
    "series/whodunit-ledger.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_SERIES_FILES)
def test_series_memory_file_exists_and_nonempty(relpath):
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
