# Spec — The genre-pack layer

Saved: 2026-07-08 | Status: design approved, pending spec review
Builds on: `2026-07-07-engine-plugin-series-folders-design.md` (the plugin + series-folder model this extends)

## Problem

Penny is now one engine (a Claude Code plugin) driving many series, each an ordinary folder you
`cd` into (active series = the working directory, resolved by `scripts/penny_paths.py`). But the
engine is not genre-neutral: the **cozy-mystery machinery is welded into the core** — fair-play
clue validation (`fairplay_check.py` + the fair-play inspector + `review-rubrics/fairplay-planting.md`),
the whodunit planning flow (`plan-mystery`, the whodunit yaml schema, the mystery lock), and the
"M — Mystery" story track are hardcoded steps every book runs.

The showrunner is now also writing a **drama thriller**, which has no whodunit and no fair-play.
There is no home for a *second genre* with a different planning artifact and a different validation
set. Cloning/forking the engine per genre reintroduces the drift the plugin was built to prevent.

A second, connected problem: much of the engine's pytest suite reads the **live cozy data** at the
repo root as a convenient stand-in fixture. This blocks the parked cozy-series cutover to
`~/myBooks/cozy-pelicans/` (removing the data breaks ~47 tests). The genre work resolves this: per-genre
**fixtures** decouple the tests from any live series.

## Goal

A **genre-pack layer**: genre becomes a swappable pack, shipped **inside the plugin**, that declares —
as data — which planning flow, structured artifact, validator, inspectors, gates, rubrics, and story
tracks apply. The engine core becomes genre-neutral; all checker/agent **code** stays in the engine.
Each series **names** its genre in one line. Adding or improving a genre is a plugin update — every
series of that genre benefits with zero per-series work (the "no drift" property, preserved). Cozy
behavior is byte-for-byte unchanged until the thriller genre is added.

## Non-goals

- **Not** a genre marketplace or third-party genres — the showrunner authors the genre packs.
- **No dynamic code loading.** Validator/checker code lives in the engine's `scripts/` and is
  fixture-tested; a genre manifest *names* which checkers/inspectors/commands to run. A brand-new
  genre needing a brand-new checker means adding engine code (a plugin update), not loading code
  from a pack.
- **Not** a rewrite of the per-chapter pipeline logic — only its **dispatch** becomes genre-driven.
- **Not** the thriller's full craft design. This spec sketches the thriller artifact and defers its
  detailed schema to Phase 4 (its own mini-design if needed).
- **No** new LLM judgments in the deterministic layer. Genre resolution + manifest reading are
  deterministic.

## Decisions (locked in brainstorming)

1. **Build the full genre-pack layer**, not just a flag that disables mystery gates.
2. **General planning-artifact framework:** each genre declares its own planning command, structured
   artifact, validator, and (optional) lock — not "mystery has an artifact, others don't."
3. **Validator/checker code lives in the engine; the genre manifest names which to run.** Genre packs
   are **data** (manifest + rubrics + conventions).
4. **Genre packs ship inside the plugin** under `genres/`; a series *selects* its genre. Not
   separate per-genre plugins (dependency/install overhead for a handful of genres).
5. **Config overlay becomes three-tier:** series override → genre pack → engine default.
6. **This subsumes the parked cozy cutover:** per-genre fixtures decouple the ~47 tests, after which
   the cozy data moves to `~/myBooks/cozy-pelicans/` cleanly (Phases 2–3).

## Architecture — three tiers

```
penny-engine/  (the plugin, installed once)
  scripts/        ENGINE — genre-neutral pipeline, gates, penny_paths, and ALL checker code
                    (fairplay_check.py, tension_check.py [new, P4], lexicon_check.py, …)
  agents/         ALL inspector/agent code (inspector-fairplay, inspector-structure/tension,
                    inspector-voice, inspector-continuity, inspector-ai-prose, drafter, editors, …)
  commands/       all commands (plan-book [new], plan-mystery, plan-thriller [new P4], review-chapter, …)
  config/         GENRE-NEUTRAL DEFAULTS — review-rubrics (continuity, voice, structure-tension,
                    ai-prose), line/copy-edit, self-audit, outline-template, beta-protocol
  genres/         ← NEW: the genre packs (DATA only), shipped with the engine
    cozy-mystery/
      genre.yaml            the manifest (see below)
      conventions.md        genre conventions doc
      review-rubrics/
        fairplay-planting.md   genre-specific rubric (overlaid on the neutral defaults)
    thriller/               (authored in Phase 4)
      genre.yaml
      conventions.md
      review-rubrics/
        escalation.md
        twist-earned.md

~/myBooks/cozy-pelicans/   (a series folder = cwd)
  series.yaml    →  genre: cozy-mystery
  config/ series/ input/ output/ .penny/

~/myBooks/<thriller>/
  series.yaml    →  genre: thriller
  config/ series/ input/ output/ .penny/
```

