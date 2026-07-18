---
book: 01
total_chapters: 2
---

<!--
  Penny outline template. The writer authors STORY here; the engine derives
  STRUCTURE for review. Set total_chapters to your chapter count and add one
  "## Chapter NN" or "## Chapter NN — Title" block per chapter (contiguous
  1..total_chapters). Each "## Solution: <label>" block is a SEALED mystery
  answer key — one per gated mystery strand (v1 gates the first; extra Solutions
  ride as threads). "## Threads" is optional; omit it and the scaffolder proposes
  the roster. The Chapter Engine and Story Tracks sections are optional guidance
  for the drafter; include them when using the rich chapter-brief format.
-->

## Solution: the-central-mystery
- culprit: <name>
- victim: <name>
- central deception / motive: <one or two prose sentences>
- suspects: <name>, <name>, <name>
- key locations: <place>, <place>

## Threads
- <strand-name> — <one line: the promise this strand opens and where it pays off>

## Chapter 01 — <Title> [type: opening]

<!-- Title flags are OPTIONAL and must come AFTER the em-dash — a bracket before it
     stops the wiring parser recognising the chapter at all.
       [type: <band>]     selects the word band from config/length-profile.md
       [long: <reason>]   a recorded override: this chapter is allowed to run long -->

### Chapter Summary
<Prose summary of the chapter's narrative scope.>

### Chapter Structure
- **Start / Desire:** <What the protagonist wants at the chapter's opening.>
- **Pressure / Obstacle:** <What blocks or complicates that want.>
- **Turn / Change:** <What is materially different by the end — what is worse now, and for whom.>
- **Texture / Pleasure Layer:** <Humour, setting, food, animals, community rituals.>
- **First line:** <What the opening sentence must DO — land in motion, on an image, or
  mid-exchange. Never weather, waking, arriving, or a scene-setting run-up.>
- **Hook:** [cliffhanger] <q-slug — the unresolved question that earns the next chapter>

<!-- Hook grade comes FIRST on the line, before the q-slug: [cliffhanger] is a turn,
     threat, or revelation that makes the next page involuntary; [promise] is the
     lesser hook — an intention, an appointment, a decision taken, and the right
     choice for a quieter chapter. A chapter that ends on neither ends on nothing. -->

<!-- Wiring (optional; all-or-nothing per book — see tension_check.py). -->
- **Because:** <ch NN — which earlier turn forced this chapter; chapter 1 writes: opening>
- **Opens:** <q-slug — the question this chapter plants>
- **Closes:** <q-slug>

### Track Movement
- **M:** <Mystery thread advancement — or "None" if a rest chapter.>
- **P:** <Personal/internal thread.>
- **R:** <Romance/community thread.>
- **B:** <Business thread.>

### Scene 1 — <Title>

<!-- The chapter word bands come from config/length-profile.md, which is YOURS
     to author (the engine ships no default). It needs a flat yaml block:
       band_default: [2000, 2500]   (+ band_<type> for each [type: ...] flag)
       min_scene_words: 250
     See README.md, "The length profile". -->

**Beat flow:**

1. <beat>

## Chapter 02 — <Title>

### Chapter Summary
<Prose summary.>

### Chapter Structure
- **Start / Desire:** <>
- **Pressure / Obstacle:** <>
- **Turn / Change:** <What is materially different by the end — what is worse now, and for whom.>
- **Texture / Pleasure Layer:** <>
- **Hook:** <q-slug — the unresolved question that earns the next chapter. On a wired book the id comes first.>

<!-- Wiring (optional; all-or-nothing per book — see tension_check.py). -->
- **Because:** <ch NN — which earlier turn forced this chapter; chapter 1 writes: opening>
- **Opens:** <q-slug — the question this chapter plants>
- **Closes:** <q-slug>

### Track Movement
- **M:** <>
- **P:** <>
- **R:** <>
- **B:** <>
