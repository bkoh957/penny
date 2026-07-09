# HERMES.md

Guidance for Hermes/Booko agents working in this repository.

## Identity and purpose

This repo is `penny`: the canonical Penny engine, packaged as a Claude Code plugin
(`.claude-plugin/plugin.json` + marketplace manifest). Commands live in top-level
`commands/`, agents in top-level `agents/`, deterministic checkers in `scripts/`, and
genre packs in `genres/`.

Penny/Booko is a harness for producing commercial fiction series with deterministic gates
and independent quality review. Treat the harness as production infrastructure, not a
scratchpad.

## Non-negotiable architecture rule

The engine is genre- and location-agnostic.

- Fixed engine/orchestration: `scripts/`, `commands/`, `agents/`
- Swappable project data (belongs to a **series folder**, not this repo): `config/`
  overrides, `input/`, `series/`
- Output/runtime artifacts (also series-folder-local): `output/`, `.penny/`

A series is an ordinary folder you `cd` into and run Claude Code from; the active
series is resolved from the **current working directory** by `scripts/penny_paths.py`
(walks up from cwd to the nearest `.penny/` marker — hard error if none). There is no
`--series` flag, `PENNY_SERIES` env var, or `current-series` pointer. Config reads
overlay: series `config/<rel>` → declared genre pack `genres/<genre>/<rel>` → engine
`config/<rel>`.

Do not hardcode Book 01, Pelican's Crook, Maggie, cozy mystery details, clues, or voice-pack details into `scripts/` or command/agent logic. Put project-specific material in the active series folder's `config/`, `input/`, or `series/`.

Use "the protagonist" in engine-layer files; do not hardcode the current protagonist name there.

## Start-of-session checklist

From engine repo root:

```bash
cd /Users/beeko/myTools/penny
git status --short
git branch --show-current
git log -1 --oneline
```

Then read:

```text
README.md      # architecture/current workflow
HANDOFF.md     # current project state and next actions
CLAUDE.md      # upstream Claude-native harness conventions
```

If drafting/reviewing, also read the relevant command and agent files under `commands/`
and `agents/` before acting. Remember: actual book pipeline commands run from a series
folder with a `.penny/` marker, not from this engine repo.

## Essential commands

Install/check dependencies:

```bash
pip install -r requirements.txt
python3 -m pytest -q
```

Targeted checks commonly used here:

```bash
python3 scripts/outline_check.py input/book-01/outline.md
python3 -m pytest tests/test_outline_check.py -q
python3 scripts/preflight.py draft 01 03
python3 scripts/preflight.py finalize 01 01
python3 -m scripts.review_gate output/book-01/chapters/ch-01.reviews
```

Check chapter length:

```bash
wc -w output/book-01/chapters/ch-MM.draft.md
```

## Chapter workflow

The Claude-native slash commands are documented in `commands/`. When operating via Hermes/Booko, follow the same runbooks manually unless the interactive agent supports the slash command directly.

Per book:

```text
/plan-mystery NN
```

Per chapter:

```text
/draft-chapter NN MM
/review-chapter NN MM
/finalize-chapter NN MM
```

Book-level:

```text
/beta-read output/book-NN/book-NN.manuscript.md
/assemble-book NN
/assemble-book NN --approve
```

Chapter artifacts live under:

```text
output/book-NN/chapters/
```

Common files:

```text
ch-MM.draft.md
ch-MM.reviews/*.md
ch-MM.gate.md
ch-MM.lineedit.md
ch-MM.copyedit.md
ch-MM.final.md
```

## Drafting discipline

Before asking Booko/Penny to redraft a chapter, provide:

1. Exact active series root, not the engine root.
2. Exact target file to overwrite.
3. Current word count.
4. Required range from `config/length-profile.md`.
5. The chapter brief from `input/book-01/outline.md`.
6. Specific underwritten sections, not generic "make it longer" feedback.
7. Verification command: `wc -w <target-file>`.

For underwritten chapters, diagnose scene-work gaps:

- missing setup before the event
- summary where action/dialogue should be dramatized
- thin interiority / emotional turn not earned
- suspect beats reduced to one-line mentions
- setting texture missing
- clue planted too vaguely or too loudly
- ending hook abstract instead of character-driven

Do not accept a pane-agent's success summary at face value. Read the file and verify word count yourself.

## Word-count rules

`config/length-profile.md` is authoritative.

Typical ranges:

- Opening chapter: 1,800-2,400
- Standard investigation / character chapter: 2,000-2,500
- Quick discovery / confrontation: 1,500-2,000
- Major reveal / emotional shift: 2,500-3,200
- Final confrontation: 3,000-4,000

A chapter must not be submitted below its range minimum. If short, extend real scene work rather than padding recap.

## Deterministic gates

Gates are deterministic, not LLM judgments.

- `scripts/preflight.py` owns preflight checks and lock/certificate checks.
- `scripts/review_gate.py` writes `ch-MM.gate.md` and returns `GATE: PASS|HOLD`.
- Verdict files use the `penny-verdict/1` envelope.
- A line beginning exactly `BLOCKING:` at column 0 is the blocker convention.
- `PASS` means zero blockers. `HOLD` means at least one blocker.

Do not patch a verdict to remove a blocker. Re-run the relevant inspector or gate so the artifact reflects actual review.

Locks and certificates are out-of-band under `.penny/locks/`. Never represent validated/approved state as a field inside the data being validated.

## Context and continuity discipline

- Always load `series/continuity/canon-core.md` for chapter work.
- Load character/location/thread entries only as a brief-scoped ledger slice: named entries plus one-hop links.
- Keep `canon-core.md` tiny; every line taxes every chapter.
- `.penny/` is gitignored runtime state. Do not `git clean -fdx` unless explicitly approved and backed up.

## Blind-review discipline

Inspectors and beta readers are blind by design.

- Inspectors get chapter text + one rubric + relevant ledger slice.
- Beta readers get text + persona only.
- Do not give blind reviewers the full solution, full outline, or other reviewers' opinions.
- Personas are distinct lenses; do not average them into mush.

## Cross-model independence

The final reader must not use a model that drafted the chapters. This is enforced via frontmatter stamps (`drafted_by`, `read_by`) and `preflight.py assemble`.

The invariant is difference, not identity: `final_read_model` must not appear among chapter `drafted_by` values.

## Git/repo handling

Canonical engine repo:

- `/Users/beeko/myTools/penny` → `https://github.com/bkoh957/penny.git`

Series folders are separate working directories. Do not copy series data into the engine
unless explicitly moving fixture/test data. Never copy secrets into git. Do not display
`.env` values.

## Current project notes from HANDOFF.md

Always re-check `HANDOFF.md`; it is the current engine handoff. As of the latest handoff:

- Penny is one engine plugin driving many series by cwd / `.penny/` marker.
- The new advisory pre-draft outline review tier has shipped (`/review-outline`,
  `scripts/outline_feedback.py`, `agents/outline-reviewer.md`, cozy outline-craft rubric).
- The deterministic suite is currently 325 tests green after the readiness/doc drift fixes.
- Next live UAT is `/review-outline` from a real series folder, especially Codex panel
  reachability and the "independence reduced" fallback.
- Thriller genre pack work remains specced but unapproved.
