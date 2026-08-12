from scripts import story_cut
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
                           reveal_chapter=2, guardrails="g", job_titles={},
                           solution={})
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


_JOBS = ["establish-protected-world", "act-iii-apparent-defeat"]
_CLUES = ["c-altered"]

_BASE = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The firing fails in front of the town.
  @maggie #act-iii-apparent-defeat +q-clear -q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""


def _findings(extra):
    return check_story(_BASE + extra, "", _JOBS, _CLUES)["blocking"]


def test_orphan_direction_names_a_strand_no_beat_uses():
    out = _findings("\n## Guardrails\n- Never soften her. @susan\n")
    assert any(f.startswith("orphan-direction:") and "@susan" in f for f in out)


def test_a_job_the_genre_does_not_declare_is_unknown_job_in_a_directive():
    out = _findings("\n## Chapter Direction\n- Give it room. #restore-world\n")
    assert any("unknown-job:" in f for f in out)


def test_a_typoed_strand_in_a_directive_is_refused_by_name():
    out = _findings("\n## Chapter Direction\n- Watch her. @Maggie\n")
    assert any(f.startswith("unknown-strand:") for f in out)


def test_orphan_direction_fires_for_a_declared_job_no_beat_carries():
    out = check_story(
        _BASE + "\n## Guardrails\n- Give it room. #restore-world\n",
        "", _JOBS + ["restore-world"], _CLUES)["blocking"]
    assert any(f.startswith("orphan-direction:") and "#restore-world" in f
               for f in out)


def test_misplaced_schedule_tag_refuses_clue_and_question_tags():
    for tag in ("!c-altered", "+q-clear", "-q-clear"):
        out = _findings(f"\n## Guardrails\n- A note. {tag}\n")
        assert any(f.startswith("misplaced-schedule-tag:") for f in out), tag


def test_a_scoped_directive_matching_a_used_tag_is_clean():
    out = _findings("\n## Guardrails\n- Never soften her. @maggie\n"
                    "- Book-wide, untagged.\n")
    assert not [f for f in out if "direction" in f or "schedule-tag" in f]


# --- FINAL REVIEW, Minor 6: the tag capture is deliberately loose, and
# guardrail prose is English sentences, so it bites here far more often than on
# beats. The message must name the token it objected to — `unknown-job`'s
# already does. ---

def test_misplaced_schedule_tag_quotes_the_offending_token():
    # "-- never" harvests as a close tag with slug "-". Without the token in
    # the message the author is told a guardrail carries a +q/-q/!clue tag and
    # cannot see which characters caused it.
    out = _findings("\n## Guardrails\n- Never soften her -- never arch. @maggie\n")
    hits = [f for f in out if f.startswith("misplaced-schedule-tag:")]
    assert hits
    assert "'--'" in hits[0], hits[0]


def test_misplaced_schedule_tag_quotes_a_real_clue_tag_too():
    out = _findings("\n## Guardrails\n- A note. !c-altered\n")
    hits = [f for f in out if f.startswith("misplaced-schedule-tag:")]
    assert hits and "'!c-altered'" in hits[0], hits


# --- FINAL REVIEW, Important 2: the emitter writes `- {text}` verbatim into the
# chapter block, and penny_wiring matches FIELD_RE/TRACK_RE against EVERY line
# of that block — not only the wiring section. So authored guardrail prose
# shaped like a wiring field forges the deterministic layer's own output:
# `- **Closes:** q-bogus` passed check_story clean and made tension_check fire
# phantom-answer on a chapter whose wiring footer never said any such thing. ---

def test_a_guardrail_shaped_like_a_wiring_field_is_refused():
    out = _findings("\n## Guardrails\n- **Closes:** q-clear\n")
    assert any(f.startswith("wiring-shaped-directive:") for f in out), out


def test_a_guardrail_shaped_like_a_track_row_is_refused():
    out = _findings("\n## Guardrails\n- **M:** Keep the murder track warm.\n")
    assert any(f.startswith("wiring-shaped-directive:") for f in out), out


def test_every_wiring_field_name_is_refused_in_a_directive():
    for field in ("Because", "Opens", "Closes", "Carries", "Hook"):
        out = _findings(f"\n## Guardrails\n- **{field}:** q-clear\n")
        assert any(f.startswith("wiring-shaped-directive:") for f in out), field


def test_chapter_direction_lines_are_held_to_the_same_shape_rule():
    out = _findings("\n## Chapter Direction\n- **Hook:** q-clear\n")
    assert any(f.startswith("wiring-shaped-directive:") for f in out), out


