# Penny Phase 3 — Mystery + Cross-model: Design Specification

> **Status:** Approved design (brainstormed 2026-06-20). Source: `penny-design-v3.md`
> §5a (per-book pre-flight), §7 (model routing / cross-model drawer time), §13.3
> (build order). Supersedes the build-order item's "`/scripts` adapters" wording:
> the cross-model alternate is **Codex via the official Codex plugin for Claude
> Code**, not a hand-rolled API adapter (see §7 below).

## 1. Purpose

Phase 3 turns on the **mystery authorship pipeline** and the **deterministic
pre-flight gates** that protect it, and records **Codex-via-plugin** as the
cross-model alternate. It is the phase where `fairplay_check.py` and
`inspector-fairplay` (built in Phase 2b) start running against real per-book
ledgers, and where the §7 independence invariant (a different model reads the book
than drafted it) gains its deterministic guard.

The organising idea is a **certificate**: the per-book mystery transitions once
from mutable to frozen, the expensive semantic validation runs at exactly that
transition, and the lock file it mints is a trust token meaning *"the heavyweight
gates passed."* Every downstream check is cheap because it only confirms the
freeze happened — and the only code path that can write the lock is the one that
ran the validators first, so the certificate cannot be forged.

## 2. Scope

**In scope:**
- `/plan-mystery N` command + `mystery-planner` sub-agent (§5a authorship flow).
- `scripts/preflight.py` — one tool, three subcommands (`lock-mystery`, `draft`,
  `assemble`), all built and tested this phase.
- Culprit/victim/suspect **existence-resolution** added to `fairplay_check.py`,
  BLOCKING at lock time.
- `/draft-chapter` wired to the draft-time pre-flight gate.
- The §7 routing guard (`assemble`) built and **fixture-tested** now; recorded
  cross-model alternate = Codex via plugin.
- `lexicon_check.py --validate` wired into the lock-time path (schema mode only).

**Out of scope (named so they do not leak in):**
- Any **runtime cross-model code**. The live final-read is a *documented manual*
  Codex plugin/CLI step; its call site is the Phase 6 `assemble-book` command.
  **Zero runnable cross-model code ships in Phase 3.**
- The `assemble-book` command itself (Phase 6). Only the `assemble` *assertion* +
  its unit tests ship now.
- voice_drift carry-forwards (`density_per_1k` keyed by `tic_id`,
  `same_domain_flag_at`) — Phase 4 prose work.
- canon-core demotion machinery — Phase 8.
- self-audit / line-edit / copy-edit — Phase 4.
- beta readers — Phase 5.

## 3. The certificate spine (architecture)

Validation runs at **two moments**, related as *validate-once-then-freeze,
gate-cheaply-thereafter*:

1. **Lock-time pre-flight** (heavy, at `/plan-mystery`, the mutable→frozen
   transition): run `fairplay_check.py` (numeric fairness + id existence) **and**
   `lexicon_check.py --validate` (lexicon schema). Only if both pass is the lock
   written.
2. **Draft-time pre-flight** (light, at every `/draft-chapter`): confirm the lock
   exists and the ledger is populated. No fairness re-audit, no LLM judgment — a
   pure file check, because the lock already certifies validation passed.

The lock file is the **trust token** between the two moments. Because the only
code path that writes it is the validated path, draft-time can trust it without
re-checking. This is why the `locked:` field is **removed** from the ledger yaml:
a hand-toggleable field is a *forgeable certificate* (it would let a mystery be
marked frozen that never passed fairplay); an out-of-band file written only by the
validated path cannot be forged that way.

## 4. Components

### 4.1 `scripts/preflight.py` — one tool, three subcommands

Deterministic structural gates that do not trust the LLM. Shares helpers:
frontmatter-stamp reading, `run-config.md` reading (via `penny_meta`), and the
existing `sys.exit("preflight: <named predicate>")` failure convention used across
the script layer. The three subcommands are one cohesive tool because they are the
same *kind* of thing and share the same provenance-reading helpers.

| Subcommand | Weight | Behaviour | Wired this phase |
|---|---|---|---|
| `lock-mystery N` | heavy | invokes `fairplay_check` + `lexicon_check --validate`; **sole writer of the lock** | yes — `/plan-mystery` |
| `draft N CH` | light | lock-file present **and** ledger populated; pure file check | yes — `/draft-chapter` |
| `assemble N` | light | routing config-invariant + reality-check (see §7) | **no — built + fixture-tested only; call site Phase 6** |

### 4.2 `fairplay_check.py` — existence-resolution

