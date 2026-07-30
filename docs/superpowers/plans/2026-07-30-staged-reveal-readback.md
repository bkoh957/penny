# Staged Reveal-Aware Read-Back Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the outline's blind fan read stop at each protected reveal instead of once, ask it what it currently believes, and turn the gap between what it believed and what the plan intended into measured, one-change-each items in the existing outline-feedback ledger.

**Architecture:** No new gate and no new script. The whodunit ledger gains an optional `reveals:` block that acts as an answer key the reader never sees. `plot_stage.py` learns to cut the reader's copy at each reveal instead of once. `outline-fan` becomes a staged reader dispatched as a fresh sub-agent per stage. The `/plot-book` readback runbook compares the reader's answers to the answer key and appends findings to `output/book-NN/reports/outline-feedback.yaml` — the ledger `/review-outline` already writes, which already owns `OF-<n>` ids, showrunner-owned `state:`, and a non-blocking backlog banner.

**Tech Stack:** Python 3 stdlib + PyYAML (whodunit ledger and feedback ledger only — both already permitted under the dependency-split rule). pytest. Markdown runbooks and agent definitions.

**Spec:** `docs/superpowers/specs/2026-07-30-staged-reveal-readback-design.md`

## Global Constraints

- **The deterministic layer makes no LLM judgment.** Every script change here is parsing, arithmetic, or file writing. The reading and the comparison are agent/runbook work.
- **Absent `reveals:` is normal and must be byte-identical to today.** A book with no block gets the existing single-cut reader's copy at the existing path `output/book-NN/reports/outline-readers-copy.md`. This is the legacy invariant and gets a regression pin (Task 3, Step 1).
- **Present-but-malformed `reveals:` fails loud, never open.** Same rule as `_reveal_chapter`'s existing docstring: once the block exists, a broken entry is a mistake, not a state. Exit nonzero and name the offending entry.
- **`reveal_chapter` (singular) is untouched.** `fairplay_check.py`, `tension_check.py`, `lmstudio_draft_chapter.py`, and `readers_copy`'s existing path all keep reading exactly that key with exactly today's meaning.
- **PyYAML only inside function-scoped imports** in `plot_stage.py`, matching the existing `_reveal_chapter` pattern. `outline_feedback.py` already imports it at module level — leave that as is.
- **No `^BLOCKING:` line and no gate** from anything in this plan. The audit is advisory; the showrunner's readback sign-off remains the decision point.
- Tests run with `python3 -m pytest` from the repo root (`pytest.ini` sets `pythonpath=.`). Full suite is 595 tests before this work.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `scripts/plot_stage.py` | Workshop stage machinery, reader's copy | Modify: add `_reveals`, `reveal_stages`, `readers_copy_staged`, `--staged` CLI flag |
| `scripts/outline_feedback.py` | Append-only feedback ledger + views | Modify: `append_items` passes through `chapters`/`metrics`; `render_view` shows them |
| `scripts/preflight.py` | Deterministic gates + lock certificate | Modify: `lock-mystery --note-skipped` |
| `tests/test_plot_stage.py` | Stage machinery tests | Modify: add reveals/staging tests |
| `tests/test_outline_feedback.py` | Ledger tests | Modify: add passthrough tests |
| `tests/test_preflight.py` | Gate tests | Modify: add `--note-skipped` test |
| `agents/outline-fan.md` | The reader's contract | Modify: staged protocol, six questions, fresh-context rule |
| `agents/mystery-planner.md` | Whodunit proposal contract | Modify: `reveals:` block + neutral clue-id naming rule |
| `commands/plot-book.md` | Workshop runbook | Modify: readback step becomes staged read + audit + ledger append |
| `config/outline-template.md` | Authored outline shape | Modify: neutral q-slug naming note |
| `CLAUDE.md` | Project instructions | Modify: reader simulation needs isolation; readback is a loop |

---

### Task 1: Parse and validate the `reveals:` block

**Files:**
- Modify: `scripts/plot_stage.py` (add `_reveals` beside the existing `_reveal_chapter`, ~line 296)
- Test: `tests/test_plot_stage.py`

**Interfaces:**
- Consumes: `penny_paths.series_path`, the existing `_root` helper, the module's `sys.exit` fail-loud convention.
- Produces: `_reveals(book: str, root: Path) -> list[dict]` — returns `[]` when the ledger is absent or has no `reveals:` key. Each returned dict has keys `id: str`, `reveal_chapter: int`, `author_truth: str`, and optionally `reader_should_think_before: list[str]`. Exits nonzero on any malformed entry. Task 2 consumes this.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_plot_stage.py`. Note `_series` and `_write` already exist at the top of that file — reuse them, do not redefine.

```python
from scripts.plot_stage import _reveals  # add to the existing import block


def _whodunit(root, book="01", extra=""):
    return _write(root, f"series/whodunit/book-{book}.yaml",
                  "book: '01'\ntotal_chapters: 30\nreveal_chapter: 26\n" + extra)


def test_reveals_absent_ledger_returns_empty(tmp_path):
    root = _series(tmp_path)
    assert _reveals("01", root) == []


def test_reveals_key_absent_returns_empty(tmp_path):
    root = _series(tmp_path)
    _whodunit(root)
    assert _reveals("01", root) == []


def test_reveals_parsed_in_order(tmp_path):
    root = _series(tmp_path)
    _whodunit(root, extra=(
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
        "  reader_should_think_before:\n"
        "  - Lisa was abusing property records\n"
        "- id: marion-is-tara\n"
        "  reveal_chapter: 27\n"
        "  author_truth: Marion is Tara.\n"))
    got = _reveals("01", root)
    assert [r["id"] for r in got] == ["impersonation", "marion-is-tara"]
    assert [r["reveal_chapter"] for r in got] == [15, 27]
    assert got[0]["reader_should_think_before"] == ["Lisa was abusing property records"]
    assert "reader_should_think_before" not in got[1]