def test_ordinary_bold_prose_in_a_guardrail_is_not_wiring_shaped():
    # The refusal is about the wiring FIELD shape, not about bold text — an
    # author emphasising a word must stay legal.
    out = _findings("\n## Guardrails\n- **Never** soften her. @maggie\n")
    assert not [f for f in out if f.startswith("wiring-shaped-directive:")], out


def test_the_forged_wiring_line_really_would_parse_as_wiring():
    # Why the refusal has to exist: proof that the emitted block is read by
    # penny_wiring as if the wiring footer had said it.
    from scripts.penny_story import parse_questions
    from scripts.penny_wiring import parse_wired_chapters
    from scripts.story_cut import emit_outline

    story = GOOD_STORY.replace(
        "## Questions", "## Guardrails\n- **Closes:** q-ghost\n\n## Questions")
    out = emit_outline(story, GOOD_PLAN, parse_questions(story), {},
                       reveal_chapter=2, guardrails="g", job_titles={},
                       solution={})
    assert any("q-ghost" in c["closes"] for c in parse_wired_chapters(out))
    # ...and check_story refuses the story before it can ever be emitted.
    assert any(f.startswith("wiring-shaped-directive:")
               for f in check_story(story, GOOD_PLAN, JOBS, CLUES)["blocking"])


def test_directive_shaped_beat_is_advised_not_blocked():
    story = (
        "- Plant only the visible contradiction: a glimpse suggests Lisa met\n"
        "  someone she treated as Maggie.\n  @maggie\n\n"
        "- Maggie finds Lisa dead at the wheel.\n  @maggie\n"
    )
    r = check_story(story, "", JOBS, [])
    assert not [f for f in r["blocking"] if "directive-shaped-beat" in f]
    advisories = [n for n in r["notes"] if "directive-shaped-beat" in n]
    assert len(advisories) == 1
    assert "beat 1" in advisories[0]


def test_every_opener_in_the_closed_list_is_advised():
    from scripts.story_cut import _DIRECTIVE_OPENERS
    for word in _DIRECTIVE_OPENERS:
        story = f"- {word} the thing that happens next.\n  @maggie\n"
        r = check_story(story, "", JOBS, [])
        assert [n for n in r["notes"] if "directive-shaped-beat" in n], word


def test_ordinary_beats_containing_those_words_are_silent():
    story = (
        "- Maggie lets the kiln cool before she opens it.\n  @maggie\n\n"
        "- Faye keeps the corner table free all morning.\n  @faye\n\n"
        "- Tom makes a joke about the surf-club minutes.\n  @tom\n"
    )
    r = check_story(story, "", JOBS, [])
    assert not [n for n in r["notes"] if "directive-shaped-beat" in n]


def test_advisory_names_the_block_the_note_probably_wants():
    story = "- Do not reveal the impostor here.\n  @maggie\n"
    r = check_story(story, "", JOBS, [])
    note = [n for n in r["notes"] if "directive-shaped-beat" in n][0]
    assert "## Guardrails" in note


# --- beat numbering (optional `- [n]` prefix) -------------------------------

_NUMBERED = """---
book: 01
---
## Act I
- [1] Maggie arrives. @maggie
- [2] She finds a body. @maggie

## Guardrails
- Never name the culprit early.
"""


def test_beat_number_is_parsed_and_stripped_from_prose():
    beats = story_cut.parse_story(_NUMBERED)
    assert [b["num"] for b in beats] == [1, 2]
    # the number must NOT survive into the text, or it reaches the drafter's packet
    assert beats[0]["text"] == "Maggie arrives."


def test_unnumbered_story_still_parses_with_num_none():
    beats = story_cut.parse_story(_NUMBERED.replace("[1] ", "").replace("[2] ", ""))
    assert [b["num"] for b in beats] == [None, None]
    assert beats[0]["text"] == "Maggie arrives."


def test_bare_leading_number_is_not_a_beat_number():
    text = _NUMBERED.replace("[1] Maggie arrives.", "1987 was the year of the flood.")
    beats = story_cut.parse_story(text)
    assert beats[0]["num"] is None
    assert beats[0]["text"] == "1987 was the year of the flood."


def test_misnumbered_beat_blocks():
    text = _NUMBERED.replace("- [2] She finds", "- [7] She finds")
    findings = story_cut.check_story(text, "", [], [])["blocking"]
    assert any(f.startswith("misnumbered-beat") and "position 2" in f for f in findings)


def test_half_numbered_file_blocks():
    text = _NUMBERED.replace("- [2] She finds", "- She finds")
    findings = story_cut.check_story(text, "", [], [])["blocking"]
    assert any(f.startswith("unnumbered-beat") for f in findings)


