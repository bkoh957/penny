# Penny Phase 4 — Prose Passes + Post-Gate Finalize — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the post-gate pipeline tail — line-edit + copy-edit passes, a hybrid ledger-updater (agent prose-body writes + a deterministic `ledger_markers.py`), and the `/finalize-chapter` command — plus the per-section `canon-meta` data contract that seeds the Phase-8 demotion `last_referenced` marker.

**Architecture:** Deterministic structured-field edits live in tested Python (`penny_meta.py` helpers + `ledger_markers.py`); semantic prose work lives in markdown agents (`line-editor`, `copy-editor`, `ledger-updater`). One `/finalize-chapter N CH` command orchestrates the tail after a deterministic gate guard (`preflight.py finalize`), with a `--commit` resume for the `ledger_approval: review` pause.

**Tech Stack:** Python 3 (stdlib only in the `/scripts` deterministic layer — no PyYAML in `penny_meta.py`/`ledger_markers.py`; `preflight.py` may use the existing `yaml` import), pytest, Claude Code agents + slash commands (markdown).

## Global Constraints

- **`/scripts` deterministic layer is dependency-free** except where a script already imports `yaml` (`preflight.py`). `penny_meta.py` and `ledger_markers.py` use **stdlib only**.
- **Every gate exits non-zero via `preflight: <named predicate>`** (the `_fail` convention) — gates never make an LLM judgment.
- **Tests are TDD**: write the failing test, watch it fail, implement minimal, watch it pass, commit. Run the whole suite (`python3 -m pytest -q`) before each commit; it must stay green (140 passing at plan start).
- **`repo_root` is injectable** on every script function that touches the filesystem (pattern: `*, repo_root=REPO`), so tests run against `tmp_path`.
- **canon-core prose body is never mutated by code** — only the HTML-comment `canon-meta` headers are edited. The drafter reads canon-core verbatim.
- **Commit messages** end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Chapter/book ids are zero-padded strings** in paths (`"01"`, `"07"`); `last_referenced`/`last_advanced_chapter` are stored as **bare ints** (`7`) per the demotion spec example.

---

### Task 1: Per-section `canon-meta` parser + header/frontmatter writers (`penny_meta.py`)

Foundation for the markers script and the canon-core data contract. Pure string functions, stdlib only.

**Files:**
- Modify: `scripts/penny_meta.py` (append new functions; leave existing ones untouched)
- Test: `tests/test_penny_meta.py` (append)

**Interfaces:**
- Consumes: existing `penny_meta._parse_kv_lines`, `_CANON_META_RE`.
- Produces:
  - `parse_canon_sections(text: str) -> list[dict]` — one dict per `##` section carrying a `canon-meta` header; each dict has `heading` plus parsed fields (`id`, `refs` as `list[str]`, etc.). File-level header (before the first `##`) excluded.
  - `write_canon_section_field(text: str, section_id: str, field: str, value) -> str` — set one `canon-meta` field of the section whose `id == section_id`; body bytes preserved; idempotent for repeated same-value stamps; raises `KeyError` if no such section.
  - `write_frontmatter_field(text: str, field: str, value) -> str` — set `field: value` in the leading `---` frontmatter; inserts at block end if absent; raises `ValueError` if no frontmatter block.

- [ ] **Step 1: Write failing tests for `parse_canon_sections`**

Append to `tests/test_penny_meta.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_meta.py -k canon_sections -v`
Expected: FAIL with `ImportError` / `AttributeError: parse_canon_sections`.

- [ ] **Step 3: Implement `parse_canon_sections`**

Append to `scripts/penny_meta.py`:

```python
_SECTION_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)


def parse_canon_sections(text: str) -> list[dict]:
    """Return one dict per ``##`` section that carries a ``canon-meta`` header.

    Each dict has ``heading`` (the ## title) plus the header's parsed fields
    (``id``, ``refs`` as a list, etc.). The file-level header that precedes the
    first ``##`` is excluded; sections without a canon-meta header are skipped.
    """
    out: list[dict] = []
    headings = list(_SECTION_RE.finditer(text))
    for i, h in enumerate(headings):
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        m = _CANON_META_RE.search(text[start:end])
        if not m:
            continue
        meta = _parse_kv_lines([part for part in m.group(1).split(",")])
        meta.setdefault("refs", [])
        meta["heading"] = h.group(1)
        out.append(meta)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_meta.py -k canon_sections -v`
Expected: PASS (2 tests).

Note: `_parse_kv_lines` already coerces `[cora-mistate]` → `["cora-mistate"]` and `[]` → `[]` via `_coerce`. The `refs` split inside `{...}` is safe because `_parse_kv_lines` splits on the top-level comma list produced by `m.group(1).split(",")` — but an inline list `[a, b]` contains a comma. **Guard:** the existing `parse_canon_meta` splits the same way and only supports flat scalars; for `refs: [a, b]` we must not split inside brackets. Verify with a two-element refs test:

