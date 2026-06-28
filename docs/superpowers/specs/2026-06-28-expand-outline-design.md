# Spec — `/expand-outline`: skeletal stubs → scene-breakdown outline

Saved: 2026-06-28 | Status: design approved, pending spec review

## Problem

The drafter consumes a per-chapter brief from `input/book-NN/outline.md`. The richest,
highest-quality brief is the **scene-breakdown format** (Chapters 01 and 02): per-scene
Location / Purpose / Beat flow / Emotional turn / Texture, plus Chapter Structure
Summary, Track Movement, Drafting Notes/Guardrails, and Line-Level Prompts. Authoring
that by hand for 29 chapters is expensive. The showrunner would rather write a
**skeletal stub** per chapter (a heading + a few sentences) and have the engine expand
each stub into the full scene-breakdown.

## Goal

A genre-agnostic engine feature that takes a skeletal chapter stub and generates the
detailed scene-breakdown brief for that chapter, consistent with the existing Ch 01/02
format and with the book's voice, setting, canon, and **sealed** mystery — without
leaking the solution into the drafter-visible outline.

## Non-goals

- Not a drafter. It produces an outline brief, not chapter prose.
- Not a mystery planner. It does not invent the whodunit or the clue schedule; those are
  upstream (`/plan-mystery`, `series/whodunit/book-NN.yaml`).
- Not a fairness judge. It never mints a lock or certificate.
- No quality scoring (no LLM-graded gate); the only deterministic check is the leak-guard.

## Pipeline position

```
write outline-skeleton.md (stubs)
  → /plan-mystery NN  +  preflight.py lock-mystery NN   (derive + seal + lock)
  → /expand-outline NN [MM]                              (THIS feature; context-rich)
  → /draft-chapter NN MM → /review-chapter → /finalize-chapter
```

The skeleton is the showrunner's high-level outline — enough for the whodunit to be
derived and locked. Expansion is a later enrichment that *requires the lock* because it
reads the sealed solution.

## Architecture (engine vs swappable)

Mirrors the `draft-chapter` + `drafter` split.

**Engine (fixed, never project-specific):**
- `.claude/commands/expand-outline.md` — the runbook (parse args, preflight, assemble
  context, dispatch agent, run leak-guard, advance marker).
- `.claude/agents/outline-expander.md` — the generative, **context-rich** role agent.
- `scripts/outline_guard.py` — deterministic post-generation leak scan.
- `preflight.py expand NN` — new subcommand: lock-present pre-check.

**Swappable (data):**
- `input/book-NN/outline-skeleton.md` — author-written stubs (input).
- `input/book-NN/outline.md` — generated scene-breakdown (output).
- `config/voice-pack`, `setting-pack`, `genre-pack`, `length-profile`,
  `series/continuity/canon-core.md`, `input/series/series-bible.md`,
  `series/whodunit/book-NN.yaml`, `output/book-NN/mystery-solution.md` — read by the agent.
- `config/leak-guard-lexicon.md` — the guilt-lexicon used by the leak-guard (genre-specific,
  therefore **config**, not hardcoded in `scripts/`).

## Input format — `outline-skeleton.md`

Frontmatter identical to `outline.md` (book, title, series, total_chapters). Then one
stub per chapter:

```markdown
## Chapter 05 — The Autumn Market

Beryl's market fills the hall and every suspect passes through Maggie's orbit. Lonely and
eager to be included, she reads the Faye/Iris feud too precisely and too publicly; the
crowd that was enjoying her goes quiet. Cal tells her to eat something; she hears it as
criticism. Hook: Faye is looking at Maggie with something more complicated than warmth.
```

A stub is just the `## Chapter NN — Title` heading plus a free-text blurb (1–6 sentences).
No fixed internal fields required.

## Output format — the canonical scene-breakdown template

Written into `input/book-NN/outline.md` for the chapter, matching Ch 01/02:

```
## Chapter NN — Title

### Overall Summary
<one paragraph>

### Scene 1 — <title>
**Location:** ...
**Purpose:** ...
**Beat flow:**
1. ...
**Emotional turn:** ...
**Texture to include:** ...

### Scene 2 — <title>
... (repeat for each scene)

### Chapter Structure Summary
- Start / Desire / Pressure / Obstacle / Turn / Change / Texture / Humour / Hook / Tommy burst

### Track Movement
- M / P / R / B

### Drafting Notes / Guardrails

### Possible Line-Level Prompts for Drafter
```

`### Overall Summary` is included (newer Ch 02 convention).

## Invocation & scope

- `/expand-outline NN MM` — expand a single chapter stub.
- `/expand-outline NN` — expand every skeleton chapter **not already in scene-breakdown
  form** in `outline.md`. "Already expanded" = that chapter's section in `outline.md`
  contains one or more `### Scene ` headings. This protects hand-crafted chapters
  (Ch 01/02) from being clobbered by a batch run.

When expanding a chapter, the engine **replaces** that chapter's entire section in
`outline.md` (or appends it if absent), preserving chapter order.

## The outline-expander agent (context-rich, generative)

Posture: generative; context-rich (the deliberate non-blind exception, like
`developmental-editor`). Reads:

- The chapter stub from `outline-skeleton.md`.
- `config/voice-pack`, `setting-pack`, `genre-pack`, `length-profile`.
- `series/continuity/canon-core.md` + the brief-derived ledger slice.
- `input/series/series-bible.md`.
- **Sealed:** `output/book-NN/mystery-solution.md` + `series/whodunit/book-NN.yaml`
  (culprit, clue_schedule, red_herrings, alibi_grid, reveal_chapter).

