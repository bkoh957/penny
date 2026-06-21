# Penny Phase 5 — Beta-Reader Layer — Design

Saved: 2026-06-21 | Phase 5 of the v3 build order (`penny-design-v3.md` §13).

## §1 Purpose

Phases 1–4 built the per-chapter flow up to and including the post-gate finalize
(`/draft-chapter` → `/review-chapter` → `/finalize-chapter` → promote
`ch-NN.final.md`). The **beta-reader layer** (design §5c, §10) is the remaining
`[STUB]` the design itself calls *"the highest-leverage open decision"* — it
converts a technically-correct manuscript into a Kindle-sellable one.

Inspectors check **rules**; beta readers report **experience** — *"what is this
like to read?"* Keeping the two populations apart protects independence: a reader
who knows the rules starts inspecting instead of reacting (design §10).

Phase 5 authors the beta **population and contract**: the six persona definitions,
the `beta-protocol.md` report schema, the blind `beta-reader` agent, a deterministic
report writer/collapser, and the **input-agnostic** `/beta-read <path>` command.

## §2 Scope

**In:**
- `config/beta-readers/personas/*.md` — six persona files (the locked roster, §4).
- `config/beta-readers/beta-protocol.md` — the reaction-report schema (§5).
- `beta-reader` agent (`.claude/agents/beta-reader.md`) — blind reaction agent (§7).
- `scripts/beta_report.py` — deterministic, fixture-tested serializer + per-persona
  cross-model collapser (§6).
- `/beta-read <path> [--out <dir>]` command (`.claude/commands/beta-read.md`) — the
  input-agnostic fan-out orchestrator (§6).
- One new run-config tunable: `beta_consensus_k` (§6).
- Scaffold/doc + unit tests (§8).

**Out (deferred to Phase 6, by deliberate seam — see §3, §9):**
- The **cross-persona revision-priority report** (consensus *across* personas) and
  its escalation into showrunner book-approval (P0.8).
- The `assemble-book` step that produces the live `book-NN.manuscript.md` input.

## §3 Why book-level, and why "input-agnostic" instead of "live now"

**Beta runs at the book level, not per chapter (design §5a, §5c, §10).** The
per-chapter flow (§5a) ends `… → COPY-EDIT → FINALIZE → promote ch-NN.final.md`
with **no** beta step, and the design rejects the per-chapter site explicitly:

> "Beta readers do **not** run per chapter — they react to the **assembled book**
> (§5c, §10). A boring chapter in isolation is a weak signal; reader experience is
> a book-level property." (§5a)

The live input is therefore `book-NN.manuscript.md`, which does **not exist until
Phase 6** (`assemble` is currently only a cross-model routing *guard* in
`preflight.py`; nothing produces the manuscript artifact yet).

So Phase 5 builds beta **fixture-tested now, live in Phase 6** — the same posture
`/finalize-chapter` holds today. The justification for building the runner now is
**not** "it has a live target" (it does not); it is: the command is cheap, it is
the natural home for the config + agent + contract being authored anyway, and an
**input-agnostic path-taker** is finished work the moment assembly lands — no
Phase-6 rework. Because the beta contract is text-in / reaction-out and
deliberately blind (no ledgers, no solution, no rules — §10), `/beta-read <path>`
runs against a chapter fixture now and a manuscript in Phase 6 with **zero change**.
The manuscript-doesn't-exist problem never bites it.

## §4 The persona roster (locked, six)

Each persona is a **distinct reader lens**. Personas are never averaged together —
divergence *between* personas is signal, not noise (a slow stretch that only bores
the Skimmer but not the Loyalist is a precise finding). Every §10 contract field
has a **primary owner**; nothing is orphaned, nothing is pure redundancy.

| §10 contract field          | Primary owner       | Failure mode probed                          |
|-----------------------------|---------------------|----------------------------------------------|
| `engagement_curve_by_chapter` | Impatient Skimmer | sagging middle (§8), reader-side             |
| `put_down_points`           | Impatient Skimmer   | pace collapse / bail points                  |
| `whodunit_guess + chapter`  | Puzzle Hawk         | over-telegraphed (too early) / unfair (never) |
| `confusion_points`          | Newcomer-Outsider   | fluency-dial onboarding (§9)                  |
| `emotional_beats`           | Loyalist / Arc / Romance | tone-comfort / transformation / chemistry |
| `would_buy_next`            | Loyalist / Arc / Romance | the return-purchase drivers              |

