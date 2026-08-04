# Chapter direction and authored guardrails in `story.md`

Date: 2026-08-04
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Extends `2026-08-03-story-source-layer-design.md` (referred to
below as "the source-layer spec").

## 1. Why

The source layer gave the showrunner a document they can actually plot in: beats in
story order, four sigils, and no surface on which boilerplate can grow. That property is
load-bearing and this design must not spend it.

But it left two real needs unhoused.

**1.1 — Direction about the cut has nowhere to go.** Reading `story.md`, the showrunner
forms opinions about structure that are not beats: *these two belong in one chapter*,
*don't let this run become four procedural chapters*, *give the raku failure its own
chapter*. Today the only way to express those is to argue with `chapter-cutter`'s
proposal after the fact, once per re-cut, from memory. The opinion is durable; the
channel for it is not.

**1.2 — Authored guardrails have nowhere to live.** Book 01's outline carries per-chapter
notes the author wrote, such as *"Do not flatten Marion into a cackling villain; her
usefulness is her camouflage."* The cut derives Guardrails from a single book-wide
config string plus the reveal-chapter line, so a note like that is dropped on
derivation. It is an instruction about the prose, aimed at the drafter, and the engine
currently has no way to carry one.

Both were found the same way — by deriving book 01's `story.md` from its hand-repaired
outline (2026-08-04) and reading what did not survive.

## 2. The scoping insight

The hard part is that **direction cannot be scoped to a chapter number, because chapter
numbers do not exist until after the cut.** Any design that asks the author to write
"chapter 15" is either wrong at authoring time or invalidated by the next re-cut.

The resolution: a note about Marion is not about a chapter, it is about **Marion**. A
note about the apparent defeat is about **that structural job**. Both are things
`story.md` already names, with sigils it already has.

> **Direction scopes with the same four sigils the beats use.** A note tagged
> `@tara-marion` applies wherever that strand acts. A note tagged
> `#act-iii-apparent-defeat` applies to the chapter that carries that job. An untagged
> note is book-wide.

Nothing new to learn, nothing to keep in sync, and re-cutting cannot invalidate a note.

## 3. Format

Two optional `##` blocks in `input/book-NN/story.md`.

```markdown
## Chapter Direction

- These two belong in one chapter — the discovery and the confrontation should not be
  split. #midpoint-case-changes-meaning
- Don't let the run after the midpoint become four procedural chapters. @maggie
- Give the raku failure its own chapter; don't fold the aftermath into it.
  #act-iii-apparent-defeat

## Guardrails

- Don't flatten Marion into a cackling villain; her usefulness is her camouflage.
  @tara-marion
- Susan's threats must never read as Tara's until the reveal. @susan
- The apparent defeat must cost her reputation, not just time. #act-iii-apparent-defeat
- Keep Faye and Cal on the page in the endgame, not merely referenced.
```

A line is one bullet: prose plus scope tags, harvested by the **same** `TAG_RE` the beats
use (source-layer spec §3). Tags are stripped from the rendered prose exactly as in a
beat. The last example above carries no tag and is therefore book-wide.

This makes `## Questions`, `## Chapter Direction` and `## Guardrails` the three headings
that mean something; every other `##` remains decoration for the author's reading. That
is a deliberate widening of the source-layer spec's "one exception" and is consistent in
kind: each is a small book-level list of id-or-tag-to-prose lines, never a per-chapter
template.

**Only `@strand` and `#job` scope a note.** `+q`, `-q` and `!clue` are refused by name in
these blocks (§5) — they look like they schedule something and they do not.

## 4. Consumption

### 4.1 `## Chapter Direction` — for the cutter, and it stops there

Added to `agents/chapter-cutter.md`'s declared Inputs beside `story.md`, the genre beat
sheet and the genre macro-structure. It shapes the proposal the agent writes; the
showrunner still edits and approves `input/book-NN/cut-plan.md`, which remains the only
thing the emitter reads for boundaries.

