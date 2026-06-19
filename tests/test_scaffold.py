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
