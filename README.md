# Penny

A Claude-Code-native harness for producing commercial fiction series with **independent
quality review**. Penny plots a book with you, then turns that plot into finished,
cross-model-reviewed manuscript prose, one chapter at a time, behind a wall of
deterministic gates.

Two things are gated deterministically, and they are the two things that make a genre novel
work: **is the puzzle fair** (`fairplay_check.py`) and **does the story pull**
(`tension_check.py` — causality, open questions, escalation, hooks). Prose craft is judged
by isolated LLM inspectors; the *structure* underneath it is judged by scripts that cannot
be sweet-talked.

This repo **is the engine, packaged as a Claude Code plugin** (`.claude-plugin/plugin.json`
+ marketplace manifest). Commands live in `commands/`, agents in `agents/`, deterministic
checkers in `scripts/`, genre packs in `genres/`.

**The one architectural rule:** the engine is genre- and location-agnostic. Everything
project-specific lives in a **series folder** — an ordinary directory you `cd` into and run
Claude Code from — or in a **genre pack**. Never in `scripts/` or the command/agent logic.
When you add behaviour, decide whether it belongs to the fixed engine, to a genre, or to
one series' own data, and keep them apart.

**Series selection is by directory, not a flag.** There is no `--series` flag, no
`PENNY_SERIES` env var, no `current-series` pointer. The **active series is the current
working directory**: `scripts/penny_paths.py` walks up from cwd to the nearest `.penny/`
marker and hard-errors if it finds none. Running a pipeline command from this engine repo
fails on purpose (`penny-paths: no series root`).

Design intent: `penny-design-v3.md` + `penny-PRD-v3.md` (the `-v3` files supersede the
un-suffixed originals);
`docs/superpowers/specs/2026-07-07-engine-plugin-series-folders-design.md` supersedes both
for the plugin/series-folder topology. Sections are cited in code as `design §N`.

---

## Contents

