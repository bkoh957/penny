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
  the roster.

  Chapter blocks are PACKET FORMAT (spec 2026-07-18 §3): the chapter's `###`
  sections say what must happen and what the reader must feel — never how it is
  staged into scenes. Scenes belong to the per-chapter PROSE MAP, a separate,
  post-lock artifact the map-maker proposes and you approve via /map-chapter —
  the outline itself carries NO "### Scene" section, ever. This is deliberate:
  putting scenes back in the outline is exactly the drift this format exists to
  prevent (design §1).
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
       [long: <reason>]   a recorded override: this chapter is allowed to run long

     The chapter word bands come from config/length-profile.md, which is YOURS
     to author (the engine ships no default). It needs a flat yaml block:
       band_default: [2000, 2500]   (+ band_<type> for each [type: ...] flag)
       min_scene_words: 250
     See README.md, "The length profile". Per-SCENE targets are proposed later
     by the map-maker and approved by you in the prose map — this profile only
     bounds the chapter as a whole and floors any one scene. -->

### Chapter Purpose
<One short paragraph: what this chapter must accomplish, and where it ends.>

### Starting State
- <What is true when the chapter opens — one line per fact.>

### Ending State
- <What is true when the chapter closes — one line per fact, matter-of-fact,
  no staging.>

### Reader-Facing Shape
Primary anchor:
- <The moment the reader will remember.>

Compress:
- <What must happen but earns no page-space of its own — travel, setup,
  repeated introductions.>

### Required Beats
<!-- One line per beat: an event, no staging, no location, no word target.
     Form, not count — a quiet chapter earns three, a set-piece may earn ten.
     ORDER IS CONTRACT: the map's "Beats covered:" lines are 1-based indices
     into this list, in the order written here. -->
- <beat>
- <beat>
- <beat>

### Clues and Plants
<!-- Merged with the whodunit ledger's clue_schedule entries for this chapter
     at packet-assembly time (packet_assemble.py) — that merge renders each
     ledger clue's `description:` field (falling back to `misleads_toward:`,
     then a placeholder if neither is set), so give every scheduled clue a
     `description:` in series/whodunit/book-NN.yaml. This section carries the
     AUTHORED anti-spotlight guidance alongside — how the plant must land. -->
- <plant, with anti-spotlight guidance: "must appear ordinary and helpful">

### Character Knowledge
<Protagonist> knows:
- <fact>

<Protagonist> does not know:
- <fact — the chapter's spoiler boundary; authorial, not derivable from the ledger>

### Guardrails
- <hard constraint — a thing this chapter must or must not do>

<!-- First line / Hook are read the same way on every chapter regardless of format. -->
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

## Chapter 02 — <Title>

### Chapter Purpose
<One short paragraph.>

### Starting State
- <fact>

### Ending State
- <What is materially different by the end — what is worse now, and for whom.>

### Reader-Facing Shape
Primary anchor:
- <>

### Required Beats
- <beat>

### Clues and Plants
- <plant, or "- None." if this chapter schedules none>

### Character Knowledge
<Protagonist> knows:
- <fact>

<Protagonist> does not know:
- <fact>

### Guardrails
- <>

- **Hook:** <q-slug — the unresolved question that earns the next chapter. On a wired book the grade comes first.>

<!-- Wiring (optional; all-or-nothing per book — see tension_check.py). -->
- **Because:** <ch NN — which earlier turn forced this chapter; chapter 1 writes: opening>
- **Opens:** <q-slug — the question this chapter plants>
- **Closes:** <q-slug>

### Track Movement
- **M:** <>
- **P:** <>
- **R:** <>
- **B:** <>
