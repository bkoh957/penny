# Cozy ideation portaprompt — design

Date: 2026-07-10
Status: proposed

## Problem

A new cozy-mystery series is being ideated. Its raw material is a **collaborative chat
transcript** with a non-Claude model. Most of the book was worked out inside that chat,
not in the writer's head — so the transcript does not under-supply, it **over-supplies**:
competing versions of the same beat, branches tried and abandoned, ideas the model
proposed that were never ruled on.

What the writer brings is taste. They know which parts are good; they do not necessarily
remember which parts are in there. Consolidation is therefore an act of **selection**, not
of extraction.

There is no path from that state into Penny. The pipeline's first door —
`/scaffold-book NN <outline-path>` — requires an outline that already exists.

Book 1 of Pelican's Crook was authored by hand across several models (Hermes → ChatGPT →
Claude), iteratively, steered by gut feel. `input/book-01/` contains only `outline.md`
and no skeleton: `/expand-outline` was built and never used. The gap is upstream of every
existing command.

## Goal

A **portable prompt** — a markdown file the writer pastes into whatever model they are
ideating with — that consolidates a collaborative transcript, via an adjudication pass,
into an `outline-skeleton.md` conforming to the shape `outline_check.py` gates and
`/expand-outline` consumes.

## Non-goals

- No engine surface. No new command, no script, no test. Nothing in `scripts/`,
  `commands/`, or `agents/` changes.
- Not a replacement for `/expand-outline`. The portaprompt stops at the skeleton; the
  engine inflates it.
- Not a quality or fairness check. `outline_check.py` verifies shape only.

## Artifacts

| Path | Role |
|---|---|
| `genres/cozy-mystery/archetype.md` | Reference lens. The archetypal cozy framework, incl. the §17 beat sheet. |
| `genres/cozy-mystery/ideation-prompt.md` | The portaprompt itself. Pasted, never loaded. |
| `<new-series>/input/book-01/outline-skeleton.md` | Emitted. Feeds `/scaffold-book`, then `/expand-outline`. |
| `<new-series>/input/book-01/ideas-carryover.md` | Emitted. Unstructured texture, archetype deviations, and a `## Roads not taken` section holding every rejected variant. |

Both engine-side files live in the genre pack because their content is cozy-specific.
The genre/location-agnostic rule forbids them in `scripts/`, `commands/`, or `agents/`.

### Why no `genre.yaml` key

`penny_genre.MANIFEST_KEYS` is `(genre, conventions, planning, inspectors, gates, rubrics,
tracks)`. `validate_manifest` checks each is *present*; it tolerates extra keys but there
is no accessor for them. Adding `archetype: archetype.md` would be decorative — a key
nothing reads. Omit it.

Note that **nothing in the engine reads `conventions.md`'s contents either**; only its
existence is validated. Genre-pack prose reaches an agent only when a command or agent
cites it explicitly. `archetype.md` is therefore a file the *portaprompt* cites, not a
file the engine loads.

## Output contract

The skeleton must satisfy the four predicates in `scripts/outline_check.py`:

1. `outline-frontmatter` — `book` and `total_chapters` present and integer-valued.
2. `outline-solution` — at least one `## Solution` heading; if a `:` label is present it
   must be non-empty. Use `## Solution: the-central-mystery`.
3. `outline-chapters-contiguous` — `## Chapter NN` headings form exactly `1..total_chapters`.
4. `outline-nonempty-beats` — no chapter block with an empty body.

Beyond the checker, matching what `/scaffold-book` and `/expand-outline` consume:

- `## Threads` — one line per strand, naming the promise it opens and where it pays off.
- Per chapter: `### Chapter Summary`, `### Chapter Structure` (Start-Desire /
  Pressure-Obstacle / Turn-Change / Texture / Hook), `### Track Movement` over the cozy
  pack's declared `tracks: [M, P, R, B]`.

This is the shape of the shipped `config/outline-template.md`. The template is not a
lesser version of book 1's outline — it is the skeleton format. Book 1's 4,261-line
scene-breakdown is what `/expand-outline` produces *from* that shape.

### Verification

Run from the series root, against a checkout of the engine. `${CLAUDE_PLUGIN_ROOT}` is not
set here — the writer runs these by hand, outside a runbook.

