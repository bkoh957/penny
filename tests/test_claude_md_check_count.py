"""Pins CLAUDE.md's accuracy about tension_check.py's named checks and the
length machinery — these drifted true when `overloaded-chapter` and
`scripts/penny_length.py` shipped without a matching update here. A doc that
undercounts the checks is the same "looks right, silently wrong" failure mode
as a runbook teaching syntax the parser doesn't accept — so pin it the same
way test_phase3_doc_note.py does.
"""
from pathlib import Path

CLAUDE_MD = Path("CLAUDE.md")


def test_claude_md_names_ten_tension_checks_including_overloaded_chapter():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "ten named checks" in text
    assert "nine named checks" not in text
    assert "`overloaded-chapter`" in text
    assert "`monotonous-closings`" in text


def test_claude_md_documents_penny_length():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "scripts/penny_length.py" in text


def test_claude_md_documents_the_check_subcommand_and_the_advisory():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "story_cut.py check" in text
    assert "directive-shaped-beat" in text
    assert "twenty-three findings" in text


def test_claude_md_names_the_craft_document_and_the_authoring_agent():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "config/story-craft/" in text
    assert "story-author" in text
