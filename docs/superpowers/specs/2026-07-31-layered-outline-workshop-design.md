# Layered outline workshop — design

> **Status:** approved in brainstorm 2026-07-31; not yet planned.
> **Supersedes:** the middle of `/plot-book`'s staged workshop — the `turning-points`,
> `chapters`, and `weave` stages, and the `outline-skeleton.md` artifact.
> **Leaves untouched:** everything from the mystery lock onward. The chapter stays the
> load-bearing unit; packets, maps, scenes, drafting, the review panel, and
> finalization are not in scope and do not change.
> **Builds on:** `2026-07-30-staged-reveal-readback-design.md` (the fan read-back and
> the `fan-audit` feedback ledger are reused here, not rebuilt),
> `2026-07-18-packet-map-chapter-design.md` (the downstream contract this must still
> satisfy).

---

## 1. The failure this fixes

The showrunner completed the plotting workshop for book 01 and came out the other side
with an outline they did not believe in, then spent days repairing it by hand. The
repair is still unfinished. This is not a tooling complaint; it is a creative-process
failure with three distinct causes.

**The workshop never produced a small whole.** It asks for the premise, then the ending,
then the turning points — three fragments, each answered as well as anyone can answer a
fragment — and then generates thirty chapters of consequence in a single move. At no
point does a complete, readable version of the story exist at a size a person can hold
in their head. So the showrunner's real judgement deferred itself to the first artifact
that was actually a story, which was `outline.md`: ninety-two kilobytes, arriving after
every decision had already been compounded into chapters.

**No one is asked whether people behave like people.** The deterministic checks count
coverage, wiring, fairness, and pacing — whether every opened question closes, whether a
thread goes dark too long, whether a chapter is overloaded. The fan read-back asks
whether the story is interesting and where a reader would put it down. The outline panel
reads for craft. Not one seat at the table asks *would this person do this*.

The consequence, in book 01: Simon is Lisa's husband. The outline repeatedly explains a
back-posted handover appointment as reading like "Simon covering office procedure" — the
same phrase, five times, in chapters 1, 4, and three others. It is not a decision a
character makes; it is a label the machine reused whenever a clue needed to land softly.
A man whose wife has been murdered, who knows an appointment was altered to put another
woman at the scene, does not quietly tidy paperwork. He goes to the police or he accuses
her. The hole is large enough that any first reader would find it, and every reviewer in
the system missed it.

**Holes of that kind are invisible at every magnification.** Simon's two load-bearing
moments are sixteen chapters apart. Each reads fine alone. A chapter-by-chapter reviewer
never crosses that distance; a reader closes it effortlessly. The defect is not in any
chapter — it is in the gap between them, and nothing in the process ever looks at a gap.

**A fourth cause, structural.** `outline-skeleton.md` and `outline.md` carry the same
eight headed sections per chapter, the second at greater length. Two files describing one
story, and they have already drifted into two different books: the skeleton is 30
chapters with the reveal at 26, `outline.md` is 28 with the reveal at 24. They agree on
chapter 1 and diverge from chapter 2 onward. Their guardrail lines contradict each other
outright — *do not name Tara before Chapter 26* against *before Chapter 24*. Neither is
wrong; there are simply two of them, and nothing in the engine can detect the
disagreement.

### 1.1 Explicitly rejected

**Rejected: more reviewers over the finished outline.** The panel and the fan read both
ran over book 01 on 2026-07-28 and both missed Simon. Adding a third reader of the same
artifact would miss him for the same reason — the artifact is chapters, and the defect is
not in a chapter.

**Rejected: a deterministic motivation checker.** Whether a grieving husband would stay
silent is a judgement about human behaviour. It cannot be a predicate, and a keyword grep
over character names would fire on every innocent mention. This is the same ruling as
`2026-07-30 §1.1`: the deterministic layer is for facts, not taste.

**Rejected: re-plotting book 01 through the new workshop.** Regenerating would discard the
outline the showrunner has already shaped. This ruling stands from
`2026-07-30 §10` and is unchanged. See §8.

---

## 2. The shape of the fix

Replace the single invisible weave with **four passes over one story, each ending at a
stopping point that asks a different question**, and each reading something small enough
to sit with in one go.

The passes make the story **thicker**, not finer. The spine stays the length it is; each
pass lays a complete new strand across it, and the strand is read *on its own* before it
is braided in. Resolution — the number of beats — grows as a side effect, never as the
goal.

