# Spec — Multi-series via one engine + swappable packs

Saved: 2026-07-03 | Status: design approved, pending spec review

## Problem

Penny's founding rule already holds: the engine (`scripts/`, `.claude/`) is
genre/location-agnostic, and everything project-specific lives in swappable `config/`,
`series/`, and `input/`. But the layout assumes **one series == the repo root**. The
multi-book unit (`book-01` … `book-13`) lives *inside* a single series; there is no home
for a *second, different* series (different genre, cast, voice, packs).

The showrunner wants to start additional series. The naive path — clone the repo per
series — reintroduces exactly the drift the architecture was designed to prevent: the
engine is still evolving (Phase 6 unbuilt), so N clones would each need every future
bugfix hand-synced and would inevitably diverge. **The decided priority is "no engine
drift": improve one engine, have every series benefit automatically.**

## Goal

One engine drives many series. Each series is a self-contained **pack** of swappable
data. Engine improvements propagate to every series with zero per-series work. Two
series can be built **in parallel** without colliding. Migrating the existing cozy
series into the new layout is a single, test-green cutover.

## Non-goals

- **Not** a genre/plugin marketplace or dynamic pack discovery — packs are directories
  the showrunner authors.
- **Not** a third "genre" config tier (explicitly ruled out; two tiers only).
- **Not** Phase 6. Per-book assembly / final read / revision-priority is deferred and
  will be built series-aware *after* this refactor lands.
- **Not** a rewrite of the per-chapter pipeline logic — only its **pathing** changes.
- **No** new LLM judgments. This is a deterministic layout + resolver change.

## Decisions (locked in brainstorming)

1. **Strategy: one engine, many packs** (parameterized series root) — not clone-per-repo,
   not engine-as-submodule. Chosen because the driver is *no engine drift*.
2. **Config = two-tier overlay.** Engine ships craft-general defaults; a pack overlays
   any file it specializes. No genre tier.
3. **Selection = layered:** `--series` flag → `PENNY_SERIES` env → `.penny/current-series`
   pointer → hard error if none.
4. **Parallelism = per-session selection + disjoint pack paths.** Two terminals, each
   with `PENNY_SERIES` set, touch completely disjoint files.
5. **Beta readers:** persona *swap* per series (`beta-readers/personas/` → pack); the
   consensus *mechanics* (`beta-readers/beta-protocol.md` + `scripts/beta_report.py`)
   stay in the engine.
6. **Sequencing:** do this refactor now; Phase 6 later.

## Architecture — layout

```
penny/                        ← the repo IS the engine
  scripts/                    ENGINE (fixed) — incl. new scripts/penny_paths.py
  .claude/                    ENGINE (commands, agents)
  config/                     ENGINE DEFAULTS (craft-general, improve-once)
  packs/                      ← NEW home for all series
    cozy-pelicans/            the current series, migrated here
      config/                 OVERRIDES only (voice/setting/genre/run-config/…)
      series/                 continuity, whodunit, arc-ledger
      input/                  outlines, series bible
      output/                 manuscripts + reports
      .penny/                 per-pack runtime: locks, current-stage, tmp
    <next-series>/…
  .penny/
    current-series            ← NEW pointer to the active pack (solo default)
```

Every mutable thing a series owns lives under `packs/<slug>/`. Two series therefore
touch **disjoint file paths**; git handles disjoint paths without conflict even on the
same branch. The only shared mutable surfaces are the engine files themselves (rarely
edited mid-authoring) and the `.penny/current-series` pointer — which is why selection
must be per-session, never solely a global pointer (see Selection).

The default slug for the existing series is **`cozy-pelicans`** (renameable; nothing in
the engine hardcodes it).

## Architecture — config two-tier overlay

Resolution for any config file:

```
config_path(rel) = packs/<active>/config/<rel>   if it exists
                 = config/<rel>                   otherwise (engine default)
```

A **file-level overlay**: a pack carries only what it specializes; everything else falls
through to the engine default, so a craft fix lands once and reaches every series.

