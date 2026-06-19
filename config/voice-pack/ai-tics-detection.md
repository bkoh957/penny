# AI-Tics Detection — prose companion (NON-PARSED)

> **This file is documentation only and is never parsed by code.** The authoritative,
> machine-read values live in `ai-tics-config.yaml` (thresholds + the compounding
> `banned_phrases` / `metaphor_pool` lists). Detection patterns live in
> `scripts/voice_drift.py`. Where a number appears both here and in the YAML, the
> YAML wins.

`voice_drift.py` is **evidence-only**: it counts tics and flags densities over
threshold, but never emits a blocking verdict. The blocking decision belongs to the
Tier-C voice inspector (Phase 2b), which reads this evidence.

## The seven tic categories
1. **Bodily reactions** — "her heart pounded", "breath caught", "stomach twisted".
   Frequency tic: one is fine, repetition is the failure.
2. **Wave / emotional-noun templates** — "a wave of grief washed over", "a sense of dread".
3. **"Something" language** — "something shifted between them", "something in his eyes".
4. **Filtering verbs** — "she noticed/realized/could feel" — distance from direct experience.
5. **Soft qualifiers** — "almost", "somehow", "as if" — hedging that drains conviction.
   Cluster rule: 2+ in one sentence is always flagged.
6. **Cinematic fragments** — runs of ultra-short verbless sentences ("A pause. A breath.").
7. **Emotional-metaphor pool** — overused source domains (wave, storm, knife, thread…).
   Keyword-count in MVP; LLM-classifier graduation is deferred.

Plus two statistical measures: **sentence-length variance** (flag monotone rhythm) and
**lexical repetition** (over-repeated content words / sentence openers).
