# Spec — The thriller genre pack (Phase 4)

Saved: 2026-07-08 | Status: **draft for review** (authored autonomously while the showrunner is offsite)
Builds on: `2026-07-08-genre-pack-layer-design.md` (the genre-pack framework this fills in) and
`2026-07-07-engine-plugin-series-folders-design.md` (the plugin + series-folder model).

> **Review note.** This spec was drafted without the usual one-question-at-a-time dialogue because the
> showrunner asked to "prep it" while offsite. Every judgment call I made is flagged inline as
> **[DECISION]** with the alternatives, so review is a matter of confirming or redirecting each, not
> reconstructing my reasoning. Nothing here is implemented yet — the approval gate is intact.

## Problem

The genre-pack framework (Phases 1–3) made genre a swappable pack and cut the cozy series out to
`~/myBooks/cozy-pelicans/`. But **only two consumers are actually manifest-driven today**:
`/review-chapter` (reads `inspectors:`) and `/plan-book` (reads `planning.command`). The
deterministic pre-flight layer — `scripts/preflight.py` — is still **genre-blind and welded to the
mystery**:

- `cmd_draft` hardcodes the whodunit ledger path (`series/whodunit/book-NN.yaml`), the `mystery`
  lock, and the error "run `/plan-mystery`".
- `cmd_lock_mystery` runs fair-play + lexicon and mints `book-NN.mystery.lock` — a mystery-specific
  subcommand, not a manifest-driven one.
- The manifest's `gates:` and `planning.{artifact,validator,lock}` fields are **declared but never
  read** by preflight.

So a `genre: thriller` series cannot pass the draft gate (it has no whodunit ledger and no mystery
lock), and there is no planning flow, structured artifact, validator, or inspector for a thriller.

The showrunner is writing a **drama thriller** — no whodunit, no fair-play. Phase 4 adds the thriller
as the *first genre authored purely as a pack + one new checker*, and in doing so finishes the job
Phases 1–3 started: making the pre-flight layer manifest-driven so the engine is genuinely
genre-neutral.

## Goal

Author `genres/thriller/` and the engine pieces it names, so that a `genre: thriller` series plans,
validates, locks, drafts, and reviews end-to-end with **zero mystery machinery** — and cozy behavior
stays byte-for-byte unchanged. Concretely:

1. A **thriller planning artifact** schema (`series/structure/book-{NN}.yaml`) — the beat sheet:
   central dramatic question, escalation ladder, reveal/twist ladder, tentpole beats, threat
   entities.
2. A deterministic **`tension` checker** (`scripts/tension_check.py`) validating that artifact —
   mirroring `fairplay_check.py`'s "audit the plan, not the prose" contract, emitting `BLOCKING:`
   lines for structural failures.
3. **Manifest-driven pre-flight** — generalize `preflight` so `draft` and a new genre-neutral
   `lock` subcommand read the active genre's `planning.{artifact,validator,lock}` and `gates:`
   instead of hardcoding the mystery. Cozy keeps identical behavior through its manifest.
4. A `plan-thriller` command, an `inspector-tension` agent (blind, prose-level), the
   `genres/thriller/` pack (manifest, conventions, two rubrics), a thriller **fixture series**, and
   tests.

## Non-goals

- **Not** the thriller's actual story content — this ships the *engine + pack*, plus a minimal
  fixture and a scaffolded empty series, not a plotted book.
- **No new LLM judgment in the deterministic layer.** `tension_check.py` enforces objective
  structural invariants only; all taste (does this scene *feel* tense?) is the blind
  `inspector-tension`'s job — exactly the fair-play checker/inspector split.
- **No** rewrite of the per-chapter pipeline; only preflight's genre-blind spots are generalized.
- **Not** multi-POV timeline verification math (deferred — see Open questions). The artifact carries
  an optional POV field the inspector can use, but the deterministic checker does not cross-validate
  timelines in Phase 4.
- **No** third-party genres — the showrunner authors packs.

## The thriller artifact — `series/structure/book-{NN}.yaml`

A drama thriller's structural promise is **escalation that pays off**: stakes rise without sagging,
and every twist is *earned* (planted before it lands). The artifact encodes exactly what a
deterministic checker can audit for that promise — the thriller analogue of the whodunit ledger.

