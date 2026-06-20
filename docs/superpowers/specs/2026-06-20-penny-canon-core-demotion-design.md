# Canon-Core Demotion — Design

Saved: 2026-06-20 | Phase: split — seed now / Phase-4 precision / Phase-8 machinery | Status: design approved, pre-plan

## §1 Purpose & the safety bar

A fact lives in `canon-core.md` because it is *active* — referenced often enough,
across enough chapters, that always-loading it is cheaper and safer than relying on
the slice loader (design §4.2) to summon it on demand. **Active is a time-varying
property.** A fact can earn always-loaded status in Books 1–3 and quietly stop
deserving it by Book 8 while remaining perfectly true.

**Demotion relocates such a fact down to a normal sectioned continuity entry**
(`series/continuity/characters/<id>.md`, `threads/<id>.md`, `locations/<id>.md`)
where the existing slice loader pulls it when relevant instead of always. The fact
stays canonical; only its loading cost changes from *every chapter* to *on demand*.

**Demotion never deletes a fact — it only relocates it.** That sets the safety bar:
a botched demotion must never lose a fact, only move it. The dangerous operation is
not the demotion itself — it is demoting something still needed always-on, so the
slice loader now sometimes fails to summon it and you get silent continuity drift.

The whole mechanism is therefore three steps:

> identify cold facts → relocate them → **guarantee the relocated fact is still reachable**

The third step is the one easy to skip and the one that bites. It is the hard,
tested gate of this design.

This mirrors the three-layer split the rest of Penny already uses
(`/plan-mystery`: *agent proposes → showrunner approves → lock freezes*). Demotion
is the same shape: **mechanical detection → human decision → safe move.**

## §2 Data contract — addressable sections (not atomised facts)

`canon-core.md` **stays one always-loaded file.** It is never sliced, so it is not
promoted to a directory. Demotion operates at **section grain** — the `##` section
is the unit that actually moves — and the review script reads section **headers**,
not prose.

Each `##` section carries a machine-readable header encoded as an **HTML comment
containing YAML**. This is invisible in rendered markdown and invisible to the
drafter (which reads canon-core verbatim), yet trivially greppable and parses as
YAML once the comment delimiters are stripped:

```markdown
## Protagonist fixed facts
<!-- canon-meta: {id: protagonist-fixed, active_window: "1-3", last_referenced: 7,
     reconfirmed_at: null, keep_reason: null} -->
- Cora Mistate, 44, recently divorced, relocated from Melbourne to Wreckers Bluff...
```

Header fields:

- **`id`** — stable section identifier (kebab-case). The addressing key for every
  layer below.
