# Developmental Editor — per-chapter craft review (design)

**Date:** 2026-06-27
**Status:** approved-pending-spec-review
**Design refs:** §5 (pipeline), §6 (review contract), §8 (structure), §10 (beta).
Supersedes nothing; adds a new role.

## Problem

A careful human read of the **finalized** Book-01 ch-01 surfaced craft failures the
pipeline never flagged:

- **No sense of place** — Geelong, Brunswick, Pelican's Crook are named but never made
  real; the reader is never grounded in coastal Victoria / Melbourne.
- **Buried motivation** — *why* Maggie moved, *why* pottery, the divorce that should drive
  the move — all compressed into one or two sentences.
- **Inert detail** — prose spent on invoices, kiln/studio technicalities that earn nothing.
- **Dry scenes** — the first Maggie–Cal meeting has no subtext, friction, humour, or nuance.

These are **developmental** problems — "does this chapter work *as reading*?" None of the
five blind inspectors own them. `inspector-structure` judges plot *shape* (tension curve,
hook, thread liveness); `inspector-voice` judges sentence-level *drift/flatness*;
`inspector-ai-prose` judges rote AI tells. The experiential, scene-level craft read — the
**developmental edit** — is simply missing. In publishing the edit stack is
**developmental → line → copy**; Penny shipped a `line-editor` and a `copy-editor` but
skipped the senior pass above them. So today the line/copy polish is spent on chapters
whose *story* isn't settled — and ch-01 was finalized while still, effectively, a first
draft.

## Goal

Add the missing **developmental-editor** role: a context-rich, per-chapter craft read that
runs **at review time, on the draft**, produces an actionable editorial report, and gates
the finalize polish until a human clears it.

## Decisions (locked with the showrunner)

1. **Advisory toward the gate verdict; hard precondition for finalize.** The dev editor
   never emits `^BLOCKING:`, so it cannot flip the review gate to HOLD on subjective taste
   (no false holds from a soft LLM judgment — consistent with Penny's distrust of soft
   gates). But the line and copy editors do **not** run until the developmental read is
   **cleared**.
