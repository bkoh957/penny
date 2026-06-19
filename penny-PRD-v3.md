# PRD — Penny

**Product:** **Penny** — a modular, Claude Code–native system for producing a
13-book commercial fiction series with independent quality review.
**Author:** [showrunner] · **Status:** Draft v3 · **Source:** penny-design-v3.md
**Orchestration:** Claude-Code-native (Option A) · **MVP 1 endpoint:** finished,
cross-model-reviewed manuscript (EPUB output is post-MVP-1).

> **v3 note:** updated alongside the design v2→v3 gap-resolution pass. Adds P0.10
> (`/plan-mystery`), P1.6 (drafter self-audit), and tightens P0.2/P0.3/P0.6 with
> the resolved mechanisms. See change log at the foot.

---

## Problem Statement

Producing a long commercial fiction series with AI is currently unreliable:
single-pass generation drifts in continuity across books, exhibits well-known
craft failures (sagging middles, flat voice, telling-not-showing, unfair
mysteries), and has no independent quality check. A solo author or small studio
wanting to ship a 13-book Kindle series needs a repeatable pipeline that
compensates for these failure modes and produces polished manuscripts — not a
one-off generator tuned to a single book. Without it, quality is inconsistent
book-to-book, continuity errors break reader immersion by book three, and manual
editing becomes the bottleneck the automation was meant to remove.

---

## Goals

1. **Genre/location independence** — swapping genre or setting requires editing
   config only, with zero changes to the engine.
2. **Continuity integrity across 13 books** — eliminate canon contradictions
   (facts, timeline, character knowledge-state) across the full series.
3. **Compensate for known AI-fiction failure modes** — every failure mode has
   both an authoring mechanism and an independent check.
4. **Genuinely independent review** — every quality verdict comes from an agent
   that did not write the work, with cross-model review available.
5. **Polished, reviewed manuscripts** — produce finished, cross-model-reviewed
   manuscripts with showrunner approval at the book level. (Format/EPUB output is
   a post-MVP-1 extension.)

---

## Non-Goals

1. **Not a one-book generator** — tuning the engine to a single title is out of
   scope; project-specific content lives in config.
2. **Not autonomous publishing** — Penny produces manuscripts; it does not upload,
   price, or market.
3. **Not cover art generation** — a separate ComfyUI pipeline handles covers; this
   PRD ends at the manuscript.
4. **Not EPUB output in MVP 1** — formatting and EPUB proofing are deferred
   post-MVP-1 (self-contained, easy to bolt on; not needed to validate the core
   value of reliable, reviewed prose).
5. **Not originating creative vision** — the showrunner sets the series bible,
   voice, and visual canon; agents enforce and extend, not invent.
6. **Not human-free quality sign-off** — taste-level calls (would a reader buy
   book 2?) escalate to the showrunner. Mystery design (P0.10) is likewise a
   deliberate human pre-flight per book, not automated away.

---

## User Stories

**Showrunner (the human operating Penny)**
- As the showrunner, I want to swap genre/setting/persona config without touching
  the engine, so that the same harness can produce a different series.
- As the showrunner, I want to set a book's mystery core once and have an agent
  propose the clue/red-herring/alibi construction, so that I spend judgment on
  taste and strategy, not combinatorial bookkeeping.
- As the showrunner, I want to run the pipeline chapter-by-chapter first, then
  per-book once stable, so that I can debug cheaply before scaling.
- As the showrunner, I want consensus quality problems and "wouldn't buy next
  book" signals escalated to me, so that I spend attention only where taste is
  required.
- As the showrunner, I want a status bar showing book/chapter/stage/gate, so that
  I always know where the pipeline is in a long session.

**Engine (sub-agents + commands, on behalf of the showrunner)**
- As a pipeline command, I want to load only the relevant ledger slice per
  chapter (canon-core + brief-derived sections + one-hop links), so that context
  stays small and continuity stays accurate.
- As a pipeline command, I want to hold the gate on any blocking issue, so that
  structural faults never reach later stages.
- As a pipeline command, I want a dedicated post-gate updater to fold a finalized
  chapter into the ledgers, so that I never grade a chapter against canon it just
  rewrote.

**Reviewer agents**
- As a blind inspector, I want only the text, one rubric, and the relevant ledger
  slice, so that my verdict is independent.
