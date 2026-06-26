---
producer: voice_drift.py
kind: deterministic-checker
target: unknown
schema: penny-verdict/1
---

- bodily_reaction: 0 (density 0.0/1k, threshold 3) ok
- wave_templates: 0 (density 0.0/1k, threshold 2) ok
- something_language: 1 (density 0.39/1k, threshold 2) ok
- filtering_verbs: 2 (density 0.77/1k, threshold 4) ok
- soft_qualifiers: 8 (density 3.09/1k, threshold 5) ok
- metaphor_pool: 0 (density 0.0/1k, threshold 5) ok
- sentence_variance: 148 (density 16.13/1k, threshold 4.0) ok
- cinematic_fragments: 0 (density 0.0/1k, threshold 1) ok
- lexical_repetition: 27 (density 17.01/1k, threshold 3) FLAGGED
metrics: {"n_sentences": 148, "n_words": 2586, "sentence_stdev": 16.13}
evidence:
  - {"line": 48, "span_text": "something in her voice", "tic_id": "something_language"}
  - {"line": 56, "span_text": "realized", "tic_id": "filtering_verbs"}
  - {"line": 84, "span_text": "seemed to", "tic_id": "filtering_verbs"}
  - {"line": 28, "span_text": "slightly", "tic_id": "soft_qualifiers"}
  - {"line": 38, "span_text": "almost", "tic_id": "soft_qualifiers"}
  - {"line": 72, "span_text": "as if", "tic_id": "soft_qualifiers"}
  - {"line": 98, "span_text": "somehow", "tic_id": "soft_qualifiers"}
  - {"line": 140, "span_text": "a little", "tic_id": "soft_qualifiers"}