def test_fully_unnumbered_file_does_not_block_on_numbering():
    text = _NUMBERED.replace("[1] ", "").replace("[2] ", "")
    findings = story_cut.check_story(text, "", [], [])["blocking"]
    assert not any("numbered-beat" in f for f in findings)


def test_renumber_fixes_positions_and_is_idempotent():
    text = _NUMBERED.replace("- [1] Maggie arrives. @maggie",
                             "- [1] Maggie arrives. @maggie\n- [9] Inserted. @maggie")
    fixed = story_cut.renumber(text)
    assert [b["num"] for b in story_cut.parse_story(fixed)] == [1, 2, 3]
    assert story_cut.renumber(fixed) == fixed


def test_renumber_leaves_inert_block_bullets_alone():
    fixed = story_cut.renumber(_NUMBERED)
    assert "- Never name the culprit early." in fixed


def test_renumber_preserves_tags_and_prose():
    before = story_cut.parse_story(_NUMBERED)
    after = story_cut.parse_story(story_cut.renumber(_NUMBERED))
    assert [(b["text"], b["strands"], b["clues"]) for b in before] == \
           [(b["text"], b["strands"], b["clues"]) for b in after]


# --- ledger walk: zero-indent sequences (the shape yaml.safe_dump emits) ------

_ZERO_INDENT_LEDGER = """book: '01'
clue_schedule:
- id: c01-first
  plant_chapter: 3
  description: first.
- id: c02-second
  plant_chapter: 4
  description: second.
red_herrings:
- id: rh-one
  plant_chapter: 5
  description: herring.
alibi_grid:
- suspect: someone
  chapter: 9
"""


def test_item_spans_finds_sequence_items_at_the_headings_own_indent():
    """`clue_schedule:` followed by `- id:` at column 0 is legal YAML and is what
    safe_dump emits. Reading the first item as the block's end found zero items,
    so every clue reported not-found and the cut refused a partial update."""
    lines = _ZERO_INDENT_LEDGER.splitlines(keepends=True)
    heading = next(i for i, l in enumerate(lines) if l.startswith("clue_schedule:"))
    assert len(story_cut._item_spans(lines, heading, "")) == 2


def test_rewrite_plant_chapters_handles_zero_indent_ledger():
    new, missing = story_cut._rewrite_plant_chapters(
        _ZERO_INDENT_LEDGER, {"c01-first": 7, "rh-one": 8})
    assert missing == []
    assert "  plant_chapter: 7" in new
    assert "  plant_chapter: 8" in new
    assert "  plant_chapter: 4" in new          # untouched item survives
    assert "  chapter: 9" in new                # alibi_grid never reached


def test_zero_indent_walk_does_not_run_past_its_collection():
    """`red_herrings:`/`alibi_grid:` sit at the same indent as `clue_schedule:`;
    a non-item line at heading indent must still end the block."""
    lines = _ZERO_INDENT_LEDGER.splitlines(keepends=True)
    heading = next(i for i, l in enumerate(lines) if l.startswith("clue_schedule:"))
    spans = story_cut._item_spans(lines, heading, "")
    assert max(e for _, e, _ in spans) <= next(
        i for i, l in enumerate(lines) if l.startswith("red_herrings:"))


# --- chapter setting and frames (spec 2026-08-12 §5.1) -----

STORY = """\
# Story

- [1] Maggie opens the shop.
- [2] The tin turns up.
- [3] She walks to the harbour.
- [4] The light goes out.
"""


def _plan(body):
    return "## Chapter 01 — X\n- **Beats:** 1-4\n" + body


FRAME = ("- **Opening:** The kiln door still warm.\n"
         "- **Closing (cliffhanger):** The light goes out.\n")


def _blocking(plan):
    return check_story(STORY, plan, [], [])["blocking"]


def test_clean_plan_produces_none_of_the_new_findings():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n" + FRAME)
    assert not [b for b in _blocking(plan) if b.split(":")[0] in {
        "beat-without-setting", "overlapping-setting", "setting-outside-chapter",
        "missing-chapter-frame", "unknown-closing-kind"}]


def test_beat_without_setting_names_the_uncovered_beat():
    plan = _plan("- **Setting:**\n  - 1-3 — the shop, morning\n" + FRAME)
    assert any(b.startswith("beat-without-setting:") and "4" in b
               for b in _blocking(plan))


def test_overlapping_setting_fires_when_two_ranges_claim_one_beat():
    plan = _plan("- **Setting:**\n  - 1-3 — the shop, morning\n"
                 "  - 3-4 — the harbour, dusk\n" + FRAME)
    assert any(b.startswith("overlapping-setting:") and "3" in b
               for b in _blocking(plan))


