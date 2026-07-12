# The Plotting Workshop — `/plot-book`, the wired outline, and `tension_check.py`

**Date:** 2026-07-12
**Status:** approved in conversation; this document is the record.
**Supersedes:** nothing — this is a new front door. It extends the outline-first pipeline
(design §5a) and reuses `/plan-mystery` (§5a) unchanged underneath.

## 1. The problem

Penny generates stories that fit the outline but not stories that are exciting to read.
The gate architecture can only block badness (continuity errors, unfair clues, voice
drift); nothing in the system *produces* or *demands* propulsion. The outline is the only
channel through which plot quality reaches the drafter, and today nothing generates a
dramatically compelling outline — the showrunner hand-builds it across chat transcripts,
and the engine checks only its file shape (`outline_check.py`) and its puzzle fairness
(`fairplay_check.py`). The drama itself — causality, open questions, escalation, hooks
that keep a reader turning pages — has no generator and no checker.

Naive one-pass LLM outlining fails structurally: generated left-to-right, each chapter is
conditioned on what came before and nothing on where the book must arrive, so the middle
drifts toward the genre's statistical mean and resolves tension at the first opportunity.
Every professional plotting method (ending-first, tentpole scenes, snowflake refinement)
is the same countermove: fix the destination and the big turns first, then fill the gaps
by interpolation. Penny already proves this works on the puzzle half — `mystery-planner`
plans the clue schedule backwards from a known solution. This project gives the drama the
same treatment.

## 2. Scope

**In scope (this spec):**

- **Part 1 — the wired chapter format** and its deterministic checker
  `scripts/tension_check.py`.
- **Part 2 — the plotting workshop**: the `/plot-book` command, its stage save-points,
  three new agents, the genre-pack beat sheet, and the blind outline beta read (the
  genre-fan persona).

**Out of scope (later projects, deliberately):**

- **Part 3 — the brief renderer** (outline→drafter-prompt compilation: intent above
  events, emphasis budget, negative space). Touches the drafting side, not planning.
- **Part 4 (full) — the adversarial predict-the-twist loop** (reader simulation
  predicting each turn before reading it; repair-span regeneration). The blind outline
  fan shipped here is the cheap slice of Part 4; the prediction loop needs its own
  tuning cycle.

## 3. Decisions already made (with the showrunner, 2026-07-12)

1. **Build Parts 1 + 2 together.** The workshop needs the format to write into; the
   format is dead data without a generator.
2. **Save points, not one long conversation.** Every stage writes a file; the files are
   the state; the conversation is never the record.
3. **The workshop absorbs mystery planning.** `/plot-book` calls the existing
   `mystery-planner` (and the existing lock machinery) at its natural moment. The ending
   chosen in the workshop is written down once; both the drama plan and the puzzle plan
   are built from it. `/plan-mystery` continues to work standalone.
4. **The showrunner's material enters at every stage** under the portaprompt's rules:
   lay out what exists (including rival versions), the showrunner chooses, never invent
   silently, never improve chosen material.
5. **Taste at the big three, machine below.** The showrunner chooses among rival
   premises, rival endings, and rival turning-point sets. Gap-filling and thread-weaving
   are machine work answerable to the checker; the showrunner reviews the finished
   outline as a whole (and can hand-edit anything — they are files).
6. **One resumable command** (`/plot-book NN`), not six commands, not one mega-agent.
7. **The lock gains the tension gate, and the showrunner can override.** Overrides are
   per-check, reasoned, and recorded inside the lock certificate — explicit, named, on
   the record. The proofreader's findings are always printed; a waiver never hides them.
8. **A blind outline beta reader** — a genre-fan persona, reading a reader's copy of the
   outline with no solution and no wiring — reports engagement, put-down risk, whodunit
   guess + chapter, and would-buy. Advisory, never blocking.

## 4. The planning folder (save points)

`input/book-NN/plot/` — under `input/` because everything in it is writer-editable.
Four files, one per decision, written in stage order:

