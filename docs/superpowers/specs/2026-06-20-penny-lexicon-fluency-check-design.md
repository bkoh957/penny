# Penny — Lexicon Fluency Check (Tier-3) — Design

**Status:** Draft v1 · **Date:** 2026-06-20 · **Phase:** slots beside the Phase-2a
Tier-3 checkers; activates in the Phase-2b `review-chapter` bus; its lock-time
validator wires into the Phase-3 lexicon/setting-pack lock when that lands.
**Source:** brainstorming session 2026-06-20; design `penny-design-v3.md` §8, §9
(newcomer fluency dial, lexicon schema); PRD §P0.2; Phase-2a spec
`2026-06-19-penny-phase2a-deterministic-checkers-design.md` (evidence-vs-blocking
rule); canon-core demotion spec `2026-06-20-penny-canon-core-demotion-design.md`
§7.1 (the `canon-meta` header convention this realizes early).

---

## 1. The gap

The newcomer fluency dial (design §9) defines three narration-vocabulary stages:

- **OUTSIDER** (Books 1–2): narration is standard English; local idiom lives only in
  other characters' mouths.
- **SETTLING** (Books 3–6): moderate local idiom creeps into narration.
- **BELONGING** (Books 7–13): local idiom is fully integrated into narration.

Every lexicon entry carries `narration_ok_from_stage`, the literal field that couples
a term to this dial — "a `BELONGING`-tagged term in Book 2 narration is an automatic
reviewer flag" (design §9, PRD §P0.2). The field was designed to be checked.

**Nothing deterministic reads it.** `scripts/voice_drift.py` does not load the
lexicon; `inspector-voice` does not list it in scope. Enforcement of a deterministic,
countable rule silently falls to an inspector's general-knowledge recall of slang —
exactly the soft-where-it-should-be-hard gap the project closes everywhere else.

## 2. The fix, in the project's idiom

A Tier-3 **evidence-only** checker, `scripts/lexicon_check.py`, deterministically
detects premature out-of-stage terms in narration, **plus** widening
`inspector-voice`'s input scope. **Both, not either:** the script makes detection
exhaustive (it will not miss a tagged term the way fuzzy recall does); the inspector
keeps the contextual blocking call.

The evidence-vs-blocking split is the one the Phase-2a spec already drew:
`fairplay_check.py` MAY emit `BLOCKING:` (it reads the locked structured ledger, where
a violation is unambiguous); `voice_drift.py` MUST NOT (it reads prose, where matches
are fuzzy). `lexicon_check.py` reads prose, so it joins the `voice_drift` category:
**emit evidence + counts + offending spans; never `BLOCKING:`.** A
BELONGING-term-in-Book-2 match is *usually* a real violation but not always (a name
that collides with a slang term; the protagonist quoting a local back at them inside a
narrative clause; a term that is both standard English and tagged local). The script
hands `inspector-voice` "here are N out-of-stage terms with line numbers and tags";
the inspector, which has the surrounding context the script lacks, decides whether each
is a real fluency break or a benign collision, and blocks accordingly. Evidence from
the script, judgment from the inspector.

## 3. Shared module — `scripts/penny_text.py`

The narration/dialogue separator **does not exist today** and must be built. This was
the load-bearing correction in brainstorming: `voice_drift.py` only tracks
`quote_depth` so it will not *split a sentence* mid-quote (`'I'm fine,' she said.`
stays one sentence); it never *excludes* dialogue. Every tic it reports is counted over
all prose, dialogue included. There is no narration-extraction primitive to reuse —
`lexicon_check.py` is the first thing in Penny that needs "narration only, dialogue
removed."

The right shape is one shared quote parser with two policies on top, so the two
voice-related checks can never disagree about what a quote is:

- **Shared = quote-span detection.** `penny_text.py` exposes *where the quotes are*:
  paired-quote spans with the documented abbreviation guard, single-quote-as-apostrophe
  (`'I'm fine'` vs the apostrophe in `don't`), em-dash dialogue, smart-vs-straight
  quotes, and dialogue spanning paragraphs.
- **Per-caller = policy.** `voice_drift` applies "do not split a sentence across a
  span" (its current behavior); `lexicon_check` applies "remove the spans → narration
  only."

Pushing the *strip* policy into the shared module would force it on `voice_drift` and
trigger the behavior change §3.1 forbids. Shared = *where the quotes are*; per-caller =
*what to do about them*.

`voice_drift.py`'s existing text primitives — `strip_frontmatter`, `_is_prose_line`,
`segment_sentences` — move into `penny_text.py`; `voice_drift` imports them.

