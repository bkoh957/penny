# Penny Phase 6 — Book Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn gate-PASSed, finalized chapters into a finished, cross-model-reviewed `book-NN.manuscript.md` plus the showrunner-facing artifacts (final read + revision-priority report) that gate book approval.

**Architecture:** Phase 6 is deliberately deterministic-heavy. A new `scripts/assemble_book.py` produces the manuscript and validates the final-read shape; `scripts/revision_priority.py` aggregates the Phase-5 beta outputs + per-chapter gate logs into a raw-threshold escalate/log report; the one genuine judgment is the cross-model `final-reader` agent, whose output is shape-enforced by a deterministic validator. A `/assemble-book` command orchestrates and pauses for showrunner approval, minting an out-of-band `book-NN.approved` certificate.

**Tech Stack:** Python 3 stdlib (`argparse`, `json`, `ast`, `datetime`, `pathlib`); `scripts/penny_meta.py` for dependency-free frontmatter/yaml-block parsing; PyYAML only where already used; pytest. Markdown for agents/commands.

## Global Constraints

- **Engine is genre/location-agnostic.** New behavior goes in `scripts/` (engine), `.claude/` (orchestration), or `config/` (swappable) — never hardcode project content in scripts. (CLAUDE.md)
- **Scripts never make an LLM judgment.** Every deterministic miss exits nonzero via a named predicate `assemble_book: <predicate>` / `revision_priority: <predicate>` / `preflight: <predicate>`, mirroring the existing `preflight:` convention. (CLAUDE.md, spec §4)
- **Deterministic layer uses `scripts/penny_meta.py`, not PyYAML**, for frontmatter / fenced ```yaml blocks. PyYAML is only for nested human-edited data (whodunit ledgers, lexicon). (CLAUDE.md)
- **Certificates are out-of-band.** A lock/approval cert exists only because validation passed; never represent "approved" as a field inside the data it gates. The cert-minting write is the script's *last* write. (CLAUDE.md, spec §5)
- **Cross-model independence is difference, not identity:** `final_read_model` / `read_by` must not appear in the manuscript's `drafted_by` set. (CLAUDE.md, spec §2/§3)
- **The report escalates on RAW threshold crossings only** — never a derived/blended severity score. Every emitted line names the rule that fired plus its raw counts. (spec §2, §3 Unit 4)
- **`penny-final-read/1` enumerated booleans are `yes|no` only** — a hedge like `mostly` must hard-fail the validator. (spec §3 Unit 3)
- **Test-first against `tests/fixtures/`.** `pytest.ini` sets `pythonpath=.`; run `python3 -m pytest`. (CLAUDE.md)
- Tests must stay green: the suite is currently **189 passing**.

---

## File structure

| File | Responsibility | New/Modify |
|---|---|---|
| `scripts/penny_meta.py` | add `strip_frontmatter(text)` body-extractor (shared by manuscript prose-strip + converged-JSON read) | Modify |
| `scripts/assemble_book.py` | manuscript producer (`assemble`/`seal`), final-read validator (`validate-read` + `validate_final_read()`) | Create |
| `scripts/revision_priority.py` | deterministic aggregator → `reports/revision-priority.md` | Create |
| `scripts/canon_core_review.py` | reserved Phase-8 demotion hook — no-op returning `[]` | Create |
| `scripts/preflight.py` | add `approve-book NN` precondition subcommand + cert mint | Modify |
| `config/run-config.md` | add 3 flags: `revision_escalate_personas`, `would_buy_escalate_count`, `book_approval` | Modify |
| `.claude/agents/final-reader.md` | cross-model informed holistic-read agent (emits `penny-final-read/1`) | Create |
| `.claude/commands/assemble-book.md` | orchestrator: assemble → preflight gate → final read → validate → report → pause/approve → demotion hook | Create |
| `tests/test_assemble_book.py` | assemble golden + fails, seal, validate_final_read | Create |
| `tests/test_revision_priority.py` | threshold boundaries, traceability, cross-consistency w/ beta_report | Create |
| `tests/test_canon_core_review.py` | hook returns `[]` with exact args | Create |
| `tests/test_preflight.py` | add approve-book precondition + cert-mint tests | Modify |

---

## Task 1: `strip_frontmatter` helper + manuscript producer (`assemble`)

**Files:**
- Modify: `scripts/penny_meta.py` (add `strip_frontmatter`)
- Create: `scripts/assemble_book.py`
- Test: `tests/test_assemble_book.py`

**Interfaces:**
- Consumes: `penny_meta.parse_frontmatter`, `penny_meta.write_frontmatter_field` (existing).
- Produces:
  - `penny_meta.strip_frontmatter(text: str) -> str` — returns the body after a leading `---` block (leading blank lines stripped); returns `text` unchanged if no frontmatter.
  - `assemble_book.cmd_assemble(book: str, *, repo_root=REPO, now=None) -> int` — writes `output/book-NN/book-NN.manuscript.md`; `now` is an optional `datetime` for deterministic `assembled_at`.
  - `assemble_book.manuscript_path(book, repo_root) -> Path`, `assemble_book.chapters_dir(book, repo_root) -> Path`, `assemble_book._fail(predicate)`.
  - Manuscript frontmatter: `schema: penny-manuscript/1`, `book`, `chapters`, `drafted_by: [sorted union]`, `assembled_at`. `read_by` ABSENT at assembly.

- [ ] **Step 1: Write the failing test for `strip_frontmatter`**

```python
# tests/test_assemble_book.py
from datetime import datetime, timezone

import pytest

from scripts import assemble_book, penny_meta


def test_strip_frontmatter_returns_body():
    text = "---\nschema: x\ndrafted_by: claude-opus\n---\n\nHello world.\n"
    assert penny_meta.strip_frontmatter(text) == "Hello world.\n"


