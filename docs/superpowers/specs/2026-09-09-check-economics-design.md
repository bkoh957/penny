# The free checks are dark and the packet is sent eight times

Date: 2026-09-09
Status: design, approved in conversation, not yet planned
Depends on: `2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md` (§3a here is
inert until that lands). Related: `2026-09-08-chapter-status-manifest-design.md`, which
is aimed at the same blind spot from the visibility side.

## 1. Why

Penny has two check layers with opposite economics, and the pipeline currently runs the
expensive one while most of the free one is switched off.

- **Deterministic — ~54 named findings, ~0 tokens.** `story_cut.py` (23),
  `tension_check.py` (10), `background_cut.py` (10), `map_check.py` (7),
  `outline_check.py` (4), plus `voice_drift.py`, `lexicon_check.py` and
  `fairplay_check.py` as evidence writers.
- **LLM — 6 dispatches, ~150,000 tokens per chapter per round.** Five isolated
  inspectors plus the developmental editor.

The first layer is what makes the second cheap: every fault a script names by id is a
fault no model has to hunt for by reading. Inverted, the system pays models to do
bookkeeping — verifying that a clue id exists, that a question was closed, that chapter
headings are contiguous — while the scripts that would have answered for free never run.

Separately and compounding it, the packet's continuity slice is transmitted to eight of
the eleven dispatches in a cycle, including five that never read it.

## 2. Evidence

Measured on the live series (`~/myBooks/pelicanscrook-series`, book 01, 12 review rounds
across ch-01 and ch-02).

### 2.1 What runs and what does not

| check | cost | status |
|---|---|---|
| `tension_check` — all 10 findings | free | never ran (`wired: False`; lock reads `validated: fairplay+lexicon`) |
| `voice_drift.py` | free | ran in 1 of 12 rounds |
| `lexicon_check.py` | free | ran in 1 of 12 rounds |
| `inspector-structure` thread liveness | free | impossible — no `series/continuity/threads/` |
| 5 inspectors + developmental editor | ~150k tok/round | ran every round |

The inspectors say so themselves. `inspector-voice`, ch-01 round v9b-r3: *"No
voice_drift.py evidence was supplied for this round"* and *"No lexicon-fluency.md
evidence was supplied either."* Its entire declared job is to turn that evidence into a
gate decision; it made the call blind, from scratch, eleven times out of twelve, at
~22,000 tokens a round. `inspector-structure`, same round: *"Thread-roster liveness could
not be evaluated… no thread-roster file was supplied."*

`voice_drift.py` and `lexicon_check.py` are the two scripts that do read prose, and both
are structurally forbidden from blocking (`voice_drift.py:5-6`, `lexicon_check.py:6-7`) —
they are evidence for `inspector-voice` to weigh, and `lexicon_check` routes any term
marked `auto_detectable: false` to inspector-only notes rather than counting it. The
division of labour is already correct: **the script counts, the model judges.** Turning
these on adds evidence, not false positives.

### 2.2 What a cycle costs

Eleven dispatches to produce a 1,963-word chapter. Packet: **18,216 words** — 9x the
output.

| dispatch | words in | ~tokens | carries the continuity slice? |
|---|---:|---:|:--:|
| map-maker | 18,216 | 24,227 | yes |
| drafter | 23,506 | 31,262 | yes |
| inspector-continuity | 16,136 | 21,460 | yes |
| inspector-fairplay | 18,133 | 24,116 | yes |
| inspector-structure | 16,225 | 21,579 | yes |
| inspector-voice | 16,475 | 21,911 | yes |
| inspector-ai-prose | 16,923 | 22,507 | yes |
| developmental-editor | 27,191 | 36,164 | yes |
| line-editor | 3,667 | 4,877 | |
| copy-editor | 3,375 | 4,488 | |
| ledger-updater | 9,186 | 12,217 | |
| **total** | **169,033** | **224,813** | |

One 13,866-word block — `## Continuity Extracts`, 40 entries (canon-core + 32
`background/` + 7 `characters/`) — is transmitted **eight times per cycle**: 110,928
words, **66% of a chapter's entire token bill**.

