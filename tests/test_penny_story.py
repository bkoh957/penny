from scripts.penny_story import parse_story, parse_questions, parse_directives
from scripts.penny_story import parse_cut_plan

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


CUT_PLAN = """---
book: 02
---

## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-3
- **Summary:** Maggie's chosen life, and the body that ends it.
- **Compress:** Gallery logistics and the drive out.
- **M:** The murder enters a world we have just been shown.
- **P:** Maggie is happy, which is what she has to lose.

## Chapter 02 — The Woman Who Found Her

- **Beats:** 4, 6-7
- **Summary:** Faye's account, and the altered appointment.
- **Compress:** Repeated introductions.
- **M:** The appointment contradiction lands.
"""


def test_parse_cut_plan_expands_ranges_and_lists():
    chapters = parse_cut_plan(CUT_PLAN)
    assert [c["num"] for c in chapters] == [1, 2]
    assert chapters[0]["beats"] == [1, 2, 3]
    assert chapters[1]["beats"] == [4, 6, 7]


def test_parse_cut_plan_reads_title_summary_compress():
    c = parse_cut_plan(CUT_PLAN)[0]
    assert c["title"] == "The Life Maggie Chose"
    assert c["summary"] == "Maggie's chosen life, and the body that ends it."
    assert c["compress"] == "Gallery logistics and the drive out."


def test_parse_cut_plan_reads_track_rows_keyed_by_letter():
    chapters = parse_cut_plan(CUT_PLAN)
    assert chapters[0]["tracks"] == {
        "M": "The murder enters a world we have just been shown.",
        "P": "Maggie is happy, which is what she has to lose."}
    assert list(chapters[1]["tracks"]) == ["M"]


STORY_WITH_BLOCKS = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie @simon +q-clear

## Chapter Direction

- These two belong in one chapter. #establish-protected-world

## Guardrails

- Don't flatten Marion into a cackling villain; her usefulness is her camouflage.
  @tara-marion
- Keep the community on the page in the endgame.

## Questions
- q-clear — how can Maggie clear herself?
"""


def test_directive_bullets_are_not_beats():
    beats = parse_story(STORY_WITH_BLOCKS)
    assert [b["text"] for b in beats] == [
        "Maggie chooses this life.",
        "The appointment was altered.",
    ]


def test_parse_directives_reads_guardrails_with_continuation_lines():
    notes = parse_directives(STORY_WITH_BLOCKS, "Guardrails")
    assert len(notes) == 2
    assert notes[0]["text"] == (
        "Don't flatten Marion into a cackling villain; "
        "her usefulness is her camouflage.")
    assert notes[0]["strands"] == ["tara-marion"]
    assert notes[1]["strands"] == [] and notes[1]["jobs"] == []


def test_parse_directives_reads_chapter_direction_and_is_case_insensitive():
    notes = parse_directives(STORY_WITH_BLOCKS, "chapter direction")
    assert [n["text"] for n in notes] == ["These two belong in one chapter."]
    assert notes[0]["jobs"] == ["establish-protected-world"]


def test_parse_directives_returns_empty_when_the_block_is_absent():
    assert parse_directives("- A beat. @maggie\n", "Guardrails") == []


# --- FINAL REVIEW, Important 1: parse_story skipped frontmatter and
# parse_directives/parse_questions did not, so a `##` heading occurring INSIDE
# frontmatter (legal in a YAML block scalar) opened a directive block that
# nothing could close — `---` is not a `##` heading — and every beat in the body
# was read as both a beat and a book-wide directive. All three parsers now walk
# the same frontmatter-skipped view of the file. ---

# A `## …` line at column 0 inside frontmatter is a YAML COMMENT — perfectly
# legal, and indistinguishable from a markdown heading to a line-walking parser
# that never skipped the frontmatter.
FRONTMATTER_TRAP = """---
stage: story
book: 02
## Guardrails
---

- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie +q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""


def test_a_guardrails_heading_inside_frontmatter_opens_no_directive_block():
    # Nothing closes it — `---` is not a `##` heading — so before the fix every
    # beat in the body was read as a book-wide guardrail as well as a beat, and
    # the whole story was emitted verbatim into every chapter's Guardrails.
    assert parse_directives(FRONTMATTER_TRAP, "Guardrails") == []


def test_beats_are_unaffected_by_a_heading_inside_frontmatter():
    assert [b["text"] for b in parse_story(FRONTMATTER_TRAP)] == [
        "Maggie chooses this life.",
        "The appointment was altered.",
    ]


QUESTIONS_FRONTMATTER_TRAP = """---
stage: story
## Questions
---

- q-main — a beat whose prose happens to lead with an id-shaped token.
  @maggie

## Questions
- q-clear — how can Maggie clear herself?
"""


def test_a_questions_heading_inside_frontmatter_is_not_the_questions_block():
    # Same offset gap, same shape: the frontmatter comment opened the questions
    # block, so body bullets before the first real heading were harvested as
    # question prose.
    assert parse_questions(QUESTIONS_FRONTMATTER_TRAP) == {
        "q-clear": "how can Maggie clear herself?"}


# --- FINAL REVIEW, Minor 4: parse_story dropped entries with neither prose nor
# tags; parse_directives did not, so a lone `- ` in the Guardrails block became
# a directive with text == "" and was emitted as a bare `- ` bullet in every
# chapter. One fold, one filter. ---

