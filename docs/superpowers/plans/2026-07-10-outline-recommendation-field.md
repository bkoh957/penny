# Outline Recommendation Field Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each outline-feedback item an optional, reviewer-authored `recommendation:` key that carries the suggested fix separately from the observation.

**Architecture:** The reviewer authors the recommendation at generation time; `outline_feedback.py` only transports it (`if pt.get("recommendation")`), never classifies it. Because `append_items` never mutates existing items, `OF-1`…`OF-22` are never retro-filled. A prerequisite task first gives the codex panel member a written output contract, since there is currently no file in which to tell codex about the new key.

**Tech Stack:** Python 3 stdlib + PyYAML (this ledger is nested human-edited data — the PyYAML side of the dependency-split rule). pytest. Markdown agent/command contracts.

**Spec:** `docs/superpowers/specs/2026-07-10-outline-recommendation-field-design.md`

## Global Constraints

- The deterministic layer makes **zero LLM/genre judgment**. `outline_feedback.py` may check *whether a key is present*, never *whether prose is a recommendation*.
- The ledger is **append-only**. `append_items` must continue to leave existing items byte-identical. Never add a migration or retro-fill.
- **Absent, not empty.** When there is no fix, the key is omitted — never `""`, never `"No action required"`.
- **Per-source, never merged.** A recommendation belongs to the item's `source`. Never reconcile two members' recommendations.
- **No scores.** `recommendation` is prose.
- `status_line` must remain byte-identical and must **never exit nonzero**.
- Tests asserting on `.md` prose must assert on the **new sentence**, never a bare token like `recommendation` (which occurs in prose elsewhere in both files and would make the test vacuous). Prove each test RED before implementing.
- Run the full suite with `python3 -m pytest` (pytest.ini sets `pythonpath=.`). Baseline before this plan: **353 passed**.

---

### Task 1: Give the codex panel member a written output contract

The claude member's shape is pinned in `agents/outline-reviewer.md:35`. The codex member has none — `commands/review-outline.md` step 6 says only "send the SAME rubric + inputs", so the orchestrator improvises codex's prompt every run. Nothing to hang `recommendation` on. Fix that first; it stands on its own merit.

**Files:**
- Modify: `commands/review-outline.md` (step 6, the `codex` bullet)
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a committed codex output contract in `commands/review-outline.md` that Task 3 extends with the `recommendation` key.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_feedback.py`:

```python
from pathlib import Path

COMMANDS = Path("commands")
AGENTS = Path("agents")


def _flat(p: Path) -> str:
    """Collapse newlines/indent so assertions survive line-wrapping."""
    return " ".join(p.read_text(encoding="utf-8").split()).lower()


def test_codex_member_has_a_written_output_contract():
    """The codex prompt must be committed, not improvised per run."""
    flat = _flat(COMMANDS / "review-outline.md")
    assert "one object per discrete point" in flat
    assert "do not assign ids" in flat
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_feedback.py::test_codex_member_has_a_written_output_contract -v`
Expected: FAIL — `assert 'one object per discrete point' in flat`

- [ ] **Step 3: Write minimal implementation**

In `commands/review-outline.md`, replace the `codex` bullet inside step 6:

```markdown
   - `codex` → send the SAME rubric + inputs to the Codex reviewer via the codex plugin
     runtime (independent tool; this is the "difference, not identity" second set of eyes).
     Give it this output contract verbatim, so both members are bound by a committed
     artifact rather than an improvised prompt:
     > Produce your feedback as a JSON array of objects `{ "text": "<one focused prose point>" }`
     > — one object per discrete point (quote the beat + name the gap + a concrete move).
     > Emit `[]` if you genuinely have nothing new to add this pass. Do NOT assign IDs; do NOT
     > add a `source` field (the command owns both).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS (all tests in file)

- [ ] **Step 5: Commit**

```bash
git add commands/review-outline.md tests/test_outline_feedback.py
git commit -m "fix(review-outline): the codex member had no written output contract

Step 6 said only 'send the SAME rubric + inputs'; the orchestrator improvised
codex's prompt each run, so 'identical inputs' bound the files but not the
instructions. Pin the same contract the outline-reviewer agent already carries."
```

