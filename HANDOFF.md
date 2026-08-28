# Handoff — Penny (fiction-series engine) / main
Saved: 2026-08-29 00:12 | Type: build (three streams, all shipped, committed and pushed)

> **Replaces** the previous HANDOFF.md, which described the `drafted_words` feature as
> "complete, tests green, NOT committed". That work was committed at the start of this
> session (`ae0cb29`) on the showrunner's instruction and is now pushed; the old file's
> status line was stale and would have misled the next session.

## What we built

Three streams, in order:

1. **Texture allocation** (spec `2026-08-27-texture-allocation-design.md` §4.1 + §4.2) — the
   feature. Texture was the only creative concern in the engine with no allocation layer:
   every chapter got the same standing guardrail and the drafter decided locally, blind to
   the other 34 chapters. Now it has a schedule, like clues, beats and words already do.
2. **Packet extract heading collision** (spec `2026-08-27-packet-extract-heading-collision-fix.md`)
   — a high-severity silent defect, filed by the showrunner mid-session.
3. **voice_drift discards its evidence** (spec `2026-08-27-voice-drift-discards-evidence-fix.md`)
   — likewise.

### 1. Texture allocation — how it works now

- **The reservoir.** `input/series/background-history.md` gains a `## Reservoir` part —
  the town's concrete sensory inventory. `background_cut.py` cuts it verbatim to
  `config/setting-pack/reservoir.md`. It is the *second* verbatim part beside `## Stance`:
  both carry their own `###` group headings through, because in a catalogue those headings
  are content, not entry names. Optional — absent, it writes no file and reports nothing.
  Excluded from `lmstudio_draft_chapter`'s pack concatenation so it cannot eat the
  2,500-char budget and truncate the stance.
- **The allocation.** `cut-plan.md` gains a nested `- **Texture:**` block beside
  `Compress:` — the positive half of a line already written. `story_cut.py` emits it as
  `### Texture`; `packet_assemble.py` carries it into the packet with no code of its own;
  the map-maker distributes it into per-scene `Texture:` fields; the drafter renders it.
- **Authoring.** `/allocate-texture NN` → the `texture-allocator` agent proposes the whole
  book at once (so no image is spent twice — construction, not accounting) → showrunner
  approves to `input/book-NN/plot/texture.md` → `scripts/texture_apply.py` splices it into
  the cut plan idempotently.
- **Deliberately ungated.** Texture is a *resource, not an obligation*. `map_check.py`
  gained no finding; there is no `unscheduled-texture` and never will be. An obligation
  would put images into competition with beats and clues for the beat sheet's
  `obligations.max_per_chapter` budget.

### 2 & 3. The two defect fixes

- **packet_assemble** now demotes every heading in an embedded continuity source below its
  `### <source>` wrapper (ATX, indented ATX, and setext), so nothing a source contains can
  structurally close `## Continuity Extracts`. The section heading carries a manifest —
  `(37 entries: canon-core.md, 30 background/, 6 characters/)` — so a short read is
  checkable instead of silent.
- **voice_drift** splits `lexical_repetition` into `repeated_openers` and
  `repeated_content_words`, each with its own count and threshold, and both now name the
  actual words with line numbers. A compat shim reads the old `lexical_repetition:` config
  block when the new keys are absent. `UnevidencedFlagError` enforces the spec's §4
  invariant: a flagged tic with empty evidence raises.

## Git state

- Branch: `main`, pushed to `origin/main`.
- Last commit: `1a4b05c` docs: track the voice-drift evidence defect spec
- Uncommitted: none.
- Tests: **1235 passing**. `CLAUDE.md`'s count line is self-checked by a test and is exact.
- Untracked leftovers, not mine: `HANDOFF-of122.md`, `HANDOFF-readiness-briefs.md`
  (single-item streams from 2026-08-25).

## Next actions

1. **Author the reservoir.** This is the real work the spec calls for and it is
   showrunner-side, in `~/myBooks/series-pelicanscrook/`: add a `## Reservoir` section to
   `input/series/background-history.md`, then run `background_cut.py`. Spec §7.1 recommends
   building ~30 items for ONE location and drafting a chapter against them before committing
   to a taxonomy — do not write 200 items first.
2. **Then allocate.** `/allocate-texture 01` on a book whose cut plan is settled. On book 01,
   which is already locked, this costs a re-cut, a lock re-mint and re-mapping any mapped
   chapters — deliberate, not free. `/plot-book` calls it before the lock so future books
   pay nothing.
3. **Migrate the series' `ai-tics-config.yaml`** to the new `repeated_openers` /
   `repeated_content_words` keys. Not urgent — the compat shim keeps the old block working —
   but the shim is marked removable once every series has migrated.
