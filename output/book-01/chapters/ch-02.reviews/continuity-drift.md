---
producer: inspector-continuity
kind: inspector
target: book-01/ch-02
schema: penny-verdict/1
score: 5
---

- Faye Denton surname matches ledger; introduced ch 2 as specified.
- Cobber real name Dennis matches ledger; fifty-something, thirty-year tenure, dawn beach presence all consistent.
- Dot and Glad first appear ch 2 as specified; disagreement-since-1987 detail consistent (ledger gives year only; chapter adds agricultural show context without contradiction).
- Beryl Foss: clipboard, CWA chair, cool toward newcomer — all consistent with ledger. No age given in ledger; chapter estimate of ~60 is not contradicted.
- Dr Hartigan named in dialogue only, not appearing in person — consistent with neil-hartigan.md (first alive ch 3). No knowledge-state violation.
- Cobber dawn sighting planted as local colour; Maggie does not act on it. Clue is seeded without knowledge-state break.
- Fluency stage OUTSIDER respected: local idiom in other characters (Cobber) only; Maggie narration standard English throughout.
- Timeline coherent: beach before 8am (Cobber), Faye arrives 9am, out at 11am (Dot/Glad, Beryl). No impossible sequencing.
- Season (Autumn) and chapter position (Book 01 ch 02, Neil alive) match canon-core.
evidence:
  - {"chapter": "Faye Denton", "field": "faye.surname", "ledger": "Denton", "verdict": "MATCH"}
  - {"chapter": "Dennis", "field": "cobber.real_name", "ledger": "Dennis", "verdict": "MATCH"}
  - {"chapter": "30 years", "field": "cobber.tenure", "ledger": "30 years", "verdict": "MATCH"}
  - {"chapter": "fifties", "field": "cobber.age", "ledger": "fifties", "verdict": "MATCH"}
  - {"chapter": "before 8am on beach", "field": "cobber.dawn_beach", "ledger": "on beach every dawn", "verdict": "MATCH"}
  - {"chapter": "ch 2", "field": "dot_glad.first_appear", "ledger": "ch 2", "verdict": "MATCH"}
  - {"chapter": "1987 agricultural show", "field": "dot_glad.disagreement_since", "ledger": "1987", "verdict": "MATCH \u2014 chapter adds show context, no contradiction"}
  - {"chapter": "clipboard under arm", "field": "beryl.clipboard", "ledger": "clipboard", "verdict": "MATCH"}
  - {"chapter": "CWA morning tea (third Thursday)", "field": "beryl.cwa_chair", "ledger": "CWA chair", "verdict": "MATCH"}
  - {"chapter": "named in dialogue only, not present", "field": "neil_hartigan.alive", "ledger": "first alive ch 3; alive at ch 2 position", "verdict": "MATCH"}
  - {"chapter": "idiom in Cobber only; Maggie standard English", "field": "fluency_stage", "ledger": "OUTSIDER", "verdict": "MATCH"}
  - {"chapter": "43", "field": "meg.age", "ledger": "43", "verdict": "MATCH"}
  - {"chapter": "late autumn", "field": "season", "ledger": "Autumn", "verdict": "MATCH"}