---

### Task 2: `append_items` transports an optional `recommendation`

**Files:**
- Modify: `scripts/outline_feedback.py:83-99` (`append_items`)
- Modify: `scripts/outline_feedback.py:168` (the `--points` help string)
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `append_items(ledger, new_points, *, reviewed_sha) -> dict`, unchanged signature. Each point is `{"source": str, "text": str, "recommendation": str | absent}`. Emitted items carry `recommendation` only when the incoming point has a truthy one.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_outline_feedback.py`:

```python
def test_append_carries_recommendation_when_present():
    out = of.append_items(
        _seed(),
        [{"source": "claude", "text": "obs", "recommendation": "plant a warm beat"}],
        reviewed_sha="newsha",
    )
    assert out["items"][-1]["recommendation"] == "plant a warm beat"


def test_append_omits_the_key_entirely_when_absent():
    """Absent, not empty: 'no fix' must be a costless answer."""
    out = of.append_items(
        _seed(),
        [{"source": "claude", "text": "this section is strong"}],
        reviewed_sha="newsha",
    )
    assert "recommendation" not in out["items"][-1]


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_append_omits_the_key_when_reviewer_sends_blank(blank):
    out = of.append_items(
        _seed(),
        [{"source": "codex", "text": "obs", "recommendation": blank}],
        reviewed_sha="newsha",
    )
    assert "recommendation" not in out["items"][-1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_feedback.py -k recommendation -v`
Expected: `test_append_carries_recommendation_when_present` FAILS with `KeyError: 'recommendation'`. The two omission tests **PASS vacuously** (the key is never written today) — that is expected and is exactly why they must be re-run after Step 3, where they become load-bearing.

- [ ] **Step 3: Write minimal implementation**

In `scripts/outline_feedback.py`, replace the loop body of `append_items`:

```python
    for pt in new_points:
        item = {
            "id": f"OF-{next_id}",
            "source": pt["source"],
            "pass": next_pass,
            "state": "open",
            "text": pt["text"],
        }
        rec = pt.get("recommendation")
        if rec and rec.strip():
            item["recommendation"] = rec
        items.append(item)
        next_id += 1
```

Update the `--points` help string on line 168:

```python
    ap.add_argument("--points", help="append: path to a JSON array of {source,text,recommendation?}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS, including `test_append_preserves_existing_items_exactly` (the append-only invariant).

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "feat(outline-feedback): transport an optional recommendation key

The script's only judgment is whether the key is present. Absent, not empty:
a blank recommendation is dropped so 'I have no fix for you' stays costless."
```

---

### Task 3: Both contracts request the optional `recommendation`

**Files:**
- Modify: `agents/outline-reviewer.md:35-38`
- Modify: `commands/review-outline.md` (step 6 codex contract from Task 1; step 7 collect shape)
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: the codex contract block added in Task 1; the transport added in Task 2.
- Produces: reviewers that emit `{source?, text, recommendation?}` points. No Python signature changes.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_feedback.py`. Assert on the **sentence**, not the bare token — `recommendation` alone would match prose elsewhere and pass vacuously:

```python
CONTRACT_SENTENCE = "add a `recommendation` field only when you are recommending a change"


def test_both_panel_contracts_request_an_optional_recommendation():
    """Agent file and command prompt must teach the same rule, or the panel half-follows it."""
    for rel in (AGENTS / "outline-reviewer.md", COMMANDS / "review-outline.md"):
        flat = _flat(rel)
        assert CONTRACT_SENTENCE.lower() in flat, f"{rel} is missing the contract sentence"
        assert "omitting it is a legitimate answer" in flat, f"{rel} must make omission costless"


def test_collect_shape_documents_the_optional_key():
    flat = _flat(COMMANDS / "review-outline.md")
    assert "{ source, text, recommendation? }" in flat.replace('"', "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_feedback.py -k contract -v`
Expected: FAIL — `agents/outline-reviewer.md is missing the contract sentence`

- [ ] **Step 3: Write minimal implementation**

In `agents/outline-reviewer.md`, replace instruction 3 (lines 35-38):

```markdown
3. Produce your feedback as a JSON array of objects `{ "text": "<one focused prose point>" }`
   — one object per discrete point (quote the beat + name the gap + a concrete move).
   Add a `recommendation` field only when you are recommending a change: `text` carries the
   observation, `recommendation` carries the fix you propose. Omitting it is a legitimate
   answer — if a point is praise, or names an ambiguity you cannot resolve, leave it off
   rather than inventing an action.
   Emit `[]` if you genuinely have nothing new to add this pass. Do NOT assign IDs; do NOT
   add a `source` field (the command owns both).
```

In `commands/review-outline.md`, extend the quoted codex contract from Task 1 with the identical two sentences:

```markdown
     > Add a `recommendation` field only when you are recommending a change: `text` carries the
     > observation, `recommendation` carries the fix you propose. Omitting it is a legitimate
     > answer — if a point is praise, or names an ambiguity you cannot resolve, leave it off
     > rather than inventing an action.
```

In `commands/review-outline.md`, update step 7's collect shape:

```markdown
7. **Collect points → JSON.** Each member returns a JSON array of `{ text, recommendation? }`.
   Tag each point with its member as `source` and concatenate into one array
   `[{ source, text, recommendation? }, ...]`. Write it to a temp file, e.g.
   `.penny/outline-points-$1.json`. Never merge or reconcile two members' recommendations —
   disagreement is the signal this tier preserves.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agents/outline-reviewer.md commands/review-outline.md tests/test_outline_feedback.py
git commit -m "feat(outline-review): both panel contracts request an optional recommendation

Worded identically in the agent file and the codex prompt. Omission is explicitly
legitimate so no reviewer invents an action to fill a slot."
```

---

### Task 4: `render_view` shows the fix beneath its observation

**Files:**
- Modify: `scripts/outline_feedback.py:121-135` (`render_view`)
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: items carrying an optional `recommendation` (Task 2).
- Produces: `render_view(ledger) -> str`, unchanged signature.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_outline_feedback.py`:

```python
def _ledger(items):
    return {"book": "01", "reviewed_outline_sha256": "sha", "items": items}


def test_render_shows_recommendation_beneath_its_observation():
    md = of.render_view(_ledger([
        {"id": "OF-1", "source": "claude", "pass": 1, "state": "open",
         "text": "romance starved after ch11", "recommendation": "plant a warm beat"},
    ]))
    lines = md.splitlines()
    obs = next(i for i, l in enumerate(lines) if "romance starved after ch11" in l)
    rec = next(i for i, l in enumerate(lines) if "plant a warm beat" in l)
    assert rec == obs + 1, "recommendation must follow its observation, never precede it"
    assert lines[rec].strip().startswith("**→**")


def test_render_omits_the_arrow_when_there_is_no_recommendation():
    md = of.render_view(_ledger([
        {"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "this is strong"},
    ]))
    assert "**→**" not in md


def test_render_of_a_pre_change_ledger_is_unchanged():
    """Back-compat: OF-1..OF-22 have no recommendation key and must render as before."""
    md = of.render_view(_ledger([
        {"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "a"},
        {"id": "OF-2", "source": "codex", "pass": 1, "state": "open", "text": "b"},
    ]))
    assert "- **OF-1** · _claude_ · pass 1\n  a" in md
    assert "- **OF-2** · _codex_ · pass 1\n  b" in md
    assert "**→**" not in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_feedback.py -k render -v`
Expected: `test_render_shows_recommendation_beneath_its_observation` FAILS with `StopIteration` (no line contains "plant a warm beat"). The other two PASS today — they are the back-compat net and must stay green through Step 3.

- [ ] **Step 3: Write minimal implementation**

In `scripts/outline_feedback.py`, inside `render_view`'s item loop, after the `text` line:

```python
        for it in rows:
            lines.append(f"- **{it.get('id')}** · _{it.get('source')}_ · pass {it.get('pass')}")
            lines.append(f"  {it.get('text', '').strip()}")
            rec = it.get("recommendation")
            if rec:
                lines.append(f"  **→** {rec.strip()}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "feat(outline-feedback): render the recommendation beneath its observation

Never a standalone list of fixes — ordering is what stops a reader skipping
the reasoning. Absent key renders exactly as before."
```

---

### Task 5: Pin the invariants that must not drift

`status_line` prints IDs only — the property that keeps item text out of a drafting context. A recommendation is item text. Prove it cannot leak, and prove the exit-0 guarantee survives.

**Files:**
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: `of.status_line(book, repo_root=None) -> str`; `append_items` from Task 2; `render_view` from Task 4.
- Produces: nothing consumed downstream.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_feedback.py`. **Reuse the file's existing `_write_outline(tmp_path, book, text)` and `_write_ledger(tmp_path, book, ledger)` helpers (defined around lines 62-71) — do not reinvent them.** Passing `repo_root=tmp_path` is what lets these tests run outside a `.penny/` series root:

```python
def test_status_line_never_prints_recommendation_text(tmp_path):
    """The banner prints IDs, never item text — a recommendation must not leak to drafting."""
    _write_outline(tmp_path, "01", "body")
    sha = of.sha256_of(tmp_path / "input" / "book-01" / "outline.md")
    _write_ledger(tmp_path, "01", {
        "book": "01",
        "reviewed_outline_sha256": sha,
        "items": [{"id": "OF-1", "source": "claude", "pass": 1, "state": "open",
                   "text": "SECRET_OBSERVATION", "recommendation": "SECRET_FIX"}],
    })

    line = of.status_line("01", repo_root=tmp_path)
    assert "OF-1" in line
    assert "SECRET_FIX" not in line
    assert "SECRET_OBSERVATION" not in line
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_feedback.py::test_status_line_never_prints_recommendation_text -v`
Expected: This should **PASS immediately** — `status_line` already prints IDs only. That is the point: it is a regression pin, not a new behavior. If it FAILS, `status_line` is leaking text today and that is a bug to fix before continuing. Record which outcome you saw.

- [ ] **Step 3: No implementation needed**

If Step 2 passed, write no code. If it failed, stop and report — the leak is out of this plan's scope and changes the spec's "What does not change" section.

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest`
Expected: `358 passed` (353 baseline + 5 new test functions; the parametrized blank test counts as 3, so confirm the arithmetic against the actual output rather than asserting this number).

- [ ] **Step 5: Commit**

```bash
git add tests/test_outline_feedback.py
git commit -m "test(outline-feedback): pin that status_line never prints item text

A recommendation is item text. The banner prints IDs only; this is the property
that keeps outline content out of a drafting context."
```

---

## Self-Review

**Spec coverage.** Schema → Task 2. Absent-not-empty → Task 2 (blank guard) + Task 3 (contract wording) + Task 4 (render branch). Per-source never merged → Task 3 (step 7 wording). Where-authored + the codex-contract gap → Tasks 1 and 3. Transport → Task 2. Rejected alternatives (prose extraction, sidecar file) → no task, correctly: they are rejections. Presentation → Task 4. What-does-not-change (`status_line`, exit 0) → Task 5. Testing bullets → distributed across Tasks 2, 4, 5, plus the contract-lockstep bullet → Task 3.

**Placeholder scan.** None. Every code step carries the code; every test step carries the assertion.

**Type consistency.** `append_items(ledger, new_points, *, reviewed_sha)` and `render_view(ledger)` keep their existing signatures throughout. The point dict key is `recommendation` in all five tasks; the rendered marker is `**→**` in both Task 4 tests and Task 4 implementation. Helpers `_flat` and `COMMANDS`/`AGENTS` are defined once in Task 1 and reused in Task 3 — Task 3's implementer must not redefine them.

**Note on Task 2 Step 2.** Two of its three tests pass before implementation. Called out in-step rather than hidden, because a test that is green before the feature exists is the exact failure this repo has shipped before. They are omission assertions and only become load-bearing once the key can be written at all.