```bash
python3 <penny-repo>/scripts/outline_check.py input/book-01/outline-skeleton.md
grep -c '^### Scene ' input/book-01/outline-skeleton.md   # must be 0
```

## The four phases

Phase order is the design. A foreign model's failure mode is eagerness: given a transcript
and a format it will emit a complete, plausible skeleton in one pass. Against a
*collaborative* transcript the dominant error is not invention but **silent selection** —
it picks one of the chat's own five versions and the other four vanish. The output looks
like the writer's material because it *is* their material, just not the version they would
have chosen. A second-order trap: a summarizing model treats the **last** version of an
idea as the decided one, when in a brainstorm the last version is usually only the last
one tried.

**A — Salvage, not synthesis.** Read the transcript. Produce three lists — *candidates*
(every substantive idea, each marked `sole` / `competing` / `unresolved`, where
`unresolved` means the other model proposed it and the writer never replied),
*contradictions*, and *gaps*. Decide nothing. The question list comes from `archetype.md`:
the enclosed world and its routines (§1), the sleuth's non-police reason to see truth
(§2), the victim as pressure point with a public and a private story (§3), the suspect
circle where not every secret is murder-related (§5), the sounding board (§6), the police
boundary (§7), the midpoint change of shape (§10), the killer's benign-trait misreading
(§14), the ordinary-task epiphany (§13).

**B — Adjudication, one item at a time.** Contradictions first, then competing candidates,
then unresolved ones, gaps last. Rival versions are presented side by side in the
transcript's own words; the writer chooses; the model records without improving.

