# Handoff — Penny (fiction-series engine) / main
Saved: 2026-09-10 | Type: build (an audit, and the two phases shipped from it)

> **Stream note.** This replaces the 2026-09-02 drafter voice-pack handoff (recoverable at
> `7f495bc`), which recorded "nothing pending". The other stream files
> (`HANDOFF-engine.md`, `HANDOFF-story.md`, `HANDOFF-direction.md`, `HANDOFF-of122.md`,
> `HANDOFF-readiness-briefs.md`) were not touched.

## What we're building

The session began as a review question — *drafting takes too many tokens; are all these
checks needed?* — and became two shipped phases. The audit measured the live series rather
than reasoning from the design docs, and found the engine **running its expensive check
layer while most of its free one was switched off**.

Two specs, both in `docs/superpowers/specs/`:
- `2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md` — **shipped**
- `2026-09-09-check-economics-design.md` — §3b **shipped**, §3a and §3c **not started**

## Git state

- Branch: `main`, **pushed through `05c1595`** (`d807ab0..05c1595`, 18 commits).
- Uncommitted: none. Untracked: `docs/superpowers/specs/2026-09-08-chapter-status-manifest-design.md`
  — from a session before this one, deliberately left alone.
- Tests: **1354 passed** (~6s). `CLAUDE.md:52` is self-enforcing — see "Watch out for".

## Next actions

**Phase A §3a is the next work, and it is the half that makes the checks cheap.** It is
already specced (`2026-09-09-check-economics-design.md` §3a), so it needs a *plan*, not a
spec. Three items:

1. **Turn on `tension_check`.** All ten findings are still dark. Before the guardrail fix
   they could not run at all (`wired: False`); now they can. Run it in **report mode
   first** — a 35-chapter outline never checked will produce a burst, and some findings
   will be threshold disagreements. Triage with the showrunner, then
   `--waive check-id:"reason"` (recorded on the certificate) rather than bending the
   outline. Only then let it gate.
   - The live series' lock still reads `validated: fairplay+lexicon`. It will need
     re-minting after a re-cut to claim `+tension`.
2. **Make `/review-chapter` actually run `voice_drift.py` and `lexicon_check.py`.** Step 5
   already specifies both; nothing asserts they ran, and they ran in **1 of 12** rounds in
   the live series. Extend the step-8 dispatch-completeness check to cover the 2a checkers.
   `inspector-voice` now declares those two files directly in its Inputs (done in Phase B
   Task 4), so the delivery route already exists.
3. **Settle the thread roster.** `series/continuity/threads/` does not exist, so
   `inspector-structure`'s liveness half is permanently inert and
   `ledger_markers.py --thread-advanced` has nothing to write to. Either create and
   populate it from `/finalize-chapter`, or switch that half off deliberately and stop the
   agent claiming it.

**Then §3c** — the roster decision (voice, structure, developmental-editor), which was
deliberately deferred until those checks have run with their real inputs at least a few
chapters.

**Owed follow-up specs** (none blocking):
- Authored `Summary:`/`Opening:` cut-plan values can still carry a column-0 heading —
  the same collision class as the guardrail fix, reproduced by a reviewer. `has_wiring`
  stays `True` because a later chapter survives, so nothing notices. Needs
  `_demote_headings` lifted into a shared module.
- A `--ledger-clues` projection, to make fairplay's clue route machine-scoped like the
  other two instead of prose-directed, and to give the legacy no-packet path a real route.
- `2026-09-09-check-economics-design.md` still says `--no-continuity` at §5 (line ~210)
  and §6 (line ~228). The flag is `--without-continuity`. Two-word doc fix.
- README describes the drafter's slice as one undifferentiated thing (~878, ~1037), with
  no equivalent of CLAUDE.md's "transmitted by consumer, not by default" framing.

## Decisions made this session

