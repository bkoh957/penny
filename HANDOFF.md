# Handoff — Penny / main
Saved: 2026-06-24 | Type: build

## What we're building
Running the per-chapter pipeline for Book 01 — finalize Ch-01 (gate HOLD, fix applied) and Ch-02 (gate PASS), then draft Ch-03. This session also added chapter-type word-count targets to the length profile and sharpened the drafter to enforce a minimum word count.

## Git state
- Branch: `main`. HEAD `294fb4d`.
- **Uncommitted changes:**
  - `.claude/agents/drafter.md` — instruction #3 updated to classify chapter type + enforce min word count
  - `config/length-profile.md` — replaced flat 2500-word target with five-row chapter-type table
  - `output/book-01/chapters/ch-01.draft.md` — HR career fix applied (line 23)
  - `series/continuity/canon-core.md` — updated: "twenty years in HR, latterly Director"
  - `series/continuity/characters/meg-quill.md` — updated: "Twenty years in HR, the last decade as Director"
- **Untracked:**
  - `output/book-01/chapters/ch-01.gate.md` — says HOLD (pre-fix)
  - `output/book-01/chapters/ch-01.reviews/` — all 5 inspector verdicts present
  - `output/book-01/chapters/ch-02.gate.md` — says PASS
  - `output/book-01/chapters/ch-02.reviews/` — all 5 inspector verdicts present
- Tests: 250 passing.

## Next actions
1. **Re-gate Ch-01.** The blocker (HR tenure mismatch) was fixed in the draft but the continuity-drift.md verdict still has the old BLOCKING flag. Re-run inspector-continuity for ch-01, then: `python3 -m scripts.review_gate output/book-01/chapters/ch-01.reviews` — confirm gate flips to PASS before finalizing.
2. **Finalize Ch-01.** Run `/finalize-chapter 01 01` — requires `gate: PASS`.
3. **Finalize Ch-02.** Run `/finalize-chapter 01 02` — already PASS, no issues.
4. **Commit.** After both finalized: ledger fixes (canon-core, meg-quill), both drafts + gate + review dirs, both `.final.md` files, plus the drafter + length-profile changes from this session.
5. **Draft Ch-03.** Brief is in `input/book-01/outline.md` under `## Chapter 03`. Meg's first migraine; Dr Neil Hartigan introduced. Opening type → 1,800–2,400 words (standard investigation range applies).

## Decisions made this session
- **Voice pack rewritten (294fb4d):** 70% Clive James (travel-writer mode) / 30% Peter Temple. James supplies warmth, observational wit, and sentence architecture; Temple supplies economy, Australian register, and a pressure-modulated cadence for the climax. Temple's darkness/menace excluded entirely.
- **Protagonist not named in voice pack:** User confirmed character name has changed and may change again — voice pack uses "the protagonist" throughout. Never hardcode a character name in engine-layer files.
- **Climax modulation rule:** As tension rises, prose shifts progressively toward Temple (shorter sentences, less ruminative, no wit at peak). Returns to James after revelation. Encoded in `config/voice-pack/voice-pack.md`.
- **Ch-01 gate: fix-then-re-gate approach:** Re-run inspector-continuity so the verdict reflects the corrected draft — don't just patch the existing verdict file.
- **inspector-voice filename mismatch (ch-02):** Voice inspector wrote to `inspector-voice.md` instead of `character-voice.md`. Fixed by copying before gating. Watch for this on future chapters.
- **Chapter length targets added this session:** Flat 2500-word target replaced with a five-row chapter-type table in `config/length-profile.md`. Drafter now classifies type from the brief and enforces the range minimum before stopping. The "check and continue" instruction in drafter.md is the load-bearing part — without it the model stops when the story feels complete rather than when the count is met.

## User preferences expressed this session
- Do not use the protagonist's name in engine-layer files (voice pack, agent definitions, scripts). Name changes are expected; use "the protagonist" instead.
- Chapters must hit their type-appropriate word-count minimum — extend scenes rather than padding with recap.

## Key files right now
- `config/length-profile.md` — just updated with chapter-type table; now the authoritative word-count reference for the drafter
- `.claude/agents/drafter.md` — instruction #3 updated; drafter now classifies chapter type and enforces minimum
- `config/voice-pack/voice-pack.md` — authoritative voice brief for drafter + inspector-voice
- `output/book-01/chapters/ch-01.draft.md` — HR fix on line 23; ready for re-gate
- `output/book-01/chapters/ch-02.draft.md` — PASS gate; ready for finalize
- `output/book-01/chapters/ch-01.reviews/` — verdicts present; continuity-drift.md still has old BLOCKING flag

## AI-prose rubric calibration (Book 1 baseline)
- Ch-01 ai-prose score: 4 (two rote-adjacent touches — Flag 1 HR dissociation "somewhere else", Flag 5 "Not happiness, not yet. Just the possibility of it." — neither blocking; final sentence rescues the ending)
- Ch-02 ai-prose score: 3 (4 rote touches — 2×Flag 2 over-explains beats, 2×Flag 3 abstract where specific would serve)

## Watch out for
- **Ch-01 gate.md still says HOLD.** Must re-run inspector-continuity (not just review_gate) — the existing continuity-drift.md verdict still contains the BLOCKING line for the old HR claim.
- **Do not name the protagonist in engine files.** Use "the protagonist" — the character's name has changed once already and may change again.
- **`input/` is the new home for authored files.** Commands/agents now read from `input/series/` and `input/book-01/`.
- **Cobber's dawn-sighting clue** — planted in ch-02: "Sometimes I see things. Cars moving around at odd hours." Do NOT make it more prominent during line-edit or copy-edit. Must remain dismissible as local colour until ch-20.
- **Culprit name (Mary Burrell)** — neither draft names or implicates the culprit. Keep it that way through all finalize passes.
- **Calloway's bench skeleton** — series seed, unresolved in Book 01. Do not let any finalize pass close this thread.
- **`.penny/` is gitignored** — the mystery lock lives there; do not `git clean -fdx`.
- **inspector-voice filename:** watch for `inspector-voice.md` vs `character-voice.md` mismatch on future chapters — copy/rename before running review_gate.