The model **may state a structural consequence** of a choice ("B leaves the Personal track
without a want") and **may not state an aesthetic preference** between the writer's own
versions ("B is stronger"). The line is exact and mirrors this repo's existing one — the
deterministic layer may ask *is this a string*, never *is this prose a recommendation*.
Machinery is analysable; taste is the thing the writer brought.

Only for genuine gaps does the model propose, and where a gap belongs to the core it
offers options with no preference at all. This mirrors `/plan-mystery`, which reserves
"who did it, why, the central deception, and any series-arc constraints" as the
irreducibly human taste-and-strategy layer.

The core it must come away holding:

- culprit, victim, central deception
- the moral engine — the sentence explaining why reader and sleuth both believed the wrong
  thing. Book 1's: a mercy mistaken for a murder; Mary is right that the death was no
  accident and catastrophically wrong about what it meant. Hardest thing to pin down,
  because a collab transcript rarely states it once — it is smeared across a dozen
  messages, and no single sentence in the chat says it.
- suspects, key locations
- the protagonist, and separately what she wants that has nothing to do with the murder —
  that want is the P track
- the four tracks' promises and payoffs → `## Threads`
- `total_chapters`, the reveal chapter, the act breaks
- the beat→chapter allocation (see below)

**C — Read-back and approval.** Restate the core in the writer's words, plus the archetype
deviations and a **Roads not taken** section listing every rejected variant and what it
would have changed. That section is the proof that no silent selection occurred: if it is
empty, either the transcript held no rivals or the model failed to surface them, and it
must say which. Stop. Nothing is written until approved. This is the gate that catches an
invented or mis-selected culprit before it is laminated into 27 chapter summaries; no
checker can catch that.

**D — Emit.** One fenced block per file. No `[GAP: …]` marker survives into output — if
something is unresolved at emit time, stop and ask rather than paper over it. Then print
the verification commands.

## The framework as a lens, not a checklist

The writer's instruction is that the framework be *loosely compared to*, not conformed to.
A model handed an 18-section framework will otherwise treat it as a compliance checklist
and sand the book to the median.

- Deviations are **recorded, never resolved.** They go into `ideas-carryover.md`, keeping
  the skeleton pure story and the meta-commentary out of `/scaffold-book`'s way.
- The framework never overrides the core. Where transcript and framework conflict, the
  model reports the tension and stops. Book 1's Neil is mourned as a saint, against §3's
  "disliked by several people." That deviation is the entire book.

### Beats are not chapters

`archetype.md` §17 is a **beat sheet** with 27 entries. Book 1 has 27 chapters. The
coincidence is enumerative. Mapping beat *n* to chapter *n* makes every book in a series
structurally identical.

So the beat→chapter allocation is an explicit Phase B output, not something read off the
sheet. `total_chapters` comes from the writer. Chapters carrying no beat are legitimate,
and in a cozy they are where the food and the gossip live.

## Distribution

The portaprompt runs in a model that cannot read the repo, so `archetype.md` must travel
with it. **Two paste blocks** (prompt, then framework, then transcript) rather than a
framework embedded inside the prompt. An embedded copy is a duplicate that will drift —
the same bug class that forces `agents/outline-reviewer.md` and `commands/review-outline.md`
to be pinned byte-identical.

## Failure modes the prompt is written against

| Failure | Defence | Caught by |
|---|---|---|
| **Silent selection** among the chat's own rival versions | Phase A marks every candidate `sole` / `competing` / `unresolved`; Phase B surfaces rivals side by side; Phase C's *Roads not taken* enumerates the rejects | Nothing automatic. The read-back is the only gate, and it is the dominant failure mode for a collaborative transcript. |
| Treating the transcript's **last** version as the decided one | Hard rule: recency is not a decision unless the writer said so in words | Nothing. |
| Carrying forward an idea the other model proposed and the writer never answered | Phase A's `unresolved` status; the prompt states that silence is not assent | Nothing. |
| Scene blocks in the skeleton | Explicit prohibition | `grep -c '^### Scene '` → 0. `/expand-outline` skips any chapter already containing one, silently disabling the expander for exactly the chapters the model liked best. |
| Invented culprit | Phase C read-back gate | Nothing. No script can detect this. |
| Plant/payoff chapter numbers in the solution block | Prohibition: skeleton states the *solution*, `series/whodunit/book-NN.yaml` states the *schedule* | Nothing at authoring time; `fairplay_check.py` later, against the derived yaml. This is the live drift class — `mystery-solution.md:33` says ch 9/20, `book-01.yaml:16` says 11/23, and the lock certifies the yaml. |
| Chapter-count drift in prose | Derive every in-prose chapter reference from `total_chapters` | **Not** `outline_check.py`, which checks heading contiguity, not prose references. Book 1's 27-vs-28-vs-29 bug was caught only by `/review-outline`'s independent panel (`OF-7` + `OF-13`). |
| Frontmatter that parses wrong (`total_chapters: 27 chapters`) | Stated as integer-valued | `outline_check.py` predicate 1, loudly. |

**Honest limit:** `outline_check.py` verifies shape, never quality or fairness. A
structurally perfect skeleton with a solution no reader could deduce passes cleanly.
Fairness is checked later by `fairplay_check.py` against the derived yaml; craft by
`/review-outline`. The portaprompt buys a well-formed starting point, not a good book.

## Downstream chain

1. Portaprompt → `input/book-01/outline-skeleton.md` (+ `ideas-carryover.md`)
2. `/scaffold-book 01 input/book-01/outline-skeleton.md` → derives
   `series/whodunit/book-01.yaml`, thread files, canon-core updates, and the sealed
   `output/book-01/mystery-solution.md`; emits a dry run of the lock. `--approve` mints it.
3. `/expand-outline 01` → inflates each chapter to scene-breakdown depth. Context-rich:
   reads the sealed solution, schedules clue beats, never stages the reveal before
   `reveal_chapter`.
4. `/review-outline 01` → the independent Claude+Codex panel.

Note step 2 must precede step 3: `/expand-outline` aborts without a sealed solution.

## Incidental fix

`genres/cozy-mystery/conventions.md` declared the B-plot as "the protagonist's post-divorce
sea-change, threaded across all 13 books" — Pelican's Crook leaking into the genre pack,
three lines above that file's own instruction to keep series-specific detail in the series
folder. A second cozy series would silently inherit it. Replaced with a genre-general
statement.

## Open question

The new series folder does not exist yet, and `/new-series` scaffolds the directory
contract only — no `series.yaml`, no config packs. A freshly scaffolded folder is not
runnable: `readiness_check.py` requires a run-config, voice pack, setting pack, genre
prose pack, length profile, and beta personas that the engine does not ship. The
portaprompt's output can be written into `input/book-01/` before any of that exists, but
`/scaffold-book` cannot run until `series.yaml` declares `genre: cozy-mystery`. Sequencing
this is out of scope here.
