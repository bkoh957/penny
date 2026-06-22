from pathlib import Path

from scripts.outline_check import check_outline, main

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
