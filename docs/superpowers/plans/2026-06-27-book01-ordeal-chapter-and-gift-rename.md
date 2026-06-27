# Book 01 — Ordeal Chapter + "the Too-Much" Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insert a short Ordeal chapter (new ch 18, *The Only Quiet*) into the Book 01 outline and rename the gift "Migraine Sight" → "the Too-Much", renumbering all downstream chapter references and re-locking the mystery.

**Architecture:** Pure data/content edits — no engine (`scripts/`) changes. Two orthogonal passes (a term rename and a +1 chapter renumber from ch 18), executed rename-first so they don't collide, then re-lock the whodunit ledger and verify against the deterministic gates.

**Tech Stack:** Markdown (outline, continuity, specs), the small YAML subset parsed by `penny_meta`, PyYAML for `series/whodunit/book-01.yaml`, `scripts/preflight.py` (lock), `scripts/fairplay_check.py`, `scripts/penny-statusline.sh`, pytest.

## Global Constraints

- Rename target: `Migraine Sight` → `the Too-Much` (capitalized, hyphenated coined proper noun in narration; lowercase/offhand allowed in dialogue). Verbatim string.
- **No chapter prose is edited** — "Migraine Sight" appears in no `ch-NN.draft.md`/`.final.md`; ch 1–5 are NOT re-gated by this work.
- Insertion is positional at chapter 18: content at old outline chapter N (N ≥ 18) moves to N+1; ch 1–17 keep their numbers; new chapter = 18; old 28 → 29.
- **Reconcile-first:** map each ledger/cross-ref chapter number to the outline scene it denotes and confirm against the current outline *before* applying +1. Do not treat ledger numbers as authoritative where they drift from the outline.
- `total_chapters: 28 → 29`; `reveal_chapter: 24 → 25`.
- The new chapter adds NO new ledger clue/red-herring/alibi row; it only re-frames `clue-erasure` (planted ch 7) into a question. It must not name or implicate the culprit (Mary).
- Editing `series/whodunit/book-01.yaml` invalidates the mystery lock → must delete and re-mint via `preflight.py lock-mystery 01` (never hand-write the lock).
- Spec of record: `docs/superpowers/specs/2026-06-27-book01-ordeal-chapter-and-gift-rename-design.md`.

---

### Task 1: Rename the gift to "the Too-Much" (term + canon fact)

**Files (Modify):**
- `input/book-01/outline.md`
- `input/series/series-bible.md`
- `series/arc-ledger.md`
- `series/continuity/canon-core.md`
- `series/continuity/threads/gift.md`, `c-internal.md`, `a-murder.md`, `series-seeds.md`
- `series/continuity/locations/neils-cottage.md`
- `series/continuity/characters/maggie-quill.md`, `artie-selwood.md`, `iris-poole.md`
- `output/book-01/mystery-solution.md`
- `input/series/style-sheet.md` (append naming convention)

**Interfaces:**
- Produces: a codebase with zero "Migraine Sight" occurrences outside regenerated `.reviews/` sidecars; the term "the Too-Much" in their place; and a new canon fact (pottery is the only reliable relief) that Task 2's chapter relies on.

- [ ] **Step 1: Inventory occurrences**

Run: `grep -rn "Migraine Sight" input/ series/ output/book-01/mystery-solution.md`
Expected: the files listed above (NOT any `ch-NN.draft.md`/`.final.md`).

- [ ] **Step 2: Replace the term in each file**

For each file above, replace `Migraine Sight` → `the Too-Much`, fixing surrounding grammar so the sentence reads naturally (e.g. "her Migraine Sight" → "her the Too-Much" is WRONG → "the Too-Much" / "her gift, the Too-Much"). Read each hit in context; do not blind-`sed`. Where a heading or label was literally "Migraine Sight", rename it to "The Too-Much".

- [ ] **Step 3: Add the pottery-relief canon fact**

In `series/continuity/threads/gift.md` and `series/continuity/characters/maggie-quill.md`, add (extractive, terse): centring clay at the wheel is Maggie's *only* reliable relief from the Too-Much — medication does not reach it, darkness only waits it out, the wheel actively quiets it. Cross-link to `[[the-wheelhouse]]` and ensure `the-wheelhouse.md`'s existing "clay-as-externalised-sight" line is consistent (it already states her hands rebuild a detail before her conscious mind catches up).

