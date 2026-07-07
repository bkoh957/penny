# Spec — One engine plugin, many series folders

Saved: 2026-07-07 | Status: design approved, pending spec review
Supersedes: `2026-07-03-multi-series-packs-design.md` (the `packs/` resolver approach)

## Problem

Penny's founding rule holds: the engine (`scripts/`, `.claude/`) is genre/location-agnostic,
and everything project-specific lives in swappable `config/`, `series/`, `input/`. But the
layout assumes **one series == the repo root**, so there is no home for a *second* series,
and the engine and the one existing series are tangled in a single repo.

The showrunner wants to start additional series with a workflow that matches how they already
work (`~/myTools`, `~/myProjects` are plain container folders holding independent repos). The
priority remains **"no engine drift"**: improve one engine, have every series benefit with zero
per-series work.

The previously approved `packs/` design met the drift goal but paid for it with a selection
apparatus — a `--series` flag, a `PENNY_SERIES` env var, a `.penny/current-series` pointer, and
a precedence resolver — plus a `packs/<slug>/` nesting inside one repo. That is more machinery
than the workflow needs.

## Goal

One engine drives many series. The engine is installed **once** as a Claude Code **plugin**;
each series is an **ordinary folder** (its own git repo) that you `cd` into and run Claude Code
in. The active series is simply the working directory — no flag, no pointer, no resolver.
Engine improvements propagate to every series via a plugin update. Two series build in parallel
because they are two directories. Migrating the existing cozy series is a single, test-green
cutover.

## Non-goals

- **Not** a genre/plugin marketplace for third parties or dynamic pack discovery — the engine
  is one private plugin the showrunner authors and updates.
- **Not** a third "genre" config tier (two tiers only: engine default + series override).
- **Not** Phase 6. Per-book assembly / final read / revision-priority is deferred and built
  series-aware *after* this refactor.
- **Not** a rewrite of the per-chapter pipeline logic — only its **pathing** changes.
- **No** new LLM judgments. This is a deterministic layout + path-anchoring change.

## Decisions (locked in brainstorming)

1. **Strategy: engine-as-plugin + series-as-folders.** Not clone-per-repo, not `packs/`
   nesting, not engine-as-submodule. Chosen because it delivers "no drift" using Claude Code's
   native plugin mechanism while making selection disappear.
2. **Active series = the current working directory.** Resolved by a marker, not a flag/pointer.
   The whole selection layer from the `packs/` spec (`--series`, `PENNY_SERIES`,
   `.penny/current-series`, `/use-series`) is **removed**.
3. **Two roots.** *Plugin root* = the engine (code + config defaults), referenced by its own
   location. *Series root* = the folder you launched in (data), found by walking up to a marker.
   Neither knows the other's internals.
4. **Config = two-tier overlay.** Series-local `config/<rel>` if present, else the plugin's
   default. A craft fix to a default lands once and reaches every series.
5. **Plugin enabled at the user level** (global availability), so `cd <new folder> && claude`
   has the commands immediately — no per-folder setup, no chicken-and-egg. (Per-folder version
   pinning remains possible but is not the default.)
6. **This repo becomes the engine plugin** (keeps its history + ~273 tests). The cozy series
   data moves to `~/myBooks/cozy-pelicans/` as a **fresh git repo**; the story's prior history
   stays archived in the engine repo's past.
7. **`~/myBooks/` is a plain container folder**; each series under it is its own git repo.
8. **Sequencing:** do this refactor now; Phase 6 later.

## Architecture — the two roots

```
~/myTools/penny/            ← THIS REPO = the ENGINE (a Claude Code plugin / marketplace)
    scripts/                ENGINE (fixed) — path anchoring changes to series-root
    .claude/                ENGINE (commands, agents, skills)
    config/                 ENGINE CONFIG DEFAULTS (craft-general, improve-once)
    tests/                  ENGINE tests (run against a fixture series)
    <plugin manifest>       registers this repo as an installable plugin

~/myBooks/                  ← plain container folder (like ~/myTools, ~/myProjects); NOT a repo
    cozy-pelicans/          ← a SERIES = its own git repo. `cd` here, run `claude`.
        .penny/             SERIES-ROOT MARKER + runtime (locks, current-stage, tmp)
        config/             OVERRIDES only (voice/setting/genre/run-config/length/personas)
        series/             continuity, whodunit, bibles
        input/              outlines, series reference
        output/             manuscripts + reports
    <next-series>/          ← new series = new folder + git repo here
```

