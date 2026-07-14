# The Outline Prompt — compiling a locked outline into chapter briefs

**Status:** proposed
**Date:** 2026-07-14
**Supersedes:** nothing. Delivers the "Part 3 — brief renderer" work deferred in
`HANDOFF-plot.md` ("outline→drafter-prompt compilation… an emphasis budget
(anchor/support/connective)… and negative space").
**Companion spec (not this one):** the cleanup crew — `length_check.py`, word count as
`/review-chapter`'s first step, and `/compress-chapter` — is deliberately held back to a
second spec. This one is the prevention; that one is the cure.

---

## 1. The problem

**There is no chapter brief.** `/draft-chapter` extracts the `## Chapter NN` section from
`input/book-NN/outline.md` and hands it to the drafter verbatim
(`commands/draft-chapter.md:43–53`: *"This full section is the brief passed to the
drafter"*).

The outline is an **authoring** artifact. It exists to help the showrunner see the flow of
the story, and it carries continuity notes, texture to remember, and checklist material.
Shipped unmodified as a **prompt**, every line of it reads as a command, and the reference
material is typographically indistinguishable from the directives. Exactly one field ever
got the memo — the drafter is told to treat "Possible Line-Level Prompts" as non-mandatory
(`agents/drafter.md:50`). The other ten fields are read as orders.

### The evidence

`output/book-01/chapters/ch-01.draft.md` is **3,802 words** against an opening range of
**1,800–2,400** — 58% over the maximum. Nothing in the pipeline noticed, because nothing in
the pipeline measures.

The showrunner had already diagnosed this and written the cure by hand.
`input/book-01/outline.md:32–72`, "Reader-Facing Scene Weighting", prescribes 1–2 anchor
scenes dramatised fully, 1–2 support beats kept subordinate, and connective beats
"compress[ed] to a paragraph, a transition, a phone call, a line of dialogue", and it names
the failure mode precisely:

> *"The reader should finish each chapter remembering one central dramatic experience, not
> six technically correct stops."*

It even carries a per-chapter table naming each chapter's anchors and what to compress.

**And chapter 1 still came out at 3,802 words** — because the doctrine lives at line 42 and
the drafter reads the chapter block at line 119. The chapter blocks are flat numbered lists
of roughly ten beats, each written with the same lavish specificity (beat 7 is a ninety-word
instruction about HR, the marriage, pottery, and the Too-Much). Nothing in that list says
which of the ten is the anchor. **The drafter obeyed the prompt it actually received.**

### The bias is systemic

Every length mechanism in Penny pushes the count **up**, and none pushes it down:

| Mechanism | What it says |
|---|---|
| `agents/drafter.md:61` | under the minimum → *"continue writing — extend a scene, deepen interiority, slow a beat, add sensory texture"* |
| `config/length-profile.md` (series) | states the floor as a hard rule; **never mentions the ceiling** |
| `scripts/lmstudio_draft_chapter.py:413` | *"It is acceptable to run a little long"* |
| `scripts/lmstudio_draft_chapter.py:592` | the repair loop repairs **shortness only** |
| `agents/line-editor.md:23` | may not cut content — sentence-level only, by design |

The one agent that could cut is forbidden from the only cutting that would matter. Going
from 3,802 to 2,400 is a 37% cut: that is beats, not adverbs.

---

## 2. Why an LLM inflates a chapter

Four forces govern how much prose a model returns per beat. The current outline gets all
four backwards.

1. **A numbered list is a promise of parity.** Ten numbered items read as *produce ten
   comparable things*. The list form itself says these are peers — it does not matter that
   item 3 is the confrontation and item 7 is her crossing the road.
2. **Instruction mass sets output mass.** Ninety words of rich, specific direction cannot
   produce one line of prose. **The prompt's own density is a covert word budget**, and it
   is the one the model actually obeys.
3. **A model's default unit is the scene.** Unconstrained, an LLM renders any beat as setup,
   action, reaction, reflection — 400–700 words. Ten beats therefore lands at 4,000–7,000
   words with total internal consistency. 3,802 was not a failure; it was arithmetic.
4. **Naming the form beats naming the number.** Models cannot count words, so "about 120
   words" is weak. "A line of dialogue." "One paragraph, in summary rather than scene."
   Those are craft categories with deep priors, and the model hits them.

### The governing principle

> **The prompt is a scale model of the chapter.** Its shape, its proportions, and its own
> density mirror the prose it intends to produce.

A corollary that inverts an authoring instinct: **write connective beats thinly.** If you
find yourself writing ninety beautiful words about a beat you intend as a transition, the
outline is telling you either that the beat is secretly an anchor, or that you are padding.

---

## 3. The stage

A new step, run **after the lock and before drafting** — front-door agnostic, so it serves
`/plot-book`, `/scaffold-book`, and `/plan-mystery` alike:

```
plot / scaffold / plan  →  lock  →  build the outline prompt  →  draft
```

**`/build-briefs NN`** (name is cheap to change) compiles the locked outline into one brief
per chapter.

The lock is the correct boundary. Once the plot is frozen, the obligations are *settled* —
the clue schedule is validated, the wiring is checked, `reveal_chapter` is fixed — so the
compiler derives each chapter's obligations from data rather than guessing at them.

**Inputs:** the locked `input/book-NN/outline.md`, `series/whodunit/book-NN.yaml`, the
wiring (`penny_wiring.py`), `config/length-profile.md`, and the active genre's
`beat-sheet.yaml`.

**Output:** `input/book-NN/briefs/ch-MM.md`, one per chapter. Authored artifacts: readable,
hand-editable, diffable. **The files are the state.**

**Staleness:** each brief is stamped `built_from_outline: <sha256>`, reusing the workshop's
existing machinery (`stage_status()` / `stamp()` in `scripts/plot_stage.py`). Edit the
outline and the briefs go
stale; `/draft-chapter` refuses a stale brief with a named predicate. Nothing drifts
silently.

### Weighting is a taste stage

Assigning anchor / support / connective is an **authoring act**, not a runtime inference, and
it happens here — once, visibly, in a file — rather than silently inside the drafter on every
run. The machine **proposes** a weighting per chapter; the showrunner accepts or edits it.
This is the workshop's own shape (`plot-proposer` surfaces rivals; the showrunner chooses the
core), and it keeps taste where design §5a puts it.

---

## 4. The brief format

What the drafter receives, in order. Layout is instruction: **a hierarchy encodes weight in a
way no adjective can**, because it changes what the beats look like they *are* — not peers,
but material in service of one scene.

1. **The one thing.** The chapter's single dramatic experience, stated *before* any beat.
   This is `outline.md:40`'s doctrine promoted to the first line of every brief.
2. **The shape.** The anchor scene at the root with its word budget, dramatised fully.
   Support and connective beats **nested beneath it**, visibly subordinate, each naming its
   **form** — "one paragraph", "a line of dialogue", "in summary, not scene".
3. **Obligations — a checklist, never beats.** Clues to plant, questions to open and close,
   tracks to advance. These are things that must be **true of the page**, not stops on an
   itinerary. This is the single biggest fix: today each obligation becomes a numbered item,
   and each numbered item becomes a scene — which is precisely how you get six technically
   correct stops. Most obligations can be discharged inside the anchor scene in a sentence.
4. **The first line — commissioned.** Land in motion, on a concrete image, or mid-exchange.
   Explicitly **forbidden**: weather, waking, arriving, scene-setting run-up. An LLM will do
   all four unless forbidden; an unstated constraint does not exist for the model.
5. **The last line — a graded hook.** Either a **cliffhanger** (a turn, threat, or revelation
   that makes the next page involuntary) or a **promise of next action** (the lesser form: an
   intention, an appointment, a decision taken). What is fatal is neither. Explicitly
   **forbidden**: the reflective button after it (*"she wondered what tomorrow would
   bring"*).
6. **Negative space.** What must not be resolved here, and what must not be dramatised — "do
   not stage the committee meeting; refer to it in a line." Left to itself an LLM resolves
   tension early and dramatises everything.
7. **Reference — demoted out of instruction voice.** Texture, continuity, line-level prompts,
   marked as *available material, not a checklist*.

The per-scene budgets **sum to the chapter's band** from `length-profile.md`. A chapter can
therefore be **priced before it is drafted**: one anchor at ~900, one support at ~400, three
connective at ~120 lands inside 1,800–2,400 — where chapter 1 was supposed to be.

---

## 5. Outline format additions

Optional and **all-or-nothing per book**, exactly as the wiring is. An outline that declares
no weights makes the compiler **degrade to today's flat pass-through with a loud note**
("unweighted — the drafter will treat all beats as equal"), mirroring `tension_check.py`'s
"no wiring detected — skipped". **Book 1 keeps drafting exactly as it does today.**

| Addition | Where | Form |
|---|---|---|
| Scene weight | `### Scene N` block | `- **Weight:** anchor \| support \| connective` |
| First line | chapter block | `- **First line:** <what it must do>` |
| Hook grade | existing `- **Hook:**` field | `[cliffhanger]` / `[promise]` prefix before the `q-` id |
| Length override / chapter type | the chapter **title** | `## Chapter 14 — The Reveal [long: the confession runs its full course]` |

**Two parser constraints, both load-bearing:**

- The title flag **must sit after the em-dash**. `outline_check.py:26`
  (`^Chapter\s+(\d+)(?:\s.*)?$`) tolerates anything after the number, but
  `penny_wiring.py:26` (`^Chapter\s+(\d+)(?:\s*[—-]\s*(.*))?$`) requires the em-dash to
  follow the digits directly. A bracket placed *before* the dash makes the wiring parser stop
  recognising the chapter at all.
- The opening-line field **cannot be called `Opens:`** — that name is already taken by the
  wiring for *story questions opened* (`penny_wiring.py:27`). Hence `First line:`.

`[long: reason]` is a **recorded override**: the showrunner can always override, and the
override is written down — the same contract as `tension_check`'s `--waive`.

---

## 6. Checks — two levels, two owners

The distinction the showrunner drew, and it is the spine of this design:

**Is the chapter doing too much *in content*?** A plot property, visible in the outline
before a word is drafted. A chapter that opens three questions, closes two, plants two clues
and advances four tracks will run long **no matter how well it is written**.
→ `tension_check.py` gains a ninth named check, **`overloaded-chapter`**: scenes plus
obligations exceed what the chapter's word band can hold. A pure count of declared fields —
no prose read, no LLM judgment — which is the shape of the other eight, and waivable the same
way with the reason recorded in the lock certificate. Budgets come from `length-profile.md`
and the genre's `beat-sheet.yaml`, **never from a constant in the engine**.

**Is the chapter doing too much *as a prompt*?** A prompt property, checked at the brief
stage, where the prompt exists.
→ **`prompt-mass-inversion`** — a scene marked *connective* carrying more instruction words
than the chapter's anchor. This is measurable with no taste at all: count the instruction
words per scene and catch the lie. It is the exact defect in book 1's chapter blocks.
→ **`unweighted-chapter`** — a chapter with no declared weights in an otherwise weighted book.
→ **`hook-grade-distribution`** — every chapter declares a grade, and the book is not
twenty-seven consecutive cliffhangers (which reads as machinery and stops being believed).
The distribution is a genre property: thresholds from the beat sheet.

**`outline-reviewer`** gains the lens in prose: *read each beat as a prompt, not as
literature — what will the drafter actually do with this instruction?*

---

## 7. Also in this spec

- **`agents/drafter.md:61` — the padding directive is removed.** *"Continue writing — extend
  a scene, deepen interiority, slow a beat, add sensory texture"* is dilution on demand, the
  literal opposite of page-turner craft. The honest instruction: a chapter that lands short
  is short on **scenes**, not on adjectives.
- **The drafter reads the compiled brief** (`input/book-NN/briefs/ch-MM.md`) rather than the
  raw outline section, falling back to the raw section — with a warning — when no brief
  exists.

---

## 8. Engine / genre / series separation

Per the architectural rule, nothing project-specific lands in `scripts/` or the command
logic:

- Word bands and the anchor/support/connective budget → `config/length-profile.md` (series).
- Hook-grade distribution and the overload budget → the genre's `beat-sheet.yaml`, resolved
  via `penny_genre.py beat-sheet`.
- The compiler and the checks are genre-agnostic and read both.

---

## 9. Testing

**Deterministic (test-first, against `tests/fixtures/`):** the compiler (a weighted outline
renders to the expected brief; an unweighted one passes through with the note), the
`built_from_outline` staleness stamp and `/draft-chapter`'s refusal of a stale brief, and the
three new checks.

**Not unit-testable:** the weight *proposal* is a judgment, like the workshop's taste stages.
Its shakedown is book 1, chapter 1 — 3,802 words against 1,800–2,400 is the hardest case in
the repo, and a correct brief should price it back inside the band.

---

## 10. Out of scope (the second spec)

`length_check.py`; word count as `/review-chapter`'s **first** step, halting a review when a
chapter is ≥25% over with no `[long:]` flag rather than spending a panel on prose about to be
cut; `/compress-chapter` and the `compression-editor` agent. Tolerance is symmetric — within
±10% of the band is fine, over *or* under; 10–25% over is absorbed by the line editor; ≥25%
over needs the knife; ≥25% under is a scene-count problem.

Its highest-value move is already visible from here: **the two places a chapter is fattest
are the two places it is weakest.** The run-up (weather, waking, three paragraphs of
throat-clearing) and the wind-down (the reflective button after the chapter has ended) are
simultaneously the free words, the dead opening, and the dead hook. The chapter usually starts
three paragraphs later than the draft thinks, and ends two sentences earlier.
