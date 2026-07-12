# Hermes Handoff — Penny / Ch3 repair + portfolio tracker mockups
Saved: 2026-07-12 17:34 AEST | Type: mixed

## What we're doing
This Hermes session continued Penny/Pelican work after LM Studio drafting support. The main story-production work was Chapter 3 AI-smell hardening: expanding the AI-smell rubric/checks, applying the expanded critique to `ch-03.draft.md`, and verifying word count plus deterministic `voice_drift.py`. The later product-design work explored a future visual tracker for managing multiple fiction series, books, reader magnets, novellas, and status/metrics.

## Current state
### Engine repo
- Working directory: `/Users/beeko/myTools/penny`
- Branch: `main`
- Last commit observed: `52af859 feat(plot-book): the resumable workshop runbook`
- Uncommitted changes at handoff save:
  - `M HANDOFF.md` — pre-existing project-owned handoff change; leave alone unless explicitly asked.
  - `M config/review-rubrics/ai-prose-taste-flags.md` — expanded Tier-C AI-prose taste flags.
  - `M config/self-audit/self-audit-checklist.md` — added mechanical self-audit fixes for contrast/dialogue/exit-return-exit.
  - `?? HERMES-HANDOFF.md` — this Hermes handoff file, still uncommitted unless committed later.
  - `?? sketches/` — portfolio tracker HTML mockups and READMEs.
- Important: per updated handoff skill, do **not** update `HANDOFF.md` by default. Use `HERMES-HANDOFF.md` for Hermes continuity.

### Series repo
- Working directory: `/Users/beeko/myBooks/series-pelicanscrook`
- Branch: `main`
- Last commit observed: `8cfd35e chore: checkpoint book 01 drafting state`
- Uncommitted changes at handoff save:
  - `M HANDOFF.md` — pre-existing project-owned series handoff change; leave alone unless explicitly asked.
  - `M output/book-01/chapters/ch-03.draft.md` — repaired Chapter 3 prose after expanded AI-smell feedback.
  - `M output/book-01/chapters/ch-03.local-checks/voice-drift.md` — rerun after prose repair.
  - `?? output/book-01/chapters/ch-03.ai-smell-expanded.md` — expanded critique artifact from user feedback.
  - `?? output/book-01/chapters/ch-03.ai-smell-repair.md` — repair log/verdict after applying changes.

## Tests/checks run
### Chapter 3 repair verification
From `/Users/beeko/myBooks/series-pelicanscrook`:
```bash
wc -w output/book-01/chapters/ch-03.draft.md
# 2085 output/book-01/chapters/ch-03.draft.md

python3 /Users/beeko/myTools/penny/scripts/voice_drift.py \
  output/book-01/chapters/ch-03.draft.md \
  --target book-01/ch-03 \
  --out output/book-01/chapters/ch-03.local-checks
```
Result: word count is within the standard 2,000–2,500 chapter range. `voice_drift.py` reports all categories OK except `lexical_repetition`, which is mostly names/core objects and recorded as line-edit caution rather than AI-smell blocker.

### Portfolio tracker mockup verification
Visual/browser verification only, intentionally no `pytest`/linters yet because user instruction for creative UI work says to hold off until the user likes the result or we are about to commit.
- Opened and visually checked `sketches/book-portfolio-command-center/index.html`; fixed matrix clipping.
- Opened and visually checked `sketches/book-portfolio-ledger/index.html`; rendered cleanly.
- Opened and visually checked `sketches/book-portfolio-minimal-command/index.html`; shortened crowded reader-magnet title and rechecked; rendered cleanly.

No full repo `pytest` was run after the UI mockups because these are standalone sketches and not approved for commit yet.

## Decisions made
- **Hermes handoffs use `HERMES-HANDOFF.md`.** The `handoff` skill was patched so normal `handoff` saves/pickups use `HERMES-HANDOFF*.md` and leave project-owned `HANDOFF*.md` untouched unless explicitly requested.
- **Expanded AI-smell should cover higher-level generated-prose patterns.** Added coverage for action-immediate-interpretation, repeated contrast machinery, every-paragraph-quotable polish, author-mouthpiece dialogue, repeated emotional conclusion, manufactured background planting, and multiple endings/block assembly.
- **Chapter 3 should be repaired before cloud review.** The older narrow AI-smell pass said clear, but the expanded user feedback made it `REPAIR_FIRST`; the draft was surgically revised.
- **Book portfolio tracker direction:** user wants the command-center information architecture, but styled like the warmer ledger mockup, compressed/minimalist, with innovative compact book/chapter status presentation. The latest/winning sketch is `book-portfolio-minimal-command`.

