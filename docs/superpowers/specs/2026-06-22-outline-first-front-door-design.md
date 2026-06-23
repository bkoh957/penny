# Penny — Outline-First, Multi-Strand Author Front Door

Saved: 2026-06-22 | Status: design approved (brainstorm complete), pending spec review

Reprioritised ahead of design-doc Phase 7 (EPUB) / Phase 8 (scale): the author UX is
the gating risk for the project's premise. Supersedes nothing; touches no shipped gate.
Realises the "human sets the irreducible core, engine derives the mechanics" intent of
`penny-design-v3.md` §5/§5a from a **prose outline** instead of interactive typing.

## 1. Goal & scope

### The pivot

Penny today makes the **human author** produce the *mechanical* artifacts — the whodunit
YAML (clue schedule + alibi grid + red herrings), the per-suspect entity files, the
per-chapter briefs — and hands the **AI** the *creative* prose. That is inverted. A
writer writes outlines, in prose. This front door lets the writer author **beats**; the
system **derives** the structure and surfaces it for approval; the human keeps the taste
gates. Nothing downstream of the lock changes.

### The load-bearing reframe (read twice)

**The mystery is not the story axis. It is one strand among several** (romance,
settling-in, a kid-subplot…). Clues / revelations / twists are the *generic* plot
primitive — a tracked promise (setup → payoff). The engine is **already multi-strand**:

- `series/continuity/threads/*.md` are generic setup→payoff strands (the deleted
  `the-inheritance` was literally tagged "the personal B-plot").
- `series/arc-ledger.md` tracks each thread's Opens / Advances / Resolves.
- `inspector-structure` already checks thread-roster liveness across **all** of them.

Only **two** things are genuinely mystery-specific:

1. a **machine-checkable fairness invariant** — was every necessary clue planted
   on-page, in an earlier chapter, before the reveal, not retro-invented? A deterministic
   gate with teeth. (Romance's "did the kiss land?" is pure taste — ungatable.)
2. a **secret to hide from the drafter** — the sealed solution / blind drafter seam.

So the core model shift: **mystery = a strand-kind that opts into {fairplay gate +
sealed solution}.** Everything else is a normal, open, un-gated thread.

**Decision:** the front door goes **multi-strand now**; the shipped
gate/inspectors/lock are **untouched**.

### Two mysteries

Falls out for free: N mysteries = N strands that both opt in. **Decision:** format the
outline for N, **build + gate exactly ONE** in v1; a secondary mystery rides as a normal
un-gated, un-sealed thread for now. To keep `fairplay_check.py` **literally untouched**,
each gated mystery strand must project to its **own single-mystery yaml** that the
existing checker reads as-is. The looping multi-gate (one book lock iff all per-strand
gates pass) is **deferred** — documented as the next step, not built in v1.

### Three new pieces (on top of everything shipped)

1. **The outline** — swappable data, authored by the writer (`series/`-class input).
2. **`scripts/outline_check.py`** — the one new deterministic engine piece.
3. **`/scaffold-book NN <outline-path>`** command + **`book-scaffolder`** agent.

### Model topology note (record only — out of scope to build)

User constraint: **no API.** Main authoring/extraction = **Claude Code** + its
sub-agents. Independent review = **Codex via a Claude Code plugin**. The cross-model
"difference, not identity" invariant (design §7) is therefore realised as **tool
difference** (Claude-drafted vs Codex-reviewed), not API-model-id difference. The front
door is entirely setup/extraction (drafting-side), so this is **out of scope** here —
**record it as a design note** so run-config / assemble-guard reflect reality; do not let
it leak into this build.

### Out of scope (flag, do not build)

- Per-chapter **blind brief** auto-derivation (`draft-chapter` already falls back to
  canon-core-only when no brief exists — that is why this is deferrable).
- The **looping multi-mystery gate** (one gated mystery in v1; secondary rides un-gated).
- **Diff-on-edit** re-derivation review (v1 overwrites derived artifacts wholesale).
- **Any** change to shipped `fairplay_check.py` / inspectors / `lock-mystery` checker
  logic. (Hard constraint.)
- The scaffolder's **extraction quality** (UAT, like every Penny agent — unproven until a
  real outline runs through; treat the first live Book-1 run as a shakedown).

