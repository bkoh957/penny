# Handoff — Penny (fiction-series engine) / views
Saved: 2026-07-31 | Type: build

> **Stream note.** `HANDOFF.md` = LM Studio drafting. `HANDOFF-plot.md` = the plotting
> workshop (shipped 2026-07-12). `HANDOFF-briefs.md` = the packet/map redesign (shipped
> 2026-07-18) — its next-actions are **superseded**, don't act on it.
> `HANDOFF-readback.md` = the staged reveal-aware read-back (shipped 2026-07-31); its
> "next actions" for book 01 are **superseded by this file**, and one of its numbers is
> wrong — see *Watch out for*.
> **This stream** shipped the three diagnostic views (2026-07-31).

## What we're building

The showrunner challenged the whole outlining process, not a tool. Going through
`/plot-book` they answered premise → ending → turning-points as best they could, but
could never see how the book was coming together — so their real judgement deferred
itself to `outline.md`, 14,000 words arriving after every decision had compounded into
chapters. Then they spent days repairing it by hand.

The proof was a hole no reviewer caught: **Simon**, the murder victim's husband, knows
the handover appointment was back-posted to put another woman at the scene — and the
outline has him quietly "covering office procedure," the same phrase five times across
sixteen chapters. Every reviewer missed it because no seat at the table asks *would this
person do this*, and the defect isn't in any chapter — it's in the gap between two.

**Shipped, pushed, done:** three read-only views over the outline that already exists —
the story at a glance, one character's line through the whole book, and the genre's
structural-job worksheet — plus `/diagnose-outline`, the `spine-mapper` agent, and a fix
freeing the blind reader's-copy generator from the retired `outline-skeleton.md`.

**Spec:** `docs/superpowers/specs/2026-07-31-layered-outline-workshop-design.md`
**Plan:** `docs/superpowers/plans/2026-07-31-outline-diagnostic-views.md` (6 tasks)
**Execution ledger:** `.superpowers/sdd/2026-07-31-outline-diagnostic-views/progress.md`
— every review finding, every controller ruling, every reproduction. **Trust it over
memory after a compaction.** Deliberately kept, not deleted.

## Git state

- Branch: `main`, **in sync with origin** (`8c4a01d..d6d1b84` pushed 2026-07-31)
- Uncommitted changes: `HANDOFF-readback.md` (untracked, never tracked) and this file
- Last commit: `d6d1b84 fix(views): five final-review findings — traceback hardening, docs drift, readback caveat`
- Tests: **712 passing** (`python3 -m pytest`). Was 647 at session start.

## Next actions

**The views are already generated on book 01** — `~/myBooks/pelicanscrook-series/output/book-01/reports/`.
Nothing needs building before the showrunner reads them.

1. **Read the strand pages.** The first run already found it:

   ```
   simon:       14 lines | chapters 01 03 04 05 07 11
   maggie:      95 lines | chapters 01 … 28  (all of them)
   tara-marion: 55 lines | chapters 01 03 07 10 12 13 15 16 17 18 21-28
   ```

   **Simon leaves the book at chapter 11 of 28 and never returns** — not at the reveal
   (24), not at the resolution (28) — after chapter 05 has him *admitting he changed the
   access records*. George vanishes for seven chapters between 03 and 10; Cal skips 10
   through 17.
2. **Run `/diagnose-outline 01`** to add the spine map — the deterministic worksheet is
   written but `spine-mapper` has not been dispatched yet, so no job-to-chapter mapping
   exists. Expect several Act II jobs to come back empty; those blanks are the sagging
   middle, named, and they are where the stalker goes.
