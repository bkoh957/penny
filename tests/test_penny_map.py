from pathlib import Path

from scripts.penny_map import map_path, parse_map

FIXTURE = Path("tests/fixtures/maps/ch-05.md")


def test_parse_map_scenes_and_targets():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["stamp"] == "0" * 64
    assert [s["num"] for s in m["scenes"]] == [1, 2, 3, 4, 5]
    assert m["scenes"][0]["title"] == "Before the Door Opens"
    assert m["scenes"][0]["target"] == (350, 450)
    assert m["scenes"][1]["target"] == (900, 1100)  # comma-grouped "1,100"


def test_parse_map_weight_is_free_text():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["scenes"][2]["weight"] == "Primary emotional anchor"
    assert m["scenes"][4]["weight"] == "Secondary anchor and chapter hook"


def test_parse_map_beats_covered_and_clue():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["scenes"][0]["beats_covered"] == [1, 2]
    assert m["scenes"][2]["beats_covered"] == [3, 4, 5, 6]
    assert "mary-domestic-order" in m["scenes"][1]["clue_text"]
    assert m["scenes"][0]["clue_text"] is None


def test_parse_map_missing_target_is_none_not_crash():
    m = parse_map("## Scene 1 — Untargeted\nWeight: Support\n\nAction:\nX.\n")
    assert m["scenes"][0]["target"] is None
    assert m["scenes"][0]["beats_covered"] == []


def test_map_path_shape(tmp_path):
    p = map_path("01", "5", tmp_path)
    assert str(p).endswith("input/book-01/maps/ch-05.md")
