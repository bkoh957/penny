# Background-History Source Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One authored series-level document, `input/series/background-history.md`, cut deterministically into compact derived files that the packet slice and prose agents already know how to load.

**Architecture:** A new `scripts/background_cut.py` in the style of `scripts/story_cut.py` — pure functions that take text and return named findings, with all IO in `main()`. It writes exactly two kinds of target: a flat `series/continuity/background/<slug>.md` per entry, and `config/setting-pack/setting.md` from the authored `## Stance` block. Every target carries a `canon-meta` header stamping the source sha and its own body sha, so re-cutting is free while stamps match and refuses the moment they do not. No LLM step, no approval gate, no writes to `canon-core.md`, `continuity/characters/`, or any whodunit ledger.

**Tech Stack:** Python 3, stdlib only (`hashlib`, `re`, `pathlib`). `scripts/penny_meta.py` for canon-meta parsing, `scripts/penny_paths.py` for path resolution. pytest. **No PyYAML** — the dependency-split rule.

**Spec:** `docs/superpowers/specs/2026-08-13-background-history-source-layer-design.md`

## Global Constraints

- **Stdlib only in `scripts/`.** No PyYAML in `background_cut.py`. Parse canon-meta via `penny_meta`.
- **Location- and genre-agnostic.** No place names, character names, or genre facts in engine code. The setting pack target is the fixed filename `setting.md`, never a place name.
- **Pure functions take text, not paths.** `check_background`, `build_entries`, `target_refusal` receive strings and return data. Only `main()` touches the filesystem. This mirrors `story_cut.check_story`.
- **Findings are `"<finding-id>: <detail>"` strings** in a `{"blocking": [...], "notes": [...]}` dict, matching `story_cut.check_story`.
- **Exit codes:** `0` clean, `1` findings, `2` usage or missing source. Matches `map_check.py`.
- **Seven blocking findings, one advisory.** The advisory (`orphan-derived`) rides `notes` and never blocks. Do not add an eighth blocking finding.
- **Never write** `series/continuity/canon-core.md`, `series/continuity/characters/**`, or `series/whodunit/**`.
- Run the full suite with `python3 -m pytest` (pytest.ini sets `pythonpath=.`). It is green at 1018 tests before this plan.
- Commit after every task. Work on a branch off `main`.

---

### Task 1: Fix `parse_canon_meta` for multi-element lists

`penny_meta.parse_canon_meta` splits its header on bare commas, so `links: [a, b]` parses as `[a` and the rest is lost. Only single-element lists have ever been exercised (`tests/test_packet_assemble.py:58`). Every character entry this feature produces has multiple links, so this is a prerequisite, not a cleanup. `_split_top_level` already exists for exactly this and is used by `parse_canon_sections`.

**Files:**
- Modify: `scripts/penny_meta.py:93-103`
- Test: `tests/test_penny_meta.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `parse_canon_meta(text: str) -> dict` — unchanged signature; `links`/`refs` values with two or more elements now parse as full lists.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_penny_meta.py`:

```python
def test_canon_meta_multi_element_list():
    text = "<!-- canon-meta: {id: maggie, links: [cal--maggie, faye--maggie]} -->\n"
    meta = penny_meta.parse_canon_meta(text)
    assert meta["id"] == "maggie"
    assert meta["links"] == ["cal--maggie", "faye--maggie"]


def test_canon_meta_single_element_list_unchanged():
    text = "<!-- canon-meta: {id: mary, links: [cal]} -->\n"
    assert penny_meta.parse_canon_meta(text)["links"] == ["cal"]


def test_canon_meta_scalar_pairs_unchanged():
    text = "<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->\n"
    meta = penny_meta.parse_canon_meta(text)
    assert meta == {"id": "canon-core", "fluency_stage": "OUTSIDER"}
```

If `tests/test_penny_meta.py` does not exist, create it with `from scripts import penny_meta` at the top — check how sibling tests import (`tests/test_lexicon_check.py` is a good reference) and match that convention exactly.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_penny_meta.py -v -k canon_meta`
Expected: `test_canon_meta_multi_element_list` FAILS — `links` is `["[cal--maggie"]` or similar truncation. The other two PASS.

- [ ] **Step 3: Write minimal implementation**

In `scripts/penny_meta.py`, `parse_canon_meta` currently ends with:

```python
    return _parse_kv_lines([part for part in inner.split(",")])
