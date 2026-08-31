# Opening and Closing are beats, not sentences

Date: 2026-08-29
Status: defect, fix brief — not a feature proposal
Severity: medium — one sentence in one agent contract; it degrades the two highest-stakes
sentences in every chapter of every book

Filed in `specs/` rather than `backlog/` deliberately: `docs/backlog/README.md` excludes
defects. Written up because the one-line fix follows from an argument that should be on the
record, and because the cheap fix was reached only after an expensive one had been proposed.

## 1. Why

`agents/drafter.md:34-35` tells the drafter:

> `### Opening` and `### Closing` are **instruction, not context**: the chapter opens and
> lands **exactly as they say**, not as something you're free to reinterpret in the room.

That instruction cannot be satisfied, because the field it governs does not contain what it
assumes. `**Opening:**` and `**Closing (kind):**` are authored in `cut-plan.md` at plotting
time, months before any prose exists, and in practice they are **a mix of two different
kinds of thing** with nothing marking which is which.

From Pelican's Crook book 01's 35 chapters:

| ch | field | actually is |
|---|---|---|
| 03 | *"Rourke fills the kettle before he looks at the body."* | a usable sentence |
| 02 | *"Lisa Vale has left three messages by nine, and all three are about money."* | a usable sentence |
| 03 | *"The town has decided what her steadiness means before she has finished being steady."* | **a description of an effect** |
| 04 | *"Five people have now told her who Lisa was, and every account is really a confession about the teller."* | **a summary of a chapter's worth of scene** |

The last two are not sentences anyone would put in a novel. They cannot be reproduced
"exactly as they say". So the drafter must decide, unaided, whether any given field is text
to copy or intent to realise — and nothing in the packet, the map or the contract tells it.

There is also a **tense mismatch built into the mechanism**. The fields are authored in
present tense (`Maggie's thumbs find…`) and the series voice contract is third limited
**past**. Every drafter must therefore transform the "verbatim" text, which means the one
thing declared fixed is guaranteed to be altered, by hand, differently each time.

**And nothing checks it.** No script compares a draft's first or last line to the packet —
verified across `map_check.py`, `chapter_refs_check.py` and `review_gate.py`. The contract
is unenforced, so the variance it produces is invisible.

## 2. Evidence from a real book

Book 01 chapter 01 was drafted three times in one day against an unchanged packet.

Packet `### Opening`:

> Maggie's thumbs find the centre of a ball of local clay before she has found the light switch.

Three drafts, three renderings:

| version | rendered as |
|---|---|
| v1 | "Maggie's thumbs found the centre of a ball of local clay before she **found** the light switch." |
| v2 | identical to v1 (v2 was allowed to read v1) |
| v3 | "Maggie's thumbs found the centre of a ball of local clay before she **had found** the light switch." |

v3 is the most faithful — the source is present perfect (`has found`), so past perfect
(`had found`) is the correct transform, and v1 flattened it to simple past. That error
survived v1's drafter, its five inspectors, its line editor and its copy editor, and was
caught only because v3's drafter worked blind and had to derive the line from the packet
rather than copy it forward.

**Worse: the sentence is technically wrong for the scene it opens.** "Finding the centre"
is *centring*, a wheel operation; thumbs at a centre is closer to *opening*, also on the
wheel. The scene wedges — `"rolling the ball up and away and turning it, forty times or
so"` — which is a bench operation done with the heels of the hands. A series whose standing
guardrail is *"pottery is evidence… never generic art language"* opens on an image that does
not match its own action.

An independent reviewer separately flagged the line as too oblique for the book's audience.

**The cost of that being "verbatim":** correcting it means editing `cut-plan.md`, which
regenerates `outline.md`, which the mystery lock pins by sha — so a craft fix to one
sentence costs a lock re-mint, packet rebuilds and map re-stamps across the book. That
price is what makes the error stick.

## 3. Fix

Replace `agents/drafter.md:34-35`:

```diff
-  `### Closing` are **instruction, not context**: the chapter opens and lands
-  exactly as they say, not as something you're free to reinterpret in the room.
+  `### Closing` name the chapter's **first and last beat, not its first and last
+  sentence.** The chapter must open on what `### Opening` describes and land on what
+  `### Closing` describes; you write the sentences. They are authored at plotting time
+  as outline shorthand, are given in present tense, and may be phrased either as a
+  usable line or as a description of an effect — render either in the series' tense and
+  voice. Do not reproduce them verbatim, and do not treat a concretely-phrased one as
+  more binding than an abstract one.
```

That is the whole change. One passage, one file.

### Why not the alternatives

**Rewriting all 70 fields into a consistent intent form.** Proposed first, and it is
overkill: it touches `cut-plan.md`, so it costs a `story_cut` run, a lock re-mint, packet
rebuilds and map re-stamps across 35 chapters — to achieve exactly what redefining the
contract achieves for free. It would also discard genuinely good lines like *"Rourke fills
the kettle before he looks at the body"*, which work perfectly well as beats.

**Dropping the fields entirely.** Available — `story_cut.py:150` treats adoption as
all-or-nothing, so it would be all 35 — but it forfeits the typed closing kind
(`cliffhanger` / `irony` / `promise of action`) and the chapter-to-chapter contract, and it
takes the risk the engine names at `story_cut.py:156`: *"a missing ending hands the last
line back to the drafter."* The cliffhanger is what turns the page; keeping a hand on where
a chapter lands is worth more than controlling the words it lands in.

**Renaming the labels to `Opens on:` / `Closes on:`.** Clearer, but `penny_story.py:185,188`
parses both labels by literal regex, so it is an engine change *plus* a 35-chapter data
migration, for a wording improvement. Worth doing only if the fields are being touched for
another reason.

**Adding a checker that enforces the verbatim contract.** The opposite fix — make the
unenforced contract real. Rejected: it would enforce a rule that is unsatisfiable for the
abstract fields, and would have locked in book 01 chapter 01's technically-wrong opening as
correct.

## 4. Consequence for the locked artefacts

None, which is the point. `cut-plan.md`, `outline.md`, the mystery lock, every packet and
every map are untouched. Book 01 chapter 01's opening ceases to be a defect the moment it is
read as a beat: *she is in the clay before she finds the light* is true, and the drafter is
then free to render it accurately for the operation the scene actually performs.

## 5. Test

1. A fixture packet whose `### Opening` is phrased as an abstract effect (*"The town has
   decided what her steadiness means"*) asserts the drafter contract does not require
   verbatim reproduction. This is a contract-wording change, so the test is on the agent
   definition text rather than on behaviour — assert `agents/drafter.md` contains no
   instruction to reproduce `### Opening` or `### Closing` exactly.
2. Regression guard: assert no script compares a draft's first or last line to the packet's
   `Opening`/`Closing`, so a future checker cannot silently reintroduce the verbatim
   contract without this spec being revisited.

## 6. Related

Fourth in a sequence of defects where **an agent receives an input that differs from what
the repository intended, and no check can see it** — after
`2026-08-27-packet-extract-heading-collision-fix.md` (a slice truncated),
`2026-08-29-engine-holds-story-details-fix.md` (a pack contradicted), and
`2026-08-29-runbook-render-corrupts-positional-vars-fix.md` (an instruction rewritten).

This one is the variant where the input is intact and the **instruction about how to read
it** is wrong. Same signature: silent, invisible to every gate, and surfaced only because a
human read the prose closely enough to notice a first sentence that did not describe its own
scene.
