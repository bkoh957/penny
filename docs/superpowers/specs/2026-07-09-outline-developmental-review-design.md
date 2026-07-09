# Penny — Outline Developmental Review (pre-draft craft tier)

Saved: 2026-07-09 | Status: design approved (brainstorm complete), pending spec review

Adds the missing **planning-tier craft read** to Penny. Today the heavy review
apparatus — five blind inspectors + the context-rich `developmental-editor` — is
entirely **post-draft**. Deterministic planning gates exist (`fairplay_check.py` on the
whodunit ledger, `outline_check.py` on outline shape, `lexicon_check.py`) but they judge
the *skeleton and the abstract mystery math*, never the outline's **craft**. Every craft
judgment about the outline ("do the problems escalate?", "is there enough romance?") is
therefore a manual read today. This spec automates that read as an **advisory** agent and
makes its findings **loud** at draft time — without ever hard-gating.

Supersedes nothing. Touches no shipped gate. Additive.

## 1. Goal & scope

### The gap (why this exists)

The outline is a **detailed prompt that shapes chapter prose**. If a chapter beat is
underspecified or the arc is thin, the drafter produces weak prose, and the weakness is
caught late — as a chapter-tier `inspector-structure` HOLD or a `developmental-editor`
flag — when the root cause was the plan. A defect caught at the outline is a one-sentence
edit; the same defect caught after drafting is a re-draft. This tier moves those
craft defects **left**, to their cheapest point.

Two examples the showrunner named, and how they map onto Penny's existing model:

- **"Do the problems escalate and connect?"** — the rising-and-causal shape of the beats
  across the arc.
- **"Is there enough romance?"** — a strand's sufficiency/cadence across the book. Under
  the front-door reframe (`2026-06-22-outline-first-front-door-design.md` §1) romance is
  one **strand** among several (M/P/R/B); "enough romance" is a strand-cadence question,
  read off the same strand model `inspector-structure` and `series/arc-ledger.md` already
  use.

### What it is

One **context-rich, whole-outline** review agent — `outline-reviewer` — the sibling of the
chapter `developmental-editor`, moved up one tier and widened to book scope. Same posture:
**diagnoses craft, never rewrites, never blocks.** Invoked by a new standalone command,
`/review-outline NN`. Its findings are surfaced **loudly at draft time** via a banner, but
nothing gates drafting.

### The load-bearing constraint: advisory, never a gate

Penny's architecture forbids **LLM judgment as a hard gate** (the "soft gate" weakness the
deterministic layer exists to prevent; `2026-06-22` §2 rejected "Approach B" for exactly
this). This tier honours that: it is advisory-only, emits **zero** `^BLOCKING:` lines, and
**does not gate `/draft-chapter`**. It is the craft counterpart to the front door's
*mechanical* dry-run (`scaffold-review.md`, `2026-06-22` §7) — the same deterministic-gate
+ advisory-craft split Penny already runs at the chapter tier, now at the plan tier.

### Non-goals (flag, do not build)

- **Not a gate.** It never blocks drafting, never writes a certificate, never emits a
  blocker. (Contrast: the mystery lock, which *is* earned deterministically.)
