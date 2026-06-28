# Design — Series Arc Doc

**Date:** 2026-06-28
**Status:** approved

## What

A new writer-authored planning-anchor file: `input/series/series-arc.md`.

Thirteen stubs — one `## Book N` section per book — holding 1–2 sentence premises. Blank placeholder (`<!-- blank -->`) where no idea exists yet. No structured fields, no frontmatter, no thread tracking. Engine never reads this file.

## Why

The series-bible (`input/series/series-bible.md`) covers what stays true always (character rules, gift rules, tone, series promise). It has no per-book breakdown beyond Book 1. The arc-ledger (`series/arc-ledger.md`) tracks thread open/advance/resolve rows but is a machine-read structured table — not a place for prose premises.

A planning-anchor doc is missing: somewhere to park rough book ideas so they aren't lost, without pressure to lock or complete anything.

## Format

```markdown
## Book N — *[optional working title]*
[1–2 sentence premise: murder setting/event, motive shape, community backdrop.]

## Book N+1
<!-- blank -->
```

## Location

`input/series/series-arc.md` — swappable writer data, same tier as the series-bible. Not read by any script or agent.

## Out of scope

- Thread open/advance/resolve tracking → `series/arc-ledger.md`
- Series rules, character rules, tone → `input/series/series-bible.md`
- Any per-book mystery design (killer identity, clue schedule) → `series/whodunit/book-NN.yaml` + `/plan-mystery`
