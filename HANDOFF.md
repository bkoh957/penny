# Handoff — Penny (fiction-series engine) / main
Saved: 2026-08-29 14:23 | Type: build (one feature, five defects, one design — all committed and pushed)

> Supersedes this file's earlier save from 2026-08-29 00:12, which covered only the texture
> layer and the first two defect fixes. Everything there is still true and still shipped;
> this adds what came after it.

## What we built

**41 commits.** One feature, five defects, one design note. All pushed to `origin/main`,
HEAD `7aa6fe7`, suite **1263 green**, tree clean.

### 1. Texture allocation — the feature (spec `2026-08-27-texture-allocation-design.md` §4.1+§4.2)

Texture was the only creative concern in the engine with no allocation layer: every chapter
got the same standing guardrail and the drafter decided locally, blind to the other 34
chapters. Now it has a schedule, like clues, beats and words.

- `## Reservoir` in `background-history.md` → `config/setting-pack/reservoir.md`, the second
  verbatim part beside `## Stance`. Optional; excluded from LM Studio's 2,500-char pack.
- `- **Texture:**` in `cut-plan.md` → `### Texture` in the outline → the packet (free — the
  packet embeds the whole block) → per-scene `Texture:` in the map → the drafter.
- `/allocate-texture NN` + the `texture-allocator` agent + `scripts/texture_apply.py`.
- **Deliberately ungated.** No `unscheduled-texture`, ever — an obligation would make images
  compete with beats and clues for the beat sheet's `obligations.max_per_chapter` budget.

§4.3 (punch-up) stayed unplanned on purpose; spec §7.3 says it is only answerable once
chapters have been drafted against an allocation.

### 2–6. The five defects

| defect | spec | state |
|---|---|---|
| packet extract heading collision | `2026-08-27-packet-extract-heading-collision-fix.md` | fixed, reviewed (4 commits) |
| voice_drift discards its evidence | `2026-08-27-voice-drift-discards-evidence-fix.md` | fixed, reviewed (2 commits) |
| engine holds one series' story details | `2026-08-29-engine-holds-story-details-fix.md` | fixed (`34b133f`) — **review never run** |
| nested cut-plan field hijack | `2026-08-29-nested-cut-plan-field-hijack-fix.md` | fixed (`597b014`) — **review never run** |
| runbook positional off-by-one | `2026-08-29-runbook-render-corrupts-positional-vars-fix.md` | **§4b only** — §4a open |

### 7. The design note

`2026-08-29-curated-artifacts-declare-their-contents-design.md` — the general shape behind
four of the defects, with the framing corrected. Not approved; one open decision in its §6.

## Git state

- Branch `main`, pushed, nothing local. Last commit `7aa6fe7`.
- Tests: **1263 passing**. `CLAUDE.md`'s count line is self-checked by a test and is exact.
- Untracked leftovers, not from this session: `HANDOFF-of122.md`,
  `HANDOFF-readiness-briefs.md` (single-item streams, 2026-08-25).

## Next actions

1. **Decide §4a of the runbook spec — the seven runbooks' off-by-one.** This is the only item
   blocking others (§4c's lint and §4d's convention sit behind it). Two options, both written
   up in the spec: renumber `$1`→`$0` on verified behaviour, or restart Claude Code and test
   whether `arguments: [book, chapter]` named binding works for **plugin commands** (it is
   documented for skills and explicitly unverified for commands). Named arguments are better
   if they work — immune to the harness changing indexing again — but must be tested, not
   assumed. **Either fix only takes effect after a restart** (see Watch out for).
2. **`## Ledger Clues` manifest + heading demotion** — §4a of the new design note. The next
   site, and the same bug latent: `packet_assemble.py:293` interpolates ledger descriptions
   raw, and ten of book 01's forty-five clue entries are multi-line block scalars. One
   authored `## ` from terminating the section, and a truncated clue list is worse than a
   truncated continuity slice because `inspector-fairplay` grades against the sealed ledger.
3. **Run the two missing reviews** — `597b014` (field hijack) and `34b133f` (engine story
   details). Both were dispatched and killed by Opus session limits; nothing was lost.
