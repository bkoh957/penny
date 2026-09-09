# Series-guardrail headings truncate every chapter block

Date: 2026-09-09
Status: design, approved in conversation, not yet planned
Supersedes: nothing. Applies upstream the same cure as
`2026-08-27-packet-extract-heading-collision-fix.md`, which fixed this collision class
in `packet_assemble.py` but never in the cut that writes the outline.

## 1. Why

`scripts/story_cut.py:1178` reads `config/series-guardrails.md` **raw** and hands the
whole file to `emit_outline(..., guardrails=guardrails, ...)`, which interpolates it into
every chapter's `### Guardrails` section. The file's own headings come along:

```
# Standing Series Guardrails — Pelican's Crook      <- H1, nested under a `- ` bullet
## C — Warmth beats are never scheduled as clues     <- column 0
## B — The map states ends, not sentences            <- column 0
## Standing                                          <- column 0
```

The three `##` headings land at column 0 in the emitted outline. A chapter block runs
from its heading to the **next `##`** (`scripts/penny_wiring.py:49-58`, `chapter_block`;
the same rule drives `parse_wired_chapters`). So every chapter block is **truncated at
`## C — Warmth beats…`**, and everything the cut emits after the guardrails —
`### Chapter Structure` (the `Opens:` / `Closes:` wiring) and `### Track Movement` —
falls outside its own chapter, into a `## Standing` pseudo-block that
`parse_wired_chapters` discards because its heading does not match `## Chapter NN`.

**The same file is interpolated raw a second time.** `packet_assemble.py:318-322` reads
`config/series-guardrails.md` and splices it at line 358 under the packet's own
`## Standing Series Guardrails` heading. Its `##` headings close that section
immediately, so the packet's guardrails section is **10 words** and the body leaks out as
three sibling top-level sections (`## C`, `## B`, `## Standing`). Any consumer reading the
guardrails by markdown structure gets an empty section. `_demote_headings` is defined in
that same file (line 117) and applied to continuity extracts — but not here.

This is not an authoring mistake. The affected outline carries `built_from_story`,
`built_from_cut` and `cut_output_sha256` — the engine wrote it, and will write it again
for every book cut through the source layer.

## 2. Evidence

Measured on the live series (`~/myBooks/pelicanscrook-series`, book 01, 35 chapters).

**The outline's heading census** — 141 top-level `## ` headings for a 35-chapter book:

| heading | count |
|---|---:|
| `## Chapter NN` | 35 |
| `## Standing` | 35 |
| `## C — Warmth beats are never scheduled as clues` | 35 |
| `## B — The map states ends, not sentences` | 35 |
| `## Solution` | 1 |

**The wiring is parsed away.** `parse_wired_chapters` finds all 35 chapters, and:

```
chapters parsed: 35 | has_wiring: False
```

against an outline containing 181 `Opens:` / `Closes:` / `**M:**` lines.

**The packet carries no wiring at all.** In `input/book-01/packets/ch-01.md`:

```
grep -c "Opens:\|Closes:\|### Track Movement\|### Chapter Structure"  ->  0
```

The drafter, the map-maker and the developmental-editor have never seen which questions
a chapter opens or closes, or what its tracks move — inside an 18,216-word packet.

**Ten deterministic checks are dark.** `check_tension` run directly against the outline:

```
wired: False   blocking: 0   notes: 0
```

so `orphan-chapter`, `dropped-question`, `phantom-answer`, `broken-hook`,
`chapter-coverage`, `dead-stretch`, `starved-thread`, `off-mark-beat`,
`overloaded-chapter` and `monotonous-closings` produce nothing. The lock certificate is
honest about it and nobody noticed:

```
book: 01
validated: fairplay+lexicon        <- not `fairplay+lexicon+tension`
```

**The packet's guardrails section is empty.** Section word counts for
`input/book-01/packets/ch-01.md`:

```
   10 words  ## Standing Series Guardrails   <- the whole section
  184 words  ## C — Warmth beats are never scheduled as clues
  196 words  ## B — The map states ends, not sentences
   43 words  ## Standing
```

**Duplication.** The guardrail body is 423 words (`## C` 184 + `## B` 196 +
`## Standing` 43). Interpolated into 35 chapter blocks that is **14,805 words**, in an
outline of 101,655.

## 3. Fix

Two changes in the cut, both narrow.

