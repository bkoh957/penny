---
producer: inspector-voice
kind: inspector
target: book-01/ch-02
schema: penny-verdict/1
score: 5
---

- Flat-voice blind test PASS: with tags removed the principals are unmistakable. Faye = brisk, run-on, imperative, gossip-comic ('Are you going to let me in, or are we doing this on the step?'); Mary = gentle, measured, parable-like, withholds the point until the doorway ('I give it to people I think might stay'); Mara = terse, conviction, no heat ('It has been here longer than the road and it will be here after'); Maggie = clipped, guarded, HR-trained reticence. No two are interchangeable.
- voice_drift lexical_repetition FLAGGED (14, density 12.2/1k) judged BENIGN, not harmful drift: the repeats are deliberate rhetorical patterning, not monotone ("someone's town and someone's kitchen and someone's morning"; the anaphoric "the way ... the way ..."; "warm as the bread had been warm"). sentence_variance is healthy (stdev 19.45). soft_qualifiers (8) under threshold. No drift call.
- Fluency stage OUTSIDER respected. Local idiom lives only in dialogue ("crook" = unwell, "sea-change", "dear" — all in Faye's mouth). Maggie's narration is standard English throughout.
- WATCH (non-blocking): "op-shop" appears in a narrative clause at line 25. Judged a benign free-indirect collision, not a stage break — the whole paragraph explicitly relays Faye's tour ("Faye was deciding what Maggie needed first"), so the term is the local's framing channelled through summary, not Maggie adopting idiom in her own voice. Flag if this pattern recurs in non-reported narration.
- lexicon_check reported 0 premature-term flags (stage OUTSIDER); concur.
metrics: {"blind_test": "pass", "drift_call": "no", "principals_distinct": 4, "stage": "OUTSIDER"}
evidence:
  - {"judgment": "benign-FID-not-stage-break", "line": 25, "span_text": "op-shop"}
  - {"judgment": "Faye voice distinct", "line": 19, "span_text": "Are you going to let me in, or are we doing this on the step?"}
  - {"judgment": "Mary voice distinct", "line": 93, "span_text": "He measures everything twice. His father was the same."}
  - {"count": 14, "judgment": "deliberate-anaphora-benign", "tic_id": "lexical_repetition"}
