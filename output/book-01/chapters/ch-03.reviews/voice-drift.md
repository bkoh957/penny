---
producer: voice_drift.py
kind: deterministic-checker
target: unknown
schema: penny-verdict/1
---

- bodily_reaction: 0 (density 0.0/1k, threshold 3) ok
- wave_templates: 0 (density 0.0/1k, threshold 2) ok
- something_language: 0 (density 0.0/1k, threshold 2) ok
- filtering_verbs: 1 (density 0.46/1k, threshold 4) ok
- soft_qualifiers: 4 (density 1.86/1k, threshold 5) ok
- metaphor_pool: 1 (density 0.46/1k, threshold 5) ok
- sentence_variance: 102 (density 17.71/1k, threshold 4.0) ok
- cinematic_fragments: 0 (density 0.0/1k, threshold 1) ok
- lexical_repetition: 24 (density 13.47/1k, threshold 3) FLAGGED
metrics: {"n_sentences": 102, "n_words": 2153, "sentence_stdev": 17.71}
evidence:
  - {"line": 28, "span_text": "seemed to", "tic_id": "filtering_verbs"}
  - {"line": 6, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 42, "span_text": "as though", "tic_id": "soft_qualifiers"}
  - {"line": 48, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 48, "span_text": "slightly", "tic_id": "soft_qualifiers"}
  - {"line": 0, "span_text": "weight", "tic_id": "metaphor_pool"}