- **Not a deterministic checker.** Craft ("is this beat specific enough?", "does romance
  land?") is genuine judgment; it belongs in an agent, never in `scripts/`. The mechanical
  checks (shape, fairness) already exist and are untouched.
- **Not a rewriter.** It diagnoses; new writing flows back to the outline author
  (`/expand-outline`, `/scaffold-book`, or the human), never to this seat.
- **Not a fairness judge.** Fair-play is `fairplay_check.py` + `inspector-fairplay`. This
  seat is **solution-blind**, exactly like `developmental-editor`.
- **No status-line indicator (v1).** The banner is the chosen loudness mechanism; a
  status-line `outline-flags:` field is a possible later addition, not built here.

## 2. Where it sits — relationship to the outline subsystem

Penny has **two** outline-production paths; this reviewer must cover both, so it is
**standalone** and reads `input/book-NN/outline.md` regardless of how that file was
produced:

```
Path A (hand-authored beats):   write outline.md → /scaffold-book → approve → lock
Path B (skeleton → expansion):  skeleton → /plan-mystery + lock → /expand-outline → outline.md

                    ... either path ...
                              │
                    ┌─────────▼─────────┐
                    │  /review-outline  │   (THIS spec — advisory craft read)
                    └─────────┬─────────┘
                              │  writes output/book-NN/reports/outline-developmental.md
                              ▼
        /draft-chapter  ──►  banner fires off the sidecar (open flags / stale)  ──►  draft
```

A reviewer folded into one path would miss the other, and the showrunner must be able to
re-run it after editing the outline **without** re-deriving or re-expanding. Hence a
standalone command. It runs whenever `input/book-NN/outline.md` exists; it is most valuable
once the outline is in its final pre-draft resolution (post-expand scene-breakdown, or a
complete beat outline), and it is designed to be **re-run** after every outline edit.

**Pre-draft counterpart to `inspector-structure`.** `inspector-structure` already judges
thread-roster liveness across all strands — but **post-draft, on prose**. This reviewer is
its **pre-draft, plan-level** counterpart for the same concern (a strand going dark, a
sagging middle), caught before any prose is spent. It does not replace or modify
`inspector-structure`.

## 3. Architecture — engine vs swappable

Governing rule (CLAUDE.md): scripts never make an LLM judgment; agents judge; commands
orchestrate; genre-specific content lives in swappable data (the genre pack), never in
`scripts/` or agent logic.

| Piece | Layer | Artifact |
|---|---|---|
| `/review-outline NN` | command (engine) | runbook: assemble context, dispatch agent, write sidecar, advance marker |
| `outline-reviewer` | agent (engine) | the craft verdict (`penny-verdict/1`, `kind: developmental`) |
| Outline craft rubric | **swappable data** (genre pack) | `genres/<g>/review-rubrics/outline-craft.md` |
| `scripts/outline_flags.py` | deterministic reporter (engine) | the draft-time banner text + nonzero-free exit |
| Banner hook in `/draft-chapter` | command (engine) | one non-blocking step that runs the reporter |

The only genuinely new pieces are the agent, the command, one pack rubric (per genre), and
one small deterministic reporter + its one-line hook in `/draft-chapter`. Everything else
(verdict envelope, genre-pack rubric pattern, `read_by`/`reviewed_*_sha256` conventions) is
reused.

## 4. The `outline-reviewer` agent (context-rich, advisory)

Mirrors `agents/developmental-editor.md`; changes only what the outline tier needs.

| | chapter `developmental-editor` | new `outline-reviewer` |
|---|---|---|
| Reads | one draft | the **whole** `outline.md` (all chapters at once) |
| Judges | craft **on the page** | craft **of the plan/arc** |
| Gate relation | advisory, but `clear-dev` gates finalize | advisory, **nothing gates drafting** |
| Cross-model | **required** (fresh eyes vs the drafter) | **not required** (see below) |
| Blindness | solution-blind | solution-blind (same) |

**Inputs** (context-rich, but solution-blind):
`{ outline.md (whole), genres/<g>/review-rubrics/outline-craft.md, input/series/series-bible.md,
series/continuity/canon-core.md, series/arc-ledger.md (optional — present on Path A) }`.
**Denied:** `output/book-NN/mystery-solution*.md` and the whodunit ledger's answer fields
(`culprit`, `clue_schedule` incrimination, etc.). Craft review does not need the solution,
so fair-play is never exposed to this seat — identical to `developmental-editor`.

**Cross-model is NOT required — deliberate difference.** The chapter `developmental-editor`
must run on a non-drafting model for genuine fresh eyes *because a draft already exists*.
At outline time **no draft exists**, so there is no drafter to be independent of. Therefore
`/review-outline` runs on the configured `outline-reviewer` model and **does not halt** if
no non-drafting model is reachable (contrast: `/review-chapter` halts). Record the model in
`read_by`.

**Output:** a verdict via `scripts/penny_verdict.py`:
- `producer: outline-reviewer`, `kind: developmental`, `target: book-NN`.
- `blocking: []` — **always empty** (the agent MUST NOT emit any `^BLOCKING:` line).
- `score`: 1–5 holistic craft judgment of the outline as a whole.
- `metrics`: per-dimension scores (§5) — human-facing; the reporter does **not** read these.
- `notes[]`: one margin note per LOW-scoring dimension — each **quotes the offending beat**,
  names the missing craft, and suggests a **concrete** move (e.g. "romance goes dark
  ch7–11; give ch9's beat a two-line Cal thread"). High-scoring dimensions get no note.
- `extra_frontmatter: { reviewed_outline_sha256: <sha256>, flags: <int> }` — **both stamped
  as top-level frontmatter scalars** so the dependency-free reporter (§7) reads them with
  `penny_meta.parse_frontmatter`, no PyYAML. `flags` = `len(notes)` (one per low dimension);
  `reviewed_outline_sha256` is the staleness anchor (mirrors `reviewed_draft_sha256`).
  Nested `metrics` is deliberately **not** where the machine-read values live.

Written to `output/book-NN/reports/outline-developmental.md`. **Named to avoid collision**
with the front door's `scaffold-review.md` (the *mechanical* lens); `outline-developmental`
echoes the chapter tier's `developmental-edit.md` and reads as "the craft read."

**Hard constraints** (same three as `developmental-editor`): diagnose never rewrite;
advisory never block (no `^BLOCKING:`); genre lives in the rubric — the agent's own
reasoning stays genre-agnostic.

## 5. The rubric — `genres/<g>/review-rubrics/outline-craft.md` (swappable)

The bars live in the **genre pack** (per the genre-pack layer, `2026-07-08`), not in
`config/` and never in `scripts/`. The agent reads whichever genre the active series
resolves to. Cozy-mystery seeds these dimensions (a thriller pack would swap in its own —
escalating threat, ticking clock, no-sag):

| Dimension | The question | Read from |
|---|---|---|
| **Escalation** | Do chapter problems *rise* across the arc rather than plateau? | the ordered beats |
| **Connection / causality** | Does each problem grow *out of* the last, not arrive unrelated? | beat-to-beat links |
| **Strand sufficiency & balance** | Is each declared strand (M/P/R/B) *present enough* and not dark too long? | Track Movement + `arc-ledger.md` |
| **Mystery progression** | Does the M-track actually *advance* in chapters that claim to? | M movement per chapter |
| **Beat draftability** | Is each beat *specific* enough to steer a strong draft (vs "she investigates the shop")? | the beat prose |
| **Hook chain** | Does each chapter's Hook genuinely earn the next? | per-chapter Hook |

The agent scores each 1–5 against *this book's* declared strands and writes a margin note
for every low score. "Enough romance" is literally the **strand-sufficiency** line applied
to the romance strand. Same agent, different pack → different bars.

## 6. The command — `/review-outline NN` (runbook)

Engine command; prose runbook (not unit-tested, consistent with `draft-chapter`/`drafter`).

1. **Parse** `book` (e.g. `01`).
2. **Precondition:** `input/book-NN/outline.md` exists; abort with a clear message if not
   ("no outline for book NN — run /scaffold-book or /expand-outline first").
3. **Marker:** write `.penny/current-stage` (`stage=OUTLINE-REVIEW`).
4. **Resolve genre** (via `scripts/penny_genre.py`) → locate
   `genres/<g>/review-rubrics/outline-craft.md`. Abort if the active genre pack ships no
   `outline-craft.md` (a pack that wants this tier must provide the rubric).
5. **Compute** the outline's sha256 (to hand the agent for `reviewed_outline_sha256`).
6. **Assemble context** (§4 inputs, solution-blind) and **dispatch `outline-reviewer`** on
   the configured model. Do **not** halt on missing non-drafting model.
7. **Write** the verdict to `output/book-NN/reports/outline-developmental.md`.
8. **Print a summary** to the console: holistic score + the flag count + each margin note's
   one-line headline, so the showrunner sees the result immediately on running it.
9. **Advance marker** (`stage=OUTLINE-REVIEWED`).

Re-running overwrites the sidecar (the outline is the source of truth; v1 overwrites
wholesale, consistent with the front door's re-derivation stance).

## 7. The loud-but-advisory mechanism — banner at draft time

**Chosen mechanism: a banner in `/draft-chapter`** (status-line indicator deferred). The
banner must be **deterministic** (Penny distrusts LLM instructions for load-bearing
surfacing), so a tiny reporter script produces it and `/draft-chapter` calls it.

### `scripts/outline_flags.py NN` (deterministic reporter)

Pure stdlib + `scripts.penny_meta` (parses the verdict frontmatter/metrics — flat, so
`penny_meta`, not PyYAML, per the dependency-split rule). Reporting-only; **never exits
nonzero** (it must not block drafting). Behaviour:

1. If `output/book-NN/reports/outline-developmental.md` is absent → print a one-line notice
   ("no outline review yet — consider /review-outline NN") and exit 0.
2. Read the top-level frontmatter scalars `flags` and `reviewed_outline_sha256` from the
   sidecar (via `penny_meta.parse_frontmatter` — no PyYAML).
3. Compute the current sha256 of `input/book-NN/outline.md`.
4. Emit the banner and exit 0:
   - **stale** (sha differs): `⚠ OUTLINE REVIEW STALE — outline changed since review; re-run /review-outline NN`.
   - **open flags** (`flags > 0`, not stale): `⚠ OUTLINE: N developmental flag(s) — see output/book-NN/reports/outline-developmental.md. Drafting anyway.`
   - **clean** (`flags == 0`, not stale): a quiet one-line `✓ outline review clean`.

It is **self-clearing**: fix the outline → re-run `/review-outline` → `flags` drops / sha
realigns → the banner goes quiet. No manual dismiss; the loudness tracks the real state of
the outline.

### Hook in `/draft-chapter`

One new **non-blocking** step near the top of the `/draft-chapter` runbook: run
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/outline_flags.py NN` and surface its output, then
**proceed regardless**. This is the "advisory but very clear" contract: in your face at the
exact moment you'd act on a thin outline, but never a barrier.

## 8. Conventions reused / consistency with prior specs

- **`2026-06-22` (outline front door):** cites §1 (multi-strand reframe → the rubric's
  strand vocabulary) and §7 (`scaffold-review.md` is the *mechanical* lens; this is the
  distinct *craft* lens). No contradiction: the front door forbade a *soft LLM gate for
  structural validity*; this tier is advisory and gates nothing.
- **`developmental-editor` (`2026-06-27`):** this agent is its outline-tier sibling —
  same envelope (`kind: developmental`, `blocking=[]`, 1–5 score, quoted margin notes,
  `reviewed_*_sha256`), differing only in scope (whole outline) and cross-model (not
  required).
- **`inspector-structure`:** the post-draft analogue for strand liveness; this is the
  pre-draft counterpart. Unchanged.
- **Genre-pack layer (`2026-07-08`):** the rubric is pack data, resolved via
  `penny_genre.py`, keeping the engine genre-agnostic (no drift).
- **Verdict convention:** the sidecar lives **outside** `ch-MM.reviews/`, so it never
  reaches `review_gate.py`; `kind: developmental` + `blocking=[]` means it contributes zero
  blockers by construction even if it ever were counted.

## 9. Error handling

| Piece | Hard-fail (nonzero) | Non-blocking / soft |
|---|---|---|
| `/review-outline` precondition | missing `outline.md` or missing genre `outline-craft.md` → abort before dispatch | — |
| `outline-reviewer` (agent) | — (agents never hard-gate) | the whole read is advisory |
| `scripts/outline_flags.py` | **never** (reporting-only; always exit 0) | the banner is a notice |
| `/draft-chapter` banner step | — | proceeds regardless of flags |

The only hard-fails are operational (no outline / no rubric). The craft read and the banner
are strictly non-blocking.

## 10. Config / run-mode (swappable layer)

- **Model routing:** add an `outline-reviewer` role to the model-per-role map in
  `config/run-config.md` (a capable model; **no** non-drafting constraint, unlike
  `developmental-editor`). Defaults apply if unset.
- **No approval mode.** Because it never gates, there is no `*_approval` pause to add
  (contrast `scaffold_approval` / `ledger_approval`).
- **Rubric is pack data**, not run-config: `genres/<g>/review-rubrics/outline-craft.md`.

## 11. Testing strategy

Test-first for the one deterministic piece; structure assertions + manual e2e for the
agent/command (no unit tests for LLM judgment, per CLAUDE.md).

- **`tests/test_outline_flags.py` vs `tests/fixtures/`:**
  - sidecar absent → "no outline review yet" notice, exit 0.
  - `flags: 0`, sha matches → "clean" line, exit 0.
  - `flags: 3`, sha matches → banner names 3 flags + the report path, exit 0.
  - sha mismatch (outline edited since review) → **stale** banner, exit 0, regardless of
    flag count.
  - reporter **never** returns nonzero on any input (explicit assertion — it must not be
    able to block a draft).
  - Fixtures are **self-contained** — never live `series/` content (the `readiness_check`
    lesson: fixtures reaching into live content rot on repo reset).
- **Cross-consistency (so conventions cannot fork, per CLAUDE.md):** a test that the
  `outline-reviewer` verdict shape the agent is specified to emit is the **exact** shape
  `outline_flags.py` reads — a `flags`/`reviewed_outline_sha256`-bearing verdict fixture
  feeds straight into the reporter without adaptation.
- **Agent/command layer:** prose runbook → assertions on the produced
  `outline-developmental.md` structure (holistic score, per-dimension metrics, one note per
  low dimension, `reviewed_outline_sha256` present) + **manual e2e on the Book-1 outline**.
- **Not tested (scope guard):** the reviewer's *judgment quality* (UAT, like every Penny
  agent); the deferred status-line indicator.

## 12. Build sequence (each piece testable as built)

1. **`scripts/outline_flags.py`** + `tests/test_outline_flags.py` + fixtures. Pure
   deterministic reporter, fully unit-testable, depends on nothing new. (TDD — the
   genuinely-new engine logic.)
2. **`genres/cozy-mystery/review-rubrics/outline-craft.md`** — the seed rubric (six
   dimensions, §5). Pack data.
3. **`agents/outline-reviewer.md`** — the craft agent; mirror `developmental-editor.md`,
   change scope + cross-model + inputs (§4). No unit tests (LLM); validated by the
   cross-consistency verdict-shape test + manual e2e.
4. **`commands/review-outline.md`** — the orchestrator (§6). Add the `outline-reviewer`
   role to `config/run-config.md`.
5. **Banner hook** — one non-blocking step in `commands/draft-chapter.md` that runs
   `scripts/outline_flags.py NN` and surfaces it (§7).

The new deterministic logic (`outline_flags`) lands first and standalone; the agent and
command build on shipped, untouched infrastructure (`penny_verdict`, `penny_genre`, the
continuity/arc-ledger layer, `draft-chapter`).

## 13. Open sequencing decision (for review)

This is **independent** of the thriller pack but shares one pattern with it (a rubric in
`genres/<g>/review-rubrics/`). Two options:

- **Own small phase after Phase 4 (recommended):** ship the thriller pack first (already
  specced + awaiting review), then this. Keeps each phase single-purpose; this tier is
  useful to *both* genres, so building it after at least one non-cozy pack exists lets the
  cross-genre rubric contract be exercised immediately.
- **Ride with Phase 4:** fold the `outline-craft.md` rubric work into the thriller-pack
  phase since both add pack rubrics. Cheaper context-switch, but couples two unrelated
  deliverables and widens the phase.

Recommendation: **own phase after Phase 4.** Decide at spec review.
