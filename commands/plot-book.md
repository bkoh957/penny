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
   | cut | PLOT-CUT | no |
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
   once, at step 10.

6. **Stage chapters:** write `input/book-$book/story.md` directly — beats in
   story order between the turning points, one per bullet, tags trailing
   (`@strand`, `#job`, `+question`/`-question`, `!clue-id` — spec
   `2026-08-03-story-source-layer-design.md` §3).

   **Read the craft document before you write a single beat:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_paths.py" resolve-dir story-craft
   ```

   Read every path it prints. That union — the engine's
   `config/story-craft/writing-beats.md` plus anything the genre or series adds
   — is what a beat is. The short version, which does not replace reading it:
   a beat is a change on the page, **one visible change per beat**, and a note
   addressed to the writer ("plant this", "do not reveal that", "keep it
   subtext") is not a beat — it belongs in `## Guardrails`, or in
   `## Chapter Direction` if it is about where chapters fall.

   Draw the clue schedule from `series/whodunit/book-$book.yaml` and tag each
   clue's `!clue-id` onto the beat that plants it.

   Open the file with this header, so an agent that arrives later — in this
   session or in another model entirely — finds the craft document from the
   file itself:

   ```markdown
   # Story — book NN

   Beats in story order. Chapters do not exist here; the cut decides them.
   Four sigils carry meaning — `@strand` `#job` `+q-id`/`-q-id` `!clue-id`.
   Everything else is for your reading.

   What a beat is: config/story-craft/writing-beats.md (read it before editing).
   Check this file with: story_cut.py check NN
   ```

   This folds what used to be two dispatches of the now-retired
   `chapter-weaver` into one: strands and questions are tagged inline as each
   beat is written, so there is no second pass left to bolt wiring onto.
   `chapter-weaver`'s other half — deciding where chapter boundaries fall and
   emitting Track Movement rows — is absorbed by `chapter-cutter`, at the cut
   stage below, not here.

   When this is a re-plot regenerating a story that already exists, clear any
   stale `woven: true` from story.md's frontmatter yourself before rewriting
   the beats — otherwise the weave stage below would read as `done` over a
   story that was never rewoven. Once every beat is tagged, set
   `woven: true` in the frontmatter, then stamp story.md, including the
   whodunit ledger it drew the clue schedule from (a real upstream — editing
   the ledger after this point must make the chapters stage go stale again):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     input/book-$book/story.md \
     --from input/book-$book/plot/turning-points.md output/book-$book/mystery-solution.md \
     series/whodunit/book-$book.yaml
   ```

   Continue directly to weave.

7. **Stage weave:**

   ```bash
   echo "book=$book stage=PLOT-WEAVE" > .penny/current-stage
   ```

   Nothing left to do here — the tags went onto the page while story.md was
   written above, and the `woven: true` frontmatter field set in that same
   step is what marks this stage done. (The weave stage has no `_UPSTREAM` of
   its own — `plot_stage.py` judges it done purely by the `woven` flag, so
   there is no separate `stamp` call here.)

   Continue directly to cut.

8. **Stage cut:**

   ```bash
   echo "book=$book stage=PLOT-CUT" > .penny/current-stage
   ```

   The chapter boundary is a judgment; the expansion into a full outline block
   is not (spec `2026-08-03-story-source-layer-design.md` §5) — so this stage
   follows the packet/map pattern already in the engine: an agent proposes,
   the showrunner approves, and only the approved artifact is consumed.

   1. Dispatch the **`chapter-cutter`** sub-agent (pass `model:` = `plot_model`
      from `config/run-config.md`, defaulting to `drafting_model` when unset)
      with `input/book-$book/story.md`. Context-rich like the other planning
      agents — it reads the sealed solution so a turn lands on the right beat
      — it proposes which beats become which chapter, plus the four authored
      fields (title, summary, compress line, per-chapter track rows). **It
      proposes only and writes nothing.**
   2. Present the proposal. The showrunner edits boundaries, titles,
      summaries, compress lines and track rows. Save the **approved** plan —
      and only the approved plan — to `input/book-$book/cut-plan.md`. A
      generated file that wrote itself into this location would look approved
      without being approved.
   3. Run the cut:

      ```bash
      python3 "${CLAUDE_PLUGIN_ROOT}/scripts/story_cut.py" "$book"
      ```

      Exit 0 wrote `input/book-$book/outline.md`, expanding the approved cut
      plan into packet-format chapter blocks. Exit 1 printed named findings —
      fix `story.md` or `cut-plan.md` and run it again; there are no waivers
      at this level. Exit 2 is a usage or missing-file error.

      **No `stamp` call follows this one.** The cut writes its own stage
      stamps — `built_from_story` and `built_from_book-NN`, exactly what
      `plot_stage.py`'s `cut` stage checks — into the outline's frontmatter,
      alongside `book:`, `total_chapters:`, `built_from_cut:` and
      `cut_output_sha256:`. It stamps them itself because a runbook step can
      be skipped, and a stamp written by hand would claim a cut that never
      ran. `plot_stage.py status $book` should report `stage cut: done`
      immediately; if it says `stale`, the cut did not finish.

   Re-cutting is safe while `outline.md` is exactly what the cut wrote — move
   a boundary in `cut-plan.md`, re-run, look again. Once `outline.md` has been
   hand-edited, the cut refuses `outline-modified-since-cut` rather than
   discarding that work.

