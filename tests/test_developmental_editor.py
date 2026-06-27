from pathlib import Path

from scripts.penny_meta import parse_frontmatter

RUBRIC = Path("config/review-rubrics/developmental-craft.md")

EIGHT_DIMENSIONS = [
    "setting grounding",
    "motivation",
    "scene economy",
    "subtext",
    "interiority",
    "show",          # show-don't-tell
    "genre delivery",
    "hook",
]


def test_rubric_exists_with_thresholds_and_boundary():
    assert RUBRIC.is_file()
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "threshold" in text
    assert "boundary" in text


def test_rubric_names_all_eight_dimensions():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    for dim in EIGHT_DIMENSIONS:
        assert dim in text, f"rubric missing dimension: {dim}"


def test_rubric_is_advisory_never_blocking():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "advisory" in text
    assert "no ^blocking" in text or "never block" in text or "not block" in text
