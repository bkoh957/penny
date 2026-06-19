---
description: Manually draft one chapter (Phase 1: no review bus yet).
argument-hint: <book-number> <chapter-number>
---
# /draft-chapter

Manual single-chapter draft. Phase 1 path: assemble context → dispatch the drafter
→ write the draft. (Review/edit/finalize arrive in later phases.)

## Steps

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