- **Engine (plugin):** fixed pipeline + all code + neutral defaults. Never per-genre.
- **Genre pack (`plugin/genres/<genre>/`):** pure data — a `genre.yaml` manifest, a conventions doc,
  and any config files (chiefly rubrics) the genre specializes, laid out to **mirror the `config/`
  tree** so the overlay resolves them uniformly. Shared across every series of that genre.
- **Series (cwd folder):** the series' data + config overrides + a one-line `series.yaml` naming its
  genre.

## Architecture — the manifest (the whole mechanism)

`genres/<genre>/genre.yaml` declares every genre difference as data. Example — cozy-mystery
(reproduces today's behavior exactly):

```yaml
genre: cozy-mystery                     # must equal the directory name
conventions: conventions.md
planning:
  command: plan-mystery                 # planning runbook (must exist in commands/)
  artifact: series/whodunit/book-{NN}.yaml   # series-relative; {NN} = zero-padded book number
  validator: fairplay                   # engine checker validating the artifact (or null)
  lock: mystery                         # required lock before drafting (or null)
inspectors: [continuity, fairplay, structure, voice, ai-prose]   # blind inspectors review-chapter fans out
gates:      [fairplay, lexicon]         # deterministic gates preflight enforces
rubrics:    [review-rubrics/fairplay-planting.md]   # genre rubric files (resolved via the overlay)
tracks:     [M, P, R, B]                # story-track letters (M = Mystery)
```

Thriller (Phase 4):

```yaml
genre: thriller
conventions: conventions.md
planning:
  command: plan-thriller
  artifact: series/structure/book-{NN}.yaml    # thriller's structured artifact (threat / escalation
                                               # beats / reveal ladder / POV-timeline) — schema in P4
  validator: tension                    # engine checker for the thriller artifact
  lock: null                            # (or a 'structure' lock if wanted)
inspectors: [continuity, structure, voice, ai-prose, tension]
gates:      [tension, lexicon]
rubrics:    [review-rubrics/escalation.md, review-rubrics/twist-earned.md]
tracks:     [P, T, R, S]                # Plot / Threat / Relationship / Stakes
```

**Every field names a thing that lives in the engine** (a command, a checker, an inspector, a gate)
or is a data file resolved through the overlay (a rubric). The manifest is the single source of
"what this genre does"; the engine holds the "how."

Note on `rubrics:` — it is a **declaration**, not a separate dispatch path. An inspector loads its
rubric through `config_path` (which resolves series → genre → default), so selecting an inspector
already pulls in that inspector's rubric from the genre pack. The `rubrics:` list exists so the
manifest-conformance test can verify the pack actually **ships** the genre-specific rubric files it
relies on (and to document them); it does not re-route resolution.

## Architecture — genre resolution (`penny_paths` additions)

- **`genre(root=None) -> str`** — reads `<series-root>/series.yaml` → the `genre` slug. Hard error
  with a named predicate if `series.yaml` is missing or names a genre absent from
  `plugin_root()/genres/<slug>/`.
- **`genre_dir(g=None, root=None) -> Path`** — `plugin_root()/genres/<g or genre()>`.
- **`genre_manifest(root=None) -> dict`** — loads and schema-validates `genre_dir()/genre.yaml`.
- **`config_path(rel, root=None)` — extended to three tiers:**
  ```
  <series-root>/config/<rel>          if it exists   (series override)
  else genre_dir()/<rel>              if it exists   (genre pack; e.g. review-rubrics/fairplay-planting.md)
  else plugin_root()/config/<rel>                    (engine default)
  ```
  The middle tier is why genre packs mirror the `config/` layout — a genre rubric at
  `genres/cozy-mystery/review-rubrics/fairplay-planting.md` resolves without special-casing.
- Data-path helpers (`series_path`/`input_path`/`output_path`/`penny_path`) are unchanged — genre
  affects config resolution and dispatch, not where a series' data lives.

## Architecture — genre-aware command dispatch (one set of commands, data-driven)

- **`/plan-book NN`** (new, thin) — reads `planning.command` from the manifest and delegates to that
  runbook (`plan-mystery` / `plan-thriller`), passing where the artifact goes (`planning.artifact`
  with `{NN}` filled) and which `validator`/`lock` apply. The genre-named planning runbooks still
  exist; `/plan-book` is the genre-neutral front door.
- **`/review-chapter`** — dispatches exactly the manifest's `inspectors:` list. Every inspector agent
  exists in the engine; the manifest **selects** (cozy fans out `fairplay`; thriller fans out
  `tension` instead). No inspector-selection logic is hardcoded.
- **`preflight`** — enforces the manifest's `gates:` and `lock:` (cozy: the `mystery` lock + the
  `fairplay` gate; thriller: the `tension` gate, no lock). `preflight`'s subcommand *mechanics* are
  unchanged; *which* gates/lock it requires now comes from the manifest.
