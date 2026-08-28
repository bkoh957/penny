"""Lint + contract test for
`docs/superpowers/specs/2026-08-29-engine-holds-story-details-fix.md`.

The defect: twelve sites under `config/` and `agents/` named a specific
series' characters (a superseded protagonist `Cora`, superseded characters
`Dez`/`Renna`, and — in one place — the *current* series' protagonist
`Maggie`) as if they were universal craft facts. One of them
(`config/line-edit/line-edit.md`'s old "Cora's register is precise and
lightly formal" line) actively contradicted the live series' Voice Pack on
every chapter, and was only avoided by an undocumented prompt override (spec
§2). The spec's own review found two of the twelve sites (both `Maggie's
narration`) *after* a full manual sweep had already happened — proof that
"is this name stale?" is the wrong test, because a name that is currently
correct produces no symptom and reads as fine (spec §3, "The lesson for the
fix"). That is why this file is a lint, not a one-off cleanup: a human
rereading these directories will make the same mistake the sweep did.

Spec §5 is explicit that the naive version of this lint — fail on any
capitalised word outside an allowlist — was implemented, measured (385 hits
across 35 files: `State`, `Knowledge`, `Reader`, `Guardrails`... ordinary
engine vocabulary) and rejected as something that would be disabled within a
week. The possessive shape (`\\b[A-Z][a-z]+'s\\b`) is the signal that
actually survived measurement: a craft document has very little reason to
write a proper noun in the possessive, and the spec measured 11 raw hits on
the pre-fix tree, 8 of them real sites (including both sites the manual
sweep missed) and 3 legitimate craft nouns.

This module's own measurement of the same regex on the same tree returns 14,
not 11 — the extra 3 are `He's`/`He's`/`It's`, all pronoun *contractions*
("he is", "it is"), not possessives. English never forms a pronoun's
possessive with an apostrophe (his, hers, its, theirs, whose) — an
apostrophe-s on a pronoun is structurally always a contraction, never a
possessive — so `PRONOUN_CONTRACTIONS` below is not a growing vocabulary
list the way the rejected all-caps lint's allowlist would have been; it is a
closed, fixed set fixed by English grammar, not by this codebase's
vocabulary. Excluding it recovers the spec's measured 11.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCAN_DIRS = ("config", "agents")

POSSESSIVE_RE = re.compile(r"\b([A-Z][a-z]+)'s\b")

# Closed class: pronouns/demonstratives whose apostrophe-s is grammatically
# always a contraction (X is / X has), never a possessive, regardless of
# what character or noun the sentence is about. Fixed by English grammar,
# not by this repo's vocabulary — does not grow the way the rejected
# all-caps lint's allowlist would have.
PRONOUN_CONTRACTIONS = frozenset({
    "He", "She", "It", "That", "This", "There", "Here",
    "What", "Who", "Where", "When", "How", "Why", "Let",
})

# The explicit record of which possessives the engine is permitted to
# write. Each entry is a genuine craft noun's possessive, never a character
# name — adding a name here defeats the lint.
ALLOWED_POSSESSIVES = frozenset({
    # config/beta-readers/beta-protocol.md, agents/beta-reader.md — the
    # persona's own facet field, e.g. "Reader's `facet` (self | place)".
    "Reader's",
    # agents/outline-expander.md — the wiring footer's Hook field, e.g.
    # "Hook's grade is the bracketed tag next to it".
    "Hook's",
})


def _iter_scanned_files():
    for scan_dir in SCAN_DIRS:
        yield from sorted((REPO / scan_dir).rglob("*.md"))


def _possessive_hits(path: Path) -> list[tuple[int, str]]:
    hits = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in POSSESSIVE_RE.finditer(line):
            word = match.group(1)
            possessive = match.group(0)
            if word in PRONOUN_CONTRACTIONS:
                continue
            if possessive in ALLOWED_POSSESSIVES:
                continue
            hits.append((lineno, possessive))
    return hits


def test_no_unallowlisted_possessive_proper_noun_under_config_or_agents():
    """A capitalised word in the possessive, under config/ or agents/, that
    is not a closed-class pronoun contraction and not on the explicit
    allowlist, is a story fact leaking into the genre/location-agnostic
    engine (CLAUDE.md:11-14). Fix the file or extend ALLOWED_POSSESSIVES
    with a genuine craft noun — never a character name."""
    offenders = []
    for path in _iter_scanned_files():
        for lineno, possessive in _possessive_hits(path):
            offenders.append(f"{path.relative_to(REPO)}:{lineno}: {possessive}")
    assert not offenders, (
        "Possessive proper noun(s) found outside the allowlist:\n"
        + "\n".join(offenders)
    )


def test_the_superseded_character_names_are_gone():
    """Cora (superseded protagonist), Dez and Renna (superseded worked-example
    characters) must not appear anywhere under config/ or agents/ — the twelve
    sites this spec removes. Deliberately NOT checking for `Maggie`: it is a
    legitimate word (the live series' protagonist) and a name denylist is
    exactly the approach the spec's §6 argues against; the possessive lint
    above is what actually covers the shape of the defect."""
    banned = ("Cora", "Dez", "Renna")
    offenders = []
    for path in _iter_scanned_files():
        text = path.read_text(encoding="utf-8")
        for name in banned:
            if name in text:
                offenders.append(f"{path.relative_to(REPO)}: {name!r}")
    assert not offenders, f"Story-specific character name(s) found:\n" + "\n".join(offenders)


def test_the_precedence_rule_is_in_line_edit_and_copy_edit():
    """Spec §4b calls this the strongest element of the fix — the only part
    that would have prevented the live harm (§2) regardless of names, and the
    only part that still works for Category C (a currently-correct name).
    Pin its presence directly rather than relying on the possessive lint,
    which cannot see it at all."""
    for rel in ("config/line-edit/line-edit.md", "config/copy-edit/copy-edit.md"):
        text = (REPO / rel).read_text(encoding="utf-8")
        collapsed = " ".join(text.split())  # tolerate the file's own line-wrapping
        assert "## Precedence" in text, f"{rel} is missing a Precedence section"
        assert "conflict with the voice pack, style sheet, or setting pack" in collapsed, (
            f"{rel} is missing the precedence rule's file list")
        assert "**that file wins.**" in collapsed, f"{rel} is missing the precedence rule text"
        assert "This file never states a fact about a character." in text
        # The rule must defer to whichever config file actually wins — never
        # naming a tier (spec's overlay is three levels: engine, genre pack,
        # series folder; hardcoding "series" forecloses a genre pack ever
        # supplying its own voice-pack default, CLAUDE.md:24-29).
        assert "series Voice Pack" not in text
        assert "series file wins" not in text
