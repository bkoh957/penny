# Handoff — Penny / LM Studio drafting + digest prompt surfaces
Saved: 2026-07-12 12:38 AEST | Type: build

## What we're doing
Penny now has a local LM Studio chapter-drafting route for smaller local models that struggle with whole-chapter prompts. This session reduced LM Studio prompt payloads by adding deterministic scene-level compaction, chapter-scoped whodunit excerpts, and curated `lmstudio-digest.md` prompt surfaces for the Pelican series. All current engine and series work was committed and pushed.

## Current state
- Engine working directory: `/Users/beeko/myTools/penny`
- Engine branch: `main`
- Engine last commit at save time: `8c52791 plan(plot-book): 12-task TDD implementation plan for the plotting workshop`
- Engine uncommitted changes after writing this handoff:
  - `M HANDOFF.md` — this handoff update.
  - `?? scripts/penny_wiring.py`, `?? tests/fixtures/outlines/wired-clean.md`, and `?? tests/test_penny_wiring.py` — appeared after the earlier clean/pushed check; inspect provenance before committing.
- Engine remote: `origin https://github.com/bkoh957/penny.git`
- Series working directory: `/Users/beeko/myBooks/series-pelicanscrook`
- Series branch: `main`
- Series last commit at save time: `8cfd35e chore: checkpoint book 01 drafting state`
- Series uncommitted changes after writing this handoff:
  - `M HANDOFF.md` — this handoff update.
- Series remote: `origin https://github.com/bkoh957/series-pelicanscrook.git`
- Tests/checks:
  - `python3 -m pytest tests/test_lmstudio_draft_chapter.py -q` passed before commit.
  - `python3 -m pytest -q` passed before commit.
  - After creating Pelican digest files, `collect_context('01', '01', /Users/beeko/myBooks/series-pelicanscrook)` loaded all three digests successfully.

## Next actions
1. If continuing LM Studio drafting, run from the active series root:
   ```bash
   cd /Users/beeko/myBooks/series-pelicanscrook
   python3 /Users/beeko/myTools/penny/scripts/lmstudio_draft_chapter.py 01 <chapter> --model <model-id>
   ```
   Watch the printed prompt character counts; they should now be much smaller because the script uses digest files and compressed chapter context.
2. For Chapter 3 specifically, proceed to the normal Penny cloud/independent review path rather than re-running local drafting unless the draft is intentionally being replaced.
3. If prompt size is still too high, inspect the printed per-call prompt char counts first, then consider more aggressive chapter-context pruning or scene-windowed stitch/repair rather than raising timeouts.
4. If working on the newer plotting workshop plan from engine commit `8c52791`, first read the committed plan/docs and avoid mixing that stream with the LM Studio drafting stream.

## Decisions made
- **Use curated digest surfaces, not just caps.** LM Studio now prefers `lmstudio-digest.md` files for voice, genre, and setting context when present, falling back to full packs only when absent.
- **Keep digest files series-authored.** The engine supports the mechanism generically; Pelican-specific prose lives under `/Users/beeko/myBooks/series-pelicanscrook/config/...`, not in engine code.
- **Do deterministic compaction, not LLM summarization.** Chapter-level context keeps headings/scene map/post-scene guardrails and sends only the current scene body. Whodunit context keeps chapter-relevant rows and withholds culprit/central deception until reveal chapter.
- **Commit all outstanding work.** User asked to commit and push all; both engine and series repos were pushed to origin/main and verified clean afterward.

## User preferences / corrections this session
- Local models are struggling with large token payloads; prioritize lean prompt surfaces over simply extending timeouts.
- User asked for succinct curated LM Studio digest files rather than only truncation caps.
- User asked to commit and push all outstanding engine/series work.

## Key files and artifacts
- `/Users/beeko/myTools/penny/scripts/lmstudio_draft_chapter.py` — LM Studio scene-shard drafter; now supports digest preference, compressed chapter context, whodunit excerpts, and prompt-size logging.
- `/Users/beeko/myTools/penny/commands/draft-chapter-lmstudio.md` — command/runbook documenting digest files and fallback behavior.
- `/Users/beeko/myTools/penny/tests/test_lmstudio_draft_chapter.py` — tests for scene splitting, compaction, whodunit excerpting, and digest precedence.
- `/Users/beeko/myBooks/series-pelicanscrook/config/voice-pack/lmstudio-digest.md` — compact voice prompt surface for local drafting/review.
- `/Users/beeko/myBooks/series-pelicanscrook/config/genre-pack/lmstudio-digest.md` — compact cozy genre prompt surface.
- `/Users/beeko/myBooks/series-pelicanscrook/config/setting-pack/lmstudio-digest.md` — compact coastal Victoria/Wreckers Bluff setting prompt surface.
- Hermes skills updated:
  - `penny-book-generation` — now instructs use of LM Studio digest files.
  - `lmstudio-penny-local-review` — now prefers digest files for local review context.

## Commands already run
```bash
# Engine tests
cd /Users/beeko/myTools/penny
python3 -m pytest tests/test_lmstudio_draft_chapter.py -q
python3 -m pytest -q

# Verify Pelican digests are loaded by collect_context
python3 - <<'PY'
from pathlib import Path
from scripts import lmstudio_draft_chapter as lm
root = Path('/Users/beeko/myBooks/series-pelicanscrook')
ctx = lm.collect_context('01', '01', root)
print(ctx['voice_pack'].splitlines()[0])
print(ctx['genre_pack'].splitlines()[0])
print(ctx['setting_pack'].splitlines()[0])
print(len(ctx['voice_pack']), len(ctx['genre_pack']), len(ctx['setting_pack']))
PY

# Commit/push engine
cd /Users/beeko/myTools/penny
git add -A && git commit -m "feat: add LM Studio chapter drafting route" && git push origin main

# Commit/push series
cd /Users/beeko/myBooks/series-pelicanscrook
git add -A && git commit -m "chore: checkpoint book 01 drafting state" && git push origin main

# Final save-time checks
cd /Users/beeko/myTools/penny
git status --short
git log -1 --oneline
git -C /Users/beeko/myBooks/series-pelicanscrook status --short
git -C /Users/beeko/myBooks/series-pelicanscrook log -1 --oneline
```

## Watch out for
- Save-time engine last commit is `8c52791`, not the LM Studio route commit `49dfed8`. That indicates additional engine work landed after the LM Studio commit; inspect before assuming LM Studio is HEAD's only change.
- The series commit `8cfd35e` intentionally included all outstanding series artifacts, including drafts/local-review reports and outline-feedback reports, because the user said commit and push all.
- The digest files are compact but not authoritative replacements for the full packs. Full packs remain authoritative for cloud/human review and broader series calibration.
- Keep engine genre/location agnostic: never move Pelican/Maggie/Wreckers Bluff-specific digest prose into `/Users/beeko/myTools/penny/scripts`, `commands`, or `agents`.
- If LM Studio output remains weak, diagnose actual prompt char counts and model selection first; do not assume a larger timeout or larger `max_tokens` will fix reasoning/context overload.
- Engine now has untracked wiring files (`scripts/penny_wiring.py`, `tests/fixtures/outlines/wired-clean.md`, `tests/test_penny_wiring.py`) that were not part of the LM Studio commit. Read them before deciding whether to commit, delete, or fold into the plotting-workshop stream.

## Open questions
- Should Chapter 3 now go to normal `/review-chapter 01 03` / cloud review?
- Should the newly committed plotting-workshop plan (`8c52791`) be the next engine stream, or should work stay focused on LM Studio drafting/review hardening?
