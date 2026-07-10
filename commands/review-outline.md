---
description: Independent pre-draft outline craft review — dispatch the Claude+Codex panel, append side-by-side prose feedback to the tracked ledger. Advisory; never gates.
argument-hint: <book-number> [--focus "<directive>"]
---
# /review-outline

Runs an INDEPENDENT reviewer panel over the whole outline and records side-by-side prose
feedback as ID'd items you can disposition. Advisory — nothing here blocks drafting.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`); optional `--focus "<directive>"` (only when you
   noticed the review missed something — the default run is unsteered).

2. **Preconditions:**
   ```bash
   test -f "input/book-$1/outline.md" || { echo "no outline for book $1 — run /scaffold-book or /expand-outline first"; exit 1; }
   ```
   Resolve the active genre (via `${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py`) and require
   its `review-rubrics/outline-craft.md`. If the active genre pack ships no `outline-craft.md`,
   abort: this tier needs the rubric.

3. **Marker:**
   ```bash
   mkdir -p .penny && echo "book=$1 stage=OUTLINE-REVIEW" > .penny/current-stage
   ```

4. **Resolve the panel roster:** read `outline_review_panel` from the active
   `config/run-config.md` (via the config overlay) if present; otherwise default to
   `[claude, codex]`.

5. **Load the current ledger** for dedup context (if it exists):
   `output/book-$1/reports/outline-feedback.yaml`.

6. **Dispatch each panel member independently, with identical inputs** (whole
   `input/book-$1/outline.md`, the genre `outline-craft.md`, `input/series/series-bible.md`,
   `series/continuity/canon-core.md`, `series/arc-ledger.md` if present, the current ledger
   for dedup, and the `--focus` directive if given). The outline includes its own
   `## Solution` block; panel members reason about the whole book.
   - `claude` → dispatch the `outline-reviewer` sub-agent.
   - `codex` → send the SAME rubric + inputs to the Codex reviewer via the codex plugin
     runtime (independent tool; this is the "difference, not identity" second set of eyes).
     Give it this output contract verbatim, so both members are bound by a committed
     artifact rather than an improvised prompt:
     > Produce your feedback as a JSON array of objects `{ "text": "<one focused prose point>" }`
     > — one object per discrete point (quote the beat + name the gap + a concrete move).
     > Add a `recommendation` field only when you are recommending a change: `text` carries the
     > observation, `recommendation` carries the fix you propose. Omitting it is a legitimate answer
     > — if a point is praise, or names an ambiguity you cannot resolve, leave it off rather than
     > inventing an action.
     > Emit `[]` if you genuinely have nothing new to add this pass. Do NOT assign IDs; do NOT
     > add a `source` field (the command owns both).
   - If a member is unreachable, continue with the rest and note
     `independence reduced: <member> unreachable this pass` in the console output.

7. **Collect points → JSON.** Each member returns a JSON array of `{ text, recommendation? }`.
   Tag each point with its member as `source` and concatenate into one array
   `[{ source, text, recommendation? }, ...]`. Write it to a temp file, e.g.
   `.penny/outline-points-$1.json`. Never merge or reconcile two members' recommendations —
   disagreement is the signal this tier preserves.

8. **Append + render** (deterministic; append-only — never disturbs your existing states):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" append $1 --points ".penny/outline-points-$1.json"
   ```

9. **Print the outcome:** the new items (id · source · one-line headline) and the current
   open-item count. Point the user at `output/book-$1/reports/outline-review.md` (side-by-side
   view) and `outline-feedback.yaml` (edit `state` to disposition: `open`→`solved`/`rejected`).

10. **Marker:**
    ```bash
    echo "book=$1 stage=OUTLINE-REVIEWED" > .penny/current-stage
    ```

Re-run any time after editing the outline; passes accumulate in the ledger and your
dispositions are never overwritten.
