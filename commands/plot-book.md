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
   sub-agent (pass `model:` = `plot_model` from `config/run-config.md`, defaulting to
   `drafting_model` when unset — the agent def has no `model` frontmatter, so without
   an override it inherits the parent) with the stage name,
   `input/book-$book/plot/material.md` if present, the genre archetype document
   (`genres/<genre>/archetype.md`), the beat sheet (resolved via
   `penny_genre.py beat-sheet`), and every earlier save point. Relay its
   options to the showrunner; when they choose, the proposer writes the one save
   point, then stamp it. The general rule, every stage, every run: `--from` gets
   EXACTLY the upstream save-point files that currently exist (per `_UPSTREAM` in
   `scripts/plot_stage.py`) — never invent an entry, and if none exist, **skip
   the stamp command entirely** rather than calling `stamp` with an empty
   `--from` (it is `nargs="+", required=True` — an empty list is a hard
   argparse error, not a no-op).

   **Premise** is the one stage where this actually happens: its only upstream,
   `material.md`, is the novelist's OPTIONAL pasted brainstorm. A brand-new book
   with no pre-authored material has zero upstream files. Guard the stamp:

   ```bash
   if [ -f input/book-$book/plot/material.md ]; then
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
       input/book-$book/plot/premise.md --from input/book-$book/plot/material.md
   fi
   # else: no material.md — do NOT run `stamp` at all. A blank start is
   # legitimate; plot_stage.py's stage_status() special-cases absent material
   # and will still report stage "premise" as done, with zero stamps recorded.
   ```

   **Ending**'s only upstream, `premise.md`, always exists by the time this
   stage runs (premise stamps unconditionally above), so stamp unconditionally:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     input/book-$book/plot/ending.md --from input/book-$book/plot/premise.md
   ```

   **Turning-points**'s two upstreams likewise always exist by this point:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     input/book-$book/plot/turning-points.md \
     --from input/book-$book/plot/premise.md input/book-$book/plot/ending.md
   ```

   End the run after the stamp — one taste decision per sitting.

5. **Stage counterplot:** dispatch the existing `mystery-planner` with the core
   read from `ending.md` + the spine from `turning-points.md` (do NOT re-ask the
   showrunner for the core — it is on disk). It proposes
   `series/whodunit/book-$book.yaml`; the showrunner edits until right; write the
   sealed solution to `output/book-$book/mystery-solution.md`, then stamp it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     output/book-$book/mystery-solution.md \
     --from input/book-$book/plot/ending.md input/book-$book/plot/turning-points.md
   ```

   **No lock here** — the lock is stage readback's last act (validate once,
   then freeze). Do not run `lock-mystery` at this stage; it runs exactly
   once, at the end of step 8.

6. **Stage chapters:** for each gap between consecutive turning points, dispatch
   `chapter-weaver` (fill pass; pass `model:` = `plot_model` from
   `config/run-config.md`, defaulting to `drafting_model` when unset) with both
   endpoints fixed and the clue schedule from the whodunit yaml. When this is a
   re-plot regenerating chapters that already exist, `chapter-weaver` clears any
   stale `woven: true` from the skeleton's frontmatter as part of that write (its
   contract, not a step here — do not re-set `woven: true` yourself) — otherwise
   the weave stage would read as `done` over chapters that were never rewoven.
   Then stamp the skeleton, including the whodunit ledger it drew the clue
   schedule from (a real upstream — editing the ledger after this point must make
   the chapters stage go stale again):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     input/book-$book/outline-skeleton.md \
     --from input/book-$book/plot/turning-points.md output/book-$book/mystery-solution.md \
     series/whodunit/book-$book.yaml
   ```

   Continue directly to weave.

7. **Stage weave:**

   ```bash
   echo "book=$book stage=PLOT-WEAVE" > .penny/current-stage
   ```

   Dispatch `chapter-weaver` (weave pass; pass `model:` = `plot_model` from
   `config/run-config.md`, defaulting to `drafting_model` when unset) over the
   filled skeleton. It sets `woven: true` and re-stamps. (The weave stage has no
   `_UPSTREAM` of its own — `plot_stage.py` judges it done purely by the `woven`
   flag, so there is no separate `stamp` call here.)

8. **Stage readback:**

   ```bash
   echo "book=$book stage=PLOT-READBACK" > .penny/current-stage
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" readers-copy $book
   ```

   The reader's copy is not just stripped of solution/wiring — it is **truncated**:
   it contains only chapters `1..reveal_chapter−1` (`reveal_chapter` read from
   `series/whodunit/book-$book.yaml`). This is deliberate, not incidental: the reveal
   chapter's own summary prose names the culprit, so a merely-stripped copy that still
   included it would leave the "blind" fan reading a sham. A real reader guesses the
   culprit before the reveal, never after reading it — the truncation is what makes
   the read genuinely blind.

   Dispatch `outline-fan` on the reader's copy with the genre's `fan_persona`. Prefer
   a model other than `plot_model` (resolved below) — this is the workshop's
   independence claim: the fan should not share a model with the agents that built the
   plan. If no other reachable model exists, degrade to `plot_model` itself and print
   "independence reduced: no non-plot_model model reachable for the fan read" rather
   than halting (same convention as `/review-outline`'s panel degradation).

   Then run the proofreader:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tension_check.py" \
     input/book-$book/outline-skeleton.md \
     --beat-sheet "$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" beat-sheet)" \
     --turning-points input/book-$book/plot/turning-points.md \
     --whodunit series/whodunit/book-$book.yaml
   ```

   `penny_genre.py beat-sheet` resolves THROUGH the active genre's `genre.yaml`
   `beat_sheet:` key (overlay-resolved, so a series can still override its genre's
   numbers) — never a hardcoded filename, so a genre pack naming its file something
   other than `beat-sheet.yaml` still gets its curve/beat checks run. It prints an
   empty string when the genre declares no `beat_sheet:` key at all; `tension_check.py`
   then simply skips the curve/beat checks and runs only the graph checks (causality,
   open-question ledger, hook chain, chapter coverage).

   Present the fan's report and the findings side by side. The showrunner either
   revises (edit any file — staleness re-opens the right stages on the next run)
   or signs off. On sign-off, stamp the fan report:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     output/book-$book/reports/outline-fan.md \
     --from input/book-$book/outline-skeleton.md
   ```

   Then mint the lock (the ONE time it is minted this workshop) — with any
   per-check waivers the showrunner dictates, each with a reason:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book \
     [--waive check-id:"reason"]...
   ```

   From here the book proceeds exactly as today: /expand-outline, /review-outline,
   /draft-chapter.
