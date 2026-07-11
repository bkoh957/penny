# Penny

A Claude-Code-native harness for producing commercial fiction series with **independent
quality review**. Penny turns an author's prose outline into finished,
cross-model-reviewed manuscript prose, one chapter at a time, behind a wall of
deterministic gates.

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
- [End to end, part 2 — plan and lock a book](#end-to-end-part-2--plan-and-lock-a-book)
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
python3 -m pytest -q     # 350 passing
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
genres/cozy-mystery/                genre.yaml, conventions.md, 2 rubrics
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

## End to end, part 2 — plan and lock a book

Two front doors. **Outline-first (`/scaffold-book`) is the recommended one** — you write
story, the engine derives structure.

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
| `/plan-book <NN>` | series | delegates by genre |
| `/plan-mystery <NN>` | book | mints the lock |
| `/scaffold-book <NN> <outline> [--approve]` | book | mints the lock |
| `/expand-outline <NN> [MM]` | book | requires sealed solution |
| `/review-outline <NN> [--focus "…"]` | book | **advisory** |
| `/draft-chapter <NN> <MM>` | chapter | requires the lock |
| `/draft-chapter-lmstudio <NN> <MM> [model-id]` | chapter | requires the lock; LM Studio scene-shard route |
| `/review-chapter <NN> <MM>` | chapter | **the gate** — PASS/HOLD |
| `/finalize-chapter <NN> <MM> [--commit]` | chapter | requires PASS + clear-dev |
| `/assemble-book <NN> [--approve]` | book | requires cross-model independence |
| `/beta-read <path> [--out <dir>]` | book | **non-blocking** |

`scripts/preflight.py` is the one deterministic-gate tool — six subcommands:
`lock-mystery NN` (validate, then mint — the *only* lock writer), `draft NN MM`,
`finalize NN MM`, `clear-dev NN MM`, `assemble NN`, `approve-book NN`.

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
   human-edited data** — the whodunit ledgers, the lexicon, the outline-feedback ledger.
   Don't reach for PyYAML to parse config or frontmatter.

2. **Orchestration — `commands/*.md` + `agents/*.md`.** Slash commands are step-by-step
   runbooks that shell out to `scripts/` (as `${CLAUDE_PLUGIN_ROOT}/scripts/…`, so they
   resolve regardless of which series folder is cwd) and dispatch sub-agents. Agents are
   role-scoped: drafter, five isolated inspectors, context-rich developmental editor,
   outline-reviewer, book-scaffolder, line/copy editors, beta readers, cross-model final
   reader.

3. **Swappable data — genre packs and the series folder.** `genres/<g>/` holds `genre.yaml`
   (inspector roster, gates, planning command, tracks), conventions, and genre rubrics. The
   series folder holds `config/` overrides, `series/` continuity, `input/`, `output/`.
   Swap either and you change genre or location without touching the engine.

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
- **Cross-model independence is difference, not identity.** `final_read_model` must not
  appear among the chapters' `drafted_by` stamps.
- **Independent panels are not averaged.** Outline review is side-by-side because
  disagreement is the signal; only *within* a beta persona do models converge.
- **Canon-core is always loaded — keep it tiny.**

Run configuration (model routing, run-mode flags, escalation thresholds) lives in the
series' `config/run-config.md`. See `CLAUDE.md` for working conventions, `TESTING.md` to
verify the harness end to end, and `HANDOFF.md` for current session state.

---

## Status line

`scripts/penny-statusline.sh` (wired in `.claude/settings.json`) reads harness state from
the **active series** — `current-stage` and `output/` under the series root resolved by
`penny_paths.py` — plus the session JSON on stdin. `$PENNY_ROOT` (default `.`) is only the
idle fallback for when cwd isn't inside any series. Requires `jq`.
