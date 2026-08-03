# tests/test_story_cut_roundtrip.py
import re
from pathlib import Path

from scripts.penny_wiring import (chapter_block, parse_packet_sections,
                                  parse_required_beats, parse_wired_chapters)
from scripts.penny_story import parse_questions
from scripts.story_cut import emit_outline

FIXTURE = Path(__file__).parent / "fixtures" / "story" / "book-01-excerpt.outline.md"

REQUIRED_SECTIONS = ["Chapter Summary", "Chapter Purpose", "Starting State",
                     "Ending State", "Reader-Facing Shape", "Required Beats",
                     "Clues and Plants", "Character Knowledge", "Guardrails",
                     "Chapter Structure", "Track Movement"]


def _story_and_plan_from(outline_text):
    """Derive beats and a cut plan from a real outline — the lossy direction,
    used here only to build a test input, never as a source (spec §11)."""
    story_lines, plan_lines, n = [], [], 0
    for ch in parse_wired_chapters(outline_text):
        block = chapter_block(outline_text, ch["num"])
        beats = parse_required_beats(parse_packet_sections(block))
        first = n + 1
        for b in beats:
            n += 1
            story_lines.append(f"- {b}\n")
        plan_lines.append(
            f"## Chapter {ch['num']:02d} — {ch['title']}\n\n"
            f"- **Beats:** {first}-{n}\n- **Summary:** s\n- **Compress:** c\n"
            f"- **M:** m\n")
    return "\n".join(story_lines), "\n".join(plan_lines)


def test_emitted_blocks_carry_every_section_the_engine_parses():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={},
                           solution={})
    for ch in parse_wired_chapters(emitted):
        sections = parse_packet_sections(chapter_block(emitted, ch["num"]))
        for name in REQUIRED_SECTIONS:
            assert name in sections, f"chapter {ch['num']} lost {name}"


def test_every_beat_survives_the_round_trip_in_order():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={},
                           solution={})
    original = [b for ch in parse_wired_chapters(outline)
                for b in parse_required_beats(
                    parse_packet_sections(chapter_block(outline, ch["num"])))]
    produced = [b for ch in parse_wired_chapters(emitted)
                for b in parse_required_beats(
                    parse_packet_sections(chapter_block(emitted, ch["num"])))]
    assert produced == original


def test_chapter_count_and_titles_are_preserved():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={},
                           solution={})
    assert ([(c["num"], c["title"]) for c in parse_wired_chapters(emitted)]
            == [(c["num"], c["title"]) for c in parse_wired_chapters(outline)])


# --- FINAL REVIEW, Important 8 (second half): this file is the spec's
# "load-bearing" proof that the emitter is faithful, but every case above
# builds its story from an outline stripped of tags — no @strand, no #job, no
# +q/-q, no !clue — and none of them ever hands the emitted outline to
# `tension_check`. That is precisely why the wiring bugs (a missing chapter-1
# `Because`, a `Hook` emitted only when a chapter opened a question) survived
# twelve task reviews: nothing here exercised the wiring at all.
#
# So: one case with real tags, cut into real chapters, whose emitted outline is
# fed to the real checker and must come back CLEAN — no findings, no waivers.

TAGGED_STORY = """- Maggie arrives; the town GP is found dead.
  @maggie @neil #establish-protected-world +q-who !clue-erasure

- Mary's kindness has edges; the tin comes back, the papers do not.
  @mary #initial-suspect-field +q-mary

- The kiln-room key vanishes.
  @maggie @cal #suspect-encounters +q-key !rh-cal

- The key returns; Artie says too much.
  @artie #real-red-herrings -q-key +q-artie

- The kitchen truth: Mary, the letter, the mercy mistaken for murder.
  @mary @maggie #expose-killer -q-who -q-mary

- Order returns, warmer and more honest.
  @maggie #restore-world

## Questions
- q-who — who killed the town GP?
- q-mary — why does Mary guard the workshop papers?
- q-key — who took the kiln-room key?
- q-artie — what does Artie know about the Too-Much?
"""

TAGGED_PLAN = "".join(
    f"## Chapter {n:02d} — Chapter {n}\n\n"
    f"- **Beats:** {n}\n"
    f"- **Summary:** What chapter {n} is.\n"
    f"- **Compress:** Something specific to chapter {n}.\n"
    f"- **M:** The mystery moves.\n- **P:** The personal moves.\n"
    f"- **R:** The relationship moves.\n- **B:** The business moves.\n\n"
    for n in range(1, 7))

TAGGED_LEDGER = {"clue-erasure": "the erased line in the appointment book",
                 "rh-cal": "Cal's blue-green car in the timeline gap"}

TAGGED_QUESTIONS = parse_questions(TAGGED_STORY)

