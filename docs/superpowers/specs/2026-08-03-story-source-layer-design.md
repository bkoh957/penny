# `story.md` — the source layer, and the cut

Date: 2026-08-03
Status: design, approved in conversation
Supersedes: `2026-07-31-layered-outline-workshop-design.md` §3.1, §3.3, §7 — settles what
that document deliberately left open. §4's four passes and gates are **not** built here.

---

## 1. The defect

`outline-skeleton.md` was supposed to be the small, editable layer above `outline.md`.
It is not, and book 01 shows why.

Measured on book 01 (2026-08-03):

| | skeleton | outline |
|---|---|---|
| bytes | 58,304 | 92,005 |
| chapters | 30 | 28 |
| bytes/chapter | 1,943 | 3,286 |
| `###` sections per chapter | 10 | 11 |

The skeleton is not an abstraction of the outline. It carries **the same section
headings in the same order** — Chapter Purpose, Starting State, Ending State,
Reader-Facing Shape, Required Beats, Clues and Plants, Character Knowledge, Guardrails,
Chapter Structure, Track Movement — with thinner sentences under each, plus its own
repeated boilerplate ("The prior open questions remain live unless this chapter closes
them").

**Same shape means the same cognitive task.** Reviewing 30 skeleton blocks is not
materially easier than reviewing 28 outline blocks, so the layer bought nothing; and
because nothing about the format resists growth, it grew. This is the general lesson and
it governs the rest of this document:

> A source layer earns its place only by being a **different representation**, not a
> shorter one. If it can be arranged into the same form as its artifact, it will drift
> into a duplicate of it.

Drift then arrived exactly as predicted. Book 01's two files disagree on chapter
*numbering*, not merely count — "Simon Behind the Desk" is chapter **07** in the skeleton
and chapter **05** in `outline.md` — and every wiring reference in the skeleton points
somewhere else as a result. Its guardrails still read *"Do not name Tara as culprit
before Chapter 26"*, the stale reveal; the canonical outline reveals at **24**. The wrong
number is baked into 30 blocks.

## 2. Scope

**In scope:** the source layer and the cut. `story.md`'s format, where it sits in
`/plot-book`, the agent that proposes chapter boundaries, the deterministic emitter that
writes `outline.md`, and the staleness rule that protects hand-shaped chapter work.

**Out of scope, deliberately:** the four passes and their four gates
(`2026-07-31` §4). Those need their own spec. The showrunner authors `story.md` the way
they author the existing plot save points — in conversation, with the machine's help —
and no new gate, pass, or reviewing agent is introduced here.

The reasoning for that split: the workshop's value is Gate 3 (*would this person do
this*), and that question can already be asked of the shipped strand views the moment
strands exist. Building the source layer first delivers the editable source, and tells us
what the passes must carry before commands are committed to them. This is the same
argument `2026-07-31` §9 made for building the diagnostics first, which held.

## 3. `input/book-NN/story.md`

Beats in **story order**, one per bullet, prose first, tags trailing.

```markdown
---
stage: story
book: 02
built_from_turning-points: <sha256>
built_from_whodunit: <sha256|none>
---

## Act I

- Maggie chooses this life: the gallery, the commission call with a closing
  date, the studio she just took over.
  @maggie #establish-protected-world

- Lisa is found dead in the studio Maggie just took over.
  @lisa @maggie #crime-and-first-contradiction

- The handover appointment was altered — in Maggie's name.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered-appointment
```

### 3.1 The vocabulary

Four sigils, and nothing else:

| sigil | means | validated against |
|---|---|---|
| `@strand` | this beat belongs to a character's line | slug contract, below |
| `#job` | this beat answers a structural job | the active genre's job list |
| `+question` / `-question` | opens / closes a dramatic question | internal consistency |
| `!clue-id` | a ledger clue is planted here | `series/whodunit/book-NN.yaml` |

`##` headings are for the author's reading and carry **no meaning to the parser**. This is
deliberate: the moment a heading means something, the file has a form to arrange, and
arranging a form is what turned the skeleton into a duplicate.

A beat with no tags is legal. A beat is prose first.

### 3.1.1 Question prose lives in one block

