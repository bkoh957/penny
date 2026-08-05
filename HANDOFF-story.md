# Handoff — Penny (fiction-series engine) / story
Saved: 2026-08-05 | Type: build

> **Stream note.** The five older streams (`HANDOFF.md` LM Studio, `HANDOFF-plot.md`
> workshop, `HANDOFF-briefs.md` packet/map, `HANDOFF-readback.md`, `HANDOFF-views.md`)
> were deleted this session — all superseded, and the plot stream's deferred designs
> (brief renderer, adversarial predict-the-twist loop) live in
> `docs/superpowers/specs/2026-07-12-plot-book-workshop-design.md`, not in the handoff.
> Recoverable from git if ever needed. **This is the only stream.**

## What we're building

The showrunner plots in `input/book-NN/story.md` — beats in story order, four sigils —
and a deterministic cut turns it into the generated `outline.md`. Book 01 is migrating
onto that layer. Three things happened this session.

**1. Book 01 got its first `## Chapter Direction` and `## Guardrails` blocks** — 8
boundary notes for the `chapter-cutter`, 15 prose guardrails, scoped by `@strand` and
`#job`. Verified to add no findings and to leave beat numbering unchanged.

**2. `/book-status` learned about the story layer.** It was built 2026-08-02, one day
before the source layer, so its top row was `outline` — a build product. A book being
edited upstream looked green and got advised from its own output.

**3. Everything was committed and pushed**, both repos, after 24 beats of the
showrunner's editing had been sitting uncommitted for a day.

**Specs:** `docs/superpowers/specs/2026-08-03-story-source-layer-design.md`,
`docs/superpowers/specs/2026-08-04-chapter-direction-and-guardrails-design.md`,
`docs/superpowers/specs/2026-08-01-book-status-design.md`

## Git state

- **Engine** (`~/myTools/penny`): `main` at `48ce499`, pushed, **clean**.
  `d3cccab` docs pass, `48ce499` the story-layer rows.
- **Series** (`~/myBooks/pelicanscrook-series`): `main` at `decf0c7`, pushed, **clean**.
  `c729cf3` story.md (148 beats + the two blocks), `decf0c7` bible/town-history/Hermes.
- Tests: **929 passing** (`python3 -m pytest`). Was 911 at session start; +18 for the
  new rows.

## Next actions

**Run `python3 ~/myTools/penny/scripts/book_status.py 01` from the series root first.**
Its `next:` line is now trustworthy — it says `fix the findings in
input/book-01/story.md`, which is right.

**Book 01's `story.md` has 16 findings.** Re-run before acting; the showrunner edits
between sessions and this list moves (13 → 15 → 16 over two days):

```bash
cd ~/myBooks/pelicanscrook-series && python3 -c "
import sys; sys.path.insert(0,'/Users/beeko/myTools/penny')
from scripts.story_cut import check_story, _job_ids_and_titles
import yaml
t=open('input/book-01/story.md').read()
d=yaml.safe_load(open('series/whodunit/book-01.yaml'))
clues=[it['id'] for c in ('clue_schedule','red_herrings') for it in (d.get(c) or [])]
jobs,_=_job_ids_and_titles()
r=check_story(t,'',jobs,clues)
for f in r['blocking']:
    if not f.startswith('beats-without-chapter'): print(' *',f)
"
```

**Ignore every `beats-without-chapter` line** — that is the empty cut-plan argument, i.e.
what "chapters don't exist yet" looks like. Noise, not a defect. (The `cut plan` row in
`/book-status` is what owns that finding now.)

As of this save the 16 group into three jobs:

1. **Twelve `unknown-clue`** — invented while editing, no ledger entry yet:
   `c02a-false-maggie-prior-meeting`, `c02b-first-elspeth-threat`,
   `rh-pruitt-blue-cottage`, `rh-cal-old-key`, `c09a-marion-access-system`,
   `c08a-backyard-firing-knowledge`, `c10b-tara-imitates-lisa`,
   `c10c-tara-imitation-pattern`, `c10a-youth-prize-lie`, `rh-elspeth-tara-grief`,
   `c13a-marion-nephew-pressure`, `c13b-dot-glad-photo-tin`. Each needs an entry in
   `series/whodunit/book-01.yaml` under `clue_schedule` or `red_herrings`. **Do not
   author `plant_chapter:` values** — the cut resolves and writes them. Give each a
   `description:`, because that is what the packet renders.
2. **Three `unknown-job`** — `#proof-pressure` (beats 16, 62) and
   `#killer-lookalike-pressure` (beat 61) are not among the cozy genre's 28 structural
   jobs. Either map them onto real jobs from
   `genres/cozy-mystery/review-rubrics/macro-structure.md`, or decide the genre pack
   needs a new job — that is a genre decision, not a story one.
3. **One `unclosed-question`** — seven to close: `q-clear`, `q-lisa-enemies`, `q-love`,
   `q-marion-why`, `q-next`, `q-surf-commission`, `q-tara`. `q-next` is the one a last
   chapter may hook.

**Then the cut.** `chapter-cutter` proposes `input/book-01/cut-plan.md`, showrunner
approves, `python3 scripts/story_cut.py 01` emits a fresh `outline.md`.

