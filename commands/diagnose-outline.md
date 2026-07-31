---
description: Render the three read-only diagnostic views over a book's existing outline, and map its chapters onto the genre's structural jobs.
---

Read-only throughout. Nothing here writes to `input/book-NN/outline.md`, and
nothing mints or deletes a lock. Safe to run on a locked book.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`). Resolve the active series root; hard-error
   if cwd is not inside a series.

2. **Render the story at a glance:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" glance "$book"
   ```

3. **Render the strand pages:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" strands "$book"
   ```

   Exit 2 with a `roster` message means the whodunit ledger has no `alibi_grid`.
   Re-run with `--who name,name`. Do not skip the view.

4. **Render the spine worksheet:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" spine "$book"
   ```

   Exit 2 means the series declares no genre, or its `genre.yaml` has no
   `macro_structure:` key. Report that by name and continue — the other two
   views still stand on their own.

5. **Dispatch `spine-mapper`** with the glance, the worksheet, and the resolved
   `macro-structure` file (`penny_genre.py macro-structure`). Write its filled
   worksheet to `output/book-$book/reports/spine-map.md`.

6. **Present, do not summarise away.** Show the showrunner: the path to the
   glance, one line per character naming how many chapters their strand covers,
   and the full list of jobs nothing answers. The empty jobs are the finding.

7. **Stop.** This command diagnoses. Every repair is the showrunner's call, made
   one chapter at a time.
