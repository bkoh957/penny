# Handoff — Penny / main
Saved: 2026-06-23 | Type: build

## What we're building
Running the per-chapter pipeline for Book 01 — review gate then finalize for Ch-01 and Ch-02. Both chapters have been drafted and reviewed; Ch-02 gated PASS; Ch-01 gated HOLD (one blocker now fixed). Next step is finalization.

## Git state
- Branch: `main`. HEAD `4d0cc79`.
- **Uncommitted changes:**
  - `output/book-01/chapters/ch-01.draft.md` — HR career fix applied (line 23: "She had been in HR for twenty years, the last eleven of them as a director.")
  - `series/continuity/canon-core.md` — updated: "twenty years in HR, latterly Director"
  - `series/continuity/characters/meg-quill.md` — updated: "Twenty years in HR, the last decade as Director"
- **Untracked:**
  - `output/book-01/chapters/ch-01.gate.md`
  - `output/book-01/chapters/ch-01.reviews/` (all 5 inspector verdicts + gate)
  - `output/book-01/chapters/ch-02.gate.md`
  - `output/book-01/chapters/ch-02.reviews/` (all 5 inspector verdicts + gate)
- Tests: 249 passing (nothing in scripts/ changed).

## Next actions
1. **Finalize Ch-01.** Run `/finalize-chapter 01 01` — the blocker (HR tenure mismatch) was fixed in the draft directly; the gate file still says HOLD but the fix is in place. You may need to re-run the gate first: `python3 -m scripts.review_gate output/book-01/chapters/ch-01.reviews` to confirm PASS, then finalize.
2. **Finalize Ch-02.** Run `/finalize-chapter 01 02` — gated PASS, no issues.
3. **Commit.** After both are finalized, commit: ledger fixes (canon-core, meg-quill), both drafts with gate + review dirs, both `.final.md` files.
4. **Draft Ch-03.** After Ch-02 is finalized, next chapter is Ch-03: Meg's first migraine; Dr Neil Hartigan introduced. Brief is in `input/book-01/outline.md` under Chapter 03.

## Decisions made this session
- **Meg's HR career corrected:** "Former HR director (twenty years)" was wrong — nobody holds Director level for 20 years. Changed to "Twenty years in HR, the last decade as Director." Draft sentence: "She had been in HR for twenty years, the last eleven of them as a director."
- **Ch-01 gate: HOLD then immediate fix.** Rather than re-running the full inspector panel for ch-01, the blocker was corrected in the draft directly. The next session should either re-gate ch-01 (fast, just re-runs `review_gate.py` on existing verdicts) or proceed straight to finalize (which runs `preflight.py finalize` and requires `gate: PASS`).
- **inspector-voice filename mismatch on ch-02:** The voice inspector wrote to `inspector-voice.md` instead of `character-voice.md`. Fixed by copying before gating. Watch for this on future chapters — the agent needs the output path specified precisely.

## AI-prose rubric calibration (Book 1 baseline)
Ch-01 ai-prose score: 4 (two rote-adjacent touches — Flag 1 HR dissociation "somewhere else", Flag 5 "Not happiness, not yet. Just the possibility of it." — neither blocking; final sentence "She did not close the door" rescues the ending).
Ch-02 ai-prose score: 3 (4 rote touches — 2×Flag 2 over-explains beats, 2×Flag 3 abstract where specific would serve. Specific candidates for line-edit: "there was something in her voice that made Meg think being always straightforward might be more complicated…" and "There was a particular ease to sitting next to someone who clearly had no agenda at all.").

## Key files right now
- `output/book-01/chapters/ch-01.draft.md` — HR career fix on line 23; ready for re-gate or finalize
- `output/book-01/chapters/ch-02.draft.md` — PASS gate; ready for finalize
- `output/book-01/chapters/ch-01.reviews/` — all verdicts present; gate says HOLD (pre-fix)
- `output/book-01/chapters/ch-02.reviews/` — all verdicts present; gate says PASS
- `series/continuity/canon-core.md` — updated this session; uncommitted
- `series/continuity/characters/meg-quill.md` — updated this session; uncommitted

## Watch out for
- **Ch-01 gate.md still says HOLD.** The fix was made to the draft after gating. To finalize, either re-run `python3 -m scripts.review_gate output/book-01/chapters/ch-01.reviews` (the continuity-drift.md verdict still says "BLOCKING" — so you'd need to re-run inspector-continuity too), OR check if `preflight.py finalize` reads the gate file directly. If it does, you'll need a fresh gate pass before finalize will accept it.
- **Cobber's dawn-sighting clue** — planted in ch-02: "Sometimes I see things. Cars moving around at odd hours." Do NOT make it more prominent during line-edit or copy-edit. Must remain dismissible as local colour until ch 20.
- **Culprit name (Mary Burrell)** — neither draft names or implicates the culprit. Keep it that way through all finalize passes.
- **Calloway's bench skeleton** — series seed, unresolved in Book 01. Do not let any finalize pass close this thread.
- **`.penny/` is gitignored** — the mystery lock lives there; do not `git clean -fdx`.
