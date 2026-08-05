# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Penny** is a Claude-Code-native harness for producing commercial fiction series with
independent quality review. This repo **is the engine, packaged as a Claude Code plugin**
(`.claude-plugin/plugin.json` + marketplace manifest): commands live in top-level
`commands/`, agents in `agents/`, deterministic checkers in `scripts/`, genre packs in
`genres/`. The non-negotiable architectural rule: **the engine is genre/location-agnostic
— everything project-specific lives in a swappable genre pack or per-series folder, never
in `scripts/` or the command/agent logic.** When adding behavior, ask whether it belongs
to the fixed engine, to a genre, or to one series' own data, and keep them separate.

Each **series is an ordinary folder you `cd` into** and run Claude Code from — its own
`config/` overrides, `series/` continuity, `input/`, `output/`, and `.penny/` runtime
state. There is no `--series` flag, no `PENNY_SERIES` env var, and no `current-series`
pointer: the **active series is the working directory**, resolved by
`scripts/penny_paths.py` walking up from cwd to the nearest `.penny/` marker (hard error
if none found). Running a pipeline command from *this* repo fails on purpose — the engine
is not a series.

Config reads overlay **three tiers**: a series' `config/<rel>` → the
declared genre's `genres/<genre>/<rel>` → the plugin default under this repo's `config/`.
**Single-file** reads (`config_path`) take the **first hit**. **Directory** reads
(`config_dirs`, `config_dir_files`) **union across all three tiers**, shadowing per
filename — a genre pack that adds one rubric must not hide the plugin's defaults. Reaching
for `config_path` on a directory reintroduces that shadowing bug.
The genre comes from a `genre:` line in the series root's **`series.yaml`**; absent that
file, the genre tier is skipped silently and `/plan-book` hard-errors. Data paths
(`series/`, `input/`, `output/`, `.penny/`) always resolve against the series root, never
the plugin root.

Source of truth for design intent is `penny-design-v3.md` (+ `penny-PRD-v3.md`); the
`-v3` files supersede the un-suffixed originals, and
`docs/superpowers/specs/2026-07-07-engine-plugin-series-folders-design.md` supersedes
both for the plugin/series-folder topology described here. Sections are cited
throughout the code as `design §N`.

**Two phase schemes coexist — don't conflate them.** Design §13's *build order* runs 1–8;
Phases 1–6 are shipped and Phase 6 (book loop) was the MVP-1 endpoint, leaving `[POST-MVP1]`
Phase 7 (EPUB) and Phase 8 (series scale + canon-core demotion). The separate *plugin/genre
roadmap* runs Phase 3a/3b (engine-plugin split, series relocation — shipped) and Phase 4
(the thriller genre pack — **specced but unapproved**, 5 open `[DECISION]` flags in
`docs/superpowers/specs/2026-07-08-thriller-genre-pack-design.md`). Check `HANDOFF.md` at
session start for current state.

## Commands

```bash
python3 -m pytest          # full suite (350 tests); pytest.ini sets pythonpath=.
python3 -m pytest tests/test_review_gate.py            # one test file
python3 -m pytest tests/test_review_gate.py -k name    # one test
pip install -r requirements.txt                        # only dep: PyYAML
```

`jq` is required by the status line. The deterministic `scripts/` layer is otherwise
pure stdlib — see the dependency split below.

## Three-layer architecture

1. **Deterministic engine — `scripts/*.py`.** Pure-Python gates and checkers that
   **never make an LLM judgment**, so they survive the "soft gate" weakness of an
   LLM-graded pipeline. Each fails loud with a named predicate and a nonzero exit.
2. **Orchestration — `commands/*.md` + `agents/*.md`.** Slash commands
   are step-by-step runbooks that shell out to `scripts/` (referenced from runbooks as
   `${CLAUDE_PLUGIN_ROOT}/scripts/...` so they resolve regardless of which series folder
   is the cwd) and dispatch sub-agents. Agents are role-scoped (drafter, the story-author,
   the 5 isolated inspectors, the context-rich developmental-editor, line/copy editors,
   beta-reader, etc.).
