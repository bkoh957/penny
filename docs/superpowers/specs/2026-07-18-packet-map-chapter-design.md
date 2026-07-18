# Packet / Map chapter redesign — outline blocks, chapter packets, prose maps

**Date:** 2026-07-18
**Status:** approved in discussion (showrunner ratified each section; spec review waived)
**Supersedes:** the scene-breakdown outline format and the brief compiler
(`docs/superpowers/specs/2026-07-14-outline-prompt-design.md`) as the per-chapter
drafting pipeline. The lock, the review gate, and everything book-level survive.

## 1. The problem, measured

The outline-expander produced ~6 scenes per chapter, uniformly, across all 27
chapters of the live book-01 — each scene 16–23 outline lines with its own
location, purpose, numbered beat flow, and emotional turn. That is ~160
dramatised units against a 65,000-word budget: ~400 words per unit if all were
staged. Chapter drift: scenes became chapter-sized (location changes, heavy
dramatic lifting), so every chapter either starves its scenes or blows its band.
The 3,802-word chapter 1 was the drafter obeying an outline that genuinely
describes a book 2–3× the size being paid for.

The brief compiler (2026-07-14 branch) was a compressor bolted downstream of an
inflator: the weigher worked out which five of six chapter-sized scenes to crush
back down. This redesign removes the inflation instead of compressing it.

**Direction chosen by the showrunner:** chapters become short units of one or
two key ideas; chapter-sized scenes are promoted to chapters (book-01: 27 →
~40); the per-chapter pipeline adopts the triple-pass structure (packet → map →
draft → audit → revise). Scenes survive **only inside the prose map**, terse and
priced — never in the outline.

**Dual mandate (standing constraint):** every design choice must serve both
(a) repairing the live, locked, partly-drafted book-01 of Pelican's Crook and
(b) greenfield future books (premise → archetype-variation plot → chapter flow).

## 2. Architecture — three artifacts

```
outline.md — chapter blocks in packet-section format, wired, NO scenes  (locked)
    │
    │  slice + lookups                      deterministic, no LLM
    ▼
PACKET  input/book-NN/packets/ch-MM.md      what the chapter needs to know
    │
    │  Pass 1: map-maker proposes, showrunner approves
    ▼
MAP     input/book-NN/maps/ch-MM.md         how the chapter spends its words
    │
    │  Pass 2: drafter (map = instruction, packet = context,
    ▼           + previous chapter's final ~300 words + mystery-solution.md)
DRAFT   output/book-NN/chapters/ch-MM.draft.md
    │
AUDIT   /review-chapter (unchanged) → clear-dev → /finalize-chapter (unchanged)
```

- **Outline says what must happen. Map says how it is spent. Draft makes it
  prose.** Each layer is checkable against the one above.
- Packet assembly is a script (slice + lookups). The map is the only new LLM
  product, and it takes the established posture: **an agent proposes, the
  showrunner approves; only the approved artifact is stamped and consumed.**
- Anchor/compress selection ("Reader-Facing Shape") is **authored in the
  outline block** — which moment carries the chapter is taste, and taste stays
  upstream. The map stages and prices what the packet already ruled.

## 3. The outline chapter block (packet-section format)

Each `## Chapter NN — Title [type: <band-type>]` block in
`input/book-NN/outline.md` contains these `###` sections (canonical example,
showrunner-authored, from the live book's chapter 5 — the murder-discovery
set-piece):

