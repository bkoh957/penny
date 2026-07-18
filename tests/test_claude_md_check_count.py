"""Pins CLAUDE.md's accuracy about tension_check.py's named checks and the
length machinery — these drifted true when `overloaded-chapter` and
`scripts/penny_length.py` shipped without a matching update here. A doc that
undercounts the checks is the same "looks right, silently wrong" failure mode
as a runbook teaching syntax the parser doesn't accept — so pin it the same
way test_phase3_doc_note.py does.
"""
from pathlib import Path

CLAUDE_MD = Path("CLAUDE.md")


def test_claude_md_names_nine_tension_checks_including_overloaded_chapter():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "nine named checks" in text
    assert "eight named checks" not in text
    assert "`overloaded-chapter`" in text


def test_claude_md_documents_penny_length():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "scripts/penny_length.py" in text
