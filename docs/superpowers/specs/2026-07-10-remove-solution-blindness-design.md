# Remove solution-blindness

**Date:** 2026-07-10
**Status:** approved (design), not yet implemented
**Supersedes:** the "Blind sub-agents" rule in `CLAUDE.md` and design §5a's drafter-blindness
clause, insofar as they hide the whodunit from generative and review agents.

## Problem

The engine hides `output/book-NN/mystery-solution.md` from the drafter, the
outline-expander (by instruction), the outline-reviewer, the developmental-editor, and
`inspector-fairplay`. This is called *blindness* and is treated as load-bearing.

Three things are wrong with it.

**Nothing enforces it.** The entire deterministic layer contains no blindness check; the
sole occurrence of the word in `scripts/` is a docstring in `beta_report.py`. Drafter
blindness is one prose sentence (`agents/drafter.md:9-10`) plus the fact that
`/draft-chapter` passes a `## Chapter NN` section rather than the whole outline. The
guarantee is asserted, never checked.

**It contradicts the engine's own doctrine.** `agents/final-reader.md:9-11` states:
"Seeing the solution does not compromise independence: the value is 'drawer time' — a
model that did NOT draft." The final reader is the most independent agent in the system
*and* fully informed. Independence is model difference, enforced by `preflight.py assemble`
against `drafted_by`. Solution-blindness is a second, contradictory theory of independence
that no gate enforces.

**It is already incoherent.** `agents/outline-reviewer.md:13` tells that agent it is
"denied the whodunit solution," while `/review-outline` (`commands/review-outline.md:36-39`)
passes it the whole `input/book-NN/outline.md` — whose `## Solution` block, required by
`outline_check.py`, names the culprit. The instruction is false about its own inputs.

The cost is real: guardrail prose across five agents and three commands, a manual
post-expansion leak review (`commands/expand-outline.md:42-45`), and an
`outline-expander` discipline documented as "the ONLY protection" against a leak that
nothing detects. The benefit is a guarantee nothing verifies.

## Non-goals

- **Reviewer isolation is not touched.** Isolation means: no other agent's output, no
  drafting history, one rubric, one chapter, one ledger slice. Granting
  `inspector-fairplay` the solution does not breach any of those — it is a fact about the
  book, not another agent's judgment. Isolation is about *whose reasoning* an inspector
  can see, never about *what is true*.
- **The mystery lock is not touched.** `preflight lock-mystery`, `fairplay_check.py`, the
  certificate model, and cross-model routing are unchanged.
- **No configurability.** No `solution_visibility` flag. A flag would not remove the
  guardrail prose being objected to; it would duplicate it across two branches. Genre packs
  already provide the axis of variation (see *Inverted mysteries*, below).

## Design

### One word, three properties

`blind` currently names three unrelated mechanisms. Replace it with three named properties.

| Property | Means | Applies to | Fate |
|---|---|---|---|
| **Independence** | the reviewing model did not draft | final-reader, beta-reader | unchanged (enforced by `preflight.py assemble`) |
| **Isolation** | narrow inputs; no other agent's output | 5 inspectors, beta-readers | unchanged |
| **Reader simulation** | the reader does not know the rules or the answer | beta-reader only | **kept** |

Solution-blindness is not on this list. It is deleted.

**Reader simulation is not a guardrail** and must not be removed with the guardrails.
`agents/beta-reader.md:8-9`: "A reader who knows the rules starts inspecting instead of
reacting." A beta reader who knows the culprit cannot report that she guessed it in
chapter four. Its `{ text, persona_file }` input contract is a functional requirement of
the simulation and survives verbatim.

`agents/beta-reader.md` is therefore **not edited at all** — it already states this
rationale correctly. The name "reader simulation" is adopted in `CLAUDE.md`'s taxonomy so
that the agent's blindness is never again filed alongside the guardrails and deleted with
them. `tests/test_beta_scaffold.py` stays untouched as the regression bar.

Consequently **"sealed" is redefined**: it means *frozen against edits*, not *hidden from
agents*. That is all `lock-mystery` ever did — an out-of-band certificate that exists
because validation passed. Re-planning still means: delete the lock, edit the yaml, re-run
`lock-mystery`.

### Where the guarantee lands

Drafter blindness structurally prevented exactly one failure: **the answer reaching the
page before `reveal_chapter`.** Removing it transfers that from a structural guarantee to a
review responsibility. The owner is `inspector-fairplay`, which already judges "the PAGE,
not the plan" and already carries a clause about a clue "flagged so hard it spoils" that it
was never equipped to evaluate, being itself denied the answer.

- **New inputs:** `{ text, fairplay-planting.md, ledger_slice, mystery_solution, reveal_chapter }`.
- **New blocking predicate:** guilt asserted or confirmed before `reveal_chapter` goes in
  `blocking_issues`.

Naming the culprit is *not* a violation — she is an on-page suspect for most of the book.
Asserting her guilt is.

