---
description: Run the developmental gate on one chapter — dispatch the 5 blind inspectors + the 2a checkers, then compute PASS/HOLD.
argument-hint: <book-number> <chapter-number>
---
# /review-chapter

The developmental gate (design §5 per-chapter flow, §6). Single-pass: dispatch
inspectors → run the deterministic checkers → compute the gate. A HOLD is surfaced
to the showrunner; re-drafting is a manual re-run (no auto-revise in this phase).

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), `chapter=$2` (e.g. `07`).

2. **Re-run cleanup (so the gate reflects ONLY this run):**

   ```bash
   python3 scripts/reset_reviews.py output/book-$book/chapters/ch-$chapter.reviews
   ```

3. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=REVIEW" > .penny/current-stage
   ```

4. **Assemble the ledger slice** (design §4.2, same as `draft-chapter`): always
   `series/continuity/canon-core.md`; then the continuity entries named in the
   chapter brief and their one-hop `links`. Canon-core-only fallback if no brief.

5. **Run the 2a deterministic checkers:**

   ```bash
   python3 scripts/voice_drift.py output/book-$book/chapters/ch-$chapter.draft.md \
     --out output/book-$book/chapters/ch-$chapter.reviews
   ```

   Run `fairplay_check.py` ONLY when `$chapter` is the `reveal_chapter` of a locked
   `series/whodunit/book-$book.yaml` (its book-level fairness gate belongs to the
   reveal chapter):

   ```bash
   python3 scripts/fairplay_check.py series/whodunit/book-$book.yaml \
     --out output/book-$book/chapters/ch-$chapter.reviews
   ```

6. **Build the thread roster** for `inspector-structure`: from
   `series/continuity/threads/*.md` + `series/arc-ledger.md`, as
   `[{ thread_id, last_advanced_chapter }]`. Until Phase 4 maintains
   `last_advanced_chapter`, set it to `unknown` (the inspector then emits no liveness
   flag).

7. **Dispatch the 5 blind inspector sub-agents**, each with the chapter text, its one
   rubric, and the ledger slice (structure also gets the roster). Each writes its
   verdict into `output/book-$book/chapters/ch-$chapter.reviews/` via
   `scripts/penny_verdict.py`:
   - `inspector-continuity` → `continuity-drift.md`
   - `inspector-fairplay` → `fairplay-planting.md`
   - `inspector-structure` → `structure-tension.md` (+ roster)
   - `inspector-voice` → `character-voice.md`
   - `inspector-ai-prose` → `ai-prose-taste-flags.md`

8. **Dispatch-completeness check:** confirm all five inspector verdict files now
   exist in the reviews dir. A missing one means a sub-agent dispatch silently failed
   — stop and report it. (This is distinct from `fairplay.md` legitimately being
   absent pre-reveal.)

9. **Compute the gate:**

   ```bash
   python3 scripts/review_gate.py output/book-$book/chapters/ch-$chapter.reviews
   ```

   It writes `output/book-$book/chapters/ch-$chapter.gate.md` and prints
   `GATE: PASS` or `GATE: HOLD (n blocking)`.

10. **Advance the marker and surface the result:**

    ```bash
    # stage=REVIEWED on PASS, stage=GATE-HELD on HOLD
    echo "book=$book chapter=$chapter stage=REVIEWED" > .penny/current-stage
    ```
