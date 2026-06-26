---
producer: inspector-continuity
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 4
---

- reviewed_by: claude-opus-4-8
- Re-review after correction: carpenter note now signs "Here at 3. C." (line 33), consistent with Callum "Cal" Burrell (characters/cal-burrell.md). Prior T. name contradiction resolved -- no blocking issues remain.
- Minor non-blocking drift (unchanged, kept as note): cat is "wearing clay dust in his fur" (line 71); glaze.md gives his naming rationale as being "permanently dusted in" glaze (clay != glaze). Cat is unnamed in ch1, non-load-bearing.
- Knowledge-state: clean -- Maggie holds no mystery knowledge; no leak of Hartigan/murder/culprit info (canon-core: no deaths yet, Hartigan alive).
- Timeline coherent: late April / early autumn / coming winter matches canon-core Season: Autumn (southern hemisphere); arrival in autumn per pelicans-crook + protagonist-fixed.
- Maggie facts consistent: 43, twenty years HR (decade as Director), divorced, potter, The Wheelhouse on Pelicans Crook main street; drive from Brunswick. Matches maggie-quill.md / protagonist-fixed.
- Glaze beats consistent: ginger tom enters open door, inspects kiln, settles on the good apron, not thrown out (glaze.md, the-wheelhouse.md ch-1 opening).
- Wheelhouse/location consistent: ground-floor shopfront on main street, bare shelves, salt smell, light off the water, kiln (the-wheelhouse.md; pelicans-crook.md geography).
- OUTSIDER narration largely respected; idioms sit in/around Cals voice. "ute" in narration vs lexicon narration_ok_from_stage unverifiable from this slice -- out of scope, defer to voice tier.
metrics: {"fact_contradictions": 0, "knowledge_state_violations": 0, "minor_drifts": 1}
evidence:
  - {"chapter": "ch-01.draft.md:33 note now signs Here at 3. C.", "slice": "characters/cal-burrell.md:9 Known as Cal; Full name Callum Burrell", "type": "resolved_ok"}
  - {"chapter": "ch-01.draft.md:71 wearing clay dust in his fur", "slice": "characters/glaze.md:11 Named for the glaze he is permanently dusted in", "type": "minor_drift"}
  - {"chapter": "ch-01.draft.md whole: no death, no mystery knowledge", "slice": "canon-core.md:17 no deaths yet recorded; Dr Neil Hartigan alive", "type": "ok_knowledge_state"}
