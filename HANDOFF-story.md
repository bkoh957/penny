# Handoff — Penny (fiction-series engine) / story
Saved: 2026-08-04 00:30 | Type: build

> **Stream note.** `HANDOFF.md` = LM Studio drafting. `HANDOFF-plot.md` = the plotting workshop
> (shipped 2026-07-12). `HANDOFF-briefs.md` = packet/map redesign (shipped 2026-07-18) —
> superseded. `HANDOFF-readback.md` = staged reveal read-back (shipped 2026-07-31) — superseded.
> `HANDOFF-views.md` = the diagnostic views + `/book-status` (shipped 2026-08-02) — its
> **engine follow-ups are done or obsolete**, but its **book-01 next-actions still stand** (see
> "The other half"). **This is the live stream.**

## What we built

The showrunner asked why, after all the diagnostic work, they were *still* hand-editing a
1,769-line `outline.md`. The answer: the views fixed **reading** and nothing had fixed
**writing**. The small editable layer was supposed to be `outline-skeleton.md` — but it carried
the same ten `###` section headings as `outline.md` in the same order, 1,943 bytes/chapter
against 3,286. Same shape, same cognitive task, and nothing resisting growth. It had drifted
into a second book: a two-chapter offset ("Simon Behind the Desk" = ch 07 there, ch 05 in the
canonical outline) with a stale reveal baked into 30 blocks.

**Shipped:** `input/book-NN/story.md` — beats in **story order**, four sigils and no other
syntax, so boilerplate has nowhere to live:

```
- The handover appointment was altered — in Maggie's name.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered
```

`@strand` `#job` `+q-id`/`-q-id` `!clue-id`. `##` headings carry no meaning except one
`## Questions` block holding question prose once. Tags are captured **loosely** and validated
**strictly**, so `@Maggie` is refused by name instead of vanishing.

Then a one-way cut: `chapter-cutter` proposes boundaries → showrunner approves
`input/book-NN/cut-plan.md` → `scripts/story_cut.py` deterministically emits packet-format
`outline.md`, deriving the seven sections the author doesn't write. Re-cutting is free while
`outline.md` matches its `cut_output_sha256`; it refuses `outline-modified-since-cut` the moment
you hand-edit — and refuses an outline carrying **no** stamp at all, which is what protects
book 01.

**Spec:** `docs/superpowers/specs/2026-08-03-story-source-layer-design.md` (carries three
corrections found during implementation — read them, they are the interesting part).
**Plan:** `docs/superpowers/plans/2026-08-03-story-source-layer.md`
**Execution ledger — every finding, ruling and reproduction; deliberately kept:**
`.superpowers/sdd/2026-08-03-story-source-layer/progress.md`

## Git state

- Branch: `main`, **30 commits ahead of origin**, `9d53dc0..dd56f18`. **Nothing pushed.**
- Uncommitted: `HANDOFF-views.md` only (pre-existing, untouched all session).
- Tests: **881 passing** (`python3 -m pytest`). Was 780 at session start.

## Next actions

1. **Push.** 30 commits sitting on local `main`. Phase-end push is the convention and this is a
   phase end.
2. **Cut book 02** — the first book through the new layer. Author `input/book-02/story.md`,
   run `/plot-book 02` to the cut stage. Book 01 does **not** go through this.
3. **The other half — book 01's repair still stands**, unchanged by this work and still the
   thing between you and a drafted book. From `HANDOFF-views.md`, still true:
   - Work the **22 open feedback items** (`outline_feedback.py render 01`). Sharpest:
     `q-clear` opens in ch 2 and is never carried again — Maggie's own jeopardy, dropped.
     The Act I commitment repair is a **footer sweep** (OF-17/OF-16) plus one sentence of
     wanting in ch 1 (OF-25), not new prose.
   - Do **not** run `/review-outline 01` — it appends a third panel pass over an unworked
     backlog. `book_status.py` still prints it as `next:`; that line is still wrong.
   - Close out: write `reveals:` (**13 and 25**), delete the stale lock, re-mint.
4. **Parked minors** — all in the ledger with rulings. The one worth taking: exactly **one**
   unclosed question is currently silent, so a dropped thread is indistinguishable from a
   deliberate series seed. Fix is a non-blocking note. Its natural home is
   `genres/*/beat-sheet.yaml` as `questions.max_carried_past_end`, default 1.

