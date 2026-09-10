---
description: Run the developmental gate on one chapter — dispatch the genre's isolated inspectors + the 2a checkers, then compute PASS/HOLD.
argument-hint: <book-number> <chapter-number>
arguments: [book, chapter]
---
# /review-chapter

The developmental gate (design §5 per-chapter flow, §6). Single-pass: dispatch
inspectors → run the deterministic checkers → compute the gate. A HOLD is surfaced
to the showrunner; re-drafting is a manual re-run (no auto-revise in this phase).

## Steps

1. **Parse args:** `book=$book` (e.g. `01`), `chapter=$chapter` (e.g. `07`).

2. **Re-run cleanup (so the gate reflects ONLY this run):**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reset_reviews.py" output/book-$book/chapters/ch-$chapter.reviews
   ```

3. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=REVIEW" > .penny/current-stage
   ```

4. **Assemble the ledger slice — for the two inspectors that grade against it,
   and no one else** (design §4.2). Two of the five isolated inspectors judge
   the chapter against series facts; the other three do not, and the slice is
   the single largest thing this command transmits, so it goes only where it is
   read:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py" $book $chapter --inspector-slice
   ```

   That prints the packet's `## Continuity Extracts` section alone, with
   `background/` entries removed — a read-only projection of the packet already
   on disk, regenerating nothing, so no `built_from_packet` stamp moves.
   `background/` is authored narrative backstory for the **drafter**;
   `characters/`, `locations/` and `threads/` are the ledger — the facts a
   chapter can actually contradict, which is all `inspector-continuity` and
   `inspector-fairplay` are grading. The heading carries a manifest recomputed
   for what is kept, `## Continuity Extracts (N entries: ...)`: read to the
   section's end (the next `## ` heading; embedded sources' own headings run
   deeper and don't end it) and check the `### ` entries you saw against the
   manifest count before trusting the read as complete.

   The projection emits that section **alone**, so `## Ledger Clues` does not
   travel with it — and that section, not the continuity one, is where
   `inspector-fairplay`'s clue-planting obligations live. Pass it to
   `inspector-fairplay` as well, read from
   `input/book-$book/packets/ch-$chapter.md`; its heading carries the same kind
   of manifest, `## Ledger Clues (N scheduled: ...)`, and the same counting rule
   applies to it. `inspector-continuity` does not get it: a clue schedule is an
   obligation, not an established fact a chapter can contradict.

   **`inspector-structure`, `inspector-voice` and `inspector-ai-prose` receive
   no continuity slice at all.** Not a narrower one — none. Structure judges the
   tension curve and the chapter-end hook from the page and its rubric;
   voice works from `config/setting-pack/lexicon.yaml` and the
   `voice_drift` / `lexicon_check` evidence written in step 5; ai-prose judges
   taste from its rubric and the prose. None of their instructions reference the
   slice, and none of their blocking predicates can be decided from it — sending
   it only bought them a way to be distracted.

   On the legacy path (no packet — book 01 is the book that hits it) there is
   nothing to project, so assemble the slice for those two inspectors by hand:
   always `series/continuity/canon-core.md`; then the `characters/`,
   `locations/` and `threads/` entries named in the chapter's raw outline
   section, plus their one-hop `links`. **Do not include
   `series/continuity/background/`** — the same exclusion the projection makes,
   for the same reason: `background/` is authored narrative backstory for the
   **drafter**, and the ledger is what a chapter can actually contradict.
   Canon-core-only fallback if there is no packet and no outline section for
   this chapter.

   The other narrowing is deliberately **not** attempted here. The
   both-ends-named rule for relationship entries (`a--b`, admitted only when
   both of its people are named in the chapter) is something the assembler
   applies mechanically; asking an agent to apply it by hand is the fragile
   version of it. Relationship entries live under `background/`, so the
   exclusion above already keeps them out of the ordinary case — but a `--`
   entry filed anywhere else still arrives on one end alone on this path. That
   gap is stated here rather than left silent; closing it properly means a
   machine-scoped route for the legacy path, in a spec of its own.

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

