from scripts.penny_meta import parse_frontmatter, parse_yaml_blocks


def test_parse_frontmatter_scalars_and_list():
    text = (
        "---\n"
        "id: margaret\n"
        "type: character\n"
        "links: [the-inheritance, lighthouse]\n"
        "---\n"
        "body text here\n"
    )
    meta = parse_frontmatter(text)
    assert meta["id"] == "margaret"
    assert meta["type"] == "character"
    assert meta["links"] == ["the-inheritance", "lighthouse"]


def test_parse_frontmatter_empty_list():
    text = "---\nid: x\ntype: thread\nlinks: []\n---\n"
    assert parse_frontmatter(text)["links"] == []


def test_parse_frontmatter_absent_returns_empty():
    assert parse_frontmatter("no frontmatter here\n") == {}


def test_parse_yaml_blocks_merges_keys_and_ignores_comments():
    text = (
        "# Title\n\n"
        "```yaml\n"
        "drafting_model: claude-opus   # a comment\n"
        "beta_models: [codex, hermes]\n"
        "```\n\n"
        "prose\n\n"
        "```yaml\n"
        "ledger_approval: review\n"
        "```\n"
    )
    cfg = parse_yaml_blocks(text)
    assert cfg["drafting_model"] == "claude-opus"
    assert cfg["beta_models"] == ["codex", "hermes"]
    assert cfg["ledger_approval"] == "review"


def test_value_with_hash_not_stripped_when_no_preceding_space():
    text = "---\nid: page\nsource: https://example.com#anchor\nlinks: []\n---\n"
    meta = parse_frontmatter(text)
    assert meta["source"] == "https://example.com#anchor"


def test_value_with_colon_is_preserved():
    text = "---\nid: bk\ntitle: The House: A Novel\nlinks: []\n---\n"
    assert parse_frontmatter(text)["title"] == "The House: A Novel"


from scripts.penny_meta import parse_canon_meta


def test_parse_canon_meta_reads_flat_map():
    text = "# Canon Core\n<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->\nbody"
    meta = parse_canon_meta(text)
    assert meta["fluency_stage"] == "OUTSIDER"
    assert meta["id"] == "canon-core"


def test_parse_canon_meta_absent_returns_empty():
    assert parse_canon_meta("# No header here\njust prose") == {}


def test_real_canon_core_declares_a_valid_stage():
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    text = (repo / "series/continuity/canon-core.md").read_text(encoding="utf-8")
    meta = parse_canon_meta(text)
    assert meta.get("fluency_stage") in {"OUTSIDER", "SETTLING", "BELONGING"}


from scripts.penny_meta import (
    parse_canon_sections,
    write_canon_section_field,
    write_frontmatter_field,
)

CANON = """---
id: canon-core
type: thread
links: []
---
<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->
# Canon Core

## Protagonist fixed facts
<!-- canon-meta: {id: protagonist-fixed, refs: [cora-mistate], active_window: "1-2", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Cora Mistate, 44.

## Current timeline position
<!-- canon-meta: {id: current-timeline, refs: [], active_window: "1-13", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Book 01, pre-draft.
"""


def test_parse_canon_sections_finds_section_headers_not_file_level():
    secs = parse_canon_sections(CANON)
    ids = [s["id"] for s in secs]
    assert ids == ["protagonist-fixed", "current-timeline"]  # file-level excluded


def test_parse_canon_sections_carries_heading_and_refs():
    secs = parse_canon_sections(CANON)
    prot = next(s for s in secs if s["id"] == "protagonist-fixed")
    assert prot["heading"] == "Protagonist fixed facts"
    assert prot["refs"] == ["cora-mistate"]
    current = next(s for s in secs if s["id"] == "current-timeline")
    assert current["refs"] == []


def test_parse_canon_sections_multi_ref_list():
    text = (
        "## S\n"
        "<!-- canon-meta: {id: s, refs: [a-one, b-two], active_window: \"1-3\"} -->\n"
        "- body\n"
    )
    secs = parse_canon_sections(text)
    assert secs[0]["refs"] == ["a-one", "b-two"]


def test_write_canon_section_field_sets_and_preserves_body():
    out = write_canon_section_field(CANON, "protagonist-fixed", "last_referenced", 7)
    secs = parse_canon_sections(out)
    prot = next(s for s in secs if s["id"] == "protagonist-fixed")
    assert prot["last_referenced"] == "7"
    assert "- Cora Mistate, 44." in out          # body untouched
    assert "{id: canon-core, fluency_stage: OUTSIDER}" in out  # file-level untouched


def test_write_canon_section_field_is_idempotent():
    once = write_canon_section_field(CANON, "protagonist-fixed", "last_referenced", 7)
    twice = write_canon_section_field(once, "protagonist-fixed", "last_referenced", 7)
    assert once == twice                         # byte-identical re-application


def test_write_canon_section_field_unknown_id_raises():
    import pytest
    with pytest.raises(KeyError):
        write_canon_section_field(CANON, "no-such-section", "last_referenced", 7)


def test_write_frontmatter_field_updates_existing_and_inserts():
    thread = "---\nid: t\ntype: thread\nlinks: []\n---\n# body\n"
    out = write_frontmatter_field(thread, "last_advanced_chapter", 5)
    assert "last_advanced_chapter: 5" in out
    assert "# body" in out
    out2 = write_frontmatter_field(out, "last_advanced_chapter", 9)
    assert "last_advanced_chapter: 9" in out2
    assert "last_advanced_chapter: 5" not in out2  # replaced, not duplicated
