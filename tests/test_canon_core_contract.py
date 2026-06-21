from pathlib import Path

from scripts.penny_meta import parse_canon_meta, parse_canon_sections

CANON = Path(__file__).resolve().parents[1] / "series/continuity/canon-core.md"
REQUIRED = {"id", "refs", "active_window", "last_referenced", "reconfirmed_at", "keep_reason"}


def test_every_section_has_full_canon_meta_header():
    text = CANON.read_text(encoding="utf-8")
    secs = parse_canon_sections(text)
    assert len(secs) == 4
    for s in secs:
        assert REQUIRED <= set(s), f"{s.get('id')} missing {REQUIRED - set(s)}"


def test_file_level_fluency_stage_preserved():
    meta = parse_canon_meta(CANON.read_text(encoding="utf-8"))
    assert meta.get("id") == "canon-core"
    assert meta.get("fluency_stage") == "OUTSIDER"


def test_protagonist_section_refs_the_protagonist():
    secs = parse_canon_sections(CANON.read_text(encoding="utf-8"))
    prot = next(s for s in secs if s["id"] == "protagonist-fixed")
    assert "cora-mistate" in prot["refs"]
