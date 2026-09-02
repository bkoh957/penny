---
description: Draft one chapter — first step of the full pipeline (review via /review-chapter, finalize via /finalize-chapter).
argument-hint: <book-number> <chapter-number>
arguments: [book, chapter]
---
# /draft-chapter

Drafts one chapter: assemble context → dispatch the drafter → write the draft. The
chapter then moves through the full pipeline: gate it with `/review-chapter`, then
edit and commit with `/finalize-chapter`.

## Steps

0. **Pre-flight gate (Phase 3):** the mystery must be validated and locked before
   any chapter is drafted. Hard-fail aborts before context assembly:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" draft $book $chapter
   ```

   A non-zero exit means the book's mystery is absent, unpopulated, or unlocked —
   run `/plan-mystery $book` first. Do not proceed on failure.

0b. **Outline review notice (advisory, non-blocking).** Surface any open outline feedback
    or staleness before drafting. This NEVER blocks — always proceed regardless of output:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" status $book
    ```

    An open-item or "stale — re-run /review-outline" notice is a reminder, not a gate.

1. **Parse args:** `book=$book` (e.g. `01`), `chapter=$chapter` (e.g. `01`).

2. **Write the harness state marker** so the status bar reflects position
   (design §11):

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=DRAFT" > .penny/current-stage
   ```

3. **Assemble the chapter's instruction and context** (design §2, §7 — map = instruction,
   packet = context):
   - **Map + packet (the current path):** if `input/book-$book/maps/ch-$chapter.md`
     exists, that file **is** the drafter's instruction — the per-scene `Target:` ranges
     are the word contract, `Weight:` tells the drafter what each scene IS, and
     `Beats covered:`/`Clue:` lines name which packet obligations land where. Pass
     alongside it `input/book-$book/packets/ch-$chapter.md` as context — the chapter's
     outline block, merged ledger clues, continuity extracts (canon-core + the entries
     the chapter names, plus their one-hop links — this replaces the separate ledger-slice
     step the brief compiler needed, since the packet already carries it), standing
     series guardrails, and the word budget the map was priced against.

     (`preflight draft` above already refuses a **stale** packet or map — one built from
     an outline, whodunit ledger, or packet that has since changed — before this step
     runs; if it refused, the cure is the same: re-run `/map-chapter $book $chapter`.)
   - **The packs (how it sounds):** the drafter also reads `config/voice-pack/voice-pack.md`,
     the setting pack, and the genre prose pack directly (per `agents/drafter.md`) — the
     packet carries *what* to write, the voice pack carries *how*. These are global files,
     so they are a direct agent read rather than assembled into the packet, exactly as the
     LM Studio path loads its voice digest.
   - **Previous chapter's tail:** attach the previous chapter's final ~300 words, so the
     drafter opens in continuity with what the reader just read. Prefer
     `output/book-$book/chapters/ch-<chapter-1>.final.md`; if that doesn't exist yet, fall
     back to `ch-<chapter-1>.draft.md`; if neither exists (chapter 1, or the previous
     chapter isn't drafted yet), omit it and say so rather than inventing a tail.
   - **Legacy fallback (no map yet):** if there is no map for this chapter, fall back to
     the raw outline path exactly as before — read `input/book-$book/outline.md` and
     extract the full `## Chapter $chapter` section verbatim as the drafter's brief. Warn
     that the chapter is drafting from an unmapped outline, and that a flat beat list
     will be read by the model as a promise of parity — run `/map-chapter $book $chapter`
     to fix it.
     - **Scene-breakdown format:** `### Overall Summary`, one or more
       `### Scene N — Title` sections with Location/Purpose/Beat flow/Emotional
       turn/Texture, then `### Chapter Structure Summary`, `### Track Movement`,
       `### Drafting Notes / Guardrails`, and optional line prompts.
     - **Compact format:** `### Chapter Summary`, `### Chapter Structure`, and
       `### Track Movement`.
     This full section is the brief passed to the drafter, plus the legacy ledger
     slice: always load `series/continuity/canon-core.md`; then load the continuity
     entries named in the section and their one-hop `links` (the packet does not exist
     on this path, so nothing else supplies it).

4. **Ensure output paths exist:**

   ```bash
   mkdir -p output/book-$book/chapters
   ```

5. **Capture the draft date** so the stamp is deterministic (not the agent's guess):

   ```bash
   draft_date=$(date +%F)   # YYYY-MM-DD
   ```

6. **Dispatch the `drafter` sub-agent** with the inputs listed in
   `agents/drafter.md` — which now include `output/book-$book/mystery-solution.md` and
   the `reveal_chapter` from `series/whodunit/book-$book.yaml` — passing `draft_date`
   for the `drafted_on` stamp.
   Write its output to `output/book-$book/chapters/ch-$chapter.draft.md` including
   `drafted_by` and `drafted_on: $draft_date` frontmatter.

7. **Stamp the draft's word count** — measured, never asked for. The drafter reports
   the shortfall it *feels* (`drafted_short:`); the number itself is counted here, so
   `drafted_words:` in the frontmatter is a fact rather than the drafting model's
   estimate of its own output:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/draft_words.py" $book $chapter
   ```

   It rewrites the field in place, so re-running after a redraft is safe. The stamp is
   the *draft's* count and keeps that name through `.lineedit.md` / `.copyedit.md` /
   `.final.md`, which carry frontmatter forward — the edits cut flab, so the finished
   chapter runs a little shorter than the number says.

8. **Clear/advance the marker** when done:

   ```bash
   echo "book=$book chapter=$chapter stage=DRAFTED" > .penny/current-stage
   ```