## 2. Architecture — the deterministic-vs-agent split

Governing rule (CLAUDE.md): scripts **never make an LLM judgment**; agents judge;
commands orchestrate; engine is genre/location-agnostic, project content lives in
swappable data. The front door honours all of it.

| Piece | Layer | Artifact |
|---|---|---|
| The outline | **swappable data** (writer-authored) | `input/book-NN/outline.md` |
| Outline structural check | deterministic — `scripts/outline_check.py` | exit code + named predicates |
| Structure extraction | **agent** — `.claude/agents/book-scaffolder.md` | the derived artifacts (below) |
| Orchestration + approval | command — `.claude/commands/scaffold-book.md` | `scaffold-review.md`, then the lock |
| The lock | deterministic — `preflight.py lock-mystery` (**built, untouched**) | `.penny/locks/book-NN.mystery.lock` |

### Approach A, and why not B or C (decided in brainstorm)

- **A (chosen):** thin deterministic guardrail (`outline_check.py` checks *shape* only) +
  LLM derivation in the command/agent layer.
- **B (rejected — pure command):** makes outline structural validity a *soft LLM gate* —
  the exact weakness the deterministic layer exists to prevent.
- **C (rejected — annotated-beats deterministic extraction):** would require the writer to
  tag which sentence belongs to which strand — re-imposing the mechanical authoring the
  whole pivot is killing.

So: **the deterministic script judges only structural shape; the agent does all genre /
semantic extraction; the human earns the lock.** `outline_check.py` is to the outline
exactly what `fairplay_check.py` is to the yaml — a fail-loud, named-predicate,
nonzero-exit structural gate with zero genre judgment.

### Generated ≠ trusted (the spine of the approval model)

The scaffolder writing a whodunit yaml does **not** make it valid. Validity is still
**earned at the lock**, by the **unchanged** `fairplay_check.py`. The derived artifacts
are written **unlocked** to their real paths; the human reviews the foregrounded mystery
strand; on approval the existing `lock-mystery` runs and either mints the cert or fails
loud with what to fix. The human taste gate sits exactly where it always has.

## 3. The outline (Piece 1 — swappable data)

One markdown file per book: `input/book-NN/outline.md` (or any path passed to the
command). Authored by the writer in prose. Shape:

```markdown
---
book: 01
total_chapters: 24
---

## Solution: the-tide-table-murder
- culprit: <name>
- victim: <name>
- central deception / motive: <prose>
- suspects: <name>, <name>, <name>
- key locations: <place>, <place>

## Threads
- romance — <one line: the promise this strand opens and where it should pay off>
- settling-in — <one line>
- the-kid — <one line>

## Chapter 01
<one prose beat for the chapter — the writer weaves ALL strands in prose, never
tagging which sentence belongs to which strand>

## Chapter 02
<prose beat>

... (contiguous through Chapter <total_chapters>)
```

**Rules of the shape:**

- **Frontmatter** carries the *only* two facts a deterministic check reads: `book` (int)
  and `total_chapters` (int).
- **`## Solution: <label>`** is **repeatable and labeled**. Each block is one mystery
  strand's **sealed answer key** (culprit, victim, central deception/motive, suspects,
  key locations). The label names the strand and routes its sealed projection.
- **`## Threads`** is one line per **non-mystery** strand. **Optional** — if omitted, the
  scaffolder *proposes* the roster from the beats. It is a roster of promises, not a form.
- **`## Chapter NN`** is one prose beat per chapter. The writer never tags strands; the
  scaffolder attributes, the writer confirms at review.
- Ship a commented **`config/outline-template.md`** skeleton so the writer never faces a
  blank page. (Template lives in `config/` — engine-class scaffolding, swappable.)

