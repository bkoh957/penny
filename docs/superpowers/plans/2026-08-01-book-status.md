# Book Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/book-status NN` shows where a book actually is — every pipeline step with two statuses (did it run, did it pass), the command that advances it, its artefact, and one `next:` line.

**Architecture:** One new deterministic module `scripts/book_status.py`. It reads only what other commands already wrote and **writes nothing at all**. Every row is a `Row` of two `Cell`s; a cell is a boolean, an `x/y` count, not-applicable, or unknown. Rendering, row-building, and `next:` selection are separate pure functions so each is testable without a filesystem.

**Tech Stack:** Python 3, stdlib only (`penny_meta`, `penny_paths`, and the existing checkers). PyYAML only for the feedback ledger, which is nested human-edited data.

**Spec:** `docs/superpowers/specs/2026-08-01-book-status-design.md`. §5 (the lock fingerprint) is **already shipped** in commit `7cb2f4e` — this plan consumes it, it does not build it.

## Global Constraints

- **This module writes nothing.** No file is created, edited, or deleted by any code path. Directories are not created — not even `output/book-NN/reports/`.
- **Exit 0 whenever the book could be read**, whatever the rows say. A book with everything failing is a *successful* run. Exit 2 only for usage errors: no such book, not inside a series, unreadable outline.
- **Never a traceback.** Any row whose check cannot run renders `?` with a named reason and must not prevent the other rows from rendering.
- **`—` is never a failure.** It means the step has nothing to pass; running it *is* the outcome.
- **A missing `outline_sha256` on a lock reports `unknown`, never `fresh`.** Legacy locks predate `7cb2f4e`.
- **mtime is never used** to judge staleness anywhere in this module. A `git checkout` rewrites mtimes and would flip a stale lock green.
- Genre/location-agnostic: no genre filename in `scripts/`. Paths resolve via `penny_paths`.
- Tests run with `python3 -m pytest` from the repo root; `pytest.ini` sets `pythonpath=.`. **715 passing** at plan time.

## Confirmed API facts (verified against the code at plan time — do not re-derive)

- `penny_paths` exports `series_root`, `series_path`, `input_path`, `output_path`, `penny_path`, `config_path`, `plugin_root`.
- `outline_check.check_outline(outline_path, *, repo_root=None) -> dict`.
- `packet_assemble.stale_packets(book, repo_root=None) -> set[str]` — zero-padded chapter numbers whose `built_from_outline`/`built_from_whodunit` stamps no longer match.
- `packet_assemble.packet_path(book, chapter, repo_root=None) -> Path`; `penny_map.map_path(book, chapter, repo_root=None) -> Path`.
- `map_check.check_map(packet_text, map_text, profile) -> dict`.
- `penny_meta.parse_frontmatter(text) -> dict`.
- Certificates: `.penny/locks/book-NN.mystery.lock`, `.penny/locks/book-NN.approved`, `.penny/locks/book-NN.ch-MM.dev-clear` (frontmatter key `cleared_draft_sha256`).
- Chapter artefacts: `output/book-NN/chapters/ch-MM.draft.md`, `.final.md`, `ch-MM.gate.md` (contains a `gate: PASS` line).
- **Manuscript is `output/book-NN/book-NN.manuscript.md`** — the spec's §4 mockup wrote `manuscript.md`; the code is authoritative (`scripts/assemble_book.py`).
- Beta reports: `output/book-NN/beta-reports/<persona>.converged.md`.

## File Structure

- `scripts/book_status.py` — **new.** Cell/Row model, row builders, `next:` selection, rendering, CLI.
- `tests/test_book_status.py` — **new.** Fixture-series tests for every row and every `next:` branch.
- `commands/book-status.md` — **new.** Thin runbook.
- `README.md` — **modify.** Command table row.

---

### Task 1: The cell/row model and the four book-level rows

**Files:**
- Create: `scripts/book_status.py`
- Create: `tests/test_book_status.py`

**Interfaces:**
- Produces: `Cell` and `Row` dataclasses; constructors `yes()`, `no(reason="")`, `count(done, total)`, `na()`, `unknown(reason)`; `book_rows(book, repo_root=None) -> list[Row]` returning the four book-level rows in order: `outline`, `diagnostics`, `feedback`, `lock`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_book_status.py`:

```python
import hashlib
from pathlib import Path

import pytest

from scripts import book_status


def _series(tmp_path):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-01").mkdir(parents=True)
    (tmp_path / "output" / "book-01").mkdir(parents=True)
    return tmp_path


OUTLINE = """---
book: 01
total_chapters: 2
---

# Outline

## Solution
culprit is x.

## Chapter 01 — A

### Required Beats
- a beat.

## Chapter 02 — B

### Required Beats
- another beat.
"""


def _write_outline(root, text=OUTLINE):
    p = root / "input" / "book-01" / "outline.md"
    p.write_text(text, encoding="utf-8")
    return p


def _row(rows, row_id):
    return next(r for r in rows if r.id == row_id)


def test_outline_row_is_not_run_when_there_is_no_outline(tmp_path):
    root = _series(tmp_path)
    r = _row(book_status.book_rows("01", root), "outline")
    assert r.run.kind == "bool" and r.run.ok is False


