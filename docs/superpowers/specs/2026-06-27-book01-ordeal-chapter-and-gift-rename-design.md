# Spec — Book 01: the Ordeal chapter + gift rename

Date: 2026-06-27
Status: approved design, pending implementation
Scope: `input/book-01/outline.md`, `series/continuity/**`, `series/whodunit/book-01.yaml`,
`series/arc-ledger.md`, `input/series/series-bible.md`, `output/book-01/mystery-solution.md`,
the mystery lock, and verification (`fairplay_check.py`, statusline).

## Why

Two linked changes to Book 01, agreed during a Hero's-Journey review of the outline:

1. **A concentrated Ordeal.** The current outline jumps from Saffron's collapse (ch 17)
   straight into the "click" (ch 18) with no genuine stuck/all-is-lost valley. We add a
   short dedicated chapter — a real stall, broken by a calm-at-the-wheel insight — so the
   midpoint low point lands and the gift's turn is earned.
2. **Rename the gift.** "Migraine Sight" medicalizes a gift and foregrounds the pain over
   the perception. Renamed to **the Too-Much** — the protagonist's own wry, midlife,
   ex-HR, reclaiming-an-insult word for it. It also rhymes with the existing ch-28 payoff
   ("The Woman Who Saw Too Much") and Elspeth Vale's 1978 caption ("Saw too much"): her
   private name turns out to be a generational echo.

## Part 1 — New chapter (inserted as Chapter 18)

Slots between current ch 17 (*The Wrong Woman*) and current ch 18 (*The Cup Returns
Home*). Short chapter. Everything from old ch 18 onward shifts +1 (see Part 3). No
drafted prose exists past ch 5, so this costs renumbering only, not re-drafting.

**Working title:** *The Only Quiet*

**Chapter Summary.**
Saffron's collapse has spent the last suspect. Beryl, Faye, Calloway — cleared or
discredited; Maggie's credibility is gone with every constituency that matters; the
town's verdict is that she is the newcomer who hurts people. She decides to stop — it was
never hers to solve. That night the Too-Much comes up off the water at its worst,
sharpened by shame and exhaustion, and nothing touches it: not the dark, not lying still.
Only the wheel ever has. She goes to the studio not to think but because centring clay is
the one thing that has ever talked the Too-Much down — medication does not reach it, time
only waits it out, but the wheel quiets it. In the after-calm (not the flood — the quiet
behind it), her hands do what they have always half-done: they rebuild a detail before
her mind catches up. She finds she has set a trimmed cup to an exact spot on the bench
and a form a hair off-true beside it — her hands recreating the spatial *wrongness* of
Neil's cottage. The clay hands her not an answer but a question: *someone reset that room
by habit — whose?* For the first time the Too-Much has worked with her, calm and useful,
and cost no one. She cannot stop after all — but this time she will look before she
speaks.

**Chapter Structure.**
- **Start / Desire:** Maggie wants to quit — to stop being the woman who sees too much and
  hurts people for it.
- **Pressure / Obstacle:** The worst Too-Much of the book, plus the shame that there is
  nothing left to investigate and no one left who trusts her.
- **Turn / Change:** At the wheel the Too-Much quiets; her hands surface the cottage's
  spatial wrongness as a question, not a verdict. The gift turns disciplined for the
  first time.
- **Texture / Pleasure Layer:** The studio at night, the wheel's hum, wet clay, Glaze
  asleep on the apron, the kiln ticking as it cools.
- **Hook:** She cannot stop — but she will bring Pruitt a habit, not a hunch.

**Track Movement.**
- **M:** No new clue invented. Recombines the already-planted staged-scene details (ch 7)
  into a precise spatial question; redirects the hunt from "who hated Neil" to "whose
  habit reset the room." Fair-play intact — the clay yields the question, later chapters
  yield the proof.
- **P:** The gift's turning point. Clay/centring established as the *only* reliable relief
  from the Too-Much; the gift becomes usable without performance or social cost. This is
  the concentrated Ordeal→turn.
- **R:** Quiet. Glaze present; Cal's post-argument distance felt but not worked. Romance
  rests.
- **B:** The same calm wheel-work that yields her repaired-glaze signature also yields the
  insight — craft and gift fuse.

**Fair-play invariant.** The chapter must NOT name or implicate the culprit, and must add
no new ledger clue. It only re-frames `clue-erasure` (already planted ch 7) into a
question. The culprit (Mary) is not named; her tidying habit is identified as a *category*
("whose habit?"), with the actual identification deferred to the next chapter (the click)
and the proof to Cobber's testimony.

## Part 2 — Rename: `Migraine Sight` → `the Too-Much`

Project-wide term replacement, plus one new canon fact. **No chapter prose is affected**
(verified: "Migraine Sight" does not appear in any `ch-NN.draft.md`/`.final.md`; the only
`output/` hits are `.reviews/` sidecars, regenerated on re-gate, and
`mystery-solution.md`). Therefore **no chapters need re-gating** for the rename.

Files containing the term (update all):
- `input/book-01/outline.md`
- `input/series/series-bible.md`
- `series/arc-ledger.md`
- `series/continuity/canon-core.md`
- `series/continuity/threads/gift.md`, `c-internal.md`, `a-murder.md`, `series-seeds.md`
- `series/continuity/locations/neils-cottage.md`
- `series/continuity/characters/maggie-quill.md`, `artie-selwood.md`, `iris-poole.md`
- `output/book-01/mystery-solution.md`