- As a cross-model reviewer, I want a fixed input/output contract, so that I plug
  in without engine changes.
- As a beta-reader persona, I want only the text (no ledgers, no solution), so
  that I react like a real reader.

**Edge/boundary cases**
- As a command, when reviewers disagree on whether an issue is *blocking*, I want
  to hold the gate and escalate rather than average, so that lenient verdicts
  don't mask faults.
- As a command, when reviewers disagree only on *degree* (score spread), I want to
  log it to the revision-priority report without holding the gate, so that
  contentious-but-passing chapters are still surfaced.
- As a copy-edit agent, I want only the text and the style sheet (not drafting
  history), so that I review with fresh eyes.
- As the final-reader, I want to run on a different model than drafted the book,
  so that the holistic read is genuinely fresh — and I want that enforced by a
  config assertion, not a checklist.

---

## Requirements

### Must-Have (P0) — MVP 1 is not viable without these

**P0.1 — Engine/config separation (Option A).**
Sub-agent definitions, slash-commands, and gate logic are the fixed engine; all
project specifics live in `/config` and `/series`.
- [ ] Genre, setting, voice, rubrics, personas are file-based config.
- [ ] Swapping a genre pack requires no engine edit.
- Given a new genre pack, when commands are repointed, then a chapter generates
  under the new conventions with no engine change.

**P0.2 — Series memory (sectioned ledgers + knowledge-state).**
Version-controlled continuity ledger as an **addressable directory**
(`/series/continuity/` with `canon-core.md` + per-`characters`/`locations`/
`threads` entry files carrying `id`/`type`/`links`), per-character knowledge-state,
and whodunit-ledger; read before each chapter and updated after the gate.
- [ ] Per-chapter load set = `canon-core` + brief-derived sections + one-hop links.
- [ ] Plan-step brief-quality gate: entities named by ledger `id`, not
  descriptively (makes the slice loader deterministic).
- [ ] Ledger updated post-**gate** (not post-draft) by the dedicated updater
  (see P0.5); write-scope bounded to the loaded slice.
- Given a fact established in chapter 3, when chapter 9 is drafted, then a
  contradiction is flagged before the gate passes.

**P0.3 — Developmental gate with independent inspectors.**
Blind Tier-1 sub-agents (one rubric each) + Tier-3 deterministic `/scripts`
checkers (fair-play, continuity, alibi/timeline, voice-drift). Any blocking issue
holds the gate; disagreements escalate per the two-signal rule.
- [ ] No reviewer inherits drafting history or other verdicts (sub-agent isolation).
- [ ] A blocking issue from any single reviewer holds the gate.
- [ ] **Blocking/non-blocking disagreement** between reviewers holds the gate and
  escalates (`escalate_on_blocking_disagreement: true`).
- [ ] **Same-dimension score spread** ≥ `score_spread_log_threshold` (default 2)
  logs to the revision-priority report and does **not** hold the gate.
- [ ] **Structure inspector** receives a thread roster (outline thread list / arc-ledger
  slice) and flags any thread dormant beyond `thread_dormant_after_chapters` (single-book
  liveness; the ledger-updater does not own this).
- **Two-signal logic is dormant in the MVP 1 default.** At `panel_size: 1` (the
  recommended early setting) the gate is held almost entirely by single-reviewer
  blocking issues plus the Tier-3 scripts; the disagreement logic above activates
  only once panels grow (cross-model panels, P1.2). It is infrastructure built now
  and plugged in later — not load-bearing on day one.
- Given a clue revealed without prior planting, when the fair-play script runs,
  then the gate is held and a blocking issue is logged.

**P0.4 — Failure-mode compensation.**
Each failure mode maps to a named rubric file and a named check.
- [ ] Every row in the §8 design table mapped to a rubric + check.
- [ ] Tell-tale AI sentence structures covered by the three-tier AI-prose defense
  (design §8a): Tier-A `ai-tics-detection.md` → `voice_drift.py`; Tier-B
  `self-audit-checklist.md` → drafter self-audit (P1.6); Tier-C
  `ai-prose-taste-flags.md` → blind inspector. Genre-config, Book-1-tunable.
- Given a chapter with monotone rhythm, when the voice-drift script runs, then low
  variance is flagged.

