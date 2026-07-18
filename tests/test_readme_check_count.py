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


# --- FINAL REVIEW C1(b): the length-profile schema changed under series authors
# with nothing shipped and nothing documented, so the live series' profile — a
# prose table with no band_*/weight_* keys — crashed the lock. The engine
# deliberately ships no default profile (CLAUDE.md), so the schema must be
# DISCOVERABLE instead: pinned here so it cannot silently drift again.
#
# Schema v2 (packet/map redesign, spec 2026-07-18 §6): the brief compiler's
# per-class weights and floors are retired — penny_length.py is a validator, not
# a generator, so the schema shrinks to band_* plus one flat min_scene_words
# floor. Legacy v1 keys (weight_<class>, min_<class>_words) are tolerated and
# ignored, never a hard failure, so this test also pins that the docs SAY so.

SCHEMA_KEYS = ("band_default", "min_scene_words")


def test_readme_documents_the_length_profile_schema():
    text = README.read_text(encoding="utf-8")
    assert "### The length profile" in text
    for key in SCHEMA_KEYS:
        assert key in text, f"README must document {key}"
    assert "legacy" in text.lower() and "tolerated" in text.lower()


def test_claude_md_documents_the_length_profile_schema():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    for key in ("band_default", "min_scene_words", "weight_<class>", "min_<class>_words"):
        assert key in text, f"CLAUDE.md must document {key}"
    assert "tolerated" in text.lower()


def test_parse_profile_error_teaches_the_documented_schema():
    # The named error a legacy profile produces must point at the same keys the
    # docs teach — one schema, three voices (error, README, CLAUDE.md).
    # v2 schema: band_default and min_scene_words are required; legacy keys tolerated.
    from scripts import penny_length
    hint = penny_length.SCHEMA_HINT
    for key in ("band_default", "min_scene_words", "Legacy"):
        assert key in hint