- The `planning.validator` (`fairplay`/`tension`) is the engine checker run against
  `planning.artifact`.

Net: the per-chapter/book commands keep genre-neutral logic; behavior is driven by the active
series' genre manifest.

## Migration — what moves, what stays

- **Into `genres/cozy-mystery/`:** `review-rubrics/fairplay-planting.md`, the cozy conventions doc,
  and `genre.yaml` (which names `plan-mystery`, the whodunit artifact, the `fairplay` validator, the
  `mystery` lock, the M-track).
- **Stays in the engine:** all *code* — `fairplay_check.py`, the `inspector-fairplay` agent, the
  `plan-mystery` runbook — plus the genre-neutral rubrics (continuity, voice, structure-tension,
  ai-prose) and every other neutral default.
- **Stays as series data, unchanged location:** the cozy series' `series/whodunit/book-01.yaml` (it
  is *this series'* content). The series gains a one-line `series.yaml: genre: cozy-mystery`.
- **The cozy cutover folds in:** once Phase 2 repoints the tests at fixtures, Phase 3 runs the parked
  cutover — `series/`, `input/`, `output/`, config overrides, `.penny/` move to
  `~/myBooks/cozy-pelicans/` (fresh repo) and are `git rm`'d from the engine; engine defaults stay.
  This spec supersedes the standalone "Task 15 cutover": the cutover happens *inside* Phase 3, after
  the tests are decoupled.

## Testing strategy

- **Fixture series per genre** under `tests/fixtures/` — a minimal cozy series (with `series.yaml`,
  a small whodunit, lexicon, canon-core) and a minimal thriller series (with its artifact) — so
  every engine checker is unit-tested against a fixture, never the live cozy data. This is what
  decouples the ~47 currently data-dependent tests.
- **Manifest-conformance test:** every shipped `genre.yaml` (a) validates against the manifest schema
  and (b) every name it references — `planning.command`, `planning.validator`, each `inspectors:`
  entry, each `gates:` entry, each `rubrics:` file — actually **exists** in the engine/genre pack. A
  genre pointing at a missing checker fails loud.
- **Genre resolution + three-tier overlay tests:** `genre()` reads `series.yaml`; unknown/missing
  genre fails loud; `config_path` resolves series → genre → default in that precedence.
- **Behavior preservation:** after Phases 1–3, the cozy series produces identical gate/inspector
  behavior to today (the cozy manifest reproduces the hardcoded set). A regression test pins this.

## Phasing (drives the implementation plan)

- **Phase 1 — resolver + manifest, no behavior change.** Add `genre()`/`genre_dir()`/
  `genre_manifest()` + the three-tier `config_path` + the manifest schema to `penny_paths`. Author
  `genres/cozy-mystery/genre.yaml` so it reproduces today's exact behavior. Engine unchanged in
  observable behavior; suite green.
- **Phase 2 — genre-aware dispatch + fixtures.** Make `/review-chapter` and `preflight` read the
  manifest (cozy still identical). Add `/plan-book`. Build the fixture cozy series and repoint the
  ~47 data-dependent tests at it (fixes the cutover decoupling). Suite green with no live series
  required.
- **Phase 3 — extract cozy pack + run the cutover.** Move `fairplay-planting.md` + cozy conventions
  into `genres/cozy-mystery/`; add `series.yaml` to the cozy series; run the cozy-series cutover to
  `~/myBooks/cozy-pelicans/`. Suite green against fixtures.
- **Phase 4 — the thriller genre.** Author `genres/thriller/` (manifest, conventions, rubrics),
  `plan-thriller`, the thriller artifact schema, and the `tension` checker (engine code +
  fixture-tested). Scaffold a thriller series folder. This is the first genre added purely by
  authoring a pack + one new checker.

Each phase leaves the full suite green; cozy behavior is unchanged until Phase 4 introduces the new
genre.

## Open questions

- **The thriller artifact schema** (threat / escalation beats / reveal ladder / POV-timeline) is
  sketched, not specified — Phase 4 defines it (possibly its own short design). Not blocking earlier
  phases.
- **`/plan-book` vs the genre-named commands:** the delegating `/plan-book` is the front door; whether
  `plan-mystery`/`plan-thriller` remain directly invocable or become internal is a Phase-2 detail.
- **Thriller lock:** whether the thriller wants a `structure` lock (freeze the beat sheet before
  drafting, mirroring the mystery lock) or no lock — a Phase-4 authoring choice, not an engine
  decision.
