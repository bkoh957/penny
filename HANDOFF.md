# Handoff — Penny / main
Saved: 2026-06-26 | Type: build

## What we're building
Running the per-chapter pipeline for Book 01. **This session was a tree-wide character rename** (euphony review → three renames applied across all swappable data + drafts). The pipeline work from the previous handoff (re-gate ch-01, finalize ch-01/02, review ch-03–05, check stale ch-05 draft) is **still outstanding** — it was deferred again to do the rename first.

## The renames (applied this session, NOT yet committed)
| Old | New | Called | Slug/file |
|---|---|---|---|
| Meg Quill | **Margaret Quill** | **Maggie** | `meg-quill` → `maggie-quill` |
| Tom Burrell | **Callum Burrell** | **Cal** | `tom` → `cal-burrell` |
| Sergeant Dave Pruitt | **Sergeant Rick Pruitt** | — | `dave-pruitt` → `rick-pruitt` |

- Display names replaced whole-word, case-sensitive (`Meg→Maggie`, `Tom→Cal`, `Dave→Rick`) across `series/ input/ output/ docs/ HERMES.md HANDOFF.md`. Repo-wide stray count is **0/0/0**; no word-collisions (e.g. `tomorrow`, `custom` untouched).
- Formal-name lines added: canon-core = `Margaret "Maggie" Quill`; each of the 3 character files now carries a `**Full name:** … **Known as:** …` line.
- Continuity ids/filenames `git mv`'d (history preserved); all cross-links/`refs`/`canon-meta` updated (`b-romance` link, canon-core `refs`, thread/location `links`).
- **Locked surnames left intact:** Burrell (Cal keeps Burrell — shared w/ Mary), Vale (Saffron/Elspeth — series payload).

## Git state
- Branch: `main`. HEAD `b29527a` (unchanged this session).
- **Uncommitted (the rename):** ~35 tracked files modified, 3 renamed (`tom.md`→`cal-burrell.md`, `meg-quill.md`→`maggie-quill.md`, `dave-pruitt.md`→`rick-pruitt.md`). Plus pre-existing `HANDOFF.md` / `HERMES.md` edits.
- **Untracked (from prior session, also got renamed in-place this session):**
  - `output/book-01/chapters/ch-01.gate.md` — still says HOLD
  - `output/book-01/chapters/ch-01.reviews/` — continuity-drift.md still has old BLOCKING flag
  - `output/book-01/chapters/ch-02.gate.md` — PASS
  - `output/book-01/chapters/ch-02.reviews/` — all 5 verdicts present
  - `output/book-01/chapters/ch-03.draft.md`, `ch-04.draft.md` — drafted pre-outline-revision; ch 3/4 outline unchanged so valid
  - `output/book-01/chapters/ch-05.draft.md` — **stale: drafted before outline revision (Iris Poole / Sight-overreach beats); needs redraft**
- Tests: **251 passing** (re-run this session, post-rename).

## Next actions
1. **Decide: commit the rename first.** Recommend committing the rename as its own atomic change before resuming pipeline work (clean diff, easy to revert). User was asked and hadn't answered when handoff was saved. Suggested message: `refactor: rename Meg→Margaret "Maggie" Quill, Tom→Callum "Cal" Burrell, Dave→Rick Pruitt`. Note this would also add the untracked ch-01/02 review dirs + gate files unless staged selectively.
2. **Re-gate Ch-01.** Re-run inspector-continuity (ch-01 `continuity-drift.md` still has the stale BLOCKING line from the old HR claim), then `python3 -m scripts.review_gate output/book-01/chapters/ch-01.reviews` — confirm gate flips to PASS.
3. **Finalize Ch-01 and Ch-02.** `/finalize-chapter 01 01` then `/finalize-chapter 01 02` (02 already PASS). Both require `gate: PASS`.
4. **Check/redraft ch-05.** Stale vs new outline (Iris Poole stall, Maggie's Sight dazzle-then-overreach on Iris's private wound, revised hook). Likely needs `/draft-chapter 01 05` again.
5. **Review/gate ch-03 and ch-04.** `/review-chapter 01 03`, `/review-chapter 01 04` (outlines unchanged, drafts valid).

## Decisions made this session
- **Renamed the continuity ids/filenames too, not just display text.** Rationale: leaving `id: meg-quill` while the character is Maggie is confusing; the whodunit yaml and engine (`scripts/`, `.claude/`) reference none of these three (protagonist & sergeant aren't suspects), so the blast radius was contained to `series/`. Verified 0 stray slugs.
- **Case-sensitive whole-word replacement, not naive.** `Tom`/`Dave`/`Meg` as bare substrings would have mangled `tomorrow`/`custom`/etc. Used `perl -i -pe 's/\bTom\b/Cal/g'` (capitalized, word-boundaried); slugs are lowercase-hyphenated so the display pass couldn't touch them.
- **Applied via `find -exec`, not a shell `for` loop.** First attempt with a `$(find…)` capture into a `for` loop silently failed (replacements didn't persist); `find … -exec perl -i {} +` worked.
- **Renames also rewrote ch-01/02 drafts + review sidecars.** Accepted — keeps prose consistent; those reviews are slated for re-gate anyway so the rewritten quotes don't matter.

## User preferences expressed this session
- **Euphony rules for character names** (the user's stated criteria, worth keeping for future books): stress alternation; trochaic first names; syllable-count interplay (short+long balances better than two punchy or two long); avoid repeated sounds at name boundaries; vowel/consonant variety.
- User picks names decisively after a shortlist — give a few good alternatives, don't over-explain.

## Key files right now
- `series/continuity/characters/maggie-quill.md`, `cal-burrell.md`, `rick-pruitt.md` — renamed character files (formal-name lines added)
- `series/continuity/canon-core.md` — protagonist line now `Margaret "Maggie" Quill`; `refs: [maggie-quill]`
- `input/book-01/outline.md` — display names updated; still authoritative for the pipeline
- `output/book-01/chapters/ch-05.draft.md` — stale draft; check/redraft before review
- `output/book-01/chapters/ch-01.reviews/continuity-drift.md` — old BLOCKING flag; must re-run inspector-continuity

## Watch out for
- **The rename is uncommitted.** A `git checkout`/`clean` would lose it. Commit before risky git ops.
- **Other characters lacking surnames were reviewed but NOT changed** (user only acted on Meg/Tom/Dave): Cobber (real name Dennis, no surname), Dot & Glad (sisters, need one shared surname), Mara (foreshore character — culturally framed, pick deliberately). Suggestions are in the conversation if the user wants them later. Saffron already has a surname (Vale).
- **Ch-01 gate.md still says HOLD** — must re-run inspector-continuity (not just review_gate); the existing continuity-drift.md verdict still carries the old BLOCKING line.
- **Ch-05 draft predates the outline revision** — needs the Iris Poole / Sight-overreach beats; likely a full redraft.
- **Do not name the protagonist in engine files** (`scripts/`, `.claude/`) — they were verified clean of character names; keep them name-agnostic. Use "the protagonist".
- **Cobber's dawn-sighting clue** (ch-02) — keep dismissible until ch-20; don't amplify in edits.
- **Culprit (Mary Burrell)** — neither draft names/implicates her; keep it so through finalize.
- **Mary raised Cal** (was "Tom") — load-bearing backstory planted ch 11; don't soften.
- **Calloway's bench skeleton** + **Elspeth/Saffron Vale** — series seeds, leave unresolved in Book 01.
- **`.penny/` is gitignored** (mystery lock lives there) — do not `git clean -fdx`.
