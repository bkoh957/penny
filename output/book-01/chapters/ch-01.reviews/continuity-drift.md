---
producer: inspector-continuity
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 2
---

BLOCKING: HR director tenure contradicts canon: ledger states twenty years; chapter states eleven years (ch text: "She had been an HR director for eleven years"; ledger: "Former HR director (twenty years)")
- Age 43 consistent with ledger.
- Season (autumn/late April) consistent with ledger.
- Cal Burrell role, first appearance, and shelving work all consistent with ledger.
- Glaze: ginger tom, walks in, inspects kiln, sits on good apron, not removed — all consistent with ledger.
- The Wheelhouse: bare shelves, salt smell, light off water — consistent.
- Pelican's Crook: main street parallel to water, arrival in autumn as town empties — consistent.
- Dr Neil Hartigan: not present in chapter; alive status not violated.
- No knowledge-state violations detected.
- No timeline coherence violations detected.
- Fluency stage (OUTSIDER): local idiom stays in other characters mouths; Maggie narration is standard English — respected.
- reviewed_by: claude-sonnet-4-6
metrics: {"contradictions": 1, "knowledge_state_violations": 0, "reviewed_by": "claude-sonnet-4-6", "timeline_violations": 0}
evidence:
  - {"chapter": "eleven years", "chapter_quote": "She had been an HR director for eleven years.", "field": "hr_tenure", "ledger": "twenty years", "ledger_source": "Maggie Quill entry: former HR director (twenty years)", "type": "fact_contradiction"}
  - {"field": "age", "type": "consistent", "value": "43"}
  - {"field": "season", "type": "consistent", "value": "autumn / late April"}
  - {"field": "tom_burrell", "type": "consistent", "value": "carpenter installs shelving ch 1"}
  - {"field": "glaze", "type": "consistent", "value": "ginger tom, kiln inspection, good apron, not removed"}
  - {"field": "the_wheelhouse", "type": "consistent", "value": "bare shelves, salt smell, water light"}
  - {"field": "pelicans_crook", "type": "consistent", "value": "main street parallel to water, autumn arrival"}
  - {"field": "fluency_stage", "type": "consistent", "value": "OUTSIDER respected \u2014 no local idiom in Maggie narration"}
