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


from scripts import penny_meta


def _built(text):
    parsed = bc.parse_background(text)
    return {b["rel"]: b["text"] for b in bc.build_entries(parsed, "SRCSHA")}


def test_targets_are_flat_background_dir_plus_setting_pack():
    rels = set(_built(SOURCE))
    assert "config/setting-pack/setting.md" in rels
    assert "series/continuity/background/maggie.md" in rels
    assert "series/continuity/background/cal--maggie.md" in rels
    assert not any("background/characters/" in r for r in rels)


def test_setting_pack_body_is_the_stance_verbatim():
    text = _built(SOURCE)["config/setting-pack/setting.md"]
    assert "- Southern Ocean, not tropical: cool, changeable." in text
    assert "Ordinary to locals, strange to the protagonist." in text


def test_entry_carries_canon_meta_header():
    text = _built(SOURCE)["series/continuity/background/maggie.md"]
    meta = penny_meta.parse_canon_meta(text)
    assert meta["id"] == "maggie"
    assert meta["kind"] == "character"
    assert meta["built_from_background"] == "SRCSHA"
    assert meta["cut_output_sha256"] == bc.body_sha(
        "A potter who does not perform fear.")


def test_relationship_links_both_characters():
    text = _built(SOURCE)["series/continuity/background/cal--maggie.md"]
    assert sorted(penny_meta.parse_canon_meta(text)["links"]) == ["cal", "maggie"]


def test_character_links_its_relationships():
    text = _built(SOURCE)["series/continuity/background/maggie.md"]
    assert penny_meta.parse_canon_meta(text)["links"] == ["cal--maggie"]


def test_town_and_secret_entries_have_no_links():
    built = _built(SOURCE)
    for slug in ("the-real-marion-wexler",
                 "the-wheelhouse-becomes-the-symbolic-centre"):
        meta = penny_meta.parse_canon_meta(
            built[f"series/continuity/background/{slug}.md"])
        assert meta["links"] == []


def test_body_sha_excludes_the_header():
    body = "A potter who does not perform fear."
    text = bc.stamp(body, {"id": "maggie", "cut_output_sha256": bc.body_sha(body)})
    assert bc.body_sha(text.split("-->\n", 1)[1].strip()) == bc.body_sha(body)


def test_stamp_renders_lists_in_canon_meta_form():
    text = bc.stamp("x", {"id": "a", "links": ["b", "c"]})
    assert penny_meta.parse_canon_meta(text)["links"] == ["b", "c"]


def test_unstamped_target_refuses():
    hand_authored = "# Setting Pack — Coastal Victoria\n\nHand written.\n"
    f = bc.target_refusal(hand_authored, "config/setting-pack/setting.md")
    assert f is not None and f.startswith("unstamped-target:")


def test_stamped_and_unchanged_target_is_safe():
    body = "The carpenter who repaired everyone."
    text = bc.stamp(body, {"id": "cal", "cut_output_sha256": bc.body_sha(body)})
    assert bc.target_refusal(text, "series/continuity/background/cal.md") is None


def test_hand_edited_target_refuses():
    body = "The carpenter who repaired everyone."
    text = bc.stamp(body, {"id": "cal", "cut_output_sha256": bc.body_sha(body)})
    edited = text.replace("repaired everyone", "repaired almost everyone")
    f = bc.target_refusal(edited, "series/continuity/background/cal.md")
    assert f is not None and f.startswith("target-modified-since-cut:")


def test_orphan_is_advisory_and_names_the_file():
    notes = bc.orphan_notes(
        ["series/continuity/background/pruitt.md",
         "series/continuity/background/cal.md"],
        ["series/continuity/background/cal.md"])
    assert len(notes) == 1
    assert notes[0].startswith("orphan-derived:")
    assert "pruitt.md" in notes[0]


def test_no_orphans_when_everything_is_produced():
    assert bc.orphan_notes(["series/continuity/background/cal.md"],
                           ["series/continuity/background/cal.md"]) == []


import pytest


@pytest.fixture
def series(tmp_path, monkeypatch):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input/series").mkdir(parents=True)
    (tmp_path / "series/continuity/characters").mkdir(parents=True)
    (tmp_path / "config/setting-pack").mkdir(parents=True)
    (tmp_path / "input/series/background-history.md").write_text(
        SOURCE, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cut_writes_targets_and_exits_zero(series, capsys):
    assert bc.main([]) == 0
    assert (series / "config/setting-pack/setting.md").is_file()
    assert (series / "series/continuity/background/maggie.md").is_file()
    assert (series / "series/continuity/background/cal--maggie.md").is_file()


def test_cut_is_idempotent(series):
    assert bc.main([]) == 0
    first = (series / "series/continuity/background/maggie.md").read_bytes()
    assert bc.main([]) == 0
    assert (series / "series/continuity/background/maggie.md").read_bytes() == first


def test_blocking_finding_writes_nothing(series, capsys):
    (series / "input/series/background-history.md").write_text(
        "## Characters\n\n### Cal\nc\n", encoding="utf-8")
    assert bc.main([]) == 1
    assert "missing-stance" in capsys.readouterr().out
    assert not (series / "series/continuity/background").exists()


def test_unstamped_setting_pack_refuses_and_writes_nothing(series, capsys):
    (series / "config/setting-pack/coastal.md").write_text("old", encoding="utf-8")
    (series / "config/setting-pack/setting.md").write_text(
        "# hand authored\n", encoding="utf-8")
    assert bc.main([]) == 1
    assert "unstamped-target" in capsys.readouterr().out
    assert (series / "config/setting-pack/setting.md").read_text() == "# hand authored\n"
    assert not (series / "series/continuity/background").exists()


def test_recut_after_source_edit_rewrites(series):
    assert bc.main([]) == 0
    src = series / "input/series/background-history.md"
    src.write_text(SOURCE.replace("The carpenter who repaired everyone.",
                                  "The carpenter who repaired the pier."),
                   encoding="utf-8")
    assert bc.main([]) == 0
    assert "repaired the pier" in (
        series / "series/continuity/background/cal.md").read_text()


def test_orphan_reported_but_left_on_disk(series, capsys):
    assert bc.main([]) == 0
    orphan = series / "series/continuity/background/pruitt.md"
    orphan.write_text(bc.stamp("gone", {"id": "pruitt",
                                        "cut_output_sha256": bc.body_sha("gone")}),
                      encoding="utf-8")
    assert bc.main([]) == 0
    out = capsys.readouterr().out
    assert "orphan-derived" in out and "pruitt.md" in out
    assert orphan.is_file()


def test_missing_source_is_exit_two(series, capsys):
    (series / "input/series/background-history.md").unlink()
    assert bc.main([]) == 2


def test_never_writes_characters_canon_core_or_whodunit(series):
    canon = series / "series/continuity/canon-core.md"
    canon.write_text("core\n", encoding="utf-8")
    char = series / "series/continuity/characters/maggie.md"
    char.write_text("---\nid: maggie\n---\n\nledger owned\n", encoding="utf-8")
    (series / "series/whodunit").mkdir(parents=True)
    ledger = series / "series/whodunit/book-01.yaml"
    ledger.write_text("culprit: x\n", encoding="utf-8")
    before = (canon.read_bytes(), char.read_bytes(), ledger.read_bytes())
    assert bc.main([]) == 0
    assert (canon.read_bytes(), char.read_bytes(), ledger.read_bytes()) == before
