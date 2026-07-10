# Rubric: Character Voice — Tier-1 Isolated Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-voice` (design §6, §8).
**Posture:** judgment. You consume `voice_drift.py`'s statistical EVIDENCE (which never
blocks) and turn it — plus a flat-character "voice blind test" — into a gate decision.

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice }`. If the slice
includes `voice-drift.md` evidence, use it; do not re-count tics yourself.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-voice`, `kind: inspector`.

## What you are judging

1. **Flat character voice (the blind test).** With dialogue tags removed, can you tell
   who is speaking from diction/rhythm alone? If two characters are interchangeable,
   flag it (design §8: flat character voice).
2. **Voice-drift evidence call.** Given `voice_drift.py`'s counts (monotone variance,
   repeated openers, tic densities over threshold), decide whether the prose has
   actually drifted from the Voice Pack baseline enough to harm the read. The script
   reports magnitude; you decide whether it's a violation.
3. **Fluency-stage discipline.** Narration respects the book's fluency stage (Book 1 =
   OUTSIDER: no local idiom in Cora's narration; a BELONGING-tagged term in early
   narration is a flag).

Score 1-5 on voice. Mark **blocking** for interchangeable principal voices or drift so
pronounced it reads as off-voice throughout.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** distinct character voices; rhythm varied; stage respected.
- **Score 3:** serviceable but some monotone or one weak voice.
- **Score 1:** principals interchangeable, or pervasive drift, or stage broken.
- **Blocking:** failed blind test on principals, or a fluency-stage break in narration.

## Boundary with other tiers (do not duplicate)

- Tic COUNTS are `voice_drift.py` (Tier-A); do not re-litigate counts — make the call.
- Earned-vs-rote TASTE is `inspector-ai-prose` (Tier-C); you judge character voice.