### 3.1 Tripwire acceptance criterion (non-negotiable)

A factor-out must be behavior-preserving for existing callers. The refactor is correct
**iff `voice_drift.py` produces byte-identical results and the existing 89 tests stay
green with no fixture edits.** The moment the factor-out changes what `voice_drift`
counts, it stops being a refactor and becomes an un-speced feature change wearing a
refactor's clothes — a green suite would no longer prove what it proved before. This
criterion is the deliverable's tripwire, listed in §8.

### 3.2 Explicitly deferred

"Should `voice_drift`'s tics be counted over narration only (excluding dialogue)?" is a
real, open question with its own answer ("should `heart pounded` inside a quote count?")
— but it is a behavior change to a shipped, tested checker, not this spec. **Deferred to
its own spec.**

## 4. `scripts/lexicon_check.py` (Tier-3, evidence-only)

Config-driven, fail-loud, evidence-emitting — built the same way as `voice_drift.py`.
Writes a verdict via `scripts/penny_verdict.py` (`producer: lexicon_check.py`,
`kind: deterministic-checker`, `name: lexicon-fluency`), with **`blocking: []` always**.

**Flag rule.** A term is flagged as a premature-term violation iff **all** hold:

1. `auto_detectable: true` on the lexicon entry, **and**
2. a word-boundary-aware match of the term appears in **narration** (dialogue removed
   via `penny_text`), **and**
3. `rank(term.narration_ok_from_stage) > rank(canon_core.fluency_stage)`.

- **Stage ordering** `OUTSIDER < SETTLING < BELONGING` is a fixed enum constant **in
  the script** — the stable algorithm lives in code, the data lives in config, the same
  division `voice_drift` draws between its detection patterns and its thresholds.
- **Word-boundary matching, never naked substring.** `arvo` is safe; many local terms
  are homographs of standard English or appear as substrings of innocent words.
- **`auto_detectable: false` terms** (homographs of standard English) are **carried
  into the evidence file as "inspector-only" notes** so `inspector-voice` still knows to
  eyeball them — but the script **never counts them as a violation**. This is the honest
  line: deterministic where mechanical matching is sound, judgment where it is not.
- **Evidence spans** carry: term, line number, the term's `narration_ok_from_stage`
  tag, and the current stage. Capped like `voice_drift` (≤5 spans + a total count).

### 4.1 Scope honesty — the dial is directional, the script covers half

The dial is directional and the script covers only the **premature-term** direction
(out-of-stage-too-early: a term tagged for a later stage appears now → deterministic
evidence). It **cannot** check the other direction — *insufficient* local idiom in the
Belonging books, where the *absence* of belonging-flavoured narration is itself a
fluency-dial failure ("the signal she belongs" did not happen). That is a density/taste
judgment, not a countable violation, and stays irreducibly `inspector-voice`'s job. The
spec states this explicitly so "a lexicon check exists" never creates the impression the
whole dial is mechanically enforced — only half of it can be.

## 5. Lexicon migration — `config/setting-pack/lexicon.yaml`

The lexicon is currently a hand-maintained markdown table that nothing parses
(LLM-context-only for the drafter). Once a deterministic script depends on it, the
format matters.

- **Data moves to `config/setting-pack/lexicon.yaml`** as the single authoritative
  source; `config/setting-pack/lexicon.md` is demoted to a short schema doc that points
  at the YAML (no duplicated rows → no drift). Loaded with `yaml.safe_load` + fail-loud,
  the same pattern as `config/voice-pack/ai-tics-config.yaml`. This avoids a brittle,
  whitespace-sensitive markdown-table parser and matches the standing preference: YAML
  for human-edited data, data in its own file, `.md` as doc.
- **Schema gains `auto_detectable: bool`.** Full entry: `term`, `gloss`, `register`,
  `speaker_type`, `freq_cap`, `narration_ok_from_stage`, `auto_detectable`, `notes`.
- **Three required fields, same fail-loud posture:** `term`, `narration_ok_from_stage`,
  `auto_detectable`. No silent defaults — implicit `auto_detectable: true` would cry wolf
  on the first un-flagged homograph; implicit `false` would silently under-enforce.

### 5.1 Validation at lock time, not mid-scan

Required-field validation is a **whole-lexicon, fail-loud pass that runs at
lexicon-validation / setting-pack-lock time and names every offender** — not a
per-chapter operational error discovered deep in a production run. A missing required
field is a config-edit fault and belongs at the config gate.

