# Handoff — Penny (fiction-series engine) / briefs → packet/map
Saved: 2026-07-18 | Type: build

> **Stream note.** `HANDOFF.md` = the Hermes / LM Studio drafting stream; `HANDOFF-plot.md`
> = the plotting workshop (shipped). This stream was the chapter-brief compiler — which is
> now **deleted and superseded**. This session replaced it wholesale with the packet/map
> pipeline. If you are reading this fresh: the brief compiler, `brief-weigher`,
> `/build-briefs`, scene weights, and the weigh-before-lock dance NO LONGER EXIST.

## What we built (this session, 2026-07-18)

The showrunner ran the brief pipeline live and found the drift: the outline-expander wrote
~6 chapter-sized scenes per chapter (~160 dramatised units vs a 65k-word budget), and the
brief compiler was a compressor bolted downstream of that inflator. Redesign (brainstormed
with the showrunner, formats are THEIR authored examples): chapters become short 1–2-idea
units; scenes survive only inside a per-chapter **prose map**.

Three artifacts per chapter: **outline block** (packet-section format: Chapter Purpose /
Starting/Ending State / Reader-Facing Shape / Required Beats / Clues and Plants /
Character Knowledge / Guardrails + bulleted-bold wiring footer; NO `### Scene` sections,
ever) → **packet** (`packet_assemble.py`, deterministic slice+lookups, stamped) →
**map** (`/map-chapter`: `map-maker` proposes, showrunner approves, `map_check.py` gates
with named findings). `preflight draft` polices the staleness chain AND map cleanliness.
`overloaded-chapter` re-based onto Required Beats. Legacy invariant: an unmigrated
scenes-format book locks and drafts exactly as before, warned by name, never blocked.

**Spec:** `docs/superpowers/specs/2026-07-18-packet-map-chapter-design.md`
**Plan:** `docs/superpowers/plans/2026-07-18-packet-map-chapter.md` (11 tasks, subagent-driven)
**Recovery ledger:** `.superpowers/sdd/progress.md` — per-task commits, review findings,
fix waves. Trust it over memory after a compaction.

## Git state

- **Branch:** `main`, clean tree, **16 commits ahead of origin — NOT PUSHED** (no GitHub
  auth in the session; `git push origin main` needed).
- Feature range: `bc048a0..886e00b` (spec+plan commits, 11 tasks, final-review fix wave).
- **Tests: 595 passing** (was 608 pre-branch; 72 brief/weight tests deleted, rebuilt on
  the new machinery). Verify: `python3 -m pytest`.
- Final whole-branch review: 2 Criticals found and fixed (expander taught unparseable
  wiring; preflight skipped map cleanliness); verdict **ready to push**.

## Next actions

1. **Push main** (`git push origin main` after auth).
2. **Book-01 migration** (series-side, showrunner-paced, spec §10, from
   `~/myBooks/series-pelicanscrook`): rechapter `outline.md` 27 → ~40 packet-format
   blocks (old six-scene expansions are quarry; ratified example: old ch-1 = new ch-1
   "The Wheelhouse" + ch-2 "The First Right Piece"); renumber whodunit `plant_chapter`s
   + `reveal_chapter`; **add `description:` fields to clue_schedule/red_herrings entries**
   (packets render them; fallback is a named placeholder); **retune
   `obligations.max_per_chapter`** in the cozy beat sheet for the beats-inclusive basis
   (canonical ch-5 carries load 15 vs the old cap 8); delete lock, `preflight
   lock-mystery 01`; then `/map-chapter` + draft one chapter at a time (existing 3 drafts
   are salvage).
3. **Deferred companion spec unchanged** (the CURE half): `length_check.py` tape measure,
   word count as `/review-chapter`'s first step, `/compress-chapter` + compression-editor
   (the first agent allowed to cut). Fold in the triple-pass doc's patch-vs-full-revision
   split and the preserve-list ("strong material that must be kept") when speccing.
4. **Separate brainstorm owed:** `/new-series` onboarding (the front-loaded config
   homework the showrunner flagged). The showrunner also said they have MORE process
   points to discuss — ask.

## Accepted minors (cosmetic, in the ledger)

`_NO_PROFILE_NOTE` doesn't name check ids; `dropped-beat` misnames out-of-range claims;
raw traceback on non-numeric chapter arg in packet_assemble; Clue/Weight regex
case-sensitivity; length profile outside the staleness chain; one weak grep-test in
test_map_chapter_command; expander template's Closes/Carries guidance parentheticals
parse loud-but-dirty if copied verbatim.

## Watch out for

- **The taste stage is again untested by construction.** 595 green proves parsing,
  assembly, arithmetic, staleness. It proves nothing about whether `map-maker` proposes
  good maps. The first live `/map-chapter` run on a migrated book-01 chapter is the real
  shakedown.
- **Wiring footer syntax is bulleted-bold only** (`- **Opens:** q-slug — phrasing`,
  `- **Hook:** q-slug — [cliffhanger] …`). The bare `Opens: q-x` form is INVISIBLE to the
  parser — this was final-review Critical C1; both the spec's example and the expander
  template now teach the parseable form. Never regress this.
- **Session-limit interruptions:** two subagents were cut off mid-task this session
  (limits reset hourly-ish); tree was clean both times, resumed via SendMessage. Check
  `git status` + the ledger before re-dispatching anything.
- The user's working style: plain language (chapter plans, proofreaders — not schemas);
  discuss in prose before offering menus; detailed feedback ending in "DONE"; the
  showrunner's authored examples ARE the format specs.