## Decisions made this session

- **A source layer earns its place by being a different representation, not a shorter one.**
  The governing lesson. If it can be arranged into the same form as its artifact, it will drift
  into a duplicate. `story.md` cannot, because the other sections have no syntax.
- **Author writes beats, strands and questions; the cut derives the rest** from the ledger,
  the genre and the tags. Cost accepted: derived sections aren't editable at story level.
- **The ledger write-back is surgical, never a re-serialisation** (owner's call). A
  `yaml.safe_load`/`safe_dump` round-trip silently discards comments, flattens anchors, and
  coerces a bare `no` in an alibi grid into a boolean. The engine may resolve a number the
  author could not know; it may not reformat their file to do it.
- **The read-back runs after the cut, against `outline.md`.** The spec said "story.md before the
  cut" — unimplementable: `readers_copy_text` is chapter-indexed and a pre-cut `story.md` has no
  chapters. As specified it wrote a near-empty reader's copy **silently at exit 0**.
- **`/expand-outline` refuses an outline the cut produced** (`cut-owned-outline`). Editing a
  generated outline in place would recreate the exact two-descriptions drift this work killed.
- **`unclosed-question` refuses two or more, not one.** `tension_check` requires every chapter
  to hook a live question, so a fully-resolved book always draws one `broken-hook` on its last
  chapter. A blanket refusal would have reinstated a blanket waiver.
- **Book 01 is not re-plotted.** Deriving `story.md` backwards from `outline.md` is lossy —
  separating spine from texture is a judgement, so the result is an interpretation.

## User preferences expressed this session

- **Push back on the process when it isn't paying.** "If I'm still stopped editing the outline
  file, then all the changes are pointless." That reframing is what produced this whole phase —
  the diagnostics had solved reading and quietly left writing alone.
- **Don't build a thing that only fixes one book.** They rejected `story.md` until it was shown
  that retiring the skeleton without a replacement would leave *every* future book with book
  01's problem.
- **Terse when off-site.** One-word answers ("a", "its right", "add it") are decisions, not
  disengagement. Give the recommendation first and the reasoning after.
- Still true: story in the subject of the sentence; precise numbers over estimates; prose before
  menus; apply an established ruling rather than re-asking.

## Key files right now

- `scripts/story_cut.py` — the checker, the emitter, the stamps, the surgical ledger rewriter,
  the CLI. The biggest new surface.
- `scripts/penny_story.py` — `parse_story`, `parse_questions`, `parse_cut_plan`.
- `agents/chapter-cutter.md` — proposes boundaries; absorbed the deleted `chapter-weaver`.
- `commands/plot-book.md` — now has a `cut` stage between `weave` and `readback`.
- `tests/test_story_cut_roundtrip.py` — the load-bearing proof: real book-01 chapter blocks
  through the emitter, output fed to `tension_check`.

## Watch out for

- **Twelve task-scoped reviews all passed, and the whole-branch review still found two
  Criticals.** Both were seams no single task owned: the ledger write-back targeted `chapter:`
  when every consumer reads `plant_chapter:`, and the emitted wiring couldn't pass
  `tension_check` (no `Because:` on ch 1, `Hook` only when a chapter opened a question — every
  cut book would have needed a blanket `--waive broken-hook`). **The lesson: review the seams by
  cutting a real book end-to-end, not by reading diffs.**
- **The spec's §8 finding-id list is stale** — it names 8, the module ships 12. The extras came
  from findings the reviews forced. `CLAUDE.md`/`README.md` document the real 12. The spec
  describes the design; the docs describe the code.
- **`outline_check`'s `outline-solution` predicate** was failing forever on cut books until
  `dd56f18`, because §5.2's derivation table never listed a `## Solution` block. If you add a
  new required outline section, check that table.
- **A comment as the *first* line under `clue_schedule:`** kills `_item_spans` and refuses the
  whole cut. Pre-existing, loud not silent, parked in the ledger.
- **`test_chapter_cutter_contract` pins `Beats:`/`Summary:`/`Compress:` but not the `- **M:**`
  track-row shape** — the one field whose drift silently empties Track Movement.
- **Contract-pin tests** (`test_runbook_gives_literal_bash_for_every_stamp_call`,
  `test_readme_check_count`) trip on deliberate prose rewrites. Standing rule: the approved
  artefact wins, re-pin the test — but only for *previously approved* artefacts.
