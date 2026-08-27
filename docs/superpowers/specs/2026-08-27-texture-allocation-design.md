# Texture allocation

Date: 2026-08-27
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Extends the allocate-then-execute pattern the engine already uses for
clues (`whodunit.yaml` `clue_schedule`), beats (`story.md` + `cut-plan.md`) and words
(`length-profile.md`). Depends on the authored-source → derived-slices pattern from
`2026-08-13-background-history-source-layer-design.md`.

## 1. Why

The showrunner asked for a way to punch up a drafted chapter — more town texture, funnier,
more dramatic — as a second pass over existing prose. Investigating where such a pass would
attach turned up a structural gap that is worth more than the pass itself.

**The engine's edit stack is additive exactly once, and subtractive thereafter.**

- `drafter` — the only stage in the pipeline that adds prose.
- `developmental-editor` — reads richly, scores eight dimensions, quotes margin notes. Its
  contract: *"Diagnose, never rewrite. New writing flows back to the `drafter`, not to
  you."* Produces an editorial letter, never prose.
- The five inspectors — gate decisions only.
- `line-editor` — hard constraint: *"No new content: no added beats, clues, red herrings, or
  setting detail that was not present in the draft."* Its moves are cut flab, strengthen
  verbs, vary sentence length, and *"tighten dialogue **tags**"* — tags, not dialogue.
- `copy-editor` — *"Never change meaning, rewrite sentences for style, or cut content."*

So a chapter that arrives with thin texture exits as **cleanly-written thin texture**:
tighter, more correct, and no better. Polish is not punch-up, and the stack only does
polish.

The obvious response is to add a punch-up agent. That is the wrong first move, and section 2
explains why.

## 2. Allocation and execution

Every other creative concern in this engine is split into a cheap global decision and a
local prose job:

- **Clues** — `whodunit.yaml`'s `clue_schedule` says which clue lands in which chapter. The
  packet slices it. The map assigns it to a scene via `Clue:`. The drafter plants it.
- **Beats** — `story.md`'s beats and `cut-plan.md`'s boundaries say what happens where. The
  drafter writes the scene.
- **Scene shape** — the map says how many scenes, their targets, what each one is for.
- **Words** — `length-profile.md` sets the band per chapter type; `draft_words.py` measures.

In every case: a whole-book decision authored once, reviewable in minutes, changeable for
free; and a local execution downstream. Nobody asks the drafter to decide which chapter gets
the murder.

**Texture is the only creative concern with no allocation layer.** It is execution-only.
Every chapter receives the same standing instruction and the drafter decides locally, with
no view of what the other 34 chapters are doing.

The standing instruction, from the packet's Guardrails:

> Preserve cozy oxygen: bakery work, clay process, weather, op-shop comedy, surf-club
> business, repairs, gossip choreography, practical kindness. **Deliberately scoped to no
> strand or job — it is a whole-book rule, and the chapters under the most tonal pressure
> are the ones least likely to reach for it unprompted.**

That guardrail predicts its own failure. It knows the chapters that most need warmth are the
ones least likely to produce it, and its only remedy is to ask harder, identically, in every
chapter.

**This is why texture feels uncontrollable while clues do not.** It is not a model quality
problem. Clues have a schedule; beats have a schedule; words have a schedule. Texture has a
wish.

## 3. Evidence

From drafting Pelican's Crook book 01 chapter 01 (2026-08-26, `claude-opus`, 1980 words in
an 1800–2000 band).

**Every memorable image traces to upstream specification, not to model quality and not to
iteration:**

- *"there had been a great many next years, and she had been reasonable about every one of
  them"* — the map instructed that the clause be ownerless and carry a person-shaped hole,
  as the plant half of a plant/tell pair completed in ch 10.
- The stranger's cup read through glass, thumb-track like handwriting, the over-correction
  left showing — the map fixed the bakery as shut, so she *could not* know whose it was. The
  constraint produced the image.
- Marion taking the sheared door bolt, diagnosing it, naming where it lives now — canon
  specifies she has "one repeatable shape."
- The drafter cut Faye tearing bread on noticing that tearing-not-slicing is canonically
  Tara's tell (`background/faye--tara.md`).

