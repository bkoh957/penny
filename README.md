# Penny

A Claude-Code-native harness for producing a 13-book commercial fiction series (cozy
mystery, Book 1) with **independent quality review**. Penny turns a per-book mystery
design into finished, cross-model-reviewed manuscript prose, one chapter at a time,
behind a wall of deterministic gates.

**The one architectural rule:** the engine is genre- and location-agnostic. Everything
project-specific lives in swappable `config/` (packs, rubrics, run-config), `input/`
(showrunner-authored files: series bible, style sheet, whodunit ledger, per-book outlines),
and `series/` (derived continuity data) — **never** in `scripts/` or the command/agent
logic. When you add behaviour, decide whether it belongs to the fixed engine or to a
swappable pack, and keep them apart.

Design intent: `penny-design-v3.md` (+ `penny-PRD-v3.md`); the `-v3` files supersede the
un-suffixed originals. Sections are cited in code as `design §N`.

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

Also needs `python3` and `jq` (the latter only for the status line). Run everything from
the repo root — `pytest.ini` sets `pythonpath=.`.

```bash
python3 -m pytest -q               # the deterministic test suite (221 passing)
```

To verify the whole harness end to end — required inputs, formats, and every approval
gate — see **[TESTING.md](TESTING.md)**.

---

## How it's built — three layers

1. **Deterministic engine — `scripts/*.py`.** Pure-Python gates and checkers that
   **never make an LLM judgment**, so they survive the soft-gate weakness of an
   LLM-graded pipeline. Each fails loud with a named predicate and a non-zero exit.
   (`penny_meta.py` is the dependency-free parser for Penny's small YAML subset; PyYAML
   is reserved for genuinely nested human-edited data — the whodunit ledgers and lexicon.)
2. **Orchestration — `.claude/commands/*.md` + `.claude/agents/*.md`.** Slash commands are
   step-by-step runbooks that shell out to `scripts/` and dispatch sub-agents. Agents are
   role-scoped: the drafter, the five blind inspectors, line/copy editors, beta readers,
   the cross-model final reader.
3. **Swappable data — `config/`, `input/`, and `series/`.** The engine reads these; it
   never hardcodes their content. `input/series/` holds showrunner-authored reference
   files (series bible, style sheet, whodunit ledger); `input/book-NN/` holds the
   per-book outline. `series/` holds derived continuity data (canon-core, character/
   location/thread ledger entries). Swap the packs and you change genre or location
   without touching the engine.

---

## The workflow

```
/plan-mystery NN            once per book — design the whodunit and LOCK it
  └─ for each chapter MM:
       /draft-chapter   NN MM
       /review-chapter  NN MM        ← the developmental GATE (PASS / HOLD)
       /finalize-chapter NN MM [--commit]
/beta-read <manuscript-path>          book-level reader reactions (NON-blocking)
/assemble-book NN [--approve]         assemble → cross-model final read → report → APPROVE
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
  manual re-run.
- `/finalize-chapter` runs the post-gate prose tail (line-edit → copy-edit →
  ledger-update → promote to `.final.md`). With `ledger_approval: review` it pauses for a
  diff review; resume with `--commit`.

**3. Beta read** (`/beta-read`) fans six reader personas across models on an assembled
text and writes per-persona reaction reports. Non-blocking — it never holds the pipeline.

**4. Assemble and approve the book.** `/assemble-book NN` assembles finalized chapters,
gates **cross-model independence** (the final reader must not be a model that drafted),
runs the one genuine holistic judgment (the `final-reader` agent), builds a deterministic
revision-priority report, then pauses for approval. `/assemble-book NN --approve` seals
the manuscript and mints `.penny/locks/book-NN.approved` — the MVP-1 finish line.

---

## Key principles to preserve

- **Gates are deterministic, never LLM judgments.** The one place a model makes a holistic
  call is the cross-model final read — and even that emits enumerated `yes|no` booleans a
  validator checks, not free prose.
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

`scripts/penny-statusline.sh` (wired in `.claude/settings.json`) reads harness state from
`.penny/current-stage` and `output/`, plus the session JSON from stdin. Honours
`$PENNY_ROOT` (default `.`).
