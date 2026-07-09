# Penny — Outline Developmental Review (independent panel, tracked feedback)

Saved: 2026-07-09 | Status: design approved (brainstorm complete), pending spec review

Adds the missing **planning-tier craft read** to Penny, shaped to the showrunner's real
outline workflow. Today the heavy review apparatus — five blind inspectors + the
context-rich `developmental-editor` — is entirely **post-draft**. Deterministic planning
gates exist (`fairplay_check.py` on the whodunit ledger, `outline_check.py` on outline
shape, `lexicon_check.py`) but judge the *skeleton and the abstract mystery math*, never
the outline's **craft**. So craft judgment on the outline is manual — and the showrunner
does it by pasting the outline into several LLMs (ChatGPT, Claude), bringing gut-feel
challenges, and iterating, across separate chat windows. This spec brings that exact
loop **into one place**: an **independent reviewer panel** producing **side-by-side prose
feedback** decomposed into **ID'd items with a state the showrunner owns**, iterated over
passes, surfaced loudly at draft time — and **never gating**.

Supersedes nothing. Touches no shipped gate. Additive.

## 1. Goal & scope

### The gap (why this exists)

The outline is a **detailed prompt that shapes chapter prose**. If a beat is
underspecified or the arc is thin, the drafter produces weak prose, and the weakness is
caught late — as a chapter-tier `inspector-structure` HOLD or a `developmental-editor`
flag — when the root cause was the plan. A defect caught at the outline is a one-sentence
edit; caught after drafting it is a re-draft. This tier moves craft defects **left**.

### The workflow this reproduces (load-bearing)

The showrunner's manual process, automated in one command:

1. **Multiple *independent* reviewers** (he uses ChatGPT + Claude) — different engines,
   genuinely different eyes.
2. **Optional steering** — a gut-feel challenge ("stress-test genre adherence"), used
   *only when he notices the review missed something*; the default run is unsteered.
3. **Back-and-forth** — read feedback → form a challenge → re-review, iterating.
4. **One place** — no copy-pasting the document across chat windows.
5. **Tracked dispositions** — each feedback point is something he can **reject** or mark
   **solved**, not just read.

### What it is

An **independent reviewer panel** — a Claude reviewer and a Codex reviewer (tool-difference
independence, per the front-door model note, §8) — reading the same outline **blind to the
solution**, producing **prose editorial letters** (no scores). The command decomposes those
letters into discrete **feedback items**, each with a stable **ID** and a **state**
(`open`/`solved`/`rejected`) the showrunner owns, accumulated in a persistent **feedback
ledger**. Re-runs **append** new items and **never** touch the showrunner's states. A
deterministic banner surfaces the open backlog + staleness at draft time. Advisory
throughout — nothing gates drafting.

### The constraint: advisory, never a gate; independent, never averaged

- **Advisory.** Penny forbids **LLM judgment as a hard gate** (`2026-06-22` §2 rejected
  "Approach B" for exactly this). This tier gates nothing, writes no certificate, emits no
  blocker. It is the *craft* counterpart to the front door's *mechanical* dry-run
  (`scaffold-review.md`, `2026-06-22` §7) — the same deterministic-gate + advisory-craft
  split Penny runs at the chapter tier, now at the plan tier.
- **Independent, side-by-side, NOT converged.** The beta layer fans reviewers across models
  and **converges** them (≥K-of-M). This tier deliberately does the **opposite**: it keeps
  the takes **side-by-side** so reviewer disagreement stays visible for the showrunner to
  judge. Averaging would destroy the very signal he reads for.

### Non-goals (flag, do not build)

- **Not a gate / not a rewriter / not a fairness judge.** Advisory only; new writing flows
  back to the outline author; fair-play stays with `fairplay_check.py` + `inspector-fairplay`
  (this seat is **solution-blind**).
- **No scores / no rubric grades.** Prose feedback, not a 1–5 scorecard (explicit
  showrunner requirement — numbers read as mechanistic).
- **No automated convergence / synthesis.** Two independent letters stand as two; the
  showrunner reconciles.
