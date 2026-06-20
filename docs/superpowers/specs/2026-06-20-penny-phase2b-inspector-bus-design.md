# Penny Phase 2b — Inspector Bus — Design

**Status:** Draft v1 · **Date:** 2026-06-20 · **Phase:** 2b of the Review Bus
(Phase 2 split into 2a deterministic checkers → 2b inspector bus).
**Source:** brainstorming session 2026-06-20; design `penny-design-v3.md` §6, §8,
§8a; PRD `penny-PRD-v3.md` P0.3, P0.4; 2a spec
`docs/superpowers/specs/2026-06-19-penny-phase2a-deterministic-checkers-design.md`.

---

## 1. Scope & Architecture

Phase 2b builds the **judgment layer** of the Review Bus on top of 2a's
deterministic checkers, plus the orchestrator that fuses both into a single gate
decision. The split that runs through the whole phase:

- **Inspectors are non-deterministic prompt files** — LLM judgment, structurally
  isolated as Claude Code sub-agents (a sub-agent never inherits the drafter's
  context — design §6). Each conforms to the fixed review contract.
- **The gate arithmetic is a deterministic, TDD'd script** (`review_gate.py`) —
  the design's stated mitigation for Option-A's soft-gate weakness ("push the
  hardest checks into `/scripts` where they ARE deterministic", §12).
- **`review-chapter` is the thin glue** — assembles context, dispatches inspectors,
  runs the 2a scripts, calls the gate evaluator, surfaces the result.

**In scope:**
- Five Tier-1 blind inspector sub-agents + their rubrics (one rubric per inspector).
- `scripts/review_gate.py` — deterministic gate evaluator (PASS/HOLD + two-signal
  conflict resolution).
- `scripts/reset_reviews.py` — re-run cleanup primitive.
- `scripts/penny_verdict.py` addition — `BLOCKING_RE` + `count_blocking()`, the
  single home of the blocker-line convention.
- `.claude/commands/review-chapter.md` — the orchestrator command.
- TDD suite for the deterministic pieces; scaffold/wiring tests for the prompt files.

**Explicitly out of scope (later phases), each tagged with its destination:**
- `inspector-location` / lexicon-fluency checks → Phase 3+ (Setting Pack maturity).
- A standalone craft inspector (telling-not-showing, conflict-resolved-too-easily,
  lack-of-subtext) → later; a couple of flags may fold into existing rubrics.
- The **deterministic alibi/timeline internal-consistency script** (design §6's
  separate "alibi/timeline checker") → Phase 3 mystery work (2a already deferred it;
  it is a *script*, not an inspector).
- Cross-model routing for `inspector-ai-prose` (Tier-2) → P1.2.
- Auto revision-loop on HOLD → Phase 4+.
- Book-level **revision-priority report** aggregation of escalations/score-spread →
  Phase 6 (P0.8).
- Ledger-updater maintaining `last_advanced_chapter` → Phase 4 (thread-liveness is
  best-effort until then; see §4).
- The two-signal conflict logic is **built now but dormant at `panel_size: 1`**
  (activates with `panel_size: 3` or cross-model panels, P1.2). Dormancy is a
  **tested** state — see §7.

**Reuse & dependencies:** reuses `penny_verdict.py` (verdict envelope, unchanged
except the additive counter), `penny_meta.py` (flat frontmatter / yaml-blocks),
the Phase 1 `output/book-NN/chapters/ch-NN.reviews/` location and `^BLOCKING:`
convention, the §4.2 ledger-slice logic from `draft-chapter`, and the two 2a
scripts (`voice_drift.py`, `fairplay_check.py`). No new third-party dependency
(PyYAML already present from 2a; the gate reads flat `run-config.md` via
`penny_meta`).

---

## 2. The Five Inspectors

Each is a blind Tier-1 sub-agent (design §6) following `.claude/agents/_TEMPLATE.md`.
Each receives the **fixed review contract** input and writes a verdict via
`penny_verdict.write_verdict(...)` with `kind: inspector` and a `score: 1-5`:

```
review contract  (design §6)
  input:  { text, rubric, ledger_slice }
  output: { score 1-5, violations[], blocking_issues[], evidence[], reviewed_by }
```

No inspector sees drafting history, the sealed solution, or another inspector's
verdict. The `ledger_slice` is assembled once by `review-chapter` and passed
uniformly to all five (the contract is fixed); the continuity/fairplay/structure
inspectors lean on it, voice/ai-prose largely ignore it.

| Inspector (`producer`) | Rubric file | Judges | May block? |
|---|---|---|---|
| `inspector-continuity` | `config/review-rubrics/continuity-drift.md` | chapter vs. ledger slice — fact contradictions, knowledge-state violations (a character acting on info they shouldn't yet have) | yes |
| `inspector-fairplay` | `config/review-rubrics/fairplay-planting.md` | **prose-planting**: did this chapter's *scheduled* clues actually land in the scene, fairly (not buried/cheated) — the page-level complement to 2a's ledger-consistency script | yes |
| `inspector-structure` | `config/review-rubrics/structure-tension.md` | tension curve / sagging middle + **thread-roster liveness** (threads idle beyond N — see §4) | yes |
| `inspector-voice` | `config/review-rubrics/character-voice.md` | consumes `voice_drift.py` *evidence* + a flat-character "voice blind test"; **makes the blocking call `voice_drift.py` structurally cannot** | yes |
| `inspector-ai-prose` | `config/review-rubrics/ai-prose-taste-flags.md` *(already exists)* | Tier-C earned-vs-rote taste (design §8a); same-model in 2b, cross-model later | yes |

**`producer` is the canonical dimension key.** The two-signal logic groups verdicts
by `producer`; the five inspectors **must declare five distinct `producer` values**
(asserted by the scaffold test, §7) so two inspectors can never silently merge into
one "dimension."

### Relationship to the 2a scripts (no duplication)

- `inspector-fairplay` (prose) ≠ `fairplay_check.py` (ledger). The script asserts the
  *plan* is fair (clue scheduled before reveal, culprit floor, catchable alibi); the
  inspector reads the actual scene and judges whether the scheduled clue was
  *genuinely planted on the page*. Script checks the plan; inspector checks the page.
- `inspector-voice` (judgment) consumes `voice_drift.py` (evidence). `voice_drift.py`
  **never** emits `^BLOCKING:` (hard rule, 2a §2); the inspector turns that evidence
  into a gate decision and may block.

---

## 3. `scripts/review_gate.py` — deterministic gate evaluator

**CLI:** `python3 scripts/review_gate.py <reviews-dir> [--config config/run-config.md]
[--out <gate.md>]`. Default `--out` is the **chapters dir sibling**
`<reviews-dir>/../ch-MM.gate.md` — *not* inside `reviews/`, so the Phase 1 status
line's recursive grep never sees it (defense against double-count).

### 3.1 Inputs

Reads every verdict `*.md` in `<reviews-dir>` via `penny_meta` frontmatter,
**filtering by `kind`**: only `kind ∈ {inspector, deterministic-checker}` are
verdicts; `kind: gate-summary` is excluded so a stray prior `gate.md` is never
re-read as a verdict. Per verdict it extracts `producer`, `kind`, `score`
(inspectors only), and `^BLOCKING:` lines.

Reads the two thresholds from `run-config.md` via `penny_meta.parse_yaml_blocks`
(flat — the two-reader boundary of 2a §5): `escalate_on_blocking_disagreement`,
`score_spread_log_threshold`. **Fail-loud, no fallback** (same posture as
`fairplay_check.py` reading `culprit_by_fraction`): absent or non-numeric → nonzero
exit with a clear message.

### 3.2 Computes three things

1. **Gate decision.** `blocking_count = penny_verdict.count_blocking(<reviews-dir>)`.
   `PASS` iff `blocking_count == 0`, else `HOLD`. The count comes **only** from the
   shared `count_blocking()` — never re-implemented here (§5).
2. **Blocking/non-blocking disagreement (HARD escalate).** Group verdicts by
   `producer`; within any dimension having ≥2 verdicts, if they disagree on whether
   *any* issue is blocking → escalate (gate holds; case escalates). At
   `panel_size: 1` each dimension has one verdict, so this **sleeps**.
3. **Same-dimension score spread (SOFT log).** Within a dimension with ≥2 inspector
   scores, `max − min ≥ score_spread_log_threshold` → log only (does not hold the
   gate). Also sleeps at `panel_size: 1`.

### 3.3 Output — `ch-MM.gate.md` (a summary, not a verdict)

Critical correctness rule: **gate.md must never emit `^BLOCKING:` lines.** The Phase 1
status line counts `^BLOCKING:` across all files in the reviews dir; duplicating them
would double-count. (gate.md also lives *outside* the reviews dir — belt and
suspenders.) Summary lines use `- blocking [producer]: …` (lowercase, `- `-prefixed):

```
---
producer: review_gate.py
kind: gate-summary
target: book-01/ch-07
gate: HOLD
blocking_count: 2
schema: penny-verdict/1
---
- HOLD: 2 blocking issue(s)
- blocking [inspector-continuity]: Cora references Edwin's will before the ch-22 reveal
- blocking [inspector-fairplay]: scheduled clue 'torn-ticket' not present in scene
- escalations: []          # dormant at panel_size 1
- score_spread_log: []     # dormant at panel_size 1
```

Stdout first line: `GATE: PASS` / `GATE: HOLD (2 blocking)`.

### 3.4 Exit codes & error handling (fail loud)

- **Exit 0** on a *successful evaluation* — PASS **or** HOLD (a HOLD is a result, not
  a crash).
- **Nonzero** only on **operational error**, refusing to emit a gate:
  - **Malformed verdict** — a file present but missing `producer`, or a
    `kind: inspector` verdict missing `score`. A missing score is a **broken
    producer, not "no opinion"**; silently skipping it could vanish a real blocker.
  - **Empty reviews dir / zero verdict files** — means dispatch failed; passing an
    unreviewed chapter is the worst failure, so this is an error, **not** a vacuous
    PASS.
  - Missing/non-numeric thresholds in `run-config.md`; unreadable reviews dir.

---

## 4. `inspector-structure` thread roster (the cross-chapter wrinkle)

Thread-liveness ("thread X opened in ch 3, idle since") is inherently *cross-chapter*,
but a blind single-chapter inspector cannot know a thread's history. The honest
sourcing:

- `review-chapter` assembles the roster as `{thread_id, last_advanced_chapter}` from
  `series/continuity/threads/*.md` + `series/arc-ledger.md`, and passes it to
  `inspector-structure` (only).
- `last_advanced_chapter` is maintained by the **ledger-updater (Phase 4)**. Until
  then it is unpopulated → the roster carries the thread with an explicit `unknown`
  marker and the inspector **emits no liveness flag** (it does not compute liveness
  from null).
- So the thread-roster mechanism is **built and wired in 2b**, but its liveness
  signal is **best-effort until Phase 4** — the same "built now, fully active later"
  pattern as `fairplay_check.py` waiting on Phase 3's `/plan-mystery`.

The threshold is `thread_dormant_after_chapters` (already in `run-config.md`,
default 3). The structure inspector owns single-book liveness; the cross-book
reviewer (Phase 8) owns it *across* books; the ledger-updater does **not** own it
(design §8 — it records only what is on the page).

---

## 5. The blocker-line convention — one home

`penny_verdict.py` (the module that owns the verdict *format*) gains:

```python
BLOCKING_RE = re.compile(r"^BLOCKING:", re.MULTILINE)   # the canonical rule
def count_blocking(reviews_dir) -> int: ...             # counts ^BLOCKING: across *.md
```

This is a **format concern** ("what a blocker line looks like, and how many are in a
dir"), so it belongs with the verdict format, not with the panel judgment. The seam
from §1 holds: **`penny_verdict` owns the blocker-line convention; `review_gate` owns
the panel decision.** `review_gate.py` imports `count_blocking()` for both
`blocking_count` and PASS/HOLD and never re-implements counting.

**The status line stays bulletproof bash.** `penny-statusline.sh` keeps its one-line
`grep '^BLOCKING:'` mirror of the identical convention. We deliberately do **not**
make it shell out to Python: the status line is a *glanceable mirror*, not the
authority (the authoritative count is `review_gate`'s), and a `python3 -c "import…"`
on every ≤300ms tick would be both a perf regression and a robustness regression (a
broken import path would silently zero the count). A status indicator must never
break.

Agreement between the two implementations is **pinned by a cross-consistency test
that execs the *real* script** (§7) — not a transcribed grep. The convention string
`^BLOCKING:` is documented as the shared contract in both files.

---

## 6. `review-chapter` command flow

```
/review-chapter <book> <chapter>          # book=NN, chapter=MM (e.g. 01)
  0. RE-RUN CLEANUP: scripts/reset_reviews.py output/book-NN/chapters/ch-MM.reviews
       — empties the chapter's verdict files AND removes the stale sibling
         ch-MM.gate.md, so the gate reflects ONLY this run's verdicts. (Single-pass
         + manual loop means /review-chapter is re-run routinely; a fixed blocker
         from run 1 must not linger and hold the gate forever.)
  1. marker → .penny/current-stage:  book=NN chapter=MM stage=REVIEW
  2. assemble ledger slice (§4.2: canon-core + brief-derived + one-hop;
       canon-core-only fallback when no brief exists yet, like draft-chapter)
  3. run the 2a scripts:
       voice_drift.py   <draft>          → ch-MM.reviews/voice-drift.md   (ALWAYS)
       fairplay_check.py <book-NN.yaml>  → ch-MM.reviews/fairplay.md
         ONLY when MM == reveal_chapter of a locked ledger
         (avoids writing a book-level verdict into another chapter's dir; the
          book-level fairness gate belongs to the reveal chapter / assemble-book — a
          2b/3 wiring note)
  4. dispatch the 5 inspector sub-agents, each { text, its rubric, ledger_slice }:
       inspector-structure ALSO gets the {thread_id, last_advanced_chapter} roster
       (§4); empty-state → `unknown` marker, no liveness flag.
       → each writes its verdict into ch-MM.reviews/ via penny_verdict.py
  5. DISPATCH-COMPLETENESS CHECK (review-chapter owns this): the 5 inspectors it
       dispatched must EACH have produced a verdict; a missing one = silently-failed
       dispatch → error. This is DISTINCT from "fairplay.md may be absent" (normal
       pre-reveal / pre-Phase-3 state). review_gate.py itself gates on whatever
       verdicts are PRESENT and requires no fixed producer manifest.
  6. review_gate.py ch-MM.reviews/  → writes ch-MM.gate.md, prints GATE: PASS|HOLD
  7. marker → stage=REVIEWED (PASS) or GATE-HELD (HOLD); surface the result.
       SINGLE-PASS — no auto-revise. A HOLD is surfaced to the showrunner; re-drafting
       is a manual re-run (auto revision-loops are Phase 4+).
```

The two checks are deliberately separate: **review-chapter** asserts "my 5 dispatches
each produced output" (a real safety net for a silently-failed sub-agent);
**review_gate** asserts nothing about *which* producers exist — it counts what's
there, so fairplay legitimately absent pre-reveal is normal, not a gate error.

---

## 7. Testing Strategy (TDD)

**Deterministic — fully tested.**

- **`penny_verdict.count_blocking()` / `BLOCKING_RE`:** counts `^BLOCKING:` across
  `*.md`; anchored + case-sensitive — assert lowercase `blocking:` and a mid-line
  `BLOCKING:` are **not** counted.
- **Cross-consistency tripwire (most valuable test):** using the existing
  `test_statusline.py` harness, write N blocking verdicts, run the **real**
  `penny-statusline.sh`, parse the rendered `gate: N blocking`, and assert
  `N == count_blocking(dir)`. Wired to the real door — editing the bash counter
  fails this test.
- **`review_gate.py`:**
  - PASS (0 blockers) → `gate: PASS`, exit 0.
  - HOLD (≥1 blocker) → `gate: HOLD`, correct `blocking_count`, exit 0.
  - **Blocking/non-blocking disagreement** (≥2 verdicts, same `producer`) → escalation
    logged; with distinct producers (panel 1) → **no** escalation (proves dormant ≠
    broken).
  - **Same-dimension score spread** ≥ threshold → logged; below → not; silent at
    panel 1 (proves dormant ≠ broken).
  - **Malformed verdict** (missing `producer`; inspector missing `score`) → nonzero,
    no gate emitted.
  - **Empty reviews dir / zero verdicts** → nonzero operational error (not vacuous
    PASS).
  - **Filter by `kind`:** a planted `kind: gate-summary` file is ignored, never
    counted as a verdict.
  - Missing/non-numeric thresholds in `run-config.md` → nonzero (fail-loud).
  - **gate.md output** contains **zero** lines matching `BLOCKING_RE`; is written to
    the chapters dir, not inside `reviews/`.
- **`reset_reviews.py`:** populate a reviews dir + a sibling `gate.md` → reset →
  assert no verdict `*.md` and no stale `gate.md` remain.

**Prompt files — wiring/scaffold only (`tests/test_inspector_scaffold.py`),
no LLM judgment in CI (the 2a posture):**
- The 5 inspector agent files exist with valid frontmatter (`name`, `description`)
  and each names its rubric.
- The 4 new rubric files exist (+ `ai-prose-taste-flags.md` present).
- The 5 inspectors declare **5 distinct `producer` values**.
- `review-chapter.md` exists and references all 5 inspectors, both 2a scripts,
  `review_gate.py`, and the step-0 `reset_reviews.py` cleanup.

The disagreement/score-spread fixtures are the proof that the two-signal logic
**works when panels grow** — so "dormant at `panel_size: 1`" (§1) is a tested state,
not an assumed one.

---

## 8. File Structure

**Create:**
- `.claude/agents/inspector-continuity.md`, `inspector-fairplay.md`,
  `inspector-structure.md`, `inspector-voice.md`, `inspector-ai-prose.md`.
- `config/review-rubrics/continuity-drift.md`, `fairplay-planting.md`,
  `structure-tension.md`, `character-voice.md`.
  *(`ai-prose-taste-flags.md` already exists — reused as-is.)*
- `scripts/review_gate.py` — deterministic gate evaluator.
- `scripts/reset_reviews.py` — re-run cleanup primitive.
- `.claude/commands/review-chapter.md` — orchestrator command.
- `tests/test_review_gate.py`, `tests/test_reset_reviews.py`,
  `tests/test_inspector_scaffold.py`, and the cross-consistency test (in
  `test_review_gate.py` or `test_statusline.py`) + fixtures under `tests/fixtures/`.

**Modify:**
- `scripts/penny_verdict.py` — add `BLOCKING_RE` + `count_blocking()` (additive;
  existing `write_verdict` unchanged).
- `penny-design-v3.md` — §6 + §8 swept together: reclassify **continuity as a Tier-1
  inspector** (not a deterministic script) in both the §6 Tier-3 list and the §8
  table row; **alibi/timeline stays a deferred Tier-3 script**; move the
  **conflict-comparison role to `review_gate.py`** (from `preflight.py`) while noting
  **`preflight.py` keeps its §7 jobs** (model-routing set-membership, lock checks) —
  preflight is not cancelled; §2 — add `scripts/review_gate.py` and
  `scripts/reset_reviews.py` to the `/scripts` list.
- `README.md` — dev note for `review-chapter` usage.

**Out of scope (later phases):** see §1. `inspector-location`, the craft inspector,
the deterministic alibi/timeline script, cross-model routing, auto revision-loops,
the book-level revision-priority report, and ledger-updater history maintenance are
all deferred with their destination phases tagged.

---

## 9. Open Items / Deferred

- **Cross-model routing for `inspector-ai-prose`** (Tier-2, P1.2): the rubric already
  says "cross-model where reachable"; 2b runs it same-model, so it becomes a routing
  swap later with no engine change.
- **Two-signal conflict logic** is built and tested in 2b but **dormant at
  `panel_size: 1`** — it activates with `panel_size: 3` or cross-model panels (P1.2).
- **Thread-liveness** is wired in 2b but best-effort until Phase 4 maintains
  `last_advanced_chapter` (§4).
- **`fairplay_check.py` book-level gating** at assemble-book time (vs. only at the
  reveal chapter) is a Phase 3 wiring decision; 2b runs it at the reveal chapter.
- Whether to later collapse the bash status-line counter into the Python
  `count_blocking()` (paying the per-tick cost for one counter) instead of the
  exec-real-script tripwire — deferred; the tripwire is the 2b choice (§5).
</content>
</invoke>
