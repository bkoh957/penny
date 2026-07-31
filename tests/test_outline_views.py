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
