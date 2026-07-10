# Handoff — Penny (fiction-series engine) / main
Saved: 2026-07-10 | Type: build

## What we're building
Penny = ONE engine (a Claude Code plugin) driving MANY series (active series = cwd via a
`.penny/` marker), with a swappable genre-pack layer. Priority: **no engine drift**.
This session finally ran the **`/review-outline` live shakedown** (carried for three sessions),
then shipped the `recommendation` field it revealed a need for. Both are done.

## Git state
- **Engine** (`~/myTools/penny`, github `bkoh957/penny`): `main` clean, **pushed** (`bd50949..efe92b6`).
  Suite **371 green** (was 353 at session start).
  - `5b9bef9` spec, `8d1bd58` plan
  - `3ed18e2..efe92b6` — 5 TDD tasks + 2 fix waves, the recommendation field
- **Series** (`~/myBooks/series-pelicanscrook`, github `bkoh957/series-pelicanscrook`
  — **PRIVATE**): `main` clean vs origin, but **two things are uncommitted and are yours to decide on**:
  - ` M input/book-01/outline.md` — your own edit, predates this session. The panel reviewed
    *this* working-tree version (ledger sha `30ac6401…` matches it, not origin's).
  - `?? output/book-01/reports/` — the new `outline-feedback.yaml` (22 items) + `outline-review.md`.
    **It names the culprit.** Accepted by spec; the repo is private. Commit or not, deliberately.

## What happened this session

### 1. THE SHAKEDOWN PASSED — all four questions (`/penny-engine:review-outline 01`)
- **Plumbing:** fresh ledger, IDs contiguous `OF-1..OF-22`, all `state: open`, `pass: 1`,
  `reviewed_outline_sha256` matches the outline actually read. `outline_feedback.py status 01`
  exits **0** and prints only IDs, never text. Staging file landed at `.penny/outline-points-01.json`
  exactly as the runbook says.
- **Independence:** **Codex answered.** 10 claude / 12 codex, dispatched concurrently. No
  "independence reduced". The second seat is real.
- **Quality:** they **genuinely disagree**. Claude read as a cozy-craft reviewer (romance starved
  after ch11 `OF-1`; suspect-and-clear plateau `OF-2`; gift-as-vice averted `OF-4`). Codex read as a
  mystery-logic reviewer (what did Mary actually *find* `OF-11`; how does Pruitt lawfully obtain the
  letter `OF-12`; ch26 carries eleven payloads `OF-16`). Averaging these would destroy the signal.
- **Solution-awareness PAID OFF and did NOT corrupt them.** Neither ran a fairness audit
  (`fairplay_check.py`'s job — the feared failure mode). Both produced findings a blind reviewer
  *structurally cannot reach*: `OF-11` is a gap **between** solution and outline; `OF-3` notices the
  keystone clue is demoted in the actual solve ("The Erasure" should *name the killer*; the outline
  resolves it into an abstract insight at the wheel in ch18 pointing at Cal).

**It found a real bug in the book.** Both members independently flagged it (`OF-7` claude, `OF-13`
codex): outline says **27 chapters**, ch24's Track Movement references "the earned repair in **ch 28**",
`series/continuity/canon-core.md` says "Reveal chapter: **25 of 29**". Independent corroboration on a
*checkable fact* is the strongest signal this design produces. Until reconciled, the continuity and
fair-play inspectors will grade drafts against beats that don't exist.

### 2. The `recommendation` field — SHIPPED (7 commits, 371 green)
Spec: `docs/superpowers/specs/2026-07-10-outline-recommendation-field-design.md`
Plan: `docs/superpowers/plans/2026-07-10-outline-recommendation-field.md`
Ledger: `.superpowers/sdd/progress.md` (final section — **recovery map, trust it over memory**)

Items gain an **optional** `recommendation:` key — the reviewer's fix, split from the observation.
Reviewer-authored at generation time (only that reviewer can fix its own point). **Absent, not empty**:
omitting it is explicitly legitimate, so no reviewer invents an action to fill a slot. **Per-source,
never merged** — `OF-1` and `OF-21` reach different fixes for the same strand.

**`OF-1..OF-22` will never carry the field.** `append_items` only appends; nothing mutates an existing
item. Hand-edit them or don't. That's the append-only invariant working, not a limitation.

**The prerequisite was the more valuable half.** `commands/review-outline.md` step 6 said only "send
the SAME rubric + inputs" — **codex had no written output contract anywhere in the repo**. The
orchestrator improvised its prompt every run, so "identical inputs" bound the *files* but not the
*instructions*. Now committed, in lockstep with `agents/outline-reviewer.md`.

## Next actions

1. **`HERMES.md:192` still teaches the deleted rule.** It says *"Do not give blind reviewers the full
   solution, full outline, or other reviewers' opinions."* The outline-reviewer now reads the whole
   solution by design. This is **residue of the PRIOR (merged) solution-blindness branch**, surfaced by
   this session's final whole-branch review. Same doc-drift class the ledger warns about. Cheap; do it first.

2. **THE DOCS TEACH AN INVOCATION THAT DOES NOT WORK.** `/review-outline 01` fails with
   `Unknown command`. Plugin skills are **namespaced**: `/penny-engine:review-outline 01`.
   `CLAUDE.md` and this file document all eleven commands **bare** (`/draft-chapter NN MM`,
   `/plan-mystery NN`, `/scaffold-book`…). The next session hits this wall on whatever it reaches for
   first. Verify against `claude plugin details penny-engine` before mass-editing — confirm whether
   bare names ever resolve, or only namespaced ones.

3. **The ch27/28/29 continuity break** (`OF-7` + `OF-13`, above). Series-side, not engine. Reconcile
   `total_chapters`, the reveal chapter, and the keystone-click chapter across `input/book-01/outline.md`
   frontmatter, ch24's Track Movement, and `series/continuity/canon-core.md`.

4. **Phase 4 (thriller genre pack)** — still specced-but-unapproved, untouched for four sessions.
   5 `[DECISION]` flags in `docs/superpowers/specs/2026-07-08-thriller-genre-pack-design.md`.
   It can do an **inverted mystery (howcatchem)** with no engine change and no flag: omit the
   premature-reveal rubric clause, drop `fairplay` from its `gates:`.

5. **`commands/scaffold-book.md:72`** — "Per-chapter blind brief derivation" still sits in a
   *"Deferred (do not build here)"* list. **Delete the line, don't rename it.** Carried from last session.

## Decisions made this session

- **`recommendation` is reviewer-authored at generation time, not a later synthesis pass.** A second
  pass would be a *different read producing a different fix*, not a recommendation attached to the
  original observation. Reinforced by the append-only invariant, which makes tool-driven retro-fill
  impossible anyway.
- **Absent, not empty.** `OF-10`'s whole point is *"two areas are genuinely strong and need no
  intervention."* A required field would force it to invent an action. Making "I have no fix for you"
  costless is the only thing stopping the field from manufacturing advice.
- **Rejected: extract the fix from the prose with a heuristic.** It would have retro-filled all 22
  existing items for free. Deciding which sentence is a recommendation is an LLM judgment; a heuristic
  fires on `OF-22`'s *"The main caution is to avoid…"* and misses `OF-20`'s bare imperative *"mark the
  few that genuinely matter."* Same trap as the premature-reveal predicate that is deliberately not a script.
- **The `isinstance(rec, str)` guard is a type check, not prose judgment.** The deterministic layer may
  ask *is this a string*; it may never ask *is this prose a recommendation*. Matches `max_pass`'s
  existing `isinstance(..., int)` precedent in the same module.
- **The stale plugin snapshot is NOT the loader.** See "Watch out for".

## User preferences expressed this session
- Detailed feedback; **discuss in prose before multiple-choice**. Lead with a recommendation.
- **Terminal-native** — the filesystem / `cd` / editing a file IS the interface. Runs work in cmux panes.
- Work phase-at-a-time on `main`; push at phase end. Both repos have remotes.
- Will land his own fixes mid-session — **re-read files before editing**.

## Key files right now
- `.superpowers/sdd/progress.md` — the SDD ledger. **Recovery map after any compaction.**
- `scripts/outline_feedback.py` — `append_items` (transport + isinstance guard), `render_view`
  (`**→**` beneath the observation), `status_line` (**IDs only — never item text**).
- `agents/outline-reviewer.md:35-39` + `commands/review-outline.md:45-51` — the two panel contracts.
  **These must always agree**; two reviewers verified byte-identical wording.
- `tests/test_outline_feedback.py` — 34 tests. `_flat()` is now blockquote-aware.
- `~/myBooks/series-pelicanscrook/output/book-01/reports/outline-feedback.yaml` — the 22 live items.

## Watch out for

- **Verify pytest counts yourself.** Current truth: **371**.
- **The plugin cache snapshot is a decoy.** `~/.claude/plugins/cache/penny-engine-marketplace/penny-engine/0.1.0`
  is a frozen non-git copy pinned at `c2fd2e4` (2026-07-07), **61+ commits stale**, and its `commands/`
  genuinely lacks `review-outline.md` and `plan-book.md`. It looks exactly like the cause of any
  "Unknown command". **It is not loaded.** `known_marketplaces.json` says
  `installLocation: /Users/beeko/myTools/penny`, and `claude plugin details penny-engine` reports all 11
  skills. Deleting it would "fix" bugs by coincidence. It also still contains a fossilized `series/`,
  `input/`, `.penny/` from before the series moved out. Prune on hygiene grounds only.
- **`_flat()` in `tests/test_outline_feedback.py` strips `>` markers now.** Before that fix, the
  contract test passed only because of where line breaks fell — an innocent markdown reflow reported
  "contract drift" that didn't exist. If you re-wrap either contract, the test should still pass; if it
  goes red, check whether the *words* changed before believing it.
- **The ledger is hand-edited, so YAML footguns are live.** `recommendation: yes` parses as bool `True`.
  Guarded now (`isinstance`), but that's why the guard exists.
- **The engine repo is NOT a series.** Any pipeline command from `~/myTools/penny` hard-errors
  `penny-paths: no series root`. Correct. `cd` to the series folder.
- **A fresh clone of the series is not a recognized series** — `.penny/` is gitignored. Recover with
  `mkdir -p .penny/locks` then `preflight.py lock-mystery 01`.
- **Your `git commit` → `git push` hook did not fire this session** (global `settings.json`,
  `PostToolUse` on `Bash(git commit*)`, `git push 2>&1 || true` — the `|| true` swallows failures
  silently). Pushed by hand. Worth checking whether the matcher misses heredoc-form commits.
- **`panel_size: 1` (fast mode)** still means a put-down can never reach `beta_consensus_k: 2`. Expected.