Five of the eight recipients do not use it. `inspector-structure` works from the thread
roster, `inspector-voice` from the lexicon and the `voice_drift` evidence,
`inspector-ai-prose` from the rubric and the page — none of their instructions reference
the slice. `map-maker` is proposing scene divisions and word targets.
`developmental-editor`'s own definition asks for `{draft, rubric, setting-pack,
character-bible slice, chapter brief, solution}`; `commands/review-chapter.md` hands it
the whole packet on top.

### 2.3 Where the slice's size comes from

`background/` joined `_CONTINUITY_SUBDIRS` on 2026-08-13 (`50b89d6`). That corpus is 58
files / 18,140 words — 5.3x the `characters/` corpus (9 files / 3,398 words). One chapter
pulls 39 of the 67 entries on disk:

- **20 named** in the chapter block — 9,963 words.
- **19 by one hop** — 3,069 words — none of them named in the chapter. Naming Maggie
  pulls `cal--maggie`, `faye--maggie`, `george--maggie`, `maggie--marion`,
  `maggie--saffron`, `maggie--simon`. CLAUDE.md predicted this exactly ("naming a
  protagonist pulls every relationship she is in — keep them terse").

`background/maggie.md` (1,405 words of backstory) and `characters/maggie.md` (1,496 words
of established facts) both load and overlap substantially — six people appear in both
trees, 4,541 words of background copies.

### 2.4 What the LLM layer has actually caught

Five blocking findings across 12 rounds: `inspector-continuity` 2, `inspector-fairplay` 3.
Both continuity catches trace to `characters/` — `characters/lisa.md:14` ("Maggie and Lisa
NEVER met in person") and `characters/maggie.md` — not to `background/`.

Scores: `character-voice` was **4 in all 12 rounds**. `developmental-edit` was **4 in all
11 rounds it ran**. `structure-tension` never left 4-5. `continuity-drift` ranged 1-5 and
`fairplay-planting` 2-5 — the two that found the blockers.

## 3. What is built

### 3a. Restore the free layer

1. **Turn on `tension_check`.** Blocked on the companion fix. Run it in **report mode**
   first: a 35-chapter outline never checked will produce a burst, and some findings will
   be threshold disagreements. Triage, then `--waive check-id:"reason"` (recorded on the
   certificate) rather than bending the outline. Only then let it gate.
2. **Actually run `voice_drift.py` and `lexicon_check.py` every round.**
   `commands/review-chapter.md` step 5 already specifies both; nothing asserts they ran.
   Extend the step-8 dispatch-completeness check to cover the 2a checkers, so a silent
   skip is a stop rather than an inspector improvising without evidence.
3. **Settle the thread roster.** `series/continuity/threads/` does not exist, so
   `inspector-structure`'s liveness half is permanently inert and
   `ledger_markers.py --thread-advanced` has nothing to write to. Either the directory is
   created and populated by `/finalize-chapter`, or the liveness half is switched off
   deliberately and the agent stops claiming it.

### 3b. Stop transmitting the slice to agents that do not read it

1. **A `--no-continuity` render in `packet_assemble.py`** — the same packet minus
   `## Continuity Extracts`. Used by `commands/map-chapter.md` for the `map-maker`, and by
   `commands/review-chapter.md` for the `developmental-editor` (which keeps its own
   character-bible slice and chapter brief).
2. **Drop the slice from `inspector-structure`, `inspector-voice` and
   `inspector-ai-prose`** in `commands/review-chapter.md` step 4, and from their agent
   definitions' declared inputs.
3. **Split the slice by consumer.** `background/` is drafter fuel — backstory, texture,
   how a character sounds. `characters/` is the ledger — the facts a chapter can
   contradict. The drafter gets both; `inspector-continuity` and `inspector-fairplay` get
   canon-core + `characters/` (4,363 words rather than 13,866). §2.4 is the evidence:
   both real catches came from `characters/`. Reversible per-inspector if a later catch
   proves otherwise.
