from pathlib import Path

from scripts.outline_check import check_outline, main
from scripts.penny_wiring import parse_wired_chapters

FIX = Path("tests/fixtures/outlines")


def _predicates(result):
    return [b.split(":", 1)[0] for b in result["blocking"]]


def test_well_formed_has_no_blockers():
    result = check_outline(FIX / "well-formed.md")
    assert result["blocking"] == []


def test_well_formed_main_exits_zero():
    assert main([str(FIX / "well-formed.md")]) == 0


def test_missing_solution_fails_named_predicate():
    result = check_outline(FIX / "missing-solution.md")
    assert "outline-solution" in _predicates(result)


def test_chapter_gap_fails_contiguity():
    result = check_outline(FIX / "chapter-gap.md")
    assert "outline-chapters-contiguous" in _predicates(result)


def test_non_int_count_fails_frontmatter():
    result = check_outline(FIX / "non-int-count.md")
    assert "outline-frontmatter" in _predicates(result)


def test_empty_beat_fails_nonempty_beats():
    result = check_outline(FIX / "empty-beat.md")
    assert "outline-nonempty-beats" in _predicates(result)


def test_main_exits_nonzero_on_broken():
    assert main([str(FIX / "missing-solution.md")]) == 1


def test_shipped_template_is_well_formed():
    result = check_outline(Path("config/outline-template.md"))
    assert result["blocking"] == []


def test_empty_solution_label_fails_outline_solution():
    result = check_outline(FIX / "empty-solution-label.md")
    assert "outline-solution" in _predicates(result)


def test_unlabeled_solution_is_valid():
    result = check_outline(FIX / "unlabeled-solution.md")
    assert result["blocking"] == []


def test_chapter_headings_with_titles_are_valid():
    result = check_outline(FIX / "well-formed-titled.md")
    assert result["blocking"] == []


def test_shipped_template_teaches_syntax_the_wiring_parser_accepts():
    """Contract test: the template is documentation, but its Chapter 01 example
    must be real, parseable syntax — not merely prose that LOOKS like the fields
    scripts/penny_wiring.py reads. A doc that teaches a form the parser silently
    ignores (the exact failure a prior task shipped for `- **Weight:**`) is worse
    than no doc at all, so this asserts the fields actually resolve.

    Post packet/map redesign (spec 2026-07-18 §3): the template's chapter blocks
    are packet format, not scene-breakdown — there is no `### Scene` section to
    round-trip any more (scenes moved to the per-chapter map). The contract now
    pins the packet-format shape instead: a real, non-empty Required Beats list
    and real, non-empty packet `###` sections, both read through
    `parse_wired_chapters` exactly as `packet_assemble.py` reads them.
    """
    text = Path("config/outline-template.md").read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)

    ch1 = next(c for c in chapters if c["num"] == 1)
    # The title flag must sit after the em-dash and still resolve to a band name.
    assert ch1["chapter_type"] == "opening"
    # "First line:" is its own field, distinct from "Opens:" (story questions).
    assert ch1["first_line"]
    # The hook grade is read from the front of the Hook field's value.
    assert ch1["hook_grade"] == "cliffhanger"
    # No "### Scene" section survives in packet format.
    assert ch1["scenes"] == []
    # The packet-format sections and Required Beats list both resolve non-empty.
    assert ch1["sections"], "template must teach real packet-format ### sections"
    assert ch1["required_beats"], "template must teach a non-empty Required Beats list"
    assert "Required Beats" in ch1["sections"]
