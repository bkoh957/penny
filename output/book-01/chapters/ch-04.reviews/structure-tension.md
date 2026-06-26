---
producer: inspector-structure
kind: inspector
target: book-01/ch-04
schema: penny-verdict/1
score: 4
---

- Beat 1 (Wheelhouse): tension rises through Cal's silent corrections; costed complication lands cleanly — Maggie wins the commission but is exposed on self-worth ('That's not a price. That's an apology'). No resolution; wound left open.
- Beat 2 middle (bakery, lines 79–97): serial grievance accumulation (fisherman → CWA pair → Saffron) repeats the same emotional register without fresh escalation between complaints. Structural slack, not structural failure; stakes are being layered even if the mechanism is repetitive.
- Beryl's shuttered reaction (line 95) is a genuine micro-complication that breaks the repetition and seeds her connection to Hartigan.
- Hook-out: strong. Mary Burrell's weighted line ('He always believed he knew what was best for people') and Maggie's recognition of its older, angrier register is a proper cozy hook — connects Cal to the murder thread, opens a new question the chapter cannot answer.
- Thread dormancy: all roster threads have last_advanced_chapter=null; per empty-state rule no dormancy flags emitted.
- reviewed_by: inspector-structure (claude-sonnet-4-6)
metrics: {"beats": 2, "costed_complications": 1, "dormant_threads_flagged": 0, "hook_quality": "strong", "sag_location": "bakery-middle lines 79-97"}
evidence:
  - {"location": "lines 57-66", "note": "Cal names the apology-price; Maggie is exposed with no defence. Commission won, self-worth cost extracted.", "type": "costed-complication"}
  - {"location": "lines 79-97", "note": "Three grievances against Hartigan in unescalating succession; same emotional register repeated without complication between beats.", "type": "structural-slack"}
  - {"location": "lines 95-96", "note": "Beryl Foss shuttered reaction to 'he'd tell you straight' \u2014 not resolved, correctly left open.", "type": "complication-seed"}
  - {"location": "lines 99-113", "note": "Mary Burrell lays down knife, delivers weighted line, resumes with enormous care. Maggie reads the depth correctly. Strong thread-opening hook (a-murder, b-romance via Cal).", "type": "hook-out"}
