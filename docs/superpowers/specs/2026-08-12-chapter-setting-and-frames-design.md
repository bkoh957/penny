# Chapter setting and chapter frames in the cut plan

Date: 2026-08-12
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Extends `2026-08-03-story-source-layer-design.md` (below, "the
source-layer spec") and `2026-08-04-chapter-direction-and-guardrails-design.md`.

## 1. Why

Two facts about a chapter have never had a home, so both are decided at generation time
by whoever is writing the sentence.

**1.1 — Nothing says where a chapter happens.** The cut emits ten sections per chapter
(`story_cut.py:371-446`) — Summary, Purpose, Starting/Ending State, Reader-Facing Shape,
Required Beats, Clues and Plants, Character Knowledge, Guardrails, Chapter Structure,
Track Movement. None of them names a room, a time of day, or the weather. The drafter
receives the whole setting pack as context and picks. That is a plotting decision being
made one chapter at a time by an agent that cannot see the book.

**1.2 — Nothing says how a chapter opens or closes.** The genre conventions require
chapter-end hooks and `tension_check`'s `broken-hook` verifies that a *question* stays
open, but a question staying open is wiring, not an ending. Nothing records that this
chapter should land on a cliffhanger, or an irony, or a promise of action — and the
opening and the closing are the two sentences a reader actually decides on.

Both belong to the same moment: **the cut**. Neither can be authored in `story.md`,
because chapters do not exist until beats are grouped, and an ending only means something
once you know where the chapter stops.

## 2. Where these live, and why not in `story.md`

The source-layer spec's division is that `story.md` carries what the author decides about
the *story* — what happens, in what order, to whom — and the cut derives everything that
is a fact about *chapters*. Setting and frames are chapter facts:

- A setting could in principle be tagged per beat with a fifth sigil. **Rejected.**
  Working out where scenes happen is part of working out how beats group into chapters,
  and doing it a beat at a time forces the decision before the information exists. It
  also puts 150 more tags in a file whose value is that it has no surface for
  boilerplate.
- An opening and a closing cannot be beat properties at all — they are properties of a
  boundary.

So all three fields are authored in `input/book-NN/cut-plan.md`, beside `Beats:`,
`Summary:`, `Compress:` and the track rows. They are proposed by `chapter-cutter`,
edited and approved by the showrunner, and consumed by the cut.

**A chapter may hold more than one setting.** Chapters move. Each setting is bound to a
range of beats, using the same positional numbers `Beats:` already uses — the numbers
`misnumbered-beat` guards (`e58c60f`). Binding to beats rather than listing places in
order is what keeps the *transition point* — when they leave the studio — out of the
drafter's hands; a bare ordered list would move the place upstream and leave the moment
downstream.

## 3. Format — the cut plan

```markdown
## Chapter 07 — The Tin in the Tide
- **Beats:** 22-25
- **Summary:** <one line; this is what the story-at-a-glance view renders>
- **Compress:** <what this chapter should spend few words on>
- **Setting:**
  - 22-23 — the pottery studio, late afternoon
  - 24-25 — the harbour road, dusk, rain coming in off the water
- **Opening:** The kiln door still warm and the studio empty behind her.
- **Closing (promise of action):** She pockets the tin and turns for the harbour.
- **M:** <how the mystery track moves here>
```

**`Setting`** is the one nested field, because it is a list. Each sub-item is
`<beat range> — <prose>`. The range accepts the same syntax as `Beats:` (`22-23`, `24`,
`22,24-25`), reusing `penny_story._expand_beats`. The prose is
**place, time** with an **optional condition** after: `the pottery studio, late
afternoon` or `the harbour road, dusk, rain coming in off the water`. Nothing parses
inside that prose — it is one string written for a person. The comma is a reading
convention, not a delimiter, and no check enforces it.

Time is included because it is a continuity fact nothing in Penny records today, so each
chapter's drafter invents its own clock and `inspector-continuity` reads a ledger slice
that never captured one. Condition is optional because pinning how a room *feels* is the
draft's job; specify it on the chapters where weather is doing dramatic work and stay
quiet elsewhere.

Places should be named the way the series setting pack names them, so the studio is the
same studio across thirteen books. **This is a convention, not a check** — there is no
locations ledger to validate against (`series/continuity/` holds only `characters/`), and
building one is out of scope here.

**`Opening`** is one line of craft guidance for the chapter's first sentence or image.
It carries no kind. It is deliberately *not* a link to an earlier chapter: an earlier
draft of this design had the intro name "the previous relevant chapter" and feed the
`Because:` wiring, and that was cut — the intro is a strong opening, and `Because:` stays
derived as it is today.

**`Closing`** is one line, with its **kind in the key**: `cliffhanger`, `irony`, or
`promise of action`. The kind sits in the key rather than the prose so it is
machine-visible without the sentence having to announce itself.

## 4. Format — the emitted chapter block

`### Setting` is emitted directly after `### Chapter Summary`, because where and when
grounds every section under it. `### Opening` and `### Closing` are emitted directly
after `### Reader-Facing Shape`, which is already the section about how the chapter lands
on a reader.

```markdown
### Setting
- Beats 1-2 — the pottery studio, late afternoon
- Beats 3-4 — the harbour road, dusk, rain coming in off the water

### Opening
The kiln door still warm and the studio empty behind her.

### Closing
Promise of action — she pockets the tin and turns for the harbour.
```

Beat numbers are renumbered **chapter-locally**, matching `### Required Beats`, which
already lists this chapter's beats rather than the book's. The closing's kind is rendered
as a prose lead-in rather than a parenthetical key, because the emitted block is read by
agents and a reader's copy, not parsed back.

## 5. Checks

Split by what each checker asks.

### 5.1 `story_cut.py` — is the plan coherent (five new blocking findings, no waivers)

Sixteen findings become **twenty-one**. Consistent with the existing sixteen: named,
loud, and unwaivable — fix the story or the cut plan (source-layer spec §8).

| finding | fires when |
|---|---|
| `beat-without-setting` | a beat in the chapter is covered by no setting range |
| `overlapping-setting` | two ranges in one chapter claim the same beat, so where it happens is ambiguous |
| `setting-outside-chapter` | a setting range names a beat this chapter does not hold |
| `missing-chapter-frame` | the chapter has no `Opening`, or no `Closing` — one finding per missing field, naming which |
| `unknown-closing-kind` | the kind is not one of the three |

**Adoption is all-or-nothing per cut plan**, exactly as beat numbers are all-or-nothing
per `story.md` (`e58c60f`). If **no** chapter in `cut-plan.md` carries `Setting`,
`Opening` or `Closing`, the plan predates this design and none of the five findings fire.
If **any** chapter carries any of them, **every** chapter must carry all three, and all
five findings are live.

The alternative — checking each chapter independently — was rejected because it makes a
half-adopted book the quiet default: the chapters you happened to fill in are governed and
the rest silently return the decision to the drafter, which is the failure this design
exists to remove. All-or-nothing makes adoption a single visible act. It also lets book
01's existing proposed cut plan run today, and lets `chapter-cutter` — which emits all
three for every chapter from now on — make adoption automatic for every new book.

`setting-outside-chapter` earns a separate name from `beat-without-setting` because the
repair differs: one means you forgot a beat, the other means you moved a chapter boundary
and left the settings behind. That second case is the routine one — every boundary move
in `cut-plan.md` shifts beats between chapters and strands the ranges.

`missing-chapter-frame` blocks rather than advises: a missing closing hands the ending
back to the drafter, which is the decision this design exists to move upstream.
`unknown-closing-kind` blocks because an unparsed kind silently disarms §5.2.

**Accepted cost, recorded deliberately.** These five fire on mechanical mistakes and add
nothing to the system's ability to judge whether a book is good — the linker layer's known
limit. What earns this change is §3's three fields, which are the first in the system to
record where a scene happens and how it lands; the findings are the seatbelt on that. If
after several books only `beat-without-setting` has ever fired, collapse the three setting
findings into one `setting-coverage` then, on evidence.

### 5.2 `tension_check.py` — does the book vary (one new waivable check)

Nine checks become **ten**. `monotonous-closings` fires when more than
`closings.max_same_kind_run` consecutive chapters end on the same kind. Five cliffhangers
in a row is a fact about the whole book rather than a defect in any one chapter, which is
what `tension_check` is for, and it is waivable with `--waive monotonous-closings:"…"`
recorded on the lock certificate.

The threshold is a **genre** number, declared in the active genre's `beat-sheet.yaml`
beside `obligations.max_per_chapter`:

```yaml
closings:
  max_same_kind_run: 3
```

Resolved through `penny_genre.py beat-sheet`, never a hardcoded filename. A check that
**cannot run** — the key is absent, or no chapter block carries a `### Closing` — prints a
named note and the lock certificate records `skipped: monotonous-closings — <why>`,
following `overloaded-chapter`'s existing precedent exactly. An outline with no `###
Closing` anywhere is the legacy shape (book 01's hand-authored outline) and is never
checked, so it still locks as before.

## 6. Alignment — generation, modification, consumption

### 6.1 Generation — `agents/chapter-cutter.md`

Its "Output format — exactly this" block gains the three fields. The agent gains two
inputs it does not have today:

- **The series setting pack**, resolved through the config overlay. It cannot propose
  *the pottery studio, late afternoon* without knowing the town's places. Today it reads
  `story.md` (including `## Chapter Direction`), the genre beat sheet and the macro
  structure, and nothing else.
- **`config/story-craft/writing-chapter-frames.md`**, a new craft doc: what distinguishes
  a cliffhanger from an irony from a promise of action, why a run of identical closings
  goes dead, and what makes an opening sentence strong. It sits beside `writing-beats.md`
  in the directory already read as a **union across all three config tiers**, so a genre
  pack can extend it without copying it. The cutter lists it the same way `story-author`
  does: `penny_paths.py resolve-dir story-craft`.

The engine ships the craft doc as a `config/` default, matching `writing-beats.md`.

### 6.2 Modification — `commands/plot-book.md`, cut stage

The runbook already presents the proposal and writes only the approved plan (line 220).
The new fields are part of what the showrunner approves. The runbook must state the drift
hazard by name: **moving a chapter boundary moves beats between chapters and leaves the
setting ranges behind** — re-running the cut then reports `setting-outside-chapter` and
`beat-without-setting` together, and both are repaired in `cut-plan.md`, not `story.md`.

### 6.3 Consumption

- **`penny_story.parse_cut_plan`** learns `Setting` (nested, ranged), `Opening`, and
  `Closing` with its kind. `_CUT_TRACK_RE` requires exactly one capital letter before the
  colon, so no new key collides with a track row.
- **`story_cut.emit_outline`** emits the three sections in §4's positions.
- **`story_cut.check_story`** gains §5.1's findings.
- **`packet_assemble.py` needs no change.** It inlines the entire chapter block
  (`packet_assemble.py:203`), so the new sections reach the packet for free.
- **`agents/map-maker.md`** — `### Setting` is the strongest available signal for where
  scenes break, since a location change is usually a scene boundary; `### Opening` and
  `### Closing` belong to the first and last scene. Stated explicitly, or the map-maker
  re-derives boundaries from beats alone and the setting ranges do no work.
- **`agents/drafter.md`** — the Opening and Closing are instruction, not context.
- **`scripts/plot_stage.py`** — `_KEEP_SUBSECTIONS` admits `setting`, `opening` and
  `closing`. The reader's copy is an **allowlist**, so a section not named here is
  invisible to the fan by construction. All three are admitted deliberately: setting is
  what a reader experiences, and the closing line is what put-down risk is made of, so
  hiding it would waste the read-back. Existing truncation at `reveal_chapter` still
  applies, so a late closing cannot leak the solution.
- **`scripts/book_status.py`** reads the plan only to count chapters — no change.

### 6.4 Documentation

- **`CLAUDE.md`** — the source-layer section states the sixteen findings by name; it
  becomes twenty-one with the five above. The `tension_check` list of nine named checks
  becomes ten. The `config/story-craft/` note gains the new craft doc. The `story.md`
  paragraph gains a sentence saying setting and frames are cut-level, *not* beat-level,
  and why.
- **`README.md`** — cut-plan format.

## 7. Out of scope

- A locations ledger under `series/continuity/locations/`, and any check that setting
  prose names a known place.
- Any change to `Because:`, `### Starting State`, or `orphan-chapter`.
- A kind taxonomy for openings.
- Migrating book 01, whose outline predates the cut entirely.

## 8. Testing

Test-first against `tests/fixtures/`, per the repo convention.

- `parse_cut_plan`: nested settings with range/list/single-beat forms; `Closing` with each
  of the three kinds; a plan with none of the three fields (legacy) parses unchanged.
- `check_story`: one test per §5.1 finding, plus a clean plan producing none of them, plus
  a legacy plan carrying none of the three fields producing none of them, plus a plan
  carrying them on one chapter only producing `missing-chapter-frame` on the rest.
- `emit_outline`: section presence and position; chapter-local renumbering; a plan without
  the fields emits no empty sections.
- `tension_check`: `monotonous-closings` fires above the threshold and not at it; absent
  genre key records `skipped:`; an outline with no `### Closing` is never checked.
- `plot_stage.readers_copy`: the three sections survive the allowlist; nothing else new
  does.
