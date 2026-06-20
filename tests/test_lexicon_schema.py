from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LEXICON = REPO / "config/setting-pack/lexicon.yaml"
REQUIRED = ("term", "narration_ok_from_stage", "auto_detectable")
STAGES = {"OUTSIDER", "SETTLING", "BELONGING"}


def test_lexicon_yaml_loads_and_has_terms():
    data = yaml.safe_load(LEXICON.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and isinstance(data.get("terms"), list)
    assert data["terms"], "lexicon has no terms"


def test_every_term_has_required_fields_with_valid_types():
    data = yaml.safe_load(LEXICON.read_text(encoding="utf-8"))
    for entry in data["terms"]:
        for field in REQUIRED:
            assert field in entry, f"{entry.get('term', entry)} missing {field}"
        assert isinstance(entry["auto_detectable"], bool), entry["term"]
        assert entry["narration_ok_from_stage"] in STAGES, entry["term"]
