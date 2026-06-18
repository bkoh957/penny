# Penny — Design Specification

**Penny** is a modular, Claude Code–native system for producing a 13-book
commercial fiction series with independent quality review. Penny is genre- and
location-agnostic: it is a **writing harness, not a generator for one kind of
book.** The current project is a cozy-mystery series with a sea-change
protagonist set in a fictional town modelled on a seaside town in coastal
Victoria, Australia — but everything specific to that project lives in swappable
config, never in the engine.

The name carries the spirit of the system: small accumulating units of value
(the ledgers, the style sheet, the banned-phrase list all compound across books),
and "the penny drops" — the click of a mystery solving.

> **Status:** Draft v3 · **Source:** penny-design.md (v2) + gap-resolution pass.
> v3 closes seven design gaps surfaced in review: ledger-slice mechanism,
> cross-model routing enforcement, whodunit-ledger authorship, solution
> isolation, inspector-disagreement thresholds, self-audit classification, and
> knowledge-state update ownership. See the change log at the foot of this file.

> **Status legend:** `[STABLE]` defined and ready · `[STUB]` slot defined,
> contents to be filled later · `[POST-MVP1]` deferred past the first milestone ·
> `[DECISION]` open choice flagged for the human · `[P1]` defined but a
> fast-follow, not in MVP 1.

> **Orchestration choice (locked):** Penny is **Claude-Code-native (Option A).**
> The harness *is* a repository Claude Code executes — sub-agent definitions,
> slash-commands, and config files — with a thin script layer only for
> deterministic checks. There is no separate controller program in MVP 1.
> A future migration of the orchestration layer to a code controller (Option C)
> is anticipated once prompts, rubrics, and ledger formats stabilize; every
> agent file and config file carries over unchanged in that migration.

---

## 1. Master Design Principle: Modularity for Every Feature

Penny separates a fixed **engine** (orchestration conventions, memory, review
loops, gates) from swappable **config** (genre, voice, setting, rubrics, reader
personas). You never edit the engine to change books — you swap config. Changing
from "cozy mystery in coastal Victoria" to "grimdark space opera" means replacing
config folders; the engine does not move.

Every reviewer, checker, and reader is a **module conforming to a fixed
contract**, so new ones (including external models) plug in without touching the
engine.

**The independence principle (the spine of the whole system).** The entity that
*judges* whether work passes must never be the entity that *produced* it, and it
must see only what it needs. This single rule recurs throughout the design — in
blind inspectors (§6), in the separated mystery-design / drafting / checking
roles (§5a), in the dedicated post-gate ledger-updater (§4), and in the
cross-model final read (§7). Wherever a judgment matters, the judge is isolated
from the author.

---

## 2. Repository Layout

