"""Pins README.md's tension_check.py check count and roster the same way
test_claude_md_check_count.py pins CLAUDE.md's — this is the fix for the gap
that let README drift: only CLAUDE.md was pinned, so when Task 9 added the
ninth check (`overloaded-chapter`) README kept teaching "eight named checks"
with an 8-row table, and a showrunner reading the README (the primary
walkthrough) would hit `preflight lock-mystery` failing on a check the doc
never mentioned.

The expected check-id list is derived from scripts/tension_check.py's own
module docstring rather than hand-typed here a second time, so this test
cannot itself drift out of sync with the source the way the prose docs did.
`undeclared-scene-weight` is deliberately excluded from that derived list:
the docstring describes it as "brief_render's own vocabulary... raised here
too", not a tension_check check in its own right — which is exactly why
CLAUDE.md's existing "nine named checks" sentence omits it too.
"""
import re
from pathlib import Path

TENSION_CHECK = Path("scripts/tension_check.py")
CLAUDE_MD = Path("CLAUDE.md")
README = Path("README.md")


def _docstring_check_ids() -> list[str]:
    text = TENSION_CHECK.read_text(encoding="utf-8")
    block = text.split("Checks (ids are the waiver handles):", 1)[1]
    block = block.split("\n\n", 1)[0]
    # New entries sit at exactly 2 leading spaces (`  id  description`);
    # wrapped continuation lines of a long description sit at 21 — so anchor
    # on precisely 2 leading spaces to avoid matching a continuation's
    # leading word as a bogus check id.
    ids = re.findall(r"^  ([a-z][a-z-]+)\s", block, re.MULTILINE)
    assert ids, "could not parse any check ids from tension_check.py's docstring"
    return [i for i in ids if i != "undeclared-scene-weight"]


def test_docstring_yields_exactly_nine_checks():
    # Sanity check on the derivation itself, so a future tenth check makes
    # this test fail loudly here rather than silently under-counting below.
    ids = _docstring_check_ids()
    assert len(ids) == 9, ids
    assert "overloaded-chapter" in ids
    assert "undeclared-scene-weight" not in ids


def test_readme_names_nine_tension_checks_including_overloaded_chapter():
    text = README.read_text(encoding="utf-8")
    assert "nine named checks" in text
    assert "eight named checks" not in text
    assert "`overloaded-chapter`" in text


def test_readme_and_claude_md_roster_every_derived_check_id():
    ids = _docstring_check_ids()
    for path in (CLAUDE_MD, README):
        text = path.read_text(encoding="utf-8")
        for check_id in ids:
            assert f"`{check_id}`" in text, f"{path}: missing `{check_id}`"