4. **`repeated_content_words` measures function words** — §7 of the voice-drift spec, verified
   not implemented. Its five cited spans on book 01 ch 01 are *that* ×27, *been* ×12,
   *could* ×10, *down* ×10, *there* ×10. Needs a real stoplist (~200 entries, in a data file)
   and a recalibrated threshold.
5. **The `**Beats:** 9` hijack is fixed** (`597b014`) — item 3 covers its review.

## Decisions made this session

- **The reservoir reaches the drafter through the setting-pack directory read, not the
  packet.** Four agents already read that whole directory; embedding a global constant in a
  per-chapter artifact is the failure CLAUDE.md names for the voice and genre packs. A
  deliberate deviation from spec §4.1's "and the packet".
- **"the voice pack", never "the series voice pack"** in engine files. That path resolves
  series → genre → plugin; naming the bottom tier forecloses the middle one. The showrunner's
  three-level model — engine / genre pack / series folder — drove this.
- **Detect, don't prevent, for the field hijack.** The parser still overwrites; `check_story`
  refuses loudly. Anchoring the parser at column 0 would turn an accidentally-indented genuine
  field line into a silently-swallowed texture item — trading one silent failure for another.
- **Reuse `wiring-shaped-directive`; roster stays 23.** Showrunner's call.
- **Manifests before receipts.** The design note recommends *against* building the receipt
  half until a manifested section is observed to be under-read anyway.
- **Examples in engine files never name a character** — written into
  `config/story-craft/writing-beats.md` after the site count moved four times (10→12→14→17),
  each wave found by a different method. One unwritten rule, not four oversights.

## User preferences expressed this session

- Commit finished-but-uncommitted work before starting new work, rather than stashing.
- Work on `main`, phase at a time, push at the end.
- Verify claims empirically rather than reasoning from documentation — this session was
  confidently wrong for a day about runbook indexing by trusting docs written for skills.
- Amend a spec when review changes it, and leave the correction visible rather than tidying
  it away — the moving count is the argument.

## Key files right now

- `docs/superpowers/specs/2026-08-29-runbook-render-corrupts-positional-vars-fix.md` — §4a is
  the live decision; §2b records the render test and how to re-run it.
- `docs/superpowers/specs/2026-08-29-curated-artifacts-declare-their-contents-design.md` —
  next build item is its §4a.
- `scripts/packet_assemble.py:293` — the raw ledger-description interpolation.
- `scripts/voice_drift.py` — split tics, compat shim, `UnevidencedFlagError`.
- `scripts/story_cut.py` — `check_story`'s indentation guard; see Watch out for.
- `.superpowers/sdd/2026-08-27-texture-allocation/progress.md` — the full ledger for the
  texture build: every ruling, parked minor and review verdict. **Gitignored**, dies with this
  machine.

## Watch out for

- **Command files are snapshotted at session start.** Editing a `commands/*.md` mid-session
  has no effect on what renders — proven by adding a probe block to `diagnose-outline.md` and
  watching it render without it. So any §4a fix needs a restart before it takes effect, and
  named arguments cannot be tested without one.
- **Runbook argument substitution is ZERO-INDEXED.** `$0` is the first argument, `$1` the
  second. Verified by rendering `finalize-chapter` with `AAA BBB CCC`. Do not "correct"
  `book=$0` back to `$1` — that is the bug, not the fix.
- **`story_cut.py`'s forgery guard is a rule about INDENTATION, not about blocks.** The first
  attempt modelled where a nested block ends by re-deriving `penny_story`'s state locally and
  a single blank line reopened the bug. Do not reintroduce a state machine.
- **Naming a load-bearing absence is house style.** Engine files say "`map_check.py` has no
  `unscheduled-texture` and never will". Two contract tests asserted the opposite and were the
  defect; they were inverted. Don't re-invert them.
- **`extract_brief.py` diverges from the awk it replaced on an interposed `# ` heading** — it
  does not stop there, `chapter_block()` matching `##` only. Inherited, no current outline
  triggers it, pinned by a test and documented in the module docstring. Fixing it would change
  every packet.
- **A commit written by the controller rather than a subagent failed its review** (`ebae29f`,
  superseded by `d56729c`). It closed only the shape its own test used. If a fix's tests
  exercise one input shape, it will pass and still be wrong.