| File | Stage | Owner of the choice | Contents |
|---|---|---|---|
| `material.md` | 0 (optional) | showrunner | Whatever the showrunner walks in with: a brainstorm transcript, a half premise, competing endings. May be absent. |
| `premise.md` | 1 | showrunner | The chosen dramatic engine: want, opposition, why she can't walk away, why the reader can't, the one-sentence pitch. Plus the rejected shortlist (raw material for later books). |
| `ending.md` | 2 | showrunner | Ending-first: who did it and why (= the mystery core), the worst moment (dark night), what the truth costs, what restored looks like. |
| `turning-points.md` | 3 | showrunner | The 6–9 tentpole scenes, each with: a beat id from the genre beat sheet (where applicable), a rough chapter position, and what breaks or reverses. `total_chapters` is decided here. |

`total_chapters` is decided in `turning-points.md` but its operative owner remains the
skeleton's frontmatter (as today, per `outline_check.py`): `chapter-weaver` initializes
the skeleton frontmatter from `turning-points.md` at stage 5, and the fingerprint
stamping catches any later divergence between the two.

Results (as opposed to decisions) do **not** live here: the killer's timeline, clue
schedule, and alibi grid land in `series/whodunit/book-NN.yaml` + the sealed
`output/book-NN/mystery-solution.md` (existing homes); chapters land in
`input/book-NN/outline-skeleton.md` (existing home); the fan's report lands in
`output/book-NN/reports/` (existing home).

### Staleness (fingerprints)

Every generated save point and the skeleton stamp, in frontmatter, the sha256 of each
upstream file it was built from (`built_from:` map — e.g. `turning-points.md` records the
shas of `premise.md` and `ending.md`). The same mechanism that binds a clear-dev cert to
a draft. A downstream file whose recorded shas no longer match is **stale**; the stage
detector reports it and `/plot-book` re-runs from the first stale stage. Hand-editing a
file is therefore a first-class act: edit `turning-points.md`, rerun, and everything
built on the old version is redone; nothing drifts silently.

## 5. The wired chapter format (Part 1)

Chapter blocks in `outline-skeleton.md` / `outline.md` keep everything they have today
(Summary, the five Chapter Structure fields, Track Movement) and gain wiring lines, in
the same bold-field style, parsed the same dependency-free way the deterministic layer
already parses outlines (never PyYAML — the dependency-split rule):

- `**Because:**` — which earlier chapter's turn forced this one, e.g.
  `**Because:** ch 06 — Faye's death turns the key theft from nuisance into evidence.`
  Chapter 1 writes `**Because:** opening`. The checker requires the referenced chapter
  to exist and precede this one.
- `**Opens:**` — question id(s) this chapter plants, with a one-line phrasing on first
  appearance: `**Opens:** q-what-mary-hides — why does Mary guard the workshop papers?`
  Ids are kebab-case slugs prefixed `q-`, named once, referenced by id thereafter.
- `**Closes:**` — question id(s) this chapter answers.
- `**Carries:**` — question id(s) deliberately left open beyond this book (series
  seeds). Typically on the final chapter; treated by the checker as closed-for-this-book,
  and on the record as a decision rather than a dropped stitch.
- `**Hook:**` (existing field, sharpened) — must lead with the id of the still-open
  question the chapter ends on: `**Hook:** q-who-killed-neil — Pruitt asks for the
  pottery lady by name.`

The **Stakes** notion rides inside the existing **Turn / Change** field, whose template
instruction is sharpened to "what is worse now, and for whom" — no new field.

**Questions have no separate index file.** They exist only in the chapters; the checker
assembles the ledger by reading all chapters. The plan cannot disagree with its own
index because there isn't one.

**Wiring is optional per book (all-or-nothing).** An outline "has wiring" iff any
chapter carries a `**Because:**` or `**Opens:**` line; the checker then requires
complete wiring on every chapter. An outline with no wiring (book 1, hand-authored
books, `/scaffold-book` imports) is untouched by the checker and by the lock's tension
gate. Workshop-built books have wiring by construction. `outline_check.py` (shape) is
unchanged. Retrofitting an old book is a hand-edit, not a migration.