```yaml
book: 01
total_chapters: 32
# The single dramatic question the book answers (prose, not validated beyond "present & non-empty").
central_question: |
  Will Dana expose the trafficking ring inside her own department before it buries her —
  and what will be left of her when she does?
protagonist: dana-reyes
antagonist: victor-malley               # the human threat behind the pressure (id resolves to an entity)
# Tentpole beats — chapter numbers, must be strictly ordered within 1..total_chapters:
opening_disturbance_chapter: 1          # the inciting break in the ordinary world
midpoint_chapter: 16                    # tentpole: false victory / false defeat, threat escalates
all_is_lost_chapter: 26                 # lowest point; protagonist stripped of options
climax_chapter: 30                      # highest stakes; the confrontation
# Escalation ladder — ordered stakes beats. stakes_level is an integer that must be
# NON-DECREASING from opening to climax (a drop before the climax is a sag = BLOCKING).
escalation_ladder:
  - { id: esc-warning,   chapter: 3,  stakes_level: 1, beat: "first anonymous warning" }
  - { id: esc-personal,  chapter: 9,  stakes_level: 2, beat: "threat turns personal — her sister" }
  - { id: esc-exposure,  chapter: 16, stakes_level: 3, beat: "midpoint: partial exposure, retaliation" }
  - { id: esc-betrayal,  chapter: 22, stakes_level: 4, beat: "ally revealed complicit" }
  - { id: esc-cornered,  chapter: 26, stakes_level: 5, beat: "all is lost: framed, isolated" }
  - { id: esc-confront,  chapter: 30, stakes_level: 6, beat: "climax: direct confrontation" }
# Reveal/twist ladder — each twist must be PLANTED before it PAYS OFF (plant < payoff),
# the thriller analogue of "necessary clue planted before the reveal". earned: true means
# the checker BLOCKS if plant >= payoff; earned: false is an author-acknowledged surprise
# (evidence-only note, never blocks) — the escape hatch, mirroring red_herrings.must_not_cheat.
reveal_ladder:
  - { id: tw-mole,     plant_chapter: 8,  payoff_chapter: 22, earned: true }
  - { id: tw-sister,   plant_chapter: 5,  payoff_chapter: 26, earned: true }
  - { id: tw-frame,    plant_chapter: 19, payoff_chapter: 26, earned: true }
# Optional. If present, each entry names a POV character; used by the inspector, NOT
# cross-validated deterministically in Phase 4.
pov_timeline:
  - { chapter: 1,  pov: dana-reyes }
  - { chapter: 2,  pov: victor-malley }
```

**[DECISION] Artifact rigor — recommend "structural parity with fair-play" (option A).**
- **A (recommended):** the artifact encodes only what a deterministic checker can honestly audit —
  tentpole ordering, a monotonic escalation ladder (sag detection), and a plant-before-payoff twist
  ladder, plus entity resolution. Maximum reuse of the proven fair-play pattern; the thriller's
  signature failure (sagging tension) becomes a hard, checkable invariant.
- **B (minimal):** only well-formedness + twist-planted-before-payoff + entity resolution; the sag
  goes unchecked, leaning entirely on the inspector. Less engine value.
- **C (rich):** add scene-level tension scoring and multi-POV timeline consistency. More power, but
  risks smuggling taste into the deterministic layer and demands much heavier artifact authoring.

The rest of this spec assumes **A**.

## The `tension` checker — `scripts/tension_check.py`

Mirrors `fairplay_check.py` exactly in shape and contract (same module conventions: the `sys.path`
shim, `check_tension(artifact_path, *, repo_root=None) -> {"blocking", "notes", "metrics"}`, a
`main()` that writes a `deterministic-checker` verdict via `penny_verdict.write_verdict`). It audits
the **plan's** structural soundness, never the prose. Deterministic invariants:

1. **Well-formed first** (stop on failure, one fault one line): required fields
   `book, total_chapters, central_question, protagonist, antagonist, opening_disturbance_chapter,
   midpoint_chapter, all_is_lost_chapter, climax_chapter`; `total_chapters` an int in 1..10000;
   each tentpole an int in `1..total_chapters`.