def test_outline_row_runs_and_passes_for_a_well_shaped_outline(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    r = _row(book_status.book_rows("01", root), "outline")
    assert r.run.ok is True
    assert r.passed.ok is True


def test_diagnostics_row_has_nothing_to_pass(tmp_path):
    """`—` is not a pending state and must never render as a failure."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-glance.md").write_text("# g\n", encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "diagnostics")
    assert r.run.ok is True
    assert r.passed.kind == "na"


def test_feedback_row_fails_while_items_are_open(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "items:\n  - {id: OF-1, state: open}\n  - {id: OF-2, state: solved}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.run.ok is True
    assert r.passed.ok is False
    assert "1 open" in r.reason


def test_feedback_row_passes_when_every_item_is_dispositioned(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "items:\n  - {id: OF-1, state: solved}\n  - {id: OF-2, state: rejected}\n",
        encoding="utf-8")
    assert _row(book_status.book_rows("01", root), "feedback").passed.ok is True


def _write_lock(root, body):
    d = root / ".penny" / "locks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "book-01.mystery.lock").write_text(body, encoding="utf-8")


def test_lock_row_passes_when_the_fingerprint_matches(tmp_path):
    root = _series(tmp_path)
    p = _write_outline(root)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    _write_lock(root, f"book: 01\nvalidated: fairplay\n"
                      f"outline_source: input/book-01/outline.md\n"
                      f"outline_sha256: {sha}\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.ok is True


def test_lock_row_is_stale_when_the_outline_changed_since(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay\n"
                      "outline_source: input/book-01/outline.md\n"
                      "outline_sha256: " + ("0" * 64) + "\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.passed.ok is False
    assert "stale" in r.reason.lower()


def test_a_legacy_lock_reports_unknown_never_fresh_and_never_stale(tmp_path):
    """The sharpest rule in the spec: a certificate must not claim coverage it
    does not have. A lock minted before 7cb2f4e carries no fingerprint, so the
    honest answer is that the question cannot be answered."""
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay+lexicon\n"
                      "locked_at: 2026-07-28T03:10:33+00:00\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.kind == "unknown"
    assert "unknown" in r.reason.lower()


def test_lock_row_compares_against_the_source_the_lock_names(tmp_path):
    """lock-mystery prefers outline-skeleton.md, so the lock records WHICH file
    it validated. Comparing against outline.md regardless would report a
    confident wrong answer."""
    root = _series(tmp_path)
    _write_outline(root)
    skel = root / "input" / "book-01" / "outline-skeleton.md"
    skel.write_text("# skeleton\n", encoding="utf-8")
    sha = hashlib.sha256(skel.read_bytes()).hexdigest()
    _write_lock(root, f"book: 01\nvalidated: fairplay\n"
                      f"outline_source: input/book-01/outline-skeleton.md\n"
                      f"outline_sha256: {sha}\n")
    assert _row(book_status.book_rows("01", root), "lock").passed.ok is True


def test_every_row_carries_a_command_and_an_artefact(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    for r in book_status.book_rows("01", root):
        assert r.command, f"{r.id} has no command"
        assert r.artefact, f"{r.id} has no artefact"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_book_status.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.book_status'`

- [ ] **Step 3: Write the implementation**

Create `scripts/book_status.py`:

```python
"""Where a book actually is (spec 2026-08-01).

READ-ONLY, absolutely: this module creates, edits and deletes nothing — not
even a reports directory. It reports on state other commands already wrote.

Two statuses per row, because "done" is two questions. RUN is "the artefact
exists". PASSED is "the proof exists AND is still current". Collapsing them
into one tick reproduces the .penny/current-stage failure this replaces: a
label someone typed, which has read OUTLINE-REVIEWED for days while the book
moved on.
"""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter


@dataclass
class Cell:
    """One status column. kind is 'bool' | 'count' | 'na' | 'unknown'.

    'na' means the step has nothing to pass — running it IS the outcome. It is
    never a failure and never a pending state.
    'unknown' means the check could not run. It is never rendered as pass or
    fail, because a report that guesses is worse than one that admits.
    """
    kind: str
    ok: bool = False
    done: int = 0
    total: int = 0


def yes() -> Cell:
    return Cell("bool", ok=True)


def no() -> Cell:
    return Cell("bool", ok=False)


def count(done: int, total: int) -> Cell:
    return Cell("count", done=done, total=total, ok=(total > 0 and done == total))


def na() -> Cell:
    return Cell("na")


def unknown() -> Cell:
    return Cell("unknown")


@dataclass
class Row:
    id: str
    label: str
    run: Cell
    passed: Cell
    command: str
    artefact: str
    reason: str = ""


def _root(repo_root):
    return Path(repo_root) if repo_root is not None else penny_paths.series_root()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _outline_path(book: str, root) -> Path:
    return Path(penny_paths.input_path(f"book-{book}/outline.md", root=root))


def _outline_row(book: str, root) -> Row:
    p = _outline_path(book, root)
    rel = f"input/book-{book}/outline.md"
    common = dict(id="outline", label="outline",
                  command=f"/plot-book {book}", artefact=rel)
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="no outline yet", **common)
    try:
        from scripts.outline_check import check_outline
        blocking = check_outline(p, repo_root=root)["blocking"]
        if blocking:
            return Row(run=yes(), passed=no(), reason=blocking[0], **common)
        return Row(run=yes(), passed=yes(), **common)
    except Exception as exc:                      # never a traceback
        return Row(run=yes(), passed=unknown(),
                   reason=f"outline_check could not run: {exc}", **common)


_DIAGNOSTIC_VIEWS = ("outline-glance.md", "spine-worksheet.md", "spine-map.md")


def _diagnostics_row(book: str, root) -> Row:
    d = Path(penny_paths.output_path(f"book-{book}/reports", root=root))
    present = [n for n in _DIAGNOSTIC_VIEWS if (d / n).is_file()]
    strands = d / "strands"
    n_strands = len(list(strands.glob("*.md"))) if strands.is_dir() else 0
    if n_strands:
        present.append(f"{n_strands} strands")
    return Row(id="diagnostics", label="diagnostics",
               run=yes() if present else no(), passed=na(),
               command=f"/diagnose-outline {book}",
               artefact=f"output/book-{book}/reports/",
               reason=", ".join(present) if present else "not run")


def _feedback_row(book: str, root) -> Row:
    p = Path(penny_paths.output_path(
        f"book-{book}/reports/outline-feedback.yaml", root=root))
    common = dict(id="feedback", label="outline feedback",
                  command=f"/review-outline {book}",
                  artefact=f"output/book-{book}/reports/outline-feedback.yaml")
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="no feedback ledger", **common)
    try:
        import yaml
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"ledger is {type(data).__name__}, not a mapping")
        items = data.get("items") or []
        if not isinstance(items, list):
            raise ValueError("items: is not a list")
        open_n = sum(1 for i in items
                     if isinstance(i, dict) and i.get("state") == "open")
    except Exception as exc:
        return Row(run=yes(), passed=unknown(),
                   reason=f"ledger could not be read: {exc}", **common)
    if open_n:
        return Row(run=yes(), passed=no(),
                   reason=f"{open_n} open of {len(items)}", **common)
    return Row(run=yes(), passed=yes(),
               reason=f"{len(items)} items, none open", **common)


def _lock_row(book: str, root) -> Row:
    p = Path(penny_paths.penny_path(f"locks/book-{book}.mystery.lock", root=root))
    common = dict(id="lock", label="mystery lock",
                  command=f"preflight lock-mystery {book}",
                  artefact=f".penny/locks/book-{book}.mystery.lock")
    if not p.is_file():
        return Row(run=no(), passed=no(), reason="not locked", **common)
    fm = parse_frontmatter_or_lines(p.read_text(encoding="utf-8"))
    recorded = fm.get("outline_sha256")
    source = fm.get("outline_source")
    if not recorded or not source:
        # Legacy lock (pre-7cb2f4e) — it records THAT it validated, not WHAT.
        # A certificate must not claim coverage it does not have, so the only
        # honest answer is that the question cannot be answered.
        return Row(run=yes(), passed=unknown(),
                   reason="staleness unknown — lock records no fingerprint; "
                          "re-mint to fix", **common)
    src = Path(_root(root)) / source
    if not src.is_file():
        return Row(run=yes(), passed=unknown(),
                   reason=f"staleness unknown — {source} no longer exists", **common)
    if _sha(src) == recorded:
        return Row(run=yes(), passed=yes(), reason=f"matches {source}", **common)
    return Row(run=yes(), passed=no(),
               reason=f"STALE — {source} has changed since the lock", **common)


def parse_frontmatter_or_lines(text: str) -> dict:
    """The lock is `key: value` lines with NO `---` fences, so parse_frontmatter
    does not apply. Kept tiny and local rather than loosening penny_meta, whose
    strictness other callers depend on."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def book_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    return [_outline_row(book, root), _diagnostics_row(book, root),
            _feedback_row(book, root), _lock_row(book, root)]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_book_status.py -v`
Expected: PASS — 10 passed

`check_outline` returns `{"blocking": [...], "metrics": {...}}` — verified against `scripts/outline_check.py:100` at plan time. `blocking` is a list of predicate strings; an empty list means the outline's shape is valid.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 725 passed (715 + 10)

- [ ] **Step 6: Commit**

```bash
git add scripts/book_status.py tests/test_book_status.py
git commit -m "feat(status): the row model and the four book-level rows