A `+q-id` tag carries only an id, but `outline.md`'s wiring lines carry **id — prose**
(`- **Opens:** q-clear — how can Maggie clear herself without performing panic?`), and
`penny_wiring.split_id` expects that shape. Repeating the prose at every mention is how
boilerplate got into the skeleton, so it is written once, in a single `## Questions` block
anywhere in the file:

```markdown
## Questions
- q-clear — how can Maggie clear herself without performing panic?
- q-main — who killed Lisa?
```

This is the one heading the parser does read, and it holds no beats. Question ids obey
`penny_wiring.QID_RE` (`^q-[a-z0-9][a-z0-9-]*$`) so the emitted wiring is parseable by the
checker that already validates it. A `+`/`-` tag naming an id absent from this block is
the `unknown-question` refusal (§8).

`@strand` ids obey `^[a-z0-9][a-z0-9-]*$` — the slug contract already imposed on
`alibi_grid` suspects, and for the same reason: strand ids become filenames on the strand
pages, so the constraint is a path-traversal guard, not a style rule.

`#job` ids resolve through the **active genre**, via `genre.yaml`, the same indirection
`beat_sheet:` already uses (`penny_genre.py`). No cozy filename appears in engine code.

### 3.2 Why this shape cannot become the skeleton

The skeleton could hold everything a chapter block holds, so eventually it did.
`story.md` cannot, because there is nowhere to type the other sections — they have no
syntax. What the author writes is what only the author can decide: **what happens, in
what order, to whom**, plus **which questions open and close**, which is a taste call no
ledger holds. Everything else is a consequence and is computed at cut time (§5).

The cost is accepted: derived sections are not editable at the story level. A Character
Knowledge line you disagree with is fixed in `outline.md` after the cut, or in the ledger
it came from.

## 4. Where it sits in `/plot-book`

Seven stages today: `premise → ending → turning-points → counterplot → chapters → weave
→ readback`.

`story.md` replaces **`chapters` and `weave` only**.

- `premise`, `ending`, `turning-points`, `counterplot` are unchanged. They are small, they
  hold the showrunner's taste calls, they work, and the `built_from_*` fingerprint chain
  between them is what reports staleness.
- `chapters` stops writing `outline-skeleton.md` and writes `story.md`.
- `weave` folds into `chapters`. Strands and questions are tagged inline as the beats are
  written; there is no second pass to bolt wiring on.
- A new `cut` stage produces `outline.md` (§5).
- `readback` is unchanged in substance and **runs after the cut, against `outline.md`.**

  **Correction, found in implementation.** This section first said the read-back would read
  `story.md` before the cut and `outline.md` after it. That is unimplementable as written:
  `readers_copy_text` is chapter-indexed, and a pre-cut `story.md` has no chapters at all.
  Left as specified it fails two ways — silently writing a near-empty reader's copy at exit 0
  when the ledger has no `reveals:` block, and hard-exiting on every reveal when it does.
  The reader's copy is cut from chapters, and chapters exist only after the cut.

  `_readback_source` therefore returns `outline.md` whenever it exists — covering a cut book
  and a legacy hand-authored one alike — and **refuses by name** when only `story.md` exists,
  rather than returning a file that cannot produce a valid copy. Making the read-back
  beat-indexed instead would be the four-pass workshop rebuild, which §2 puts out of scope.

  **Correction to `2026-07-31` §3.3 and §8.1**, which recorded `readers-copy`'s
  hard-requirement on the skeleton as a live defect. It was fixed in the 2026-08 views
  stream and is not outstanding. `_readback_source()` (`plot_stage.py:571`) now prefers
  the skeleton *while it exists* and falls back to `outline.md`. Because it resolves its
  first choice through `stage_paths(book, root)["chapters"]`, pointing that key at
  `story.md` redirects the read-back with no further change — the work here is deleting
  the now-dead skeleton branch and its comment, not repairing a defect.

`stage_paths()` and `_UPSTREAM` in `scripts/plot_stage.py` change accordingly:
`"chapters"` and `"weave"` both point at `story.md`; `"cut"` points at `outline.md` with
upstream `["chapters", "whodunit"]`.

## 5. The cut

The chapter boundary is a judgment. The expansion is not. The cut therefore follows the
packet/map pattern already in the engine (`2026-07-18` §7) rather than inventing one:

1. **`chapter-cutter` proposes.** A new agent reads `story.md` and the genre beat sheet
   and proposes a grouping — which beats become which chapter — plus the four authored
   fields (§5.1). It **writes nothing**.
2. **The showrunner approves**, editing boundaries freely. The approved grouping is
   written to `input/book-NN/cut-plan.md`.
3. **`scripts/story_cut.py` emits.** Deterministic, no LLM. It expands the approved
   grouping into packet-format chapter blocks in `input/book-NN/outline.md`, deriving
   every section the author did not write (§5.2), and resolving clue chapter numbers
   (§6).

Only step 1 is a model. Step 3 is testable Python, which matters because it writes the
file every downstream stage reads.

`chapter-cutter` **absorbs `chapter-weaver`**. Weaving wiring across chapters and emitting
Track Movement rows is the same act as deciding where chapters fall; splitting them across
two agents is what allowed the skeleton and the outline to disagree.

### 5.1 What `cut-plan.md` carries

Four fields per chapter, authored by the agent and approved by the showrunner, because
none is derivable:

- **chapter title**
- **chapter summary** — the line the story-at-a-glance view renders
- **the Compress line** — per-chapter, not boilerplate. Book 01's is identical across most
  chapters and outline-feedback item **OF-13** is currently complaining that the drafter
  reads it as a vacuum. Making it per-chapter fixes that at the source.
- **Track Movement rows** — load-bearing, not decorative: `tension_check.py`'s
  `starved-thread` check reads them (`tension_check.py:39,146-148`) and the drafter reads
  them (`agents/drafter.md:38,41,89`).

Plus the beat ranges themselves.

### 5.2 What `story_cut.py` derives

| outline section | derived from |
|---|---|
| Required Beats | the chapter's beats, in order |
| Clues and Plants | `!clue` tags, rendered with the ledger's `description:` |
| Chapter Structure (wiring) | `+`/`-` tags and beat adjacency — the exact fields `tension_check.py` validates |
| Character Knowledge | `@strand` history up to this chapter, gated by `reveal_chapter` |
| Guardrails | `reveal_chapter` + `config/series-guardrails.md` |
| Starting State / Ending State | carried questions + the neighbouring chapters |
| Chapter Purpose | the `#job` descriptions the chapter's beats carry |
| Chapter Summary / Compress / Track Movement / title | `cut-plan.md` (§5.1) |

The emitted format is packet format, unchanged — `packet_assemble.py` slices one chapter
block out and must keep working with no modification. The repetition in `outline.md` is
required and is not reduced (`2026-07-31` §3.4); the file remains a machine input that the
showrunner does not read.

## 6. Clue resolution and the ledger write-back

`clue_schedule` in `series/whodunit/book-NN.yaml` schedules clues **by chapter number**.
Chapter numbers do not exist until the cut. The ledger therefore cannot be the source for
*which chapter plants a clue*.

Resolution: the author tags the **beat** with `!clue-id`. The cut assigns the clue to
whichever chapter that beat lands in and **writes the resolved chapter numbers back into
the ledger**.

This is safe because of ordering: `preflight lock-mystery` runs *after* the cut, so the
ledger is still unsealed when the cut touches it. Once locked, nothing writes to it — the
existing rule is unchanged.