```python
def test_parse_canon_sections_multi_ref_list():
    text = (
        "## S\n"
        "<!-- canon-meta: {id: s, refs: [a-one, b-two], active_window: \"1-3\"} -->\n"
        "- body\n"
    )
    secs = parse_canon_sections(text)
    assert secs[0]["refs"] == ["a-one", "b-two"]
```

If this fails (comma inside `[...]` split the list), fix by splitting top-level commas only. Add this helper above `parse_canon_sections` and use it instead of `m.group(1).split(",")`:

```python
def _split_top_level(inner: str) -> list[str]:
    """Split on commas that are not inside an inline ``[...]`` list."""
    parts, depth, buf = [], 0, []
    for ch in inner:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts
```

Then in `parse_canon_sections`: `meta = _parse_kv_lines(_split_top_level(m.group(1)))`.

- [ ] **Step 5: Run the multi-ref test and the whole meta suite**

Run: `python3 -m pytest tests/test_penny_meta.py -v`
Expected: PASS (all, including pre-existing `parse_canon_meta` tests — regression check).

- [ ] **Step 6: Write failing tests for the two writers**

Append:

```python
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
```

- [ ] **Step 7: Run to verify they fail**

Run: `python3 -m pytest tests/test_penny_meta.py -k "write_canon or write_frontmatter" -v`
Expected: FAIL (`AttributeError`).

- [ ] **Step 8: Implement the two writers**

Append to `scripts/penny_meta.py`:

```python
def _fmt_meta_value(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _set_inline_field(inner: str, field: str, value: str) -> str:
    """Update or insert ``field: value`` inside a canon-meta inner string,
    normalizing to a single space. Other fields are preserved byte-for-byte."""
    pat = re.compile(rf"\b{re.escape(field)}\s*:\s*[^,}}]*")
    if pat.search(inner):
        return pat.sub(f"{field}: {value}", inner, count=1)
    sep = ", " if inner.strip() else ""
    return inner.rstrip() + f"{sep}{field}: {value}"


def write_canon_section_field(text: str, section_id: str, field: str, value) -> str:
    """Set the canon-meta ``field`` of the ``##`` section whose id is
    ``section_id``. Preserves body bytes. Idempotent on repeated same-value
    stamps. Raises KeyError if no section has that id."""
    val = _fmt_meta_value(value)
    headings = list(_SECTION_RE.finditer(text))
    for i, h in enumerate(headings):
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        m = _CANON_META_RE.search(text[start:end])
        if not m:
            continue
        inner = m.group(1)
        if _parse_kv_lines(_split_top_level(inner)).get("id") != section_id:
            continue
        new_inner = _set_inline_field(inner, field, val)
        abs_start, abs_end = start + m.start(1), start + m.end(1)
        return text[:abs_start] + new_inner + text[abs_end:]
    raise KeyError(f"no canon-core section with id {section_id!r}")


def write_frontmatter_field(text: str, field: str, value) -> str:
    """Set ``field: value`` in the leading ``---`` frontmatter block, preserving
    the body. Inserts the field at the block end if absent. Raises ValueError if
    there is no frontmatter block."""
    val = _fmt_meta_value(value)
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block")
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if close is None:
        raise ValueError("unterminated frontmatter block")
    pat = re.compile(rf"^\s*{re.escape(field)}\s*:.*$")
    for i in range(1, close):
        if pat.match(lines[i].rstrip("\n")):
            nl = "\n" if lines[i].endswith("\n") else ""
            lines[i] = f"{field}: {val}{nl}"
            return "".join(lines)
    lines.insert(close, f"{field}: {val}\n")
    return "".join(lines)
```

- [ ] **Step 9: Run to verify they pass**

Run: `python3 -m pytest tests/test_penny_meta.py -v`
Expected: PASS (all).

- [ ] **Step 10: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add scripts/penny_meta.py tests/test_penny_meta.py
git commit -m "$(printf 'feat(meta): per-section canon-meta parser + header/frontmatter writers\n\nparse_canon_sections + write_canon_section_field (idempotent, body-preserving)\n+ write_frontmatter_field, for the Phase-4 ledger markers.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: Author per-section `canon-meta` headers on `canon-core.md`

Lay down the data contract on the real file. `active_window` values are the showrunner's to confirm — the values below are defensible defaults (permanent/meta facts get `"1-13"`; setup facts that fade get a short window).

**Files:**
- Modify: `series/continuity/canon-core.md`
- Test: `tests/test_canon_core_contract.py` (create)

**Interfaces:**
- Consumes: `parse_canon_sections` (Task 1).
- Produces: a `canon-core.md` whose 4 `##` sections each carry a `canon-meta` header with `id`, `refs`, `active_window`, `last_referenced: null`, `reconfirmed_at: null`, `keep_reason: null`.