```markdown
## Chapter 05 — Opening Day [type: event]

### Chapter Purpose
Maggie's open-studio afternoon succeeds commercially but tempts her to use
the Too-Much for public approval. She makes one survivable ethical mistake.
The chapter ends when news arrives that Neil is dead.

### Starting State
- The Wheelhouse is ready for its first open-studio event.
- Maggie has sold one difficult vase to Neil.
- Neil understands that the Too-Much is cognitive overload.
- Maggie and Faye are becoming friends.
- Maggie is attracted to Cal but misreads some of his practical care.
- Mary appears kind, useful and protective of Cal.
- Neil is alive at the beginning of the chapter.

### Ending State
- The Wheelhouse has made real sales.
- Maggie has used Faye and Iris's visible tension for one public joke.
- Faye is newly cautious around Maggie, but their friendship is not broken.
- Maggie is physically overextended.
- Mary's domestic-order habit has been planted inconspicuously.
- Neil has been found dead.

### Reader-Facing Shape
Primary anchor:
- The open-studio social set-piece.

Secondary anchor:
- Maggie's too-clever joke about the Faye/Iris choreography.

Closing turn:
- Faye receives the news about Neil.

Compress:
- Setup and pack-down.
- Individual customer transactions.
- Minor introductions already established elsewhere.

### Required Beats
- Stronger pottery is finally displayed.
- Faye brings food.
- Iris's duplicate jam creates visible social geography.
- Maggie makes one accurate joke that earns a laugh.
- Faye warns her with a look.
- Maggie stops before revealing the deeper private wound.
- Mary helps with cups, plates and a tea towel.
- Cal notices Maggie has not eaten.
- Neil appears alive and concerned near closing.
- Faye receives the death call.

### Clues and Plants
- Mary restores cups, plates and towels to their places.
- The behaviour must appear ordinary and helpful.
- Neil's vase must not be described as a future murder weapon.
- The jam material is a mini-mystery seed, not part of Neil's murder.

### Character Knowledge
Maggie knows:
- Neil bought her ugly vase.
- Faye and Iris have an unresolved jam-related tension.
- Mary is close to Cal.

Maggie does not know:
- Mary will kill Neil.
- Why Mary resents Neil.
- What happened to Mary's father.
- That Mary's domestic habits will matter.

### Guardrails
- The Too-Much is observation, not mind-reading.
- Maggie can see avoidance and object placement, but not secret motives.
- Keep Maggie sympathetic.
- The public mistake must be survivable, not cruel.
- Do not villain-signal Mary.
- Do not ominously foreshadow Neil's death.
- Cal understands Maggie's attraction; he is not oblivious.

- **Because:** ch 04 — opening day gathers the full cast the investigation will need.
- **Opens:** q-neil-death — who killed Neil?
- **Closes:** q-opening-ready
- **M:** the death arrives; the mystery begins.
- **R:** Cal notices Maggie's overload.
- **Hook:** q-neil-death — [cliffhanger] Faye receives the death call.
```

Rules:

- **`[type: …]`** in the title selects the band from `length-profile.md`
  (existing mechanism, unchanged). `[long: reason]` remains a recorded override.
- **Required Beats** are one line each: an event, no staging, no location, no
  word target. The discipline is **form, not count** — a quiet chapter has
  three, a set-piece may earn ten. A beat is a moment the book breaks without.
- **Character Knowledge** includes the authored **does-not-know list** — the
  chapter's spoiler boundary, made explicit for `inspector-continuity` and
  `inspector-fairplay` to check the page against. The knows-list is
  cross-checkable against the continuity ledger; the does-not-know list is
  authorial and cannot be derived.
- **Clues and Plants** carries both the plants and the authored anti-spotlight
  guidance ("must appear ordinary and helpful"). At packet-assembly time the
  ledger's machine clue IDs are merged in (§5).
- **The wiring footer** (`Because / Opens / Closes / Carries` plus the
  per-track `M`/`P`/`R`/`B` rows / `Hook`) is machine-read by the nine tension
  checks, at the foot of the block, beneath Guardrails. It is the **same
  bulleted-bold field-per-line syntax the wired-outline convention already
  uses** (`- **Field:** value`, one field per line, q-slugs — never thread
  letters — in Opens/Closes/Carries, `[cliffhanger]`/`[promise]` bracketed
  onto the Hook line) — a bare `Because: …` / `Opens: x. Closes: y.` prose
  line is invisible to `penny_wiring.py`'s `FIELD_RE`, not merely a stylistic
  variant of it.
- **NO `### Scene` sections.** The container that drifted no longer exists.

## 4. The prose map (Pass 1 output — replaces the brief)

`input/book-NN/maps/ch-MM.md`. Canonical example (showrunner-authored, same
chapter):