- [ ] **Step 4: Add the style-sheet entry**

In `input/series/style-sheet.md` under `## Decisions`, append:
`- Gift name: "the Too-Much" — capitalized, hyphenated coined proper noun in narration; may be lowercase/offhand in dialogue. Keep understated early so the ch-28 "Saw too much" echo lands. (Replaces the retired "Migraine Sight".)`

- [ ] **Step 5: Verify**

Run: `grep -rn "Migraine Sight" input/ series/ output/book-01/mystery-solution.md`
Expected: no matches.
Run: `python3 -m pytest -q`
Expected: all pass (data-only change; meta-parsers must still parse).

- [ ] **Step 6: Commit**

```bash
git add input/ series/ output/book-01/mystery-solution.md
git commit -m "feat(book-01): rename gift 'Migraine Sight' -> 'the Too-Much'; clay as its only relief"
```

---

### Task 2: Reconcile chapter numbering, then renumber the outline + insert ch 18

**Files (Modify):** `input/book-01/outline.md`

**Interfaces:**
- Consumes: the renamed outline from Task 1.
- Produces: a 29-chapter outline with the new ch 18 inserted; a written reconciliation map (in the commit body / scratch) that Tasks 3–4 reuse for renumbering ledger and continuity refs.

- [ ] **Step 1: Build the reconciliation map**

Read `input/book-01/outline.md` chapter headers (old 1–28) and `series/whodunit/book-01.yaml`. For every chapter reference in the ledger and in the outline's inline callbacks (Track Map at a Glance, Drafting Checks by Act, "(ch NN)" mentions), record the outline scene it denotes and its NEW number under the rule: old N → N (N ≤ 17), new chapter → 18, old N → N+1 (N ≥ 18). Note the two known drifts explicitly: Saffron's collapse is outline ch 17 (ledger alibi says 18) → its scene stays 17; `clue-erasure` pays off at the "click" (outline ch 18 → new 19; ledger said 19 → confirm it means the click, then it becomes 20 only if it denotes a scene at old ≥18). Resolve each against the outline scene, not the bare number.

- [ ] **Step 2: Renumber existing outline chapter headers 18–28 → 19–29**

In `input/book-01/outline.md`, change the section headers `## Chapter 18 — …` through `## Chapter 28 — …` to `## Chapter 19 …` through `## Chapter 29 …` (text after the em-dash unchanged). Leave ch 1–17 untouched.

- [ ] **Step 3: Insert the new Chapter 18**

Insert, immediately after old ch 17 (*The Wrong Woman*) and before the now-ch-19 (*The Cup Returns Home*), in the house format, using the spec's Part 1 content:

```markdown
## Chapter 18 — The Only Quiet

### Chapter Summary
Saffron's collapse has spent the last suspect. Beryl, Faye, Calloway — cleared or discredited; Maggie's credibility is gone with every constituency that matters; the town's verdict is that she is the newcomer who hurts people. She decides to stop — it was never hers to solve. That night the Too-Much comes up off the water at its worst, sharpened by shame and exhaustion, and nothing touches it: not the dark, not lying still. Only the wheel ever has. She goes to the studio not to think but because centring clay is the one thing that has ever talked the Too-Much down — medication does not reach it, time only waits it out, but the wheel quiets it. In the after-calm — not the flood, the quiet behind it — her hands do what they have always half-done: they rebuild a detail before her mind catches up. She finds she has set a trimmed cup to an exact spot on the bench and a form a hair off-true beside it, her hands recreating the spatial wrongness of Neil's cottage. The clay hands her not an answer but a question: someone reset that room by habit — whose? For the first time the Too-Much has worked with her, calm and useful, and cost no one. She cannot stop after all — but this time she will look before she speaks.

### Chapter Structure
- **Start / Desire:** Maggie wants to quit — to stop being the woman who sees too much and hurts people for it.
- **Pressure / Obstacle:** The worst Too-Much of the book, plus the shame that there is nothing left to investigate and no one left who trusts her.
- **Turn / Change:** At the wheel the Too-Much quiets; her hands surface the cottage's spatial wrongness as a question, not a verdict. The gift turns disciplined for the first time.
- **Texture / Pleasure Layer:** The studio at night, the wheel's hum, wet clay, Glaze asleep on the apron, the kiln ticking as it cools.
- **Hook:** She cannot stop — but she will bring Pruitt a habit, not a hunch.

### Track Movement
- **M:** No new clue. Recombines the planted staged-scene details (ch 7) into a precise spatial question; redirects the hunt from "who hated Neil" to "whose habit reset the room." Fair-play intact — the clay yields the question, later chapters yield the proof.
- **P:** The gift's turning point. Clay/centring established as the only reliable relief from the Too-Much; the gift becomes usable without performance or social cost. The concentrated Ordeal→turn.
- **R:** Quiet. Glaze present; Cal's post-argument distance felt but not worked. Romance rests.
- **B:** The same calm wheel-work that yields her repaired-glaze signature also yields the insight — craft and gift fuse.

---
```

