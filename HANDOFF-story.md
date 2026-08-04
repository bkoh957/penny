# Handoff — Penny (fiction-series engine) / story
Saved: 2026-08-04 | Type: build

> **Stream note.** `HANDOFF.md` = LM Studio drafting. `HANDOFF-plot.md` = the plotting
> workshop (shipped 2026-07-12). `HANDOFF-briefs.md` = packet/map redesign (2026-07-18) —
> superseded. `HANDOFF-readback.md` = staged reveal read-back (2026-07-31) — superseded.
> `HANDOFF-views.md` = diagnostic views + `/book-status` (2026-08-02); its engine
> follow-ups are done or obsolete and **its book-01 next-actions are now superseded by
> this file**. **This is the live stream.**

## What we're building

The previous session shipped the `story.md` source layer and ruled that **book 01 would
not go through it** — deriving `story.md` backwards from a hand-repaired `outline.md` is
lossy, so book 01 would be repaired by hand instead.

**That ruling was overturned this session, by the showrunner, and they were right.** The
whole phase existed because they said that if they were still stopped editing the outline
file, the changes were pointless — and the ruling sent them back to editing the outline
file. Twenty-two open feedback items, all to be worked by hand across 1,769 lines.

**What changed the call was a measurement.** Book 01's `outline.md` is 1,769 lines, of
which **124 are Required Beat lines**. That is the whole story; the rest restates it.
Chapter 15 is typical — 55 lines whose entire content is three sentences, each appearing
in three sections. That is OF-22, one of the open feedback items, describing the file the
showrunner was being told to hand-edit. So the "lossy derivation" objection was protecting
the furniture, not the book.

**Shipped this session:** `input/book-01/story.md` — 185 lines, 124 beats in story order,
31 questions, 23 ledger clues placed, 9 strands, 26 of the genre's 28 structural jobs.
Derived from `outline.md`'s beats + `spine-map.md`'s jobs + the whodunit ledger's clue ids
+ the wiring footers' question ids. Committed and pushed before the showrunner edits it.

**Spec:** `docs/superpowers/specs/2026-08-03-story-source-layer-design.md`
**Execution ledger from the build:** `.superpowers/sdd/2026-08-03-story-source-layer/progress.md`

## Git state

- **Engine** (`~/myTools/penny`): `main` at `9fd3a5b`, **in sync with origin**. The 30-commit
  backlog from last session plus the views-handoff refresh were pushed this session.
- **Series** (`~/myBooks/pelicanscrook-series`, remote `series-pelicanscrook`): `main` at
  `2481e85`, **in sync**, working tree **clean**. That commit snapshots `story.md` plus all
  the work that had been sitting uncommitted — diagnostic reports, feedback ledger, voice
  pack, series bible, canon-core, plot turning-points.
- Tests: **881 passing** at last run (previous session). **Not re-run this session** — no
  engine code was changed.

## Next actions

**The showrunner is editing `input/book-01/story.md` right now.** Everything below waits on
that.