**Shape is decided up front, not judged at the end.** This is a deliberate choice against
the alternative, and it is justified by the genre pack rather than by taste: cozy mystery
is a well-mapped form, and this repo already ships the map. `genres/cozy-mystery/review-rubrics/macro-structure.md`
enumerates **28 numbered structural jobs** in order across four acts — *Establish the
Protected World*, *Deliver the Crime and Its First Contradiction*, *Plant the Fair-Play
Solution*, *Midpoint Turning Point — The Case Changes Meaning*, *Apparent Defeat and Final
Contradiction*, *Restore the World*, and the rest — each stating what the story must
accomplish there and how it commonly fails. Pass 1 is not invention. It is answering a
form that is already written down.

The accepted cost: a strand cannot move a turn. If the culprit's chronology wants the
midpoint reversal later, the answer is no; the material before it gets compressed
instead. In a genre this constrained that trade is cheap, and it buys a book that is
structurally sound from the first pass.

---

## 3. One story file, two views

### 3.1 `input/book-NN/story.md`

The passes write into a single file. It begins as the 28-job spine and grows as strands
braid in. **It is never regenerated from scratch — only added to.** Beats are written in
story order, and each beat is tagged with the strand or strands it belongs to.

This replaces five artifacts that currently all claim to describe the story: three plot
save points, `outline-skeleton.md`, and `outline.md`.

### 3.2 Three derived views, never authored

The showrunner never reads the source. They read views rendered from it on demand — no
second file, no possibility of drift, the same relationship `plot_stage.py readers-copy`
already has to the outline. Three lenses, each answering a different question:

**Story at a glance.** Every chapter's title and summary, in order, and nothing else.
This is the view for judging whether the book works, and it is the one that gets used
every time rather than only when something is wrong. Measured on book 01 as a pure
extraction from `outline.md`'s existing `### Chapter Summary` sections: **2,140 words
against the outline's 14,170** — fifteen percent, eight minutes to read.

**Spine map.** Which of the structural jobs have a real event and which come back empty.
The view for judging whether the structure has holes.

**Strand pages.** One character's line through the whole book, alone on a page.
Deterministic: extracted by tag from `story.md`, or by mention-in-order from
`outline.md`. The view for judging whether people behave like people, and the reason the
design is worth building:

```
SIMON  arranges the handover  →  wife found dead  →  says
       nothing about the appointment  →  keeps covering
       office procedure  →  ...
```

Four lines on one page. No magnification of the murder spine ever puts them adjacent.

### 3.3 `outline-skeleton.md` is retired

It exists only to be a thinner copy of `outline.md`, and it is the mechanism by which
book 01 became two books. Everything that reads it already falls back to `outline.md`
(`preflight.py:321-322` tries both), with one exception that must be fixed as part of
this work: **`plot_stage.py readers-copy` hard-requires the skeleton** (`plot_stage.py:209`,
and the two `sys.exit("plot_stage: no outline-skeleton for book …")` paths at `:566` and
`:607`). It must read `story.md` before the cut and `outline.md` after it.

This is a live defect today, not merely a future concern — see §8.

### 3.4 `outline.md` is a machine input and does not shrink

The showrunner's complaint that `outline.md` is unreadable — signal lost in noise — is
correct and is **not** fixed by trimming it. Measured on book 01: 1,769 lines for 28
chapters, of which eleven section headings repeat in every chapter (308 lines of pure
furniture), plus `Primary anchor:` / `Compress:` / `Maggie knows:` / `Maggie does not
know:` at 28 each, plus lines that are verbatim identical across most of the book — the
same guardrail 23 times, the same "Maggie does not know the full Marion/Tara truth" 23
times, the same "prior open questions remain live" 21 times. Roughly a third of the file
is structure and boilerplate carrying no story.

That repetition is **required**. `packet_assemble.py` slices one chapter out of
`outline.md` and builds the drafter's packet from it, so every chapter block must be
self-contained. The file's audience is the packet assembler and, through it, the drafter.

The showrunner has been reading it only because nothing else existed. §3.2 is the fix:
the file stays exactly as it is, and they stop reading it.

---

## 4. The four passes and their gates

**Pass 1 — the spine.** The 28 structural jobs, each answered with what happens in this
book. Turn positions come from the genre beat sheet as they do now (`inciting-death` by
0.15, `midpoint-reversal` at 0.50 ±0.08, `dark-night` in [0.70, 0.85], `reveal` from the
whodunit ledger). After this pass those positions do not move again. No chapters exist.
Length: roughly a page and a half; four minutes to read.

> **Gate 1 — does the crime hold?** And: does every one of the 28 jobs contain a real
> event rather than a placeholder? A job that can only be answered vaguely is a hole,
> found while the fix is one sentence.

