---
description: The plotting workshop — build a book's dramatic outline in staged, resumable save points; your taste at premise/ending/turning-points, machine work below, blind fan read-back, then the lock.
argument-hint: <book-number>
---
# /plot-book

The recommended front door for a NEW book (spec: docs/superpowers/specs/
2026-07-12-plot-book-workshop-design.md). Resumable: the planning files ARE the
state; this command never asks you anything a file already answers.

## Steps

1. **Parse args:** `book=$1` (e.g. `02`). Resolve the active series root (hard
   error outside a series). Resolve the genre from `series.yaml` and hard-error
   without it (same rule as /plan-book).

2. **Ask the stage machinery where we are:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" status $book
   ```

   Report the full stage table to the showrunner, then enter the stage named
   `next:`. If `next: none`, say so and stop — the plan is complete.

3. **Write the harness marker for the entered stage** (name per the table below):

   ```bash
   mkdir -p .penny && echo "book=$book stage=PLOT-<STAGE>" > .penny/current-stage
   ```

   | stage | marker | pauses? |
   |---|---|---|
   | premise | PLOT-PREMISE | yes — showrunner chooses |
   | ending | PLOT-ENDING | yes — showrunner chooses |
   | turning-points | PLOT-SPINE | yes — showrunner chooses |
   | counterplot | PLOT-COUNTERPLOT | yes — showrunner approves the yaml |
   | chapters | PLOT-CHAPTERS | no |
   | weave | PLOT-WEAVE | no |
   | readback | PLOT-READBACK | yes — showrunner signs off → lock |

4. **Stages premise / ending / turning-points:** dispatch the `plot-proposer`
   sub-agent with the stage name, `input/book-$book/plot/material.md` if present,
   the genre archetype document (`genres/<genre>/archetype.md`), the beat sheet
   (overlay-resolved `beat-sheet.yaml`), and every earlier save point. Relay its
   options to the showrunner; when they choose, the proposer writes the one save
   point, then stamp it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     input/book-$book/plot/<file>.md --from <each upstream save point that exists>
   ```

   End the run after the stamp — one taste decision per sitting.

5. **Stage counterplot:** dispatch the existing `mystery-planner` with the core
   read from `ending.md` + the spine from `turning-points.md` (do NOT re-ask the
   showrunner for the core — it is on disk). It proposes
   `series/whodunit/book-$book.yaml`; the showrunner edits until right; write the
   sealed solution to `output/book-$book/mystery-solution.md`, then stamp the
   solution file `--from` ending.md and turning-points.md. **No lock here** —
   the lock is stage readback's last act (validate once, then freeze). Do not
   run `lock-mystery` at this stage; it runs exactly once, at the end of step 8.

6. **Stage chapters:** for each gap between consecutive turning points, dispatch
   `chapter-weaver` (fill pass) with both endpoints fixed and the clue schedule
   from the whodunit yaml. When this is a re-plot regenerating chapters that
   already exist, `chapter-weaver` clears any stale `woven: true` from the
   skeleton's frontmatter as part of that write (its contract, not a step here
   — do not re-set `woven: true` yourself) — otherwise the weave stage would
   read as `done` over chapters that were never rewoven. Then stamp the skeleton
   `--from` turning-points.md and the solution file. Continue directly to weave.

7. **Stage weave:** dispatch `chapter-weaver` (weave pass) over the filled
   skeleton. It sets `woven: true` and re-stamps.

8. **Stage readback:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" readers-copy $book
   ```

   Dispatch `outline-fan` on the reader's copy with the genre's `fan_persona`
   (cross-model where reachable; degrade with "independence reduced", never halt).
   Then run the proofreader:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tension_check.py" \
     input/book-$book/outline-skeleton.md \
     --beat-sheet "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_paths.py" resolve config beat-sheet.yaml)" \
     --turning-points input/book-$book/plot/turning-points.md \
     --whodunit series/whodunit/book-$book.yaml
   ```

   `penny_paths.py resolve config <rel>` is the CLI already shipped for
   overlay-resolved config reads — cleaner than reimplementing the overlay
   inline, and it always prints a path even if `beat-sheet.yaml` doesn't exist
   anywhere in the overlay (falling back to the plugin default location). A
   genre with no beat sheet at all is fine: `tension_check.py` simply skips the
   curve/beat checks and runs only the graph checks (causality, open-question
   ledger, hook chain).

   Present the fan's report and the findings side by side. The showrunner either
   revises (edit any file — staleness re-opens the right stages on the next run)
   or signs off. On sign-off, stamp the fan report `--from` the skeleton, then
   mint the lock (the ONE time it is minted this workshop) — with any per-check
   waivers the showrunner dictates, each with a reason:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book \
     [--waive check-id:"reason"]...
   ```

   From here the book proceeds exactly as today: /expand-outline, /review-outline,
   /draft-chapter.
