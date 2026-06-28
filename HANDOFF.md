# Handoff — Penny / main
Saved: 2026-06-28 | Type: build

## Where things stand
Two pieces of work shipped this session, plus one design parked:

1. **Developmental-editor review role — SHIPPED + PUSHED.** A context-rich, per-chapter
   craft read that runs at review time on the draft; advisory toward the gate (never
   `^BLOCKING`, never flips PASS/HOLD) but a hard precondition for finalize via a
   `clear-dev` certificate bound to the draft's sha256. Spec → plan → 9 TDD tasks →
   review → fix wave. (Pushed earlier at HEAD `ab65cf2`.)

2. **Book-01 suspect-arc restructure — the "Cal false lead" — COMPLETE on main.** The back
   half went from a serial suspect fade-out to a three-stage collapse-and-converge:
   dead-end (Saffron + Beryl both fizzle, ch 17) → Cal emerges as a real suspect (ch 19;
   evidence converges, Maggie disciplines herself and seeks proof, not accusation) → Cal
   clears on two independent proofs = Mary converges (ch 20; the precision habit was hers,
   she raised him). ch 24: Maggie admits she suspected him. Edited `input/book-01/outline.md`
   + `series/whodunit/book-01.yaml`; mystery lock re-minted. Spec → plan → 5 tasks → opus
   whole-branch review → fix wave. 273 tests green, fairplay 0 blocking.

3. **Ghost / bad-marriage motivation (John Truby "ghost") — PARKED mid-brainstorm.** The
   idea: make the divorce an active haunting that motivates Maggie (root of her
   weakness/approval-hunger), not ambient backstory. I offered three "ghost shapes"
   (he weaponized her seeing [recommended — ties to the Too-Much]; he made her art small;
   she stopped seeing to survive it); the user wanted to **clarify the question first** and
   hasn't picked. Resume by asking what they want to clarify, then settle the ghost's shape.

## Git state
- Branch: `main`. The false-lead work is committed (`98a3e0d`..`c4e4c50`, 7 commits incl
  spec + plan) but **unpushed**. The dev-editor docs (`README.md`, `CLAUDE.md`) + this
  HANDOFF are being committed now and pushed with everything.
- Tests: `python3 -m pytest` → **273 passed**. fairplay 0 blocking; book-01 mystery lock present.
- Untracked `.ghost.swp` is the user's own vim swap for a `ghost` working file — leave it.
- `.superpowers/sdd/` and `.penny/` are gitignored runtime state.

## Next actions
1. **Resume the ghost brainstorm** (item 3) — ask the user what they wanted to clarify about
   the ghost-shape question, then design it. It threads through the Personal track and the
   Too-Much; it is a separate spec from the false lead.
2. **Calibration for the dev editor** (still not done): run `/review-chapter` on finalized
   ch 01/02 — it should surface the 4 known first-draft craft issues; then a `drafter`
   revise pass. ⚠️ Needs a reachable non-drafting model or `/review-chapter` now HALTS.
3. **Draft the restructured chapters** through the normal pipeline when ready (the outline +
   ledger now describe the new arc; drafter notes are logged in the SDD ledger for ch 16/17/20).
4. Eventually resume **Phase 6** (per-book assembly + final read + revision-priority report).

## Watch out for
- **Deferred ledger note (pre-existing, not from this work):** `series/whodunit/book-01.yaml`
  `clue-car-on-street` has `plant_chapter: 11`, but the blue-green car is narratively planted
  in ch 9 (Dot & Glad) and payoff is listed 23. Not a regression; reconcile when next touching
  the car thread.
- **Re-planning a locked mystery = delete the lock, edit the yaml, re-run `preflight
  lock-mystery 01`.** Never hand-edit a "locked" field; the lock is an out-of-band cert.
- **Dev-editor advisory invariant** is load-bearing and test-pinned: a `kind: developmental`
  verdict must never add a `^BLOCKING:` line. Two distinct hash keys: report
  `reviewed_draft_sha256`, cert `cleared_draft_sha256`, both compared to live `draft_sha256()`.
- Finalized ch 01–02 prose is untouched; the restructure only re-times resolutions from ch 10+.