**P0.5 — Descending-funnel prose passes + post-gate ledger update.**
Developmental → line-edit → copy-edit → finalize, in order. Copy-edit runs on a
fresh-context sub-agent with the style sheet only. Finalize runs the dedicated
`ledger-updater` sub-agent.
- [ ] Line-edit runs only after the developmental gate passes.
- [ ] Copy-edit sub-agent receives text + style sheet, never drafting history.
- [ ] Style sheet updated with new decisions.
- [ ] `ledger-updater` runs at finalize (post-gate), proposes `ch-NN.ledger-diff.md`,
  commits on `ledger_approval: auto` / pauses on `review`; literal/extractive
  posture; write-scope bounded to the loaded slice.

**P0.6 — Cross-model final read (drawer-time rule), config-enforced.**
The final holistic pre-assembly read runs on a different model than drafted it,
enforced deterministically.
- [ ] `run-config.md` declares model-per-role.
- [ ] Config-invariant pre-flight in `assemble-book`: `final_read_model != drafting_model`
  (hard-fail; difference, not a specific model identity).
- [ ] **Set-membership reality check**: collect every chapter's `drafted_by` stamp,
  dedupe, assert `final_read_model ∉ {drafted_by stamps}` — hard-fail otherwise.
  Closes the mid-book-model-swap case.
- [ ] Provenance stamps (`drafted_by`/`reviewed_by`/`read_by`) on artifacts.

**P0.7 — Book assembly + standalone-vs-arc check.**
Chapters assemble into a manuscript; a check confirms the book resolves its
mystery while leaving the right personal thread open.
- [ ] `book-NN.manuscript.md` produced from finalized chapters.
- [ ] Standalone-vs-arc check runs at book level.

**P0.8 — Showrunner approval at book level + revision-priority report.**
- [ ] Beta readers run at **book level** on the assembled manuscript (not per
  chapter); their reaction reports feed the book-level revision-priority report.
- [ ] Consensus put-down points and "wouldn't buy next" escalate to the showrunner.

**P0.9 — TUI status bar.**
A status line shows live harness state by reading `.penny/current-stage`, `/output`
progress, review verdicts, and the session JSON context %.
- [ ] Pipeline commands write the current stage to `.penny/current-stage`.
- [ ] `scripts/penny-statusline.sh` renders book/chapter/stage/gate + context %.
- Given the pipeline is mid copy-edit on book 3 chapter 7, when the status line
  refreshes, then it shows that stage and position.

**P0.10 — Per-book mystery design + lock (`/plan-mystery`).**
The whodunit-ledger and sealed solution are authored before drafting, by separated
roles, and locked.
- [ ] `/plan-mystery N`: showrunner sets core (culprit, deception, arc
  constraints) → `mystery-planner` proposes clue schedule + red herrings + alibi
  grid → showrunner approves → writes `whodunit-ledger.md` (per-chapter clue
  schedule) + sealed `mystery-solution.md` → sets `book-NN.mystery.lock`.
- [ ] `/draft-chapter` hard-fails (deterministic pre-flight) if the book's
  whodunit-ledger is absent, unpopulated, or unlocked.
- [ ] Drafter receives only **this chapter's** clue-planting obligations; full
  `mystery-solution.md` is sealed from drafter, beta readers, and final reader.
- [ ] Re-running `/plan-mystery` re-locks and flags affected chapters for recheck.
- Given a clue handed to chapter 5's drafter, when the chapter is drafted, then it
  plants that clue without the drafter having seen the culprit's identity.

### Nice-to-Have (P1) — strong fast-follows

**P1.1 — Beta-reader module live** with defined personas and `beta-protocol.md`
report format. Runs at **book level** on the assembled manuscript (P0.8, design
§5c/§10). Currently stubbed.

**P1.2 — Cross-model panels** across Codex/Hermes/OpenClaw for inspection and beta
reaction; convergence treated as strong signal. Uses the `reviewed_by` provenance
stamps from P0.6 for convergence analysis.

**P1.3 — Accumulating banned-phrase list and voice baselines** compounding across
the 13 books (the "Penny" effect).

**P1.4 — Run-mode flags** (cadence, panel size, gate strictness, escalation scope)
as `run-config.md` settings.

**P1.5 — ccstatusline composition** — delegate the generic git/cost/context-bar
widgets to ccstatusline via a wrapper, if the richer display is wanted. (MVP 1
default: single script.)