**The key is `plant_chapter:`, in both `clue_schedule` and `red_herrings`.** This
paragraph originally said "by chapter number" and left the field name to the
implementation, which wrote a `chapter:` key nothing reads. The name is not the spec's to
choose — it belongs to the consumers, and every one of them reads `plant_chapter`:
`penny_whodunit._plant_chapter` (and through it `clues_by_chapter`, which feeds
`packet_assemble` and `tension_check`'s `overloaded-chapter`), `fairplay_check`, and
`lmstudio_draft_chapter`. Both collections are written, because `clues_by_chapter` and
`packet_assemble` both schedule from both — a `!rh-…` tag is as real an obligation as a
`!clue-…` one.

**The write is surgical, never a re-serialisation.** The ledger is read with PyYAML —
lossless — but written by rewriting only the matched `plant_chapter:` values in place,
preserving indentation and trailing comments. Both authored item shapes are supported: the
block form (`- id: x` / `  plant_chapter: 5` on their own lines) and the **inline
flow-mapping** form (`- { id: x, plant_chapter: 5, … }`), which is what this repo's own
fixtures use — only the value inside the braces moves. Everything else in the file comes
out byte-identical.

A `yaml.safe_load` → `yaml.safe_dump` round-trip was rejected: the ledger is a hand-authored
showrunner artifact, and re-serialising it silently discards comments, flattens anchors into
duplicated blocks, re-quotes scalars, and coerces a bare `no` or `off` in an alibi grid into
a boolean. `sort_keys=False` preserves only top-level key order and prevents none of that.
The engine may resolve a number the author could not know; it may not reformat their file to
do it.

## 7. Re-cutting

`outline.md`'s frontmatter gains `built_from_story: <sha256>`, `built_from_cut: <sha256>`,
and `cut_output_sha256: <sha256 of the body the cut wrote>`.

On re-run, `story_cut.py` hashes the current body and compares:

- **matches** — the file is still exactly what the cut produced. Re-cut freely: move a
  boundary, re-run, look again. This loop is what the skeleton never permitted.
- **differs** — someone shaped chapters by hand. **Refuse**, named `outline-modified-since-cut`,
  and say so. Never overwrite hand-shaped chapter work.

This preserves `2026-07-31` §7's one-way rule and `2026-07-30` §10's ruling, but starts the
one-way clock at the first hand edit rather than at the cut. Before that edit the cut is
cheap and repeatable; after it, `story.md` is frozen history exactly as §7 requires.

mtime is not consulted. A `git checkout` would flip it, and a wrong answer is worse than
no answer — the same ruling the lock's `outline_sha256` already follows.

## 8. Refusals

`story_cut.py` fails loud, by name, with a nonzero exit, and never writes a partial
outline:

| finding | condition |
|---|---|
| `unknown-strand` | `@tag` fails the slug contract |
| `unknown-job` | `#tag` not in the active genre's job list |
| `unknown-clue` | `!tag` not in the whodunit ledger |
| `unknown-question` | `+`/`-` tag names an id absent from `## Questions` (§3.1.1) |
| `unscheduled-clue` | a ledger clue no beat plants |
| `orphan-question` | `-q` closed without a matching `+q` |
| `beats-without-chapter` | the cut plan does not cover every beat |
| `outline-modified-since-cut` | §7 |

Exit codes follow `map_check.py`: 0 clean, 1 findings, 2 usage. **No waivers at this
level** — fix the story or fix the cut plan.

## 9. Testing

Test-first against `tests/fixtures/`, pure stdlib, per the dependency-split rule: the beat
parser belongs in `penny_meta.py`'s family, not PyYAML.

The load-bearing test is a **round-trip on book 01**: parse its `outline.md` back into
beats, cut them forward again, and diff against the real file. Not to ship a regenerated
book 01 — §11 forbids that — but because it is the only honest way to prove the emitter
produces what the rest of the engine already accepts.

## 10. Retiring `outline-skeleton.md`

`2026-07-31` §9 step 5's rule applies without amendment: **enumerate every glob and
literal naming the artifact** across `scripts/`, `commands/`, `agents/`,
`genres/cozy-mystery/ideation-prompt.md`, and `README.md`. Both plan defects in the
2026-07-30 stream were this omission.

## 11. Book 01 does not go through this

`2026-07-31` §1.1 and §8's ruling stands: book 01 is diagnosed, not re-plotted. Its
repairs remain hand edits to `outline.md`, driven by the 22 open feedback items — the
`q-clear` carry sweep first (OF-17, OF-16), and OF-25's one sentence of wanting in chapter
1.

Deriving `story.md` backwards from `outline.md` is lossy — separating spine from texture
is a judgment, so the result is an interpretation rather than a representation
(`2026-07-31` §8.2.1). Book 01's skeleton is deleted, not converted.

**Book 02 is the first book with a `story.md`.**

## 12. Open, and deliberately not settled here

- The four passes and their gates (`2026-07-31` §4) — own spec.
- Whether `/expand-outline` is retired outright or becomes the cut's entry point. It is an
  implementation decision for the plan, as `2026-07-31` §7 already recorded.
- The derived `story.md` worksheet for book 01 (`2026-07-31` §8.2.1). Its stated purpose
  was placing the stalker; it is not required by anything here.
