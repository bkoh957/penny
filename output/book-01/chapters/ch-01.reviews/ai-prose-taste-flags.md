---
producer: inspector-ai-prose
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 4
---

- No blocking-density figuration. Voice is dry, specific, and largely earns its texture; only one genuinely rote tell, below the 3-instance threshold.
- Flag 5 (closing cadence) ROTE but isolated: "Maggie Quill allowed herself something she hadn't felt in a long time. / Not happiness, not yet. Just the possibility of it." (L97-99) is near-identical in shape to the rubric example ("for the first time in years, she allowed herself to hope"). The specific final line "She did not close the door." (L101) partially redeems it, but the summation beat is stock uplift-resolution.
- Flag 1/cadence (EARNED, noted): the "not X, (not Y,) just Z" construction recurs 3x (L17 'not dramatic, just very large'; L67 'not threatening, not especially beautiful, just present'; L99 'Not happiness, not yet. Just the possibility'). Each instance does concrete work individually; the repetition is a frequency-tic concern (Tier A), not a per-instance taste fault.
- Flags 1-3 otherwise EARNED: 'travelling light was a virtue and not a diagnosis' (L9), 'emptiness that a room has when it's waiting rather than abandoned' (L19), 'the way the sea is when it decides to be the main fact of a place' (L17), 'the colour of the sea doing its own business' (L67) are specific to this place/character and not liftable into another book.
- Flag 2 interpretive endings are controlled and witty rather than instructive: 'The eucalypts had not offered any insight.' (L11), 'The kiln remembered all of it and said nothing.' (L43) — earned voice, not hand-holding.
- Flag 4 (airless): does NOT fire. Rhythm varies; many sentences are allowed to do one thing ('She left those in the boot.' L41; 'She did not move him.' L93). Prose breathes.
metrics: {"airless_passage": false, "blocking_threshold": "3+ across flags 1-3/5 or any full-scene airless", "rote_instances_flags_1_3_5": 1}
evidence:
  - {"call": "rote", "flag": 5, "line": "97-99", "quote": "allowed herself something she hadn't felt in a long time. Not happiness, not yet. Just the possibility of it."}
  - {"call": "earned-but-repeated", "flag": "1/cadence", "lines": "17,67,99", "note": "not X, (not Y,) just Z recurs 3x"}
  - {"call": "earned", "flag": 3, "line": 17, "quote": "the way the sea is when it decides to be the main fact of a place"}
  - {"call": "earned", "flag": 2, "line": 43, "quote": "The kiln remembered all of it and said nothing."}
  - {"call": "not-present", "flag": 4, "note": "rhythm varies; single-purpose sentences present"}
  - {"reviewed_by": "claude-opus-4-8"}
