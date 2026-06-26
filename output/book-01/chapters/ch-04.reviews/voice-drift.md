---
producer: voice_drift.py
kind: deterministic-checker
target: unknown
schema: penny-verdict/1
---

- bodily_reaction: 0 (density 0.0/1k, threshold 3) ok
- wave_templates: 0 (density 0.0/1k, threshold 2) ok
- something_language: 0 (density 0.0/1k, threshold 2) ok
- filtering_verbs: 4 (density 1.74/1k, threshold 4) ok
- soft_qualifiers: 8 (density 3.47/1k, threshold 5) FLAGGED
- metaphor_pool: 3 (density 1.3/1k, threshold 5) ok
- sentence_variance: 79 (density 22.47/1k, threshold 4.0) ok
- cinematic_fragments: 0 (density 0.0/1k, threshold 1) ok
- lexical_repetition: 12 (density 14.75/1k, threshold 3) FLAGGED
metrics: {"n_sentences": 79, "n_words": 2305, "sentence_stdev": 22.47}
evidence:
  - {"line": 6, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 36, "span_text": "could hear", "tic_id": "filtering_verbs"}
  - {"line": 84, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 94, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 30, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 38, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 68, "span_text": "as if", "tic_id": "soft_qualifiers"}
  - {"line": 84, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 84, "span_text": "As though", "tic_id": "soft_qualifiers"}
  - {"line": 0, "span_text": "wave", "tic_id": "metaphor_pool"}
  - {"line": 0, "span_text": "knife", "tic_id": "metaphor_pool"}
  - {"line": 0, "span_text": "knife", "tic_id": "metaphor_pool"}