@pytest.mark.parametrize("bad,needle", [
    ("reveals: not-a-list\n", "must be a list"),
    ("reveals:\n- reveal_chapter: 15\n  author_truth: x\n", "missing 'id'"),
    ("reveals:\n- id: a\n  author_truth: x\n", "missing 'reveal_chapter'"),
    ("reveals:\n- id: a\n  reveal_chapter: 15\n", "missing 'author_truth'"),
    ("reveals:\n- id: a\n  reveal_chapter: nine\n  author_truth: x\n", "not an integer"),
    ("reveals:\n- id: a\n  reveal_chapter: 1\n  author_truth: x\n", "cannot be chapter 1"),
    ("reveals:\n- id: a\n  reveal_chapter: 31\n  author_truth: x\n", "beyond total_chapters"),
    ("reveals:\n- id: a\n  reveal_chapter: 20\n  author_truth: x\n"
     "- id: b\n  reveal_chapter: 15\n  author_truth: y\n", "not in ascending"),
    ("reveals:\n- id: a\n  reveal_chapter: 15\n  author_truth: x\n"
     "- id: a\n  reveal_chapter: 20\n  author_truth: y\n", "duplicate reveal id"),
])
def test_reveals_malformed_exits_loud(tmp_path, bad, needle):
    root = _series(tmp_path)
    _whodunit(root, extra=bad)
    with pytest.raises(SystemExit) as exc:
        _reveals("01", root)
    assert needle in str(exc.value)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_plot_stage.py -k reveals -v`
Expected: FAIL — `ImportError: cannot import name '_reveals'`

- [ ] **Step 3: Write the implementation**

Insert into `scripts/plot_stage.py` immediately after `_reveal_chapter` (which ends at the `return rc_int` around line 295):

```python
def _reveals(book: str, root: Path) -> list[dict]:
    """Read the OPTIONAL `reveals:` block from series/whodunit/book-NN.yaml
    (spec 2026-07-30 §3) — the protected turns the staged reader's copy is cut
    at, and the answer key the audit measures the reader against.

    Absent ledger, or a ledger with no `reveals:` key, returns [] — that is the
    normal legacy case and the caller falls back to the single-cut copy. But a
    block that EXISTS and is malformed exits loud, never open: the same
    fail-loud-not-open rule _reveal_chapter documents. Silently falling back to
    one stage would hand the fan a copy that runs past a protected turn while
    the showrunner believed it was staged."""
    path = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=root)
    if not path.is_file():
        return []
    import yaml  # PyYAML: the whodunit ledger is genuinely nested human data
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"plot_stage: malformed whodunit ledger {path}: {exc}")
    if not isinstance(data, dict):
        sys.exit(
            f"plot_stage: whodunit ledger {path} must be a YAML mapping, "
            f"got {type(data).__name__}")
    raw = data.get("reveals")
    if raw is None:
        return []
    if not isinstance(raw, list):
        sys.exit(f"plot_stage: {path}: 'reveals' must be a list, "
                 f"got {type(raw).__name__}")
    total = data.get("total_chapters")
    total_int = total if isinstance(total, int) and not isinstance(total, bool) else None
    out: list[dict] = []
    seen_ids: set[str] = set()
    prev_ch = 0
    for i, entry in enumerate(raw, start=1):
        where = f"{path}: reveals[{i}]"
        if not isinstance(entry, dict):
            sys.exit(f"plot_stage: {where} must be a mapping, "
                     f"got {type(entry).__name__}")
        rid = entry.get("id")
        if not isinstance(rid, str) or not rid.strip():
            sys.exit(f"plot_stage: {where} missing 'id'")
        rid = rid.strip()
        if rid in seen_ids:
            sys.exit(f"plot_stage: {where} duplicate reveal id {rid!r}")
        seen_ids.add(rid)
        if "reveal_chapter" not in entry:
            sys.exit(f"plot_stage: {where} ({rid}) missing 'reveal_chapter'")
        rc = entry["reveal_chapter"]
        if not isinstance(rc, int) or isinstance(rc, bool):
            sys.exit(f"plot_stage: {where} ({rid}) reveal_chapter is not an "
                     f"integer: {rc!r}")
        truth = entry.get("author_truth")
        if not isinstance(truth, str) or not truth.strip():
            sys.exit(f"plot_stage: {where} ({rid}) missing 'author_truth'")
        if rc < 2:
            sys.exit(f"plot_stage: {where} ({rid}) cannot be chapter {rc} — a "
                     "reveal at chapter 1 leaves its stage with no chapters to "
                     "read")
        if total_int is not None and rc > total_int:
            sys.exit(f"plot_stage: {where} ({rid}) reveal_chapter {rc} is "
                     f"beyond total_chapters ({total_int})")
        if rc < prev_ch:
            sys.exit(f"plot_stage: {where} ({rid}) reveal_chapter {rc} is not "
                     f"in ascending order (previous was {prev_ch})")
        prev_ch = rc
        item = {"id": rid, "reveal_chapter": rc, "author_truth": truth.strip()}
        hints = entry.get("reader_should_think_before")
        if isinstance(hints, list) and hints:
            item["reader_should_think_before"] = [str(h).strip() for h in hints]
        out.append(item)
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_plot_stage.py -k reveals -v`
Expected: PASS (12 tests)

Then confirm nothing regressed: `python3 -m pytest tests/test_plot_stage.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "$(cat <<'EOF'
feat(plot): parse and validate the optional whodunit reveals: block

The answer key the staged reader's copy is cut at (spec 2026-07-30 §3).
Absent block returns [] and the caller keeps today's single-cut behaviour;
a block that exists and is broken exits loud with the offending entry
named, the same fail-loud-not-open rule _reveal_chapter documents — a
silent fallback to one stage would hand the fan a copy running past a
protected turn while the showrunner believed it was staged.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Derive stage boundaries from the reveals

**Files:**
- Modify: `scripts/plot_stage.py` (add `reveal_stages` after `_reveals`)
- Test: `tests/test_plot_stage.py`

**Interfaces:**
- Consumes: Task 1's `_reveals` return shape (list of dicts with `reveal_chapter: int`).
- Produces: `reveal_stages(reveals: list[dict]) -> list[int | None]` — one entry per stage, the **last chapter that stage's copy may contain**. `None` means "no limit, the whole book" and is always the final entry. Returns `[]` for empty input. Task 3 consumes this.

Boundary rule from spec §4: for reveals at chapters `r1 ≤ r2 ≤ … ≤ rk`, stage *n* ends at `rn − 1`, and a final stage carries `None`. Equal reveal chapters produce one shared boundary — two protected turns landing in the same chapter is legitimate (a suspect reveal and an identity reveal can share a chapter) and must not become two identical stages.

