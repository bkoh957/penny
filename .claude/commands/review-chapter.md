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

9. **Compute the gate and advance the marker:**

   ```bash
   gate_out="$(python3 scripts/review_gate.py output/book-$book/chapters/ch-$chapter.reviews)"
   echo "$gate_out"
   if printf '%s' "$gate_out" | grep -q '^GATE: HOLD'; then
     stage=GATE-HELD
   else
     stage=REVIEWED
   fi
   echo "book=$book chapter=$chapter stage=$stage" > .penny/current-stage
   ```

   `review_gate.py` writes `output/book-$book/chapters/ch-$chapter.gate.md` and
   prints `GATE: PASS` or `GATE: HOLD (n blocking)`. The marker is set to
   `stage=REVIEWED` on a PASS gate and `stage=GATE-HELD` on a HOLD gate.

10. **Surface the result** to the showrunner: report the gate verdict and, on a
    HOLD, list the blocking items from
    `output/book-$book/chapters/ch-$chapter.gate.md`.
