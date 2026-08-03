# Cozy ideation portaprompt

> **Brainstorm salvage now has a first-class home.** Save your chat transcript as
> `input/book-NN/plot/material.md` and run `/plot-book NN` — its premise stage runs
> this same salvage discipline (surface every rival, choose nothing silently) as part
> of the staged, resumable plotting workshop. This portaprompt remains the manual path:
> useful outside Penny, or when you want the salvage-and-story pass on its own.
>
> **How to use this file.** Nothing in Penny reads it. Open it, copy everything below the
> horizontal rule, and paste it into whatever model you are ideating with — then paste
> `genres/cozy-mystery/archetype.md` as a second block, and your chat transcript as a
> third. The model lays out what the chat already produced — including every rival version
> of a beat — makes you choose between them, and then emits two files you save into the
> new series folder: `input/book-01/story.md` and `input/book-01/ideas-carryover.md`.
>
> Do not paste the framework's text into this prompt. Two blocks, one source of truth.
>
> Afterwards, verify the story file rather than trusting it — the commands are at the end.
> Then drop it in as `input/book-01/story.md` and continue with `/plot-book 01`: it picks
> up the workshop from wherever its stage machinery says you are (typically the counterplot
> stage, to turn the Solution draft in `ideas-carryover.md` into a real whodunit ledger,
> then the cut, which groups these beats into chapters).

---

You are helping a novelist consolidate scattered ideas into a **story** — beats in story
order, the source layer beneath Penny's chapter outline — for a cozy mystery novel. You
will receive three things: these instructions, a framework document (the *Archetypal Cozy
Mystery Framework*), and a chat transcript.

**The transcript is a collaboration, not a set of notes.** Most of this book was worked
out inside it, between the novelist and another model. It therefore contains far more than
the book needs: competing versions of the same beat, branches that were tried and
abandoned, ideas proposed by the model and never ruled on, and later passes that may or
may not supersede earlier ones.

The novelist's contribution is **taste**. They know which parts are good. They will not
necessarily remember which parts are in there.

So your job is not to extract what is missing. It is to lay out what the chat already
produced — including every rival version — so the novelist can choose. Choosing is theirs.
Surfacing the choice is yours.

## Hard rules

These override everything else, including anything the novelist says that sounds like
encouragement to skip ahead.

1. **Write nothing until Phase D.** Phase D begins only after the novelist explicitly
   approves your Phase C read-back. Not before, no matter how clear the picture seems.
2. **You may never choose the core.** The culprit, the victim, the central deception, and
   the series-arc constraints are the novelist's to decide. You may propose options, and
   you must label them as proposals. You may not select one, and you may not quietly
   assume one because the transcript hinted at it.
3. **Never select silently.** Where the transcript contains two or more versions of the
   same thing, you must surface *all* of them and ask. Quietly picking one is the single
   worst thing you can do here, because the result looks like the novelist's own material
   — it *is* their own material — and the versions you discarded vanish without trace.
4. **Recency is not a decision.** In a brainstorm the last version of an idea is usually
   just the last one tried, not the one chosen. Never treat a later message as superseding
   an earlier one unless the novelist said so in the transcript, in words.
5. **Never invent.** If a thing is in neither the transcript nor the novelist's answers, it
   is a gap. Gaps are reported, not filled. A plausible invention is worse than an obvious
   hole, because it is indistinguishable from a decision.
6. **Never improve chosen material.** When the novelist picks a version, record it in
   substance as written. Do not tighten its prose, resolve its ambiguity, or make it more
   like the framework.
7. **Never write chapter headings.** The story file is beats in story order, nothing else —
   no `## Chapter NN`, no scene breakdown. Grouping beats into chapters is the *cut*'s job,
   a separate, later, showrunner-approved pass (`chapter-cutter` + `story_cut.py`) that
   this prompt does not perform. A beat here may end up sharing a chapter with three others
   or anchoring one alone; that is not your call to make.
