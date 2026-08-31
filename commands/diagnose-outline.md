---
description: Render the three read-only diagnostic views over a book's existing outline, and map its chapters onto the genre's structural jobs.
argument-hint: <book-number>
arguments: [book]
---

Read-only throughout. Nothing here writes to `input/book-NN/outline.md`, and
nothing mints or deletes a lock. Safe to run on a locked book.

## Steps

1. **Parse args:** `book=$book` (e.g. `01`). Resolve the active series root; hard-error
   if cwd is not inside a series.

2. **Render the story at a glance:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" glance "$book"
   ```

   Exit 2 means the CLI refused — read the exact line it printed on stderr; it
   fires for a missing `outline.md` or an invalid book id. Fix the named
   problem and re-run rather than guessing.

3. **Render the strand pages:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" strands "$book"
   ```

   Exit 2 means the CLI refused rather than write an empty or wrong report —
   read the exact line it printed on stderr and act on it, don't assume a
   single cause: it fires both when there is no whodunit ledger at all and
   when the ledger has no `alibi_grid` entries. Either way, re-run with
   `--who name,name`. Do not skip the view.

4. **Render the spine worksheet:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" spine "$book"
   ```

   Exit 2 means the CLI refused — read the exact line it printed on stderr,
   don't assume a single cause. It fires for several distinct reasons: the
   series declares no genre; the genre's `genre.yaml` has no
   `macro_structure:` key; the structural-job file has a malformed or
   duplicate `<!-- job: -->` marker; or the file defines no jobs at all.
   Report the printed line verbatim and continue — the other two views still
   stand on their own, and **skip step 5**: with no worksheet written, there
   is nothing for `spine-mapper` to fill.

5. **If step 4 exited 0** (a worksheet was written), **dispatch
   `spine-mapper`** with the glance, the worksheet, and the resolved
   `macro-structure` file (`penny_genre.py macro-structure`). Write its filled
   worksheet to `output/book-$book/reports/spine-map.md`. If step 4 exited 2,
   skip this step entirely — never dispatch `spine-mapper` with a worksheet
   that was never written.

6. **Present, do not summarise away.** Show the showrunner: the path to the
   glance, one line per character naming how many chapters their strand covers,
   and the full list of jobs nothing answers. If step 4 exited 2, say plainly
   that the spine view was unavailable and why (the stderr line from step 4),
   rather than presenting an empty or missing jobs list as if it were a
   finding. The empty jobs are the finding — only when the view actually ran.

7. **Stop.** This command diagnoses. Every repair is the showrunner's call, made
   one chapter at a time.
