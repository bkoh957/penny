# Handoff — Penny / main
Saved: 2026-06-22 | Type: build

## What we did this session
UAT run: settled name gaps, minted the mystery lock, drafted Chapters 01 and 02 via the
blind drafter agent. Also installed the `codex@openai-codex` Claude Code plugin (user-scope).
Everything worked end-to-end; the pipeline is proven.

## Git state
- Branch: `main`. HEAD `816c693`.
- **Uncommitted changes:**
  - `series/continuity/characters/faye.md` — surname added (Denton)
  - `series/continuity/characters/cobber.md` — real name added (Dennis)
  - `HANDOFF.md` — this file
- **Untracked:** `output/book-01/chapters/` (ch-01.draft.md, ch-02.draft.md)
- Tests: 249 passing (nothing in scripts/ changed).

## Next actions
1. **Commit the name fixes + chapter drafts.** Stage and commit:
   - `series/continuity/characters/faye.md`
   - `series/continuity/characters/cobber.md`
   - `output/book-01/chapters/ch-01.draft.md`
   - `output/book-01/chapters/ch-02.draft.md`
2. **Gate the chapters.** Run `/review-chapter 01 01` then `/review-chapter 01 02` — dispatches the 5 blind inspectors and emits `ch-NN.gate.md`. Both should PASS before finalizing.
3. **Finalize.** `/finalize-chapter 01 01` → `/finalize-chapter 01 02` — line-edit → copy-edit → ledger update → promote to `.final.md`.
4. **Continue drafting.** After ch-02 is finalized, the next chapter is Ch-03 (Meg's first migraine; Neil's introduction).

## Decisions made this session
- **Faye's surname: Denton** — warm, Australian-sounding; chosen from (Prior / Denton / Laing).
- **Cobber's real name: Dennis** — nobody uses it; fits the demographic. Added as a note at the bottom of `cobber.md`.
- **Lock earned via shell, not `/scaffold-book`** — `python3 scripts/preflight.py lock-mystery 01` run directly; `.penny/locks/book-01.mystery.lock` now exists. The `--approve` flag approach was skipped; the lock is valid.
- **UAT confirmed the naming convention is `01` (zero-padded)** — preflight with raw `1` fails; always use `01`.

## Key files right now
- `output/book-01/chapters/ch-01.draft.md` — 2,318 words; arrival chapter; no clues scheduled; hook is Glaze settling on the apron
- `output/book-01/chapters/ch-02.draft.md` — 2,596 words; Faye/Cobber/Dot+Glad/Beryl; Cobber's dawn-sighting clue planted (non-necessary; pays off ch 20)
- `series/continuity/characters/faye.md` — surname Denton added; uncommitted
- `series/continuity/characters/cobber.md` — real name Dennis added; uncommitted

## Plugins installed this session
- `codex@openai-codex` v1.0.4 — user scope. Adds `/codex:review`, `/codex:adversarial-review`, `/codex:rescue`, `/codex:status`, `/codex:result`, `/codex:cancel`, `/codex:setup`. Codex binary already present at `/Users/beeko/.local/bin/codex`. **Requires reload + `/codex:setup` to confirm auth** before first use.

## Watch out for
- **`.penny/` is gitignored** — the lock lives there; it is NOT committed. It persists on disk and will survive normal session changes, but would be lost on a clean checkout. Don't `git clean -fdx`.
- **Cobber's clue seam** — planted in ch-02 as pure atmosphere ("Sometimes I see things. Cars moving around at odd hours."). Do NOT make it more prominent during review/edit; it must remain dismissible until ch 20.
- **Culprit name (Mary Burrell)** — the OUTSIDER constraint is working; neither draft names the culprit. Keep it that way through all finalize passes.
- **Calloway's bench skeleton** — series seed, unresolved in Book 01. Do not let any editor or finalize pass close this thread.