**Nothing from this block is emitted into `outline.md`.** It is direction about how to
cut, and once the cut plan is approved it has served its purpose. It stays in `story.md`
because it must survive to the *next* re-cut, not because the outline needs it.

### 4.2 `## Guardrails` — for the drafter, and it survives the cut

`emit_outline` builds each chapter's `### Guardrails` section from:

1. every authored guardrail that applies to this chapter — book-wide (untagged), or
   scoped to an `@strand` or `#job` appearing in one of **that chapter's own beats** —
   **in the order the author wrote them in `story.md`**;
2. the existing series-wide guardrail string (unchanged, from config);
3. the existing `Do not resolve the mystery before chapter NN.` line (unchanged).

**Authoring order, not a scope ranking.** An earlier draft of this section enumerated
book-wide notes first, then strand-scoped, then job-scoped. That was wrong and the
implementation was right (final review, Minor 3): the author already controls the order by
writing it, a note's scope is not a claim about its importance, and "the order you wrote
them in" is the simpler rule to hold in your head while editing the block. Only the two
derived lines have a fixed position — last, and in that order.

**Its own beats, not the running strand high-water mark.** `emit_outline` already keeps
`seen_strands` accumulating across chapters, for Character Knowledge. Reusing it here
would be wrong: a note about Marion would follow her into every chapter after her first
appearance, including ones she is absent from. Guardrails are per-scene instructions to
the drafter, so they attach where the strand actually acts. Character Knowledge
accumulates; guardrails do not.

The distribution is arithmetic over the author's tags. **No LLM sits in the emit path**,
so the cut remains deterministic and re-runnable, as §5.2 of the source-layer spec
requires.

### 4.3 Consequence: a book-wide guardrail widens every packet's continuity slice

Recorded because it is a real per-chapter context cost, not a surprise to discover later.
`scripts/packet_assemble.py` hands the **whole chapter block** to its continuity slicer,
which word-matches continuity entry names to decide what the packet carries. A book-wide
guardrail naming two characters therefore pulls those two entries — **plus their one-hop
`links`** — into the packet of *every* chapter, including chapters they never appear in.

That is the ledger-slice budget the design §4.2 memory rule exists to protect, so the
practical guidance is: keep book-wide notes about *craft* ("keep the community on the page
in the endgame"), and scope notes that *name a character* to that character with `@strand`
so they land only where she acts. No code change follows from this — the slicer is doing
exactly what it should with the text it is given — but an author who writes six book-wide
notes full of proper nouns has quietly enlarged every chapter's context, and should know it.

## 5. Refusals

Three new findings, in the existing vocabulary, **with no waivers** — the same rule the
rest of this layer follows (source-layer spec §8): fix the story, don't excuse it.

- **`orphan-direction`** — a note tagged `@susan` when no beat tags `@susan`, or tagged
  `#job` when no beat carries that job. The note would be rendered nowhere and read by
  no one. Exact parallel to `orphan-question`, and the same justification: a written
  instruction that silently reaches nothing is worse than one that was never written,
  because the author believes it is in force. Applies to both blocks.
- **`misplaced-schedule-tag`** — a `+q`, `-q` or `!clue` tag on a line in either block.
  Scheduling is a property of beats. A clue tag here would look like a plant and would
  never be planted. The message **quotes the harvested sigil+slug**: the tag capture is
  deliberately loose and guardrail prose is English sentences, so `-- never arch` harvests
  as a close tag with slug `-`, and without the token in the message the author cannot see
  which characters caused it (final review, Minor 6).
- **`wiring-shaped-directive`** — a line in either block whose prose, once emitted as
  `- {text}`, matches `penny_wiring`'s `FIELD_RE` (`- **Because:**` / `**Opens:**` /
  `**Closes:**` / `**Carries:**` / `**Hook:**`) or `TRACK_RE` (`- **M:**`). The emitter
  writes authored guardrails verbatim into the chapter block, and `penny_wiring` matches
  those patterns against **every line of the block**, not only the wiring section — so
  `- **Closes:** q-bogus` in `## Guardrails` passes every other check and then makes
  `tension_check` fire `phantom-answer` on a chapter whose wiring footer never said any
  such thing, with nothing to tell the author why. The deterministic layer's own output
  must not be forgeable from authored prose (final review, Important 2). Applies to both
  blocks: one shape rule, one place to learn it.

