# Deep Architectural Review: PRD & Design — Penny Project

This document provides a deep, expert-level architectural critique of the **Penny Product Requirements Document (PRD v3)** and the **Penny Design Specification (v3)**. It focuses on identifying long-term scaling risks, logical boundary conflicts, and integration gaps as the system scales to a 13-book series.

---

## 1. Context Window & Bible Bloat over 13 Books

### The Mechanism
Penny limits context window drift by loading only a "slice" of the continuity ledger:
$$\text{load\_set} = \text{canon-core.md} + \text{brief-derived entries} + \text{one-hop links}$$

### The Scale Risk
As the series progresses from Book 1 to Book 13, the following elements will scale linearly:
1.  **`canon-core.md` contents:** Accumulating major historical milestones, timeline position, protagonist's evolving facts, and previous book whodunit outcomes.
2.  **Entity links density:** More character/location links will accumulate in continuity folders, causing the "one-hop" query to pull in an increasingly large graph.

> [!WARNING]
> Without a **Ledger Garbage Collection Policy**, the always-loaded `canon-core.md` and the recursively loaded one-hop graph will eventually saturate the context window of the drafter and inspectors, degrading generation quality (needle-in-a-haystack dilution).

### QA Recommendation
*   **Implement an Archiving Directive:** Introduce a subfolder `/series/continuity/archive/`. Characters who die, locations that are destroyed, or threads that are permanently resolved should be moved here. 
*   **Strict canon-core.md size caps:** Limit `canon-core.md` to a maximum of 2,000 tokens. Historical plot summaries from past books should be summarized into a separate static file `past-books-summary.md` and loaded *only* if explicitly referenced in the chapter brief.

---

## 2. The Fluency Dial Verification Gap (Critical Design Flaw)

### The Constraint
The showrunner's "Newcomer Fluency Dial" (PRD §P0.2, Design §9) dictates three stages of narration vocabulary:
*   **OUTSIDER** (Books 1–2): Narration must contain no local Australian idiom.
*   **SETTLING** (Books 3–6): Moderate local idioms and slang appear in narration.
*   **BELONGING** (Books 7–13): Local idiom is fully integrated into narration.

