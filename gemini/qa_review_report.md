# QA Consultant Report — Penny Project Review

This report provides an independent QA and technical audit of **Penny** (a modular writing harness). It covers the consistency of current specifications, reviews the existing codebase (Phases 1 & 2a), and critically reviews the design specification and implementation plan for Phase 2b (Inspector Bus).

---

## 1. Executive Summary

Penny's architecture is built on a sound core concept: separating a **fixed engine** from **swappable configurations** (packs) while enforcing a strict **independence principle** between the drafting agent and the quality review gate. 

Overall, the project is structured cleanly, and the separation of mutable/immutable state is highly disciplined. However, our review has uncovered several logical gaps and subtle bugs across the specification, the existing codebase, and the upcoming Phase 2b plan. Resolving these before Phase 2b implementation starts will prevent revision loop escapes, TUI status inconsistencies, and potential silent passes on malformed reviews.

---

## 2. Current Codebase Audit (Phase 1 & 2a)

We reviewed the implemented files in the [scripts](file:///Users/beeko/myTools/penny/scripts) folder. While the code is high quality and dependency-free (except for standard `yaml`), we found several gaps against the spec.

### 2.1 Culprit-ID Resolution Check in [fairplay_check.py](file:///Users/beeko/myTools/penny/scripts/fairplay_check.py)
In Phase 2a, the ledger checker resolves the culprit ID against `series/continuity/characters` (which holds mutable facts/states):
```python
# fairplay_check.py:L118-121
chars = Path(__file__).resolve().parents[1] / "series/continuity/characters"
if chars.is_dir() and any(chars.iterdir()):
    if not (chars / f"{culprit}.md").is_file():
        notes.append(f"culprit id '{culprit}' does not resolve in series/continuity/characters/ (evidence; blocking in 2b/3)")
```
> [!IMPORTANT]
> **The Gap:** The design defines both static character profiles in `series/characters/` (e.g., `cora-mistate.static.md`) and mutable continuity states in `series/continuity/characters/` (e.g., `cora-mistate.md`).
> 
> *   **Resolution Mismatch:** If the checker only checks for `{culprit}.md` under mutable continuity, it will fail to resolve character IDs that are defined statically but have not yet been instantiated in the continuity log. 
> *   **Filename inconsistency:** Static characters are stored with the naming convention `<id>.static.md`, whereas continuity profiles use `<id>.md`. The resolver does not account for this naming shift.
> *   **Carry-Forward Neglected:** [HANDOFF.md](file:///Users/beeko/myTools/penny/HANDOFF.md) notes that in Phase 2b, culprit-id resolution must be promoted to `BLOCKING:` and should check the static directory (`series/characters/`) or both. However, neither the Phase 2b Spec nor the Phase 2b Plan contains tasks to modify [fairplay_check.py](file:///Users/beeko/myTools/penny/scripts/fairplay_check.py) to implement this.

### 2.2 Unused Configuration Seeds in [ai-tics-config.yaml](file:///Users/beeko/myTools/penny/config/voice-pack/ai-tics-config.yaml)
*   **`same_domain_flag_at`**: The config file declares `metaphor_pool_rule: { same_domain_flag_at: 3, total_flag_at: 5 }`. As noted in the handoff, this is an unused future seed. [voice_drift.py](file:///Users/beeko/myTools/penny/scripts/voice_drift.py) completely ignores it. This is acceptable for Phase 2a/2b, but should be marked in config comments as `2b/future` to avoid confusing future developers.

---

## 3. Phase 2b Design & Plan Critique

We evaluated [2026-06-20-penny-phase2b-inspector-bus-design.md](file:///Users/beeko/myTools/penny/docs/superpowers/specs/2026-06-20-penny-phase2b-inspector-bus-design.md) and [2026-06-20-penny-phase2b-inspector-bus.md](file:///Users/beeko/myTools/penny/docs/superpowers/plans/2026-06-20-penny-phase2b-inspector-bus.md). The plan to use a deterministic python script (`review_gate.py`) is an excellent mitigation against Option A's instruction-following weaknesses. However, we identified three critical issues.

### 3.1 Command Stage Transition Bug (Critical)
In Task 7 (Step 3: Create `.claude/commands/review-chapter.md`), the command's instructions contain a code block that unconditionally sets the stage to `REVIEWED`:

```markdown
10. **Advance the marker and surface the result:**

    ```bash
    # stage=REVIEWED on PASS, stage=GATE-HELD on HOLD
    echo "book=$book chapter=$chapter stage=REVIEWED" > .penny/current-stage
    ```
```

> [!WARNING]
> If a developer or runner executes this command verbatim (which is standard behavior for automated/copy-pasted code execution blocks in Option A), the harness will write `stage=REVIEWED` to `.penny/current-stage` even if `review_gate.py` outputted a `HOLD` (due to blockers). 
> 
> Because `review_gate.py` returns exit code `0` on both PASS and HOLD (by design, since a HOLD is a valid result, not an operational failure), the parent command cannot rely on exit codes alone without branching logic.

### 3.2 Silent Skip of Malformed Verdict Files (High Risk)
In the planned `_load_verdicts` implementation inside [review_gate.py](file:///Users/beeko/myTools/penny/scripts/review_gate.py):
```python
meta = parse_frontmatter(text)
kind = meta.get("kind")
if kind not in VERDICT_KINDS:
    continue  # skip gate-summary and anything non-verdict
```
> [!CAUTION]
> If an inspector sub-agent fails during generation or outputs a malformed verdict file missing the `kind` frontmatter field (or has a typo like `kind: inspectr`), `kind not in VERDICT_KINDS` evaluates to `True`. The gate evaluator will **silently skip** the file and proceed.
>
> If that inspector file contained critical `BLOCKING:` issues, they will be bypassed. Even though the command has a completeness check ("verify 5 inspector files exist"), a file that *exists* but is malformed will bypass the gate. `review_gate.py` should **fail-loud** on any malformed file in the reviews directory rather than skipping it.

### 3.3 Thread-Roster Empty-State
The spec states that the structure inspector should receive a thread roster. If `last_advanced_chapter` is `unknown`, it should not compute liveness.
*   **QA Checklist item:** The prompt file [inspector-structure.md](file:///Users/beeko/myTools/penny/.claude/agents/inspector-structure.md) must be strictly audited during implementation to ensure it does not hallucinate chapter indices when given `unknown`. We should explicitly add test assertions or instructions in the prompt to enforce this boundary.

---

## 4. Summary of Gaps & Inconsistencies

The following table summarizes the alignment mismatches between the specifications, plans, and codebase.

| Issue ID | Area / File | Description | Severity | Target Phase for Fix |
|---|---|---|---|---|
| **GAP-01** | `fairplay_check.py` | Culprit-ID resolution only checks `continuity/characters/<id>.md` and ignores static characters `<id>.static.md`. | Medium | Phase 2b (Must integrate) |
| **BUG-01** | `review-chapter.md` | Unconditional transition to `stage=REVIEWED` in bash code block, even when gate is `HOLD`. | High | Phase 2b (Must integrate) |
| **BUG-02** | `review_gate.py` | Malformed verdict files missing `kind` or `producer` are silently skipped instead of raising a `GateError`. | High | Phase 2b (Must integrate) |
| **GAP-02** | `ai-tics-config.yaml` | `same_domain_flag_at` is an unused seed and has no documentation / comments explaining it. | Low | Phase 2b (Nice to have) |

---

## 5. Actionable QA Recommendations

To resolve these findings, we recommend modifying the Phase 2b specification and plan with the following changes.

### Recommendation 1: Fix `review-chapter.md` Stage Transition
Update Task 7 Step 3 to make the stage marker update deterministic via bash branching:
```diff
-    # stage=REVIEWED on PASS, stage=GATE-HELD on HOLD
-    echo "book=$book chapter=$chapter stage=REVIEWED" > .penny/current-stage
+    if grep -q "gate: HOLD" output/book-$book/chapters/ch-$chapter.gate.md; then
+      echo "book=$book chapter=$chapter stage=GATE-HELD" > .penny/current-stage
+    else
+      echo "book=$book chapter=$chapter stage=REVIEWED" > .penny/current-stage
+    fi
```

### Recommendation 2: Make `review_gate.py` Malformed Checks Fail-Loud
Modify `_load_verdicts` to validate every file found in the reviews directory. If a file does not have a valid `kind` or is missing crucial metadata, it must raise a `GateError` to prevent silent gate escapes:
```diff
      for path in sorted(root.glob("*.md")):
          text = path.read_text(encoding="utf-8")
          meta = parse_frontmatter(text)
          kind = meta.get("kind")
+        if not kind:
+            raise GateError(f"{path.name}: missing 'kind' frontmatter")
          if kind not in VERDICT_KINDS:
+            if kind == "gate-summary":
+                # Should not be here, but skip if found
+                continue
+            raise GateError(f"{path.name}: invalid verdict kind {kind!r}")
          producer = meta.get("producer")
```

### Recommendation 3: Promote Culprit ID Resolution & Resolve Static vs. Continuity
Modify [fairplay_check.py](file:///Users/beeko/myTools/penny/scripts/fairplay_check.py) to check both static and continuity folders, and promote the failure to a blocker.
Add a step in the Phase 2b spec/plan to adjust `check_fairplay()`:
```python
    # Resolve culprit id against static characters (*.static.md) and/or continuity
    continuity_chars = Path(__file__).resolve().parents[1] / "series/continuity/characters"
    static_chars = Path(__file__).resolve().parents[1] / "series/characters"
    
    resolved = False
    if continuity_chars.is_dir() and (continuity_chars / f"{culprit}.md").is_file():
        resolved = True
    elif static_chars.is_dir() and (static_chars / f"{culprit}.static.md").is_file():
        resolved = True
        
    if not resolved:
        blocking.append(f"culprit id '{culprit}' does not resolve in characters bible (static or continuity)")
```
*(This moves culprit-id checking from an evidence note to a `blocking` check, fulfilling the carry-forward decision from Phase 2a.)*