**"Primary owner" means diagnostic weight, not exclusive emission.** The §10
contract has *every* persona return *every* field — so all six emit `would_buy_next`
and `emotional_beats`. The table names whose read on a field is *load-bearing*; the
other personas still emit the field, stamped with their own lens (a Skimmer's
`would_buy_next: no` carries `driver: pace`). This is why the `would_buy_next.driver`
enum is six values (§5.1), not three.

1. **The Cozy Loyalist** — reads for **tone-contract violation**. The genre
   promises comfort and restored order; flags when violence, bleakness, or cynicism
   breaks the cozy contract. Lens/driver: `comfort-tone`. Primary axes:
   `emotional_beats`, `would_buy_next`. Catches what inspectors cannot — whether it
   *feels* cozy.
2. **The Puzzle Hawk** — reads for **fairness and solvability**, actively tries to
   solve. `whodunit_guess + chapter` is diagnostic: too early = clues
   over-telegraphed, never = unfair or muddy. The human-experience complement to the
   Tier-3 fair-play checker (the script proves clues were *planted*; the Hawk reveals
   whether a real solver could *use* them). Lens/driver: `fairness`.
3. **The Arc Reader** — reads for **interiority and self-reinvention**: does she
   change, is the sea-change earned, is the growth real. Indifferent to romance
   specifically. Lens/driver: `transformation`, with **facets `self | place`** —
   place-belonging ("has she made this town home / somewhere I want to stay") is the
   same interiority axis pointed at setting rather than self, and is the home for
   **setting-charm** as a return driver.
4. **The Romance Reader** — reads for **relational tension and payoff**: chemistry,
   slow-burn pacing, will-they/won't-they, whether romantic beats land or feel
   perfunctory. Its `would_buy_next` diagnostic is specifically *"did the romantic
   thread leave me wanting the next book"* — distinct from the §9 rule that *a*
   personal thread stays open. Same fields as the Loyalist, different lens, no
   collision. Lens/driver: `chemistry`. **Always-on; returns `n/a` when no live
   romance thread** (never `no`).
5. **The Impatient Skimmer** — reads for **engagement decay**; bails when pace sags.
   The primary signal-generator for `put_down_points` and `engagement_curve` —
   probes the §8 "sagging middle" from the reader side. Lens/driver: `pace`.
6. **The Newcomer-Outsider** — reads for **confusion / onboarding**; series-bespoke.
   File invariant (stated verbatim in the persona file): *enters with zero lexicon
   fluency regardless of series position; flags any term/idiom/local reference used
   as if already known.* It is **lexicon-cold, not character-cold** — character
   coldness is already the book-level default (beta reads one assembled manuscript
   with no series memory) and needs no persona to enforce it. The valuable invariant
   is series-economics: *can a reader entering at book 5 still follow?* The
   reader-side mirror of the lexicon checker's `narration_ok_from_stage` discipline
   (the checker proves a term was stage-legal to use; the Outsider reveals whether a
   cold reader could follow it). Lens/driver: `onboarding`.

## §5 The protocol — `beta-protocol.md`

The §10 contract, serialized under three banked rules that fall directly out of the
distinct-lenses principle.

### §5.1 Banked serialization rules

1. **Shared-field rule (general).** Any contract field with **more than one primary
   owner** is serialized as `{value, lens}`, never a bare value, where **`lens` =
   the emitting persona's stamped lens** (the same six-value space as `driver`).
   Concretely:
   - `would_buy_next: {verdict, driver, facet?}`
   - `emotional_beats: [{beat, lens}]`
   This makes cross-persona convergence *computable* rather than coincidental: a
   Loyalist `would_buy_next: no` (too bleak) and a Romance `no` (chemistry flat) are
   **different revision actions** and must not merge into mush.
