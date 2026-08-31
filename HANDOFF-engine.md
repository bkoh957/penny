# Handoff — Penny (fiction-series engine) / engine
Saved: 2026-08-31 | Type: build (three defects, all shipped)

> **Stream note.** This is the engine stream. `HANDOFF.md` is a *different* session —
> lobo/LoboFlow/Meowtown, no engine code — and is deliberately not overwritten. The
> engine work before today is in the committed `HANDOFF.md` at `70d15f8`.

## What we're building

Closing out the backlog of shipped-but-unfixed defect specs. Three landed today, all
from the same family the specs call out by name: **an agent receives an input that
differs from what the repository intended, and no gate can see it.** Suite went
1265 → 1311.

## Git state

- Branch `main`, **not pushed**. Three commits ahead of `53894a4`.
- `e27bb5a` runbooks: arguments are bound by name, not by position
- `c031444` packet_assemble: Ledger Clues declares what it holds, and survives a heading
- `13314ce` drafter: Opening and Closing name a beat, not a sentence
- Tests: **1311 passed**, clean.
- Uncommitted, and none of it mine: `HANDOFF.md` + `HERMES.md` (modified, lobo session),
  `HANDOFF-of122.md` + `HANDOFF-readiness-briefs.md` (untracked, older streams).

## Next actions

1. **Restart Claude Code, then run `/argprobe AAA BBB`.** Both halves matter. Command
   files are cached per session, so today's fifteen migrated runbooks are NOT live in
   the session that wrote them — a restart is required before any pipeline command
   behaves as intended. And `commands/argprobe.md` gained a "Braced and default forms"
   block that has never been rendered (the cache is why), so its answers about
   `${book}`, `${extra:-FALLBACK}` and `${extra:+"$extra"}` are still unknown. Nothing
   depends on them — the migration avoids braced declared-argument forms entirely — but
   confirm before anyone writes one.
2. **Rebuild the packets for book 01** — `/map-chapter 01 MM` per chapter. Today's
   Ledger Clues manifest only reaches a chapter when its packet is regenerated, and
   `preflight draft`'s staleness chain will not tell you: it stamps
   `built_from_outline`/`built_from_whodunit`, so it cannot see a *format* change. Three
   agents are now told to check a manifest that old packets do not carry. Benign — they
   find nothing and proceed — but the guarantee is not live until the rebuild.
3. **`repeated_content_words` measures function words** — §7 of
   `2026-08-27-voice-drift-discards-evidence-fix.md`, verified not implemented. Its five
   cited spans on book 01 ch 01 are *that* ×27, *been* ×12, *could* ×10, *down* ×10,
   *there* ×10. Needs a real stoplist (~200 entries, in a data file, not in code) and a
   recalibrated threshold. The largest remaining item that needs no decision from you.
4. **Run the two missing reviews** — `597b014` (nested cut-plan field hijack) and
   `34b133f` (engine story details). Both were dispatched in an earlier session and
   killed by Opus session limits; nothing was lost, but the work is unreviewed.
5. **Thriller genre pack** — blocked on you, not on work. Five open `[DECISION]` flags in
   `2026-07-08-thriller-genre-pack-design.md`: artifact rigor, the escalation-gap note,
   the fair-play back-fix, `/plan-thriller`'s fate, the `_resolves` extraction.

## Decisions made this session

- **Named arguments, not renumbering — and the showrunner had already chosen
  renumbering.** The spec hedged because named binding was "documented for skills and
  explicitly unverified for commands". Re-running the §2b probe (which §5 demands before
  implementing) verified it works, and surfaced a third fact nobody had anticipated: **an
  absent named argument renders empty; an absent positional stays literal.** Renumbering
  would therefore have rendered `flag=$1` — those two characters, as text — whenever an
  optional flag was omitted, leaving `assemble-book`, `finalize-chapter` and `book-status`
  actively broken where they are currently accidentally fine. That inverted the call, and
  it was put back to the showrunner before any file was touched.
- **The lint is "no bare positional anywhere", not "none inside fenced blocks".** The spec
  measured seven affected runbooks in code and eight more in prose. Prose is substituted
  too; the eight were survivable only because a reader corrects them by comprehension. A
  rule needing no clause about *where* it applies is the one that stays true.
