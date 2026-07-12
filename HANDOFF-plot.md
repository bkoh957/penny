# Handoff — Penny (fiction-series engine) / plot
Saved: 2026-07-12 | Type: build

> **Stream note.** `HANDOFF.md` belongs to a **parallel Hermes session** (LM Studio drafting +
> digest prompt surfaces) and is still live — I did not overwrite it. This file is the
> **plotting-workshop stream**. Two agents are working this repo; see "Watch out for".
>
> One thing that handoff flags is now **resolved**: it lists `scripts/penny_wiring.py`,
> `tests/fixtures/outlines/wired-clean.md`, `tests/test_penny_wiring.py` as untracked files of
> unknown provenance — **they are mine** (plotting workshop, Task 1) and are committed.

## What we're building

The session began as a **review of Penny against its real aim** — "a genre book generation
machine that produces page-turners" — and the review found the gap is structural:

> **Every gate in Penny can only block badness; nothing demands goodness.** `review_gate.py`
> PASSes on zero blockers, and all five inspectors detect *defects* (continuity errors, unfair
> clues, voice drift, AI tics, dormant threads). A chapter that is consistent, fair, on-voice,
> human-sounding **and completely boring passes cleanly.** Boredom is nobody's job.

The user then sharpened it: **genre bestsellers live or die on PLOT**, and since the drafter
sees nothing but the outline plus the packs, **the outline is the only channel through which
plot quality reaches the page.** It is therefore a dual artifact — a good *dramatic* outline AND
a good *prompt* — and Penny guarded neither (`outline_check.py` gates the outline's *shape*; the
mystery lock gates the *puzzle*; nothing gates the *drama*).

**Shipped this session: the plotting workshop** — Parts 1+2 of a 4-part programme.
Spec: `docs/superpowers/specs/2026-07-12-plot-book-workshop-design.md`
Plan: `docs/superpowers/plans/2026-07-12-plot-book-workshop.md` (executed subagent-driven)

## Git state

- **Branch:** `main`. **20 commits ahead of origin — NOT PUSHED** (`8c52791..1f57d60`).
  The user reviews before pushing; that is the open decision.
- **Tests: 484 passing** (371 at session start). Verify: `python3 -m pytest`.
- **Uncommitted, NOT MINE — leave alone:**
  - `config/review-rubrics/ai-prose-taste-flags.md` (+59), `config/self-audit/self-audit-checklist.md` (+26)
    — the **Hermes session** expanded the AI-smell rubric with new flags 5–8 (repeated
    explanation after action; rhetorical contrast machinery `not X but Y`; over-precise
    explanatory dialogue; manufactured background planting). Good work, currently homeless —
    **it wants a commit.**
  - `HANDOFF.md` (modified) — the Hermes stream's handoff. `HERMES-HANDOFF.md`, `sketches/` (untracked).

## What shipped

**`/plot-book NN`** — the recommended front door for a **new** book; a resumable, staged
plotting workshop. Three front doors now: `/plot-book`, `/scaffold-book`, `/plan-mystery`.

- **Save points** in `input/book-NN/plot/`: `material.md` (optional — a pasted brainstorm),
  `premise.md`, `ending.md`, `turning-points.md`. **The files are the state; the conversation is
  never the record.** Staleness via sha256 `built_from_*` fingerprints — hand-edit the ending,
  rerun, and everything built on it is redone. Nothing drifts silently.
- **Stages:** premise → ending → turning-points *(showrunner's taste; rivals proposed, the core
  never chosen for him)* → counterplot *(dispatches the **existing** `mystery-planner` — the
  workshop **absorbs** mystery planning rather than duplicating it)* → chapters → weave
  *(machine, answerable to the checker)* → readback *(blind fan)* → **lock, minted once.**
- **New scripts:** `penny_wiring.py` (THE wired-outline parser), `tension_check.py` (the
  proofreader), `plot_stage.py` (stage status / stamping / the blind reader's copy).
- **New agents:** `plot-proposer`, `chapter-weaver`, `outline-fan`.
- **Genre pack:** `genres/cozy-mystery/beat-sheet.yaml` + `personas/genre-fan.md`, declared via
  optional `genre.yaml` keys `beat_sheet:` / `fan_persona:`. **This is the worked example the
  thriller pack (Phase 4) has been waiting for.**

### The wired outline format (optional per book, all-or-nothing)

Chapters may carry `- **Because:**` (which earlier chapter's turn *forced* this one — the
"therefore/but" test as data), `- **Opens:** / **Closes:** / **Carries:**` (named story
questions, ids `q-<slug>`; *carries* = a deliberate series seed), and `- **Hook:**` leading with
the id of a still-open question.

### `tension_check.py` — eight named checks

`orphan-chapter` · `dropped-question` · `phantom-answer` · `dead-stretch` (**the sagging middle
as arithmetic** — no open question is pulling the reader forward) · `broken-hook` ·
`starved-thread` · `off-mark-beat` · `chapter-coverage`. Thresholds come from the genre beat
sheet, never from constants in the engine. **An un-wired outline is SKIPPED entirely** — book 1
stays valid. Wired into `preflight.py lock-mystery` as a third validator, with per-check
`--waive check-id:"reason"` **recorded in the lock certificate** (the machine never overrules
the author — and never lets an override pass silently).

## Next actions

1. **Review the 20 commits, then push.** Nothing is pushed; the user's call.
2. **THE SHAKEDOWN — plot Pelican's Crook book 2 via `/penny-engine:plot-book 02`.** This is the
   plan's own endpoint and the real next step. The deterministic layer is hammered (484 tests,
   mutation-tested); **the taste stages have never been run.** Only a live run answers: does the
   proposer's rival-generation feel like a workshop or like a form to fill in? Are the
   beat-sheet seed numbers right for a 27-chapter cozy? Does the fan's report tell you anything
   you didn't already know?
