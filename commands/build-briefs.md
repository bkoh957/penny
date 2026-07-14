---
description: Compile a locked outline into one prompt-shaped brief per chapter — the emphasis hierarchy, the word budgets, the obligations checklist, the commissioned first and last lines.
argument-hint: <book-number>
---
# /build-briefs NN

The step between the lock and the first draft. The outline is an authoring artifact; this
turns it into a **prompt**.

**Preconditions:** the book is locked (`.penny/locks/book-NN.mystery.lock`). Run from the
series folder.

## Steps

1. **Refuse an unlocked book.**

   ```bash
   test -f ".penny/locks/book-$1.mystery.lock" || {
     echo "build-briefs: book $1 is not locked — the obligations are not settled yet."; exit 1; }
   ```

2. **Weigh the scenes (the taste stage).**

   If the outline declares no `- **Weight:**` on its scenes, dispatch the **`brief-weigher`**
   sub-agent once per chapter (pass `model:` = `plot_model` from `config/run-config.md`,
   defaulting to `drafting_model`). Present its proposal to the showrunner **per chapter**.

   The showrunner accepts, edits, or rejects. **Only the showrunner's accepted weights are
   written into `input/book-NN/outline.md`.** The machine never writes a weight it chose
   itself — the weighting is the chapter's dramatic hierarchy, and that is taste.

3. **Check the prompt.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" check "$1"
   ```

   Findings are reported, not enforced: `prompt-mass-inversion` (a connective scene
   carrying more instruction than the anchor — the outline lying about what matters),
   `unweighted-chapter`, `undeclared-scene-weight`, `multi-anchor-chapter`,
   `hook-grade-distribution`. Present them to the showrunner and resolve them by editing
   the outline, then re-run. `render_brief` refuses outright to compile a chapter with no
   anchor, more than one anchor, or an undeclared scene weight — so `check` before
   `build` is not decoration; it names the chapter `build` would otherwise skip.

4. **Compile.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" build "$1"
   ```

   Writes `input/book-NN/briefs/ch-MM.md`, each stamped with the sha256 of both the
   outline and the whodunit ledger it was built from. Edit either afterwards and every
   brief goes stale; `/draft-chapter` will refuse until you re-run this. `build` names
   and skips any chapter it cannot compile and exits nonzero if any failed — a partial
   write is never mistaken for a clean one.

5. **Report.** Name the per-chapter word budgets and the total, so the showrunner sees the
   book priced before a word of it is drafted.

## Notes

- An outline with **no scene weights is passed through untouched** — no briefs are written,
  and `/draft-chapter` reads the raw outline section exactly as it does today. Book 1 is
  unaffected until you choose to weigh it.
- The weights live in the **outline** (`- **Weight:** anchor|support|connective` inside
  each `### Scene N` block), not in the briefs. The briefs are compiled artifacts; the
  outline is the source of truth. Re-compiling is always safe.