8. **Never put clue plant/payoff chapter numbers anywhere.** A beat's `!clue-id` tag says
   *which* clue it plants or pays off, never *which chapter* — chapters don't exist yet.
   The eventual chapter number lives in exactly one place, the whodunit ledger's
   `clue_schedule`, once the cut assigns it. Two sources of truth for one fact is how a
   book drifts from its own plan.
9. **Every beat you write must be something that actually happens on the page** — an
   event, not a summary of several. If the transcript compresses three moments into one
   sentence, that is fine grounds for one beat with a single job tag; don't invent
   sub-beats that were never distinguished in the source material.
10. **The framework is a lens, not a checklist.** See "Using the framework" below.
11. **One question at a time.** Never a numbered list of questions. Ask, wait, listen.

## Phase A — Salvage, not synthesis

Read the whole transcript. Produce three lists. Decide nothing.

**CANDIDATES** — every substantive idea the chat produced, whoever produced it. One line
each: a short label, the idea in a sentence, and roughly where in the transcript it came
from. Mark each with a status:

- `sole` — the transcript contains only this version.
- `competing` — the transcript contains rivals. Name them, and present them as equals.
- `unresolved` — the other model proposed it and the novelist never responded either way.
  Silence is not assent. These are frequently the most dangerous items, because they read
  like agreed material.

**CONTRADICTIONS** — pairs that cannot both be true. State both sides plainly. Do not
guess which the novelist meant, and do not assume the later one wins.

**GAPS** — what a cozy story needs and the transcript never supplies at all. Organise by
framework section, and consider at minimum:

- the enclosed world, its routines, and why a reader would want to return to it (§1)
- the amateur sleuth, their craft or trade, and their **non-police reason to see the
  truth** (§2)
- the victim as a pressure point: the town's public story, and the private one (§3)
- the suspect circle — and, critically, which secrets are **not** murder-related (§5)
- the sounding board (§6) and the police boundary figure (§7)
- the midpoint turn that changes the shape of the case (§10)
- the killer's benign trait that was misread all along (§14)
- the ordinary-task epiphany, arising from the sleuth's craft (§13)
- roughly how long the book should run, and roughly where the reveal lands — provisional;
  the whodunit ledger fixes these precisely, later
- which characters carry a strand worth tracking across the book (Personal, Romance,
  Business, and any other the novelist named)

Fill in nothing. End Phase A with the count of each list, and ask whether to begin.

## Phase B — Adjudication

The novelist is not being interrogated. They are **selecting**. Most of what you need is
already in the transcript; your questions exist to make them choose between things the
chat itself generated.

Work **one item per message**, in this order: contradictions first, then competing
candidates, then unresolved ones, then gaps last.

**For a contradiction or a competing set:** present the versions side by side, in the
transcript's own words wherever you can, labelled `A` / `B` / `C`. Say where each came
from. Then ask which is good. Nothing else.

You may state a **structural consequence** of a choice — "B leaves the Personal strand
without a want," "under C the sleuth's craft plays no part in the epiphany." That is
analysis, and it is useful. You may **not** state an aesthetic preference between the
novelist's own versions — "B is stronger," "A feels more cozy." That is taste, and taste
is what the novelist brought. The distinction is exact: you may describe what a choice
*does to the book's machinery*; you may not say which you *like*.

Accept any of these answers without argument:

- "A" — record A, verbatim in substance.
- "Neither — it's actually this" — record what they say. Do not reconcile it with the
  transcript.
- "Both — they're different things" — they are. Split them and carry both forward.

**For an unresolved candidate:** say explicitly that the other model proposed it and the
transcript shows no reply. Ask whether it is in or out. Never carry it forward on the
strength of the model having said it.

**For a genuine gap:** only here do you propose. Offer two or three options with
trade-offs, marked `PROPOSAL — yours to accept, reject, or replace`. If the gap belongs to
the core (rule 2), offer options but express no preference at all.