```

Replace that line with:

```python
    # Split on top-level commas only — a `links: [a, b]` value contains commas
    # that are not field separators. `_split_top_level` is the same splitter
    # `parse_canon_sections` uses.
    return _parse_kv_lines(_split_top_level(inner))
```

`_split_top_level` is defined below `parse_canon_meta` in the file. Python resolves it at call time, so no reordering is needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_meta.py -v -k canon_meta`
Expected: all three PASS.

Run: `python3 -m pytest`
Expected: all pass (1018 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_meta.py tests/test_penny_meta.py
git commit -m "fix(penny-meta): canon-meta links with two or more elements no longer truncate"
```

---

### Task 2: Parse the heading contract

**Files:**
- Create: `scripts/background_cut.py`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `PART_HEADINGS: tuple[str, ...]` = `("Stance", "Town", "Characters", "Relationships", "Secrets")`
  - `KIND_BY_PART: dict[str, str]` mapping `Town→town`, `Characters→character`, `Relationships→relationship`, `Secrets→secret`
  - `slug(title: str) -> str`
  - `relationship_slug(title: str) -> str | None` — `None` when the title has no ` and ` separator
  - `parse_background(text: str) -> dict` with keys `stance` (str), `entries` (list of dicts with `part`, `kind`, `title`, `slug`, `body`), `unknown_parts` (list[str]), `deep_headings` (list[str])

- [ ] **Step 1: Write the failing test**

Create `tests/test_background_cut.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'scripts.background_cut'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/background_cut.py`:

```python
#!/usr/bin/env python3
"""Cut input/series/background-history.md into derived continuity entries and
the setting pack (spec 2026-08-13).

Pure functions take text and return findings; all IO lives in main(). The cut
never writes canon-core.md, continuity/characters/, or any whodunit ledger —
those have their own owners (spec §6).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import penny_meta, penny_paths  # noqa: E402

PART_HEADINGS = ("Stance", "Town", "Characters", "Relationships", "Secrets")
KIND_BY_PART = {
    "Town": "town",
    "Characters": "character",
    "Relationships": "relationship",
    "Secrets": "secret",
}

_EM_DASH = "—"
_HEADING_RE = re.compile(r"^(?P<hashes>#{2,})\s+(?P<title>.+?)\s*$")
_AND_RE = re.compile(r"\s+and\s+", re.IGNORECASE)


def slug(title: str) -> str:
    """Truncate at the first em dash, then lowercase with non-alphanumerics
    collapsed to single hyphens."""
    head = title.split(_EM_DASH, 1)[0]
    out = re.sub(r"[^a-z0-9]+", "-", head.strip().lower())
    return out.strip("-")


def relationship_slug(title: str) -> "str | None":
    """`Maggie and Cal` -> `cal--maggie`. None when there is no ` and `."""
    parts = _AND_RE.split(title.split(_EM_DASH, 1)[0].strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    left, right = slug(parts[0]), slug(parts[1])
    if not left or not right:
        return None
    return "--".join(sorted((left, right)))


def parse_background(text: str) -> dict:
    """Split the source on its heading contract (spec §3)."""
    stance_lines: list[str] = []
    entries: list[dict] = []
    unknown_parts: list[str] = []
    deep_headings: list[str] = []

    part: "str | None" = None
    current: "dict | None" = None
    buf: list[str] = []

    def flush():
        nonlocal current, buf
        if current is not None:
            current["body"] = "\n".join(buf).strip()
            entries.append(current)
        current, buf = None, []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if not m:
            if current is not None:
                buf.append(line)
            elif part == "Stance":
                stance_lines.append(line)
            continue

        level, title = len(m.group("hashes")), m.group("title")
        if level == 2:
            flush()
            part = title if title in PART_HEADINGS else None
            if title not in PART_HEADINGS:
                unknown_parts.append(title)
            continue
        if level >= 4:
            deep_headings.append(title)
            continue
        # level == 3
        flush()
        if part is None or part == "Stance":
            continue
        kind = KIND_BY_PART[part]
        s = relationship_slug(title) if kind == "relationship" else slug(title)
        current = {"part": part, "kind": kind, "title": title, "slug": s}

    flush()
    return {
        "stance": "\n".join(stance_lines).strip(),
        "entries": entries,
        "unknown_parts": unknown_parts,
        "deep_headings": deep_headings,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: all 11 PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/background_cut.py tests/test_background_cut.py
git commit -m "feat(background-cut): parse the background-history heading contract"
```

---

### Task 3: The five source-side blocking findings

**Files:**
- Modify: `scripts/background_cut.py`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: `parse_background(text) -> dict` from Task 2.
- Produces: `check_background(parsed: dict) -> dict` with keys `blocking` (list[str]) and `notes` (list[str]). Each finding string is `"<finding-id>: <detail>"`.

Findings owned by this task: `missing-stance`, `unknown-section`, `unknown-entry-depth`, `duplicate-entry`, `malformed-relationship`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_background_cut.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_background_cut.py -v -k "blocking or stance or unknown or duplicate or malformed"`
Expected: FAIL — `AttributeError: module 'scripts.background_cut' has no attribute 'check_background'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/background_cut.py`:

```python
def check_background(parsed: dict) -> dict:
    """Named findings over the parsed source (spec §5.2). No waivers."""
    blocking: list[str] = []
    notes: list[str] = []

    if not parsed["stance"].strip():
        blocking.append(
            "missing-stance: no `## Stance` block, or its body is empty — "
            "the setting pack is authored, not derived (spec §3.1)")

    for title in parsed["unknown_parts"]:
        blocking.append(
            f"unknown-section: `## {title}` is not one of "
            f"{', '.join(PART_HEADINGS)}")

    for title in parsed["deep_headings"]:
        blocking.append(
            f"unknown-entry-depth: `#### {title}` — entries are `###` only")

    seen: dict[str, str] = {}
    for e in parsed["entries"]:
        if e["slug"] is None:
            blocking.append(
                f"malformed-relationship: `### {e['title']}` has no ` and ` "
                f"separator")
            continue
        if e["slug"] in seen:
            blocking.append(
                f"duplicate-entry: `### {e['title']}` and "
                f"`### {seen[e['slug']]}` both slug to `{e['slug']}`")
            continue
        seen[e["slug"]] = e["title"]

    return {"blocking": blocking, "notes": notes}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/background_cut.py tests/test_background_cut.py
git commit -m "feat(background-cut): five source-side findings, no waivers"
```

---

### Task 4: Build the derived entries — links, bodies, stamps

**Files:**
- Modify: `scripts/background_cut.py`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: `parse_background`, `check_background`.
- Produces:
  - `body_sha(text: str) -> str` — sha256 hexdigest of the body, header excluded
  - `stamp(body: str, meta: dict) -> str` — prepends the `canon-meta` comment; `meta` values that are lists render as `[a, b]`
  - `build_entries(parsed: dict, source_sha: str) -> list[dict]` — each dict has `rel` (path relative to the series root, e.g. `series/continuity/background/maggie.md`) and `text` (the stamped file contents). Includes the setting-pack target at `config/setting-pack/setting.md`.

Link rule (spec §4.1): a relationship entry links to both its characters; a character entry links to every relationship whose slug contains it as a part. Town and secret entries have no automatic links.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_background_cut.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_background_cut.py -v -k "built or stamp or links or body_sha or targets"`
Expected: FAIL — `has no attribute 'build_entries'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/background_cut.py`:

```python
BACKGROUND_DIR = "series/continuity/background"
SETTING_PACK_REL = "config/setting-pack/setting.md"


def body_sha(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _fmt(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def stamp(body: str, meta: dict) -> str:
    """Prepend the canon-meta comment header. Comment form, not frontmatter —
    packet_assemble reads entries with parse_canon_meta, which only sees this
    form (spec §4)."""
    inner = ", ".join(f"{k}: {_fmt(v)}" for k, v in meta.items())
    return f"<!-- canon-meta: {{{inner}}} -->\n\n{body.strip()}\n"


def build_entries(parsed: dict, source_sha: str) -> list[dict]:
    """Emitted files for a parsed source. Assumes check_background is clean."""
    entries = [e for e in parsed["entries"] if e["slug"]]
    rel_slugs = {e["slug"] for e in entries if e["kind"] == "relationship"}

    def links_for(e: dict) -> list[str]:
        if e["kind"] == "relationship":
            return sorted(e["slug"].split("--"))
        if e["kind"] == "character":
            return sorted(r for r in rel_slugs
                          if e["slug"] in r.split("--"))
        return []

    out: list[dict] = []
    for e in entries:
        meta = {
            "id": e["slug"],
            "kind": e["kind"],
            "links": links_for(e),
            "source": f"{e['part'].lower()}-{e['slug']}",
            "built_from_background": source_sha,
            "cut_output_sha256": body_sha(e["body"]),
        }
        out.append({"rel": f"{BACKGROUND_DIR}/{e['slug']}.md",
                    "text": stamp(e["body"], meta)})

    stance = parsed["stance"]
    out.append({
        "rel": SETTING_PACK_REL,
        "text": stamp(stance, {
            "id": "setting-pack",
            "kind": "stance",
            "built_from_background": source_sha,
            "cut_output_sha256": body_sha(stance),
        }),
    })
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/background_cut.py tests/test_background_cut.py
git commit -m "feat(background-cut): build stamped entries with derived links"
```

---

### Task 5: Target-side guards and the orphan advisory

**Files:**
- Modify: `scripts/background_cut.py`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: `body_sha` from Task 4.
- Produces:
  - `target_refusal(existing_text: str, rel: str) -> str | None` — returns an `unstamped-target:` or `target-modified-since-cut:` finding string, or `None` when the file is safe to overwrite
  - `orphan_notes(existing_rels: list[str], produced_rels: list[str]) -> list[str]` — `orphan-derived:` advisory strings

- [ ] **Step 1: Write the failing test**

Append to `tests/test_background_cut.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_background_cut.py -v -k "target or orphan"`
Expected: FAIL — `has no attribute 'target_refusal'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/background_cut.py`:

```python
def target_refusal(existing_text: str, rel: str) -> "str | None":
    """Guard an existing file at a derived path (spec §5.1).

    An absent stamp is a refusal, not a licence: a file with no
    cut_output_sha256 was never produced by a cut, so it is hand-authored work
    and deleting it is the showrunner's explicit act — the same branch that
    protects a hand-authored outline.md.
    """
    meta = penny_meta.parse_canon_meta(existing_text)
    stamped = str(meta.get("cut_output_sha256", "")).strip()
    if not stamped:
        return (f"unstamped-target: {rel} has no cut_output_sha256 — it was "
                f"not produced by a cut. Delete it to adopt the layer.")
    body = existing_text.split("-->", 1)[1] if "-->" in existing_text else existing_text
    if body_sha(body) != stamped:
        return (f"target-modified-since-cut: {rel} was edited by hand since "
                f"the last cut. Move the change into background-history.md.")
    return None


def orphan_notes(existing_rels: list, produced_rels: list) -> list:
    """Advisory only — never deleted. A vanished heading is as likely to be a
    rename in progress as a deletion (spec §5.2)."""
    produced = set(produced_rels)
    return [
        f"orphan-derived: {rel} has no section in background-history.md. "
        f"It still loads into packets until you delete it."
        for rel in sorted(existing_rels) if rel not in produced
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/background_cut.py tests/test_background_cut.py
git commit -m "feat(background-cut): stamp guards refuse, orphans only advise"
```

---

### Task 6: CLI — read, guard, write, report

**Files:**
- Modify: `scripts/background_cut.py`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv=None) -> int`. Exit `0` clean, `1` findings, `2` usage or missing source. Invoked as `python3 scripts/background_cut.py` from a series root.

Order of operations, and it matters: parse → `check_background` → if blocking, print and return 1 **without writing anything** → guard every existing target → if any refusal, print and return 1 **without writing anything** → write all targets → print orphan advisories → return 0.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_background_cut.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_background_cut.py -v -k "cut_ or blocking_finding or unstamped_setting or recut or orphan_reported or missing_source or never_writes"`
Expected: FAIL — `has no attribute 'main'`.

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/background_cut.py`:

```python
SOURCE_REL = "input/series/background-history.md"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        print("usage: background_cut.py   (run from a series root)",
              file=sys.stderr)
        return 2

    root = penny_paths.series_root()
    src = root / SOURCE_REL
    if not src.is_file():
        print(f"background_cut: missing {src}", file=sys.stderr)
        return 2

    text = src.read_text(encoding="utf-8")
    parsed = parse_background(text)
    result = check_background(parsed)
    if result["blocking"]:
        for f in result["blocking"]:
            print(f)
        return 1

    built = build_entries(parsed, body_sha(text))

    refusals = []
    for b in built:
        p = root / b["rel"]
        if p.is_file():
            f = target_refusal(p.read_text(encoding="utf-8"), b["rel"])
            if f:
                refusals.append(f)
    if refusals:
        for f in refusals:
            print(f)
        return 1

    for b in built:
        p = root / b["rel"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(b["text"], encoding="utf-8")

    bg = root / BACKGROUND_DIR
    existing = ([f"{BACKGROUND_DIR}/{p.name}" for p in sorted(bg.glob("*.md"))]
                if bg.is_dir() else [])
    notes = orphan_notes(existing, [b["rel"] for b in built])

    print(f"background_cut: wrote {len(built)} files from {src}")
    if notes:
        print("\nAdvisory — nothing blocks on these:")
        for n in notes:
            print(f"  {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: all PASS.

Run: `python3 -m pytest`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/background_cut.py tests/test_background_cut.py
git commit -m "feat(background-cut): cli writes only when source and targets are both clean"
```

---

### Task 7: Background entries join the packet slice

**Files:**
- Modify: `scripts/packet_assemble.py:48`
- Test: `tests/test_packet_assemble.py`

**Interfaces:**
- Consumes: entries written by Task 6 at `series/continuity/background/<slug>.md`.
- Produces: `_CONTINUITY_SUBDIRS` gains `"background"`. No signature changes.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_packet_assemble.py`, matching the fixture style already used in that file (read `test_continuity_slice`-style tests there first and reuse their setup helper rather than inventing a new one):

```python
def test_background_entry_loads_when_named(tmp_path, monkeypatch):
    """A background entry named in the chapter lands in the packet, and its
    one-hop links pull the relationship entry with it."""
    bg = tmp_path / "series/continuity/background"
    bg.mkdir(parents=True)
    (bg / "maggie.md").write_text(
        "<!-- canon-meta: {id: maggie, kind: character, links: [cal--maggie]} -->\n\n"
        "A potter who does not perform fear.\n", encoding="utf-8")
    (bg / "cal--maggie.md").write_text(
        "<!-- canon-meta: {id: cal--maggie, kind: relationship, links: [cal, maggie]} -->\n\n"
        "Slow, and neither will name it first.\n", encoding="utf-8")
    (bg / "pruitt.md").write_text(
        "<!-- canon-meta: {id: pruitt, kind: character, links: []} -->\n\n"
        "Not in this chapter.\n", encoding="utf-8")

    out = packet_assemble._continuity_slice(tmp_path, "Maggie opens the studio.")
    assert "A potter who does not perform fear." in out
    assert "Slow, and neither will name it first." in out
    assert "Not in this chapter." not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_packet_assemble.py -v -k background`
Expected: FAIL — the background entry is absent from the slice, because `_CONTINUITY_SUBDIRS` does not include it.

- [ ] **Step 3: Write minimal implementation**

In `scripts/packet_assemble.py:48`:

```python
_CONTINUITY_SUBDIRS = ("characters", "locations", "threads", "background")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_packet_assemble.py -v`
Expected: all PASS.

Run: `python3 -m pytest`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/packet_assemble.py tests/test_packet_assemble.py
git commit -m "feat(packet): background entries join the continuity slice"
```

---

### Task 8: Agent inputs, rubric path, and docs

**Files:**
- Modify: `agents/drafter.md:49-51`, `agents/chapter-cutter.md:15-16`, `agents/outline-expander.md:29-31`, `agents/developmental-editor.md:17`, `agents/story-author.md`, `agents/plot-proposer.md`
- Modify: `config/review-rubrics/developmental-craft.md:30`
- Modify: `README.md`, `CLAUDE.md`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: the derived paths from Tasks 4 and 6.
- Produces: no code interfaces. A docs test pins the agent declarations.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_background_cut.py`:

```python
REPO = Path(__file__).resolve().parent.parent


def test_agents_declare_the_background_layer():
    for rel in ("agents/story-author.md", "agents/plot-proposer.md"):
        body = (REPO / rel).read_text(encoding="utf-8")
        assert "background" in body.lower(), f"{rel} does not declare background"


def test_setting_pack_consumers_do_not_name_a_place():
    """The engine ships no place name — the derived pack is setting.md."""
    for rel in ("agents/drafter.md", "agents/chapter-cutter.md",
                "agents/outline-expander.md",
                "config/review-rubrics/developmental-craft.md"):
        body = (REPO / rel).read_text(encoding="utf-8")
        assert "coastal-victoria-au" not in body, f"{rel} names a place"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_background_cut.py -v -k "agents_declare or do_not_name"`
Expected: `test_agents_declare_the_background_layer` FAILS (neither agent mentions background). `test_setting_pack_consumers_do_not_name_a_place` may already pass for some files — check each and fix any that fail.

- [ ] **Step 3: Write the edits**

In `agents/story-author.md`, add to its `**Inputs:**` list:

```markdown
- The `## Stance` block from `config/setting-pack/setting.md`, and the
  `series/continuity/background/` entries for the `@strand`s in the beat range
  being worked — a slice, never the whole background. An agent writing five
  beats does not need twelve character histories (design §4.2).
```

In `agents/plot-proposer.md`, add to its inputs:

```markdown
- `config/setting-pack/setting.md` — the series' stance. Derived from
  `input/series/background-history.md`; never edited directly.
```

In `agents/drafter.md`, `agents/chapter-cutter.md`, `agents/outline-expander.md`, `agents/developmental-editor.md`, and `config/review-rubrics/developmental-craft.md`: replace any reference to a named setting file (e.g. `config/setting-pack/coastal-victoria-au.md`) with `config/setting-pack/setting.md`, and leave generic `config/setting-pack/` directory references as they are. Read each file's surrounding sentence and keep its voice.

In `README.md`, under the setting-pack table rows, change the `config/setting-pack/<place>.md` row to:

```markdown
| `config/setting-pack/setting.md` | the setting pack — **derived**, cut from `input/series/background-history.md` |
```

and add to the `input/series/` paragraph that `background-history.md` is the authored source for the background layer.

In `CLAUDE.md`, add a short paragraph after the source-layer section:

```markdown
**The background layer** (spec `docs/superpowers/specs/2026-08-13-background-history-source-layer-design.md`):
`input/series/background-history.md` is one authored, series-level document — town
history, character histories, relationships, secrets — that `scripts/background_cut.py`
cuts into a flat `series/continuity/background/` and the derived
`config/setting-pack/setting.md`. The `## Stance` block is **authored, not compressed**:
the setting pack is loaded on every chapter and truncated at 2,500 chars on the LM Studio
path, and a lossy compression step would degrade silently. Seven blocking findings —
`missing-stance`, `unknown-section`, `unknown-entry-depth`, `duplicate-entry`,
`malformed-relationship`, `unstamped-target`, `target-modified-since-cut` — no waivers,
plus one advisory, `orphan-derived`, which never deletes. The cut **never** writes
`canon-core.md`, `continuity/characters/` (owned by `ledger-updater`), or any whodunit
ledger (per-book and sealed by the lock).
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v -k "agents_declare or do_not_name"`
Expected: both PASS.

Run: `python3 -m pytest`
Expected: all pass. If `tests/test_developmental_editor.py:60` or `tests/test_story_craft_doc.py:76` fail, they assert on the string `setting-pack`, which the edits preserve — re-read the assertion before changing the doc.

- [ ] **Step 5: Commit**

```bash
git add agents/ config/review-rubrics/developmental-craft.md README.md CLAUDE.md tests/test_background_cut.py
git commit -m "docs(background): agents read the derived pack, story-author gets a slice"
```

---

## Verification

After Task 8, from the engine repo:

```bash
python3 -m pytest
```

Expected: all pass (1018 before this plan, plus roughly 45 new).

Enumerate the finding roster **by reading the source**, never by grepping for finding strings — the `2026-08-12` plan's Step-5 grep produced exactly the wrong number and looked like confirmation:

```bash
python3 - <<'PY'
import inspect
from scripts import background_cut
src = inspect.getsource(background_cut)
print("read check_background, target_refusal and orphan_notes and count by hand")
PY
```

Confirm: seven strings appended to `blocking` across `check_background` and `target_refusal`; exactly one appended to `notes` (`orphan-derived`).

## Out of scope for this plan

Per spec §9 — do not build these, even if they seem natural while implementing:

- Per-book background copies, deltas, or a book tier in the config overlay.
- A `check` subcommand or `--dry-run` (`story_cut.py` has one; this spec does not call for it).
- A `kind`-aware hop limit in `_continuity_slice` (spec §4.1's accepted cost).
- Cross-checking secret ids against a book's whodunit ledger (spec §6.4).
- Migrating the cozy series' files — that is series work, spec §8, done by the showrunner.
- Converting the existing `continuity/characters/*.md` from frontmatter to canon-meta headers, even though one-hop linking is inert for them today (spec §4).