**The reader's copy** strips the Solution block, all wiring lines, question ids inside
Hook lines, Track Movement, and any drafting notes — leaving title, summary, and the
structure prose in story order. **It is also TRUNCATED before the reveal chapter**
(chapters `1..reveal_chapter−1` only; `reveal_chapter` comes from
`series/whodunit/book-NN.yaml`) — a deliberate, accepted change made after a shakedown
review found the reveal chapter's own summary prose names the culprit outright (e.g. "The
reveal: Mary, the letter, the mercy mistaken for murder."). Stripping wiring *fields* alone
left the blind fan reading a sham: the un-blinding text lives in ordinary chapter-summary
prose, which no field-level strip can target. Truncating before the reveal chapter is what
makes "blind" actually true — a real reader guesses the culprit before the reveal, never
after reading it. Produced deterministically (see §7, `plot_stage.py readers-copy`), so
"blind" is enforced by construction, not by asking an agent to look away.

## 6. `tension_check.py` (the proofreader)

A deterministic checker beside `fairplay_check.py`: stdlib-only, named predicates,
fails loud, exit nonzero on violation (0 = evaluated clean; operational errors are
distinct and also nonzero, per existing checker conventions). No LLM judgment anywhere —
every check is arithmetic over the wiring and the beat sheet.

Checks (ids are the waiver handles):

| id | fires when |
|---|---|
| `orphan-chapter` | a chapter's `Because:` is missing, names a nonexistent chapter, or points forward |
| `dropped-question` | a question is opened and never closed or carried by book end |
| `phantom-answer` | a chapter closes (or carries) a question no earlier chapter opened |
| `dead-stretch` | the count of open questions drops below the beat sheet's `questions.min_open_before_reveal` (default 1) on any chapter before the reveal chapter |
| `broken-hook` | a chapter's hook names a question already closed by that chapter's end, or names no known question |
| `starved-thread` | a track's consecutive no-advance run (from Track Movement rows) exceeds the genre's `max_dark_gap` for that track |
| `off-mark-beat` | a turning point tagged with a beat id sits outside the beat sheet's position window for that beat; the reveal's position comes from the whodunit yaml (proposed or locked), not the beat sheet |

Inputs: the outline (skeleton or full — whichever is being checked),
`turning-points.md` (for `off-mark-beat`), the genre beat sheet, and
`series/whodunit/book-NN.yaml` if present (for the reveal chapter). Output: a findings
report naming each check, the chapter(s), and the evidence — printed every run,
including runs where everything is waived.

### The genre beat sheet

`genres/<genre>/beat-sheet.yaml` — nested, human-edited data, so PyYAML (same precedent
as the whodunit ledgers). Referenced from `genre.yaml` (`beat_sheet:` key) and resolved
through the three-tier overlay like every other config file, so a series can override
its genre's numbers. Cozy seed values (tunable, like every Book-1 threshold):

```yaml
beats:
  - { id: inciting-death,    by_fraction: 0.15 }
  - { id: midpoint-reversal, at_fraction: 0.50, tolerance: 0.08 }
  - { id: dark-night,        window: [0.70, 0.85] }
  - { id: reveal,            from: whodunit }
tracks:
  max_dark_gap: { M: 2, P: 4, R: 4, B: 5 }
questions:
  min_open_before_reveal: 1
```

Fractions are of `total_chapters`, computed — never hand-numbered from a framework's
beat numbering. The script stays genre-blind; a thriller pack ships different numbers
and the same script enforces them.

### The lock gains the tension gate (with recorded waivers)

`preflight.py lock-mystery NN` gains a third validator: when the outline has wiring, it
runs `tension_check.py` alongside fairplay and lexicon, and mints no lock while any
check fails un-waived. Overrides are per-check and reasoned:

```
preflight.py lock-mystery 02 --waive dead-stretch:"quiet ch 14 is the designed breath before the second body"
```

Waivers are written into the lock certificate body, so a locked book with a waived
finding says so on its face. For a book without wiring, `lock-mystery` behaves exactly
as today — fully backward compatible. The lock file remains the only certificate; no
`locked:`/`waived:` field ever appears inside the data it gates.

## 7. `/plot-book NN` (Part 2)

Engine-level command; runs from a series folder (normal `.penny/` root resolution);
resolves the genre from `series.yaml` and hard-errors without it, like `/plan-book`.

### Stage detection: `scripts/plot_stage.py`

The "which stage next, what's stale" decision is a deterministic script, not runbook
improvisation:

- `plot_stage.py status NN` — prints, per stage, `done | missing | stale` (from file
  presence + `built_from:` fingerprints), and names the first actionable stage.
  Informational; never blocks (exit 0 unless operational error).