3. **The showrunner's decisions, which nothing can derive:** is Simon the stalker or is
   it someone else (and if someone else, what is Simon's answer for staying silent); why
   does the witness not go to the police — that answer becomes the subplot's engine; and
   which empty Act II jobs to fill.
4. **Work the findings one chapter at a time**, editing `outline.md` in conversation.
   Regenerate the strands after edits and re-read — new material makes new holes. Then
   write the `reveals:` block, delete the drifted skeleton and the stale lock, run the
   read-back, re-mint.
5. **Then, separately:** book 01's derived `story.md` worksheet (spec §8.2.1) — a second
   short plan, deliberately deferred until the strands show what it must carry. And the
   full skeleton retirement (spec §9 step 5).

## Decisions made this session

- **Thicker, not finer.** Each pass lays a complete strand over a fixed spine and the
  strand is read *alone* before braiding, rather than re-rendering the same story at
  higher resolution. Chosen because Simon's hole is invisible at every magnification —
  his two load-bearing moments are sixteen chapters apart and each reads fine alone.
- **Shape decided up front, not judged at the end.** The showrunner's call, and better
  than the alternative I leaned to: cozy is a well-mapped form and this repo already
  ships the map — `macro-structure.md` enumerates **28 numbered structural jobs**. Pass 1
  is answering a form already written down, not invention. Accepted cost: a strand cannot
  move a turn.
- **Beats are the foundation; chapters are a late cut.** Post-lock the engine is
  unchanged and the chapter stays load-bearing. The showrunner explicitly did **not**
  want the engine reframed — only a better outline out of it.
- **`outline.md` stays exactly as it is, and the showrunner stops reading it.** Measured:
  1,769 lines, of which 11 headings repeat in every chapter and the same guardrail
  appears 23 times. That repetition is *required* — `packet_assemble.py` slices one
  chapter out, so each block must stand alone. It is a machine input whose audience was
  never the writer. The fix is derived views, not a smaller file.
- **Book 01 is diagnosed, not re-plotted.** Spec §1.1's ruling stands. The views are
  read-only over the outline already shaped by hand.
- **Book 01's `story.md` will be a worksheet, never a source** — it lives in `output/`,
  the cut only ever reads `input/`, and the derivation is lossy (mapping chapters onto
  jobs is judgement). Enforced by construction, not by memory.

## User preferences expressed this session

- **Ask for a walkthrough when a design is abstract.** They twice stopped a menu to say
  "break it down / give me a concrete example" — and both times the concrete version
  changed the design. Lead with the worked example on their own book, not the taxonomy.
- **Name what is real vs. what is not yet built.** They asked "is that a command, or am I
  changing a variable?" after I described unbuilt tooling as if runnable. Always separate
  *exists today* from *this plan builds it*.
- **"By hand" was heard as "you, alone, in an editor."** They are not asking to do the
  work themselves — they decide, the machine generates and edits. Say which is which.
- Still true from earlier streams: story in the subject of the sentence, never component
  tables; precise numbers over estimates; prose before menus; apply an established ruling
  rather than re-asking it.

## Key files right now

- `scripts/outline_views.py` — the three views + CLI. `iter_chapters`, `glance`,
  `strand`/`render_strand`/`roster`, `parse_jobs`, `spine_worksheet`, `_main`.
- `commands/diagnose-outline.md` — the runbook. Read-only, safe on a locked book.
- `agents/spine-mapper.md` — maps chapters onto jobs; told plainly that an empty job **is
  the finding** and inventing coverage destroys the view's only value.
- `genres/cozy-mystery/review-rubrics/macro-structure.md` — now carries 28
  `<!-- job: id -->` markers; promoted from review rubric to consumed template.
- `~/myBooks/pelicanscrook-series/input/book-01/outline.md` — canonical, 28 chapters,
  reveal at 24. The thing being repaired.

## Watch out for

- **The previous handoff's `reveals:` numbers are wrong.** `HANDOFF-readback.md` says
  `impersonation` at 15 and `marion-is-tara` at 27. Those are *skeleton* numbers. Against
  `outline.md` the same turns are at **13** and **25** (reveal at 24). Nothing validates
  a `reveals:` chapter against what that chapter contains, so writing 15/27 would have
  silently protected the wrong chapters.
- **Do NOT re-run `/plot-book 01` after deleting the skeleton.** `stage_paths()` still
  hard-names `outline-skeleton.md`, so with it gone the tracker reports `chapters`
  missing and `next_stage()` returns `chapters` — `/plot-book` would resume by
  dispatching `chapter-weaver` to regenerate the book's middle, spec §1.1's forbidden
  move, arriving silently. `stamp` now refuses by name instead of tracebacking, and the
  caveat is recorded in the plan's "After this plan" section. `/diagnose-outline` and the
  three views are unaffected. Full fix = spec §9 step 5.
- **Book 01 still has two outlines.** The 30-chapter `outline-skeleton.md` (reveal at 26)
  sits beside the canonical 28-chapter `outline.md` (reveal at 24). `readers_copy` now
  *prefers the skeleton while it exists* — so the read-back still reads the wrong book
  until that file is deleted.
- **A slug-format contract is now imposed on series data.** `^[a-z0-9][a-z0-9-]*$` on
  every `alibi_grid` `suspect:` — it is the path-traversal guard, so one nonconforming
  slug aborts the whole strands run by design. Nothing else in the engine documents this.
- **`agents/outline-reviewer.md:19` and `commands/review-outline.md:26`** still name
  `review-rubrics/macro-structure.md` literally — now the only hardcoded genre filenames
  left in `agents/`+`commands/`. This session shipped the resolver
  (`penny_genre.py macro-structure`) that retires them; fold into the §9 step 5 sweep.
- **Contract-pin tests** (`test_runbook_gives_literal_bash_for_every_stamp_call`,
  `test_outline_fan_contract`, `test_readme_check_count`) trip on any deliberate rewrite
  of an agent brief, runbook, or README. Standing rule: **the approved artifact wins;
  re-pin the test.** Note the refinement from this session — that rule protects
  *previously-approved* artifacts; a test written minutes ago by the same task is not a
  contract, and the module's own convention outranks it.
