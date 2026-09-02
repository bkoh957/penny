# Handoff — Penny (fiction-series engine) / main
Saved: 2026-09-02 | Type: build (one defect, shipped and pushed)

> **Stream note.** Single-defect session on the engine. The prior `HANDOFF.md`
> (lobo/LoboFlow/Meowtown-v2, 2026-08-30) was uncommitted on the working tree;
> it is now preserved in git at `f4cbbe5` and this file replaces it. Other
> stream files (`HANDOFF-engine.md`, `HANDOFF-story.md`, `HANDOFF-direction.md`,
> `HANDOFF-of122.md`, `HANDOFF-readiness-briefs.md`) were not touched.

## What we built

An agent found that a chapter drafted through `/draft-chapter` (the cloud/main
path) came out as uncalibrated "literary" stunt prose, while the LM Studio path
produced correctly-voiced prose. Their diagnosis: "the main path never loads the
voice pack."

That was right about the symptom, wrong about the cause. `agents/drafter.md`
**already declared** `config/voice-pack/voice-pack.md` as an input — but as
item 6 of a run-on 7-item Inputs clause, and instruction 1 told the drafter to
"Read the map, the packet, and the tail" — three things, voice pack not among
them. A model reads that as: voice is optional. `inspector-ai-prose` only
catches the result after the fact.

The v6 cure the agent found earlier ("my dispatch brief pointed at the voice
pack manually") was a workaround living in the series' `.penny/` dispatch files
— it dies the moment someone drafts through the engine's own command.

Fix — all in the engine, `32e7854`:
- **`agents/drafter.md`** — voice pack pulled into its own Inputs bullet with
  the *what (packet/map) vs. how (voice pack)* framing; instruction 1 now reads
  the voice/setting/genre packs **first**, then the map/packet/tail.
- **`commands/draft-chapter.md`** — a note in the context-assembly step (step 3)
  that the packs are a direct agent read, mirroring the LM Studio digest load,
  so the parity is visible in the runbook.
- **`tests/test_drafter_loads_voice_pack.py`** — new contract test: voice pack
  is named as its own input, instruction 1 reads it before the map, and the
  command names it too.
- **`CLAUDE.md`** — full-suite count 1311 → 1314.

## Git state

- Branch: `main`, pushed through `f4cbbe5`.
- `32e7854` — the drafter voice-pack fix (4 files).
- `f4cbbe5` — preserved the prior uncommitted lobo handoff + `HERMES.md` rename
  + two untracked stream handoffs.
- Uncommitted changes: none (this file will be the only one after saving).
- Tests: `1314 passed in ~6s` — full green.

## Next actions

Nothing pending from this defect — it is closed, shipped, pushed, tested.

If picking up general engine work, the live threads are in the other stream
files, unchanged:
- `HANDOFF-engine.md` (2026-09-01) — most recent engine build state.
- `HANDOFF-story.md` — story-layer / book-01 blocking findings.

## Decisions made this session

- **Fixed the agent file, not the runbook.** The other agent proposed adding a
  line to `commands/draft-chapter.md:49–53`. But the packs are direct agent
  reads (like the setting and genre packs — CLAUDE.md: "the setting pack stays a
  direct read by `drafter`"), so the runbook was never the place a load was
  missing. The real weakness was emphasis in `drafter.md`. The runbook got a
  one-note cross-reference only, for visibility.
- **Kept the prior lobo handoff.** It was a full session's handoff, uncommitted
  — overwriting it would have been unrecoverable. Committed as-found first.

## Watch out for

- **`test_texture_allocation_docs.py::test_claude_md_test_count_matches_the_suite`**
  pins the "full suite (N tests)" number in CLAUDE.md against a live
  `--collect-only`. Any test you add breaks it until you bump that line.
- **`HERMES.md` now says "Meow", not "Booko"** — that rename came in with the
  preserved prior-session commit, not this session.
