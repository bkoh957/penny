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
    # EVERY chapter carries a Because — one per chapter, no exceptions. This
    # test previously asserted `== 1` and so pinned the bug: chapter 01 had no
    # Because line at all, which `tension_check` reports as
    # `orphan-chapter: ch 01 has no Because line` on every cut book (final
    # review, Critical 2).
    assert out.count("- **Because:**") == len(parse_wired_chapters(out))


def test_chapter_one_because_is_the_literal_tension_check_accepts():
    # `_graph_checks` accepts exactly two forms — the literal `opening` (only
    # on chapter 1) or `ch NN` naming an earlier chapter. Anything else is
    # `orphan-chapter: … Because names no chapter`.
    out = _emit()
    assert "- **Because:** opening" in out
    assert out.count("- **Because:** opening") == 1


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


# --- Fix-report coverage: findings from the Task 4 review -----------------

def test_carries_excludes_a_question_this_chapter_closes():
    # Chapter 02 closes q-clear (beat 3). Close-and-carry in the same chapter
    # is a shape the format never produces (0/28 in book-01's outline) — the
    # bug was `_carried` alone deciding "carried", with no exclusion for
    # questions this same chapter closes.
    chapters = parse_wired_chapters(_emit())
    ch2 = next(c for c in chapters if c["num"] == 2)
    assert "q-clear" in ch2["closes"]
    assert "q-clear" not in ch2["carries"]


def test_carries_still_includes_a_question_this_chapter_opens():
    # Chapter 01 opens q-clear (beat 2) and does not close it — the 28/28
    # case the reviewer confirmed against book-01: an opened-and-not-yet-closed
    # question still carries out of the chapter that opens it.
    chapters = parse_wired_chapters(_emit())
    ch1 = next(c for c in chapters if c["num"] == 1)
    assert "q-clear" in [qid for qid, _ in ch1["opens"]]
    assert "q-clear" in ch1["carries"]


EMPTY_CHAPTER_STORY = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie @simon #crime-and-first-contradiction

- Tom rules it out.
  @tom
"""

EMPTY_CHAPTER_PLAN = """## Chapter 01 — Opening

- **Beats:** 1
- **Summary:** Setup.
- **Compress:** N/A.

## Chapter 02 — Interlude

- **Summary:** A breather chapter with no beats of its own.
- **Compress:** N/A.

## Chapter 03 — Payoff

- **Beats:** 2-3
- **Summary:** Payoff.
- **Compress:** N/A.
"""


def test_strands_so_far_survives_an_empty_middle_chapter():
    # Chapter 02 has no **Beats:** field at all (parse_cut_plan leaves
    # ch["beats"] == []). The old `max(ch["beats"], default=0)` reset the
    # accumulator to nothing for this chapter, under-reporting who the
    # reader has met; the fix is a running high-water mark across chapters.
    out = emit_outline(EMPTY_CHAPTER_STORY, EMPTY_CHAPTER_PLAN, {}, {},
                       reveal_chapter=3, guardrails="No spoilers.", job_titles={})
    ch2 = parse_packet_sections(chapter_block(out, 2))["Character Knowledge"]
    assert "maggie" in ch2


ORPHAN_STORY = """- Beat one.
  @a

- Beat two, never placed in any chapter.
  @a +q-orphan
"""

ORPHAN_PLAN = """## Chapter 01 — Only Chapter

- **Beats:** 1
- **Summary:** Just the one beat.
- **Compress:** N/A.
"""


def test_orphan_beat_question_is_never_read_as_carried():
    # Beat 2 (which opens q-orphan) is claimed by no chapter, so
    # beat_chapter.get(2, 0) == 0. The old code still recorded opened_by
    # for it under the sentinel chapter 0, which made `opened_at <=
    # upto_index` trivially true from chapter 1 onward — an orphan open read
    # as carried everywhere. The fix skips questions whose owning chapter
    # resolves to 0 entirely.
    out = emit_outline(ORPHAN_STORY, ORPHAN_PLAN, {}, {},
                       reveal_chapter=1, guardrails="No spoilers.", job_titles={})
    assert "q-orphan" not in out


# --- FINAL REVIEW, Critical 2: the Hook was emitted only when a chapter
# OPENED a question, so `tension_check` reported `broken-hook: ch NN Hook does
# not lead with a question id` on every chapter that merely carried one — on a
# real 11-chapter cut, nine of eleven. Every cut book therefore reached
# `preflight lock-mystery` needing a blanket `--waive broken-hook`, which
# disables the check for the whole book. ---

HOOK_STORY = """- Beat one.
  @a +q-live

- Beat two — this chapter opens nothing of its own.
  @a

- Beat three closes it.
  @a -q-live

## Questions
- q-live — will it hold?
"""

HOOK_PLAN = """## Chapter 01 — Opens

- **Beats:** 1
- **Summary:** s
- **Compress:** c

## Chapter 02 — Carries Only

- **Beats:** 2
- **Summary:** s
- **Compress:** c

## Chapter 03 — Closes

- **Beats:** 3
- **Summary:** s
- **Compress:** c
"""


def _hook_emit():
    return emit_outline(HOOK_STORY, HOOK_PLAN, parse_questions(HOOK_STORY), {},
                        reveal_chapter=3, guardrails="g", job_titles={})


def test_a_chapter_that_only_carries_a_question_still_gets_a_hook():
    ch2 = next(c for c in parse_wired_chapters(_hook_emit()) if c["num"] == 2)
    assert not ch2["opens"]
    assert ch2["hook_q"] == "q-live"


def test_the_hook_prefers_a_question_this_chapter_opens():
    ch1 = next(c for c in parse_wired_chapters(_hook_emit()) if c["num"] == 1)
    assert ch1["hook_q"] == "q-live"
    assert "q-live" in [q for q, _ in ch1["opens"]]


def test_the_hook_never_names_a_question_this_chapter_closes():
    # `tension_check`'s third broken-hook branch: a hook naming a question
    # already closed by this chapter is as broken as no hook at all. Chapter 03
    # closes the only live question, so it has nothing legitimate to hook —
    # emitting the closed one would be worse than emitting none.
    ch3 = next(c for c in parse_wired_chapters(_hook_emit()) if c["num"] == 3)
    assert ch3["hook_q"] != "q-live"


def test_qline_does_not_truncate_prose_ending_in_a_dash():
    # The old `.rstrip(" —")` stripped trailing dash/space characters from
    # the whole rendered "qid — prose" string, so legitimate prose ending in
    # an em dash (or a trailing space) got silently truncated.
    questions = {"q-clear": "how can Maggie clear herself —"}
    out = emit_outline(STORY, PLAN, questions, LEDGER,
                       reveal_chapter=2, guardrails="Do not name the culprit early.",
                       job_titles=JOB_TITLES)
    assert "q-clear — how can Maggie clear herself —" in out
