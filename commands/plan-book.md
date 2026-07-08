---
description: Plan a book — resolve the active series' genre and delegate to that genre's planning runbook.
argument-hint: <book-number>
---

# /plan-book NN

Genre-neutral planning front door. It resolves the active series' genre (from
`series.yaml`, via `penny_genre`) and runs that genre's planning flow — so a cozy
series runs the whodunit planner and a thriller runs the thriller planner, without
the author choosing a genre-specific command.

## Steps

1. **Parse args:** `book=NN` (e.g. `01`).

2. **Resolve the genre's planning command:**

   ```bash
   PLAN_CMD="$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" planning-command)"
   ```

   If this fails (no `series.yaml` / unknown genre), stop and tell the author to
   run `/new-series` or add a `genre:` line to `series.yaml`.

3. **Delegate** to the genre's planning runbook named by `$PLAN_CMD`
   (e.g. `plan-mystery` for cozy-mystery). Invoke that command with the same
   `book` argument and follow it to completion. `/plan-book` adds no planning
   logic of its own — it only routes.