- **No consensus quorum** (contrast beta's K-of-M).
- **No status-line indicator (v1).** The draft-time banner is the chosen loudness surface.

## 2. Where it sits — relationship to the outline subsystem

Penny has **two** outline-production paths; the reviewer covers both, so it is
**standalone** and reads `input/book-NN/outline.md` however it was produced:

```
Path A (hand-authored beats):   write outline.md → /scaffold-book → approve → lock
Path B (skeleton → expansion):  skeleton → /plan-mystery + lock → /expand-outline → outline.md

                     ... either path ...
                               │
                     ┌─────────▼──────────┐
                     │  /review-outline    │   (THIS spec — independent panel, advisory)
                     │   [--focus "..."]   │
                     └─────────┬──────────┘
                               │  appends to output/book-NN/reports/outline-feedback.yaml
                               ▼
        /draft-chapter  ──►  banner: open items + stale?  ──►  draft (never blocked)
```

A reviewer folded into one path would miss the other, and the showrunner must re-run it
after editing the outline **without** re-deriving/re-expanding. Hence a standalone,
re-runnable command.

**Pre-draft counterpart to `inspector-structure`.** `inspector-structure` already judges
thread-roster liveness across strands — but **post-draft, on prose**. This is its
**pre-draft, plan-level** counterpart for the same concern (a strand going dark, a sagging
middle), caught before prose is spent. `inspector-structure` is unchanged.

## 3. Architecture — engine vs swappable

Governing rule (CLAUDE.md): scripts never make an LLM judgment; agents judge; commands
orchestrate; genre-specific content lives in swappable pack data.

| Piece | Layer | Artifact |
|---|---|---|
| `/review-outline NN [--focus …]` | command (engine) | dispatch panel, decompose→append ledger, render view |
| `outline-reviewer` | agent (engine) | one reviewer's prose letter as a list of discrete points |
| Codex reviewer | tool (engine, via codex plugin) | the second, independent letter (same prompt/rubric) |
| Outline craft rubric | **swappable data** (genre pack) | `genres/<g>/review-rubrics/outline-craft.md` |
| `scripts/outline_feedback.py` | deterministic (engine) | `render` (yaml→md view) + `status` (banner) |
| Banner hook in `/draft-chapter` | command (engine) | one non-blocking step running `… status NN` |

New pieces: the agent, the command, one pack rubric per genre, one deterministic
render+status script, and one non-blocking hook line. Everything else reuses shipped
infrastructure (`penny_genre`, the codex runtime, the continuity/arc-ledger layer,
`draft-chapter`).

## 4. The independent panel (prose, side-by-side, solution-blind)

**The panel** (from `config/run-config.md` → `outline_review_panel`, default
`[claude, codex]`). Each member gets **identical inputs** and reviews **independently**:

- **Claude reviewer** — the `outline-reviewer` agent (a Claude Code sub-agent).
- **Codex reviewer** — the same rubric + prompt sent through the Codex plugin runtime.
  This realises Penny's "difference, not identity" as **tool difference** (`2026-06-22`
  §8): authoring is Claude; independent review includes Codex.

**Inputs (context-rich, solution-blind), identical per member:**
`{ whole outline.md, genres/<g>/review-rubrics/outline-craft.md (coverage checklist),
input/series/series-bible.md, series/continuity/canon-core.md, series/arc-ledger.md
(optional — present on Path A), the current feedback ledger (§6, for dedup), and the
optional --focus directive }`. **Denied:** `output/book-NN/mystery-solution*.md` and the
ledger's answer fields — craft review does not need the solution, identical to
`developmental-editor`.

**Independence model:**
- **Within a pass:** members run **in parallel, blind to each other's current output** —
  two genuinely independent reads of this outline.
- **Across passes:** each member is shown the **accumulated ledger** (prior items + their
  states) so it can *dedup* — it must not re-raise a `solved`/`rejected`/`open` item unless
  it has something materially new, though it may add a new item noting a `rejected` concern
  still stands. (Shared memory of past dispositions ≠ shared current-pass judgment.)

**Output shape (per member):** a short prose editorial letter expressed as a **list of
discrete points** — each point one focused paragraph (quote the beat, name what's thin,
suggest a concrete move), plus optional "no notes here" acknowledgements. **No scores, no
grades.** The member does **not** assign IDs (the command owns ID allocation, §6).

**Degrade, never halt.** If a panel member is unreachable (e.g. Codex plugin down), the
command runs the reachable member(s) and records in the ledger/view *"independence reduced:
codex unreachable this pass."* Because the whole value is the second set of eyes, this is
surfaced plainly — but the tier is advisory, so it never halts (contrast `/review-chapter`,
which halts if no non-drafting model). **Cross-model is not *required*** (no draft exists
yet, so there is no drafter to be independent of); independence here is about *reviewer
diversity*, not drafter-avoidance.