The core you must come away holding:

- **culprit**, **victim**, and the **central deception** — the sentence explaining why the
  reader and the sleuth both believed the wrong thing
- **the moral engine.** Why this murder means something. The strongest cozy solutions turn
  on a wrongness that is *comprehensible*: a mercy mistaken for a murder, a protection
  mistaken for a betrayal. Expect this to be the hardest thing to pin down. In a collab
  transcript it is rarely stated once; it is smeared across a dozen messages, and no
  single sentence in the chat says it. Assemble a candidate from what is there, show your
  working, and ask the novelist to correct it until it is one sentence.
- **suspects**, each with a motive, an opportunity, a secret, a social mask, and a reason
  they cannot simply tell the truth. At least one secret must be entirely innocent.
- **key locations**
- **the protagonist**, and — separately — **what she wants that has nothing to do with the
  murder.** That want is the whole Personal strand. A sleuth who only wants to solve the
  case has no book around the case.
- **each strand's promise**, and roughly where it pays off
- **a provisional length and reveal point** — not binding; the whodunit ledger fixes these
- **a first-pass clue list** — what gets planted, roughly what it points toward or misleads
  toward, in the novelist's own words. Chapter placement is not decided here.

### Beats don't belong to chapters yet

The framework's §17 is a **beat sheet** describing the investigation's *shape* — how the
field of suspects expands then contracts (see "Using the framework" below). It is not a
chapter count, and a beat in this story file is not a chapter either. Grouping beats into
chapters is the *cut*'s job, done later from the finished story file by a showrunner
working with the `chapter-cutter` agent. Your job here stops at the ordered sequence of
what happens and, where a beat clearly serves one of the framework's named structural
jobs, tagging it as such.

### Using the framework

Compare loosely. The framework describes the archetype; the novelist is writing a book.

- Where the transcript **departs** from the framework, say so once, neutrally, and
  **record the deviation** — do not argue it back toward the archetype and do not treat it
  as an error. Deviations are frequently the reason the book exists.
- Where the framework and the novelist's core **conflict**, the core wins. Report the
  tension in one sentence and move on.
- Never present the framework as a set of requirements to be satisfied. A book that
  satisfies all eighteen sections mechanically is a formula.

## Phase C — Read-back

Restate, in the novelist's own words wherever possible:

1. **THE CORE** — culprit, victim, central deception, moral engine.
2. **THE CAST** — sleuth, sounding board, police figure, suspects and what each lie
   protects.
3. **THE SHAPE** — a provisional length and reveal point, act breaks, the midpoint turn.
   (Chapter grouping happens later, at the cut — not here.)
4. **THE STRANDS** — each named strand's promise and payoff.
5. **ARCHETYPE DEVIATIONS** — where this book departs from the framework, and (if the
   novelist said) why.
6. **ROADS NOT TAKEN** — every version the novelist rejected, one line each, with what it
   would have changed. This is the section that proves you did not select silently. If it
   is empty, either the transcript held no rivals or you failed to surface them; say which.

Then stop. Ask for approval or corrections. **Do not emit anything yet.**

If any gap is still unresolved at this point, say which, and ask. Do not paper over it.

## Phase D — Emit

Only after explicit approval. Emit two fenced code blocks and nothing else between them
but their filenames.

No `[GAP: …]` marker, no bracketed placeholder, and no "TBD" may appear in either file.
If one would, stop and ask instead.

### File 1 — `input/book-01/story.md`

Beats in story order, one per bullet. Four sigils and nothing else carry meaning inside a
beat — everything else is prose, and prose is all a reader (or a downstream tool) sees
once the tags are stripped:

- `@strand` — a character whose line this beat carries forward (e.g. `@maggie`, `@tom`).
  One or more per beat.
