# Writing beats

The engine's default craft guidance for `input/book-NN/story.md`
(spec `2026-08-06-dramatic-beat-authoring-design.md` §3).

This file is read through the config overlay as a **directory** — a genre pack
or a series adds files beside it, and only a file of the same name replaces it.

## Examples never name a character

**Examples in engine files never name a character.** Use a role noun — *the
potter*, *the carpenter*, *the victim*, *the protagonist* — and generic slugs,
not a series character's name. A name in an example is indistinguishable from
canon to whoever reads it next, and it dates the moment the series changes:
the engine is genre/location-agnostic (`CLAUDE.md:11-14`), and an example is
still engine content even though nothing in it is executed. This applies
however the name is spelled — capitalised in prose, lowercased inside a
hyphenated slug, subject or possessive — the test is whether a character is
named at all, not the grammar it's named in.

## What a beat is

**A beat is a change on the page.** Someone wants something, does something,
and the situation is different afterwards.

If you cannot see it happen — who is present, what they do, what is true after
that was not before — it is not a beat yet.

**One beat is one visible change.** A bullet carrying four characters through
five actions is four beats. Chapters are made of beats later; a beat is not a
small chapter.

## Three tells that you have written architecture instead

**1 — The subject is an abstraction.**

> The harbor town's calm is strained by rent debts and old grudges.

Nothing happened. A condition was described.

**2 — The verb is not an action.** *surfaces, reads as, is seeded, establishes,
gives, shows.*

> The carpenter's thread surfaces through practical repair.

Surfacing is something the *book* does, not something the carpenter does.

**3 — It addresses the writer, not the world.** *Plant, Keep, Save for later,
Do not reveal, rather than.*

> Plant only the visible contradiction: a glimpse, log or half-overheard gossip
> suggests Priya may have met someone she treated as Odette. Do not reveal the
> witness's certainty here.

That is a guardrail wearing a beat's clothes. `story_cut.py check NN` will name
it as `directive-shaped-beat` — advisory, never blocking, because only this
third tell is grammar rather than judgment.

## The repair

Ask **what does the reader watch happen?** and write that.

> The printer's premises fear surfaces through print-shop work and customer rhythm
> rather than exposition.

becomes

> The printer hides the eviction notice under the till when Odette asks who else
> wanted The Tannery.

Same information, now visible.

## Where the rest goes

Nothing you wrote is deleted. It is filed:

| the note is about | it belongs in |
|---|---|
| how the prose should read | `## Guardrails` |
| where chapters should fall | `## Chapter Direction` |
| what a question means | `## Questions` |
| what happens | the beat |

Direction and guardrails scope with the same sigils the beats use — `@strand`,
`#job`, or untagged for book-wide. Never a chapter number: chapters do not
exist until the cut, so any chapter-shaped scoping is invalidated by the next
re-cut.

## The beat number

A beat may open with its position: `- [12] The potter throws the cup she meant to
keep.` Optional, but all-or-nothing per file — number every beat or none.

The number is **not** an identity. It is the beat's current position, written
down so it can be checked. Position is the truth; insert a beat at 5 and the old
5 becomes 6, whatever its bracket still says.

That is exactly why it is worth writing down. A cut plan says `Beats: 22-25`,
which is positional, so one inserted beat quietly hands a chapter its
neighbour's work — and nothing else catches it, because the ranges still cover
every beat and still look contiguous. `story_cut.py check NN` compares each
written number against its real position and blocks on the mismatch.

**Never renumber by hand.** After any insert, delete or reorder:

```bash
python3 scripts/story_cut.py number NN
```

It rewrites only the brackets, refuses to write if any beat's prose or tags
would change, and skips `## Questions`, `## Chapter Direction` and `##
Guardrails` — whose bullets are not beats. Keep those three blocks at the bottom
of the file.

## What a beat never carries

Chapter numbers, packet sections, Character Knowledge, Starting/Ending State,
wiring rows. All of those are **derived** by the cut from the ledger, the genre
and your tags. If you are typing one into `story.md`, it is already being
written for you somewhere else.

The `[n]` prefix is not an exception: it is a *beat* number, not a chapter
number, and the tool writes it.
