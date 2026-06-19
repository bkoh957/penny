# AI-Tics Detection List — Tier A (Deterministic)

**Layer:** `/config/voice-pack/` · consumed by `/scripts/voice_drift.py` and the
compounding banned-phrase/metaphor list (P1.3).
**Posture:** counts, not vibes. These are **frequency** problems, not presence
problems — one instance is fine, the failure is repetition. The drafter is bad at
holding a running count and rationalizes each instance locally; a script counts
dispassionately. None of these belong in the self-audit.

**Tuning note:** all thresholds below are **per-1000-words seeds**, calibrated
during Book 1 against real verdict distributions — not load-bearing constants.
Genre-tunable: a literary series may relax several of these; a cozy mystery should
hold them tight.

---

## How this file is used

Each entry declares a **pattern** (regex or closed lexical set) and a **threshold**
(density per 1000 words, or a clustering rule). `voice_drift.py` reports a count
and a flag when density exceeds threshold. Flags are **statistical evidence for
the gate**, surfaced as Tier-3 checker output, not an automatic block — they feed
the inspector's blocking decision and the revision-priority report.

---

## 1. Generic bodily reactions

Closed dictionary, fuzzy-matched (subject + verb).

```
heart (pounded|hammered|raced|thudded|skipped|clenched)
breath (caught|hitched|stilled)
chill (ran|crawled|went) (down|up) (her|his|their) spine
stomach (twisted|dropped|knotted|churned|lurched)
throat (tightened|closed|went dry)
blood (ran cold|froze)
pulse (quickened|jumped)
```

- **Threshold:** ≤ 2 per 1000 words. Flag at 3+.
- **Compounding:** every novel variant caught is appended to this list, so the
  list grows across the 13 books (the Penny effect).

## 2. Vague emotional nouns + "wave" templates

```
a (wave|surge|flood|rush|tide|swell) of \w+ (washed|swept|came|rolled|crashed) over
a (deep |profound |strange )?sense of (unease|dread|loss|longing|foreboding)
felt a (pang|stab|flicker|wave) of
```

- **Threshold:** ≤ 1 per 1000 words. Flag at 2+.

## 3. "Something" language

```
\bsomething\b   (when subject or object of a clause about feeling/change/perception)
something (shifted|changed|passed) between them
something in (his|her|their) (voice|eyes|face|expression)
```

- **Threshold:** ≤ 1 emotionally-loaded "something" per 1000 words. Flag at 2+.
  (Do not count literal uses — "something to eat.")

## 4. Filtering verbs

Closed set. Distances the reader from direct experience.

```
noticed | realized | could feel | could see | could hear | found (himself|herself|themselves)
watched as | saw that | felt herself | seemed to | began to
```

- **Threshold:** ≤ 3 per 1000 words. Flag at 4+.

## 5. Soft qualifiers

Closed set. Hedging that drains conviction.

```
almost | somehow | slightly | seemingly | for a moment | as if | something like
a little | not quite | as though | in a way
```

- **Threshold:** ≤ 4 per 1000 words. Flag at 5+. (Cluster rule: 2+ in one sentence
  is always flagged regardless of overall density.)

## 6. Cinematic fragments

Runs of ultra-short verbless sentences. Extends the existing sentence-length
variance check.

- **Rule:** flag any cluster of **3+ consecutive sentences under 4 words** where
  at least two are verbless. ("A pause. A breath. Then silence.")
- **Threshold:** ≤ 1 such cluster per chapter. Effective once; generated when
  repeated.

## 7. Emotional-metaphor pool

Maintained list of overused source domains for emotion.

```
wave(s) | storm | weight | knife | thread | shadow | flame | spark | abyss | hollow
```

- **Rule:** count emotional metaphors drawing on this pool; flag when 3+ per
  chapter draw from the same domain, or 5+ total draw from the pool.
- **Compounding:** this is the primary home of the P1.3 "avoid its own tics"
  mechanism — every repeated metaphor Penny reaches for gets added here.

---

## Output contract (to the gate)

```
voice_drift.py emits, per chapter:
  { tic_id, count, threshold, density_per_1k, flagged: bool, evidence_spans[] }
```

Flagged items appear in `ch-NN.reviews/` as Tier-3 evidence and in the
revision-priority report. A flag is **evidence**, not an automatic blocking issue;
the blocking decision stays with the inspector reading the rubric in §8.
