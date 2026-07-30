# Staged reveal-aware read-back — design

Date: 2026-07-30
Status: approved (showrunner, 2026-07-30), amended same day on three points — §7 (a clean
context matters, a second model does not), §6.1 (findings land as measured, one-change-each
items in the existing feedback ledger, because the repair is conversational), and §10 (book
01 is repaired at outline level by working those items, and `/plot-book` is not re-run).
Supersedes: nothing. Extends the `/plot-book` readback stage
(`docs/superpowers/specs/2026-07-12-plot-book-workshop-design.md` §7, beside the
proofreader of its §6) and the reader-simulation property described in
`docs/superpowers/specs/2026-07-10-remove-solution-blindness-design.md`.

## 1. The failure this fixes

Book 01's chapter-2 clue was named `c02-lisa-already-met-maggie` and its chapter-3
question was `q-vase — who made the false Maggie vase?`. Both name the Act II reveal
(someone impersonated Maggie before she arrived), which is not meant to land until
chapter 15. `packet_assemble.py` renders clue ids verbatim into the chapter packet, so
chapter 2's drafting instruction says the reveal out loud, thirteen chapters early.

**The engine already had the instrument that should have caught this, and it ran.** On
2026-07-28 both the outline panel (`/review-outline`, 12 items) and the blind fan read
(`outline-fan`) executed against this outline. Neither reported the leak. The panel's
item OF-2 actively *recommended* a chapter-7 beat where "Simon's access explains the
impersonator's research" — it proposed deepening the leak. The fan report said:

- Ch 02 — 4/5. The "earlier Maggie" contradiction is a **strong hook**.
- Ch 11 — I would be **leaning toward some kind of impersonation here**.
- Whodunit guess: Marion. **Chapter first sure: Chapter 15.**
- The midpoint is strong. **Protect it.**

The reader found the leak in chapter 2, was suspicious from 11, certain at 15 — the
chapter that was supposed to reverse the book — and then praised the midpoint.

Three structural reasons it could not do better:

1. **It read its own work with its own context.** The report header records
   `independence: reduced — report generated in the active Hermes session rather than a
   separate non-plotting model`. The operative words are **"in the active session"**, not
   "same model". The read happened inside the plotting conversation, carrying the
   solution, the turning points, and every decision that built the book. This is an
   **isolation** failure in CLAUDE.md's existing sense — narrow inputs, no cross-talk —
   and not an independence failure. No persona instruction survives a context that
   already knows the answer; it will take the shortcut every time.
2. **It was never told a surprise was coming.** Nothing told the fan chapter 15 was a
   trapdoor. Certainty at 11 therefore read as satisfying foreshadowing, not a broken
   midpoint. A reader who does not know where the trapdoor is cannot report that the
   trapdoor was visible.
3. **It read past the reveal.** `readers_copy_text` truncates at
   `reveal_chapter` — 26, the *culprit* reveal. So the copy ran to chapter 25, well past
   the chapter-15 pivot. The fan read the pivot, enjoyed it, and reported it landed.

**Therefore this design adds no new gate.** The intelligence was present; the briefing
was not. The fix instruments the reader that already exists.

### 1.1 Explicitly rejected

An earlier draft of this session designed a deterministic reveal-leak checker
(forbidden-term greps over clue ids, q-slugs, and pre-reveal outline prose) plus a
render-time surface-name translation layer in `packet_assemble.py`. **Both are dropped.**
The evidence above shows the failure was not an absent check, and CLAUDE.md's existing
reasoning applies: the deterministic layer is for facts, not taste. "This outline gives
its midpoint away" is not a predicate.

What replaces them: measure the *effect* (a reader suspects too early) rather than
grepping the *cause* (a word appears too early).

## 2. The instrument

One dial, read from both ends:

- A reader who suspects a reveal **too early** is the suspense failure — the story is
  boring, the midpoint is spent.
- A reader who **never** suspects it is the fairness failure — the clue is not landing
  and the solution is a cheat.

Fair-play stops being a separate authority with its own schedule and becomes one reading
on this gauge. That is the demotion; the reveal order is the spine.

## 3. Data: the `reveals:` block

New optional block in `series/whodunit/book-NN.yaml`, beside the existing `act_pivots:`.
The whodunit ledger is the home because all three front doors write it (`/plot-book` via
`mystery-planner`, `/plan-mystery`, `/scaffold-book` via `book-scaffolder`), the mystery
lock seals it, and `plot_stage.py` already reads it.

