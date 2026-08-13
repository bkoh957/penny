# Handoff — Penny (fiction-series engine) / direction
Saved: 2026-08-11 17:02 | Type: review + design (no code written)

> **Stream note.** This is a strategy stream, not a build. It sits beside
> `HANDOFF-story.md` (the story-layer build, untouched this session and still at
> 19 blocking findings on book 01). **Nothing here has been approved.** Every
> recommendation below is a proposal awaiting the showrunner's call.

## What this session was

A full review of Penny's 475 commits, the v3 PRD/design, and all 35 specs, to answer
three questions the showrunner asked in sequence: what has Penny actually become,
why is the plotting poor when almost every real defect is caught by hand, and how
would you build a cozy engine from scratch.

No files were changed. The output is the analysis below and five engine options.

## Git state

- **Engine** (`~/myTools/penny`): `main` at `32d803e`, clean, pushed. Untouched this session.
- **Series** (`~/myBooks/pelicanscrook-series`): `main` at `decf0c7`; `input/book-01/story.md`
  and `input/series/town-and-character-history.md` still uncommitted (showrunner's own
  in-progress editing, unchanged).
- Tests: not run — no code touched. Last known 962 passing.

## Finding 1 — Penny was specced as a factory and became an instrument

Measured, not asserted:

| Period | What was built | ~commits |
|---|---|---|
| 18–28 Jun | The whole review machine (phases 1–6, "MVP 1 complete") | 160 |
| 26 Jun – 6 Jul | Book 01 content work | 50 |
| 3–10 Jul | Engine-as-plugin, series folders, genre packs | 90 |
| 12 Jul – 6 Aug | Everything upstream of prose: workshop, tension checks, read-back, views, `/book-status`, `story.md`, the cut, beat craft | 170 |

- **Every review/prose script was last modified in June or early July.** `review_gate.py`
  8 Jul, `fairplay_check.py` and `voice_drift.py` 7 Jul, `beta_report.py` 21 Jun,
  `assemble_book.py` 7 Jul. All five inspector agents and four of five rubrics: 10 Jul —
  and that commit was the *blind → isolated* rename, **not a capability change**.
- `output/book-01/` currently holds **reports and nothing else. Zero drafts, zero finals.**
  Five chapters were drafted and gated PASS in late June, two finalized, then reset 5 Jul.
  Book 01 has been in pre-production for over a month.
- **None of the PRD's success metrics are instrumented anywhere.** No code counts a defect
  rate, a first-pass gate rate, or a revision-loop count. The only aggregator is
  `revision_priority.py` at assembly.

The PRD's lagging metric is *showrunner-touch ratio decreasing across Books 1→13*. Every
design decision since 12 July increases showrunner touch on purpose. **The stated goals
and the built system now contradict each other.**

## Finding 2 — why the plotting is poor (three separate causes, don't merge them)

1. **The deterministic layer is a linker, not an editor.** 32 named findings total
   (16 `story_cut.py` + 9 `tension_check.py` + 7 `map_check.py`) and every one asks *do
   the references resolve?* That is a compiler. It cannot tell you the book is worth
   reading, and it is pointed at the one error class the showrunner does not make.
2. **The LLM reviewers read summaries, and the defects live below summary resolution.**
   Proof in the fan report's own words: chapter 4 "could risk feeling like aftermath
   machinery **unless the scene has a vivid social moment**"; **9 of its 25 chapter notes
   are conditional on prose it never saw**, and it scored the book 3s/4s/5s throughout.
   A summary is written in the **justifying voice** — every line silently announces the
   job it does — so bad motivation is invisible, not hidden. This is *not* a compression
   problem: `outline.md` is 92,005 bytes (3,286/chapter) and the Simon hole survived four
   expansion passes.
3. **The data model has no room for why anyone does anything.** The whole plot vocabulary
   is `@strand` / `#job` / `+q`/`-q` / `!clue` — who, function, question state, evidence.
   No field for want, cost, or fear. So the machine fills slots and reaches for the
   cheapest reason a body can be in a room.

**Empirical backing:** `output/book-01/reports/outline-feedback.yaml` holds 34 items
(19 codex, 15 claude; 22 open, 12 rejected). **All 34 came from the open-question review
panel. Zero from any deterministic check. Zero fan-audit items, ever.** The ~250 lines of
`/review-outline` carry 100% of the automated yield.