```markdown
# Chapter 5 Prose Map

## Scene 1 — Before the Door Opens
Target: 350–450 words
Weight: Compressed support

Desire:
Maggie wants The Wheelhouse to look professionally ready without revealing
how badly she needs the launch to succeed.

Action:
She displays stronger work, rewrites prices and repeatedly moves one bowl.
Faye arrives with food and takes over practical hosting tasks.

Turn:
The room stops feeling like Maggie's private test and becomes a public place.

Carry forward:
Maggie has not eaten.

## Scene 2 — The Wheelhouse Fills
Target: 900–1,100 words
Weight: Primary anchor

Desire:
Maggie wants to be useful, charming and commercially successful.

Pressure:
Every visitor brings history Maggie does not understand.

Action:
Sales, food, Dot and Glad, Glaze, Cal at the edge, Mary helping with cups.

Clue:
Mary naturally returns cups and plates to particular positions and folds a
tea towel. Give this no emphasis beyond Maggie noticing competent help.

Turn:
Maggie's observations improve sales and earn social approval.

## Scene 3 — The Jam Border
Target: 700–850 words
Weight: Primary emotional anchor

Desire:
Maggie wants to keep the room's pleased attention.

Pressure:
Faye and Iris's physical avoidance creates an obvious social pattern.

Action:
Maggie makes a clever joke about where the jam may safely sit.

Result:
The room laughs.

Ethical turn:
Faye's look tells Maggie the observation was accurate but not hers to spend.
Maggie redirects before revealing the deeper wound.

## Scene 4 — Care Misread
Target: 400–550 words
Weight: Support

Action:
Mary quietly restores the room.
Glaze creates a distraction.
Cal tells Maggie to eat.

Turn:
Maggie interprets concern as judgement because she is ashamed and overloaded.

## Scene 5 — The Call
Target: 500–650 words
Weight: Secondary anchor and chapter hook

Action:
The event thins out. Neil appears briefly and recognises Maggie's overload.
He advises her to stop.

Turn:
Faye's phone rings. She goes still. Neil has been found dead.

Closing image:
The Wheelhouse changes from a shop full of opening-day evidence into the
place where death first enters Maggie's new life.
```

Rules:

- The machine parses only: `## Scene N — Title`, `Target: A–B words`, `Clue:`
  presence, and the coverage lines below. **All other field names
  (Desire / Pressure / Action / Turn / Result / Ethical turn / Carry forward /
  Closing image / …) are open vocabulary, used selectively** — Scene 4 needs
  only Action and Turn, so that is all it has.
- **`Weight:` is free descriptive text for the drafter** ("Primary emotional
  anchor", "Compressed support") — not an enum, not priced by class. The
  one-anchor rule is dead: a chapter may have an action peak, an emotional
  peak, and a hook peak. The **targets** carry the hierarchy; the machine reads
  only the numbers.
- **Targets are authored** (proposed by the map-maker, approved/edited by the
  showrunner) — `penny_length` validates them against the band, it no longer
  computes them.
- **Coverage lines** make beat/clue coverage deterministic: each scene may
  carry `Beats covered: 2, 7` (indices into the packet's Required Beats list,
  1-based, in list order) and clue IDs in its `Clue:` line. `map_check`
  verifies total coverage (§6). The map-maker writes these; the showrunner's
  approval covers them. (The canonical example above was authored before the
  coverage mechanism existed and omits them; the test-fixture version of this
  map adds `Beats covered:` lines and a clue ID — a map without them fails
  `dropped-beat`/`unscheduled-clue` by design.)
- The map file is stamped `built_from_packet: <sha256>` in frontmatter.

## 5. The packet (deterministic assembly — no LLM)

`packet_assemble.py NN MM` writes `input/book-NN/packets/ch-MM.md`:

1. **The chapter's outline block, verbatim** (all §3 sections including the
   wiring footer).
2. **Merged into Clues and Plants:** every ledger clue whose `plant_chapter`
   is this chapter, with its machine ID and fair-play description, from the
   locked `series/whodunit/book-NN.yaml`. (Authored anti-spotlight guidance
   from the block stays alongside.)
3. **Appended — Continuity Extracts:** `canon-core.md` (always) + the
   continuity entries named in the block + their one-hop `links`. Nothing more:
   the packet is the curation boundary — future chapters, unplanted clues, and
   other characters' secrets stay out.
