# Handoff — Penny (fiction-series engine) / views
Saved: 2026-08-03 | Type: build

> **Stream note.** `HANDOFF.md` = LM Studio drafting. `HANDOFF-plot.md` = the plotting
> workshop (shipped 2026-07-12). `HANDOFF-briefs.md` = packet/map redesign (shipped
> 2026-07-18) — **superseded, do not act on it.** `HANDOFF-readback.md` = staged
> reveal-aware read-back (shipped 2026-07-31) — its book-01 next-actions are
> **superseded by this file**, and its `reveals:` numbers are wrong (see *Watch out for*).
> **This is the only live stream.**

## What we're building

The showrunner challenged the whole outlining process. Going through `/plot-book` they
answered premise → ending → turning-points as best they could but could never see the
book coming together, so real judgement deferred itself to `outline.md` — 14,000 words
arriving after every decision had compounded into chapters. The proof was **Simon**, the
victim's husband, who knows the handover appointment was altered, never acts on it, and
leaves the book at chapter 11 of 28. Every reviewer missed him, because nothing asks
*would this person do this* and the defect lives in the gap between two chapters.

**Shipped and pushed:**
- **`/diagnose-outline NN`** — three read-only views over the outline that already
  exists: the story at a glance (2,140 words vs the outline's 14,170), one character's
  strand through the whole book, and the genre's 28-job spine worksheet + `spine-mapper`.
- **`/book-status NN [MM]`** — where a book actually is. Two statuses per row (RUN = the
  artefact exists, PASSED = the proof exists *and is still current*), the command that
  advances each, and one `next:` line.
- **The mystery lock now records `outline_sha256` + `outline_source`**, so it can say
  when it describes a book you have since changed. Legacy locks report `unknown`, never
  `fresh`.
- `readers-copy` no longer requires the retired `outline-skeleton.md`.

**Specs:** `docs/superpowers/specs/2026-07-31-layered-outline-workshop-design.md`,
`docs/superpowers/specs/2026-08-01-book-status-design.md`
**Plans:** `docs/superpowers/plans/2026-07-31-outline-diagnostic-views.md`,
`docs/superpowers/plans/2026-08-01-book-status.md`
**Execution ledgers (every finding, ruling and reproduction — trust over memory after a
compaction; deliberately kept):** `.superpowers/sdd/2026-07-31-outline-diagnostic-views/progress.md`,
`.superpowers/sdd/2026-08-01-book-status/progress.md`

## Git state

- Branch: `main`, **in sync with origin** (`d6d1b84..9d53dc0` pushed 2026-08-02)
- Uncommitted changes: none in this repo. **The series repo has uncommitted work** —
  `input/book-01/outline.md` is modified (the showrunner's own edit, see below).
- Last commit: `9d53dc0 fix(status): feedback row is three states, not stale-vs-fine`
- Tests: **780 passing** (`python3 -m pytest`). Was 647 at the start of this stream.

## Next actions

Run `python3 ~/myTools/penny/scripts/book_status.py 01` from
`~/myBooks/pelicanscrook-series` — it prints the current state and the next action.
As of this save it says `next: /review-outline 01`, **and that is the one wrong line on
the table — do not run it** (see *Watch out for*).

1. **Work the 22 open feedback items.** `outline_feedback.py render 01` writes the
   side-by-side view. 15 from Claude, 7 from Codex, pass 2, correctly indexed to the
   current 28-chapter outline. The showrunner decides; the edits go into `outline.md`
   one chapter at a time; each item's `state:` is hand-edited to `solved`/`rejected`.
   - Sharpest: **`q-clear` opens in ch 2 and is never carried again** — Maggie's own
     jeopardy, dropped, though the impersonation makes her *more* framable. Seven
     questions open and never close.
2. **The stalker.** The spine map says he is load-bearing, not a subplot: he fills both
   empty structural jobs. Decide who he is (Simon, or someone else — and if someone
   else, what is Simon's answer for staying silent) and **why the witness does not go to
   the police** — that answer is the subplot's engine.
3. **Re-read after edits:** `outline_views.py strands 01`, then `book_status.py 01`.
   Loop until the strand pages read clean.
4. **Close out:** write `reveals:` (**13 and 25**, not 15 and 27), delete the drifted
   `outline-skeleton.md`, delete the stale lock, `preflight.py lock-mystery 01`. The
   re-minted lock will carry a fingerprint.
5. **Engine follow-ups, in priority order:** the `next:` fix-command gap (below); the
   `outline_feedback.py` destructive overwrite; the multi-line parse error bleeding
   across the status table's columns; retiring `outline-skeleton.md` repo-wide
   (spec §9 step 5); book 01's derived `story.md` worksheet (spec §8.2.1).

## Decisions made this session

- **Thicker, not finer.** Each pass lays a complete strand over a fixed spine, read
  *alone* before braiding — because Simon's hole is invisible at every magnification.
- **Shape decided up front.** `macro-structure.md` already enumerates 28 structural jobs;
  pass 1 answers a form already written down. Cost: a strand cannot move a turn.
- **`outline.md` stays as it is and the showrunner stops reading it.** A third of its
  1,769 lines is repeated furniture, and that repetition is *required* —
  `packet_assemble.py` slices one chapter out, so each block must stand alone. It is a
  machine input. The fix is derived views, not a smaller file.
- **Two statuses, because "done" is two questions.** Collapsing RUN and PASSED into one
  tick reproduces the `.penny/current-stage` failure in a new file.
- **A certificate must not claim coverage it does not have.** Legacy locks report
  `unknown`. mtime is explicitly refused as a staleness fallback — a `git checkout`
  would flip a stale lock green, and a wrong answer is worse than no answer.
- **Three ledger states, not two:** *unreadable* / *never panel-reviewed* / *stale*.
  Collapsing them made the tool state a falsehood and advise a destructive fix.
- **Book 01 is diagnosed, not re-plotted** — spec §1.1 ruling stands.

## User preferences expressed this session

- **Ask for the concrete walkthrough.** They twice stopped a menu to say "break it down
  / give me an example", and both times the concrete version changed the design. Lead
  with the worked example on their own book, not the taxonomy.
- **Separate what exists from what is planned.** "Is that a command, or am I changing a
  variable?" — never describe unbuilt tooling as runnable.
- **"By hand" reads as "you, alone, in an editor."** They decide; the machine generates
  and edits. Say which is which.
- **They spot the systemic fix.** Twice they cut through a reconciliation task with
  "isn't it easier to pick a source of truth?" — and were right both times. Offer the
  structural option before the laborious one.
- Still true: story in the subject of the sentence, no component tables; precise numbers
  over estimates; prose before menus; apply an established ruling rather than re-asking.

## Key files right now

- `scripts/book_status.py` — the pipeline report. `Cell`/`Row`, `book_rows`,
  `chapter_rows`, `tail_rows`, `next_action`, `render`, `one_chapter_rows`, `_main`.
- `scripts/outline_views.py` — the three views + CLI.
- `scripts/preflight.py` — `cmd_lock_mystery` now stamps `outline_sha256`/`outline_source`.
- `~/myBooks/pelicanscrook-series/output/book-01/reports/` — glance, spine-map,
  8 strand pages, `outline-review.md` (the 22 open items).
- `~/myBooks/pelicanscrook-series/input/book-01/outline.md` — canonical. 28 chapters,
  midpoint 13, reveal 24.

## Watch out for

- **`next:` names the wrong command for a STALE feedback row.** It prints
  `/review-outline 01`, which appends a *third* panel pass instead of clearing the
  backlog. A `fix_command` was added for the *open-items* case and not the *stale* case
  — a gap introduced knowingly and not closed. **Work the 22 items; do not re-review.**
- **The outline is "stale" only in the sha sense.** The showrunner edited two lines on
  2026-08-01 18:39 (the `# Outline Skeleton` heading, and the P thread rewritten to
  Maggie's fear-independence). Any byte flips the flag; it does not invalidate the 22
  items.
- **`HANDOFF-readback.md`'s `reveals:` numbers are wrong** — it says 15 and 27, which
  are skeleton-indexed. Against `outline.md` the same turns are **13 and 25**.
- **Do NOT run `/plot-book 01` after deleting the skeleton.** `stage_paths()` still
  hard-names it, so the tracker reports `chapters` missing and `/plot-book` would
  dispatch `chapter-weaver` to regenerate the book's middle. `stamp` now refuses by name
  rather than tracebacking. Full fix = spec §9 step 5.
- **Book 01 still has two outlines** — the 30-chapter skeleton (reveal 26) beside the
  canonical 28-chapter `outline.md` (reveal 24). `readers_copy` *prefers the skeleton
  while it exists*, so the read-back still reads the wrong book until it is deleted.
- **`outline_feedback.py` overwrites a corrupted ledger.** `append` → `load_ledger`
  (blank on parse failure) → `write_ledger`. `/book-status` no longer advises that path,
  but running `/review-outline` directly against a bad-indent ledger still discards every
  hand-set `state:`. Unfixed by design decision, not oversight.
- **A slug-format contract is now imposed on series data** — `^[a-z0-9][a-z0-9-]*$` on
  every `alibi_grid` `suspect:`. It is the path-traversal guard, so one nonconforming
  slug aborts the whole strands run. Nothing else in the engine documents this.
- **The unguarded-read class bit five times in one plan** — every instance traced to
  complete code written into the plan and transcribed faithfully. If you write
  implementation code into a plan, budget review rounds for your own blind spots, and
  make reviewers *reproduce* rather than reason.
- **Contract-pin tests** (`test_runbook_gives_literal_bash_for_every_stamp_call`,
  `test_outline_fan_contract`, `test_readme_check_count`) trip on deliberate prose
  rewrites. Standing rule: the approved artefact wins, re-pin the test — but that
  protects *previously-approved* artefacts; a test written minutes ago by the same task
  is not a contract, and the module's own convention outranks it.