## 4. `scripts/outline_check.py` (Piece 2 — the one new engine piece)

Pure stdlib + `scripts.penny_meta` (frontmatter via `parse_frontmatter`; **no PyYAML** —
this is flat frontmatter + headings, the `penny_meta` side of the dependency-split rule).
**Zero LLM / genre judgment.** Fail-loud named predicates + nonzero exit, mirroring
`fairplay_check.py` / `preflight.py` (`outline_check: <predicate>`).

Checks **only structural shape** — four named predicates:

| Predicate | Asserts |
|---|---|
| `outline-frontmatter` | frontmatter present with integer `book` **and** integer `total_chapters` |
| `outline-solution` | at least one `## Solution` block (label optional but, if present, non-empty) |
| `outline-chapters-contiguous` | `## Chapter NN` headings number `1..total_chapters` — no gaps, no dupes, no extras |
| `outline-nonempty-beats` | every `## Chapter NN` block has non-whitespace body text |

It does **NOT** judge fairness, suspect-existence, prose quality, or strand attribution —
those belong to the lock (`fairplay_check.py`), the scaffolder (extraction), and the
human review respectively. The script is the *gate that the outline is shaped like an
outline*, nothing more.

**Public surface (for reuse by the command's dry-run and by tests):**

```python
def check_outline(outline_path, *, repo_root=None) -> dict:
    """Returns {"blocking": [str, ...], "metrics": {...}}.
    blocking is empty iff the outline is structurally well-formed.
    Each blocking string starts with one of the four named predicates."""
```

`main(argv)` parses one positional `outline` path, calls `check_outline`, prints any
blocking lines, and exits non-zero iff blocking is non-empty (exit 0 = well-formed).

## 5. `/scaffold-book` + `book-scaffolder` (Piece 3 — orchestration + extraction)

LLM extraction belongs in the **agent** layer, never a deterministic script (Approach A).

### Command flow — `.claude/commands/scaffold-book.md`

`/scaffold-book NN <outline-path>`:

1. **Structural gate:** run `python3 scripts/outline_check.py <outline-path>`. Non-zero
   exit aborts before any derivation — the outline is not shaped like an outline yet.
2. **Re-derivation hygiene:** if `.penny/locks/book-NN.mystery.lock` exists, **delete it
   first** (re-planning requires re-validation — the §5a clean re-lock story). The outline
   is the source of truth; v1 **overwrites** derived artifacts wholesale.
3. **Dispatch `book-scaffolder`** with `{ outline_text, book_number }`. It extracts
   structure from the beats + Solution(s) + Threads and writes the derived artifacts
   **unlocked** to their real paths (§6 routing table).
4. **Emit `output/book-NN/scaffold-review.md`** — the tiered review lens (§7).
5. **Pause** (human gate; default `review`, mirroring `ledger_approval` / `book_approval`).
6. **On `/scaffold-book NN --approve`:** run the **existing, unchanged**
   `python3 scripts/preflight.py lock-mystery NN`. It mints the lock iff fairplay +
   lexicon pass; otherwise it fails loud and writes no lock, and the review shows what to
   fix. **The lock is still earned by the shipped checker** — the front door never writes
   it.

### Agent — `.claude/agents/book-scaffolder.md`

Role-scoped, Claude Code. **Reads** the outline (it is the only agent that sees all the
Solutions — it must, to project them). **Writes** the derived artifacts. Its job is
*faithful extraction with least invention* — attribute beats to strands, lift the clue
schedule / alibi grid / red herrings the beats imply, name cast & locations, propose the
non-mystery thread roster if `## Threads` was omitted. It does **not** judge fairness
(the lock does) and does **not** write the lock or any certificate.

## 6. Derivation routing — each derived thing → its existing home

The scaffolder writes into the **already-shipped** continuity layer; nothing here is a new
storage format. Shapes verified against the live code/fixtures.

| Derived | Routed to (unlocked, real path) | Gated by | Verified shape |
|---|---|---|---|
| **Mystery strand:** clue schedule, alibi grid, red herrings, culprit/victim/deception | `series/whodunit/book-NN.yaml` (primary) + `series/whodunit/book-NN.<label>.yaml` (each extra gated strand) | `preflight.py lock-mystery` → `fairplay_check.py` | required keys `book, total_chapters, reveal_chapter, culprit, culprit_first_appearance_chapter`; optional `victim, central_deception, clue_schedule[], red_herrings[], alibi_grid[]` (see `tests/fixtures/ledgers/fair.yaml`). **No `locked:` field** — the lock is out-of-band. |
| **Non-mystery strands** (romance, settling, the-kid) | `series/continuity/threads/<id>.md` + a row in `series/arc-ledger.md` | `inspector-structure` liveness (shipped) | thread file: frontmatter `id, type: thread, links: [...], last_advanced_chapter:` + a prose body. arc-ledger: a `\| Thread \| Opens \| Advances \| Resolves \| Notes \|` row. |
| **Cast & locations** named anywhere in beats/Solutions | `series/continuity/characters/<id>.md`, `series/continuity/locations/<id>.md` | fairplay **entity-existence** check (culprit/victim/suspect ids must resolve) | `<!-- canon-meta: {...} -->` header + `id, type, links` frontmatter; an id "resolves" if `series/characters/<id>.static.md` **or** `series/continuity/characters/<id>.md` exists. |
| **Always-true facts** (protagonist, timeline, fluency, whodunit constraints) | `series/continuity/canon-core.md` updates (keep tiny — every line taxes every chapter) | `readiness_check` (reporting) | edit the placeholder lines under the existing `## Protagonist fixed facts` / `## Current timeline position` / `## Active-book whodunit constraints` / `## Fluency stage` sections; preserve their `canon-meta` headers. |
| **Sealed answer key(s)** | `output/book-NN/mystery-solution.md` (primary) + `output/book-NN/mystery-solution.<label>.md` (each extra gated strand) | **sealed** from drafter/beta/final readers | the §5a sealed-solution artifact `/plan-mystery` step 6 already writes. |

### The blind-brief seam is UNCHANGED

Nothing routed to a **drafter-visible** artifact contains a `## Solution`. Only **mystery
strands** get a sealed projection (`mystery-solution*.md`, the blind seam). All other
strands are **fully open** — their threads/arc-ledger rows carry no secret. The drafter
still sees exactly what it sees today.

## 7. The tiered review surface — `scaffold-review.md`

`output/book-NN/scaffold-review.md` is the **lens** over artifacts that are already on
disk (unlocked). It foregrounds the thing the human must judge and collapses the rest.

- **Foregrounded — the MYSTERY STRAND:** the clue schedule as **plant → payoff** chapters
  with `necessary` flags, the red herrings, the alibi grid, the culprit/victim/deception —
  plus an **inline dry-run** of `readiness_check` and `fairplay_check` (via
  `check_outline` / `check_fairplay` / `_fairplay_check`) so the writer sees **what the
  lock will say BEFORE approving**. This is where the human taste gate lives.
- **Collapsed (expandable):** the non-mystery **Threads**, the **Cast & Locations**, the
  **canon-core updates**. Surfaced for completeness, not foregrounded for judgment.

**Approval = earning the lock.** The writer edits the outline (or the derived yaml)
until the dry-run is green, then approves → the existing `lock-mystery` runs. Generated ≠
trusted; a failed lock leaves no cert and the review shows what to fix.

**Re-derivation:** re-run `/scaffold-book NN <outline-path>` → it deletes the lock first
(§6 step 2), re-derives, re-shows the review. v1 overwrites; **diff-on-edit is deferred**.

## 8. Error handling

| Piece | Hard-fail (nonzero) | Non-blocking / soft |
|---|---|---|
| `outline_check` | any of the four named predicates fails | — |
| `book-scaffolder` (agent) | — (agents never hard-gate) | extraction is reviewed, not gated |
| `scaffold-review` dry-run | — (reports what the lock *would* say) | red even when shown — it is a preview |
| `lock-mystery` (built, unchanged) | fairplay or lexicon fails → no lock written | — |
| command on `--approve` | propagates `lock-mystery`'s nonzero exit | absent lock = "not yet validated" (a state) |

Every deterministic miss is a named predicate + nonzero exit (`outline_check: <predicate>`,
matching `fairplay: …` / `preflight: …`). The agent and the review are non-blocking; only
`outline_check` and the shipped `lock-mystery` hard-fail.

## 9. Testing strategy

Test-first against `tests/fixtures/`, per CLAUDE.md. The deterministic piece gets unit
tests; the agent/command layer gets structure assertions + manual e2e (no unit tests for
LLM extraction).

- **`tests/test_outline_check.py` vs `tests/fixtures/outlines/`:**
  - `well-formed.md` → `check_outline` returns empty `blocking`; `main` exits 0.
  - `missing-solution.md` → fails with `outline-solution`.
  - `chapter-gap.md` (e.g. 1,2,4 of 4) → fails with `outline-chapters-contiguous`.
  - `non-int-count.md` (`total_chapters: many`) → fails with `outline-frontmatter`.
  - `empty-beat.md` (a `## Chapter NN` with whitespace body) → fails with
    `outline-nonempty-beats`.
  - Fixtures are **self-contained** — never real `series/` content (the readiness_check
    lesson: fixtures that reach into live content rot when the repo resets).
- **Command/agent layer:** prose runbook → assertions on the produced `scaffold-review.md`
  structure (foregrounds mystery, collapses the rest) + **manual e2e on the Book-1
  outline**. **Reuse existing `lock-mystery` tests** — no new lock-writing code means no
  new lock tests.
- **Cross-consistency (so conventions cannot fork, per CLAUDE.md):** a test that the yaml
  the scaffolder is specified to emit is the **exact** shape `fairplay_check` /
  `readiness_check` read — i.e. a `well-formed` derived yaml fixture feeds straight into
  `check_fairplay` and the entity-existence resolver without adaptation.

**Not tested (scope guard):** the scaffolder's extraction quality (UAT); the looping
multi-mystery gate (deferred); diff-on-edit (deferred).

## 10. New config / run-mode (swappable layer — never hardcoded)

Added to `config/run-config.md`:

```yaml
scaffold_approval:  review   # review (pause for writer) | auto
```

Mirrors the existing `ledger_approval` / `book_approval` pause convention. Plus the new
swappable scaffolding file `config/outline-template.md` (the commented skeleton). The
"no API → tool-difference" topology (§1) is **recorded as a run-config design note** so
the assemble-guard's cross-model invariant reads true; no behavioural change.

## 11. Build sequence (each piece testable as built)

1. **`scripts/outline_check.py`** + `tests/test_outline_check.py` + the
   `tests/fixtures/outlines/` set + `config/outline-template.md`. Pure deterministic,
   fully unit-testable, depends on nothing new. (TDD, the genuinely-new engine logic.)
2. **`.claude/agents/book-scaffolder.md`** — the extraction agent; reads the outline,
   writes the derived artifacts into their existing homes (§6) unlocked. No unit tests
   (LLM); validated by the cross-consistency yaml-shape test + manual e2e.
3. **`.claude/commands/scaffold-book.md`** — the orchestrator: `outline_check` →
   lock-delete-on-rederive → dispatch scaffolder → emit tiered `scaffold-review.md` →
   pause → `--approve` runs the **unchanged** `lock-mystery`. Add `scaffold_approval` to
   run-config + the topology design note.

The new deterministic logic (`outline_check`) lands first and standalone; the agent and
command build on shipped, untouched infrastructure (`lock-mystery`, the continuity layer,
`inspector-structure`).
