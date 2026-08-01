# Handoff — Penny (fiction-series engine) / readback
Saved: 2026-07-31 | Type: build

> **Stream note.** `HANDOFF.md` = the Hermes / LM Studio drafting stream.
> `HANDOFF-plot.md` = the plotting workshop (shipped 2026-07-12).
> `HANDOFF-briefs.md` = the packet/map redesign (shipped 2026-07-18); its own
> "next actions" are **superseded** — it describes a 39-chapter `outline-packet.md`
> migration that the 2026-07-28 series restart replaced with a 30-chapter re-plot.
> Don't act on that file.
> **This stream** shipped the staged reveal-aware read-back (2026-07-31).

## What we're building

The engine's blind fan read of a book's chapter plan was structurally unable to
catch a spoiled midpoint, and proved it on book 01. This stream instrumented the
reader that already existed rather than adding another gate.

**Shipped, pushed, done:** the whodunit ledger takes an optional `reveals:` block
listing a book's protected turns; the reader's copy is cut at *every* turn (one
cumulative copy per stage, each stopping one chapter short) instead of once at the
culprit reveal; `outline-fan` is dispatched **fresh per stage** and asked what it
currently believes; and its answers are compared to the ledger and appended to the
existing `outline-feedback.yaml` as measured, one-change-each `fan-audit` items.

**Spec:** `docs/superpowers/specs/2026-07-30-staged-reveal-readback-design.md`
**Plan:** `docs/superpowers/plans/2026-07-30-staged-reveal-readback.md` (7 tasks)
**Execution ledger:** `.superpowers/sdd/2026-07-30-staged-reveal-readback/progress.md`
— every showrunner ruling, every controller ruling, all reproductions. **Trust it
over memory after a compaction.** Deliberately kept, not deleted.

## Git state

- Branch: `main`, **in sync with origin** (`e9750aa..8c4a01d` pushed 2026-07-31)
- Uncommitted changes: **none**
- Last commit: `8c4a01d fix(plot): C1 fingerprint made whitespace-proof, not whitespace-exact (RULING)`
- Tests: **647 passing** (`python3 -m pytest`). Was 595 at session start.
- The three commits before the plan work (`f47fc90`, `9e3ebd2`, `4273dd7`) are
  unrelated work that was sitting uncommitted in the tree and got committed
  separately to clear it: the cozy beat-sheet cap retune 8→15, the four-act
  `macro-structure.md` rubric + archetype rebuild + `/review-outline` lens wiring,
  and the stale briefs-stream handoff save.

## Next actions

1. **Book 01's repair — the showrunner's job, editorially. Do NOT re-run `/plot-book`.**
   That is a ruling, recorded in spec §10: regenerating would discard the outline
   they have already shaped. Order of work:
   1. Write the `reveals:` block into
      `~/myBooks/pelicanscrook-series/series/whodunit/book-01.yaml` —
      `impersonation` at 15, `marion-is-tara` at 27. This is a taste call and
      cannot be derived.
   2. Delete `.penny/locks/book-01.mystery.lock`. It must be re-minted anyway: it
      dates 2026-07-28T03:10 while `outline.md` was modified 2026-07-29T16:31, so
      it already attests to an outline that no longer exists.
   3. `/plot-book 01` → readback. It writes the staged copies, dispatches
      `outline-fan` per stage, runs the suspicion audit, appends `fan-audit` items.
   4. Work the open items one at a time in conversation, editing
      `outline-skeleton.md` and the ledger; mark each `solved`/`rejected` by hand.
   5. Re-read to confirm, then `lock-mystery`. Loop 3–5 as needed.
2. **Success is not a green run.** It is stage 1's "what is this story about right
   now" sentence being about Lisa and the property, and its "next big turn"
   prediction being something *other* than the impersonation. If the reader still
   calls it at stage 1, the leak is in the beats rather than the labels — and the
   audit will have said so, which is the whole point of measuring the effect.
3. **Deferred, and genuinely wanted: the stage layer.** Chapters 7–14 still exist
   because clues are due, not because that stretch has a dramatic job. This is the
   other half of the showrunner's original complaint and it needs its own spec —
   it changes how `chapter-weaver` fills a book. Spec §11 records it as out of
   scope. The audit's `never` and `dead-thread` findings should say how badly it
   is still needed once book 01 has been read back.
4. **Still owed from earlier streams:** the length/compression companion spec
   (`length_check.py`, `/compress-chapter`); the `/new-series` onboarding brainstorm.

## Decisions made this session

- **Instrument the reader; add no gate.** The `/review-outline` panel and the fan
  read both ran on book 01 on 2026-07-28 and both missed the leak — the panel's
  OF-2 actively *recommended* deepening it. So the failure was never an absent
  predicate. An earlier design in this same session (forbidden-term greps over
  clue ids and pre-reveal prose, plus surface-name translation in
  `packet_assemble.py`) is recorded in spec §1.1 as **explicitly rejected** so
  nobody rebuilds it. The deterministic layer is for facts, not taste.
