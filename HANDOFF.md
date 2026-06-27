# Handoff — Penny / main
Saved: 2026-06-27 | Type: build

## What we're building
Book 01 of the cozy-mystery series. This session: finalized ch-01 (the full
post-gate prose pipeline ran for the first time ever), then did a structural revision —
renamed the psychic gift "Migraine Sight" → **"the Too-Much"** and inserted a new
**Ordeal chapter (ch 18, *The Only Quiet*)**, taking Book 01 from 28 → 29 chapters,
renumbering everything downstream and re-locking the mystery. Also routed the finalize
editors to Sonnet and fixed two latent `finalize-chapter.md` bugs.

## Git state
- Branch: `main`. All work committed AND pushed. HEAD `f280c8c`. Tree clean.
- Tests: **252 passing** (`python3 -m pytest`). NOTE: subagents kept misreporting this as
  "189" — the real number is 252; verify independently if a subagent claims otherwise.
- `.penny/current-stage` = `book=01 chapter=01 stage=FINALIZED`.
- Key commits this session (newest→oldest):
  - `f280c8c` fix(finalize): derive brief from outline; commit characters/ + locations/
  - `94ffd82` fix(book-01): culprit_first_appearance_chapter 5 → 2
  - `0304ce7` chore: gitignore root fairplay.md
  - `1174c9f` fix(book-01): style-sheet echo ref ch-28 → ch-29
  - `87f08c1`/`b794820`/`a4457b6`/`76f2b82` etc. — the rename + ch-18 insert + renumber + re-lock
  - `630b179` finalize: book 01 chapter 01
  - `d953343` chore(config): route finalize editors (line/copy/ledger) to Sonnet

## Current pipeline state
- **ch-01 FINALIZED** (`.final.md` exists; continuity ledger advanced; committed).
- **ch-02..05 are `gate: PASS` but NOT finalized** — next up for `/finalize-chapter`.
- **ch-06..29 not drafted.** Book is now **29 chapters**; **reveal chapter is 25**
  (`Mary at the Door`); the new ch-18 is the Ordeal (`The Only Quiet`).
- Mystery lock present & valid (`preflight.py lock-mystery 01` exit 0); fairplay exit 0.

## Next actions
1. **Finalize ch-02..05:** `/finalize-chapter 01 02` → `03` → `04` → `05`. `ledger_approval:
   review` so each PAUSES for a diff review; resume with `--commit`. The finalize-chapter
   bugs are now FIXED, so it runs end-to-end (auto-derives the brief; commits characters/
   + locations/ too) — no manual brief-extraction / hand-staging needed (that was only
   required for ch-01 before the fix).
2. Then draft the new Ordeal chapter and beyond: `/draft-chapter 01 06` … and eventually
   `/draft-chapter 01 18` (The Only Quiet — see its outline entry + the spec for intent).
3. Optional cleanup: none outstanding — both deferred items (gitignore fairplay, culprit
   first-appearance) were resolved this session.

## Decisions made this session
- **Gift renamed to "the Too-Much"** (the protagonist's own wry, ex-HR, reclaiming-an-
  insult word). Chosen over potter-craft names (the Lustre/Kiln-light) because it's her
  voice and it rhymes with the ch-29 payoff ("The Woman Who Saw Too Much" / Elspeth Vale's
  "Saw too much" caption). Keep it UNDERSTATED early so the ch-29 echo detonates. Canon:
  centring clay at the wheel is its ONLY reliable relief (set up by the new ch-18).
- **New ch-18 "The Only Quiet" = the concentrated Ordeal** (Hero's-Journey gap the user
  felt). All-is-lost stall → calm-at-the-wheel insight. FAIR-PLAY: names no culprit, adds
  no clue — the clay only re-frames the planted ch-7 erasure into a *question*; the click
  (ch-19) + Cobber (ch-20) still carry the proof.
- **Reconcile-FIRST renumber** (user-approved): map each ledger/continuity chapter ref to
  the *outline scene* it denotes, then renumber — do NOT blind-+1. This caught real
  pre-existing drift: `clue-erasure` (19), `clue-cobber-dawn-witness` (20), and the Saffron
  collapse (ch 17) were +1 ahead of their scenes, so they did NOT move; only no-drift
  entries (`clue-car`→23, `clue-old-records`→22, reveal→25) shifted.
- **Finalize editors → Sonnet** (line/copy/ledger). ledger-updater kept at Sonnet (NOT
  Haiku) because knowledge-state tracking is load-bearing for fair-play.
- **Drafters Opus, inspectors Sonnet, final-read codex** (carried from prior session).

## User preferences expressed this session
- Lead with a recommendation; decisive after a shortlist. Commit + push at the end (atomic,
  logically-separated commits). Push to GitHub.
- Used the superpowers flow end-to-end: brainstorm → spec → plan → subagent-driven exec →
  final review. The review loops earned their keep (caught 3 real defects). User chose
  subagent-driven (option 1) when offered.

## Key files right now
- `input/book-01/outline.md` — now 29 chapters; new ch-18 at line ~394.
- `series/whodunit/book-01.yaml` — total 29, reveal 25, culprit_first_appearance 2.
- `docs/superpowers/specs/2026-06-27-book01-ordeal-chapter-and-gift-rename-design.md` and
  `docs/superpowers/plans/2026-06-27-book01-ordeal-chapter-and-gift-rename.md` — the spec
  & plan for this session's revision.
- `.superpowers/sdd/progress.md` — the SDD ledger (all 5 tasks complete; reconciliation
  map at `.superpowers/sdd/reconciliation-map.md`). `.superpowers/` is gitignored scratch.
- `.claude/commands/finalize-chapter.md` — bugs fixed this session.
- `config/run-config.md` — lineedit/copyedit/ledger models = sonnet.

## Watch out for
- **Mary Burrell is the sealed culprit; reveal is now ch 25.** Keep her identity out of all
  drafter-visible artifacts (only `mary-burrell.md` may carry it). Mary first appears ch 2
  (lemon cutting), returns ch 5 (market). Iris is NOT the murderer.
- **"Migraine Sight" still appears in 6 frozen `output/**/.reviews/` sidecars** — that's
  intentional (audit records; regenerate on next re-gate). No prose chapter contains it.
- **`fairplay.md` (repo root) is gitignored now** — `fairplay_check.py` writes it to cwd
  when `--out` is omitted; don't be alarmed if it reappears on disk.
- **OUTSIDER fluency (Book 1):** no local idiom in Maggie's narration — only in dialogue.
- **`.penny/` is gitignored** (lock + current-stage + tmp briefs). Do not `git clean -fdx`.
- **`/finalize-chapter` re-derives the brief into `.penny/tmp/`** now — that's expected.
- **`The Only Quiet` is a PLACEHOLDER title** for ch-18 (per the spec); fine to rename.
