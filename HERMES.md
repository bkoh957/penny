# HERMES.md

Guidance for Hermes/Booko agents working in this repository.

## Identity and purpose

This repo is `penny-hermes`: a Hermes-friendly mirror of the original Penny harness. It is a separate git repository with its own remote (`bkoh957/penny-hermes`), synced from the source repo at `/Users/beeko/myTools/penny` when requested.

Penny/Booko is a harness for producing a 13-book commercial cozy mystery series with deterministic gates and independent quality review. Treat the harness as production infrastructure, not a scratchpad.

## Non-negotiable architecture rule

The engine is genre- and location-agnostic.

- Fixed engine/orchestration: `scripts/`, `.claude/commands/`, `.claude/agents/`
- Swappable project data: `config/`, `input/`, `series/`
- Output/runtime artifacts: `output/`, `.penny/`

Do not hardcode Book 01, Pelican's Crook, Maggie, cozy mystery details, clues, or voice-pack details into `scripts/` or command/agent logic. Put project-specific material in `config/`, `input/`, or `series/`.

Use "the protagonist" in engine-layer files; do not hardcode the current protagonist name there.

## Start-of-session checklist

From repo root:

```bash
cd /Users/beeko/myTools/penny-hermes
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

If drafting/reviewing, also read the relevant command and agent files under `.claude/` before acting.

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

The Claude-native slash commands are documented in `.claude/commands/`. When operating via Hermes/Booko, follow the same runbooks manually unless the interactive agent supports the slash command directly.

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

1. Exact repo root: `/Users/beeko/myTools/penny-hermes`
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

This repo is separate from `/Users/beeko/myTools/penny`.

- Source repo: `/Users/beeko/myTools/penny` → `https://github.com/bkoh957/penny.git`
- Hermes mirror: `/Users/beeko/myTools/penny-hermes` → `git@github.com:bkoh957/penny-hermes.git`

When syncing from source, preserve `penny-hermes` as its own repo:

```bash
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='*.pem' \
  --exclude='*.key' \
  --exclude='.DS_Store' \
  /Users/beeko/myTools/penny/ \
  /Users/beeko/myTools/penny-hermes/
```

Then verify:

```bash
diff -qr --exclude .git --exclude .env --exclude '.env.*' --exclude '.DS_Store' \
  /Users/beeko/myTools/penny /Users/beeko/myTools/penny-hermes | head -80
python3 scripts/outline_check.py input/book-01/outline.md
python3 -m pytest tests/test_outline_check.py -q
```

Never copy secrets into git. Do not display `.env` values.

## Current project notes from HANDOFF.md

At the time this file was recreated after a source resync:

- Ch-01 has a gate artifact that may still say HOLD from before a fix; re-run the relevant inspector/gate rather than editing the verdict by hand.
- Ch-02 gate says PASS and is ready for finalize.
- The outline is the single source of truth for both solution/thread scaffolding and rich chapter briefs.
- `input/` is the home for showrunner-authored files.
- Cobber's dawn-sighting clue must remain dismissible local colour until later.
- The culprit should not be named or implicated in early chapter drafts/finalize passes.
- Calloway's bench skeleton is a series seed and should not be resolved in Book 01.

Always re-check `HANDOFF.md` because it may be newer than these notes.
