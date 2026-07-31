from pathlib import Path

import pytest

from scripts import outline_views

FIXTURE = Path("tests/fixtures/outlines/views-sample.md")


@pytest.fixture
def text():
    return FIXTURE.read_text(encoding="utf-8")


def test_iter_chapters_yields_number_title_block_in_order(text):
    got = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    assert got == [(1, "The Arrival"), (2, "The Body"),
                   (3, "Quiet Rooms"), (4, "Tara")]


def test_iter_chapters_block_carries_the_sections(text):
    blocks = {n: b for n, _t, b in outline_views.iter_chapters(text)}
    assert "### Chapter Summary" in blocks[1]
    assert "### Chapter Summary" not in blocks[4]


def test_glance_carries_every_chapter_heading(text):
    out = outline_views.glance(text)
    assert "## 01 — The Arrival" in out
    assert "## 04 — Tara" in out


def test_glance_carries_summary_prose(text):
    out = outline_views.glance(text)
    assert "Maggie finds Lisa dead at the wheel" in out


def test_glance_names_a_missing_summary_rather_than_dropping_it(text):
    out = outline_views.glance(text)
    assert "*(no summary)*" in out


def test_glance_omits_required_beats(text):
    """The glance is summaries only — beats are the outline's noise, not signal."""
    out = outline_views.glance(text)
    assert "Simon mentions a scheduling irregularity" not in out


def test_name_tokens_splits_a_hyphenated_slug():
    assert outline_views.name_tokens("tara-marion") == ["tara", "marion"]
    assert outline_views.name_tokens("simon") == ["simon"]


def test_strand_collects_chapters_naming_the_character_in_order(text):
    hits = outline_views.strand(text, "simon")
    assert [n for n, _line in hits] == [1, 1]


def test_strand_matches_whole_words_only(text):
    """'Simone' at the surf club must not land in Simon's strand — a substring
    match would put another character's action on his page and invent a hole."""
    lines = [line for _n, line in outline_views.strand(text, "simon")]
    assert not any("surf club" in line for line in lines)


def test_strand_matches_any_token_of_a_hyphenated_slug(text):
    hits = outline_views.strand(text, "tara-marion")
    assert [n for n, _line in hits] == [4]


def test_strand_omits_chapters_that_never_name_the_character(text):
    assert 3 not in [n for n, _line in outline_views.strand(text, "simon")]


def test_strand_returns_empty_for_an_absent_character(text):
    assert outline_views.strand(text, "george") == []


def test_render_strand_shows_chapter_numbers(text):
    out = outline_views.render_strand("simon", outline_views.strand(text, "simon"))
    assert "simon" in out.lower()
    assert "ch 01" in out


def test_strand_raises_on_empty_slug(text):
    """A degenerate slug yields no tokens and would match every line — fail loud."""
    with pytest.raises(ValueError, match="strand: slug '' yields no name tokens"):
        outline_views.strand(text, "")


def test_strand_raises_on_hyphens_only_slug(text):
    """Hyphens alone split to empty tokens — fail loud, not silently."""
    with pytest.raises(ValueError, match="strand: slug '-' yields no name tokens"):
        outline_views.strand(text, "-")
    with pytest.raises(ValueError, match="strand: slug '--' yields no name tokens"):
        outline_views.strand(text, "--")


def test_parse_jobs_reads_ids_in_file_order():
    from scripts import penny_genre
    path = penny_genre.macro_structure()
    if path is None:                      # engine repo has no declared genre
        path = Path("genres/cozy-mystery/review-rubrics/macro-structure.md")
    jobs = outline_views.parse_jobs(Path(path).read_text(encoding="utf-8"))
    assert len(jobs) == 28
    assert jobs[0] == ("establish-protected-world", "Establish the Protected World")
    assert jobs[9][0] == "plant-fair-play-solution"
    assert jobs[27] == ("restore-world", "Restore the World")


def test_parse_jobs_ignores_a_heading_with_no_marker():
    text = "## 1. Titled\n<!-- job: titled -->\n\n## 2. Unmarked\n\nbody\n"
    assert outline_views.parse_jobs(text) == [("titled", "Titled")]