**The one failure is the mirror image.** The draft invented that the kiln was *"tested a
fortnight ago by an electrician who charged her properly for it."* Nothing specified it. It
breaks two later beats: beat 10 needs the ch-02 controller oddity to read as **studio
disrepair, not sabotage**, and a clean professional test a fortnight earlier makes any
malfunction read as recent tampering; beat 34's stated payoff is that Cal is *"one person in
town who can say what that controller was doing before anybody touched it,"* which a more
recent tradesman contradicts.

Where the drafter was told exactly what to do it was good. Where it improvised it caused a
continuity failure. That is an argument for more allocation, not for more execution.

**The reservoir is thin.** The town's entire documented sensory inventory is roughly
twenty-five concrete images: `config/setting-pack/setting.md` (~28 lines — kelp at low tide,
salt on windows, eucalypt after rain, basalt headland bending the wind sideways, wind-bent
gums, a creek that floods after winter rain, converted boat sheds, plus the walking
distances) and the voice pack's *Cozy sensuality* list (kettle steam, clay slip drying on
wrists, wet wool in the bakery, a cat's weight on canvas, and so on).

`config/setting-pack/lexicon.yaml` supplies nothing usable here — 30 lines, and it is a
*policing* list (`narration_ok_from_stage` flags for `lexicon_check.py`), not a supply.

Twenty-five images across 35 chapters. The failure mode past chapter 10 is not genericness
but **repetition**.

## 4. Design

Three components, in dependency order. Each is independently useful; each later one depends
on the earlier.

**Scope for planning.** 4.1 and 4.2 are one implementation plan — the reservoir is inert
without something that spends it, and the allocation has nothing to allocate without it.
**4.3 is a separate plan and should not be written yet**: whether it is needed at all is an
open question (section 7.3) that only becomes answerable once chapters have been drafted
against an allocation. Planning it now would presume the answer.

### 4.1 The reservoir — what this town concretely offers

A catalogue of concrete, specific sensory material: what the bakery smells like at 6am
versus 3pm, what the wind does to the shed roof at three different strengths, what is on the
op-shop counter, what the creek does in the week after it floods, what the arts strip sounds
like on a Tuesday in February.

**Authored, not derived.** It is showrunner material, in the showrunner's voice, the same
way `background-history.md` is.

**Home:** a new top-level section in `input/series/background-history.md`, cut by
`background_cut.py` into `config/setting-pack/reservoir.md`. This reuses the existing
machinery from `2026-08-13-background-history-source-layer-design.md` and adds no new
plumbing. It also inherits the derived-file discipline: nothing hand-edits the cut output.

**Consumers:** the allocation pass (4.2), and the packet, so the drafter has it directly.

**Sizing:** for 35 chapters, aim at 150–250 discrete items, grouped by location, weather,
season, time of day, craft process, and social ritual. This is the real work in this spec;
4.2 and 4.3 are mostly plumbing.

### 4.2 The allocation — which chapter spends what

**Home: `cut-plan.md`, as a `**Texture:**` line alongside the existing `**Compress:**`
line.**

This is the key structural observation. The cut plan is already doing texture allocation —
in the negative only. Chapter 01:

> **Compress:** … The town texture arrives as three specific things she picks up and puts
> down, **never as a survey** …

Chapter 03:

> **Compress:** The rumour cloud. Suspicion is social choreography — who moves seats, whose
> order comes last — **never reported gossip**.

Every one of those clauses says what the chapter must *not* spend or must not render. There
is no positive counterpart saying what it *does* spend. This spec adds the other half of a
line already written, authored at the same time and by the same judgment.

**The pipe already exists:**

```
cut-plan.md ──story_cut.py──> outline.md ──packet_assemble──> packet ──> map ──> drafter
```

Everything else in the cut plan (Summary, Compress, Setting sub-ranges, M/P/R/B tracks)
already flows down that chain. A `Texture:` line inherits it whole.

**What authors it:** a new command mirroring `/plan-mystery` — run once per book, after the
cut plan exists and before mapping. It reads all 35 chapter summaries, the tension curve and
the reservoir, and allocates:

- which chapters carry heavy sensory load and which run lean
- where texture goes deliberately quiet, per the voice pack's *Register under pressure*:
  *"Peak tension: sentences stop building. Things happen and the prose reports them. No wit
  until the pressure drops"*
- which images recur as motifs, and where — an image planted at ch 3 returning at ch 29
  meaning something different
- what each chapter spends, so that nothing is spent twice

