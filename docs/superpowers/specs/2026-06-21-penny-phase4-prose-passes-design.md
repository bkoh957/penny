# Penny Phase 4 — Prose Passes + Post-Gate Finalize — Design

Saved: 2026-06-21 | Phase 4 of the v3 build order (`penny-design-v3.md` §13).

## §1 Purpose

Phases 1–3 built the pipeline up to and including the developmental gate
(`/draft-chapter` → `/review-chapter` → PASS/HOLD). Everything *after* the gate is
unbuilt. Phase 4 builds the post-gate tail of the per-chapter flow (design §5):

```
DEVELOPMENTAL GATE (built)
  → LINE-EDIT      prose rhythm / word choice / voice at sentence level
  → COPY-EDIT      fresh-context agent + style sheet; grammar/consistency
  → FINALIZE       ledger-updater (post-gate) + deterministic markers; ledger-diff
  → promote ch-NN.final.md
```

It also lands the **Phase-4 slice of the canon-core demotion feature**
(`2026-06-20-penny-canon-core-demotion-design.md` §7.1): the per-section
`canon-meta` data contract and the `last_referenced` precision marker, written at
the same post-gate point as the analogous thread `last_advanced_chapter`.

## §2 Scope

**In:**
- `line-editor` agent + `config/line-edit/line-edit.md` config module.
- `copy-editor` agent + `config/copy-edit/copy-edit.md` config module.
- `ledger-updater` agent (prose-body extractive writes).
- `ledger_markers.py` deterministic helper (structured-field marker writes; fixture-tested).
- `/finalize-chapter N CH` command (orchestrates the tail; `--commit` resume).
- `preflight.py finalize N CH` subcommand (deterministic gate guard).
- Per-section `canon-meta` data contract on `canon-core.md` + `active_window` authored
  for the existing sections + `parse_canon_sections()` parser/writer support.
- `last_referenced` (canon-core sections) + `last_advanced_chapter` (threads) markers.
- Style-sheet accumulation (copy-edit appends).
- Touch-ups: `review-chapter.md` roster from real `last_advanced_chapter`;
  `draft-chapter.md` stale-preamble refresh.

**Out (explicitly deferred):**
- **Self-audit `[P1]` + Tier-B** fix-pass — fast-follow, measured by revision-loop
  reduction; sits *pre-gate* (a different insertion point), built once Phase 4 is stable.
- **Demotion detector / executor / reachability assert** (`canon_core_review.py` and the
  move machinery) — Phase 8; cross-book coldness cannot fire on Book 1.
- **`active_window` *consumption*** — Phase 8. Phase 4 only *authors* the data (the
  capture window is now; the only mutable→frozen moment for these Book-1 facts).
- Beta layer — Phase 5.

## §3 Key decisions (and why)

1. **Self-audit deferred.** It is a cost optimization measured by revision-loop
   reduction, which requires a running pipeline; and it inserts *pre-gate*, a
   different seam from this post-gate work. Keeping Phase 4 to the tail keeps the
   surface focused.

2. **Hybrid ledger update — split by edit-type (mechanical vs. semantic).**
   - The `ledger-updater` **agent** owns **prose-body** writes (knowledge-state,
     newly-established canonical facts) — LLM reading-comprehension work.
   - `ledger_markers.py` **script** owns all **structured-field** edits (HTML-comment
     `canon-meta` headers; thread frontmatter) — fiddly, error-prone for an LLM, and
     the demotion *precision seed*, so it belongs in tested Python.

   This mirrors the design's own altitude discipline (deterministic where mechanically
   checkable; LLM only where judgment is required) and the existing
   `fairplay_check` / `lexicon_check` / `voice_drift` script pattern.

3. **One `/finalize-chapter` command, gate-guarded.** The four post-gate steps always
   run in sequence after a PASS; one command per pipeline stage matches the existing
   `draft → review → finalize` rhythm. A deterministic guard refuses to finalize a
   HELD or un-reviewed chapter.

4. **Full per-section `canon-meta` schema authored now.** `active_window` is only
   capturable at promotion time (demotion spec §2, §7.1); the 4 existing canon-core
   sections were "promoted" at skeleton time, so this is the capture window. Laying the
   full header schema down now unblocks Phase 8 on the data side at near-zero cost.

