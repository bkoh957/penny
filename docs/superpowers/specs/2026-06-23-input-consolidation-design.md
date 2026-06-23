# Input Consolidation — Design Spec
Date: 2026-06-23

## Problem

User-authored inputs are scattered across two directories that also contain Penny-derived data:

- `output/book-NN/outline.md` — the per-book outline lives in `output/`, which is semantically owned by Penny's produced artifacts.
- `series/series-bible.md`, `series/style-sheet.md`, `series/whodunit-ledger.md` — the series-level authored files live alongside derived continuity data, whodunit yaml, and arc-ledger in `series/`.

The fix: introduce a single `input/` tree for everything the showrunner authors. Penny's derived data stays exactly where it is.

## Chosen Approach

Pure path migration. Move the four authored files to `input/`, update every hardcoded reference across commands/agents/scripts/tests/docs. No new abstractions, no config keys, no symlinks. `git mv` preserves history on each file.

## New Directory Structure

```
input/
  series/
    series-bible.md        ← was series/series-bible.md
    style-sheet.md         ← was series/style-sheet.md
    whodunit-ledger.md     ← was series/whodunit-ledger.md
  book-NN/
    outline.md             ← was output/book-NN/outline.md
```

Everything else is unchanged:

- `series/` retains derived data only: `continuity/`, `whodunit/`, `arc-ledger.md`.
- `output/book-NN/` retains Penny's chapter artifacts: `chapters/`, `mystery-solution.md`.
- `config/` (packs, rubrics, run-config) is engine configuration — not user narrative input — and does not move.

## Files That Move

| Old path | New path |
|---|---|
| `series/series-bible.md` | `input/series/series-bible.md` |
| `series/style-sheet.md` | `input/series/style-sheet.md` |
| `series/whodunit-ledger.md` | `input/series/whodunit-ledger.md` |
| `output/book-NN/outline.md` | `input/book-NN/outline.md` |

The Book 01 concrete move: `output/book-01/outline.md` → `input/book-01/outline.md`.

## Reference Updates

All hardcoded path references updated in one pass:

| File | Change |
|---|---|
| `scripts/penny-statusline.sh` | `output/book-$book/outline.md` → `input/book-$book/outline.md` |
| `.claude/commands/scaffold-book.md` | Argument-hint doc: `output/book-$book/outline.md` → `input/book-$book/outline.md` |
| `.claude/commands/finalize-chapter.md` | 4× `series/style-sheet.md` → `input/series/style-sheet.md` |
| `.claude/agents/copy-editor.md` | 5× `series/style-sheet.md` → `input/series/style-sheet.md` |
| `config/copy-edit/copy-edit.md` | 4× `series/style-sheet.md` → `input/series/style-sheet.md` |
| `config/voice-pack/voice-pack.md` | 1× `series/style-sheet.md` → `input/series/style-sheet.md` |
| `tests/test_scaffold.py` | 3 path assertions updated to `input/series/` |
| `scripts/outline_check.py` | Docstring/help text updated to `input/book-NN/outline.md` |
| `penny-design-v3.md` | Directory tree diagram and prose references updated |

`scripts/fairplay_check.py` — comment-only mention of whodunit-ledger, no path change needed. `outline_check.py`'s runtime logic takes the path as a CLI argument; only the help text changes.

## Invariants Preserved

- The outline is still a CLI argument to `/scaffold-book` — the user passes the path, so no command logic changes beyond updating the documented default.
- The copy-editor and finalize-chapter workflows read/write the style-sheet at a path. After the move, that path is `input/series/style-sheet.md` everywhere.
- `mystery-solution.md` is derived by the book-scaffolder from the outline — it stays in `output/book-NN/` (sealed, Penny-owned).
- `series/whodunit-ledger.md` is a human doc, never parsed. The move is cosmetic for all scripts.
- `.penny/` (gitignored runtime state) is untouched.

## Migration Order

1. `git mv` the four files to their new homes.
2. Update all references (commands, agents, scripts, config, tests, docs) in one commit.
3. Run `python3 -m pytest` — all 249 tests should pass.