- [ ] **Step 4: Renumber inline cross-references**

In the same file, update every inline chapter citation that denotes a scene at old ch ≥ 18 by +1, per the Step-1 map. Cover: the `# Track Map at a Glance` section (Mystery/Personal/Romance/Business track ranges and parentheticals), the `# Drafting Checks by Act` section (e.g. "End of Act II — Chapter 22" → 23; "Final Movement — Chapters 23–28" → 24–29), and in-summary callbacks (e.g. "the click (ch 18)" → 19, "Cobber places Mary (ch 19)" → 20, "ch 21 papers" → 22, "ch 22 Pruitt" → 23, "ch 23 rupture" → 24, "ch 24 arrest" → 25, "ch 27", "ch 28"). Leave references to scenes at old ch ≤ 17 unchanged (incl. ch 7 staged-scene callbacks).

- [ ] **Step 5: Verify chapter count**

Run: `grep -cE '^## Chapter [0-9]' input/book-01/outline.md`
Expected: `29`. (This is the same `^## Chapter [0-9]` pattern the statusline counts, so a count of 29 here means the statusline total will read 29 once `total_chapters` is set to 29 in Task 3.)

- [ ] **Step 6: Commit**

```bash
git add input/book-01/outline.md
git commit -m "feat(book-01): insert Ordeal chapter (new ch 18) and renumber outline to 29"
```

---

### Task 3: Renumber the whodunit ledger and re-lock the mystery

**Files (Modify):** `series/whodunit/book-01.yaml`; (Delete) `.penny/locks/book-01.mystery.lock`

**Interfaces:**
- Consumes: the reconciliation map from Task 2 Step 1.
- Produces: a validated, re-locked ledger with `total_chapters: 29`, `reveal_chapter: 25`, and clue payoffs shifted, on which the book-level fair-play gate passes.

- [ ] **Step 1: Edit the ledger**

In `series/whodunit/book-01.yaml` apply, per the reconciliation map:
- `total_chapters: 28` → `29`
- `reveal_chapter: 24` → `25`
- `culprit_first_appearance_chapter: 5` → unchanged
- `clue-erasure`: `plant_chapter` 7 unchanged; `pays_off_chapter` 19 → `20`
- `clue-car-on-street`: plant 11 unchanged; `pays_off_chapter` 22 → `23`
- `clue-old-records`: plant 15 unchanged; `pays_off_chapter` 21 → `22`
- `clue-cobber-dawn-witness`: plant 2 unchanged; `pays_off_chapter` 20 → `21`
- `rh-saffron` (plant 9), `rh-beryl` (plant 10), `rh-faye` (plant 13): unchanged
- alibi `saffron`: reconcile first — the scene is Saffron's public collapse at outline ch 17 (stays 17); set the ledger `chapter` to the reconciled value (17 if it denotes the collapse; otherwise its old value +1 if it genuinely denoted an old ≥18 scene). Record the decision in the commit body.
- alibi `beryl-foss` (14), `faye` (13), `vincent-calloway` (14), `cobber` (11), `mary-burrell` (7): unchanged
- Add NO new rows.