def test_strip_frontmatter_no_frontmatter_is_identity():
    assert penny_meta.strip_frontmatter("Hello.\n") == "Hello.\n"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_assemble_book.py -k strip_frontmatter -v`
Expected: FAIL — `AttributeError: module 'scripts.penny_meta' has no attribute 'strip_frontmatter'`

- [ ] **Step 3: Add `strip_frontmatter` to `scripts/penny_meta.py`**

Append at end of file:

```python
def strip_frontmatter(text: str) -> str:
    """Return the body after a leading ``---`` frontmatter block, with leading
    blank lines removed. If there is no frontmatter block, return ``text`` as-is."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1:]).lstrip("\n")
    return text
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_assemble_book.py -k strip_frontmatter -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Write the failing test for `assemble` (golden + asserts)**

Add a fixture helper and golden test:

```python
def _make_chapter(chapters_dir, num, drafted_by, body):
    chapters_dir.mkdir(parents=True, exist_ok=True)
    text = (f"---\nschema: penny-chapter/1\ntarget: book-99/ch-{num:02d}\n"
            f"drafted_by: {drafted_by}\n---\n\n{body}\n")
    (chapters_dir / f"ch-{num:02d}.final.md").write_text(text, encoding="utf-8")


def _book_tree(tmp_path, book="99"):
    return tmp_path / "output" / f"book-{book}" / "chapters"


FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def test_assemble_produces_manuscript(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "Chapter one prose.")
    _make_chapter(chapters, 2, "codex", "Chapter two prose.")
    assert assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW) == 0
    man = assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8")
    fm = penny_meta.parse_frontmatter(man)
    assert fm["schema"] == "penny-manuscript/1"
    assert fm["book"] == "99"
    assert fm["chapters"] == "2"
    assert fm["drafted_by"] == ["claude-opus", "codex"]   # sorted union
    assert fm["assembled_at"] == "2026-06-21T12:00:00+00:00"
    assert "read_by" not in fm                             # absent until seal
    body = penny_meta.strip_frontmatter(man)
    assert body == ("# Chapter 1\n\nChapter one prose.\n\n"
                    "# Chapter 2\n\nChapter two prose.\n")
```

- [ ] **Step 6: Run to verify it fails**

Run: `python3 -m pytest tests/test_assemble_book.py -k test_assemble_produces -v`
Expected: FAIL — `module 'scripts.assemble_book' has no attribute ...` (module does not exist yet)

- [ ] **Step 7: Create `scripts/assemble_book.py` with `assemble`**

```python
"""Per-book manuscript producer + final-read shape validator (Phase 6).

Deterministic — never an LLM judgment. Three subcommands:

    assemble NN       build output/book-NN/book-NN.manuscript.md from ch-*.final.md
    seal NN           stamp read_by (from the final read) into the manuscript
    validate-read NN  hard-fail a malformed penny-final-read/1 artifact

Every miss exits non-zero via `assemble_book: <named predicate>`, mirroring
`preflight:`. The manuscript has one path but three states: assembled -> read
(seal) -> blessed (preflight approve-book mints the cert).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import (parse_frontmatter, strip_frontmatter,
                                 write_frontmatter_field)

REPO = Path(__file__).resolve().parents[1]
MANUSCRIPT_SCHEMA = "penny-manuscript/1"
FINAL_READ_SCHEMA = "penny-final-read/1"
FINAL_READ_BOOLEANS = ("standalone", "mystery_resolved", "thread_left_open")
ENUM = {"yes", "no"}


def _fail(predicate: str):
    sys.exit(f"assemble_book: {predicate}")


def book_dir(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}"


