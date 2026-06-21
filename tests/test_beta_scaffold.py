# tests/test_beta_scaffold.py
from pathlib import Path
from scripts.penny_meta import parse_frontmatter
from scripts.beta_report import DRIVER_BY_PERSONA

ROOT = Path(__file__).resolve().parents[1]
PERSONA_DIR = ROOT / "config/beta-readers/personas"


def test_all_six_personas_present():
    names = {p.stem for p in PERSONA_DIR.glob("*.md")}
    assert names == set(DRIVER_BY_PERSONA), f"persona set mismatch: {names}"


def test_each_persona_declares_matching_driver():
    for path in PERSONA_DIR.glob("*.md"):
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        assert fm["name"] == path.stem
        assert fm["driver"] == DRIVER_BY_PERSONA[path.stem], path.stem
        assert "primary_axes" in fm


def test_only_arc_reader_declares_facets():
    for path in PERSONA_DIR.glob("*.md"):
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        facets = str(fm.get("facets", "[]"))
        if path.stem == "arc-reader":
            assert "self" in facets and "place" in facets
        else:
            assert "self" not in facets and "place" not in facets, path.stem


def test_newcomer_states_frozen_lexicon_cold_invariant():
    text = (PERSONA_DIR / "newcomer-outsider.md").read_text(encoding="utf-8").lower()
    assert "zero lexicon fluency" in text
    assert "regardless of series position" in text


def test_romance_authorizes_na_verdict():
    text = (PERSONA_DIR / "romance-reader.md").read_text(encoding="utf-8").lower()
    assert "n/a" in text and "romantic thread" in text
