from pathlib import Path

from scripts import penny_wiring
from scripts.penny_wiring import parse_wired_chapters, has_wiring, split_id, parse_turning_points

FIX = Path("tests/fixtures/outlines")
PLOT = Path("tests/fixtures/plot")


def _clean():
    return parse_wired_chapters((FIX / "wired-clean.md").read_text(encoding="utf-8"))


def test_parses_all_chapters_in_order():
    chs = _clean()
    assert [c["num"] for c in chs] == [1, 2, 3, 4, 5, 6]
    assert chs[0]["title"] == "Arrival"


def test_because_parsed():
    chs = _clean()
    assert chs[0]["because"] == "opening" and chs[0]["because_ch"] is None
    assert chs[1]["because_ch"] == 1


def test_opens_closes_carries_hook():
    chs = _clean()
    assert chs[0]["opens"] == [("q-who-killed-neil", "who killed the town GP?")]
    assert chs[4]["closes"] == ["q-who-killed-neil", "q-what-mary-hides"]
    assert chs[5]["carries"] == ["q-elspeth-vale"]
    assert chs[0]["hook_q"] == "q-who-killed-neil"


def test_tracks_parsed():
    chs = _clean()
    assert chs[1]["tracks"]["P"] == "None"
    assert chs[0]["tracks"]["M"] == "Body found."


def test_has_wiring_true_on_clean_false_on_legacy():
    assert has_wiring(_clean()) is True
    legacy = (FIX / "well-formed.md").read_text(encoding="utf-8")
    assert has_wiring(parse_wired_chapters(legacy)) is False


def test_bad_question_id_lands_in_errors():
    text = ("---\nbook: 01\ntotal_chapters: 1\n---\n\n## Solution: x\n- culprit: A\n\n"
            "## Chapter 01 — T\nbody\n- **Because:** opening\n- **Opens:** WhoDidIt — bad id\n")
    chs = parse_wired_chapters(text)
    assert chs[0]["errors"] and "WhoDidIt" in chs[0]["errors"][0]


def test_split_id():
    assert split_id("q-x — why?") == ("q-x", "why?")
    assert split_id("q-x") == ("q-x", "")


def test_turning_points_parsed():
    tp = parse_turning_points((PLOT / "turning-points-good.md").read_text(encoding="utf-8"))
    assert tp["total_chapters"] == 6
    assert tp["points"][0] == {"title": "TP-1 — The body in the kitchen",
                               "beat": "inciting-death", "chapter": 2}
    assert len(tp["points"]) == 4


def test_turning_points_tolerates_missing_fields():
    tp = parse_turning_points("---\ntotal_chapters: 4\n---\n\n## TP-1 — Untagged\n- **Breaks:** x\n")
    assert tp["points"][0]["beat"] is None and tp["points"][0]["chapter"] is None


WEIGHTED = Path(__file__).resolve().parent / "fixtures" / "outlines" / "weighted-clean.md"


def test_parse_scenes_reads_weights_beats_and_instruction_mass():
    chapters = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    ch1 = chapters[0]
    assert [s["weight"] for s in ch1["scenes"]] == ["connective", "anchor"]
    assert [s["num"] for s in ch1["scenes"]] == [1, 2]
    assert ch1["scenes"][0]["title"] == "The Drive"
    assert ch1["scenes"][0]["beats"] == 2
    assert ch1["scenes"][1]["beats"] == 3
    # instruction mass = words in the beat-flow text; the anchor carries more here
    assert ch1["scenes"][1]["instruction_words"] > ch1["scenes"][0]["instruction_words"]


def test_parse_chapter_reads_first_line_and_hook_grade():
    chapters = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    assert chapters[0]["first_line"] == "in motion, mid-argument with the estate agent."
    assert chapters[0]["hook_grade"] == "cliffhanger"
    assert chapters[0]["hook_q"] == "q-who-is-she"   # the grade must not eat the id
    assert chapters[1]["hook_grade"] == "promise"


def test_title_flags_parse_type_and_long_waiver():
    chapters = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    assert chapters[0]["chapter_type"] is None
    assert chapters[0]["long_waiver"] is None
    assert chapters[1]["chapter_type"] == "major-reveal"
    assert chapters[1]["long_waiver"] == "the confession runs its full course"
    # the flags must not survive into the title the reader's copy prints
    assert chapters[1]["title"] == "The Reveal"


