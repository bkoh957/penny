# Penny Phase 2a — Deterministic Tier-3 Checkers — Design

**Status:** Draft v1 · **Date:** 2026-06-19 · **Phase:** 2a of the Review Bus
(Phase 2 split into 2a deterministic checkers → 2b inspector bus).
**Source:** brainstorming session 2026-06-19; design `penny-design-v3.md` §6, §8,
§8a; PRD `penny-PRD-v3.md` P0.3, P0.4, P0.10.

---

## 1. Scope & Architecture

Phase 2a builds the two **deterministic Tier-3 checkers** of the Review Bus, plus
the shared verdict writer they use. These are pure mechanism — no LLM, no
judgment — producing evidence/verdicts the Phase 2b inspector bus consumes.

**In scope:**
- `scripts/voice_drift.py` — statistical prose checker (sentence-length variance,
  lexical repetition, the 7 AI-tic categories of `ai-tics-detection.md`). Operates
  on **chapter text**. Useful immediately.
- `scripts/fairplay_check.py` — whodunit-ledger **consistency** checker (required
  clues scheduled before the reveal; culprit introduced early enough). Operates on
  the **structured per-book ledger**. Built/tested against fixtures in 2a;
  activates for real once `/plan-mystery` (Phase 3) authors ledgers.
- `scripts/penny_verdict.py` — small shared helper that writes a verdict file in
  the agreed envelope, so the format lives in one place (reused by 2b inspectors).

**Explicitly out of scope (Phase 2b):** Tier-1 blind inspector sub-agents and
their rubrics, the `review-chapter` command/orchestration, the two-signal conflict
resolution, and the prose-planting fairplay inspector. 2a produces *checkers that
write verdicts*; 2b produces *the bus that dispatches inspectors and computes the
gate*.

**Reuse & dependencies:** stdlib `re`, `json`; reuses `penny_meta.py` for flat
frontmatter; honors the Phase 1 `output/book-NN/chapters/ch-NN.reviews/` location
and `BLOCKING:` convention. **Adds PyYAML** — Penny's first third-party runtime
dependency — for nested human-edited data (see §5). Each checker is a standalone
CLI, independently testable, which is exactly how 2b's `review-chapter` will invoke
them.

---

## 2. The Verdict Envelope

Every verdict is a markdown file in `output/book-NN/chapters/ch-NN.reviews/`, named
by producer (`voice-drift.md`, `fairplay.md`). Shared shape, written by
`penny_verdict.py`:

```
---
producer: voice_drift.py
kind: deterministic-checker        # vs "inspector" in 2b
target: book-01/ch-07
schema: penny-verdict/1
---
BLOCKING: <one line per blocking issue>     # 0+ lines; counted by the status line + gate
- <non-blocking violation / evidence>       # weighed by the 2b inspector
metrics: { ... }                            # producer-specific structured data
evidence:
  - { ... }                                 # sampled spans (see §3)
```

- Frontmatter is `penny_meta.py`-parseable. Blocking issues are `^BLOCKING:` lines
  (Phase 1 convention, uniform across all producers). The gate counts `BLOCKING:`
  lines regardless of producer.
- `score: 1-5` is **inspector-only** (2b). Deterministic checkers emit
  metrics + flags, never a subjective score.

**Blocking vs. evidence — the central rule (from `ai-tics-detection.md`):**
- **`fairplay_check.py` MAY emit `BLOCKING:` lines.** Fair-play is a hard,
  deterministic requirement (success metric: 100%). An unfair plan blocks directly.
- **`voice_drift.py` MUST NOT emit `BLOCKING:` lines.** Its flags are *evidence*;
  *"the blocking decision stays with the inspector."* Voice-drift contributes 0 to
  the gate's blocking count. **This is a hard rule** — a wildly-over-threshold count
  is still evidence, not a block.

---

## 3. `voice_drift.py`

**Input:** a chapter text file. **Output:** `voice-drift.md` (evidence + metrics, no
`BLOCKING:` lines). **CLI:**
`python3 scripts/voice_drift.py <chapter.md> [--out <reviews-dir>] [--config <path>]`.