Realized as a `validate` capability of `lexicon_check.py` (a subcommand / `--validate`
mode), runnable standalone now and wired into the Phase-3 setting-pack/lexicon lock
pre-flight when that lands. The per-chapter scan assumes validated input but still
fails loud — never guesses — if a required field is somehow absent at runtime
(belt-and-suspenders).

## 6. Canon-core stage — machine-readable, inside active-book state

The current stage is book-scoped active state (it advances as books progress), so it
belongs **with canon-core's active-book state, not as a free-floating top-level key**.
Today the stage exists only as prose (`## Fluency stage` says "**OUTSIDER**…"), which a
script cannot trust.

**Mechanism: a `canon-meta` HTML-comment YAML header.** Store the stage as
`fluency_stage` inside a `<!-- canon-meta: { ... } -->` header co-located with
canon-core's active-book state. This is the convention the demotion design specced
(`2026-06-20-penny-canon-core-demotion-design.md`): an HTML comment is fully invisible
to the drafter (no risk it reads `fluency_stage` as content) while staying greppable and
parseable. The prior handoff is explicit that *if Phase 3–7 work touches canon-core
structure, the `canon-meta` convention should be adopted then* — this is that moment,
and `fluency_stage` becomes the convention's first real consumer, realizing the parked
demotion **data seed** early and correctly (demotion spec §7.1 lands the cheap seed
early anyway). The prose `## Fluency stage` section stays as the human explanation.

- A minimal `parse_canon_meta` reader extracts the comment body and `yaml.safe_load`s
  it (small, ~stdlib + PyYAML, no new dependency). It joins `penny_meta.py` /
  `penny_verdict.py` as a shared loader primitive.
- **No stage declared → operational error**, never "assume OUTSIDER."

### 6.1 Drift-guard — prose vs machine value must be visible

Because the `canon-meta` `fluency_stage` is now authoritative, a silent disagreement
between it and the prose `## Fluency stage` section is newly possible. The check (or the
validator) compares the two and **surfaces a mismatch as evidence** — it is never
silently resolved in favour of either.

## 7. `inspector-voice` scope widening

Add to `inspector-voice`'s input scope: `config/setting-pack/lexicon.yaml`, the current
`fluency_stage`, and the `lexicon-fluency.md` evidence file. Its instructions gain:

- **Use** the script's premature-term evidence — do not re-detect terms — and decide
  whether each flagged term is a real fluency break or a benign collision (name clash,
  in-narrative quotation, standard-English homograph), blocking accordingly.
- **Judge the half the script cannot see:** *insufficient* local idiom for the current
  stage in the Belonging books (a taste judgment, per §4.1).
- It keeps the blocking call; the lexicon check never takes it.

## 8. Testing

- **`penny_text.py` — fresh adversarial narration-vs-dialogue fixtures** (this
  capability is new and unproven; it earns its own proving, not inherited confidence):
  - dialogue excluded, the `said`-bookend narration kept;
  - a local term **inside a quote does not flag**, the same term in the narrative clause
    **does**;
  - apostrophe-vs-single-quote, em-dash dialogue, smart vs straight quotes, dialogue
    spanning paragraphs.
- **`voice_drift.py` — the tripwire:** the existing 89 tests stay green with **no
  fixture edits**, proving the factor-out was behavior-preserving (§3.1).
- **`lexicon_check.py`:** premature term flagged; in-stage term clean; `auto_detectable:
  false` homograph → inspector-only note, never a violation; term inside dialogue not
  flagged; word-boundary correctness (no substring false positives); evidence cap;
  config-missing hard-fail; `blocking` always `[]`.
- **Validation:** missing `auto_detectable` / `narration_ok_from_stage` (and `term`) →
  lock-time hard-fail naming **every** offender, not just the first.
- **Canon-core:** missing `fluency_stage` → operational error; prose-vs-`canon-meta`
  mismatch → drift evidence.

## 9. Wiring

`lexicon_check.py` joins `voice_drift.py` in the `review-chapter` orchestrator's Tier-3
checker fan-out, writing `lexicon-fluency.md` into the chapter's `*.reviews/` dir before
the inspectors run. Its `--validate` mode wires into the Phase-3 lexicon/setting-pack
lock pre-flight.

## 10. Out of scope

- Retrofitting `voice_drift` to narration-only counting (§3.2 — its own spec).
- The *insufficient-fluency* (later-book) direction as a deterministic check (§4.1 —
  irreducibly inspector judgment).
- The full canon-core demotion machinery (parked for Phase 8); only the `canon-meta`
  header convention is adopted here, for `fluency_stage`.
