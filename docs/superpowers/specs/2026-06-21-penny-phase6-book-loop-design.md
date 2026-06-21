# Penny Phase 6 — Book Loop (per-book assembly + final read + revision-priority report)

Saved: 2026-06-21 | Status: design approved, pending spec review
Supersedes nothing. Implements the per-book flow of `penny-design-v3.md` §5
(lines 375-393), §7 (cross-model routing), §10 (beta feeds the report), and
P0.6/P0.7/P0.8. Demotion hook per `2026-06-20-penny-canon-core-demotion-design.md`
§7.1.

## 1. Goal & scope

Phase 6 is the last MVP-1 mile: turn gate-PASSed, finalized chapters into a
finished, cross-model-reviewed `book-NN.manuscript.md` and the showrunner-facing
artifacts that gate its approval (P0.8).

**One spec, five units, sequenced so each is independently testable:**

1. **Manuscript producer** — `scripts/assemble_book.py` (deterministic)
2. **Pre-flight gate** — `preflight.py assemble` (built Phase 3; Phase 6 *wires* it)
3. **Final holistic read** — `.claude/agents/final-reader.md` (cross-model agent) +
   `penny-final-read/1` shape contract + deterministic validator
4. **Revision-priority report** — `scripts/revision_priority.py` (deterministic aggregator)
5. **Book approval** — `/assemble-book` command pause + `book-NN.approved` certificate +
   reserved demotion hook

Orchestrated by `.claude/commands/assemble-book.md`.

### Decided scope trims (from brainstorm)

- **Standalone-vs-arc is folded into the final read** — one cross-model holistic read
  answers all three questions (holds together / mystery resolved / right personal
  thread left open). **Fold the work, not the signal:** the standalone-vs-arc answer is
  emitted as discrete structured fields in the final-read output, never buried in prose,
  because P0.7's acceptance criterion is a discrete check and the P0.8 gate keys off it.
- **Demotion hook is a reserved no-op** with a *defined invocation signature* (not a
  comment), per design §10 (833-835) and demotion spec §7.1. No behavior behind it.
- **Revision-priority report is NOT trimmed** — it is the one genuinely-new orchestration
  in Phase 6 (everything else is assembly plumbing) and gets first-class treatment.

### Out of scope

- EPUB compile / proof agent (POST-MVP1).
- Any actual demotion *behavior* (Phase 8; §7.1 — coldness cannot fire on Book 1).
- The final-reader's *judgment quality* (UAT, like all Penny agents — unproven until a
  real assembled book runs through; treat first live run as a shakedown).

## 2. Architecture — the deterministic-vs-agent split

Governing rule (CLAUDE.md): scripts **never make an LLM judgment**; agents judge;
commands orchestrate. Phase 6 is deliberately deterministic-heavy — only Unit 3 is a
genuine taste judgment.

| Unit | Layer | Artifact |
|---|---|---|
| 1. Manuscript producer | deterministic — `scripts/assemble_book.py` | `book-NN.manuscript.md` |
| 2. Pre-flight gate | deterministic — `preflight.py assemble` (built) | exit code |
| 3. Final holistic read | **agent** — `.claude/agents/final-reader.md` (cross-model) | `book-NN.final-read.md` |
| 4. Revision-priority report | deterministic — `scripts/revision_priority.py` | `reports/revision-priority.md` |
| 5. Book approval | command pause + certificate | `.penny/locks/book-NN.approved` |
| orchestrator | command — `.claude/commands/assemble-book.md` | — |

### Why the report is deterministic (the most important call)

Escalate-vs-log is **threshold arithmetic over three already-structured inputs**
(cross-persona put-down counts, would-buy-next tallies, accumulated score spreads).
None of it requires reading prose. An agent here would reintroduce exactly the
soft-judgment failure mode P0.8 exists to prevent — a model summarizing "this looks
mostly fine" over a tally that, read literally, crosses an escalation threshold. The
showrunner must be able to trust the report did not get talked out of an escalation.