def test_has_weights_true_for_weighted_outline_false_for_the_wired_one():
    weighted = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    assert penny_wiring.has_weights(weighted) is True
    wired = penny_wiring.parse_wired_chapters((FIX / "wired-clean.md").read_text(encoding="utf-8"))
    assert penny_wiring.has_weights(wired) is False


def test_weight_accepts_bare_and_bulleted_forms():
    # commands/build-briefs.md teaches the bulleted form (matching every other
    # bold field a showrunner already writes: Because/Opens/Closes/Carries/Hook
    # are all "- **Field:**"), and hand-authored outlines will follow it. The
    # parser must accept both spellings and read the identical weight from each.
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Scene 1 — Bare

**Weight:** anchor

**Beat flow:**

1. Beat.

### Scene 2 — Bulleted

- **Weight:** anchor

**Beat flow:**

1. Beat.
"""
    chapters = penny_wiring.parse_wired_chapters(text)
    scenes = chapters[0]["scenes"]
    assert scenes[0]["weight"] == "anchor"
    assert scenes[1]["weight"] == "anchor"


def test_parse_scenes_bounds_last_scene_at_next_h3_heading_of_any_name():
    # A trailing "### Drafting Notes" (or "### Track Movement", etc.) after the
    # last scene must not be swept into that scene's body — its own numbered
    # list is drafting guidance, not beats, and must not inflate beats/
    # instruction_words (the overloaded-chapter check reads these numbers).
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Scene 1 — Only Scene

**Weight:** anchor

**Beat flow:**

1. First beat.
2. Second beat.

### Drafting Notes / Guardrails

1. Not a beat, this is drafting guidance for the model.
2. Neither is this one.
"""
    chapters = penny_wiring.parse_wired_chapters(text)
    scene = chapters[0]["scenes"][0]
    assert scene["beats"] == 2
    assert scene["instruction_words"] == len("First beat.".split()) + len("Second beat.".split())


from scripts.penny_wiring import (chapter_block, parse_packet_sections,
                                  parse_wired_chapters)

PACKET_FIXTURE = Path("tests/fixtures/outlines/packet-format.md")


def test_parse_packet_sections_maps_h3_headings_to_bodies():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    block = chapter_block(text, 5)
    sections = parse_packet_sections(block)
    assert "Chapter Purpose" in sections
    assert "tempts her to use" in sections["Chapter Purpose"]
    assert "Required Beats" in sections
    assert "Guardrails" in sections
    # A section body stops at the next H3 heading
    assert "Faye brings food" not in sections["Chapter Purpose"]


def test_parse_wired_chapters_extracts_required_beats_in_order():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    ch5 = next(c for c in chapters if c["num"] == 5)
    assert len(ch5["required_beats"]) == 10
    assert ch5["required_beats"][0] == "Stronger pottery is finally displayed."
    assert ch5["required_beats"][9] == "Faye receives the death call."
    ch6 = next(c for c in chapters if c["num"] == 6)
    assert ch6["required_beats"] == [
        "Maggie hears the official version of Neil's death."]


def test_packet_format_block_keeps_wiring_and_type_flag():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    ch5 = next(c for c in chapters if c["num"] == 5)
    assert ch5["chapter_type"] == "event"
    assert ch5["because_ch"] == 4
    assert [q for q, _ in ch5["opens"]] == ["q-neil-death"]
    assert ch5["hook_grade"] == "cliffhanger"
    assert ch5["tracks"]["M"].startswith("the death arrives")
    # Packet blocks have no ### Scene sections — the scene list is empty
    assert ch5["scenes"] == []


def test_chapter_with_no_sections_has_empty_dict_and_beats():
    chapters = parse_wired_chapters("## Chapter 01 — Bare\n\nSome prose.\n")
    assert chapters[0]["sections"] == {}
    assert chapters[0]["required_beats"] == []


def test_chapter_block_returns_raw_block():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    block = chapter_block(text, 6)
    assert block.startswith("### Chapter Purpose")
    assert "sergeant asks" in block
    assert "Opening Day" not in block
