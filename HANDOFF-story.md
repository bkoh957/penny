# Handoff — Penny (fiction-series engine) / story
Saved: 2026-08-06 | Type: build

> **Stream note.** This is the only stream. Five older ones were deleted 2026-08-05 as
> superseded (recoverable from git); the plot stream's deferred designs live in
> `docs/superpowers/specs/2026-07-12-plot-book-workshop-design.md`, not here.

## What we're building

The showrunner plots in `input/book-NN/story.md` — beats in story order, four sigils —
and a deterministic cut turns it into the generated `outline.md`. Book 01 is migrating
onto that layer.

**This session shipped the missing half of that layer: what a beat *is*.** The engine had
specified `story.md`'s syntax completely and its craft not at all, so an editing agent
aimed at the only stated criteria — four sigils, prose first — and produced correctly-tagged
*architecture notes* ("Plant only the visible contradiction… Do not reveal the witness's
certainty") instead of dramatic beats. Five artefacts now fix that, all on `main` and
pushed:

- **`config/story-craft/writing-beats.md`** — the craft document. A beat is a change on
  the page; **one visible change per beat**; three tells that you've written architecture
  instead (abstraction as subject, non-action verb, addressed-to-the-writer); and a
  **routing rule** that files each misplaced note rather than deleting it — prose notes to
  `## Guardrails`, boundary notes to `## Chapter Direction`, question prose to
  `## Questions`. Read as an overlay **directory**, so a genre pack can add to it without
  copying it.
- **`agents/story-author.md`** — the authoring role. Its reason to exist beyond the craft
  doc is **authority**: `@strand` slugs are the author's to mint (shape-checked only), but
  `!clue-id` is a ledger fact and `#job` is a genre fact, and the agent must name what it
  needs and stop. That missing sentence is exactly how book 01 collected 18 invented ids.
- **`story_cut.py check NN`** — validates a story with no cut plan. Suppresses
  `beats-without-chapter` (with no plan it fires once per beat), and suppresses
  `unknown-clue`/`unknown-job` with a named note when the ledger or genre can't be resolved
  at all, because that is the normal mid-workshop state and a checker that guesses is worse
  than one that admits.
- **`directive-shaped-beat`** — the one advisory, on `check_story`'s existing non-blocking
  `notes` channel. Tests **grammar, not drama**: a beat opening with an imperative
  (*Plant, Keep, Save, Do not, Reveal…*). The other two tells stay human judgment, for the
  same reason there is no solution-blindness script.
- **`penny_paths.py resolve-dir <rel> [glob]`** — prints an overlay directory's union, so a
  runbook or an agent in any model can list the craft docs from the shell.

`/plot-book` step 6 now reads that union before writing a beat, and opens a new `story.md`
with a header that names how to resolve the craft document — the portable half, for when
you're editing in another model.

**Specs:** `docs/superpowers/specs/2026-08-06-dramatic-beat-authoring-design.md` (this
session), `2026-08-03-story-source-layer-design.md`,
`2026-08-04-chapter-direction-and-guardrails-design.md`,
`2026-08-01-book-status-design.md`
**Plan:** `docs/superpowers/plans/2026-08-06-dramatic-beat-authoring.md` — all 7 tasks
complete, whole-branch review clean after one fix wave.

## Git state

- **Engine** (`~/myTools/penny`): `main` at `27f91d4`, pushed, **clean**.
  16 commits this session, `976fea1` (spec) through `27f91d4`.
- **Series** (`~/myBooks/pelicanscrook-series`): `main` at `decf0c7`. **Two files
  uncommitted** — `input/book-01/story.md` and `input/series/town-and-character-history.md`.
  Not touched this session; that is the showrunner's own in-progress editing.
- Tests: **962 passing** (`python3 -m pytest`). Was 929 at session start.

## Next actions

**The command replaces the old snippet.** From the series root:

```bash
cd ~/myBooks/pelicanscrook-series
python3 ~/myTools/penny/scripts/story_cut.py check 01
```

That is now the way to validate a story alone. The ten-line Python snippet this file used
to carry is gone — delete it from muscle memory.

**Book 01 as of this save: 19 blocking findings + 2 advisories.** Re-run before acting;
the showrunner edits between sessions and this list moves.

The migration order is **spec `2026-08-06` §8, and the order is load-bearing**:

1. **Split and file** — `story.md`'s compound bullets become one-change beats, and the
   directive-shaped ones move into `## Guardrails` (or `## Chapter Direction` if they are
   about where chapters fall). The two advisories name where to start: beats 6 and 7 both
   open with "Plant". This is the `story-author` agent's first real job.
2. **Resolve the 19 findings** — 14 `unknown-clue` need ledger entries in
   `series/whodunit/book-01.yaml` with a `description:` and **no `plant_chapter:`** (the cut
   resolves that); 4 `unknown-job` are `#proof-pressure` (beats 16, 63) and
   `#killer-lookalike-pressure` (beats 61, 62), which must map onto declared cozy jobs from
   `genres/cozy-mystery/review-rubrics/macro-structure.md` or be escalated as a genre
   decision; the `unclosed-question` lists seven where at most one may survive — `q-next` is
   the one a last chapter may hook.
3. **Then** delete `input/book-01/outline.md`, `outline-skeleton.md`, and the stale mystery
   lock. Both outline files are committed and recoverable; the lock must go because the cut
   rewrites `plant_chapter:`, which is only safe while the ledger is unsealed.
4. **Then** cut — `chapter-cutter` proposes, showrunner approves `cut-plan.md`,
   `python3 scripts/story_cut.py 01`.
5. `reveals:` **13 and 25** (not 15/27 — those are skeleton numbers), then
   `preflight.py lock-mystery 01`.

**Why 1–2 must precede 4:** splitting changes the beat count, which changes every chapter's
obligation load, which is exactly what the cut and `obligations.max_per_chapter` are
deciding on. Cut first and you cut twice. Expect 148 beats to become 200+.

## Decisions made this session

- **Craft and authority are two documents, because they answer to different things.**
  Craft is taste; authority is the engine's data model. No amount of craft guidance
  produces "you don't own these ids", which is what the 18 findings needed.
- **The advisory rides the existing `notes` channel, not a new `advisory` key.**
  `check_story` already had a non-blocking channel carrying exactly this kind of
  observation. A second one with identical semantics is the duplication this engine keeps
  refusing. Consequence, accepted: a cut also prints advisories on its way through.
- **Only one of the three tells ships as code.** "Surfaces" and "reads as" appear in
  perfectly good beats; a checker for them would fire on innocent lines. Grammar is
  checkable, drama is not.
- **`config/story-craft/` is a directory read, never `config_path`.** A single-file read
  takes the first hit, so a genre pack wanting to add two lines would have to copy the whole
  engine document — the shadowing bug, in prose form.
- **The craft document's examples use invented names** (Odette, Renna, Dez, Priya, The
  Tannery). The first draft used the cozy series' own cast, which couples a shipped engine
  default to one series' data. Placeholders were rejected: a craft doc teaching what a beat
  is only works with concrete before/after prose.