2. **Tentpole ordering (BLOCKING):**
   `opening_disturbance_chapter < midpoint_chapter < all_is_lost_chapter < climax_chapter <= total_chapters`.
3. **Escalation monotonic — sag guard (BLOCKING):** sort `escalation_ladder` by `chapter`; every
   `stakes_level` must be an int and **non-decreasing**; the last beat's chapter must be
   `>= midpoint_chapter` (escalation must run into the back half). A `stakes_level` that drops as the
   chapter advances is the "sag" → BLOCKING with the offending pair.
4. **Earned twists (BLOCKING):** for each `reveal_ladder` entry with `earned: true` (default),
   `plant_chapter` and `payoff_chapter` must be ints and `plant_chapter < payoff_chapter`. `earned:
   false` emits an evidence-only note (never blocks) — the acknowledged-surprise escape hatch.
5. **Escalation-gap note (evidence-only) [DECISION]:** if the largest gap between consecutive
   escalation-beat chapters exceeds `tension_max_gap` (read from `run-config.md`, **default 8** when
   the key is absent), emit a **note** — not a block. Rationale: a long flat stretch is a smell, not
   a provable defect, so it informs the inspector rather than hard-failing the plan. (Alternative:
   make it BLOCKING — rejected as too blunt for a soft signal.)
6. **Entity resolution (BLOCKING):** `protagonist`, `antagonist`, and every `pov_timeline[].pov`
   id must resolve to a character entity (`series/characters/<id>.static.md` **or**
   `series/continuity/characters/<id>.md`) — presence only, never identity fit. Reuses fair-play's
   `_resolves` logic (candidate for extraction to a shared helper — see Migration).

**Lazy defaults from the start:** unlike `fairplay_check.py`/`lexicon_check.py` (whose argparse
`default=str(default_run_config())` eagerly resolves `series_root()` — the footgun fixed for lexicon
in commit `341ed46`), `tension_check.py` resolves its `--run-config` default **after** parsing
(`args.run_config or default_run_config()`), so the checker never requires a series root when given
explicit paths. **[DECISION]** I recommend also back-fixing `fairplay_check.py` the same way in this
phase (one-line parity fix + a locking test) so the two checkers match; flag if you'd rather keep
that out of Phase 4's scope.

## Manifest-driven pre-flight (the engine generalization)

This is the part that turns the manifest's declared-but-unread fields into behavior, and the only
place cozy code changes (behavior preserved through cozy's manifest).

- **`preflight draft N CH`** — replace the hardcoded whodunit-ledger + mystery-lock checks with
  manifest reads: resolve `planning.artifact` (`{NN}` filled) and require it present + non-empty;
  if `planning.lock` is non-null, require `.penny/locks/book-NN.<lock>.lock`. Cozy's manifest
  (`artifact: series/whodunit/book-{NN}.yaml`, `lock: mystery`) reproduces today's checks exactly;
  thriller's (`artifact: series/structure/book-{NN}.yaml`, `lock: structure`) checks its own artifact
  and lock. The error message names `planning.command` ("run `/plan-thriller`") from the manifest.
- **`preflight lock N`** (new, genre-neutral) — the general lock-minting gate:
  1. run the manifest's `planning.validator` (`fairplay`/`tension`) against `planning.artifact`; any
     blocking → refuse, lock NOT written;
  2. run each `gates:` entry **other than the validator itself** in its `--validate` mode (cozy:
     `gates: [fairplay, lexicon]` minus validator `fairplay` → `lexicon --validate`; thriller:
     `[tension, lexicon]` minus `tension` → `lexicon --validate`). This is why the validator commonly
     appears first in `gates:` — it is run once, in step 1, not twice;
  3. if all pass and `planning.lock` is non-null, mint `book-NN.<lock>.lock` (the LAST write — the
     out-of-band certificate rule holds).
  `lock-mystery` becomes a thin alias that calls `lock N` (kept so existing cozy runbooks/tests keep
  working), or is retired in favor of `/plan-book`'s delegation — **[DECISION]** recommend keeping
  `lock-mystery` as a compatibility alias for one phase to avoid churning the cozy runbooks, then
  removing it in a later cleanup.
- **`preflight assemble/finalize/clear-dev/approve-book`** — unchanged; they are already
  genre-neutral (cross-model routing, gate PASS, dev-clearance, book approval).

**[DECISION] Thriller lock = yes, a `structure` lock.** Freezing the beat sheet before drafting
mirrors the mystery lock's discipline (validate, then lock; re-planning = delete lock, edit yaml,
re-lock). Alternative: `lock: null` (no freeze) — rejected, because the escalation ladder is exactly
the thing that must not drift mid-draft, and parity keeps the pipeline uniform. (Drafter *blindness*
matters less than in a whodunit — a thriller has no single hidden solution — so the lock is about
freezing structure, not concealment.)

