from scripts.penny_wiring import (parse_packet_sections, parse_required_beats,
                                  parse_wired_chapters, chapter_block)
from scripts.story_cut import emit_outline
from scripts.penny_story import parse_questions

STORY = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered

- Tom rules it out.
  @tom -q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""

PLAN = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen, and the body that ends it.
- **Compress:** Gallery logistics.
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right in a way Maggie resents.
"""

LEDGER = {"c-altered": "the handover appointment, changed in Maggie's name"}
JOB_TITLES = {"establish-protected-world": "Establish the Protected World",
              "crime-and-first-contradiction": "Deliver the Crime and Its First Contradiction"}


def _emit():
    return emit_outline(STORY, PLAN, parse_questions(STORY), LEDGER,
                        reveal_chapter=2, guardrails="Do not name the culprit early.",
                        job_titles=JOB_TITLES)


def test_emits_one_block_per_chapter_that_the_wiring_parser_accepts():
    chapters = parse_wired_chapters(_emit())
    assert [c["num"] for c in chapters] == [1, 2]
    assert chapters[0]["title"] == "The Life Maggie Chose"


def test_required_beats_are_the_chapters_beats_in_order():
    sections = parse_packet_sections(chapter_block(_emit(), 1))
    beats = parse_required_beats(sections)
    assert beats == ["Maggie chooses this life.", "The appointment was altered."]


def test_wiring_carries_opens_and_closes_with_question_prose():
    out = _emit()
    assert "- **Opens:** q-clear — how can Maggie clear herself?" in out
    assert "- **Closes:** q-clear — how can Maggie clear herself?" in out


def test_because_chains_each_chapter_to_the_one_before():
    out = _emit()
    assert "- **Because:** ch 01" in out
    assert out.count("- **Because:**") == 1  # chapter 01 has no antecedent


def test_clue_section_renders_the_ledger_description():
    sections = parse_packet_sections(chapter_block(_emit(), 1))
    assert "c-altered" in sections["Clues and Plants"]
    assert "handover appointment" in sections["Clues and Plants"]


def test_character_knowledge_names_only_strands_seen_so_far():
    ch1 = parse_packet_sections(chapter_block(_emit(), 1))["Character Knowledge"]
    assert "maggie" in ch1 and "simon" in ch1
    assert "tom" not in ch1


def test_guardrails_and_purpose_are_derived():
    sections = parse_packet_sections(chapter_block(_emit(), 1))
    assert "Do not name the culprit early." in sections["Guardrails"]
    assert "Establish the Protected World" in sections["Chapter Purpose"]


def test_track_movement_rows_come_from_the_cut_plan():
    sections = parse_packet_sections(chapter_block(_emit(), 2))
    assert "- **M:** The police are right in a way Maggie resents." in sections["Track Movement"]


def test_compress_line_is_per_chapter_not_boilerplate():
    a = parse_packet_sections(chapter_block(_emit(), 1))["Reader-Facing Shape"]
    b = parse_packet_sections(chapter_block(_emit(), 2))["Reader-Facing Shape"]
    assert "Gallery logistics." in a
    assert "Procedure." in b
    assert a != b