```yaml
reveal_chapter: 26        # UNCHANGED — the culprit reveal. fairplay_check.py and
                          # every existing consumer keep reading exactly this.

reveals:                  # NEW — protected turns, in ascending reveal_chapter order
- id: impersonation
  reveal_chapter: 15
  author_truth: >
    Someone used Maggie's identity to arrange studio access before she arrived.
  reader_should_think_before:        # optional, for the side-by-side only
  - Lisa was abusing property records for a quick flip
  - Simon covered an office/process breach
- id: marion-is-tara
  reveal_chapter: 27
  author_truth: >
    Marion is Tara, George's missing daughter.
```

Fields: `id` (kebab-case, unique), `reveal_chapter` (int in `1..total_chapters`),
`author_truth` (one line — what is revealed), `reader_should_think_before` (optional
list; shown beside the reader's own summary, never used to censor anything).

**The reader never sees this block.** It is the answer key the harness holds. This
preserves reader simulation as CLAUDE.md defines it: the beta/fan reader receives
`{ text, persona_file }` and nothing else.

`reveals:` is **optional and absent is normal** — a book with no block gets today's
single-cut read, unchanged. Legacy books never break.

### 3.1 Clue and question naming

`c02-lisa-already-met-maggie` leaks because `packet_assemble.py:168` renders the id into
the packet, and the id cannot simply be dropped: `map_check.py` gates `unscheduled-clue`
by id, so the map-maker needs a stable handle.

The rule is therefore an **authoring discipline, not a checker**: a clue id and a q-slug
name the clue's *apparent* subject, never its solution meaning. `c02-early-key-note`, not
`c02-lisa-already-met-maggie`. `q-vase — whose hand made this vase?`, not `who made the
false Maggie vase?`. The true meaning lives in the clue's `description:` and in
`author_truth`, which the packet does not render as a label.

This is deliberately not machine-checked. A keyword grep over ids is the approach §1.1
rejects, and the staged read measures the consequence that actually matters. Recorded in:
`config/outline-template.md` (the `### Clues and Plants` comment), `agents/mystery-planner.md`,
and `agents/chapter-weaver.md`.

## 4. Staged reader's copy

`readers_copy_text` already takes `reveal_chapter` and truncates to `1..reveal_chapter−1`.
Extend it to a **through-chapter**, and drive it once per stage.

Stages derive from `reveals:` — no new authored data. For reveals at chapters `r1 < r2 <
… < rk` and `total_chapters` T:

| Stage | Chapters emitted | Cut before |
|---|---|---|
| 1 | 1 … r1−1 | the first protected turn |
| 2 | 1 … r2−1 | the second |
| … | | |
| k+1 | 1 … T | nothing (final stage, whole book) |

Each stage's copy is **cumulative from chapter 1**, not just that stage's own chapters.
Considered and rejected: emitting only the new chapters per stage. Cumulative is one
parameter change rather than two, and mirrors a real read (the earlier chapters remain
available). The contamination it admits is bounded and harmless — a stage-2 reader
re-reads chapters 1–14 already knowing the pivot, but its stage-1 report is on disk and
immutable before stage 2 is generated, so the honest answers are already captured.

CLI: `plot_stage.py readers-copy NN [--through M]`. Output path gains a stage suffix,
`output/book-NN/reports/outline-readers-copy-stage-K.md`. With no `reveals:` block the
command behaves exactly as today, writing the unsuffixed
`outline-readers-copy.md` — the legacy path stays byte-identical.

The existing strip (solution, wiring, question ids, track rows, title type-flags) is
unchanged and still by construction.

## 5. What the reader is asked

`agents/outline-fan.md` gains a staged protocol. Per stage it writes
`output/book-NN/reports/outline-fan-stage-K.md` answering, in order:

1. **What is this story about right now?** One sentence — the question live in the
   reader's head. If at the end of stage 1 that sentence names the impersonation, the
   midpoint is already spent.
2. **Top three suspects, most to least, each with how sure (1–5).** A curve, not a name.
   "Marion, but I hope I'm wrong" and "Marion, obviously" are different books.
3. **What do you expect the next big turn to be?** The load-bearing question — it
   measures directly whether the trapdoor is visible from outside. Put beside the actual
   next turn, it needs no rubric.
4. **What have you stopped wondering about?** A question the reader has quietly closed is
   a thread dead on the page but still being serviced in the outline — the
   evidence-accounting feel, caught from the reader's side.
5. **Anything you suspect but cannot prove**, each with how sure (1–5). This is what the
   suspicion audit matches against `reveals:`.
6. **Per-chapter interest 1–5** and **put-down points** for this stage's new chapters.
   Unchanged from today.
7. **Would-buy, yes/no with one sentence** — final stage only.

Hard constraints, unchanged: prose as a reader, never craft jargon, never a `^BLOCKING:`
line, never holds a gate. The fan is given its stage's copy and the persona. It is **not**
given its own earlier reports — each stage answers from the text in front of it, and
comparing across stages is the audit's job, not the reader's.

## 6. The suspicion audit

A step in the `/plot-book` readback runbook, not a new agent and not a script. The
orchestrating session reads `reveals:` plus every stage report and writes
`output/book-NN/reports/suspicion-audit.md`: one row per reveal.

```
reveal            meant to land   first suspected   gap      note
impersonation     ch 15           stage 1 (4/5)     EARLY    reader named it before ch 15
marion-is-tara    ch 27           stage 2 (2/5)     ok       suspicion rising, not certain
```

Below the table, for each reveal not yet landed, the audit sets the reader's own
"what is this story about right now" sentence beside that reveal's
`reader_should_think_before` list where the ledger supplies one. That side-by-side is the
field's only consumer: it shows the showrunner whether the reader is chasing the intended
wrong answer or has drifted somewhere the plan never accounted for.

Findings are named for the showrunner's eye, not for an exit code:

- **`early`** — the reader named the reveal, with confidence ≥3, in a stage that closes
  before its `reveal_chapter`.
- **`never`** — in the stage closing immediately before its `reveal_chapter`, the reader
  does not name the reveal at all. The fairness end of the same dial: `early` is that
  stage naming it with confidence ≥3; `never` is that stage not reaching it.

  (RULING, final review I4: the earlier wording — "not suspected in any stage closing at
  or after its `reveal_chapter`" — cannot fire. Stage boundaries are `r₁−1, …, r_k−1, T`,
  so every stage closing at or after `r_i` **contains chapter `r_i`**, meaning the reader
  has already read the reveal on the page by the time that stage closes; a reader who
  "never suspects it" in such a stage cannot be observed at all. Measuring it one stage
  earlier — the same stage `early` reads — is what makes the fairness end of the dial
  actually readable.)
- **`predicted`** — the reader's "next big turn" for stage K is the reveal that stage K+1
  contains. The sharpest form of `early`.

The orchestrating session sees the whole solution, so it cannot contaminate the reader —
the reader has already filed. The audit is a clerk, not a reader.

**No exit code, no gate.** It is presented at readback beside `tension_check.py`'s
findings, and the showrunner's existing sign-off is the decision point — unchanged from
today, and consistent with the fan's advisory contract. The lock is still readback's last
act.

### 6.1 Findings land as dispositionable items, not prose

**Decision (showrunner, 2026-07-30): the outline is repaired by working findings one at a
time in conversation, never by re-running the workshop. So a finding has to be granular and
measured — a general or vague observation is unusable.**

The markdown table above stays as the at-a-glance view, but it is not the product. Every
finding is also appended to the **existing** feedback ledger,
`output/book-NN/reports/outline-feedback.yaml`, via `outline_feedback.py append` with
`source: fan-audit`. That ledger already provides everything this needs: sequential
`OF-<n>` ids, a `state:` per item the showrunner owns by hand (`open`/`solved`/`rejected`),
append-only history, a side-by-side reading view via `render`, and a
never-blocks-drafting backlog banner via `status`. It is the same surface `/review-outline`
already writes to, so there is one place to work through and one place to disposition.

**The granularity rule: one item = one change to one chapter.** If a finding implicates six
chapters, it is split into six items. An audit that emits "the Lisa thread is weak" has
failed, however true it is, because it cannot be worked one at a time. Each item names its
chapter, states what the reader did, and proposes the smallest specific repair.

`append_items` currently builds each item from `{source, text, recommendation?}`. It gains
passthrough of two optional fields so items carry their measurements:

```yaml
- id: OF-13
  source: fan-audit
  pass: 1
  state: open
  chapters: [11]
  metrics: {finding: early, reveal: impersonation, meant_to_land: 15,
            first_suspected: 11, confidence: 4, gap_chapters: 4}
  text: >
    At the end of stage 1 the reader said the story was "about someone pretending
    to be Maggie" and rated that 4/5 sure, from chapter 11's wrong-voice note.
    The reveal is not due until chapter 15, so the midpoint arrives four chapters
    after the reader already had it.
  recommendation: >
    Chapter 11: make the note's wrongness a class/handwriting oddity Maggie reads
    as Lisa's office sloppiness, not a voice that isn't Maggie's.
```

`chapters` is a list of ints; `metrics` is a flat mapping. Both are optional, both are
opaque to the ledger — it stores and renders them, it does not interpret them. Existing
items without them are unaffected, and `/review-outline`'s panel items may use them too
where a point is chapter-specific.

The measurements per finding type:

| Finding | Metrics |
|---|---|
| `early` | `reveal`, `meant_to_land`, `first_suspected`, `confidence` (1–5), `gap_chapters` |
| `never` | `reveal`, `meant_to_land`, `first_suspected: null`, `confidence: 0` |
| `predicted` | `stage`, `predicted`, `actual_next`, `reveal`, `meant_to_land` |
| `drift` | `interest` (1–5), `put_down_risk` (bool) — one item per chapter |
| `dead-thread` | `stage`, `closed_question`, `still_serviced_in` (chapter list) — the reader stopped wondering, the outline keeps paying |

`dead-thread` is the one that reaches the plumbing complaint from the reader's side: a
question the reader has closed while chapters 17 and 19 still spend words servicing it is
exactly a chapter existing for bookkeeping rather than for the story.

**The loop this creates.** Readback is no longer one pass. Read → items → work the open
items against the outline → re-read to confirm → lock. The outline must be unlocked while
items are being worked, which it already is: readback's sign-off is what mints the lock,
and re-locking after edits is the ordinary "delete the lock, re-run `lock-mystery`" path.
A book may go round this loop as many times as the showrunner wants; the ledger's
append-only history is the record of what each pass found.

## 7. A clean context, not a second model

**Decision (showrunner, 2026-07-30): running the fan on the plotting model is
acceptable. Running it in the plotting model's *context* is not.** What corrupts the read
is inherited context — an AI that already holds the solution and its own planning
decisions will take the shortcut regardless of the persona it is handed. Model identity
is the wrong axis for this particular read.

So the requirement inverts. Today's runbook prefers a different model and tolerates a
same-session read. From here:

- **The fan MUST be a sub-agent dispatch, always.** Never performed inline by the
  orchestrating session. A sub-agent dispatch is a fresh context by construction, which is
  the only mechanical guarantee available — and it is precisely what was skipped on
  2026-07-28.
- **Its inputs stay exactly `{ reader's copy for this stage, fan persona }`.** Nothing
  else, as its agent definition already says. Same model, no shared context, narrow
  inputs.
- **A same-model read is no longer a degradation and is not noted as one.** The
  `independence: reduced` header line loses its meaning here and is replaced by
  `context: fresh sub-agent` plus the model id, which is what the reader's credibility
  actually rests on.
- **Model preference stays as a preference.** Where a non-`plot_model` model is reachable,
  still use it — a second model is a bonus, no longer the thing being claimed.

`preflight.py lock-mystery` still gains `--note-skipped "<check-id>: <why>"`, appending to
the `skipped_lines` list it already builds, but for one case only: the fan read **did not
happen at all**, recording `skipped: fan-read — <why>`. Same convention as
`overloaded-chapter`'s existing skip note — a certificate must not claim coverage it does
not have. There is no longer a `fan-independence` note, because same-model is no longer a
shortfall.

The wider engine principle is untouched: `preflight.py assemble` still enforces
model difference against `drafted_by` for the final read, where a genuinely different
model *is* the claim. This section narrows only the fan read, and it does so using
CLAUDE.md's existing distinction — reader simulation needs **isolation**; the final read
needs **independence**.

## 8. Error handling and degradation

| Condition | Behaviour |
|---|---|
| No `reveals:` block | Single-cut read at `reveal_chapter`, today's behaviour exactly. Never an error. |
| `reveals:` present, malformed (missing `id`/`reveal_chapter`, non-int, out of `1..total_chapters`, duplicate id, not ascending) | `plot_stage.py` exits loud and names the offending entry. Consistent with `_reveal_chapter`'s existing fail-loud-not-open rule — a book that authored the block and got it wrong must not silently fall back to one stage. |
| A reveal at `reveal_chapter: 1` | Loud error: stage 1 would emit zero chapters. |
| Whodunit ledger absent | No truncation, no stages — the legitimate pre-planning case, already handled. |
| Fan cannot be dispatched at all | Print "fan read skipped" and pass `--note-skipped fan-read`. Never halts the workshop. |
| Only `plot_model` reachable | Proceed on it, as a fresh sub-agent. Not a degradation, no note (§7). |
| Fan would have to run inline (no sub-agent dispatch available) | Refuse the read and treat it as skipped, above. An inline read is the 2026-07-28 failure and is worse than no read — it returns a confident report that reassures. |

## 9. Testing

New deterministic tests (`tests/test_plot_stage.py`, fixtures under `tests/fixtures/`):

- `readers_copy_text` with `--through M` emits chapters `1..M` and no more; the withheld
  notice names the right last chapter.
- Stage derivation from a two-reveal ledger produces three stages with the boundaries in
  §4's table.
- A ledger with no `reveals:` writes the unsuffixed legacy path with byte-identical
  content to today (regression pin — this is the legacy invariant).
- Each malformed-`reveals:` case in §8 exits nonzero with the entry named.
- The existing strip still removes solution/wiring/q-ids/track rows/type-flags at every
  stage, including the final whole-book stage.
- `lock-mystery --note-skipped` puts the note on the certificate.

- `append_items` passes `chapters` and `metrics` through when present, omits both keys when
  absent, and never mutates an existing item's `state` (extends the current append tests).
- `render` shows an item's chapters and metrics without choking on an unknown metric key —
  the ledger stores them opaquely.

The staged read itself and the audit are LLM work and are **not** unit-testable. Their
verification is the book-01 repair in §10.

## 10. Book 01 as the proof

Book 01 is the case that produced the failure, so it verifies the fix.

**Decision (showrunner, 2026-07-30): book 01 is repaired at the OUTLINE level, by the
showrunner working the ledger's findings one at a time in conversation. `/plot-book` is NOT
re-run.** Regenerating the book would discard the outline the showrunner has already shaped
and would replace deliberate judgment with a fresh machine pass. The engine ships the
machinery and the measured findings; the repair is editorial, item by item, per §6.1.

The known leaks the findings must therefore name as individual items — each one a change to
one chapter or one ledger entry: the clue ids, the q-slug, and the missing `reveals:`
block. §3.1's naming rule accordingly lands as a rule the showrunner applies while working
these items, and in `mystery-planner`'s contract so future books get it at generation
time:

- clue ids `c01-marion-tara-memory`, `c02-lisa-already-met-maggie`,
  `c03-wrong-clay-wrong-hand-vase`, `c09-lisa-note-voice-wrong`,
  `c10-tara-object-hidden-catch`
- the q-slug `q-vase — who made the false Maggie vase?`, at all four sites (opened ch 3,
  carried ch 4 and ch 10, closed ch 24)
- a `reveals:` block: `impersonation` at 15, `marion-is-tara` at 27

**Order of work**, because the staged read cannot stage without the answer key:

1. The showrunner writes the `reveals:` block — `impersonation` at 15, `marion-is-tara` at
   27. This is a taste call about which turns are protected and cannot be derived.
2. Delete the lock. It must be re-minted regardless: the current certificate dates
   2026-07-28T03:10 while `outline.md` was modified 2026-07-29T16:31, so it already
   attests to an outline that no longer exists.
3. Run the staged read and the audit. Findings append to the ledger as `fan-audit` items.
4. Work the open items in conversation, one at a time, editing `outline.md` and the
   whodunit ledger. Mark each `solved` or `rejected` by hand.
5. Re-read to confirm, then `lock-mystery`. Repeat 3–5 as needed.

Readback's staged read, as a fresh sub-agent per §7, is the verification.

**Success is not a green run.** Success is stage 1's "what is this story about" sentence
being about Lisa and the property, and its "next big turn" prediction being something
other than the impersonation. If the reader still calls it at stage 1 after the re-run,
the leak is in the beats rather than the labels, and the audit will have told us that —
which is the whole point of measuring the effect instead of grepping the cause.

## 11. Out of scope

- **The stage layer** (giving chapters 7–14 an active pursuit so they exist for a
  dramatic reason rather than because clues are due). Discussed this session and
  genuinely wanted, but it changes how `chapter-weaver` fills the book and deserves its
  own spec. The audit's `never` finding and its "stopped wondering about" question will
  say whether it is still needed after this lands.
- **Moving `macro-structure.md` pre-lock.** The four-act lens is already written and
  wired into `/review-outline` (uncommitted in the working tree as of this spec). It is a
  separate, small change and should be committed on its own merits first.
- Any change to `fairplay_check.py`, `tension_check.py`, or `map_check.py`.
