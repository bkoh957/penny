# Cozy-mystery genre conventions

The cozy-mystery genre: an amateur sleuth, a closed community, fair-play clue
planting, no on-page gore, warmth and comfort texture, a satisfying reveal.

## Conventions
- Amateur sleuth; no graphic violence or sex; small contained community; justice
  restored; balance of comfort and puzzle.

## Dual engine
- **A-plot:** the book's mystery (a death, solved by the end).
- **B-plot:** the protagonist's ongoing personal arc, threaded across the series
  via the arc-ledger. The arc's content and the series' book count are
  series-specific — declare them in the series folder, not here.

## Tracks

`genre.yaml` declares four, and `beat-sheet.yaml` sets how long each may go dark
(`max_dark_gap`). The letters mean:

| | track | goes dark for at most | notes |
|---|---|---|---|
| **M** | Mystery — the investigation advances | 2 chapters | write "None" for a deliberate rest chapter |
| **P** | Personal / internal — the sleuth's own arc | 4 chapters | |
| **R** | **Romance** / community | 4 chapters | **not** "relationships" generally — see below |
| **B** | Business — livelihood, premises, craft standing | 5 chapters | |

**R is the one that gets misread.** Read as "relationships", it silently becomes a
second community track and the romance thread starves while every row still looks
full — the check cannot catch this, because a row about who helped in the bakery is
a populated row. Community belongs in R, but a book whose R rows are only logistics
has dropped half the track. Per the dual-engine rule above, the personal thread is
what drives the next purchase; the romance inside it is usually what a cozy reader
means when they say they would buy the next one.

## Per-book rule
- The mystery **resolves**; a personal thread **does not** (drives the next
  purchase). Chapter-end hooks are mandatory.

> A series may also provide `config/genre-pack/cozy-mystery.md` as its active genre prose
> pack. Keep genre-general rules here; keep series-specific detail in the series folder.