**Pass 2 — the counterplot.** The culprit's own chronology, in her order, including what
happened before the book opens. Read alone, then braided onto spine beats. This stage
still dispatches the existing `mystery-planner` and still produces the sealed whodunit
ledger — that machinery is unchanged.

> **Gate 2 — does the plan make sense, and is the culprit a person doing it rather than
> a mechanism?** This is the gate that would have asked who witnessed Marion meeting
> Lisa — a question the current process never puts.

**Pass 3 — the people.** Every significant character gets a line through the whole book,
read on its own page via §3.2. **This pass has no equivalent in the current engine.**

> **Gate 3 — would this person do this?** The empty seat, filled. See §5.

**Pass 4 — texture.** Set pieces, subplots, tangents — each hung off a spine beat it
serves, never free-floating.

> **Gate 4 — is this a book someone wants to read?** The existing blind fan read-back,
> pointed at a page and a half instead of ninety kilobytes.

### 4.1 Gate 4 reuses the shipped read-back

The staged reveal-aware read-back from `2026-07-30` applies here unchanged in substance:
`outline-fan` dispatched fresh per stage, never inline; cumulative reader's copies each
stopping one chapter short of a protected turn; the suspicion audit comparing what the
reader believes against the `reveals:` block it is never shown. It works *better* at this
position — the copy is cut at beats rather than chapters, so there is no reveal-chapter
summary prose to truncate around.

All four gates write findings into the existing `output/book-NN/reports/outline-feedback.yaml`
ledger, in the same append-only, one-item-one-change form, with `state:` owned by the
showrunner. Gates 1–3 use new `--source` values alongside the existing `fan-audit`.
The readback loop shape is unchanged: read → findings → work them → re-read.

---

## 5. Gate 3: the seat that was empty

A new agent whose entire brief is to read one strand and ask whether a human being would
behave this way. It is given the strand, the premise, and what that character knows and
when. It is **not** given the other strands — this is isolation in the established sense
(`CLAUDE.md`, *Independence, isolation, reader simulation*): narrow inputs, no
cross-talk, so it cannot rationalise a hole by appeal to plot convenience elsewhere.

It holds the solution. Like `inspector-fairplay`, knowing the truth is what lets it judge
whether the character's ignorance or silence is earned.

Its findings are granular by the same rule as `2026-07-30 §6.1`: one item, one change,
one named beat. *"Simon's line is weak"* is a failed finding however true, because the
showrunner cannot sit down and fix it.

### 5.1 Worked example — the stalker

The showrunner's proposed subplot: someone stalks Maggie in Act I; the reader is led to
read stalker-as-killer; in truth the stalker witnessed Lisa meeting "Maggie" — actually
Marion impersonating her — concluded the real Maggie is the murderer, and is pursuing
revenge. This is the design working end to end, and it is recorded here because it
demonstrates each pass doing its job:

- It **enters at pass 3**: it is a person's line through the book.
- It **sends a question back to pass 2**: who witnessed that meeting? The current
  counterplot never asks, which is precisely why the meeting exists in book 01 as an
  inert paperwork smudge that no human reacts to.
- It **collides with the Simon hole, and they are the same wound.** Someone knows about
  that meeting. The current outline has that person shrugging. A strand pass forces the
  question *why does the witness not go to the police* — the same question that breaks
  Simon — and whatever answer the showrunner chooses becomes the subplot's engine
  rather than an embarrassment.
- It **takes its position from pass 1**: it arrives after the death and the initial
  suspect field, applies pressure at job 11 (*Apply the First Meaningful Pressure*), and
  cannot be unmasked before the midpoint reversal, because its truth is meaningless to a
  reader who does not yet know about the impersonation.
- It **owes a plant** at job 10 (*Plant the Fair-Play Solution*): something early that
  reads either way — a sign he fears Maggie rather than hunts her.
- It **gives Act II a job.** Book 01's chapters 7–14 sag because they exist to deliver
  clues; a stalker running underneath them is pressure that is not clue-delivery.

---

## 6. How this maps onto `/plot-book`

The existing runbook already has the right bones. `STAGE_ORDER` and the `_UPSTREAM`
staleness map in `plot_stage.py` are extended, not rebuilt; the sha256 `built_from_*`
save-point pattern is unchanged and simply applies to more stages.

Current: `premise → ending → turning-points → counterplot → chapters → weave → readback`
→ lock.

- **`material`, `premise`, `ending`** — unchanged. These taste stages work.
- **`turning-points` becomes the spine.** Same seat, wider aperture: instead of three or
  four turns, all 28 jobs. `plot-proposer` already reads the archetype and beat sheet, so
  it is being asked for more of what it already does.
