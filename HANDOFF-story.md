# Handoff — Penny (fiction-series engine) / story
Saved: 2026-08-04 19:03 | Type: build

> **Stream note.** `HANDOFF.md` = LM Studio drafting. `HANDOFF-plot.md` = the plotting
> workshop (2026-07-12). `HANDOFF-briefs.md` = packet/map redesign (2026-07-18) —
> superseded. `HANDOFF-readback.md` = staged reveal read-back (2026-07-31) — superseded.
> `HANDOFF-views.md` = diagnostic views + `/book-status` (2026-08-02); engine follow-ups
> done, book-01 next-actions superseded by this file. **This is the live stream.**

## What we're building

The showrunner plots in `input/book-NN/story.md` — beats in story order, four sigils —
and a deterministic cut turns it into the generated `outline.md`. Two things happened
this session.

**1. Book 01 was brought onto the source layer**, reversing last session's ruling that it
would stay hand-edited. The measurement that settled it: `outline.md` was 1,769 lines of
which **124 were Required Beat lines**; the rest restated them, which is what the review
panel's own OF-22 says. `input/book-01/story.md` was derived from those beats +
`spine-map.md`'s jobs + the ledger's clue ids. **The showrunner has been editing it ever
since and it has grown well past the derivation** — 146 beats now, new characters
(Elspeth Bell, Pruitt, Dot/Glad), a new false lead, Cal's old key.

**2. Chapter direction and authored guardrails shipped** — the feature the showrunner
asked for while reading: a place to record structural notes and prose guardrails as they
occur, scoped by the same sigils the beats use, so re-cutting cannot invalidate them.

**3. `README.md` and `CLAUDE.md` were brought in line** (this evening, uncommitted). The
shipping commits had already updated the 16-finding rosters, so the two remaining gaps were
substantive: README documented the new blocks' *refusals* but never taught the blocks
themselves, and **both docs still claimed book 01 "never goes through `story.md` or the
cut"** — false since decision 1 above. See "Decisions" for the engine fact that replaced it.

**Specs:** `docs/superpowers/specs/2026-08-03-story-source-layer-design.md`,
`docs/superpowers/specs/2026-08-04-chapter-direction-and-guardrails-design.md`
**Plan:** `docs/superpowers/plans/2026-08-04-chapter-direction-and-guardrails.md`
**Execution ledger — every finding, ruling and reproduction; deliberately kept:**
`.superpowers/sdd/2026-08-04-chapter-direction-and-guardrails/progress.md`

## Git state

- **Engine** (`~/myTools/penny`): `main` at `72dd39c`, in sync with origin, but **three
  files are modified and uncommitted**: `CLAUDE.md` and `README.md` (the doc pass above —
  reviewed, tests green, **not yet committed or pushed**) and this handoff. The earlier
  push was `9fd3a5b..72dd39c` — spec, plan, four tasks, one fix wave.
- **Series** (`~/myBooks/pelicanscrook-series`, remote `series-pelicanscrook`): `main` at
  `2481e85`, in sync. **`input/book-01/story.md` is modified and uncommitted** — the
  showrunner's live editing. Nothing else dirty.
- Tests: **911 passing** (`python3 -m pytest`), re-verified after the doc edits — the four
  contract-pin files pass (`test_readme_check_count`, `test_claude_md_check_count`,
  `test_skeleton_retired`, `test_solution_visibility`). Was 898 at the start of the
  feature, 881 at session start.

## Next actions

**First, the cheap one: commit `CLAUDE.md` + `README.md` and push.** They are reviewed and
green; they were left uncommitted only because the showrunner hadn't said so yet. Keep this
handoff out of that commit or in it, either way — but do not sweep `story.md` in from the
series repo, that's a different repository.

**Book 01's `story.md` has 13 real findings right now.** Re-run the checker before acting
— they are mid-edit and this list moves:

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
what "chapters don't exist yet" looks like. Noise, not a defect.

As of this save, the 13 group into three jobs:

1. **Nine `unknown-clue`** — new clues the showrunner invented that have no ledger entry
   yet: `c02a-elspeth-witness-false-maggie`, `c02b-first-elspeth-threat`,
   `rh-pruitt-blue-cottage`, `rh-cal-old-key`, `c09a-marion-access-system`,
   `c10a-youth-prize-lie`, `rh-elspeth-tara-grief`, `c13a-marion-nephew-pressure`,
   `c13b-dot-glad-photo-tin`. Each needs an entry in
   `series/whodunit/book-01.yaml` under `clue_schedule` or `red_herrings`. **Do not
   author `plant_chapter:` values** — the cut resolves and writes them. Give each a
   `description:`, because that is what the packet renders.
2. **Three `unknown-job`** — `#proof-pressure` (beats 16, 59) and
   `#killer-lookalike-pressure` (beat 58) are not among the cozy genre's 28 structural
   jobs. Either map them onto real jobs from
   `genres/cozy-mystery/review-rubrics/macro-structure.md`, or decide the genre pack
   needs a new job — that is a genre decision, not a story one.
3. **One `unclosed-question`** — still seven to close: `q-clear`, `q-lisa-enemies`,
   `q-love`, `q-marion-why`, `q-next`, `q-surf-commission`, `q-tara`. `q-next` is the one
   a last chapter may hook. Unchanged from the derivation; the newer questions the
   showrunner added (`q-elspeth`, `q-stalker`, `q-pruitt`, `q-cal-key`) all close cleanly.

**Then the cut.** `chapter-cutter` proposes `input/book-01/cut-plan.md`, showrunner
approves, `python3 scripts/story_cut.py 01` emits a fresh `outline.md`.

**Delete `input/book-01/outline.md` and `outline-skeleton.md` before cutting.** This is
the key mechanical fact of the session: `story_cut.py` only calls `recut_refusal` inside
`if outline_p.is_file()`. The no-stamp refusal exists to stop the cut overwriting an
outline it did not produce — with no outline present there is nothing to refuse. Both
files are committed at `2481e85`, so the delete is recoverable.

**Close out:** write `reveals:` (**13 and 25**, not 15/27 — those are skeleton numbers),
delete the stale lock, `preflight.py lock-mystery 01`.

## Decisions made this session

- **Book 01 goes through `story.md` after all.** Last session's ruling was protecting the
  derived furniture, which is exactly what the panel was complaining about.
- **Deleting `outline.md` is what makes the cut legal — no engine change needed.** I had
  begun drafting a spec for an "adoption path"; the showrunner's "delete the outline
  files" dissolved it.
- **Direction scopes with the same four sigils the beats use** — because chapter numbers
  do not exist until after the cut, so any chapter-shaped scoping is invalidated by the
  next re-cut. A note about Marion is about *Marion*, and `@tara-marion` already names her.
- **Guardrails attach to a chapter's OWN beats, never the running `seen_strands`
  high-water mark.** Character Knowledge accumulates; guardrails do not. Reusing the mark
  would follow a character's note into chapters she is absent from.
- **Authoring order, not scope ranking** (controller ruling, final review Minor 3). The
  spec had enumerated book-wide → strand → job; the code preserved authoring order. The
  code was right and **the spec was amended** — the author controls the order by writing
  it, and scope is not a claim about importance.
- **`wiring-shaped-directive` applies to both blocks**, though `## Chapter Direction` is
  never emitted and the check is purely defensive there. One shape rule, one place to
  learn it.
- **The migration path is the no-stamp refusal itself, and gets documented as such — there
  must be no adoption flag.** `recut_refusal` is only called inside `if outline_p.is_file()`,
  so deleting the unstamped `outline.md` is what makes a legacy book's first cut legal. Both
  docs now say this, and CLAUDE.md says *why an override must not be added*: the guard
  protects work that is still on disk, so removing it has to be the showrunner's explicit
  act. This is the spec I started drafting last session and the showrunner dissolved,
  written down as three sentences instead.
- **The docs teach the engine fact; book 01 is demoted to an example.** README's
  "Book 02 is the first book with a `story.md`" is gone. Book 01 is now described as what it
  is — a legacy, unstamped outline being migrated by that route — with the 1,769-lines /
  124-beat-lines measurement kept, because it is the argument, not decoration.

## User preferences expressed this session