**This predicate stays out of `scripts/`.** It is an LLM judgment, and the deterministic
layer's defining promise (`CLAUDE.md`, three-layer architecture) is that it never makes
one. A lexical check — does the culprit's name appear before ch22 — would fire on every
innocent sentence in which she appears. The rubric clause lives in
`genres/cozy-mystery/review-rubrics/fairplay-planting.md`, because "do not reveal before
the reveal" is a genre convention, not an engine rule.

### Inverted mysteries

A howcatchem (culprit known from chapter one) needs no engine change and no flag. Its genre
pack simply omits the premature-reveal rubric clause and declares different `gates:` in
`genre.yaml` — `fairplay` audits whether necessary clues precede the reveal, which is not
the contract of an inverted mystery. The engine is already agnostic; this design keeps it
that way.

## Change surface

### Agents (5)

| File | Change |
|---|---|
| `agents/drafter.md:9-10` | delete the independence clause; add `mystery-solution.md` to Inputs |
| `agents/developmental-editor.md:11-18` | remove "denied the whodunit solution"; add it to Inputs |
| `agents/outline-reviewer.md:13` | remove the false "denied the whodunit solution" clause |
| `agents/outline-expander.md:3,11-13,24` | keep the solution input; delete the withholding discipline and the "no automated leak-guard / ONLY protection" framing |
| `agents/inspector-fairplay.md:13,16,23-32` | add `mystery_solution` + `reveal_chapter` to Inputs; add the premature-reveal blocking predicate; keep isolation language |

### Commands (4)

| File | Change |
|---|---|
| `commands/draft-chapter.md:69-70` | pass `output/book-NN/mystery-solution.md` to the drafter |
| `commands/review-outline.md:38-39` | delete the "do NOT pass `mystery-solution*.md`" instruction |
| `commands/expand-outline.md:42-45` | delete the manual post-expansion leak review step |
| `commands/review-chapter.md:108` | stop excluding the solution from the developmental-editor dispatch; pass `reveal_chapter` to `inspector-fairplay` |

### Genre data (1)

`genres/cozy-mystery/review-rubrics/fairplay-planting.md` — add the premature-reveal
coverage clause.

### Docs (2)

- `CLAUDE.md:183-200` — replace the "Blind sub-agents" section with the three-property
  taxonomy; update `:69` ("the 5 blind inspectors" → isolated), `:133`, `:137`.
- `README.md:253,257,285` — same.

### Scripts (0)

No change. `fairplay_check.py`, `preflight.py`, `review_gate.py`, `penny_verdict.py`,
`penny_paths.py` are all untouched. No new config key, no new state, no new file.

## Data flow

Before: `mystery-solution.md` → `{ mystery-planner (author), outline-expander (withholds),
final-reader }`.

After: `mystery-solution.md` → `{ mystery-planner (author), outline-expander,
outline-reviewer, drafter, developmental-editor, inspector-fairplay, final-reader }`.

Still excluded: **beta-reader** (reader simulation), and the four inspectors other than
fairplay (isolation — they have no use for it; continuity, structure, voice, and ai-prose
judge against their own rubric and ledger slice, and widening their inputs would dilute
isolation for no gain).

## Error handling

- `inspector-fairplay` dispatched without `reveal_chapter` (no locked ledger for the book):
  it must **not** silently skip the premature-reveal check. `/review-chapter` already runs
  `fairplay_check.py` only for locked books; the inspector receives `reveal_chapter` only
  when a lock exists, and its rubric instructs it to state in `evidence[]` that the check
  was not applicable. Absence of a lock is a planning-stage condition, not a gate failure.
- No new failure mode reaches `scripts/`. The gate's PASS/HOLD contract
  (`review_gate.py`, `^BLOCKING:` at column 0) is unchanged; the new predicate produces an
  ordinary blocking issue counted exactly like every other.

## Testing

Test-first, against `tests/fixtures/`, per repo convention.

1. `tests/test_developmental_editor.py:61` — currently asserts the agent is denied the
   whodunit. **Invert:** assert `mystery-solution.md` is named among its inputs.
2. `tests/test_beta_scaffold.py:61,70` — **must pass untouched.** This is the regression bar
   proving reader simulation survived the removal of the guardrails.
3. New agent-contract tests (mirroring `tests/test_inspector_scaffold.py`) that
   `drafter.md`, `outline-reviewer.md`, and `inspector-fairplay.md` each name
   `mystery-solution.md` as an input.
4. New test that `agents/inspector-fairplay.md` declares the premature-reveal blocking
   predicate, and that `genres/cozy-mystery/review-rubrics/fairplay-planting.md` carries the
   corresponding rubric clause.
5. New negative test that `agents/beta-reader.md` still declares `{ text, persona_file }`
   only and still contains no solution input.
6. Full suite green: 330 existing + new.

## Accepted consequence

`/review-outline`'s panel becomes solution-aware, so reviewer feedback may name the culprit
in `output/book-NN/reports/outline-feedback.yaml`, which is committed to the series repo.
This is judged harmless: `outline_feedback.py:105` (`status_line`) prints only item **IDs**
into the draft-time banner, never item text, so it cannot leak into a drafting context — and
after this change the drafter is informed anyway. Recorded here because it will look
alarming to a future reader who does not know it was considered.
