# PRD — Penny

**Product:** **Penny** — a modular, Claude Code–native system for producing a
13-book commercial fiction series with independent quality review.
**Author:** [showrunner] · **Status:** Draft v2 · **Source:** penny-design.md
**Orchestration:** Claude-Code-native (Option A) · **MVP 1 endpoint:** finished,
cross-model-reviewed manuscript (EPUB output is post-MVP-1).

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
   book 2?) escalate to the showrunner.

---

## User Stories

**Showrunner (the human operating Penny)**
- As the showrunner, I want to swap genre/setting/persona config without touching
  the engine, so that the same harness can produce a different series.
- As the showrunner, I want to run the pipeline chapter-by-chapter first, then
  per-book once stable, so that I can debug cheaply before scaling.
- As the showrunner, I want consensus quality problems and "wouldn't buy next
  book" signals escalated to me, so that I spend attention only where taste is
  required.
- As the showrunner, I want a status bar showing book/chapter/stage/gate, so that
  I always know where the pipeline is in a long session.

**Engine (sub-agents + commands, on behalf of the showrunner)**
- As a pipeline command, I want to load only the relevant ledger slice per
  chapter, so that context stays small and continuity stays accurate.
- As a pipeline command, I want to hold the gate on any blocking issue, so that
  structural faults never reach later stages.
- As a pipeline command, I want to update ledgers and the style sheet after each
  chapter, so that later books stay consistent.

**Reviewer agents**
- As a blind inspector, I want only the text, one rubric, and the relevant ledger
  slice, so that my verdict is independent.
- As a cross-model reviewer, I want a fixed input/output contract, so that I plug
  in without engine changes.
- As a beta-reader persona, I want only the text (no ledgers, no solution), so
  that I react like a real reader.

**Edge/boundary cases**
- As a command, when reviewers disagree beyond a threshold, I want to escalate
  rather than average, so that lenient verdicts don't mask faults.
- As a copy-edit agent, I want only the text and the style sheet (not drafting
  history), so that I review with fresh eyes.
- As the final-reader, I want to run on a different model than drafted the book,
  so that the holistic read is genuinely fresh.

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

**P0.2 — Series memory (ledgers + knowledge-state).**
Version-controlled continuity ledger, per-character knowledge-state, whodunit
ledger; read before each chapter and updated after.
- [ ] Relevant slice (not whole series) loaded per chapter.
- [ ] Ledger updated post-chapter.
- Given a fact established in chapter 3, when chapter 9 is drafted, then a
  contradiction is flagged before the gate passes.

**P0.3 — Developmental gate with independent inspectors.**
Blind Tier-1 sub-agents (one rubric each) + Tier-3 deterministic `/scripts`
checkers (fair-play, continuity, alibi/timeline, voice-drift). Any blocking issue
holds the gate; disagreements above threshold escalate.
- [ ] No reviewer inherits drafting history or other verdicts (sub-agent isolation).
- [ ] A blocking issue from any single reviewer holds the gate.
- Given a clue revealed without prior planting, when the fair-play script runs,
  then the gate is held and a blocking issue is logged.

**P0.4 — Failure-mode compensation.**
Each failure mode maps to a named rubric file and a named check.
- [ ] All ten failure modes mapped to rubric + check.
- Given a chapter with monotone rhythm, when the voice-drift script runs, then low
  variance is flagged.

**P0.5 — Descending-funnel prose passes.**
Developmental → line-edit → copy-edit, in order. Copy-edit runs on a
fresh-context sub-agent with the style sheet only.
- [ ] Line-edit runs only after the developmental gate passes.
- [ ] Copy-edit sub-agent receives text + style sheet, never drafting history.
- [ ] Style sheet updated with new decisions.

**P0.6 — Cross-model final read (drawer-time rule).**
The final holistic pre-assembly read runs on a different model than drafted it.
- [ ] Routing rule enforced: drafting model ≠ final-read model.

**P0.7 — Book assembly + standalone-vs-arc check.**
Chapters assemble into a manuscript; a check confirms the book resolves its
mystery while leaving the right personal thread open.
- [ ] `book-NN.manuscript.md` produced from finalized chapters.
- [ ] Standalone-vs-arc check runs at book level.

**P0.8 — Showrunner approval at book level + revision-priority report.**
- [ ] Consensus put-down points and "wouldn't buy next" escalate to the showrunner.