- **A declared argument's name may never be reused as a shell variable.** Learned by
  breaking it: `new-series` computed `root="${root_arg:-$HOME/myBooks}"` then used
  `target="$root/$name"`, which would have built `target="/cozy-pelicans"` whenever the
  optional root was omitted, because every `$root` is substituted before the shell runs.
  Now `books_root`, and linted.
- **`argprobe.md` is committed, not deleted**, against its own frontmatter's "Delete after
  use". §5.3 makes re-confirmation an ongoing need after any Claude Code upgrade, and the
  lint exempts it by name and asserts it exists — a fresh clone fails without it.
- **Opening/Closing were redefined rather than rewritten.** The alternative was rewriting
  all 70 fields in `cut-plan.md` into a consistent intent form; that costs a `story_cut`
  run, a lock re-mint, packet rebuilds and map re-stamps across 35 chapters to achieve
  what redefining the contract achieves for free — and would discard genuinely good lines
  like *"Rourke fills the kettle before he looks at the body"*.
- **A checker enforcing the verbatim Opening/Closing contract was rejected**, and there is
  now a regression guard against anyone building one: no script may both read a chapter's
  prose artefact and name the `Opening`/`Closing` fields. It would enforce a rule that is
  unsatisfiable for the abstract fields, and would have locked in book 01 ch 01's
  technically-wrong opening as correct.
- **Ledger Clues got a third change beyond the spec's two bullets:** the manifest is
  documented in all three contracts that read a packet. A declaration nobody is asked to
  compare against is decoration.
- **Receipts (curated-artifacts §6) still not built.** The spec's own recommendation, and
  it stands: a manifest alone does most of the work. Build the receipt loop only if a
  manifested section is observed to be under-read anyway.

## User preferences expressed this session

- **Lead with a recommendation, then the reasoning.** Asked for "the best item to work on",
  not a survey.
- **Plain language.** "What is runbook off-by-one?" wanted the mechanism in writer's terms
  first, not the spec's vocabulary.
- Terse direction (`renumber`, `do ledger`) — take it and go; surface a fork only when the
  evidence actually changes the answer, as it did once today.

## Key files right now

- `commands/*.md` — fifteen migrated to `arguments: [...]` + `$name`. `plan-book` untouched
  (no placeholders of either kind); `expand-outline` gained frontmatter it never had.
- `tests/test_runbook_arguments.py` — new. Two rules: no bare positional; no declared name
  reused as a shell variable.
- `CLAUDE.md` — new "Runbook arguments" section, with the re-confirmation procedure and the
  per-session caching caveat.
- `scripts/packet_assemble.py` — clue descriptions now heading-demoted; `## Ledger Clues`
  carries `(N scheduled: ids…)`.
- `agents/drafter.md` — the Opening/Closing contract. Also `map-maker.md` and
  `commands/review-chapter.md` for the manifest instruction.

## Watch out for

- **A restart is mandatory before trusting any runbook.** Command files are cached per
  session. Editing one and re-invoking it renders the OLD body with NEW arguments — which
  is exactly how this was discovered, and it looks like the edit silently failed.
- **`argprobe`'s new block is unrendered.** Inert prose, no risk, but do not cite its
  braced-form answers until it has actually been run post-restart.
- **Old packets carry no Ledger Clues manifest and nothing flags them.** See next action 2.
  The staleness chain watches content hashes, not format.
- **`test_claude_md_test_count_matches_the_suite` pins the suite size in `CLAUDE.md`.**
  Every commit that adds a test must update the number in `CLAUDE.md`'s Commands block, or
  the suite fails. It is currently 1311.
- **Three defect specs from this family are now closed; the family is not.** The sequence is
  `2026-08-27-packet-extract-heading-collision-fix` (a slice truncated),
  `2026-08-29-engine-holds-story-details-fix` (a pack contradicted),
  `2026-08-29-runbook-render-corrupts-positional-vars-fix` (an instruction rewritten),
  `2026-08-29-opening-closing-are-beats-not-sentences-fix` (an instruction misread), and
  `2026-08-29-curated-artifacts-declare-their-contents-design` §4a (a curated set silent
  about its own omissions). When something else in this shape turns up, that list is the
  precedent to read first.
- **Nothing is pushed.** Three commits sit on local `main`.
