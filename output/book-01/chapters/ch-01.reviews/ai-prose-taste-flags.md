---
producer: inspector-ai-prose
kind: inspector
target: book-01/ch-01
schema: penny-verdict/1
score: 4
---

- reviewed_by: claude-sonnet-4-6
- Flag 1 (polished contrasts): one mild rote instance — the HR backstory sentence 'the rest of her had gone somewhere else, and she hadn't noticed until it had been gone quite a long time'. The dissociation insight is earned by context but 'somewhere else' is never located; the prose gestures at depth without grounding it.
- Flag 2 (interpretive endings): no unearned instances. 'The eucalypts had not offered any insight. She had started the car again.' earns its deadpan by refusing the revelation. 'In the way of things, come undone' functions as wit integrated into sentence rhythm, not an explanatory tail.
- Flag 3 (generic lyricism): none. Lyrical sentences are anchored to physical specifics of this place and character throughout. The prose actively avoids the interchangeable type.
- Flag 4 (airless passages): no full-scene violation. HR backstory paragraph is densest but reads as compressed summary rather than scenic airlessness. Cal's scene actively inverts the tendency: sparse dialogue, unmarked silences, sentences that arrive after their required gaps.
- Flag 5 (predictable closing cadence): one recognizable-type instance — 'Not happiness, not yet. Just the possibility of it.' The structure matches the stock uplift-resolution beat. Partially earned by: (a) sustained withholding of interpretation throughout the chapter makes this landing feel arrived-at; (b) the actual final sentence ('She did not close the door.') performs rather than states and is the real landing; (c) the cat on the apron gives the feeling a concrete vehicle.
- Overall: prose consistently refuses the expected AI moves. No weather symbolism, no interiority as stage direction, no generic lyricism. Two rote-adjacent touches (flag 1, flag 5) read as moments of tiredness rather than systemic AI default. Not blocking.
metrics: {"rote_flag1": 1, "rote_flag2": 0, "rote_flag3": 0, "rote_flag4": 0, "rote_flag5": 1, "total_rote": 2}
evidence:
  - {"flag": 1, "line": "the rest of her had gone somewhere else, and she hadn't noticed until it had been gone quite a long time", "reason": "dissociation gesture ungrounded \u2014 'somewhere else' unnamed; prose gestures at depth without locating it", "verdict": "rote-adjacent"}
  - {"flag": 5, "line": "Not happiness, not yet. Just the possibility of it.", "reason": "stock uplift-resolution structure; partially redeemed by 'She did not close the door.' as performing rather than stating the final beat", "verdict": "rote-adjacent"}
  - {"flag": 1, "line": "travelling light was a virtue and not a diagnosis", "reason": "contrast is the chapter's premise; 'diagnosis' specified concretely in the next sentence", "verdict": "earned"}
  - {"flag": 2, "line": "The eucalypts had not offered any insight. She had started the car again.", "reason": "deadpan refusal of the revelatory beat is itself the beat; withholds rather than over-explains", "verdict": "earned"}
  - {"flag": 3, "line": "the sea was doing what the sea does, which is to say it was going on without her", "reason": "generic frame subverted by 'going on without her' \u2014 specific emotional register for this character at this moment", "verdict": "earned"}
  - {"flag": 4, "line": "Here at 3. T.", "reason": "Cal's scene is the strongest counter-evidence to airlessness; two words, no interpretation, no atmosphere layered on", "verdict": "counter-evidence"}
