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
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" draft $1 $2
   ```

   A non-zero exit means the book's mystery is absent, unpopulated, or unlocked —
   run `/plan-mystery $1` first. Do not proceed on failure.

0b. **Outline review notice (advisory, non-blocking).** Surface any open outline feedback
    or staleness before drafting. This NEVER blocks — always proceed regardless of output:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" status $1
    ```

    An open-item or "stale — re-run /review-outline" notice is a reminder, not a gate.

1. **Parse args:** `book=$1` (e.g. `01`), `chapter=$2` (e.g. `01`).

2. **Write the harness state marker** so the status bar reflects position
   (design §11):

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=DRAFT" > .penny/current-stage
   ```

3. **Assemble the chapter brief and ledger slice** (design §4.2):
   - **Chapter brief:** Read `input/book-$book/outline.md`. Extract the full
     section for chapter $chapter: the `## Chapter $chapter — *` heading, its
     **Chapter Summary**, **Chapter Structure** (Start/Desire, Pressure/Obstacle,
     Turn/Change, Texture/Pleasure Layer, Hook), and **Track Movement** (M/P/R/B).
     This is the brief passed to the drafter.
   - **Ledger slice:** Always load `series/continuity/canon-core.md`; then load the
     continuity entries named in the brief and their one-hop `links`.

4. **Ensure output paths exist:**

   ```bash
   mkdir -p output/book-$book/chapters
   ```

5. **Capture the draft date** so the stamp is deterministic (not the agent's guess):

   ```bash
   draft_date=$(date +%F)   # YYYY-MM-DD
   ```

6. **Dispatch the `drafter` sub-agent** with the inputs listed in
   `agents/drafter.md`, passing `draft_date` for the `drafted_on` stamp.
   Write its output to `output/book-$book/chapters/ch-$chapter.draft.md` including
   `drafted_by` and `drafted_on: $draft_date` frontmatter.

7. **Clear/advance the marker** when done:

   ```bash
   echo "book=$book chapter=$chapter stage=DRAFTED" > .penny/current-stage
   ```
