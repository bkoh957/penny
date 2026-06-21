---
description: Draft one chapter — first step of the full pipeline (review via /review-chapter, finalize via /finalize-chapter).
argument-hint: <book-number> <chapter-number>
---
# /draft-chapter

Drafts one chapter: assemble context → dispatch the drafter → write the draft. The
chapter then moves through the full pipeline: gate it with `/review-chapter`, then
edit and commit with `/finalize-chapter`.

## Steps

0. **Pre-flight gate (Phase 3):** the mystery must be validated and locked before
   any chapter is drafted. Hard-fail aborts before context assembly:

   ```bash
   python3 scripts/preflight.py draft $1 $2
   ```

   A non-zero exit means the book's mystery is absent, unpopulated, or unlocked —
   run `/plan-mystery $1` first. Do not proceed on failure.

1. **Parse args:** `book=$1` (e.g. `01`), `chapter=$2` (e.g. `01`).

2. **Write the harness state marker** so the status bar reflects position
   (design §11):

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=DRAFT" > .penny/current-stage
   ```

3. **Assemble the ledger slice** (design §4.2): always load
   `series/continuity/canon-core.md`; then load the continuity entries named in the
   chapter brief and their one-hop `links`. (Phase 1: if no brief exists yet, load
   canon-core only.)

4. **Ensure output paths exist:**

   ```bash
   mkdir -p output/book-$book/chapters
   ```

5. **Dispatch the `drafter` sub-agent** with the inputs listed in
   `.claude/agents/drafter.md`. Write its output to
   `output/book-$book/chapters/ch-$chapter.draft.md` including `drafted_by`
   frontmatter.

6. **Clear/advance the marker** when done:

   ```bash
   echo "book=$book chapter=$chapter stage=DRAFTED" > .penny/current-stage
   ```