Two statuses per row, because done is two questions: RUN is the artefact
exists, PASSED is the proof exists AND is still current. A draft exists
while its gate says HOLD; an outline exists with a lock that no longer
describes it.

The lock row is the one that earns this. A legacy lock carries no
fingerprint, so it reports unknown — never fresh, never stale. And it
compares against the source the lock NAMES, because lock-mystery prefers
outline-skeleton.md and comparing against outline.md regardless would give
a confident wrong answer."
```

---

### Task 2: The per-chapter count rows

**Files:**
- Modify: `scripts/book_status.py`
- Modify: `tests/test_book_status.py`

**Interfaces:**
- Consumes: `Cell`, `Row`, `count`, `na`, `unknown`, `_root` from Task 1.
- Produces: `total_chapters(book, repo_root=None) -> int | None`; `chapter_rows(book, repo_root=None) -> list[Row]` in order: `packets`, `maps`, `drafts`, `gates`, `dev-cleared`, `finals`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_book_status.py`:

```python
def _chapters_dir(root):
    d = root / "output" / "book-01" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_total_chapters_comes_from_the_outline_frontmatter(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    assert book_status.total_chapters("01", root) == 2


def test_total_chapters_is_none_when_the_outline_does_not_declare_it(tmp_path):
    root = _series(tmp_path)
    _write_outline(root, "---\nbook: 01\n---\n\n## Chapter 01 — A\n")
    assert book_status.total_chapters("01", root) is None


def test_count_rows_are_unknown_when_total_chapters_is_unknown(tmp_path):
    """A count with no denominator is a guess. Report that it cannot be
    computed rather than inventing a total from whichever directory is fullest."""
    root = _series(tmp_path)
    _write_outline(root, "---\nbook: 01\n---\n\n## Chapter 01 — A\n")
    for r in book_status.chapter_rows("01", root):
        assert r.run.kind == "unknown" or r.passed.kind == "unknown"


def test_drafts_row_counts_draft_files(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").write_text("x\n", encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "drafts")
    assert (r.run.done, r.run.total) == (1, 2)
    assert r.run.ok is False


def test_drafts_row_passes_only_when_every_chapter_has_one(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    for n in ("01", "02"):
        (d / f"ch-{n}.draft.md").write_text("x\n", encoding="utf-8")
    assert _row(book_status.chapter_rows("01", root), "drafts").run.ok is True


def test_gates_row_counts_only_passing_gates(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.gate.md").write_text("gate: PASS\n", encoding="utf-8")
    (d / "ch-02.gate.md").write_text("gate: HOLD\n", encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "gates")
    assert r.run.kind == "na"
    assert (r.passed.done, r.passed.total) == (1, 2)


def test_dev_cleared_counts_only_certs_bound_to_the_current_draft(tmp_path):
    """The cert records cleared_draft_sha256 — a cert for a draft that has since
    been edited is not a clearance for the draft on disk."""
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    draft = d / "ch-01.draft.md"
    draft.write_text("current text\n", encoding="utf-8")
    (d / "ch-02.draft.md").write_text("other\n", encoding="utf-8")
    locks = root / ".penny" / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    good = hashlib.sha256(draft.read_bytes()).hexdigest()
    (locks / "book-01.ch-01.dev-clear").write_text(
        f"---\ncleared_draft_sha256: {good}\n---\n", encoding="utf-8")
    (locks / "book-01.ch-02.dev-clear").write_text(
        "---\ncleared_draft_sha256: " + ("0" * 64) + "\n---\n", encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "dev-cleared")
    assert (r.passed.done, r.passed.total) == (1, 2)


def test_packets_row_reports_stale_packets_as_not_passed(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    pk = root / "input" / "book-01" / "packets"
    pk.mkdir(parents=True, exist_ok=True)
    (pk / "ch-01.md").write_text(
        "---\nbuilt_from_outline: deadbeef\n---\n\n### Required Beats\n- x\n",
        encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "packets")
    assert (r.run.done, r.run.total) == (1, 2)
    assert r.passed.done == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_book_status.py -v -k "total_chapters or drafts_row or gates_row or dev_cleared or packets_row or count_rows"`