```
.claude/                      Claude-Code-native runtime (Option A)
  /agents                       sub-agent role definitions (blind, fresh context)
    drafter.md
    mystery-planner.md          proposes the whodunit construction (§5a)
    inspector-continuity.md
    inspector-fairplay.md
    inspector-alibi.md
    inspector-voice.md
    inspector-structure.md
    inspector-location.md
    line-editor.md
    copy-editor.md
    ledger-updater.md           literal/extractive post-gate record-keeper (§4)
    beta-reader.md              loads a persona
    final-reader.md             cross-model holistic read
  /commands                     the pipeline as slash-commands
    plan-mystery.md             per-book mystery design + lock (§5a)
    draft-chapter.md
    review-chapter.md
    edit-chapter.md
    finalize-chapter.md
    assemble-book.md
  settings.json                 statusLine config (see §11)

/scripts                      [STABLE] thin deterministic layer
  voice_drift.py                sentence-variance / repetition / tic stats
  fairplay_check.py             clue-planting cross-reference vs. whodunit-ledger
  preflight.py                  config invariants + lock + provenance checks (§5a, §7)
  penny-statusline.sh           TUI status bar reader (see §11)
  (epubcheck wrapper)           [POST-MVP1]

/config                       all swappable modules
  run-config.md                 [STABLE] model-per-role, run-mode flags,
                                escalation thresholds (§7, §12)
  /genre-pack                   [STABLE] cozy-mystery (swap per series)
  /voice-pack                   [STABLE] POV, tense, register, rhythm rules
  /review-rubrics               [STABLE] one file per failure mode (§8)
  /setting-pack                 [STABLE] coastal-Victoria AU (swap per location)
  /beta-readers
    /personas                   [STUB] reader archetypes — define later
    beta-protocol.md            [STUB] reaction-report format — define later
  /line-edit                    [STABLE] prose-refinement pass config
  /copy-edit                    [STABLE] grammar/consistency pass config
  /format-proof                 [POST-MVP1] EPUB proof config (stub slot)
    epub-proof.md               [POST-MVP1]
    /output-targets             [POST-MVP1] KDP/Kindle specifics
  length-profile                [STABLE] word-count targets per chapter/book

/series                       this project's data + living memory
  series-bible.md               overarching 13-book arc, themes, the long game
  arc-ledger.md                 which threads open/resolve in which book
  /characters                   STATIC character design: voice fingerprint, arc,
                                secrets (authored by showrunner; rarely changes)
  /world                        setting facts, the town, recurring locations
  /continuity                   [STABLE] sectioned, addressable continuity ledger (§4)
    canon-core.md                 always-loaded: protagonist fixed facts, current
                                  timeline position, active-book whodunit
                                  constraints, fluency-stage
    /characters
      <id>.md                     MUTABLE per-character knowledge-state + canonical
                                  facts established in-text (updated post-gate)
    /locations
      <id>.md                     per-location facts
    /threads
      <id>.md                     per-thread (objects, secrets, cross-book links)
  whodunit-ledger.md            per-book: culprit, per-chapter clue schedule,
                                red herrings, alibi grid (authored by /plan-mystery)
  style-sheet.md                accumulating spelling/punctuation decisions

/output
  /book-NN
    outline.md
    /chapters
      ch-NN.draft.md              frontmatter carries drafted_by: <model> (§7)
      ch-NN.reviews/              verdicts from inspectors (carry reviewed_by)
      ch-NN.ledger-diff.md        proposed ledger updates, post-gate (§4)
      ch-NN.final.md
    mystery-solution.md         sealed; never given to drafter, beta, or final readers
    book-NN.manuscript.md       assembled, cross-model-reviewed; carries read_by
    book-NN.epub                [POST-MVP1]
    /reports                    beta reaction reports, revision-priority report

.penny/                       runtime state for the TUI status bar (see §11)
  current-stage                 single-line marker the commands write as they run
  /locks
    book-NN.mystery.lock        set by /plan-mystery; gates /draft-chapter (§5a)
```

**Bible discipline (best-practice caution):** keep the bible *functional, not
comprehensive.* Track only what will actually be referenced; document
immediately after each chapter/book while fresh; resist over-building elaborate
lore before Book 1 reveals what actually matters. The same discipline applies
doubly to `canon-core.md` — it is always loaded, so every line in it is a tax on
every chapter. Keep it small on purpose.

---

## 3. The Module Layers

**Engine (fixed, Claude-Code-native):** the sub-agent role conventions, the
slash-command pipeline, the gate logic expressed in command instructions, and the
memory/ledger read-write discipline. Plus the thin `/scripts` layer for
deterministic checks.

**Config modules (swappable):** Genre Pack · Voice Pack · Setting Pack ·
Review Rubrics · Beta-Reader Personas · Line-Edit · Copy-Edit · Length Profile ·
Run-Config · Format-Proof `[POST-MVP1]`.

Genre swap = repoint commands at different Genre + Voice + Rubric + Setting +
Persona files. Same engine.

---

## 4. The Repository as Series Memory

Claude Code's strength is reading/writing a structured, version-controlled
filesystem. Series memory lives in Git-tracked files, not a drifting chat
context. This is the single most important defense against the #1 killer of
AI-written series: continuity drift across many books.

### 4.1 Sectioned, addressable continuity ledger

The continuity ledger is **a directory, not a single file** — `/series/continuity/`
split into `/characters/<id>.md`, `/locations/<id>.md`, `/threads/<id>.md`, plus
the always-loaded `canon-core.md`. Directory form makes "load these sections" a
literal file-glob, which is exactly what a slash-command does well.

Each entry file carries a small header:

```yaml
---
id: margaret
type: character        # character | location | thread
links: [the-inheritance, lighthouse]   # other entry ids this one depends on
---
```

The `links` field is the mechanism that catches buried cross-book constraints —
loading "Margaret" also pulls "the-inheritance" and "lighthouse" even when this
chapter's brief never names them.

Each **character** entry additionally carries a **knowledge-state**: what that
person knows at this point in the timeline. This prevents characters acting on
information they shouldn't yet have.