2. **Context-rich, not blind.** Unlike the five inspectors (deliberately starved of context
   so they can't rationalize), the dev editor gets the `setting-pack`, a `character-bible`
   slice, and the **chapter brief/intent** — a real developmental editor knows what the
   chapter is trying to do. It is **denied the whodunit solution** — craft review doesn't
   need it, so fair-play is not exposed.
3. **Diagnoses, never rewrites.** The dev editor emits an editorial letter (scores + margin
   notes), like a real developmental editor. Revision — new writing — flows back to the
   `drafter`, not a mechanical refiner. (Contrast: line/copy editors modify prose in place.)
4. **Showrunner clears it.** Clearance is a deliberate human act, not an automatic score
   threshold. You may clear-as-is ("noted, proceeding") or revise the draft first and
   re-clear.
5. **Eight rubric dimensions** (below), obligation-aware. The editorial letter writes margin
   notes **only for dimensions that score low** — full-coverage scoring, no bloat on
   dimensions the chapter already nails.
6. **Cross-model is a hard precondition.** The dev read must run on a non-drafting model; if
   none is available, `/review-chapter` halts loud rather than degrading to a same-model
   read. (A same-model "fresh eyes" read is a soft gate — rejected on principle.)

## Role differentiation (for the record)

| | Developmental *(new)* | Line *(exists)* | Copy *(exists)* |
|---|---|---|---|
| Asks | Does it work as reading? | Does each sentence land? | Is it correct/consistent? |
| Altitude | Scene & chapter | Sentence | Character (glyph) |
| Touches prose? | **No — advises** | Yes — rewrites | Yes — corrects |
| When | Review, on the draft | Finalize, post-PASS | Finalize, post-line |
| Context | setting-pack + bible slice + brief | voice-pack + length | style-sheet only (blind) |
| Output | `developmental-edit.md` report | revised `.lineedit.md` | corrected `.copyedit.md` |

vs. the existing **reviewers**: the five inspectors judge compliance + narrow craft,
**blind**, and **block** the gate; the beta-reader judges whole-book *experience*, blind,
post-assembly, non-blocking. The dev editor fills the empty cell: **per-chapter,
context-rich, actionable craft notes — before the polish is spent.**

## The pipeline change

```
draft → review-chapter (5 inspectors + dev editor) → ⟨DEV CLEARANCE⟩ → finalize (line → copy → ledger → promote)
```

`preflight finalize N CH` today blocks unless `gate: PASS`. It gains a **second deterministic
precondition**: a valid **dev-clearance certificate** for this chapter must exist.

## Components

### 1. `.claude/agents/developmental-editor.md` (engine — genre-agnostic)

A single holistic agent (not eight micro-inspectors; the dimensions are facets of one read).

- **Inputs:** `{ draft text, config/review-rubrics/developmental-craft.md, setting-pack,
  character-bible slice, chapter brief }`. **No** whodunit solution; **no** drafting history.
- **Cross-model required (halts otherwise):** runs on a non-drafting model (genuine fresh
  eyes, same rationale as `final-reader`). Cross-model independence is a **hard
  precondition**: if no non-drafting model is available (e.g. fast/`panel_size: 1` mode with
  only the drafting model reachable), `/review-chapter` **halts loud** rather than degrading
  to a same-model read — a same-model "fresh eyes" read is a soft gate, which Penny rejects.
  Stamps `read_by` (must differ from the chapters' `drafted_by`).
- **Output:** an advisory verdict written via `scripts/penny_verdict.py` to
  `ch-MM.reviews/developmental-edit.md`, `producer: developmental-editor`,
  `kind: developmental`. Per-dimension `score` (1–5) **and `reviewed_draft_sha256`** (the
  hash of the draft it read — load-bearing for clearance binding). Margin notes go in
  `violations[]`/`evidence[]`: each note **quotes the passage**, names the missing craft,
  and suggests a concrete move. It **must not** emit any `^BLOCKING:` line.

### 2. `config/review-rubrics/developmental-craft.md` (swappable pack)

Eight obligation-aware dimensions — judged against *what this chapter must do* per its brief,
so a mid-book chapter isn't dinged for not re-establishing place:

1. Setting grounding (draws on `setting-pack/coastal-victoria-au.md`)
2. Motivation & stakes (the "why")
3. Scene economy (inert detail)
4. Scene texture / subtext
5. Interiority / emotional access
6. Show-don't-tell
7. Genre delivery (cozy warmth/charm/comfort-tone)
8. Hook & promise of the premise (esp. openers)

Genre-specific content lives **here**, in the pack — the agent and command logic stay
genre-agnostic per the engine/pack rule.

### 3. `/review-chapter` (orchestration)

Dispatches the dev editor alongside the five inspectors (blind isolation preserved for the
inspectors; the dev editor's richer inputs are separate). Writes `developmental-edit.md`.
**Halts loud** before dispatching the dev read if no non-drafting model is available
(cross-model is a hard precondition — see Decision 6).

### 4. Gate-summary rendering (`review_gate.py` / `ch-MM.gate.md`)

Grows a **Developmental** section that **always prints** — including on `gate: PASS` — so the
craft report is surfaced prominently and is never silently swallowed. Because the dev editor
emits no `^BLOCKING:` lines, it **never affects** the `PASS`/`HOLD` computation; the
existing blocker-count logic is untouched.

### 5. `scripts/preflight.py` — clearance certificate

Mirror `cmd_lock_mystery`/`cmd_approve_book`: validate preconditions, **mint last**.

- **New `clear-dev N CH` subcommand** (sole writer of the clearance cert):
  1. `developmental-edit.md` exists for N/CH (can't clear an un-reviewed chapter).
  2. The report's `reviewed_draft_sha256` equals the **current** draft's hash (you're
     clearing the version that was actually reviewed, not a stale one).
  3. Both green → mint `.penny/locks/book-NN.ch-MM.dev-clear` recording `book`, `chapter`,
     `cleared_draft_sha256` (= the current draft hash), `cleared_at`.
- **`cmd_finalize` gains a second predicate:** after the `gate: PASS` check, require the
  dev-clearance cert to exist **and** its `cleared_draft_sha256` to equal the current
  draft's hash. A revision after clearance changes the hash → clearance is automatically
  stale → finalize refuses with a named predicate. This keeps "cleared" an out-of-band
  certificate that exists *only because the showrunner cleared this exact draft* — never a
  forgeable field inside the data it gates.

## Tests (test-first, against `tests/fixtures/`)

- `developmental-edit.md` conforms to the `penny-verdict` envelope; `kind: developmental`.
- **Advisory invariant:** a dev verdict with low scores / many notes contributes **zero**
  to `review_gate.count_blocking`; gate stays `PASS` when only the dev editor objects.
- Gate summary renders the Developmental section on both PASS and HOLD.
- **Cross-model halt:** `/review-chapter` refuses (loud, nonzero) when the only reachable
  model is the chapter's drafting model — no silent same-model degradation.
- Margin notes are emitted only for low-scoring dimensions (high-scoring dimensions get a
  score but no note).
- `preflight clear-dev` refuses when no report / when report hash ≠ current draft; mints on
  success.
- `preflight finalize` refuses when no clearance / stale clearance (hash mismatch);
  passes with a fresh clearance; **and still** refuses on `gate != PASS` (existing predicate
  intact).

## Rollout

1. Build engine + rubric + tests.
2. **Calibrate on the chapters whose problems are already known:** run the dev editor on the
   finalized ch-01 (the calibration target) and ch-02. It should independently surface the
   four issues above. Tune the rubric thresholds ("seeds, tunable during Book 1", like the
   other rubrics).
3. Use the generated reports to drive a revise pass on ch-01/ch-02 via the `drafter`, then
   re-clear and re-finalize.

## Out of scope (YAGNI)

- Auto-clear / score-threshold gating (explicitly rejected — reintroduces a soft LLM gate).
- Book-level developmental pass (the beta-reader + revision-priority report already occupy
  the book-level experiential tier).
- Making any dev finding blocking. If a *specific, objective* check later proves worth
  hard-gating, promote it deliberately — not by default.