- [ ] **Step 1: Write the failing contract test**

Create `tests/test_canon_core_contract.py`:

```python
from pathlib import Path

from scripts.penny_meta import parse_canon_meta, parse_canon_sections

CANON = Path(__file__).resolve().parents[1] / "series/continuity/canon-core.md"
REQUIRED = {"id", "refs", "active_window", "last_referenced", "reconfirmed_at", "keep_reason"}


def test_every_section_has_full_canon_meta_header():
    text = CANON.read_text(encoding="utf-8")
    secs = parse_canon_sections(text)
    assert len(secs) == 4
    for s in secs:
        assert REQUIRED <= set(s), f"{s.get('id')} missing {REQUIRED - set(s)}"


def test_file_level_fluency_stage_preserved():
    meta = parse_canon_meta(CANON.read_text(encoding="utf-8"))
    assert meta.get("id") == "canon-core"
    assert meta.get("fluency_stage") == "OUTSIDER"


def test_protagonist_section_refs_the_protagonist():
    secs = parse_canon_sections(CANON.read_text(encoding="utf-8"))
    prot = next(s for s in secs if s["id"] == "protagonist-fixed")
    assert "cora-mistate" in prot["refs"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_canon_core_contract.py -v`
Expected: FAIL (`len(secs) == 4` is 0 — no section headers yet).

- [ ] **Step 3: Add the per-section headers**

Edit `series/continuity/canon-core.md` so each `##` section gains a header immediately under it. Final file:

```markdown
---
id: canon-core
type: thread
links: []
---
<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->
# Canon Core — always loaded every chapter (design §4.2)

Keep this small: every line is a tax on every chapter. Holds only what is always
relevant.

## Protagonist fixed facts
<!-- canon-meta: {id: protagonist-fixed, refs: [cora-mistate], active_window: "1-2", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- **Cora Mistate**, 44, recently divorced, relocated from Melbourne to the town of
  Wreckers Bluff. Outsider. Fluency stage tracked below.

## Current timeline position
<!-- canon-meta: {id: current-timeline, refs: [], active_window: "1-13", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Book 01, pre-draft. Season: late autumn. No deaths yet recorded.

## Active-book whodunit constraints
<!-- canon-meta: {id: whodunit-constraints, refs: [], active_window: "1-13", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- None locked yet (authored per book by `/plan-mystery`, Phase 3).

## Fluency stage (design §9 newcomer dial)
<!-- canon-meta: {id: fluency-stage, refs: [cora-mistate], active_window: "1-2", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- **OUTSIDER** (Books 1–2): narration is standard English; local idiom lives in
  other characters' mouths, never Cora's narration.
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_canon_core_contract.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Confirm `lock-mystery` stage-drift still parses canon-core**

The lock path reads canon-core for fluency-stage drift (`preflight.cmd_lock_mystery` → `stage_drift`). Verify nothing broke:

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: PASS.

- [ ] **Step 6: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add series/continuity/canon-core.md tests/test_canon_core_contract.py
git commit -m "$(printf 'feat(canon): per-section canon-meta headers + authored active_window\n\nSeeds the demotion data contract (spec 2026-06-20, §7.1) at the capture\nwindow. active_window values are showrunner-adjustable.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

> **Review note for the showrunner:** confirm the four `active_window` values — `protagonist-fixed: "1-2"`, `fluency-stage: "1-2"`, `current-timeline: "1-13"`, `whodunit-constraints: "1-13"`. These are unrecoverable later (only capturable at promotion).

---

### Task 3: `ledger_markers.py` — `last_referenced` mechanical scan + stamp

**Files:**
- Create: `scripts/ledger_markers.py`
- Test: `tests/test_ledger_markers.py` (create)

**Interfaces:**
- Consumes: `penny_meta.parse_canon_sections`, `penny_meta.write_canon_section_field`.
- Produces:
  - `referenced_section_ids(canon_text: str, brief_text: str, chapter_text: str) -> list[str]` — section ids whose any `refs` token appears in brief or chapter text.
  - `stamp_last_referenced(canon_text: str, chapter: int, brief_text: str, chapter_text: str) -> str` — updated canon text with `last_referenced=chapter` on every referenced section; ref-less sections untouched.

- [ ] **Step 1: Write failing tests**

Create `tests/test_ledger_markers.py`:

```python
from scripts import ledger_markers as lm

CANON = """# Canon Core
<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->

## Protagonist fixed facts
<!-- canon-meta: {id: protagonist-fixed, refs: [cora-mistate], active_window: "1-2", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Cora.

## Current timeline position
<!-- canon-meta: {id: current-timeline, refs: [], active_window: "1-13", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- Book 01.
"""