**P1.6 — Drafter self-audit (cost optimization, not a quality gate).**
After Draft, before the developmental gate, the drafter runs a mechanical
detect-and-restructure pass against the Tier-B checklist
(`/config/self-audit/self-audit-checklist.md`: repeated openers, named-emotion
telling, banned-phrase hits, obvious clue-planting gaps). **Quality is guaranteed
by the independent inspectors regardless** — the self-audit's only job is to lower
the **revision-loop count** (target ≤2) by arriving at the gate cleaner. It is P1
because MVP 1 reaches the same quality without it, just with more loops; its worth
is measured by a drop in revision-loop count once enabled (see Success Metrics).
- [ ] Produces a revised draft only; emits **no** self-assessment.
- [ ] Inspectors receive no signal that a self-audit occurred (independence preserved).
- [ ] Framed as "detect-and-restructure," never "rate your compliance."

### Future Considerations (P2) — design for, don't build yet

**P2.1 — Format-proof / EPUB pipeline `[POST-MVP1]`** — compile to EPUB; EPUB proof
agent (EPUBCheck + metadata incl. series index + rendered read) as a terminal
blocking gate; `output-targets` per store. Slot and contract already reserved.

**P2.2 — Cover-art pipeline integration (ComfyUI)** — agentic concepting, prompt
generation against a series visual canon, multimodal cover review. Trigger point
(draft done → title → cover) noted so it slots in cleanly.

**P2.3 — Option-C migration** — move orchestration from command-instructions to a
deterministic code controller once prompts/rubrics/ledgers stabilize; agent and
config files carry over unchanged.

**P2.4 — Alternate output formats** (print PDF) via a swappable format-proof module.

**P2.5 — Spin-off / series-expansion support** — arc-ledger structured to allow a
later spin-off without retrofitting.

---

## Success Metrics

**Leading indicators (days–weeks)**
- **Continuity defect rate** — continuity blocking issues per finished chapter.
  Target: trending to <0.1 by end of Book 1; stretch: 0 across a book.
- **First-pass gate rate** — % of chapters passing the developmental gate without
  a revision loop. Target: ≥60% by mid–Book 1; stretch: ≥80%.
- **Fair-play pass rate** — % of mysteries with all needed clues planted before the
  reveal. Target: 100% (hard requirement).
- **Revision-loop count per chapter** — average loops to final. Target: ≤2.
  *This is also the measure of the P1.6 self-audit's worth: enabling it should
  produce a measurable drop in revision-loop count; if it doesn't, it isn't
  earning its cost.*

**Lagging indicators (weeks–months)**
- **Cross-book consistency** — cross-book reviewer flags per new book. Target:
  decreasing across the series.
- **Beta "would-buy-next" rate** — % of persona panels answering yes at book level.
  Target: ≥75% consensus before a book is approved. *(Depends on P1.1.)*
- **Showrunner-touch ratio** — human edits/decisions per finished book. Target:
  decreasing across Books 1→13 as baselines, style sheet, and `ledger_approval`
  shift from `review` to `auto` (the Penny effect).
- **Throughput** — calendar time per finished manuscript once unattended. Target:
  baseline at Book 2, improve thereafter.

Measurement: counts logged to `/output/.../reports`; evaluate at end of each book.

---

## Open Questions

- **[Showrunner] Beta-reader personas** — which archetypes, how many, exact
  `beta-protocol.md` format? *(Blocking for P1.1; non-blocking for P0. Deferred to
  Phase 5.)*
- **[Showrunner] Run-mode defaults** — recommendations recorded in `run-config.md`
  (chapter cadence + `panel_size: 1` + strict gate + `ledger_approval: review`
  early). *(Non-blocking; tune during Book 1.)*
- **[Engineering] Cross-model adapters** — confirm API access + uniform contract
  for Codex/Hermes/OpenClaw. *(Blocking for P1.2; P0.6 needs ≥1 alternate model
  reachable — the `!=` invariant lets any reachable alternate satisfy it.)*
- **[Research] Lexicon accuracy** — verify coastal-Victorian idiom and AFL
  loyalties before locking the Setting Pack. *(Blocking for setting lock, not engine.)*