# Deliberately carries no `true_motive` key at all — the covering test below
# asserts the emitter omits that bullet rather than writing it empty.
TAGGED_SOLUTION = {
    "culprit": "mary",
    "victim": "neil",
    "central_deception": "Mary believed for a decade her father was murdered.",
    "murder_method": "poison in the evening tea",
    "murder_location": "the pottery studio kiln room",
    "alibi_grid": [
        {"suspect": "mary", "chapter": 7, "alibi": "dismissed as harmless grieving",
         "holds": False},
        {"suspect": "cal", "chapter": 11, "alibi": "independently accounted",
         "holds": True},
    ],
}


def _tagged_outline():
    from scripts.story_cut import emit_outline as emit
    return emit(TAGGED_STORY, TAGGED_PLAN, TAGGED_QUESTIONS, TAGGED_LEDGER,
                reveal_chapter=5, guardrails="Stay in Maggie's POV.",
                job_titles={}, solution=TAGGED_SOLUTION)


def test_the_emitted_outline_passes_tension_check_clean(tmp_path):
    """The whole point: a cut book must reach `preflight lock-mystery` needing
    NO waivers. Run the real checker, with the real genre beat sheet, over the
    real emitted text."""
    from scripts.tension_check import check_tension

    outline = tmp_path / "outline.md"
    outline.write_text(_tagged_outline(), encoding="utf-8")
    whodunit = tmp_path / "book-99.yaml"
    whodunit.write_text(
        "reveal_chapter: 5\n"
        "clue_schedule:\n  - { id: clue-erasure, plant_chapter: 1 }\n"
        "red_herrings:\n  - { id: rh-cal, plant_chapter: 3 }\n", encoding="utf-8")
    beat_sheet = Path("genres/cozy-mystery/beat-sheet.yaml")

    result = check_tension(outline, beat_sheet_path=beat_sheet,
                           whodunit_path=whodunit)
    assert result["wired"], "the emitted outline must carry wiring at all"
    assert result["blocking"] == []


def test_every_chapter_of_a_tagged_cut_has_a_because_and_a_hook():
    # The two literals tension_check refuses without. Asserted directly as well
    # as through the checker above, so a future change to check_tension cannot
    # quietly take this coverage away with it.
    chapters = parse_wired_chapters(_tagged_outline())
    assert len(chapters) == 6
    assert chapters[0]["because"] == "opening"
    for c in chapters:
        assert c["because"], f"ch {c['num']} has no Because"
        assert c["hook_q"], f"ch {c['num']} has no hook question id"


def test_a_tagged_cut_places_every_clue_in_the_chapter_its_beat_landed_in():
    from scripts.penny_wiring import chapter_block as blk
    out = _tagged_outline()
    assert "clue-erasure" in parse_packet_sections(blk(out, 1))["Clues and Plants"]
    assert "rh-cal" in parse_packet_sections(blk(out, 3))["Clues and Plants"]
    # ...and nowhere else
    assert out.count("[clue-erasure]") == 1
    assert out.count("[rh-cal]") == 1


# --- Solution-block coverage (spec §5.2 table gap): the cut emitted chapter
# blocks but no `## Solution` block, so `outline_check`'s `outline-solution`
# predicate failed on every cut book forever — /book-status showed the
# outline row red even with the mystery locked and packets built. ---

def test_solution_block_carries_culprit_victim_and_suspects():
    out = _tagged_outline()
    assert "## Solution" in out
    # Before the first chapter block, not after it.
    assert out.index("## Solution") < out.index("## Chapter 01")
    assert "- culprit: mary" in out
    assert "- victim: neil" in out
    assert "- suspects: mary, cal" in out


def test_solution_block_omits_a_bullet_whose_ledger_key_is_missing():
    # TAGGED_SOLUTION carries no `true_motive` key at all. The old
    # implementation this guards against would be one that writes
    # "- true motive: " with nothing after the colon instead of skipping the
    # bullet outright.
    out = _tagged_outline()
    assert "true motive" not in out
    assert not re.search(r"^- [a-z ]+:\s*$", out, re.MULTILINE)


def test_the_emitted_outline_passes_outline_check_cleanly(tmp_path):
    """The assertion that actually closes the finding: /book-status's outline
    row reads red-forever on a cut book because `outline_check.check_outline`
    blocks on `outline-solution` with no `## Solution` block present. Run the
    real checker over real emitted (and stamped) output, not a hand-written
    fixture."""
    from scripts.outline_check import check_outline
    from scripts.story_cut import stamp_outline

    body = _tagged_outline()
    full = stamp_outline(body, story_sha="a" * 64, cut_sha="b" * 64,
                         book="99", total_chapters=6)
    outline = tmp_path / "outline.md"
    outline.write_text(full, encoding="utf-8")

    result = check_outline(outline)
    assert result["blocking"] == []
