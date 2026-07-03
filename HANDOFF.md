# Handoff — Penny / main
Saved: 2026-07-03 14:30 | Type: build

## What we're building
Expanding Penny from a single-series harness into a **one-engine, many-series** system.
Each series becomes a self-contained pack under `packs/<slug>/`; the engine
(`scripts/`, `.claude/`) stays shared so fixes never drift across series. The design is
**approved and specced**; next step is the implementation plan. This is effectively a
new engine phase, done *before* the still-unbuilt Phase 6.

## Git state
- Branch: main
- Uncommitted changes: none (clean tree)
- Last commit: `66a32cd` docs(spec): multi-series via one engine + swappable packs
- Tests: not re-run this session (no code changed yet); baseline ~273 passing

## Next actions
1. **Wait for the user's spec review.** The brainstorming flow is paused at the
   user-review gate — they were asked to review
   `docs/superpowers/specs/2026-07-03-multi-series-packs-design.md`. Two items flagged
   for their attention: (a) the exact engine-default vs pack-override config split, and
   (b) comfort with a **fixture pack** under `tests/fixtures/` for resolver/gate tests
   vs pointing tests at live `cozy-pelicans` content. Apply any requested changes and
   re-commit the spec.
2. **Once approved, invoke the `writing-plans` skill** (NOT any implementation skill) to
   turn the spec into a TDD-ordered plan under `docs/superpowers/plans/`.
3. Plan must order work as: land `scripts/penny_paths.py` + its own tests FIRST
   (red→green in isolation), THEN migrate consumers one script at a time keeping the
   full suite green, THEN the `git mv` migration into `packs/cozy-pelicans/`, THEN the
   two new commands (`/use-series`, `/new-series`).

## Decisions made this session
- **Strategy B (one engine, many packs) — not clone-per-repo, not engine-as-submodule**:
  chosen because the user's stated driver is "no engine drift." Clone reintroduces the
  drift; submodule was heavier than needed for a handful of series.
- **Two-tier config overlay, not three**: engine ships craft-general defaults, a pack
  overlays any file (`pack/config/<rel>` else engine `config/<rel>`). User explicitly
  rejected a middle "genre" tier.
- **Layered selection `--series` flag > `PENNY_SERIES` env > `.penny/current-series`
  pointer > hard error**: pointer alone is global mutable state and unsafe for parallel
  work; per-session env/flag gives clean parallelism. User confirmed wanting parallel
  series builds.
- **Beta readers = persona swap only**: `beta-readers/personas/` → pack; but
  `beta-readers/beta-protocol.md` (K-of-M consensus mechanics tied to `beta_report.py`)
  STAYS in the engine. The driver-value enum travels with the personas, not the protocol.
- **Sequencing: do multi-series refactor now, defer Phase 6** (per-book assembly / final
  read / revision-priority). User said "leave phase 6 for now." Building it series-aware
  later avoids refactoring the same output-path scripts twice.
- **Slug for the existing series: `cozy-pelicans`** (renameable at migration time).

## User preferences expressed this session
- Lead with a recommendation, then options (consistent with saved working-style memory).
- Wants genuine parallel multi-series capability, not just sequential switching.
- Beta readers are a per-series lens; keep only the persona layer swappable.

## Key files right now
- `docs/superpowers/specs/2026-07-03-multi-series-packs-design.md` — the approved spec;
  the source of truth for the plan. Read it first.
- `scripts/preflight.py` — already threads `repo_root`; the model for how paths should be
  parameterized. Lightest to adapt.
- `scripts/readiness_check.py` — the widest path-hardcoder; biggest refactor target.
- `scripts/penny-statusline.sh` — must show active series + read the active pack's
  `.penny/current-stage`, honoring `PENNY_SERIES` for parallel terminals.
- `CLAUDE.md` — the engine-vs-swappable rule this whole effort operationalizes.

## Watch out for
- **HARD-GATE (brainstorming skill):** do NOT start implementation until the user
  approves the written spec. We are at the review gate, not past it. After approval the
  ONLY next skill is `writing-plans`.
- **Test blast radius is the real risk:** many of the ~273 tests assert literal
  `output/book-01/…`, `config/…`, `series/…` paths. Plan mitigation is: `penny_paths` +
  tests first in isolation, then migrate consumers one at a time. Do not do the big
  `git mv` before the resolver + tests are green.
- `scripts/penny_meta.py`, `penny_verdict.py`, `penny_text.py` are layout-agnostic — do
  NOT touch them.
- The existing `HANDOFF.md` before this save was from the book-01 authoring session; this
  overwrite intentionally replaces it with the multi-series work state.
- Don't add a PyYAML dependency for any of this (dependency-split rule); the pointer file
  and config parsing use `penny_meta` / plain reads.