4. **Appended — Standing series guardrails:** an authored series-level block
   (e.g. Australian spelling, outsider narration) attached to every packet
   automatically so it is always present and never drifts per chapter. Home:
   `config/series-guardrails.md`, overlay-resolved; absent file → section
   omitted with a named note in the packet.
5. **Appended — Word budget:** the band resolved from `length-profile.md` via
   the `[type:]` flag.
6. Frontmatter stamps: `built_from_outline: <sha256>`,
   `built_from_whodunit: <sha256|none>` (absent ledger is stamped `none`; a
   ledger appearing later makes the packet stale — same contract as briefs).

Staleness chain: outline or whodunit edit → packet stale → map stale (its
`built_from_packet` no longer matches) → `preflight draft` refuses until
`/map-chapter` is re-run. **A check that can silently vanish is not a check**:
every refusal is by name.

`packet_assemble.py` refuses an unlocked book (obligations come from the sealed
ledger). Completeness test: **the map-maker never needs to open another file
and can never blame a missing fact for a bad map.**

Deliberately NOT in the packet: scene divisions and per-scene targets (the
map's job); the rest of the book (slice discipline); the previous chapter's
final ~300 words (attached at **draft** time by `/draft-chapter`, so packets
don't go stale on upstream draft revisions); `mystery-solution.md` (a drafter
input, not a packet element).

## 6. Deterministic checks

**`map_check.py NN MM`** (new; run by `/map-chapter` after approval and by
`preflight draft`). Named findings, each fail-loud:

| finding | predicate |
|---|---|
| `band-mismatch` | scene target ranges cannot sum into the chapter's band: `Σmin > band_max` or `Σmax < band_min` |
| `starved-scene` | a scene's `Target` max is below the profile's `min_scene_words` floor |
| `dropped-beat` | a Required Beat index appears in no scene's `Beats covered:` |
| `unscheduled-clue` | a packet clue ID appears in no scene's `Clue:` line |
| `duplicate-beat` | a beat index claimed by more than one scene |
| `unparseable-target` | a scene without a parseable `Target: A–B words` line |

**`tension_check.py` re-base:** `overloaded-chapter` loses its scene-weight
basis (weights no longer exist in the outline) and re-bases on countable
outline facts: `len(Required Beats) + clues planted + questions opened/closed +
tracks advanced` vs the genre beat sheet's `obligations.max_per_chapter`. The
cozy beat sheet's cap number must be retuned for the new count basis (genre
data change, showrunner-owned). The check remains waivable and remains
skipped-by-name when its inputs are missing.

**`penny_length.py`:** `band_for` unchanged. `scene_budgets` (the generator)
is deleted; a new validator implements the `band-mismatch`/`starved-scene`
arithmetic. Length-profile schema v2: `band_default`/`band_<type>` unchanged;
`weight_<class>` and `min_<class>_words` are **retired** (tolerated if present,
ignored with a named note); new key **`min_scene_words`** (single floor for any
scene). README schema section updated to match.

## 7. Command surface

**`/map-chapter NN MM`** (new; replaces `/build-briefs`):
1. Resolve series root; require the lock (packet needs the sealed ledger).
2. `packet_assemble.py NN MM` → write the stamped packet.
3. Dispatch **`map-maker`** (model: `plot_model`, defaulting to
   `drafting_model` — planning work, same routing as the workshop) with the
   packet. It proposes the full prose map, including targets and coverage
   lines.
4. Present to the showrunner. **The showrunner edits/approves; only the
   approved map is written** to `input/book-NN/maps/ch-MM.md`, stamped.
5. `map_check.py NN MM` — findings by name; the map is not consumable until
   clean (no waivers at map level; fix the map or the outline).

**`/draft-chapter NN MM`** (modified):
- `preflight draft` gains: fresh packet + fresh clean map when they exist.
- Drafter inputs become: the map (instruction), the packet (context), the
  previous chapter's final ~300 words (from `.final.md`, else `.draft.md`,
  else omitted with a note), `mystery-solution.md` + `reveal_chapter`, voice
  pack. The map's per-scene targets are the word contract; "do not pad" and
  `drafted_short:` conventions carry over unchanged.