## 5. The rubric — a coverage checklist in the genre pack (not a grade sheet)

`genres/<g>/review-rubrics/outline-craft.md` (pack data, per the genre-pack layer,
`2026-07-08`). It is a **checklist of concerns each reviewer must address in prose** — its
job is to make the *unsteered* run thorough enough that steering stays rare (§1.2). It is
**not** scored. Cozy-mystery seeds these coverage areas (a thriller pack swaps its own —
escalating threat, ticking clock, no-sag):

- **Escalation** — do chapter problems *rise* across the arc rather than plateau?
- **Connection / causality** — does each problem grow *out of* the last, not arrive cold?
- **Strand sufficiency & balance** — is each declared strand (M/P/R/B) *present enough* and
  not dark too long? ("Is there enough romance" is this area applied to the romance strand.)
- **Mystery progression** — does the M-track actually *advance* where a chapter claims it?
- **Beat draftability** — is each beat *specific* enough to steer a strong draft?
- **Hook chain** — does each chapter's Hook earn the next?

Same panel, different pack → different bars. The reviewers' own reasoning stays
genre-agnostic; genre lives in the rubric.

## 6. The feedback ledger — IDs, owned states, append-only (the heart)

### Source of truth: `output/book-NN/reports/outline-feedback.yaml`

Nested, human-edited data → **PyYAML** is the correct parser (same class as the whodunit
ledgers; the `penny_meta` dependency-split rule reserves PyYAML for exactly this). Shape:

```yaml
book: 01
reviewed_outline_sha256: a1b2c3…        # sha of the outline the latest pass read
items:
  - id: OF-1                # stable, sequential, never reused
    source: claude          # claude | codex | <panel-member id>
    pass: 1                 # the pass that first raised it
    state: open             # open | solved | rejected  ← SHOWRUNNER OWNS
    text: >
      Romance goes quiet ch7–11 — softest stretch. The community thread
      covers it, but a reader waiting on Cal will feel the wait.
  - id: OF-2
    source: claude
    pass: 1
    state: solved
    text: >
      ch9 "Maggie investigates the shop" is too vague to draft — name what
      she is looking for and what she should not yet understand.
  - id: OF-3
    source: codex
    pass: 1
    state: rejected
    text: >
      Romance dark ch7–11 reads as a cozy genre miss — force a Cal beat into ch9.
```

Fields: `id` (command-allocated, `OF-<n>`, monotonic, never reused), `source` (provenance —
which panel member), `pass`, `state` (**the only field the showrunner edits**), `text`
(the prose point). An optional `note:` lets the showrunner annotate a disposition.

### The load-bearing invariant: the command is append-only over items

On every pass the command **only appends new items** (fresh IDs, `state: open`, `pass=N`)
and **never modifies or deletes an existing item** — not its `text`, not its `state`. This
is what guarantees the showrunner's triage (`OF-2 solved`, `OF-3 rejected`) survives every
future pass. State flows one way: reviewers propose (append); the showrunner disposes
(edits `state`); the command never overwrites a disposition. It **does** update the
top-level `reviewed_outline_sha256` to the sha it just reviewed.

### Setting state = editing the field (terminal-native)

The showrunner changes `open` → `solved`/`rejected` **directly in the yaml**. No command
ceremony — it fits how he works (edit a file, not run a verb). A `/review-outline resolve
OF-3` / `reject OF-3` shortcut is a trivial later add, not built in v1.

### Rendered reading view: `output/book-NN/reports/outline-review.md`

`scripts/outline_feedback.py render NN` regenerates a **side-by-side** markdown snapshot
from the yaml — grouped by pass, then by `source`, each item showing `id`, `state`, and
`text` (open items foregrounded, solved/rejected collapsed). This is the "two letters next
to each other" reading surface; the **yaml remains the source of truth** and tools never
trust the rendered `.md`. (Matches the user's "structured data in its own file, `.md` as
the doc" preference.) The view is a snapshot: after a manual state edit, re-render (or the
next pass regenerates it).

## 7. The command — `/review-outline NN [--focus "…"]` (runbook)

Engine command; prose runbook (not unit-tested, per `draft-chapter`/`drafter`).

