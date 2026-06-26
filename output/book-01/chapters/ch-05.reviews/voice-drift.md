---
producer: voice_drift.py
kind: deterministic-checker
target: unknown
schema: penny-verdict/1
---

- bodily_reaction: 0 (density 0.0/1k, threshold 3) ok
- wave_templates: 0 (density 0.0/1k, threshold 2) ok
- something_language: 0 (density 0.0/1k, threshold 2) ok
- filtering_verbs: 3 (density 1.26/1k, threshold 4) ok
- soft_qualifiers: 9 (density 3.78/1k, threshold 5) ok
- metaphor_pool: 0 (density 0.0/1k, threshold 5) ok
- sentence_variance: 102 (density 18.97/1k, threshold 4.0) ok
- cinematic_fragments: 1 (density 0.0/1k, threshold 1) ok
- lexical_repetition: 19 (density 14.28/1k, threshold 3) FLAGGED
metrics: {"n_sentences": 102, "n_words": 2381, "sentence_stdev": 18.97}
evidence:
  - {"line": 26, "span_text": "could see", "tic_id": "filtering_verbs"}
  - {"line": 42, "span_text": "could see", "tic_id": "filtering_verbs"}
  - {"line": 62, "span_text": "could feel", "tic_id": "filtering_verbs"}
  - {"line": 4, "span_text": "somehow", "tic_id": "soft_qualifiers"}
  - {"line": 8, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 26, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 40, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 50, "span_text": "as though", "tic_id": "soft_qualifiers"}