1. **Re-run the checker when they are done** and show what is still open:
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
   for k,v in r.items():
       if v: print(k, len(v)); [print('  *',x) for x in v]
   "
   ```
   **Ignore the 124 `beats-without-chapter` findings** — that is the empty cut-plan
   argument, i.e. what "chapters don't exist yet" looks like. It is noise, not a defect.
2. **Close seven of the eight unclosed questions.** The one real finding on the derived
   file is `unclosed-question`, naming `q-clear`, `q-lisa-enemies`, `q-love`,
   `q-marion-gap`, `q-marion-why`, `q-next`, `q-surf-commission`, `q-tara`. Exactly OF-17,
   reproduced independently by the checker. `q-next` is the one a last chapter may hook.
3. **The two jobs nothing answers** — `act-i-commitment` and `persuasive-first-theory` —
   are OF-31 (commitment never dramatized) and OF-15 (Maggie is never wrong). These need
   *new beats*, not edits. OF-19 supplies the material: Cal, George and Faye are named as
   suspects in the Solution block and none of them ever conceals anything.
4. **Then the cut:** `chapter-cutter` proposes `input/book-01/cut-plan.md`, showrunner
   approves, `python3 scripts/story_cut.py 01` emits a fresh `outline.md`.
5. **Delete `input/book-01/outline.md` and `outline-skeleton.md` before cutting** (see the
   guard note below). Both are committed at `2481e85`, so the delete is recoverable.
6. **Close out:** write `reveals:` (**13 and 25**, not 15/27 — those are skeleton numbers),
   delete the stale lock, `preflight.py lock-mystery 01`.

## Decisions made this session

- **Book 01 goes through `story.md` after all.** The overturned ruling. Deriving backwards
  is lossy only about derived sections, and those are exactly what the review panel is
  complaining about.
- **Deleting `outline.md` is what makes the cut legal — no engine change needed.**
  `story_cut.py` only calls `recut_refusal` inside `if outline_p.is_file()`. The no-stamp
  refusal exists to stop the cut overwriting an outline it did not produce; with no outline
  present there is nothing to refuse and it writes a fresh one. I had begun proposing a
  spec to add an adoption path — unnecessary. The showrunner's "delete the outline files"
  was the whole fix.
- **`story.md` is upstream; `outline.md` is derived.** Confirmed against the shipped design
  when the showrunner asked directly. Plot in `story.md`, re-cut, never hand-edit the
  outline.
- **Several feedback items stop being edits and become impossible.** `story_cut.py` refuses
  `unclosed-question`/`orphan-question` by name (OF-17, the `q-clear` drop); there is
  nowhere to type a sentence three times (OF-22); the cut resolves clue chapter numbers
  itself (OF-26); the wiring footer is derived (OF-23's broken `Because:`). The remaining
  22-item backlog is really a handful of story decisions.
- **The `!clue-id` tag exists so chapter numbers are never authored.** The cut resolves
  which chapter a beat landed in and writes `plant_chapter:` back into the ledger,
  surgically. `fairplay_check` and `packet_assemble` both read that key.

## User preferences expressed this session

- **When they restate the goal, stop defending the ruling.** "Don't be stupid. Focus on the
  goal." I had quoted last session's own ruling to block precisely the thing the phase was
  built to deliver. A prior ruling is not an argument against the person who made it.
- **They spot the structural fix; take it seriously immediately.** "Delete the outline
  files" dissolved a problem I was about to write a spec for. This is the third time across
  streams — it is now a pattern, not luck.
- **Answer the question that was asked.** "What does this mean, `!c02-...`" wanted the
  meaning of one tag on their own book, shown from their own ledger — not a tour of the
  sigil system.
- Still true: story in the subject of the sentence; precise numbers over estimates; prose
  before menus; terse replies are decisions, not disengagement; apply an established ruling
  rather than re-asking.

## Key files right now

- `~/myBooks/pelicanscrook-series/input/book-01/story.md` — **the file being edited.** The
  thing this whole stream exists for.
- `~/myBooks/pelicanscrook-series/series/whodunit/book-01.yaml` — 23 clues, `reveal_chapter: 24`.
  The cut rewrites its `plant_chapter:` values.
- `~/myBooks/pelicanscrook-series/output/book-01/reports/outline-feedback.yaml` — 22 open,
  12 rejected. Hand-edit `state:` as items are worked.
- `scripts/story_cut.py` — checker, emitter, stamps, surgical ledger rewriter. `recut_refusal`
  at :386, called at :625 under `if outline_p.is_file()`.
- `scripts/penny_story.py` — `parse_story`, `parse_questions`, `parse_cut_plan`.

## Watch out for

- **`story_cut.py`'s CLI is `story_cut.py <book>`** — there is no `check` subcommand, and it
  requires `cut-plan.md` to exist. To validate `story.md` alone, call `check_story` directly
  with an empty cut-plan string, as in Next Actions #1.
- **The derivation is mine, not the showrunner's.** I placed the `#job` tags and decided
  which beat opens and closes which question. Those are judgement calls and the showrunner
  is editing them. Do not treat the tags as authored fact.
- **One thing the derivation genuinely dropped:** per-chapter authored notes such as *"Do
  not flatten Marion into a cackling villain; her usefulness is her camouflage."*
  `story.md` has no slot for them — Guardrails are emitted as one book-wide string plus the
  reveal-chapter line. Offered to fold that one into the Marion beat text; not yet done.
- **Delete the stale lock before cutting.** The cut rewrites the whodunit ledger, which is
  only safe while the ledger is unsealed. `preflight lock-mystery` runs *after* the cut.
- **`book_status.py 01` still prints `next: /review-outline 01`.** Still the one wrong line
  on the table — it appends a third panel pass over an unworked backlog. Do not run it.
- **Do NOT run `/plot-book 01` after deleting the skeleton.** `stage_paths()` still
  hard-names `outline-skeleton.md`; the tracker would report `chapters` missing and resume
  by regenerating the book's middle. `stamp` refuses by name rather than tracebacking.
- **The spec's §8 finding-id list is stale** — it names 8, the module ships 13.
  `CLAUDE.md`/`README.md` document the real set. The spec describes the design; the docs
  describe the code.
- **A comment as the *first* line under `clue_schedule:`** kills `_item_spans` and refuses
  the whole cut. Pre-existing, loud not silent, parked in the ledger.
- **Contract-pin tests** (`test_runbook_gives_literal_bash_for_every_stamp_call`,
  `test_readme_check_count`) trip on deliberate prose rewrites. Standing rule: the approved
  artefact wins, re-pin the test — but only for *previously approved* artefacts.
