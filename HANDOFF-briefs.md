# Handoff — Penny (fiction-series engine) / briefs → packet/map
Saved: 2026-07-19 | Type: build

> **Stream note.** `HANDOFF.md` = the Hermes / LM Studio drafting stream; `HANDOFF-plot.md`
> = the plotting workshop (shipped). This stream shipped the packet/map redesign
> (2026-07-18) and is now mid-way through the **book-01 migration** it enabled
> (2026-07-19). The brief compiler, `brief-weigher`, `/build-briefs`, scene weights, and
> the weigh-before-lock dance NO LONGER EXIST — don't reach for them.

## What we're building

The packet/map redesign (previous save) is shipped and pushed. This session did the
**book-01 migration** it was waiting on: rechaptered the live series' 27-chapter outline
into 39 packet-format chapters, retuned the cozy genre's overload cap for the new
beats-inclusive counting, and renumbered + corrected the whodunit ledger to match. The
book is currently **unlocked** (lock deliberately deleted) and **not yet re-lockable** —
see the blocking gap below before attempting `preflight lock-mystery`.

**Spec:** `docs/superpowers/specs/2026-07-18-packet-map-chapter-design.md` §10 (migration)
**Recovery ledger:** `.superpowers/sdd/progress.md` — the packet/map build's per-task
history. This migration session wasn't plan-driven, so it isn't in that ledger; this
handoff is the record.

## Git state — TWO repos touched this session

**Engine repo** (`~/myTools/penny`), branch `main`:
- Uncommitted: `genres/cozy-mystery/beat-sheet.yaml` (`obligations.max_per_chapter` 8→15)
  and `tests/test_preflight.py` (bumped `_beat_heavy_wired_outline`'s fixture from 9→16
  beats so it still exceeds the new cap — the old fixture's load of 10 no longer tripped
  cap 15, which silently broke two tests until I fixed the fixture).
- Last commit: `e9750aa` (previous handoff save). Nothing new committed this session.
- **Tests: 595 passing**, verified after both edits. Verify: `python3 -m pytest`.

**Series repo** (`~/myBooks/series-pelicanscrook`), a separate private git repo:
- **New, untracked:** `input/book-01/outline-packet.md` (2,218 lines) — the full 39-chapter
  packet-format outline, migrated from the old 27-chapter `outline.md` (which is
  UNTOUCHED — both files currently exist side by side).
- **Modified, uncommitted:** `series/whodunit/book-01.yaml` — renumbered to the 39-chapter
  scheme (`total_chapters: 39`, `reveal_chapter: 37`), with five entries corrected against
  the outline TEXT rather than mechanically translated (the pre-existing ledger already
  disagreed with the prose in these spots, independent of this migration — see the
  in-file comment for which ones and why).
- **Deleted in the working tree (git status shows `D`), NOT deleted by me this session**:
  several `output/book-01/chapters/*` draft/review artifacts (ch-01.draft.md, ch-02/03
  ai-smell and local-review files). Pre-existing local state from before this session —
  investigate before committing anything broadly, since a wide `git add` would commit
  those deletions too.
- **Untracked, not created by me:** `output/book-01/chapters/ch-01.draft-codex.md`.
- **Lock removed:** `.penny/locks/book-01.mystery.lock` deleted (gitignored, won't show in
  `git status`). The book is functionally unlocked right now.
- Last commit (series repo): `b14f701 docs: trim book 1 outline beats`.

## Next actions

