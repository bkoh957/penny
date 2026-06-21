# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Penny** is a Claude-Code-native harness for producing a 13-book commercial fiction
series (cozy mystery, Book 1) with independent quality review. The non-negotiable
architectural rule: **the engine is genre/location-agnostic — everything
project-specific lives in swappable `config/` and `series/`, never in `scripts/` or
the command/agent logic.** When adding behavior, ask whether it belongs to the fixed
engine or to a swappable pack, and keep them separate.

Source of truth for design intent is `penny-design-v3.md` (+ `penny-PRD-v3.md`); the
`-v3` files supersede the un-suffixed originals. Sections are cited throughout the code
as `design §N`. The build proceeds **phase by phase**; Phases 1–5 are shipped, Phase 6
(per-book assembly + final holistic read + revision-priority report) is next. Check
`HANDOFF.md` at session start for current state.

## Commands

```bash
python3 -m pytest          # full suite (~189 tests); pytest.ini sets pythonpath=.
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
2. **Orchestration — `.claude/commands/*.md` + `.claude/agents/*.md`.** Slash commands
   are step-by-step runbooks that shell out to `scripts/` and dispatch sub-agents.
   Agents are role-scoped (drafter, the 5 blind inspectors, line/copy editors,
   beta-reader, etc.).
3. **Swappable data — `config/` (packs, rubrics, run-config) and `series/`
   (continuity ledger, bibles, whodunit data).** The engine reads these; it never
   hardcodes their content.

### Dependency-split rule (load-bearing)

- `scripts/penny_meta.py` is a **dependency-free** parser for the small YAML subset
  Penny uses (frontmatter, fenced ```yaml blocks, and `<!-- canon-meta: {...} -->`
  headers). The deterministic layer uses it to avoid a PyYAML dependency.
- **PyYAML is used only for genuinely nested human-edited data** — the whodunit
  ledgers (`series/whodunit/*.yaml`) and the lexicon. Don't reach for PyYAML to parse
  config/frontmatter; use `penny_meta`.

## The per-chapter pipeline

`/plan-mystery NN` (once per book) → `/draft-chapter NN MM` → `/review-chapter NN MM`
(the gate) → `/finalize-chapter NN MM [--commit]`. `/beta-read <path>` is book-level
and **non-blocking**.

Chapter artifacts live under `output/book-NN/chapters/`:
`ch-MM.draft.md` → `.lineedit.md` → `.copyedit.md` → `.final.md`, plus the review
sidecar dir `ch-MM.reviews/` and the gate summary `ch-MM.gate.md`.

### Gates and the verdict convention

- **`scripts/preflight.py`** is the one deterministic-gate tool, four subcommands:
  `lock-mystery N` (validate fairplay+lexicon, then mint the lock — the *only* lock
  writer), `draft N CH` (lock present + ledger populated), `assemble N` (cross-model
  routing guard), `finalize N CH` (chapter must have `gate: PASS`).
- **Verdict files** (`ch-MM.reviews/*.md`) share one envelope — see the docstring of
  `scripts/penny_verdict.py` (`schema: penny-verdict/1`). A **`^BLOCKING:`** line at
  column 0 is *the* blocker convention; it is counted identically by
  `review_gate.py`, `penny_verdict.count_blocking`, and `penny-statusline.sh`'s grep.
  A cross-consistency test pins this agreement — don't fork the convention.
- **`scripts/review_gate.py`** owns the panel DECISION: `PASS` iff zero blockers, else
  `HOLD`. It writes `ch-MM.gate.md` and prints `GATE: PASS|HOLD`. Exit 0 means the gate
  *evaluated* (PASS or HOLD); nonzero means an operational error.

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

### Blind sub-agents

Inspectors and beta-readers are dispatched **blind**: each gets only its narrow inputs
(chapter text + one rubric + ledger slice for inspectors; `{text, persona_file}` only
for beta-readers — no ledger, outline, or solution). Preserve this isolation. Personas
are distinct lenses and are **never averaged**; models are the within-persona consensus
axis (≥K-of-M via `beta_consensus_k`).

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

`config/run-config.md` holds model-per-role routing, run-mode flags (`panel_size`,
`gate_mode`, `ledger_approval`, `beta_consensus_k`…), and escalation thresholds, all in
fenced ```yaml blocks. `ledger_approval: review` makes `/finalize-chapter` pause for a
diff review (resume with `--commit`); `auto` commits end-to-end. Note `panel_size: 1`
(fast mode) means a put-down can never reach `beta_consensus_k: 2` consensus — expected,
not a bug.

## Conventions

- Phase work flows through the `superpowers` skills: brainstorm → spec
  (`docs/superpowers/specs/`) → plan (`docs/superpowers/plans/`) → TDD/subagent-driven
  execution. New deterministic behavior is test-first against `tests/fixtures/`.
- Work phase-at-a-time on `main`; push at phase end. Verify claims against the actual
  design doc rather than asserting from memory.
