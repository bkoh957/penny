# Handoff — Penny / main
Saved: 2026-06-22 | Type: build

## What we built this session
Populated all the book-01 series scaffolding by hand (bypassing `/scaffold-book` — the
user asked Claude to do the extraction directly). The series bible and 28-chapter outline
were authored by the user; we derived and wrote every mechanical artifact from them.

## Git state
- Branch: `main`. HEAD `b972aeb`. **origin/main == b972aeb — nothing pushed this session.**
- Uncommitted: a significant working tree — all the story content files below. None committed yet.
- Tests: **249 passing**, nothing broken.

## Files created / modified this session (all uncommitted)

**Modified:**
- `series/continuity/canon-core.md` — filled with real protagonist facts (Meg Quill, 43, OUTSIDER, autumn Book 01, sealed whodunit constraint)
- `series/arc-ledger.md` — 7-thread roster with opens/advances/resolves columns
- `series/series-bible.md` — (user-authored; we didn't touch it this session)

**Created (untracked):**
- `output/book-01/outline.md` — 28-chapter prose outline (user-authored + our stub); ## Solution block updated with Mary Burrell
- `output/book-01/mystery-solution.md` — **SEALED.** Full culprit/motive/clue/revelation details for Mary Burrell
- `series/whodunit/book-01.yaml` — whodunit yaml: culprit `mary-burrell`, victim `neil-hartigan`, 4 clues, 3 red herrings, 6-entry alibi grid; fairplay check exits 0
- `series/continuity/threads/` × 7 — a-murder, b-romance, c-internal, gift, victim-reveal, comedy, series-seeds
- `series/continuity/characters/` × 14 — meg-quill, neil-hartigan, tom, mary-burrell, faye, beryl-foss, dot, glad, cobber, saffron, vincent-calloway, artie-selwood, glaze, dave-pruitt
- `series/continuity/locations/` × 11 — pelicans-crook, the-wheelhouse, the-bakery, the-op-shop, the-pub, the-lighthouse, the-old-cemetery, the-wellness-retreat, neils-cottage, the-community-hall, the-beach

## Decisions made this session
- **Tom Burrell** — family surname chosen by user ("Burrell"). Tom's aunt is **Mary Burrell**.
- **Culprit ID: `mary-burrell`** — entity ID in whodunit yaml, alibi grid, and character file. The outline prose still says "Tom's aunt" in the chapter beats (correct narrative voice); only the `## Solution` block and sealed file use her name.
- **Bypassed `/scaffold-book`** — user asked Claude to do the extraction directly rather than dispatch the scaffolder agent. The artifacts are all written; the lock has NOT been earned yet. That still requires running `/scaffold-book 01 output/book-01/outline.md --approve` (which shells to `preflight.py lock-mystery 01`).
- **Blind-drafter seam preserved** — Mary Burrell's role as culprit appears ONLY in `mary-burrell.md` (with a SEALED warning), `mystery-solution.md`, `whodunit/book-01.yaml`, and the `## Solution` block in the outline. No other drafter-visible file names her as the killer.

## Next actions
1. **Commit the story content.** The working tree has a large set of new/modified story files. Commit them as story content (suggest one commit for outline+solution, one for the continuity scaffolding). Or the user may want to review first.
2. **Earn the lock.** Run `/scaffold-book 01 output/book-01/outline.md --approve` — this shells out to `python3 scripts/preflight.py lock-mystery 01`, which validates the yaml and mints `.penny/locks/book-01.mystery.lock`. The fairplay check already passes; the lock should be mintable.
3. **Name the remaining unnamed characters** (optional before drafting):
   - Faye's surname (Prior / Denton / Laing were suggested)
   - Cobber's real name (Ray / Dennis / Gary were suggested)
4. **Start drafting** — once the lock is earned, the pipeline is: `/plan-mystery 01` (already have the yaml, so this may be a thin step) → `/draft-chapter 01 01`.

## Key files right now
- `series/whodunit/book-01.yaml` — the mechanical mystery core; fairplay check passes
- `output/book-01/mystery-solution.md` — SEALED; full culprit+motive+clue details
- `series/continuity/canon-core.md` — always loaded; protagonist facts + whodunit constraint
- `output/book-01/outline.md` — 28-chapter prose outline; the author document

## Watch out for
- **The lock is not yet earned.** The yaml exists and passes fairplay, but `.penny/locks/book-01.mystery.lock` does not exist. Do not draft without the lock.
- **`mary-burrell` is the entity ID** throughout — if her name is ever changed, update: `whodunit/book-01.yaml` (culprit + suspect + central_deception), `characters/mary-burrell.md` (rename file + frontmatter), `mystery-solution.md`, and the outline `## Solution` block.
- **The outline prose beats still say "Tom's aunt"** — this is intentional (narrative voice). Don't replace those with Mary Burrell; she is introduced to the reader by her relationship to Tom, not by name, for most of the book.
- **Cobber's role in the alibi grid** — marked `holds: true` (he's a witness, not a suspect). His dawn sighting is a non-necessary clue (`clue-cobber-dawn-witness`, planted ch 2, pays off ch 20).
- **Calloway's bench skeleton** — series seed, explicitly NOT resolved in Book 01. Do not let a drafter close this thread.
