# Line-Edit Rubric [STABLE]

> Scope: sentence-level refinement only. No new content. No story changes.
> Design §7. Consumed by `.claude/agents/line-editor.md`.

## What to refine

### Flab cuts
- Remove redundant qualifiers ("very", "quite", "rather", "somewhat", "a little").
- Delete throat-clearing openers ("It was the case that", "There was a", "She found herself").
- Convert zombie nouns back to verbs where the sentence allows ("make a decision" → "decide").

### Verb strengthening
- Favour specific active verbs over "was/were + past participle" when the passive adds no emphasis.
- Replace vague motion verbs ("went", "moved", "came") with precise ones where context supplies them.
- Do NOT strengthen a weak verb if the weakness is deliberate register (e.g., Cora being deliberately understated).

### Rhythm
- Vary sentence length: long sentences carry weight; short sentences land punches. A run of same-length sentences is flat.
- Do not open consecutive sentences with the same word or grammatical structure (enforced statistically by `voice_drift.py` in Phase 2 — but fix obvious cases here).
- Read each paragraph aloud mentally; if a sentence trips, re-scan for a tongue-tangling cluster.

### Dialogue tags
- "Said" and "asked" are invisible. Use them. Substitute only when the beat genuinely demands it.
- Cut adverbs on dialogue tags ("she said softly") and move the beat into action or context.

## What to leave alone

- Meaning. If a sentence is ambiguous, preserve the ambiguity.
- Voice. Cora's register is precise and lightly formal with warmth through observation. Do not warm it up or cool it down.
- Clues, red herrings, beats. If something reads as deliberate plant, leave it.
- Word count: keep the chapter within [chapter_min_words, chapter_max_words] from `config/length-profile.md`.
- POV discipline: third person limited, past tense, Cora's perspective.

## Move checklist (pass in order)

1. [ ] Read Voice Pack before starting.
2. [ ] Cut flab (qualifiers, throat-clearing, zombie nouns).
3. [ ] Strengthen verbs (where safe — see above).
4. [ ] Fix rhythm monotony (sentence-length variance).
5. [ ] Tighten dialogue tags.
6. [ ] Verify word count in range.
7. [ ] Confirm no new content was added.
