---
description: Per-book mystery design + lock (design §5a). Validate-once-then-freeze.
argument-hint: <book-number>
---
# /plan-mystery

Run once per book, before any `/draft-chapter`. Separates three roles: showrunner
sets the core, `mystery-planner` proposes the construction, showrunner approves and
locks. The lock file is a **certificate** — it exists only if fairplay + lexicon
validation passed (the only writer is `preflight.py lock-mystery`).

## Steps

1. **Parse args:** `book=$1` (e.g. `01`).

2. **Showrunner sets the irreducible core** (interactive): who did it, why, the
   central deception, and any series-arc constraints. This is the irreducibly human
   taste-and-strategy layer.

3. **Dispatch the `mystery-planner` sub-agent** with the core + series bible. It
   proposes the clue schedule, red herrings, and alibi grid.

4. **Write the proposed (unlocked) ledger** to `series/whodunit/book-$book.yaml`.
   Do NOT add a `locked:` field — the lock is an out-of-band file, never a field
   inside the data it gates (a field would be a forgeable certificate).

5. **Showrunner reviews and approves** (taste): edit the proposed yaml until right.

6. **Write the sealed solution** to `output/book-$book/mystery-solution.md` — the
   full answer key, sealed from the drafter, beta, and final readers.

7. **Validate and lock (LAST):**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book
   ```

   This runs `fairplay_check.py` (numeric fairness + culprit/victim/suspect
   existence) and `lexicon_check.py --validate` (lexicon schema). Only if both pass
   does it write `.penny/locks/book-$book.mystery.lock`. If either fails it exits
   non-zero and writes no lock — leaving an unlocked-but-present yaml that
   `/draft-chapter` correctly rejects. Fix the reported issues and re-run.

   **Re-planning:** delete the lock, edit the yaml, re-run this step — the clean
   re-lock story (§5a).
