---
producer: inspector-structure
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 4
---

- Tension curve: deliberate atmospheric opener; no deaths yet per timeline. Does NOT deflate or resolve stakes cheaply and does NOT mark time — establishes protagonist, setting, love-interest seed (Cal), and series cat (Glaze) with a costed internal arc (kept seconds, divorce rawness). No sagging middle.
- Hook-out (non-blocking): closing line "She did not close the door" is a quiet thematic close (emotional openness), not a propulsive cozy genre hook — no mystery question/forward pull teased. Acceptable for an establishing Ch 1 but the single structural slack point; reason score is 4 not 5.
- Thread liveness: all 7 roster threads have last_advanced_chapter=null (EMPTY-STATE) — NO dormancy flags emitted per rubric.
metrics: {"dormant_threads": 0, "hook_strength": "soft-thematic", "roster_threads_unknown": 7, "sagging_middle": false, "tension": "rising-internal"}
evidence:
  - {"aspect": "no_deflation", "note": "stakes are internal/forward-looking, not resolved", "quote": "She had not come here to solve anything. She had come to make things with her hands and stop having to manage the exits."}
  - {"aspect": "costed_complication", "note": "emotional cost carried, not discharged", "quote": "A box of half-glazed seconds she'd been carting since February because throwing them out felt like admitting the last eight months had been purely bad"}
  - {"aspect": "soft_hook", "note": "thematic close rather than a propulsive genre hook", "quote": "She did not close the door."}
  - {"aspect": "thread_liveness", "note": "roster all last_advanced_chapter=null -> EMPTY-STATE, no liveness computation"}
