from scripts.penny_story import parse_story, parse_questions

STORY = """---
stage: story
book: 02
---

## Act I

- Maggie chooses this life: the gallery, the commission call
  with a closing date.
  @maggie #establish-protected-world

- The handover appointment was altered — in Maggie's name.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered

- Tom closes the file on the appointment.
  -q-clear

## Questions
- q-clear — how can Maggie clear herself without performing panic?
- q-main — who killed Lisa?
"""


def test_parses_beats_in_order_with_tags_stripped_from_text():
    beats = parse_story(STORY)
    assert len(beats) == 3
    assert beats[0]["text"] == (
        "Maggie chooses this life: the gallery, the commission call "
        "with a closing date.")
    assert beats[0]["strands"] == ["maggie"]
    assert beats[0]["jobs"] == ["establish-protected-world"]
    assert beats[0]["opens"] == []


def test_collects_every_sigil():
    b = parse_story(STORY)[1]
    assert b["strands"] == ["maggie", "simon"]
    assert b["jobs"] == ["crime-and-first-contradiction"]
    assert b["opens"] == ["q-clear"]
    assert b["clues"] == ["c-altered"]
    assert "@maggie" not in b["text"]
    assert "!c-altered" not in b["text"]


def test_close_sigil_is_not_confused_with_a_bullet():
    beats = parse_story(STORY)
    assert beats[2]["closes"] == ["q-clear"]
    assert beats[2]["text"] == "Tom closes the file on the appointment."


def test_headings_carry_no_meaning_and_questions_block_holds_no_beats():
    # "## Act I" must not become a beat, and the Questions block's bullets
    # must not either — spec 3.1, 3.1.1.
    assert all("Act I" not in b["text"] for b in parse_story(STORY))
    assert all("how can Maggie" not in b["text"] for b in parse_story(STORY))


def test_parse_questions_reads_id_and_prose():
    q = parse_questions(STORY)
    assert q["q-clear"] == "how can Maggie clear herself without performing panic?"
    assert q["q-main"] == "who killed Lisa?"


def test_line_numbers_count_from_the_full_text_including_frontmatter():
    beats = parse_story(STORY)
    assert STORY.splitlines()[beats[0]["line"] - 1].startswith("- Maggie chooses")


def test_untagged_beat_is_legal():
    beats = parse_story("- Just a thing that happens.\n")
    assert beats[0]["text"] == "Just a thing that happens."
    assert beats[0]["strands"] == []