- **`check` admits when it cannot run.** Suppressing `unknown-clue` with a named note when
  there is no ledger follows `book_status.py`'s precedent — the mid-workshop state is a
  story drafted before the counterplot stage writes the ledger, and blaming the author's
  story for that is a wall of false findings.
- Carried over: **authored guardrails scope with `@strand`/`#job`, never chapter numbers**,
  because chapter numbers don't exist until the cut.

## User preferences expressed this session

- **Terse replies are decisions** — "ok", "beat", "1", "yes". Not disengagement.
- **The showrunner reverses an earlier answer when they see further** — mid-brainstorm,
  "engine only" became "engine + named migration". Take the update, don't relitigate.
- Still true: answer the question that was asked, lead with the direct answer then the
  mechanism; story in the subject of the sentence; explain a fix as a before/after of what
  the showrunner would *see*; precise numbers over estimates; prose before menus; apply an
  established ruling rather than re-asking.

## Key files right now

- `~/myBooks/pelicanscrook-series/input/book-01/story.md` — **the live file**, uncommitted.
  148 beats, 12 strands, plus `## Chapter Direction` (9) and `## Guardrails` (21).
- `~/myBooks/pelicanscrook-series/series/whodunit/book-01.yaml` — needs 14 new clue
  entries. `reveal_chapter: 24`.
- `config/story-craft/writing-beats.md` — the craft document; read it before editing beats.
- `agents/story-author.md` — the authority table.
- `scripts/story_cut.py` — `_DIRECTIVE_OPENERS`, `directive_advisories()`, `_check()`;
  sixteen blocking findings, unchanged.

## Watch out for

- **The `story` row in `/book-status` stays a red top line while a book is being edited**,
  and `next:` will keep saying "fix your story" until it is clean. Defensible while findings
  are finite and genuinely block the cut — but watch it on book 02.
- **Do NOT run `/plot-book 01` after deleting the skeleton** — `stage_paths()` still
  hard-names `outline-skeleton.md` and the tracker would resume by regenerating the book's
  middle.
- **A comment as the *first* line under `clue_schedule:`** kills `_item_spans` and refuses
  the whole cut. Pre-existing, loud not silent.
- **`diagnostics` still reports 8 strands** where `story.md` has 12 — computed from the old
  outline, and nothing recomputes them. Stale, not wrong, and no row says so.
- **Every count denominator (`0/28`) comes from the outline's frontmatter**, so it is only
  as current as the last cut.
- **22 of 34 outline-feedback items are still open**, and the feedback row's STALE branch
  returns before counting them, so the table cannot see the backlog. Known, unfixed.
- **Once book 01's `outline.md` is deleted and cut**, re-read README's "Book 01 predates all
  of this" paragraph and CLAUDE.md's re-cutting paragraph — the tense will be wrong and no
  test will catch it.
- **Deferred minors from this session's review** (all judged safe to ride): `_declared_genre()`
  reads real `Path.cwd()` rather than the passed root; the craft doc's tell-3 list names
  phrases like *"rather than"* that the advisory does not actually fire on; `_OPENER_RE`
  misses `**Plant**`; the `beats-without-chapter` suppression now exists in both
  `story_cut.py` and `book_status.py`.
