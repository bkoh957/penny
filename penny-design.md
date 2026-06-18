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

> **Status legend:** `[STABLE]` defined and ready · `[STUB]` slot defined,
> contents to be filled later · `[POST-MVP1]` deferred past the first milestone ·
> `[DECISION]` open choice flagged for the human.

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

---

## 2. Repository Layout

```
.claude/                      Claude-Code-native runtime (Option A)
  /agents                       sub-agent role definitions (blind, fresh context)
    drafter.md
    inspector-continuity.md
    inspector-fairplay.md
    inspector-alibi.md
    inspector-voice.md
    inspector-structure.md
    inspector-location.md
    line-editor.md
    copy-editor.md
    beta-reader.md              loads a persona
    final-reader.md             cross-model holistic read
  /commands                     the pipeline as slash-commands
    draft-chapter.md
    review-chapter.md
    edit-chapter.md
    finalize-chapter.md
    assemble-book.md
  settings.json                 statusLine config (see §11)

/scripts                      [STABLE] thin deterministic layer
  voice_drift.py                sentence-variance / repetition / tic stats
  fairplay_check.py             clue-planting cross-reference vs. whodunit-ledger
  penny-statusline.sh           TUI status bar reader (see §11)
  (epubcheck wrapper)           [POST-MVP1]

/config                       all swappable modules
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
  /characters                   one file per character: voice, arc, secrets,
                                knowledge-state
  /world                        setting facts, the town, recurring locations
  continuity-ledger.md          canonical facts (eye colour, timeline, who knows what)
  whodunit-ledger.md            per-book: culprit, clues, red herrings, alibi grid
  style-sheet.md                accumulating record of spelling/punctuation decisions

/output
  /book-NN
    outline.md
    /chapters
      ch-NN.draft.md
      ch-NN.reviews/            verdicts from inspectors land here
      ch-NN.final.md
    mystery-solution.md         sealed; not given to beta/final readers
    book-NN.manuscript.md       assembled, cross-model-reviewed (MVP 1 endpoint)
    book-NN.epub                [POST-MVP1]
    /reports                    beta reaction reports, revision-priority report

.penny/                       runtime state for the TUI status bar (see §11)
  current-stage                 single-line marker the commands write as they run
```

**Bible discipline (best-practice caution):** keep the bible *functional, not
comprehensive.* Track only what will actually be referenced; document
immediately after each chapter/book while fresh; resist over-building elaborate
lore before Book 1 reveals what actually matters.

---

## 3. The Module Layers

**Engine (fixed, Claude-Code-native):** the sub-agent role conventions, the
slash-command pipeline, the gate logic expressed in command instructions, and the
memory/ledger read-write discipline. Plus the thin `/scripts` layer for
deterministic checks.

**Config modules (swappable):** Genre Pack · Voice Pack · Setting Pack ·
Review Rubrics · Beta-Reader Personas · Line-Edit · Copy-Edit · Length Profile ·
Format-Proof `[POST-MVP1]`.

Genre swap = repoint commands at different Genre + Voice + Rubric + Setting +
Persona files. Same engine.

---

## 4. The Repository as Series Memory

Claude Code's strength is reading/writing a structured, version-controlled
filesystem. Series memory lives in Git-tracked files, not a drifting chat
context.

- Ledgers are **read before every chapter** (relevant slice only, to avoid
  context bloat and drift) and **updated after every chapter.**
- Each character file carries a **knowledge-state**: what that person knows at
  this point in the timeline. Prevents characters acting on information they
  shouldn't yet have.
- The **whodunit-ledger** tracks clue planting and the alibi grid so fairness is
  auditable.
- The **style-sheet** accumulates every concrete spelling/hyphenation/
  capitalization decision actually made, so Book 9 punctuates the way Book 1 did.

This is the single most important defense against the #1 killer of AI-written
series: continuity drift across many books.

---

## 5. The Production Pipeline

Chapter-by-chapter first (to iron out bugs), then commands loop to produce full
books, surfacing only gate failures and conflicts to the human (the showrunner).

Two review populations run in order:
- **Inspectors** — answer *"is this correct?"* They **block the gate.**
- **Beta readers** — answer *"what is this like to read?"* They run only after
  inspectors pass, receive text and nothing else, return reaction reports, and
  **do not block.**

### Per-chapter flow

```
Context Assembly  (load relevant ledger slice + outline + packs)
  → Plan          (chapter brief: beats, POV, clue/red-herring planted,
                   emotional turn, hook-out — reviewed BEFORE prose)
  → Draft         (write against brief + Voice Pack + Setting Pack)
  → Self-Audit    (same agent flags its own rubric violations)
  → DEVELOPMENTAL GATE — inspectors, blocking (§6, §8)
  → LINE-EDIT pass        (prose rhythm, word choice, voice at sentence level)
  → COPY-EDIT pass        (fresh-context agent + style sheet; grammar/consistency)
  → BETA READERS          (reaction reports, non-blocking) → revision-priority report → showrunner
  → Ledger + style-sheet update
  → promote ch-NN.final.md
```

Each command writes the current stage to `.penny/current-stage` as it runs, so the
TUI status bar reflects live pipeline position (§11).

### Per-book flow (after chapters finalized)

```
Assemble chapters
  → STANDALONE-vs-ARC CHECK  (does this book satisfy alone — mystery solved —
                              while leaving the right personal thread open to
                              drive the next purchase?)
  → FINAL HOLISTIC READ      (ROUTING RULE: must run on a DIFFERENT model than
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
  output: { score 1-5, violations[], blocking_issues[], evidence[] }
```