**Engine defaults (shared, improve-once):**
- `config/review-rubrics/*`
- `config/line-edit/`, `config/copy-edit/`
- `config/self-audit/`
- `config/outline-template.md`
- `config/beta-readers/beta-protocol.md` — the report schema + K-of-M consensus math,
  tied to `scripts/beta_report.py`. It references personas only generically ("the
  emitting persona's stamped DRIVER value"); it must **not** hardcode any single
  series' driver enum.

**Pack overrides (per-series):**
- `config/voice-pack/`
- `config/setting-pack/` (incl. `lexicon.yaml`)
- `config/genre-pack/`
- `config/length-profile.md`
- `config/run-config.md` (model routing + run-mode flags are per-series)
- `config/beta-readers/personas/` — the reader lenses. The **driver-value enum travels
  with the personas** (a sci-fi series defines its own personas and their driver space);
  the engine's protocol consumes whatever enum the active pack's personas declare.

Debatable-but-kept-as-default: `review-rubrics/fairplay-planting.md` and the
mystery-flavored personas are genre-specific, but a non-mystery pack simply overrides
them — this avoids the rejected third tier.

## Architecture — the resolver (heart of "no drift")

A single new module `scripts/penny_paths.py` becomes the *only* place that knows the
layout. Everything else asks it.

**Selection — `series_root()`:**
Resolve in strict order, first hit wins:
1. `--series <slug>` argument (when the caller passes one)
2. `PENNY_SERIES` environment variable
3. `.penny/current-series` pointer file (single line: the slug)
4. **Hard error** with a named predicate (no silent default — refusing to guess which
   series prevents cross-series corruption).

Validate the resolved slug exists as `packs/<slug>/` and fail loud otherwise.

**Path helpers** (all relative to the resolved pack, `REPO` anchored via
`Path(__file__).resolve().parents[1]` as today):
- `config_path(rel)` — overlay resolution (pack-then-engine) described above.
- `series_path(rel)` — `packs/<active>/series/<rel>`
- `input_path(rel)` — `packs/<active>/input/<rel>`
- `output_path(rel)` — `packs/<active>/output/<rel>`
- `penny_path(rel)` — `packs/<active>/.penny/<rel>` (per-pack runtime: locks, stage, tmp)

**CLI shim** so the markdown runbooks (which are executed by the model, not Python) can
resolve a path without hardcoding one:

```
python3 -m scripts.penny_paths resolve config voice-pack/voice-pack.md
python3 -m scripts.penny_paths active          # prints the resolved slug
```

## Engine changes — scripts to refactor

These currently hardcode `config/…`, `series/…`, `input/…`, `output/…`, or
`.penny/…` relative to the repo root and must route through `penny_paths`:

- `scripts/preflight.py` — already threads `repo_root`; adapt its path helpers to pack
  paths (locks, chapters, whodunit, run-config, lexicon, canon-core all become
  per-pack). Its five subcommands' semantics are unchanged.
- `scripts/readiness_check.py` — the widest hardcoder (voice/setting/genre/rubrics/
  personas/canon-core paths).
- `scripts/fairplay_check.py` — whodunit yaml, characters, run-config.
- `scripts/outline_check.py` — `input/book-NN/outline.md`.
- `scripts/lexicon_check.py` — lexicon.yaml (pack), canon-core.md (pack).
- `scripts/review_gate.py` — run-config; reviews dir is passed in (already relative).
- `scripts/revision_priority.py` — output reports + chapters dirs.
- `scripts/assemble_book.py` — output chapters → manuscript.
- `scripts/penny-statusline.sh` — read `current-stage` from the **active pack's**
  `.penny/`, and show the active series slug (uses the `penny_paths active` CLI or reads
  the pointer directly; must honor `PENNY_SERIES` for parallel terminals).

`scripts/penny_meta.py`, `scripts/penny_verdict.py`, `scripts/penny_text.py` are
layout-agnostic (operate on passed-in content/paths) and need no change.

## Engine changes — commands & agents

- **New `/use-series <slug>`** — writes `.penny/current-series`. Validates the pack
  exists. Prints the active series so the showrunner has confirmation.
- **New `/new-series <slug>`** — scaffolds an empty `packs/<slug>/` skeleton: minimal
  required overrides (`config/voice-pack/`, `config/setting-pack/`, `config/genre-pack/`
  stubs, a `run-config.md`), empty `series/continuity/{canon-core.md,characters/,
  locations/,threads/}`, empty `series/whodunit/`, empty `input/`, `output/`, and
  `.penny/`. It does **not** invent content — it lays down the directory contract so the
  existing planning/drafting commands have somewhere to write.
- **Existing per-chapter/book commands** (`/plan-mystery`, `/expand-outline`,
  `/draft-chapter`, `/review-chapter`, `/finalize-chapter`, `/beta-read`, and the
  Phase-6 `assemble-book` when built) gain an optional `--series` passthrough; otherwise
  they resolve via env/pointer. Their runbook *logic* is unchanged — only the paths they
  compute now come from `penny_paths`.
- **Agents** are unaffected: they already receive explicit input paths from the
  dispatching command. Blindness/isolation invariants are untouched — a pack is just a
  different set of input paths.

## Migration — one cutover, test-green

Its own phase, executed test-first. Steps:

1. `git mv` the pack-specific slice into `packs/cozy-pelicans/`:
   - config overrides: `voice-pack/`, `setting-pack/`, `genre-pack/`,
     `length-profile.md`, `run-config.md`, `beta-readers/personas/`
   - `series/` (whole), `input/` (whole), `output/` (whole)
   - runtime: `.penny/locks/`, `.penny/current-stage`, `.penny/tmp/`
2. Leave engine defaults in place at repo `config/` (rubrics, line/copy-edit,
   self-audit, outline-template, `beta-readers/beta-protocol.md`).
3. Add `scripts/penny_paths.py` + tests (resolution order, overlay fallback, missing-slug
   error, missing-pack error).
4. Refactor the scripts above to call `penny_paths`; update the status line.
5. Seed `.penny/current-series` = `cozy-pelicans`.
6. **Get the full suite (~273 tests) green.** Many tests assert literal
   `output/book-01/…` / `config/…` / `series/…` paths; they migrate to either the pack
   path or a dedicated **fixture pack** under `tests/fixtures/` so unit tests don't
   depend on the live `cozy-pelicans` content. Prefer a fixture pack for resolver and
   gate tests; use the real pack only where a test already exercised live series data.

**Risk:** the test path-surface is the largest blast radius. Mitigation: land
`penny_paths` + its own tests first (red→green in isolation), *then* migrate consumers
one script at a time, keeping the suite green at each step.

## Testing strategy

- **Resolver unit tests** (new): flag > env > pointer precedence; each source in
  isolation; overlay pack-then-engine fallback per file; unknown slug and no-selection
  both fail loud with named predicates.
- **Parallel-safety test:** two resolutions with different `PENNY_SERIES` values yield
  disjoint `output_path`/`penny_path` roots.
- **Migration regression:** existing gate/preflight/fairplay/lexicon/outline tests pass
  unchanged in behavior once repointed at the fixture pack.
- **Status line:** shows the active slug and reads the active pack's `current-stage`.

## Open questions

None blocking. Slug `cozy-pelicans` is renameable at migration time. Whether a future
non-mystery pack wants to override `fairplay-planting.md` or drop it is a per-pack
authoring choice, not an engine decision.
