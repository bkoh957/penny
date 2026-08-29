"""Lint + contract test for
`docs/superpowers/specs/2026-08-29-engine-holds-story-details-fix.md`.

The defect: sites across the engine's shipped files named a specific
series' characters (a superseded protagonist `Cora`, superseded characters
`Dez`/`Renna`, and — in one place — the *current* series' protagonist
`Maggie`) as if they were universal craft facts. One of them
(`config/line-edit/line-edit.md`'s old "Cora's register is precise and
lightly formal" line) actively contradicted the live series' Voice Pack on
every chapter, and was only avoided by an undocumented prompt override (spec
§2). The spec's own review found two more sites (both `Maggie's
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
SCAN_DIRS = ("config", "agents", "commands", "scripts", "genres")

# Both apostrophes: ASCII and U+2019. An ASCII-only pattern is defeated
# silently by one paste from a word processor.
POSSESSIVE_RE = re.compile(r"\b([A-Z][a-z]+)['’]s\b")

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
    # The engine's own name, not a story noun — commands/, scripts/ and
    # genres/ all refer to "Penny's" behaviour.
    "Penny's",
    # scripts/penny_genre.py — the genre's name, e.g. "Cozy's roster".
    "Cozy's",
    # genres/cozy-mystery/ — genre ROLE nouns, which is exactly what the
    # convention tells authors to use instead of a character name.
    "Sleuth's",
    "Victim's",
})


def _iter_scanned_files():
    # Not just *.md: `CLAUDE.md:11-14`'s rule names `scripts/` and the
    # command logic, and three of the sites the .md-only sweep missed were
    # in module docstrings and comments.
    for scan_dir in SCAN_DIRS:
        for suffix in ("*.md", "*.py", "*.yaml", "*.sh"):
            yield from sorted((REPO / scan_dir).rglob(suffix))


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
    """The named cohort must not appear anywhere under the scanned engine dirs:
    `Cora` (superseded protagonist), `Dez`/`Renna` (superseded worked-example
    characters), and `Priya`/`Odette`/`Talia`/`Tannery` — the invented names
    `HANDOFF-story.md:119-121` chose so the craft docs would not couple to one
    series' cast. The convention pinned below supersedes that choice: an
    invented name is indistinguishable from canon to whoever reads it next,
    so examples name no character at all.

    Deliberately NOT checking for `Maggie`: it is the live series'
    protagonist, a name denylist is the approach the spec's §6 argues
    against, and the possessive lint above is what covers the defect's actual
    shape. This test is a pin on names already removed — by construction it
    cannot catch the next one."""
    # Word-boundary, not substring: `if "Dez" in text` false-positives on any
    # future word containing it.
    banned = ("Cora", "Dez", "Renna", "Priya", "Odette", "Talia", "Tannery")
    pattern = re.compile(r"\b(" + "|".join(banned) + r")\b")
    offenders = []
    for path in _iter_scanned_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in pattern.finditer(line):
                offenders.append(f"{path.relative_to(REPO)}:{lineno}: {m.group(1)!r}")
    assert not offenders, "Story-specific character name(s) found:\n" + "\n".join(offenders)


CONVENTION_FILE = REPO / "config" / "story-craft" / "writing-beats.md"
CONVENTION_HEADING = "## Examples never name a character"


def test_the_naming_convention_is_stated_where_authors_read_it():
    """Nothing pinned §4e — the element the spec calls the part that ends the
    sequence — so it could be deleted with the suite staying green. It states
    the rule the two lints above only approximate, and it is the reason a
    future author writing a new craft example does not reach for a cast list.

    Pinned together with a re-run of the possessive lint over that same file,
    because the review that prompted this found the file declaring the
    convention in its opening section and breaking it thirty-three lines
    down."""
    text = CONVENTION_FILE.read_text(encoding="utf-8")
    assert CONVENTION_HEADING in text, (
        f"{CONVENTION_FILE.relative_to(REPO)} no longer states the naming "
        f"convention ({CONVENTION_HEADING!r})")
    assert not _possessive_hits(CONVENTION_FILE), _possessive_hits(CONVENTION_FILE)


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
