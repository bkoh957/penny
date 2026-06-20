from pathlib import Path

RUBRICS = Path("config/review-rubrics")
EXPECTED_RUBRICS = [
    "ai-prose-taste-flags.md",  # pre-existing (2a)
    "continuity-drift.md",
    "fairplay-planting.md",
    "structure-tension.md",
    "character-voice.md",
]


def test_all_rubric_files_exist():
    for name in EXPECTED_RUBRICS:
        assert (RUBRICS / name).is_file(), f"missing rubric {name}"


def test_new_rubrics_have_thresholds_and_boundary_sections():
    for name in EXPECTED_RUBRICS:
        text = (RUBRICS / name).read_text(encoding="utf-8").lower()
        assert "threshold" in text, f"{name}: no thresholds guidance"
        assert "boundary" in text, f"{name}: no boundary-with-other-tiers section"