1. **BLOCKING GAP — `preflight lock-mystery` will NOT read the new outline yet.**
   `scripts/preflight.py`'s `cmd_lock_mystery` hardcodes
   `input/book-{book}/outline.md` (lines ~321, ~365) — it has no awareness of
   `outline-packet.md`. Re-locking right now would validate the OLD 27-chapter outline
   against the NEW 39-chapter ledger (chapter numbers wouldn't even align) and either
   crash or silently validate the wrong thing. **Before re-locking**, decide and do one of:
   - Replace `outline.md` with `outline-packet.md`'s content (rename/overwrite) — the
     straightforward path, since the old file's only remaining value is as a diff
     reference now that migration is done.
   - Or teach `packet_assemble.py`/`preflight.py` to read an alternate filename — more
     invasive, not obviously worth it for a one-off migration.
   I did not make this call — it's the showrunner's, since it touches which file is
   canonical going forward.
2. **Then**: `preflight lock-mystery 01` from the series root — validates fairplay +
   lexicon + the nine tension checks (including the retuned `overloaded-chapter`) against
   the new outline + corrected ledger, and mints a fresh certificate.
3. **Then**: `/map-chapter 01 01` (or wherever the showrunner wants to start) — the real
   shakedown. The existing 3 drafts (old ch-01 opus/codex/glm, old ch-02) are salvage
   material for whichever new chapters they map onto (old ch-1 became new ch-1 "The
   Wheelhouse" + new ch-2 "The First Right Piece" — the ratified split example).
4. **Review before committing** the series repo's uncommitted changes (`outline-packet.md`,
   the ledger) — and resolve the pre-existing deleted/untracked files noted above first,
   so they don't get swept into an unrelated commit.
5. **Deferred, unchanged:** the length/compression companion spec (`length_check.py`,
   `/compress-chapter`); `/new-series` onboarding brainstorm (still owed).

## Decisions made this session

- **`obligations.max_per_chapter` retuned 8 → 15**, not left blended with a formula
  change. Beats + tracks alone measured 6–9 per chapter across the new 39-chapter outline
  (mean 8.2); the canonical spec example (real book-1 chapter 5) carries exactly 15. The
  check fires on `load > cap`, so 15 clears that example with zero headroom above it and
  clears every chapter in the new outline (max currently 9, before ledger clues are
  counted in). Considered and rejected: removing beats from the check entirely — that
  would make the check blind to the exact beat-inflation disease this whole redesign
  exists to fix (a chapter with 15+ required beats and no clues would score near-zero).
- **Ledger renumbering was content-first, not number-first.** Several of the ledger's OLD
  chapter references already didn't match the OLD outline's prose (pre-existing drift,
  confirmed by grep against the actual scene content) — `clue-car-on-street`'s plant/payoff
  chapters, and the `faye`/`vanessa-calloway`/`cobber` alibi_grid rows. I corrected these
  against the text rather than mechanically translating stale numbers forward, since
  `pays_off_chapter` isn't validated by any deterministic check (confirmed: only
  `lmstudio_draft_chapter.py` reads it) so silently propagating wrong numbers would help
  no one. `plant_chapter` IS checked by `fairplay_check.py`, but only for presence/validity,
  not textual accuracy — so getting these right matters for `packet_assemble.py` pulling
  the right clue prose into the right chapter's packet, not for passing the lock.
- **Wrote the new outline to a new filename (`outline-packet.md`), not over `outline.md`.**
  Deliberate, so the showrunner could compare old vs new before committing to the
  replacement — this is *why* next-action #1 above is now a blocking gap: the safety
  choice created a follow-up decision that wasn't resolved this session.

## User preferences expressed this session

- Wants the actual counting mechanism explained precisely when questioning a check (asked
  "how does it identify a beat" — wanted the literal regex/parsing behavior, not a
  conceptual gloss). Answer: `Required Beats` are counted by a naive bullet-line regex
  (`^\s*-\s+(.*\S)\s*$`) under that H3 heading — no semantic judgment, purely syntactic;
  worth remembering this predicate style when explaining any deterministic check.
  Also asked "why count beats at all" and "what if we remove them" before agreeing to just
  raise the cap — walk through the tradeoff, don't just defend the existing design.
- Confirmed: raise the cap to a specific number (15) rather than have me pick — wants the
  concrete number decided, then wants me to just execute (find the file, make the edit,
  verify) without further discussion once the number is given.
- Wants exact counts when asking "how many would fail" — ran the numbers precisely (11 of
  39 at the old cap, named which chapters) rather than giving an estimate.

## Watch out for

- **The BLOCKING GAP above is the single most important thing for the next session to
  read first.** Don't run `preflight lock-mystery 01` without resolving it — it will not
  do what anyone expects.
- **The taste stage is still untested by construction.** 595 green + a clean fairplay
  check proves parsing, renumbering, and cap arithmetic. It proves nothing about whether
  `map-maker` proposes good maps against the new 39-chapter material. First live
  `/map-chapter` run is still the real shakedown, same caveat as the previous handoff.
- **Two repos, two git states, easy to conflate.** The engine repo's uncommitted changes
  (beat-sheet cap + test fixture) are small and safe to commit together. The series repo's
  uncommitted state is bigger and has pre-existing clutter (the deleted/untracked files
  above) that predates this session — don't `git add -A` there without checking first.
- Wiring footer syntax is still bulleted-bold only (`- **Opens:** q-slug — phrasing`) — the
  new `outline-packet.md` deliberately carries NO `Because/Opens/Closes` q-slug chains at
  all (it's unwired, like the source outline was), only Required Beats + tracks + a graded
  Hook. `has_wiring()` on it returns `False` by design — the tension graph checks stay
  skipped exactly as they were pre-migration. Don't be alarmed if `tension_check.py` reports
  "no wiring detected."
- User's working style, still true: plain language over jargon; discuss in prose before
  menus; wants precise numbers when precision is available rather than estimates; confirms
  a decision once, then wants execution without re-litigating.