Output is a few hundred lines: readable in five minutes, arguable, cheap to redo. Same shape
and same economics as the clue schedule.

**Where it lands per scene:** the map gains a `Texture:` field per scene, exactly parallel to
`Clue:`. The map-maker assigns the chapter's allocation to specific scenes; the drafter
renders it.

**Deliberately NOT an obligation.** `tension_check.py` enforces
`obligations.max_per_chapter` from the genre beat sheet; book 01's chapters are capped at 15
and `length-profile.md` records that this cap is what prevents chapter overload. If texture
items became obligations they would consume that budget and compete with beats and clues for
room.

Texture is therefore a **resource allocation, not a discharge requirement**: the chapter is
told what it *may* spend, never what it must prove it spent. Consequences:

- `map_check.py` gains no new finding. There is no `unscheduled-texture`.
- `inspector-fairplay` is untouched.
- A chapter using three of four allocated images is correct, not short.
- The whole layer is advisory and can never block a finalize.

**Repetition is prevented by construction**, not by accounting: because one pass allocates
across all 35 chapters at once, no chapter can be handed an image another chapter already
holds.

### 4.3 The punch-up pass — repair for chapters that miss anyway

Only after 4.1 and 4.2. With allocation in place most chapters should not need a second
pass, which makes this a small targeted instrument rather than a systemic requirement.

**Invocation:** on-demand and directed. `/punch-up <book> <chapter> --texture | --humour |
--tension`, optionally scoped to a scene. Each dimension is a separate brief with separate
rules. It runs on no chapter by default.

**Position in the pipeline: after `review-chapter` passes, before `finalize-chapter`'s
line-edit.**

```
draft → review (inspectors + dev editor) → clear-dev
      → [punch-up]           ← new, optional
      → finalize: line-edit → copy-edit → ledger → promote
```

**Word budget: overrun then cut back.** The showrunner chose this over three alternatives
(section 5). Punch-up may exceed the chapter band by an allowance — 15% is the proposed
starting figure — and `line-editor` then does what it already does, bringing the chapter back
into band by cutting flab. `line-editor` already enforces the band, so no contract changes.

**The known risk in that ordering:** the line editor may cut the texture punch-up just added.
Mitigation is that the two agents are aimed at different material — the line editor's
checklist is *"redundant qualifiers, throat-clearing, zombie nouns"*, which is flab, not
sensory detail. If this proves insufficient in practice, the fallback is for punch-up to emit
a manifest of what it added and pass it to the line editor as protected text. **Do not build
the manifest until the simple version is observed to fail.**

**Context:** fresh, isolated, holding the chapter plus its allocation slice plus the
reservoir plus the voice pack. Isolation is correct here *because* the allocation layer holds
the accounting — a fresh agent cannot know what chapters 1–19 spent, and with 4.2 in place it
does not need to.

**Cross-model:** route via `run-config.md` to a non-drafting model, same rationale as
`developmental-editor` and `final-reader`.

**Re-gating:** punch-up adds prose after continuity and fair-play have passed. It must
therefore be forbidden from touching any sentence carrying a scheduled clue, and its output
should re-run `inspector-continuity` before finalize. This is the main safety cost of the
pass and is a further argument for doing 4.1 and 4.2 first, since they reduce how often it
runs.

## 5. Rejected alternatives

