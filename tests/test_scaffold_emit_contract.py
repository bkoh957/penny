import shutil
from pathlib import Path

from scripts.fairplay_check import check_fairplay

FIXTURE = Path("tests/fixtures/outlines/derived-whodunit.yaml")
ENTITY_IDS = ["margaret", "edwin-tilley", "thomas"]


def _seed_entities(repo_root: Path):
    d = repo_root / "series/continuity/characters"
    d.mkdir(parents=True, exist_ok=True)
    for eid in ENTITY_IDS:
        (d / f"{eid}.md").write_text(
            f"---\nid: {eid}\ntype: character\nlinks: []\n---\n# {eid}\n",
            encoding="utf-8",
        )


def test_scaffolder_emit_shape_passes_fairplay(tmp_path):
    led = tmp_path / "series/whodunit/book-01.yaml"
    led.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, led)
    _seed_entities(tmp_path)

    result = check_fairplay(led, culprit_by_fraction=0.85, repo_root=tmp_path)

    assert result["blocking"] == [], result["blocking"]