## The pack — `genres/thriller/`

```
genres/thriller/
  genre.yaml
  conventions.md
  review-rubrics/
    escalation.md        # rubric for the tension inspector: does stakes actually rise here?
    twist-earned.md      # rubric: are reveals set up, or do they cheat?
```

`genre.yaml` (as sketched in the framework spec, now committed):

```yaml
genre: thriller
conventions: conventions.md
planning:
  command: plan-thriller
  artifact: series/structure/book-{NN}.yaml
  validator: tension
  lock: structure
inspectors: [continuity, structure, voice, ai-prose, tension]
gates:      [tension, lexicon]
rubrics:    [review-rubrics/escalation.md, review-rubrics/twist-earned.md]
tracks:     [P, T, R, S]     # Plot / Threat / Relationship / Stakes
```

Note the deliberate **name reuse**: `tension` is both a blind prose inspector (`inspector-tension`,
in `inspectors:`) and the deterministic artifact validator/gate (`tension_check.py`, in `validator:`
and `gates:`) — exactly as `fairplay` is both inspector and ledger checker in cozy. The
manifest-conformance test already resolves `validator` → `scripts/<v>_check.py` and inspector →
`agents/inspector-<n>.md`, so both must exist.

`conventions.md` documents drama-thriller conventions (escalation, dramatic irony, the
try/fail cycle, earned twists, chapter-end hooks) — the drafter/expander read it the way cozy reads
its conventions. `escalation.md` / `twist-earned.md` are the genre rubrics the `inspector-tension`
loads via the three-tier overlay.

## New agent — `agents/inspector-tension.md`

A blind, prose-level inspector (same contract as `inspector-fairplay`): receives `{chapter text, one
rubric, ledger slice}`, emits a `penny-verdict/1` with a score and any `^BLOCKING:` lines. It reads
the `escalation.md` + `twist-earned.md` rubrics (via overlay) and judges whether the chapter's stakes
genuinely rise and whether setups/payoffs land — the taste the deterministic checker deliberately
refuses to judge. Never sees the artifact's "answer" beyond its ledger slice, preserving the blind
convention.

## New command — `commands/plan-thriller.md`

The thriller planning runbook `/plan-book` delegates to (mirroring `plan-mystery`): it guides
authoring `series/structure/book-{NN}.yaml`, then runs `preflight lock N` (validator + gates → mint
the `structure` lock). Genre-neutral `/plan-book` already resolves `planning.command` and delegates,
so no change to `/plan-book`.

## Testing strategy

- **Thriller fixture series** — `tests/fixtures/thriller/`, minimal and self-contained, mirroring
  `tests/fixtures/cozy/`: `series.yaml` (`genre: thriller`), `.penny/` marker, a small
  `series/structure/book-01.yaml`, `series/continuity/canon-core.md`, one character entity
  (`series/continuity/characters/<protagonist>.md` + the antagonist) so entity resolution passes, a
  `config/run-config.md`, and a minimal lexicon. A `tests/conftest.py` `thriller_fixture` fixture
  returns its path (parity with `cozy_fixture`).
- **`tension_check.py` unit tests** — fixture artifacts under `tests/fixtures/structure/` (a
  `sound.yaml` and failing variants), each asserting the specific invariant: sag detection,
  unearned twist (`plant >= payoff`), tentpole misordering, missing fields, gap note, unresolved
  antagonist id. Same file layout as `test_fairplay_check.py`.
