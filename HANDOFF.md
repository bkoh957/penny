# Handoff — Penny (fiction-series engine) / main
Saved: 2026-07-10 | Type: build (+ a short debug detour)

## What we're building
Penny = ONE engine (a Claude Code plugin) driving MANY series (active series = cwd via a
`.penny/` marker), with a swappable genre-pack layer. Priority: **no engine drift**.
This session ran the long-deferred **`/review-outline` live shakedown** (it passed), shipped the
**`recommendation` field** the shakedown showed a need for, and then stopped at an open decision
about whether to re-run the panel.

## Git state
- **Engine** (`~/myTools/penny`, github `bkoh957/penny`): `main` **clean and pushed** through `a94b8da`.
  Suite **371 green** (353 at session start). Nothing in flight.
  - `5b9bef9` spec · `8d1bd58` plan · `3ed18e2..efe92b6` 5 TDD tasks + 2 fix waves · `a94b8da` handoff
- **Series** (`~/myBooks/series-pelicanscrook`, **PRIVATE**): `main` level with origin, but
  **14 files are uncommitted — see the WARNING below. They are the showrunner's own edits, not the
  engine's.** `.penny/current-stage` = `book=01 stage=OUTLINE-REVIEWED`.

## 🔴 WARNING — READ BEFORE TOUCHING THE SERIES

**The solution prose has diverged from its own lock.** These are *not* engine bugs; they are the
state the working tree was left in.

1. `output/book-01/mystery-solution.md` was edited to move `clue-car-on-street` to
   **plant ch 9 / pay off ch 20**.
   `series/whodunit/book-01.yaml:16` — **unmodified** — still reads
   `{ id: clue-car-on-street, plant_chapter: 11, pays_off_chapter: 23 }`.
   The lock (`.penny/locks/book-01.mystery.lock`, minted **8 Jul**) certifies **the yaml**, not the prose.
   A lock is an out-of-band certificate: it exists only because validation passed *on the yaml*.
   **Fix per CLAUDE.md: delete the lock, edit the yaml to match, re-run `preflight.py lock-mystery 01`.**
   Until then `inspector-fairplay` schedules that clue against a chapter the solution no longer uses.

2. `series/continuity/canon-core.md` still says *"Culprit identity SEALED — **do not write it into any
   drafter-visible artifact**"*. Post-solution-blindness-removal the drafter **reads**
   `mystery-solution.md`. "Sealed" now means *frozen against edits*, never *hidden from agents*.
   That clause is stale — same doc-drift class as `HERMES.md:192` below, but in **series data**.

**Provenance:** at session start the series showed only ` M input/book-01/outline.md`. The other 13
files appeared at 17:04–17:06 while I worked in the engine repo. `canon-core.md` now reads
*"Structure: 27 chapters; reveal/arrest ch 25, public aftermath ch 26, private coda ch 27"* — i.e. the
`OF-7`/`OF-13` chapter-count fix. **I did not make these edits and did not review them.** Assumed to
be the showrunner acting on the panel's feedback mid-session (consistent with prior handoffs).
`output/book-01/reports/` is still untracked.

## What happened this session

