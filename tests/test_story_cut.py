from scripts.story_cut import check_story

JOBS = ["establish-protected-world", "crime-and-first-contradiction"]
CLUES = ["c-altered", "c-vase"]

GOOD_STORY = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie #crime-and-first-contradiction +q-clear !c-altered

- The vase is wrong.
  @maggie !c-vase -q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""

GOOD_PLAN = """## Chapter 01 — One

- **Beats:** 1-2
- **Summary:** s
- **Compress:** c

## Chapter 02 — Two

- **Beats:** 3
- **Summary:** s
- **Compress:** c
"""


def _ids(findings):
    return sorted(f.split(":")[0] for f in findings)


def test_clean_story_and_plan_produce_no_findings():
    r = check_story(GOOD_STORY, GOOD_PLAN, JOBS, CLUES)
    assert r["blocking"] == []


def test_unknown_job_is_named():
    story = GOOD_STORY.replace("#establish-protected-world", "#invented-job")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert _ids(r["blocking"]) == ["unknown-job"]
    assert "invented-job" in r["blocking"][0]


def test_unknown_clue_is_named():
    story = GOOD_STORY.replace("!c-vase", "!c-ghost")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unknown-clue" in _ids(r["blocking"])


def test_unscheduled_clue_is_named_when_no_beat_plants_it():
    story = GOOD_STORY.replace(" !c-vase", "")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unscheduled-clue" in _ids(r["blocking"])
    assert "c-vase" in " ".join(r["blocking"])


def test_orphan_question_when_closed_without_opening():
    story = GOOD_STORY.replace("+q-clear", "")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "orphan-question" in _ids(r["blocking"])


def test_unknown_question_when_absent_from_questions_block():
    story = GOOD_STORY.replace("- q-clear — how can Maggie clear herself?", "")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unknown-question" in _ids(r["blocking"])


def test_beats_without_chapter_when_plan_misses_a_beat():
    plan = GOOD_PLAN.replace("- **Beats:** 3", "- **Beats:** 2")
    r = check_story(GOOD_STORY, plan, JOBS, CLUES)
    assert "beats-without-chapter" in _ids(r["blocking"])
    assert "3" in " ".join(r["blocking"])


def test_unknown_strand_when_slug_contract_is_broken():
    story = GOOD_STORY.replace("@maggie", "@Maggie", 1)
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unknown-strand" in _ids(r["blocking"])
    assert "Maggie" in " ".join(r["blocking"])


def test_a_beat_claimed_by_two_chapters_is_named():
    plan = GOOD_PLAN.replace("- **Beats:** 3", "- **Beats:** 2-3")
    r = check_story(GOOD_STORY, plan, JOBS, CLUES)
    assert "duplicate-beat" in _ids(r["blocking"])


def test_beat_index_zero_is_named():
    plan = GOOD_PLAN.replace("- **Beats:** 1-2", "- **Beats:** 0,1-2")
    r = check_story(GOOD_STORY, plan, JOBS, CLUES)
    assert "beats-without-chapter" in _ids(r["blocking"])
    assert "0" in " ".join(r["blocking"])


def test_same_beat_open_and_close_is_not_orphaned():
    # Insert the same-beat open+close beat BEFORE "## Questions" — appending
    # after it would land the new beat inside the Questions block itself,
    # where parse_story stops collecting beats.
    story = GOOD_STORY.replace(
        "## Questions",
        "- Same beat opens and closes.\n  @maggie +q-x -q-x\n\n## Questions")
    story = story.replace(
        "- q-clear — how can Maggie clear herself?",
        "- q-clear — how can Maggie clear herself?\n- q-x — same-beat sanity check")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "orphan-question" not in _ids(r["blocking"])


# --- FINAL REVIEW, Important 3: `dropped-question` is unreachable on a cut
# outline. The emitter carries every live question into every chapter through
# the last one, and `tension_check._graph_checks` treats carried-at-the-end as
# deliberate — so a question opened and never closed was caught by nothing.
# `check_story` had `orphan-question` (close without open) and no converse. ---

def _story_with_unclosed(*qids):
    """GOOD_STORY plus one extra beat opening each of `qids` and closing none."""
    opens = " ".join(f"+{q}" for q in qids)
    prose = "\n".join(f"- {q} — dangling" for q in qids)
    story = GOOD_STORY.replace(
        "## Questions",
        f"- A beat that opens and never closes.\n  @maggie {opens}\n\n## Questions")
    return story.replace("- q-clear — how can Maggie clear herself?",
                         f"- q-clear — how can Maggie clear herself?\n{prose}")


def test_two_questions_opened_and_never_closed_are_named():
    r = check_story(_story_with_unclosed("q-seed", "q-forgotten"), GOOD_PLAN,
                    JOBS, CLUES)
    assert "unclosed-question" in _ids(r["blocking"])
    joined = " ".join(r["blocking"])
    assert "q-seed" in joined and "q-forgotten" in joined


def test_one_unclosed_question_is_the_books_seed_and_is_allowed():
    # Not leniency: the wiring format REQUIRES it. Every chapter must hook a
    # question open at it (tension_check's broken-hook), and the final chapter
    # can only hook something the book has not closed — which is exactly the
    # shape tests/fixtures/outlines/wired-clean.md ends on.
    r = check_story(_story_with_unclosed("q-seed"), GOOD_PLAN, JOBS, CLUES)
    assert "unclosed-question" not in _ids(r["blocking"])


def test_a_fully_closed_story_is_told_its_last_chapter_will_have_no_hook():
    # Advisory, never blocking: check_story's notes channel. The showrunner
    # should not discover this only when preflight lock-mystery refuses.
    r = check_story(GOOD_STORY, GOOD_PLAN, JOBS, CLUES)
    assert r["blocking"] == []
    assert any("broken-hook" in n for n in r["notes"])


def test_tension_check_cannot_see_an_unclosed_question_on_a_cut_outline():
    """The reason the refusal has to live here: proof that the downstream
    checker is blind to it.

    Emit an outline from a story that opens a question and never closes it, and
    run the real `tension_check` over it — `dropped-question` never fires,
    because the emitter's `Carries:` line makes every dangling question look
    deliberate. Nothing downstream of `check_story` can tell the difference.
    """
    from scripts.penny_story import parse_questions
    from scripts.story_cut import emit_outline
    from scripts.tension_check import check_tension

    story = _story_with_unclosed("q-seed", "q-forgotten")
    plan = GOOD_PLAN.replace("- **Beats:** 3", "- **Beats:** 3-4")
    outline = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=2, guardrails="g", job_titles={})
    assert "q-forgotten" in outline  # it really is in the emitted wiring

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "outline.md"
        p.write_text(outline, encoding="utf-8")
        result = check_tension(p)
    assert result["wired"]
    assert not [b for b in result["blocking"] if b.startswith("dropped-question")]
    # ...while check_story, which CAN see it, refuses by name.
    assert "unclosed-question" in _ids(check_story(story, plan, JOBS, CLUES)["blocking"])