BRIEF_REFS = "POV: cora-mistate. Beats: she arrives at the-bluff.\n"
BRIEF_NONE = "POV: thomas. Beats: a stranger appears.\n"


def test_referenced_when_ref_in_brief():
    ids = lm.referenced_section_ids(CANON, BRIEF_REFS, "prose with no ids")
    assert ids == ["protagonist-fixed"]            # current-timeline has empty refs


def test_not_referenced_when_absent():
    assert lm.referenced_section_ids(CANON, BRIEF_NONE, "prose") == []


def test_stamp_writes_chapter_on_referenced_only():
    out = lm.stamp_last_referenced(CANON, 7, BRIEF_REFS, "prose")
    from scripts.penny_meta import parse_canon_sections
    secs = {s["id"]: s for s in parse_canon_sections(out)}
    assert secs["protagonist-fixed"]["last_referenced"] == "7"
    assert secs["current-timeline"]["last_referenced"] == "null"   # untouched


def test_stamp_is_idempotent():
    once = lm.stamp_last_referenced(CANON, 7, BRIEF_REFS, "prose")
    twice = lm.stamp_last_referenced(once, 7, BRIEF_REFS, "prose")
    assert once == twice                            # byte-identical re-application


def test_stamp_leaves_body_bytes_intact():
    out = lm.stamp_last_referenced(CANON, 7, BRIEF_REFS, "prose")
    assert "- Cora." in out and "- Book 01." in out
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_ledger_markers.py -v`
Expected: FAIL (`ModuleNotFoundError: scripts.ledger_markers`).

- [ ] **Step 3: Implement the module**

Create `scripts/ledger_markers.py`:

```python
"""Deterministic post-gate recency markers (Phase 4; design §4.3, §4.5).

Stamps structured-field markers that are mechanically detectable — no LLM:
  - last_referenced  on canon-core section headers (id-scan of brief + text)
  - last_advanced_chapter  on thread frontmatter (driven by the updater's flag)

Structured-field editing is fiddly and is the Phase-8 demotion precision seed,
so it lives in tested Python, not in the ledger-updater agent's prose output.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_canon_sections, write_canon_section_field


def referenced_section_ids(canon_text: str, brief_text: str, chapter_text: str) -> list[str]:
    """Section ids whose any ``refs`` token appears (substring) in the brief or
    chapter text. Sections with empty refs are never referenced."""
    hay = f"{brief_text}\n{chapter_text}"
    out: list[str] = []
    for sec in parse_canon_sections(canon_text):
        refs = sec.get("refs") or []
        if any(ref and ref in hay for ref in refs):
            out.append(sec["id"])
    return out


def stamp_last_referenced(canon_text: str, chapter: int, brief_text: str,
                          chapter_text: str) -> str:
    """Return canon_text with ``last_referenced=chapter`` set on every referenced
    section. Ref-less / unreferenced sections are left untouched."""
    text = canon_text
    for sec_id in referenced_section_ids(canon_text, brief_text, chapter_text):
        text = write_canon_section_field(text, sec_id, "last_referenced", int(chapter))
    return text
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest tests/test_ledger_markers.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add scripts/ledger_markers.py tests/test_ledger_markers.py
git commit -m "$(printf 'feat(markers): ledger_markers.py last_referenced mechanical scan + stamp\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 4: `ledger_markers.py` — `last_advanced_chapter` thread stamp + CLI

Extends the module with the thread marker (driven by the updater's `advanced` flag) and a CLI for the command to call.

**Files:**
- Modify: `scripts/ledger_markers.py`
- Test: `tests/test_ledger_markers.py` (append)

**Interfaces:**
- Consumes: `penny_meta.write_frontmatter_field` (Task 1); Task 3 functions.
- Produces:
  - `stamp_thread_advanced(thread_text: str, chapter: int) -> str` — set `last_advanced_chapter=chapter` in a thread file's frontmatter.
  - CLI: `python3 scripts/ledger_markers.py NN CH --brief P --text P --canon P [--thread-advanced PATH ...]` — stamps canon-core in place and each named thread file in place; prints a one-line summary; exit 0.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ledger_markers.py`:

```python
THREAD = "---\nid: the-inheritance\ntype: thread\nlinks: [the-bluff]\n---\n# Thread\n- Status: OPEN.\n"


def test_stamp_thread_advanced_sets_frontmatter():
    out = lm.stamp_thread_advanced(THREAD, 4)
    assert "last_advanced_chapter: 4" in out
    assert "- Status: OPEN." in out                 # body intact


def test_stamp_thread_advanced_idempotent():
    once = lm.stamp_thread_advanced(THREAD, 4)
    assert lm.stamp_thread_advanced(once, 4) == once


def test_cli_stamps_canon_and_thread_in_place(tmp_path):
    canon = tmp_path / "canon-core.md"
    canon.write_text(CANON, encoding="utf-8")
    brief = tmp_path / "brief.md"
    brief.write_text(BRIEF_REFS, encoding="utf-8")
    text = tmp_path / "ch.md"
    text.write_text("prose", encoding="utf-8")
    thread = tmp_path / "the-inheritance.md"
    thread.write_text(THREAD, encoding="utf-8")

    rc = lm.main([
        "01", "07",
        "--canon", str(canon), "--brief", str(brief), "--text", str(text),
        "--thread-advanced", str(thread),
    ])
    assert rc == 0
    assert "last_referenced: 7" in canon.read_text(encoding="utf-8")
    assert "last_advanced_chapter: 7" in thread.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_ledger_markers.py -k "thread_advanced or cli" -v`
Expected: FAIL (`AttributeError: stamp_thread_advanced` / `main`).

- [ ] **Step 3: Implement the thread stamp + CLI**

Append to `scripts/ledger_markers.py` (add the import at the top alongside the existing one):

```python
from scripts.penny_meta import write_frontmatter_field  # add to the existing import line


def stamp_thread_advanced(thread_text: str, chapter: int) -> str:
    """Return thread_text with ``last_advanced_chapter=chapter`` in its frontmatter."""
    return write_frontmatter_field(thread_text, "last_advanced_chapter", int(chapter))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Penny post-gate recency markers.")
    ap.add_argument("book")
    ap.add_argument("chapter")
    ap.add_argument("--canon", required=True)
    ap.add_argument("--brief", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--thread-advanced", action="append", default=[],
                    help="thread file path the updater flagged advanced (repeatable)")
    args = ap.parse_args(argv)
    ch = int(args.chapter)

    canon_p = Path(args.canon)
    canon_p.write_text(
        stamp_last_referenced(
            canon_p.read_text(encoding="utf-8"), ch,
            Path(args.brief).read_text(encoding="utf-8"),
            Path(args.text).read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    for tp in args.thread_advanced:
        p = Path(tp)
        p.write_text(stamp_thread_advanced(p.read_text(encoding="utf-8"), ch),
                     encoding="utf-8")
    print(f"markers: canon last_referenced<-{ch}; "
          f"{len(args.thread_advanced)} thread(s) advanced<-{ch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Keep the existing top-of-file import readable, e.g.:

```python
from scripts.penny_meta import (
    parse_canon_sections,
    write_canon_section_field,
    write_frontmatter_field,
)
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest tests/test_ledger_markers.py -v`
Expected: PASS (all).

- [ ] **Step 5: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add scripts/ledger_markers.py tests/test_ledger_markers.py
git commit -m "$(printf 'feat(markers): last_advanced_chapter thread stamp + ledger_markers CLI\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 5: `preflight.py finalize N CH` gate guard

A 4th preflight subcommand: refuse to finalize unless the chapter's gate PASSed.

**Files:**
- Modify: `scripts/preflight.py` (add `cmd_finalize` + wire the subparser + docstring)
- Test: `tests/test_preflight.py` (append)

**Interfaces:**
- Consumes: `penny_meta.parse_frontmatter` (already imported), `preflight._fail`.
- Produces: `cmd_finalize(book: str, chapter: str, *, repo_root=REPO) -> int` — reads `output/book-NN/chapters/ch-CH.gate.md`; `_fail` unless its frontmatter `gate == "PASS"`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_preflight.py`:

```python
def _make_gate(root, book, ch, verdict):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.gate.md").write_text(
        f"---\nproducer: review_gate.py\nkind: gate-summary\n"
        f"target: book-{book}/ch-{ch}\ngate: {verdict}\nblocking_count: 0\n"
        f"schema: penny-verdict/1\n---\n\n- {verdict}: 0 blocking issue(s)\n",
        encoding="utf-8",
    )


def test_finalize_passes_on_passing_gate(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    assert preflight.cmd_finalize("01", "07", repo_root=tmp_path) == 0


def test_finalize_blocks_on_held_gate(tmp_path):
    _make_gate(tmp_path, "01", "07", "HOLD")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "did not pass" in str(e.value)


def test_finalize_blocks_when_gate_missing(tmp_path):
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "no gate" in str(e.value)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_preflight.py -k finalize -v`
Expected: FAIL (`AttributeError: cmd_finalize`).

- [ ] **Step 3: Implement `cmd_finalize` + wire it**

Add to `scripts/preflight.py` after `cmd_draft`:

```python
def gate_path(book: str, chapter: str, repo_root) -> Path:
    return (Path(repo_root) / "output" / f"book-{book}" / "chapters"
            / f"ch-{chapter}.gate.md")


def cmd_finalize(book: str, chapter: str, *, repo_root=REPO) -> int:
    gp = gate_path(book, chapter, repo_root)
    if not gp.is_file():
        _fail(f"no gate for book {book} ch {chapter} ({gp}) — run /review-chapter first")
    gate = parse_frontmatter(gp.read_text(encoding="utf-8")).get("gate")
    if gate != "PASS":
        _fail(f"chapter {book}/{chapter} did not pass the gate (gate: {gate}); "
              f"resolve the HOLD before finalizing")
    return 0
```

Wire the subparser in `main` (mirroring `draft`):

```python
    p_fin = sub.add_parser("finalize", help="post-gate guard: chapter must have PASSed")
    p_fin.add_argument("book")
    p_fin.add_argument("chapter")
```

And the dispatch:

```python
    if args.cmd == "finalize":
        return cmd_finalize(args.book, args.chapter)
```

Update the module docstring's subcommand list to add the `finalize` line.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest tests/test_preflight.py -k finalize -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "$(printf 'feat(preflight): finalize gate guard — refuse unless gate PASS\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 6: Prose-pass agents + config modules + ledger-updater agent

The semantic layer: three agents and two config modules (markdown). Tested by scaffold-presence assertions, matching `tests/test_inspector_scaffold.py`.

**Files:**
- Create: `.claude/agents/line-editor.md`, `.claude/agents/copy-editor.md`, `.claude/agents/ledger-updater.md`
- Create: `config/line-edit/line-edit.md`, `config/copy-edit/copy-edit.md`
- Test: `tests/test_prose_pass_scaffold.py` (create)

**Interfaces:**
- Consumes: nothing (markdown).
- Produces: agent + config files the `/finalize-chapter` command (Task 7) dispatches/reads.

- [ ] **Step 1: Inspect the existing agent + scaffold-test pattern**

Read `.claude/agents/drafter.md`, `.claude/agents/_TEMPLATE.md`, and `tests/test_inspector_scaffold.py` to match the frontmatter shape (`name`, `description`, `tools`) and the kind of assertions used (file exists; key sections present; key invariants named in prose).

- [ ] **Step 2: Write the failing scaffold test**

Create `tests/test_prose_pass_scaffold.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude/agents"
CONFIG = ROOT / "config"


def test_prose_pass_files_exist():
    for p in [
        AGENTS / "line-editor.md",
        AGENTS / "copy-editor.md",
        AGENTS / "ledger-updater.md",
        CONFIG / "line-edit/line-edit.md",
        CONFIG / "copy-edit/copy-edit.md",
    ]:
        assert p.is_file(), f"missing {p}"


def test_copy_editor_is_fresh_context():
    text = (AGENTS / "copy-editor.md").read_text(encoding="utf-8").lower()
    assert "style sheet" in text or "style-sheet" in text
    assert "drafting history" in text          # must state it never sees it


def test_ledger_updater_states_its_guards():
    text = (AGENTS / "ledger-updater.md").read_text(encoding="utf-8").lower()
    assert "write-scope" in text or "loaded slice" in text   # bounded writes
    assert "canon-core" in text                              # never mutates body
    assert "advanced" in text                                # emits per-thread flag
```

- [ ] **Step 3: Run to verify it fails**

Run: `python3 -m pytest tests/test_prose_pass_scaffold.py -v`
Expected: FAIL (files missing).

- [ ] **Step 4: Author the five files**

`.claude/agents/line-editor.md` — frontmatter `name: line-editor`, a one-line `description`, `tools: All tools` (match sibling agents). Body states: inputs (draft text, Voice Pack, length profile); job (rhythm, word choice, flow, cut flab, strengthen verbs, **preserve voice and meaning**); hard constraints (no new content, no plot/continuity/mystery changes; output is revised prose only); points to `config/line-edit/line-edit.md`.

`.claude/agents/copy-editor.md` — `name: copy-editor`. Body states: **fresh context — given only the text + `series/style-sheet.md`, never the drafting history**; job (grammar, punctuation, consistency against the style sheet); writes corrected prose **and** appends new decisions to `series/style-sheet.md`; points to `config/copy-edit/copy-edit.md`.

`.claude/agents/ledger-updater.md` — `name: ledger-updater`. Body states: literal/extractive post-gate record-keeper (design §4.3); inputs (finalized text, brief, the **same loaded slice**); writes **prose-body only**, **write-scope bounded to the loaded slice** (knowledge-state for present characters → `series/continuity/characters/<id>.md`; new canonical facts → the entry's "Established facts"); **guards**: never mutates `canon-core` body (promotion is a showrunner act; markers are the script's job), never judges thread liveness (the structure inspector's job); **emits per in-slice thread an `advanced: yes/no` line in `ch-CH.ledger-diff.md`** for `ledger_markers.py` to consume.

`config/line-edit/line-edit.md` — the line-edit rubric/instruction module (`[STABLE]`, design §7): what to refine and what to leave alone; a short checklist of prose-refinement moves.

`config/copy-edit/copy-edit.md` — the copy-edit rubric/instruction module (`[STABLE]`): grammar/punctuation/consistency scope, Australian spelling per the style sheet, and the rule to append (never overwrite) style-sheet decisions.

- [ ] **Step 5: Run to verify it passes**

Run: `python3 -m pytest tests/test_prose_pass_scaffold.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add .claude/agents/line-editor.md .claude/agents/copy-editor.md .claude/agents/ledger-updater.md config/line-edit/line-edit.md config/copy-edit/copy-edit.md tests/test_prose_pass_scaffold.py
git commit -m "$(printf 'feat(prose): line-editor + copy-editor + ledger-updater agents and configs\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 7: `/finalize-chapter` command + touch-ups (roster, thread seed, draft preamble)

Wires the orchestrator and updates the two existing seams. The command is markdown; the touch-ups are content + a doc-note test.

**Files:**
- Create: `.claude/commands/finalize-chapter.md`
- Modify: `series/continuity/threads/the-inheritance.md` (seed `last_advanced_chapter`)
- Modify: `.claude/commands/review-chapter.md` (roster from real marker; null = silent)
- Modify: `.claude/commands/draft-chapter.md` (refresh stale preamble)
- Test: `tests/test_finalize_command.py` (create)

**Interfaces:**
- Consumes: `preflight.py finalize` (Task 5), `ledger_markers.py` (Task 4), the three agents (Task 6).
- Produces: the user-facing `/finalize-chapter N CH [--commit]` command.

- [ ] **Step 1: Write the failing command/doc test**

Create `tests/test_finalize_command.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_finalize_command_exists_and_wires_the_tail():
    text = (ROOT / ".claude/commands/finalize-chapter.md").read_text(encoding="utf-8").lower()
    assert "preflight.py finalize" in text          # gate guard step 0
    assert "ledger_markers.py" in text              # markers step
    assert "line-editor" in text and "copy-editor" in text and "ledger-updater" in text
    assert "--commit" in text                       # resume path documented
    assert "ledger-review" in text                  # the review pause stage


def test_finalize_refuses_rerun_without_commit_flag():
    text = (ROOT / ".claude/commands/finalize-chapter.md").read_text(encoding="utf-8").lower()
    # the no-flag refusal guard must be described
    assert "refus" in text and "ledger-review" in text


def test_review_chapter_roster_uses_real_marker_and_treats_null_silent():
    text = (ROOT / ".claude/commands/review-chapter.md").read_text(encoding="utf-8").lower()
    assert "last_advanced_chapter" in text
    assert "unknown" not in text or "null" in text  # no longer the unknown placeholder
    assert "null" in text                           # null = no liveness flag


def test_thread_seed_has_marker_field():
    text = (ROOT / "series/continuity/threads/the-inheritance.md").read_text(encoding="utf-8")
    assert "last_advanced_chapter" in text


def test_draft_preamble_refreshed():
    text = (ROOT / ".claude/commands/draft-chapter.md").read_text(encoding="utf-8").lower()
    assert "no review bus yet" not in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_finalize_command.py -v`
Expected: FAIL (command missing; markers/preamble assertions unmet).

- [ ] **Step 3: Author `.claude/commands/finalize-chapter.md`**

Frontmatter: `description:` (the post-gate tail, one line), `argument-hint: <book-number> <chapter-number> [--commit]`. Body — the steps from spec §4.1, with exact commands:

- **Step 0 — gate guard:** ```python3 scripts/preflight.py finalize $1 $2``` (abort on non-zero).
- **`--commit` resume branch (handle first):** if invoked with `--commit`, assert `.penny/current-stage` shows `stage=LEDGER-REVIEW` for this chapter, then **git-commit the already-written working tree** (`output/book-$book/chapters/ch-$chapter.final.md`, the continuity writes, `series/style-sheet.md`, canon-core + thread marker edits), set `stage=FINALIZED`, and stop. **Run no agents.**
- **No-flag refusal guard:** if no `--commit` and the chapter is already at `stage=LEDGER-REVIEW`, **refuse** and instruct the showrunner to run `/finalize-chapter $1 $2 --commit` (re-running would re-edit prose non-idempotently and discard the reviewed text).
- **Step 1 — LINE-EDIT:** write `stage=LINE-EDIT`; dispatch `line-editor` with `ch-$chapter.draft.md` + Voice Pack + length profile → `ch-$chapter.lineedit.md`.
- **Step 2 — COPY-EDIT:** write `stage=COPY-EDIT`; dispatch `copy-editor` with **only** `ch-$chapter.lineedit.md` + `series/style-sheet.md` → `ch-$chapter.copyedit.md`; appends decisions to the style sheet.
- **Step 3 — FINALIZE:** write `stage=FINALIZE`; dispatch `ledger-updater` (prose-body writes within the loaded slice; emits per-thread `advanced: yes/no` in `ch-$chapter.ledger-diff.md`); then run the markers, passing each advanced thread file:
  ```bash
  python3 scripts/ledger_markers.py $book $chapter \
    --canon series/continuity/canon-core.md \
    --brief <chapter brief path> --text output/book-$book/chapters/ch-$chapter.copyedit.md \
    --thread-advanced <thread file> ...
  ```
- **Step 4 — promote:** copy `ch-$chapter.copyedit.md` → `ch-$chapter.final.md` (carry frontmatter).
- **Step 5 — ledger_approval branch** (read `ledger_approval` from `config/run-config.md`):
  - `auto`: git-commit the chapter end-to-end; `stage=FINALIZED`.
  - `review`: **pause** — surface `ch-$chapter.ledger-diff.md`, tell the showrunner to review `git diff` then run `/finalize-chapter $1 $2 --commit`; `stage=LEDGER-REVIEW`; **no commit**.

- [ ] **Step 4: Seed the thread marker**

Edit `series/continuity/threads/the-inheritance.md` frontmatter to add `last_advanced_chapter:` (unset/blank value is fine — author it as `last_advanced_chapter:` with no value, or omit value). To keep the parser happy and the intent explicit, write it as a commented intent line is NOT allowed in frontmatter; instead add the key with an empty value:

```yaml
---
id: the-inheritance
type: thread
links: [the-bluff, cora-mistate]
last_advanced_chapter:
---
```

- [ ] **Step 5: Update `review-chapter.md` step 6**

Replace the current step-6 text (which sets `last_advanced_chapter` to `unknown`) with: build the roster `[{thread_id, last_advanced_chapter}]` from each thread file's real frontmatter `last_advanced_chapter`; **a missing/empty value maps to `null`, which `inspector-structure` treats as "no advancement recorded yet" → no dormancy flag** (identical to the prior `unknown` behaviour, but now reading real data populated by `/finalize-chapter`).

- [ ] **Step 6: Refresh `draft-chapter.md` preamble**

Update the `description:` and the opening line so they no longer say "Phase 1: no review bus yet" — state the current reality (draft step of the full pipeline; review via `/review-chapter`, finalize via `/finalize-chapter`).

- [ ] **Step 7: Run to verify it passes**

Run: `python3 -m pytest tests/test_finalize_command.py -v`
Expected: PASS (5 tests).

- [ ] **Step 8: Run the whole suite and commit**

Run: `python3 -m pytest -q`
Expected: all green.

```bash
git add .claude/commands/finalize-chapter.md .claude/commands/review-chapter.md .claude/commands/draft-chapter.md series/continuity/threads/the-inheritance.md tests/test_finalize_command.py
git commit -m "$(printf 'feat(finalize): /finalize-chapter command + roster/thread/preamble touch-ups\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Self-Review (completed during planning)

**Spec coverage:**
- §4.1 `/finalize-chapter` + `--commit` resume + no-flag guard → Task 7 (+ guard tests).
- §4.2 line-editor, §4.3 copy-editor, §4.4 ledger-updater → Task 6.
- §4.5 `ledger_markers.py` (last_referenced mechanical scan + `refs`) → Task 3.
- §4.5 `last_advanced_chapter` from `advanced` flag → Task 4.
- §4.6 `preflight finalize` guard → Task 5.
- §4.7 per-section `canon-meta` + `refs` + `active_window` + `parse_canon_sections`/writers → Tasks 1–2.
- §5 review-chapter roster (null = silent) + draft preamble → Task 7.
- §7 resume/idempotency seams → Task 1 (idempotent writers) + Task 3/4 (idempotency tests) + Task 7 (resume/refusal).
- §8 testing focus → tests across Tasks 1–7 (round-trip, id-scan, write-scope, re-application idempotency, body-intact, gate guard).

**Out-of-scope items NOT planned (correct):** self-audit/Tier-B, demotion detector/executor, `active_window` consumption, beta layer.

**Placeholder scan:** Task 6 file *contents* are described as authoring instructions (markdown prose, not code) — acceptable, since these are agent/config prose whose exact wording is editorial; the scaffold tests pin the load-bearing invariants. All code steps carry complete code.

**Type consistency:** `parse_canon_sections`/`write_canon_section_field`/`write_frontmatter_field`/`_split_top_level`/`_set_inline_field`/`_fmt_meta_value` (Task 1) match their uses in Tasks 3–4; `stamp_last_referenced`/`stamp_thread_advanced`/`referenced_section_ids`/`main` (Tasks 3–4) match their command call in Task 7; `cmd_finalize`/`gate_path` (Task 5) match the preflight wiring. Markers store bare ints; parsed values read back as strings (`"7"`) — tests assert the string form.
