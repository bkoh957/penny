---
description: Expand skeletal chapter stubs in a book's outline into packet-format chapter blocks, in place — for outlines the cut never touched.
argument-hint: <book-number> [chapter-number]
arguments: [book, chapter]
---
# /expand-outline

Expands skeletal chapter stubs in `input/book-NN/outline.md` into packet-format chapter
blocks (spec 2026-07-18 §3), in place. Context-rich: the expander reads the sealed
solution, so the mystery must already be planned. Scenes are no longer part of the outline
at all — they belong to the per-chapter map, staged later by `/map-chapter`.

## Steps

1. **Parse args:** `book` (e.g. `01`) and optional `chapter` (e.g. `05`).

2. **Preconditions:**

   The sealed solution must exist (the expander reads it). Abort if not:

   ```bash
   test -f output/book-$book/mystery-solution.md || { echo "no sealed solution for book $book — run /plan-mystery $book first"; exit 1; }
   ```

   **This command is for outlines that were never cut, and refuses the ones that were.**
   An outline produced by `/plot-book`'s cut is regenerated from `story.md`, never edited
   upstream of it — expanding a stub in place there would silently make `story.md` and
   `outline.md` disagree, the exact drift that retired the outline's earlier staging layer
   in the first place. A legacy outline with no `cut_output_sha256` stamp (hand-authored, or
   `/scaffold-book`-derived — book 01, for instance) was never cut from a `story.md` and
   keeps working exactly as before. If `input/book-$book/outline.md` exists, check it:

   ```bash
   if [ -f "input/book-$book/outline.md" ]; then
     python3 -c "
   import sys
   sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
   from scripts.story_cut import expand_in_place_refusal
   text = open('input/book-$book/outline.md', encoding='utf-8').read()
   refusal = expand_in_place_refusal(text)
   if refusal:
       sys.exit('expand-outline: ' + refusal)
   " || exit 1
   fi
   ```

   If it refuses, tell the showrunner in one line: this book's outline is cut from
   `story.md` — edit the beats there and re-run the cut instead of expanding in place.

3. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=${chapter:-all} stage=EXPAND" > .penny/current-stage
   ```

4. **Determine target chapters:**
   - If `chapter` given → just that chapter.
   - Else (batch) → every `## Chapter NN` in `input/book-$book/outline.md` whose section
     does **not** already contain a `### Required Beats` heading (i.e. not yet expanded
     into packet format). This protects hand-crafted chapters.

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
