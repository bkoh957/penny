# beta-protocol.md — Beta reaction-report format (design §5c, §10)

Beta readers react to assembled prose and report **experience**, never rules.
Output is **non-blocking** — it never holds a gate. Two artifacts.

## Raw reading — one per (persona, model)

The §10 contract fields, produced by a single blind `beta-reader` sub-agent and
serialized by `scripts/beta_report.py`:

- `engagement_curve` — per-chapter `{chapter, score}` (1–5).
- `put_down_points` — chapters where the reader nearly stopped.
- `whodunit_guess` — `{name, chapter}` (first chapter the reader felt sure).
- `confusion_points` — places the reader could not follow.
- `emotional_beats` — `[{beat, lens}]`.
- `would_buy_next` — `{verdict, driver, facet?}`.
- `notes` — free text.

### Three serialization rules

1. **Shared-field rule.** Any field with more than one primary owner serializes as
   `{value, lens}`, where `lens` = the emitting persona's stamped DRIVER value
   (e.g. `comfort-tone`, `fairness` — same six-value space as `would_buy_next.driver`).
   Applies to `emotional_beats` (`[{beat, lens}]`) and `would_buy_next` (`{verdict, driver}`).
   This keeps cross-persona convergence computable, not coincidental.
2. **`n/a` is a first-class verdict, distinct from `no`.** A persona that cannot
   read an axis in a given book (e.g. the Romance Reader on a romance-less book)
   returns `n/a`, which is **excluded from the `would_buy_next` denominator** — it
   is never counted as a failure.
3. **`driver` is stamped, not reader-picked.** The reader emits only
   `yes | no | n/a`; the harness stamps `driver` from the persona's lens. The Arc
   Reader's `facet` (`self | place`) is the only reader-chosen sub-tag.

## Converged report — one per persona

`scripts/beta_report.py` collapses a persona's `M` model-readings (the within-
persona consensus axis is the **model**):

- `engagement_curve` — per chapter `{chapter, central, band:[min,max]}`.
- `put_down_points` — `{consensus, logged}`; a chapter is consensus iff flagged by
  `>= beta_consensus_k` of the `M` readings, else logged.
- `would_buy_next` — `{tally, denominator}`, where `tally` is `{yes, no, "n/a"}` (per-verdict counts) and `denominator` excludes the `n/a` count.
- `panel` — `{m, k, panel_size, distinct_models, degraded}`.

## Cross-persona rollup — [Phase 6]

Consensus *across* personas (do put-down points / "would not buy" span personas?)
and the escalation into showrunner book-approval (P0.8) are the **revision-priority
report**, built in **Phase 6**. Phase 5 stops at per-persona converged reports.