- [ ] **Step 1: Write the failing tests**

```python
from scripts.plot_stage import reveal_stages  # add to the existing import block


def test_reveal_stages_empty_when_no_reveals():
    assert reveal_stages([]) == []


def test_reveal_stages_two_reveals_gives_three_stages():
    reveals = [{"id": "a", "reveal_chapter": 15, "author_truth": "x"},
               {"id": "b", "reveal_chapter": 27, "author_truth": "y"}]
    assert reveal_stages(reveals) == [14, 26, None]


def test_reveal_stages_single_reveal_gives_two_stages():
    assert reveal_stages([{"id": "a", "reveal_chapter": 15, "author_truth": "x"}]) == [14, None]


def test_reveal_stages_dedupes_shared_chapter():
    reveals = [{"id": "a", "reveal_chapter": 27, "author_truth": "x"},
               {"id": "b", "reveal_chapter": 27, "author_truth": "y"}]
    assert reveal_stages(reveals) == [26, None]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_plot_stage.py -k reveal_stages -v`
Expected: FAIL — `ImportError: cannot import name 'reveal_stages'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/plot_stage.py` after `_reveals`:

```python
def reveal_stages(reveals: list[dict]) -> list[int | None]:
    """Stage boundaries for the staged reader's copy (spec 2026-07-30 §4).

    Returns one entry per stage: the LAST chapter that stage's copy may
    contain, with None (the always-final entry) meaning the whole book. Stage n
    stops one chapter short of the nth protected reveal, so the reader files
    what it believes BEFORE reading the turn.

    Equal reveal_chapter values collapse to one boundary — two protected turns
    landing in the same chapter is legitimate (a suspect reveal and an identity
    reveal can share it) and must not produce two identical stages. Empty input
    returns [], which the caller reads as "no staging, use the legacy
    single-cut copy"."""
    if not reveals:
        return []
    bounds: list[int | None] = []
    for r in reveals:
        b = r["reveal_chapter"] - 1
        if b not in bounds:
            bounds.append(b)
    bounds.append(None)
    return bounds
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_plot_stage.py -k reveal_stages -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "$(cat <<'EOF'
feat(plot): derive staged reader's-copy boundaries from the reveals block

Stage n stops one chapter short of the nth protected reveal so the reader
files what it believes before reading the turn; a final stage carries the
whole book. Reveals sharing a chapter collapse to one boundary — a suspect
reveal and an identity reveal legitimately land together and must not
produce two identical stages.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Write the staged reader's copies

**Files:**
- Modify: `scripts/plot_stage.py` — `readers_copy_text` (line 160), add `readers_copy_staged`, extend the `readers-copy` CLI parser (line 344)
- Test: `tests/test_plot_stage.py`

**Interfaces:**
- Consumes: Task 1's `_reveals`, Task 2's `reveal_stages`, the existing `readers_copy_text`, `_chapter_numbers`, and `stage_paths(book, root)["chapters"]` (the outline skeleton path).
- Produces:
  - `readers_copy_text(text: str, *, reveal_chapter: int | None = None, last_chapter: int | None = None) -> str` — `reveal_chapter` keeps today's exact meaning (emit chapters `num < reveal_chapter`); `last_chapter` is the new staged form (emit `num <= last_chapter`). **Mutually exclusive** — passing both raises `ValueError`.
  - `readers_copy_staged(book: str, *, repo_root=None) -> list[Path]` — one path per stage, `output/book-NN/reports/outline-readers-copy-stage-K.md`, K 1-based. Returns `[]` when the ledger has no `reveals:` block (the caller then uses `readers_copy`).
- `readers_copy` is **not** changed. Task 6's runbook calls `readers_copy_staged` first and falls back.

- [ ] **Step 1: Write the failing tests, including the legacy regression pin**

```python
from scripts.plot_stage import readers_copy_staged  # add to the existing import block

_SKEL = """---
book: '01'
total_chapters: 4
---

## Chapter 01 — Arrival

### Required Beats
- Maggie arrives.

- **Hook:** q-start — what is wrong with the studio?
- **Opens:** q-start
### Track Movement
- **M:** Setup.

## Chapter 02 — The Key

### Required Beats
- An odd early key note surfaces.

## Chapter 03 — The Turn

### Required Beats
- The case changes shape.

## Chapter 04 — The End

### Required Beats
- Maggie names the culprit.
"""


def test_readers_copy_text_last_chapter_is_inclusive():
    out = readers_copy_text(_SKEL, last_chapter=2)
    assert "## Chapter 02" in out
    assert "## Chapter 03" not in out
    assert "Chapters 1–2" in out


def test_readers_copy_text_rejects_both_cut_params():
    with pytest.raises(ValueError):
        readers_copy_text(_SKEL, reveal_chapter=3, last_chapter=2)


def test_readers_copy_text_last_chapter_none_emits_all():
    out = readers_copy_text(_SKEL, last_chapter=None)
    assert "## Chapter 04" in out
    assert "The book continues past this point" not in out


def test_readers_copy_text_still_strips_wiring_at_every_cut():
    for kwargs in ({"last_chapter": 2}, {"last_chapter": None}, {"reveal_chapter": 3}):
        out = readers_copy_text(_SKEL, **kwargs)
        assert "**Opens:**" not in out
        assert "q-start" not in out
        assert "**M:**" not in out


def test_readers_copy_staged_writes_one_file_per_stage(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n"
           "reveals:\n- id: turn\n  reveal_chapter: 3\n  author_truth: The case turns.\n")
    paths = readers_copy_staged("01", repo_root=root)
    assert [p.name for p in paths] == ["outline-readers-copy-stage-1.md",
                                       "outline-readers-copy-stage-2.md"]
    s1 = paths[0].read_text(encoding="utf-8")
    assert "## Chapter 02" in s1 and "## Chapter 03" not in s1
    s2 = paths[1].read_text(encoding="utf-8")
    assert "## Chapter 04" in s2


def test_readers_copy_staged_is_cumulative_from_chapter_one(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n"
           "reveals:\n- id: turn\n  reveal_chapter: 3\n  author_truth: The case turns.\n")
    s2 = readers_copy_staged("01", repo_root=root)[1].read_text(encoding="utf-8")
    assert "## Chapter 01" in s2  # spec §4: cumulative, not just the new chapters