2. **`n/a` is a first-class verdict, distinct from `no`.** `{verdict: n/a}` (e.g.
   Romance on a romance-less book, or any persona that legitimately cannot read an
   axis in a given book) must never be read as `{verdict: no, driver: …}`. The
   collapser and the future rollup ignore `n/a` reads rather than counting them as
   failures.
3. **`driver` is persona-*stamped*, not reader-*picked*.** The reader emits only
   `yes | no | n/a`; the harness attaches `driver` from the persona file's declared
   lens. Asking the reader to classify *why* it won't buy invites the rule-reasoning
   the blind contract forbids (same reason ledgers/solution are withheld). The
   **`driver` enum is one value per persona lens** (six values), because the §10
   contract has *every* persona return `would_buy_next`:

   ```
   would_buy_next.driver ∈ {
     comfort-tone   (Cozy Loyalist)
     transformation (Arc Reader)        facet: self | place
     chemistry      (Romance Reader)
     pace           (Impatient Skimmer)
     fairness       (Puzzle Hawk)
     onboarding     (Newcomer-Outsider)
   }
   ```

   The **`facet` (Arc only: `self | place`) is the one genuinely reader-chosen
   sub-tag** — the reader does know whether her interior arc or her place-belonging
   fell flat. So: `driver` = stamped constant (= persona identity); `facet` = the
   only reader judgment. Invariant preserved: **one persona → one driver → one
   revision action.**

### §5.2 Two artifacts

- **Raw reading** — one per `(persona, model)`. The §10 output fields:
  `{ engagement_curve_by_chapter, put_down_points, whodunit_guess + chapter,
  confusion_points, emotional_beats: [{beat, lens}], would_buy_next: {verdict,
  driver, facet?}, notes }`.
- **Per-persona converged report** — one per persona, after collapsing its `M`
  model-readings (§6):
  - `engagement_curve` per chapter as `{central, band}` (convergent-low = a robust
    slow stretch; wide band = a model artifact, discount it).
  - `put_down_points` by **≥K-of-M** consensus; singletons logged, not escalated.
  - `would_buy_next` as the M-model vote (verdicts tallied; `n/a` excluded from the
    denominator).

**No cross-persona rollup.** That section of the schema is present but marked
`[Phase 6]`. Phase 5 stops at per-persona, model-converged reports.

## §6 The runner — `/beta-read <path>` + `beta_report.py`

**Command** (`.claude/commands/beta-read.md`, Steps modeled on `review-chapter.md`):

1. Read `beta_models` + `panel_size` + `beta_consensus_k` from
   `config/run-config.md`; resolve the **reachable** subset of `beta_models`.
2. For each of the six personas, dispatch up to `panel_size` `beta-reader`
   sub-agents across **distinct** reachable models. If fewer models are reachable
   than `panel_size`, repeat-sample the reachable ones and record a reachability
   note (honest degradation — §10 flags cross-model as rate-limited).
3. Each sub-agent receives **only** `{ text, persona_file }` — no ledgers, no
   outline, no solution, no rules. It writes a raw reading via `beta_report.py`.
4. Collapse each persona's model-readings into its converged report via
   `beta_report.py`.
5. Write reports to `--out` (default `<input-dir>/beta-reports/`). The command
   **never** writes `.penny/current-stage` gate state and **never** emits
   `BLOCKING:` lines — beta is non-blocking by construction (a slow stretch is a
   quality signal, not a correctness failure — §10).

Fan-out per book: up to `6 × panel_size` sub-agent reads (18 at the book-level
`panel_size: 3`), collapsing to six per-persona converged reports.

**`scripts/beta_report.py`** — deterministic, fixture-tested (mirrors
`penny_verdict.py` / `ledger_markers.py`). Two jobs, both pure shape, no judgment:
- **serialize** one raw reading, *enforcing* the verdict enum (`yes | no | n/a`),
  `n/a`-as-first-class, the stamped `driver`, the `{value, lens}` shape, and the Arc
  `facet`.
- **collapse** `M` raw readings → one per-persona converged report: `engagement_curve`
  `{central, band}`, `put_down_points` by `≥K-of-M` (`K = beta_consensus_k`),
  `would_buy_next` tally (`n/a` excluded from the denominator).

The agent supplies the reaction; the script enforces the format. The
**cross-persona rollup is not implemented here** (Phase 6).

