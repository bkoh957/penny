from scripts import background_cut as bc

SOURCE = """# Pelican's Crook — Background History

Some connective prose that is not an entry.

## Stance
- Southern Ocean, not tropical: cool, changeable.
- Ordinary to locals, strange to the protagonist.

## Town
Reference prose under the part heading, not cut.

### The Wheelhouse becomes the symbolic centre
The old boat shed took the pottery in 1998.

## Characters

### Maggie — the woman who rebuilt without erasing herself
A potter who does not perform fear.

### Cal
The carpenter who repaired everyone.

## Relationships

### Maggie and Cal
Slow, and neither will name it first.

## Secrets

### The real Marion Wexler
Marion is a borrowed name.
"""


def test_slug_truncates_at_em_dash():
    assert bc.slug("Maggie — the woman who rebuilt without erasing herself") == "maggie"


def test_slug_lowercases_and_collapses():
    assert bc.slug("The Wheelhouse becomes the symbolic centre") == \
        "the-wheelhouse-becomes-the-symbolic-centre"


def test_relationship_slug_sorts_both_ways():
    assert bc.relationship_slug("Maggie and Cal") == "cal--maggie"
    assert bc.relationship_slug("Cal and Maggie") == "cal--maggie"


def test_relationship_slug_none_without_separator():
    assert bc.relationship_slug("Maggie") is None


def test_parse_stance_is_verbatim():
    parsed = bc.parse_background(SOURCE)
    assert parsed["stance"] == (
        "- Southern Ocean, not tropical: cool, changeable.\n"
        "- Ordinary to locals, strange to the protagonist."
    )


def test_parse_entries_by_part():
    entries = bc.parse_background(SOURCE)["entries"]
    by_slug = {e["slug"]: e for e in entries}
    assert set(by_slug) == {
        "the-wheelhouse-becomes-the-symbolic-centre",
        "maggie", "cal", "cal--maggie", "the-real-marion-wexler",
    }
    assert by_slug["maggie"]["kind"] == "character"
    assert by_slug["cal--maggie"]["kind"] == "relationship"
    assert by_slug["the-real-marion-wexler"]["kind"] == "secret"
    assert by_slug["the-wheelhouse-becomes-the-symbolic-centre"]["kind"] == "town"


def test_entry_body_is_verbatim():
    entries = {e["slug"]: e for e in bc.parse_background(SOURCE)["entries"]}
    assert entries["cal"]["body"] == "The carpenter who repaired everyone."


def test_prose_under_part_heading_is_not_an_entry():
    entries = bc.parse_background(SOURCE)["entries"]
    assert not any("Reference prose" in e["body"] for e in entries)


def test_unknown_part_is_reported_not_cut():
    parsed = bc.parse_background("## Stance\nx\n\n## Weather\n\n### Rain\nwet\n")
    assert parsed["unknown_parts"] == ["Weather"]
    assert parsed["entries"] == []


def test_deep_heading_is_reported():
    parsed = bc.parse_background(
        "## Stance\nx\n\n## Characters\n\n### Cal\nc\n\n#### Cal's hands\nh\n")
    assert parsed["deep_headings"] == ["Cal's hands"]


def test_absent_part_cuts_nothing():
    parsed = bc.parse_background("## Stance\njust a stance\n")
    assert parsed["entries"] == []
    assert parsed["stance"] == "just a stance"


def _blocking(text):
    return bc.check_background(bc.parse_background(text))["blocking"]


def test_clean_source_has_no_blocking():
    assert _blocking(SOURCE) == []


def test_missing_stance():
    found = _blocking("## Characters\n\n### Cal\nc\n")
    assert any(f.startswith("missing-stance:") for f in found)


def test_empty_stance_is_missing_stance():
    found = _blocking("## Stance\n\n## Characters\n\n### Cal\nc\n")
    assert any(f.startswith("missing-stance:") for f in found)


def test_unknown_section():
    found = _blocking("## Stance\nx\n\n## Weather\n\n### Rain\nwet\n")
    assert any(f.startswith("unknown-section:") and "Weather" in f for f in found)


def test_unknown_entry_depth():
    found = _blocking(
        "## Stance\nx\n\n## Characters\n\n### Cal\nc\n\n#### Cal's hands\nh\n")
    assert any(f.startswith("unknown-entry-depth:") and "Cal's hands" in f
               for f in found)


def test_duplicate_entry():
    found = _blocking(
        "## Stance\nx\n\n## Characters\n\n### Cal — the carpenter\na\n\n"
        "### Cal — the other one\nb\n")
    assert any(f.startswith("duplicate-entry:") and "cal" in f for f in found)


def test_relationship_reversal_is_a_duplicate():
    found = _blocking(
        "## Stance\nx\n\n## Relationships\n\n### Maggie and Cal\na\n\n"
        "### Cal and Maggie\nb\n")
    assert any(f.startswith("duplicate-entry:") and "cal--maggie" in f
               for f in found)


def test_malformed_relationship():
    found = _blocking("## Stance\nx\n\n## Relationships\n\n### Maggie\na\n")
    assert any(f.startswith("malformed-relationship:") and "Maggie" in f
               for f in found)


def test_duplicate_across_parts_collides():
    """A town section and a character that slug the same collide — one flat dir."""
    found = _blocking(
        "## Stance\nx\n\n## Town\n\n### Cal\nplace\n\n## Characters\n\n### Cal\nperson\n")
    assert any(f.startswith("duplicate-entry:") for f in found)