Gains presence-resolution for `culprit`, `victim`, and every `alibi_grid[].suspect`:
each id must glob to a `series/characters/<id>.static.md` **or**
`series/continuity/characters/<id>.md` file (static-or-continuity). Unresolvable →
the checker's existing `BLOCKING:` line (consumed by `lock-mystery` as a lock
failure). The pre-existing numeric audit (culprit on-page by `culprit_by_fraction`,
necessary clues plant-before-payoff, reveal ordering) is unchanged.

**Existence only, never identity correctness.** At lock time the resolver answers
"does an entity with this id have a home" — a file-presence glob. It must NOT judge
whether the culprit is plausible, whether their static file's secrets support the
deception, or any semantic fit. That is showrunner taste (at the core-setting step)
or review-time inspection, not a deterministic lock gate. Same discipline as
`--validate`: presence at lock, semantics elsewhere. The resolver checks the id has
a home; it does not read what is in the home.

### 4.3 `lexicon_check.py --validate` at lock time — schema only

`--validate` at lock is the **structural/schema** check only: every row has its
required fields, `narration_ok_from_stage` is a legal stage value, `freq_cap`
parses, no malformed entries. This is the "lexicon cannot be malformed when
drafting begins" guarantee, deterministic, so it belongs at lock. It is kept
strictly distinct from the **review-time runtime enforcement** (a BELONGING-tagged
term appearing in later-book narration is a reviewer flag — §9; a per-chapter
concern against actual drafted prose). Same file, two modes — mirroring how
`fairplay_check` is structural at lock but does its real clue-payoff audit against
text at the gate. `--validate` must not grow into prose-checking; it has no prose
to check yet.

### 4.4 `.claude/commands/plan-mystery.md`

Orchestrates the §5a authorship flow and the §5 certificate write-order (§5 below).

### 4.5 `.claude/agents/mystery-planner.md`