### 3.1 What it computes (three groups)

1. **Statistical rhythm** (design §6): sentence-length **variance** (flag if stdev
   below `sentence_variance.min_stdev` → monotone); **lexical repetition** (flag
   over-repeated content words and repeated sentence openers).
2. **The 7 AI-tic categories** (`ai-tics-detection.md`): bodily reactions, wave /
   emotional-noun templates, "something" language, filtering verbs, soft qualifiers
   (+ the ≥2-in-one-sentence cluster rule), cinematic fragments (≥3 consecutive
   sub-4-word sentences, ≥2 verbless), emotional-metaphor pool.
3. Each detected item yields an **evidence span** (see §3.4).

The metaphor-pool item is **keyword-count only** in 2a (the keyword-vs-LLM
`[DECISION]` stays deferred; keyword-count is the Book-1 seed).

### 3.2 Patterns in script, thresholds + lists in config

- `voice_drift.py` holds detection logic: `PATTERNS = {tic_id: compiled regex /
  closed word-set}` plus the variance/repetition algorithms. A header comment marks
  this boundary: *detection logic here (stable algorithm); tunable values in config.*
- `config/voice-pack/ai-tics-config.yaml` (PyYAML) holds the **tunable seeds +
  compounding data**: per-tic `{per_1k, flag_at, ...}`, `sentence_variance.min_stdev`,
  and the hand-grown `banned_phrases` / `metaphor_pool` lists (P1.3 — grow each book).

### 3.3 Config loading — authoritative, fail loud

- `--config` omitted → single documented default path
  `config/voice-pack/ai-tics-config.yaml`.
- Path given but unreadable/malformed, **or** the default missing → **hard-fail**
  with a clear message. **No hardcoded threshold fallback** — patterns live in code,
  thresholds/lists *always* come from config. (Preserves the genre-config principle.)

### 3.4 Frontmatter strip & sentence segmentation (the accuracy risks)

- **Frontmatter strip:** remove only a leading `---…---` block (via `penny_meta`
  semantics), keep all prose. A chapter with **no** frontmatter must not crash
  (returns text unchanged). Exclude non-prose lines from segmentation: markdown
  headings (`#…`) and horizontal-rule / scene-break markers (`***`, `* * *`, `---`
  used as a rule).
- **Sentence segmentation is the key accuracy risk** (variance + cinematic-fragment
  detection depend on it; dialogue-dense cozy prose is adversarial). Dependency-free
  heuristic: split on `[.!?]+` followed by whitespace + an opening quote/capital,
  with (a) an **abbreviation guard set** (`Mr. Mrs. Ms. Dr. St. …`), (b) **no split
  inside paired quotes** (dialogue), (c) ellipsis `…`/`...` and em-dash treated as
  **non-terminal**. **Known failure modes are documented** in the script and spec;
  the test corpus includes adversarial dialogue. Downstream inspectors treat counts
  as signal, not gospel.

### 3.5 Evidence-span contract

Each span: `{ tic_id, span_text, line }` (line number lets the inspector locate it
in the chapter). **Capped at first 5 spans per tic + the total count** (the count is
the signal; spans are a sample). Per-tic structured record preserves the Tier-A
contract `{ tic_id, count, threshold, density_per_1k, flagged, evidence_spans }`.

---

## 4. `fairplay_check.py`

**Input:** a structured per-book whodunit ledger. **Output:** `fairplay.md` (MAY
emit `BLOCKING:` lines). **CLI:**
`python3 scripts/fairplay_check.py <ledger.yaml> [--out <reviews-dir>]`.

Operates on the **ledger, not the prose** (ledger-consistency). Whether the drafter
actually planted a scheduled clue in the scene is the 2b `inspector-fairplay` job.

### 4.1 Assertions

**Blocking (each failure → a `BLOCKING:` line):**
- Every `necessary: true` clue has a `clue_schedule` entry **and**
  `plant_chapter < reveal_chapter` (planted-before-reveal). Missing/late → BLOCKING.