- **`active_window`** — the book range the showrunner declared this fact load-bearing
  for, e.g. `"1-3"`. **Hand-authored at promotion time.** The cheap seed: needs no
  per-chapter instrumentation, and front-loads the judgment ("how long do you expect
  this to be hot?") to promotion, which is healthy discipline on its own.
- **`last_referenced`** — a chapter number, written by the **Phase-4 ledger-updater**
  (design §4.3, post-gate). The P1 precision upgrade. The updater marks a section
  *touched* if **any** of the section's ids appeared in a finalized chapter's brief
  or text — one write per hot section per chapter (per-section recency is far cheaper
  than per-fact). "Referenced" = id appears in a finalized brief/chapter; detectable
  without LLM judgment.
- **`reconfirmed_at`** — book number at which a showrunner keep-decision last
  re-confirmed this section as still hot (§5). `null` until a keep happens.
- **`keep_reason`** — free text justifying a low-frequency fact's continued always-on
  status (§5). Institutional memory; lives in the header where the review script
  reads it, never in prose the drafter sees.

**One file, two reads.** The token-budget check and the demotion check read the same
structure: the budget script sums the file, the demotion script reads the section
headers, both off the one file. No second view of canon-core to maintain.

## §3 Layer 1 — mechanical detection (`canon_core_review.py`)

Built at **Phase 8 (series scale)**, invoked **per book** via the Phase-6 book-loop
hook (§7.1). **Proposes candidates; never demotes, never mutates, never asserts.** Reads section headers (not prose). Same posture as
the revision-priority report: *surface, don't decide.*

### §3.1 Per-section coldness verdict

For each section, compute the verdict using **precedence**, never blending (blending
two different-unit signals into a score is the "mushy average" the gate design
explicitly rejects — chapter-delta vs. book-range never need reconciling because
precedence picks one mechanism):

1. **`last_referenced` present** (P1 signal) →
   `cold = (current_chapter − last_referenced) > canon_core_cold_after`
   where `canon_core_cold_after` is a `run-config.md` knob (chapters; tunable).
2. **else `active_window` present** (cheap seed) →
   `cold = current_book > active_window.end` (the declared hot window has passed).
3. **neither present** → **WARN — un-instrumented.** Never treated as hot *or* cold.
   Emit nothing decisive (the same "fails silent on absent data, never fires on it"
   pattern as thread-liveness). The WARN is **actionable**: it names the *available*
   fix — `"add active_window"` is available immediately; `"wait for recency data"`
   only applies once the Phase-4 updater is live — so a Book-2 WARN does not read as
   "blocked on Phase 4" when the cheap annotation is available now.

### §3.2 Directional precedence — three outcomes, not two

`last_referenced` taking precedence is **directional**. Artifact beats declaration
when the artifact shows *activity*; it must **not** beat declaration on *absence* of
activity, because inactivity is exactly the signature of a load-bearing arc plant
(a fact rarely referenced but silently governing continuity until it pays off in a
later book). Demoting that fact is the precise silent-continuity-loss the whole
mechanism exists to prevent.

| recency | window | outcome |
|---|---|---|
| hot | any | **`hot`** |
| cold | absent or also-passed | **`cold`** — high-confidence demotion candidate |
| cold | still open | **`cold-but-protected`** — escalation; default action **keep**; report prints why (the arc-plant safe harbor) |
| hot | cold | **`hot`** — recency corrects a stale window guess (safe direction) |

`cold-but-protected` is surfaced for showrunner attention ("recency suggests cold,
but you declared this hot through Book N — confirm whether the window still holds"),
but is **never auto-proposed for demotion with confidence**. The showrunner either
re-confirms (still load-bearing) or releases it (paid off early → demote).

### §3.3 Output

A **report**, not an action, per candidate section:

```
{id, fact, last_referenced, active_window, verdict, proposed_target}
```

- `verdict ∈ {cold, cold-but-protected, hot, warn-uninstrumented}` (only the first
  two and warn surface as candidates; `hot` is omitted or summarized).
- `proposed_target`:
  - For a fact tied to a **named entity**, recovered mechanically
    (e.g. `characters/margaret`) — the entity id is in the fact.
  - For a **free-floating** fact (world rule, cross-character constraint) with no
    natural home, `UNRESOLVED` — the script cannot invent a target.

The **same script** also emits the **size-budget warning** (sum the file against a
`canon_core_size_budget` knob), since both reads are off the one file.

## §4 Layer 2 — human decision (escalation)

The showrunner reviews the candidate list and rules per candidate:
**demote / keep / keep+annotate.**

- Coldness-by-metric is necessary but not sufficient. The killer case is the fact
  rarely referenced but load-bearing when it is. This is irreducibly a taste/strategy
  call — it escalates, identical to mystery design and "would a reader buy book 2."
- `cold-but-protected` candidates **default to keep**.
- `UNRESOLVED` candidates are **not movable** until the showrunner assigns a home
  (and, if needed, adds a `links` edge to make it reachable). Assignment is intent;
  the move-time assert (§5) verifies the artifact.
- **keep** decisions are themselves valuable output: they document why a low-frequency
  fact still earns always-on status, which is the institutional memory that prevents
  the same candidate being re-flagged every book.

## §5 Layer 3 — the safe move (executor; mechanical + tested)

This is the step that **must** be mechanical and tested, because it is where facts
get lost. On an approved demotion:

### §5.1 Move-time reachability assert (the hard precondition)

Runs **as a hard precondition before any file mutation**, and reads **actual file
state, not the approval record** — *validate the artifact, not the promise* (same
reason the cross-model reality-check reads `drafted_by` stamps rather than trusting
`run-config.md`; a showrunner can assign intent and forget the edit).

**Reachable** ≝ the target satisfies **either**:

- **(a) addressable** — the target entry file exists, carries an `id` in frontmatter,
  **and its `## Established facts` section is within the slice loader's loaded scope**
  (not merely that the file exists — see §6); **OR**
- **(b) link-reachable** — the target id appears in the `links:` array of some entry
  that is itself addressable, *verified by reading the real file at move time*.

If neither holds → **refuse the move** (hard-fail, fail-loud). Kick back to "keep in
canon-core" or "showrunner must add the `links` edge first." This is the demotion
analogue of the brief-quality gate: the loader can only protect facts it can resolve,
so demotion must prove resolvability before it lets a fact leave the always-loaded
set. This assertion is the single most important part of the whole mechanism.

### §5.2 On a passing assert — the relocation

1. **Append** the demoted prose under the target entry's `## Established facts`
   heading (create the heading if absent). **Append-only** — the move never overwrites
   target content, so a botched move can never clobber an existing fact in the target.
2. **Self-containment flag.** At move time, flag any fact whose prose is **not
   self-contained** (relies on canon-core context to make sense — e.g. an unqualified
   "her eyes are green") for **human touch-up**, so the relocated sentence stands
   alone in its new home.
3. **Tombstone in canon-core.** Replace the demoted section's body with a one-line
   breadcrumb comment, e.g.:
   ```markdown
   <!-- demoted: protagonist-arrival → threads/the-inheritance @ book-04
        keep_reason history: "load-bearing while Cora is an outsider" (book-02) -->
   ```
   Not deletion — a tombstone. Provides (a) an audit trail of where every fact went,
   (b) a double-residency guard read by the promotion path (§6), and (c) a greppable
   record. **Accumulated `keep_reason` history survives into the tombstone.**

### §5.3 keep / keep+annotate — write the header, not the body

A **keep** decision on a `cold-but-protected` candidate stamps `reconfirmed_at:
book-NN` into that section's `canon-meta` header. **keep+annotate** additionally
writes `keep_reason: <text>`. Both write the **header, not prose** — the review script
reads them; the drafter never sees them.

`reconfirmed_at` **suppresses re-escalation only while the `active_window` is still
open**, and **lapses when the window actually ends** — at which point the section
returns to a normal `cold` candidate (a human said "keep through Book N"; once past
Book N the suppression expires and it is re-examined as genuinely cold).

## §6 Cross-system agreements (where silent failure hides)

Each is the same shape: the mechanism is right, but it touches a *second* system that
must agree, and that seam is where silent failure hides.

- **Loader.** The slice loader must read `## Established facts`. The §5.1 reachability
  assert *means that section is loaded*, not merely that the target file exists. If
  the loader skipped that section, a "reachable" target would still silently fail to
  summon the fact.
- **Promotion path.** Whatever promotes a fact *into* canon-core must read tombstones
  to prevent **double-residency** — a fact re-promoted into canon-core while it still
  lives in its demoted target home.
- **Budget counter.** The budget counter's exclusion of tombstones and `canon-meta`
  headers must be **proven by a test**, not asserted — so the file provably shrinks on
  demotion rather than merely appearing to.

## §7 Config & phase placement

New knobs in `run-config.md` (escalation-thresholds block, same fail-loud pattern as
existing knobs):

```yaml
canon_core_cold_after:   <N>     # chapters; recency-cold threshold; tunable
canon_core_size_budget:  <N>     # tokens or lines; size-budget warning; tunable
```

### §7.1 The feature splits across three phases (it does not land in one)

Coldness is an inherently **cross-book** property. `active_window: "1-3"` with
`cold = current_book > active_window.end` **cannot fire until book 4**. A fact does
not go cold inside a single book — it goes cold across books ("hot in Books 1–3, dead
weight by Book 8"). Consequence: the demotion *machinery* has nothing to act on until
multiple books exist, and **MVP1's endpoint (Phase 6) produces Book 1** — where
demotion can never trigger. Building the detector + executor at Phase 6 would be dead
code through all of MVP1.

So the feature is deliberately split into three pieces, each landing where its
dependency or its payoff actually is:

| Piece | Phase | Rationale |
|---|---|---|
| **Data contract** — the `canon-meta` HTML-comment header schema (§2) + `active_window` authored at promotion time | **Seed now** (whenever a fact first enters canon-core / the earliest phase that touches canon-core structure) | `active_window` is *only* capturable at promotion time; miss it and it is unrecoverable. This is the "start collecting now" seed. Cost is near-zero — a header convention, no machinery. |
| **`last_referenced` marker** | **Phase 4** (rides the ledger-updater, design §4.3) | Written at the same post-gate point, by the same machinery, as thread `last_advanced_chapter`. Prerequisite for the *precision* coldness path only; the cheap `active_window` path does not need it. |
| **Detection (`canon_core_review.py`) + executor (move, reachability assert, tombstone) + the `run-config.md` knobs** | **Phase 8 (series scale)** | This is where cross-book coldness is real and where its natural neighbors live — the arc-ledger across all 13 books and the cross-book reviewers. Demotion is series-scale hygiene, not a single-book operation. By Phase 8 the promotion path and loader behavior are settled, so the §6 cross-system agreements become real verifications rather than forward-references. |

The **per-book review cadence** is a Phase-6 *hook* only — a cheap placeholder
invocation point that is a no-op until the manuscript spans enough books for a fact to
go cold. It is not where the machinery is built.

### §7.2 The shape that falls out, per book (Phase 8 machinery)

```
1. canon_core_review.py  → reads canon-core section headers + recency/active-window
                         → emits candidates {id, fact, last_referenced, active_window,
                           verdict, proposed_target}  (+ size-budget warning)
2. showrunner reviews    → demote / keep / keep+annotate         (escalation)
3. on approved demotion (executor):
     assert reachable(target)   ← reads real files; hard-fail if unreachable
     append fact → target ## Established facts   (append-only)
     flag non-self-contained prose for human touch-up
     write tombstone into canon-core (carries keep_reason history)
   on keep / keep+annotate:
     stamp reconfirmed_at (+ keep_reason) into the section header
```

## §8 Testing focus

- **Reachability assert** — addressable-OR-link-reachable, reading real file state
  (not the approval record); hard-fail on unreachable; the link-edge case verified
  against an actual `links:` array, including the "human promised the edge but forgot
  to add it" path.
- **Directional coldness table** — all four recency×window combinations resolve to the
  correct one of `hot / cold / cold-but-protected`, plus the un-instrumented WARN.
- **Append-only + tombstone move** — no fact lost, no target content clobbered;
  tombstone written with correct target + book; `keep_reason` history carried in.
- **Budget excludes tombstones + headers** — provable shrink on demotion.
- **`reconfirmed_at` lifecycle** — suppresses re-escalation within the open window,
  lapses to a normal `cold` candidate once the window ends.
- **Self-containment flag** — a non-self-contained fact is flagged for human touch-up
  at move time.

## §9 Decisions made (and the alternatives rejected)

- **Split across phases, not landed at Phase 6.** Coldness is a cross-book property
  that cannot fire on Book 1, so the *machinery* belongs at Phase 8 (series scale)
  where it earns its keep; only the cheap, unrecoverable-if-missed **data seed**
  (`canon-meta` header + `active_window` at promotion) lands early, and the
  `last_referenced` precision marker rides Phase 4. See §7.1.
- **Section-grain addressable, not per-fact atomisation.** canon-core is never sliced,
  so promoting it to a directory (one file per fact) stands up machinery for no
  loader benefit. Sections are the unit that actually moves.
- **HTML-comment YAML header, not a fenced `yaml` block or a heading-line tag.** Only
  the HTML comment is fully invisible to the drafter (no risk the model treats
  `active_window`/`id` as content, no leaked code block costing tokens) while staying
  greppable and YAML-parseable.
- **Reachability is a move-time precondition, not a detection-time check.** Detection
  cannot see future briefs, so it only *proposes* targets (possibly `UNRESOLVED`); the
  assert runs at the move, against real files.
- **Directional precedence.** Recency overrides window only in the hot direction;
  recency-cold against window-hot is an escalation (`cold-but-protected`), not a
  verdict — inactivity must not silently override an explicit human "keep this hot."
- **Tombstone, not deletion.** Audit trail + double-residency guard + greppable record,
  at negligible (header-excluded) size cost.
