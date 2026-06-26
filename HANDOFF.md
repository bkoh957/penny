# Handoff — Penny / main
Saved: 2026-06-27 | Type: build

## What we're building
Running the per-chapter pipeline for Book 01. This session: re-gated ch-01 to PASS,
discovered ch-02..05 drafts were ALL stale against the revised outline (not just ch-05
as the prior handoff thought), redrafted all four against the current outline, added
the missing Iris Poole continuity entry, and gated ch-02..05 to PASS. Inspectors were
switched to Sonnet. Also fixed an unrelated status-bar bug.

## Git state
- Branch: `main`. All work committed AND pushed. HEAD `6beb89e`.
- Uncommitted changes: **none** (clean tree).
- Tests: **all passing** (~180; full `python3 -m pytest` green this session).
- This session's commits (oldest→newest):
  - `299f5ae` fix(book-01): resolve ch-01 continuity HOLD; re-gate PASS
  - `b16fd84` feat(book-01): redraft ch-02..05 against revised outline; add Iris Poole
  - `44b64a5` feat(book-01): gate ch-02..05 to PASS (sonnet inspectors)
  - `6beb89e` fix(statusline): count only numbered chapters in the total

## Current pipeline state
- **ch-01..05 all `gate: PASS`** (`.penny/current-stage` = `book=01 chapter=05 stage=REVIEWED`).
- **None are finalized.** No chapter has been through `/finalize-chapter` (line-edit →
  copy-edit → ledger update → promote → commit). No `.final.md` exists yet.
- ch-06..28 not drafted. Reveal chapter is **24** (book-level `fairplay_check.py` only
  fires there).

## Next actions
1. **Finalize the gated chapters.** `/finalize-chapter 01 01`, then `02`, `03`, `04`,
   `05`. Each requires `gate: PASS` (all satisfied). Note `config/run-config.md`
   `ledger_approval` controls whether finalize pauses for a diff review or commits
   end-to-end — check it before running. `copyedit_model: claude-opus`.
2. **(Recommended) Fix the verdict-filename contract bug** — see Watch out for. Low
   effort, prevents silent false HOLDs on future re-gates.
3. Then continue drafting ch-06 onward (`/draft-chapter 01 06` → review → finalize).

## Decisions made this session
- **Drafters on Opus, inspectors on Sonnet.** User's explicit choice. Set
  `inspector_model: claude-sonnet` in `config/run-config.md`. Pass `model: "opus"` /
  `model: "sonnet"` on Agent dispatches (the agent defs have no `model` frontmatter, so
  without an override they inherit the parent = Opus). Sonnet-inspecting-Opus is genuine
  cross-model independence; also dodges the Opus session cap (which DID hit mid-session).
- **Resolved every ledger-vs-draft conflict by treating the outline as source of truth.**
  When a blind inspector flagged a contradiction, the fix went to whichever side
  disagreed with the *outline*: ch-01 HR tenure → "decade" (matched ledger); ch-02 Mary
  "first appears ch 5" → **ch 2** (outline gives her the lemon-cutting scene, so the
  ledger was stale); ch-03 Neil "edge of the bed" → **"sat close"** (outline sets the
  migraine in the studio, "bed" was incidental staging); ch-04 Mary-as-stranger → Maggie
  recognises her (ripple from the ch-02 fix). ch-04 also: `footy`/`tinnie` → neutral
  (OUTSIDER fluency).
- **Iris Poole minimal continuity entry**, drafted from the outline + Faye's file (she's
  the jam-feud counterpart / show judge; NOT a murder suspect; feud's buried origin is a
  ch-13 clue, kept off-page pre-reveal). Added reciprocal `iris-poole` link in faye.md.
- **Atomic commits**, separating the ch-01 fix, the redraft batch, the gating pass, and
  the unrelated statusline fix.

## User preferences expressed this session
- **Draft with Opus, inspect with Sonnet** (now in run-config; persist for future books).
- Lead with a recommendation; decisive after a shortlist (consistent with prior memory).
- Commit, then push to GitHub. Atomic, logically-separated commits.

## Key files right now
- `output/book-01/chapters/ch-0{1..5}.draft.md` — all PASS, awaiting finalize.
- `series/continuity/characters/iris-poole.md` — NEW this session; eyeball her framing
  before she recurs (ch-13 pays off the feud).
- `series/continuity/characters/mary-burrell.md`, `neil-hartigan.md` — ledger lines
  corrected this session (Mary first-appears ch 2; Neil "sat close").
- `config/run-config.md` — `inspector_model: claude-sonnet` (changed this session).
- `scripts/penny-statusline.sh:63` + `tests/test_statusline.py` — statusline fix + new
  regression test.

## Watch out for
- **Verdict-filename inconsistency (latent engine bug).** Several inspector subagents
  wrote `inspector-<role>.md` (derived from the verdict `producer` field) instead of the
  canonical `<rubric>.md` that `/review-chapter` expects (`continuity-drift.md`,
  `fairplay-planting.md`, `structure-tension.md`, `character-voice.md`,
  `ai-prose-taste-flags.md`). Because `review_gate.py` greps `^BLOCKING:` across **all**
  `.md` files in the reviews dir, a stale duplicate (e.g. a pre-fix `inspector-voice.md`)
  silently caused a false HOLD on ch-04 this session. I normalised names by hand and the
  committed dirs are now clean (each has exactly the canonical 5 + `voice-drift.md` +
  `lexicon-fluency.md`). Fix options: pin `penny_verdict.write_verdict` to the canonical
  filename, or have the gate/`reset_reviews` reject non-canonical names. Check
  `scripts/penny_verdict.py`'s filename logic.
- **`reset_reviews.py` runs at the start of `/review-chapter`** and clears the dir — so a
  re-gate reflects only that run. Good, but it means committed review dirs get rewritten
  on every re-gate.
- **28 chapters is correct** (matches `total_chapters: 28`); the old "29 vs 28" scare was
  just `## Chapter Engine Used Throughout` matching a loose grep — resolved by the
  statusline fix (`^## Chapter [0-9]`).
- **Mary Burrell is the sealed culprit** — neither her file's drafter-visible section nor
  any draft names/implicates her; keep it so through finalize. **Mary raised Cal** (planted
  ch 11). **Iris is NOT the murderer** — feud is sad, not murderous (cleared ch 13).
- **OUTSIDER fluency (Book 1):** no local idiom in Maggie's narration — only in dialogue.
- **`.penny/` is gitignored** (holds the mystery lock + current-stage). Do not `git clean -fdx`.
- **Cross-model invariant:** `final_read_model: codex` must differ from all `drafted_by`
  stamps. Drafts are `claude-opus`; fine. Don't draft/finalize-read with the same model.
