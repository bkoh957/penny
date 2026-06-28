# /expand-outline

Expands skeletal chapter stubs from `input/book-NN/outline-skeleton.md` into the full
scene-breakdown outline in `input/book-NN/outline.md`. Context-rich: the expander reads
the sealed solution, so the mystery must already be planned.

## Steps

0. **Precondition:** the sealed solution must exist (the expander reads it). Abort if not:

   ```bash
   test -f output/book-$book/mystery-solution.md || { echo "no sealed solution for book $book — run /plan-mystery $book first"; exit 1; }
   ```

1. **Parse args:** `book` (e.g. `01`) and optional `chapter` (e.g. `05`).

2. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=${chapter:-all} stage=EXPAND" > .penny/current-stage
   ```

3. **Determine target chapters:**
   - If `chapter` given → just that chapter.
   - Else (batch) → every `## Chapter NN` in `input/book-$book/outline-skeleton.md`
     whose section in `input/book-$book/outline.md` does **not** already contain a
     `### Scene ` heading (i.e. not yet expanded). This protects hand-crafted chapters.

4. **For each target chapter**, assemble the inputs listed in
   `.claude/agents/outline-expander.md` (the stub for that chapter; the voice/setting/
   genre/length packs; `series/continuity/canon-core.md` + the brief-derived ledger
   slice; `input/series/series-bible.md`; and the sealed `output/book-$book/mystery-solution.md`
   + `series/whodunit/book-$book.yaml`). Dispatch the `outline-expander` sub-agent and
   write its output into `input/book-$book/outline.md`, **replacing that chapter's
   section** (from its `## Chapter NN` heading to the next chapter heading or EOF),
   preserving chapter order.

   **The expander is context-rich and there is no automated leak-guard** — before moving
   on, eyeball its output: it must not name the culprit as the culprit, or state the
   motive/solution, in any chapter before the in-story detective-click (~ch19). If it does,
   discard that chapter's output and re-dispatch with a tightened guardrail.

5. **Advance the marker:**

   ```bash
   echo "book=$book chapter=${chapter:-all} stage=EXPANDED" > .penny/current-stage
   ```