def test_readers_copy_staged_returns_empty_without_reveals(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n")
    assert readers_copy_staged("01", repo_root=root) == []


def test_legacy_readers_copy_unchanged_without_reveals(tmp_path):
    """Regression pin — the legacy invariant (Global Constraints)."""
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n")
    dest = readers_copy("01", repo_root=root)
    assert dest.name == "outline-readers-copy.md"
    assert dest.read_text(encoding="utf-8") == readers_copy_text(_SKEL, reveal_chapter=4)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_plot_stage.py -k "last_chapter or staged or legacy_readers" -v`
Expected: FAIL — `ImportError: cannot import name 'readers_copy_staged'`

- [ ] **Step 3: Change `readers_copy_text`'s signature and cut logic**

In `scripts/plot_stage.py`, replace the `def readers_copy_text(...)` line (160) and its docstring's final paragraph, and the two-line `emitted`/`truncated` block (182–184).

Replace the signature line:

```python
def readers_copy_text(text: str, *, reveal_chapter: "int | None" = None,
                      last_chapter: "int | None" = None) -> str:
```

Append to the existing docstring, after the sentence ending `...(current/legacy behaviour).`:

```
    `last_chapter` is the STAGED form (spec 2026-07-30 §4): emit chapters
    num <= last_chapter, so a caller can cut one chapter short of a protected
    reveal without pretending that reveal is the book's culprit reveal. The two
    parameters are mutually exclusive — they express the same cut with different
    off-by-one conventions, and accepting both would silently apply one.
```

Replace lines 182–184:

```python
    if reveal_chapter is not None and last_chapter is not None:
        raise ValueError(
            "readers_copy_text: pass reveal_chapter or last_chapter, not both")
    if last_chapter is not None:
        emitted = [c for c in chapters if c[0] <= last_chapter]
    else:
        emitted = [c for c in chapters
                   if reveal_chapter is None or c[0] < reveal_chapter]
    truncated = len(emitted) < len(chapters)
```

Note the `truncated` flag is now computed from the emitted count alone, which is
equivalent to today's expression when `last_chapter is None` and correct for the
staged case too.

- [ ] **Step 4: Add `readers_copy_staged`**

Insert into `scripts/plot_stage.py` immediately after `readers_copy` (which ends `return dest`, ~line 332):

```python
def readers_copy_staged(book: str, *, repo_root=None) -> list[Path]:
    """Write one reader's copy per protected reveal (spec 2026-07-30 §4).

    Each stage's copy is CUMULATIVE from chapter 1 and stops one chapter short
    of that stage's reveal; the final stage is the whole book. Returns the paths
    in stage order, or [] when the ledger declares no `reveals:` — the caller
    then falls back to readers_copy() and today's behaviour is untouched."""
    root = _root(repo_root)
    reveals = _reveals(book, root)
    stages = reveal_stages(reveals)
    if not stages:
        return []
    skel = stage_paths(book, root)["chapters"]
    if not skel.is_file():
        sys.exit(f"plot_stage: no outline-skeleton for book {book} ({skel})")
    skel_text = skel.read_text(encoding="utf-8")
    nums = _chapter_numbers(skel_text)
    last = max(nums) if nums else 0
    for r in reveals:
        if r["reveal_chapter"] > last:
            sys.exit(
                f"plot_stage: reveal {r['id']!r} is at chapter "
                f"{r['reveal_chapter']} but the skeleton's last chapter is "
                f"{last} for book {book} — that stage cannot be cut")
    out_dir = root / "output" / f"book-{book}" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, bound in enumerate(stages, start=1):
        dest = out_dir / f"outline-readers-copy-stage-{i}.md"
        dest.write_text(readers_copy_text(skel_text, last_chapter=bound),
                        encoding="utf-8")
        written.append(dest)
    return written
```

- [ ] **Step 5: Wire the CLI**

In `main()`, replace the `p_rc` parser block (line 344–345) and the `readers-copy` dispatch (357–359):

```python
    p_rc = sub.add_parser("readers-copy")
    p_rc.add_argument("book")
    p_rc.add_argument("--staged", action="store_true",
                      help="one copy per protected reveal (whodunit reveals: "
                           "block); falls back to the single-cut copy when the "
                           "ledger declares none")
```

```python
    if args.cmd == "readers-copy":
        if args.staged:
            paths = readers_copy_staged(args.book)
            if paths:
                for p in paths:
                    print(p)
                return 0
            print("plot_stage: no reveals: block — writing the single-cut copy")
        print(readers_copy(args.book))
        return 0
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_plot_stage.py -k "last_chapter or staged or legacy_readers" -v`
Expected: PASS (8 tests)

Then the whole file, to confirm the signature change broke no existing caller:
Run: `python3 -m pytest tests/test_plot_stage.py -q`
Expected: all pass.

Then the full suite:
Run: `python3 -m pytest -q`
Expected: all pass (595 + the new tests).

- [ ] **Step 7: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "$(cat <<'EOF'
feat(plot): staged reader's copies, one per protected reveal

readers_copy_text gains last_chapter (inclusive, the staged cut) beside the
existing reveal_chapter (exclusive, the legacy culprit cut); passing both
raises rather than silently applying one. readers_copy_staged writes one
cumulative copy per reveal, each stopping a chapter short of its turn so the
reader files what it believes BEFORE reading it, plus a final whole-book
stage. readers-copy --staged drives it and falls back with a printed note
when the ledger declares no reveals.

readers_copy itself is untouched and pinned by a regression test: a book
with no reveals block still gets outline-readers-copy.md byte-identical to
readers_copy_text(skel, reveal_chapter=N).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Carry measurements on feedback items

**Files:**
- Modify: `scripts/outline_feedback.py` — `append_items` (line 83), `render_view` (line 125), the `--points` help text (line 175)
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: the existing ledger shape — items with `id`, `source`, `pass`, `state`, `text`, optional `recommendation`.
- Produces: `append_items` additionally passes through two optional keys from each input point: `chapters` (list of ints) and `metrics` (flat mapping). Both are stored opaquely and omitted entirely when absent. Malformed values exit loud (`append` is operator-driven and must fail loudly — see the module docstring). `render_view` prints them on the item's line when present. Task 6's runbook produces points in this shape.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_outline_feedback.py`. That file imports the module as
`import scripts.outline_feedback as of` and builds ledgers with a local `_seed()` helper
returning a dict with two existing items (`OF-1` solved, `OF-2` rejected) — reuse both.

```python
def test_append_passes_through_chapters_and_metrics():
    out = of.append_items(_seed(), [{
        "source": "fan-audit",
        "text": "Reader named the impersonation at ch 11.",
        "chapters": [11],
        "metrics": {"finding": "early", "reveal": "impersonation",
                    "meant_to_land": 15, "first_suspected": 11,
                    "confidence": 4, "gap_chapters": 4},
    }], reviewed_sha="abc")
    item = out["items"][-1]
    assert item["id"] == "OF-3"
    assert item["chapters"] == [11]
    assert item["metrics"]["gap_chapters"] == 4
    assert item["metrics"]["finding"] == "early"


def test_append_omits_both_keys_when_absent():
    out = of.append_items(_seed(), [{"source": "claude", "text": "A point."}],
                          reviewed_sha="abc")
    assert "chapters" not in out["items"][-1]
    assert "metrics" not in out["items"][-1]


def test_append_rejects_non_int_chapters():
    with pytest.raises(SystemExit) as exc:
        of.append_items(_seed(),
                        [{"source": "fan-audit", "text": "x", "chapters": ["11"]}],
                        reviewed_sha="abc")
    assert "chapters" in str(exc.value)


def test_append_rejects_non_mapping_metrics():
    with pytest.raises(SystemExit) as exc:
        of.append_items(_seed(),
                        [{"source": "fan-audit", "text": "x", "metrics": [1, 2]}],
                        reviewed_sha="abc")
    assert "metrics" in str(exc.value)


def test_append_with_metrics_does_not_disturb_existing_state():
    out = of.append_items(_seed(), [{"source": "fan-audit", "text": "second",
                                     "chapters": [4], "metrics": {"interest": 3}}],
                          reviewed_sha="b")
    assert out["items"][0]["state"] == "solved"    # OF-1 from _seed()
    assert out["items"][1]["state"] == "rejected"  # OF-2 from _seed()
    assert out["items"][2]["id"] == "OF-3"


def test_render_shows_chapters_and_unknown_metrics():
    led = of.append_items(_seed(), [{
        "source": "fan-audit", "text": "A finding.",
        "chapters": [17, 19],
        "metrics": {"finding": "dead-thread", "some_future_key": "value"},
    }], reviewed_sha="abc")
    view = of.render_view(led)
    assert "ch 17, 19" in view
    assert "some_future_key=value" in view
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_feedback.py -k "chapters or metrics" -v`
Expected: FAIL — `KeyError: 'chapters'` / `AssertionError` on the render assertions

- [ ] **Step 3: Extend `append_items`**

In `scripts/outline_feedback.py`, replace the body of the `for pt in new_points:` loop (lines 88–100) with:

```python
    for pt in new_points:
        item = {
            "id": f"OF-{next_id}",
            "source": pt["source"],
            "pass": next_pass,
            "state": "open",
            "text": pt["text"],
        }
        rec = pt.get("recommendation")
        if isinstance(rec, str) and rec.strip():
            item["recommendation"] = rec
        # Optional measurements (spec 2026-07-30 §6.1). Stored OPAQUELY — the
        # ledger records and renders them, it never interprets them, so a new
        # finding type needs no change here. `append` is operator-driven and
        # fails loudly (module docstring), so a malformed value is named rather
        # than dropped: a silently-discarded metric would leave an item reading
        # as a vague observation, which is the exact failure §6.1 exists to fix.
        chapters = pt.get("chapters")
        if chapters is not None:
            if (not isinstance(chapters, list)
                    or not all(isinstance(c, int) and not isinstance(c, bool)
                               for c in chapters)):
                raise SystemExit(
                    f"append: item {item['id']}: 'chapters' must be a list of "
                    f"integers, got {chapters!r}")
            item["chapters"] = list(chapters)
        metrics = pt.get("metrics")
        if metrics is not None:
            if not isinstance(metrics, dict):
                raise SystemExit(
                    f"append: item {item['id']}: 'metrics' must be a mapping, "
                    f"got {type(metrics).__name__}")
            item["metrics"] = dict(metrics)
        items.append(item)
        next_id += 1
```

- [ ] **Step 4: Extend `render_view`**

In `render_view`, replace the per-item block (lines 136–140) with:

```python
        for it in rows:
            head = f"- **{it.get('id')}** · _{it.get('source')}_ · pass {it.get('pass')}"
            chs = it.get("chapters")
            if isinstance(chs, list) and chs:
                head += " · ch " + ", ".join(str(c) for c in chs)
            lines.append(head)
            lines.append(f"  {it.get('text', '').strip()}")
            mets = it.get("metrics")
            if isinstance(mets, dict) and mets:
                # Rendered generically so an unrecognised metric key still shows.
                lines.append("  _" + " · ".join(
                    f"{k}={v}" for k, v in mets.items()) + "_")
            rec = it.get("recommendation")
            if isinstance(rec, str) and rec.strip():
                lines.append(f"  **→** {rec.strip()}")
```

- [ ] **Step 5: Update the `--points` help text**

Replace line 175:

```python
    ap.add_argument("--points", help="append: path to a JSON array of "
                                     "{source,text,recommendation?,chapters?,metrics?}")
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS — the six new tests plus every existing one.

- [ ] **Step 7: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "$(cat <<'EOF'
feat(review): feedback items carry chapters + metrics

A finding has to be granular and measured to be worked one at a time, so
items gain two optional passthrough fields: chapters (list of ints) and
metrics (flat mapping). Both are opaque — the ledger stores and renders
them without interpreting, so a new finding type needs no change here — and
both are omitted entirely when absent, leaving existing items untouched.

Malformed values exit loud rather than being dropped: a silently discarded
metric leaves an item reading as a vague observation, which is the exact
failure this is meant to fix. render shows chapters on the item line and
metrics generically, so an unrecognised key still displays.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Record a skipped fan read on the lock certificate

**Files:**
- Modify: `scripts/preflight.py` — `cmd_lock_mystery` signature (line 294), the `skipped_lines` assembly (line 337), the `lock-mystery` parser (line 421), the dispatch (line 439)
- Test: `tests/test_preflight.py`

**Interfaces:**
- Consumes: the existing `skipped_lines: list[str]` and the certificate write at line 401.
- Produces: `cmd_lock_mystery(book, *, repo_root=None, run_config=None, waivers=None, note_skipped=None)` where `note_skipped` is a list of `"check-id: reason"` strings, each becoming a `skipped: <check-id> — <reason>` line on the certificate. CLI: `--note-skipped 'fan-read: reason'`, repeatable.

Per spec §7 there is exactly one use: the fan read did not happen. A same-model read is **not** a shortfall and gets no note.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_preflight.py`. That file imports `from scripts import preflight` and
already has the helper `_scaffold_lockable(tmp_path, *, ledger_fixture, valid_lexicon=True)`
plus the module-level `FAIR` ledger fixture — reuse both, exactly as
`test_lock_mystery_writes_lock_when_valid` does. Note it takes `tmp_path` as the repo root
and returns the ledger path, so pass `repo_root=tmp_path`.

```python
def test_lock_mystery_records_note_skipped_on_certificate(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        note_skipped=["fan-read: no sub-agent dispatch available"]) == 0
    cert = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "skipped: fan-read — no sub-agent dispatch available" in cert


def test_lock_mystery_note_skipped_without_colon_is_a_usage_error(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    with pytest.raises(SystemExit):
        preflight.cmd_lock_mystery("01", repo_root=tmp_path,
                                   note_skipped=["fan-read"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_preflight.py -k note_skipped -v`
Expected: FAIL — `TypeError: cmd_lock_mystery() got an unexpected keyword argument 'note_skipped'`

- [ ] **Step 3: Write the implementation**

Change the signature at line 294:

```python
def cmd_lock_mystery(book: str, *, repo_root=None, run_config=None, waivers=None,
                     note_skipped=None) -> int:
```

Immediately after `skipped_lines: list[str] = []` (line 337), insert:

```python
    # Coverage the certificate must not claim (spec 2026-07-30 §7). The only
    # current use is a fan read that did not happen at all — a same-model read
    # is NOT a shortfall and gets no note, because what a reader's credibility
    # rests on is a clean context, not a second model.
    for raw in (note_skipped or []):
        cid, sep, why = str(raw).partition(":")
        if not sep or not cid.strip() or not why.strip():
            _fail(f"--note-skipped expects 'check-id: reason', got {raw!r}")
        skipped_lines.append(f"skipped: {cid.strip()} — {why.strip()}")
```

Add to the parser at line 421, after the `--waive` line:

```python
    p_lock.add_argument("--note-skipped", action="append", default=[],
                        metavar='CHECK:"REASON"',
                        help="record coverage the certificate must not claim "
                             "(e.g. 'fan-read: no sub-agent dispatch available')")
```

Change the dispatch at line 439:

```python
    if args.cmd == "lock-mystery":
        return cmd_lock_mystery(args.book, waivers=args.waive,
                                note_skipped=args.note_skipped)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_preflight.py -k note_skipped -v`
Expected: PASS (2 tests)

Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "$(cat <<'EOF'
feat(preflight): lock-mystery --note-skipped records uncovered checks

Reuses the skipped_lines convention overloaded-chapter already uses: a
certificate must not claim coverage it does not have. One current use — the
fan read did not happen at all. A same-model read is deliberately NOT a
note, because what the reader's credibility rests on is a clean context,
not a second model (spec 2026-07-30 §7).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: The reader's staged contract, the runbook, and the naming rule

**Files:**
- Modify: `agents/outline-fan.md` (whole Inputs/Output/Cross-model section)
- Modify: `commands/plot-book.md` — step 8, the readback stage (lines 138–178)
- Modify: `agents/mystery-planner.md`
- Modify: `config/outline-template.md` (the `### Clues and Plants` and Hook comments)
- Modify: `CLAUDE.md` (the "Independence, isolation, reader simulation" section and the pipeline's optional-passes note)

**Interfaces:**
- Consumes: `plot_stage.py readers-copy NN --staged` (Task 3), `outline_feedback.py append --points` with the Task 4 shape, `preflight.py lock-mystery --note-skipped` (Task 5).
- Produces: no code interface. This task is prose contracts, and it is where the behaviour actually becomes real — Tasks 1–5 only make it possible.

There is no test cycle for prose. The verification step is a documentation-consistency read, then the full suite to confirm no runbook-referenced flag is misspelled.

- [ ] **Step 1: Rewrite `agents/outline-fan.md`**

Replace the file's body below the frontmatter with:

```markdown
# Outline Fan

**Role posture:** reader simulation. You are the one voice in the workshop that
does not know the ending — and that is the entire value.

**Isolation — a clean context, not a second model.** You are ALWAYS dispatched as a
fresh sub-agent and never run inside the plotting conversation. That is the whole
guarantee: an agent that already holds the solution and its own planning decisions
takes the shortcut whatever persona it is handed. On 2026-07-28 a read generated
inside the plotting session found this book's Act II reveal leaking in chapter 2,
called it "a strong hook", and reported the midpoint was strong. Running on the same
MODEL as the plot is fine and is not a degradation; running with the plot's CONTEXT
is not.

Blindness is additionally enforced BY CONSTRUCTION (`plot_stage.py readers-copy`
mechanically strips the solution, the wiring, the question ids, the track rows and the
chapter type-flags, and truncates the copy): do not go looking for what the strip
removed. You are never shown the whodunit ledger's `reveals:` block — that is the
answer key you are being measured against, and a reader told where the surprise is
cannot report whether the surprise works.

**Inputs:** `{ this stage's reader's copy
(output/book-NN/reports/outline-readers-copy-stage-K.md, or
outline-readers-copy.md on an unstaged book), the genre fan persona (resolved from
genre.yaml's fan_persona via the overlay), the stage number K }`. Nothing else — no
solution, no wiring, no plot/ folder, no whodunit yaml, no other agent's output, and
**not your own earlier stage reports**. Each stage answers from the text in front of
it; comparing across stages is the audit's job, not yours.

**Model:** prefer any reachable model other than `plot_model`. A second model is a
bonus, not the claim — if none is reachable, proceed on `plot_model` and say so
neutrally in the header. Do not write "independence reduced": it is not.

**Output:** `output/book-NN/reports/outline-fan-stage-K.md`, header carrying
`stage: K`, `context: fresh sub-agent`, and the model id. Then, in this order:

1. **What is this story about right now?** One sentence — the question actually live
   in your head as you stop reading.
2. **Top three suspects**, most to least, each with how sure you are (1–5).
3. **What do you expect the next big turn to be?** Commit to a guess.
4. **What have you stopped wondering about?** Anything you have quietly closed or
   lost interest in.
5. **Anything you suspect but cannot prove**, each with how sure (1–5).
6. **Per-chapter interest 1–5** (one line each) for this stage's new chapters, and any
   chapter where you would put the book down, with why.
7. **Would you buy this book?** Yes/no with one sentence — FINAL STAGE ONLY.

Prose as a reader, never rules or craft jargon. Advisory: you MUST never emit any
`^BLOCKING:` line, and your report never holds any gate.
```

- [ ] **Step 2: Rewrite step 8 of `commands/plot-book.md`**

Replace the whole readback stage (from `8. **Stage readback:**` through the line ending
`Present the fan's report and the findings side by side. The showrunner either`) with:

````markdown
8. **Stage readback:** a LOOP, not a single pass — read, findings, work them, re-read,
   then lock.

   ```bash
   echo "book=$book stage=PLOT-READBACK" > .penny/current-stage
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" readers-copy $book --staged
   ```

   `--staged` writes one reader's copy per protected reveal declared in the whodunit
   ledger's `reveals:` block — each cumulative from chapter 1 and stopping ONE CHAPTER
   SHORT of its reveal, plus a final whole-book stage. It prints the paths in stage
   order. When the ledger declares no `reveals:` it says so and writes the single-cut
   `outline-readers-copy.md` instead: an unstaged book still reads back exactly as
   before, never blocked.

   The cut matters and is not incidental. A copy that runs past a protected turn lets
   the fan read the turn and then report that the turn landed — which is precisely how
   book 01's midpoint leak passed unnoticed on 2026-07-28.

   **Dispatch `outline-fan` ONCE PER STAGE, each as a fresh sub-agent**, with that
   stage's copy, the genre's `fan_persona`, and the stage number. Never perform the read
   inline in this session: this session holds the solution and every plotting decision,
   and no persona survives that. Prefer a model other than `plot_model`; if none is
   reachable, proceed on `plot_model` — that is NOT a degradation and gets no note. Do
   not pass a fan its own earlier reports.

   If the read cannot be dispatched as a sub-agent at all, **skip it** and carry that to
   the certificate at step 9 with
   `--note-skipped 'fan-read: <why>'`. An inline read is worse than no read: it returns
   a confident report that reassures.

   **Then the suspicion audit.** You (this session) may see the solution — the readers
   have already filed, so you cannot contaminate them. Read the ledger's `reveals:`
   block and every stage report, and write
   `output/book-$book/reports/suspicion-audit.md`: one row per reveal — reveal id, the
   chapter it was meant to land in, where the reader first suspected it and how sure,
   and the gap. Below the table, set each not-yet-landed reveal's
   `reader_should_think_before` list (where the ledger supplies one) beside that stage's
   own "what is this story about right now" sentence.

   Name findings:
   - **`early`** — the reader named the reveal, confidence ≥3, in a stage closing before
     its `reveal_chapter`.
   - **`never`** — not suspected in any stage closing at or after its `reveal_chapter`.
     The fairness end of the same dial: too early is boring, never is a cheat.
   - **`predicted`** — the reader's "next big turn" for stage K is what stage K+1
     contains. The sharpest form of `early`.
   - **`drift`** — a chapter scored ≤3 for interest, or named as a put-down point.
   - **`dead-thread`** — the reader stopped wondering about something the outline still
     spends chapters servicing.

   **Append every finding to the feedback ledger** so it can be worked one at a time.
   **One item = one change to one chapter** — split a finding that implicates six
   chapters into six items. A finding like "the Lisa thread is weak" has failed however
   true it is, because the showrunner cannot sit down and fix it.

   Write a JSON array of
   `{source: "fan-audit", text, recommendation?, chapters?, metrics?}` to a temp file,
   then:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" append $book \
     --points /tmp/fan-audit-points.json
   ```

   Metrics per finding type: `early` → `finding, reveal, meant_to_land,
   first_suspected, confidence, gap_chapters`; `never` → `finding, reveal,
   meant_to_land, first_suspected: null, confidence: 0`; `predicted` → `finding, stage,
   predicted, actual_next, reveal, meant_to_land`; `drift` → `finding, interest,
   put_down_risk`; `dead-thread` → `finding, stage, closed_question,
   still_serviced_in`.

   Then run the proofreader:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tension_check.py" \
     input/book-$book/outline-skeleton.md \
     --beat-sheet "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" beat-sheet)" \
     --turning-points input/book-$book/plot/turning-points.md \
     --whodunit series/whodunit/book-$book.yaml
   ```

   `penny_genre.py beat-sheet` resolves THROUGH the active genre's `genre.yaml`
   `beat_sheet:` key (overlay-resolved, so a series can still override its genre's
   numbers) — never a hardcoded filename, so a genre pack naming its file something
   other than `beat-sheet.yaml` still gets its curve/beat checks run. It prints an
   empty string when the genre declares no `beat_sheet:` key at all; `tension_check.py`
   then simply skips the curve/beat checks and runs only the graph checks (causality,
   open-question ledger, hook chain, chapter coverage).

   Present the audit, the open ledger items, and the tension findings side by side. The
   showrunner either works the open items (editing `outline.md` and the whodunit ledger,
   marking each `solved`/`rejected` by hand in
   `output/book-$book/reports/outline-feedback.yaml`) and comes back round this stage,
   or signs off. Nothing here blocks: the audit has no exit code and the fan holds no
   gate. The showrunner's sign-off is the decision point, as before.
````

- [ ] **Step 3: Add the `reveals:` block and the naming rule to `agents/mystery-planner.md`**

Add to that agent's output contract:

```markdown
**Protected reveals.** Propose a `reveals:` block beside `act_pivots:` — one entry per
turn the reader must not have early, in ascending `reveal_chapter` order, each with
`id`, `reveal_chapter`, `author_truth` (one line), and optionally
`reader_should_think_before` (what the reader should believe instead meanwhile). A book
has more than one: the culprit reveal that `reveal_chapter` already names is usually the
LAST of several, and the mid-book turns are the ones that get leaked. `reveal_chapter`
(singular) keeps its existing meaning and is unaffected.

**Name a clue by what it LOOKS like, never by what it means.** Clue ids and q-slugs are
rendered verbatim into the chapter packet, which is the drafter's instruction — so
`c02-lisa-already-met-maggie` at plant chapter 2 tells chapter 2's writer the Act II
answer, and the scene gets shaped around it even if the word never reaches the page.
Write `c02-early-key-note`. The true meaning belongs in the clue's `description:` and in
the reveal's `author_truth`, which carry no label into the packet. Same for questions:
`q-vase — whose hand made this vase?`, never "who made the false Maggie vase?".
```

- [ ] **Step 4: Add the naming note to `config/outline-template.md`**

In the `### Clues and Plants` HTML comment, after the existing sentence about giving every
scheduled clue a `description:`, add:

```
     NAME a clue and a q-slug by what it LOOKS like at the chapter where it
     lands, never by what it turns out to mean — the id is rendered into the
     packet, which is the drafter's instruction, so a solution-shaped id
     leaks the reveal into the writing of every chapter that plants it.
     "early-key-note", not "lisa-already-met-maggie".
```

In the Hook comment, after the grade explanation, add:

```
     The q-slug and its phrasing travel: the wiring graph matches a question
     across chapters by slug, so a question named after its own answer leaks
     for its whole life. Phrase it as the reader would ask it.
```

- [ ] **Step 5: Update `CLAUDE.md`**

In the "Independence, isolation, reader simulation" section, replace the
**Reader simulation** bullet with:

```markdown
- **Reader simulation = the reader stays unknowing, in a clean context.**
  `{ text, persona_file }` only. Not a guardrail: a reader who knows the culprit cannot
  report that she guessed her in chapter four. For the OUTLINE fan read the operative
  property is **isolation, not independence** — `outline-fan` must always be a fresh
  sub-agent and never run inline in the plotting session, because inherited context
  defeats any persona; running on the same *model* as the plot is fine and is not
  recorded as a shortfall (spec `2026-07-30-staged-reveal-readback-design.md` §7).
  Personas are distinct lenses and are **never averaged**; models are the
  within-persona consensus axis (≥K-of-M via `beta_consensus_k`).
```

In the `/review-outline` paragraph of "Optional pre-draft passes", append:

```markdown
The same ledger also receives the plot workshop's **`fan-audit`** items — the staged
read-back's measured findings (spec `2026-07-30-staged-reveal-readback-design.md`).
Items may carry `chapters:` and `metrics:`, stored opaquely; one item is one change to
one chapter, because the showrunner works them one at a time. `/plot-book`'s readback is
therefore a **loop** — read, findings, work them, re-read, lock — not a single pass.
```

- [ ] **Step 6: Verify the docs against the code**

Confirm every flag the runbooks now name actually exists:

```bash
python3 scripts/plot_stage.py readers-copy --help
python3 scripts/outline_feedback.py append --help
python3 scripts/preflight.py lock-mystery --help
```

Expected: `--staged`, `--points` mentioning `chapters?,metrics?`, and `--note-skipped`
all present.

Then confirm no stale vocabulary survives:

```bash
grep -rn "independence reduced" agents/ commands/ CLAUDE.md
```

Expected: hits only in `/review-outline`'s panel degradation (which keeps the term
legitimately — that IS a model-difference claim) and none in `outline-fan.md` or
`plot-book.md`'s readback.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add agents/outline-fan.md agents/mystery-planner.md commands/plot-book.md \
        config/outline-template.md CLAUDE.md
git commit -m "$(cat <<'EOF'
feat(readback): staged reveal-aware read-back becomes the workshop's contract

outline-fan is now a staged reader: one fresh sub-agent per protected
reveal, each answering what the story is about right now, its three
suspects with confidence, what it expects next, what it has stopped
wondering about, and what it suspects unproven. Never dispatched inline —
the 2026-07-28 read ran inside the plotting session, praised a midpoint
leak as "a strong hook", and that is what this prevents. Same model is
fine and no longer written up as reduced independence.

plot-book's readback becomes a loop: staged copies, per-stage reads, a
suspicion audit against the reveals block (early / never / predicted /
drift / dead-thread), findings appended to the existing feedback ledger as
fan-audit items with their measurements, then work-and-re-read or sign off.
One item is one change to one chapter.

mystery-planner now proposes the reveals block and must name clues and
q-slugs by apparent meaning — the id reaches the drafter's instruction, so
a solution-shaped id leaks the reveal into the writing of every chapter
that plants it. Recorded in the outline template too.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review notes

**Spec coverage.** §3 `reveals:` schema → Task 1. §3.1 naming discipline (authoring rule,
deliberately no checker) → Task 6 steps 3–4. §4 staged copies + cumulative + legacy path →
Tasks 2–3. §5 the six questions → Task 6 step 1. §6 audit + finding names → Task 6 step 2.
§6.1 ledger items, granularity rule, metrics per type, the loop → Task 4 + Task 6 steps 2
and 5. §7 clean context, no independence note, `--note-skipped` for a skipped read →
Task 5 + Task 6 steps 1–2, 5. §8 error table → Task 1 (malformed), Task 3 (out-of-range
reveal, no skeleton), Task 6 step 2 (inline refusal, unreachable fan). §9 testing → the
test steps of Tasks 1–5. §10 book 01 → **deliberately not a task**: the spec assigns that
repair to the showrunner, editorially, and `/plot-book` is not re-run. §11 out of scope
(the stage layer, moving `macro-structure.md` pre-lock) → no tasks, correctly.

**Naming consistency.** `_reveals` / `reveal_stages` / `readers_copy_staged` /
`last_chapter` / `note_skipped` / `chapters` / `metrics` / `source: "fan-audit"` /
`outline-readers-copy-stage-K.md` / `outline-fan-stage-K.md` / `suspicion-audit.md` are
used identically in every task and in the runbook.

**Known follow-up, not blocking.** The working tree carries unrelated uncommitted work
(the cozy beat-sheet cap retune, a `test_preflight.py` fixture bump, the `archetype.md`
rewrite, the new `macro-structure.md` rubric, and `/review-outline` lens wiring). Commit or
stash that separately — do not sweep it into this plan's commits, and expect
`tests/test_preflight.py` to already differ from `HEAD` when Task 5 edits it.