- **[Data] Metric instrumentation** — what writes the gate/defect/loop counts, and
  where? *(Non-blocking; needed before metrics are trustworthy. Note Option-A
  limitation: metrics are command-written, not code-emitted.)*
- **[Decision] Metaphor-pool detection** (Tier-A AI-tics, design §8a) — keyword/
  n-gram count vs. LLM-assisted classifier. *(Non-blocking; default keyword-count
  seed for Book 1, revisit if it under-catches.)*

---

## Timeline / Phasing

Follows the design build order; each phase is independently useful. MVP 1 = phases
1–6.

1. **Skeleton** — repo, `.claude/` scaffold, sectioned continuity ledger +
   `canon-core`, style sheet, **`run-config.md` created with the model-per-role
   block + run-mode flags + thresholds** (so all later references resolve), one
   genre/voice/setting pack, status bar. Manual single-chapter runs. *(P0.1, P0.2, P0.9.)*
2. **Review Bus** — Tier-1 blind sub-agents (incl. Tier-C AI-prose taste inspector)
   + Tier-3 `/scripts` checkers (incl. `voice_drift.py` consuming Tier-A
   `ai-tics-detection.md`); structure-inspector thread roster; wire two-signal
   conflict resolution. *(P0.3, P0.4.)*
3. **Mystery + Cross-model** — `/plan-mystery` + lock pre-flight; `/scripts`
   adapters; `preflight.py` set-membership routing assertion + provenance stamps. *(P0.10, P0.6, P1.2.)*
4. **Prose passes** — line-edit + copy-edit + post-gate ledger-updater; accumulate
   style sheet. *(P0.5, P1.3; self-audit P1.6 + Tier-B `self-audit-checklist.md`
   fast-follow.)*
5. **Beta layer** — personas + protocol; reaction reports. *(P1.1.)*
6. **Book loop** — commands run chapter-by-chapter across an outline; book-level
   approval; standalone-vs-arc check. **← MVP 1 endpoint.** *(P0.7, P0.8.)*
7. **`[POST-MVP1]` Format + ship** — EPUB compile + EPUB proof agent. *(P2.1.)*
8. **Series scale** — arc-ledger across all 13 with cross-book reviewers.

**Dependencies:** P0.6 depends on ≥1 alternate model being reachable. P0.10 is a
pre-flight for all drafting and must land before the book loop. P1.1 depends on
the persona/protocol decision. Setting-pack lock depends on the research pass.
EPUB phase depends on the output-target spec.

**No hard external deadlines** identified; phasing is gated by quality thresholds
(advance when the prior phase's leading metrics hit target), not dates.

---

## Change log — v2 → v3

- **Added P0.10** — `/plan-mystery` (whodunit-ledger + sealed solution authored by
  separated roles, locked; drafter hard-fails without it; per-chapter clue
  obligations only).
- **Added P1.6** — drafter self-audit as a fix-pass that emits no verdict.
- **P0.2** — ledger is now a sectioned addressable directory; load set defined;
  brief-quality gate added; updates moved post-gate.
- **P0.3** — two-signal disagreement rule made explicit (blocking-split hard
  escalate; same-dimension score spread soft log).
- **P0.5** — added the post-gate `ledger-updater` step + `ledger_approval` flag.
- **P0.6** — cross-model rule made a deterministic config assertion (`!=`) with
  provenance stamps and a reality check.

### Showrunner feedback round (within v3)

- **Beta at book level** (P0.8, P1.1) — beta readers react to the assembled
  manuscript, not per chapter.
- **P0.3** — added the explicit "two-signal logic dormant at `panel_size: 1`" note
  and the structure-inspector thread-roster check (single-book thread liveness).
- **P0.4** — "every row in the §8 table" instead of a hardcoded count; wired the
  three-tier AI-prose defense (Tier-A/B/C config files).
- **P0.6** — reality check upgraded to **set membership** (`final_read_model ∉
  {drafted_by stamps}`), closing the mid-book-swap case.
- **P1.6** — reframed as a cost optimization measured by revision-loop reduction;
  consumes the Tier-B `self-audit-checklist.md`.
- **Phase 1** — `run-config.md` named an explicit skeleton deliverable so later
  references don't dangle.
- **Success Metrics** — revision-loop count doubles as the self-audit's worth gauge.
- **Open Questions** — added the metaphor-pool detection decision (keyword vs. LLM).