3. **Swappable data — genre packs + the active series folder.** `genres/<g>/` holds
   `genre.yaml` (inspector roster, gates, planning command, tracks), conventions, and
   genre rubrics. The series folder holds `config/` overrides (packs, rubrics,
   run-config), `series/` (continuity ledger, bibles, whodunit data), and `input/`
   (writer-authored outlines and series reference files). The engine reads these; it
   never hardcodes their content.

   **What this repo actually ships as a `config/` default** is a short list — the review
   rubrics, line/copy-edit style, self-audit, the outline template, and `beta-protocol.md`.
   It ships **no** `run-config.md`, voice-pack, setting-pack, genre-pack, `length-profile.md`,
   or beta personas, even though `readiness_check.py` requires all of them. Those are
   series-authored, so a freshly `/new-series`-scaffolded folder is **not yet runnable**.
   `series/`, `input/`, and `output/` have no plugin-side default at all.

### Dependency-split rule (load-bearing)

- `scripts/penny_meta.py` is a **dependency-free** parser for the small YAML subset
  Penny uses (frontmatter, fenced ```yaml blocks, and `<!-- canon-meta: {...} -->`
  headers). The deterministic layer uses it to avoid a PyYAML dependency.
- **PyYAML is used only for genuinely nested human-edited data** — the whodunit
  ledgers (`series/whodunit/*.yaml`), the lexicon, the outline-feedback ledger, and
  the genre beat sheet (`beat-sheet.yaml`). Don't reach for PyYAML to parse
  config/frontmatter; use `penny_meta`.

### Readiness is genre/location-agnostic

`scripts/readiness_check.py` accepts any authored setting-pack prose file under
`config/setting-pack/` and resolves the genre prose pack from `series.yaml` as
`config/genre-pack/<genre>.md`. Do not reintroduce hardcoded setting or genre filenames in
engine code.

## The pipeline

**Series setup:** `/new-series <name> [root]` writes the directory contract only — no
`series.yaml`, no config packs, no story content. See the shipped-defaults note above.

**Per book (three front doors, all earning the same lock):**
- `/plot-book NN` — **the recommended door for a new book.** A resumable, staged
  plotting workshop: save points under `input/book-NN/plot/` (`material.md` optional,
  then `premise.md`, `ending.md`, `turning-points.md`) hold the showrunner's own taste
  calls; `plot_stage.py status` names the next stage and what went stale (sha256
  `built_from_*` fingerprints on each save point). Stages run `premise → ending →
  turning-points → counterplot → chapters → weave → cut → readback`
  (`scripts/plot_stage.py`'s `STAGE_ORDER`); `chapters` and `weave` both write
  `input/book-NN/story.md` (the source layer, below) — the counterplot stage
  dispatches the existing `mystery-planner` rather than duplicating it. It ends with
  a blind genre-fan read-back (`plot_stage.py readers-copy` strips solution/wiring
  throughout, and
  **truncates** the copy to chapters `1..reveal_chapter−1` — not merely a strip,
  because the reveal chapter's own summary prose names the culprit) presented
  beside `tension_check.py`'s findings, then mints the lock —
  the workshop's only lock mint — with any per-check `--waive check-id:"reason"`
  recorded in the certificate.
- `/scaffold-book NN <outline-path> [--approve]` — the outline-first door for an
  outline authored elsewhere. `outline_check.py` gates the outline's *shape* (four
  named predicates: integer `book`/`total_chapters` frontmatter, a `## Solution`
  block, contiguous non-empty `## Chapter NN` headings). The `book-scaffolder` then
  derives structure **unlocked** into its real homes and emits
  `output/book-NN/scaffold-review.md` with a **dry run of what the lock will say**.
  `--approve` calls the shipped, unchanged `preflight lock-mystery`. Generated ≠
  trusted: the scaffolder never writes a certificate.
- `/plan-book NN` resolves `series.yaml`'s genre and delegates; `/plan-mystery NN` is
  cozy-mystery's interactive planner, standalone (showrunner core → `mystery-planner`
  proposal → approve + lock) — for the puzzle alone, when the dramatic outline is
  already settled some other way.

**The source layer (spec `docs/superpowers/specs/2026-08-03-story-source-layer-design.md`):**

```
story.md    input/book-NN/story.md      beats in story order, four sigils
    │  chapter-cutter proposes, showrunner approves — cut-plan.md
    ▼
outline.md  input/book-NN/outline.md    packet format, generated  (locked)
```

`story.md` carries only what the author decides — what happens, in what order, to whom
(`@strand`), which structural job a beat answers (`#job`), which questions open and close
(`+q-id` / `-q-id`), and where a ledger clue is planted (`!clue-id`). Question prose lives
once, in a `## Questions` block. Two further blocks are optional and scope with the same
sigils: `## Chapter Direction` (structural notes the `chapter-cutter` reads and the cut
never emits) and `## Guardrails` (prose notes carried into each chapter's Guardrails
section, scoped to that chapter's own beats — spec
`docs/superpowers/specs/2026-08-04-chapter-direction-and-guardrails-design.md`).
Everything else in a chapter block — Character Knowledge,
Guardrails, wiring, Starting/Ending State, Chapter Purpose — is **derived** by
`scripts/story_cut.py` from the ledger, the genre and the tags. There is nowhere to type
boilerplate, which is why `story.md` cannot drift into the duplicate the retired
chapter-skeleton layer became. `story_cut.py` fails loud, by name, on sixteen findings —
`unknown-strand`, `unknown-job`, `unknown-clue`, `unknown-question`, `unscheduled-clue`,
`orphan-question`, `unclosed-question`, `beats-without-chapter`, `duplicate-beat`,
`missing-reveal-chapter`, `clue-not-found-in-ledger-text`, `outline-modified-since-cut`,
`cut-owned-outline`, `orphan-direction`, `misplaced-schedule-tag`,
`wiring-shaped-directive` — no waivers at this level (spec §8): fix the story or the cut
plan. Authored guardrails are emitted **in authoring order**, ahead of the derived
series-guardrail and reveal-chapter lines; a note shaped like a wiring field or a Track
Movement row is refused rather than emitted, since the emitted block is parsed line by
line and authored prose must not be able to forge the cut's own output.

What a beat *is* — as opposed to how it is tagged — lives in the config overlay at
`config/story-craft/`, read as a **directory** so a genre pack can add to it without
copying it (spec `2026-08-06-dramatic-beat-authoring-design.md`). A beat is a change
on the page, one visible change per beat; a note addressed to the writer belongs in
`## Guardrails`, and a note about where chapters fall in `## Chapter Direction`.
`/plot-book`'s chapters stage reads that union before writing a beat, and the
**`story-author`** agent works a named range of beats with the showrunner — it may
mint `@strand` slugs (shape-checked only) but never a `!clue-id` (a ledger fact) or a
`#job` (a genre fact) — the missing-authority gap is exactly how book 01's 18 invented
ids went missing.
`story_cut.py check NN` validates a story with no cut plan, suppressing
`beats-without-chapter` (with no plan it fires once per beat) and printing the one
advisory, **`directive-shaped-beat`** — a beat opening with an imperative such as
*Plant* or *Do not*. It rides the existing non-blocking `notes` channel, never
`blocking`: the sixteen findings stay sixteen, and an advisory that could block would
just be a seventeenth with a softer name.

`unclosed-question` is the converse of `orphan-question` and **the only place it can be
caught**: the emitter carries every live question into every chapter through the last one,
so downstream an abandoned question is indistinguishable from a deliberate series seed —
`tension_check`'s `dropped-question` can never fire on a cut outline. The rule is *at most
one*, not *none*, because one unclosed question is structural: every chapter must hook a
question open at it (`broken-hook`), and the final chapter can only hook something the book
has not closed. A second is a dropped thread wearing the seed's clothes.

Clue chapter numbers don't exist until the cut, so `story_cut.py` resolves each `!clue-id`
to the chapter its beat lands in and writes the number back into
`series/whodunit/book-NN.yaml` — into **`plant_chapter:`**, the key every consumer actually
reads (`penny_whodunit._plant_chapter` → `clues_by_chapter` → `packet_assemble` and
`tension_check`'s `overloaded-chapter`; `fairplay_check`; `lmstudio_draft_chapter`), across
**both** `clue_schedule` and `red_herrings`, since both collections schedule obligations.
The write is **surgical**: only the matched `plant_chapter:` values move, in either the
block form or the inline flow-mapping form (`- { id: x, plant_chapter: 5, … }`), never a
`yaml.safe_load`/`safe_dump` round-trip, which would silently flatten the ledger's
comments, anchors, and quoting (spec §6). Safe because `preflight lock-mystery` runs after
the cut, while the ledger is still unsealed.

Re-cutting is free while `outline.md` still matches its `cut_output_sha256` stamp, and
refuses `outline-modified-since-cut` the moment it does not — the same finding also fires
when the stamp is **absent altogether**, which is not a lesser case: an outline with no
`cut_output_sha256` was never produced by a cut at all, and absence is a refusal, never a
licence. This is the branch that protects a hand-authored/scaffolded outline (book 01's)
from being cut over. It is also **the whole migration path onto the source layer, and needs
no engine support**: `recut_refusal` is only called inside `if outline_p.is_file()`, so a
legacy book joins by writing `story.md`, committing, **deleting the unstamped `outline.md`**
(and the stale lock, since the cut rewrites `plant_chapter:`), and cutting. There is no
adoption flag and must not be one — the guard protects work still on disk, and deleting it
is the showrunner's explicit act. `/expand-outline` refuses a cut-produced outline the same
way (`cut-owned-outline`) — it is for outlines the cut never touched. The plot
workshop's `readback` stage runs after the cut, against `outline.md` — never against
`story.md`, which carries no chapters to read back.

**Per book, around the lock — three artifacts, one per chapter (design
`docs/superpowers/specs/2026-07-18-packet-map-chapter-design.md` §2–§7,
supersedes the brief compiler above the lock):**

```
outline.md  — packet-format chapter blocks, wired, NO scenes         (locked)
    │  slice + lookups, deterministic — packet_assemble.py
    ▼
PACKET  input/book-NN/packets/ch-MM.md      what the chapter needs to know
    │  map-maker proposes, showrunner approves — /map-chapter
    ▼
MAP     input/book-NN/maps/ch-MM.md         how the chapter spends its words
    │  drafter: map = instruction, packet = context
    ▼
DRAFT   output/book-NN/chapters/ch-MM.draft.md
```

Each outline chapter block carries packet-section `###` headings (Chapter Purpose,
Starting/Ending State, Reader-Facing Shape, Required Beats, Clues and Plants, Character
Knowledge, Guardrails, the wiring footer) and **no `### Scene` section, ever** — scenes
drifted into chapter-sized units once already (design §1) and the fix is removing the
container, not compressing its contents downstream. `/map-chapter NN MM` (replaces
`/build-briefs`) runs both halves per chapter, post-lock:

1. `packet_assemble.py NN MM` — deterministic, no LLM: slices this chapter's outline
   block, merges in every ledger clue scheduled for this chapter (rendering each clue's
   `description:` field, falling back to `misleads_toward:`, then a named placeholder if
   neither is set — series authors should add `description:` to
   `clue_schedule`/`red_herrings` entries so packets read well), appends the continuity
   extracts (canon-core + entries the block names + their one-hop links), the standing
   `config/series-guardrails.md` block, and the chapter's word band. Refuses **by name**:
   no mystery lock (the packet needs the sealed ledger's obligations), or no `###
   Required Beats` section (this chapter isn't in packet format yet). Stamps
   `built_from_outline: <sha256>` and `built_from_whodunit: <sha256|none>`.
2. The **`map-maker`** agent proposes the prose map from the packet — scene divisions,
   `Target: A–B words` per scene, free-text `Weight:` (no enum, no per-class pricing —
   the one-anchor rule is dead), `Beats covered:` indices into the packet's Required
   Beats (1-based, order is contract), and every ledger clue id placed in exactly one
   scene's `Clue:` field. **Proposes only** — the showrunner edits/approves, and only the
   approved map is written, stamped `built_from_packet: <sha256 of the packet file>`
   (`scripts/penny_map.py`'s `map_path`).
3. `map_check.py NN MM` gates the approved map with named findings — `band-mismatch`
   (scene targets can't sum into the band), `starved-scene` (a target's max is below
   `min_scene_words`), `unparseable-target`, `dropped-beat`, `duplicate-beat`,
   `unscheduled-clue`, `stale-map` (the packet changed since) — **no waivers at this
   level**: fix the map or fix the outline. Exit 0/1/2 (clean / findings / usage).

`/draft-chapter` then reads the map as its instruction and the packet as its context (plus
the previous chapter's final ~300 words). `preflight draft` polices the staleness chain —
stale packet, or a map whose `built_from_packet` stamp no longer matches — and **passes
silently when neither a packet nor a map exists at all**, the legacy fallback: an
unmigrated book (book 1) drafts from the raw outline section exactly as before, warned by
name, never blocked.

**The length profile is series-authored and the engine ships none** — so its schema is
documented, not defaulted (README, "The length profile"). Schema v2: `band_default: [min,
max]` (plus `band_<type>` overrides selected by a chapter title's `[type: …]` flag,
unchanged) and one flat `min_scene_words` floor for any scene in the prose map.
`scripts/penny_length.py` no longer generates per-scene budgets from emphasis weights — it only
`band_for`s the chapter and validates the map-maker's authored targets against the band
and the floor (`validate_targets`). Legacy v1 keys (`weight_<class>`, `min_<class>_words`)
are tolerated and ignored, never a hard failure. A profile the engine cannot parse never
crashes a command: `lock-mystery` records `skipped: overloaded-chapter — …` on the
certificate and locks; `map_check.py` names which keys are missing.

**Per chapter:** `/draft-chapter NN MM` → `/review-chapter NN MM` (the gate; also dispatches
the context-rich `developmental-editor` advisory) → `preflight clear-dev NN MM` →
`/finalize-chapter NN MM [--commit]` (requires `gate: PASS` **and** a clear-dev cert bound
to the draft's sha256). For local LM Studio models that output reliable short scenes but
not whole chapters, `/draft-chapter-lmstudio NN MM [model-id]` is an alternate first step:
same preflight/artifact, scene-shard orchestration, stitch pass, and length repair before
the normal `/review-chapter` gate.

**Per book, at the end:** `/assemble-book NN [--approve]`. `/beta-read <path>` is book-level
and **non-blocking**.

### Optional pre-draft passes

`/expand-outline NN [MM]` expands skeletal stubs in `input/book-NN/outline.md` into
packet-format chapter blocks in place — never a `### Scene` section. It reads the solution
to schedule clue beats, and must not schedule a reveal beat before `reveal_chapter`. It
refuses `cut-owned-outline` on any outline the cut produced (see the source layer, above);
it is for outlines the cut never touched — a legacy book such as book 01.

`/review-outline NN [--focus "…"]` runs an **independent Claude + Codex panel** over the
whole outline (identical inputs) and appends prose feedback — **no scores** —
as ID'd `OF-<n>` items to `output/book-NN/reports/outline-feedback.yaml`. Presented
**side-by-side, never converged**: reviewer disagreement is the signal, so averaging it away
(the beta layer's K-of-M) would destroy it — this deliberately inverts that convention. The
ledger is **append-only**; the showrunner owns each item's `state:` (`open`/`solved`/
`rejected`) by hand-editing the yaml. `outline_feedback.py status` is the draft-time banner
and **never exits nonzero** (it must never block drafting); `append`/`render` fail loudly.
Advisory throughout; if the Codex runtime is unreachable the panel degrades to Claude-only
and says "independence reduced" — by design, never a halt.

The same ledger also receives the plot workshop's **`fan-audit`** items — the staged
read-back's measured findings (spec `2026-07-30-staged-reveal-readback-design.md`).
Items may carry `chapters:` and `metrics:`, stored opaquely; one item is one change to
one chapter, because the showrunner works them one at a time. `/plot-book`'s readback is
therefore a **loop** — read, findings, work them, re-read, lock — not a single pass.

Chapter artifacts live under `output/book-NN/chapters/`:
`ch-MM.draft.md` → `.lineedit.md` → `.copyedit.md` → `.final.md`, plus the review
sidecar dir `ch-MM.reviews/` and the gate summary `ch-MM.gate.md`.

### Gates and the verdict convention

- **`scripts/preflight.py`** is the one deterministic-gate tool, six subcommands:
  `lock-mystery N` (validate fairplay+lexicon+tension, then mint the lock — the
  *only* lock writer; `tension_check.py` is the dramatic-wiring checker beside
  `fairplay_check.py`, nine named checks — `orphan-chapter`, `dropped-question`,
  `phantom-answer`, `broken-hook`, `chapter-coverage`, `dead-stretch`,
  `starved-thread`, `off-mark-beat`, `overloaded-chapter` — each waivable with
  `--waive check-id:"reason"`,
  recorded in the lock certificate; the beat sheet driving the last three is
  resolved through the active genre's `genre.yaml` `beat_sheet:` key
  (`penny_genre.py beat-sheet`), never a hardcoded filename; an outline with no
  wiring is SKIPPED entirely, so book 1 and any hand-authored/scaffolded outline
  still lock exactly as before. `overloaded-chapter` is the one check that reads
  **Required Beats rather than wiring** — it runs over any chapter block carrying a
  `### Required Beats` section (packet format), and counts the chapter's **obligation
  load** (required beats +
  clues planted + questions opened/closed + tracks advanced) against the genre beat
  sheet's `obligations.max_per_chapter`. A chapter with no Required Beats gives it
  nothing to do; an outline with none anywhere (the legacy scenes/weights shape) is
  never checked. Per-scene word pricing (band-mismatch, starved-scene) moved with the
  scenes themselves to `map_check.py`, post-lock, per chapter — this check is now purely
  a plot-obligation count, not a word-count arithmetic. A check that **cannot run** — the
  genre beat sheet declares no `obligations.max_per_chapter`, or the whodunit ledger
  cannot be read — is never silent and never a traceback: it prints a named note and the
  lock certificate records it as `skipped: <check-id> — <why>`, so the certificate cannot
  claim coverage it does not have), `draft N CH`
  (lock present + ledger populated + the review panel is routed off the drafting
  model — `inspector_model` must exist and differ from `drafting_model`, since the
  inspector agents carry no `model:` frontmatter and would otherwise inherit the
  drafting session and grade their own prose), `assemble N` (cross-model routing guard),
  `finalize N CH` (chapter must have `gate: PASS` + a fresh clear-dev cert),
  `clear-dev N CH` (showrunner approves developmental report), `approve-book N`
  (precondition gate + mints the `.approved` cert — its last write).
- **Verdict files** (`ch-MM.reviews/*.md`) share one envelope — see the docstring of
  `scripts/penny_verdict.py` (`schema: penny-verdict/1`). A **`^BLOCKING:`** line at
  column 0 is *the* blocker convention; it is counted identically by
  `review_gate.py`, `penny_verdict.count_blocking`, and `penny-statusline.sh`'s grep.
  A cross-consistency test pins this agreement — don't fork the convention.
- **`scripts/review_gate.py`** owns the panel DECISION: `PASS` iff zero blockers, else
  `HOLD`. It writes `ch-MM.gate.md` and prints `GATE: PASS|HOLD`. Exit 0 means the gate
  *evaluated* (PASS or HOLD); nonzero means an operational error.
- **`kind: developmental`** verdicts (from the developmental-editor) are advisory: they contribute zero blockers and never prevent finalization.

### Locks and certificates

A mystery lock (`.penny/locks/book-NN.mystery.lock`) is an **out-of-band certificate**:
it exists only because validation passed. Never represent "locked/validated" as a field
*inside* the data it gates (a field would be a forgeable certificate). Re-planning =
delete the lock, edit the yaml, re-run `lock-mystery`.

### Cross-model independence

The final read and beta read must be done by a model that did **not** draft. The
invariant is **difference, not identity**: `final_read_model` must not appear in the
chapters' `drafted_by` frontmatter stamps. `preflight.py assemble` enforces this; agent
outputs carry `drafted_by`/`read_by` stamps so it can.

### Independence, isolation, reader simulation

One word — *blind* — used to name three unrelated things. It named them badly. There are
three properties, each with its own justification (spec:
`docs/superpowers/specs/2026-07-10-remove-solution-blindness-design.md`):

- **Independence = model difference, not ignorance.** The reviewing model must not be the
  drafting model. Enforced by `preflight.py assemble` against `drafted_by`. `final-reader`
  sees the whole solution and is the most independent agent in the system.
- **Isolation = narrow inputs, no cross-talk.** Each inspector gets one chapter, one
  rubric, one ledger slice, and never another inspector's verdict. Isolation is about
  *whose reasoning* an inspector can see, never about *what is true* — which is why
  `inspector-fairplay` holds the solution and is still isolated.
- **Reader simulation = the reader stays unknowing, in a clean context.**
  `{ text, persona_file }` only. Not a guardrail: a reader who knows the culprit cannot
  report that she guessed her in chapter four. For the OUTLINE fan read the operative
  property is **isolation, not independence** — `outline-fan` must always be a fresh
  sub-agent and never run inline in the plotting session, because inherited context
  defeats any persona; running on the same *model* as the plot is fine and is not
  recorded as a shortfall (spec `2026-07-30-staged-reveal-readback-design.md` §7).
  Personas are distinct lenses and are **never averaged**; models are the
  within-persona consensus axis (≥K-of-M via `beta_consensus_k`).

**There is no solution-blindness.** The drafter, outline-expander, outline-reviewer,
developmental-editor, and inspector-fairplay all read `mystery-solution.md`. The one thing
drafter blindness bought — no reveal before `reveal_chapter` — is a blocking predicate on
`inspector-fairplay`, with the rubric clause in the genre pack. It is deliberately **not**
a script: it is an LLM judgment, and a name-grep would fire on every innocent sentence the
culprit appears in.

A **mystery lock** is still "sealed" — meaning *frozen against edits*, never *hidden from
agents*.

## Series memory & context discipline

- `series/continuity/canon-core.md` is **always loaded every chapter** — keep it tiny;
  every line taxes every chapter. Other continuity entries (`characters/`, `locations/`,
  `threads/`) are loaded as a **ledger slice**: only entries named in the chapter brief
  plus their one-hop `links` (design §4.2).
- Continuity sections carry `<!-- canon-meta: {...} -->` headers (id, refs,
  active_window, last_referenced…) read/written by `penny_meta`. The demotion machinery
  (last_referenced scanning) is partial — see the memory note on phase dependencies.
- `.penny/` (gitignored) holds runtime state: `current-stage` drives the status line,
  `locks/` holds certificates.

## Run configuration

`config/run-config.md` — resolved through the overlay, so in practice the **series'** copy;
the engine ships no default — holds model-per-role routing, run-mode flags (`panel_size`,
`gate_mode`, `ledger_approval`, `beta_consensus_k`…), and escalation thresholds, all in
fenced ```yaml blocks. `ledger_approval: review` makes `/finalize-chapter` pause for a
diff review (resume with `--commit`); `auto` commits end-to-end. Likewise `book_approval`
for `/assemble-book`. Note `panel_size: 1` (fast mode) means a put-down can never reach
`beta_consensus_k: 2` consensus — expected, not a bug. Optional `plot_model:` routes
`/plot-book`'s `plot-proposer` and `chapter-cutter` (defaults to `drafting_model`); the
`outline-fan` prefers any reachable model other than `plot_model`; proceeding on
`plot_model` when none is reachable is not a degradation and gets no note.

## Conventions

- Phase work flows through the `superpowers` skills: brainstorm → spec
  (`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`) → TDD/subagent-driven
  execution. New deterministic behavior is test-first against `tests/fixtures/`.
- Work phase-at-a-time on `main`; push at phase end. Verify claims against the actual
  design doc rather than asserting from memory.