Writes the scene-breakdown for the chapter. Critically, it uses the sealed knowledge to
**place clue-planting and red-herring beats in the right scenes** and to **write accurate
Drafting Notes/Guardrails** (e.g. "plant the wrong-cup detail here, unspotlighted"; "keep
Neil alive; no early culprit implication") — but it **must withhold the solution from the
page**: it never names who the culprit is, never states the motive/central deception, and
never marks a clue as incriminating a named suspect. The guardrails it writes look exactly
like the existing Ch 01/02 ones.

This withholding is what preserves **drafter blindness**: the drafter reads `outline.md`
and must not learn whodunit, so the clue is present-but-unspotlighted (fair-play).

## The leak-guard (deterministic backstop)

Because the agent is context-rich and writes into a drafter-visible file, an LLM
instruction to "withhold the solution" is a *soft* gate. The leak-guard is the *hard* gate.

### Pre-check: `preflight.py expand NN`
Confirms `.penny/locks/book-NN.mystery.lock` exists (the sealed solution must be present
to be read). Nonzero exit + named predicate on failure. Reuses existing preflight idioms.

### Post-check: `scripts/outline_guard.py NN [MM]`
Co-occurrence heuristic. The culprit is a *visible character* (Mary Burrell appears from
ch 2), so the guard must detect the **solution**, not the **name**.

Algorithm:
1. Read `reveal_chapter` and `culprit` (slug) from `series/whodunit/book-NN.yaml`.
2. Build **culprit-name tokens**: de-slugify the culprit slug → display name and given
   name (`mary-burrell` → `"Mary Burrell"`, `"Mary"`). **Exclude the bare surname**
   when it is shared (e.g. "Burrell" is also Cal). Token set is name-only; red-herring
   suspects are explicitly *not* tokens (they are meant to be pointed at).
3. Read the **guilt lexicon** from `config/leak-guard-lexicon.md` (genre-specific, swappable):
   e.g. `killer, culprit, murderer, murdered, guilty, did it, avenged, avenging,
   incriminate, incriminating, perpetrator, confessed, the one who killed`.
4. For each chapter section in `outline.md` whose number `< reveal_chapter`:
   for each **paragraph** (the proximity unit — tighter than whole-chapter to keep
   false positives low), flag if a culprit-name token AND a guilt-lexicon term co-occur.
5. Any flag → print `BLOCKING: culprit '<name>' co-occurs with '<guilt term>' in
   ch-NN outline (paragraph: "...")` and exit nonzero. Clean → exit 0.

Notes:
- Proximity is **same paragraph** by default (not whole-chapter) to minimise false
  positives like a chapter that both features Mary and contains "the killer is still out
  there" in unrelated paragraphs. Tunable.
- Post-reveal chapters (`>= reveal_chapter`) are exempt — naming the culprit is allowed
  there.
- Case-insensitive matching; word-boundary aware.
- This catches the high-value concrete leak (name + guilt). A purely **thematic** leak
  (motive with no name) is out of scope for the deterministic guard and is the agent's +
  human reviewer's responsibility — consistent with how Penny's deterministic gates catch
  the concrete case and leave taste to the (blind) review layer.

## Command runbook (`expand-outline.md`) steps

0. Parse `book` and optional `chapter`.
1. `preflight.py expand NN` → abort on failure.
2. Write `.penny/current-stage` marker (`stage=EXPAND`).
3. Determine target chapters: one (`MM` given) or all not-yet-expanded (batch).
4. For each target chapter: assemble context (stub + packs + canon slice + sealed
   solution), dispatch `outline-expander`, write its output into `outline.md` (replacing
   that chapter's section, preserving order).
5. After writing, run `scripts/outline_guard.py NN [MM]`. On BLOCKING: surface the leak,
   leave the written outline in place for inspection, and **halt** (nonzero) — the
   showrunner fixes the leak (usually by editing the offending Drafting Note) and re-runs.
6. Advance marker (`stage=EXPANDED`).

## Testing (TDD, `tests/fixtures/`)

`scripts/outline_guard.py`:
- leak: a pre-reveal chapter paragraph with "Mary" + "killer" → exit nonzero, BLOCKING msg.
- clean: "Mary" + "lemon cutting" → exit 0.
- clean: red-herring suspect ("Saffron") + "guilty" in a pre-reveal chapter → exit 0
  (not the culprit).
- clean: shared surname "Burrell" (Cal) + guilt term → exit 0 (surname excluded).
- exempt: post-reveal chapter (>= 25) with "Mary" + "killer" → exit 0.
- proximity: name and guilt term in *different paragraphs* of the same chapter → exit 0.

`preflight.py expand`:
- lock present → exit 0; lock absent → nonzero with named predicate.

The command and agent are markdown runbooks and are not unit-tested (consistent with
`draft-chapter`/`drafter`).

## Open decisions resolved

- Output format: scene-breakdown (Ch 01/02). ✓
- Input: separate `outline-skeleton.md` → `outline.md`. ✓
- Scope: `NN MM` one / `NN` all-not-yet-expanded. ✓
- Expander context: context-rich (reads sealed solution). ✓
- Leak detection: co-occurrence heuristic, zero authoring. ✓
- Guilt lexicon lives in `config/` (swappable, genre-specific), not in `scripts/`. ✓
