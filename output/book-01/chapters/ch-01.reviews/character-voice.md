---
producer: inspector-voice
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 5
---

- Blind test PASS: Cal and Maggie dialogue is immediately distinguishable without tags. Cal's speech is functional trade shorthand (contracted, measurement-driven, subjectless fragments). Maggie's two spoken lines are bare and held-back — a different register entirely.
- Lexical repetition 31 (flagged by voice_drift.py): NOT harmful. Repetitions are spatial anchors (kiln, shelves, apron, sea, clay, door) appropriate to a chapter in which the protagonist is inventorying a new space. Anaphoric construction in the HR-face passage ('she had been... she had sat... she had kept it on') is deliberate stylistic accumulation, not monotony. Repetition earns its keep.
- Fluency-stage (OUTSIDER): CLEAN. Maggie's narration is standard English throughout. 'Grog-proof' (l.1) is colloquial Australian English a Melbourne HR director would use, not a Pelican's Crook local idiom — no insider-belonging signal. Local idiom ('she'll hold fine', 'd'you want them') is correctly confined to Cal's mouth.
- Voice-drift checkers all clean (0 flags) except lexical_repetition; lexical_repetition judged benign (see above).
- Principal voices: Maggie (warm, observant, dry, accumulating grief-by-HR-face), Cal (laconic, measurement-centric, practically expressive), Glaze the cat (behaviour only — property-inspection framing is nicely rendered). Three principals, three legible registers.
- Rhythm: Maggie's narration alternates long wound-up sentences with short declarative cutoffs ('The eucalypts had not offered any insight. She had started the car again.'). Cal's speech arrives in the gaps it needs. Variance is structural, not accidental.
- reviewed_by: claude-sonnet-4-6
metrics: {"filtering_verbs": 1, "fluency_stage": "OUTSIDER", "lexical_repetition": 31, "premature_terms": 0, "sentence_stdev": 17.06, "soft_qualifiers": 3}
evidence:
  - {"check": "blind_test", "note": "Cal trade-shorthand vs Maggie held-back register; no interchangeability", "principals": ["Maggie", "Cal"], "result": "PASS"}
  - {"check": "lexical_repetition", "count": 31, "judgment": "benign \u2014 spatial anchoring and anaphoric accumulation; not monotony"}
  - {"check": "fluency_stage", "note": "grog-proof ruled non-local; all local idiom in Cal dialogue only", "stage": "OUTSIDER", "violations": 0}
  - {"check": "voice_drift", "other_flags": 0, "verdict": "no drift concern"}