**Two character locations, deliberately split by mutability.**
`/series/characters/<id>.md` holds the *static* character design — voice
fingerprint, arc intentions, secrets — authored by the showrunner and rarely
touched. `/series/continuity/characters/<id>.md` holds the *mutable* record —
knowledge-state and canonical facts as established in the text — written only by
the post-gate ledger-updater (§4.3). The static file is design intent; the
continuity file is what has actually become true on the page. The slice loader
(§4.2) addresses the continuity file; the static file is loaded as part of the
relevant pack when a character is in play.

### 4.2 The per-chapter load set (the "relevant slice")

Relevance is resolved automatically, not by human memory. The load set is:

```
load_set = canon-core.md
         + brief-derived sections   (entries named in the chapter brief)
         + one-hop links            (entries those entries link to)
```

- **`canon-core.md`** (always loaded): protagonist's fixed facts, current
  timeline position, the active book's whodunit constraints, the fluency-stage
  setting. Deliberately bounded.
- **Brief-derived sections**: the context-assembly step in `draft-chapter` reads
  the chapter brief, extracts the cast / locations / named threads, and maps them
  to entry files.
- **One-hop links**: each loaded entry's `links` pull their targets in too. One
  hop is the chosen depth — two hops reintroduces context bloat. If a class of
  drift escapes one-hop, the fix is to add the missing fact to `canon-core`, not
  to increase hop depth.

**Brief-quality gate (the detail that makes the loader deterministic).** The Plan
step's rubric requires the brief to name entities **canonically, by ledger `id`**,
never descriptively ("the woman from the bakery" is a fault; `margaret` is
correct). A descriptive reference the loader can't resolve is a brief-quality
violation flagged at the Plan gate — cheap to check, and it's what keeps
brief→section mapping reliable.

### 4.3 Read/write symmetry

The slice loader and the ledger-updater (§5, finalize) use the **same addressing,
in both directions**. Context-assembly *reads* `canon-core` + brief-derived +
one-hop. The updater *writes back* only to that same loaded set (plus
knowledge-state for present characters). The updater cannot mutate sections this
chapter never touched — bounding write-scope to the read-scope is what prevents
uncontrolled mutation.

The **whodunit-ledger** tracks clue planting and the alibi grid so fairness is
auditable (authored by `/plan-mystery`, §5a). The **style-sheet** accumulates
every concrete spelling/hyphenation/capitalization decision actually made, so
Book 9 punctuates the way Book 1 did.

---

## 5. The Production Pipeline

Chapter-by-chapter first (to iron out bugs), then commands loop to produce full
books, surfacing only gate failures and conflicts to the human (the showrunner).

Two review populations run in order:
- **Inspectors** — answer *"is this correct?"* They **block the gate.**
- **Beta readers** — answer *"what is this like to read?"* They run only after
  inspectors pass, receive text and nothing else, return reaction reports, and
  **do not block.**

### 5a. Per-book pre-flight: `/plan-mystery N`

Run **once per book, before any `/draft-chapter`**. This applies the independence
principle to the mystery itself by separating three roles:

1. **Showrunner sets the irreducible core** — who did it, why, the central
   deception, and any series-arc constraints (this culprit ties to Book 9; this
   victim advances the personal thread). The taste-and-strategy layer; small, and
   irreducibly human.