Expected: FAIL — `AttributeError: module 'scripts.book_status' has no attribute 'total_chapters'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/book_status.py`:

```python
_UNKNOWN_TOTAL = "total_chapters not declared in the outline frontmatter"


def total_chapters(book: str, repo_root=None) -> int | None:
    """The denominator for every count, taken from the outline's frontmatter.

    Deliberately NOT inferred from whichever directory happens to be fullest: a
    count with a guessed denominator reads as fact and is a guess.
    """
    root = _root(repo_root)
    p = _outline_path(str(book).zfill(2), root)
    if not p.is_file():
        return None
    raw = parse_frontmatter(p.read_text(encoding="utf-8")).get("total_chapters")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _glob_chapters(d: Path, pattern: str) -> set[str]:
    """Zero-padded chapter numbers matching e.g. 'ch-*.draft.md'."""
    if not d.is_dir():
        return set()
    out = set()
    for p in d.glob(pattern):
        stem = p.name.split(".")[0]           # 'ch-07'
        if stem.startswith("ch-") and stem[3:].isdigit():
            out.add(stem[3:].zfill(2))
    return out


def chapter_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    total = total_chapters(book, root)
    chapters = Path(penny_paths.output_path(f"book-{book}/chapters", root=root))
    packets_dir = Path(penny_paths.input_path(f"book-{book}/packets", root=root))
    maps_dir = Path(penny_paths.input_path(f"book-{book}/maps", root=root))
    locks = Path(penny_paths.penny_path("locks", root=root))

    def c(done: int) -> Cell:
        return unknown() if total is None else count(done, total)

    reason = _UNKNOWN_TOTAL if total is None else ""

    packets = _glob_chapters(packets_dir, "ch-*.md")
    try:
        from scripts.packet_assemble import stale_packets
        stale = stale_packets(book, root)
        fresh = len(packets - stale)
        packet_passed = c(fresh)
        packet_reason = reason or (f"{len(stale)} stale" if stale else "")
    except Exception as exc:
        packet_passed, packet_reason = unknown(), f"staleness could not be read: {exc}"

    maps = _glob_chapters(maps_dir, "ch-*.md")
    drafts = _glob_chapters(chapters, "ch-*.draft.md")
    finals = _glob_chapters(chapters, "ch-*.final.md")

    passing_gates = 0
    for num in _glob_chapters(chapters, "ch-*.gate.md"):
        body = (chapters / f"ch-{num}.gate.md").read_text(encoding="utf-8")
        if any(l.strip() == "gate: PASS" for l in body.splitlines()):
            passing_gates += 1

    cleared = 0
    for num in drafts:
        cert = locks / f"book-{book}.ch-{num}.dev-clear"
        draft = chapters / f"ch-{num}.draft.md"
        if not cert.is_file():
            continue
        recorded = parse_frontmatter(
            cert.read_text(encoding="utf-8")).get("cleared_draft_sha256")
        if recorded and recorded == _sha(draft):
            cleared += 1

    return [
        Row("packets", "packets", c(len(packets)), packet_passed,
            f"/map-chapter {book} MM", f"input/book-{book}/packets/", packet_reason),
        Row("maps", "maps", c(len(maps)), na(),
            f"/map-chapter {book} MM", f"input/book-{book}/maps/", reason),
        Row("drafts", "drafts", c(len(drafts)), na(),
            f"/draft-chapter {book} MM",
            f"output/book-{book}/chapters/ch-MM.draft.md", reason),
        Row("gates", "gates", na(), c(passing_gates),
            f"/review-chapter {book} MM",
            f"output/book-{book}/chapters/ch-MM.gate.md", reason),
        Row("dev-cleared", "dev cleared", na(), c(cleared),
            f"preflight clear-dev {book} MM",
            f".penny/locks/book-{book}.ch-MM.dev-clear", reason),
        Row("finals", "finals", c(len(finals)), na(),
            f"/finalize-chapter {book} MM",
            f"output/book-{book}/chapters/ch-MM.final.md", reason),
    ]
```

