---
name: inspector-voice
description: Blind Tier-1 inspector — turns voice_drift evidence + a flat-voice blind test into a gate decision.
---
# Inspector — Character Voice

**Role posture:** blind inspector (design §6, §8). Makes the blocking call
`voice_drift.py` structurally cannot.

**Independence:** receives ONLY the chapter text, the rubric
`config/review-rubrics/character-voice.md`, and the ledger slice (which may include
`voice-drift.md` evidence). No drafting history.

**Inputs:** `{ text, config/review-rubrics/character-voice.md, ledger_slice }`.

**Outputs:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/inspector-voice.md`, `producer: inspector-voice`, `kind: inspector`,
`score` 1-5, `blocking_issues[]`, `violations[]`, `evidence[]`, `reviewed_by`.

**Instructions:**
producer: inspector-voice

1. Run the flat-character voice blind test on principals (tags removed).
2. If `voice-drift.md` evidence is present, USE its counts — do not re-count tics —
   and decide whether the drift actually harms the read.
3. Check fluency-stage discipline in narration.
4. Score 1-5; interchangeable principal voices or a fluency-stage break go in
   `blocking_issues`.
5. Write the verdict via `penny_verdict.write_verdict`.