4. **Require both ends named for a one-hop relationship entry.** In
   `_continuity_slice`, a hopped entry whose stem contains `--` survives only when every
   segment names an entry already matched in the chapter. On ch-01 this drops nine
   entries — `cal--lisa`, `cal--maggie`, `cal--tara`, `george--lisa`, `george--maggie`,
   `george--marion`, `lisa--saffron`, `maggie--saffron`, `saffron--tara` — 1,045 words of
   relationships between people who are not in the chapter. Non-relationship one-hop
   entries are untouched.

Result:

| | before | after |
|---|---:|---:|
| words per cycle | 169,033 | 79,652 |
| ~tokens per cycle | 224,813 | 105,937 |
| 40-chapter book, one pass | ~8.0M | ~4.0M |

**53%**, and every cut removes an input the receiving agent's own definition does not ask
for. No check is deleted, no inspector stops running, no gate judgment changes.

### 3c. The roster decision — deferred, on purpose

**Keep** `inspector-continuity` and `inspector-fairplay`: they found all five blockers.
**Keep** `inspector-ai-prose`: it is the only check for rote LLM prose, which no script
can see, and the drafter is an LLM. Never blocking is not the same as never earning.

**Re-evaluate** `inspector-voice` after 3a.2 and `inspector-structure` after 3a.1/3a.3.
Both look like no-ops on the scores and both have never had their declared inputs;
judging them now would be judging a check that has never run properly. Expect the outcome
to be a sampled cadence rather than deletion.

**Make `developmental-editor` opt-in** — first draft of a chapter, or on request. It is
the single most expensive dispatch (36,164 tokens), advisory by design, and scored 4 in
every round it ran.

## 4. Decisions settled

- **No deterministic finding is deleted.** The rosters stay at twenty-three
  (`story_cut`), ten (`tension_check`), seven (`map_check`), ten (`background_cut`).
- **No change to the `^BLOCKING:` convention, `review_gate.py`, locks or certificates.**
- **No change to the isolation, independence or cross-model rules.** Narrowing an
  inspector's inputs is isolation working as designed (§ "Independence, isolation, reader
  simulation"): fewer inputs, never another inspector's reasoning.
- **The slice split is by consumer, not by deletion.** `background/` is not removed from
  the series or from the drafter; it stops being sent to graders whose job it is not.
- **Report mode before gating** for `tension_check`, because the alternative is a first
  run that blocks a lock on ten checks nobody has read yet.

## 5. Test

1. `packet_assemble --no-continuity` emits a packet identical to the full one minus the
   `## Continuity Extracts` section, and its manifest-bearing sibling headings are intact.
2. `_continuity_slice` both-ends rule: a fixture where `a--b` is linked from `a` and `b`
   is absent excludes `a--b`; where both are named, includes it; a non-relationship
   one-hop entry is unaffected.
3. The consumer split: a slice requested for an inspector contains canon-core and
   `characters/` and no `background/` entry; a slice requested for the drafter contains
   both.
4. Contract tests on the runbooks, in the shape of `tests/test_drafter_loads_voice_pack.py`:
   `review-chapter` does not name the slice as an input to structure/voice/ai-prose;
   `map-chapter` dispatches `map-maker` with the no-continuity render.
5. The step-8 completeness assert fails when `voice-drift.md` or `lexicon-fluency.md` is
   absent from the reviews dir.

## 6. Blast radius

Packets are stamped `built_from_outline` / `built_from_whodunit` and maps carry
`built_from_packet`; `preflight draft` refuses a stale chain. Adding a render **variant**
must not change the stamped packet on disk — the `--no-continuity` form is a dispatch-time
projection, never a second artefact, or every map in the series goes stale at once.

`_continuity_slice` narrowing changes the packet's content and therefore its sha256, which
does invalidate existing maps by design. Land it deliberately, at a chapter boundary, and
expect to re-run `/map-chapter` for any chapter mapped but not yet drafted.

Nothing here touches `series/`, `input/`, `output/` content, or any certificate.