### The Flaw
The PRD states: *"a `BELONGING`-tagged term in Book 2 narration is an automatic reviewer flag."* However:
1.  [voice_drift.py](file:///Users/beeko/myTools/penny/scripts/voice_drift.py) (Tier-3 checker) does not read `config/setting-pack/lexicon.md`.
2.  `inspector-voice` (Tier-1 agent) does not list `config/setting-pack/lexicon.md` as part of its input scope.

Without loading the lexicon database, the voice inspector must rely on fuzzy, non-deterministic general knowledge of slang to detect fluency violations. This breaks the principle of deterministic verification for countable metrics.

### QA Recommendation
Promote lexicon compliance to a Tier-3 deterministic checker. A script `lexicon_check.py` should run as a pre-gate script:
1.  Parse the draft, stripping dialogue blocks (text inside quotes U+0022 or smart quotes U+201C/U+201D).
2.  Search the remaining narration text for keys defined in `config/setting-pack/lexicon.md`.
3.  Cross-reference the matching terms' `narration_ok_from_stage` against the book's current stage declared in `canon-core.md`.
4.  Emit evidence or `BLOCKING:` warnings if an out-of-stage term is found.

---

## 3. Thread-Liveness & Cross-Book False Positives

### The Constraint
The structure inspector detects "dormant threads" within a book using a thread roster:
```markdown
# Design §8:
Structure inspector flags any thread dormant beyond thread_dormant_after_chapters (default 3).
```

### The Scale Risk
Penny spans a 13-book arc. Many threads defined in `arc-ledger.md` are **series-level threads** (e.g., the protagonist's divorce B-plot, or the mystery of the Aunt's death). These are designed to be dormant during specific books to allow standalone mysteries to take center stage.

If the structure inspector reads the entire continuity threads directory (`series/continuity/threads/*.md`) blindly:
*   Series-level threads that are intentionally inactive in the current book will be flagged as dormant.
*   The gate will hold on Book 2 because a series-level thread hasn't been advanced since Book 1.

### QA Recommendation
Define a scope field in each thread's metadata frontmatter:
```yaml
---
id: the-inheritance
type: thread
scope: series          # series | book
active_books: [1, 3, 7, 13]
---
```
The thread roster builder in `review-chapter` must check `scope` and `active_books` against the current book index. If a series thread is not active in the current book, it must be excluded from the structure inspector's active roster.

---

## 4. The Exit Status Dilemma in Option A Gating

### The Architecture
Penny is designed as **Claude-Code-native (Option A)**. The gate evaluator `review_gate.py` runs within bash command scripts.

### The Conflict
*   **Design §3.4**: `review_gate.py` exits `0` on a successful evaluation — PASS or HOLD alike. It exits non-zero only on operational errors (e.g., malformed files, empty directories).
*   **Automation Gating**: If a HOLD results in an exit status of `0`, a sequential loop (e.g., the Phase 6 Book Loop drafting chapters sequentially) cannot easily use standard shell check patterns (`command || exit 1`) to halt drafting.

If the pipeline continues running after a HOLD, the independence of the gate is compromised.

### QA Recommendation
Implement a three-tiered exit code architecture for `review_gate.py`:
*   `0`: **PASS** (Evaluation successful, zero blockers. Chapter is clean to finalize.)
*   `1`: **HOLD** (Evaluation successful, but blockers exist. Pipeline should halt.)
*   `2+`: **OPERATIONAL ERROR** (Refusal to gate: missing files, bad configuration, malformed verdicts.)

This enables deterministic loop halting in bash (`python3 review_gate.py ... || exit $?`).

---

## 5. Score 1 vs. Blocker Inconsistency

### The Rubrics
Rubrics (e.g., `continuity-drift.md`) use a 1–5 scoring scale alongside explicit `BLOCKING:` line outputs:
*   **Score 1**: Defined as a catastrophic failure (e.g., load-bearing contradiction, fluency-stage break).
*   **Blocking**: Contradictions that the slice establishes.

### The Risk
If an inspector sub-agent encounters a critical error and outputs a `score: 1` but fails to write an explicit `BLOCKING: <message>` line in its verdict file:
1.  `count_blocking()` returns `0`.
2.  `review_gate.py` evaluates the gate as `PASS`.

This is a significant gap: a chapter with a score of `1` (catastrophic failure) will bypass the gate.

### QA Recommendation
Update `review_gate.py` to assert that if any inspector verdict returns a `score` of `1` or `2`, the gate evaluator must treat it as an implicit blocker, overriding `blocking_count == 0` and forcing a `HOLD`.
```python
# Proposed update in review_gate.py:
if any(v["score"] is not None and v["score"] <= 2 for v in verdicts):
    gate = "HOLD"
```
This adds defense-in-depth against LLM failure modes where the inspector recognizes a severe problem (low score) but forgets to format the specific `BLOCKING:` prefix line.

---

## 6. Beta Reader Persona Bias & Blindness

### The Architecture
Beta readers run at the book level, loaded from config personas, and return qualitative reactions (PRD §P1.1, Design §10).

### The Risk
If beta readers run on the same LLM model (e.g., Claude Opus) as the drafter:
*   **Homogeneous Taste**: The model will naturally approve of its own stylistic choices, tone, and metaphors, producing a false "would-buy-next: yes" consensus.
*   **Lack of Blindness**: Even if text context is fresh, the model architecture's internal weights share identical creative boundaries.

### QA Recommendation
*   **Enforce Beta Model Heterogeneity**: Extend the P0.6 preflight check to cover the beta stage. Ensure that `beta_models` in `run-config.md` does not overlap with the set of `drafted_by` stamps across the book's chapters.
*   **Stochastic Persona Temperature**: Force a higher temperature (e.g., `temperature: 0.7`) on beta reader sub-agents to elicit more diverse and authentic "reader-like" reactions, rather than the default deterministic copy-editing style of low-temperature dispatches.