**Punch-up as an always-on stage in `finalize-chapter`.** Spends model budget on chapters
that do not need it, and a generic "enrich" brief reliably produces the exact artefacts
`inspector-ai-prose` and `ai-tics-detection.md` exist to catch (*"a wave of grief washed
over"*). Texture written without anything specific to be textured about is the failure, not
the cure.

**Punch-up driven automatically by developmental-editor scores.** Attractive — diagnosis
drives treatment, and the margin notes are already quoted and specific. Rejected for now
only because it presumes the punch-up pass is the answer; revisit after 4.1/4.2 are in and
the residual failure rate is known.

**Whole-book punch-up execution.** The showrunner asked whether the pass could run across
the whole book at once. Reading 35 chapters (~72,500 words, ~100k tokens) is feasible;
*emitting* a punched-up 72,500 words is not, so it would decompose to per-chapter work
inside a wrapper, minus the ability to checkpoint or reject one chapter. It also lands after
every chapter is finalized, ledgered and committed, so it would edit text the ledger has
already described — requiring a full re-run of continuity and fair-play across the book to
discover what broke. **The global insight was right and is preserved: it is adopted as
whole-book *allocation* in 4.2, and rejected only as whole-book execution.**

**Reserve headroom by drafting thin** (drafter targets ~85% of band, punch-up spends the
rest). Clean — nothing needs protecting because the space was never used — but it makes the
drafter deliberately under-deliver and invites the developmental editor to flag chapters as
underwritten.

**Swap, not add** (punch-up holds word count constant, funding every addition by cutting its
own flab). Elegant and forces each addition to be net-positive per word, but a much harder
brief, and it will make weak trades to stay level.

**Raise the length bands.** 35 chapters × ~150 words is roughly +5k, taking book 01 from
70–75.5k to 77–80k and changing a commercial length target set deliberately.

## 6. Interactions and risks

- **Mystery lock.** `cut-plan.md` is one of the two files whose edit invalidates the lock
  (`story.md` is the other). Adding `Texture:` lines to an existing book therefore requires a
  re-mint. Known and cheap, but not free — and it means texture allocation for a book already
  in flight is a deliberate act, not a background improvement.
- **`story_cut.py`** must carry the new field through to `outline.md`, and
  `packet_assemble.py` into the packet. Both are additive changes to existing parsers.
- **`map_check.py`** is deliberately untouched. Resisting the urge to gate this is the point.
- **Obligation cap.** See 4.2 — texture must not become an obligation.
- **Reservoir staleness.** Being derived from `background-history.md` via `background_cut.py`
  makes it correct by construction, per the 2026-08-13 spec. Do not create a hand-maintained
  second copy in `config/`, which is precisely the failure mode section 7's appendix records.

## 7. Open decisions

1. **Reservoir size and grouping.** 150–250 items is a guess. Worth building 30 for one
   location first and drafting a chapter against it before committing to a taxonomy.
2. **Does the reservoir belong in `background-history.md` or its own authored source?** The
   former reuses `background_cut.py` with no new plumbing; the latter keeps a 72KB canon
   document from doubling. Recommend starting inside `background-history.md` and splitting
   only if it becomes unwieldy.
3. **Whether 4.3 is needed at all** after 4.1 and 4.2 land. Deliberately deferred.

## Appendix — unrelated engine hygiene found in the same session

Not part of this design; recorded here so it is not lost. The
`2026-08-13-background-history-source-layer-design.md` spec fixed the setting pack, which had
described *"a town called Wreckers Bluff and a protagonist called Cora."* **The same stale
protagonist survives in six engine files that spec did not reach**, and unlike the setting
pack these are engine-level, so they apply to every series. The override path is unused in
practice: the only existing series (`pelicanscrook-series`) carries `beta-readers`,
`genre-pack`, `length-profile.md`, `run-config.md`, `setting-pack` and `voice-pack` in its
own `config/`, and no `line-edit/`, `copy-edit/` or `review-rubrics/`. So the engine's
copies are the ones in force, with nothing shadowing them:

- `config/line-edit/line-edit.md:30` — *"Cora's register is precise and lightly formal with
  warmth through observation. Do not warm it up or cool it down."* This is the live harm: the
  line editor receives this **and** the series voice pack, which says *"Default register is
  James: compound sentences that build, with subordinate clauses that earn their length."*
  Two contradictory register instructions, one naming a character who does not exist in the
  book being edited.
- `config/line-edit/line-edit.md:33` and `agents/line-editor.md:25` — POV anchored to
  "Cora's perspective"
- `config/line-edit/line-edit.md:16` — "Cora being deliberately understated"
- `config/copy-edit/copy-edit.md:14` — "Cora's deceased husband's name"
- `config/review-rubrics/character-voice.md:23` — "no local idiom in Cora's narration"

Plus four worked examples using `Dez` in `config/story-craft/writing-beats.md` and
`writing-chapter-frames.md`, which are defensible but better as role nouns.

**The rule this suggests:** engine files state craft *mechanics*; series files state story
*facts*. Any sentence under `penny/config/` or `penny/agents/` naming a character, a
register or a POV anchor is a config value in the wrong repository. A lint that fails on
capitalised words outside a small craft-vocabulary allowlist would turn this class of bug
into a CI failure rather than a discovery eighteen chapters later.
