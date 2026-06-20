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
