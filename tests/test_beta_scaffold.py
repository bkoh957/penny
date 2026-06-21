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


def test_beta_protocol_documents_contract_and_phase6_seam():
    text = (ROOT / "config/beta-readers/beta-protocol.md").read_text(encoding="utf-8").lower()
    # all §10 contract fields named
    for field in ["engagement_curve", "put_down_points", "whodunit_guess",
                  "confusion_points", "emotional_beats", "would_buy_next"]:
        assert field in text, field
    # the three serialization rules
    assert "n/a" in text and "first-class" in text          # rule 2
    assert "stamp" in text                                   # rule 3 (stamped driver)
    assert "{value, lens}" in text or "value, lens" in text  # rule 1
    # the seam
    assert "phase 6" in text
    assert "cross-persona" in text
    # non-blocking
    assert "non-blocking" in text or "never block" in text


def test_beta_reader_agent_is_blind_and_well_formed():
    path = ROOT / ".claude/agents/beta-reader.md"
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert fm["name"] == "beta-reader"
    assert "description" in fm
    text = path.read_text(encoding="utf-8").lower()
    # blind contract: only text + persona file
    assert "persona" in text and "text" in text
    assert "no ledger" in text or "no ledgers" in text
    assert "no solution" in text
    # reacts, does not rule-reason; driver stamped not picked
    assert "react" in text
    assert "yes" in text and "no" in text and "n/a" in text
    assert "beta_report.py" in text