**3a. Demote the interpolated headings, at both sites.** Before the guardrail text is
spliced in, demote its embedded ATX (and setext) headings the way
`packet_assemble._demote_headings` already does for continuity extracts and canon-core.
An authored `##` inside a carried file must never be able to close the structure it is
carried into. The live call site is `packet_assemble.py:358` (the packet's guardrails section), where
`_demote_headings` is already defined in the same file at line 117 and simply not applied.
`story_cut.py:652` needs no demote once §3b lands, because it will no longer carry a
multi-line file into a chapter block at all — the guarantee there is an **invariant test**
(§5.4) rather than a second call to the helper. No shared module is required;
`scripts/penny_text.py` is prose primitives for the voice checkers and is the wrong home.

**3b. Stop interpolating the file per chapter.** The chapter-level `### Guardrails`
section is for *this chapter's* authored guardrails plus the derived series-guardrail and
reveal-chapter lines. The standing series guardrails are a global, constant file — the
packet already appends them once as `## Standing Series Guardrails`, which is the correct
home for exactly the reason the voice and genre packs are not embedded per chapter. Emit
a reference, not the body.

3b is what makes the outline parse correctly and removes the 14,805 words; 3a is what
makes the packet's own guardrails section non-empty. They fix two different sites of one
defect and are independently testable — do both, in either order.

### Rejected

- **Rewriting `config/series-guardrails.md` to use `###`.** Fixes one series' file and
  leaves the engine able to do this to the next one. The engine must be safe against any
  authored heading depth, which is the whole finding of the 2026-08-27 spec.
- **Teaching `chapter_block` to model where a chapter "really" ends** (e.g. resume after
  a known guardrail heading). This is the shape that already failed once —
  `2026-08-29-nested-cut-plan-field-hijack-fix.md` records that a guard modelling block
  membership was tried and a single blank line reopened the bug. The rule stays "the next
  `##` ends the block"; the cure is that carried content may not contain one.

## 4. Blast radius

`story_cut.py` writes `input/book-NN/outline.md`, which is stamped `cut_output_sha256`.
Existing outlines are **already on disk in the broken shape** and the fix does not reach
back:

- Re-cutting is free while the stamp still matches (`outline-modified-since-cut` does not
  fire), so a book on the source layer joins by re-running the cut.
- Re-cutting rewrites `plant_chapter:` in `series/whodunit/book-NN.yaml`, so the mystery
  lock must be deleted and re-minted afterwards — the ordinary re-plan sequence.
- Book 01's outline is cut-produced and re-cuttable. Expect its lock to move from
  `validated: fairplay+lexicon` to `fairplay+lexicon+tension`, and expect
  `tension_check` to have findings to report for the first time (see the companion spec).

Downstream, once the chapter block is whole the wiring footer is inside the slice and
flows into the packet by itself — but `packet_assemble.py` still needs its own §3a fix for
the guardrails it appends directly. Existing packets are stamped and consumed by stamped
maps: re-assembling a packet changes its sha256 and invalidates that chapter's map, so
land this at a chapter boundary and re-run `/map-chapter` for anything mapped but not yet
drafted.

## 5. Test

Test-first against `tests/fixtures/`:

1. **`emit_outline` demotes carried guardrail headings** — a guardrails fixture
   containing `## X` and a setext heading produces an outline whose only column-0 `##`
   headings are `## Chapter NN` and `## Solution`.
2. **A cut outline round-trips as wired** — cut a fixture story + cut plan whose
   guardrails file carries `##` headings, then assert `has_wiring(parse_wired_chapters(...))`
   is True and each chapter block contains its own `### Chapter Structure`.
3. **The packet carries the wiring** — assemble a packet from that outline and assert the
   chapter section contains its `Opens:` / `Closes:` lines. This is the regression that
   would have caught the live defect.
3b. **The packet's guardrails section carries its body** — assemble a packet with a
   guardrails fixture containing `##` headings and assert `## Standing Series Guardrails`
   holds the whole body, with no sibling section introduced after it.
4. **The body is not duplicated per chapter** (3b) — the emitted outline contains the
   guardrail body zero times; a chapter's `### Guardrails` still carries its authored and
   derived lines.
5. **`tension_check` sees a cut outline as wired** — end-to-end, guarding the ten checks
   against going dark again.

`tests/test_runbook_arguments.py` and the existing `story_cut` finding tests must stay
green: this adds no finding and removes none — the roster stays at twenty-three.
