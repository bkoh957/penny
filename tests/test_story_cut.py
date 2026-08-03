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
