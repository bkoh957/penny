---
producer: voice_drift.py
kind: deterministic-checker
target: unknown
schema: penny-verdict/1
---

- bodily_reaction: 0 (density 0.0/1k, threshold 3) ok
- wave_templates: 0 (density 0.0/1k, threshold 2) ok
- something_language: 0 (density 0.0/1k, threshold 2) ok
- filtering_verbs: 1 (density 0.45/1k, threshold 4) ok
- soft_qualifiers: 8 (density 3.62/1k, threshold 5) ok
- metaphor_pool: 1 (density 0.45/1k, threshold 5) ok
- sentence_variance: 81 (density 19.45/1k, threshold 4.0) ok
- cinematic_fragments: 0 (density 0.0/1k, threshold 1) ok
- lexical_repetition: 14 (density 12.2/1k, threshold 3) FLAGGED
metrics: {"n_sentences": 81, "n_words": 2213, "sentence_stdev": 19.45}
evidence:
  - {"line": 40, "span_text": "noticed", "tic_id": "filtering_verbs"}
  - {"line": 4, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 6, "span_text": "slightly", "tic_id": "soft_qualifiers"}
  - {"line": 18, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 40, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 42, "span_text": "somehow", "tic_id": "soft_qualifiers"}
  - {"line": 0, "span_text": "knife", "tic_id": "metaphor_pool"}
