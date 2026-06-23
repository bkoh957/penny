---
description: Derive a book's structure from a prose outline, review it, then earn the lock (design §5a, outline-first front door).
argument-hint: <book-number> <outline-path> [--approve]
---
# /scaffold-book

The author front door. The writer authors a prose **outline**; this command derives
the mechanical structure into its existing homes, foregrounds the mystery strand for
review, and — on approval — runs the **unchanged** `lock-mystery`. The lock is still
earned by the shipped checker; this command never writes a certificate.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), `outline=$2` (e.g.
   `input/book-$book/outline.md`), optional `--approve`.

2. **Structural gate (deterministic):**

   ```bash
   python3 scripts/outline_check.py "$outline"
   ```

   A non-zero exit means the outline is not shaped like an outline yet (missing
   solution, chapter gap, non-integer count, empty beat). Show the named predicate
   and stop — do not derive.

3. **Re-derivation hygiene (§5a clean re-lock):** if a lock exists, delete it first,
   because re-planning requires re-validation. v1 overwrites derived artifacts.

   ```bash
   rm -f ".penny/locks/book-$book.mystery.lock"
   ```

4. **Dispatch the `book-scaffolder` sub-agent** with `{ outline_text, book_number }`.
   It writes the derived artifacts UNLOCKED to their real homes (see
   `.claude/agents/book-scaffolder.md`): the gated mystery →
   `series/whodunit/book-$book.yaml`; non-mystery strands →
   `series/continuity/threads/` + `series/arc-ledger.md`; cast & locations →
   `series/continuity/characters|locations/`; always-true facts →
   `series/continuity/canon-core.md`; the sealed key →
   `output/book-$book/mystery-solution.md`.

5. **Emit the tiered review** `output/book-$book/scaffold-review.md`:
   - **Foreground the MYSTERY STRAND** — the clue schedule as plant→payoff chapters
     with `necessary` flags, red herrings, the alibi grid, culprit/victim/deception —
     with an inline DRY-RUN of what the lock will say, so the writer sees it BEFORE
     approving:

     ```bash
     python3 scripts/readiness_check.py "$book"
     python3 scripts/fairplay_check.py "series/whodunit/book-$book.yaml" --target "book-$book"
     ```

   - **Collapse (expandable)** the non-mystery Threads, the Cast & Locations, and the
     canon-core updates. The artifacts are already on disk; this doc is the lens.

6. **Pause for the writer** (human gate; default `scaffold_approval: review`). The
   writer edits the outline (or the derived yaml) until the dry-run is green.

7. **On `/scaffold-book $book $outline --approve`** — earn the lock with the SHIPPED,
   UNCHANGED checker:

   ```bash
   python3 scripts/preflight.py lock-mystery "$book"
   ```

   It mints `.penny/locks/book-$book.mystery.lock` iff fairplay + lexicon pass;
   otherwise it exits non-zero and writes no lock, and the review shows what to fix.
   Generated ≠ trusted — validity is earned here, never by the scaffolder.

## Deferred (do not build here)
Per-chapter blind brief derivation (`/draft-chapter` falls back to canon-core-only);
the looping multi-mystery gate (v1 gates the first `## Solution`; extra Solutions ride
as un-gated threads); diff-on-edit re-derivation review (v1 overwrites).