`unknown-strand` and `unknown-job` (both already defined) extend to cover lines in these
blocks, so a typo'd tag is refused by name rather than silently scoping to nothing —
which is the loose-capture / strict-validation contract the source-layer spec §3 already
sets for beats.

This takes the module from 13 named findings to 16.

## 6. Compatibility

**Both blocks are optional, and their absence is byte-for-byte today's behaviour.** This
is the first test, not an afterthought: book 01's current `story.md` must cut to a
byte-identical `outline.md` after this change.

No stamp work is needed. `stamp_outline` already records `story_sha` over the whole of
`story.md`, so adding these blocks moves the fingerprint automatically, and
`recut_refusal`'s logic is untouched.

## 7. Tests

1. **Null change.** A `story.md` with neither block cuts to an outline identical to the
   one produced before this change. Run against book 01's real derived story.
2. **Strand scoping.** A guardrail tagged `@tara-marion` appears in the Guardrails of
   exactly those chapters whose own beats tag `@tara-marion`, and in no others —
   including *not* in a later chapter she is absent from, which is the `seen_strands`
   trap in §4.2.
3. **Job scoping.** A guardrail tagged `#act-iii-apparent-defeat` appears in exactly the
   chapter whose beats carry that job.
4. **Book-wide.** An untagged guardrail appears in every chapter.
5. **Ordering.** The series-wide guardrail string and the reveal-chapter line are still
   present, after the authored ones.
6. **Direction is not emitted.** No text from `## Chapter Direction` appears anywhere in
   the emitted outline.
7. **`orphan-direction`** fires by name, for an unused `@strand` and for an unused
   `#job`, in both blocks.
8. **`misplaced-schedule-tag`** fires by name for each of `+q`, `-q` and `!clue`.
9. **`unknown-strand` / `unknown-job`** fire on typo'd tags in these blocks.
10. **Agent contract.** `agents/chapter-cutter.md` declares `## Chapter Direction` among
    its inputs (pinned like the existing cutter-contract test).
11. **Authoring order.** On a chapter carrying an untagged note *and* a scoped note, the
    emitted order matches the order they were authored in — the assertion must be made on
    a chapter where a scoped note competes for the front of the list, or it cannot tell
    authoring order from the ranking §4.2 used to enumerate.
12. **`wiring-shaped-directive`** fires by name for each `FIELD_RE` field and for a
    `TRACK_RE` row, in both blocks, while ordinary bold emphasis in a note stays legal.
13. **Frontmatter is not the body.** A `##` heading occurring inside frontmatter (a legal
    YAML comment at column 0) opens no directive block and no questions block — all three
    parsers walk the same frontmatter-skipped view.

## 8. Deliberately excluded

- **Checkable structural direction.** A finding that fires when the approved cut plan
  splits beats the author said belong together is tempting and would make
  `## Chapter Direction` load-bearing rather than advisory. Excluded for now: it turns a
  reading note into a gate before anyone has used the notes on a real book, and the
  natural expression of "these belong together" is a beat-index range, which is exactly
  the fragile chapter-number-shaped scoping §2 exists to avoid.
- **Per-beat direction.** Appending notes to individual beat lines. A beat is one
  sentence of what happens; a beat carrying a paragraph of instruction becomes the
  duplicate-outline failure `story.md` was built to prevent, and it cannot express
  anything book-wide.
- **A separate `input/book-NN/direction.md`.** Philosophically tidier — `story.md` stays
  purely beats — but it splits the author's attention while reading, puts the Marion note
  a file away from Marion's beats, and an empty file named `direction.md` is precisely
  the kind of unscoped surface that grew into a second book once already.
