# Tommy Quill Ghost — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Maggie's ex-husband Tommy Quill a felt presence throughout Book 01 — an off-page ghost whose belittling lines surface as short flashback bursts that sting (ch1–18), then spur (ch19–29) — without ever putting him on the page.

**Architecture:** Two phases. **Phase A (Tasks 1–7)** locks Tommy into the swappable data layer — a new ghost character file, edits to Maggie's bible / the C-internal / gift / series-seeds threads / series-bible, a style-sheet treatment rule, and outline burst-beats. These are direct file edits to `series/` and `input/`, verified by grep invariants + the existing pytest suite (which parses continuity via `penny_meta`). **Phase B (Tasks 8–10)** is the prose retrofit: seed bursts into ch-01/02 (finalized → re-finalize through the gate) and the ch-03–05 drafts, via the normal `/review-chapter` → `/finalize-chapter` pipeline.

**Tech Stack:** Markdown continuity files with `<!-- canon-meta: {...} -->` headers (parsed by `scripts/penny_meta.py`); the Penny per-chapter pipeline (`/review-chapter`, `/finalize-chapter`); `python3 -m pytest` (~273 tests, stdlib + PyYAML).

## Global Constraints

- **Cozy register only.** Tommy's lines are emotional/diminishing condescension — never slurs, never violence, never sexual menace. "I'm just being honest, love" plausibility.
- **Off-page rule (Book 01).** Tommy never appears: no phone call, letter, or scene. He exists only as quoted memory in Maggie's interiority.
- **Treatment.** Flashback bursts are 1–2 sentences of *quoted Tommy* in *italics*, no scene-break, surfacing at a trigger.
- **Origin invariant (do not break):** migraines since 19 / "her whole life" stays true. The change is that after 40 the Too-Much sharpened from *recording* to *reading*; Tommy's affair was its first decode. Do NOT open the gift's full origin (that stays Artie's series mystery).
- **Pivot invariant:** the sting→spur turn lands at the ch19 "click" (same beat that solves the murder). Coda at ch29 = voice gone quiet + she stamps her pots "Quill" (name reclaim).
- **canon-core restraint:** `canon-core.md` is loaded every chapter — add at most one short clause.
- **Prose conventions:** Australian spelling (`-ise`, colour, towards); spaced em-dashes (space — space); spell out whole numbers in narration.
- **OUTSIDER narration:** Maggie's narration stays standard English. Tommy's quoted lines are remembered dialogue, so dialect/idiom rules don't apply to them — but keep his voice flat-corporate, not folksy.

---

### Task 1: Create the Tommy Quill ghost character file

**Files:**
- Create: `series/continuity/characters/thomas-quill.md`

**Interfaces:**
- Produces: continuity entry `id: thomas-quill`, linked from `maggie-quill`, `c-internal`, `series-seeds`. Other tasks reference this id in their `links:`.

- [ ] **Step 1: Write the character file**

Create `series/continuity/characters/thomas-quill.md` with exactly:

```markdown
---
id: thomas-quill
type: character
links: [maggie-quill, c-internal, series-seeds]
---
<!-- canon-meta: {id: thomas-quill, refs: [], active_window: "1-13", last_referenced: null, reconfirmed_at: null, keep_reason: "off-page ex-husband; the ghost-voice device"} -->
# Thomas "Tommy" Quill

**Full name:** Thomas Quill. **Known as:** Tommy. **Role:** Maggie's ex-husband. **Off-page** — never appears in Book 01.

Real-estate broker. Jealous of Maggie's competence and quietly threatened by it. A belittler of the plausible kind: never a raised voice or a raised hand, just the steady "I'm only being honest, love" condescension that corrodes precisely because it sounds reasonable. He is the voice that taught Maggie to take up less space.

**The end of the marriage.** The affair was real. When Maggie's waking gift (the Too-Much sharpening from recording to *reading* after forty) decoded it — the first thing it ever made her understand — she was willing to forgive him. He turned it into anger and divorced her. The gift and the divorce are one wound: she left because she finally *saw*.

**The kept name.** Maggie is still Maggie **Quill**. She kept his surname. The Book 01 finale reclaims it (ch 29: she stamps her finished pots "Quill" — the name made hers, not his).

**The device (the ghost).** Tommy lives in Book 01 only as short flashback bursts — one or two sentences of his actual belittling speech, surfacing in Maggie's head at moments of confidence. Sting from ch1–18; from the ch19 click the same lines spur her instead. The wheel is the one place his voice cannot reach. Cross-ref: [[c-internal]], [[gift]].

**Register samples (calibration, not canon dialogue):**
- *"You're not really a 'pottery' person, Mags. You're a person who likes the idea of it."*
- *"Leave the clever stuff to people who do it for a living."*

**Series status.** A *possible* future on-page presence; whether Tommy ever returns is deliberately unresolved (a series-seed). Book 01 never lets him in the room.

## Knowledge state
*Off-page.* Not present in Book 01; holds no knowledge of Pelican's Crook events.

## Established facts
- Real-estate broker. Maggie's ex-husband; he initiated the divorce.
- Had an affair during the marriage; Maggie discovered it when the Too-Much began to read rather than only record.
- Surname Quill; Maggie kept the married name.
```

- [ ] **Step 2: Verify it parses and the suite stays green**

Run: `python3 -m pytest -q`
Expected: same pass count as before the change (~273 passed), no errors from continuity parsing.

- [ ] **Step 3: Verify the file is well-formed**

Run: `grep -c "canon-meta" series/continuity/characters/thomas-quill.md`
Expected: `1`

- [ ] **Step 4: Commit**

```bash
git add series/continuity/characters/thomas-quill.md
git commit -m "feat(book-01): add Tommy Quill — off-page ex-husband ghost character"
```

---

### Task 2: Wire Tommy into Maggie's bible

**Files:**
- Modify: `series/continuity/characters/maggie-quill.md`

**Interfaces:**
- Consumes: `thomas-quill` id (Task 1).
- Produces: `tommy-quill` link in Maggie's `links:`; the relationship/origin/flaw text the prose tasks lean on.

- [ ] **Step 1: Add the link**

In the frontmatter, change:

```
links: [the-wheelhouse, b-romance, c-internal, gift, a-murder]
```
to:
```
links: [the-wheelhouse, b-romance, c-internal, gift, a-murder, thomas-quill]
```

- [ ] **Step 2: Add the relationship + the kept-name detail**

After the first paragraph (ends "...uncertain about her new life."), insert a new paragraph:

```markdown
**The ex-husband (the ghost).** Married to Thomas "Tommy" Quill — real-estate broker, jealous of her competence, a belittler of the plausible "I'm only being honest" kind. He had the affair; when her waking gift read it she was willing to forgive, and it was he who turned angry and divorced her. He never appears in Book 01: he lives only as short flashback bursts of his belittling lines surfacing in her head. She kept his surname — she is still Maggie **Quill** — and the name is reclaimed at the ch-29 kiln finale. Cross-ref: [[thomas-quill]].
```

- [ ] **Step 3: Tie the origin to the existing Too-Much paragraph**

In the **The Too-Much** paragraph, after "Meaning arrives later, usually when she is pain-free and doing something mundane." insert:

```
 The migraines have been with her since nineteen, but the *reading* — meaning, not just detail — only sharpened after forty; the first thing it ever decoded was Tommy's affair.
```

- [ ] **Step 4: Tie the flaw to the voice**

In the **Character flaw** paragraph, after "...performs her sharpness for approval." insert:

```
 Tommy's belittling voice is the engine of this: she shrank to fit him for years, and "taking up space" is exactly what his remembered lines punish.
```

- [ ] **Step 5: Verify the origin invariant survived**

Run: `grep -i "since she was nineteen\|since nineteen" series/continuity/characters/maggie-quill.md`
Expected: at least one match (migraines-since-19 still asserted).

- [ ] **Step 6: Commit**

```bash
git add series/continuity/characters/maggie-quill.md
git commit -m "feat(book-01): wire Tommy into Maggie's bible (relationship, kept name, first-decode origin)"
```

---

### Task 3: Update the C-internal, gift, and series-seeds threads

**Files:**
- Modify: `series/continuity/threads/c-internal.md`
- Modify: `series/continuity/threads/gift.md`
- Modify: `series/continuity/threads/series-seeds.md`

**Interfaces:**
- Consumes: `thomas-quill` id (Task 1).
- Produces: the mechanism/pivot/seed text the outline (Task 7) and prose (Phase B) implement.

- [ ] **Step 1: c-internal — add Tommy link and the mechanism**

In `c-internal.md` frontmatter, change `links: [maggie-quill, the-wheelhouse]` to `links: [maggie-quill, the-wheelhouse, thomas-quill]`.

Then append, after the existing final bullet ("The binge (ch 5)..."):

```markdown
- **The Tommy-voice is the concrete mechanism of this arc.** "Apologising for taking up space" is literal: short flashback bursts of her ex-husband's belittling lines fire at confidence thresholds. Sting ch1–18; they **pivot to fuel at the ch19 click** (the sight that exposed Tommy becomes her strength); spur ch19–29. Coda ch29: the voice has gone quiet and she stamps her pots "Quill" — reclaiming the name. Cross-ref: [[thomas-quill]].
```

- [ ] **Step 2: gift — add the first-decode origin (light touch)**

In `gift.md`, after the existing sentence ending "Neither thread is closed in Book 01." append a new sentence to that paragraph:

```
 One origin fact is fixed without opening the larger mystery: the migraines are lifelong (since nineteen), but the gift only began to *read* rather than merely record after forty, and the first thing it ever decoded was her husband's affair — the read that ended the marriage.
```

- [ ] **Step 3: series-seeds — Tommy as a possible future presence**

In `series-seeds.md` frontmatter, change `links: [artie-selwood, vincent-calloway, saffron, the-lighthouse]` to `links: [artie-selwood, vincent-calloway, saffron, the-lighthouse, thomas-quill]`.

Add a 4th numbered seed before the Status line:

```markdown
4. **Tommy Quill, off-page.** Maggie's ex-husband is a felt presence in Book 01 but never appears. Whether he ever returns on-page — and what his reappearance would cost her hard-won quiet — is deliberately left open. Cross-ref: [[thomas-quill]]. Do NOT bring him on-page in Book 01.
```

- [ ] **Step 4: Verify links resolve and suite stays green**

Run: `python3 -m pytest -q`
Expected: ~273 passed, no parse errors.

Run: `grep -rl "thomas-quill" series/continuity/threads/`
Expected: lists `c-internal.md`, `gift.md`, `series-seeds.md`.

- [ ] **Step 5: Commit**

```bash
git add series/continuity/threads/c-internal.md series/continuity/threads/gift.md series/continuity/threads/series-seeds.md
git commit -m "feat(book-01): thread Tommy through c-internal (mechanism+pivot), gift (first-decode), series-seeds"
```

---

### Task 4: Enrich the divorce framing in the series bible

**Files:**
- Modify: `input/series/series-bible.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the bible-level framing that keeps the existing flaw-rhyme intact while introducing Tommy.

- [ ] **Step 1: Enrich the Background paragraph**

In `series-bible.md`, in the **Background.** paragraph, after "...a marriage that went stale." insert:

```
 The marriage was to Tommy Quill, a real-estate broker who was jealous of her and belittled her for years; the staleness was her shrinking to fit him until she stopped seeing her own life. He had an affair; when she finally saw it she offered to forgive, and he divorced her in anger.
```

- [ ] **Step 2: Preserve the flaw-rhyme paragraph**

In the paragraph beginning "The analogy earns its place..." (ends "...There is restraint to learn."), after "...staying in a stale marriage to feel safe" the existing text already carries the rhyme. Add one clause after "reaching for external validation instead of sitting with herself":

```
 — the same external validation Tommy trained her to crave by withholding it.
```

- [ ] **Step 3: Verify flaw-rhyme intact**

Run: `grep -i "external validation" input/series/series-bible.md`
Expected: at least one match (the rhyme survives, now Tommy-anchored).

- [ ] **Step 4: Commit**

```bash
git add input/series/series-bible.md
git commit -m "docs(series-bible): enrich divorce framing — Tommy explains why she stopped taking up space"
```

---

### Task 5: Add the flashback-burst treatment rule to the style-sheet

**Files:**
- Modify: `input/series/style-sheet.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the typographic convention every drafter/copy-editor follows for the bursts.

- [ ] **Step 1: Append the decision**

At the end of the `## Decisions` list in `style-sheet.md`, add:

```markdown
- Tommy-voice flashback bursts: rendered in *italics*, as one or two sentences of quoted ex-husband speech inside Maggie's narration, with no scene-break and no attribution tag (the reader learns whose voice it is from context/the first instance). Cozy register only — diminishing condescension, never abuse or threat. Keep each burst short (≤ two sentences). The wheel is the one place his voice never intrudes — never plant a burst mid-throwing.
- Characters: Thomas "Tommy" Quill (Maggie's off-page ex-husband; real-estate broker). Spelling locked for the series.
```

- [ ] **Step 2: Verify**

Run: `grep -c "Tommy-voice flashback" input/series/style-sheet.md`
Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add input/series/style-sheet.md
git commit -m "docs(style-sheet): flashback-burst treatment convention + lock Tommy Quill spelling"
```

---

### Task 6: One-clause canon-core reference (restraint check)

**Files:**
- Modify: `series/continuity/canon-core.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a single always-loaded reminder so drafters carry the device without loading Tommy's full file.

- [ ] **Step 1: Add one clause to the protagonist-fixed bullet**

In `canon-core.md`, in the **Margaret "Maggie" Quill** bullet, after "...she records everything and understands later." append:

```
 Her ex-husband Tommy (off-page) recurs only as short *italic* flashback bursts of his belittling lines — sting early, spur after the ch19 click.
```

Do not add anything else to canon-core (it taxes every chapter).

- [ ] **Step 2: Verify canon-core stayed tiny**

Run: `grep -c "^-" series/continuity/canon-core.md`
Expected: unchanged bullet count vs. before (the clause is appended to an existing bullet, not a new one).

- [ ] **Step 3: Commit**

```bash
git add series/continuity/canon-core.md
git commit -m "feat(book-01): one-clause Tommy reminder in canon-core (kept minimal)"
```

---

### Task 7: Add burst beats to the Book 01 outline

**Files:**
- Modify: `input/book-01/outline.md`

**Interfaces:**
- Consumes: the pivot/coda canon (Task 3).
- Produces: per-chapter burst beats the Phase-B prose tasks implement.

- [ ] **Step 1: Read the outline to find the anchor chapters**

Run: `grep -n "^#\|Chapter\|ch-\?[0-9]" input/book-01/outline.md | head -60`
Locate the beat blocks for chapters 1, 2, 5, 6, 7, 19, 24, 29 and a mid-book assertion chapter (around ch12–16).

- [ ] **Step 2: Add a Tommy-burst beat to each anchor chapter**

Under each anchor chapter's beats, add a single line in the outline's existing style. Use these exact intentions (phrasing to match surrounding outline voice):

- **ch1:** sting — a Tommy line undercuts the "quietly deranged" lease decision (she's signed for a studio he'd call a hobby).
- **ch2:** sting — when the town's warmth lands and she feels grateful, his voice mocks her needing to be liked.
- **ch5:** sting (deepest) — at the binge, his line about performing for approval lands as she overindulges.
- **ch6:** sting — hangover; his "told-you-so" register as the price comes due.
- **ch7:** sting — at the keystone flood she doubts her own perception; his line that she imagines things.
- **mid-book (assertion beat):** sting — she risks a deduction aloud; his "leave the clever stuff to people who do it for a living" fires.
- **ch19 (PIVOT):** the click solves it; a Tommy line surfaces and, for the first time, **powers** her — the sight that exposed him is now her strength.
- **ch24:** spur — Cal's wound tempts her to retreat into smallness; his voice says stay small, and she refuses.
- **ch29 (CODA):** the voice has gone quiet; she notices its absence and stamps her finished pots "Quill" — name reclaimed.

- [ ] **Step 3: Verify the pivot and coda are recorded**

Run: `grep -in "pivot\|reclaim\|quill" input/book-01/outline.md`
Expected: matches at the ch19 and ch29 beats.

- [ ] **Step 4: Commit**

```bash
git add input/book-01/outline.md
git commit -m "plan(book-01): outline burst-beats — sting (ch1-18), ch19 pivot, ch29 name reclaim"
```

---

### Task 8: Retrofit ch-01 (re-finalize through the gate)

**Files:**
- Modify: `output/book-01/chapters/ch-01.draft.md` (seed bursts, then re-run pipeline)
- Regenerate: `ch-01.lineedit.md` → `ch-01.copyedit.md` → `ch-01.final.md` via `/finalize-chapter`

**Interfaces:**
- Consumes: style-sheet treatment (Task 5), canon (Tasks 1–3).
- Produces: a re-finalized ch-01 carrying the two ch1 bursts.

**Prerequisite:** A non-drafting model must be reachable (the `/review-chapter` developmental-editor HALTS otherwise — see `CLAUDE.md`). Confirm `config/run-config.md` routing before starting.

- [ ] **Step 1: Seed the bursts in the draft**

Edit `output/book-01/chapters/ch-01.draft.md`. Add two short italic bursts at:
1. The lease-signing beat (existing line: signed "in a state she would later describe as quietly deranged"). Add, in her interiority, an italic Tommy line mocking the studio as a hobby — e.g. *"A shop. With your savings. Christ, Mags."*
2. The doorway/marriage beat (existing line: "...until the marriage was over and the filing had... come undone."). Add one italic belittling line that the "filing come undone" recalls.

Keep each ≤ two sentences, italics, no attribution tag, no scene-break. Do not place a burst inside any clay-throwing passage.

- [ ] **Step 2: Run the review gate**

Run: `/review-chapter 01 01`
Expected: `GATE: PASS` (zero blockers). If continuity/voice inspectors flag the bursts, address before finalize. The developmental-editor advisory may comment; it never blocks.

- [ ] **Step 3: Finalize**

Run: `/finalize-chapter 01 01 --commit` (or without `--commit` if `ledger_approval: review`, then review the diff and resume).
Expected: `ch-01.final.md` regenerated; ledger updated; commit made.

- [ ] **Step 4: Verify Tommy reads on the page**

Run: `grep -ci "mags\|tommy" output/book-01/chapters/ch-01.final.md`
Expected: ≥ 1 (a burst survives into the final).

---

### Task 9: Retrofit ch-02 (re-finalize through the gate)

**Files:**
- Modify: `output/book-01/chapters/ch-02.draft.md`
- Regenerate: `ch-02.lineedit.md` → `ch-02.copyedit.md` → `ch-02.final.md`

**Interfaces:**
- Consumes: Task 5, Tasks 1–3.
- Produces: re-finalized ch-02 with the ch2 burst.

**Prerequisite:** non-drafting model reachable (see Task 8).

- [ ] **Step 1: Seed the burst**

Edit `output/book-01/chapters/ch-02.draft.md`. At the beat where the town's warmth lands and Maggie feels "enormously and embarrassingly grateful," add one italic Tommy line mocking her need to be liked — e.g. *"Look at you, desperate to be everyone's favourite."* ≤ two sentences, italics, no tag.

- [ ] **Step 2: Run the review gate**

Run: `/review-chapter 01 02`
Expected: `GATE: PASS`.

- [ ] **Step 3: Finalize**

Run: `/finalize-chapter 01 02 --commit`
Expected: `ch-02.final.md` regenerated; commit made.

- [ ] **Step 4: Verify**

Run: `grep -ci "grateful" output/book-01/chapters/ch-02.final.md`
Expected: ≥ 1 (the grateful beat still present, now with its burst).

---

### Task 10: Seed bursts into the ch-03–05 drafts

**Files:**
- Modify: `output/book-01/chapters/ch-03.draft.md`, `ch-04.draft.md`, `ch-05.draft.md`

**Interfaces:**
- Consumes: Task 5, Tasks 1–3, Task 7 (outline beats).
- Produces: draft-stage bursts that ride the normal pipeline when these chapters finalize (do NOT force-finalize here unless that's the current frontier task).

- [ ] **Step 1: Seed per the outline beats**

For each draft, add the burst(s) named in Task 7 for that chapter (ch5 = the binge sting; ch3/04 = settling/assertion stings if the outline places one there). Italics, ≤ two sentences, no clay-throwing placement.

- [ ] **Step 2: Sanity-check the drafts still read**

Run: `grep -c "_.*_\|\*.*\*" output/book-01/chapters/ch-05.draft.md`
Expected: ≥ 1 (an italicised burst is present in ch-05, the binge chapter).

- [ ] **Step 3: Commit the draft seeds**

```bash
git add output/book-01/chapters/ch-03.draft.md output/book-01/chapters/ch-04.draft.md output/book-01/chapters/ch-05.draft.md
git commit -m "draft(book-01): seed Tommy bursts in ch-03-05 drafts (gate runs when finalized)"
```

---

## Notes on execution order

- **Phase A (Tasks 1–7) must land before Phase B (Tasks 8–10)** — the prose retrofit relies on the style-sheet rule, the canon, and the outline beats.
- Phase B is heavier (LLM pipeline, cross-model reachability). If a non-drafting model is not reachable, do Phase A now and defer Phase B to a session where it is — the device is fully locked as canon either way (this matches the spec's "retrofit" intent while respecting the gate).
