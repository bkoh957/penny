---
description: Show where a book is in the pipeline — every step with two statuses, its command, its artefact, and the single next action.
argument-hint: <book-number> [chapter-number]
---

# /book-status

Read-only. This command writes nothing, mints nothing, and touches no lock. It
is safe to run at any time, on any book, including one mid-draft.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), optional `chapter=$2`. Resolve the
   active series root; hard-error if cwd is not inside a series.

2. **Render the status:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/book_status.py" "$book" ${2:+"$2"}
   ```

   Exit 2 means a usage problem — no such book, an invalid id, or no outline to
   report on. Show the message; there is nothing to work around.

3. **Present it as printed.** Do not summarise the table away or re-order it.
   The two columns mean different things: **RUN** is "the artefact exists",
   **PASS** is "the proof exists and is still current". A `—` means the step has
   nothing to pass and is never a failure. A `?` means the check could not run —
   say so plainly rather than treating it as either a pass or a fail.

4. **Lead with the `next:` line.** It names the one command that advances the
   book, and it prefers finishing something half-done over starting something
   new.

5. **Stop.** This command reports. It never advances a step.