def chapters_dir(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / "chapters"


def manuscript_path(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / f"book-{book}.manuscript.md"


def final_read_path(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / f"book-{book}.final-read.md"


def _chapter_num(path: Path) -> int:
    # ch-07.final.md -> 7
    return int(path.name[len("ch-"):].split(".")[0])


def _stamps(value) -> set[str]:
    if isinstance(value, list):
        return {s for s in value if s}
    if isinstance(value, str) and value:
        return {value}
    return set()


def cmd_assemble(book: str, *, repo_root=REPO, now=None) -> int:
    cdir = chapters_dir(book, repo_root)
    finals = sorted(cdir.glob("ch-*.final.md"), key=_chapter_num)
    if not finals:
        _fail(f"no finalized chapters for book {book} ({cdir}/ch-*.final.md)")
    nums = [_chapter_num(p) for p in finals]
    expected = list(range(1, len(nums) + 1))
    if nums != expected:
        missing = sorted(set(expected) - set(nums))
        _fail(f"chapters not contiguous for book {book}: have {nums}, "
              f"missing {missing}")
    drafted: set[str] = set()
    bodies: list[str] = []
    for p in finals:
        text = p.read_text(encoding="utf-8")
        stamp = parse_frontmatter(text).get("drafted_by")
        if not _stamps(stamp):
            _fail(f"{p.name} missing drafted_by stamp")
        drafted |= _stamps(stamp)
        n = _chapter_num(p)
        bodies.append(f"# Chapter {n}\n\n{strip_frontmatter(text).rstrip(chr(10))}\n")
    # outline count guard (only if outline.md declares one).
    outline = book_dir(book, repo_root) / "outline.md"
    if outline.is_file():
        declared = parse_frontmatter(outline.read_text(encoding="utf-8")).get("chapters")
        if declared is not None and str(declared) != str(len(nums)):
            _fail(f"outline declares {declared} chapters but {len(nums)} finalized")
    ts = (now or datetime.now(timezone.utc)).isoformat()
    drafted_inline = "[" + ", ".join(sorted(drafted)) + "]"
    front = ("---\n"
             f"schema: {MANUSCRIPT_SCHEMA}\n"
             f"book: {book}\n"
             f"chapters: {len(nums)}\n"
             f"drafted_by: {drafted_inline}\n"
             f"assembled_at: {ts}\n"
             "---\n\n")
    out = manuscript_path(book, repo_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(front + "\n".join(bodies), encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny per-book manuscript producer.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_asm = sub.add_parser("assemble", help="build the manuscript from ch-*.final.md")
    p_asm.add_argument("book")
    args = ap.parse_args(argv)
    if args.cmd == "assemble":
        return cmd_assemble(args.book)
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8: Run to verify the golden test passes**

Run: `python3 -m pytest tests/test_assemble_book.py -v`
Expected: PASS (all)

- [ ] **Step 9: Write the failing fail-path tests**

```python
def test_assemble_fails_on_gap(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    _make_chapter(chapters, 3, "codex", "three")        # gap at 2
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "not contiguous" in str(e.value)


def test_assemble_fails_on_zero_chapters(tmp_path):
    _book_tree(tmp_path).mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "no finalized chapters" in str(e.value)


def test_assemble_fails_on_missing_drafted_by(tmp_path):
    chapters = _book_tree(tmp_path)
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / "ch-01.final.md").write_text(
        "---\nschema: penny-chapter/1\n---\n\nbody\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "missing drafted_by" in str(e.value)


def test_assemble_fails_on_outline_count_mismatch(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    (tmp_path / "output" / "book-99" / "outline.md").write_text(
        "---\nchapters: 2\n---\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "outline declares 2" in str(e.value)
```

- [ ] **Step 10: Run to verify the fail-path tests pass**

Run: `python3 -m pytest tests/test_assemble_book.py -v`
Expected: PASS (all) — the implementation from Step 7 already covers these predicates.

- [ ] **Step 11: Commit**

```bash
git add scripts/penny_meta.py scripts/assemble_book.py tests/test_assemble_book.py
git commit -m "feat(assemble): manuscript producer + strip_frontmatter helper"
```

---

## Task 2: `seal` subcommand (stamp `read_by`)

**Files:**
- Modify: `scripts/assemble_book.py`
- Test: `tests/test_assemble_book.py`

**Interfaces:**
- Consumes: `manuscript_path`, `final_read_path`, `_stamps`, `parse_frontmatter`, `write_frontmatter_field` (Task 1).
- Produces: `assemble_book.cmd_seal(book: str, *, repo_root=REPO) -> int` — reads `read_by` from `book-NN.final-read.md`, asserts `read_by ∉ manuscript.drafted_by`, stamps `read_by` into the manuscript frontmatter. Idempotent on the same value.

- [ ] **Step 1: Write the failing tests**

```python
def _seal_setup(tmp_path, read_by="codex"):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assemble_book.final_read_path("99", tmp_path).write_text(
        f"---\nschema: penny-final-read/1\nread_by: {read_by}\n"
        f"standalone: yes\nmystery_resolved: yes\nthread_left_open: yes\n---\n"
        "## Holistic verdict\nGood.\n", encoding="utf-8")


def test_seal_stamps_read_by(tmp_path):
    _seal_setup(tmp_path, read_by="codex")
    assert assemble_book.cmd_seal("99", repo_root=tmp_path) == 0
    fm = penny_meta.parse_frontmatter(
        assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8"))
    assert fm["read_by"] == "codex"


def test_seal_is_idempotent(tmp_path):
    _seal_setup(tmp_path, read_by="codex")
    assert assemble_book.cmd_seal("99", repo_root=tmp_path) == 0
    first = assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8")
    assert assemble_book.cmd_seal("99", repo_root=tmp_path) == 0     # re-seal = no-op
    assert assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8") == first


def test_seal_rejects_read_by_in_drafted_by(tmp_path):
    _seal_setup(tmp_path, read_by="claude-opus")     # claude-opus drafted ch-01
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_seal("99", repo_root=tmp_path)
    assert "appears in drafted_by" in str(e.value)


def test_seal_fails_when_final_read_absent(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_seal("99", repo_root=tmp_path)
    assert "no final-read artifact" in str(e.value)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_assemble_book.py -k seal -v`
Expected: FAIL — `module 'scripts.assemble_book' has no attribute 'cmd_seal'`

- [ ] **Step 3: Implement `cmd_seal` in `scripts/assemble_book.py`**

Add after `cmd_assemble`:

```python
def cmd_seal(book: str, *, repo_root=REPO) -> int:
    man = manuscript_path(book, repo_root)
    if not man.is_file():
        _fail(f"no manuscript to seal for book {book} ({man}) — run assemble first")
    fr = final_read_path(book, repo_root)
    if not fr.is_file():
        _fail(f"no final-read artifact for book {book} ({fr}) — run the final read first")
    read_by = parse_frontmatter(fr.read_text(encoding="utf-8")).get("read_by")
    if not read_by:
        _fail(f"final-read artifact has no read_by stamp ({fr})")
    man_text = man.read_text(encoding="utf-8")
    drafted = _stamps(parse_frontmatter(man_text).get("drafted_by"))
    if read_by in drafted:
        _fail(f"read_by '{read_by}' appears in drafted_by set {sorted(drafted)}")
    man.write_text(write_frontmatter_field(man_text, "read_by", read_by),
                   encoding="utf-8")
    return 0
```

Wire the subcommand in `main`, before `ap.error`:

```python
    p_seal = sub.add_parser("seal", help="stamp read_by from the final read")
    p_seal.add_argument("book")
```

and in the dispatch block:

```python
    if args.cmd == "seal":
        return cmd_seal(args.book)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_assemble_book.py -k seal -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/assemble_book.py tests/test_assemble_book.py
git commit -m "feat(assemble): seal stamps read_by into the manuscript"
```

---

## Task 3: `validate_final_read` + `validate-read` subcommand + `final-reader` agent

**Files:**
- Modify: `scripts/assemble_book.py`
- Create: `.claude/agents/final-reader.md`
- Test: `tests/test_assemble_book.py`

**Interfaces:**
- Consumes: `final_read_path`, `parse_frontmatter`, `FINAL_READ_SCHEMA`, `FINAL_READ_BOOLEANS`, `ENUM` (Task 1).
- Produces: `assemble_book.validate_final_read(book: str, *, repo_root=REPO) -> int` — hard-fails (SystemExit `assemble_book:`) a malformed `penny-final-read/1` artifact; returns 0 if valid. Exposed as `validate-read NN`. Reusable by `preflight.py approve-book` (Task 6).

- [ ] **Step 1: Write the failing tests**

```python
def _write_final_read(tmp_path, *, schema="penny-final-read/1", read_by="codex",
                      standalone="yes", mystery_resolved="yes", thread_left_open="yes"):
    book_dir = tmp_path / "output" / "book-99"
    book_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"schema: {schema}"]
    if read_by is not None:
        lines.append(f"read_by: {read_by}")
    if standalone is not None:
        lines.append(f"standalone: {standalone}")
    if mystery_resolved is not None:
        lines.append(f"mystery_resolved: {mystery_resolved}")
    if thread_left_open is not None:
        lines.append(f"thread_left_open: {thread_left_open}")
    lines += ["---", "", "## Holistic verdict", "Reads well.", ""]
    (book_dir / "book-99.final-read.md").write_text("\n".join(lines), encoding="utf-8")


def test_validate_read_accepts_enum(tmp_path):
    _write_final_read(tmp_path)
    assert assemble_book.validate_final_read("99", repo_root=tmp_path) == 0


def test_validate_read_rejects_hedge(tmp_path):
    _write_final_read(tmp_path, standalone="mostly")     # the hedge
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "standalone" in str(e.value) and "mostly" in str(e.value)


def test_validate_read_rejects_missing_boolean(tmp_path):
    _write_final_read(tmp_path, thread_left_open=None)
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "thread_left_open" in str(e.value)


def test_validate_read_rejects_missing_read_by(tmp_path):
    _write_final_read(tmp_path, read_by=None)
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "read_by" in str(e.value)


def test_validate_read_rejects_bad_schema(tmp_path):
    _write_final_read(tmp_path, schema="penny-beta/1")
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "schema" in str(e.value)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_assemble_book.py -k validate_read -v`
Expected: FAIL — `module 'scripts.assemble_book' has no attribute 'validate_final_read'`

- [ ] **Step 3: Implement `validate_final_read` in `scripts/assemble_book.py`**

Add after `cmd_seal`:

```python
def validate_final_read(book: str, *, repo_root=REPO) -> int:
    fr = final_read_path(book, repo_root)
    if not fr.is_file():
        _fail(f"no final-read artifact for book {book} ({fr})")
    fm = parse_frontmatter(fr.read_text(encoding="utf-8"))
    if fm.get("schema") != FINAL_READ_SCHEMA:
        _fail(f"final-read schema is {fm.get('schema')!r}, expected {FINAL_READ_SCHEMA!r}")
    if not fm.get("read_by"):
        _fail(f"final-read missing read_by stamp ({fr})")
    for field in FINAL_READ_BOOLEANS:
        val = fm.get(field)
        if val not in ENUM:
            _fail(f"final-read field {field!r} is {val!r}, must be one of {sorted(ENUM)} "
                  f"(no hedging)")
    return 0
```

Wire the subcommand in `main`:

```python
    p_val = sub.add_parser("validate-read", help="hard-fail a malformed final read")
    p_val.add_argument("book")
```

and the dispatch:

```python
    if args.cmd == "validate-read":
        return validate_final_read(args.book)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_assemble_book.py -k validate_read -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Create `.claude/agents/final-reader.md`**

```markdown
---
name: final-reader
description: Cross-model informed holistic read — the one genuine Phase-6 judgment; emits penny-final-read/1 with enumerated standalone-vs-arc booleans + a prose verdict.
---
# Final Reader

**Role posture:** the single cross-model holistic read of the assembled book
(design §5, §7, §10). This is QC, not a reader-proxy — so, **unlike the blind beta
readers (which get only text), the final reader is INFORMED.** Seeing the solution
does not compromise independence: the value is "drawer time" — a model that did NOT
*draft* this prose reads it whole.

**Independence (load-bearing):** you MUST be a model that did not draft any chapter.
The harness enforces `read_by ∉ drafted_by` (`preflight.py assemble`); your output
stamps `read_by` so it can.

**Inputs:** `{ manuscript_text, mystery_solution (the book-NN whodunit), arc-ledger
slice (which thread is the intended series hook) }`. The solution makes
`mystery_resolved` reliable against ground truth; the arc slice is REQUIRED to judge
`thread_left_open` (unjudgeable from prose alone).

**Output:** `output/book-NN/book-NN.final-read.md`, `schema: penny-final-read/1`.
Frontmatter MUST carry, with these EXACT enumerated values (a hedge like `mostly`
hard-fails `assemble_book.py validate-read`):

```
---
schema: penny-final-read/1
read_by: <your model id>
standalone: yes|no          # does the book hold together as one satisfying read?
mystery_resolved: yes|no    # is the whodunit fairly and fully resolved?
thread_left_open: yes|no    # is the intended personal/series thread left open as a hook?
---
## Holistic verdict
<the qualitative cross-model taste read — the reason this pass exists.>

## Standalone-vs-arc notes
<the prose backing the three booleans above.>
```

**Instructions:**

1. Read the manuscript whole, as one book, not chapter-by-chapter.
2. Cross-check the resolution against `mystery_solution`; set `mystery_resolved`.
3. Using the arc-ledger slice, decide whether the intended series-hook thread is left
   open; set `thread_left_open`. Decide whether the book stands alone; set `standalone`.
4. Write `## Holistic verdict` (taste) and `## Standalone-vs-arc notes` (the prose
   behind the booleans). Booleans live ALONGSIDE the prose, never in place of it.
5. The booleans are `yes|no` ONLY. If you are tempted to hedge, choose the answer the
   evidence most supports and explain the nuance in the prose section.
```

- [ ] **Step 6: Commit**

```bash
git add scripts/assemble_book.py .claude/agents/final-reader.md tests/test_assemble_book.py
git commit -m "feat(final-read): penny-final-read/1 validator + cross-model final-reader agent"
```

---

## Task 4: `canon_core_review.py` — reserved demotion hook (no-op)

**Files:**
- Create: `scripts/canon_core_review.py`
- Test: `tests/test_canon_core_review.py`

**Interfaces:**
- Produces: `canon_core_review.review(book: str, canon_core: str) -> list` — returns `[]` in Phase 6. CLI: `--book NN --canon-core <path>`, prints the candidate list as JSON. The Phase-8 candidate shape is `{id, fact, last_referenced, active_window, verdict, proposed_target}`; empty now.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_canon_core_review.py
import json

from scripts import canon_core_review


def test_review_returns_empty_candidate_list(tmp_path):
    canon = tmp_path / "canon-core.md"
    canon.write_text("# canon\n", encoding="utf-8")
    assert canon_core_review.review("99", str(canon)) == []


def test_cli_prints_empty_json_list(capsys, tmp_path):
    canon = tmp_path / "canon-core.md"
    canon.write_text("# canon\n", encoding="utf-8")
    rc = canon_core_review.main(["--book", "99", "--canon-core", str(canon)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_canon_core_review.py -v`
Expected: FAIL — `No module named 'scripts.canon_core_review'`

- [ ] **Step 3: Create `scripts/canon_core_review.py`**

```python
"""Reserved per-book demotion hook (Phase-6 no-op; Phase-8 fills the body).

Per the canon-core demotion design §7.1, coldness is a cross-book property that
cannot fire on Book 1 — so the per-book review cadence is a *hook* only. This
script exists, takes the exact Phase-8 args (`--book`, `--canon-core`), and returns
an empty candidate list. The interface is pinned so Phase 8 fills in the detector
body with no engine edit. The Phase-8 candidate shape is:

    {id, fact, last_referenced, active_window, verdict, proposed_target}
"""
from __future__ import annotations

import argparse
import json


def review(book: str, canon_core: str) -> list:
    """Return demotion candidates for `book`. Phase 6: always empty (no behavior)."""
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Per-book canon-core demotion review (reserved).")
    ap.add_argument("--book", required=True)
    ap.add_argument("--canon-core", required=True)
    args = ap.parse_args(argv)
    print(json.dumps(review(args.book, args.canon_core)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_canon_core_review.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/canon_core_review.py tests/test_canon_core_review.py
git commit -m "feat(demotion): reserved Phase-6 canon-core-review hook (no-op)"
```

---

## Task 5: `revision_priority.py` — the aggregator + 2 config flags

**Files:**
- Create: `scripts/revision_priority.py`
- Modify: `config/run-config.md` (add `revision_escalate_personas`, `would_buy_escalate_count`)
- Test: `tests/test_revision_priority.py`

**Interfaces:**
- Consumes: `penny_meta.parse_yaml_blocks`, `penny_meta.strip_frontmatter` (Task 1); `beta_report.write_converged` / `build_raw_reading` / `collapse_persona` (existing, for the cross-consistency test).
- Produces:
  - `revision_priority.aggregate(book: str, *, repo_root=REPO, config_path=None) -> dict` — returns `{"escalate": [str], "log": [str]}` (the emitted report lines).
  - `revision_priority.cmd_report(book, *, repo_root=REPO, config_path=None) -> int` — writes `output/book-NN/reports/revision-priority.md`; always returns 0 (non-blocking).
  - `revision_priority.report_path(book, repo_root) -> Path`.
- Report schema: `penny-revision-priority/1`, frontmatter `escalations: <count>`, sections `## ESCALATE` / `## LOG`. Every line names its rule + raw counts.

**Note on inputs (verified against the code):**
- `output/book-NN/reports/<persona>.converged.md` — `---` frontmatter then a JSON body (`beta_report.serialize_converged`). Read with `strip_frontmatter` → `json.loads`. Fields used: `persona`, `put_down_points.{consensus,logged}` (chapter ints), `would_buy_next.tally.no` (int).
- `output/book-NN/chapters/ch-*.gate.md` — `score_spread_log` is written by `review_gate.write_gate_md` as a body line `- score_spread_log: [<python-repr list of dicts>]`. Parse with `ast.literal_eval` of the text after the colon.

- [ ] **Step 1: Add the two flags to `config/run-config.md`**

In the "Escalation thresholds (design §6)" ```yaml block, append after `score_spread_log_threshold`:

```yaml
revision_escalate_personas: 2             # >=N distinct personas flag a put-down at a chapter -> escalate; tunable
would_buy_escalate_count:   3             # >=N personas say "would not buy next" -> escalate; tunable
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_revision_priority.py
import json

import pytest

from scripts import beta_report, revision_priority


def _write_converged(reports_dir, persona, *, consensus=None, logged=None, no=0):
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "penny-beta/1", "persona": persona,
        "driver": beta_report.DRIVER_BY_PERSONA[persona],
        "panel": {"m": 2, "k": 2, "panel_size": 2,
                  "distinct_models": ["a", "b"], "degraded": False},
        "engagement_curve": [],
        "put_down_points": {"consensus": consensus or [], "logged": logged or []},
        "would_buy_next": {"tally": {"yes": 0, "no": no, "n/a": 0}, "denominator": 2},
    }
    beta_report.write_converged(reports_dir, report)


def _write_gate(chapters_dir, chapter, score_spread_log):
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (chapters_dir / f"ch-{chapter:02d}.gate.md").write_text(
        "---\nproducer: review_gate.py\nkind: gate-summary\n"
        f"target: book-99/ch-{chapter:02d}\ngate: PASS\nblocking_count: 0\n"
        "schema: penny-verdict/1\n---\n\n- PASS: 0 blocking issue(s)\n"
        "- escalations: []\n"
        f"- score_spread_log: {score_spread_log!r}\n", encoding="utf-8")


def _book99(tmp_path):
    return (tmp_path / "output" / "book-99" / "reports",
            tmp_path / "output" / "book-99" / "chapters")


def _config(tmp_path, personas=2, would_buy=3):
    cfg = tmp_path / "run-config.md"
    cfg.write_text(f"```yaml\nrevision_escalate_personas: {personas}\n"
                   f"would_buy_escalate_count: {would_buy}\n```\n", encoding="utf-8")
    return cfg


def test_putdown_below_threshold_is_log(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "puzzle-hawk", consensus=[3])     # 1 persona at ch.3
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, personas=2))
    assert any("cross_persona_putdown<2" in ln and "ch.3" in ln for ln in res["log"])
    assert not any("ch.3" in ln for ln in res["escalate"])


def test_putdown_at_threshold_escalates(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "puzzle-hawk", consensus=[7])
    _write_converged(reports, "cozy-loyalist", logged=[7])      # 2 distinct personas at ch.7
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, personas=2))
    line = next(ln for ln in res["escalate"] if "ch.7" in ln)
    assert "cross_persona_putdown>=2" in line
    assert "2 personas" in line
    assert "cozy-loyalist" in line and "puzzle-hawk" in line   # named + sorted