LONE_BULLET = (
    "- A beat. @maggie\n"
    "\n"
    "## Guardrails\n"
    "\n"
    "- \n"
    "- A real note.\n"
)


def test_an_empty_directive_bullet_is_dropped():
    notes = parse_directives(LONE_BULLET, "Guardrails")
    assert [n["text"] for n in notes] == ["A real note."]


PLAN = """\
## Chapter 07 — The Tin in the Tide
- **Beats:** 22-25
- **Summary:** She finds the tin.
- **Compress:** the walk back
- **Setting:**
  - 22-23 — the pottery studio, late afternoon
  - 24-25 — the harbour road, dusk, rain coming in off the water
- **Opening:** The kiln door still warm and the studio empty behind her.
- **Closing (promise of action):** She pockets the tin and turns for the harbour.
- **M:** the tin surfaces
"""


def test_settings_parse_in_order_with_expanded_ranges():
    ch = parse_cut_plan(PLAN)[0]
    assert ch["settings"] == [
        {"beats": [22, 23], "text": "the pottery studio, late afternoon"},
        {"beats": [24, 25],
         "text": "the harbour road, dusk, rain coming in off the water"},
    ]


def test_opening_and_closing_parse_with_kind_in_the_key():
    ch = parse_cut_plan(PLAN)[0]
    assert ch["opening"] == "The kiln door still warm and the studio empty behind her."
    assert ch["closing"] == {"kind": "promise of action",
                             "text": "She pockets the tin and turns for the harbour."}


def test_setting_range_accepts_single_beats_and_lists():
    plan = ("## Chapter 01 — X\n"
            "- **Beats:** 1-4\n"
            "- **Setting:**\n"
            "  - 1 — the kitchen, dawn\n"
            "  - 2,4 — the yard, noon\n")
    assert [s["beats"] for s in parse_cut_plan(plan)[0]["settings"]] == [[1], [2, 4]]


def test_closing_kind_is_lowercased_but_not_validated_here():
    plan = ("## Chapter 01 — X\n"
            "- **Beats:** 1\n"
            "- **Closing (Cliffhanger):** the door opens\n")
    assert parse_cut_plan(plan)[0]["closing"]["kind"] == "cliffhanger"


def test_legacy_plan_without_the_fields_gets_empty_defaults():
    plan = ("## Chapter 01 — X\n"
            "- **Beats:** 1-3\n"
            "- **Summary:** s\n"
            "- **Compress:** c\n"
            "- **M:** m\n")
    ch = parse_cut_plan(plan)[0]
    assert ch["settings"] == [] and ch["opening"] == "" and ch["closing"] is None
    assert ch["tracks"] == {"M": "m"}


def test_a_track_row_is_never_mistaken_for_a_new_field():
    ch = parse_cut_plan(PLAN)[0]
    assert ch["tracks"] == {"M": "the tin surfaces"}


# --- Task 3: the cut plan's Texture allocation (spec 2026-08-27 §4.2) --------

TEXTURE_PLAN = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen, and the body that ends it.
- **Compress:** Gallery logistics.
- **Texture:**
  - bakery 6am: proving-room warmth, the scorched tray edge
  - shed roof at 25 knots (plants the ch 29 return)
- **Setting:**
  - 1-2 — the pottery studio, late afternoon
- **Opening:** The kiln is still warm.
- **Closing (irony):** She locks a door that was never the way in.
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right in a way Maggie resents.
"""


def test_texture_items_are_parsed_in_authoring_order():
    chapters = parse_cut_plan(TEXTURE_PLAN)
    assert chapters[0]["texture"] == [
        "bakery 6am: proving-room warmth, the scorched tray edge",
        "shed roof at 25 knots (plants the ch 29 return)",
    ]


def test_a_chapter_with_no_texture_field_defaults_to_empty():
    chapters = parse_cut_plan(TEXTURE_PLAN)
    assert chapters[1]["texture"] == []


def test_texture_nesting_does_not_swallow_the_fields_that_follow_it():
    chapters = parse_cut_plan(TEXTURE_PLAN)
    ch = chapters[0]
    assert [s["text"] for s in ch["settings"]] == ["the pottery studio, late afternoon"]
    assert ch["opening"] == "The kiln is still warm."
    assert ch["closing"]["kind"] == "irony"
    assert ch["tracks"] == {"M": "The murder enters a world just shown."}
    assert ch["compress"] == "Gallery logistics."


def test_an_indented_track_row_after_texture_is_still_a_track_not_an_item():
    # The item pattern is broad free prose, so the field patterns must win.
    plan = """## Chapter 01 — T

- **Summary:** s
- **Texture:**
  - one image
  - **M:** the mystery moves
"""
    ch = parse_cut_plan(plan)[0]
    assert ch["texture"] == ["one image"]
    assert ch["tracks"] == {"M": "the mystery moves"}


def test_an_inline_texture_value_is_kept_as_a_first_item():
    plan = "## Chapter 01 — T\n\n- **Summary:** s\n- **Texture:** one image\n"
    assert parse_cut_plan(plan)[0]["texture"] == ["one image"]


def test_a_plan_written_before_texture_existed_parses_exactly_as_before():
    plan = "## Chapter 01 — T\n\n- **Beats:** 1-2\n- **Summary:** s\n- **M:** m\n"
    ch = parse_cut_plan(plan)[0]
    assert ch["texture"] == []
    assert ch["beats"] == [1, 2]
    assert ch["tracks"] == {"M": "m"}
