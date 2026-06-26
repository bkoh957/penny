---
producer: inspector-voice
kind: inspector
target: book-01/ch-03
schema: penny-verdict/1
score: 4
---

- BLIND TEST PASS: Neil Hartigan unmistakably distinct without tags — flat imperative register, no softening, withholds explanation; Maggie narration sensory/observational/dry-ironic; principals non-interchangeable
- Neil voice markers confirmed: clipped directives ("Curtains. Both of them."), repeated "How much" without question mark, single-word pronouncements ("Interesting"), pre-empts apology before it is spoken, one-word exit lines
- Maggie register confirmed: involuntary-meaning perception (glazes passage), HR-trained gap-reading framing, dry self-deprecation ("practically anonymous"), heavy words she declines to lift
- Faye: warm/functional secondary — too few lines to fully differentiate; not a principal; no concern
- DRIFT: lexical_repetition 13.47/1k flagged (threshold 3); repetitions are craft-intentional — "How much" anaphora is Neil character beat, "she heard" series builds migraine soundscape, "the light/foil/pain/vase" carry thematic load; not voice drift; no blocking
- All other tic metrics within threshold; sentence_stdev 17.71 indicates strong rhythmic variety
- FLUENCY: 0 premature-term flags; OUTSIDER stage respected throughout; local flavour ("Maggie love" from Faye, surf-club remarks) correctly in dialogue only; Maggie explicitly frames herself as new-to-town outsider
- No local idiom in Maggie narration; "footpath" (standard Australian English) correctly passes the lexicon check
- reviewed_by: inspector-voice (claude-sonnet-4-6)
metrics: {"blind_test": "PASS", "drift_blocking": false, "fluency_stage": "OUTSIDER", "lexical_repetition_density": 13.47, "lexical_repetition_judgment": "craft-intentional", "premature_terms": 0, "score": 4, "sentence_stdev": 17.71}
evidence:
  - {"check": "blind_test", "markers": "flat imperative register; no question marks on How much; withheld explanations; pre-empts speech", "principal": "neil-hartigan"}
  - {"check": "blind_test", "markers": "involuntary-meaning perception; HR gap-reading; dry self-deprecation; heavy words declined", "principal": "maggie-quill"}
  - {"check": "drift", "density": 13.47, "flag": "lexical_repetition", "judgment": "intentional anaphora and thematic repetition; not drift", "threshold": 3}
  - {"check": "fluency", "note": "all idiom in dialogue; narration standard English", "stage": "OUTSIDER", "violations": 0}