Given the showrunner's irreducible core (who/why/central deception/arc
constraints), proposes the clue schedule, red herrings (mislead-but-don't-cheat),
and alibi grid — the heavy combinatorial craft. It consumes the core; it never
writes from a drafter's seat and the sealed solution is authored by the command,
not handed to any drafter.

### 4.6 `.claude/commands/draft-chapter.md`

New **step 0**: run `preflight.py draft N CH`; a non-zero exit aborts before any
context assembly or drafting. The rest of the Phase-1 draft flow is unchanged.

## 5. Data flow — the certificate write-order

`/plan-mystery N`:
1. Showrunner sets the irreducible core (interactive; taste-and-strategy layer).
2. `mystery-planner` proposes the construction → written to
   `series/whodunit/book-NN.yaml` as the **proposed, unlocked** ledger.
3. `preflight.py lock-mystery N` validates the on-disk yaml: `fairplay_check`
   (numeric + existence) **and** `lexicon_check --validate` (schema). Either fails
   → **exit non-zero, no lock written**. The unlocked yaml remains on disk, and
   `draft N CH` correctly rejects it.
4. On pass, the showrunner reviews and approves (taste).
5. Commit, in order: write `output/book-NN/mystery-solution.md` (the sealed answer
   key), then **write `.penny/locks/book-NN.mystery.lock` last**.

**Invariant:** a lock file never exists beside a ledger that did not pass both
validators. **The lock is written strictly last**, after both validators passed and
the showrunner approved.

**Implementation choice — write-yaml-in-place-unlocked.** The proposed ledger is
written to its real path before validation (so the validators have an on-disk
artifact to read), and only the lock is written after. A failed run therefore
leaves an unlocked-but-present yaml — which is the *desired* state, because
draft-time pre-flight rejects exactly that. (The temp-and-move alternative was
considered and rejected as unnecessary complexity given this property is wanted.)

**Re-planning** preserves the invariant for free: delete the lock, re-validate,
re-write the lock — the clean re-lock story §5a promised. Drafting never silently
mutates the solution.

`/draft-chapter N CH`: step 0 runs `preflight.py draft N CH`; proceeds to the
existing draft flow only on exit 0.

## 6. Solution isolation (§5a, carried)

`/plan-mystery` writes the full `mystery-solution.md` sealed; the drafter receives
**only the current chapter's clue-planting obligations**, never the solution. Beta
and final readers never receive it either. This is command/agent-instruction
discipline (Option A); the deterministic engine guarantees the *lock*, not the
sealing, which is a structural sub-agent-boundary property.

## 7. Cross-model — Codex via plugin, and the §7 routing guard

**Alternate model = Codex via the official Codex plugin for Claude Code**
(`openai/codex-plugin-cc`). This supersedes design §7's "`/scripts` adapter"
shell-out and §13.3's "`/scripts` adapters"; **Hermes/OpenClaw drop out**.
`run-config.md` keeps `final_read_model: codex`; the *mechanism* is a plugin/CLI
invocation from command instructions, not a Python adapter. The plugin's packaged
`/codex:review` is tuned for code, so Penny's prose passes call Codex with the
`{text, rubric, ledger_slice}` prose-review prompt (CLI or general delegation
path); to be verified at the Phase 6 call site. The `[ENGINEERING]` open item
shrinks to "install plugin + Codex credential + Codex CLI present" — self-serve.

**No runtime cross-model code ships in Phase 3.** The live final-read is a
documented manual step whose only obligation back to the engine is writing
`read_by: codex` provenance. Its call site is the Phase 6 `assemble-book` command.

**The `assemble N` routing guard (built + fixture-tested now):**
1. **Config-invariant:** `final_read_model != drafting_model` in `run-config.md` —
   deterministic string comparison. Hard-fail catches misconfiguration.
2. **Reality-check (set membership):** collect every chapter's `drafted_by` stamp,
   dedupe, assert `final_read_model ∉ {drafted_by stamps}`. Catches config-vs-reality
   drift and the mid-book-swap case.

Provenance rides along on existing artifacts (`drafted_by` in chapter frontmatter,
`read_by` in the final read's output) — no new write step.

**Why build the guard now, three phases before its call site:** the assertion is
pure deterministic comparison with zero dependency on `assemble-book`, a real book,
or a reachable Codex. Deferring the code defers no difficulty — only the test
coverage of an invariant that is load-bearing for the whole independence guarantee.
It is cohesive with the other two subcommands (shared stamp/config helpers) and is
the consumer of the same provenance contract the mystery-pipeline fixtures already
produce.

## 8. Error handling

Every gate is non-zero-exit + a named predicate, e.g.:
- `preflight: no lock for book 01`
- `preflight: ledger unpopulated`
- `preflight: final_read_model equals drafting_model`
- `preflight: final-read model 'codex' appears in drafted_by set`

`lock-mystery` surfaces the underlying `fairplay`/`lexicon` failures verbatim. No
subcommand makes an LLM judgment — all survive Option A's soft-gate weakness.

## 9. Testing

- **preflight `lock-mystery`:** pass → lock written; fairplay-fail → no lock;
  lexicon-fail → no lock; existence-fail → no lock; **lock strictly last** (a
  failure after the yaml write leaves yaml-but-no-lock).
- **preflight `draft`:** locked → exit 0; unlocked → non-zero; missing yaml →
  non-zero; populated-but-no-lock → non-zero.
- **preflight `assemble`** (fixture configs + fixture frontmatter, no real
  `/output` tree): green case; `read_by` collides with a drafter (named-predicate
  fail); config-invariant fail (`final_read_model == drafting_model`); and the
  **drift fixture** — config declares a valid `!=` split, but the chapter
  `drafted_by` stamps reveal the configured final-reader already drafted chapters.
  The drift fixture is mandatory: without config-and-stamps disagreeing in the
  dangerous direction, only the config-invariant is tested and the reality-check
  rides along untested.
- **fairplay existence:** resolves via static; resolves via continuity;
  unresolvable culprit → BLOCKING; unresolvable suspect → BLOCKING; existence-only
  (a resolvable-but-implausible culprit does NOT flag — no semantic judgment).
- **command/agent scaffold tests:** `plan-mystery.md` + `mystery-planner.md` exist
  with required frontmatter/sections (mirrors `test_inspector_scaffold.py`).
- `series/whodunit/book-01.yaml` is reframed as a **fixture**: its ids
  (`margaret`, `edwin-tilley`, `thomas`) resolve only via fixture character dirs in
  the test corpus; the `locked:` field is removed.

## 10. Files

**New:** `scripts/preflight.py`, `.claude/commands/plan-mystery.md`,
`.claude/agents/mystery-planner.md`, `tests/test_preflight.py`, test fixtures.

**Modified:** `scripts/fairplay_check.py` (existence-resolution),
`.claude/commands/draft-chapter.md` (step 0 pre-flight),
`series/whodunit/book-01.yaml` (drop `locked:`), `tests/test_fairplay_check.py`.

**Doc:** the §7 / build-order rewrites in `penny-design-v3.md` (Codex-via-plugin,
Hermes/OpenClaw dropped) are folded into the **implementation plan** and applied
when we build — not edited mid-brainstorm.

## 11. Out-of-scope carry-forwards (recorded, not built)

From prior phase reviews, still standing and explicitly NOT Phase 3 work:
`density_per_1k` is tic-specific (Phase 4 voice work); `same_domain_flag_at` in
`ai-tics-config.yaml` is an unused Phase-3-adjacent seed (leave dormant); the
canon-core demotion `active_window` seed is Phase 8 (the `canon-meta` header
convention already adopted — keep using it if canon-core structure is touched).
