---
producer: inspector-voice
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 5
---

- Blind test PASSED. Cal Burrell is unmistakable on diction alone: clipped tradesman vernacular and Australian register ("Where dyou want them?", "saw something in the grain, shell hold fine", "whenever youre ready", "he was right, thanks"). Maggie speaks almost no dialogue but her close-third interior voice is distinct and consistent: dry, self-auditing, elaborate ("travelling light was a virtue and not a diagnosis"). The two are in no way interchangeable.
- voice_drift evidence used as-is, not re-counted. Only lexical_repetition FLAGGED (31, density 13.41 vs threshold 3); all other tics under threshold and sentence_stdev 17.04 is healthy. Inspector call: the repetition is benign — function words plus DELIBERATE parallelism in a single-POV chapter ("She looked at him. He looked at her."; the recurring "looked at... then looked at" patterning of Cal measuring). It reads as controlled rhythm, not off-voice drift. Not a violation; not blocking.
- Fluency stage OUTSIDER respected. lexicon-fluency reports 0 premature-term flags. Eyeball confirms: boot/petrol/kerb/ute/grog-proof are standard Australian English and ceramics vocabulary in Maggies register, not Pelicans Crook local idiom; no BELONGING-tagged term leaks into her narration. Local colour stays out of her mouth, as the stage requires.
- Score 5: distinct principal voices, varied rhythm, fluency stage held.
metrics: {"blind_test": "pass", "drift_flag_call": "lexical_repetition benign", "fluency_stage": "OUTSIDER", "principals_tested": ["maggie", "cal"], "stage_break": false}
evidence:
  - {"line": 53, "note": "Cal idiom distinct", "span_text": "Where d'you want them?"}
  - {"line": 57, "note": "Cal tradesman register", "span_text": "saw something in the grain, she'll hold fine"}
  - {"line": 9, "note": "Maggie interior voice distinct", "span_text": "travelling light was a virtue and not a diagnosis"}
  - {"line": 85, "note": "intentional parallelism, not drift", "span_text": "She looked at him. He looked at her."}
