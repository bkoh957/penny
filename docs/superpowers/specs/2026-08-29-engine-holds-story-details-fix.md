# The engine still holds one series' story details

Date: 2026-08-29
Status: defect, fix brief — not a feature proposal
Severity: medium-high — one live contradiction reaching a prose agent on every chapter;
the rest is latent

Filed in `specs/` rather than `backlog/` deliberately: `docs/backlog/README.md` excludes
defects. Written up rather than silently patched because it recurs — see §6 — and because
the lint in §4 needs agreeing, not just coding.

Related: `2026-08-13-background-history-source-layer-design.md` fixed this same stale
protagonist in `config/setting-pack/` by making that file derived. **It did not reach the
engine's own craft configs**, and this spec is the remainder of that work.

## 1. Why

`CLAUDE.md:11-14` states the rule, and calls it non-negotiable:

> The non-negotiable architectural rule: **the engine is genre/location-agnostic —
> everything project-specific lives in a swappable genre pack or per-series folder, never
> in `scripts/` or the command/agent logic.** When adding behavior, ask whether it belongs
> to the fixed engine, to a genre, or to one series' own data, and keep them separate.

Twelve sites under `config/` and `agents/` violate it. They name characters — a superseded
protagonist called **Cora**, superseded characters called **Dez** and **Renna**, and, in one
place, the *current* series' protagonist **Maggie** — and in six cases state facts about them
as if they were craft rules binding on whatever book is running.

This is not a style complaint. One of them actively contradicts the active series' Voice
Pack, and it reaches a prose agent that rewrites the manuscript.

**Amended 2026-08-29 after review.** This spec first said ten sites. Two more were found by
running §5's proposed lint against the tree — the review's own account of that is in §3's
Category C and §5. That the manual sweep missed two is not an embarrassment to be quietly
corrected; it is the argument of §6, and it is left visible here on purpose.

## 2. The live harm

`config/line-edit/line-edit.md:30`, under a heading reading **"What to leave alone"**:

> - Voice. **Cora's register is precise and lightly formal with warmth through
>   observation.** Do not warm it up or cool it down.

`/finalize-chapter` step 1 dispatches `line-editor` with **both** that file and
`config/voice-pack/voice-pack.md`. The Pelican's Crook voice pack says:

> Default register is **James**: compound sentences that build, with subordinate clauses
> that earn their length. The surprise is in the arrival — the sentence sets up a direction
> and lands somewhere slightly unexpected.

So the agent receives two mutually exclusive register instructions, one of them naming a
character who does not exist in the book being edited, and both filed under "what to leave
alone". There is no precedence rule telling it which wins.

**The failure mode is specific and expensive.** Book 01 chapter 01's central plant is a
building compound sentence:

> It had always been going to be next year, and there had been a great many next years, and
> she had been reasonable about every one of them.

That is textbook James register, and it is the plant half of a plant/tell pair paid off in
chapter 10. A line editor obeying "precise and lightly formal — do not warm it up" could
reasonably compress it to two clean short sentences and destroy the payoff, while believing
it was following its checklist.

On 2026-08-29 this was avoided only because the dispatching session hard-coded an override
into the prompt, telling the agent to disregard every Cora reference and that the Voice Pack
wins. **That workaround is not in any file.** It has to be remembered on each of the
remaining 34 chapters of book 01, and on every chapter of every later book.

## 3. The twelve sites

**Category A — story facts stated as craft rules (6).** These assert things about a specific
protagonist as though universally true:

| File | Line | Text |
|---|---|---|
| `config/line-edit/line-edit.md` | 30 | "Cora's register is precise and lightly formal…" — §2, the live harm |
| `config/line-edit/line-edit.md` | 33 | "POV discipline: third person limited, past tense, Cora's perspective." |
| `config/line-edit/line-edit.md` | 16 | "…deliberate register (e.g., Cora being deliberately understated)." |
| `agents/line-editor.md` | 25 | "No POV breaks (third-person limited, past tense, Cora's perspective)." |
| `config/copy-edit/copy-edit.md` | 14 | "…and Cora's deceased husband's name are never variant-spelled." |
| `config/review-rubrics/character-voice.md` | 23 | "no local idiom in Cora's narration" |

The copy-edit one is worth noting: Pelican's Crook's protagonist has a **living** ex-husband,
Nick Hartley. The engine instructs the copy-editor to guard the spelling of a dead man who
does not exist in this or any current series.

