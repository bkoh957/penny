# Book status — design

> **Status:** approved in brainstorm 2026-08-01; not yet planned.
> **Adds:** one deterministic reporter (`/book-status`) over state that already exists.
> **Changes elsewhere:** one field added to the mystery lock certificate (§5) — the only
> edit outside the new script.
> **Leaves untouched:** every gate, every command, every artefact. This spec reports; it
> never advances a book.

---

## 1. The failure this fixes

There is no view of where a book is. Three partial things exist, and one of them gives
dangerous advice.

**`.penny/current-stage`** is a single hand-written line — book 01's currently reads
`book=01 stage=OUTLINE-REVIEWED`. It feeds the terminal status line and nothing else. It
is a label someone typed, not a state anyone checked, and it has been wrong for days.

**`plot_stage.py status NN`** is the only real progress tracker and it covers only the
plotting workshop. Run today against book 01 it reports every stage stale and
`next: premise` — go rewrite the premise of a book that has been shaped by hand for
weeks. It is not lying about its own stages; it simply cannot see that the book left the
workshop, because nothing downstream of the workshop is in its model.

**`preflight.py`** knows every gate in the pipeline, but answers one question at a time,
only when a command asks it.

So the showrunner cannot answer "where is this book, what is done, what is next, and
where is the artefact" without reading the filesystem by hand.

**The sharpest instance: staleness is invisible.** Book 01's mystery lock was minted
2026-07-28T03:10. `input/book-01/outline.md` was last edited 2026-07-30 13:48. The lock
exists, so every existence check passes — and it attests to a book that changed two days
later. Nothing in the engine surfaces that, and the showrunner found it only because a
spec review went looking.

---

## 2. Two statuses, because "done" is two different questions

Each row carries **RUN** and **PASSED**.

- **RUN** — the artefact exists.
- **PASSED** — the gate, certificate, or check that proves the artefact is good exists
  **and is still current**.

Keeping them apart is what makes the view honest. A draft exists while its gate says
HOLD. An outline exists with a lock that no longer describes it. Collapsing these into
one "done" tick reproduces exactly the `current-stage` failure in a new file.

**`—` means the step has nothing to pass.** Running it *is* the outcome — the diagnostic
views, the beta read. A `—` is not a pending state and must never render as a failure.

**Staleness is a reason, not a third column.** A stale artefact shows `PASSED ✗` with the
reason named in the row: *STALE — outline 30 Jul, lock 28 Jul*. Two columns stay
scannable; the reason column carries the detail. This is the same shape as the rest of
the engine — a named predicate, not a status code.

---

## 3. Everything is derived. No new certificate.

The brainstorm proposed that human judgement calls become out-of-band certificates. On
working through the rows, **they already are**, and no new certificate is needed:

- the **mystery lock** certifies the whodunit validated;
- the **dev-clear cert** (`.penny/locks/book-NN.ch-MM.dev-clear`) certifies the showrunner
  accepted a developmental report, bound to `cleared_draft_sha256`;
- the **`.approved` cert** (`.penny/locks/book-NN.approved`) certifies the book approved.

The one row that looked like it needed a new certificate — *outline reviewed* — turns out
to be derivable: the feedback ledger exists (RUN) and carries zero `state: open` items
(PASSED). Book 01 has twelve, all open.

So `/book-status` reads only what other commands already wrote. **It never writes
anything**, mints nothing, and cannot itself go stale, because there is nothing to keep
up to date.

---

## 4. The rows

Book-level rows always render. Chapter work renders as `x/28` counts (§6).

| Row | RUN | PASSED |
|---|---|---|
| outline | `input/book-NN/outline.md` exists | `outline_check.py` exits 0 |
| diagnostics | `output/book-NN/reports/outline-glance.md` exists | `—` (name which of glance / strands / spine-map are present in the reason column) |
| outline feedback | `outline-feedback.yaml` exists | see below — three states, not one pass/fail |
| mystery lock | `.penny/locks/book-NN.mystery.lock` exists | lock exists **and is not stale** (§5) |
| packets | count of `input/book-NN/packets/ch-*.md` | count whose `built_from_outline` still matches |
| maps | count of `input/book-NN/maps/ch-*.md` | count where `map_check.py` exits 0 |
| drafts | count of `ch-MM.draft.md` | `—` |
| gates | `—` | count of `ch-MM.gate.md` containing `gate: PASS` |
| dev cleared | `—` | count of dev-clear certs whose `cleared_draft_sha256` matches the current draft |
| finals | count of `ch-MM.final.md` | `—` |
| manuscript | `output/book-NN/book-NN.manuscript.md` exists | `.approved` cert exists |
| beta read | per-persona beta reports exist | `—` |

