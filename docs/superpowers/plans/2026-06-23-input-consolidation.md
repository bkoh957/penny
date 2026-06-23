# Input Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the four showrunner-authored files into a new `input/` tree, then update every hardcoded reference so the rest of the system points to the new paths.

**Architecture:** Pure path migration — `git mv` four files, then find-and-replace every reference across commands/agents/scripts/tests/docs. No new abstractions, no config keys, no symlinks. Tests are updated first (TDD) so the file moves make them pass.

**Tech Stack:** bash, Python 3, pytest

## Global Constraints

- `git mv` for all file moves (preserves history).
- No new config keys, no new abstractions.
- `input/series/` holds series-level authored files; `input/book-NN/` holds the per-book outline.
- `series/` retains only derived data (continuity/, whodunit/, arc-ledger.md). `output/book-NN/` retains only Penny-produced artifacts (chapters/, mystery-solution.md).
- Run `python3 -m pytest` after every commit to confirm no regressions.

---

### Task 1: Update tests and move files (TDD)

**Files:**
- Modify: `tests/test_scaffold.py`
- Move: `series/series-bible.md` → `input/series/series-bible.md`
- Move: `series/style-sheet.md` → `input/series/style-sheet.md`
- Move: `series/whodunit-ledger.md` → `input/series/whodunit-ledger.md`
- Move: `output/book-01/outline.md` → `input/book-01/outline.md`

**Interfaces:**
- Produces: `input/series/` and `input/book-01/` directories with the four files at their new paths.

- [ ] **Step 1: Update REQUIRED_SERIES_FILES in test_scaffold.py**

Replace the existing list at the top of `tests/test_scaffold.py`:

```python
REQUIRED_SERIES_FILES = [
    "input/series/series-bible.md",
    "series/arc-ledger.md",
    "input/series/style-sheet.md",
    "input/series/whodunit-ledger.md",
]
```

Also add a new list and parametrized test immediately after the existing `test_series_memory_file_exists_and_nonempty` test:

```python
REQUIRED_INPUT_BOOK_FILES = [
    "input/book-01/outline.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_INPUT_BOOK_FILES)
def test_input_book_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"
```

- [ ] **Step 2: Run tests — expect failures**

```bash
python3 -m pytest tests/test_scaffold.py -v
```

Expected: 4 FAIL — `input/series/series-bible.md`, `input/series/style-sheet.md`, `input/series/whodunit-ledger.md`, `input/book-01/outline.md` not found. All other tests pass.

- [ ] **Step 3: Create directories and move files**

```bash
mkdir -p input/series input/book-01
git mv series/series-bible.md input/series/series-bible.md
git mv series/style-sheet.md input/series/style-sheet.md
git mv series/whodunit-ledger.md input/series/whodunit-ledger.md
git mv output/book-01/outline.md input/book-01/outline.md
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_scaffold.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_scaffold.py input/
git commit -m "feat(structure): move authored inputs to input/ tree"
```

---

### Task 2: Update scripts

**Files:**
- Modify: `scripts/penny-statusline.sh:61`
- Modify: `scripts/outline_check.py:3,10,106`

**Interfaces:**
- Consumes: `input/book-01/outline.md` from Task 1.

- [ ] **Step 1: Update penny-statusline.sh line 61**

Change:
```bash
outline="$ROOT/output/book-$book/outline.md"
```
To:
```bash
outline="$ROOT/input/book-$book/outline.md"
```

- [ ] **Step 2: Update outline_check.py docstring and help text**

Line 3 — change:
```
Validates that an author outline (output/book-NN/outline.md) is SHAPED like an
```
To:
```
Validates that an author outline (input/book-NN/outline.md) is SHAPED like an
```

Line 10 — change:
```
  python3 scripts/outline_check.py output/book-01/outline.md
```
To:
```
  python3 scripts/outline_check.py input/book-01/outline.md
```

Line 106 — change:
```python
    ap.add_argument("outline", help="path to output/book-NN/outline.md")
```
To:
```python
    ap.add_argument("outline", help="path to input/book-NN/outline.md")
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/penny-statusline.sh scripts/outline_check.py
git commit -m "fix(scripts): update outline path to input/book-NN/"
```

---

### Task 3: Update commands and agents

**Files:**
- Modify: `.claude/commands/scaffold-book.md`
- Modify: `.claude/commands/finalize-chapter.md`
- Modify: `.claude/agents/copy-editor.md`