- **The checks were never the problem — the wiring was.** 12 review rounds in the live
  series produced 5 blocking findings total; 10 of 12 rounds passed the gate. Nothing was
  deleted as a result of the audit, and nothing should be until §3a gives the quiet
  inspectors their real inputs.
- **Projections are pure functions of the packet's text, printed to stdout.** They never
  write and never call `assemble()`. Forced by the staleness chain: packets are stamped
  and every map carries `built_from_packet`, so a regenerating projection would stale
  every map in the series at once. Three separate tests of this invariant were found
  **vacuous** before landing — a byte-identity assertion cannot catch regeneration,
  because `assemble()` is deterministic. The surviving tests use a marker the
  regeneration would destroy, and for `inspector_slice` that marker must sit **inside**
  the continuity section, since the projection returns only that.
- **The slice splits by consumer, not by deletion.** `background/` is drafter fuel;
  `characters/`/`locations/`/`threads/` are the ledger. Evidence: both real continuity
  blockers in the live series trace to `characters/` (`characters/lisa.md:14`,
  `characters/maggie.md`). Reversible per-inspector if a later catch proves otherwise.
- **`CLAUDE.md`'s test count moves with every test-adding commit.** The original plan said
  "don't edit CLAUDE.md"; that was a plan defect —
  `tests/test_texture_allocation_docs.py:118` re-collects the suite and asserts the line,
  so adding a test without bumping it turns the suite red by construction.
- **Deferred, not dismissed:** the authored-`Summary:` collision (needs a shared-module
  refactor that does not belong in a fix wave) and the roster decision (needs data).

## User preferences expressed this session

- **Push at phase end, and say so.** The instruction was "commit and push before building";
  it was read narrowly (specs safe before risky work) and the push was held for two full
  phases before being asked for again. Next time: push at phase end without re-asking.
- **Plan and build with subagents.** Established mode for this repo now — plan file,
  one implementer per task, fresh reviewer per task, final whole-branch review.
- **The version churn on book 01 was the story being written, not waste.** Nine redrafts of
  ch-01 were the showrunner resolving plot gaps and are accepted as part of the process.
  Do not treat redraft count as a defect metric.

## Key files right now

- `docs/superpowers/specs/2026-09-09-check-economics-design.md` — §3a is the next work.
- `scripts/packet_assemble.py` — `without_continuity`, `inspector_slice`, `_manifest`,
  `_continuity_slice`'s both-ends rule, and `main()`'s projection branch.
- `commands/review-chapter.md` — steps 4, 5, 7, 7b carry the routing; step 5 is where
  §3a.2 lands.
- `scripts/tension_check.py` — ten findings, all currently unexercised on the live series.
- `tests/test_packet_projection_wiring.py` — pins the wiring; a projection nothing
  dispatches is inert and no other test would notice.

## Watch out for

- **`CLAUDE.md:52`'s `full suite (N tests)` line is asserted against a live collect.** Any
  commit that adds a test must move it, or the suite goes red by construction.
- **Runbook edits need a session restart** — `commands/*.md` are cached per session.
- **Never write a bare `$` before a digit in `commands/*.md`.** Substitution applies inside
  fenced code blocks; `tests/test_runbook_arguments.py` fails the build on one.
- **A test that looks like it bites often does not.** Four times this session a test
  asserted an invariant it could not actually observe. Mutation-test anything guarding a
  load-bearing property: break it deliberately, confirm the test fails, restore.
- **The live series (`~/myBooks/pelicanscrook-series`) was never modified** — read-only
  throughout. It is a separate repo. Phase B changed packet hashes by design, so when it
  is next touched: chapters mapped but not yet drafted need `/map-chapter` re-run, and a
  re-cut invalidates the mystery lock.
- **`inspector-fairplay` was grading clue-planting without the clue schedule** until Phase B
  Task 4 routed `## Ledger Clues` to it. Latent for a long time — its instruction 1 says
  "From the slice", and the slice never carried that section. Worth remembering when
  reading any older verdict from that inspector.
