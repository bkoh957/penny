---
producer: voice_drift.py
kind: deterministic-checker
target: unknown
schema: penny-verdict/1
---

- bodily_reaction: 0 (density 0.0/1k, threshold 3) ok
- wave_templates: 0 (density 0.0/1k, threshold 2) ok
- something_language: 0 (density 0.0/1k, threshold 2) ok
- filtering_verbs: 1 (density 0.43/1k, threshold 4) ok
- soft_qualifiers: 3 (density 1.3/1k, threshold 5) ok
- metaphor_pool: 0 (density 0.0/1k, threshold 5) ok
- sentence_variance: 118 (density 17.06/1k, threshold 4.0) ok
- cinematic_fragments: 0 (density 0.0/1k, threshold 1) ok
- lexical_repetition: 31 (density 13.45/1k, threshold 3) FLAGGED
metrics: {"n_sentences": 118, "n_words": 2304, "sentence_stdev": 17.06}
evidence:
  - {"line": 18, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 26, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 66, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 86, "span_text": "slightly", "tic_id": "soft_qualifiers"}