def test_would_buy_no_at_threshold_escalates(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "puzzle-hawk", no=1)
    _write_converged(reports, "cozy-loyalist", no=1)
    _write_converged(reports, "arc-reader", no=1)               # total no = 3
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, would_buy=3))
    line = next(ln for ln in res["escalate"] if "would-buy" in ln)
    assert "would_buy_no>=3" in line and "3" in line


def test_score_spread_is_log_only(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_gate(chapters, 5, [{"producer": "inspector-voice", "spread": 2}])
    res = revision_priority.aggregate("99", repo_root=tmp_path, config_path=_config(tmp_path))
    line = next(ln for ln in res["log"] if "score-spread" in ln)
    assert "ch.5" in line and "inspector-voice" in line and "spread 2" in line
    assert not res["escalate"]


def test_all_clean_has_no_escalations(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "cozy-loyalist", no=0)
    _write_gate(chapters, 1, [])
    rc = revision_priority.cmd_report("99", repo_root=tmp_path, config_path=_config(tmp_path))
    assert rc == 0
    text = revision_priority.report_path("99", tmp_path).read_text(encoding="utf-8")
    assert "escalations: 0" in text


def test_cross_consistency_with_beta_report(tmp_path):
    """Build a converged report the real way (beta_report) and feed it straight in:
    the aggregator must parse the exact shape write_converged emits."""
    reports, chapters = _book99(tmp_path)
    raws = [beta_report.build_raw_reading(
        persona="impatient-skimmer", model=m,
        engagement_curve=[{"chapter": 4, "score": 2}],
        put_down_points=[4], whodunit_guess={"name": "x", "chapter": 9},
        confusion_points=[], emotional_beats=["dread"], would_buy_verdict="no")
        for m in ("a", "b")]
    converged = beta_report.collapse_persona(raws, k=2, panel_size=2)
    beta_report.write_converged(reports, converged)
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, personas=1, would_buy=2))
    assert any("ch.4" in ln for ln in res["escalate"])          # 1 persona, threshold 1
    assert any("would-buy" in ln for ln in res["escalate"])     # tally.no=2, threshold 2
