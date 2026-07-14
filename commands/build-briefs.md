---
description: Weigh a book's scenes (before the lock) and compile the locked outline into one prompt-shaped brief per chapter — the emphasis hierarchy, the word budgets, the obligations checklist, the commissioned first and last lines.
argument-hint: <book-number>
---
# /build-briefs NN

The step between the outline and the first draft. The outline is an authoring artifact;
this turns it into a **prompt**.

**Two halves, two preconditions — do not conflate them:**

| Half | Needs | When |
|---|---|---|
| **Weigh + check** (steps 3–4) | the outline + `config/length-profile.md` | **before the lock**, so `lock-mystery`'s `overloaded-chapter` check can see the weights |
| **Compile** (step 5) | the **locked** whodunit ledger (the obligations come from it) | after the lock |

Weighing is an **outline act**. Weights added to an *already sealed* outline are weights the
lock certificate does not cover — so if the book is already locked when you weigh it, the
lock must be re-minted (step 4b). Run from the series folder.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`). Note whether the book is locked:

   ```bash
   test -f ".penny/locks/book-$book.mystery.lock" && locked=yes || locked=no
   ```

2. **Refuse a book with no outline.** The weights live in `input/book-$book/outline.md` —
   the *expanded* outline, the one with `### Scene N` blocks. If it does not exist yet, run
   `/expand-outline $book` first; there is nothing to weigh in a chapter with no scenes.

3. **Weigh the scenes (the taste stage).**

   If the outline declares no `- **Weight:**` on its scenes, dispatch the **`brief-weigher`**
   sub-agent once per chapter (pass `model:` = `plot_model` from `config/run-config.md`,
   defaulting to `drafting_model`). Present its proposal to the showrunner **per chapter**.

   The showrunner accepts, edits, or rejects. **Only the showrunner's accepted weights are
   written into `input/book-NN/outline.md`.** The machine never writes a weight it chose
   itself — the weighting is the chapter's dramatic hierarchy, and that is taste.

4. **Check the prompt.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" check "$book"
   ```

   Findings are reported, not enforced: `prompt-mass-inversion` (a non-anchor scene
   carrying more instruction than the anchor — the outline lying about what matters),
   `unweighted-chapter`, `undeclared-scene-weight`, `multi-anchor-chapter`,
   `hook-grade-distribution`. Present them to the showrunner and resolve them by editing
   the outline, then re-run. `render_brief` refuses outright to compile a chapter with no
   anchor, more than one anchor, or an undeclared scene weight — so `check` before
   `build` is not decoration; it names the chapter `build` would otherwise refuse. (A
   **compact-format** chapter — no `### Scene` blocks at all — is not one of those: it has
   nothing to weigh, `build` skips it by name, and the drafter receives the raw outline
   section for it, exactly as for an unweighted book. Neither half calls that a failure.)

   **Present the findings to the showrunner and stop here.** Do not proceed while `check`
   names a chapter `build` would refuse. Resume once the outline is edited (or the
   showrunner accepts the findings as-is).

4b. **The lock must cover the weights.**

   - **`locked=no`** — this is the good order. Tell the showrunner to lock now
     (`/plot-book $book` finishes there, or `preflight lock-mystery $book` directly): the
     lock's ninth tension check, `overloaded-chapter`, reads exactly these weights and
     prices every chapter against its word band. Then come back for step 5.
   - **`locked=yes`** — the weights were added to a **sealed** outline, and the certificate
     validates a plot that did not have them. Do not pretend otherwise. Re-mint it — the
     documented re-planning flow, delete then re-run:

     ```bash
     rm ".penny/locks/book-$book.mystery.lock"
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery "$book" \
       [--waive overloaded-chapter:"reason"]
     ```

     If `overloaded-chapter` fires, the chapter is doing more than its length can hold: cut
     stops, or waive it with a reason that lands in the certificate.

5. **Compile** (the book must now be locked).

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" build "$book"
   ```

   Writes `input/book-NN/briefs/ch-MM.md`, each stamped with the sha256 of both the
   outline and the whodunit ledger it was built from. Edit either afterwards and every
   brief goes stale; `/draft-chapter` will refuse until you re-run this. `build` names
   and skips any chapter it cannot compile and exits nonzero if any failed — a partial
   write is never mistaken for a clean one. A compact-format chapter is *skipped*, not
   failed, and does not make the run nonzero.

6. **Report.** Name the per-chapter word budgets and the total, so the showrunner sees the
   book priced before a word of it is drafted.

## Notes

- An outline with **no scene weights is passed through untouched** — no briefs are written,
  and `/draft-chapter` reads the raw outline section exactly as it does today. Book 1 is
  unaffected until you choose to weigh it.
- The weights live in the **outline** (`- **Weight:** anchor|support|connective` inside
  each `### Scene N` block), not in the briefs. The briefs are compiled artifacts; the
  outline is the source of truth. Re-compiling is always safe.
- The per-scene word budgets come from `config/length-profile.md` (series-authored; the
  engine ships none). If it predates the `band_*` / `weight_*` / `min_<class>_words` schema
  (see README, "The length profile"), `build` fails **by name** and says which keys are
  missing — and the lock still works, recording `skipped: overloaded-chapter` on the
  certificate rather than claiming a check it could not run.