- [ ] **Step 2: Delete the stale lock**

```bash
rm .penny/locks/book-01.mystery.lock
```

- [ ] **Step 3: Re-mint the lock (validates fairplay + lexicon)**

Run: `python3 scripts/preflight.py lock-mystery 01`
Expected: exit 0 and the lock file recreated at `.penny/locks/book-01.mystery.lock`. A non-zero exit means the edited ledger does not validate — fix the ledger (do not hand-write the lock) and re-run.

- [ ] **Step 4: Verify the fair-play checker (standalone confirmation)**

Run: `python3 scripts/fairplay_check.py series/whodunit/book-01.yaml`
Expected: no `BLOCKING:` lines; reveal_chapter 25 in range, all necessary clues planted before 25, culprit first-appears before 25. (Note: `preflight.py lock-mystery` in Step 3 already runs `check_fairplay` as a blocking gate, so a successful Step 3 implies this passes; this step is an explicit re-confirmation.)

- [ ] **Step 5: Commit**

```bash
git add series/whodunit/book-01.yaml .penny/locks/book-01.mystery.lock
git commit -m "feat(book-01): renumber whodunit ledger (reveal 25, total 29); re-lock mystery"
```

Note: `.penny/` is gitignored; the lock will not stage. That is expected — commit only the ledger; the lock is local runtime state.

---

### Task 4: Renumber chapter references in continuity, bible, arc-ledger, solution

**Files (Modify):**
- `series/continuity/**` (character, thread, location prose bodies + any canon-meta `active_window` ranges referencing chapters ≥ 18)
- `input/series/series-bible.md`
- `series/arc-ledger.md`
- `output/book-01/mystery-solution.md`

**Interfaces:**
- Consumes: the reconciliation map from Task 2 Step 1.
- Produces: all narrative chapter references consistent with the 29-chapter outline.

- [ ] **Step 1: Inventory chapter references ≥ 18**

Run: `grep -rnE "ch(apter)?[ -]?(1[89]|2[0-9])" series/continuity/ series/arc-ledger.md input/series/series-bible.md output/book-01/mystery-solution.md`
Review each hit; classify whether it denotes a scene at old ch ≥ 18 (shift +1) or ≤ 17 (leave).

- [ ] **Step 2: Apply +1 to the qualifying references**

Edit each qualifying reference (e.g. ch 18→19, 19→20, 20→21, 21→22, 22→23, 23→24, 24→25, 27→28, 28→29). Include `active_window:` ranges in `<!-- canon-meta: {...} -->` headers whose upper/lower bound is ≥ 18. Leave ch ≤ 17 references (ch 2, 5, 7, 11, 13, 14, 15 staged-scene/clue callbacks) unchanged.

- [ ] **Step 3: Verify parsers + suite**

Run: `python3 -m pytest -q`
Expected: all pass (canon-meta and frontmatter still parse after edits).

- [ ] **Step 4: Commit**

```bash
git add series/ input/series/series-bible.md output/book-01/mystery-solution.md
git commit -m "feat(book-01): +1 chapter refs (>=18) across continuity, bible, arc-ledger, solution"
```

---

### Task 5: Final cross-consistency verification

**Files:** none (verification only)

- [ ] **Step 1: No stray old term**

Run: `grep -rn "Migraine Sight" . --include="*.md" | grep -v "\.reviews/"`
Expected: no matches (regenerated `.reviews/` sidecars may still contain it until next re-gate — acceptable).

- [ ] **Step 2: Chapter count + reveal coherence**

Run: `grep -cE '^## Chapter [0-9]' input/book-01/outline.md` → `29`.
Run: `grep -E "total_chapters|reveal_chapter" series/whodunit/book-01.yaml` → `29` and `25`.

- [ ] **Step 3: Gates green**

Run: `python3 scripts/preflight.py lock-mystery 01` (lock still validates) and `python3 -m pytest` (full suite green).
Expected: lock present/valid; `N passed`.

- [ ] **Step 4: Spec/plan checkbox sweep**

Confirm every spec Part (1 chapter, 2 rename, 3 renumber, 4 re-lock, 5 verification) maps to a completed task. Update `HANDOFF.md` if ending the session here.