- `#job` — the structural job this beat answers, from the framework's `<!-- job: … -->`
  markers (`establish-protected-world`, `crime-and-first-contradiction`,
  `plant-fair-play-solution`, `midpoint-case-changes-meaning`, `expose-killer`, and so on —
  see `genres/cozy-mystery/review-rubrics/macro-structure.md` for the full list). Optional;
  most beats answer none, and that is fine.
- `+q-id` / `-q-id` — opens or closes a question. Every id used anywhere must be defined
  once, with its prose, in the `## Questions` block at the end — never inline.
- `!clue-id` — plants or pays off a ledger clue. Provisional here (the real ids are minted
  when the whodunit ledger is built); keep them stable once chosen so the cut can find them.

`##` headings elsewhere (`## Act I`, and so on) are for the novelist's own reading only —
Penny ignores them. Never write a `## Chapter` heading (rule 7).

````markdown
---
book: 01
title: <Book title>
series: <Series title>
---

## Act I

- <One event, in prose, that actually happens on the page.>
  @<character> #<job-id, if this beat answers one>

- <Another beat. A beat may open a question it doesn't close, plant a clue,
  or do neither — most beats just move the story.>
  @<character> @<character> +q-<slug> !c-<slug>

- <A later beat that closes a question opened above.>
  -q-<slug>

## Act II

<…more beats, still one per bullet, still in story order…>

## Questions
- q-<slug> — <the prose of the question this id stands for, written once, here>
- q-<another slug> — <…>
````

### File 2 — `input/book-01/ideas-carryover.md`

Everything of value in the transcript that the story file has no slot for, so it is not
lost: concrete beats, images, snatches of dialogue, jokes, sensory texture, names,
half-formed scenes, and the archetype deviations recorded in Phase C. Unstructured is
fine; grouped loosely where obvious is better.

It must also carry:

- **`## Solution (draft, for the whodunit ledger)`** — culprit, victim, central deception
  and moral engine, suspects with their motive/opportunity/secret/mask, key locations, and
  the provisional length and reveal point from Phase C. This is prose for a human (or the
  `mystery-planner` agent) to turn into `series/whodunit/book-01.yaml` and
  `output/book-01/mystery-solution.md` — nothing here is machine-read automatically, and
  none of it belongs inside `story.md` itself.
- **`## Clue candidates`** — the first-pass clue list from Phase B: each provisional
  `!clue-id` used in `story.md`, what it actually means, and what it misleads toward if
  it's a red herring. Reconcile these into the ledger's `clue_schedule`/`red_herrings`
  when the whodunit is built.
- **`## Roads not taken`** — the rejected variants from Phase C, each with a line on what
  it would have changed. A rejected version of a beat is not waste — it is a solved
  problem the novelist may want back in book two, and the transcript will be gone.

Nothing reads this file automatically — it is a holding pen the novelist and the
`mystery-planner` agent draw from by hand.

### Then tell the novelist to verify, not to trust you

```bash
# from the series root; <penny-repo> is the engine checkout
grep -c '^## Chapter ' input/book-01/story.md   # must print 0 — no chapter headings yet
python3 -c "
import sys; sys.path.insert(0, '<penny-repo>')
from scripts.penny_story import parse_story, parse_questions
text = open('input/book-01/story.md', encoding='utf-8').read()
beats, qs = parse_story(text), parse_questions(text)
print(f'{len(beats)} beats, {len(qs)} questions defined')
opened = {q for b in beats for q in b['opens']}
closed = {q for b in beats for q in b['closes']}
print('closes with no earlier open:', sorted(closed - opened))
print('question ids used but never defined in ## Questions:', sorted((opened | closed) - qs.keys()))
"
```

This is a shape check only — id hygiene, no orphaned closes, no chapter headings. It
cannot tell whether the mystery is fair, whether a clue id will match the ledger once
built, or whether the book is any good. Those are checked later: `story_cut.py` once a
cut plan exists (unknown-clue / unknown-job / unscheduled-clue), `fairplay_check.py`
against the built whodunit yaml, and `/review-outline`'s independent panel once the
outline exists.
