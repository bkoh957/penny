# /expand-outline

Expands skeletal chapter stubs from `input/book-NN/outline-skeleton.md` into the full
scene-breakdown outline in `input/book-NN/outline.md`. Context-rich: the expander reads
the sealed solution, so the mystery must already be planned.

## Steps

1. **Parse args:** `book` (e.g. `01`) and optional `chapter` (e.g. `05`).

2. **Precondition:** the sealed solution must exist (the expander reads it). Abort if not:

   ```bash
   test -f output/book-$book/mystery-solution.md || { echo "no sealed solution for book $book — run /plan-mystery $book first"; exit 1; }
   ```

3. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=${chapter:-all} stage=EXPAND" > .penny/current-stage
   ```

4. **Determine target chapters:**
   - If `chapter` given → just that chapter.
   - Else (batch) → every `## Chapter NN` in `input/book-$book/outline-skeleton.md`
     whose section in `input/book-$book/outline.md` does **not** already contain a
     `### Scene ` heading (i.e. not yet expanded). This protects hand-crafted chapters.
   - **If `input/book-$book/outline.md` does not exist yet**, initialize it before the
     skip-check (copy the frontmatter from `outline-skeleton.md`, or create an empty file)
     so that section replacement in Step 5 will work.

5. **For each target chapter**, assemble the inputs listed in
   `agents/outline-expander.md` (the stub for that chapter; the voice/setting/
   genre/length packs; `series/continuity/canon-core.md` + the brief-derived ledger
   slice; `input/series/series-bible.md`; and the sealed `output/book-$book/mystery-solution.md`
   + `series/whodunit/book-$book.yaml`). Dispatch the `outline-expander` sub-agent and
   write its output into `input/book-$book/outline.md`, **replacing that chapter's
   section** (from its `## Chapter NN` heading to the next chapter heading or EOF),
   preserving chapter order.

6. **Advance the marker:**

   ```bash
   echo "book=$book chapter=${chapter:-all} stage=EXPANDED" > .penny/current-stage
   ```