- [ ] **Step 1: Update scaffold-book.md**

In `.claude/commands/scaffold-book.md`, find line 15:
```
   `output/book-$book/outline.md`), optional `--approve`.
```
Change to:
```
   `input/book-$book/outline.md`), optional `--approve`.
```

- [ ] **Step 2: Update finalize-chapter.md — all 4 occurrences**

Replace every instance of `series/style-sheet.md` with `input/series/style-sheet.md` in `.claude/commands/finalize-chapter.md`. There are 4 occurrences (lines 57, 117, 121, 176 approximately — use replace-all).

- [ ] **Step 3: Update copy-editor.md — all 5 occurrences**

Replace every instance of `series/style-sheet.md` with `input/series/style-sheet.md` in `.claude/agents/copy-editor.md`. There are 5 occurrences.

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/scaffold-book.md .claude/commands/finalize-chapter.md .claude/agents/copy-editor.md
git commit -m "fix(commands/agents): update style-sheet and outline paths"
```

---

### Task 4: Update config files

**Files:**
- Modify: `config/copy-edit/copy-edit.md`
- Modify: `config/voice-pack/voice-pack.md`

- [ ] **Step 1: Update config/copy-edit/copy-edit.md — all 4 occurrences**

Replace every instance of `series/style-sheet.md` with `input/series/style-sheet.md`. There are 4 occurrences.

- [ ] **Step 2: Update config/voice-pack/voice-pack.md — 1 occurrence**

Find:
```
> Says *how to write*. (What was *decided* lives in `series/style-sheet.md`.)
```
Change to:
```
> Says *how to write*. (What was *decided* lives in `input/series/style-sheet.md`.)
```

- [ ] **Step 3: Run tests**

```bash
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add config/copy-edit/copy-edit.md config/voice-pack/voice-pack.md
git commit -m "fix(config): update style-sheet path to input/series/"
```

---

### Task 5: Update penny-design-v3.md

**Files:**
- Modify: `penny-design-v3.md`

- [ ] **Step 1: Update the directory tree — /series block**

Find the `/series` block in the directory tree (around line 118). Remove these three lines from it:
```
  series-bible.md               overarching 13-book arc, themes, the long game
  whodunit-ledger.md            [human doc, NEVER parsed] how the schedule works,
                                narrative notes
  style-sheet.md                accumulating spelling/punctuation decisions
```

- [ ] **Step 2: Update the directory tree — /output block**

Find `outline.md` under `/output/book-NN` (around line 145). Remove that line.

- [ ] **Step 3: Add /input block to the directory tree**

Insert a new `/input` section before `/series` in the tree:

```
/input                        showrunner-authored source files
  /series
    series-bible.md             overarching 13-book arc, themes, the long game
    style-sheet.md              accumulating spelling/punctuation decisions
    whodunit-ledger.md          [human doc, NEVER parsed] how the schedule works,
                                narrative notes
  /book-NN
    outline.md                  per-book chapter beats + sealed Solutions
```

- [ ] **Step 4: Update prose references**

Find and replace these two prose occurrences:

Line 304: `` `/series/whodunit-ledger.md` (human notes) `` → `` `/input/series/whodunit-ledger.md` (human notes) ``

Line 308: `` if the book's whodunit-ledger is absent `` — no path here, no change needed. Check for any other hardcoded paths to the three series files and the outline in prose sections; replace with `input/series/` or `input/book-NN/` as appropriate.

- [ ] **Step 5: Run tests**

```bash
python3 -m pytest -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add penny-design-v3.md
git commit -m "docs(design): update directory tree for input/ consolidation"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full test suite**

```bash
python3 -m pytest -v
```

Expected: all tests pass (249+ tests).

- [ ] **Step 2: Grep for any remaining stale references**

```bash
grep -rn "series/series-bible\|series/style-sheet\|series/whodunit-ledger\|output/book.*outline" \
  .claude scripts config tests penny-design-v3.md CLAUDE.md README.md \
  2>/dev/null | grep -v ".git" | grep -v "__pycache__"
```

Expected: no output. If any hits remain, fix them and re-commit.

- [ ] **Step 3: Confirm input/ directory looks right**

```bash
find input/ -type f | sort
```

Expected output:
```
input/book-01/outline.md
input/series/series-bible.md
input/series/style-sheet.md
input/series/whodunit-ledger.md
```