- `plot_stage.py stamp NN <file> --from <upstream>...` — writes the `built_from:`
  fingerprints (single writer for the mechanism).
- `plot_stage.py readers-copy NN` — renders the blind reader's copy from the skeleton
  (deterministic strip per §5, **truncated to chapters `1..reveal_chapter−1`** so the fan
  never reads past where a real reader would have guessed) to
  `output/book-NN/reports/outline-readers-copy.md`.

### The stages

`/plot-book NN` runs `status`, reports the plan's state, and enters the first
actionable stage. Stages 1–4 each pause for the showrunner (1–3 for a choice, 4 for
approval of the proposed whodunit yaml) and end the run after their save point is
written — one taste decision per sitting, the showrunner reruns to continue. Stages
5–6 run consecutively without pausing; stage 7 pauses for sign-off. `.penny/current-stage` is updated per
stage (`stage=PLOT-PREMISE`, `PLOT-ENDING`, `PLOT-SPINE`, `PLOT-COUNTERPLOT`,
`PLOT-CHAPTERS`, `PLOT-WEAVE`, `PLOT-READBACK`).

1. **Premise** *(showrunner chooses)* — `plot-proposer` reads `material.md` (if
   present) under portaprompt rules + the genre archetype document; lays out the
   showrunner's candidates including every rival version; generates rivals to fill
   gaps, each stated as a dramatic engine with its one-sentence pitch; presents a
   shortlist. Choice → `premise.md`.
2. **Ending** *(showrunner chooses)* — `plot-proposer` again: rival endings honouring
   the premise (culprit, why, dark night, cost, restoration). Choice → `ending.md`.
   For a mystery this file *is* the irreducible core.
3. **Turning points** *(showrunner chooses)* — `plot-proposer` again: rival tentpole
   sets placed against the beat sheet, chapter count decided. Choice →
   `turning-points.md`.
4. **The killer's book** *(machine proposes, showrunner approves)* — the existing
   `mystery-planner`, dispatched with the core from `ending.md` + the spine: proposes
   the counter-plot timeline, clue schedule, red herrings, alibi grid into
   `series/whodunit/book-NN.yaml`; the sealed solution is written to
   `output/book-NN/mystery-solution.md`. Showrunner edits until right (as in
   `/plan-mystery` today). **No lock yet** — the lock moves to stage 7 (validate once,
   then freeze; re-planning mid-workshop must not mean repeated lock deletion).
5. **Fill the gaps** *(machine, checked)* — `chapter-weaver`, one dispatch per
   inter-turning-point span, with both endpoint scenes fixed: writes the chapters that
   force the path from one turn to the next, in the wired format, each escalating
   ("worse in kind, not just degree"), each carrying its scheduled clue obligations
   from the whodunit yaml. Output: chapter blocks in `outline-skeleton.md`.
6. **Weave the threads** *(machine, checked)* — `chapter-weaver`, second pass over the
   filled skeleton: braids P/R/B arcs through the chapters, respecting `max_dark_gap`,
   preferring collisions (two tracks in one scene) over parallel lanes.
7. **Read-back and lock** — `plot_stage.py readers-copy`; dispatch `outline-fan` on the
   reader's copy (cross-model where reachable, degrade with a printed "independence
   reduced", per `/review-outline` precedent); run `tension_check.py`; present the
   fan's report and the findings side by side. Showrunner revises (touched files go
   stale, earlier stages rerun as needed) or signs off. On sign-off:
   `preflight.py lock-mystery NN` (now fairplay + lexicon + tension, §6) mints the
   lock. From here the book proceeds exactly as today: `/expand-outline`,
   `/review-outline`, `/draft-chapter`, …

### The agents

Three new role-scoped agents, each shipped with a written output contract (the
review-outline lesson: an improvised prompt binds nothing):

- **`plot-proposer`** — runs stages 1–3 (same shape each time: lay out the showrunner's
  material with rivals surfaced, generate machine rivals, present a choice; never
  choose the core, never invent silently, never improve chosen material). Reads the
  genre archetype + beat sheet. Writes nothing until the showrunner chooses.
- **`chapter-weaver`** — stages 5–6. Context-rich (reads the sealed solution, whodunit
  yaml, premise/ending/turning-points, canon-core + ledger slice). Emits wired chapter
  blocks only; never drafts prose, never writes ledgers or certificates.