**run-config** — no churn to existing keys (`beta_models`, `panel_size` already
present). One new tunable:

```yaml
beta_consensus_k: 2   # ≥K-of-M models must flag a put-down for per-persona consensus;
                      # default = majority of panel_size (book-level panel_size: 3 → 2)
```

## §7 The agent — `beta-reader`

`.claude/agents/beta-reader.md`, same independence posture as the blind inspectors
(`inspector-ai-prose.md` as the format model) but **reacting, not ruling**.

- **Role posture:** blind reaction reader (design §10). Reports experience; never
  inspects against rules.
- **Independence:** receives ONLY `{ text, persona_file }`. No ledgers, no outline,
  no solution, no rubrics, no other personas' reads — the same blindness a real
  reader has.
- **Inputs:** `{ text, persona_file }`.
- **Outputs:** a raw reading written via `beta_report.py` (the §5.2 raw shape).
  Emits only `yes | no | n/a` for `would_buy_next`; the `driver` is stamped by the
  harness from the persona file, never chosen by the agent. The Arc `facet` is the
  only field the agent classifies.
- **Cross-model:** a routing swap (P1.2), no engine change — the same agent runs on
  each reachable `beta_models` entry.

## §8 Testing

Posture mirrors `test_finalize_command.py` + `test_prose_pass_scaffold.py`
(scaffold/doc) plus unit tests for the deterministic script.

**Scaffold / doc tests:**
- all six persona files exist, parse, and declare a valid `driver` (one of the six
  enum values) + `primary_axes`; only `arc-reader` declares `facets: [self, place]`.
- `newcomer-outsider.md` body contains the frozen lexicon-cold invariant.
- `romance-reader.md` authorizes the `n/a` verdict.
- `beta-protocol.md` documents all §10 fields, the three serialization rules, and
  marks the cross-persona rollup `[Phase 6]`.
- `beta-read.md` command Steps present; never writes gate state / `BLOCKING:`.
- `beta-reader.md` agent is well-formed and blind (inputs are `{text, persona_file}`
  only).

**Unit tests for `beta_report.py`:**
- verdict-enum enforcement (rejects anything but `yes | no | n/a`).
- `n/a` ≠ `no` (an `n/a` read is excluded from the `would_buy_next` denominator and
  never counted as a failure).
- `driver` is stamped from the persona file, not accepted from the reading payload.
- collapse math: `engagement_curve` `{central, band}`; `put_down_points` `≥K-of-M`
  with singletons dropped; reachability-degraded panels (fewer models than
  `panel_size`) annotated.

**Fixtures:** a stub manuscript under `tests/fixtures/` so the command and collapser
exercise end-to-end without a live `book-NN.manuscript.md`.

## §9 The Phase-6 seam (documented, not built)

The six per-persona converged reports are the **input** to the future
**revision-priority report** (Phase 6), which computes cross-persona consensus and
escalates to showrunner book-approval (P0.8): *"do consensus put-down points and
'would not buy next' span personas?"* (design §5c, §10).

Two reasons this aggregation stays Phase 6, not Phase 5:
- **Consensus is unsettled until book-level.** `panel_size` defaults differ by site;
  cross-persona consensus tuned against anything but the book-level panel would be
  re-tuned anyway.
- **Escalation has no target yet.** P0.8 book-approval is itself a Phase-6 artifact;
  building escalation against an absent approval flow is wasted motion.

The `{value, lens}` + `n/a`-first-class serialization (§5.1) is precisely what makes
that future cross-persona rollup computable rather than coincidental.

## §10 Out of scope / explicitly not doing

- No per-chapter beta site (design rejects it — §3). If ever reconsidered, that is a
  conscious design *amendment* to `penny-design-v3.md`, not a Phase-5 build.
- No conditional / per-book persona gating. All six personas always run; absence of
  a readable axis is expressed as `n/a`, not by withholding the persona — gating
  would hand the blind runner a judgment the contract forbids.
- No cross-persona aggregation, no P0.8 escalation, no `assemble-book` (all Phase 6).
- No new gate coupling: beta never blocks, never writes `.penny/current-stage`.
