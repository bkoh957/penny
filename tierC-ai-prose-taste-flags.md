# Rubric: AI-Prose Taste Flags — Tier C (Blind Inspector)

**Layer:** `/config/review-rubrics/` · one rubric file, consumed by a blind
inspector sub-agent (design §6), cross-model where reachable.
**Posture:** **judgment, by a reader who did not write the text.** Everything here
requires deciding whether a line does *real work* or merely *performs depth* — the
exact call an author cannot make about their own prose, because they normalized
the choice when they wrote it. That is why these are here and not in the
self-audit: only a structurally-fresh reader catches them, and a different model
is structurally a different reader (§7).

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice }`. No drafting
history. No other verdicts. No signal that a self-audit ran.

**Output (fixed contract, §6):**
`{ score 1-5, violations[], blocking_issues[], evidence[], reviewed_by }`

**Cross-model preference:** route to an alternate model where reachable. These
flags are precisely the ones the drafting model is worst at seeing in its own work,
so a heterogeneous reader is highest-value here.

---

## What you are judging

Whether the prose reaches for the appearance of emotional depth or literary
texture without earning it — the recognizable "AI house style." For each flag
below, the question is **earned vs. rote**, not "is the pattern present." The
pattern being present is not a violation; the pattern being *unearned* is. Cite
specific lines as evidence.

Score the chapter 1–5 on this dimension overall. Mark individual lines as
violations. Mark a violation **blocking** only when the density or prominence of
unearned figuration materially damages the read (see thresholds), not for isolated
instances.

---

## 1. Polished contrasts

> "It was not fear, exactly, but something deeper."
> "She was no longer the woman she had been."

**Earned:** the distinction names something the scene has actually established, and
the "deeper" thing is concretely present.
**Rote:** the contrast gestures at nuance it never delivers — "something deeper"
with no referent. Flag the empty ones.

## 2. Unnecessary interpretive endings

> "She closed the door, knowing nothing would ever be the same."

**Earned:** rare, and only when the interpretation adds something the action
doesn't already carry.
**Rote:** the sentence tells the reader how to feel about a beat that already spoke
for itself. Most are rote. Flag them; the door closing was enough.

## 3. Generic lyrical sentences

> "The city hummed around her, alive with possibility."
> "The silence stretched between them like a fragile thread."

**Earned:** the image is specific to *this* place, *this* moment, and could not be
lifted into any other book.
**Rote:** interchangeable mood-wallpaper that would fit any scene in any novel.
Flag the interchangeable ones.

## 4. Excessively complete / airless sentences

A **passage-level** property, not a single line. When *every* sentence neatly
delivers action + emotion + atmosphere + meaning at once, the prose has no
breathing room and reads as generated.

**How to judge:** read the passage for rhythm, not the sentence for correctness.
If nothing is ever left implicit, if no sentence is allowed to just *do one thing*,
flag the passage and name 2–3 representative lines. This is the flag the drafter
most cannot self-detect.

## 5. Predictable closing cadence

> "And for the first time in years, she allowed herself to hope."

**Earned:** essentially never in this exact shape.
**Rote:** the stock uplift-resolution beat. Recognizable as a *type*. Flag it and
ask for a closing image specific to the scene instead.

---

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** none of the above present, or all instances clearly earned.
- **Score 3:** several rote instances; prose noticeably generic but readable.
- **Score 1:** pervasive; the chapter reads as AI-default throughout.
- **Blocking:** mark blocking when rote figuration is dense enough to break
  immersion — as a seed, **3+ rote instances across flags 1–3 or 5 in a single
  chapter, or any airless-passage flag (flag 4) spanning a full scene.** Calibrate
  once real verdict distributions are visible.

---

## Boundary with the other tiers (do not duplicate)

- **Frequency tics** (bodily reactions, "something," filtering verbs, qualifiers,
  metaphor-pool repetition, cinematic fragments) are counted by `voice_drift.py`
  (Tier A). Do not re-litigate counts here; use that evidence if it's in the slice,
  but your job is the **taste** call.
- **Mechanical sentence shapes** (action+feeling tails, participial openers,
  emotion-after-action, dialogue-then-explanation, balanced antithesis) are the
  drafter's self-audit (Tier B). If many survived into the text you're reading,
  that's legitimate evidence of a weak draft — flag the prose quality, but you are
  not the self-audit.
