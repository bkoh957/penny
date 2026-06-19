from pathlib import Path

from scripts.penny_meta import load, parse_frontmatter

CONTINUITY = Path("series/continuity")
VALID_TYPES = {"character", "location", "thread"}
TYPE_DIRS = {"characters": "character", "locations": "location", "threads": "thread"}


def test_canon_core_exists():
    assert (CONTINUITY / "canon-core.md").is_file(), "canon-core.md is the always-loaded slice"


def test_every_continuity_entry_has_valid_frontmatter():
    entries = []
    for subdir in TYPE_DIRS:
        entries.extend((CONTINUITY / subdir).glob("*.md"))
    assert entries, "expected at least one example continuity entry per type"
    for path in entries:
        meta = parse_frontmatter(load(path))
        assert meta.get("id"), f"{path} missing id"
        assert meta.get("type") in VALID_TYPES, f"{path} has invalid type {meta.get('type')!r}"
        assert isinstance(meta.get("links"), list), f"{path} links must be a list"


def test_entry_type_matches_its_directory():
    for subdir, expected_type in TYPE_DIRS.items():
        for path in (CONTINUITY / subdir).glob("*.md"):
            meta = parse_frontmatter(load(path))
            assert meta["type"] == expected_type, (
                f"{path} is in /{subdir} but typed {meta['type']!r}"
            )


def test_links_resolve_to_existing_entries():
    by_id = {}
    for subdir in TYPE_DIRS:
        for path in (CONTINUITY / subdir).glob("*.md"):
            meta = parse_frontmatter(load(path))
            by_id[meta["id"]] = path
    for subdir in TYPE_DIRS:
        for path in (CONTINUITY / subdir).glob("*.md"):
            meta = parse_frontmatter(load(path))
            for link in meta["links"]:
                assert link in by_id, f"{path} links to unknown id {link!r}"