**Note on the `maps` row:** it renders `na()` in PASSED rather than running `map_check` per chapter. `check_map` needs both the packet text and a parsed length profile, and a book with no length profile would make every map row `unknown` — noise, not signal. Map validity is enforced at `/map-chapter` time by `map_check.py`, which is where a failure can actually be acted on. Do not add a per-map check here.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_book_status.py -v`
Expected: PASS — 18 passed

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 733 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/book_status.py tests/test_book_status.py
git commit -m "feat(status): per-chapter work as x/total counts

The denominator comes from the outline's total_chapters, never from
whichever directory happens to be fullest — a count with a guessed
denominator reads as fact and is a guess. No denominator means the row
reports unknown.

dev-cleared counts only certs still bound to the draft on disk: a
clearance for a draft that has since been edited is not a clearance."
```

---

### Task 3: The tail rows and the `next:` rule

**Files:**
- Modify: `scripts/book_status.py`
- Modify: `tests/test_book_status.py`

**Interfaces:**
- Consumes: `book_rows`, `chapter_rows`.
- Produces: `tail_rows(book, repo_root=None) -> list[Row]` (`manuscript`, `beta`); `all_rows(book, repo_root=None) -> list[Row]`; `next_action(rows) -> Row | None`; `unknown_rows(rows) -> list[Row]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_book_status.py`:

```python
def _r(row_id, run, passed):
    return book_status.Row(row_id, row_id, run, passed, "cmd", "path")


def test_next_is_the_first_run_but_not_passed_row():
    rows = [_r("a", book_status.yes(), book_status.yes()),
            _r("b", book_status.yes(), book_status.no()),
            _r("c", book_status.no(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_next_prefers_fixing_over_starting():
    """A half-done thing outranks an unstarted one — that is the whole rule."""
    rows = [_r("a", book_status.no(), book_status.no()),
            _r("b", book_status.yes(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_next_falls_through_to_the_first_unrun_row():
    rows = [_r("a", book_status.yes(), book_status.yes()),
            _r("b", book_status.no(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_a_partly_done_count_row_is_run_but_not_passed():
    rows = [_r("a", book_status.count(3, 28), book_status.na())]
    assert book_status.next_action(rows).id == "a"


def test_an_na_passed_cell_never_makes_a_row_fail():
    rows = [_r("a", book_status.yes(), book_status.na()),
            _r("b", book_status.no(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_an_na_run_cell_is_judged_only_on_passed():
    rows = [_r("a", book_status.na(), book_status.count(0, 28))]
    assert book_status.next_action(rows).id == "a"


def test_unknown_rows_are_never_selected_as_next():
    """Guessing a next action from a fact the engine admits it does not have is
    exactly the failure this replaces."""
    rows = [_r("a", book_status.yes(), book_status.unknown()),
            _r("b", book_status.yes(), book_status.no())]
    assert book_status.next_action(rows).id == "b"
    assert [r.id for r in book_status.unknown_rows(rows)] == ["a"]


def test_next_is_none_when_everything_has_passed():
    rows = [_r("a", book_status.yes(), book_status.yes())]
    assert book_status.next_action(rows) is None


def test_manuscript_row_passes_only_with_an_approved_cert(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    (root / "output" / "book-01" / "book-01.manuscript.md").write_text(
        "x\n", encoding="utf-8")
    r = _row(book_status.tail_rows("01", root), "manuscript")
    assert r.run.ok is True and r.passed.ok is False
    (root / ".penny" / "locks").mkdir(parents=True, exist_ok=True)
    (root / ".penny" / "locks" / "book-01.approved").write_text("x\n", encoding="utf-8")
    assert _row(book_status.tail_rows("01", root), "manuscript").passed.ok is True


def test_beta_row_runs_when_converged_reports_exist(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = root / "output" / "book-01" / "beta-reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / "cosy-reader.converged.md").write_text("x\n", encoding="utf-8")
    r = _row(book_status.tail_rows("01", root), "beta")
    assert r.run.ok is True and r.passed.kind == "na"


def test_book_01_shape_selects_the_feedback_row(tmp_path):
    """The real case: an outline that passes, diagnostics run, a feedback ledger
    with open items, and a lock. plot_stage.py says 'next: premise' for this
    shape — go rewrite the premise of a book shaped by hand for weeks."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-glance.md").write_text("# g\n", encoding="utf-8")
    (reports / "outline-feedback.yaml").write_text(
        "items:\n  - {id: OF-1, state: open}\n", encoding="utf-8")
    _write_lock(root, "book: 01\nvalidated: fairplay\n")
    assert book_status.next_action(book_status.all_rows("01", root)).id == "feedback"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_book_status.py -v -k "next_ or manuscript_row or beta_row or book_01_shape or na_run or na_passed or unknown_rows or partly_done"`
