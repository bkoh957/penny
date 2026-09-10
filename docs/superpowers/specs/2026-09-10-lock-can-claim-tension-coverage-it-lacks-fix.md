# The lock certificate can claim tension coverage it does not have

Date: 2026-09-10
Status: design, approved in conversation, not yet implemented
Supersedes: nothing. Closes the residual surfaced by the final whole-branch review of
`docs/superpowers/plans/2026-09-10-restore-the-free-check-layer.md`, which was left
unfixed because the process allows one fix wave after a final review.

## 1. Why

A mystery lock is an **out-of-band certificate**: it exists only because validation
passed, and it records *what* it validated so it cannot claim more than it did. That is
the point of the `skipped: <check-id> — <why>` line, and `scripts/preflight.py:371-373`
says so in as many words:

```
# A check that COULD NOT RUN is never silent, and never a crash: it is
# named here and recorded on the certificate below, so the lock cannot
# claim coverage it does not have.
```

It can. Three of `tension_check`'s ten checks have **no code path by which to record a
skip**.

`scripts/preflight.py`'s `skipped_lines` are built from `check_tension`'s `notes`
channel. `check_overload` notes its own unrunnable cases explicitly — `"overloaded-chapter
— the obligation half of the check could not run: …"` — which is how `overloaded-chapter`
and `monotonous-closings` reach the certificate. But `_curve_checks` and `_beat_checks`
take no `notes` argument at all. They are simply skipped by a guard:

```python
# scripts/tension_check.py:492-498
if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
    beat_sheet = _load_yaml(beat_sheet_path)
    metrics["open_counts"] = _curve_checks(chapters, beat_sheet, reveal_ch, blocking)
    if turning_points_path is not None and Path(turning_points_path).is_file():
        ...
        _beat_checks(tp["points"], beat_sheet, total, reveal_ch, blocking)
...
return {"wired": True, "blocking": blocking, "notes": over["notes"], "metrics": metrics}
```

The returned `notes` are **only** `over["notes"]`. So when the guard is false, `dead-stretch`,
`starved-thread` and `off-mark-beat` produce nothing — no finding, no note, no `skipped:`
line — and the certificate is stamped `validated: fairplay+lexicon+tension`.

**There are two doors, not one.** The second is nested: with a beat sheet present but no
turning points, `off-mark-beat` alone vanishes the same way.

## 2. Evidence

A reviewer locked a genre-less series end-to-end: stdout named all five beat-sheet-dependent
checks, and the certificate read

```
validated: fairplay+lexicon+tension
```

with **zero** `skipped:` lines. In that legacy-shaped fixture all five vanished without
trace — the other two only reach the certificate when a beat sheet exists but declares no
`obligations.max_per_chapter` / `closings.max_same_kind_run`, which is a different case
from having no beat sheet at all.

The live series is a milder instance of the same shape: `.penny/locks/book-01.mystery.lock`
reads `validated: fairplay+lexicon`, which is honest — but only because the outline is
unwired, so tension is skipped wholesale and nothing claims otherwise.

## 3. Fix

Give the two silent guards the same duty `check_overload` already discharges: a check that
cannot run says so, by name, in the format the certificate already records.

**3a. Wired, no resolvable beat sheet.** Note `dead-stretch`, `starved-thread` and
`off-mark-beat` as unrunnable, naming the missing beat sheet as the reason.

**3b. Beat sheet present, no turning points.** Note `off-mark-beat` alone, naming the
missing turning points.

Both notes belong in `check_tension`'s **wired** branch only, and must flow through the
existing `notes` channel so `preflight` records them without change. Reuse
`BEAT_SHEET_DEPENDENT` where it applies rather than re-listing check ids.

### Explicitly NOT changed

- **The unwired path.** An unwired outline skips tension wholesale and `validated:` stays
  `fairplay+lexicon`, so nothing over-claims. These three checks all need wiring; on that
  path they are *not applicable*, not *unrunnable*, and noting them would turn every legacy
  outline's correct silence into spurious certificate noise — the same trap
  `_closings_check` already documents for an outline with no Closing section anywhere.
- **The stdout note.** `NO_BEAT_SHEET_NOTE` is a report line for a human reading the
  terminal. It stays. This spec is about the certificate.
- **No finding is added.** The roster stays at ten. A note is not a finding: it does not
  block, is not waivable, and cannot fail a lock.

## 4. Blast radius

`preflight lock-mystery` will now write `skipped:` lines on certificates that previously
carried none. A lock minted **before** this fix may therefore over-claim relative to one
minted after — the certificates are not comparable across the change, which is correct:
the old ones were wrong.

No lock is invalidated and none is rewritten; certificates are only ever minted, never
amended. Re-minting is the existing `delete the lock, re-run lock-mystery` path.

## 5. Test

1. **Wired, no beat sheet → three notes.** `check_tension` on a wired outline with
   `beat_sheet_path=None` returns notes naming `dead-stretch`, `starved-thread` and
   `off-mark-beat`.
2. **Wired, beat sheet, no turning points → one note.** Only `off-mark-beat`.
3. **Unwired, no beat sheet → no such notes.** The correct-silence case; guards against
   over-correction.
4. **End-to-end on the certificate.** `preflight lock-mystery` on a wired book with no
   resolvable beat sheet writes a `skipped:` line for each of the three. This is the test
   that would have caught the defect, and the one to mutation-test: delete the new notes
   and confirm it fails on the certificate's contents, not merely on stdout.
5. **A lock that runs every check records no `skipped:` line** — the converse, so the fix
   cannot degrade into noting unconditionally.