9. **Stage readback:** a LOOP, not a single pass — read, findings, work them, re-read,
   then lock. The cut above has already run, so `input/book-$book/outline.md` exists.

   ```bash
   echo "book=$book stage=PLOT-READBACK" > .penny/current-stage
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" readers-copy $book --staged
   # Clear stale fan reports BEFORE dispatching, so what is on disk always
   # matches the stages the ledger currently declares. `plot_stage.py status`
   # counts EVERY outline-fan*.md under this glob: a report left over from a
   # previous shape — a legacy single-file read, or a stage that no longer
   # exists because a reveal was removed — would either deadlock readback
   # (the stamp loop in step 10 only ever writes outline-fan-stage-*.md, never
   # the legacy outline-fan.md) or be silently miscounted as coverage for a
   # stage that isn't being read this pass (final review I2).
   rm -f output/book-$book/reports/outline-fan*.md
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
   the certificate at step 10 with
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
   - **`never`** — in the stage closing immediately before its `reveal_chapter`, the
     reader does not name the reveal at all. The fairness end of the same dial: `early`
     is that stage naming it with confidence ≥3; `never` is that stage not reaching it.
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
   `{source: "fan-audit", text, recommendation?, chapters?, metrics?}` to
   `output/book-$book/reports/.fan-audit-points.json` (book-scoped — a fixed `/tmp` path
   would collide across two concurrently-worked books), then:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" append $book \
     --points output/book-$book/reports/.fan-audit-points.json \
     --source input/book-$book/outline.md
   ```

   `--source` still matters here, even though `outline.md` now exists (the cut
   stage above just wrote it): the fan-audit reviewed the readers'-copy render, not
   a full independent panel pass over the outline. Passing `--source` leaves
   `reviewed_outline_sha256` untouched instead of either stamping it blank or silently
   re-stamping it to current (which would clear a staleness warning no panel review
   earned) — final review I6.

   Metrics per finding type: `early` → `finding, reveal, meant_to_land,
   first_suspected, confidence, gap_chapters`; `never` → `finding, reveal,
   meant_to_land, first_suspected: null, confidence: 0`; `predicted` → `finding, stage,
   predicted, actual_next, reveal, meant_to_land`; `drift` → `finding, interest,
   put_down_risk`; `dead-thread` → `finding, stage, closed_question,
   still_serviced_in`.

   Then run the proofreader — against `outline.md`, not `story.md`: `tension_check.py`
   parses chapter wiring (`Because:`/`Opens:`/`Closes:`/`Carries:`/`Hook:`) out of
   `## Chapter NN` blocks, a shape only the cut's output carries — `story.md`'s flat
   beats have neither chapters nor wiring fields:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tension_check.py" \
     input/book-$book/outline.md \
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
   showrunner either works the open items (editing `story.md` and re-running the
   cut, or hand-editing `outline.md` directly, plus the whodunit
   ledger, marking each `solved`/`rejected` by hand in
   `output/book-$book/reports/outline-feedback.yaml`) and comes back round this stage,
   or signs off. Nothing here blocks: the audit has no exit code and the fan holds no
   gate. The showrunner's sign-off is the decision point, as before.

10. **Mint the lock:**

   On sign-off, stamp every stage's fan report (the fan writes one per protected
   reveal, so this is a loop, not a single file) against `outline.md` — the file
   readback actually reads (the cut ran above; a hand-authored book like book
   01 has no cut but has always had an outline.md):

   ```bash
   for f in output/book-$book/reports/outline-fan-stage-*.md; do
     [ -e "$f" ] || continue
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
       "$f" --from input/book-$book/outline.md
   done
   ```

   The `[ -e "$f" ] || continue` guard matters: with no matching files the glob stays
   literal and would otherwise be passed through as a filename. `plot_stage.py status`
   counts readback done only when EVERY stage report carries a current stamp.

   Then mint the lock (the ONE time it is minted this workshop) — with any
   per-check waivers the showrunner dictates, each with a reason, and any
   `--note-skipped` recorded above for a fan read that could not be dispatched:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book \
     [--waive check-id:"reason"]... [--note-skipped check-id:"reason"]...
   ```

   From here the book proceeds exactly as today: /expand-outline, /review-outline,
   /draft-chapter.