Everything a series owns lives under its own folder, so two series touch **disjoint paths** and
never collide. The only shared surface is the engine plugin itself (rarely edited mid-authoring,
and updated deliberately).

## Architecture — finding the series root

A series folder is marked by its **`.penny/` directory** (created by `/new-series`). Any engine
script resolves the series root by walking **up from the current working directory** to the
nearest ancestor containing `.penny/`, and fails loud with a named predicate if none is found
(so a stray invocation can never write into the wrong place). This lets commands run from the
series root *or* any subfolder. The engine repo is never launched as an authoring working
directory; its own `.penny/` (if any) is test runtime, not a series.

## Architecture — config two-tier overlay

Resolution for any config file:

```
config_path(rel) = <series-root>/config/<rel>   if it exists
                 = <plugin-root>/config/<rel>    otherwise (engine default)
```

A **file-level overlay**: a series carries only what it specializes; everything else falls
through to the engine default.

**Engine defaults (shared, improve-once), stay in the plugin's `config/`:**
- `review-rubrics/*`
- `line-edit/`, `copy-edit/`
- `self-audit/`
- `outline-template.md`
- `beta-readers/beta-protocol.md` — the report schema + K-of-M consensus math, tied to
  `scripts/beta_report.py`. References personas only generically ("the emitting persona's
  stamped DRIVER value"); must **not** hardcode any single series' driver enum.

**Series overrides (per-series), move into `<series>/config/`:**
- `voice-pack/`
- `setting-pack/` (incl. `lexicon.yaml`)
- `genre-pack/`
- `length-profile.md`
- `run-config.md` (model routing + run-mode flags are per-series)
- `beta-readers/personas/` — the reader lenses; the **driver-value enum travels with the
  personas**, and the engine's protocol consumes whatever enum the active series' personas
  declare.

Debatable-but-kept-as-default: `review-rubrics/fairplay-planting.md` and the mystery-flavored
personas are genre-specific, but a non-mystery series simply overrides them — which avoids the
rejected third tier.

## Architecture — the plugin

The engine repo doubles as a **plugin marketplace**: a manifest plus the existing
`.claude/commands`, `.claude/agents`, skills, and bundled `scripts/`. The showrunner adds the
marketplace and installs the `penny` plugin **once, at the user level**, so its commands and
skills are available in every directory.

- **Engine code paths** (running the checkers, reading config defaults) resolve against the
  **plugin root** — the plugin's on-disk location, exposed to command runbooks and scripts so
  nothing is hardcoded to a machine path.
- **Series data paths** resolve against the **series root** (cwd marker) as above.
- **Upgrades:** push to the engine repo, update the plugin; every series with it enabled picks
  up the new engine next run. No copying, no per-series edits — the "no drift" property,
  delivered by Claude Code's own mechanism instead of a bespoke resolver.

> Confirmation follow-up (planning phase, not a design hole): the exact plugin manifest schema,
> the marketplace registration, and the `${PLUGIN_ROOT}`-style reference used by command
> runbooks will be pinned against the current Claude Code plugin docs (via the built-in
> claude-code guide) before implementation. The design does not depend on any specific field
> name — only on the documented capabilities: a plugin bundles commands/agents/skills/scripts,
> is installed once, referenced by a stable root, and updated centrally.

## Engine changes — scripts

These currently anchor paths to the engine's own location
(`Path(__file__).resolve().parents[1]`). They change so that **data** paths anchor to the
**series root** (the `.penny` marker) while **engine/config-default** paths anchor to the
**plugin root**:

- `scripts/penny_paths.py` (**new**) — the single module that knows both roots: `series_root()`
  (walk-up marker resolution + loud failure), `plugin_root()`, and the helpers
  `config_path()` (overlay), `series_path()`, `input_path()`, `output_path()`, `penny_path()`.
  Also a CLI shim so markdown runbooks can resolve paths without hardcoding.
- `scripts/preflight.py` — already threads `repo_root`; repoint its helpers (locks, chapters,
  whodunit, run-config, lexicon, canon-core) to series/plugin paths. Its five subcommands'
  semantics are unchanged.
- `scripts/readiness_check.py` — the widest hardcoder (voice/setting/genre/rubrics/personas/
  canon-core).
- `scripts/fairplay_check.py` — whodunit yaml, characters, run-config.
- `scripts/outline_check.py` — `input/book-NN/outline.md`.
- `scripts/lexicon_check.py` — lexicon.yaml (series), canon-core.md (series).
- `scripts/review_gate.py` — run-config; reviews dir is passed in (already relative).
- `scripts/revision_priority.py` — output reports + chapters dirs.
- `scripts/assemble_book.py` — output chapters → manuscript.
- `scripts/penny-statusline.sh` — read `current-stage` from the **series root's** `.penny/` and
  show the active series (the series folder name); resolve via `penny_paths` / the CLI shim.

`scripts/penny_meta.py`, `scripts/penny_verdict.py`, `scripts/penny_text.py` operate on
passed-in content/paths and need no change.

The list above is representative, not exhaustive: the implementation plan performs a **full
sweep** of `scripts/` for any remaining hardcoded `config/…` / `series/…` / `input/…` /
`output/…` / `.penny/…` path (e.g. `canon_core_review.py`, `ledger_markers.py`,
`reset_reviews.py`, `voice_drift.py`) and repoints each through `penny_paths` under the same
"data → series root, defaults → plugin root" rule.

## Engine changes — commands & agents

- **New `/new-series <name>`** — scaffolds `~/myBooks/<name>/`: the `.penny/` marker, empty
  `series/continuity/{canon-core.md,characters/,locations/,threads/}`, empty `series/whodunit/`,
  minimal `config/` override stubs (`voice-pack/`, `setting-pack/`, `genre-pack/`,
  `run-config.md`), empty `input/`, `output/`, and `git init`. It lays down the directory
  contract only — it invents no content. (The `~/myBooks` root is a configurable default.)
- **`/use-series` and the entire selection apparatus — deleted.** You switch series by `cd`.
- **Existing commands** (`/plan-mystery`, `/expand-outline`, `/draft-chapter`,
  `/review-chapter`, `/finalize-chapter`, `/beta-read`, and Phase-6 `assemble-book` when built)
  are unchanged in logic; the paths they compute now come from `penny_paths` resolving against
  the series root.
- **Agents** are unaffected: they already receive explicit input paths from the dispatching
  command. Blindness/isolation invariants are untouched — a series is just a different set of
  input paths.

## Migration — one cutover, test-green

Its own phase, executed test-first, in this order to keep the blast radius contained:

1. Add `scripts/penny_paths.py` (marker walk-up, overlay fallback, plugin/series roots) **+ its
   own tests** in isolation (red→green): resolution from a nested subdir, overlay pack-then-
   default fallback per file, no-marker error, and two disjoint series roots resolving to
   disjoint data paths (parallel-safety).
2. Add the plugin manifest so this repo is installable; document enabling it at the user level.
3. Refactor the scripts above to call `penny_paths`, **one script at a time**, keeping the full
   suite green at each step. Tests run against a **fixture series** under `tests/fixtures/` so
   unit tests don't depend on live story content; use real content only where a test already
   exercised live series data.
4. Update the status line to read the series root's `current-stage` and show the series name.
5. `git mv` the cozy series data out of this repo into `~/myBooks/cozy-pelicans/`: `series/`,
   `input/`, `output/`, the config **overrides** (`voice-pack/`, `setting-pack/`, `genre-pack/`,
   `length-profile.md`, `run-config.md`, `beta-readers/personas/`), and `.penny/` runtime.
   Leave the engine **defaults** in this repo's `config/`. Then `git init` the cozy folder as a
   **fresh repo** (prior story history remains archived in this engine repo's past).
6. **Get the full suite (~273 tests) green** against the fixture series.

**Risk:** the test path-surface is the largest blast radius (many tests assert literal
`output/book-01/…` / `config/…` / `series/…`). Mitigation: land `penny_paths` + its own tests
first, then migrate consumers one at a time keeping the suite green; do the `git mv` only after
the resolver and its consumers are green.

## Testing strategy

- **Resolver unit tests** (new): series-root walk-up from the root and from a nested subdir;
  overlay series-then-default fallback per file; missing marker fails loud with a named
  predicate; plugin-root resolution independent of cwd.
- **Parallel-safety test:** two series roots yield disjoint `output_path`/`penny_path` roots.
- **Migration regression:** existing gate/preflight/fairplay/lexicon/outline tests pass
  unchanged in behavior once repointed at the fixture series.
- **Status line:** shows the active series name and reads that series' `current-stage`.

## Open questions

None blocking. Series folder names are the series identity (renameable). Whether a future
non-mystery series overrides or drops `fairplay-planting.md` is a per-series authoring choice,
not an engine decision. The exact plugin manifest fields are a confirmation step in planning,
not a design dependency (see the plugin section).