```

- [ ] **Step 3: Run to verify they fail**

Run: `python3 -m pytest tests/test_revision_priority.py -v`
Expected: FAIL — `No module named 'scripts.revision_priority'`

- [ ] **Step 4: Create `scripts/revision_priority.py`**

```python
"""Deterministic revision-priority aggregator (Phase 6, design §10).

Pure reader over three already-structured signals — cross-persona put-down counts,
would-buy-next tallies, accumulated score spreads. Escalate-vs-log is RAW threshold
arithmetic; it NEVER computes a blended/derived severity score (that would smuggle
judgment back into the deterministic layer). Every emitted line names the rule that
fired plus its raw counts, so the showrunner sees *why* it escalated, not just that
it did. Non-blocking: always exits 0; the escalations inform the human gate.

Inputs (shapes verified against the producers):
  - output/book-NN/reports/<persona>.converged.md  (beta_report.serialize_converged:
    frontmatter + JSON body; put_down_points.{consensus,logged}, would_buy_next.tally.no)
  - output/book-NN/chapters/ch-*.gate.md            (review_gate.write_gate_md:
    body line `- score_spread_log: [<repr list of dicts>]`)
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_yaml_blocks, strip_frontmatter

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "penny-revision-priority/1"


def _fail(predicate: str):
    sys.exit(f"revision_priority: {predicate}")


def book_dir(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}"


def report_path(book: str, repo_root) -> Path:
    return book_dir(book, repo_root) / "reports" / "revision-priority.md"


def _load_thresholds(config_path) -> dict:
    cfg = parse_yaml_blocks(Path(config_path).read_text(encoding="utf-8"))
    try:
        return {"personas": int(cfg["revision_escalate_personas"]),
                "would_buy": int(cfg["would_buy_escalate_count"])}
    except (KeyError, ValueError) as exc:
        _fail(f"run-config missing/non-numeric revision_escalate_personas or "
              f"would_buy_escalate_count ({exc})")


def _load_converged(reports_dir) -> list[dict]:
    out = []
    for path in sorted(Path(reports_dir).glob("*.converged.md")):
        try:
            out.append(json.loads(strip_frontmatter(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, ValueError) as exc:
            _fail(f"malformed converged report {path.name}: {exc}")
    return out


def _score_spreads(chapters_dir) -> list[tuple[int, dict]]:
    """Return (chapter, entry) for every score_spread_log entry across gate.md files."""
    out = []
    for path in sorted(Path(chapters_dir).glob("ch-*.gate.md")):
        chapter = int(path.name[len("ch-"):].split(".")[0])
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("- score_spread_log:"):
                raw = s[len("- score_spread_log:"):].strip()
                try:
                    entries = ast.literal_eval(raw) if raw else []
                except (ValueError, SyntaxError) as exc:
                    _fail(f"unparsable score_spread_log in {path.name}: {exc}")
                for e in entries:
                    out.append((chapter, e))
    return out


def aggregate(book: str, *, repo_root=REPO, config_path=None) -> dict:
    config_path = config_path or (Path(repo_root) / "config/run-config.md")
    th = _load_thresholds(config_path)
    converged = _load_converged(book_dir(book, repo_root) / "reports")

    # Rule 1 — cross_persona_putdown: per chapter, count DISTINCT personas with a
    # put-down (consensus or logged). >= threshold -> ESCALATE else LOG.
    by_chapter: dict[int, set[str]] = {}
    for rep in converged:
        persona = rep["persona"]
        pd = rep.get("put_down_points", {})
        for ch in set(pd.get("consensus", [])) | set(pd.get("logged", [])):
            by_chapter.setdefault(int(ch), set()).add(persona)

    escalate, log = [], []
    for ch in sorted(by_chapter):
        personas = sorted(by_chapter[ch])
        n = len(personas)
        names = ", ".join(personas)
        noun = "persona" if n == 1 else "personas"
        if n >= th["personas"]:
            escalate.append(f"- [put-down] ch.{ch} — rule cross_persona_putdown>="
                            f"{th['personas']} ({n} {noun}: {names})")
        else:
            log.append(f"- [put-down] ch.{ch} — rule cross_persona_putdown<"
                       f"{th['personas']} ({n} {noun}: {names})")

    # Rule 2 — would_buy_no: sum tally.no across personas. >= threshold -> ESCALATE.
    total_no = sum(int(r.get("would_buy_next", {}).get("tally", {}).get("no", 0))
                   for r in converged)
    if total_no >= th["would_buy"]:
        escalate.append(f"- [would-buy] book — rule would_buy_no>={th['would_buy']} "
                        f"({total_no} personas said would-not-buy-next)")
    elif total_no:
        log.append(f"- [would-buy] book — rule would_buy_no<{th['would_buy']} "
                   f"({total_no} personas said would-not-buy-next)")

    # Rule 3 — score_spread: every entry -> LOG only (SOFT per design §6).
    for ch, e in _score_spreads(book_dir(book, repo_root) / "chapters"):
        log.append(f"- [score-spread] ch.{ch} — rule score_spread "
                   f"(producer {e.get('producer')}, spread {e.get('spread')})")

    return {"escalate": escalate, "log": log}


def write_report(out_path, result) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"schema: {SCHEMA}", "kind: revision-priority",
             f"escalations: {len(result['escalate'])}", "---", "",
             "## ESCALATE", ""]
    lines += result["escalate"] or ["- (none)"]
    lines += ["", "## LOG", ""]
    lines += result["log"] or ["- (none)"]
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def cmd_report(book: str, *, repo_root=REPO, config_path=None) -> int:
    result = aggregate(book, repo_root=repo_root, config_path=config_path)
    write_report(report_path(book, repo_root), result)
    print(f"REVISION-PRIORITY: {len(result['escalate'])} escalation(s)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny revision-priority aggregator.")
    ap.add_argument("book")
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    return cmd_report(args.book, config_path=args.config)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/test_revision_priority.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add scripts/revision_priority.py config/run-config.md tests/test_revision_priority.py
git commit -m "feat(report): deterministic revision-priority aggregator + escalation flags"
```

---

## Task 6: `preflight.py approve-book` precondition + cert mint + `book_approval` flag

**Files:**
- Modify: `scripts/preflight.py`
- Modify: `config/run-config.md` (add `book_approval`)
- Test: `tests/test_preflight.py`

**Interfaces:**
- Consumes: `assemble_book.validate_final_read`, `assemble_book.manuscript_path`, `assemble_book.final_read_path` (Tasks 1–3); `revision_priority.report_path` (Task 5); `penny_meta.parse_frontmatter`.
- Produces: `preflight.cmd_approve_book(book: str, *, repo_root=REPO) -> int` — asserts manuscript present + final-read valid shape + `read_by ∉ drafted_by` + revision-priority present, then mints `.penny/locks/book-NN.approved` as its LAST write. CLI: `preflight.py approve-book NN`.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_preflight.py
from scripts import assemble_book, revision_priority


def _approvable(tmp_path, *, read_by="codex", standalone="yes",
                with_report=True, with_manuscript=True):
    """Build a book-99 tree that approve-book should accept."""
    book = tmp_path / "output" / "book-99"
    (book / "chapters").mkdir(parents=True, exist_ok=True)
    if with_manuscript:
        assemble_book.manuscript_path("99", tmp_path).write_text(
            "---\nschema: penny-manuscript/1\nbook: 99\nchapters: 1\n"
            "drafted_by: [claude-opus]\nassembled_at: 2026-06-21T00:00:00+00:00\n---\n\n"
            "# Chapter 1\n\nprose\n", encoding="utf-8")
    assemble_book.final_read_path("99", tmp_path).write_text(
        f"---\nschema: penny-final-read/1\nread_by: {read_by}\n"
        f"standalone: {standalone}\nmystery_resolved: yes\nthread_left_open: yes\n---\n"
        "## Holistic verdict\nGood.\n", encoding="utf-8")
    if with_report:
        revision_priority.report_path("99", tmp_path).parent.mkdir(parents=True, exist_ok=True)
        revision_priority.report_path("99", tmp_path).write_text(
            "---\nschema: penny-revision-priority/1\nescalations: 0\n---\n", encoding="utf-8")


def test_approve_book_mints_cert_when_green(tmp_path):
    _approvable(tmp_path)
    assert preflight.cmd_approve_book("99", repo_root=tmp_path) == 0
    cert = tmp_path / ".penny/locks/book-99.approved"
    assert cert.is_file()


def test_approve_book_fails_without_manuscript(tmp_path):
    _approvable(tmp_path, with_manuscript=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "no manuscript" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_on_hedged_final_read(tmp_path):
    _approvable(tmp_path, standalone="mostly")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "standalone" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_when_read_by_drafted(tmp_path):
    _approvable(tmp_path, read_by="claude-opus")     # drafted_by is [claude-opus]
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "appears in drafted_by" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_without_report(tmp_path):
    _approvable(tmp_path, with_report=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "revision-priority" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_preflight.py -k approve_book -v`
Expected: FAIL — `module 'scripts.preflight' has no attribute 'cmd_approve_book'`

- [ ] **Step 3: Implement `cmd_approve_book` in `scripts/preflight.py`**

Add imports near the top (after the existing `from scripts.* import` lines):

```python
from scripts import assemble_book, revision_priority
```

Add the approved-cert path helper near `lock_path`:

```python
def approved_path(book: str, repo_root) -> Path:
    return Path(repo_root) / ".penny/locks" / f"book-{book}.approved"
```

Add the subcommand handler (after `cmd_assemble`):

```python
def cmd_approve_book(book: str, *, repo_root=REPO) -> int:
    man = assemble_book.manuscript_path(book, repo_root)
    if not man.is_file():
        _fail(f"no manuscript for book {book} ({man}) — run /assemble-book first")
    # final-read shape (reuses the validator; raises assemble_book: on a bad shape).
    assemble_book.validate_final_read(book, repo_root=repo_root)
    read_by = parse_frontmatter(
        assemble_book.final_read_path(book, repo_root).read_text(encoding="utf-8")
    ).get("read_by")
    drafted = parse_frontmatter(man.read_text(encoding="utf-8")).get("drafted_by")
    drafted = set(drafted) if isinstance(drafted, list) else {drafted} if drafted else set()
    if read_by in drafted:
        _fail(f"final-read model '{read_by}' appears in drafted_by set {sorted(drafted)}")
    report = revision_priority.report_path(book, repo_root)
    if not report.is_file():
        _fail(f"no revision-priority report for book {book} ({report})")
    # all preconditions green — mint the cert (the LAST write).
    cert = approved_path(book, repo_root)
    cert.parent.mkdir(parents=True, exist_ok=True)
    cert.write_text(
        f"book: {book}\napproved: final-read+revision-priority\n"
        f"approved_at: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    return 0
```

Wire the subcommand in `main` (after the `p_asm` parser):

```python
    p_app = sub.add_parser("approve-book", help="precondition gate + mint .approved cert")
    p_app.add_argument("book")
```

and the dispatch (after the `assemble` branch):

```python
    if args.cmd == "approve-book":
        return cmd_approve_book(args.book)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_preflight.py -k approve_book -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Add the `book_approval` flag to `config/run-config.md`**

In the "Run-mode flags (design §12)" ```yaml block, append after `ledger_approval`:

```yaml
book_approval:    review           # review (pause for showrunner) | auto
```

- [ ] **Step 6: Run the full suite to confirm no regression**

Run: `python3 -m pytest -q`
Expected: all green (189 prior + the new tests).

- [ ] **Step 7: Commit**

```bash
git add scripts/preflight.py config/run-config.md tests/test_preflight.py
git commit -m "feat(approve): preflight approve-book precondition gate + book_approval flag"
```

---

## Task 7: `/assemble-book` command orchestrator

**Files:**
- Create: `.claude/commands/assemble-book.md`

**Interfaces:**
- Consumes everything above: `assemble_book.py` (`assemble`/`seal`/`validate-read`), `preflight.py` (`assemble`/`approve-book`), `revision_priority.py`, `canon_core_review.py`, the `final-reader` agent, and `book_approval` in run-config.
- No automated test (orchestration runbook — agent judgment is UAT, per spec §1/§5). Verified by structural review + a manual dry-run.

- [ ] **Step 1: Create `.claude/commands/assemble-book.md`**

```markdown
---
description: Assemble finalized chapters into the book manuscript, run the cross-model final read, build the revision-priority report, and pause for showrunner approval.
argument-hint: <book-number> [--approve]
---
# /assemble-book

The book loop (design §5 per-book flow, §7 cross-model routing, §10). Assembles the
manuscript, gates cross-model independence, runs the ONE genuine holistic judgment
(the `final-reader`), builds the deterministic revision-priority report, then pauses
for the showrunner. Approve by re-running with `--approve`. Mirrors `ledger_approval`:
`book_approval: review` pauses; `auto` would mint the cert end-to-end.

## Steps

### Parse args

```bash
book=$1            # e.g. 01
flag=${2:-}        # optional --approve
```

---

### `--approve` RESUME BRANCH (handle before everything else)

If `$flag` equals `--approve`, enter the approval path — do NOT re-run any agents
(re-running the final read would discard the reviewed judgment):

1. Assert the showrunner has seen the artifacts (stage marker reads
   `book=$book stage=BOOK-REVIEW`). If not, stop and report which stage is active.

2. Seal the manuscript (stamp `read_by` from the final read):

   ```bash
   python3 scripts/assemble_book.py seal $book
   ```

3. Run the precondition gate + mint the `.approved` cert (its last write):

   ```bash
   python3 scripts/preflight.py approve-book $book
   ```

   A nonzero exit aborts — the cert is NOT minted; resolve the named predicate first.

4. Call the reserved per-book demotion hook (Phase-6 no-op; pinned signature):

   ```bash
   python3 scripts/canon_core_review.py --book $book \
     --canon-core series/continuity/canon-core.md
   ```

5. Write the stage marker and report:

   ```bash
   echo "book=$book stage=BOOK-APPROVED" > .penny/current-stage
   ```

   Report "Book $book approved — `.penny/locks/book-$book.approved` minted." and STOP.

---

### Step 1 — Assemble the manuscript

```bash
echo "book=$book stage=ASSEMBLE" > .penny/current-stage
python3 scripts/assemble_book.py assemble $book
```

A nonzero exit (chapter gap, missing `drafted_by`, outline mismatch) aborts.

### Step 2 — Cross-model pre-flight gate (built Phase 3; wired here)

```bash
python3 scripts/preflight.py assemble $book
```

This enforces `final_read_model != drafting_model` and `final_read_model ∉ drafted_by`
BEFORE the read runs. A nonzero exit aborts — fix routing in `config/run-config.md`.

### Step 3 — Dispatch the `final-reader` agent (cross-model, informed)

Dispatch the **`final-reader`** sub-agent with:
- `output/book-$book/book-$book.manuscript.md` — the assembled manuscript.
- `series/whodunit/book-$book.yaml` — the mystery solution (informed read).
- the arc-ledger slice (`series/arc-ledger.md` + the thread file that is the intended
  series hook) — required to judge `thread_left_open`.

The agent MUST be `final_read_model` (must not be a drafter). It writes
`output/book-$book/book-$book.final-read.md` (`schema: penny-final-read/1`).

### Step 4 — Validate the final-read shape (hard gate)

```bash
python3 scripts/assemble_book.py validate-read $book
```

A nonzero exit means a malformed/hedged read (`standalone`/`mystery_resolved`/
`thread_left_open` must be `yes|no`). Stop and re-dispatch the agent — do not proceed
to approval with a malformed read.

### Step 5 — Build the revision-priority report (deterministic)

```bash
python3 scripts/revision_priority.py $book
```

Reads the 6 `output/book-$book/reports/<persona>.converged.md` (from `/beta-read`) +
every `output/book-$book/chapters/ch-*.gate.md`. Writes
`output/book-$book/reports/revision-priority.md`. Non-blocking (always exit 0).

> If `/beta-read` has not been run for this book, the converged reports are absent and
> the report's put-down/would-buy sections will be empty — note this to the showrunner;
> it is a missing input, not a clean book.

### Step 6 — Present the two artifacts and pause (`book_approval`)

Read `book_approval` from `config/run-config.md`.

**`review` (default):** Set the stage marker and surface BOTH artifacts:

```bash
echo "book=$book stage=BOOK-REVIEW" > .penny/current-stage
```

Present to the showrunner:
- the final-read booleans (`standalone` / `mystery_resolved` / `thread_left_open`)
  and the `## Holistic verdict` prose from `book-$book.final-read.md`;
- the `## ESCALATE` / `## LOG` sections and `escalations:` count from
  `reports/revision-priority.md`.

Then say:

> "Book $book is assembled and read. Review the final-read verdict + revision-priority
> report above, then approve by running:
>
> `/assemble-book $book --approve`"

**Do not seal, gate, or mint the cert. Stop here.** The showrunner must explicitly
re-run with `--approve`.

**`auto`:** proceed directly through the `--approve` branch steps 2–5 (seal →
approve-book → demotion hook → marker) without pausing.
```

- [ ] **Step 2: Structural self-check (no test framework — verify by reading)**

Confirm every shell command in the command references a real subcommand built in
Tasks 1–6:
- `assemble_book.py assemble|seal|validate-read` ✓ (Tasks 1–3)
- `preflight.py assemble|approve-book` ✓ (built Phase 3 / Task 6)
- `revision_priority.py <book>` ✓ (Task 5)
- `canon_core_review.py --book --canon-core` ✓ (Task 4)
- agent `final-reader` ✓ (Task 3)

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/assemble-book.md
git commit -m "feat(book-loop): /assemble-book orchestrator command"
```

---

## Task 8: Full-suite verification + handoff update

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all green — the prior 189 plus the new `test_assemble_book.py`,
`test_revision_priority.py`, `test_canon_core_review.py`, and the added
`approve_book` tests in `test_preflight.py`.

- [ ] **Step 2: Confirm no engine/data leakage**

Run: `grep -rnE "book-99|claude-opus|codex" scripts/` and confirm matches appear
ONLY in docstrings/comments, never as hardcoded behavior. Project-specific values
must live in `config/` and `series/`, read at runtime.

- [ ] **Step 3: Push at phase end (per working-style)**

```bash
git push origin main
```

---

## Self-Review (completed against the spec)

**1. Spec coverage**
- §3 Unit 1 (manuscript producer `assemble`+`seal`, three states) → Tasks 1, 2.
- §3 Unit 2 (preflight `assemble` wired as pre-read gate) → Task 7 Step 2.
- §3 Unit 3 (`final-reader` agent + `penny-final-read/1` + `validate_final_read`) → Task 3.
- §3 Unit 4 (`revision_priority.py`, raw-threshold rules, traceable lines, non-blocking) → Task 5.
- §3 Unit 5 (command pause + `approve-book` cert + reserved demotion hook) → Tasks 4, 6, 7.
- §5 testing strategy (golden manuscript, fail tests, seal idempotency, enum/hedge,
  threshold boundaries, rule-traceability, all-clean, cross-consistency, demotion no-op)
  → Tasks 1–6 test steps.
- §6 three config flags → Tasks 5 (two) + 6 (`book_approval`).
- §7 build sequence honored: assemble → seal/validate → demotion stub → aggregator →
  approve-cert → command (aggregator lands with its dependencies already built).

**2. Placeholder scan:** every code step shows complete code; no TBD/TODO/"handle edge
cases"; fail predicates are spelled out.

**3. Type consistency:** `manuscript_path`/`final_read_path`/`report_path`/`approved_path`
helpers are defined once and reused across tasks; `validate_final_read(book, *, repo_root)`
signature is identical where Task 6 reuses it; `aggregate(...) -> {"escalate","log"}` keys
match between producer (Task 5 impl) and tests; `_stamps()` handles both str and list
`drafted_by` consistently in assemble (Task 1) and approve-book (Task 6).
