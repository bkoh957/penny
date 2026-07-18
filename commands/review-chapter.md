---
description: Run the developmental gate on one chapter — dispatch the genre's isolated inspectors + the 2a checkers, then compute PASS/HOLD.
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
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reset_reviews.py" output/book-$book/chapters/ch-$chapter.reviews
   ```

3. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=REVIEW" > .penny/current-stage
   ```

4. **Assemble the ledger slice** (design §4.2, same as `draft-chapter`): when
   `input/book-$book/packets/ch-$chapter.md` exists, its `## Continuity Extracts`
   section already carries the assembled slice — canon-core + the entries this
   chapter names + their one-hop `links` — so read it from there directly. On the
   legacy path (no packet), assemble it the old way: always
   `series/continuity/canon-core.md`; then the continuity entries named in the
   chapter's raw outline section and their one-hop `links`. Canon-core-only
   fallback if neither a packet nor a brief exists.

5. **Run the 2a deterministic checkers:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/voice_drift.py" output/book-$book/chapters/ch-$chapter.draft.md \
     --out output/book-$book/chapters/ch-$chapter.reviews
   ```

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lexicon_check.py" output/book-$book/chapters/ch-$chapter.draft.md \
     --out output/book-$book/chapters/ch-$chapter.reviews \
     --target book-$book/ch-$chapter
   ```

   `lexicon_check.py` is evidence-only: it writes `lexicon-fluency.md` and never
   blocks. `inspector-voice` weighs the evidence and makes the blocking call.

   Run `fairplay_check.py` ONLY when `$chapter` is the `reveal_chapter` of a locked
   `series/whodunit/book-$book.yaml` (its book-level fairness gate belongs to the
   reveal chapter):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fairplay_check.py" series/whodunit/book-$book.yaml \
     --out output/book-$book/chapters/ch-$chapter.reviews
   ```

6. **Build the thread roster** for `inspector-structure`: from
   `series/continuity/threads/*.md` + `series/arc-ledger.md`, as
   `[{ thread_id, last_advanced_chapter }]`. Read each thread file's real frontmatter
   `last_advanced_chapter` value. A missing or empty value maps to `null`, which
   `inspector-structure` treats as "no advancement recorded yet" — no dormancy flag is
   emitted (identical behaviour to the old `unknown` placeholder, but now reading real
   data written by `/finalize-chapter`).

7. **Resolve the active genre's inspector set:**

   ```bash
   INSPECTORS="$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" inspectors)"
   ```

   `$INSPECTORS` is the active genre's isolated-inspector set (for a cozy series:
   `continuity fairplay structure voice ai-prose`). The genre chooses WHICH
   inspectors run; the static table below is the engine's fixed reference for each
   inspector's rubric and verdict file:

   | inspector | agent | rubric | verdict file |
   |---|---|---|---|
   | continuity | inspector-continuity | continuity-drift.md | continuity-drift.md |
   | fairplay | inspector-fairplay | fairplay-planting.md | fairplay-planting.md |
   | structure | inspector-structure | structure-tension.md | structure-tension.md (also gets the thread roster) |
   | voice | inspector-voice | character-voice.md | character-voice.md |
   | ai-prose | inspector-ai-prose | ai-prose-taste-flags.md | ai-prose-taste-flags.md |

   **Dispatch, in isolation, exactly the inspectors named in `$INSPECTORS`** — for each, the
   `inspector-<name>` sub-agent (pass `model:` = `inspector_model` from
   `config/run-config.md`; the agent defs have no `model` frontmatter, so without an
   override they inherit the parent — the drafting session, grading its own prose) with
   the chapter text, its rubric (from the table above), and the ledger slice (structure
   also gets the roster). Each writes its
   verdict into `output/book-$book/chapters/ch-$chapter.reviews/` via
   `${CLAUDE_PLUGIN_ROOT}/scripts/penny_verdict.py`, to the verdict file named in the
   table above. `inspector-fairplay` additionally receives
   `output/book-$book/mystery-solution.md` and the `reveal_chapter` value read from
   `series/whodunit/book-$book.yaml`. If the book has no locked ledger, dispatch it
   without `reveal_chapter` — the inspector will record the premature-reveal check as
   not applicable.

7b. **Cross-model guard + dispatch the developmental editor (context-rich, advisory).**

   The developmental read MUST run on a non-drafting model (genuine fresh eyes, design §6).
   Determine a reachable model that is **not** `drafting_model` (per `config/run-config.md`,
   e.g. `inspector_model` / `final_read_model`). **If the only reachable model is the
   drafting model, HALT** — print a named error and stop; do NOT degrade to a same-model
   read (a same-model "fresh eyes" read is a soft gate Penny rejects).

   Compute the draft hash to bind the read to this exact draft:

   ```bash
   dev_sha="$(python3 -c "import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}'); \
     from scripts.preflight import draft_sha256; print(draft_sha256('$book', '$chapter'))")"
   ```

   Dispatch the `developmental-editor` sub-agent (pass `model:` = the non-drafting model
   resolved above; the same frontmatter gap applies — without an explicit override the
   guard above is inert, because the agent silently inherits the drafting session) with
   its **context-rich** inputs — the
   chapter draft text, `config/review-rubrics/developmental-craft.md`, the setting pack,
   a character-bible slice, and the chapter's map + packet (or, on the legacy path, the
   raw outline section), plus `output/book-$book/mystery-solution.md`. Pass
   `$dev_sha` as the `reviewed_draft_sha256` it must record. It writes
   `output/book-$book/chapters/ch-$chapter.reviews/developmental-edit.md` via
   `${CLAUDE_PLUGIN_ROOT}/scripts/penny_verdict.py` (`kind: developmental`, no `^BLOCKING:` lines).

8. **Dispatch-completeness check:** confirm one verdict file (per the static table's
   `verdict file` column) for each inspector named in `$INSPECTORS`, AND
   `developmental-edit.md`, now exist in the reviews dir. A missing one means a sub-agent
   dispatch silently failed — stop and report it. (This is distinct from `fairplay.md`
   legitimately being absent pre-reveal.)

9. **Compute the gate and advance the marker:**

   ```bash
   gate_out="$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_gate.py" output/book-$book/chapters/ch-$chapter.reviews)"
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

11. **Developmental clearance (showrunner gate before finalize).** The gate summary always
    prints an advisory **Developmental** section; it never affects PASS/HOLD. Finalize is
    blocked until you clear the developmental read for this exact draft:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" clear-dev $book $chapter
    ```

    Clear as-is ("noted, proceeding") or have the `drafter` revise first and re-run
    `/review-chapter` (a revised draft changes the hash and re-requires clearance).