### 1. THE SHAKEDOWN PASSED — all four questions
Command is **`/penny-engine:review-outline 01`** (see trap #2 below).
- **Plumbing:** ledger `OF-1..OF-22`, contiguous, all `state: open`, `pass: 1`,
  `reviewed_outline_sha256` matched the outline actually read. `status` exits **0**, prints IDs only.
  Staging file at `.penny/outline-points-01.json`, exactly as the runbook says.
- **Independence:** **Codex answered.** 10 claude / 12 codex, concurrent. No "independence reduced".
- **Quality:** they **genuinely disagree**. Claude = cozy-craft lens (`OF-1` romance starved after ch11;
  `OF-4` gift-as-vice averted). Codex = mystery-logic lens (`OF-11` what did Mary actually *find*;
  `OF-12` how does Pruitt lawfully obtain the letter). Averaging would destroy the signal.
- **Solution-awareness paid off and did NOT corrupt them.** Neither ran a fairness audit (the feared
  failure mode — that's `fairplay_check.py`'s job). `OF-11` is a gap **between** solution and outline;
  `OF-3` sees the keystone clue demoted in the actual solve. A blind reviewer cannot reach either.
- **It found a real bug in the book:** `OF-7` (claude) + `OF-13` (codex) **independently** flagged
  27 chapters vs ch24's "ch 28" vs canon-core's "25 of 29". Independent agreement on a *checkable fact*
  is the strongest signal this design produces. (Now partly addressed by the uncommitted edits above.)

### 2. The `recommendation` field — SHIPPED (7 commits, 353 → 371 green)
Spec: `docs/superpowers/specs/2026-07-10-outline-recommendation-field-design.md`
Plan: `docs/superpowers/plans/2026-07-10-outline-recommendation-field.md`
Ledger: `.superpowers/sdd/progress.md` (final section — **recovery map, trust it over memory**)

Items gain an **optional** `recommendation:` key — the reviewer's fix, split from the observation.
Reviewer-authored at generation time. **Absent, not empty**: omitting it is explicitly legitimate.
**Per-source, never merged.** `scripts/` changed in one file only (`outline_feedback.py`, +10/−3).

**`OF-1..OF-22` will never carry the field** — `append_items` only appends. Hand-edit or don't.

**The prerequisite was the more valuable half:** codex had **no written output contract anywhere in the
repo**; the orchestrator improvised its prompt each run, so "identical inputs" bound the *files* but not
the *instructions*. Now committed, in lockstep with `agents/outline-reviewer.md`.

## Next actions

1. **Resolve the lock divergence (WARNING #1).** Highest consequence, smallest effort. Decide whether
   the yaml or the prose is right, make them agree, re-lock.

2. **The open question I stopped on: how to re-run the panel.** The outline sha still matches the
   ledger, so a plain re-run risks appending ~20 near-duplicates to an **append-only** ledger with 22
   untriaged items. The options I was about to put to you:
   - *(my recommendation)* fix the chapter-count/lock issues first — that changes the outline's sha, so
     `status` correctly reports **stale** and pass 2 is the **designed** trigger. `OF-23`+ then arrive
     carrying `recommendation:` and the field gets its real live test.
   - or `--focus "…"` to give both members a genuinely new lens on an unchanged outline;
   - or re-run plain and treat the result as a finding about whether reviewers honour
     *"Emit `[]` if you genuinely have nothing new to add"*;
   - or verify `append`/`render` against a scratch ledger and leave book-01's alone.

3. **`HERMES.md:192`** still says *"Do not give blind reviewers the full solution, full outline, or
   other reviewers' opinions."* Residue of the **prior, merged** solution-blindness branch, surfaced by
   this session's final whole-branch review. Engine-side. Cheap.

4. **THE DOCS TEACH AN INVOCATION THAT DOES NOT WORK.** `/review-outline 01` → `Unknown command`.
   Plugin skills are **namespaced**: `/penny-engine:review-outline 01`. `CLAUDE.md` documents all
   eleven commands **bare**. Verify against `claude plugin details penny-engine` before mass-editing.

5. **Phase 4 (thriller genre pack)** — specced-but-unapproved, untouched for four sessions. 5
   `[DECISION]` flags in `docs/superpowers/specs/2026-07-08-thriller-genre-pack-design.md`. It can do an
   **inverted mystery (howcatchem)** with no engine change: omit the premature-reveal rubric clause,
   drop `fairplay` from its `gates:`.

6. **`commands/scaffold-book.md:72`** — "Per-chapter blind brief derivation" in the *"Deferred"* list.
   **Delete the line, don't rename it.** Carried from last session.

## Decisions made this session
- **`recommendation` is reviewer-authored at generation time, not a later synthesis pass.** A second
  pass would be a *different read producing a different fix*. The append-only invariant makes
  tool-driven retro-fill impossible anyway.
- **Absent, not empty.** `OF-10` says *"two areas are genuinely strong and need no intervention"*; a
  required field would force it to invent an action. Costless omission is what stops the field from
  manufacturing advice.
- **Rejected: a heuristic that extracts the fix from the prose.** It would have retro-filled all 22
  items free — but deciding which sentence is a recommendation is an LLM judgment. It fires on `OF-22`'s
  *"The main caution is to avoid…"* and misses `OF-20`'s *"mark the few that genuinely matter."* Same
  trap as the premature-reveal predicate that is deliberately not a script.
- **`isinstance(rec, str)` is a type check, not prose judgment.** The deterministic layer may ask *is
  this a string*; never *is this prose a recommendation*. Matches `max_pass`'s existing precedent.

## User preferences expressed this session
- Detailed feedback; **discuss in prose before multiple-choice**. Lead with a recommendation.
- **Terminal-native**; runs live work in **cmux panes** and wants them monitored.
- Work phase-at-a-time on `main`; push at phase end.
- **Lands his own fixes mid-session, in another window — re-read files before editing.** Bit us today:
  13 series files changed underneath us.

## Key files right now
- `.superpowers/sdd/progress.md` — the SDD ledger. **Recovery map after any compaction.**
- `scripts/outline_feedback.py` — `append_items` (transport + isinstance guard), `render_view`
  (`**→**` beneath the observation), `status_line` (**IDs only — never item text**).
- `agents/outline-reviewer.md:35-39` + `commands/review-outline.md:45-51` — the two panel contracts.
  **These must always agree**; verified byte-identical.
- `~/myBooks/series-pelicanscrook/series/whodunit/book-01.yaml:16` — the diverged clue row.
- `~/myBooks/series-pelicanscrook/output/book-01/reports/outline-feedback.yaml` — 22 live items, untracked.

## Watch out for
- **Verify pytest counts yourself.** Current truth: **371**.
- **`/exit` typed into a running Claude session is treated as a PROMPT, not a command.** It answers you
  conversationally and stays alive; the next line you send (`claude "…"`) then lands as prompt text too.
  A cmux pane may look relaunched when it is the same session with a growing context. Check the
  `Session:` id and `Ctx:` in the statusline.
- **The plugin cache snapshot is a decoy.** `~/.claude/plugins/cache/penny-engine-marketplace/penny-engine/0.1.0`
  is a frozen non-git copy pinned at `c2fd2e4`, 61+ commits stale, and its `commands/` really does lack
  `review-outline.md` and `plan-book.md`. **It is not loaded** — `known_marketplaces.json` says
  `installLocation: /Users/beeko/myTools/penny`, and `claude plugin details penny-engine` lists all 11
  skills. Deleting it "fixes" bugs by coincidence. Prune on hygiene grounds only.
- **`_flat()` in `tests/test_outline_feedback.py` strips `>` markers now.** Before that fix the contract
  test passed only because of where line breaks fell. If you re-wrap a contract and it goes red, check
  whether the *words* changed before believing it.
- **The ledger is hand-edited, so YAML footguns are live.** `recommendation: yes` parses as bool `True`.
  Guarded (`isinstance`) — that's why the guard exists.
- **The engine repo is NOT a series.** Pipeline commands from `~/myTools/penny` hard-error
  `penny-paths: no series root`. Correct. `cd` to the series folder.
- **A fresh clone of the series is not a recognized series** — `.penny/` is gitignored. Recover with
  `mkdir -p .penny/locks` then `preflight.py lock-mystery 01`.
- **Your `git commit` → `git push` hook did not fire this session** (global `settings.json`,
  `PostToolUse` on `Bash(git commit*)`, `git push 2>&1 || true` — the `|| true` swallows failures).
  Pushed by hand. The matcher may miss heredoc-form commits.
