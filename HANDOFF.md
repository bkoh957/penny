# Handoff — Penny / main
Saved: 2026-06-28 | Type: build

## What we're building
Penny is a Claude-Code-native harness for a 13-book cozy-mystery series. This session
was focused on series shaping: creating a new planning-anchor doc (`input/series/series-arc.md`)
to capture per-book premises, and parking three unassigned book ideas the user surfaced.
No code/engine changes; pure writer-data work.

## Git state
- Branch: `main`
- Uncommitted changes:
  - `HANDOFF.md` (modified — this file)
  - `docs/superpowers/specs/2026-06-28-series-arc-doc-design.md` (untracked — new spec)
  - `input/series/series-arc.md` (untracked — new series arc doc)
- Last commit: `65a123b` plan(book-01): outline burst-beats — sting (ch1-18), ch19 pivot, ch29 name reclaim
- Tests: not run this session; last known state was 273 passed.

## Next actions
1. **Commit the two new files** (spec + series-arc) — user hasn't asked yet; hold until told.
2. **Continue populating `input/series/series-arc.md`** — user said "not sure which books these relate to" for the three ideas; they may have more. Ask if there are more rough ideas to capture before trying to slot any into numbered books.
3. **Ghost brainstorm (still parked)** — the John Truby "ghost" / bad-marriage motivation for Maggie was mid-brainstorm when the previous session ended; it was not resumed this session.
4. **Dev-editor calibration** — run `/review-chapter` on finalized ch 01/02 to surface known first-draft craft issues; still not done.
5. **Draft restructured chapters** (ch 10, 16–20, 24) through normal pipeline when ready.

## Decisions made this session
- **`input/series/series-arc.md` is writer data, not engine data** — the engine never reads it; it's a planning anchor only. Thread open/resolve tracking stays in `series/arc-ledger.md`; mystery design stays in `series/whodunit/book-NN.yaml`. WHY NOT extend the bible: the bible is reference material (rules, tone, character), not a premises list — mixing them muddles its purpose.
- **Unassigned ideas go in a holding section** at the bottom of series-arc.md rather than forcing a book number. Rationale: Tommy/Cal/parents ideas have sequencing logic (noted in file comments) that should inform placement later, not now.
- **Skipped writing-plans for this task** — implementation was a single markdown file; running writing-plans would have been overhead disproportionate to the work.

## User preferences expressed this session
- **Commit only when told; push only when told.**
- Minimum viable per-book entry: just the premise (1–2 sentences), no structured fields.
- Planning-anchor mode: capture ideas without pressure to lock or complete.

## Key files right now
- `input/series/series-arc.md` — NEW: the series planning anchor, 13 stubs, Book 1 filled, 3 unassigned ideas at bottom.
- `docs/superpowers/specs/2026-06-28-series-arc-doc-design.md` — NEW: spec for the above.
- `input/series/series-bible.md` — reference; §50 "arc across the series" is the prose-level series intent.
- `series/arc-ledger.md` — thread tracking; only Book 01 rows filled in.

## Watch out for
- The **ghost brainstorm is still parked** — if user mentions Tommy or the bad-marriage ghost, that's a separate spec (`2026-06-28-tommy-quill-ghost-design.md` already exists in specs/). Don't conflate with the new series-arc work.
- **Three unassigned ideas** have implicit sequencing logic captured in inline notes in `input/series/series-arc.md`: Tommy = mid-series (not Book 2), Cal accused = late-series (romance must have stakes), parents = c-internal-adjacent. Don't slot them without discussing.
- `series/arc-ledger.md` Books 2–13 rows are all blank — don't try to fill them from the series-arc doc automatically; the user decides when to formalise thread tracking.
- `.ghost.swp` in root — user's open vim swap file, leave alone.