- **Legacy fallback preserved:** a chapter with no map falls back to the raw
  outline section exactly as today (warn, never block) — nothing breaks
  mid-migration.

**`/expand-outline NN [MM]`** (repurposed): expands a skeleton chapter stub
into a **packet-format chapter block** (§3) — reads the solution to place
Clues/Plants and Knowledge honestly, never schedules a reveal beat before
`reveal_chapter`, and **never writes a `### Scene` section**.

**`/plot-book`** unchanged through the lock; its weave stage's chapter blocks
remain the wired skeleton stubs that `/expand-outline` fills out.

**`/build-briefs` is deleted** (command, and the weigh-before-lock two-phase
dance with it — the lock now covers what it always covered, and maps are
cleanly post-lock, per chapter, just-in-time).

## 8. Agents

- **`map-maker`** (new; replaces `brief-weigher`): proposes the complete prose
  map from the packet — scene divisions, targets, weights-as-prose, selective
  fields, coverage lines. Proposes only; the showrunner decides. Never edits
  the outline, never writes ledgers or certificates.
- **`outline-expander`** (rewritten): emits packet-format blocks, never scenes.
- **`drafter`** (inputs updated per §7; rules unchanged).
- **`brief-weigher` is deleted.**

## 9. Deletions and survivals

Deleted: `### Scene` sections in outlines; `brief_render.py`'s renderer and
reference-extract surgery; the one-anchor rule; the weight enum and per-class
pricing; `brief-weigher`; `/build-briefs`; the weigh-before-lock seam;
`input/book-NN/briefs/` (existing briefs in the live series become historical
artifacts — `preflight draft` stops consulting them).

Survives untouched: the plotting workshop and its save points; the lock as an
out-of-band certificate and its delete-and-re-mint re-planning flow; the eight
wiring-based tension checks; the whodunit ledger; the five isolated inspectors
+ developmental editor + review gate; clear-dev; finalize; assemble; beta.
Independence/isolation/reader-simulation posture is untouched — there is still
no solution-blindness.

Reused in new clothes: staleness stamping (`penny_meta` frontmatter hashes);
the obligations-from-ledger merge; `band_for`; the `[type:]`/`[long:]` title
flags; the `- None.`-style explicitness conventions.

## 10. Book-01 migration (operational sequence, series-side)

1. Redraw `outline.md` into packet-format blocks — 27 → ~40 short chapters,
   showrunner's call per chapter, mining the old six-scene expansions as
   quarry. (Ratified example: old ch-1 splits into "The Wheelhouse" — arrival,
   unlock, missing key — and "The First Right Piece" — Cal, shelves, mug; the
   3,802-word draft was two chapters wearing one number.)
2. Renumber the whodunit ledger's `plant_chapter`s and `reveal_chapter`.
3. `rm .penny/locks/book-01.mystery.lock` → `preflight lock-mystery 01`
   (documented re-planning flow; `overloaded-chapter` prices the new blocks).
4. `/map-chapter` + draft one chapter at a time; the three existing drafts are
   salvage material for the chapters they map onto.

The engine work (this spec) ships first; the migration is showrunner-paced work
in the series repo and is not part of the implementation plan.

## 11. Out of scope

- New-series onboarding (the front-loaded config homework) — separate
  brainstorm, separate spec.
- The length/compression companion (Pass 3B: `length_check.py`,
  `/compress-chapter`, word count as `/review-chapter`'s first step) — still
  deferred; its "preserve-list" and patch-vs-full-revision ideas from the
  triple-pass doc fold in when it is specced.
- Sampling-temperature control per pass (LM Studio route already has it;
  no engine-wide mechanism).

## 12. Testing

TDD against `tests/fixtures/`: new packet-format outline + map fixtures
(chapter 5 above is the canonical pair); `packet_assemble` (slice, merge,
stamps, `none`-ledger, refusal on unlocked book, missing-guardrails note);
`map_check` (each named finding + clean pass); `penny_length` validator;
`tension_check` re-base (+ skip-by-name when beats absent); `preflight draft`
staleness chain (outline→packet→map); legacy fallback (an old-format book
drafts exactly as before — the stop-everything invariant transfers to
*unmigrated* books). Delete tests only for deleted machinery; the suite stays
green throughout.