- **`counterplot`** — keeps its job, gains gate 2. `mystery-planner` untouched.
- **`weave` is the stage being replaced.** It currently braids all four secondary tracks
  through the chapters in one invisible move with no stopping point. That move becomes
  passes 3 and 4, braided separately, each gated. **This is the heart of the change;
  everything else is consequence.**
- **`chapters` moves from the middle to the end.** It becomes the cut (§7).
  `chapter-weaver` survives with a narrower, easier job: it no longer invents the middle
  of the book, it decides where the cuts fall.
- **`readback`** — stays, becomes gate 4, runs before the cut.
- **The lock** — untouched.

### 6.1 The honest cost

Stopping points go from roughly four to eight, in a workshop the showrunner already found
hard to sit through. The defence is that they are a different *kind* of stop. The current
ones ask the showrunner to invent something from very little — which is the hard part,
and why judgement deferred itself. The new ones ask them to read a page and react, which
is the work they were already doing three weeks later against ninety kilobytes.

---

## 7. The cut is a handover, not a link

Chapters are cut once, at the end, from the finished `story.md` straight into
`outline.md` in packet format. Chapter count, combining, and splitting are technical
decisions delegated to the model, because the foundation underneath is already sound.

**After the cut, `outline.md` is canonical and `story.md` is frozen history.** There is
no regeneration path from story back to chapters. This is deliberate and it protects the
`2026-07-30 §10` ruling: hand-shaped chapter work must never be overwritten from
upstream. By the time the cut happens the story is already right — that is the entire
point of the four passes.

From the cut onward the existing engine takes over completely unchanged: wiring,
`tension_check.py`, `preflight lock-mystery`, packets, maps, drafting.

`/expand-outline`'s current job (skeleton → `outline.md`) is absorbed by the cut, since
the cut produces packet format directly. Whether the command is retired or reused as the
cutting mechanism is an implementation decision for the plan.

---

## 8. Book 01 — diagnosis, not re-plotting

Book 01 is not re-plotted. §1.1's ruling stands. What book 01 gets is the **first slice of
this design, built as a read-only diagnostic over the outline that already exists.**

### 8.1 The live defect, fix first

`plot_stage.py readers-copy` reads `outline-skeleton.md` and never falls back to
`outline.md`. Book 01's skeleton is the drifted 30-chapter version with the reveal at 26.
**The fan read-back queued as book 01's next action would therefore have read a book that
no longer exists**, and its findings would have been worked against the wrong chapters.
This must be fixed, or the skeleton deleted, before any read-back is run.

### 8.2 What is generated

- **The story at a glance**, extracted from `outline.md`'s existing summaries (§3.2).
- **Strand pages** for every significant character, extracted in order from `outline.md`.
- **A spine map**: which of the 28 structural jobs `outline.md` answers, and which come
  back empty or weak. Expectation: several Act II jobs are blank — *Apply the First
  Meaningful Pressure* especially — and those blanks are the sagging middle, named.
- **Findings** into the existing feedback ledger.

Nothing is written to `outline.md` by machine. Nothing regenerates. No file is at risk.

### 8.2.1 A derived `story.md` for book 01 — as a worksheet, never a source

Book 01 also gets a `story.md` reconstructed backwards from `outline.md`. It buys two
things: the stalker is far easier to place in a beat list than across 28 chapter blocks
carrying wiring and clue obligations, and it tests the `story.md` format on a real book
before book 02 commits to it — the cheapest validation available.

**It carries no authority.** Editing it must never re-cut book 01's chapters; that is
§1.1's forbidden move. Changes decided at the story level are hand-translated into
`outline.md` edits, one chapter at a time. The worksheet is a thinking tool that is
thrown away.

Two things enforce that, because relying on memory will not hold:

1. **Location states authority.** Book 02's authored `story.md` lives in `input/`, where
   sources live. Book 01's derived one lives in `output/book-01/reports/`, where
   generated artifacts live. The two are the same shape; only the folder says which is
   which, and that is sufficient because no cutting path ever reads from `output/`.
2. **No cut path exists for it.** The cut (§7) reads `input/book-NN/story.md` and nothing
   else. A worksheet in `output/` is unreachable by it, by construction rather than by
   convention.

**The derivation is lossy, which is the second reason it cannot be a source.** Pulling
strands out is mechanical — every beat naming Simon, in order. Mapping 28 chapters onto
28 structural jobs is a judgement, and separating spine from texture is another. Book
01's `story.md` is therefore an *interpretation* of the outline made by an agent reading
it, not a representation of it. Sound for thinking with; disqualifying as a source of
truth.

