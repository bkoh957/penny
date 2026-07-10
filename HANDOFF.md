# Handoff — Penny (fiction-series engine) / main
Saved: 2026-07-10 03:00 | Type: build (docs reconciliation + repo hygiene)

## What we're building
Penny = ONE engine (a Claude Code plugin) driving MANY series (active series = cwd via a
`.penny/` marker), with a swappable genre-pack layer. Priority: **no engine drift**. This
session shipped no new capability: it **reconciled the docs with the shipped code**, then
gave the cozy series a private GitHub remote and renamed it. The previous session's feature
(the pre-draft outline developmental review tier) is still **un-shaken-down live** — that
remains the top next action.

## Git state
- **Engine** (`~/myTools/penny`, github `bkoh957/penny`): `main` clean, pushed.
  Suite **325 green**.
  - `be72623` — README + CLAUDE.md redrafted (mine).
  - `63d3722` — `fix: align Penny engine docs and readiness checks` (**the user's own
    commit**, landed mid-session). Removed the hardcoded-filename drift I'd flagged; also
    touched HERMES.md, TESTING.md, drafter/outline-expander agents, draft-chapter,
    +1 test in `tests/test_readiness_check.py`.
- **Series** (`~/myBooks/series-pelicanscrook`, github `bkoh957/series-pelicanscrook`
  — **PRIVATE**): `main` clean, pushed, tracking `origin/main`. `8fb4a11`, `a530de8`.
- Uncommitted: this `HANDOFF.md` only.

## What happened this session
1. **README fully redrafted** as an end-to-end runbook (create a runnable series → plan/lock
   a book → per-chapter loop → assemble/read/approve). It had omitted four shipped commands
   entirely: `/scaffold-book` (now the recommended outline-first front door), `/plan-book`,
   `/expand-outline`, `/review-outline`. It also never mentioned the `genres/` layer.
2. **CLAUDE.md reconciled**: config overlay is **three tiers** (series → `genres/<g>/` →
   plugin default, keyed off `series.yaml`'s `genre:` line), not two; `preflight.py` has
   **six** subcommands (`approve-book` was missing); test count; the three context-rich
   agent exceptions (developmental-editor, outline-expander, outline-reviewer).
3. **Disambiguated two phase schemes** that were being conflated: design §13's *build order*
   (1–8; Phase 6 shipped = MVP-1 endpoint) vs the *plugin/genre roadmap* (Phase 3a/3b
   shipped; **Phase 4 = thriller pack, specced but unapproved**).
4. **Series repo published** to a private remote, and renamed `cozy-pelicans` →
   `series-pelicanscrook` to match. `series.yaml` gained a `name:` field.
5. Documented `.penny/` fresh-clone recovery in the series README — **verified against a
   real throwaway clone**, not asserted.

## Next actions
1. **LIVE SHAKEDOWN of the outline-review tier (UAT).** Still not done — carried over. Its
   deterministic core is tested; the agent/command/**Codex panel** layer is unit-test-exempt
   by design. `cd ~/myBooks/series-pelicanscrook && /review-outline 01`. Judge (a) reviewer
   quality and (b) that Codex actually answers as the second panel member. **Codex is
   installed and reachable** (`codex-cli 0.141.0` at `~/.local/bin/codex`) — I verified this,
   so a "Claude-only, independence reduced" result is now a REAL BUG, not the expected
   graceful degradation.
2. **Fix the surviving overlay bug** (below) — small, and it will bite the thriller pack.
3. **Phase 4 (thriller genre pack)** — still specced-but-unapproved, untouched for two
   sessions. Resolve the 5 `[DECISION]` flags in
   `docs/superpowers/specs/2026-07-08-thriller-genre-pack-design.md`, then writing-plans →
   subagent-driven-development. It should ship its own `review-rubrics/outline-craft.md` so
   `/review-outline` works there too (the rubric is genre data; the engine is agnostic).

## OPEN BUG — directory lookups don't union across overlay tiers
From the series root, `readiness_check.py 01` reports:

```
- name: review-rubrics
  status: blocked
  detail: 2/5 file(s)
```

`config_path("review-rubrics")` hits the **genre tier** (`genres/cozy-mystery/review-rubrics/`,
2 files) and stops, **shadowing** the plugin tier's 5. First-hit-wins is right for *files* and
wrong for *directories*: a genre pack adding `fairplay-planting.md` should not hide
`character-voice.md`. Survived `63d3722` (that commit fixed a *different* drift — the
hardcoded `coastal-victoria-au.md` / `cozy-mystery.md` filenames — which is now genuinely gone).

Not currently load-bearing (readiness is a reporter, never a gate), **but `/review-chapter`
resolves its inspector rubrics through the same overlay** — check whether the inspector
roster is silently short a rubric before trusting a PASS. Fix is likely a union-across-tiers
`config_dir()` helper, distinct from `config_path()`.

## Decisions made this session
- **Documented the shipped-defaults gap rather than papering over it.** The engine ships NO
  `run-config.md`, voice-pack, setting-pack, genre-pack, `length-profile.md`, or beta
  personas, though `readiness_check.py` requires all of them — so a freshly `/new-series`'d
  folder is **not yet runnable**. A doc implying otherwise sends the next agent hunting for
  files that don't exist.
- **`series.yaml`'s new `name:` field is inert** — `penny_paths` parses only `genre:`, and
  the display name comes from the directory via `active()`. Said so in the commit message so
  nobody mistakes it for load-bearing. Making the engine honour it would cut against the
  "the directory IS the selector" principle ([[anchor-design-to-working-style]]).
- **Confirmed repo visibility before pushing.** The series holds the unpublished manuscript
  AND `output/book-01/mystery-solution.md` (the sealed answer key). It was **public** on
  first probe; the user made it private; I re-probed (unauth GET 200 → 404) before pushing.
  Do this again before any future push.

## User preferences expressed this session
- Detailed feedback; **discuss in prose before multiple-choice**. Lead with a recommendation.
- **Terminal-native** — the filesystem/`cd`/editing a file IS the interface.
- Will land his own fixes mid-session (see `63d3722`) — **re-read files before editing**;
  don't assume your last write is still the current content.
- Work phase-at-a-time on `main`; push at phase end (both repos now have remotes).

## Key files right now
- `scripts/penny_paths.py:36` (`config_path`) + `scripts/readiness_check.py` — the open bug.
- `commands/review-outline.md` — the orchestrator to exercise in the live shakedown.
- `README.md` / `CLAUDE.md` — freshly reconciled; trust them over memory now.
- `.superpowers/sdd/progress.md` — SDD ledger + recovery map for the outline-review build.

## Watch out for
- **Verify pytest counts yourself** — implementers have misreported before. Current truth: **325**.
- **The engine repo is NOT a series.** Running any pipeline command (incl. `/review-outline`)
  from `~/myTools/penny` hard-errors `penny-paths: no series root`. That is correct. `cd` to
  the series folder.
- **A fresh clone of the series is not a recognized series** — `.penny/` is gitignored (locks
  are earned by validation, never by checkout) and git can't store empty dirs. Recover with
  `mkdir -p .penny/locks` then `preflight.py lock-mystery 01`. Documented in that repo's README.
- The **outline-feedback ledger is hand-editable YAML** — a malformed edit is tolerated by
  `status` (nudge, still exit-0) but makes `/review-outline append` fail loudly (intended).
- Deferred minors (in `.superpowers/sdd/progress.md`): `VALID_STATES` dead const;
  `status_line` path-prefix partial DRY; render-fail exit test.
