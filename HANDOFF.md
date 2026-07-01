# Handoff — Penny / main
Saved: 2026-06-29 | Type: build

## What we're building
Two distinct threads are live and **uncommitted**:
1. **NEW this session (DONE, uncommitted):** the drafter now stamps a `drafted_on: <YYYY-MM-DD>`
   date into draft frontmatter, and all five existing drafts (ch-01..05) were backfilled.
2. **STILL PENDING from prior handoff (NOT started this session):** reconcile the two stale
   sealed mystery files (`series/whodunit/book-01.yaml`, `output/book-01/mystery-solution.md`)
   to the outline and re-mint the lock. See "Next actions §B".

## Git state
- Branch: `main` (pushed through `6ff1272`)
- Uncommitted changes:
  - `.claude/agents/drafter.md` — Outputs + step 4 require `drafted_on`
  - `.claude/commands/draft-chapter.md` — new step 5 captures `draft_date=$(date +%F)`, passes
    to drafter; following step renumbered to 7
  - `output/book-01/chapters/ch-01..05.draft.md` — backfilled `drafted_on` stamps
  - `input/book-01/outline.md` — **pre-existing M, NOT mine** (user edited since prior handoff;
    working SHA `96c502d` ≠ HEAD `25bfe99`; prior handoff wrongly said it was clean)
  - `HANDOFF.md` — this file
- Deleted this session: stray `output/ch-01.draft-sonnet.md` (superseded sonnet draft, was untracked)
- Last commit: `6ff1272` feat(book-01): expand full outline to scene-breakdown (all 29 chapters)
- Tests: **not run this session.** Drafter change is additive-only (all consumers read frontmatter
  by single key via `parse_frontmatter(...).get("drafted_by")`, never a fixed key-set — verified
  by grep across scripts/ and tests/). Were green (273) at prior handoff.

## Next actions
### A. Finish the drafter-date thread (immediate)
1. Decide whether to commit thread 1 now. Suggested split: commit the drafter feature + backfills
   **separately** from the reconcile work (B), and leave `outline.md`/`HANDOFF.md` out of that commit.
   Suggested: `git add .claude/agents/drafter.md .claude/commands/draft-chapter.md
   output/book-01/chapters/ch-0{1..5}.draft.md` then commit.
2. (Optional) run `python3 -m pytest` to reconfirm 273 green before committing.

### B. Reconcile stale mystery files (carried over — re-verify against CURRENT outline first)
**The outline changed since the prior handoff (96c502d ≠ 25bfe99), so re-verify every line item
below against the current `input/book-01/outline.md` before applying — don't trust the old numbers blind.**
1. `series/whodunit/book-01.yaml`:
   - `clue-car-on-street`: plant_chapter 11 → **9** (planted via Dot & Glad, outline ch 9).
   - `clue-old-records`: plant_chapter 15 → **14** (Neil's papers, outline ch 14).
   - `rh-faye`: plant_chapter 13 → **12** (Faye raised+cleared, outline ch 12).
   - `rh-cal`: yaml plant ch 11 but real Cal head-fake is structural at **ch 19** — re-point to 19 or drop.
   - Beryl alibi grid already ch 17 ✓.
2. `output/book-01/mystery-solution.md` (sealed: true, drafter-invisible — safe to edit as showrunner):
   - Move keystone **click ch 19 → ch 20** (ch 19 is now the Cal head-fake).
   - Rewrite keystone mechanism as **transmitted precision**: room-reset habit points at Cal first
     (his trained precision), resolves to Mary because she raised Cal and taught him the habit
     (Cobber ch 20: "She made him who he is").
   - Fix internal inconsistencies: car payoff ch 23 (table) vs 20 (arc); Beryl demolished ch 14
     (table) vs 17 (yaml/outline).
3. Re-mint: `python3 scripts/preflight.py lock-mystery 01` (delete old stale lock first if required).
4. `python3 -m pytest` to confirm green.

## Decisions made this session
- **`drafted_on` field name** chosen to parallel `drafted_by`; ISO `YYYY-MM-DD` format.
- **Date sourced from the command, not the agent.** `/draft-chapter` computes `date +%F` and passes
  it in — the LLM agent can't reliably know today's date, so the stamp must be deterministic.
- **Backfill dates derived from git, not file mtime:** ch-01 = 2026-06-28 (Opus redraft `eb5a438`);
  ch-02 = 2026-06-22 (original add); ch-03/04/05 = 2026-06-26 (draft add). ch-04's 06-27 commit was
  a 5-line gate fix, NOT a redraft, so its draft date is the 06-26 add.
- **Reconcile = outline is source of truth** (carried over): conform yaml/solution.md to it, not vice versa.

## User preferences expressed this session
- Commit/push only when told. Work on `main`.
- Verify a delete target before removing it (did so: confirmed the sonnet draft before `rm`).

## Key files right now
- `.claude/agents/drafter.md`, `.claude/commands/draft-chapter.md` — drafter-date feature (DONE).
- `output/book-01/chapters/ch-01..05.draft.md` — backfilled (DONE).
- `input/book-01/outline.md` — source of truth for reconcile; **changed since prior handoff, re-verify**.
- `series/whodunit/book-01.yaml`, `output/book-01/mystery-solution.md` — STALE; fix per Next actions §B.
- `.penny/locks/book-01.mystery.lock` — minted against stale yaml; re-mint after §B edits.

## Watch out for
- **Nothing is committed.** Two unrelated threads are intermingled in the working tree — split the
  commits (A vs B) and keep the pre-existing `outline.md` edit out of the drafter-feature commit.
- **`outline.md` is dirty and not mine** — the user edited it; reconcile (§B) must be re-verified
  against the current text, not the prior handoff's chapter numbers.
- Fair-play planting on the page is already correct (ch 5/7/9 verified previously) — the drift is
  ONLY in the metadata files.
- `mystery-solution.md` stays `sealed: true` and drafter-invisible — don't let its content leak into
  drafter-visible files.
