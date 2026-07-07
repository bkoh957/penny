# Penny

A Claude-Code-native harness for producing commercial fiction series (cozy mystery,
Book 1 of the first series) with **independent quality review**. Penny turns a per-book
mystery design into finished, cross-model-reviewed manuscript prose, one chapter at a
time, behind a wall of deterministic gates.

This repo **is the engine, packaged as a Claude Code plugin** — see
`.claude-plugin/plugin.json` and its marketplace manifest. Commands live in top-level
`commands/`, agents in `agents/`, deterministic checkers in `scripts/`.

**The one architectural rule:** the engine is genre- and location-agnostic. Everything
project-specific lives in a **series folder** — an ordinary directory you `cd` into and
run Claude Code from, holding that series' `config/` overrides, `input/`
(showrunner-authored files: series bible, style sheet, whodunit ledger, per-book outlines),
`series/` (derived continuity data), `output/`, and `.penny/` runtime state — **never**
in `scripts/` or the command/agent logic. When you add behaviour, decide whether it
belongs to the fixed engine or to a series' own data, and keep them apart.

**Series selection is by directory, not a flag or pointer.** There is no `--series`
flag, no `PENNY_SERIES` env var, and no `current-series` pointer file. The **active
series is the current working directory**: `scripts/penny_paths.py` walks up from cwd
to the nearest `.penny/` marker and hard-errors if it finds none. Config reads
**overlay**: a series' own `config/<rel>` wins if present, else this repo's shipped
default under `config/`. Run `/new-series <name>` from anywhere to scaffold a new
series folder's directory contract (default under `~/myBooks/`); then `cd` there and
run `/plan-mystery 01`.

Design intent: `penny-design-v3.md` (+ `penny-PRD-v3.md`); the `-v3` files supersede the
un-suffixed originals, and
`docs/superpowers/specs/2026-07-07-engine-plugin-series-folders-design.md` supersedes
both for the plugin/series-folder topology described here. Sections are cited in code
as `design §N`.

---

## Status

MVP 1 is complete. The Build Order (`penny-design-v3.md` §13) has 8 phases; **Phases 1–6
are shipped**, and Phase 6 is the MVP-1 endpoint — a finished, cross-model-reviewed
`book-NN.manuscript.md` plus a showrunner approval certificate. Remaining work is
`[POST-MVP1]`:

- **Phase 7** — EPUB compile + proof agent (format + ship).
- **Phase 8** — series scale: arc-ledger across all 13 books, cross-book reviewers, and
  the canon-core demotion machinery (a no-op stub until books span enough range).

---

## Install

```bash
pip install -r requirements.txt    # only third-party dep: PyYAML
```

Also needs `python3` and `jq` (the latter only for the status line). The engine's own
test suite runs from this repo root — `pytest.ini` sets `pythonpath=.`:

```bash
python3 -m pytest -q               # the deterministic test suite (273 passing)
```

Working on an actual book happens from inside a **series folder**, not this repo — see
"Series folders" below.

To verify the whole harness end to end — required inputs, formats, and every approval
gate — see **[TESTING.md](TESTING.md)**.

---

## How it's built — three layers

1. **Deterministic engine — `scripts/*.py`.** Pure-Python gates and checkers that
   **never make an LLM judgment**, so they survive the soft-gate weakness of an
   LLM-graded pipeline. Each fails loud with a named predicate and a non-zero exit.
   (`penny_meta.py` is the dependency-free parser for Penny's small YAML subset; PyYAML
   is reserved for genuinely nested human-edited data — the whodunit ledgers and lexicon.)
2. **Orchestration — `commands/*.md` + `agents/*.md`.** Slash commands are step-by-step
   runbooks that shell out to `scripts/` (via `${CLAUDE_PLUGIN_ROOT}/scripts/...`) and
   dispatch sub-agents. Agents are role-scoped: the drafter, the five blind inspectors,
   the context-rich developmental editor, line/copy editors, beta readers, the
   cross-model final reader.
3. **Swappable data — each series folder's `config/`, `input/`, and `series/`.** The
   engine reads these; it never hardcodes their content. `input/series/` holds
   showrunner-authored reference files (series bible, style sheet, whodunit ledger);
   `input/book-NN/` holds the per-book outline. `series/` holds derived continuity data
   (canon-core, character/location/thread ledger entries). Swap the series folder and
   you change genre or location without touching the engine.

### Series folders

A **series is an ordinary directory** — its own `config/` overrides, `series/`
continuity, `input/`, `output/`, and a `.penny/` marker + runtime state — that you `cd`
into and run Claude Code from. There is no `--series` flag, no `PENNY_SERIES` env var,
and no `current-series` pointer file: the **active series is the current working
directory**. `scripts/penny_paths.py` resolves it by walking up from cwd to the nearest
`.penny/` marker (a hard error if none is found — the engine never guesses which series
you mean). Config reads **overlay**: a series' own `config/<rel>` wins if present, else
this repo's shipped default under `config/`; data paths (`series/`, `input/`,
`output/`, `.penny/`) always resolve against the series root.