Expected: FAIL — `AttributeError: module 'scripts.book_status' has no attribute 'next_action'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/book_status.py`:

```python
def tail_rows(book: str, repo_root=None) -> list[Row]:
    root = _root(repo_root)
    book = str(book).zfill(2)
    ms = Path(penny_paths.output_path(
        f"book-{book}/book-{book}.manuscript.md", root=root))
    approved = Path(penny_paths.penny_path(f"locks/book-{book}.approved", root=root))
    beta_dir = Path(penny_paths.output_path(f"book-{book}/beta-reports", root=root))
    n_beta = len(list(beta_dir.glob("*.converged.md"))) if beta_dir.is_dir() else 0
    return [
        Row("manuscript", "manuscript",
            yes() if ms.is_file() else no(),
            yes() if approved.is_file() else no(),
            f"/assemble-book {book}",
            f"output/book-{book}/book-{book}.manuscript.md",
            "approved" if approved.is_file() else
            ("assembled, not approved" if ms.is_file() else "not assembled")),
        Row("beta", "beta read", yes() if n_beta else no(), na(),
            f"/beta-read output/book-{book}/book-{book}.manuscript.md",
            f"output/book-{book}/beta-reports/",
            f"{n_beta} personas" if n_beta else "not run"),
    ]


def all_rows(book: str, repo_root=None) -> list[Row]:
    return (book_rows(book, repo_root) + chapter_rows(book, repo_root)
            + tail_rows(book, repo_root))


def _is_run(row: Row) -> bool:
    c = row.run
    if c.kind == "na":
        return True             # judged only on PASSED
    if c.kind == "count":
        return c.done > 0
    return c.ok


def _is_passed(row: Row) -> bool:
    c = row.passed
    if c.kind == "na":
        return True             # nothing to pass; running it IS the outcome
    if c.kind == "count":
        return c.total > 0 and c.done == c.total
    return c.ok


def unknown_rows(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.run.kind == "unknown" or r.passed.kind == "unknown"]


def next_action(rows: list[Row]) -> "Row | None":
    """First row that RAN but did not PASS; else the first not yet run.

    Fixing a thing that ran badly outranks starting the next thing — which is
    the whole difference from `plot_stage.py status`, whose per-stage view sends
    book 01 back to rewrite its premise. Rows whose checks could not run are
    skipped: guessing from a fact the engine admits it lacks is the failure
    this replaces.
    """
    skip = {id(r) for r in unknown_rows(rows)}
    candidates = [r for r in rows if id(r) not in skip]
    for r in candidates:
        if _is_run(r) and not _is_passed(r):
            return r
    for r in candidates:
        if not _is_run(r):
            return r
    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_book_status.py -v`
Expected: PASS — 29 passed

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 744 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/book_status.py tests/test_book_status.py
git commit -m "feat(status): the tail rows and the next: rule

next: is the first row that RAN but did not PASS; failing that, the first
not yet run. Fixing a half-done thing outranks starting the next one, and
that single rule produces the right answer for book 01 with no special
cases — where plot_stage.py, seeing only its own stages, says
'next: premise'.

Rows whose checks could not run are skipped rather than guessed at."
```

---

### Task 4: Rendering, the CLI, chapter drill-down, and the command

**Files:**
- Modify: `scripts/book_status.py`
- Modify: `tests/test_book_status.py`
- Create: `commands/book-status.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: `render_cell(cell) -> str`; `render(book, rows, next_row, unknowns) -> str`; `one_chapter_rows(book, chapter, repo_root=None) -> list[Row]`; CLI `book_status.py NN [MM]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_book_status.py`:

```python
import subprocess
import sys
import os


def test_render_cell_shapes():
    assert book_status.render_cell(book_status.yes()) == "✓"
    assert book_status.render_cell(book_status.no()) == "✗"
    assert book_status.render_cell(book_status.na()) == "—"
    assert book_status.render_cell(book_status.unknown()) == "?"
    assert book_status.render_cell(book_status.count(3, 28)) == "3/28"


def test_render_includes_every_row_its_command_and_its_artefact(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    rows = book_status.all_rows("01", root)
    out = book_status.render("01", rows, book_status.next_action(rows),
                             book_status.unknown_rows(rows))
    for r in rows:
        assert r.label in out
        assert r.command in out
    assert "next:" in out


def test_render_names_unknown_rows_beneath_next(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay\n")   # legacy, no fingerprint
    rows = book_status.all_rows("01", root)
    out = book_status.render("01", rows, book_status.next_action(rows),
                             book_status.unknown_rows(rows))
    assert "mystery lock" in out
    assert "unknown" in out.lower()


def test_one_chapter_rows_cover_the_per_chapter_pipeline(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").write_text("x\n", encoding="utf-8")
    ids = [r.id for r in book_status.one_chapter_rows("01", "01", root)]
    assert ids == ["packet", "map", "draft", "gate", "dev-clear", "final"]
    assert _row(book_status.one_chapter_rows("01", "01", root), "draft").run.ok is True


def _run(cwd, *args):
    env = dict(os.environ, PYTHONPATH=str(Path.cwd()))
    return subprocess.run(
        [sys.executable, str(Path.cwd() / "scripts" / "book_status.py"), *args],
        cwd=cwd, capture_output=True, text=True, env=env)


def test_cli_exits_zero_even_when_every_row_fails(tmp_path):
    """A report is not a gate. A book with everything undone is a SUCCESSFUL
    run of book-status."""
    root = _series(tmp_path)
    _write_outline(root)
    proc = _run(root, "01")
    assert proc.returncode == 0, proc.stderr
    assert "next:" in proc.stdout


def test_cli_refuses_a_book_with_no_outline(tmp_path):
    root = _series(tmp_path)
    proc = _run(root, "01")
    assert proc.returncode == 2
    assert "outline" in (proc.stdout + proc.stderr).lower()


def test_cli_refuses_a_traversal_book_id(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    proc = _run(root, "01/../../etc")
    assert proc.returncode == 2
    assert "invalid" in (proc.stdout + proc.stderr).lower()


def test_cli_writes_nothing(tmp_path):
    """The module's central promise. Nothing is created — not even a reports dir."""
    root = _series(tmp_path)
    _write_outline(root)
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    names_before = {str(p.relative_to(root)) for p in root.rglob("*")}
    assert _run(root, "01").returncode == 0
    names_after = {str(p.relative_to(root)) for p in root.rglob("*")}
    after = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert names_before == names_after, "book-status created something"
    assert before == after, "book-status modified something"


def test_cli_drills_into_one_chapter(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    proc = _run(root, "01", "01")
    assert proc.returncode == 0, proc.stderr
    assert "packet" in proc.stdout and "final" in proc.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_book_status.py -v -k "render or one_chapter or cli_"`
Expected: FAIL — `AttributeError: module 'scripts.book_status' has no attribute 'render_cell'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/book_status.py`:

