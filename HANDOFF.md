# Handoff — Penny (fiction-series engine) / main
Saved: 2026-09-10 | Type: build (engine work complete; the next step is operator work on the book)

> **Stream note.** Updates the earlier 2026-09-10 handoff (`fda1a7a`), whose next-action 2
> (the certificate hole) is now **done**. Other stream files (`HANDOFF-engine.md`,
> `HANDOFF-story.md`, `HANDOFF-direction.md`, `HANDOFF-of122.md`,
> `HANDOFF-readiness-briefs.md`) untouched.

## What we're building

An audit found the engine **running its expensive LLM check layer while most of its free
deterministic one was switched off**. Four phases have shipped from it. Specs in
`docs/superpowers/specs/`:

| | spec | state |
|---|---|---|
| guardrail heading collision | `2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md` | **shipped** |
| packet slice transmission cut | `2026-09-09-check-economics-design.md` §3b | **shipped** |
| restore the free check layer | `2026-09-09-check-economics-design.md` §3a | **shipped** |
| lock claims coverage it lacks | `2026-09-10-lock-can-claim-tension-coverage-it-lacks-fix.md` | **shipped** |
| the roster decision | `2026-09-09-check-economics-design.md` §3c | **not started, deliberately** |

**The engine side is done.** Everything remaining is work on the book itself.

## Git state

- Branch: `main`, **pushed through `e3b44a9`**. In sync with origin.
- Uncommitted: none. Untracked: none.
- Tests: **1408 passed** (~6s). `CLAUDE.md:52` is self-enforcing — see "Watch out for".

## Next actions

### 1. The book-01 pass — operator work, and the whole point of the last four phases

**Do not skip the re-cut.** The engine is fixed; book 01's outline is not. It still carries
105 guardrail headings (35 chapters × 3), so `tension_check 01` today reports `wired: False`
and finds nothing. The fix changed what `story_cut.py` *emits*; it only reaches an outline
produced by a fresh cut.

Checked this session: **the re-cut is safe** — `recut_refusal` returns `None`, so the outline
still matches its `cut_output_sha256` and nobody has hand-edited it since the cut. The source
layer is intact: `story.md` (272 beats), `cut-plan.md`, and four plot save points.

Sequence, from `~/myBooks/pelicanscrook-series`:

1. **Re-cut** — emits the outline without the pasted guardrails, so chapter blocks stay whole
   and the wiring footers survive.
2. That rewrites `plant_chapter:` in `series/whodunit/book-01.yaml` and **invalidates the
   mystery lock** — delete `.penny/locks/book-01.mystery.lock`.
3. **`preflight lock-mystery 01`** — this is where all ten checks finally run. Expect a burst
   on a 35-chapter outline never checked. **Some findings will be threshold disagreements to
   waive, not fix**: `--waive check-id:"reason"` records the reason on the certificate.
4. The outline's hash changes, so the 2 packets and 2 maps go stale — re-run `/map-chapter`
   for each. (Phase §3b changed packet hashes anyway, so this was already owed.)

Blast radius is small **now**: 2 mapped chapters, 2 drafts, 1 final. The same re-cut after
twenty chapters are mapped costs twenty `/map-chapter` runs. The drafts and the final are
untouched by any of it.

### 2. Then §3c — the roster decision, with real data

Deferred until the quiet inspectors had run with their declared inputs. After a few chapters
under action 1: re-evaluate `inspector-voice` (12/12 at score 4, never blocked — but had never
been handed `voice_drift`/`lexicon_check` evidence until §3a) and `inspector-structure` (now
single-job since the liveness retirement). And make `developmental-editor` opt-in — 36,164
tokens, advisory by design, scored 4 in all 11 rounds it ran.

### Parked, with reasons (none blocking)

- **A tautological test.** `tests/test_preflight.py:904-908` asserts
  `lock_path("1".zfill(2)) == lock_path("01")` — it pads its own input, so both sides are
  identical and it cannot fail for any implementation. Delete or route through `main()`.
- `tests/test_review_completeness.py:238` and `tests/test_plot_book_command.py:3` use
  cwd-relative paths, so those files fail from a non-repo-root cwd.