## §4 Components

### §4.1 `/finalize-chapter N CH` — the orchestrator

A new command `.claude/commands/finalize-chapter.md`. Argument-hint:
`<book-number> <chapter-number> [--commit]`.

**Normal run (`/finalize-chapter N CH`):**

0. **Gate guard (deterministic).**
   ```bash
   python3 scripts/preflight.py finalize $1 $2
   ```
   Non-zero exit ⇒ the chapter has not passed the gate; abort before any agent
   dispatch. (See §4.6.)
1. `stage=LINE-EDIT` → dispatch **line-editor** with `ch-CH.draft.md` + Voice Pack +
   length profile. Output `ch-CH.lineedit.md`.
2. `stage=COPY-EDIT` → dispatch **copy-editor** with **only** `ch-CH.lineedit.md` +
   `series/style-sheet.md` (never drafting history). Output `ch-CH.copyedit.md`;
   appends any new decisions to `series/style-sheet.md`.
3. `stage=FINALIZE` →
   - dispatch **ledger-updater** agent (prose-body writes to the loaded slice;
     emits per-thread `advanced: yes/no`);
   - run `ledger_markers.py` (structured marker writes);
   - both writes summarized in `ch-CH.ledger-diff.md`.
4. **Promote:** copy `ch-CH.copyedit.md` → `ch-CH.final.md` (carrying frontmatter).
5. **`ledger_approval` branch** (read from `config/run-config.md`):
   - **`auto`** → the command git-commits `ch-CH.final.md` + the continuity writes +
     the style-sheet append + the marker edits; `stage=FINALIZED`.
   - **`review`** → **pause**: all artifacts are already written to the working tree
     (only the commit is withheld); surface `ch-CH.ledger-diff.md` and instruct the
     showrunner to review `git diff`, then run `/finalize-chapter N CH --commit`.
     `stage=LEDGER-REVIEW`. No commit.

**Resume run (`/finalize-chapter N CH --commit`):**

- Assert `stage == LEDGER-REVIEW` (artifacts present). Then **skip straight to the
  git commit** of the already-written working tree; `stage=FINALIZED`. **Runs no agents.**

**No-flag refusal guard.** A plain `/finalize-chapter N CH` on a chapter already at
`stage == LEDGER-REVIEW` **refuses** and points to `--commit`. Re-running the pipeline
would re-dispatch line-edit/copy-edit, which produce *different prose each time*
(inherently non-idempotent), silently discarding the prose the showrunner just
reviewed. A true redo requires explicitly clearing the artifacts / resetting the stage.

Each step writes `.penny/current-stage` (`book=NN chapter=CH stage=…`) so the status
bar tracks live position (design §11).

### §4.2 `line-editor` agent

`.claude/agents/line-editor.md` + `config/line-edit/line-edit.md`.

- **Inputs:** the draft text, the Voice Pack, the length profile.
- **Does:** refine rhythm, word choice, flow, cut flab, strengthen verbs — **preserving
  voice and meaning**.
- **Does not:** add content, alter plot/continuity, or touch the mystery. Output is
  **revised prose only**.

### §4.3 `copy-editor` agent

`.claude/agents/copy-editor.md` + `config/copy-edit/copy-edit.md`.

- **Fresh context:** given **only** the (line-edited) text + `series/style-sheet.md`,
  **never** the drafting history — the industry "hand the copyedit to someone new"
  practice (design §7).
- **Does:** grammar, punctuation, consistency against the style sheet.
- **Writes:** corrected prose **and** appends any new spelling/hyphenation/
  capitalization decisions to `series/style-sheet.md` (accumulates across 13 books).

### §4.4 `ledger-updater` agent (prose-body writes)

`.claude/agents/ledger-updater.md`. Literal/extractive post-gate record-keeper
(design §4.3).

- **Inputs:** the finalized chapter text, the chapter brief, and the **same loaded
  slice** the draft/review steps used (`canon-core` + brief-derived + one-hop links).
