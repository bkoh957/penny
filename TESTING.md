# Testing Penny — MVP 1

How to verify the Penny harness end to end. MVP 1 is the Build-Order endpoint
(`penny-design-v3.md` §13, item 6): a finished, cross-model-reviewed
`book-NN.manuscript.md`. Phases 7 (EPUB/ship) and 8 (series scale) are `[POST-MVP1]`.

There are **two kinds of testing**, and they are independent:

1. **The deterministic test suite** — pure-Python, no LLM, no inputs to author. Proves
   the engine's gates and parsers. Run it on every change. *(Fast, fully automated.)*
2. **The live MVP-1 walkthrough** — actually drives the chapter→book pipeline with the
   slash commands and sub-agents. This is the only way to exercise **agent judgment**
   (drafter, inspectors, final-reader), which the test suite cannot cover. *(Slow,
   requires authored inputs + model access; treat the first run as a shakedown.)*

---

## 1. The deterministic test suite

```bash
pip install -r requirements.txt    # only third-party dep: PyYAML
python3 -m pytest -q                # full suite — currently 221 passing
```

- `pytest.ini` sets `pythonpath=.`, so run from the repo root.
- One test file: `python3 -m pytest tests/test_review_gate.py`
- One test: `python3 -m pytest tests/test_review_gate.py -k name`
- `jq` is required only by the status line (`scripts/penny-statusline.sh`), not by the
  suite.

This layer covers every `scripts/*.py` gate against `tests/fixtures/`. **A green suite
means the deterministic engine is sound; it says nothing about prose quality** — that is
what the live walkthrough is for.

---

## 2. The live MVP-1 walkthrough

The pipeline, in order:

```
/plan-mystery NN            once per book — design + LOCK the mystery
  └─ for each chapter MM:
       /draft-chapter   NN MM
       /review-chapter  NN MM       ← the developmental GATE (PASS/HOLD)
       /finalize-chapter NN MM [--commit]
/beta-read <manuscript-path>         book-level, NON-blocking
/assemble-book NN [--approve]        assemble → cross-model final read → report → APPROVE
```

Every command shells out to a deterministic gate first and aborts on a non-zero exit.
The gates are the test: if you can drive a book from `/plan-mystery` to a minted
`.penny/locks/book-NN.approved` certificate, MVP 1 works.

### 2.0 Prerequisites before you can draft a single chapter

The repo ships with a **partial** Book-1 fixture. Two inputs are **not** authored and
will block a real run — author them first:

| Needed input | Status in repo | Why it blocks |
|---|---|---|
| Character entities for every culprit/victim/suspect id in the ledger | **Missing** (only `cora-mistate` exists) | `lock-mystery` fairplay gate requires each id to resolve to a file (see §3.1) |
| Chapter briefs (`series/briefs/book-NN/ch-MM-brief.md`) | **No `series/briefs/` dir exists** | The drafter's primary input; without it `/draft-chapter` falls back to canon-core only and cannot plant scheduled clues |

> Concretely: the shipped `series/whodunit/book-01.yaml` names `culprit: margaret`,
> `victim: edwin-tilley`, and suspect `thomas` — **none of which have character
> entities**, so `python3 scripts/preflight.py lock-mystery 01` fails today with three
> blocking lines. Create those entities (§3.4) before locking.

---

## 3. Required inputs and their formats