**Constraint (load-bearing):** the script escalates on the **raw threshold crossing,
never on a derived "severity score" it computes itself.** The moment it weights or
blends signals, judgment is smuggled back into a deterministic layer and auditability is
lost. Every escalation line traces to a **specific named rule that fired** plus its raw
counts, so the showrunner sees *why* it escalated, not just *that* it did. Rules are
legible in the output, not merely applied.

### Why the `penny-final-read/1` shape contract is non-negotiable

It is the direct cost of folding standalone-vs-arc into an agent's holistic read. Once
those three answers live inside prose, the only thing stopping them from silently
degrading is a shape contract. Discrete enumerated fields + a validator that hard-fails
a malformed read is what stops a vague read sliding through P0.8. Judgment in the agent,
shape enforced by script — the same division the whole system runs on.

## 3. Unit-by-unit data flow

### Unit 1 — `scripts/assemble_book.py` (manuscript producer)

The manuscript file has **one path but three states**, which resolves the §5-flow
paradox (the manuscript is both the final-read's *input* and the listed *endpoint*):

```
assemble  → book-NN.manuscript.md  [state: assembled]  ← final-reader & /beta-read read THIS
seal (after final read PASS)       [state: read]        ← read_by stamped in
approve   → mint .approved cert     [state: blessed]     ← MVP1 endpoint
```

**Subcommand `assemble NN`:**
- **In:** `output/book-NN/chapters/ch-*.final.md` (sorted).
- **Asserts (fail loud, `assemble_book: <predicate>`, nonzero):** chapters contiguous
  `01..N` with no gaps; at least one chapter; each `.final.md` carries `drafted_by`
  frontmatter; if `output/book-NN/outline.md` declares a chapter count, it matches.
- **Out:** `output/book-NN/book-NN.manuscript.md` —
  - frontmatter: `schema: penny-manuscript/1`, `book: NN`, `chapters: N`,
    `drafted_by: [union of per-chapter stamps]`, `assembled_at: <iso8601>`.
  - `read_by` is **absent at assembly** (stamped by `seal`).
  - body: chapter bodies (per-chapter frontmatter stripped) joined with chapter headings.

**Subcommand `seal NN`:**
- Reads `read_by` from `book-NN.final-read.md`; re-asserts `read_by ∉ drafted_by`
  (delegating to the preflight membership check); stamps `read_by` into the manuscript
  frontmatter. Deterministic + **idempotent** (re-seal with the same value is a no-op,
  not an error). This honors design's "manuscript carries `read_by`" without the agent
  mutating the manuscript.
- **Fail loud:** `final-read.md` absent, no `read_by` stamp, or `read_by ∈ drafted_by`.

### Unit 2 — pre-flight (built; Phase 6 wires it)

`preflight.py assemble NN`, run as the gate **between assembly and the final read**. No
code change. Already enforces (§7): config invariant `final_read_model != drafting_model`;
set-membership `final_read_model ∉ {drafted_by stamps}`; and when `final-read.md` exists,
`read_by ∉ drafted_by`.

### Unit 3 — `final-reader` agent (cross-model) + `penny-final-read/1`

The final read is **QC, not a reader-proxy**, so — unlike the blind beta readers (which
get *nothing* but text) — it is **informed**:
- **In:** `{ manuscript_text, mystery_solution (book-NN whodunit), arc-ledger slice
  (which threads are the series hooks) }`. Rationale: `mystery_resolved` is far more
  reliable against ground truth; `thread_left_open` *requires* knowing which thread is
  the intended series hook (unjudgeable from prose alone). Cross-model "drawer time"
  value is preserved because the model did not *draft* the prose — seeing the solution
  does not compromise that independence.
- **Out:** `output/book-NN/book-NN.final-read.md`, `schema: penny-final-read/1`:
  - **required, enumerated** booleans (validator hard-fails a hedge like `"mostly"`):
    `standalone: yes|no`, `mystery_resolved: yes|no`, `thread_left_open: yes|no`.
  - `read_by: <model>`.
  - separate prose fields, kept *alongside* the booleans, never in place of them:
    `## Holistic verdict` (the qualitative cross-model taste read — the reason the pass
    exists) and `## Standalone-vs-arc notes` (the prose backing the three booleans).

**`validate_final_read()`** — a deterministic function in `scripts/assemble_book.py`
(which already reads `final-read.md` in `seal`), exposed as subcommand
`assemble_book.py validate-read NN`. Enforces the shape: every boolean present and in
`{yes, no}`, `read_by` present, schema correct. A malformed read fails loud rather than
silently passing the approval gate.

### Unit 4 — `scripts/revision_priority.py` (the aggregator)

Pure reader; raw-threshold rules; every line traceable.
- **In:** all `output/book-NN/reports/<persona>.converged.md` (the 6 Phase-5 outputs) +
  all `output/book-NN/chapters/ch-*.gate.md`.
- **Rules (each fires independently; no blending, no severity score):**
  - `cross_persona_putdown`: for each chapter, count **distinct personas** reporting a
    put-down there (from `put_down_points.consensus` ∪ `.logged`); if
    `≥ revision_escalate_personas` → **ESCALATE**, else **LOG**.
  - `would_buy_no`: sum `would_buy_next.tally.no` across personas; if
    `≥ would_buy_escalate_count` → **ESCALATE**.
  - `score_spread`: every `score_spread_log` entry in any `ch-*.gate.md` → **LOG**
    (already SOFT per design §6 line 465; surfaced for visibility, not auto-escalated).
- **Out:** `output/book-NN/reports/revision-priority.md`, `schema:
  penny-revision-priority/1`, frontmatter `escalations: <count>`, two sections
  `## ESCALATE` / `## LOG`. **Every line names the rule + raw counts**, e.g.
  `- [put-down] ch.7 — rule cross_persona_putdown>=2 (3 personas: impatient-skimmer, cozy-loyalist, arc-reader)`.
- **Non-blocking, exit 0.** The escalations never fail the run; they inform the human gate.
- The final-read booleans are **NOT** folded in here — they are a parallel gate input to
  approval, keeping this report exactly the three beta/inspection signals.

### Unit 5 — book approval (command pause + cert + demotion hook)

- `/assemble-book NN` presents **two** artifacts to the showrunner: the final-read
  booleans + prose, and `revision-priority.md`. It then **pauses** (human gate; default
  `review`, mirroring `ledger_approval`).
- On `/assemble-book NN --approve`: a new deterministic precondition subcommand
  `preflight.py approve-book NN` asserts manuscript present + `final-read.md` valid shape
  (reusing `validate_final_read`) + `read_by ∉ drafted_by` + `revision-priority.md`
  present, and — as the sole writer of the cert, mirroring `lock-mystery` — mints
  `.penny/locks/book-NN.approved` as its last write. The **human invocation IS the approval**;
  the certificate records that the mechanical preconditions were green when they said go.
  Out-of-band certificate, same pattern as the mystery lock (never a field inside the
  data it gates). Reserves the POST-MVP1 EPUB gate for free.
- **Demotion hook (reserved no-op, defined signature):** at book-close the command calls
  `scripts/canon_core_review.py --book NN --canon-core series/continuity/canon-core.md`,
  which **exists, takes those exact args, and returns an empty candidate list** — the
  Phase-8 shape `{id, fact, last_referenced, active_window, verdict, proposed_target}`,
  empty now. The interface is pinned so Phase 8 fills the body without an engine edit
  (which is the Option-A violation the reservation avoids).

## 4. Error handling

Every deterministic script fails loud with a **named predicate + nonzero exit**
(`assemble_book: <predicate>`, matching `preflight: …`). Agents and the report are
non-blocking; only the gates (preflight, validator, approval preconditions) hard-fail.

| Unit | Hard-fail (nonzero) | Non-blocking / soft |
|---|---|---|
| assemble | chapter gap, zero chapters, `.final.md` missing `drafted_by`, outline count mismatch | — |
| seal | `final-read.md` absent / no `read_by`, `read_by ∈ drafted_by` | idempotent re-seal = no-op |
| preflight (built) | config invariant, `read_by ∈ drafted_by` | — |
| final-read validator | missing/non-enum boolean (the hedge), missing `read_by`, bad schema | empty prose field = warn |
| revision_priority | malformed converged JSON / unreadable gate.md | escalations never fail the run (exit 0) |
| approval | preconditions not green when `--approve` given | absent cert = "not yet approved" (a state) |
| demotion hook | — | always no-op, returns empty (Phase 6) |

## 5. Testing strategy

Test-first against `tests/fixtures/`, per CLAUDE.md.

- **Fixtures:** a synthetic `book-99/` tree reused across unit tests — a handful of stub
  `ch-*.final.md` (distinct `drafted_by` stamps), 6 `<persona>.converged.md` (one rigged
  to cross the put-down threshold, one to the would-buy threshold, one clean), and
  `ch-*.gate.md` with a `score_spread_log` entry.
- **assemble_book:** golden-file test on the produced manuscript (ordering, stripped
  frontmatter, aggregated `drafted_by` set); gap / empty / missing-stamp fail tests;
  `seal` stamps `read_by` + idempotency + `read_by ∈ drafted_by` rejection.
- **final-read validator:** enum-pass; hedge-reject (`"mostly"` → fail); missing-field
  reject; missing-`read_by` reject.
- **revision_priority (load-bearing):** threshold-boundary cases (N-1 personas → LOG,
  N → ESCALATE); would-buy boundary; spread → LOG-only; **rule-traceability** (assert
  each emitted line names its rule + raw counts); all-clean fixture → empty ESCALATE.
- **demotion hook:** Phase-6 invocation with the exact `--book/--canon-core` args returns
  an empty candidate list.
- **Cross-consistency tests** (so conventions cannot fork, per CLAUDE.md):
  - the `penny-final-read/1` envelope agrees with everything that reads it (validator +
    approval precondition parse the same fields);
  - `revision_priority` parses the *exact* `put_down_points` / `would_buy_next` shape
    `beta_report.write_converged` emits — a test that builds a converged report via
    `beta_report` and feeds it straight into the aggregator, so the two cannot drift.

**Not tested (scope guard):** the final-reader's judgment quality (UAT); any actual
demotion behavior (Phase 8).

## 6. New config / run-mode flags

Added to `config/run-config.md` (the swappable layer — never hardcoded):

```yaml
revision_escalate_personas: 2   # >=N distinct personas flag a put-down at a chapter -> escalate
would_buy_escalate_count:   3    # >=N personas say "would not buy next" -> escalate
book_approval:              review   # review (pause for showrunner) | auto
```

`final_read_model` already exists (§7). No churn beyond these three.

## 7. Build sequence (each unit testable as built)

1. `scripts/assemble_book.py` (`assemble` + `seal` + `validate_final_read`) — pure
   plumbing, testable with stub chapters.
2. Wire `preflight.py assemble` as the pre-read gate in the command.
3. `.claude/agents/final-reader.md` + `penny-final-read/1` validator — the merged read
   emitting the standalone-vs-arc structured fields.
4. `scripts/revision_priority.py` — the aggregator; built last because it integrates the
   beta-layer output + per-chapter gate logs (its dependencies already in place).
5. `.claude/commands/assemble-book.md` orchestrator + approval cert
   (`preflight.py approve-book`) + reserved `scripts/canon_core_review.py` no-op stub +
   the three run-config flags.

The genuinely-new logic (the aggregator) lands with its dependencies already built.
```