**Also noted:** cozy is arguably the *hard* genre for this architecture, not the easy one —
its plot is the small part. Thriller (packed specced 8 Jul, 5 open `[DECISION]` flags,
unapproved for a month) would suit the built machinery better.

## Finding 3 — the gate that was named as the whole point was never built

`2026-07-31-layered-outline-workshop-design.md` calls Gate 3 — *would this person do
this* — the workshop's value. `2026-08-03` deferred it explicitly ("those need their own
spec"). The two specs since built the source layer's plumbing and its craft instead.
**No spec, no plan, no owner.** It is the highest-value unbuilt thing in the record.

## The showrunner's correction (take this seriously — it reframed the design)

My first from-scratch proposal centred the town and cast with an emergent plot. **That is
the 1990s Malice Domestic cozy and it is wrong for the market.** The modern KU cozy is
closer to a thriller in cozy clothing: short chapters, a hook on nearly every one, an
**active killer working against the sleuth**, a ticking clock, real danger by act three.
Texture sells the series; **plot sells the book.** Structure matters more than my first
answer allowed — Penny's instinct to model structure was not the error; checking
references instead of pressure was.

## The five options (proposed, none chosen)

Framing that makes them legible: the model already knows cozy and **defaults to the mean**;
expertise is specificity and commitment, so each option is a different mechanism for making
the average unavailable.

1. **Exemplar library** — deconstruct 30–40 modern comps into structure maps; plot by
   retrieval and explicit variation, never from theory. *Ceiling: imitation.*
2. **Adversarial table** — killer / sleuth / reader agents play the book as a game; the
   killer has a plan and reacts. The transcript is the plot. *Risk: wanders; no governor.*