4. **Decide on §4.3, the punch-up pass.** Deliberately unplanned. Spec §7.3: whether it is
   needed at all is only answerable once chapters have been drafted against an allocation.
   Don't plan it before then.

## Decisions made this session

- **The reservoir reaches the drafter through the setting-pack directory read, not the
  packet.** Four agents already read all of `config/setting-pack/`, so a file cut there
  needs no plumbing; embedding a global constant in a per-chapter artifact is the failure
  CLAUDE.md names for the voice and genre packs. This deviates from spec §4.1's "and the
  packet" — deliberately, with the showrunner's agreement.
- **`Texture:` is nested sub-bullets, not a single line** like `Compress:`, so the map-maker
  can distribute items one at a time.
- **The approved allocation gets its own save point** (`input/book-NN/plot/texture.md`) and a
  deterministic splice script, rather than 35 hand edits into `cut-plan.md`.
- **`texture_apply.py` never partially applies.** A blocking finding leaves `cut-plan.md`
  byte-identical, even when earlier chapters already spliced successfully.
- **voice_drift's §4 invariant raises rather than warning.** It is evidence-only and never
  gates a chapter, so a raise cannot block a finalize — it fails the checker loudly during
  review, as the engine does elsewhere.
- **The tic split ships with a compat shim**, so an un-updated series does not silently stop
  flagging — the exact failure class that spec is about.

## User preferences expressed this session

- Commit the finished-but-uncommitted `drafted_words` work before starting new work, rather
  than stashing it or branching around it.
- Work on `main`, phase at a time, push at the end.
- When a review's recommendation and a spec's letter conflict, prefer the reading that keeps
  a stated guarantee true (see the `unscheduled-texture` naming ruling below).

## Key files right now

- `scripts/texture_apply.py` — the splice; idempotent, never partially applies.
- `scripts/story_cut.py` — `check_story`'s indented-track-row guard is the subtle part; see
  "Watch out for".
- `scripts/packet_assemble.py` — `_demote_headings` and its five exclusion regexes.
- `scripts/voice_drift.py` — the split tics, the compat shim, `_assert_evidenced`.
- `agents/texture-allocator.md`, `commands/allocate-texture.md` — the authoring surface.
- `.superpowers/sdd/2026-08-27-texture-allocation/progress.md` — the full ledger: every
  ruling, every parked minor, every review verdict. Gitignored, so it dies with this
  machine; read it before redoing any of this.

## Watch out for

- **`story_cut.py`'s texture forgery guard is a rule about INDENTATION, not about blocks.**
  It refuses any indented `TRACK_RE` line inside a chapter block. The first attempt modelled
  where a nested block ends, re-deriving `penny_story`'s state locally, and got it wrong — a
  single blank line reopened the bug. Do not reintroduce a state machine there. `story_cut`
  imports `penny_story._CUT_CHAPTER_RE` deliberately so the two cannot drift.
- **Naming a load-bearing absence is this codebase's house style.** `agents/` files say
  "`map_check.py` has no `unscheduled-texture` and never will". Two contract tests asserted
  the opposite (that the string was absent) and were the defect, not the prose — they were
  inverted. Don't re-invert them.
- **`agents/chapter-cutter.md`'s output template carries an HTML comment where the Texture
  field would be.** That is deliberate: a `- **Texture:** …` placeholder there parses as a
  real inline texture item if a cutter copies the template verbatim.
- **A nested item shaped like a cut-plan KEY still hijacks the chapter's own field, silently.**
  `  - **Beats:** 9` under `- **Texture:**` rewrites the chapter's beat range to `[9]` with
  zero findings. Same class as the bug fixed above, through the other half of the field
  table; pre-existing (arrived with `Setting:` in August), out of scope for the texture spec,
  **surfaced to the showrunner and not fixed.** Beat-range corruption is arguably worse than
  the phantom track that was fixed — CLAUDE.md itself warns an off-by-one there steals beats
  with no symptom. Proposed fix: extend the same indentation rule to
  `_CUT_FIELD_RE`/`_CUT_CLOSING_RE`, reusing `wiring-shaped-directive` (roster stays 23).
- **`voice_drift`'s `flag_at: 0` hazard is fixed but instructive.** A zero threshold used to
  flag on zero matches with empty evidence — harmless until the §4 invariant made it a
  crash, across six tics the spec never mentioned. Flags now require a positive count.
- **Ten minor findings were triaged and deferred**, all listed in the SDD ledger. None
  affect correctness; the final whole-branch review judged every one "fine to leave".
- **`commit ebae29f` was written by the controller, not a subagent** (both dispatches died on
  rate limits) and its review found it defective — it closed only the one input shape its own
  test used. `d56729c` replaced it. The lesson held: a fix whose tests only exercise the shape
  it handles will pass and still be wrong.