- **When they restate the goal, stop defending the ruling.** "Don't be stupid. Focus on
  the goal." Go measure what the old decision was protecting; do not quote it back.
- **They spot the structural fix — check it against the code before proposing
  engineering.** "Delete the outline files" was right and cheaper than the spec I was
  drafting.
- **Answer the question that was asked.** "What does this mean, `!c02-…`" wanted that one
  tag explained from their own ledger, not a tour of the sigil system.
- **Terse replies are decisions, not disengagement** — "good", "1", "push".
- Still true: story in the subject of the sentence; precise numbers over estimates; prose
  before menus; apply an established ruling rather than re-asking.

## Key files right now

- `~/myBooks/pelicanscrook-series/input/book-01/story.md` — **the live file.** 146 beats,
  12 strands (`cal dot-glad elspeth faye george lisa maggie pruitt saffron simon
  tara-marion tom`), uncommitted.
- `~/myBooks/pelicanscrook-series/series/whodunit/book-01.yaml` — needs the 9 new clue
  entries. `reveal_chapter: 24`.
- `scripts/penny_story.py` — `_fold` is now the single shared bullet/continuation parser
  behind `parse_story`, `parse_questions` and `parse_directives`.
- `scripts/story_cut.py` — 16 named findings; `recut_refusal` at ~:386, called under
  `if outline_p.is_file()`.
- `agents/chapter-cutter.md` — now reads `## Chapter Direction`; told it is advisory.
- `README.md` — the source-layer walkthrough gained `#### Notes to yourself: ## Chapter
  Direction and ## Guardrails` (format, sigil scoping, who reads which block, authoring
  order, and the book-wide-guardrail packet cost from spec §4.3); the no-stamp and book-01
  passages were rewritten. Uncommitted.
- `CLAUDE.md` — the re-cutting paragraph now carries the migration path and the
  no-adoption-flag rule. Uncommitted.

## Watch out for

- **The showrunner's `story.md` edits are uncommitted.** Commit before anything that
  rewrites it.
- **Per-task reviews all passed and the whole-branch review still found two Importants** —
  both in seams no task owned, the same pattern as last phase. A `## Guardrails` line
  inside frontmatter opened a block nothing closed; and authored prose could forge a
  wiring line (`- **Closes:** q-bogus`) because `penny_wiring` parses the whole chapter
  block, not just the footer. **Review the seams by cutting a real book end-to-end.**
- **Both bugs came from one cause:** `parse_directives` was written as a near-copy of
  `parse_story` and the two drifted. Now one shared `_fold`. Don't re-fork it.
- **`story_cut.py`'s CLI is `story_cut.py <book>`** — no `check` subcommand, and it needs
  `cut-plan.md`. To validate `story.md` alone, call `check_story` with an empty cut-plan
  string, as above.
- **Delete the stale lock before cutting** — the cut rewrites the ledger's
  `plant_chapter:` values, which is only safe while the ledger is unsealed.
- **`book_status.py 01` still prints `next: /review-outline 01`.** Still the one wrong
  line on the table; it appends a third panel pass over an unworked backlog.
- **Do NOT run `/plot-book 01` after deleting the skeleton** — `stage_paths()` still
  hard-names `outline-skeleton.md` and the tracker would resume by regenerating the
  book's middle.
- **A comment as the *first* line under `clue_schedule:`** kills `_item_spans` and refuses
  the whole cut. Pre-existing, loud not silent.
- **Contract-pin tests** (`test_readme_check_count`, `test_chapter_cutter_contract`,
  `test_runbook_gives_literal_bash_for_every_stamp_call`) trip on deliberate prose
  rewrites. Standing rule: the approved artefact wins, re-pin the test — but only for
  *previously approved* artefacts. The doc pass above did **not** need any re-pinning: it
  kept all 16 finding ids and all 9 tension-check ids intact.
- **The docs now describe book 01 as mid-migration, which is a claim about the series repo,
  not the engine.** Once its `outline.md` is deleted and cut, re-read README's
  "Book 01 predates all of this" paragraph and CLAUDE.md's re-cutting paragraph — the
  tense will be wrong, and no test will catch it.