- **Manifest-conformance** — the existing generic test (`test_real_cozy_manifest_conforms`) gains a
  thriller sibling: `genres/thriller/genre.yaml` validates against the schema, and every name it
  references (`plan-thriller`, `tension` validator → `scripts/tension_check.py`, each inspector →
  `agents/inspector-<n>.md`, each rubric file) exists.
- **Manifest-driven preflight** — tests that, against the thriller fixture, `preflight draft` checks
  the structure artifact + `structure` lock (not the whodunit ledger); against the cozy fixture,
  behavior is byte-identical to today. A `structure` lock is minted by `preflight lock` only when
  `tension` + `lexicon` pass; refused otherwise.
- **Cozy regression** — the whole existing suite stays green; cozy's gate/inspector/lock behavior is
  unchanged (its manifest reproduces the old hardcode). The full suite is already data-independent
  (Phase 3a), so these run against fixtures with no live series.
- **`new-series`/scaffold** — scaffolding a `genre: thriller` series produces the structure-artifact
  directory contract (`series/structure/`) rather than `series/whodunit/`.

## Migration — what's new, what changes, what stays

- **New engine code:** `scripts/tension_check.py`; a genre-neutral `preflight lock` subcommand +
  manifest-driven `preflight draft`. **[DECISION]** extract fair-play's `_resolves` +
  well-formedness helpers into a shared spot (e.g. `penny_text` or a small `checker_common`) so
  `tension_check` reuses entity resolution rather than copy-pasting it (DRY; the review rubric flags
  verbatim logic duplication). If extraction proves noisy, a documented shared helper import is the
  fallback.
- **New pack + agents + command:** `genres/thriller/` (manifest, conventions, 2 rubrics),
  `agents/inspector-tension.md`, `commands/plan-thriller.md`.
- **Changed (behavior preserved via manifest):** `preflight.py` `cmd_draft` + `cmd_lock_mystery`
  (the latter becomes/aliases the general `lock`). Cozy output identical.
- **Unchanged:** every other checker/agent/command; the cozy pack; `~/myBooks/cozy-pelicans/`; all
  data-path resolution.

## Phasing (drives the implementation plan)

1. **Generalize preflight (engine, no new genre yet).** Make `cmd_draft` read `planning.{artifact,
   lock}` from the manifest and add the genre-neutral `lock` subcommand reading `planning.validator`
   + `gates:`; alias `lock-mystery`. Prove cozy behavior byte-identical against the cozy fixture.
2. **`tension_check.py` + the structure artifact schema.** TDD the checker against
   `tests/fixtures/structure/` variants; wire `tension` as a recognized validator/gate.
3. **Author the thriller pack.** `genres/thriller/` (manifest, conventions, rubrics),
   `agents/inspector-tension.md`, `commands/plan-thriller.md`; manifest-conformance test passes.
4. **Thriller fixture + end-to-end.** Build `tests/fixtures/thriller/`, add `thriller_fixture`, prove
   `plan → lock → draft → review` resolves entirely through the thriller manifest; scaffold an empty
   thriller series folder under `~/myBooks/`.

Each phase leaves the full suite green; cozy is unchanged throughout.

## Open questions (for review)

- **Artifact schema rigor** — confirm **[DECISION] A** (structural parity) vs minimal/rich.
- **Structure lock** — confirm **[DECISION] yes**, a `structure` lock (vs no lock).
- **Back-fix `fairplay_check.py`'s eager default** in this phase, or leave it? (Recommended: fix, for
  parity with `tension_check`/`lexicon_check`.)
- **`lock-mystery` alias** — keep as a compatibility alias for a phase (recommended), or retire now
  and repoint cozy runbooks/tests immediately?
- **Multi-POV timeline verification** — deferred; the artifact carries `pov_timeline` for the
  inspector but the checker does not cross-validate it in Phase 4. Promote to a checker invariant
  later if the thriller turns out heavily multi-POV.
- **The `lexicon` gate for thriller** — kept in the manifest (an empty/minimal lexicon passes), on
  the view that regional-fluency is a series/setting feature, not cozy-specific. Drop from the
  thriller manifest if the drama thriller has no dialect arc.
