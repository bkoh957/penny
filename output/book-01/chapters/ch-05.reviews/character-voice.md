---
producer: inspector-voice
kind: inspector
target: book-01/ch-05
schema: penny-verdict/1
score: 4
---

- BLIND TEST PASS: Cal (laconic, physical, <=6-word declaratives) and Maggie (analytical, calibrated-defensive) are distinguishable without dialogue tags; Dot/Glad double-act has its own rhythm; no principal voices are interchangeable
- DRIFT CALL — lexical_repetition flagged (19 instances, density 14.28/1k, threshold 3): repetitions are structural — coffee-cup arc tracks migraine onset, tea-towel repetition is the ch-7 keystone clue plant; earned, not rote; no harm to read
- DRIFT CALL — soft_qualifiers: 9 instances, density 3.78/1k, below threshold 5; hedging is character-appropriate for an uncertain newcomer; no violation
- DRIFT CALL — sentence_variance 18.97 (threshold 4.0): strong rhythm variation throughout; narration correctly shifts from long analytical cadences to short punchy beats; clean
- FLUENCY STAGE PASS (OUTSIDER): narration is standard English throughout; zero premature-term flags from checker; local colour ('lamingtons', community nicknames) is setting vocabulary or in other characters' mouths, never Maggie's idiom layer
- Faye has no spoken dialogue this chapter; her on-page presence (facial expression 'a door easing shut from the inside') is distinct from Maggie's narrating voice; not a blind-test concern
- Mary Burrell: non-verbal and physical (tea towel folding), distinct composure register; reads unmistakably as her own register
- Migraine Sight onset integrated naturally via sensory narration without over-labelling; consistent with ledger spec
- reviewed_by: inspector-voice
metrics: {"blocking_count": 0, "drift_flags_above_threshold": 1, "drift_flags_harmless": 1, "fluency_flags": 0, "score": 4}
evidence:
  - {"distinguishable": true, "principals_tested": ["Maggie", "Cal"], "result": "PASS", "test": "blind_voice"}
  - {"count": 19, "density_per_1k": 14.28, "inspector_call": "HARMLESS \u2014 structural plant and migraine-arc tracking", "threshold": 3, "tic_id": "lexical_repetition"}
  - {"count": 9, "density_per_1k": 3.78, "inspector_call": "CLEAR \u2014 below threshold; character-appropriate", "threshold": 5, "tic_id": "soft_qualifiers"}
  - {"check": "fluency_stage", "premature_flags": 0, "result": "PASS", "stage": "OUTSIDER"}
