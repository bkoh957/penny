# Flexible chapter beats

**Recorded:** 2026-08-17 · **Status:** open · **Raised by:** book 01 Act IV reorder

## Problem

`tension_check._obligation_load` treats every obligation as costing exactly the
same:

```python
count = len(beats) + len(clues) + len(ch["opens"]) + len(ch["closes"]) + len(tracks)
```

against a single flat `obligations.max_per_chapter` from the genre beat sheet
(15, for cozy mystery). A beat that is one sentence costs what a beat carrying a
whole community-hall scene costs. Closing a question that needs a scene costs
what opening one with a line of dialogue costs. A track row costs the same as a
required beat.

The check's stated purpose is sound — *"a chapter doing too much IN CONTENT — a
plot property, visible before a word is drafted… past the cap they stop being
sentences and start being stops."* The counting is the part that has stopped
fitting.

## Evidence from book 01

At the end of the Act IV reorder (161 beats, 28 chapters, all five checks green),
**20 of the 28 chapters sit at exactly 15.** The cap is not an occasional ceiling;
it is the shape of the whole book.

Two chapters with identical loads and nothing else in common:

| ch | beats | clues | opens | closes | tracks | load |
|---|---|---|---|---|---|---|
| 20 The Firing | 9 | 1 | 1 | 0 | 4 | 15 |
| 21 Surface and Correction | 4 | 0 | 0 | 7 | 4 | 15 |

Ch 20 is a nine-beat public disaster. Ch 21 is four beats at a borrowed wheel that
happen to resolve seven standing questions. The checker cannot tell them apart, and
neither can anyone reading its output.

**Three things the cap deformed during the reorder, none of them craft decisions:**

1. Ch 26 needed to open `q-mercy` and close `q-becoming`. It could afford one.
   `q-becoming` was pushed to ch 27 — a question now closes in a chapter chosen by
   arithmetic rather than because that is where the answer lands.
2. Ch 27 and ch 28 were re-cut around where the restitution beats fell, not around
   where the surrender ends. The boundary is where it is because 8 beats plus 5
   closes did not fit and 6 plus 4 did.
3. The endgame is structurally close-heavy — questions have to land somewhere, and
   they land late. Late chapters are therefore penalised for doing the one job the
   act exists to do. Ch 26, 27 and 28 all finished at exactly 15.

**A perverse incentive, found the same day.** Ch 3 carries only three track rows
(no `B:`), so its load is 15 rather than 16 — it bought a beat by dropping a track.
`starved-thread` only catches a track that stays dark *across* chapters, so
omitting one here and there is free. Nothing suggests book 01 did this deliberately,
which is rather the point: the cheapest way to fit under the cap is to advance one
fewer thread, and that is the opposite of what the cap is for.

## What it costs today

Structure gets bent to satisfy arithmetic, and the bend is invisible afterwards —
the outline records where a question closed, never that it closed there because a
neighbouring chapter was full. Over a series that is a slow accumulation of
decisions nobody made.

It also mis-reports. A showrunner told "every chapter is at the cap" reasonably
concludes the book is dense everywhere, when in fact eight chapters are dense and
twelve are merely closing questions.

## Sketches

**1. Weight the terms by size.** Derive a beat's cost from its own length or clause
count; charge questions less than beats.
*Objection:* the check's whole virtue is that it is a pure count — no prose read, no
model judgement, nothing that can be sweet-talked. A length-derived weight is gameable
by writing terse beats, and it makes the number unauditable by hand. This trades the
one property worth keeping for the problem being solved.

**2. Per-position caps.** Let the beat sheet declare `max_per_chapter` by act
position, so an endgame may legitimately close more than a setup chapter.
*Objection:* a fudge factor. It does not fix "all obligations cost 1", it moves the
line so the error hurts less. In its favour: it is honest about being a fudge, it is
about ten lines, and it needs no new data.

**3. Separate budgets.** Cap beats, clue plants and question-events independently
instead of summing them.
*Objection:* more knobs to tune per genre, and the genuine failure mode — a chapter
doing too much *in total* — stops being caught at all.

**4. Asymmetric question costs.** An open costs less than a close; an open and close
of the same question inside one chapter costs full freight.
*Objection:* sometimes the open *is* the chapter (a cliffhanger question is the whole
closing move). The asymmetry is real on average and wrong often enough to argue about.
Note that the current flat count already gets the open-and-close-in-one-chapter case
right, and it is the one case it gets right for the right reason: during the reorder
it correctly flagged `q-official`, `q-return` and `q-unsayable` as costing two
obligations for no structural work, and all three were retired.

**5. Measure the thing the cap is a proxy for.** The cap exists to predict "this
chapter will run long." The packet stage already carries per-chapter word bands. Let a
chapter buy headroom by declaring itself long, with total book length as the real
constraint.
*Objection:* this is probably the right model and it is the most expensive. It needs
the word-band machinery to be trustworthy first, and it moves a pre-draft structural
check into partial dependence on a downstream stage.

## Why not now

- The current rule **worked** on the case that raised this. Mid-reorder it caught ch 26
  at 19 and ch 27 at 21, and both were genuinely doing too much. A rule that produces a
  true positive on its first hard test has earned some patience.
- Changing the cap changes what every already-issued lock certificate claimed. That
  wants a migration story, not a patch.
- One book is one data point. Sketches 2 and 5 point in different directions and the
  evidence to choose does not exist yet — book 02's outline, cut under the same rule,
  is the cheapest way to get it.

## If it is picked up

Start by instrumenting rather than changing: have `tension_check` report the load
breakdown for every chapter, not only the ones over cap. Book 01 shows 20 chapters at
15 and nobody knew until it was computed by hand. A second book with that number
printed on every run would settle sketch 2 against sketch 5 in an afternoon.

Fix the track-omission incentive separately and first. It is small, it is clearly
wrong, and it does not depend on any of the above.