- **Isolation, not independence, is what the fan read needs.** The 2026-07-28
  report said `independence: reduced — generated in the active Hermes session`.
  The operative words were "in the active session", not "same model": it held the
  solution and every plotting decision. So a same-model read is fine and is no
  longer written up as a shortfall; what is now mandatory is a **fresh sub-agent
  dispatch**, and an inline read is refused outright and recorded as skipped. This
  reuses CLAUDE.md's existing distinction rather than inventing a concept.
- **The reader is never shown `reveals:`.** It is the answer key the harness holds
  and measures against. A reader told where the surprise is cannot report whether
  the surprise works.
- **Findings must be granular or they are useless.** One item = one change to one
  chapter. "The Lisa thread is weak" is a failed finding however true, because the
  showrunner cannot sit down and fix it. Hence `chapters`/`metrics` on ledger items.
- **Clue/q-slug naming is an authoring rule with no checker.** A keyword grep over
  ids is the approach §1.1 rejects; the staged read measures the consequence.
  Recorded in `mystery-planner`, `chapter-weaver`, `outline-expander`, and the
  outline template.
- **Chapter freshness ignores the `reveals:` block AND blank lines.** This was the
  session's Critical, found only by the whole-branch review: the turns live in the
  same file as the clue schedule, which is a fingerprint upstream of the `chapters`
  stage — so writing them told the workshop to regenerate the book, exactly what
  spec §10 forbids. Two failed fixes preceded the right one (a `yaml.safe_dump`
  round-trip moved the bug one step later; text-stripping left it in the
  whitespace). Final rule: fingerprint the ledger's **non-blank lines minus the
  reveals block**. Accepted cost — a book already stamped re-stamps once.

## User preferences expressed this session

- **Explanations must put the story, not the code, in the subject of the sentence.**
  The failure mode is not jargon, it is grammar: "`packet_assemble.py:168` renders
  the id verbatim" versus "chapter 2's instructions literally say
  `lisa-already-met-maggie`, so the writer shapes the scene around it". No component
  tables, no "architecture" headings, no design-doc structure when talking an idea
  through. Specs are the exception. I proposed a `CLAUDE.md` section enforcing this
  and the showrunner did not answer either way — **offer it again if it slips.**
- **Menu labels must name the real mechanism.** They stopped a menu to ask "why
  ignore the turns?" because my label sounded like discarding their work when it
  meant excluding one section from a staleness fingerprint. A misleading label
  costs a round trip and can invite the wrong choice.
- **Apply an established ruling; do not re-ask it.** Once they ruled "the approved
  artifact wins, re-pin the test", the second instance of that pattern was mine to
  decide. Escalate only when the new case differs in kind.
- Still true from earlier streams: precise numbers over estimates; confirm a
  decision once, then execute without re-litigating; discuss in prose before menus.

## Key files right now

- `scripts/plot_stage.py` — `_reveals`, `reveal_stages`, `readers_copy_staged`,
  `_upstream_sha`/`_strip_reveals_block` (the Critical's fix), and `stage_status`'s
  readback branch.
- `agents/outline-fan.md` — the staged reader's contract; the six questions.
- `commands/plot-book.md` step 8 — readback is now a **loop**: read → findings →
  work them → re-read → lock. Step 9 mints the lock.
- `scripts/outline_feedback.py` — `chapters`/`metrics` passthrough; `--source`.
- `series/whodunit/book-01.yaml` (in the series repo) — where the `reveals:` block
  goes next.

## Watch out for

- **The series repo moved.** It is `~/myBooks/pelicanscrook-series`, not
  `series-pelicanscrook` as older handoffs say. Its `input/book-01/` is entirely
  untracked, and there is a stray `input/book 01/` (with a space) beside it.
- **Book 01 is a 30-chapter re-plot** (`stage: expanded-outline`, `woven: true`),
  not the 27- or 39-chapter versions older handoffs describe. `outline.md` is
  canonical; there is no `outline-packet.md`.
- **Two contract-pin tests guard prose** — `test_outline_fan_contract` and
  `test_runbook_gives_literal_bash_for_every_stamp_call`. Any deliberate rewrite of
  an agent brief or runbook trips them, and they cannot tell an improvement from a
  weakening. Both needed re-pinning this session. The standing rule: **the approved
  artifact wins; re-pin the test, never reword the artifact to satisfy it.** Budget
  for this in any plan touching `agents/*.md` or `commands/*.md`.
- **Any task that changes an artifact's filename must enumerate every glob and
  literal naming it** across `scripts/`, `commands/`, `agents/`, and `README.md`.
  Both plan defects this session were that omission — the fan report's rename broke
  the stage tracker and the runbook's stamp command, and `/plot-book` would have
  looped on readback forever.
- **The plan file carries stale wording** (the pre-ruling `never` definition, a
  `/tmp` points path). Plans are historical execution records; the **spec** and the
  runbook are the live contract.
- `render_view` shows a `never` metric's `first_suspected` as `—`; that is
  deliberate, not a missing value.
