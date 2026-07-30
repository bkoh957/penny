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

8. **Stage readback:** a LOOP, not a single pass — read, findings, work them, re-read,
   then lock.

   ```bash
   echo "book=$book stage=PLOT-READBACK" > .penny/current-stage
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" readers-copy $book --staged
   ```

   `--staged` writes one reader's copy per protected reveal declared in the whodunit
   ledger's `reveals:` block — each cumulative from chapter 1 and stopping ONE CHAPTER
   SHORT of its reveal, plus a final whole-book stage. It prints the paths in stage
   order. When the ledger declares no `reveals:` it says so and writes the single-cut
   `outline-readers-copy.md` instead: an unstaged book still reads back exactly as
   before, never blocked.

   The cut matters and is not incidental. A copy that runs past a protected turn lets
   the fan read the turn and then report that the turn landed — which is precisely how
   book 01's midpoint leak passed unnoticed on 2026-07-28.

   **Dispatch `outline-fan` ONCE PER STAGE, each as a fresh sub-agent**, with that
   stage's copy, the genre's `fan_persona`, and the stage number. Never perform the read
   inline in this session: this session holds the solution and every plotting decision,
   and no persona survives that. Prefer a model other than `plot_model`; if none is
   reachable, proceed on `plot_model` — that is NOT a degradation and gets no note. Do
   not pass a fan its own earlier reports.

   If the read cannot be dispatched as a sub-agent at all, **skip it** and carry that to
   the certificate at step 9 with
   `--note-skipped 'fan-read: <why>'`. An inline read is worse than no read: it returns
   a confident report that reassures.

   **Then the suspicion audit.** You (this session) may see the solution — the readers
   have already filed, so you cannot contaminate them. Read the ledger's `reveals:`
   block and every stage report, and write
   `output/book-$book/reports/suspicion-audit.md`: one row per reveal — reveal id, the
   chapter it was meant to land in, where the reader first suspected it and how sure,
   and the gap. Below the table, set each not-yet-landed reveal's
   `reader_should_think_before` list (where the ledger supplies one) beside that stage's
   own "what is this story about right now" sentence.

   Name findings:
   - **`early`** — the reader named the reveal, confidence ≥3, in a stage closing before
     its `reveal_chapter`.
   - **`never`** — not suspected in any stage closing at or after its `reveal_chapter`.
     The fairness end of the same dial: too early is boring, never is a cheat.
   - **`predicted`** — the reader's "next big turn" for stage K is what stage K+1
     contains. The sharpest form of `early`.
   - **`drift`** — a chapter scored ≤3 for interest, or named as a put-down point.
   - **`dead-thread`** — the reader stopped wondering about something the outline still
     spends chapters servicing.

   **Append every finding to the feedback ledger** so it can be worked one at a time.
   **One item = one change to one chapter** — split a finding that implicates six
   chapters into six items. A finding like "the Lisa thread is weak" has failed however
   true it is, because the showrunner cannot sit down and fix it.

   Write a JSON array of
   `{source: "fan-audit", text, recommendation?, chapters?, metrics?}` to a temp file,
   then:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" append $book \
     --points /tmp/fan-audit-points.json
   ```

   Metrics per finding type: `early` → `finding, reveal, meant_to_land,
   first_suspected, confidence, gap_chapters`; `never` → `finding, reveal,
   meant_to_land, first_suspected: null, confidence: 0`; `predicted` → `finding, stage,
   predicted, actual_next, reveal, meant_to_land`; `drift` → `finding, interest,
   put_down_risk`; `dead-thread` → `finding, stage, closed_question,
   still_serviced_in`.

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

   Present the audit, the open ledger items, and the tension findings side by side. The
   showrunner either works the open items (editing `outline.md` and the whodunit ledger,
   marking each `solved`/`rejected` by hand in
   `output/book-$book/reports/outline-feedback.yaml`) and comes back round this stage,
   or signs off. Nothing here blocks: the audit has no exit code and the fan holds no
   gate. The showrunner's sign-off is the decision point, as before.

9. **Mint the lock:**

   On sign-off, stamp the fan report:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     output/book-$book/reports/outline-fan.md \
     --from input/book-$book/outline-skeleton.md
   ```

   Then mint the lock (the ONE time it is minted this workshop) — with any
   per-check waivers the showrunner dictates, each with a reason, and any
   `--note-skipped` recorded above for a fan read that could not be dispatched:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book \
     [--waive check-id:"reason"]... [--note-skipped check-id:"reason"]...
   ```

   From here the book proceeds exactly as today: /expand-outline, /review-outline,
   /draft-chapter.
