---
description: Draft one chapter through LM Studio using scene-shard orchestration for short-output local models.
argument-hint: <book-number> <chapter-number> [model-id]
---
# /draft-chapter-lmstudio

Drafts one complete chapter through a local LM Studio OpenAI-compatible server. This is
an alternate pathway for models that write strong short scenes but tend to stop before a
whole chapter. It keeps Penny's normal deterministic gates and artifact layout, but the
prose generation is orchestrated as scene shards → stitch pass → word-count repair.

Use this when the selected local model, e.g. a Gemma/Gemini-family model in LM Studio,
outputs small scenes instead of complete chapters through `/draft-chapter`.

## Requirements

- LM Studio is running its local server, normally at `http://localhost:1234/v1`.
- A model is loaded in LM Studio.
- Optional environment/config:
  - `LMSTUDIO_BASE_URL` overrides the base URL.
  - `LMSTUDIO_MODEL` selects the model id.
  - Or put `lmstudio_drafter_model: <model-id>` / `lmstudio_model: <model-id>` in a fenced
    yaml block in `config/run-config.md`.
  - Optional compact prompt digests for smaller local models:
    - `config/voice-pack/lmstudio-digest.md`
    - `config/genre-pack/lmstudio-digest.md`
    - `config/setting-pack/lmstudio-digest.md`
    If present, these are used instead of the longer voice/genre/setting pack prose for
    LM Studio drafting only. Keep them short, curated, and series-authored.
- If no model is supplied, the script asks `/v1/models` and uses the first loaded id.

## Steps

0. **Pre-flight gate (unchanged):** the script runs the same deterministic draft preflight
   as `/draft-chapter` before any LM Studio call:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" draft $1 $2
   ```

   A non-zero exit means the book's mystery is absent, unpopulated, or unlocked — run
   `/plan-mystery $1` or fix the lock first. Do not proceed on failure.

0b. **Outline review notice (advisory, non-blocking).** The script also surfaces the same
    outline-feedback status as `/draft-chapter`. Open or stale feedback never blocks.

1. **Parse args:** `book=$1`, `chapter=$2`, optional `model=$3`.

2. **Run the local scene-shard drafter:**

   ```bash
   if [ -n "$3" ]; then
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lmstudio_draft_chapter.py" "$1" "$2" --model "$3"
   else
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lmstudio_draft_chapter.py" "$1" "$2"
   fi
   ```

   The script:
   - resolves the active series from cwd via `.penny/`;
   - writes `.penny/current-stage` as `DRAFT-LMSTUDIO` then `DRAFTED`;
   - reads the chapter section from `input/book-$book/outline.md`, then sends LM Studio a
     compressed chapter-level context for each scene instead of repeating every other scene body;
   - reads `config/voice-pack/lmstudio-digest.md`, `config/genre-pack/lmstudio-digest.md`, and
     `config/setting-pack/lmstudio-digest.md` when present, falling back to the normal packs;
   - reads `config/length-profile.md`,
     `series/continuity/canon-core.md` plus brief-matched continuity entries, and a chapter-scoped
     whodunit excerpt rather than the full sealed answer key on every scene call;
   - splits scene-breakdown chapters by `### Scene N — ...` blocks, or treats compact chapters
     as one unit;
   - asks LM Studio for one prose shard per unit and prints approximate prompt character counts;
   - runs a stitch pass to smooth the chapter;
   - runs up to three expansion passes if the draft is under the length-profile minimum;
   - writes `output/book-$book/chapters/ch-$chapter.draft.md` with frontmatter:
     `drafted_by: lmstudio/<model-id>` and `drafted_on: YYYY-MM-DD`.

3. **Verify completion:** the command output prints the path, `drafted_by`, and word count.
   If the script exits non-zero because the draft remains under minimum, do not proceed to
   `/review-chapter`; inspect the draft and rerun with a stronger model or manually brief an
   expansion pass.

4. **Continue the normal pipeline:**

   ```text
   /review-chapter NN MM
   /finalize-chapter NN MM
   ```

## Guardrails

- This route is still a full-chapter drafter. Scene shards are implementation detail; the
  final artifact must be one complete `ch-MM.draft.md` chapter.
- Do not use the same LM Studio model for the final reader. Penny's assemble preflight checks
  `drafted_by` against `final_read_model`; model difference is the independence invariant.
- If a local model keeps under-shooting, fix the orchestration or choose a larger context/model;
  do not lower the length-profile minimum for the book.
