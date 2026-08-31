---
description: Allocate a book's sensory texture across every chapter at once — the positive half of the cut plan's compress line (spec 2026-08-27 §4.2).
argument-hint: <book-number>
arguments: [book]
---
# /allocate-texture

Run once per book, **after `cut-plan.md` is approved and before `/map-chapter`**.
One whole-book pass decides which chapter spends which image, where texture goes
deliberately quiet, and which images return as motifs — so that no image is spent
twice and no chapter is left asking the drafter to improvise the town.

Same economics as the clue schedule: a few hundred lines, readable in five
minutes, arguable, cheap to redo.

**Read this before running it on a book already in flight.** The allocation edits
`cut-plan.md`, which means the book must be re-cut, which changes `outline.md`.
If the book is already locked, the lock must be re-minted and every packet built
from the old outline is stale. That is known and cheap, but it is a deliberate
act — not a background improvement. Step 6 covers it.

## Steps

1. **Parse args and write the harness state marker:**

   ```bash
   book=$book
   mkdir -p .penny
   echo "book=$book stage=TEXTURE" > .penny/current-stage
   ```

2. **Check the preconditions.** `input/book-$book/cut-plan.md` must exist and be
   the approved plan — the allocation is written against its chapter numbers.
   `config/setting-pack/reservoir.md` should exist; if it does not, the series
   has not authored a `## Reservoir` section in
   `input/series/background-history.md`. Write one and run:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/background_cut.py"
   ```

   Allocating against an absent reservoir is possible but thin — the whole point
   of the layer is that it spends a real inventory rather than a wish.

3. **Dispatch the `texture-allocator` sub-agent** (pass `model:` = `plot_model`
   from `config/run-config.md`, defaulting to `drafting_model` when unset —
   planning work, same routing as the workshop; the agent def carries no
   `model:` frontmatter, so without this override it silently inherits the
   parent). It reads the whole cut plan, the reservoir, the setting and voice
   packs, the genre beat sheet and the sealed solution, and proposes the
   allocation for every chapter at once. **It proposes only and writes nothing.**

4. **Present the proposal to the showrunner.** This is a taste call: which
   chapters run rich, which run lean, which go silent under pressure, which
   images return and where. The showrunner edits it. Save the **approved**
   allocation — and only the approved allocation — to
   `input/book-$book/plot/texture.md`.

5. **Splice it into the cut plan and re-cut:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/texture_apply.py" $book
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/story_cut.py" $book
   ```

   `texture_apply.py` is idempotent — it replaces any block it wrote before, so
   re-allocating is one command. Exit 1 names what it refused and writes
   nothing:
   - `unknown-chapter` — the allocation names a chapter `cut-plan.md` does not
     have. A boundary moved; re-allocate against the current plan.
   - `no-anchor` — a chapter has neither a `**Summary:**` nor a `**Compress:**`
     line to place the block after; repair the cut plan.

   Advisories are printed and block nothing: `unallocated-chapter` (a chapter
   spends nothing this book — legal; texture is a resource, not an obligation)
   and `empty-allocation` (a chapter named with no items).

   `story_cut.py` then rewrites `outline.md` with a `### Texture` section in each
   allocated chapter block. It refuses `outline-modified-since-cut` if the
   outline has been hand-edited since the cut wrote it — that work is yours to
   keep or discard, and the cut will not decide for you.

6. **If the book was already locked, re-mint and re-map.** `cut-plan.md` is one
   of the two files whose edit invalidates the lock:

   ```bash
   rm .penny/locks/book-$book.mystery.lock
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book
   ```

   Every packet built from the previous outline is now stale (`built_from_outline`
   no longer matches). Re-run `/map-chapter $book <MM>` for any chapter already
   mapped; `preflight draft` will refuse a stale packet or map by name if you
   forget.

7. **Advance the marker:**

   ```bash
   echo "book=$book stage=TEXTURED" > .penny/current-stage
   ```

   The book's chapters now carry what they may spend. `/map-chapter` distributes
   each chapter's allocation across its scenes' `Texture:` fields, and the
   drafter renders it.