3. **Commit the Hermes rubric work** (see Git state) — unrelated to this branch, currently homeless.
4. **Deferred by design (each its own spec cycle):**
   - **Part 3 — the brief renderer.** Outline→drafter-prompt compilation: dramatic intent above
     the event list, reader-state deltas, an emphasis budget (anchor/support/connective — the
     doctrine the user already hand-wrote into book 1's outline), and **negative space** (what
     must NOT be resolved yet — LLMs resolve tension prematurely by default, the single most
     bestseller-hostile instinct they have).
   - **Part 4 — the adversarial predict-the-twist loop.** The reader-sim predicts each turn
     *before* reading it; where it guesses right, the twist is a cliché and that span is
     regenerated against a forbidden list. The blind fan shipped here is its cheap slice.
5. **Two drafter-side findings from the review, not yet acted on** (cheap, high leverage):
   - `agents/drafter.md:61` is a **padding directive** — if under the word-count minimum,
     *"continue writing — extend a scene, deepen interiority, slow a beat."* Dilution on demand;
     the literal opposite of page-turner craft. Length belongs to scene count at outline time.
   - **`ch-01.draft.md` is 3,802 words against an opening range of 1,800–2,400 — 58% over max,
     and nothing caught it.** Word-count-in-range is an *instruction to the line editor* when it
     is the most script-checkable predicate in the pipeline.

## Decisions made this session

- **The reader's copy is TRUNCATED before the reveal chapter** — a deliberate deviation from the
  spec as written, and the most consequential call here. The final review found the reveal
  chapter's own *summary* names the culprit ("The reveal: Mary, the letter, the mercy mistaken
  for murder"), so **no amount of stripping could hide the answer: the blind fan was a sham.**
  Truncation also *is* the real reading experience — a reader guesses **before** the ending. The
  retained span (ch 1..reveal−1) carries the entire sagging-middle risk anyway; a reader who
  reaches the reveal finishes. **Overrule this if you disagree — it is a taste call.**
- **Blindness is enforced BY CONSTRUCTION, never by instruction.** We never hand an agent the
  full outline and ask it not to peek. Reviews found three real leaks (a hand-typed
  `### Track movement` with a lowercase 'm' leaked the `**M:**` row — *which states what the
  culprit does*; non-canonical bullets; a Hook line with no separator). Closed three ways over,
  swept clean against every fixture.
- **The workshop absorbs mystery planning** rather than running beside it — the ending is
  written down **once** and both plans are built from it. The disease this prevents is already
  in the repo's history: book 1's solution prose diverged from its own locked yaml.
- **Taste at the big three, machine below.** Rival premises / endings / turning-point sets go to
  the showrunner; gap-filling and weaving are machine work answerable to the checker. ~6
  decisions per book instead of 27 chapters of structure hand-built in a chat transcript.
- **Generation and validation are the same knowledge pointed in opposite directions.** Beat
  positions, question ledgers, causality: *constraints in the prompt* during construction,
  *predicates in the checker* after it. Penny built the checker-shaped half first.

## User preferences expressed this session

- **PLAIN LANGUAGE — not engineering jargon.** Explicit correction: *"I have a problem with your
  language, it is too technical."* Talk about chapter plans and proofreaders, not schemas and
  deterministic validators. Saved to memory (`plain-language-voice.md`).
- **The showrunner can always override** — but the override must be **recorded**. This shaped the
  waiver design directly.
- Phase-at-a-time on `main`; push at phase end; detailed feedback ending in "DONE".

## Key files right now

- `.superpowers/sdd/progress.md` — **the recovery map.** Every task, every review finding, every
  fix wave, with rationale. **Trust it over memory after a compaction.**
- `docs/superpowers/specs/2026-07-12-plot-book-workshop-design.md` — the spec (updated for the
  truncation decision).
- `commands/plot-book.md` — the runbook.
- `scripts/{penny_wiring,tension_check,plot_stage}.py` — the new deterministic layer.
- `genres/cozy-mystery/beat-sheet.yaml` — the seed numbers the shakedown will tune.

## Watch out for

- **The taste stages are UNTESTED BY CONSTRUCTION.** No unit test can prove a proposal is good.
  The deterministic layer is hammered; the creative layer has never run. **Do not mistake 484
  green for "it works."**
- **Book 1 is un-wired and must stay lockable.** Verified against the *real* live outline:
  `python3 scripts/tension_check.py ~/myBooks/series-pelicanscrook/input/book-01/outline.md`
  → *"no wiring detected — skipped"*, exit 0; certificate byte-identical to pre-change.
  **If a change ever breaks this, stop.**
- **TWO AGENTS ARE WORKING THIS REPO.** A Hermes session edited `config/` while this one worked.
  **Re-read files before editing**, and don't assume `HANDOFF.md` is yours.
- **`~/myBooks/series-pelicanscrook` is the LIVE series, a separate private repo.** The engine
  repo is NOT a series — pipeline commands run from `~/myTools/penny` hard-error by design.
- **Live commands are namespaced:** `/penny-engine:plot-book 02`, not `/plot-book 02`.
  `CLAUDE.md` documents them bare, by convention.
- **The engine ships no run-config, voice pack, or personas** — a freshly scaffolded series is
  not yet runnable. Unchanged by this work, but it surprises people.
