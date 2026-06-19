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
