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


def test_parse_map_clue_terminates_before_inline_field():
    # An inline field (text on the same line as its label) must terminate the
    # clue body just like a bare `Turn:` label line does.
    m = parse_map(
        "## Scene 1 — Inline After Clue\n"
        "Weight: Support\n"
        "\n"
        "Clue:\n"
        "Mary folds a tea towel.\n"
        "[whodunit: mary-domestic-order]\n"
        "\n"
        "Result: The room laughs.\n"
    )
    clue = m["scenes"][0]["clue_text"]
    assert "mary-domestic-order" in clue
    assert "The room laughs" not in clue


def test_parse_map_missing_target_is_none_not_crash():
    m = parse_map("## Scene 1 — Untargeted\nWeight: Support\n\nAction:\nX.\n")
    assert m["scenes"][0]["target"] is None
    assert m["scenes"][0]["beats_covered"] == []


def test_map_path_shape(tmp_path):
    p = map_path("01", "5", tmp_path)
    assert str(p).endswith("input/book-01/maps/ch-05.md")


# --- Task 5: the scene-level Texture field (spec 2026-08-27 §4.2) -----------

def test_parse_map_reads_a_scenes_texture_field():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    t = m["scenes"][0]["texture_text"]
    assert "proving-room warmth" in t
    assert "Shed roof at 25 knots" in t


def test_a_scene_with_no_texture_field_is_none():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["scenes"][1]["texture_text"] is None


def test_a_texture_field_does_not_swallow_the_clue_that_follows_it():
    text = ("## Scene 1 — S\nTarget: 400–500 words\nWeight: anchor\n"
            "Beats covered: 1\n"
            "Texture:\nBakery at 6am — proving-room warmth.\n"
            "Clue:\n[c-altered] the appointment, changed.\n")
    s = parse_map(text)["scenes"][0]
    assert "proving-room warmth" in s["texture_text"]
    assert "[c-altered]" not in s["texture_text"]
    assert "[c-altered]" in s["clue_text"]


def test_a_field_label_with_an_apostrophe_terminates_the_clue_body():
    # Regression: CLUE_FIELD_RE's character class must include the STRAIGHT
    # apostrophe (U+0027), not just the curly right single quote, so an
    # ordinary open-vocabulary field label such as "Maggie's turn:" still
    # terminates the preceding Clue: body instead of being swallowed into it.
    text = ("## Scene 1 — S\nTarget: 400–500 words\nWeight: anchor\n"
            "Beats covered: 1\n"
            "Clue:\n[c-altered] the appointment, changed.\n"
            "Maggie's turn: she looks away.\n")
    s = parse_map(text)["scenes"][0]
    assert "Maggie's turn" not in s["clue_text"]


def test_a_field_label_with_an_apostrophe_terminates_the_texture_body():
    text = ("## Scene 1 — S\nTarget: 400–500 words\nWeight: anchor\n"
            "Beats covered: 1\n"
            "Texture:\nBakery at 6am — proving-room warmth.\n"
            "Maggie's turn: she looks away.\n")
    s = parse_map(text)["scenes"][0]
    assert "Maggie's turn" not in s["texture_text"]