### 8.3 What is decided and by whom

The showrunner decides: whether Simon is the stalker or the stalker is someone else,
where the stalker enters, which empty Act II jobs to fill. The edits to `outline.md` are
then made one chapter at a time, in conversation, each one seen before it lands — the
same loop as the readback, driven by a named list instead of a reread.

The stalker is the large piece and this spec does not pretend otherwise: folding a new
strand through Acts I and II touches placement, per-appearance action, reader
permission, and the fair-play plant. It is real work either way. The difference is
placing him deliberately against a spine rather than guessing.

### 8.4 Also owed for book 01 — with one correction

Write the `reveals:` block; delete the drifted `outline-skeleton.md`; delete the stale
lock, which already attests to an outline modified after it was minted; re-mint after the
repair.

**Correction to the previous stream's handoff.** It records the turns as `impersonation`
at **15** and `marion-is-tara` at **27**. Those are *skeleton* chapter numbers. Against
the canonical `outline.md` the same two turns are at **13** (`The Vase Was a Rehearsal
[type: midpoint-reversal]`) and **25** (`Tara`, following the reveal at 24). Writing 15
and 27 would have protected two chapters that hold neither turn, and the staged read-back
would have cut the reader's copy in the wrong places — silently, since nothing validates
a `reveals:` chapter against what that chapter contains.

This is §1's drift defect arriving in the very next action queued for book 01, and it is
the strongest available argument for §3.3. The numbers must be re-derived against
`outline.md` and confirmed by the showrunner, since which turns are protected remains a
taste call even once the numbering is settled.

### 8.5 Book 02 is the first book through the full workshop

By then the strand and spine views will have earned their place on a real book, and we
will know whether these are the right four passes before committing the workshop to them.

---

## 9. Build order

1. **The three views as read-only diagnostics over `outline.md`** (§3.2), plus book 01's
   derived worksheet (§8.2.1). Unblocks book 01 this week; costs almost nothing; proves
   the central idea. Story-at-a-glance first — it is pure extraction, it is the view that
   gets used every time, and it is already demonstrated working on book 01.
2. **Fix `readers-copy`'s skeleton dependency** (§8.1) — a live defect regardless.
3. **Book 01's repair**, working the findings from step 1.
4. **The workshop rebuild** — `story.md`, the four passes, gates 1–3, the cut — informed
   by what book 01's strands actually turned up.
5. **Retire `outline-skeleton.md`** across `scripts/`, `commands/`, `agents/`,
   `genres/cozy-mystery/ideation-prompt.md`, and `README.md`.

Step 5 is a filename change, and the standing rule from `2026-07-30` applies: **enumerate
every glob and literal naming the artifact** across all four locations. Both plan defects
in that stream were this omission.

**Steps 1–3 are one implementation plan. Step 4 needs its own spec.** This document
settles the shape of the workshop rebuild — the four passes, the gates, the cut, the
handover rule — but it deliberately does not settle `story.md`'s beat syntax, how strand
tags are written, or how the 28 jobs are addressed in a genre-agnostic way. Those are
decided once book 01's strands have shown what the passes actually need to carry, which
is the whole reason the diagnostic comes first.

---

## 10. Testing

Test-first against `tests/fixtures/`, per repo convention.

- The strand renderer is deterministic and gets fixture-based tests: a beat tagged with
  two strands appears in both views; an untagged beat appears in neither; strand order
  follows story order.
- The spine map is deterministic in its *coverage* reporting (which of the 28 jobs have
  content) even though filling them is an LLM judgement.
- `readers-copy` gets a regression test asserting it reads `story.md`/`outline.md` and
  does not require `outline-skeleton.md`.
- Any edit to `commands/plot-book.md` trips
  `test_runbook_gives_literal_bash_for_every_stamp_call`, and gate 4's changes reach
  `test_outline_fan_contract`. Standing rule: **the approved artifact wins; re-pin the
  test, never reword the artifact to satisfy it.** Budget for this in every task touching
  `agents/*.md` or `commands/*.md`.

---

## 11. Out of scope

- Everything after the mystery lock. Chapters remain the load-bearing unit.
- Genre packs other than cozy-mystery. The 28-job spine comes from
  `macro-structure.md`, which is a cozy artifact; another genre supplies its own, and the
  engine must resolve it through `genre.yaml` rather than by filename. No hardcoding.
- The length/compression companion spec (`length_check.py`, `/compress-chapter`) and the
  `/new-series` onboarding brainstorm, both still owed from earlier streams.