- [Install](#install)
- [The two roots, and the config overlay](#the-two-roots-and-the-config-overlay)
- [End to end, part 1 — create a runnable series](#end-to-end-part-1--create-a-runnable-series)
- [End to end, part 2 — plot and lock a book](#end-to-end-part-2--plot-and-lock-a-book)
- [End to end, part 3 — the per-chapter loop](#end-to-end-part-3--the-per-chapter-loop)
- [End to end, part 4 — assemble, read, approve](#end-to-end-part-4--assemble-read-approve)
- [Command reference](#command-reference)
- [How it's built — three layers](#how-its-built--three-layers)
- [Key principles to preserve](#key-principles-to-preserve)
- [Status line](#status-line)

---

## Install

```bash
git clone <this-repo> ~/myTools/penny
cd ~/myTools/penny
pip install -r requirements.txt    # only third-party dep: PyYAML
```

Also needs `python3`, and `jq` for the status line. Add the plugin to Claude Code via the
marketplace manifest in `.claude-plugin/`, so `/new-series`, `/draft-chapter` and the rest
resolve from any directory.

> If another plugin exposes a colliding command name, Claude Code namespaces Penny's as
> `/penny-engine:<command>` (e.g. `/penny-engine:draft-chapter`). This README uses the bare
> form throughout.

The engine's test suite runs **from this repo root** (`pytest.ini` sets `pythonpath=.`):

```bash
python3 -m pytest -q     # 484 passing
```

Actual book work happens **from inside a series folder**, never from here.

Several steps below invoke `scripts/` directly from a series folder, where `scripts/` is
not on the path. Export the engine location once:

```bash
export PENNY_ENGINE=~/myTools/penny
```

Slash commands don't need this — they resolve scripts via `${CLAUDE_PLUGIN_ROOT}`.

---

## The two roots, and the config overlay

Penny always resolves against **two** roots (`scripts/penny_paths.py`):

| Root | What lives there | How it's found |
|---|---|---|
| **plugin root** | code, genre packs, config *defaults* | the engine repo containing `penny_paths.py` |
| **series root** | that series' data and overrides | nearest ancestor of cwd holding a `.penny/` dir |

**Data paths** — `series/`, `input/`, `output/`, `.penny/` — always resolve against the
series root. They have no plugin-side default.

**Config paths** overlay **three tiers**:

```
series/config/<rel>          →   genres/<declared-genre>/<rel>   →   plugin config/<rel>
(this series' override)          (its genre pack)                    (engine default)
```

Asking for a **single file** takes the first tier that has it. Asking for a **directory**
(e.g. the review rubrics) **unions** all three, with a higher tier shadowing only the
same filename — so a genre pack can add a rubric without hiding the engine's.

The declared genre comes from a `genre:` line in the series root's **`series.yaml`**. Miss
that file and genre-tier lookups are skipped silently, while `/plan-book` hard-errors.

### What the engine actually ships as a default

Only these. Everything else on the required list is **yours to author**:

```
config/outline-template.md          config/review-rubrics/        (5 rubrics)
config/line-edit/line-edit.md       config/copy-edit/copy-edit.md
config/self-audit/…                 config/beta-readers/beta-protocol.md
genres/cozy-mystery/                genre.yaml, conventions.md, 2 rubrics,
                                     beat-sheet.yaml, personas/genre-fan.md
```

---

## End to end, part 1 — create a runnable series

`/new-series` creates the **directory contract only**. It deliberately invents no story
content — and, as of today, it also writes neither `series.yaml` nor the config packs the
pipeline requires. A freshly scaffolded series is **not yet runnable**. Steps 2–4 close
that gap; budget real authoring time for them.

### 1. Scaffold the folder

```bash
/new-series cozy-pelicans              # → ~/myBooks/cozy-pelicans, git init'd
/new-series cozy-pelicans /some/root   # optional alternate root
cd ~/myBooks/cozy-pelicans             # this cd IS the series selection
```

It refuses to touch an existing directory. You get `.penny/locks/`,
`series/continuity/{characters,locations,threads}/`, `series/whodunit/`,
`config/{voice-pack,setting-pack,genre-pack}/`, `input/`, `output/`, and an empty
`series/continuity/canon-core.md`.

### 2. Declare the genre

```bash
echo 'genre: cozy-mystery' > series.yaml
```

Required. It selects the genre pack (`genres/cozy-mystery/`) that supplies the inspector
roster, the fairplay + lexicon gates, and the outline-craft rubric.

### 3. Author the config pack

`scripts/readiness_check.py` enumerates what every run reads. The engine ships defaults for
the last four; **you must create the rest** under the series' `config/`:

| File | What it is |
|---|---|
| `config/run-config.md` | model-per-role routing, run-mode flags, escalation thresholds (fenced ```yaml blocks) |
| `config/voice-pack/voice-pack.md` | the narrative voice the drafter writes in |
| `config/voice-pack/ai-tics-config.yaml` | tic list driving `voice_drift.py` |
| `config/voice-pack/ai-tics-detection.md` | how the AI-prose inspector reads those tics |
| `config/setting-pack/lexicon.yaml` | place/idiom lexicon gated at lock time |
| `config/setting-pack/<place>.md` | the setting pack itself |
| `config/genre-pack/<genre>.md` | genre conventions as prose for the drafter |
| `config/length-profile.md` | target chapter/book word counts |
| `config/beta-readers/personas/*.md` | six reader personas (`beta-protocol.md` ships; personas don't) |

Fastest honest start: copy a working set from `tests/fixtures/cozy/config/` or an existing
series, then rewrite the contents. Copying gets the *shape* right; none of the prose will
be yours.

`readiness_check.py` is genre/location-agnostic: it accepts any authored setting-pack prose
file under `config/setting-pack/` and expects the genre prose pack to match `series.yaml`
as `config/genre-pack/<genre>.md`.

### 4. Author the series reference files

Under `input/series/` — showrunner-authored, read by planners and reviewers:
`series-bible.md`, `series-arc.md`, `style-sheet.md`, `whodunit-ledger.md`.

### 5. Confirm the series is ready

```bash
python3 $PENNY_ENGINE/scripts/readiness_check.py           # engine + config only
python3 $PENNY_ENGINE/scripts/readiness_check.py 01        # + book-01 inputs & progress
```

A **reporter, not a gate** — it never exits non-zero and never mints a certificate. It
reuses the same predicates the real gates enforce, so a green checklist lines up with a
clean `lock-mystery`. Statuses: `ready` / `missing` / `blocked` (present but failing
validation).

---

## End to end, part 2 — plot and lock a book

Three front doors, all earning the same lock. **`/plot-book` is the recommended one for a
new book** — you and the engine build the plot together. Use `/scaffold-book` when you
already have an outline written elsewhere, and `/plan-mystery` when only the puzzle needs
planning.

### The workshop front door — `/plot-book NN`

A **resumable, staged** plotting workshop. Plotting a novel takes days, so every stage
saves its answer to a file under `input/book-NN/plot/` and you can stop after any of them:
the files are the state, never the conversation. Ask it where you left off and it tells
you — including what your last hand-edit invalidated:

```bash
/plot-book 02                                   # runs the next unfinished stage
python3 $PENNY_ENGINE/scripts/plot_stage.py status 02   # or just ask
```

| Stage | Who decides | What it writes |
|---|---|---|
| premise | **you** | `plot/premise.md` — the dramatic engine + the rejected shortlist |
| ending | **you** | `plot/ending.md` — who did it, the worst moment, the cost (= the mystery core) |
| turning-points | **you** | `plot/turning-points.md` — the 6–9 tentpole scenes, placed against the genre beat sheet |
| counterplot | machine → **you approve** | the whodunit ledger + sealed solution, via the existing `mystery-planner` |
| chapters | machine | the wired chapter skeleton, interpolated between fixed turning points |
| weave | machine | the secondary tracks braided through |
| readback | **you** | the blind fan's report + the proofreader's findings, then the lock |

Three ideas do the work. **The ending is decided before the middle exists** — chapters are
then *interpolated* between fixed points rather than extrapolated left-to-right, which is
what makes middles sag. **Your taste decides the big three** (premise, ending, turning
points); the machine proposes rivals for each and never chooses the core for you. And the
workshop **absorbs mystery planning** rather than running beside it, so the ending is
written down once and both the drama plan and the puzzle plan are built from it.

Optional: drop a brainstorm transcript at `plot/material.md` first and every stage will
read it — laying out your own rival versions for you to choose between, never quietly
inventing around them.

**Staleness is fingerprinted.** Each generated file records the sha256 of what it was built
from. Hand-edit the ending, rerun, and everything downstream is redone. Nothing drifts.

### The outline-first front door

Author `input/book-01/outline.md`, starting from `config/outline-template.md`. Its shape is
checked deterministically by `outline_check.py` (four named predicates, shape only — no
genre or quality judgment):

- YAML frontmatter with `book:` and `total_chapters:`
- one `## Chapter NN` heading per chapter, **contiguous** `1..total_chapters`, none empty
- at least one `## Solution: <label>` block — the sealed answer key
- optional `## Threads`

Then derive, review, and earn the lock:

```bash
/scaffold-book 01 input/book-01/outline.md             # derive + review, no lock
/scaffold-book 01 input/book-01/outline.md --approve   # earn the lock
```

The unapproved pass runs the structural gate, deletes any stale lock, dispatches the
`book-scaffolder` to write derived artifacts **unlocked** to their real homes
(`series/whodunit/book-01.yaml`, continuity threads/cast/locations, `canon-core.md`, and
the sealed key at `output/book-01/mystery-solution.md`), then writes
`output/book-01/scaffold-review.md` foregrounding the mystery strand with a **dry run of
what the lock will say**. Edit the outline and re-run until the dry run is green.

`--approve` calls the shipped, unchanged checker — `preflight.py lock-mystery 01` — which
mints `.penny/locks/book-01.mystery.lock` **iff** fairplay + lexicon pass. Generated ≠
trusted: the scaffolder never writes a certificate.

### The interactive front door

```bash
/plan-book 01      # resolves series.yaml's genre → that genre's planning command
/plan-mystery 01   # cozy-mystery's planner, directly
```

`/plan-mystery` separates three roles: the **showrunner** sets the irreducible core (who,
why, the central deception), the `mystery-planner` agent proposes the clue schedule / red
herrings / alibi grid, the showrunner approves and locks.

### The wired outline, and the proofreader that reads it

A chapter can carry four extra lines that state its **drama**, not just its events:

```markdown
- **Because:** ch 03 — the key theft turns Mary's kindness into surveillance.
- **Opens:** q-what-mary-hides — why does Mary guard the workshop papers?
- **Closes:** q-key-theft
- **Hook:** q-what-mary-hides — the tin comes back, the papers do not.
```

`Because` is the "therefore/but" test as data — a chapter that can't name the earlier turn
that *forced* it is an "and then" chapter, and the machine can see that. `Opens`/`Closes`
name the questions the reader is carrying; `Carries` marks one deliberately left open past
this book (a series seed, not a dropped stitch). `Hook` must lead with a question still
open, so a hook stops being a mood and becomes a promise on record.

`scripts/tension_check.py` then reads the whole outline and fails loud on **nine named checks**:

| Check | Fires when |
|---|---|
| `orphan-chapter` | nothing caused this chapter |
| `dropped-question` | a question is opened and never answered or carried |
| `phantom-answer` | a chapter answers a question nobody asked |
| `dead-stretch` | **the reader has no open question pulling them forward** — the sagging middle, as arithmetic |
| `broken-hook` | a chapter ends on a question already answered |
| `starved-thread` | a subplot goes dark longer than the genre allows |
| `off-mark-beat` | a tentpole scene sits outside its beat-sheet window |
| `chapter-coverage` | the chapter set has gaps, dupes, or extras |
| `overloaded-chapter` | a chapter's scenes can't each be paid their floor out of its word band, **or** its obligation load (clues planted + questions opened/closed + tracks advanced) exceeds the genre's cap — too many stops for the length, a plotting problem caught before the lock rather than in the prose |

Every threshold comes from the genre's `beat-sheet.yaml` or your `config/length-profile.md`
— never from a constant in the engine. **Wiring is optional per book:** an outline without
it is skipped entirely, so outlines written before this existed stay valid and still lock.
`overloaded-chapter` is the exception that reads **scene weights**, not wiring, so it runs
over the expanded `input/book-NN/outline.md` — the file the weights live in. An outline with
no weights is never overload-checked. And a check that *cannot* run (no length profile, one
the engine can't parse, no floors, no obligation cap) never crashes the lock and is never
silently dropped: it prints a note, the book still locks, and the certificate records
`skipped: overloaded-chapter — <why>`.

### The length profile

`config/length-profile.md` is **series-authored — the engine ships no default**, so here is
the schema it must carry, in a fenced ```yaml block:

```yaml
band_opening:      [1800, 2400]   # band_<type>, selected by a chapter title's [type: …] flag
band_default:      [2000, 2500]   # REQUIRED — the band for a chapter that declares no type
weight_anchor:      8             # a scene's share of the band's midpoint …
weight_support:     3             # … an anchor is worth eight connective beats
weight_connective:  1             #     because that is what YOUR series says it is worth
min_connective_words: 100         # min_<class>_words: below this, the scene is starved …
min_support_words:    250         # … and the chapter is doing more than its band can pay for
```

`anchor | support | connective` are the engine's vocabulary (the outline parser reads exactly
those three, and the brief compiler carries drafting prose for them); the **numbers** are
yours. A profile missing `band_default` fails by name and tells you which keys to add — an
older profile written before this schema keeps every command working, and simply means
`overloaded-chapter` records itself as skipped on the lock certificate until you add them.

### The lock, and your override

`preflight.py lock-mystery NN` now validates **fairplay + lexicon + tension** and mints the
certificate only if all three pass. You can always overrule the proofreader — but the
override goes on the record:

```bash
preflight.py lock-mystery 02 --waive dead-stretch:"ch 14 is the designed breath before the second body"
```

Findings are printed whether waived or not, and the waiver is written **into the lock
certificate**, so a locked book with a waived finding says so on its face. The machine never
overrules you, and never lets an override pass silently.

### Re-planning

A lock is an **out-of-band certificate** — it exists only because validation passed. To
re-plan: delete the lock, edit the yaml, re-run `lock-mystery`. Never add a `locked:` field
to the data the lock gates; a field would be a forgeable certificate.

### Optional pre-draft passes

```bash
/expand-outline 01 [05]                  # outline-skeleton.md → scene-breakdown outline.md
/review-outline 01 [--focus "<directive>"]
```

`/expand-outline` is the **context-rich exception** among generative roles: it reads the
solution to schedule clue beats; the reveal-timing rule is enforced on the page by
`inspector-fairplay`.

`/review-outline` runs an **independent Claude + Codex panel** over the whole outline
(identical inputs) and appends prose feedback — **no scores** — as ID'd
`OF-<n>` items to `output/book-01/reports/outline-feedback.yaml`. It is presented
**side-by-side, never converged**: reviewer disagreement is the signal, so averaging would
destroy it. Advisory; nothing here blocks drafting.

You own each item's disposition by hand-editing `state:` to `open` / `solved` / `rejected`.
Re-runs only ever append; they never overwrite your dispositions. `/draft-chapter` surfaces
open items and outline staleness as a **non-blocking banner**.

If the Codex runtime is unreachable the panel degrades to Claude-only and says so
("independence reduced") — by design, never a halt.

### Build the chapter briefs — `/build-briefs NN`

The step between the outline and the first draft:

```bash
/build-briefs 02
```

It has two halves with two different preconditions. **Weighing the scenes is an outline
act** — it needs only the outline and the length profile, so do it **before the lock**, and
the lock's `overloaded-chapter` check will then see the weights it exists to check.
**Compiling the briefs needs the locked ledger's obligations**, so that half runs after.
If you weigh a book that is already locked, the certificate no longer covers what you
changed: delete the lock and re-run `preflight lock-mystery NN` — the same re-planning flow
as any other edit to a sealed plot.

The raw outline hands the drafter a flat numbered list of beats written with equal
lavishness — a promise of parity the model reads literally, which is how a chapter meant
to run 1,800–2,400 words comes out at 3,800. `/build-briefs` compiles the locked outline
into one prompt-shaped brief per chapter (`input/book-NN/briefs/ch-MM.md`): an emphasis
hierarchy (anchor/support/connective) with per-scene word budgets from
`config/length-profile.md`, obligations as a checklist rather than stops, a commissioned
first line, a graded hook (cliffhanger | promise), declared negative space, and a compact
non-scene reference extract. The full raw `### Scene` beat-flow list is deliberately not
inlined again: prompt mass is instruction mass, and pasting the flat list back into the
brief would recreate the parity problem the compiler exists to remove.

If the outline declares no scene weights, `/build-briefs` dispatches the `brief-weigher`
sub-agent to propose a weighting per chapter — you accept, edit, or reject; only your
accepted weights are written back into the outline. **An outline with no scene weights at
all is passed through untouched**, so book 1 is unaffected until you choose to weigh it.
Each brief is stamped with the outline's sha256 **and** the whodunit ledger's — the
ledger is a real upstream of every brief too, since the obligations come from it, so
moving a clue's `plant_chapter` goes stale the same way editing the outline does. Edit
either afterwards and every brief goes stale, so `/draft-chapter` refuses until you
re-run this.

---

## End to end, part 3 — the per-chapter loop

Run for `MM = 01, 02, …` from the series root:

```bash
/draft-chapter 01 07
/review-chapter 01 07
python3 $PENNY_ENGINE/scripts/preflight.py clear-dev 01 07
/finalize-chapter 01 07 [--commit]
```

For local LM Studio models that write strong short scenes but tend not to complete whole
chapters in one pass, use the alternate scene-shard route in the first slot:

```bash
/draft-chapter-lmstudio 01 07 [model-id]
```

It runs the same draft preflight and writes the same `ch-07.draft.md` artifact, but
orchestrates generation as scene shards, a stitch pass, and length repair before the normal
`/review-chapter` gate.

**`/draft-chapter`** hard-fails first via `preflight.py draft` (lock present + ledger
populated), shows the outline-review banner, then dispatches the `drafter` against the
chapter brief, the packs, and a **ledger slice** — canon-core plus brief-named entries plus
their one-hop `links`. The drafter reads the full solution; it also gets this
chapter's clue obligations.

**`/draft-chapter-lmstudio`** uses `scripts/lmstudio_draft_chapter.py` against LM Studio's
OpenAI-compatible server (default `http://localhost:1234/v1`). It stamps drafts as
`drafted_by: lmstudio/<model-id>`, so the normal assemble-time cross-model independence gate
still applies.

**`/review-chapter`** is the gate. Five **isolated** inspectors (continuity, fairplay,
structure, voice, AI-prose, per the genre pack's roster) plus the deterministic checkers.
The panel **PASSes iff zero blockers**, else **HOLDs**; a HOLD surfaces to you and
re-drafting is a manual re-run. It also dispatches the **developmental editor** — the top
of the edit stack and the deliberate **context-rich exception**: it gets the setting pack, a
character-bible slice, the chapter brief, and the solution, because a craft read
must know what the chapter is trying to do. It runs on a non-drafting model for fresh eyes;
if none is reachable the command **halts** rather than degrade to a same-model read. Its
verdict is `kind: developmental` — **advisory**, contributing zero blockers, never affecting
PASS/HOLD.

**`clear-dev`** is you, the showrunner, signing off the developmental read. It mints a
certificate **bound to the draft's sha256**. Revise the draft afterwards and the hash
changes, re-requiring clearance.

**`/finalize-chapter`** refuses unless the chapter both carries `gate: PASS` **and** a fresh
dev-clearance matching the current draft hash. It then runs the post-gate prose tail:
line-edit → copy-edit → ledger-update → ledger markers → promote to `.final.md`. Under
`ledger_approval: review` it pauses for a diff review; resume with `--commit`. Under `auto`
it commits end to end.

Artifacts land in `output/book-01/chapters/`:

```
ch-07.draft.md → ch-07.lineedit.md → ch-07.copyedit.md → ch-07.final.md
ch-07.reviews/   (verdict sidecars)        ch-07.gate.md   (panel decision)
```

**The blocker convention:** a `^BLOCKING:` line at column 0 in a verdict file. Counted
identically by `review_gate.py`, `penny_verdict.count_blocking`, and the status line's
grep — a cross-consistency test pins that agreement. Don't fork it.

---

## End to end, part 4 — assemble, read, approve

```bash
/assemble-book 01              # assemble → cross-model gate → final read → priority report
/assemble-book 01 --approve    # seal the manuscript, mint the approval certificate
```

Step one assembles the finalized chapters, then gates **cross-model independence**: the
`final_read_model` must not appear among the chapters' `drafted_by` frontmatter stamps. The
invariant is **difference, not identity**, enforced by `preflight.py assemble`. The
`final-reader` agent then makes the one genuine holistic judgment in the whole pipeline —
emitting enumerated `yes|no` booleans a validator checks, not free prose — and a
deterministic revision-priority report is built. The command pauses.

`--approve` seals `book-01.manuscript.md` and mints `.penny/locks/book-01.approved`.

Book-level beta reading is **non-blocking** and can run any time after assembly:

```bash
/beta-read output/book-01/book-01.manuscript.md [--out <dir>]
```

Six personas fan across reachable `beta_models`. Beta readers are the most isolated agents
in Penny: each gets only `{text, persona_file}` — no ledger, no outline, no solution.
**Personas are distinct lenses and are never averaged**; models are the within-persona
consensus axis (≥K-of-M via `beta_consensus_k`).

> With `panel_size: 1` (fast mode) a put-down can never reach `beta_consensus_k: 2`
> consensus. Expected, not a bug.

---

## Command reference

| Command | Scope | Blocking? |
|---|---|---|
| `/new-series <name> [root]` | anywhere | — creates dir contract only |
| `/plot-book <NN>` | book | **the workshop** — resumable; mints the lock at the end |
| `/plan-book <NN>` | series | delegates by genre |
| `/plan-mystery <NN>` | book | mints the lock |
| `/scaffold-book <NN> <outline> [--approve]` | book | mints the lock |
| `/expand-outline <NN> [MM]` | book | requires sealed solution |
| `/review-outline <NN> [--focus "…"]` | book | **advisory** |
| `/build-briefs <NN>` | book | requires the lock |
| `/draft-chapter <NN> <MM>` | chapter | requires the lock |
| `/draft-chapter-lmstudio <NN> <MM> [model-id]` | chapter | requires the lock; LM Studio scene-shard route |
| `/review-chapter <NN> <MM>` | chapter | **the gate** — PASS/HOLD |
| `/finalize-chapter <NN> <MM> [--commit]` | chapter | requires PASS + clear-dev |
| `/assemble-book <NN> [--approve]` | book | requires cross-model independence |
| `/beta-read <path> [--out <dir>]` | book | **non-blocking** |

`scripts/preflight.py` is the one deterministic-gate tool — six subcommands:
`lock-mystery NN [--waive check-id:"reason"]` (validate fairplay + lexicon + tension, then
mint — the *only* lock writer), `draft NN MM`, `finalize NN MM`, `clear-dev NN MM`,
`assemble NN`, `approve-book NN`.

`scripts/plot_stage.py` runs the workshop's save points: `status NN` (which stage is next,
what your last edit invalidated), `stamp NN …` (the fingerprints), and `readers-copy NN`
(the blind fan's copy).

`scripts/review_gate.py` owns the panel DECISION: `PASS` iff zero blockers, else `HOLD`. It
writes `ch-MM.gate.md` and prints `GATE: PASS|HOLD`. **Exit 0 means the gate *evaluated***
(either verdict); non-zero means an operational error.

---

## How it's built — three layers

1. **Deterministic engine — `scripts/*.py`.** Pure-Python gates and checkers that **never
   make an LLM judgment**, so they survive the soft-gate weakness of an LLM-graded
   pipeline. Each fails loud with a named predicate and a non-zero exit.

   *Dependency-split rule (load-bearing):* `penny_meta.py` is a **dependency-free** parser
   for the small YAML subset Penny uses — frontmatter, fenced ```yaml blocks, and
   `<!-- canon-meta: {...} -->` headers. **PyYAML is reserved for genuinely nested
   human-edited data** — the whodunit ledgers, the lexicon, the outline-feedback ledger, and
   the genre beat sheet. Don't reach for PyYAML to parse config or frontmatter.

2. **Orchestration — `commands/*.md` + `agents/*.md`.** Slash commands are step-by-step
   runbooks that shell out to `scripts/` (as `${CLAUDE_PLUGIN_ROOT}/scripts/…`, so they
   resolve regardless of which series folder is cwd) and dispatch sub-agents. Agents are
   role-scoped: drafter, five isolated inspectors, context-rich developmental editor,
   outline-reviewer, book-scaffolder, line/copy editors, beta readers, cross-model final
   reader — plus the workshop's three: `plot-proposer` (surfaces your material and proposes
   rivals, never chooses the core), `chapter-weaver` (interpolates and braids, never drafts
   prose), and `outline-fan` (the blind genre-fan reader).

3. **Swappable data — genre packs and the series folder.** `genres/<g>/` holds `genre.yaml`
   (inspector roster, gates, planning command, tracks, plus the optional `beat_sheet:` and
   `fan_persona:` keys `/plot-book` reads — cozy's `beat-sheet.yaml` and
   `personas/genre-fan.md` are the worked example a thriller pack will follow),
   conventions, and genre rubrics. The series folder holds `config/` overrides, `series/`
   continuity, `input/`, `output/`. Swap either and you change genre or location without
   touching the engine.

### Series memory & context discipline

`series/continuity/canon-core.md` is **loaded every chapter — keep it tiny**; every line
taxes every chapter. Everything else loads as a brief-scoped **ledger slice**. Continuity
sections carry `<!-- canon-meta: {...} -->` headers (id, refs, active_window,
last_referenced) read and written by `penny_meta`. The demotion machinery is partial by
design — see `docs/` and the phase notes.

`.penny/` (gitignored) holds runtime state: `current-stage` drives the status line, `locks/`
holds certificates.

---

## Key principles to preserve

- **Gates are deterministic, never LLM judgments.** A model makes a holistic call in only
  two places, and neither is a hard gate: the **advisory** developmental read (never blocks
  PASS/HOLD), and the cross-model final read — which emits enumerated `yes|no` booleans a
  validator checks.
- **Locks and certificates are out-of-band.** Never represent "validated" or "approved" as a
  field *inside* the data it gates.
- **Sub-agents are isolated, not ignorant.** Inspectors get one rubric + a ledger slice and
  never another agent's output; beta readers get only `{text, persona}` because a reader who
  knows the culprit stops reacting like a reader. Everyone else reads the solution.
- **Blindness is enforced by construction, never by instruction.** We never hand a reader the
  whole outline and ask it not to peek. `plot_stage.py readers-copy` *mechanically* removes
  the solution, the wiring, the question ids and the track rows, and truncates before the
  reveal chapter — because the reveal chapter's own summary names the culprit, so no amount
  of stripping could hide the answer. The fan reads chapters 1..reveal−1, which is exactly
  what reading is: you guess **before** the ending.
- **Cross-model independence is difference, not identity.** `final_read_model` must not
  appear among the chapters' `drafted_by` stamps.
- **Independent panels are not averaged.** Outline review is side-by-side because
  disagreement is the signal; only *within* a beta persona do models converge.
- **Canon-core is always loaded — keep it tiny.**

Run configuration (model routing, run-mode flags, escalation thresholds) lives in the
series' `config/run-config.md`. See `CLAUDE.md` for working conventions, `TESTING.md` to
verify the harness end to end, and `HANDOFF*.md` for current session state (one file per
parallel workstream).

---

## Status line

`scripts/penny-statusline.sh` (wired in `.claude/settings.json`) reads harness state from
the **active series** — `current-stage` and `output/` under the series root resolved by
`penny_paths.py` — plus the session JSON on stdin. `$PENNY_ROOT` (default `.`) is only the
idle fallback for when cwd isn't inside any series. Requires `jq`.
