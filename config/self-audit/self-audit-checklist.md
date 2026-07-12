# Self-Audit Checklist — Tier B (Drafter Fix-Pass)

**Layer:** `/config/self-audit/` · consumed by the drafter at the `[Self-Audit]`
step (P1.6, design §5b).
**Posture:** **fix-pass, never verdict.** Every item is framed as *"detect this
shape, restructure it"* — never *"rate how well you did."* The instant the drafter
is asked to grade its own compliance, it returns a defensive "no violations." So
this file contains no scoring, no self-assessment, no rating scale.

**Hard constraints (carried from the requirement so it stays safe to build):**
- Produces a **revised draft only.** Emits **no** self-assessment, score, or note.
- Inspectors receive **no signal** that a self-audit ran. They get text, one
  rubric, the ledger slice — isolated as always. The drafter never influences the gate.
- This is a **cost optimization, not a quality gate.** Its job is to lower the
  revision-loop count (target ≤ 2) by arriving at the gate cleaner. Quality is
  guaranteed by the independent inspectors regardless. Measure its worth by a drop
  in revision-loop count once switched on.

**Why only these items live here:** each has a **detectable trigger** and a
**mechanical fix** that requires reshaping, not judging quality. Frequency-only
tics live in the scripts (Tier A); taste-level calls live in the inspectors
(Tier C). Putting a taste call here would invite skimming or, worse, stripping
lines that were actually working.

---

## How to run this pass

For each item: scan for the trigger shape, and where found, apply the fix. Do not
ask whether the sentence is "good." Ask only: **is this shape present? Then break
it.** Leave a sentence untouched only when the shape is genuinely absent — not
when you judge your instance to be the acceptable exception.

---

## 1. Repeated sentence shape: "She did X, feeling Y"

**Trigger:** main clause of physical action + trailing participial/gerund clause
naming a feeling or thought.
> "She set down the cup, feeling the weight of his silence."

**Fix:** cut the trailing clause, or split into two sentences and dramatize the
feeling instead of naming it. The action should carry the feeling.
> "She set down the cup. The silence sat between them like a third person at the
> table." *(or simply end at the action.)*

## 2. Too many participial openers

**Trigger:** sentence opening with a participial phrase ("Turning toward the
window, …", "Wondering what came next, …").

**Fix:** count them in the passage. Where they cluster, **rewrite at least half**
into plain subject-verb openers. Vary the entry point of sentences.

## 3. Emotion stated after the action (the most fixable item)

**Trigger:** physical action + comma + clause that names the emotion the action
already showed.
> "He clenched his fists, anger rising inside him."

**Fix:** **delete the naming clause.** The clenched fists already carry the anger.
If the emotion isn't legible from the action alone, change the *action*, don't add
a label.
> "He clenched his fists."

## 4. Dialogue followed by explanation

**Trigger:** dialogue + tag + concessive clause explaining the subtext the line
already implied.
> "'I'm fine,' she said, though the tremor in her voice betrayed her."

**Fix:** cut the explaining clause. Trust the reader to hear the tremor, or move it
into a separate beat of action.
> "'I'm fine.' Her voice caught on the second word."

## 5. Balanced / symmetrical emotional antithesis

**Trigger:** the `X, but/yet Y` construction that neatly poses two opposed feelings.
> "He wanted to stay, but he knew he had to leave."
> "She was angry, yet beneath the anger was grief."

**Fix:** break the symmetry. Pick the live half and dramatize it, or separate the
two into different sentences/beats so the antithesis isn't pre-packaged for the
reader.

## 6. Repeated "not this, but that" machinery

**Trigger:** clusters of `not X but Y`, `not just X`, `didn't X; Y`, `not brighter,
not louder — just`, `rather than`, or similar contrast formulations.

**Fix:** keep at most the one contrast that genuinely clarifies a necessary
distinction. Rewrite the rest as plain action, dialogue, or concrete observation.
Do not replace one antithesis with another.

## 7. Dialogue explaining the design brief

**Trigger:** a character in stress, embarrassment, or ordinary conversation states
the chapter's thematic/clinical meaning with essay-like precision.

**Fix:** make the line more provisional and human. Let the character describe one
specific symptom, observation, or question; move clean labels into later medical
follow-up only when earned.

## 8. Exit, return, exit

**Trigger:** a scene reaches an exit or emotional landing, then restarts for a
second symbolic object beat or another explanatory speech before ending again.

**Fix:** choose the real ending. Fold late business before the first exit, or cut
the extra exit/re-entry so the scene has one clean shape.

---

## What this pass must NOT touch

These belong to the inspectors (Tier C). Do **not** add them here, and do **not**
strip them during this pass — you cannot freshly judge your own taste-level
choices, and removing them blind does more harm than leaving them:

- Polished contrasts ("not fear, exactly, but something deeper")
- Unnecessary interpretive endings ("knowing nothing would ever be the same")
- Generic lyrical sentences ("the city hummed, alive with possibility")
- Excessively complete / airless sentences (a passage-level gestalt, not a local trigger)
- Predictable closing cadence ("for the first time in years, she allowed herself to hope")

Leave these for the isolated inspector / cross-model read.