- **Culprit floor (non-negotiable):** `culprit_first_appearance_chapter`
  (on-page) `< reveal_chapter`. Else BLOCKING.
- **Culprit seed (tunable):** `culprit_first_appearance_chapter ≤
  round(culprit_by_fraction × total_chapters)` (default `culprit_by_fraction: 0.5`
  in `run-config.md`). Else BLOCKING.
- **Well-formed:** required fields present, chapters numeric and in range
  (`1..total_chapters`, reveal ≤ total); `culprit` id resolves in
  `series/continuity/characters/`. Else BLOCKING (a malformed locked ledger is
  itself a fairness failure that must not silently pass).
- **Auditable culprit gap:** the culprit has at least one `alibi_grid` entry with
  `holds: false` — a gap that makes them catchable. A culprit whose alibi always
  holds is an unsolvable, unfair mystery → BLOCKING. (This is the minimal,
  fairness-relevant alibi assertion; fuller alibi/timeline internal-consistency
  checking is deferred — see §8.)

**Evidence (non-blocking `-` lines, for showrunner context/override):**
- `culprit_first_mention_chapter < culprit_first_appearance_chapter` (mentioned
  before on-page) — context for an override decision.
- A red herring with `must_not_cheat: false`, or any clue/herring scheduled at/after
  the reveal.

### 4.2 Filing the verdict

Fairplay is book-level but matters at the gate of the **reveal chapter**, so the
default `--out` is that chapter's reviews dir
(`output/book-NN/chapters/ch-<reveal>.reviews/fairplay.md`). Exact wiring is a 2b/3
concern; 2a writes wherever `--out` points, defaulting as above.

---

## 5. Config, Schema & the Two-Reader Boundary

Penny now has **two structured-data readers**, with an explicit boundary so it never
blurs:

| Reader | Handles | Files |
|---|---|---|
| `penny_meta.py` (flat, stdlib) | flat `key: value` + inline lists | continuity entry frontmatter (`id/type/links`), `run-config.md` yaml-blocks |
| **PyYAML** (nested, new dep) | nested human-edited maps/lists | `config/voice-pack/ai-tics-config.yaml`, `series/whodunit/book-NN.yaml` |

**Rule:** *flat → `penny_meta`; nested human-edited → PyYAML.* We do **not** retire
`penny_meta.py` (Phase 1 depends on it); we add PyYAML only where the data is
genuinely nested and hand-edited. PyYAML is justified because the whodunit ledger is
authored, edited, and **locked by the showrunner by hand** — JSON's no-comments /
trailing-comma fragility is hostile there, and `central_deception`/alibi notes want
multiline strings.

### 5.1 `config/voice-pack/ai-tics-config.yaml`

```yaml
bodily_reaction:   { per_1k: 2, flag_at: 3 }
wave_templates:    { per_1k: 1, flag_at: 2 }
something_language:{ per_1k: 1, flag_at: 2 }
filtering_verbs:   { per_1k: 3, flag_at: 4 }
soft_qualifiers:   { per_1k: 4, flag_at: 5, cluster_in_sentence: 2 }
cinematic_fragments: { max_clusters_per_chapter: 1 }
metaphor_pool_rule:  { same_domain_flag_at: 3, total_flag_at: 5 }
sentence_variance: { min_stdev: 4.0 }
lexical_repetition: { opener_repeat_flag_at: 3, content_word_per_1k_flag_at: 8 }
banned_phrases: []     # grows each book (P1.3)
metaphor_pool: [ wave, storm, weight, knife, thread, shadow, flame, spark, abyss, hollow ]
```

`config/voice-pack/ai-tics-detection.md` is **rewritten to prose-only**, declared
**non-parsed**, and points at the authoritative `.yaml`. Where a threshold value
appears in the prose, the `.yaml` is authoritative.

### 5.2 `series/whodunit/book-NN.yaml`