All project-specific data lives in `config/` (swappable packs) and `series/` (this
book's content). The engine reads these; it never hardcodes their content. Formats below
are the **real** shapes the scripts parse.

### 3.1 Mystery ledger — `series/whodunit/book-NN.yaml` (PyYAML)

The whodunit design, validated by `fairplay_check.py` and frozen by the lock. Authored
by the showrunner + `mystery-planner` via `/plan-mystery`.

```yaml
book: 01
total_chapters: 24
reveal_chapter: 22
culprit: margaret                      # must resolve to a character entity (see below)
culprit_first_appearance_chapter: 2    # on-page; gates the "culprit floor"
culprit_first_mention_chapter: 2       # optional; evidence only
victim: edwin-tilley                   # must resolve to a character entity
central_deception: |
  Margaret swapped the tide tables.
clue_schedule:
  - { id: clue-torn-ticket, plant_chapter: 5, pays_off_chapter: 22, necessary: true }
  - { id: clue-tide-table,  plant_chapter: 9, pays_off_chapter: 22, necessary: true }
red_herrings:
  - { id: rh-the-neighbour, plant_chapter: 7, misleads_toward: "the neighbour", must_not_cheat: true }
alibi_grid:
  - { suspect: margaret, chapter: 12, alibi: "at the church fete", holds: false }
  - { suspect: thomas,   chapter: 12, alibi: "on the ferry",       holds: true }
```

**Required fields:** `book`, `total_chapters`, `reveal_chapter`, `culprit`,
`culprit_first_appearance_chapter`.

**Fairplay rules enforced at lock (BLOCKING):**
- `total_chapters` ∈ 1..10000; `reveal_chapter` ∈ 1..total; `culprit_first_appearance_chapter` ∈ 1..total.
- Every `necessary: true` clue must be planted **before** the reveal chapter.
- **Culprit floor:** culprit must first appear by `culprit_by_fraction × total_chapters`
  (default 0.5 → chapter 12 of 24).
- **Auditable gap:** the culprit must have at least one alibi-grid row with `holds: false`
  (an all-`holds: true` culprit is unsolvable → blocked).
- **Existence resolution:** `culprit`, `victim`, and **every** alibi-grid `suspect` id
  must have a home at `series/characters/<id>.static.md` **or**
  `series/continuity/characters/<id>.md`. Presence only — never identity fit.

**Do NOT add a `locked:` field.** The lock is an out-of-band certificate file, never a
field inside the data it gates (a field would be forgeable).

### 3.2 Run configuration — `config/run-config.md` (fenced ```yaml blocks)

Model routing, run-mode flags, escalation thresholds. Parsed by `penny_meta`'s
`parse_yaml_blocks` (not PyYAML). The load-bearing values for testing:

```yaml
# Model-per-role (§7) — the cross-model invariant is DIFFERENCE, not identity:
drafting_model:   claude-opus
final_read_model: codex            # MUST differ from drafting_model, and must not
                                   # appear in any chapter's drafted_by stamp
beta_models:      [codex, hermes, openclaw]

# Run-mode flags (§12):
panel_size:       1                # 1 (fast) | 3 (consensus)
beta_consensus_k: 2                # ≥K-of-M beta models to call a put-down consensus
gate_mode:        strict
ledger_approval:  review           # review = /finalize pauses for diff; auto = commits
book_approval:    review           # review = /assemble pauses for approval; auto = mints cert

# Escalation thresholds (§6):
culprit_by_fraction:         0.5   # read by fairplay_check.py
revision_escalate_personas:  2     # ≥N personas flag a put-down → escalate
would_buy_escalate_count:    3     # ≥N personas "would not buy next" → escalate
thread_dormant_after_chapters: 3
```

> Note: at `panel_size: 1` a put-down can never reach `beta_consensus_k: 2` consensus.
> That is expected fast-mode behaviour, not a bug.

### 3.3 Canon-core — `series/continuity/canon-core.md`

**Always loaded every chapter** — keep it tiny. Markdown with frontmatter and per-section
`<!-- canon-meta: {...} -->` headers read/written by `penny_meta`:

```markdown
---
id: canon-core
type: thread
links: []
---
<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->
# Canon Core — always loaded every chapter

## Protagonist fixed facts
<!-- canon-meta: {id: protagonist-fixed, refs: [cora-mistate], active_window: "1-2", last_referenced: null, reconfirmed_at: null, keep_reason: null} -->
- **Cora Mistate**, 44, recently divorced, relocated to Wreckers Bluff. Outsider.
```

The `fluency_stage` here is cross-checked against the lexicon at lock time (stage drift).

### 3.4 Continuity entries — `series/continuity/{characters,locations,threads}/*.md`

Loaded as a **ledger slice**: only entries named in the chapter brief + their one-hop
`links`. Frontmatter carries `id`, `type`, `links`, and (threads) `last_advanced_chapter`:

```markdown
---
id: the-inheritance
type: thread
links: [the-bluff, cora-mistate]
last_advanced_chapter:        # written by /finalize-chapter; null = no advancement yet
---
# Thread: the inheritance
- Cora inherited the Bluff property from her aunt...
- Status: OPEN.
```

**Static identity** files (`series/characters/<id>.static.md`) are showrunner design
intent (voice fingerprint, arc, secrets) and are distinct from the mutable
`series/continuity/characters/<id>.md` knowledge-state file. **Either** satisfies the
fairplay existence check — so to unblock the shipped `book-01.yaml` you minimally need
`margaret`, `edwin-tilley`, and `thomas` to exist in one of those two locations.

### 3.5 Chapter brief — `series/briefs/book-NN/ch-MM-brief.md` (you must author)

Not shipped. The drafter's primary input. Per the `drafter` agent it provides: beats,
POV, the specific clue/red-herring to plant, the emotional turn, and the ending hook. The
brief is also where the **ledger slice** is named (which continuity entries to load).
`/finalize-chapter` passes this path to `ledger_markers.py`.

### 3.6 Other packs (shipped; swap per project)

- `config/voice-pack/` — `voice-pack.md`, `ai-tics-config.yaml`, `ai-tics-detection.md`
  (the latter two feed `voice_drift.py`).
- `config/setting-pack/` — at least one setting prose pack (`*.md`) + `lexicon.yaml`
  (the data `lexicon_check.py` reads; required keys per term: `term`,
  `narration_ok_from_stage`, `auto_detectable`).
- `config/genre-pack/<genre>.md` matching `series.yaml`, `config/length-profile.md`.
- `config/review-rubrics/*.md` — one per inspector.
- `config/beta-readers/personas/*.md` — the six blind reader lenses.

---

## 4. The approval gates (what actually blocks)

Every gate is **deterministic** (`scripts/`), never an LLM judgment, and fails loud with
a named predicate + non-zero exit. This is the whole point of the architecture — it
survives the "soft gate" weakness of an LLM-graded pipeline.

| # | Gate (command) | Enforced predicate | On failure |
|---|---|---|---|
| 1 | `preflight.py lock-mystery NN` | fairplay (§3.1) **and** lexicon schema + stage-drift all pass | No lock written; exits non-zero. This is the **sole writer** of the mystery lock. |
| 2 | `preflight.py draft NN MM` | ledger present + populated **and** `.penny/locks/book-NN.mystery.lock` exists | `/draft-chapter` aborts before context assembly. |
| 3 | `review_gate.py` (`/review-chapter`) | panel DECISION: **PASS iff zero `^BLOCKING:` lines** across the 5 inspector verdicts, else **HOLD** | Writes `ch-MM.gate.md` (`gate: PASS`/`HOLD`), prints `GATE: …`. Exit 0 = gate *evaluated*; non-zero = operational error. |
| 4 | `preflight.py finalize NN MM` | `ch-MM.gate.md` exists **and** shows `gate: PASS` | `/finalize-chapter` aborts; resolve the HOLD first. |
| 5 | `ledger_approval` pause (`/finalize-chapter`) | `review` → pause at `LEDGER-REVIEW`; showrunner inspects diff, resumes with `--commit` | Not a hard gate — a human review checkpoint. `auto` commits end to end. |
| 6 | `preflight.py assemble NN` | `final_read_model != drafting_model` **and** `final_read_model ∉ drafted_by` set **and** (if artifact present) `read_by ∉ drafted_by` | `/assemble-book` aborts before the final read; fix routing in run-config. |
| 7 | `assemble_book.py validate-read NN` | `schema: penny-final-read/1`, a `read_by` stamp, and `standalone`/`mystery_resolved`/`thread_left_open` each exactly `yes` or `no` (**no hedging**) | Aborts; re-dispatch the final-reader. |
| 8 | `book_approval` pause (`/assemble-book`) | `review` → pause at `BOOK-REVIEW`; showrunner approves with `--approve` | `auto` proceeds straight to sealing + cert. |
| 9 | `preflight.py approve-book NN` | manuscript exists + valid final-read + `read_by ∉ drafted_by` + revision-priority report exists | **Last write** mints `.penny/locks/book-NN.approved`. No failure path leaves a cert. |

**The `^BLOCKING:` convention (gate 3):** a line beginning `BLOCKING:` at **column 0** of
any inspector verdict is *the* blocker. It is counted identically by `review_gate.py`,
`penny_verdict.count_blocking`, and the status line's grep. A cross-consistency test pins
this; don't fork it.

**Cross-model independence (gates 6, 7, 9):** the final read and beta read must be done by
a model that did **not** draft. The invariant is *difference*, enforced at three points
as defense-in-depth. `drafted_by` stamps come from chapter frontmatter; `read_by` from the
final-read frontmatter.

---

## 5. Artifacts at each stage

Per chapter, under `output/book-NN/chapters/`:

```
ch-MM.draft.md       → /draft-chapter   (frontmatter: drafted_by)
ch-MM.reviews/       → /review-chapter  (5 inspector verdicts + 2a checker outputs)
ch-MM.gate.md        → review_gate.py   (gate: PASS|HOLD)
ch-MM.lineedit.md    ┐
ch-MM.copyedit.md    ├ /finalize-chapter
ch-MM.ledger-diff.md │  (per-thread advanced: yes/no)
ch-MM.final.md       ┘  ← the promoted chapter
```

Per book, under `output/book-NN/`:

```
book-NN.manuscript.md   → assemble  (three states: assembled → read → blessed)
book-NN.final-read.md   → final-reader agent (schema: penny-final-read/1)
reports/<persona>.converged.md  → /beta-read (six personas)
reports/revision-priority.md    → revision_priority.py (deterministic aggregate)
```

Runtime state (gitignored) in `.penny/`: `current-stage` (drives the status line) and
`locks/` (the mystery lock and the approval certificate).

---

## 6. A minimal live test recipe (Book 1)

```bash
# 0. Author the missing inputs first (see §2.0):
#    - character entities for margaret, edwin-tilley, thomas
#    - at least one chapter brief: series/briefs/book-01/ch-01-brief.md

# 1. Lock the mystery (gate 1). Must print nothing + exit 0; mints the lock.
python3 scripts/preflight.py lock-mystery 01

# 2. Drive one chapter through the pipeline (each command runs its gate first):
#    /draft-chapter 01 01
#    /review-chapter 01 01        → expect GATE: PASS (or HOLD with blocking list)
#    /finalize-chapter 01 01      → pauses at LEDGER-REVIEW (ledger_approval: review)
#    /finalize-chapter 01 01 --commit

# ...repeat draft→review→finalize for every chapter...

# 3. Beta read the assembled text (non-blocking), then assemble the book:
#    /beta-read output/book-01/book-01.manuscript.md
#    /assemble-book 01            → assembles, cross-model final read, builds report,
#                                   pauses at BOOK-REVIEW
#    /assemble-book 01 --approve  → seals + mints .penny/locks/book-01.approved
```

A successful run ends with `.penny/locks/book-01.approved` present. That certificate —
minted only after every precondition above passed — *is* the MVP-1 pass condition.

> **First-run caveat:** the book loop and the `final-reader` agent have no validated live
> run yet. The deterministic scaffolding is well-tested (221 passing), but **agent
> judgment quality is unproven** until a real assembled book runs through. Treat the first
> `/assemble-book 01` as a shakedown, not a validated result.