- **Writes (prose body only), within the loaded slice — write-scope = read-scope:**
  - knowledge-state updates for **present** characters → `series/continuity/characters/<id>.md`;
  - newly-established canonical facts → the relevant entry's "Established facts" region.
- **Emits** a small structured signal in `ch-CH.ledger-diff.md`: per in-slice thread,
  `advanced: yes/no` (a **semantic** judgment — *mention ≠ advance*). This is the one
  agent→script seam, consumed by `ledger_markers.py`.
- **Guards:**
  - **Does not** mutate `canon-core.md` body. Promotion *into* canon-core stays a
    deliberate showrunner act; facts land in entry files, not canon-core. The updater's
    only effect on canon-core is the `last_referenced` header stamp, performed by the
    script.
  - **Does not** write structured marker fields (the script's job) and **does not**
    judge thread *liveness/dormancy* (the structure inspector's job, design §8) — it
    only records that a thread *advanced* on the page.

### §4.5 `ledger_markers.py` (deterministic, fixture-tested)

`scripts/ledger_markers.py`. Dependency-free, in the style of the existing checkers.
Owns **all structured-field edits** (header/frontmatter), because such edits are
error-prone for an LLM and the markers are the Phase-8 demotion precision seed.

- **`last_referenced: CH`** into each canon-core **section header** the script computes
  as referenced — a **mechanical id-scan**: a section is "referenced" iff any of its
  ids appears in the finalized brief or chapter text (substring/token match, no LLM).
- **`last_advanced_chapter: CH`** into **thread frontmatter** for threads the
  ledger-updater flagged `advanced: yes`.
- Drives the per-section `canon-meta` edits via the shared parser/writer in
  `penny_meta.py` (`parse_canon_sections()` + the section-header writer, §4.7);
  `ledger_markers.py` itself holds the marker policy (which section/thread to stamp
  with what), not the YAML-in-HTML-comment mechanics.
- **Write-scope bounded to the loaded slice** — never stamps a section/thread the
  chapter did not load.
- **Idempotent re-application** (§7): re-stamping a section already at `CH` is a clean
  byte-identical no-op; stamping over an older value cleanly overwrites; canon-core
  **prose body is left byte-intact** (the drafter reads it verbatim).

### §4.6 `preflight.py finalize N CH` (gate guard)

A 4th subcommand on the existing `scripts/preflight.py` (joining `lock-mystery`,
`draft`, `assemble`), consistent with preflight's role as Penny's deterministic gate
tool. Reads `output/book-NN/chapters/ch-CH.gate.md` and exits non-zero unless it shows
a PASS verdict. A HOLD, or a missing gate file, blocks finalize. Deterministic file
read — immune to soft-gate weakness.

### §4.7 Data-contract changes

- **`canon-core.md`:** each `##` section gains
  `<!-- canon-meta: {id, active_window, last_referenced, reconfirmed_at, keep_reason} -->`
  (demotion spec §2). The **file-level** header (`{id: canon-core, fluency_stage: OUTSIDER}`)
  is retained — `fluency_stage` is a real always-loaded value. The showrunner authors
  `active_window` for the 4 existing sections during this phase (`last_referenced`,
  `reconfirmed_at`, `keep_reason` start unset/`null`).
- **`penny_meta.py`:** add `parse_canon_sections(text) -> list[dict]` returning the
  per-section headers (id + fields) keyed to their `##` heading, plus a section-header
  **writer** (update one field, write back, preserving body bytes). Leave the existing
  `parse_canon_meta()` (first/file-level header, for `fluency_stage`) **untouched** —
  backward compatible.
- **Thread files** (`series/continuity/threads/*.md`): add `last_advanced_chapter` to
  frontmatter (initially unset).

## §5 Touch-ups to existing wiring

- **`review-chapter.md` step 6:** build the structure-inspector roster from threads'
  **real `last_advanced_chapter`** instead of the current `unknown` placeholder. The
  roster builder maps a missing/unset value → `null` (never an error). `null` =
  "no advancement recorded yet" → `inspector-structure` emits **no** dormancy flag for
  that thread (identical to today's `unknown` contract). Dormancy is measured only
  once a thread has at least one recorded advancement — this avoids false-flagging
  freshly-opened Book-1 threads while the data populates. (Decision: unset stays
  *silent*, not flag-as-dormant.)
- **`draft-chapter.md` preamble:** refresh the stale "Phase 1: no review bus yet"
  wording (a deferred Phase-3 follow-up).

## §6 Data flow

```
ch-CH.draft.md ──► line-editor ──► ch-CH.lineedit.md
                                       │
                 style-sheet.md ◄──┐   ▼
                                   copy-editor ──► ch-CH.copyedit.md
                                                       │
   loaded slice (canon-core + brief-derived + one-hop) │
            │                                          ▼
            ├─► ledger-updater (agent) ──► continuity entry files (prose body)
            │            │                 + per-thread {advanced: yes/no}
            │            └──────────────────────────┐
            └─► ledger_markers.py (script) ◄─────────┘ (consumes advanced flag)
                       │  last_referenced → canon-core section headers (mechanical id-scan)
                       │  last_advanced_chapter → thread frontmatter (from advanced flag)
                       ▼
                 ch-CH.ledger-diff.md  ──►  promote ch-CH.final.md
                       │
            ledger_approval: auto → git commit (stage=FINALIZED)
            ledger_approval: review → pause (stage=LEDGER-REVIEW) ──► /finalize-chapter --commit
```

## §7 Resume / idempotency seams (the under-specified joints, pinned)

1. **Review→resume.** In `review` mode FINALIZE writes all artifacts to the working
   tree; only the commit is withheld. The review surface *is* the working tree (`git
   diff` + `ledger-diff.md`); the showrunner may hand-edit a continuity file before
   committing. Resume is the **explicit `--commit` flag** (commit-only, runs no
   agents), **not** a pipeline re-run. A no-flag re-run on a `LEDGER-REVIEW` chapter is
   **refused** (protects reviewed prose from non-idempotent re-editing). See §4.1.

2. **Unset `last_advanced_chapter`** is a value, never an error: roster builder maps
   it → `null` → no dormancy flag (silent until a baseline exists). See §5.

3. **Marker idempotency under redo.** Normal resume re-applies *nothing* (markers ran
   pre-pause; `--commit` just captures them). But re-application is still safe for
   forced redos / double-runs, and is tested as such (§8): re-stamp `CH` over `CH` =
   byte-identical no-op; over an older value = clean overwrite; full second pass = no-op
   diff; canon-core prose body untouched throughout.

## §8 Testing focus (TDD, per the Phase-2a/3 pattern)

- **`ledger_markers.py`:**
  - per-section `canon-meta` parse → edit one field → write-back **round-trip**;
  - mechanical id-scan referenced/not-referenced;
  - `last_advanced_chapter` stamp driven by the `advanced` flag;
  - **write-scope bounded to the loaded slice** (never stamps an unloaded section/thread);
  - **re-application idempotency** (stamp `CH` over `CH` = byte-identical no-op; over
    older value = clean overwrite; full second pass = no-op);
  - **canon-core prose body left byte-intact** (drafter reads it verbatim).
- **`parse_canon_sections()`** unit tests; existing `parse_canon_meta()` unchanged
  (regression: still reads file-level `fluency_stage`).
- **`preflight.py finalize`** gate-guard: PASS allows, HOLD blocks, missing gate file
  blocks.
- **Cross-consistency:** marker writes do not corrupt the canon-core prose the drafter
  loads; style-sheet append is well-formed.

## §9 Acceptance

- `/finalize-chapter N CH` runs the full tail after a PASS gate and refuses after a HOLD.
- `review` mode pauses cleanly and resumes via `--commit` with no prose loss; no-flag
  re-run on a paused chapter is refused.
- `auto` mode commits the chapter end-to-end.
- canon-core carries per-section `canon-meta` headers with showrunner-authored
  `active_window`; `last_referenced` and `last_advanced_chapter` are populated by a
  finalize run.
- `review-chapter` builds its roster from real `last_advanced_chapter`, treating unset
  as silent.
- All new scripts fixture-tested and green; existing suite still green.
```