3. **Apprentice + master editor** — a compounding craft memory of real corrections
   (the showrunner's own reads weighted highest). *Weak on book 1; this is the "Penny
   effect" the PRD promised and never built.*
4. **Two engines — puzzle + pressure** — formal fair-play machine beside an independent
   escalation/hook machine, then interleave. *Cheapest from here; the seam shows on the
   best books.*
5. **Scene-first** — generate ~80 candidate scenes, keep the 20 with heat, find the book
   they imply. *Needs option 4's puzzle half bolted on for fair play.*

**Recommendation given:** **2 as the core, 1 as its governor, 3 as its memory**, with 4's
puzzle half retained underneath and 5 held in reserve. Reasoning: the defect is deadness,
not incorrectness, and only 2 stops behaviour being assigned by a planner — which also
generates thriller pressure for free, since opposition escalates without being scheduled.
**Named risk, unresolved:** cutting a commercial 30-chapter shape out of a multi-agent
transcript is unsolved work; prototype on one act before committing.

## Next actions

The showrunner has not chosen. Do **not** start building. In likely order:

1. **Get the decision** on which option (or hybrid) to pursue, and whether it is a fresh
   build alongside Penny or a graft onto it. My stated view: fresh build, because the
   format inversion (human writes prose, machine derives structure) cannot be added to a
   system whose contract is that humans type tags.
2. **Rewrite `penny-PRD-v3.md`'s Goals and Success Metrics** regardless of option chosen —
   they actively contradict the shipped design and every future session reads them.
3. **Prototype the governor** if option 2 proceeds: one act, three agents, then cut a
   commercial shape from the transcript. That is the risky part, so it goes first.
4. **Decide book 01's fate.** It predates the packet format, the source layer, the
   direction blocks and the craft doc; it has been migrated three times and is still 19
   findings from a cut. Every defect in it is confounded with four architectures. Starting
   book 02 clean would tell you in a week whether a process works; book 01 no longer can.

## Standing recommendations from this session (also unapproved)

- **Stop building deterministic checks.** They are done. Keep them as a pre-commit linter —
  they would have caught the skeleton/outline drift — but they are not quality review and
  no more should be built. This is most of the time being lost.
- **Stop reviewing summaries.** Two fixes, neither needing a format change: make the
  reviewer **stage** the moment (render what a reader would see, then judge), or **judge
  across the gap** using a character's whole line through the book. `outline_views.py`
  already renders the second and nothing has ever been pointed at it.
- **Drop every score in the system.** None has ever changed a decision.

## What survives from Penny under any option

Fair play (`fairplay_check.py`) — fairness is genuinely mechanical. The
certificate-not-a-field discipline. Chapters *cut* from a continuous story rather than
authored as containers. Cross-model independence for the final read. Save points instead
of one long conversation. `/book-status`. The packet/map split for drafting. Roughly the
bottom third of the build is right.

## Key files right now

- `penny-PRD-v3.md` — Goals + Success Metrics are the stale part; §Non-Goals still holds.
- `docs/superpowers/specs/2026-07-31-layered-outline-workshop-design.md` §1 — the clearest
  statement of the failure, in the showrunner's own approved words. Read this first.
- `docs/superpowers/specs/2026-08-06-dramatic-beat-authoring-design.md` §1 — the
  syntax-specified/craft-unspecified pattern.
- `~/myBooks/pelicanscrook-series/output/book-01/reports/outline-feedback.yaml` — the
  34-item ledger; the evidence for what actually catches defects.
- `~/myBooks/pelicanscrook-series/output/book-01/reports/outline-fan.md` — the summary-blind
  fan read; the conditional phrasing is the proof.

## Watch out for

- **Nothing in this file is approved.** A fresh agent must not treat the recommendation as
  a decision.
- **The two review failures are separate causes.** The deterministic checks fail because
  they only check references (they never read prose at all); the LLM reviewers fail because
  they read summaries. Merging them produces the wrong fix.
- **"Compress less" is the wrong lever** and the 92KB outline disproves it. The problem is
  the justifying voice, not the byte count.
- **Do not re-derive the June review layer as broken.** It works; it is aimed at AI prose
  tics and continuity, which is a different theory of quality than the showrunner now
  holds. It is stale, not wrong.
- **`HANDOFF-story.md` is a live separate stream** and was not touched. If the direction
  above is adopted, that stream's migration work (19 findings on book 01) may become moot —
  check before spending a session on it.
- **Terse replies from the showrunner are decisions**, and they reverse an earlier answer
  when they see further. Take the update; do not relitigate.

---

# Session append — 2026-08-11/12 | Type: build (engine changed, tests green)

> **Stream note.** This session was the story-layer build, not the strategy stream above.
> It cleared book 01's story findings, produced a chapter cut plan (still unapproved), and
> shipped one engine feature. **Nothing in the direction analysis above was actioned, and
> nothing above is superseded by this.**

## What happened, in order

1. **Book 01's story findings went 19 → 0.** The 14 `unknown-clue` findings were fixed by
   adding the missing entries to `series/whodunit/book-01.yaml` (11 to `clue_schedule`,
   3 to `red_herrings`) — the sub-clues (`c02a`, `c10b`…) and three red herrings existed
   only as story.md tags. The 4 `unknown-job` findings and the unclosed questions were
   fixed by the showrunner directly.
2. **The mystery lock was re-minted** and now carries an `outline_sha256`, clearing the
   `?` that `/book-status` had been showing for a missing fingerprint.
3. **The plot stages were re-stamped.** All six upstream stages read `stale` purely from
   drift, not missing work — `plot_stage.py status` said `next: premise`, which would have
   walked the workshop from the top and **overwritten a 150-beat story.md at the chapters
   stage.** Re-stamping top-down (each stamp rewrites its target's frontmatter, so order
   matters) walked `next:` forward to `cut`. `woven: true` was set on story.md.
4. **A cut plan was proposed** by `chapter-cutter`, rejected once by the showrunner, and
   reworked. It is at `input/book-01/cut-plan.proposed.md` — deliberately NOT at
   `cut-plan.md`, which is what the cut consumes and must hold only an approved plan.
5. **Beat numbers shipped** (branch `story-beat-numbers`, commit `e58c60f`, pushed).

## The engine change

`- [12] Maggie throws the cup…` — optional, all-or-nothing per file, stripped from the
prose, verified by `check_story`. Position stays the truth; the number is a checkable
claim about it. Findings: `misnumbered-beat`, `unnumbered-beat`. Tool:
`story_cut.py number NN`. Files: `penny_story.py`, `story_cut.py`, `tests/test_story_cut.py`,
plus `README`, `CLAUDE.md`, `writing-beats.md`, `plot-book.md`, `story-author.md`,
`chapter-cutter.md`. **971 tests pass** (was 962 in the session above).

**Why it exists.** A cut plan's `Beats: 22-25` is positional, so one inserted beat hands a
chapter its neighbour's work — ranges stay contiguous, stay plausible, and nothing catches
it. Book 01 has **225 bullets against 150 beats**, because `## Questions`,
`## Chapter Direction` and `## Guardrails` bullets are not beats. The cutter's file-order
counting survived only because those three blocks sit at the bottom of the file.

## Open decisions on book 01 — none of these are settled

- **Track letters are undefined.** The genre pack declares `M, P, R, B` and
  `max_dark_gap: {M: 2, P: 4, R: 4, B: 5}` but never says what they mean. The cutter read
  them as Mystery / Personal / Relationships / Business and **every track row in the cut
  plan assumes that**. Consistent with the gap values; still inference. Unanswered.
- **The old `outline.md` must be deleted for the cut to run** — it carries no
  `cut_output_sha256`, so the cut refuses `outline-modified-since-cut` rather than
  discarding hand-authored work. Not done; it is the showrunner's call. It has zero
  coverage of the stalker, Elspeth, Pruitt or the Dot-and-Glad tin, so it describes a book
  that no longer exists.
- **`act_pivots` in the ledger need III and IV re-stamped** (14-21 → 15-20, 22-28 → 21-28).
  Act I now matches at 1-4 after the ch 1 rework.
- **Ch 3 carries no B row by decision**, to bring it to 15 against the cap. Safe:
  `starved-thread` fires only ABOVE `max_dark_gap`, and B's is 5.
- The showrunner has NOT approved the cut plan.

## Watch out for

- **`plot_stage.py status` will tell you to re-plot a finished book.** Stale stamps and
  missing work are indistinguishable in its output. Read what is on disk before entering
  the stage it names — `next: premise` here meant "stamps drifted", not "no premise".
- **`chapter-cutter`'s audit tables over-claim.** It listed 11 de-flag fixes; only those
  inside chapters it actually reworked were real. For ch 5, 8, 10, 12 and 13 it described
  the fix it *would* make without applying it. Verify against the text, not the summary.
- **The clue `plant_chapter` values in the ledger are provisional.** The cut rewrites them
  all from the beat→chapter mapping (`_rewrite_plant_chapters`, both collections). Do not
  hand-tune them before the cut; that work is discarded. This was learned by doing it.
- **`lock-mystery` runs AFTER the cut**, per `story_cut.main`'s own comment. It was run
  before the cut this session, which is backwards — the resulting lock is provisional and
  goes stale the moment the outline is rebuilt.
- **Keep the three inert blocks at the bottom of story.md.** Numbering and beat indexing
  both walk the file in order; a `## Guardrails` block between acts would silently shift
  every later index.
- **`HANDOFF-direction.md` (this file) is still untracked** and was not committed with the
  beat-number work — it is unrelated to that branch.

---

# Session append — 2026-08-12/13 | Type: brainstorm → spec → plan → build (shipped, merged to main)

> **Stream note.** This session was a feature build requested mid-stream, not the
> strategy work above. **Nothing in the direction analysis was actioned and nothing
> above is superseded.** The five options are still unchosen, the PRD's Goals and
> Success Metrics are still stale, and Gate 3 — *would this person do this* — is still
> unbuilt and still the highest-value thing in the record.

## What shipped

**Where a chapter happens, and how it opens and closes, are now cut-level decisions.**
`cut-plan.md` gains three authored fields, `chapter-cutter` proposes them, the showrunner
approves them, and the cut emits them:

```markdown
- **Setting:**
  - 22-23 — the pottery studio, late afternoon
  - 24-25 — the harbour road, dusk, rain coming in off the water
- **Opening:** The kiln door still warm and the studio empty behind her.
- **Closing (promise of action):** She pockets the tin and turns for the harbour.
```

Spec `docs/superpowers/specs/2026-08-12-chapter-setting-and-frames-design.md`, plan
`docs/superpowers/plans/2026-08-12-chapter-setting-and-frames.md`. 21 commits, merged to
`main` at `370208f`. **1018 tests pass** (was 978).

**The design decisions that are not obvious from the code:**

- **Setting is bound to beat ranges, not a bare ordered list.** A bare list would move the
  *place* upstream and leave the *transition point* — when they leave the studio — with the
  drafter, which is the decision the whole change exists to move. The ranges use the same
  positional numbers as `Beats:`, so `misnumbered-beat` already guards them.
- **Setting is cut-level, not a fifth beat sigil.** Working out where scenes happen is part
  of working out how beats group into chapters; a beat tag forces it before the information
  exists, and puts 150 more tags in a file whose value is having no surface for boilerplate.
- **The closing carries a named kind** (`cliffhanger` / `irony` / `promise of action`) in
  its key rather than its prose, so a script can see it. That is what makes
  `monotonous-closings` possible — a run of identical endings is a book-level fact no
  per-chapter check can see.
- **The opening is craft guidance only.** An earlier draft had it name "the previous
  relevant chapter" and feed the `Because:` wiring; that was cut. `Because:` is unchanged.
- **Adoption is all-or-nothing per cut plan**, as beat numbers are per `story.md`. Checking
  chapters independently would make a half-adopted book the quiet default — the chapters you
  filled in governed, the rest silently returning the ending to the drafter. Book 01's
  existing proposed cut plan still runs untouched.

`story_cut.py` gains five unwaivable findings; `tension_check.py` gains `monotonous-closings`
(waivable, threshold from the genre beat sheet's `closings.max_same_kind_run`).
`config/story-craft/writing-chapter-frames.md` is the new craft doc the cutter reads.

## Three defects found on the way, all pre-existing

These matter more than the feature, because each had been shipping silently.

1. **The "blind" fan read has not been blind since 2026-08-04.** The reader's copy used a
   denylist, the chapter-direction feature added `### Guardrails` to every chapter block,
   nothing added it to the list, and the copy began shipping **the culprit, the identity
   twist and the motive from chapter 1**. `### Clues and Plants` and `### Character
   Knowledge` leaked the same way. Now an allowlist — a new section is invisible until
   deliberately admitted. **Every fan-audit finding taken before this date was produced by a
   reader who could see the solution**, which is worth weighing against Finding 2 in the
   analysis above.
2. **The allowlist conversion then over-corrected**, dropping `### Required Beats` and
   leaving the fan roughly one line per chapter (book 01: 135KB → 20KB). Showrunner ruled
   this session: **re-admit Required Beats only**; Chapter Purpose and Starting/Ending State
   stay out as machinery.
3. **CLAUDE.md had understated `story_cut.py` since `e58c60f`.** It said sixteen findings;
   the real number was eighteen, because `unnumbered-beat` and `misnumbered-beat` were
   documented in a separate paragraph and never folded in. Now **twenty-three**, all
   enumerated. The roster test never caught it because it only checks listed→source, never
   source→listed.

Also fixed: `_item_spans` could not find ledger items in a `yaml.safe_dump`-shaped sequence,
so `_rewrite_plant_chapters` reported every clue as not-found and the cut refused a partial
update — while the ledger still validated and locked. And the cozy track letters M/P/R/B are
now defined (`R` is **Romance**, not relationships-in-general — read as the latter it becomes
a second community track and the romance thread starves while every row still looks full).

## Watch out for

- **The plan's Step-5 verification grep is a broken instrument.** It misses findings raised
  as plain string literals rather than f-strings, and falsely matches `book:` and the
  notes-channel advisory. Its two errors cancelled to exactly the wrong number and looked
  like confirmation. Do not reuse it; enumerate by reading `check_story`, `main`,
  `recut_refusal` and `expand_in_place_refusal`.
- **`tests/test_readme_check_count.py` only checks listed→source.** A finding added to the
  code and not to the docs still passes. That is how the count drifted for a month.
- **Four of the five review findings this session were defects in the plan, not the
  implementations.** The subagents transcribed faithfully; the reviewers are what stopped
  bad instructions shipping. Budget for review, not for implementation.
- **Book 01 is still uncut.** Its `cut-plan.proposed.md` is unapproved, its stale unstamped
  `outline.md` still has to be deleted by hand before the cut will run, and `act_pivots`
  still need re-stamping. None of that moved this session.
- **`main` is pushed as of this session; `origin/story-beat-numbers` is stale** and can be
  deleted whenever.
- Minor findings shipped un-fixed by triage: an inline (non-nested) `Setting:`, a hyphen
  where the em dash is required, and a `Closing:` with no kind each produce a *loud but
  mis-named* finding — the repair they name is not the repair you need. `CLOSING_KINDS` is
  an engine constant while its threshold is genre-resolved, which will want a `[DECISION]`
  when the thriller pack lands.

---

# Session append — 2026-08-13 | Type: diagnostic → brainstorm → spec → plan → build (shipped, merged, pushed)

> **Stream note.** Another feature build requested mid-stream. **Nothing in the direction
> analysis above was actioned and nothing above is superseded.** The five options are still
> unchosen, the PRD's Goals and Success Metrics are still stale, and Gate 3 — *would this
> person do this* — is still unbuilt and still the highest-value thing in the record.

## What started it

The showrunner asked how the setting/background config is actually consumed. Tracing it
found two failures pointing opposite ways:

- **`config/setting-pack/coastal-victoria-au.md` is stale by two names.** 837 bytes, last
  edited 8 July, describing a town called **Wreckers Bluff** and a protagonist called
  **Cora**. The series is Pelican's Crook and Maggie. Five consumers read it.
- **`input/series/town-and-character-history.md` is read by nothing.** 72KB, edited 11
  August, actively maintained. Zero references in `scripts/`, `commands/`, `agents/`.

So the file that was wrong was wired in, and the file that was right was orphaned.
`readiness_check.py` reported READY and was correct to — it verifies a setting `*.md`
exists, never what is in it, because the engine is location-agnostic by rule. **No
deterministic check can catch this class of drift**, which is why the fix had to be
making the pack *derived* rather than adding a checker.

Also found, unfixed: **`input/book 01/materials.md`** — 42KB, directory name uses a
**space** not a hyphen, so nothing reads it (`plot_stage.py` looks in `input/book-01/plot/`).

## How the setting pack actually reaches agents (the answer to the original question)

Two mechanisms, and it travels by the weaker one.

| Stage | Reads it? | How |
|---|---|---|
| `story-author`, `plot-proposer`, `mystery-planner` | **No** | — |
| `chapter-cutter` | Yes | named in `Inputs:`, agent reads it itself |
| **`packet_assemble.py`** | **No** | setting is not in the packet |
| `map-maker` | No | reads the packet only |
| `drafter` (Claude) | Yes | named in `Inputs:` |
| `drafter` (LM Studio) | Yes | pasted into **every scene prompt**, 2,500-char cap |
| `developmental-editor` | Yes | via `developmental-craft.md:30` |

**The packet does not carry setting.** The drafter gets it only because its agent file says
to go read it — an instruction, not a contract. That asymmetry is why the new layer puts
background *entries* in the packet but deliberately leaves the *pack* a direct read.

## What shipped

**The background-history source layer.** One authored series-level document,
`input/series/background-history.md`, cut deterministically into a flat
`series/continuity/background/` plus a derived `config/setting-pack/setting.md`.

Spec `docs/superpowers/specs/2026-08-13-background-history-source-layer-design.md`, plan
`docs/superpowers/plans/2026-08-13-background-history-source-layer.md`. 12 commits, merged
to `main` at `130b0ac`, **pushed**. **1070 tests pass** (was 1018).

Eight blocking findings — `missing-stance`, `unknown-section`, `unknown-entry-depth`,
`duplicate-entry`, `malformed-relationship`, `unslugged-entry`, `unstamped-target`,
`target-modified-since-cut` — no waivers. Two advisories: `orphan-derived`,
`stale-setting-pack`.

Documented at `3aa0f9a`: README gains a **"The background layer"** section between series
setup and book plotting (series-scoped, so it sits outside the per-book parts) covering the
heading contract, why `## Stance` is authored, the findings, what the cut never writes and
whose those files are, and a consumption table. That commit also fixes a contradiction the
layer introduced — `config/setting-pack/setting.md` was listed under "you must create the
rest" while being derived.

## The design decisions that are not obvious from the code

- **The `## Stance` block is authored, not compressed — and that is what removes the LLM
  from this layer entirely.** The setting pack is loaded every chapter and truncated at
  2,500 chars, so no verbatim slice of fourteen town-history sections fits. An earlier
  draft had an agent compress it behind an approval gate. **Both were cut.** Approval
  exists in this engine only where a generated artifact would be mistaken for a decision;
  a compressed pack is a lossy *view* of a decision already made in the source, so a gate
  bought nothing and added showrunner touch on every re-cut. But removing the gate left
  what the gate covered for — silent lossy compression, the same failure class as the
  2026-08-04 fan-read leak. **So the compression was removed instead of gated.** Same move
  as `## Questions` in `story.md`: the author writes it once, the machine copies it.
- **Background gets its own directory rather than a section inside `characters/`.**
  `ledger-updater` already writes those files after every finalized chapter, so a re-cut
  would clobber its accumulated record. Separate homes is the only option under which
  re-cutting stays free forever, and it keeps the two kinds of knowledge distinct:
  background is what the showrunner decided, the ledger is what the books put on the page.
  When they disagree that should be visible, not silently resolved by whoever ran last.
- **Flat, not nested.** `packet_assemble.py` walks a fixed subdir allowlist with a flat
  `*.md` glob, so `background/characters/…` would have been invisible. `kind` lives in the
  `canon-meta` header instead of the path.
- **`## Secrets` never touches the whodunit ledger.** That ledger is per-book and gets
  sealed; the background is series-level and never freezes. Background says what is true;
  the ledger says what this book plants and when. Accepted cost: renaming a secret does not
  check that book-01's ledger still agrees.
- **`unslugged-entry` was added as an eighth finding against the plan's own "seven, do not
  add an eighth" constraint.** A `###` title of pure punctuation or non-Latin script slugged
  to `""` and the entry *vanished silently with exit 0*. It was not folded into
  `malformed-relationship` because a Town or Secrets entry would then report a relationship
  defect — the mis-named-finding lesson from 2026-08-12.

## Two pre-existing defects found on the way

1. **`penny_meta.parse_canon_meta` truncated multi-element lists.** It split its header on
   bare commas, so `links: [a, b]` parsed as `[a` and the rest was lost. Only
   single-element lists had ever been exercised. `_split_top_level` already existed for
   exactly this and is used by `parse_canon_sections`. Fixed (`f62fb3b`).
2. **My own spec §8 was wrong and the final review caught it.** It claimed the cut would
   *refuse* the stale `coastal-victoria-au.md`. It never could — `target_refusal` only sees
   paths the cut is about to write. Meanwhile `lmstudio_draft_chapter.py` concatenates
   **every** `*.md` in `config/setting-pack/` into the prompt, so the stale town kept
   reaching the drafter. Now named by the `stale-setting-pack` advisory.

## Series work (separate repo, pushed)

**Elspeth has a continuity entry** — `series/continuity/characters/elspeth.md`, commit
`b2f9659`, pushed. She is named 11 times in `story.md` and had none, so nothing loaded for
her. Facts extracted from `series-bible.md`, the town history and her own beats; nothing
invented. Verified against the real slice: naming her pulls George, Lisa and Tara/Marion.

**Her header is the `canon-meta` comment form, unlike her eight frontmatter siblings** —
see the next section for why that matters.

## Watch out for

- **One-hop linking has never fired for any of the eight original characters.** They use
  YAML frontmatter; `packet_assemble` reads entries with `parse_canon_meta`, which only
  recognises the comment form, so their `links:` is invisible. It is dead config that looks
  live. `elspeth.md` is currently the only character in the series whose links work.
  Converting the other eight is mechanical and would make the graph live for the whole cast
  — deliberately out of the spec's scope, not done.
- **`built_from_background` is a stamp with no reader.** Every other `built_from_*` in the
  engine has a gate (`map_check`'s `stale-map`, `packet_assemble`'s `stale_packets`,
  `plot_stage`'s stage staleness). This one does not, so a derived tree that has fallen
  behind an edited source is invisible: you would draft against a version of the background
  you had already replaced, with every artifact looking healthy. Re-cutting after an edit is
  discipline, not enforcement. Cheapest real fix is a `/book-status` row, **not** a
  `preflight draft` refusal — a background edit should not be able to block a draft.
- **The series migration has NOT been done.** `background-history.md` does not exist yet;
  the file is still `town-and-character-history.md`, still has no `## Stance`, and the
  headings are not yet conformed. `coastal-victoria-au.md` is still on disk and still
  reaching the LM Studio drafter. Spec §8 has the four steps.
- **`input/book-01/cut-plan.proposed.md` is still uncommitted** in the series repo — the
  showrunner's own in-progress editing, untouched this session.
- **`HANDOFF-story.md` is badly out of date** — it says book 01 has 19 blocking findings
  (cleared) and `story_cut.py` has sixteen (it has twenty-three). Read it as history only.
- **Nothing in the direction analysis at the top of this file has been actioned**, and three
  build sessions have now been appended beneath it. That gap is itself worth a decision.
