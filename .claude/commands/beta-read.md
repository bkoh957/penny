---
description: Book-level beta read — fan the six personas across reachable beta_models on an assembled text, write per-persona converged reaction reports. Non-blocking.
argument-hint: <path-to-text> [--out <dir>]
---
# /beta-read

The beta-reader layer (design §5c, §10). **Input-agnostic:** takes a text path —
a finalized chapter fixture now, `book-NN.manuscript.md` in Phase 6 — and runs the
six blind reader personas on it. Beta is **non-blocking**: this command never
writes `.penny/current-stage` and never emits `BLOCKING:` lines.

## Steps

1. **Parse args:** `path=$1` (the text to read); optional `--out <dir>` (default
   `<dir-of-path>/beta-reports/`). Read the text once.

2. **Read run-config** (`config/run-config.md`, via `parse_yaml_blocks`):
   `beta_models`, `panel_size`, `beta_consensus_k`. Resolve the **reachable**
   subset of `beta_models` (skip models the adapter layer cannot reach today —
   cross-model access is rate-limited, §10).

3. **Fan out.** For each of the six personas in
   `config/beta-readers/personas/*.md`, dispatch up to `panel_size` `beta-reader`
   sub-agents across **distinct** reachable models. If fewer models are reachable
   than `panel_size`, repeat-sample the reachable ones (the collapser flags the
   panel `degraded`). Each sub-agent receives ONLY `{ text, persona_file }` — no
   ledgers, outline, solution, or rules.

4. **Each sub-agent** writes one raw reading via `scripts/beta_report.py`
   (`build_raw_reading` → `write_raw_reading`) into the `--out` dir.

5. **Collapse.** For each persona, load its raw readings and call
   `beta_report.collapse_persona(readings, k=beta_consensus_k, panel_size=panel_size)`,
   then `write_converged(out_dir, report)` → `<persona>.converged.md`.

6. **Report** to the showrunner: the six per-persona converged reports (engagement
   curves, consensus put-down points, would-buy tallies), noting any `degraded`
   panels. Do **NOT** aggregate across personas — the cross-persona revision-priority
   report is Phase 6. Do **NOT** write `.penny/current-stage`; this stage is
   non-blocking and outside the gate.