**Delete `input/book-01/outline.md` and `outline-skeleton.md` before cutting.**
`story_cut.py` only calls `recut_refusal` inside `if outline_p.is_file()`. The no-stamp
refusal exists to stop the cut overwriting an outline it did not produce — with no
outline present there is nothing to refuse. Both files are committed, so recoverable.

**Close out:** write `reveals:` (**13 and 25**, not 15/27 — those are skeleton numbers),
delete the stale lock, `preflight.py lock-mystery 01`.

## Decisions made this session

- **The `cut` row hands over no runnable command.** Re-cutting rewrites the ledger's
  `plant_chapter:` values (needs the ledger unsealed) and restales every packet. A
  copy-pasteable command would hide both prerequisites behind one word — a status table
  is not a reason to delete a lock. The row names the costs from what is on disk instead.
- **Presence on disk is the switch for the story rows, not a flag.** No `story.md`, no
  rows. Same rule the cut itself uses. Side effect worth knowing: every pre-existing
  `next_action` test passed untouched, because the old fixtures have no story files.
- **Row order is the whole mechanism.** `next_action` already prefers the first
  ran-but-failed row, so putting the source above the build product fixed the `next:`
  line with no change to `next_action` at all.
- **`beats-without-chapter` belongs to the `cut plan` row, not the `story` row.** It
  fires for every beat when no plan exists, which is the normal state of a story being
  written; counting it in the story row would make every live book look broken.
- **A `cut` row with no `built_from_story` is a fail, not an unknown.** It is a known
  fact that the outline is not the story's output (book 01's shape). `unknown` is for
  checks that could not run.
- **`_job_ids_and_titles` gained a `root=` parameter** — `book_status` reports on a book
  without being run from inside it, and resolving the genre from cwd would read some
  other series' pack.
- **Authored guardrails scope with `@strand`/`#job`, never chapter numbers** (carried
  over): chapter numbers don't exist until the cut, so any chapter-shaped scoping is
  invalidated by the next re-cut.

## User preferences expressed this session

- **Answer the question that was asked.** "Doesn't really answer the question" —
  a design explanation that describes the code instead of what the showrunner would see
  is not an answer. Lead with the direct yes/no, then the mechanism.
- **Explain a proposed fix as a before/after of what prints**, not as functions and
  rows. The rendered table is the shared language.
- **Ask for cascade effects and take them seriously** — the "no runnable re-cut command"
  decision came from the showrunner asking what could go wrong, not from the original
  design.
- **Terse replies are decisions** — "ok go ahead", "yes". Not disengagement.
- Still true: story in the subject of the sentence; precise numbers over estimates;
  prose before menus; apply an established ruling rather than re-asking.

## Key files right now

- `~/myBooks/pelicanscrook-series/input/book-01/story.md` — **the live file.** 148 beats,
  12 strands, plus `## Chapter Direction` (8) and `## Guardrails` (15) at the end.
- `~/myBooks/pelicanscrook-series/series/whodunit/book-01.yaml` — needs 12 new clue
  entries. `reveal_chapter: 24`.
- `scripts/book_status.py` — `_story_row`, `_cut_plan_row`, `_cut_row`, `_recut_cost`;
  `book_rows` gates them on `_story_path(...).is_file()`.
- `scripts/story_cut.py` — 16 named findings; `recut_refusal` called under
  `if outline_p.is_file()`; `stamp_outline` writes `built_from_story`.
- `tests/test_book_status.py` — the story-layer block is at the end, 18 tests.

## Watch out for

- **The `story` row is now a permanent red top line while a book is being edited**, and
  `next:` will keep saying "fix your story" until it is clean. That is the same shape as
  the bug it replaced (one sticky row eating the `next:` line). Defensible here because
  findings are finite and genuinely block the cut — but **watch it on book 02** and be
  willing to revisit.
- **`book_status.py _main` now refuses only when there is neither a story nor an
  outline.** It used to refuse on a missing outline, which would have turned the table
  off at the exact moment book 01 deletes its outline to migrate.
- **`diagnostics` still reports 8 strands** where `story.md` has 12 — those views were
  computed from the old outline and nothing recomputes them. Not wrong, just stale, and
  no row says so.
- **Every count denominator (`0/28`) comes from the outline's frontmatter**, so it is
  only as current as the last cut. After the cut it will change.
- **Do NOT run `/plot-book 01` after deleting the skeleton** — `stage_paths()` still
  hard-names `outline-skeleton.md` and the tracker would resume by regenerating the
  book's middle.
- **Delete the stale lock before cutting** — the cut rewrites `plant_chapter:`, which is
  only safe while the ledger is unsealed.
- **A comment as the *first* line under `clue_schedule:`** kills `_item_spans` and
  refuses the whole cut. Pre-existing, loud not silent.
- **`story_cut.py`'s CLI is `story_cut.py <book>`** — no `check` subcommand, and it needs
  `cut-plan.md`. To validate `story.md` alone, use the snippet above.
- **22 of 34 outline-feedback items are still open**, and the feedback row's STALE branch
  returns before it counts them — so the table cannot see the backlog. Known, unfixed;
  it was the second defect identified this session and was left out of scope.
- **The docs describe book 01 as mid-migration.** Once its `outline.md` is deleted and
  cut, re-read README's "Book 01 predates all of this" paragraph and CLAUDE.md's
  re-cutting paragraph — the tense will be wrong, and no test will catch it.