Adding a model = one adapter call, not an engine change.

**Tier 3 — Deterministic specialist checkers (`/scripts`, not vibes):**
- **Fair-play checker** — every clue needed to solve the murder appeared before
  the reveal; culprit introduced early enough. Cross-refs whodunit-ledger.
- **Continuity checker** — chapter vs. continuity-ledger; flags contradictions.
- **Alibi/timeline checker** — validates the alibi grid is internally consistent.
- **Voice-drift checker** — sentence-length variance, lexical repetition, tic
  frequency vs. the Voice Pack baseline.

**Conflict resolution:** reviewers do not vote into a mushy average. Any
*blocking* issue from any reviewer holds the gate. Score disagreements above a
threshold escalate to the showrunner. (In Option A this rule lives in the
`review-chapter` command instructions; see the known-limitation note in §12.)

---

## 7. Line-Edit, Copy-Edit, and the Cross-Model "Drawer Time" Rule

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

**Cross-model replaces drawer time.** Human drawer time works by letting the
writer return as a *different reader* whose normalization has faded. A different
model is structurally a different reader — it never normalized the prose because
it never wrote it, and never knew the *intended* version, so it reads what is on
the page. Implemented as a **routing rule**: the final holistic pre-assembly read
MUST run on a different model than did the drafting.

---

## 8. Compensating for AI Creative-Writing Failure Modes

Each is a rubric module (one swappable file) with an authoring instruction and an
independent review check.

| Failure mode | Authoring mechanism | Independent check |
|---|---|---|
| Continuity drift across series | Ledgers read pre-write, updated post-write | Continuity checker diffs canon |
| Sagging middle | Outline enforces midpoint reversal + escalation beats | Structure reviewer scores tension curve |
| Repetitive sentence rhythm | Voice Pack mandates length variance, bans opener repetition | Voice-drift checker (statistical) |
| Telling not showing | Brief specifies dramatized vs. summarized | Reviewer flags emotion-naming / exposition dumps |
| Conflict resolved too easily | Brief requires cost/complication per resolution | Reviewer checks stakes weren't deflated |
| Flat character voice | Per-character speech fingerprint in character files | Reviewer "voice blind test" — ID speaker with tags removed |
| Cliché / purple prose | Voice Pack banned-phrase list (grows over series) | Cliché-density checker against list |
| Lack of subtext | Brief requires a scene where said ≠ meant | Reviewer flags on-the-nose dialogue |
| Unfair mystery | Clue planting tracked in whodunit-ledger | Fair-play checker (Tier 3) |
| Series fatigue / repetitive plotting | Arc-ledger ensures each book differs | Cross-book reviewer compares to prior books |

The banned-phrase list and voice baselines **accumulate across the 13 books**, so
Penny gets progressively better at avoiding its *own* tics — a deliberate
compounding feature, and the source of the name.

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

`beta-protocol.md` (exact report format) is `[STUB]` pending persona definition.

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

**Optional ccstatusline composition** `[DECISION]`. The generic half (model, git,
cost, context bar) can be delegated to the `ccstatusline` CLI by making
`penny-statusline.sh` a wrapper that runs ccstatusline and concatenates its output
after the Penny harness fields. Recommended only if the richer git/cost widgets
are wanted; otherwise the single bash script (harness fields + context % from JSON)
is fewer moving parts. Default for MVP 1: **single script, no ccstatusline.**

---

## 12. Run-Mode Flags & Known Option-A Limitations

**Run-mode flags** (command-level settings, not code):
- **Cadence** `[DECISION]` — chapter-level (tuning) vs. book-milestone (production).
  Recommended: chapter-level early, book-level once inspectors are reliable.
- **Panel size per persona** `[DECISION]` — 1 (fast) vs. 3 (consensus).
  Recommended: 3 on book-level passes, 1 on chapter passes.
- **Gate strictness** `[DECISION]` — strict-blocking vs. fast-mode once proven.
  Recommended: strict for flagship books, fast once validated.
- **Escalation scope** `[DECISION]` — auto-resolve minor cross-model disagreements
  and escalate major ones, vs. log everything for batch review.

**Known Option-A limitations (accepted for MVP 1, motivate later Option-C migration):**
- Gate logic is an *instruction Claude Code follows*, not strictly deterministic
  code; usually complied with, occasionally rationalized. Mitigate by pushing the
  hardest checks into `/scripts` (fair-play, voice-drift) where they ARE deterministic.
- Cross-model routing is shell-out from commands, not first-class dispatch.
- Long unattended runs accumulate small deviations; favor human-in-the-loop
  chapter-by-chapter until the pipeline is stable.
- Metrics are written to report files by command instruction, not emitted by code.

---

## 13. Build Order

1. **Skeleton** — repo, `.claude/` agents+commands scaffold, ledgers, style sheet,
   one Genre/Voice/Setting Pack, status bar. Manual single-chapter runs.
2. **Review Bus** — Tier-1 blind sub-agents + Tier-3 `/scripts` checkers; tune
   rubrics on real drafts.
3. **Cross-model** — `/scripts` adapters; wire the cross-model final-read rule.
4. **Prose passes** — line-edit + copy-edit; begin accumulating the style sheet.
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
  converts "technically correct" into "Kindle readers buy book 2").
- `[DECISION]` Run-mode flags in §12, plus the ccstatusline composition choice (§11).
- `[TODO]` `research-notes.md` accuracy pass on coastal-Victorian lexicon and AFL
  loyalties before locking the Setting Pack.
- `[POST-MVP1]` Format-proof module: `epub-proof.md` contents and `output-targets`
  spec for the intended store (KDP assumed).