- `NO_BEAT_SHEET_NOTE` fires inside `if tres["wired"]` in preflight but unconditionally in
  `tension_check`, so for an unwired outline the report names five and the gate names none.
  Cosmetic — `validated:` correctly stays `fairplay+lexicon`.
- `check_overload`'s note says "declares no `obligations.max_per_chapter`" even when no beat
  sheet resolved at all. Pre-existing wording.
- **Bundle for a later phase:** `commands/finalize-chapter.md`'s `--thread-advanced` write has
  no reader since the liveness retirement; `tests/test_run_config.py:17` still requires
  `thread_dormant_after_chapters`; `tests/fixtures/cozy/series/arc-ledger.md:13` still
  describes the roster.
- **Owed follow-up specs:** the authored `Summary:`/`Opening:` heading collision (same class as
  the guardrail fix, invisible because `has_wiring` survives it); a `--ledger-clues` projection
  to make fairplay's clue route machine-scoped.

## Decisions made this session

- **The certificate had three doors, not two.** The spec named two (no beat sheet; beat sheet
  but no turning points); review found a third inside the first's success case — a beat sheet
  that resolves but declares no `tracks.max_dark_gap` left `starved-thread` silent. All three
  now record.
- **`dead-stretch` deliberately does NOT note** when it has no explicit threshold: it defaults
  `min_open_before_reveal` to 1 and genuinely runs, so a note would be the certificate claiming
  a skip that never happened. The fix had to be truthful in both directions.
- **Scoped to the wired branch.** On an unwired outline these checks are *not applicable*
  rather than *unrunnable*, `validated:` correctly stays `fairplay+lexicon`, and noting them
  would turn every legacy outline's correct silence into certificate noise.
- **Thread-liveness was retired, not built** (§3a). Nothing creates a thread file; the genre's
  four tracks catch the same failure at book scale via `starved-thread`. Named per-thread
  dormancy is Phase 8 work. Recorded in the spec rather than rewriting `penny-design-v3.md`,
  which stays the source of truth for design intent.

## Key files right now

- `docs/superpowers/specs/2026-09-09-check-economics-design.md` — §3c is the remaining spec work.
- `scripts/tension_check.py` — `resolve_inputs`, `BEAT_SHEET_DEPENDENT`, `CURVE_BEAT_CHECKS`,
  the three notes, the book-number CLI.
- `scripts/preflight.py:369-375` — the `notes` → `skipped:` transcription (unbranched and
  string-agnostic, which is why module-level coverage of a new note is sufficient).
- `scripts/review_completeness.py` — the new gate; `VERDICT_FILES` pinned against the runbook.
- `commands/review-chapter.md` — live step labels `1,2,3,4,5,6,6b,7,8,9,10`; 5 = the 2a
  checkers, 7 = completeness, 8 = gate.

## Watch out for

- **`CLAUDE.md:52`'s `full suite (N tests)` line is asserted against a live collect.** Any
  commit adding or removing a test must move it. It can go **down** — one fix replaced a
  five-case parametrize and the count fell.
- **Runbook edits need a session restart**; `commands/*.md` are cached per session.
- **Never a bare `$` before a digit in `commands/*.md`.**
- **Mutation-test anything load-bearing.** Seven tests across these four phases asserted
  invariants they could not observe: one compared a dict to its own copy; one matched a note
  naming the same ids as the finding it meant to check; one padded its own input; one derived
  its expected set by subtracting the very list it was meant to guard. A green run is not
  evidence. Break it, confirm the failure, restore.
- **Watch what the test watches, not just what it asserts.** The certificate defect survived
  1400 tests because the coverage was on **stdout** while the bug was in the **artefact**.
  Deleting the fix fails the certificate test and leaves the stdout test green.
- **Check the whole call graph.** `/plot-book` was the engine's only caller of `tension_check`
  and still used the broken path form after the book-number form landed — caught by the final
  whole-branch review, not by any task review.
- **The live series (`~/myBooks/pelicanscrook-series`) has never been modified** — read-only
  across every session so far. It is a separate repo. Action 1 is the first write.
