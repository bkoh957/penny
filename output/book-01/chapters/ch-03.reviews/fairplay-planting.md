---
producer: inspector-fairplay
kind: inspector
target: book-01/ch-03
schema: penny-verdict/1
score: 5
---

- Obligation 1 (Neil reputation changed): PRESENT and fairly available. Planted in townsfolk dialogue per OUTSIDER fluency. Footpath women, lines 82-84: "There he goes... Good of him to come, I suppose." / "Suppose," in a tone that withdrew the suggestion. Capstone line 90: "He used to be lovely, you know... Once. You'd not believe it now, but he was." Maggie files it as gossip (line 92), so the reader receives the change without it being authorially underlined.
- Obligation 2 (keystone physical clue: heavy, ugly failed vase Neil buys, read as kindness): PRESENT and fairly available. The object is concretely on the page lines 62-74: "a tall, heavy, graceless thing... an oxblood that had gone wrong in the firing and pooled thick and dark at the base." Neil insists on buying it ("How much," lines 66/70) and pays exact coins (line 72). Maggie's innocent reading is explicit, line 76: "Maggie decided... that this had been a generosity."
- Fairness check: the vase's physical properties (heavy, ugly, graceless) are stated plainly without an authorial nudge toward future significance; Neil's "only honest piece in the room" line reads as in-character, and Maggie's kindness-interpretation actively defuses suspicion rather than spoiling it. Not buried, not over-flagged.
- No retroactive or schedule-contradicting clue detected. Migraine Sight and Neil-takes-migraines-seriously beats are consistent with canon; any phrasing nuance (bedside vs studio stool) is continuity's domain, not fairplay.
- Did not re-derive schedule internal fairness (fairplay_check.py owns that).
metrics: {"obligations_absent": 0, "obligations_present": 2, "obligations_total": 2}
evidence:
  - {"lines": "82-90", "obligation": "neil-reputation-changed", "quote": "He used to be lovely, you know... Once. You'd not believe it now, but he was.", "status": "present-fair"}
  - {"lines": "62-76", "obligation": "keystone-vase-purchase", "quote": "a tall, heavy, graceless thing... an oxblood that had gone wrong... pooled thick and dark at the base", "status": "present-fair"}
  - {"line": "76", "obligation": "kindness-misreading", "quote": "Maggie decided... that this had been a generosity", "status": "present-fair"}