def test_setting_outside_chapter_fires_on_a_beat_this_chapter_does_not_hold():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "  - 9 — the harbour, dusk\n" + FRAME)
    assert any(b.startswith("setting-outside-chapter:") and "9" in b
               for b in _blocking(plan))


def test_missing_chapter_frame_fires_once_per_missing_field():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n")
    found = [b for b in _blocking(plan) if b.startswith("missing-chapter-frame:")]
    assert len(found) == 2
    assert any("Opening" in b for b in found) and any("Closing" in b for b in found)


def test_unknown_closing_kind_names_the_three_valid_kinds():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "- **Opening:** The kiln door.\n"
                 "- **Closing (twist):** The light goes out.\n")
    hits = [b for b in _blocking(plan) if b.startswith("unknown-closing-kind:")]
    assert hits and "promise of action" in hits[0]


def test_a_plan_carrying_none_of_the_fields_is_pre_design_and_silent():
    plan = _plan("- **Summary:** s\n- **Compress:** c\n")
    assert not [b for b in _blocking(plan) if b.split(":")[0] in {
        "beat-without-setting", "overlapping-setting", "setting-outside-chapter",
        "missing-chapter-frame", "unknown-closing-kind"}]


# --- FINAL REVIEW, Minor: emit_outline writes Opening/Chapter Summary
# verbatim at column 0 and Compress with a bare "- " prefix it adds itself —
# the same forgery hazard as an authored Guardrail, just one level up (in
# the cut plan rather than story.md). ---

def test_a_wiring_shaped_opening_is_refused_by_name():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "- **Opening:** - **Closes:** q-bogus\n"
                 "- **Closing (cliffhanger):** The light goes out.\n")
    hits = [b for b in _blocking(plan) if b.startswith("wiring-shaped-directive:")]
    assert hits and "Opening" in hits[0], hits


def test_a_wiring_shaped_summary_is_refused_by_name():
    plan = _plan("- **Summary:** - **Because:** ch 01\n- **Compress:** c\n")
    hits = [b for b in _blocking(plan) if b.startswith("wiring-shaped-directive:")]
    assert hits and "Chapter Summary" in hits[0], hits


def test_a_wiring_shaped_compress_is_refused_by_name():
    # Compress gets its "- " prefix from the emitter itself, so the AUTHORED
    # value need not repeat it — "**Because:** ch 01" alone becomes
    # "- **Because:** ch 01" once emitted.
    plan = _plan("- **Summary:** s\n- **Compress:** **Because:** ch 01\n")
    hits = [b for b in _blocking(plan) if b.startswith("wiring-shaped-directive:")]
    assert hits and "Compress" in hits[0], hits


def test_the_forged_opening_really_would_parse_as_wiring():
    # Same proof as the guardrail case: the emitted block really is read by
    # penny_wiring as if the cut itself had written the wiring field.
    from scripts.penny_wiring import parse_wired_chapters
    from scripts.story_cut import emit_outline
    from scripts.penny_story import parse_questions

    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "- **Opening:** - **Closes:** q-bogus\n"
                 "- **Closing (cliffhanger):** The light goes out.\n")
    out = emit_outline(STORY, plan, parse_questions(STORY), {},
                       reveal_chapter=2, guardrails="g", job_titles={},
                       solution={})
    assert any("q-bogus" in c["closes"] for c in parse_wired_chapters(out))
    # ...and check_story refuses the plan before it can ever be emitted.
    assert any(b.startswith("wiring-shaped-directive:") for b in _blocking(plan))


def test_ordinary_opening_and_summary_prose_is_not_wiring_shaped():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "- **Summary:** She finds the tin.\n"
                 "- **Compress:** the walk to the harbour\n" + FRAME)
    assert not [b for b in _blocking(plan) if b.startswith("wiring-shaped-directive:")]


def test_adoption_is_all_or_nothing_across_the_whole_plan():
    plan = ("## Chapter 01 — X\n- **Beats:** 1-2\n"
            "- **Setting:**\n  - 1-2 — the shop, morning\n"
            "- **Opening:** The kiln door.\n"
            "- **Closing (irony):** She laughs.\n"
            "## Chapter 02 — Y\n- **Beats:** 3-4\n"
            "- **Summary:** s\n")
    found = [b for b in _blocking(plan) if b.startswith("missing-chapter-frame:")]
    assert len(found) == 2 and all("ch 02" in b for b in found)
    assert any(b.startswith("beat-without-setting:") and "ch 02" in b
               for b in _blocking(plan))