## Key files and artifacts
### Engine / skills / rubrics
- `/Users/beeko/.hermes/skills/productivity/handoff/SKILL.md` — patched earlier so Hermes saves `HERMES-HANDOFF*.md`, not `HANDOFF*.md`.
- `/Users/beeko/.hermes/skills/creative/lmstudio-penny-local-review/templates/ai-smell-check.md` — expanded AI-smell prompt template.
- `/Users/beeko/.hermes/skills/creative/lmstudio-penny-local-review/SKILL.md` — prompt discipline updated to include the expanded smell checks.
- `/Users/beeko/myTools/penny/config/review-rubrics/ai-prose-taste-flags.md` — expanded Tier-C taste flags.
- `/Users/beeko/myTools/penny/config/self-audit/self-audit-checklist.md` — added mechanical fix-pass items.

### Series / Chapter 3
- `/Users/beeko/myBooks/series-pelicanscrook/output/book-01/chapters/ch-03.draft.md` — repaired draft, 2,085 words.
- `/Users/beeko/myBooks/series-pelicanscrook/output/book-01/chapters/ch-03.local-checks/voice-drift.md` — post-repair deterministic check.
- `/Users/beeko/myBooks/series-pelicanscrook/output/book-01/chapters/ch-03.ai-smell-expanded.md` — expanded critique artifact.
- `/Users/beeko/myBooks/series-pelicanscrook/output/book-01/chapters/ch-03.ai-smell-repair.md` — repair log; verdict `READY_FOR_CLOUD_REVIEW_WITH_LINE_EDIT_CAUTION`.

### Portfolio tracker mockups
- `/Users/beeko/myTools/penny/sketches/book-portfolio-command-center/index.html` — first dark command-center variant.
- `/Users/beeko/myTools/penny/sketches/book-portfolio-command-center/README.md`
- `/Users/beeko/myTools/penny/sketches/book-portfolio-ledger/index.html` — warm editorial release-ladder variant.
- `/Users/beeko/myTools/penny/sketches/book-portfolio-ledger/README.md`
- `/Users/beeko/myTools/penny/sketches/book-portfolio-minimal-command/index.html` — latest hybrid/minimal preferred direction.
- `/Users/beeko/myTools/penny/sketches/book-portfolio-minimal-command/README.md`

Open latest mockup:
```bash
open /Users/beeko/myTools/penny/sketches/book-portfolio-minimal-command/index.html
```

## Next actions
1. If continuing Chapter 3 production, run/send the repaired Ch 3 through normal cloud/Penny review:
   ```bash
   cd /Users/beeko/myBooks/series-pelicanscrook
   # use the normal /review-chapter 01 03 path if operating through Claude/Penny,
   # or manually run the equivalent review workflow from the series root.
   ```
2. If continuing tracker design, use the latest hybrid mockup:
   ```bash
   open /Users/beeko/myTools/penny/sketches/book-portfolio-minimal-command/index.html
   ```
   User asked for command-center functionality with ledger style, compressed/minimal, and innovative book/chapter status displays. Iterate there, not the earlier two variants, unless comparing ideas.
3. Before committing mockups, clean/KISS the HTML and then run the relevant repo checks. The user explicitly instructed not to run tests/linters for creative UI sketches until they like the result or we are about to commit.
4. If committing, stage only intentional files. There are unrelated/pre-existing `HANDOFF.md` modifications in both engine and series; do not stage them unless the user explicitly asks.

## User preferences / corrections this session
- For creative UI/visual work: hold off on tests/linters until the user likes the result or we are about to commit.
- Before every commit: clean the work, keep it KISS/DRY, match style, and be concise/elegant.
- User wants the portfolio tracker to avoid spreadsheet/kanban bloat: command-center usefulness, ledger warmth, compressed minimalist presentation, innovative book/chapter status.
- User asked that Hermes `handoff` skill generate `HERMES-HANDOFF.md` and leave project `HANDOFF.md` alone.

## Watch out for
- The engine repo and series repo both have `M HANDOFF.md` from earlier. They are project-owned and should be left alone by default.
- The latest engine HEAD is `52af859`, newer than several earlier commits mentioned in old handoffs; always re-check git before assuming context.
- The portfolio mockups are standalone HTML sketches under `sketches/`; they are not wired into a production app.
- Do not claim full `pytest` verification for the mockups; only visual browser verification has been done after the UI changes.
- Chapter 3 is repaired locally but still should go through cloud/normal Penny review before treating it as fully cleared.

## Open questions
- Does the user like the `book-portfolio-minimal-command` direction enough to promote/refine it?
- Should Ch 3 go to cloud review now?
- Should the expanded AI-smell rubric/self-audit changes be committed with the Ch 3 artifacts, or separately?
