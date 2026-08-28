# voice_drift discards the evidence it computes

Date: 2026-08-27
Status: defect, fix brief — not a feature proposal
Severity: medium — not silent, but it degrades every voice inspection

Filed in `specs/` rather than `backlog/` deliberately: `docs/backlog/README.md` excludes
defects. This is a defect; it is written up because the fix has a small design choice in it
and because the invariant in §4 is worth agreeing before it is coded.

## 1. Why

`voice_drift.py` is evidence-only by design. Its own docstring says so, and
`/review-chapter` restates it: *"`lexicon_check.py` is evidence-only… `inspector-voice`
weighs the evidence and makes the blocking call."* The script reports magnitude; the
inspector decides whether it harms the read.

That contract only works if the flag comes with evidence. Three tics hard-code an empty
evidence list:

```python
# scripts/voice_drift.py:133   sentence_variance
"evidence_spans": [],
# scripts/voice_drift.py:165   cinematic_fragments
"flagged": frag_clusters > max_clusters, "evidence_spans": []})
# scripts/voice_drift.py:183   lexical_repetition
"flagged": bool(lex_flagged), "evidence_spans": []})
```

`lexical_repetition` is the worst of the three, because it **computes precisely which words
repeat and then throws that away.** Both counters are in hand two lines earlier:

```python
# scripts/voice_drift.py:170-174
openers = Counter((_words(s)[0].lower() if _words(s) else "") for s in sentences)
top_opener = max(openers.values(), default=0)
content = [w.lower() for w in words if w.lower() not in _STOP and len(w) > 3]
cw_counts = Counter(content)
top_cw_count = max(cw_counts.values(), default=0)
```

`openers` and `cw_counts` hold the answer. Only `max()` survives into the verdict.

A second, smaller problem: the tic reports `count` from the **opener** measurement and
`density_per_1k` from the **content-word** measurement, so one row mixes two different
findings and the reader cannot tell which one tripped the flag.

## 2. Evidence from a real book

Pelican's Crook, book 01, chapter 01, reviewed 2026-08-27. `voice-drift.md` emitted:

```
- lexical_repetition: 16 (density 12.62/1k, threshold 3) FLAGGED
evidence:
  - {"line": 32, "span_text": "could see", "tic_id": "filtering_verbs"}
  - {"line": 52, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 60, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 76, "span_text": "not quite", "tic_id": "soft_qualifiers"}
```

The only FLAGGED tic in the chapter contributed **zero** of the four evidence spans. Every
span belongs to a tic that passed comfortably inside threshold.

What the checker actually found, recovered by rerunning its own logic by hand:

```
top sentence openers: [('the', 16), ('she', 16), ('it', 10), ('there', 3), ('maggie', 3)]
top content words:    [('could', 10), ('about', 10), ('down', 10), ('there', 10), ('maggie', 10)]
```

**16 of the chapter's 89 sentences open with "The" and another 16 with "She" — 36% of the
chapter beginning with one of two words.** That is a real, actionable voice finding, exactly
the kind of rhythm problem the Voice Pack legislates against (*"Rule of thumb: if a paragraph
has four sentences of roughly equal length, at least one is wrong"*).

**Observed cost.** `inspector-voice` was dispatched with an explicit instruction to
investigate the unevidenced flag itself rather than defer to the count. It did the work and
returned a well-argued 4/5 — correctly identifying that *"forward and down, forward and
down"* is deliberate and that the counted award/house/kiln inventory is a required
structural beat, and separately catching a genuine tic the checker never looks for (the
frame *"the way [clause]"*, four times).

**It never found the 16/16 opener problem.** Given no spans, it reasoned about repeated
*phrases* and never thought to tabulate sentence openers — the one thing the checker had
already measured. So the checker computed a real finding, discarded it, and the discard
propagated: the human-style read went looking in the wrong place.

That is the cost of an unevidenced flag. It is not merely unhelpful; it actively misdirects.

## 3. Fix

**3a. Populate `evidence_spans` for `lexical_repetition`.** Emit the offending opener and
the offending content words, with line numbers, using the counters already computed. A
reasonable shape:

```
{"tic_id": "lexical_repetition", "span_text": "sentence opener \"The\" ×16", "line": <first>}
{"tic_id": "lexical_repetition", "span_text": "sentence opener \"She\" ×16", "line": <first>}
{"tic_id": "lexical_repetition", "span_text": "content word \"could\" ×10", "line": <first>}
```

Cap consistently with the existing `spans[:5]` convention at `:93`.

**3b. Split the mixed row.** `lexical_repetition` measures two independent things against
two independent thresholds (`opener_repeat_flag_at`, `content_word_per_1k_flag_at`). Emit
them as two tics — `repeated_openers` and `repeated_content_words` — so `count` and
`density_per_1k` each describe the measurement they belong to, and the inspector can see
which threshold tripped.

This changes the tic vocabulary, so `config/review-rubrics/character-voice.md` and any
rubric naming `lexical_repetition` need updating in the same change.

**3c. Populate the other two.** `sentence_variance` should cite the longest run of
near-equal-length sentences; `cinematic_fragments` should cite the offending cluster. Both
already know where they are.

## 4. The invariant worth agreeing

Add an assertion, and a test for it:

> **A tic with `flagged: True` and an empty `evidence_spans` is a bug.**

Enforced at the top of `_flatten_evidence` (`:190`) or in `main` before the verdict is
written, this makes the entire class of defect impossible rather than fixing three
instances of it. It also protects the `/review-chapter` contract, which assumes flags are
weighable.

Unflagged tics may legitimately carry no spans; the invariant applies only to flags.

## 5. Test

1. A chapter fixture with 10 sentences all opening "The" asserts `repeated_openers` is
   flagged **and** that its evidence names `"The"` with a line number.
2. A fixture exercising each of the three currently-empty tics asserts non-empty evidence
   when flagged.
3. A property-style test over any fixture: no tic may be `flagged` with empty
   `evidence_spans`. This is the §4 invariant and is the one that matters.

## 6. Note for whoever picks this up

Book 01 ch 01 remains a live reproduction: `output/book-01/chapters/ch-01.draft.md` in the
Pelican's Crook series, 89 sentences, 16/16 openers. Its `voice-drift.md` verdict is on
disk and shows the empty-evidence flag as filed.
