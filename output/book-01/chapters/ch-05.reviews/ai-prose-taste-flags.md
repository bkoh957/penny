---
producer: inspector-ai-prose
kind: inspector
target: book-01/ch-05
schema: penny-verdict/1
score: 3
---

- reviewed_by: claude-sonnet-4-6
- Flag 4 (airless passages): two sub-scene passages are consistently over-complete — the Iris Poole reading block and the Mary Burrell tea-towel sequence each load every sentence with action+meaning+atmosphere+character simultaneously, leaving no gap for the reader; does not span a full scene so below blocking threshold
- Flag 1 (polished contrast): line 78 — 'something more complicated than warmth — something that was still trying to be kind and was not sure it could manage' — contrast gestures at specificity but stays in abstract-emotional register; rote
- Flag 2 (interpretive ending): line 70 — 'and that was somehow the worst thing anyone had done to her all morning' — the cup-in-bin gesture was already eloquent; interpretive tail tells rather than trusts; rote
- Flag 3 (generic lyricism): no rote instances; imagery is specific to the setting (glaze, mugs, foreshore, pelican)
- Flag 5 (predictable closing cadence): none — chapter ends on an interruption, not a stock uplift beat
- Earned strengths: pottery/glaze metaphors are character-specific and non-portable; pelican paragraph earns its weight; Dot/Glad dialogue breaks interpretive density effectively
metrics: {"flag1_rote": 1, "flag2_rote": 1, "flag3_rote": 0, "flag4_airless_passages": 2, "flag5_rote": 0}
evidence:
  - {"excerpt": "It was a wound... It was the posture of a person holding something that had cost her, holding it in public, year after year, in a room that had decided to call it a feud about jam because the truth underneath was nobody's to touch.", "flag": 4, "judgment": "every sentence triple-loaded; no sentence does only one thing; characteristic over-completion of interpretive passage", "location": "para-10-iris-poole-reading"}
  - {"excerpt": "a fold so practised it was barely a decision... as though her hands belonged to someone steadier than the rest of them.", "flag": 4, "judgment": "every action decoded simultaneously; 'as if working were a kind of mercy she was extending to the room' is action+meaning in one move; nothing left implicit", "location": "para-16-mary-tea-towel"}
  - {"excerpt": "something more complicated than warmth \u2014 something that was still trying to be kind and was not sure it could manage", "flag": 1, "judgment": "rote polished contrast; 'more complicated than X' without concrete landing", "location": "line-78"}
  - {"excerpt": "and that was somehow the worst thing anyone had done to her all morning", "flag": 2, "judgment": "unnecessary interpretive tail; cup-in-bin action already carried the weight", "location": "line-70"}