6. **Resolve the active genre's inspector set:**

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
   | structure | inspector-structure | structure-tension.md | structure-tension.md |
   | voice | inspector-voice | character-voice.md | character-voice.md |
   | ai-prose | inspector-ai-prose | ai-prose-taste-flags.md | ai-prose-taste-flags.md |

   **Dispatch, in isolation, exactly the inspectors named in `$INSPECTORS`** — for each, the
   `inspector-<name>` sub-agent (pass `model:` = `inspector_model` from
   `config/run-config.md`; the agent defs have no `model` frontmatter, so without an
   override they inherit the parent — the drafting session, grading its own prose) with
   the chapter text and its rubric (from the table above), plus **only** the extra inputs
   step 4 assigns it: `continuity` and `fairplay` get the `--inspector-slice` ledger,
   `fairplay` alone also gets the packet's `## Ledger Clues` section (the projection
   doesn't carry it, and it is where fairplay's obligations live), `structure` gets
   nothing beyond the page and its rubric, `voice` gets the lexicon and the step-5
   evidence files, `ai-prose` gets nothing beyond the page and its rubric. Each
   writes its verdict into `output/book-$book/chapters/ch-$chapter.reviews/` via
   `${CLAUDE_PLUGIN_ROOT}/scripts/penny_verdict.py`, to the verdict file named in the
   table above. `inspector-fairplay` additionally receives
   `output/book-$book/mystery-solution.md`, and the `reveal_chapter` value read from
   `series/whodunit/book-$book.yaml`. If the book has no locked ledger, dispatch it
   without `reveal_chapter` — the inspector will record the premature-reveal check as
   not applicable.

6b. **Cross-model guard + dispatch the developmental editor (context-rich, advisory).**

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
   raw outline section), plus `output/book-$book/mystery-solution.md`.

   Pass the packet through the projection, not whole — **when there is a packet**:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py" $book $chapter --without-continuity
   ```

   On the legacy path there is nothing to project: with no
   `input/book-$book/packets/ch-$chapter.md`, that command exits 1 with
   `PREDICATE FAILED: no packet` — the projection reads the packet on disk and
   never assembles one. Hand the editor the chapter's raw outline section
   instead, exactly as before; this is the same scoping step 4 gives the
   inspectors' slice, and book 01 is the book that hits it.

   Context-rich is not the same as everything. The developmental editor's own
   inputs already name the two things it reads about the series — the setting
   pack and a character-bible slice — and it was being handed the packet's whole
   continuity block on top of them, a third copy of overlapping material it
   never cites. What it needs from the packet is what the chapter was *trying to
   do*: Chapter Purpose, Starting/Ending State, Reader-Facing Shape, Required
   Beats, Guardrails, the word band. All of that survives the projection. Pass
   `$dev_sha` as the `reviewed_draft_sha256` it must record. It writes
   `output/book-$book/chapters/ch-$chapter.reviews/developmental-edit.md` via
   `${CLAUDE_PLUGIN_ROOT}/scripts/penny_verdict.py` (`kind: developmental`, no `^BLOCKING:` lines).

7. **Dispatch-completeness check:** confirm one verdict file (per the static table's
   `verdict file` column) for each inspector named in `$INSPECTORS`, AND
   `developmental-edit.md`, now exist in the reviews dir. A missing one means a sub-agent
   dispatch silently failed — stop and report it. (This is distinct from `fairplay.md`
   legitimately being absent pre-reveal.)

8. **Compute the gate and advance the marker:**

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

9. **Surface the result** to the showrunner: report the gate verdict and, on a
   HOLD, list the blocking items from
   `output/book-$book/chapters/ch-$chapter.gate.md`.

10. **Developmental clearance (showrunner gate before finalize).** The gate summary always
    prints an advisory **Developmental** section; it never affects PASS/HOLD. Finalize is
    blocked until you clear the developmental read for this exact draft:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" clear-dev $book $chapter
    ```

    Clear as-is ("noted, proceeding") or have the `drafter` revise first and re-run
    `/review-chapter` (a revised draft changes the hash and re-requires clearance).
