# tests/test_story_cut_roundtrip.py
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
                           reveal_chapter=24, guardrails="g", job_titles={})
    for ch in parse_wired_chapters(emitted):
        sections = parse_packet_sections(chapter_block(emitted, ch["num"]))
        for name in REQUIRED_SECTIONS:
            assert name in sections, f"chapter {ch['num']} lost {name}"


def test_every_beat_survives_the_round_trip_in_order():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={})
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
                           reveal_chapter=24, guardrails="g", job_titles={})
    assert ([(c["num"], c["title"]) for c in parse_wired_chapters(emitted)]
            == [(c["num"], c["title"]) for c in parse_wired_chapters(outline)])