2. **The `mystery-planner` sub-agent proposes the construction** — given the
   core, it drafts the clue schedule, the red herrings (mislead-but-don't-cheat),
   and the alibi grid. This is the heavy combinatorial craft work where the agent
   earns its keep.
3. **Showrunner approves/edits and locks** — the ledger is reviewed, adjusted,
   and frozen.

On approval, `/plan-mystery` writes `/series/whodunit-ledger.md` (the trackable
clue/red-herring/alibi data, **structured per chapter** so each chapter's
planting obligations can be handed out without revealing the answer) and
`/output/book-NN/mystery-solution.md` (the sealed answer key), then sets
`.penny/locks/book-NN.mystery.lock`.

- `/draft-chapter` **hard-fails** if the book's whodunit-ledger is absent,
  unpopulated, or unlocked — a deterministic file-presence + lock check in
  `preflight.py`, not an LLM judgment, so it survives Option A's soft-gate weakness.
- The drafter consumes the ledger and the solution is **sealed from it**: the
  drafter receives **only this chapter's clue-planting obligations**, never the
  full `mystery-solution.md`. It drafts toward planting clues naturally rather
  than writing backward from the answer.
- **Re-planning is deliberate**: if mid-book the mystery must change, re-run
  `/plan-mystery`, which re-locks and flags affected chapters for recheck.
  Drafting never silently mutates the solution.

This front-loads one human session per book. That's correct: mystery design is
the highest-leverage taste decision in the book and the cheapest place to spend
human attention for the largest quality return.

### Per-chapter flow

```
Context Assembly  (load canon-core + brief-derived + one-hop slice; §4.2)
  → Plan          (chapter brief: beats, POV, clue/red-herring planted,
                   emotional turn, hook-out — reviewed BEFORE prose;
                   brief-quality gate: entities named by ledger id, §4.2)
  → Draft         (write against brief + Voice Pack + Setting Pack +
                   THIS chapter's clue-planting obligations only; §5a)
  → [Self-Audit]  [P1] drafter fix-pass against a bounded checklist;
                   emits a revised draft only, no verdict (§5b).
                   MVP 1 runs Draft → Gate directly.
  → DEVELOPMENTAL GATE — inspectors, blocking (§6, §8)
  → LINE-EDIT pass        (prose rhythm, word choice, voice at sentence level)
  → COPY-EDIT pass        (fresh-context agent + style sheet; grammar/consistency)
  → BETA READERS          (reaction reports, non-blocking) → revision-priority report → showrunner
  → FINALIZE              (ledger-updater runs post-gate; writes ch-NN.ledger-diff.md;
                           commits on ledger_approval: auto, pauses on review; §4.3, §12)
  → promote ch-NN.final.md
```

Each command writes the current stage to `.penny/current-stage` as it runs, so the
TUI status bar reflects live pipeline position (§11).

### 5b. Self-audit — `[P1]`, fix-pass not verdict

The self-audit is a **cost optimization, not a gate**, so it is P1, not P0: MVP 1
is viable without it because the independent inspectors catch everything it would.
It is built as **revision, never judgment** — the drafter is asked to *find and
fix* specific high-frequency mechanical issues against a checklist (repeated
sentence openers, named-emotion telling, banned-phrase hits, obvious
clue-planting gaps), **not** to rate its own compliance (which would invite a
defensive "no violations" verdict).

Constraints carried in the requirement so it's built safely:
- Produces a **revised draft only**; emits **no self-assessment**.
- Inspectors receive **no signal** that a self-audit occurred — they get text,
  one rubric, the ledger slice, blind as always. The drafter never influences the
  gate; the independence principle is preserved.

### Per-book flow (after chapters finalized)

```
Assemble chapters
  → STANDALONE-vs-ARC CHECK  (does this book satisfy alone — mystery solved —
                              while leaving the right personal thread open to
                              drive the next purchase?)
  → PRE-FLIGHT (preflight.py): assert final_read_model != drafting_model, and
                              drafted_by stamps in chapters != model about to
                              do the final read; hard-fail otherwise (§7)
  → FINAL HOLISTIC READ      (ROUTING RULE: runs on a DIFFERENT model than
                              drafted it — absorbs "drawer time," see §7)
  → book-NN.manuscript.md    ← MVP 1 ENDPOINT: finished, reviewed manuscript
  → COMPILE TO EPUB          [POST-MVP1]
  → EPUB PROOF AGENT         [POST-MVP1] deterministic validation + rendered read
  → ship-ready               [POST-MVP1]
```

### Descending-funnel rationale

Mirrors professional practice: big-picture first, word-level last
(developmental → line → copy → final read). Structural problems are cheap to fix
early and expensive late, so gates are front-loaded.

---

## 6. Independent Quality Reviews

"Independent" means genuinely isolated: a reviewer never wrote what it judges,
gets only what it needs, and cannot see other reviewers' verdicts. In Option A
this isolation is provided **structurally** by Claude Code sub-agent boundaries —
a sub-agent does not inherit the drafter's context.

**Tier 1 — Blind same-model reviewers.** Fresh Claude Code sub-agents, no
draft-history. Each gets the chapter + ONE rubric + the relevant ledger slice.
One reviewer per failure mode, so no single reviewer rationalizes across
categories.

**Tier 2 — Cross-model reviewers.** External agents (Codex, Hermes, OpenClaw,
etc.) invoked via the `/scripts` layer (shell-out to their APIs) conforming to a
fixed contract. Heterogeneous models have different blind spots; disagreement is
signal.

```
review contract
  input:  { text, rubric, ledger_slice }
  output: { score 1-5, violations[], blocking_issues[], evidence[], reviewed_by }
```

`reviewed_by` records which model produced the verdict — provenance that rides
along on an artifact already being written, and that feeds cross-model
convergence analysis (P1.2). Adding a model = one adapter call, not an engine change.

**Tier 3 — Deterministic specialist checkers (`/scripts`, not vibes):**
- **Fair-play checker** — every clue needed to solve the murder appeared before
  the reveal; culprit introduced early enough. Cross-refs whodunit-ledger.
- **Continuity checker** — chapter vs. the continuity ledger; flags contradictions.
- **Alibi/timeline checker** — validates the alibi grid is internally consistent.
- **Voice-drift checker** — sentence-length variance, lexical repetition, tic
  frequency vs. the Voice Pack baseline.

### Conflict resolution — two signals, two responses

Reviewers do not vote into a mushy average. The system distinguishes
disagreement about **kind** from disagreement about **degree**:

- **Blocking/non-blocking split = disagreement about *kind* → HARD escalate.**
  If one reviewer marks a violation blocking and another does not, they disagree
  on the one variable that controls the gate. The gate **holds** and the case
  escalates to the showrunner immediately. (`escalate_on_blocking_disagreement: true`.)
- **Score spread within a dimension = disagreement about *degree* → SOFT log.**
  If reviewers scoring the *same rubric dimension* differ by
  `score_spread_log_threshold` (default 2 on the 1–5 scale) or more, the chapter
  is contentious — noted in the revision-priority report, but it does **not** hold
  the gate (neither reviewer said it should).

Two definitional guards:
- **Same-dimension only.** Score spread is meaningful only *within* a rubric
  dimension. Inspector-voice rating voice 2 and inspector-structure rating
  structure 4 is not a disagreement — different things.
- **Couples to `panel_size`.** With `panel_size: 1` (one same-model inspector per
  failure mode) there's usually one score per dimension, so the spread check
  mostly sleeps and the blocking-disagreement check does the work. With
  `panel_size: 3` or cross-model panels, the spread signal wakes up and becomes
  useful. The default `2` is a **seed tunable during Book 1**, not a load-bearing
  constant — calibrate once real verdict distributions are visible.

(In Option A these rules live in the `review-chapter` command instructions plus
the deterministic comparisons in `preflight.py`; see the known-limitation note
in §12.)

---

## 7. Line-Edit, Copy-Edit, Cross-Model "Drawer Time", and Model Routing

Professional editing treats these as distinct descending passes, not one review.

- **Line-edit module** — refines prose: rhythm, word choice, flow, cutting flab,
  strengthening verbs — while preserving voice. Runs after the developmental gate.
- **Copy-edit module** — grammar, punctuation, consistency. Run by a
  **fresh-context sub-agent** given only the text and the **style sheet** (never
  the drafting history), matching the industry practice of handing the copyedit
  to someone new. Updates the style sheet with any new decisions.
- **Style sheet** — distinct from the Voice Pack. The Voice Pack says *how to
  write*; the style sheet records *what was decided*. Accumulates across all 13
  books.

### Cross-model "drawer time" as a validated invariant

Human drawer time works by letting the writer return as a *different reader*
whose normalization has faded. A different model is structurally a different
reader — it never normalized the prose because it never wrote it, and never knew
the *intended* version, so it reads what is on the page. Implemented as a
**routing rule**: the final holistic pre-assembly read MUST run on a different
model than did the drafting.

**This is enforced by config assertion, not honor system** — "did a different
model read it" is mechanically checkable, so it shouldn't be left to a checklist.

`/config/run-config.md` declares **model-per-role**:

```yaml
drafting_model:   claude-opus
inspector_model:  claude-opus
copyedit_model:   claude-opus
final_read_model: codex            # MUST differ from drafting_model
beta_models:      [codex, hermes, openclaw]
```

The invariant is **difference, not identity** — encoded as `!=`, not `==`. The
final reader must be a *different model than the drafter*, not *specifically*
Codex. This keeps the independence guarantee while letting you substitute
whatever alternate model is reachable on a given day — important because
cross-model access is rate-limited / intermittent (an open engineering question
in the PRD). A config that hard-required one specific model would block the whole
book whenever that model was down.

**Two-part pre-flight in `assemble-book` (`preflight.py`):**
1. **Config invariant:** `final_read_model != drafting_model` — hard-fail.
   Catches misconfiguration. Deterministic string comparison, immune to Option A's
   soft-gate weakness.
2. **Reality check:** the `drafted_by` stamps in the actual chapter files must
   differ from the model about to perform the final read. Catches config-vs-reality
   drift (you swapped models mid-book and the config now lies).

**Provenance stamps ride along — no new write step.** Each role records its model
in the artifact it already produces: `drafted_by` in chapter frontmatter,
`reviewed_by` in verdicts (§6), `read_by` in the final read's output. Provenance
lives *in the artifact it describes*, so it can't fall out of sync the way a
separate metadata file would — and `reviewed_by` is independently useful for
P1.2 convergence analysis.

---

## 8. Compensating for AI Creative-Writing Failure Modes

Each is a rubric module (one swappable file) with an authoring instruction and an
independent review check.

| Failure mode | Authoring mechanism | Independent check |
|---|---|---|
| Continuity drift across series | Ledgers read pre-write, updated post-gate | Continuity checker diffs canon |
| Sagging middle | Outline enforces midpoint reversal + escalation beats | Structure reviewer scores tension curve |
| Repetitive sentence rhythm | Voice Pack mandates length variance, bans opener repetition | Voice-drift checker (statistical) |
| Telling not showing | Brief specifies dramatized vs. summarized | Reviewer flags emotion-naming / exposition dumps |
| Conflict resolved too easily | Brief requires cost/complication per resolution | Reviewer checks stakes weren't deflated |
| Flat character voice | Per-character speech fingerprint in character files | Reviewer "voice blind test" — ID speaker with tags removed |
| Cliché / purple prose | Voice Pack banned-phrase list (grows over series) | Cliché-density checker against list |
| Lack of subtext | Brief requires a scene where said ≠ meant | Reviewer flags on-the-nose dialogue |
| Unfair mystery | Clue planting tracked in whodunit-ledger (§5a) | Fair-play checker (Tier 3) |
| Series fatigue / repetitive plotting | Arc-ledger ensures each book differs | Cross-book reviewer compares to prior books |

The banned-phrase list and voice baselines **accumulate across the 13 books**, so
Penny gets progressively better at avoiding its *own* tics — a deliberate
compounding feature, and the source of the name.

**Coverage limitation (continuity-of-omission).** The post-gate ledger-updater
(§4.3) is a *fidelity* mechanism — it records what's on the page. It cannot catch
a fact that *should* have changed but the chapter forgot to establish (a thread
that quietly dies). That's a *coverage* problem, caught by the structure
inspector / cross-book reviewer ("thread X opened in ch 3, never advanced"), not
by the updater. Don't over-trust the updater as a completeness guarantee.

---

## 9. Current Config Snapshot — Cozy Mystery / Coastal Victoria AU

**Genre Pack (cozy-mystery):** amateur sleuth; no graphic violence/sex; small
contained community; justice restored; comfort + puzzle balance. **Dual engine:**
A-plot = the book's mystery; B-plot = the protagonist's post-divorce sea-change,
threaded across all 13 via the arc-ledger. **Series spine:** her transformation
is the real long game; each murder is the vehicle. Per-book rule: mystery
*resolves* + a personal thread *doesn't* (drives the next purchase). Chapter-end
hooks mandatory.

**Setting Pack (coastal Victoria, Australia):** real region, **invented town**
(a `fictionalization-map.md` firewalls real-derived texture from invented
names/businesses/people — authentic and legally clean). Southern Ocean, not
tropical — cool/changeable weather, southerly busters, kelp + salt + eucalypt,
hard southern light, wind as a constant. Core stance: the town is **ordinary to
locals, strange to the protagonist** — never travel-brochure framing.

**Newcomer fluency dial (a structural spine, enforced per book):**
- Books 1–2 (Outsider): narration standard English; she mishears/over-formalizes;
  slang lives in other characters' mouths.
- Books 3–6 (Settling): awkward code-switching; charming misuse; local rhythm
  creeping into observation.
- Books 7–13 (Belonging): local idiom leaks into her *narration* — the signal she
  belongs. The town has become ordinary to her.

Her ignorance doubles as the reader's onboarding: because *she* needs terms
explained, the reader learns the world without clumsy exposition.

**Lexicon schema (fixed; contents swap per location):**
`term | gloss | register | speaker_type | freq_cap | narration_ok_from_stage | notes`
The `narration_ok_from_stage` field couples each term to the fluency dial — a
`BELONGING`-tagged term in Book 2 narration is an automatic reviewer flag.

> **Accuracy note:** lexicon seeds are from general knowledge of Australian usage.
> Before locking for a 13-book run, a `research-notes.md` pass should verify
> regional specifics (coastal-Victorian surf-town idiom and intensely local AFL
> club loyalties differ from Sydney/Queensland). Research stays in config.

---

## 10. Beta-Reader Module

A separate review population from the inspectors. Inspectors check rules; beta
readers report experience. Keeping them apart protects independence — a reader who
knows the rules starts inspecting instead of reacting.

- **Personas are config** `[STUB]`, loaded by filename. Add/remove/rewrite =
  edit `/config/beta-readers/personas/` only.
- They run **after** inspectors pass, receive the text and **nothing else**
  (no ledgers, no outline, no solution) — the same blindness a real reader has.
- **Cross-model capable** via the `/scripts` adapter layer; convergence across
  models is strong signal.

```
beta contract
  input:  { text, persona_file }     (no ledgers, no solution, no rules)
  output: { engagement_curve, put_down_points, whodunit_guess + chapter,
            confusion_points, emotional_beats, would_buy_next: yes/no, notes }
```

Reaction reports feed a **revision-priority report**: consensus put-down points
and "would not buy next" escalate to the showrunner; scattered single-reader
gripes are logged. Beta output never blocks the gate — a boring chapter is a
quality signal, not a correctness failure.

`beta-protocol.md` (exact report format) is `[STUB]` pending persona definition —
the highest-leverage open decision, deferred to Phase 5.

---

## 11. TUI Status Bar

Penny surfaces live pipeline position in the Claude Code status line, turning the
status bar into a harness dashboard. Because Option A keeps all state in files,
the status script can read **harness state**, not just session state.

**Mechanism.** Claude Code pipes session JSON to one configured command on each
tick (≤ every 300ms); only the first line of stdout becomes the status line.
Config in `.claude/settings.json`:

```json
{ "statusLine": { "type": "command",
                  "command": "scripts/penny-statusline.sh", "padding": 0 } }
```

**State marker.** Each pipeline command writes one line to `.penny/current-stage`
as it runs (e.g. `book=03 chapter=07 stage=COPY-EDIT`). `scripts/penny-statusline.sh`
reads that file for harness state, derives chapter progress from `/output`
(`.final.md` count), counts blocking verdicts in `ch-NN.reviews/` for gate state,
and pulls `context_window.used_percentage` from the piped JSON. Example render:

```
Penny · Book 03 · Ch 7/24 · COPY-EDIT · gate: 2 blocking · ctx 41%
```

**Notes / gotchas.** Script needs `jq` (fails silently without it) and the execute
bit (`chmod +x`); workspace trust must be accepted or the line is skipped; consume
stdin once (capture to a variable) if also piping to another consumer.

**ccstatusline composition `[DECISION — resolved for MVP 1]`.** The generic half
(model, git, cost, context bar) *could* be delegated to the `ccstatusline` CLI via
a wrapper. **MVP 1 default: single bash script, no ccstatusline** — fewer moving
parts. Revisit only if the richer git/cost widgets are wanted later.

---

## 12. Run-Mode Flags & Known Option-A Limitations

All run-mode settings live in `/config/run-config.md` alongside the model-per-role
block (§7). Flags:

```yaml
# cadence / panel
cadence:      chapter | book-milestone   # chapter-level early, book-level once stable
panel_size:   1 | 3                       # 1 fast (chapter); 3 consensus (book-level)
gate_mode:    strict | fast               # strict for flagship; fast once validated
escalation_scope: minor-auto | log-all    # auto-resolve minor x-model gaps vs. batch

# ledger updates (§4.3)
ledger_approval: auto | review            # review early (Book 1, tuning); auto once clean

# escalation thresholds (§6)
escalate_on_blocking_disagreement: true   # HARD — holds gate, escalates now
score_spread_log_threshold: 2             # SOFT — logged only; tunable during Book 1
                                          # spread = max(scores) − min(scores), same dimension
```

Recommended defaults: chapter-level cadence + `panel_size: 1` + strict gate +
`ledger_approval: review` early; move to book-milestone + `panel_size: 3` +
fast-where-validated + `ledger_approval: auto` once inspectors and the updater
prove reliable. The **showrunner-touch ratio** success metric should show this
transition happening on purpose, not by hope.

**Known Option-A limitations (accepted for MVP 1, motivate later Option-C migration):**
- Gate logic is an *instruction Claude Code follows*, not strictly deterministic
  code; usually complied with, occasionally rationalized. Mitigate by pushing the
  hardest checks into `/scripts` (fair-play, voice-drift, and the §5a/§7 pre-flight
  assertions) where they ARE deterministic.
- Cross-model routing is shell-out from commands, not first-class dispatch.
- Long unattended runs accumulate small deviations; favor human-in-the-loop
  chapter-by-chapter until the pipeline is stable.
- Metrics are written to report files by command instruction, not emitted by code.

---

## 13. Build Order

1. **Skeleton** — repo, `.claude/` agents+commands scaffold, sectioned continuity
   ledger + `canon-core`, style sheet, `run-config.md`, one Genre/Voice/Setting
   Pack, status bar. Manual single-chapter runs.
2. **Review Bus** — Tier-1 blind sub-agents + Tier-3 `/scripts` checkers; tune
   rubrics on real drafts; wire the two-signal conflict resolution (§6).
3. **Mystery + Cross-model** — `/plan-mystery` + lock pre-flight; `/scripts`
   adapters; `preflight.py` model-routing assertions + provenance stamps.
4. **Prose passes** — line-edit + copy-edit; the post-gate ledger-updater +
   `ledger_approval`; begin accumulating the style sheet. *(Self-audit `[P1]` is a
   fast-follow here.)*
5. **Beta layer** — define personas + protocol; reaction reports.
6. **Book loop** — commands run chapter-by-chapter across an outline; book-level
   showrunner approval; standalone-vs-arc check. **← MVP 1 endpoint: finished,
   cross-model-reviewed manuscript.**
7. **`[POST-MVP1]` Format + ship** — EPUB compile + EPUB proof agent.
8. **Series scale** — arc-ledger across all 13 with cross-book reviewers.

---

## 14. Open Items Awaiting the Showrunner

- `[STUB]` Beta-reader persona definitions and `beta-protocol.md` report format —
  the only fully stubbed module, and the highest-leverage open decision (it's what
  converts "technically correct" into "Kindle readers buy book 2"). Deferred to
  Phase 5.
- `[TODO]` `research-notes.md` accuracy pass on coastal-Victorian lexicon and AFL
  loyalties before locking the Setting Pack. *(Non-blocking for the engine.)*
- `[DATA]` Metric instrumentation — what writes the gate/defect/loop counts and
  where. *(Non-blocking; needed before metrics are trustworthy. Option-A caveat:
  metrics are command-written, not code-emitted.)*
- `[ENGINEERING]` Cross-model adapter access — confirm API access + uniform
  contract for the alternate models. *(Blocking for P1.2; P0 cross-model final
  read needs ≥1 reachable alternate model.)*
- `[POST-MVP1]` Format-proof module: `epub-proof.md` contents and `output-targets`
  spec for the intended store (KDP assumed).

---

## Change log — v2 → v3

Seven design gaps surfaced in review, all resolved by applying the independence
principle plus deterministic `/scripts` enforcement:

1. **Ledger slice (§4)** — sectioned `/series/continuity/` directory + `canon-core`
   always-load + brief-derived sections + one-hop links; brief-quality gate
   requires canonical ledger ids.
2. **Cross-model routing (§7)** — `run-config.md` model-per-role; `!=` invariant
   asserted in `preflight.py`; provenance stamps (`drafted_by`/`reviewed_by`/
   `read_by`) ride along on existing artifacts; reality check vs. config.
3. **Whodunit authorship (§5a)** — new `/plan-mystery N`: showrunner core →
   `mystery-planner` proposes → approve → lock. Drafter consumes, never writes.
4. **Solution isolation (§5a)** — per-chapter clue obligations handed to the
   drafter; full `mystery-solution.md` sealed from drafter + beta + final readers.
5. **Disagreement thresholds (§6)** — blocking-split = hard escalate (holds gate);
   same-dimension score spread ≥2 = soft log. Values tunable in Book 1.
6. **Self-audit (§5b)** — reclassified `[P1]`; built as a fix-pass that emits no
   verdict; inspectors stay blind to it. Diagram annotated.
7. **Knowledge-state updates (§4.3, §5)** — dedicated `ledger-updater` at
   `finalize` (post-gate), write-scope bounded to the loaded slice,
   `ledger_approval: auto | review` flag.