```python
import re

_BOOK_RE = re.compile(r"\A[0-9]{1,3}\Z")


def render_cell(c: Cell) -> str:
    if c.kind == "na":
        return "—"
    if c.kind == "unknown":
        return "?"
    if c.kind == "count":
        return f"{c.done}/{c.total}"
    return "✓" if c.ok else "✗"


def render(book: str, rows: list[Row], next_row, unknowns: list[Row]) -> str:
    out = [f"BOOK {book}", ""]
    out.append(f"{'STEP':<16}{'RUN':>6}{'PASS':>7}   WHY / ARTEFACT")
    out.append("─" * 72)
    for r in rows:
        out.append(f"{r.label:<16}{render_cell(r.run):>6}{render_cell(r.passed):>7}   "
                   f"{r.reason or r.artefact}")
        out.append(f"{'':<16}{'':>6}{'':>7}   {r.command}")
    out.append("─" * 72)
    out.append(f"next: {next_row.command if next_row else 'nothing — every step has passed'}"
               + (f"   ({next_row.label})" if next_row else ""))
    for u in unknowns:
        out.append(f"  ? {u.label}: {u.reason}")
    return "\n".join(out) + "\n"


def one_chapter_rows(book: str, chapter: str, repo_root=None) -> list[Row]:
    """The same six steps as the count rows, for one chapter."""
    root = _root(repo_root)
    book, ch = str(book).zfill(2), str(chapter).zfill(2)
    chapters = Path(penny_paths.output_path(f"book-{book}/chapters", root=root))
    packet = Path(penny_paths.input_path(f"book-{book}/packets/ch-{ch}.md", root=root))
    mp = Path(penny_paths.input_path(f"book-{book}/maps/ch-{ch}.md", root=root))
    draft = chapters / f"ch-{ch}.draft.md"
    gate = chapters / f"ch-{ch}.gate.md"
    final = chapters / f"ch-{ch}.final.md"
    cert = Path(penny_paths.penny_path(
        f"locks/book-{book}.ch-{ch}.dev-clear", root=root))

    def b(p: Path) -> Cell:
        return yes() if p.is_file() else no()

    gate_pass = no()
    if gate.is_file():
        body = gate.read_text(encoding="utf-8")
        gate_pass = yes() if any(l.strip() == "gate: PASS"
                                 for l in body.splitlines()) else no()
    cleared = no()
    if cert.is_file() and draft.is_file():
        rec = parse_frontmatter(cert.read_text(encoding="utf-8")).get(
            "cleared_draft_sha256")
        cleared = yes() if rec and rec == _sha(draft) else no()
    return [
        Row("packet", "packet", b(packet), na(),
            f"/map-chapter {book} {ch}", str(packet)),
        Row("map", "map", b(mp), na(), f"/map-chapter {book} {ch}", str(mp)),
        Row("draft", "draft", b(draft), na(),
            f"/draft-chapter {book} {ch}", str(draft)),
        Row("gate", "gate", b(gate), gate_pass,
            f"/review-chapter {book} {ch}", str(gate)),
        Row("dev-clear", "dev clear", b(cert), cleared,
            f"preflight clear-dev {book} {ch}", str(cert)),
        Row("final", "final", b(final), na(),
            f"/finalize-chapter {book} {ch}", str(final)),
    ]


def _main(argv: list[str]) -> int:
    if not argv or len(argv) > 2:
        print("usage: book_status NN [MM]", file=sys.stderr)
        return 2
    book = argv[0]
    if not _BOOK_RE.match(book):
        print(f"book_status: invalid book id {book!r} — digits only",
              file=sys.stderr)
        return 2
    book = book.zfill(2)
    try:
        root = penny_paths.series_root()
    except SystemExit:
        raise
    if not _outline_path(book, root).is_file():
        print(f"book_status: no outline for book {book} "
              f"({_outline_path(book, root)})", file=sys.stderr)
        return 2
    if len(argv) == 2:
        ch = argv[1]
        if not _BOOK_RE.match(ch):
            print(f"book_status: invalid chapter id {ch!r} — digits only",
                  file=sys.stderr)
            return 2
        rows = one_chapter_rows(book, ch, root)
        print(render(f"{book} ch {ch.zfill(2)}", rows,
                     next_action(rows), unknown_rows(rows)))
        return 0
    rows = all_rows(book, root)
    print(render(book, rows, next_action(rows), unknown_rows(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

Move `import re` up with the other imports at the top of the file rather than leaving it mid-module.

- [ ] **Step 4: Write the command runbook**

Create `commands/book-status.md`:

```markdown
---
description: Show where a book is in the pipeline — every step with two statuses, its command, its artefact, and the single next action.
argument-hint: <book-number> [chapter-number]
---

# /book-status

Read-only. This command writes nothing, mints nothing, and touches no lock. It
is safe to run at any time, on any book, including one mid-draft.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), optional `chapter=$2`. Resolve the
   active series root; hard-error if cwd is not inside a series.

2. **Render the status:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/book_status.py" "$book" ${2:+"$2"}
   ```

   Exit 2 means a usage problem — no such book, an invalid id, or no outline to
   report on. Show the message; there is nothing to work around.

3. **Present it as printed.** Do not summarise the table away or re-order it.
   The two columns mean different things: **RUN** is "the artefact exists",
   **PASS** is "the proof exists and is still current". A `—` means the step has
   nothing to pass and is never a failure. A `?` means the check could not run —
   say so plainly rather than treating it as either a pass or a fail.

4. **Lead with the `next:` line.** It names the one command that advances the
   book, and it prefers finishing something half-done over starting something
   new.

5. **Stop.** This command reports. It never advances a step.
```

- [ ] **Step 5: Add the README row**

In `README.md`'s command table (near the `/diagnose-outline` row added in the previous plan), add:

```
/book-status 01 [07]                     # where the book is: two statuses per step + next action
```

If `test_readme_check_count.py` fails after the edit, update the count — the documentation is the artefact that wins.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_book_status.py -v`
Expected: PASS — 38 passed

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 753 passed

- [ ] **Step 8: Verify against the real series by hand**

Run, from `~/myBooks/pelicanscrook-series`:

```bash
python3 ~/myTools/penny/scripts/book_status.py 01
```

Expected on book 01 at plan time: outline ✓/✓, diagnostics ✓/—, outline feedback ✓/✗ with 12 open, mystery lock ✓/? (legacy, no fingerprint), all chapter counts 0/28, and `next:` pointing at `/review-outline 01`. Confirm nothing was created under the series — `git status` in that repo must be unchanged.

- [ ] **Step 9: Commit**

```bash
git add scripts/book_status.py tests/test_book_status.py commands/book-status.md README.md
git commit -m "feat(status): /book-status renders the pipeline and drills into a chapter

One table, two honest columns, the command that advances each step, and one
next: line. Exit 0 whenever the book could be read — a book with everything
undone is a successful run of a report.

A test asserts the command creates and modifies nothing at all, which is
the module's central promise."
```

---

## After this plan

**`.penny/current-stage` still exists and is still hand-written.** The terminal status line reads it, and this reporter neither replaces nor updates it, so the two can disagree — book 01's has said `OUTLINE-REVIEWED` for days. Spec §11 records this as deliberately out of scope. Settling it is a small follow-up: either the status line derives its stage from `book_status`, or `current-stage` is retired.

**Deliberately not built:** a series-wide roll-up across books (spec §11), and any backfill of `outline_sha256` onto existing locks — legacy locks report `unknown` until re-minted in the ordinary course of work.
