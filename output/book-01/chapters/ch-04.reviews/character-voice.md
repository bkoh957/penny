---
producer: inspector-voice
kind: inspector
target: book-01/ch-04
schema: penny-verdict/1
score: 4
---

- Blind test PASS: Cal (minimal declarative register, no qualifiers, physical-action framing), Faye (warm/gossip/"love" address), Saffron (rehearsed-wound carrying voice), Mary Burrell (controlled flat devastation) all identifiable by diction alone without tags.
- Fluency stage CLEAN (OUTSIDER): lexicon-fluency reports 0 premature-term flags; narration line 111 uses "football" and "boat" (standard English); no local idiom bleeds into Maggie narration.
- Voice drift BENIGN: soft_qualifiers flagged at count 8 (threshold 5) — "as though/as if" constructions are this narrator's characteristic observational instrument (hedged perception, the gap between seeing and understanding); not harmful drift.
- Voice drift BENIGN: lexical_repetition flagged at count 12 — repeated "knife" tracks a physical prop across the Mary Burrell beat (intentional structural use); "noticed" density 1.74/1k is below the 4/1k flag threshold.
- Minor soft qualifier density at Saffron passage (two consecutive "as though" in narration wrapping line 89) is slightly dense but does not break voice; held from score 5 on this basis.
- reviewed_by: inspector-voice (blind; no draft history)
metrics: {"blind_test": "pass", "drift_verdict": "benign", "fluency_stage": "OUTSIDER", "lexical_repetition_count": 12, "premature_term_flags": 0, "soft_qualifiers_count": 8}
evidence:
  - {"check": "blind_test", "principal": "Cal", "verdict": "distinct \u2014 minimal declarative, physical-action framing, zero qualifiers"}
  - {"check": "blind_test", "principal": "Faye", "verdict": "distinct \u2014 warm/gossipy, \"love\" address, practical exposition"}
  - {"check": "blind_test", "principal": "Maggie-spoken", "verdict": "distinct from Cal \u2014 defensive monosyllables under challenge"}
  - {"check": "blind_test", "principal": "Mary Burrell", "verdict": "distinct \u2014 controlled flat evenness, single devastating line"}
  - {"check": "fluency_stage", "narration_clean": true, "note": "post-fix football/boat confirmed standard English", "stage": "OUTSIDER"}
  - {"check": "drift", "count": 8, "decision": "benign \u2014 characteristic observational mode, not LLM hedging", "tic": "soft_qualifiers"}
  - {"check": "drift", "count": 12, "decision": "benign \u2014 knife tracks physical prop; noticed below density threshold", "tic": "lexical_repetition"}