- **`outline-fan`** — the blind outline beta reader. Inputs: `{ reader's copy,
  genre fan persona }` and nothing else — reader simulation, same isolation rationale
  as the book-level beta reader (a reader who knows the culprit cannot report when she
  guessed). Reports per-chapter interest (1–5), put-down point(s), whodunit guess
  `{name, chapter}`, would-buy — to `output/book-NN/reports/outline-fan.md`.
  Advisory; never blocks; no `^BLOCKING:` lines.

The fan persona ships in the genre pack (`genres/cozy-mystery/personas/genre-fan.md`,
referenced from `genre.yaml` as `fan_persona:`), because knowing what a genre's readers
crave is genre knowledge. Series may override through the overlay as usual.

### Run-config

One optional addition to `config/run-config.md`: `plot_model:` (defaults to
`drafting_model`) for the proposer and weaver. The fan prefers any reachable
non-`plot_model` model, degrading gracefully.

## 8. Engine / genre / series split (the load-bearing rule)

- **Engine:** `commands/plot-book.md`, `agents/plot-proposer.md`,
  `agents/chapter-weaver.md`, `agents/outline-fan.md`, `scripts/tension_check.py`,
  `scripts/plot_stage.py`, `preflight.py` lock extension, outline template wiring
  additions. All genre-blind.
- **Genre pack (cozy):** `beat-sheet.yaml`, `personas/genre-fan.md`, two new
  `genre.yaml` keys (`beat_sheet:`, `fan_persona:`). `archetype.md` becomes a
  load-bearing input to `plot-proposer` (it is currently loaded by nothing).
- **Series:** nothing new required. Book 1 remains valid un-wired. The workshop first
  runs for real on Pelican's Crook book 2.

`/scaffold-book` (writer-authored outlines) and standalone `/plan-mystery` remain as
front doors; `/plot-book` becomes the recommended door for a new book. The cozy
ideation portaprompt gains a pointer note: its salvage job now has a home inside the
workshop as `material.md` + the proposer's rules.

## 9. Testing

- **`tension_check.py` — test-first, fixture-driven.** `tests/fixtures/` gains one
  clean wired outline and one broken fixture per check id (orphan chapter, dropped
  question, phantom answer, dead stretch, broken hook, starved thread, off-mark beat).
  Tests prove each check fires and stays quiet correctly, the all-or-nothing wiring
  detection, the carried-question exemption, and waiver behaviour end to end
  (`lock-mystery` refusing, then minting with the waiver recorded in the cert body).
- **`plot_stage.py` — unit tests** for stage detection (missing vs stale vs done),
  fingerprint stamping, and the reader's-copy strip (the blind guarantee is a
  deterministic property — test that no solution text, wiring line, or question id
  survives).
- **Agents — contracts, then shakedown.** Output contracts reviewed in lockstep with
  their runbook steps (byte-identical where duplicated, as with the outline-reviewer
  panel). The taste stages cannot be unit-tested; the live shakedown is plotting
  Pelican's Crook book 2, watched, with findings folded back into this spec's
  thresholds.
- **Cross-consistency:** the wired-field parser lives in one place (`penny_meta` or a
  sibling helper) and is shared by `tension_check.py` and `plot_stage.py` — no forked
  parsing conventions.

## 10. Docs

- `CLAUDE.md`: pipeline section gains the third front door and the two new scripts;
  the dependency-split note gains `beat-sheet.yaml` (PyYAML side).
- `README.md` / genre-pack docs: `beat-sheet.yaml` + `fan_persona` documented as part
  of the genre-pack contract — the worked example the thriller pack has been waiting
  for.
- `config/outline-template.md`: wiring lines added with comments; Turn/Change
  instruction sharpened.
- Portaprompt: pointer note (salvage → `material.md`).

## 11. Open questions (deliberately deferred)

- **Rival-count knobs** (how many premises/endings/spines the proposer generates) —
  seed as instructions in the agent contracts, promote to `run-config.md` only if the
  shakedown shows they need turning.
- **Multi-fan panels** (several personas / models on the outline read) — v1 is one fan,
  one reading. The beta layer's K-of-M machinery exists if the signal proves noisy.
- **Retrofitting book 1's wiring** — showrunner's call, an afternoon's hand-edit;
  nothing in this project depends on it.