1. **Parse** `book` and optional `--focus "<directive>"`.
2. **Precondition:** `input/book-NN/outline.md` exists (else abort: "run /scaffold-book or
   /expand-outline first"). Resolve genre (via `penny_genre.py`) → require
   `genres/<g>/review-rubrics/outline-craft.md` (abort if the active pack ships none — a
   pack that wants this tier must provide the rubric).
3. **Marker:** `.penny/current-stage` → `stage=OUTLINE-REVIEW`.
4. **Hash** `outline.md` (for `reviewed_outline_sha256` + staleness).
5. **Load** the current ledger (if any) to hand members for dedup (§4).
6. **Dispatch the panel in parallel** (`outline_review_panel`), identical inputs,
   solution-blind, `--focus` injected into each prompt if present. Unreachable member →
   degrade + record (§4), never halt.
7. **Decompose & append:** for each member's returned points, allocate the next `OF-<n>`
   IDs and append items (`source`, `pass=N`, `state: open`, `text`). **Never** modify
   existing items. Update `reviewed_outline_sha256`.
8. **Render** the side-by-side view (`outline_feedback.py render NN`).
9. **Print** the new items (IDs + source + one-line headline) and the current open count to
   the console, so the result is immediate.
10. **Advance marker** → `stage=OUTLINE-REVIEWED`.

Default (no `--focus`) is a full unsteered rubric pass; `--focus` is the exception lever
for when the showrunner notices a gap.

## 8. The banner — deterministic, keyed on open items + staleness

`scripts/outline_feedback.py status NN` (reporting-only; **never** exits nonzero — it must
not block drafting). Reads the ledger yaml (PyYAML):

1. Ledger absent → nudge ("no outline review yet — consider /review-outline NN"), exit 0.
2. Count `items` with `state: open`; compare current `outline.md` sha to
   `reviewed_outline_sha256`.
3. Emit + exit 0:
   - **stale** (sha differs): `⚠ OUTLINE changed since its last review — re-run /review-outline NN`.
   - **open backlog** (open > 0, fresh): `⚠ OUTLINE: N open feedback item(s) (OF-…) — see output/book-NN/reports/outline-feedback.yaml. Drafting anyway.`
   - **clean** (open == 0, fresh): quiet `✓ outline reviewed — no open items`.

The count is an **open action-item backlog**, not a quality grade (honours "no scores").
Self-clearing: disposition items (`solved`/`rejected`) or fix-and-re-review → open drops /
sha realigns → banner goes quiet.

**Hook in `/draft-chapter`:** one **non-blocking** step near the top runs
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py status NN`, surfaces its line,
and **proceeds regardless** — "advisory but very clear," never a barrier.

## 9. Conventions reused / consistency with prior specs

- **`2026-06-22` (outline front door):** cites §1 (multi-strand model → the rubric's strand
  vocabulary), §7 (`scaffold-review.md` is the *mechanical* lens; this is the distinct
  *craft* lens — named `outline-review.md`/`outline-feedback.yaml` to avoid collision), and
  §8 (the no-API tool-difference topology → Claude + Codex panel). No contradiction: the
  front door forbade a *soft LLM gate for structural validity*; this tier gates nothing.
- **`developmental-editor` (`2026-06-27`):** the outline-tier craft sibling — but diverges
  deliberately: a **panel** not a single reader, **prose** not scores, a **tracked ledger**
  not a one-shot verdict, and **no cross-model *requirement*** (independence here is
  reviewer diversity, not drafter-avoidance).
- **Beta layer (`2026-06-21`):** reuses its *multi-model dispatch* pattern but **inverts its
  convergence** — side-by-side, no K-of-M quorum.
- **`inspector-structure`:** the post-draft analogue for strand liveness; this is the
  pre-draft counterpart. Unchanged.
- **Genre-pack layer (`2026-07-08`):** rubric is pack data via `penny_genre.py` (no drift).
- **Dependency-split rule:** the nested human-edited ledger → **PyYAML** (right side of the
  rule, like the whodunit ledgers), not `penny_meta`.
- **Gate isolation:** the ledger lives **outside** `ch-MM.reviews/`, is never read by
  `review_gate.py`, and emits no `^BLOCKING:` — zero blockers by construction.

## 10. Error handling

| Piece | Hard-fail (nonzero) | Non-blocking / soft |
|---|---|---|
| `/review-outline` precondition | missing `outline.md` or missing genre `outline-craft.md` | — |
| panel member unreachable | — (degrade + record "independence reduced") | advisory read continues |
| `outline-reviewer` / Codex (agents) | — (agents never hard-gate) | the whole read is advisory |
| `outline_feedback.py status` | **never** (reporting-only; always exit 0) | the banner is a notice |
| `/draft-chapter` banner step | — | proceeds regardless of open items |

Only operational misses (no outline / no rubric) hard-fail. The craft read, the panel, and
the banner are strictly non-blocking.

## 11. Config / run-mode (swappable layer)

Added to `config/run-config.md`:

```yaml
outline_review_panel: [claude, codex]   # independent reviewers; extensible; degrades if one is unreachable
```

- **No approval mode** — it never gates, so there is no `*_approval` pause (contrast
  `scaffold_approval` / `ledger_approval`).
- **Rubric is pack data**, not run-config: `genres/<g>/review-rubrics/outline-craft.md`.

## 12. Testing strategy

Test-first for the deterministic script; structure assertions + manual e2e for the
agent/command/panel (no unit tests for LLM judgment, per CLAUDE.md).

- **`tests/test_outline_feedback.py` vs `tests/fixtures/`:**
  - `status`, ledger absent → nudge, exit 0.
  - `status`, all items `solved`/`rejected`, sha matches → "no open items", exit 0.
  - `status`, 2 items `open`, sha matches → banner names 2 open + the ledger path, exit 0.
  - `status`, sha mismatch → **stale** banner, exit 0, regardless of open count.
  - `status` **never** returns nonzero on any input (explicit — it must not block a draft).
  - `render` → produces side-by-side md grouped by pass/source, open items foregrounded,
    solved/rejected collapsed; is a pure function of the yaml.
  - **Append-only invariant:** given a ledger with a `solved` and a `rejected` item, a
    simulated new pass's items are appended with fresh IDs and the existing items'
    `state`/`text`/`id` are **byte-identical** afterwards. (This is the load-bearing test.)
  - Fixtures **self-contained** — never live `series/` content (the `readiness_check`
    lesson: fixtures reaching into live content rot on repo reset).
- **Agent/command/panel layer:** prose runbook → assertions on the produced ledger shape
  (IDs monotonic, `source`/`pass`/`state:open` stamped, `reviewed_outline_sha256` set) +
  **manual e2e on the Book-1 outline** across two passes (verify pass-2 dedup against the
  ledger and that a hand-set `solved`/`rejected` survives pass 2).
- **Not tested (scope guard):** reviewer *judgment quality* (UAT, like every Penny agent);
  Codex extraction fidelity; the deferred status-line indicator and the resolve/reject
  command shortcut.

## 13. Build sequence (each piece testable as built)

1. **`scripts/outline_feedback.py`** (`render` + `status`) + `tests/test_outline_feedback.py`
   + fixtures — including the **append-only invariant** test. Pure deterministic, fully
   unit-testable, depends only on PyYAML (already a dep). (TDD — the genuinely-new engine
   logic and the one place correctness lives.)
2. **`genres/cozy-mystery/review-rubrics/outline-craft.md`** — the seed coverage checklist
   (§5). Pack data.
3. **`agents/outline-reviewer.md`** — the Claude reviewer; prose points, solution-blind,
   dedup-aware (§4). No unit tests (LLM); validated by manual e2e + the ledger-shape assertions.
4. **`commands/review-outline.md`** — the orchestrator (§7): dispatch the panel (Claude +
   Codex), decompose→append, render, print. Add `outline_review_panel` to `run-config.md`.
5. **Banner hook** — one non-blocking step in `commands/draft-chapter.md` running
   `outline_feedback.py status NN` (§8).

The deterministic ledger logic lands first and standalone; the panel/command build on
shipped, untouched infrastructure (`penny_genre`, the codex runtime, the
continuity/arc-ledger layer, `draft-chapter`).

## 14. Open sequencing decision (for review)

Independent of the thriller pack, but shares the genre-pack-rubric pattern. Options:

- **Own small phase after Phase 4 (recommended):** ship the thriller pack first (specced,
  awaiting review), then this. Keeps phases single-purpose; this tier serves *both* genres,
  so building it once a second pack exists lets the cross-genre rubric contract be exercised
  immediately.
- **Ride with Phase 4:** fold `outline-craft.md` into the thriller-pack phase since both add
  pack rubrics. Cheaper context-switch, but couples two unrelated deliverables.

Recommendation: **own phase after Phase 4.** Decide at spec review.