**Category B — worked examples using a character name (5).** `Dez`, in
`config/story-craft/writing-beats.md:32,34,79` and
`config/story-craft/writing-chapter-frames.md:42`; and `Renna`, in
`config/story-craft/writing-beats.md:51` ("Renna's premises fear surfaces through print-shop
work and customer rhythm rather than exposition"). Defensible — examples need a subject — but
a role noun costs nothing and cannot be mistaken for canon.

**Category C — the CURRENT series' protagonist, in an engine file (1).**

| File | Line | Text |
|---|---|---|
| `agents/outline-expander.md` | 115 | "Book 1 = OUTSIDER: no local idiom in **Maggie's** narration; idiom lives in locals' dialogue only" |

This one deserves its own category because every instinct that finds Category A misses it.
Maggie **is** the live series' protagonist (`canon-core.md:18`), so the line reads as correct
to anyone checking it today, contradicts nothing, and produces no symptom. It is wrong in the
same way as the others and will only announce itself when a second series exists — at which
point the engine will instruct that series' outline-expander about a character it has never
heard of.

It is also the same craft rule as `config/review-rubrics/character-voice.md:23` ("no local
idiom in Cora's narration"), written twice, for two different series' protagonists, one
superseded and one live. That the two copies disagree about who the protagonist is, and that
neither is right in general, is the whole defect in one pair of lines.

**The lesson for the fix:** "is this name stale?" is not the test. The test is "does an
engine file name a character at all?" — which is what §5 has to enforce, because a human
sweep looking for *stale* names will pass straight over a current one.

## 4. Fix

### 4a. Category A — delete the fact, defer to the series pack

The engine states craft *mechanics*; the series states story *facts*. Each site loses its
character and points at the authoritative source:

```diff
-- Voice. Cora's register is precise and lightly formal with warmth through observation. Do not warm it up or cool it down.
+- Voice. The protagonist's register is defined by the series Voice Pack. Do not warm it up or cool it down.

-- POV discipline: third person limited, past tense, Cora's perspective.
+- POV discipline: hold the POV, tense and anchor specified in the series Voice Pack.

-- Do NOT strengthen a weak verb if the weakness is deliberate register (e.g., Cora being deliberately understated).
+- Do NOT strengthen a weak verb if the weakness is deliberate register (e.g., a protagonist written as deliberately understated).

-- No POV breaks (third-person limited, past tense, Cora's perspective).
+- No POV breaks — hold the POV, tense and anchor specified in the series Voice Pack.

-   OUTSIDER: no local idiom in Cora's narration; a BELONGING-tagged term in early
+   OUTSIDER: no local idiom in the protagonist's narration; a BELONGING-tagged term in early
```

The copy-edit line is **generalised rather than deleted**, because the underlying craft point
is real — a name that appears only in backstory is the easiest kind to drift:

```diff
-- Proper nouns: match the ledger entry exactly. Character names, place names, business names, and Cora's deceased husband's name are never variant-spelled.
+- Proper nouns: match the ledger entry exactly. Character names, place names and business names are never variant-spelled — including names that appear only in backstory or dialogue and never in a scene.
```

### 4b. Add an explicit precedence rule

Even with the names gone, nothing tells an agent what to do when the engine checklist and a
series pack disagree. Add to `config/line-edit/line-edit.md` and `config/copy-edit/copy-edit.md`:

> **Precedence.** This checklist states craft mechanics. Where it appears to conflict with
> the series Voice Pack, style sheet, or setting pack on any matter of voice, register, POV
> or story fact, **the series file wins.** This file never states a fact about a character.

That converts a silent contradiction into a resolvable one.

**This is the strongest element of the fix, and it should be done first.** It is the only
part that would have prevented §2 *regardless of the names* — a line editor holding two
contradictory register instructions needs a precedence rule, not a rename. It is also the
only part that keeps working for Category C: when the engine names the current protagonist,
nothing is stale and nothing contradicts, but "the series file wins, and this file never
states a fact about a character" still tells the agent to disregard it. Renames fix the
twelve instances; the precedence rule fixes the shape.

### 4c. Category B — role nouns

`Dez's thread` → `The carpenter's thread`; `Dez pocketed the key` → `The locksmith pocketed
the key`; `[12] Dez throws the cup` → `[12] The potter throws the cup`; and
`Renna's premises fear surfaces through print-shop work` → `The printer's premises fear
surfaces through print-shop work`.

### 4d. Category C — the same treatment, and it is not optional

`agents/outline-expander.md:115` loses the name the same way Category A does:

```diff
-   canon-core (Book 1 = OUTSIDER: no local idiom in Maggie's narration; idiom lives in
+   canon-core (Book 1 = OUTSIDER: no local idiom in the protagonist's narration; idiom lives in
```

Resist the argument that this one is harmless because the name is currently right. Being
right by coincidence is the property that hides it, and `config/review-rubrics/character-voice.md:23`
is the proof of where that ends: the same sentence, kept until the name it contained had been
wrong for months.

## 5. The lint — what stops this recurring

Renames fix today. They do not stop the next one, and there has already been a next one
(§6).

**Amended 2026-08-29 after review — the original proposal was measured and does not work.**

The first draft of this section proposed failing on any capitalised word outside a small
allowlist of craft vocabulary, sentence-initial words and known proper nouns, and argued that
the tuning to quieten it "is the point". That was implemented and run against the tree:

> **385 hits across 35 files.** The most frequent are `State`, `Knowledge`, `Title`,
> `Reader`, `Clues`, `Texture`, `Plants`, `Guardrails`, `Required` — every one of them
> legitimate engine vocabulary or a section name.

The allowlist would have to grow until it contained substantially the whole engine
vocabulary, at which point it catches nothing new, and a lint at that signal-to-noise ratio
is switched off within a week. Rejected.

**Use the possessive instead.** Fail on `\b[A-Z][a-z]+'s\b` — a capitalised word in the
possessive — under `config/` and `agents/`. Measured against the same tree:

> **11 hits.** Eight are real sites, including **both of the two this spec's own manual sweep
> missed**. Three are craft nouns that go in the allowlist: `Reader's` (×2), `Hook's`.

The possessive is the right signal because it is how a story fact almost always enters a
craft doc: *Cora's register*, *Cora's perspective*, *Cora's narration*, *Cora's deceased
husband's*, *Dez's thread*, *Renna's premises*, *Maggie's narration*. A craft document has
very little other reason to write a proper noun in the possessive.

It misses four of the twelve — the three `Dez`-as-subject examples
(`writing-beats.md:34,79`, `writing-chapter-frames.md:42`) and `line-edit.md:16`'s
parenthetical "(e.g., Cora being deliberately understated)". Accept that. §4a and §4c sweep
those by hand, and a lint that catches eight and stays enabled is worth more than one that
catches twelve and gets disabled. The allowlist becomes the explicit record of which
possessives the engine is permitted to write — a short, meaningful list rather than a
transcription of its vocabulary.

This turns a class of bug that currently surfaces **eighteen chapters later, by accident,
during an unrelated investigation** into a CI failure at the commit that introduces it.

## 6. Why this needs the lint rather than another sweep

This is the third pass at the same defect — and the review of this very spec is the evidence,
because the sweep in §3 missed two sites and the lint in §5 found them both within seconds of
being run. A fourth careful reading would not have found `Maggie's narration`: it is not
stale, it contradicts nothing, and it looks right.

The three passes: 

1. Before 2026-08-13, `config/setting-pack/` described "a town called Wreckers Bluff and a
   protagonist called Cora" while the live series was Pelican's Crook and Maggie.
2. `2026-08-13-background-history-source-layer-design.md` fixed that by making the setting
   pack **derived** from authored canon — correct by construction, and it has held.
3. It did not reach `line-edit/`, `copy-edit/`, `review-rubrics/`, `story-craft/` or
   `agents/line-editor.md`, because those are engine files rather than series data, and
   nothing derives them from anything.

The 2026-08-13 fix worked precisely because it removed the possibility of drift rather than
correcting an instance of it. These twelve sites cannot be made derived — they are engine
craft docs and should be — so the equivalent structural guarantee is the lint.

There is also no series-level escape hatch. The only existing series carries `beta-readers`,
`genre-pack`, `length-profile.md`, `run-config.md`, `setting-pack` and `voice-pack` in its
own `config/`, and no `line-edit/`, `copy-edit/` or `review-rubrics/`. So the engine's
copies are always the ones in force, with nothing shadowing them.

## 7. Provenance of this note

These sites were found on 2026-08-27 while investigating where a texture punch-up pass would
attach, and were recorded as an **appendix** to
`2026-08-27-texture-allocation-design.md` — a document about something else. The texture
design was then implemented in full (`5837d64` and following) and the appendix was not
actioned, because appendix material in a spec about another subject is not a work item.

Filing it as its own defect spec is the correction to that.
