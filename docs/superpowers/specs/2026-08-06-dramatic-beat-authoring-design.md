# Writing dramatic beats in `story.md`

Date: 2026-08-06
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Extends `2026-08-03-story-source-layer-design.md` (below: "the
source-layer spec") and `2026-08-04-chapter-direction-and-guardrails-design.md`
("the direction spec").

## 1. Why

The source layer gave the showrunner a document to plot in. It defined that document's
**syntax** completely — four sigils, prose first, tags trailing — and its **craft** not at
all.

Everything the engine says about a beat is bookkeeping, and everything it checks is
bookkeeping: `unknown-clue`, `unknown-job`, `unclosed-question` are all id consistency.
`/plot-book` step 6, the only place in the engine that creates a `story.md`, describes the
work in one clause:

> beats in story order between the turning points, one per bullet, prose first, tags
> trailing

Point a capable writing agent at criteria like that and it produces a correctly-tagged
specification document. That is what happened. Book 01's `story.md`, written and edited
across several sessions, carries beats like:

> Plant only the visible contradiction: a glimpse, log, remark or half-overheard gossip
> suggests Lisa may have met someone she treated as Maggie before the official handover.
> Do not reveal the witness's certainty, the impostor, Tara, or Marion's role here.

> Faye's premises fear surfaces through bakery work and customer rhythm rather than
> exposition.

beside beats like:

> Maggie goes to the studio for her first real entry and finds Lisa dead at the wheel
> beside an incomplete vase.

Only the third is a beat. The other two are instructions to the writer and notes about
rendering — architecture, not drama. They are not *wrong*: they are **misfiled**, and the
direction spec already built both of their homes (`## Guardrails`, `## Chapter Direction`)
without ever saying which content belongs in which block.

There is a second, sharper failure in the same file. Its 18 outstanding `unknown-clue` and
`unknown-job` findings are not craft failures at all — an editing agent minted
`!c02a-false-maggie-prior-meeting` and `#proof-pressure` because nothing told it that clue
ids are ledger facts and jobs are genre facts. That is a question of **authority**, not
taste, and no craft document produces it.

So this design ships two documents, because they answer to different things: craft is
taste, authority is the engine's data model.

## 2. Constraints that shaped it

**2.1 — Editing happens inside and outside Penny.** The showrunner works `story.md` in a
Penny session *and* in other models. Guidance that lives only in agent frontmatter is
unreachable from half of that. The craft document is therefore a **file with a path**,
readable in-session and pasteable out of it, and the agent reads the same file rather than
restating it.

**2.2 — A beat is one visible change, not one scene.** Book 01 has both sizes. The bakery
counter bullet runs four characters through five actions; the studio discovery is one
moment. The guidance says one change per beat. This is a decision with downstream cost —
see §6.

**2.3 — No script can judge drama.** Two of the three tells in §3 are matters of judgment
and stay out of the checker, for the reason there is no solution-blindness script (design
`2026-07-10`): a grep fires on innocent lines. Only the tell that is grammar rather than
judgment is checkable.

## 3. `config/story-craft/writing-beats.md`

The engine's default craft document, and the source of truth for what a beat is.

### 3.1 Where it lives, and why it is a directory

`config/story-craft/` is read as an overlay **directory** (`penny_paths.config_dir_files`),
never as a single file (`config_path`).

A single-file read takes the first hit across the three tiers, so a genre pack wanting to
add two lines about its own beats would have to copy the engine's whole document to say
them — the shadowing bug CLAUDE.md names, in prose form. As a directory the tiers union
per filename: the engine's `writing-beats.md` is always present, and a genre or series
adds files beside it.

The engine ships exactly one file in that directory. Every consumer reads the union, in
tier order (series, genre, plugin), and there is no ranking beyond that.

### 3.2 What it says

1. **The test.** A beat is a change on the page. Someone wants something, does something,
   and the situation is different afterwards. If you cannot see it happen — who is
   present, what they do, what is true after that was not before — it is not a beat yet.

2. **One beat is one visible change.** A bullet carrying four characters through five
   actions is four beats. Chapters are made of beats later; a beat is not a small chapter.

3. **The three tells**, each with a before/after drawn from book 01:

   | tell | example | what it actually is |
   |---|---|---|
   | the subject is an abstraction | "The town's warmth is strained by money and premises fear." | a condition, not an event |
   | the verb is not an action | "Cal's thread surfaces through practical repair." | something the *book* does, not something Cal does |
   | it addresses the writer | "Plant only the visible contradiction… Do not reveal the witness's certainty." | a guardrail wearing a beat's clothes |

4. **The repair move.** Ask *what does the reader watch happen?* and write that:

   > "Faye's premises fear surfaces through bakery work and customer rhythm rather than
   > exposition."
   > → **"Faye hides the adjoining-shop letter under a tray when Maggie asks who else
   > wanted The Wheelhouse."**

5. **The routing rule** — the part that makes the tells actionable. Nothing is deleted;
   it is filed:

   | the note is about | it belongs in |
   |---|---|
   | how the prose should read | `## Guardrails` |
   | where chapters should fall | `## Chapter Direction` |
   | what a question means | `## Questions` |
   | what happens | the beat |

   Every "don't write this here" in the document names the block that wants it. A rule
   with no destination is how the instinct gets suppressed instead of housed.

## 4. `agents/story-author.md`

The authoring role. Context-rich: it reads the sealed solution, because beats are written
toward an ending.

**Inputs:** `{ input/book-NN/story.md, the union of config/story-craft/,
series/whodunit/book-NN.yaml (read-only), the active genre's macro-structure job list,
output/book-NN/mystery-solution.md, and the beat range the showrunner names }`.

**Posture:** proposes in conversation; writes to `story.md` only on the showrunner's
explicit approval; never touches beats outside the named range; never renumbers.

### 4.1 Authority

Derived from what the engine actually validates — `story_cut.py` checks strand slugs for
*shape* only, and checks jobs and clues against external data.

| | |
|---|---|
| `@strand` slug | **the agent's to mint.** Only `^[a-z0-9][a-z0-9-]*$` is enforced; strands are the author's own map of the book. |
| `!clue-id` | **not the agent's.** A clue is a ledger fact. If a beat plants something new: name what it plants, in conversation, and stop. The showrunner writes the ledger entry — with a `description:` and **never** a `plant_chapter:`, which the cut resolves. |
| `#job` | **not the agent's.** A job is a genre fact. A job the genre does not declare is a genre-pack decision, escalated, never invented in the story. |
| `+q-id` / `-q-id` | may open a question, but must add its prose to `## Questions` and must close it. At most one question survives a book — the seed its last chapter hooks. |
| beat prose in range | proposes freely, under §3. |

The agent states which of these it needed and could not do, every time, rather than
routing around them. An agent that mints an id to keep moving produces exactly the 18
findings this design exists to stop.

## 5. `story_cut.py check NN`

A new subcommand, so the story can be validated without a cut plan.

`story_cut.py <book>` is unchanged and still cuts. `story_cut.py check <book>` runs
`check_story` against an **empty cut plan** and prints:

- the blocking findings, **minus every `beats-without-chapter` line**. With no cut plan
  that finding fires once per beat, which is what a story mid-writing looks like, not a
  defect. This is the same call `/book-status` already made when it gave that finding to
  the `cut plan` row rather than the `story` row.
- the advisories, under their own clearly separated heading.

**Exit:** 0 clean, 1 blocking findings present, 2 usage. **Advisories never affect the exit
code.**

This also retires a real papercut: today the only way to validate a `story.md` alone is a
ten-line Python snippet, which `HANDOFF-story.md` documents as the procedure.

### 5.1 The advisory: `directive-shaped-beat`

Fires when a beat's first word is an imperative from one short closed list:

```
Plant, Keep, Save, Show, Do, Don't, Avoid, Ensure, Establish,
Introduce, Reveal, Treat, Let, Leave, Use, Make
```

The message names the bullet and points at the routing rule (§3.2.5) — the note probably
wants `## Guardrails`.

This tests grammar, not judgment, which is why it is the only one of the three tells that
ships as code. "Surfaces" and "reads as" occur in perfectly good beats; a checker for them
would fire on innocent lines.

**The advisory must not enter `check_story`'s `blocking` list, and must not become a cut
refusal.** Sixteen findings that fail loud by name with no waivers is a property worth
keeping clean; an advisory that can block is a seventeenth finding with a softer name.
Implementation: a separate `advisory` key in `check_story`'s returned dict, which existing
callers (`book_status`, the cut) ignore.

`/book-status`'s story row continues to count blocking findings only. Advisories are for
the authoring loop, not the pipeline table.

## 6. Wiring

**`/plot-book` step 6** loses "beats in story order… prose first, tags trailing" and gains
a read of the `config/story-craft/` union plus the routing rule. The stage's other
instructions — draw the clue schedule from the ledger, tag inline, stamp — are unchanged.

**A freshly created `story.md` carries a header naming the craft document's path**, so an
agent arriving with no other context still finds it. That header is the portable half of
constraint §2.1: it is what makes a `story.md` opened in any model self-describing.

## 7. Consequence of "one beat is one visible change"

Splitting book 01's compound bullets takes it from 148 beats to something over 200. Beat
count is an input to the cut and to `obligations.max_per_chapter`, so **splitting must
precede cutting** — see §8. The rule earns that cost: an obligation count computed over
bullets of wildly different sizes is measuring the wrong thing, and a chapter whose beats
are each one change is a chapter whose load the beat sheet can actually judge.

## 8. The named migration — book 01

Engine work is §3–§6. This section is the ordered series work that follows it, recorded
here because the order is load-bearing and book 01 is one session from its cut.

1. **Split and file.** Compound bullets become one-change beats. Directive-shaped bullets
   move to `## Guardrails`; boundary notes move to `## Chapter Direction`.
2. **Resolve the outstanding findings** (19 as of this date, and the list moves between
   sessions — re-run `story_cut.py check 01`): the missing clue ids get ledger entries
   with `description:` and no `plant_chapter:`; `#proof-pressure` and
   `#killer-lookalike-pressure` are mapped onto declared cozy jobs or escalated as a genre
   decision; the surplus unclosed questions are closed or converted, leaving at most one.
3. **Then** delete `input/book-01/outline.md`, `outline-skeleton.md`, and the stale mystery
   lock. Both outline files are committed and recoverable; the lock must go because the cut
   rewrites `plant_chapter:` and that is only safe while the ledger is unsealed.
4. **Then** cut: `chapter-cutter` proposes, the showrunner approves `cut-plan.md`,
   `story_cut.py 01` emits `outline.md`.
5. `reveals:` 13 and 25, then `preflight lock-mystery 01`.

Steps 1–2 precede step 4 because splitting changes every chapter's obligation load, which
is precisely what the cut and `obligations.max_per_chapter` are deciding on. Cut first and
the cut is done twice.

## 9. Tests

Test-first against `tests/fixtures/`, pure stdlib, per the dependency-split rule.

1. **`directive-shaped-beat` fires** on a beat opening with each word in the closed list,
   case-sensitively at the start of the bullet.
2. **It stays silent** on ordinary beats, including ones containing those words
   mid-sentence ("Maggie lets the kiln cool", "Faye keeps the corner table").
3. **The advisory is absent from `blocking`** — a story whose only problem is a
   directive-shaped beat produces an empty `blocking` list and a non-empty `advisory` list.
4. **The advisory does not refuse a cut.** The same story cuts successfully.
5. **`check` exit codes:** 0 on a clean story, 0 on a story with advisories only, 1 with
   blocking findings, 2 on usage error.
6. **`check` suppresses `beats-without-chapter` and nothing else** — a story with both that
   finding and an `unknown-clue` prints only the second.
7. **`story_cut.py <book>` is unchanged** — the existing cut tests pass untouched, and
   `check` is not mistaken for a book number.
8. **The craft directory unions across tiers** — a genre file and the plugin file are both
   returned, and a series file with the plugin's filename shadows only that filename.

## 10. Deliberately excluded

- **A blocking beat-quality finding.** Tempting once the advisory exists, and wrong: the
  two tells worth blocking on are judgments, and the one that is checkable is grammar,
  which has honest false positives ("Let the kettle boil" could open a real beat). An
  advisory a human reads costs a glance; a refusal costs a waiver mechanism this level
  deliberately does not have.
- **An LLM beat-quality inspector.** A `story.md` reviewer that grades beats for drama.
  Plausible later, and premature now: the craft document has never been used on a book, and
  building a grader for a rubric nobody has written against is how the skeleton layer grew.
- **Rewriting book 01 as engine work.** §8 is series work, done by the showrunner with the
  new role. Nothing in `scripts/` knows about book 01.
- **A beat-size finding.** Counting actions per bullet to enforce §2.2 mechanically. The
  count is not computable — "finds Lisa dead at the wheel beside an incomplete vase" is one
  change described in three noun phrases.
- **Teaching the craft document to `chapter-cutter` or `drafter`.** They consume beats;
  they do not author them. Adding a craft read to every agent that touches `story.md` puts
  the same guidance in four contexts and invites drift.