**New canon fact to add** (to `gift.md` and `maggie-quill.md`, cross-linked to
`the-wheelhouse.md`): pottery — specifically centring clay at the wheel — is Maggie's only
reliable relief from the Too-Much. Medication does not reach it; darkness only waits it
out; the wheel actively quiets it. This is what makes the new ch-18 wheel-breakthrough
mechanism canonical rather than convenient.

**Naming convention.** Capitalized, hyphenated coined proper noun in narration: **the
Too-Much**. May appear lowercase/offhand in dialogue. Keep it understated early (Maggie's
quiet, almost embarrassed word) so the ch-28 "Saw too much" echo detonates rather than
merely rhymes. Add this entry to `input/series/style-sheet.md`.

## Part 3 — Renumber (insertion at chapter 18)

Insertion is positional: content currently at outline chapter N (for N ≥ 18) moves to
N+1; ch 1–17 keep their numbers. The new chapter becomes 18; old 18→19 … old 28→29.

### Reconcile first, then shift

The whodunit ledger already carries some outline↔ledger drift that must be reconciled
**before** applying the +1, so we don't propagate existing off-by-ones:
- Saffron alibi: ledger `chapter: 18` vs outline collapse at ch 17 (*The Wrong Woman*).
- `clue-erasure` `pays_off_chapter: 19` vs the click currently at outline ch 18.

Implementation rule: map each ledger chapter reference to the **outline scene it denotes**,
confirm against the current outline, then renumber by the scene's new position. Surface
any reference whose intended scene is ambiguous before locking.

### `series/whodunit/book-01.yaml` — target values

Assuming each ledger ref denotes the outline scene at the same number (to be confirmed
during reconciliation), the +1 rule on refs ≥ 18 gives:

- `total_chapters: 28 → 29`
- `reveal_chapter: 24 → 25`  **(critical — `fairplay_check.py` reads this)**
- `culprit_first_appearance_chapter: 5` → unchanged
- `clue-erasure`: plant 7 (unchanged), pays_off 19 → **20**
- `clue-car-on-street`: plant 11 (unchanged), pays_off 22 → **23**
- `clue-old-records`: plant 15 (unchanged), pays_off 21 → **22**
- `clue-cobber-dawn-witness`: plant 2 (unchanged), pays_off 20 → **21**
- `rh-saffron` (plant 9), `rh-beryl` (plant 10), `rh-faye` (plant 13) → unchanged
- alibi `saffron` chapter 18 → **19** (pending reconciliation with outline ch 17)
- alibi `beryl-foss` (14), `faye` (13), `vincent-calloway` (14), `cobber` (11),
  `mary-burrell` (7) → unchanged (all < 18)
- **No new clue/red-herring/alibi rows are added** — the new chapter recombines an
  existing clue; fair-play schedule is otherwise unchanged.

### Cross-references elsewhere (+1 where the cited scene is at old ch ≥ 18)

- `input/book-01/outline.md`: the 11 chapter section headers from old 18–28; every inline
  callback citing ch 18–28 (Track Map at a Glance, Drafting Checks by Act, inter-chapter
  references such as "the click (ch 18)", "Cobber places Mary (ch 19)", "ch 21 papers",
  "ch 22 Pruitt", "ch 23 rupture", "ch 24 arrest", "ch 27", "ch 28"); and the new
  chapter inserted as 18.
- `series/continuity/**`: chapter citations in prose bodies and any `active_window` /
  canon-meta windows that reference chapters ≥ 18 (e.g. ch 18/19/20/21/23/24/27/28
  mentions in character and thread files). Audit each; shift only refs at old ch ≥ 18.
- `series/arc-ledger.md`, `input/series/series-bible.md`,
  `output/book-01/mystery-solution.md`: same +1 rule on chapter refs ≥ 18.

## Part 4 — Re-lock the mystery

The mystery lock (`.penny/locks/book-01.mystery.lock`) is an out-of-band certificate over
the ledger's validity; editing the ledger invalidates it. Procedure (per CLAUDE.md
"Re-planning = delete the lock, edit the yaml, re-run lock-mystery"):

1. Delete `.penny/locks/book-01.mystery.lock`.
2. Apply the ledger edits (Part 3) + the rename in any ledger-adjacent files.
3. Re-mint: `python3 scripts/preflight.py lock-mystery 01` (validates fairplay + lexicon,
   then writes the lock). A non-zero exit means the edited ledger does not validate — fix
   before proceeding; do not hand-write the lock.

## Part 5 — Verification

- `python3 scripts/fairplay_check.py` (or the book-level gate that wraps it) passes with
  `reveal_chapter: 25`, `total_chapters: 29`, and all necessary clues planted before 25.
- `python3 -m pytest` green (no engine code changes expected; this is data only).
- Statusline reports 29 numbered chapters (`penny-statusline.sh` counts `^## Chapter
  [0-9]`); confirm after the outline edit.
- Grep confirms zero remaining "Migraine Sight" occurrences outside regenerated
  `.reviews/` sidecars.

## Out of scope / deferred

- Drafting the new chapter's prose (this spec only inserts its outline entry + ledger
  position; drafting follows the normal `/draft-chapter` pipeline later).
- Re-gating ch 1–5 (not required — no prose changed).
- Any change to chapters 1–17 content beyond the rename term.

## Open items to confirm at implementation

1. Saffron alibi chapter (ledger 18 vs outline 17) and `clue-erasure` payoff (ledger 19 vs
   outline 18) — reconcile against the outline before applying +1.
2. Whether the new chapter's title *The Only Quiet* is final or a placeholder.