Every row also carries **the command that advances it** and **the path to its artefact**,
so the view answers "what do I run next" without a second lookup.

Counts are always `x/total_chapters`, read from the outline's frontmatter — never from
whichever directory happens to be fullest.

**The outline-feedback row is three states, not a pass/fail.** "Done" collapsed two
different questions before this same failure was fixed for RUN/PASSED in general (§2);
the feedback row had a second instance of it hiding inside its own PASSED cell, between
"never reviewed by a panel" and "reviewed, then the outline moved on":

- **Unreadable** — the ledger file exists but does not parse (bad YAML) or parses to
  something other than a mapping (e.g. a bare list). → `?` (`unknown`), with a named
  reason, on the `?` footer, excluded from `next:` selection. This must be detected
  *before* the row hands the file to `outline_feedback.load_ledger()`: that accessor
  returns a blank empty ledger (`reviewed_outline_sha256: ""`) for any unreadable file,
  indistinguishable downstream from a ledger that was genuinely never
  panel-reviewed — which would misreport a parse failure as a truthful staleness verdict
  it cannot possibly have earned.
- **Never panel-reviewed** — the ledger parses fine, but `reviewed_outline_sha256` is
  empty or absent. → **not stale.** This is the ordinary shape while `/plot-book`'s
  fan-audit is the only thing that has appended: it deliberately leaves the stamp blank
  because no review panel has read `outline.md` (only `outline-skeleton.md`, or nothing
  yet — see `commands/plot-book.md`'s `--source` handling). Open items are counted
  exactly as the reviewed case, `fix_command` is preserved, and the reason names that no
  panel review has run yet, so the row reads honestly without being falsely marked STALE
  the moment `/expand-outline` later writes `outline.md`.
- **Stale** — a **non-empty** `reviewed_outline_sha256` that no longer matches the
  outline on disk. → fails, regardless of open-item count (this is the shipped I2
  behaviour — see `outline_feedback.status_line`, which this row must not contradict).

---

## 5. Staleness needs the lock to carry a fingerprint

**The mystery lock records no fingerprint.** Its whole content is:

```
book: 01
validated: fairplay+lexicon+tension
locked_at: 2026-07-28T03:10:33.165673+00:00
```

So "is this lock still true of this outline" cannot be answered from the certificate. The
dev-clear cert already solves the same problem correctly, binding to
`cleared_draft_sha256`; the lock is the odd one out.

**Change:** `preflight lock-mystery` gains one field on the certificate —
`outline_sha256`, the sha of the outline it validated. `/book-status` compares it to the
current outline. This is the only edit this spec makes outside the new reporter.

**Legacy locks report `staleness unknown`, never `fresh`.** A lock minted before this
change has no `outline_sha256`, and the correct report is that the question cannot be
answered — not a green tick. This follows the rule the codebase already applies to the
lock certificate (`2026-07-30 §7`): a certificate must never claim coverage it does not
have. Book 01's existing lock is exactly this case, and it is being re-minted during the
book's repair anyway.

**mtime is not the fallback.** Comparing `locked_at` against the outline's mtime is
tempting and wrong: a `git checkout` rewrites mtimes and would silently flip a stale lock
to fresh, or a fresh one to stale. A wrong answer here is worse than `unknown`, because
the entire value of this row is that it catches the case existence checks miss.

---

## 6. Chapter drill-down

`/book-status NN` shows counts. `/book-status NN MM` expands one chapter into its own
rows — packet, map, draft, gate, dev-clear, final — with the same two statuses and the
same command-and-artefact columns.

Counts by default because at 28 chapters a full grid of dots dominates the view during
the many weeks a book is still being outlined. Detail is one argument away when a chapter
is actually stuck.

---

## 7. The `next:` line

One line at the foot naming the next action. It is the point of the whole view, and the
thing today's tooling gets wrong: `plot_stage.py` says `next: premise` for book 01;
reading the same filesystem, this should say *work the 12 open feedback items, then
re-mint the lock*.

**Rule: `next:` is the first row that is RUN but not PASSED; if every run row has passed,
it is the first row not yet RUN.** Fixing a thing that ran badly outranks starting the
next thing. That single rule produces the correct answer for book 01 without special
cases — the outline feedback row is RUN with twelve open items, so it comes before the
lock, which comes before packets.

Three clarifications the rule needs to be unambiguous:

- **A count row is RUN when its count is above zero, and PASSED only when every chapter
  has passed** (`28/28`). So a partially drafted book has a RUN-but-not-PASSED row and is
  correctly told to finish it before starting the next step.
- **A `—` cell is never a failure and never selects the row.** A row that is `—` in the
  PASSED column can still be chosen on the RUN half of the rule; a row that is `—` in the
  RUN column is only ever judged on PASSED.
- **A `?` row — a check that could not run (§8) — is skipped for `next:` selection and
  named on its own line beneath it.** Guessing a next action from a fact the engine
  admits it does not have is exactly the failure this spec exists to remove.
- **The row names the command that advances it *from its current state* — for a row
  that ran and failed, that is the fix, not the re-run.** Most rows' create-command and
  fix-command are the same thing (e.g. a stale mystery lock re-validates and rewrites on
  `preflight lock-mystery`, so no distinct fix is needed). Two rows are the exception,
  where re-running the create-command is actively harmful: outline feedback
  RUN-but-not-PASSED must not print `/review-outline`, which appends a second review pass
  and grows the backlog it is reporting — the fix is hand-editing `state:` in the ledger;
  manuscript assembled-but-not-approved must not print the bare `/assemble-book`, which
  re-runs the cross-model final read — the fix is `/assemble-book NN --approve`.

`next:` is advisory. It never blocks and the command always exits 0 when it could read
the book (§8).

---

## 8. Errors and degradation

- **Exit 0 whenever the book could be read**, whatever the rows say. This is a report, not
  a gate; a book with everything failing is a successful run of `/book-status`.
  Exit 2 for usage errors: no such book, an invalid book/chapter id. **Exit 1 when run
  outside a series** — the house convention, set by `penny_paths.series_root()`'s
  `sys.exit(msg)` and shared by every script in the engine; `/book-status` does not carve
  out its own exit 2 for this one case.
- **A row whose check cannot run reports why, in its reason column, and never guesses.**
  An unparseable length profile, an unreadable ledger, a missing genre — each renders as
  `?` with the reason named, exactly as §5 handles a legacy lock. For the feedback
  ledger specifically, "unreadable" means a genuine parse failure or a non-mapping
  document (§4) — detected before the row ever calls `outline_feedback.load_ledger()`,
  whose own empty-ledger fallback would otherwise turn that failure into a false
  staleness verdict. A ledger that parses fine but was never panel-reviewed
  (`reviewed_outline_sha256` empty) is a known, ordinary state (§4), not an unreadable
  one, and must not render as `?`.
- **Never a traceback.** A malformed feedback ledger, a corrupt lock, a packet with no
  stamp: each degrades to `?` plus a named reason for that row alone. One broken artefact
  must not cost the showrunner the other eleven rows.
- No row's failure prevents another row from rendering.

---

## 9. Genre and location agnosticism

`/book-status` names no genre artefact. Rows are pipeline steps, which are engine-level
and identical across genres. Where a row needs genre data — the map check's length
profile, the lock's validator set — it resolves through the existing accessors
(`penny_genre`, `penny_paths`), never by filename. A series whose genre declares no beat
sheet still gets every row it can compute, with `?` and a reason on the rest.

Paths resolve against the series root via `penny_paths`, so `/book-status` runs from any
directory inside a series and refuses outside one, like every other pipeline command.

---

## 10. Testing

Test-first against `tests/fixtures/`, per repo convention. The reporter is fully
deterministic, so every row is directly testable.

- A fixture series per interesting shape: nothing but an outline; outline + stale lock;
  outline + fresh lock + partial packets; a book mid-draft with mixed gate results.
- **The staleness row gets the sharpest test:** a lock whose `outline_sha256` matches
  reports PASSED; one that does not reports `✗ STALE`; one with no `outline_sha256` at all
  reports `? unknown` and **must not** report either PASSED or STALE.
- `next:` gets a test per branch of §7's rule, including the run-but-not-passed case that
  book 01 exercises.
- One test asserts a malformed artefact degrades that row to `?` and leaves every other
  row intact — the §8 promise.
- One test asserts exit 0 on a book where every row fails, and exit 1 outside a series
  (§8's ruling).

---

## 11. Out of scope

- **Advancing anything.** `/book-status` reports. It never runs a step, mints a
  certificate, or edits an artefact.
- **A series-wide view across books.** `/book-status` takes one book. A roll-up across a
  series is a reasonable later addition and is not designed here.
- **Retiring `.penny/current-stage`.** The status line still reads it. Whether this
  reporter should replace that file is a separate question — this spec neither removes it
  nor keeps it in sync, and the two may disagree until it is settled.
- **Backfilling `outline_sha256` onto existing locks.** Legacy locks report `unknown`
  (§5) until re-minted in the ordinary course of work.
