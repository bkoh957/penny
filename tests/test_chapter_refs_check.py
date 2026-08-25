"""chapter_refs_check: the rules that survived, and the false positives they must not raise.

Written against the book-01 rot that motivated the checker — a 29->35 re-cut left
seventeen chapter references pointing at the wrong chapter, and the review panel
caught fewer than half of them.
"""
import textwrap
from pathlib import Path

import pytest

from scripts.chapter_refs_check import check


def _series(tmp_path, *, cut_plan, story, whodunit=None, book="01"):
    bd = tmp_path / "input" / f"book-{book}"
    bd.mkdir(parents=True)
    (bd / "cut-plan.md").write_text(textwrap.dedent(cut_plan), encoding="utf-8")
    (bd / "story.md").write_text(textwrap.dedent(story), encoding="utf-8")
    if whodunit is not None:
        wd = tmp_path / "series" / "whodunit"
        wd.mkdir(parents=True)
        (wd / f"book-{book}.yaml").write_text(textwrap.dedent(whodunit), encoding="utf-8")
    return tmp_path


CUT = """\
    ## Chapter 01 — First
    - **Beats:** 1-2
    ## Chapter 02 — Second
    - **Beats:** 3-4
    ## Chapter 03 — Third
    - **Beats:** 5-6
    """

STORY = """\
    - [1] She arrives. @maggie
    - [2] She unpacks. @maggie
    - [3] He admits the smaller lie. @simon !c-smaller-lie
    - [4] The town notices. @maggie
    - [5] The hand is proved. @maggie
    - [6] It closes. @maggie
    """


def test_clean_book_has_no_findings(tmp_path, capsys):
    root = _series(tmp_path, cut_plan=CUT, story=STORY)
    assert check(root / "input" / "book-01", root, "01") == 0
    assert "no findings" in capsys.readouterr().out


def test_out_of_range_reference_blocks(tmp_path, capsys):
    root = _series(tmp_path, cut_plan=CUT,
                   story=STORY + "\n- Guardrail: see ch 09 for the payoff.\n")
    assert check(root / "input" / "book-01", root, "01") == 1
    assert "out-of-range" in capsys.readouterr().out


def test_clue_plant_mismatch_blocks(tmp_path, capsys):
    """The sigil sits in ch 02; the ledger claims ch 03. Same fact, written twice."""
    root = _series(tmp_path, cut_plan=CUT, story=STORY, whodunit="""\
        clues:
        - id: c-smaller-lie
          plant_chapter: 3
          description: He admits it.
        """)
    assert check(root / "input" / "book-01", root, "01") == 1
    out = capsys.readouterr().out
    assert "clue-plant-mismatch" in out and "ch 02" in out


def test_clue_plant_agreement_is_silent(tmp_path, capsys):
    root = _series(tmp_path, cut_plan=CUT, story=STORY, whodunit="""\
        clues:
        - id: c-smaller-lie
          plant_chapter: 2
          description: He admits it.
        """)
    assert check(root / "input" / "book-01", root, "01") == 0
    assert "clue-plant-mismatch" not in capsys.readouterr().out


def test_prose_reference_outside_declared_span_is_advisory(tmp_path, capsys):
    """The book-01 bug: prose said ch 05 for a lie confessed in ch 06."""
    root = _series(tmp_path, cut_plan=CUT, story=STORY, whodunit="""\
        red_herrings:
        - id: rh-simon
          plant_chapter: 2
          resolves_chapter: 3
          description: That is the smaller lie he confesses without naming in ch 01.
        """)
    assert check(root / "input" / "book-01", root, "01") == 0   # advisory never blocks
    assert "yaml-field-disagreement" in capsys.readouterr().out


def test_prose_reference_inside_declared_span_is_not_flagged(tmp_path, capsys):
    """A herring planted at 2 and resolved at 3 may name ch 03 mid-arc without rot.
    This is the false positive that killed the first version of the rule."""
    root = _series(tmp_path, cut_plan=CUT, story=STORY, whodunit="""\
        red_herrings:
        - id: rh-simon
          plant_chapter: 2
          resolves_chapter: 3
          description: Cleared of the murder at ch 03, then live again.
        """)
    assert check(root / "input" / "book-01", root, "01") == 0
    assert "yaml-field-disagreement" not in capsys.readouterr().out


def test_chapter_headings_are_not_treated_as_references(tmp_path, capsys):
    root = _series(tmp_path, cut_plan=CUT, story=STORY)
    check(root / "input" / "book-01", root, "01")
    assert "out-of-range" not in capsys.readouterr().out


def test_missing_book_returns_usage_error(tmp_path):
    assert check(tmp_path / "input" / "book-99", tmp_path, "99") == 2
