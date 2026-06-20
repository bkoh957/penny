from pathlib import Path

from scripts.penny_meta import parse_frontmatter

RUBRICS = Path("config/review-rubrics")
EXPECTED_RUBRICS = [
    "ai-prose-taste-flags.md",  # pre-existing (2a)
    "continuity-drift.md",
    "fairplay-planting.md",
    "structure-tension.md",
    "character-voice.md",
]

AGENTS = Path(".claude/agents")
INSPECTORS = {
    "inspector-continuity": "continuity-drift.md",
    "inspector-fairplay": "fairplay-planting.md",
    "inspector-structure": "structure-tension.md",
    "inspector-voice": "character-voice.md",
    "inspector-ai-prose": "ai-prose-taste-flags.md",
}


def test_all_rubric_files_exist():
    for name in EXPECTED_RUBRICS:
        assert (RUBRICS / name).is_file(), f"missing rubric {name}"


def test_new_rubrics_have_thresholds_and_boundary_sections():
    for name in EXPECTED_RUBRICS:
        text = (RUBRICS / name).read_text(encoding="utf-8").lower()
        assert "threshold" in text, f"{name}: no thresholds guidance"
        assert "boundary" in text, f"{name}: no boundary-with-other-tiers section"


def test_all_inspector_agents_exist_with_valid_frontmatter():
    for name in INSPECTORS:
        path = AGENTS / f"{name}.md"
        assert path.is_file(), f"missing agent {name}"
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        assert meta.get("name") == name
        assert meta.get("description")


def test_each_inspector_names_its_rubric_and_producer():
    for name, rubric in INSPECTORS.items():
        text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
        assert rubric in text, f"{name} does not reference its rubric {rubric}"
        assert f"producer: {name}" in text, f"{name} does not declare its producer"


def test_five_distinct_producers():
    producers = set()
    for name in INSPECTORS:
        text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("producer:"):
                producers.add(line.split("producer:")[1].strip())
    assert len(producers) == 5, f"expected 5 distinct producers, got {producers}"