```yaml
book: 01
locked: true
total_chapters: 24
reveal_chapter: 22
culprit: margaret                       # ledger id; must resolve in continuity/characters/
culprit_first_appearance_chapter: 2     # ON-PAGE — assertion basis
culprit_first_mention_chapter: 1        # named only — evidence for override
victim: edwin-tilley
central_deception: |
  ...multiline ok in YAML...
clue_schedule:
  - { id: clue-torn-ticket, plant_chapter: 5, pays_off_chapter: 22, necessary: true }
red_herrings:
  - { id: rh-the-neighbour, plant_chapter: 7, misleads_toward: "...", must_not_cheat: true }
alibi_grid:
  - { suspect: margaret, chapter: 12, alibi: "...", holds: false }
```

Drafter consumes only a **per-chapter slice** of this (its clue obligations), never
the whole ledger (design §5a). `series/whodunit-ledger.md` becomes a **human doc**
(how the schedule works, narrative notes) — **never parsed**.

### 5.3 `run-config.md` addition

```yaml
culprit_by_fraction: 0.5    # fairplay seed — culprit on-page by this fraction of the book; tunable
```

---

## 6. Testing Strategy (TDD)

- **`penny_verdict.py`:** unit-test the writer — frontmatter round-trips via
  `penny_meta`, `BLOCKING:` lines emitted at line start, body sections present.
- **`voice_drift.py`:** prose fixtures — clean (no flags), tic-saturated (each
  category flags at its threshold), monotone (variance flag), and an **adversarial
  dialogue fixture** locking segmentation (`"'I'm fine,' she said."` = 1 sentence;
  `Mrs. Pennington` not split; ellipsis/em-dash non-terminal). Assert counts,
  evidence cap (≤5 spans + total), config-missing hard-fail, and **zero `BLOCKING:`
  lines**.
- **`fairplay_check.py`:** fixture ledgers — fair (clean, no BLOCKING),
  necessary-clue-after-reveal (BLOCKING), culprit-at-reveal (floor BLOCKING),
  culprit-past-fraction (seed BLOCKING), malformed/missing-field (BLOCKING),
  unresolved culprit id (BLOCKING), mention-before-appearance (evidence line). Assert
  `BLOCKING:` presence/absence and the evidence lines.

---

## 7. File Structure

**Create:**
- `scripts/penny_verdict.py` — shared verdict writer.
- `scripts/voice_drift.py` — statistical prose checker.
- `scripts/fairplay_check.py` — ledger-consistency checker.
- `config/voice-pack/ai-tics-config.yaml` — tic thresholds + compounding lists.
- `series/whodunit/book-01.yaml` — example/fixture ledger.
- `requirements.txt` — `PyYAML`.
- `tests/test_penny_verdict.py`, `tests/test_voice_drift.py`,
  `tests/test_fairplay_check.py` + fixtures (under `tests/fixtures/`).

**Modify:**
- `config/voice-pack/ai-tics-detection.md` — rewrite to prose-only, non-parsed,
  pointing at the `.yaml`.
- `run-config.md` — add `culprit_by_fraction`.
- `README.md` — dev note: PyYAML dependency + `pip install -r requirements.txt`.
- **Design docs:** `penny-design-v3.md` §2 (repo layout: `series/whodunit/` per-book
  yaml; `series/whodunit-ledger.md` now human-doc) and §5a (per-book ledger path);
  `penny-PRD-v3.md` P0.10 (ledger path).

**Out of scope (2b):** inspector agents, rubrics, `review-chapter`, conflict
resolution.

---

## 8. Open Items / Deferred

- Metaphor-pool detection: keyword-count in 2a; LLM-classifier graduation remains a
  `[DECISION]` (design §8a).
- Prose-planting fairplay verification → 2b `inspector-fairplay`.
- **Fuller alibi/timeline internal-consistency checker** (design §6's separate
  "alibi/timeline checker": cross-validating all suspects' alibis against the
  timeline) → deferred. 2a's fairplay does only the minimal culprit-gap assertion
  (§4.1).
- Exact verdict filing/wiring into the gate → 2b `review-chapter`.
- `voice_drift` runs on draft or final text → decided by 2b orchestration; the script
  itself is text-source-agnostic.