**P0.9 — TUI status bar.**
A status line shows live harness state by reading `.penny/current-stage`, `/output`
progress, review verdicts, and the session JSON context %.
- [ ] Pipeline commands write the current stage to `.penny/current-stage`.
- [ ] `scripts/penny-statusline.sh` renders book/chapter/stage/gate + context %.
- Given the pipeline is mid copy-edit on book 3 chapter 7, when the status line
  refreshes, then it shows that stage and position.

### Nice-to-Have (P1) — strong fast-follows

**P1.1 — Beta-reader module live** with defined personas and `beta-protocol.md`
report format. Currently stubbed.

**P1.2 — Cross-model panels** across Codex/Hermes/OpenClaw for inspection and beta
reaction; convergence treated as strong signal.

**P1.3 — Accumulating banned-phrase list and voice baselines** compounding across
the 13 books (the "Penny" effect).

**P1.4 — Run-mode flags** (cadence, panel size, gate strictness, escalation scope)
as command-level settings.

**P1.5 — ccstatusline composition** — delegate the generic git/cost/context-bar
widgets to ccstatusline via a wrapper, if the richer display is wanted.

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

**Lagging indicators (weeks–months)**
- **Cross-book consistency** — cross-book reviewer flags per new book. Target:
  decreasing across the series.
- **Beta "would-buy-next" rate** — % of persona panels answering yes at book level.
  Target: ≥75% consensus before a book is approved. *(Depends on P1.1.)*
- **Showrunner-touch ratio** — human edits/decisions per finished book. Target:
  decreasing across Books 1→13 as baselines and style sheet mature (the Penny effect).
- **Throughput** — calendar time per finished manuscript once unattended. Target:
  baseline at Book 2, improve thereafter.

Measurement: counts logged to `/output/.../reports`; evaluate at end of each book.

---

## Open Questions

- **[Showrunner] Beta-reader personas** — which archetypes, how many, exact
  `beta-protocol.md` format? *(Blocking for P1.1; non-blocking for P0.)*
- **[Showrunner] Run-mode defaults** — cadence, panel size, gate strictness,
  escalation scope? *(Non-blocking; tune during Book 1.)*
- **[Showrunner] Status-bar composition** — single bash script vs. ccstatusline
  wrapper? *(Non-blocking; default single script for MVP 1.)*
- **[Engineering] Cross-model adapters** — confirm API access + uniform contract
  for Codex/Hermes/OpenClaw. *(Blocking for P1.2; P0.6 needs ≥1 alternate model.)*
- **[Research] Lexicon accuracy** — verify coastal-Victorian idiom and AFL
  loyalties before locking the Setting Pack. *(Blocking for setting lock, not engine.)*
- **[Data] Metric instrumentation** — what writes the gate/defect/loop counts, and
  where? *(Non-blocking; needed before metrics are trustworthy. Note Option-A
  limitation: metrics are command-written, not code-emitted.)*

---

## Timeline / Phasing

Follows the design build order; each phase is independently useful. MVP 1 = phases
1–6.

1. **Skeleton** — repo, `.claude/` scaffold, ledgers, style sheet, one
   genre/voice/setting pack, status bar. Manual single-chapter runs. *(P0.1, P0.2, P0.9.)*
2. **Review Bus** — Tier-1 blind sub-agents + Tier-3 `/scripts` checkers; tune
   rubrics. *(P0.3, P0.4.)*
3. **Cross-model** — `/scripts` adapters; cross-model final-read rule. *(P0.6, P1.2.)*
4. **Prose passes** — line-edit + copy-edit; accumulate style sheet. *(P0.5, P1.3.)*
5. **Beta layer** — personas + protocol; reaction reports. *(P1.1.)*
6. **Book loop** — commands run chapter-by-chapter across an outline; book-level
   approval; standalone-vs-arc check. **← MVP 1 endpoint.** *(P0.7, P0.8.)*
7. **`[POST-MVP1]` Format + ship** — EPUB compile + EPUB proof agent. *(P2.1.)*
8. **Series scale** — arc-ledger across all 13 with cross-book reviewers.

**Dependencies:** P0.6 depends on ≥1 alternate model being reachable. P1.1 depends
on the persona/protocol decision. Setting-pack lock depends on the research pass.
EPUB phase depends on the output-target spec.

**No hard external deadlines** identified; phasing is gated by quality thresholds
(advance when the prior phase's leading metrics hit target), not dates.
