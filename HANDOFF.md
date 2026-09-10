# Handoff — Penny (fiction-series engine) / main
Saved: 2026-09-10 | Type: build (check-economics §3a shipped; the book-01 pass is next and is operator work)

> **Stream note.** Replaces the 2026-09-10 handoff written earlier the same day
> (recoverable at `9a32c17`). Other stream files (`HANDOFF-engine.md`,
> `HANDOFF-story.md`, `HANDOFF-direction.md`, `HANDOFF-of122.md`,
> `HANDOFF-readiness-briefs.md`) untouched.

## What we're building

An audit found the engine **running its expensive LLM check layer while most of its free
deterministic one was switched off**. Three phases have now shipped from it. All specs live
in `docs/superpowers/specs/`.

| | spec | state |
|---|---|---|
| guardrail heading collision | `2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md` | **shipped** |
| packet slice transmission cut | `2026-09-09-check-economics-design.md` §3b | **shipped** |
| restore the free check layer | `2026-09-09-check-economics-design.md` §3a | **shipped (engine side)** |
| the roster decision | `2026-09-09-check-economics-design.md` §3c | **not started, deliberately** |

## Git state

- Branch: `main`, **pushed through `36b3672`**. In sync with origin.
- Uncommitted: none. Untracked: none.
- Tests: **1398 passed** (~6s). `CLAUDE.md:52` is self-enforcing — see "Watch out for".

## Next actions

### 1. The book-01 tension pass — operator work, do this first

`tension_check` has never run on the live series. It can now:

```bash
cd ~/myBooks/pelicanscrook-series
python3 "$PENNY/scripts/tension_check.py" 01     # read-only, mints nothing
```

Expect a burst — ten checks over a 35-chapter outline never checked. **Some findings will
be threshold disagreements to waive, not fix**; `preflight lock-mystery 01 --waive
check-id:"reason"` records the reason on the certificate. This is a session with the
showrunner reading findings, not something to run to completion unattended.

Note the lock still reads `validated: fairplay+lexicon`. It needs re-minting to claim
`+tension`, and a re-cut first if the outline changes.

### 2. Fix the certificate-coverage hole while you are there

**The lock can claim tension coverage it does not have.** `_curve_checks`
(`scripts/tension_check.py:492-498`) only runs when a beat sheet resolves, and it takes no
`notes` argument — so `dead-stretch`, `starved-thread` and `off-mark-beat` have **no code
path** by which to record a skip. `overloaded-chapter` and `monotonous-closings` reach the
certificate through `notes` → `skipped_lines` (`scripts/preflight.py:370-375`).

Verified end-to-end by a reviewer on a genre-less series: stdout named all five, the
certificate read `validated: fairplay+lexicon+tension` with **zero** `skipped:` lines. In a
legacy-shaped outline all five vanish without trace. `scripts/preflight.py:371-373` carries
a comment saying "the lock cannot claim coverage it does not have".

Fix is small — append `NO_BEAT_SHEET_NOTE` to `skipped_lines`, or have the curve/beat checks
raise their notes unconditionally. Left undone because the process allows one fix wave after
a final review. **Do it in the same session as action 1**, since that session re-mints the lock.

### 3. Then §3c — the roster decision, with real data

Deferred until the quiet inspectors had run with their declared inputs. After a few chapters
under action 1: re-evaluate `inspector-voice` (12/12 at score 4, never blocked, but had never
been given `voice_drift`/`lexicon_check` evidence until now) and `inspector-structure` (now
single-job). And make `developmental-editor` opt-in — 36,164 tokens, advisory by design,
scored 4 in all 11 rounds it ran.

### Parked, with reasons (none blocking)

- **A tautological test.** `tests/test_preflight.py:904-908` asserts
  `lock_path("1".zfill(2)) == lock_path("01")` — it pads its own input, so both sides are
  identical and it cannot fail for any implementation. Delete it or route it through `main()`
  for two subcommands.
- `tests/test_review_completeness.py:238` keeps a cwd-relative `Path` under a shadowing local
  import, so that file still fails from a non-repo-root cwd. Same for
  `tests/test_plot_book_command.py:3`.
- `NO_BEAT_SHEET_NOTE` fires inside `if tres["wired"]` in preflight but unconditionally in
  `tension_check`, so for an unwired outline the report names five and the gate names none.
  Cosmetic — `validated:` correctly stays `fairplay+lexicon`.
- `HANDOFF` step-map staleness has bitten twice now; §3a.2 landed as **step 7**, not step 5.
- **Bundle for a later phase:** `commands/finalize-chapter.md`'s `--thread-advanced` write has
  no reader since the liveness retirement; `tests/test_run_config.py:17` still requires
  `thread_dormant_after_chapters`; `tests/fixtures/cozy/series/arc-ledger.md:13` still
  describes the roster.
- **Owed follow-up specs:** the authored `Summary:`/`Opening:` heading collision (same class as
  the guardrail fix, invisible because `has_wiring` survives it); a `--ledger-clues` projection
  to make fairplay's clue route machine-scoped.

## Decisions made this session

- **Thread-liveness was retired, not built.** Nothing creates a thread file, `ledger_markers.py`
  only updates existing ones, `arc-ledger.md` is an empty table. The genre's four tracks catch
  the same failure at book scale via `starved-thread`, which works. Named per-thread dormancy is
  Phase 8 series-scale work. Recorded in the spec rather than rewriting `penny-design-v3.md`,
  which remains the source of truth for design intent.
- **The completeness check moved from prose to a script.** An agent asked to confirm files exist
  is the soft gate this engine rejects; CLAUDE.md's layer rule puts deterministic gates in
  `scripts/`.
- **One resolution, two callers.** `tension_check.resolve_inputs` is shared with
  `preflight lock-mystery` so a pre-lock report cannot disagree with the gate about what ran.

## Key files right now

- `docs/superpowers/specs/2026-09-09-check-economics-design.md` — §3c is the remaining work.
- `scripts/tension_check.py` — `resolve_inputs`, `BEAT_SHEET_DEPENDENT`, the book-number CLI.
- `scripts/preflight.py` — `main()` pads the book number for every subcommand; `:370-375` is
  where the certificate gap lives.
- `scripts/review_completeness.py` — the new gate; `VERDICT_FILES` is pinned against the
  runbook's table.
- `commands/review-chapter.md` — live step labels `1,2,3,4,5,6,6b,7,8,9,10`; 5 = the 2a
  checkers, 7 = completeness, 8 = gate.

## Watch out for

- **`CLAUDE.md:52`'s `full suite (N tests)` line is asserted against a live collect.** Any
  commit adding or removing a test must move it, or the suite goes red by construction. Note
  it can go **down** — one fix replaced a five-case parametrize and the count fell.
- **Runbook edits need a session restart**; `commands/*.md` are cached per session.
- **Never a bare `$` before a digit in `commands/*.md`.**
- **Mutation-test anything load-bearing.** Six tests across these three phases asserted
  invariants they could not observe — one compared a dict to its own copy, one matched a note
  that named the same ids as the finding it meant to check, one padded its own input. A green
  run is not evidence. Break it, confirm the failure, restore.
- **Check the whole call graph, not just the file you changed.** `/plot-book` was the engine's
  only caller of `tension_check` and still used the broken path form after the book-number form
  landed — caught by the final whole-branch review, not by any task review.
- **The live series (`~/myBooks/pelicanscrook-series`) was never modified** — read-only
  throughout, separate repo. Phase B changed packet hashes by design: chapters mapped but not
  drafted need `/map-chapter` re-run.
