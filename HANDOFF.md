# Handoff — Penny (fiction-series engine) / main
Saved: 2026-07-09 | Type: build

## What we're building
Penny = ONE engine (a Claude Code plugin) driving MANY series (active series = cwd via a
`.penny/` marker), with a swappable genre-pack layer. Priority: **no engine drift** — all
genre/series-specific data lives in `genres/<g>/` packs or the series folder, never in
`scripts/`. **This session designed + shipped a brand-new capability: the pre-draft outline
developmental review tier** (spec → plan → subagent-driven build → merged to main).

## Git state
- Branch: `main`, **clean vs `origin/main` — pushed** (merge `f0799e6`). Suite **324 green**
  (was 308; +16 new tests in `tests/test_outline_feedback.py`).
- Only uncommitted change: this `HANDOFF.md` (commit it after reading).
- Feature landed via `feat/outline-review` (now deleted) merged `--no-ff` — Phase-3a pattern
  (branch → merge), not direct-on-main.

## What shipped this session — outline developmental review
An **advisory, pre-draft** craft-review tier so outline defects are caught before they cost
a draft. Files:
- `scripts/outline_feedback.py` — the ONLY new engine logic (fully unit-tested). Append-only
  ID'd feedback **ledger** (`output/book-NN/reports/outline-feedback.yaml`), `status` banner
  (open backlog + outline staleness; **bulletproof exit-0** — never blocks a draft), `render`
  side-by-side view, `append` CLI (render/append fail loudly — exit-0 is scoped to `status`).
- `agents/outline-reviewer.md` — Claude panel member: solution-blind, **prose feedback (no
  scores)**, dedup across passes, emits a JSON array of `{"text": ...}`.
- `commands/review-outline.md` — `/review-outline NN [--focus "…"]`: dispatches an
  **independent Claude+Codex panel** (identical solution-blind inputs), tags each point with
  `source`, appends to the ledger. Side-by-side, **NOT converged** (deliberately inverts the
  beta layer's K-of-M).
- `genres/cozy-mystery/review-rubrics/outline-craft.md` — the 6-area coverage rubric (pack data).
- `commands/draft-chapter.md` — new non-blocking step `0b` runs the banner.
- Design intent: `docs/superpowers/specs/2026-07-09-outline-developmental-review-design.md`;
  plan: `docs/superpowers/plans/2026-07-09-outline-developmental-review.md`.

## Next actions
1. **LIVE SHAKEDOWN of the new tier (UAT).** The deterministic core is tested, but the
   agent/command/**Codex panel** layer is unit-test-exempt by design — run `/review-outline`
   on a real book-01 outline in `~/myBooks/cozy-pelicans/` and judge (a) reviewer quality and
   (b) that the **Codex plugin runtime is actually reachable** for the second panel member
   (degrades to Claude-only + "independence reduced" note if not — never halts).
2. **Phase 4 (thriller genre pack) is STILL specced-but-unapproved** — untouched this session.
   Spec: `docs/superpowers/specs/2026-07-08-thriller-genre-pack-design.md`; resolve its 5
   `[DECISION]` flags, then writing-plans → subagent-driven-development. (We built the
   outline-review tier *ahead* of Phase 4 at the user's direction; §14 of its spec had
   recommended after-Phase-4, but the user chose to implement it now.)
3. A thriller pack, when built, should ship its own `review-rubrics/outline-craft.md` so
   `/review-outline` works there too (the rubric is genre data; the engine is agnostic).

## Decisions made this session
- **Independent panel, side-by-side, no synthesis** — reviewer disagreement is the signal;
  averaging (K-of-M) would destroy it. Independence = **tool difference** (Claude + Codex),
  per the front-door spec's no-API model note.
- **Prose feedback, no numeric scores** — a scorecard read as mechanistic to the showrunner;
  the rubric is a *coverage checklist*, not a grade sheet.
- **ID'd feedback ledger with owner-set state** (`open`/`solved`/`rejected`), **append-only**:
  the command only appends new `OF-<n>` items; the showrunner owns `state` by editing the yaml
  (terminal-native, no command ceremony). Re-runs never overwrite dispositions.
- **Banner keyed on staleness + open-count**, never blocks (advisory). Exit-0 scoped to
  `status` only; `render`/`append` fail loudly (final-review fix).
- Reconciled a spec §6 doc-drift: shipped render groups **by state**, not by pass/source.

## User preferences expressed this session
- Detailed feedback; **discuss in prose before multiple-choice** (rejected an MC prompt, asked
  to talk it through — respect this). Lead with a recommendation.
- **Terminal-native** — the filesystem/`cd`/editing a file IS the interface; don't build
  selectors/flags/pointers on top of what the shell already does (see memory).
- Develops outlines across multiple LLMs (Hermes → ChatGPT/Claude), iteratively, steered by
  gut-feel; wanted that consolidated into Penny (drove this feature — see memory).
- Works ON-site this session (not offsite); phase-at-a-time on `main`; push to GitHub.

## Key files right now
- `scripts/outline_feedback.py` — the tested deterministic core; where all correctness lives.
- `commands/review-outline.md` — the orchestrator to exercise in the live shakedown.
- `.superpowers/sdd/progress.md` — the SDD ledger for this build (8 tasks + 2 fix waves + final
  review, all recorded) AND the prior Phase-3a/3b records. Recovery map.
- Memory (`~/.claude/projects/-Users-beeko-myTools-penny/memory/`): NEW this session —
  `anchor-design-to-working-style.md` (the abandoned series-selector lesson) and
  `outline-review-workflow.md` (how the user reviews outlines). Index in `MEMORY.md`.

## Watch out for
- **Verify pytest counts yourself** — implementers misreported before. Current truth: **324**.
- **Codex reachability is unproven live** — the second panel member routes through the codex
  plugin runtime; if it's down, `/review-outline` runs Claude-only and says "independence
  reduced" (by design). Don't mistake that for a bug until you've confirmed Codex is installed.
- The **feedback ledger is hand-editable YAML** — a malformed edit is tolerated by `status`
  (falls back to a nudge, still exit-0) but will make a `/review-outline append` pass fail
  loudly (intended).
- Engine repo is **not a series** — running a series pipeline command (incl. `/review-outline`)
  from the engine root hard-errors (`no series root`). Use a series folder (`~/myBooks/…`) as cwd.
- Deferred minors (in `.superpowers/sdd/progress.md`, triaged non-blocking): `VALID_STATES`
  dead const; `status_line` path-prefix partial DRY; render-fail exit test.
