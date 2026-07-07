---
description: Assemble finalized chapters into the book manuscript, run the cross-model final read, build the revision-priority report, and pause for showrunner approval.
argument-hint: <book-number> [--approve]
---
# /assemble-book

The book loop (design §5 per-book flow, §7 cross-model routing, §10). Assembles the
manuscript, gates cross-model independence, runs the ONE genuine holistic judgment
(the `final-reader`), builds the deterministic revision-priority report, then pauses
for the showrunner. Approve by re-running with `--approve`. Mirrors `ledger_approval`:
`book_approval: review` pauses; `auto` would mint the cert end-to-end.

## Steps

### Parse args

```bash
book=$1            # e.g. 01
flag=${2:-}        # optional --approve
```

---

### `--approve` RESUME BRANCH (handle before everything else)

If `$flag` equals `--approve`, enter the approval path — do NOT re-run any agents
(re-running the final read would discard the reviewed judgment):

1. Assert the showrunner has seen the artifacts (stage marker reads
   `book=$book stage=BOOK-REVIEW`). If not, stop and report which stage is active.

2. Seal the manuscript (stamp `read_by` from the final read):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/assemble_book.py" seal $book
   ```

3. Run the precondition gate + mint the `.approved` cert (its last write):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" approve-book $book
   ```

   A nonzero exit aborts — the cert is NOT minted; resolve the named predicate first.

4. Call the reserved per-book demotion hook (Phase-6 no-op; pinned signature):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/canon_core_review.py" --book $book \
     --canon-core series/continuity/canon-core.md
   ```

5. Write the stage marker and report:

   ```bash
   echo "book=$book stage=BOOK-APPROVED" > .penny/current-stage
   ```

   Report "Book $book approved — `.penny/locks/book-$book.approved` minted." and STOP.

---

### Step 1 — Assemble the manuscript

```bash
echo "book=$book stage=ASSEMBLE" > .penny/current-stage
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/assemble_book.py" assemble $book
```

A nonzero exit (chapter gap, missing `drafted_by`, outline mismatch) aborts.

### Step 2 — Cross-model pre-flight gate (built Phase 3; wired here)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" assemble $book
```

This enforces `final_read_model != drafting_model` and `final_read_model ∉ drafted_by`
BEFORE the read runs. A nonzero exit aborts — fix routing in `config/run-config.md`.

### Step 3 — Dispatch the `final-reader` agent (cross-model, informed)

Dispatch the **`final-reader`** sub-agent with:
- `output/book-$book/book-$book.manuscript.md` — the assembled manuscript.
- `series/whodunit/book-$book.yaml` — the mystery solution (informed read).
- the arc-ledger slice (`series/arc-ledger.md` + the thread file that is the intended
  series hook) — required to judge `thread_left_open`.

The agent MUST be `final_read_model` (must not be a drafter). It writes
`output/book-$book/book-$book.final-read.md` (`schema: penny-final-read/1`).

### Step 4 — Validate the final-read shape (hard gate)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/assemble_book.py" validate-read $book
```

A nonzero exit means a malformed/hedged read (`standalone`/`mystery_resolved`/
`thread_left_open` must be `yes|no`). Stop and re-dispatch the agent — do not proceed
to approval with a malformed read.

### Step 5 — Build the revision-priority report (deterministic)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/revision_priority.py" $book
```

Reads the 6 `output/book-$book/reports/<persona>.converged.md` (from `/beta-read`) +
every `output/book-$book/chapters/ch-*.gate.md`. Writes
`output/book-$book/reports/revision-priority.md`. Non-blocking (always exit 0).

> If `/beta-read` has not been run for this book, the converged reports are absent and
> the report's put-down/would-buy sections will be empty — note this to the showrunner;
> it is a missing input, not a clean book.

### Step 6 — Present the two artifacts and pause (`book_approval`)

Read `book_approval` from `config/run-config.md`.

**`review` (default):** Set the stage marker and surface BOTH artifacts:

```bash
echo "book=$book stage=BOOK-REVIEW" > .penny/current-stage
```

Present to the showrunner:
- the final-read booleans (`standalone` / `mystery_resolved` / `thread_left_open`)
  and the `## Holistic verdict` prose from `book-$book.final-read.md`;
- the `## ESCALATE` / `## LOG` sections and `escalations:` count from
  `reports/revision-priority.md`.

Then say:

> "Book $book is assembled and read. Review the final-read verdict + revision-priority
> report above, then approve by running:
>
> `/assemble-book $book --approve`"

**Do not seal, gate, or mint the cert. Stop here.** The showrunner must explicitly
re-run with `--approve`.

**`auto`:** proceed directly through the `--approve` branch steps 2–5 (seal →
approve-book → demotion hook → marker) without pausing.