Run `/new-series <name>` from anywhere to scaffold a new series folder's directory
contract (default location `~/myBooks/<name>/`, root configurable); it invents no story
content. Then `cd` into it and run `/plan-mystery 01` to begin.

---

## The workflow

```
# 1. Lock the mystery (once per book)
/plan-mystery NN

# 2. Per chapter — repeat for MM = 01, 02, 03 … N
/draft-chapter NN MM
/review-chapter NN MM        # 5 blind inspectors + advisory developmental editor; PASS → continue, HOLD → fix draft & re-run
python3 scripts/preflight.py clear-dev NN MM   # showrunner clears the developmental read for this draft
/finalize-chapter NN MM      # requires gate PASS + a fresh dev-clearance; add --commit to auto-commit

# 3. Beta read (non-blocking — can run any time after assembly)
/beta-read output/book-NN/book-NN.manuscript.md

# 4. Assemble + final read + approve
/assemble-book NN            # assembles, cross-model final read, revision-priority report
/assemble-book NN --approve  # seals manuscript, mints the approval certificate
```

**1. Plan and lock the mystery.** `/plan-mystery NN` separates three roles: the showrunner
sets the irreducible core (who, why, the central deception), the `mystery-planner` agent
proposes the clue schedule / red herrings / alibi grid, and the showrunner approves. The
result is validated and frozen into a **lock certificate**
(`.penny/locks/book-NN.mystery.lock`). The lock exists *only* because validation passed —
re-planning means delete the lock, edit the yaml, re-lock.

**2. Draft → review → finalize, per chapter.**
- `/draft-chapter` dispatches the `drafter` against the chapter brief, packs, and a
  **ledger slice** (canon-core + brief-named entries + one-hop links). The drafter is
  blind to the full solution; it gets only this chapter's clue obligations.
- `/review-chapter` is the gate: five **blind** inspectors (continuity, fairplay,
  structure, voice, AI-prose) plus deterministic 2a checkers. The panel **PASSes iff
  zero blockers**, else **HOLDs**. A HOLD is surfaced to the showrunner; re-drafting is a
  manual re-run. It also dispatches the **developmental editor** — the top of the edit
  stack: a *context-rich* (not blind) craft read on the draft that scores eight craft
  dimensions (sense of place, motivation, scene economy, subtext, interiority,
  show-don't-tell, genre delivery, hook). It is **advisory** — it never emits a blocker
  and never affects PASS/HOLD — but its read is a precondition for finalize (below). It
  runs on a non-drafting model for fresh eyes; if none is reachable, `/review-chapter`
  **halts** rather than degrade to a same-model read.
- `/finalize-chapter` runs the post-gate prose tail (line-edit → copy-edit →
  ledger-update → promote to `.final.md`). It refuses unless the chapter both passed the
  gate **and** carries a fresh **developmental clearance** — an out-of-band certificate
  bound to the draft's sha256, minted by `preflight clear-dev` when the showrunner clears
  the developmental read. Revising the draft after clearance changes the hash and
  re-requires it. With `ledger_approval: review` it pauses for a diff review; resume with
  `--commit`.

**3. Beta read** (`/beta-read`) fans six reader personas across models on an assembled
text and writes per-persona reaction reports. Non-blocking — it never holds the pipeline.

**4. Assemble and approve the book.** `/assemble-book NN` assembles finalized chapters,
gates **cross-model independence** (the final reader must not be a model that drafted),
runs the one genuine holistic judgment (the `final-reader` agent), builds a deterministic
revision-priority report, then pauses for approval. `/assemble-book NN --approve` seals
the manuscript and mints `.penny/locks/book-NN.approved` — the MVP-1 finish line.

---

## Key principles to preserve

- **Gates are deterministic, never LLM judgments.** A model makes a holistic call in only
  two places, and neither is a hard gate: the **advisory** developmental read (which never
  blocks PASS/HOLD), and the cross-model final read — and even that emits enumerated
  `yes|no` booleans a validator checks, not free prose.
- **Locks and certificates are out-of-band.** Never represent "validated/approved" as a
  field *inside* the data it gates — a field would be a forgeable certificate.
- **Sub-agents are dispatched blind.** Inspectors get one rubric + a ledger slice; beta
  readers get only `{text, persona}`. Personas are distinct lenses and are never averaged.
- **Cross-model independence is difference, not identity:** `final_read_model` must not
  appear among the chapters' `drafted_by` stamps. Enforced at three points.
- **Canon-core is always loaded — keep it tiny.** Every line taxes every chapter. Other
  continuity loads only as a brief-scoped slice.

Configuration (model routing, run-mode flags, escalation thresholds) lives in
`config/run-config.md`. See `CLAUDE.md` for the working conventions and the
dependency-split rule, and `HANDOFF.md` for current session state.

## Status line

`scripts/penny-statusline.sh` (wired in `.claude/settings.json`) reads harness state
from the **active series**, resolved via `scripts/penny_paths.py` (`current-stage` and
`output/` under that series root), plus the session JSON from stdin. `$PENNY_ROOT`
(default `.`) is only the idle fallback for when cwd isn't inside any series.
