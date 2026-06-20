# Penny Phase 2b — Inspector Bus — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the judgment layer of the Review Bus — five blind Tier-1 inspector sub-agents plus a deterministic gate evaluator that fuses their verdicts and the 2a checkers into a single PASS/HOLD decision.

**Architecture:** Inspectors are non-deterministic Claude Code sub-agent prompt files (structurally isolated, one rubric each, conforming to the §6 review contract). The gate arithmetic is a deterministic, TDD'd Python script (`review_gate.py`). `review-chapter` is the thin orchestrator command that assembles context, dispatches inspectors, runs the 2a scripts, and calls the gate evaluator. The blocker-line *convention* lives in one place (`penny_verdict.count_blocking()`); the bash status line keeps a documented mirror, pinned by a test that execs the real script.

**Tech Stack:** Python 3 (stdlib only — `re`, `sys`, `argparse`, `pathlib`, `collections`; reuses `penny_meta.py`), pytest, bash (existing `penny-statusline.sh`), Claude Code agent/command markdown.

## Global Constraints

- **Run tests from repo root** (`pytest.ini` is there; CLI/script tests use `cwd=REPO`). Import scripts as `from scripts.X import Y`.
- **No new third-party runtime dependency.** `review_gate.py` and `reset_reviews.py` are stdlib-only; they read flat `run-config.md` via `penny_meta.parse_yaml_blocks` (the flat reader), not PyYAML.
- **The blocker convention is the literal regex `^BLOCKING:`** — anchored, case-sensitive, `MULTILINE`. Documented identically in `penny_verdict.py` (Python) and `penny-statusline.sh` (bash `grep '^BLOCKING:'`).
- **`voice_drift.py` MUST NOT emit `^BLOCKING:`** (2a hard rule); the inspector turns its evidence into a gate decision.
- **`gate.md` MUST NEVER contain a `^BLOCKING:` line** (double-count defense) and is written to the chapters dir, a sibling of `ch-MM.reviews/`, never inside it.
- **Fail loud, no fallback** for config: missing/non-numeric thresholds → nonzero exit, never a hardcoded default (mirrors `fairplay_check.py` reading `culprit_by_fraction`).
- **Gate exit codes:** `0` on successful evaluation (PASS *or* HOLD); nonzero **only** on operational error (malformed verdict, empty reviews dir, bad config, unreadable dir).
- **Verdict envelope** (unchanged from 2a, `scripts/penny_verdict.py`): `kind ∈ {inspector, deterministic-checker, gate-summary}`; inspectors add `score: 1-5`; `producer` is the canonical dimension key.
- **`producer` per inspector == the inspector's `name`** (e.g. `inspector-continuity`); the five must be distinct.
- **TDD throughout; commit after each green task.** Co-author trailer on commits: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

**Create:**
- `scripts/review_gate.py` — deterministic gate evaluator (load verdicts, count, PASS/HOLD, two-signal conflict, write `gate.md`).
- `scripts/reset_reviews.py` — re-run cleanup primitive (empty a chapter's verdicts + remove stale sibling `gate.md`).
- `.claude/agents/inspector-continuity.md`, `inspector-fairplay.md`, `inspector-structure.md`, `inspector-voice.md`, `inspector-ai-prose.md`.
- `config/review-rubrics/continuity-drift.md`, `fairplay-planting.md`, `structure-tension.md`, `character-voice.md`.
- `.claude/commands/review-chapter.md` — orchestrator command.
- `tests/test_review_gate.py`, `tests/test_reset_reviews.py`, `tests/test_inspector_scaffold.py`.

**Modify:**
- `scripts/penny_verdict.py` — add `BLOCKING_RE` + `count_blocking()` (additive).
- `tests/test_penny_verdict.py` — add count_blocking unit + cross-consistency tests.
- `penny-design-v3.md` — §6/§8 sweep + §2 scripts list.
- `README.md` — `review-chapter` dev note.

---

## Task 1: `count_blocking()` — the single home of the blocker convention

**Files:**
- Modify: `scripts/penny_verdict.py`
- Test: `tests/test_penny_verdict.py`

**Interfaces:**
- Produces: `scripts.penny_verdict.BLOCKING_RE` (compiled `re.Pattern`), `scripts.penny_verdict.count_blocking(reviews_dir) -> int`. Used by `review_gate.py` (Task 2) for the authoritative blocker count.

- [ ] **Step 1: Write the failing unit tests**

Add to `tests/test_penny_verdict.py`:

```python
from scripts.penny_verdict import count_blocking


def test_count_blocking_anchored_and_case_sensitive(tmp_path):
    (tmp_path / "a.md").write_text(
        "BLOCKING: real one\n"
        "- not a blocker\n"
        "blocking: lowercase not counted\n"
        "see BLOCKING: mid-line not counted\n",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text("BLOCKING: another\nBLOCKING: and another\n", encoding="utf-8")
    assert count_blocking(tmp_path) == 3


def test_count_blocking_absent_dir_is_zero(tmp_path):
    assert count_blocking(tmp_path / "nope") == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_penny_verdict.py -k count_blocking -v`
Expected: FAIL — `ImportError: cannot import name 'count_blocking'`.

- [ ] **Step 3: Implement in `scripts/penny_verdict.py`**

Add near the top (after `import json`):

```python
import re
from collections.abc import Iterable  # noqa: F401  (kept for type clarity)

# The blocker-line convention lives HERE (the verdict-format module owns what a
# blocker line looks like). Mirrored verbatim by penny-statusline.sh's
# `grep '^BLOCKING:'`; agreement is pinned by a cross-consistency test.
BLOCKING_RE = re.compile(r"^BLOCKING:", re.MULTILINE)


def count_blocking(reviews_dir) -> int:
    """Count ``^BLOCKING:`` lines across every file in ``reviews_dir`` (recursive).

    Mirrors ``grep -rh '^BLOCKING:'``: reads all files, anchored + case-sensitive.
    Returns 0 if the directory is absent.
    """
    root = Path(reviews_dir)
    if not root.is_dir():
        return 0
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            total += len(BLOCKING_RE.findall(text))
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_penny_verdict.py -k count_blocking -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Write the cross-consistency tripwire test (execs the REAL status line)**

Add to `tests/test_penny_verdict.py` (reuses the `penny_root` fixture from `conftest.py`, which runs the real `scripts/penny-statusline.sh`):

```python
import re as _re
from scripts.penny_verdict import count_blocking


def test_count_blocking_agrees_with_real_status_line(penny_root):
    # The status line is the OTHER implementation of the ^BLOCKING: convention.
    # Pin them to agree by running the real script, not a transcribed grep.
    penny_root.write_stage("book=01 chapter=07 stage=REVIEW")
    penny_root.write_blocking("01", "07", 2)  # writes 2 BLOCKING: lines into the reviews dir
    out = penny_root.run('{"context_window": {"used_percentage": 41.2}}')
    rendered = int(_re.search(r"gate: (\d+) blocking", out).group(1))

    reviews = penny_root.path / "output" / "book-01" / "chapters" / "ch-07.reviews"
    assert count_blocking(reviews) == rendered == 2
```

- [ ] **Step 6: Run the tripwire test**

Run: `pytest tests/test_penny_verdict.py -k agrees_with_real_status_line -v`
Expected: PASS. (If it fails, the bash counter and `count_blocking` have drifted — that is the tripwire firing.)

- [ ] **Step 7: Commit**

```bash
git add scripts/penny_verdict.py tests/test_penny_verdict.py
git commit -m "feat(verdict): count_blocking() as the single home of the ^BLOCKING: convention

Adds BLOCKING_RE + count_blocking() to penny_verdict.py and a cross-consistency
test that execs the real penny-statusline.sh, pinning the bash mirror to the
Python counter.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `review_gate.py` — core gate (count, PASS/HOLD, gate.md, error paths)

**Files:**
- Create: `scripts/review_gate.py`
- Test: `tests/test_review_gate.py`

**Interfaces:**
- Consumes: `scripts.penny_verdict.count_blocking` (Task 1); `scripts.penny_meta.parse_frontmatter`, `parse_yaml_blocks`.
- Produces: `scripts.review_gate.GateError`; `evaluate_gate(reviews_dir, config_path) -> dict` returning keys `gate` (`"PASS"|"HOLD"`), `blocking_count` (int), `blocking_issues` (list of `(producer, issue)`), `escalations` (list — empty until Task 3), `score_spread_log` (list — empty until Task 3); `write_gate_md(out_path, target, result) -> Path`; `main(argv=None) -> int`. Task 3 extends `evaluate_gate`; Task 7's command calls `main`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review_gate.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict
from scripts.review_gate import GateError, evaluate_gate, write_gate_md, main

CONFIG = Path("config/run-config.md").resolve()


def _reviews(tmp_path):
    d = tmp_path / "output" / "book-01" / "chapters" / "ch-07.reviews"
    d.mkdir(parents=True)
    return d


def _inspector(d, name, *, blocking=None, score=3):
    write_verdict(out_dir=d, producer=name, kind="inspector", target="book-01/ch-07",
                  name=name, blocking=blocking or [], notes=[], metrics={}, evidence=[],
                  score=score)


def test_pass_when_no_blockers(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity")
    _inspector(d, "inspector-voice")
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "PASS"
    assert result["blocking_count"] == 0


def test_hold_counts_blockers(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity", blocking=["will referenced before reveal"])
    _inspector(d, "inspector-fairplay", blocking=["clue not on the page"])
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "HOLD"
    assert result["blocking_count"] == 2
    assert ("inspector-continuity", "will referenced before reveal") in result["blocking_issues"]


def test_gate_summary_files_are_ignored(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-voice")
    # A stray prior gate.md sitting in the dir must NOT be read as a verdict.
    write_gate_md(d / "ch-07.gate.md", "book-01/ch-07",
                  {"gate": "HOLD", "blocking_count": 9, "blocking_issues": [],
                   "escalations": [], "score_spread_log": []})
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "PASS"  # the gate-summary's 9 is not counted


def test_malformed_verdict_missing_producer_raises(tmp_path):
    d = _reviews(tmp_path)
    (d / "broken.md").write_text("---\nkind: inspector\nscore: 3\n---\n- note\n", encoding="utf-8")
    with pytest.raises(GateError):
        evaluate_gate(d, CONFIG)


def test_inspector_missing_score_raises(tmp_path):
    d = _reviews(tmp_path)
    (d / "x.md").write_text("---\nproducer: inspector-voice\nkind: inspector\n---\n- note\n",
                            encoding="utf-8")
    with pytest.raises(GateError):
        evaluate_gate(d, CONFIG)


def test_empty_reviews_dir_raises(tmp_path):
    d = _reviews(tmp_path)
    with pytest.raises(GateError):
        evaluate_gate(d, CONFIG)


def test_missing_thresholds_raises(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-voice")
    bad_config = tmp_path / "bad.md"
    bad_config.write_text("# no yaml block here\n", encoding="utf-8")
    with pytest.raises(GateError):
        evaluate_gate(d, bad_config)


def test_gate_md_has_no_blocking_lines_and_is_sibling(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity", blocking=["bad thing"])
    result = evaluate_gate(d, CONFIG)
    out = d.parent / "ch-07.gate.md"
    write_gate_md(out, "book-01/ch-07", result)
    text = out.read_text(encoding="utf-8")
    assert not any(line.startswith("BLOCKING:") for line in text.splitlines())
    meta = parse_frontmatter(text)
    assert meta["kind"] == "gate-summary"
    assert meta["gate"] == "HOLD"
    assert out.parent.name == "chapters"  # sibling of the reviews dir, not inside it


def test_main_exit0_on_hold_and_writes_gate_md(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity", blocking=["bad thing"])
    rc = main([str(d), "--config", str(CONFIG)])
    assert rc == 0  # HOLD is a result, not a crash
    assert (d.parent / "ch-07.gate.md").exists()


def test_main_nonzero_on_operational_error(tmp_path):
    d = _reviews(tmp_path)  # empty -> operational error
    rc = main([str(d), "--config", str(CONFIG)])
    assert rc != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_review_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.review_gate'`.

- [ ] **Step 3: Implement `scripts/review_gate.py`**

```python
"""Deterministic gate evaluator for the Penny Review Bus (Phase 2b).

Reads the verdict files in a chapter's ``ch-NN.reviews/`` directory, computes the
gate decision (PASS iff zero blockers) and the two-signal conflict outcomes, and
writes a ``ch-NN.gate.md`` summary alongside the chapter (sibling of reviews/).

The blocker COUNT is owned by ``penny_verdict.count_blocking`` (the single home of
the ^BLOCKING: convention); this module owns the panel DECISION. Fails loud
(nonzero exit) on operational errors; exit 0 for PASS or HOLD alike.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from scripts.penny_meta import parse_frontmatter, parse_yaml_blocks
from scripts.penny_verdict import count_blocking

VERDICT_KINDS = ("inspector", "deterministic-checker")


class GateError(Exception):
    """Operational error — refuse to emit a gate (caller exits nonzero)."""


def _load_thresholds(config_path) -> dict:
    try:
        text = Path(config_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(f"cannot read config {config_path}: {exc}") from exc
    cfg = parse_yaml_blocks(text)
    try:
        spread = int(cfg["score_spread_log_threshold"])
        escalate = str(cfg["escalate_on_blocking_disagreement"]).strip().lower() == "true"
    except (KeyError, ValueError) as exc:
        raise GateError(
            "run-config missing/non-numeric escalate_on_blocking_disagreement "
            "or score_spread_log_threshold"
        ) from exc
    return {"escalate_on_blocking_disagreement": escalate, "score_spread_log_threshold": spread}


def _load_verdicts(reviews_dir) -> list[dict]:
    root = Path(reviews_dir)
    if not root.is_dir():
        raise GateError(f"reviews dir not found: {reviews_dir}")
    verdicts: list[dict] = []
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        kind = meta.get("kind")
        if kind not in VERDICT_KINDS:
            continue  # skip gate-summary and anything non-verdict
        producer = meta.get("producer")
        if not producer:
            raise GateError(f"{path.name}: malformed verdict — missing producer")
        score = None
        if kind == "inspector":
            raw = meta.get("score")
            if raw is None:
                raise GateError(f"{path.name}: malformed inspector verdict — missing score")
            try:
                score = int(raw)
            except (TypeError, ValueError) as exc:
                raise GateError(f"{path.name}: non-numeric score {raw!r}") from exc
        blocking = [ln[len("BLOCKING:"):].strip()
                    for ln in text.splitlines() if ln.startswith("BLOCKING:")]
        verdicts.append({"file": path.name, "producer": producer, "kind": kind,
                         "score": score, "blocking": blocking})
    if not verdicts:
        raise GateError(f"no verdicts in {reviews_dir} (dispatch failed?)")
    return verdicts


def evaluate_gate(reviews_dir, config_path) -> dict:
    cfg = _load_thresholds(config_path)
    verdicts = _load_verdicts(reviews_dir)
    blocking_count = count_blocking(reviews_dir)  # authoritative, matches status line
    gate = "PASS" if blocking_count == 0 else "HOLD"
    blocking_issues = [(v["producer"], issue) for v in verdicts for issue in v["blocking"]]
    return {
        "gate": gate,
        "blocking_count": blocking_count,
        "blocking_issues": blocking_issues,
        "escalations": [],        # populated in Task 3
        "score_spread_log": [],   # populated in Task 3
    }


def write_gate_md(out_path, target, result) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "producer: review_gate.py", "kind: gate-summary",
             f"target: {target}", f"gate: {result['gate']}",
             f"blocking_count: {result['blocking_count']}",
             "schema: penny-verdict/1", "---", "",
             f"- {result['gate']}: {result['blocking_count']} blocking issue(s)"]
    for producer, issue in result["blocking_issues"]:
        lines.append(f"- blocking [{producer}]: {issue}")  # never ^BLOCKING:
    lines.append(f"- escalations: {result['escalations']}")
    lines.append(f"- score_spread_log: {result['score_spread_log']}")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _derive_target(reviews_dir) -> str:
    # output/book-01/chapters/ch-07.reviews -> "book-01/ch-07"
    p = Path(reviews_dir)
    chapter = p.name.replace(".reviews", "")
    book = p.parent.parent.name
    return f"{book}/{chapter}"


def _default_out(reviews_dir) -> Path:
    p = Path(reviews_dir)
    chapter = p.name.replace(".reviews", "")
    return p.parent / f"{chapter}.gate.md"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Penny Review Bus gate evaluator")
    parser.add_argument("reviews_dir")
    parser.add_argument("--config", default="config/run-config.md")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        result = evaluate_gate(args.reviews_dir, args.config)
    except GateError as exc:
        print(f"review_gate: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else _default_out(args.reviews_dir)
    write_gate_md(out, _derive_target(args.reviews_dir), result)
    suffix = f" ({result['blocking_count']} blocking)" if result["gate"] == "HOLD" else ""
    print(f"GATE: {result['gate']}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_review_gate.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Commit**

```bash
git add scripts/review_gate.py tests/test_review_gate.py
git commit -m "feat(gate): review_gate.py core — count, PASS/HOLD, gate.md, fail-loud

Loads kind-filtered verdicts, counts blockers via the shared primitive, writes a
gate-summary with no ^BLOCKING: lines (sibling of reviews/), and fails loud on
malformed verdicts, empty dirs, and bad config. Exit 0 for PASS or HOLD.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `review_gate.py` — two-signal conflict resolution (dormant at panel 1)

**Files:**
- Modify: `scripts/review_gate.py`
- Test: `tests/test_review_gate.py`

**Interfaces:**
- Consumes: the verdict list shape from Task 2 (`producer`, `kind`, `score`, `blocking`).
- Produces: populated `escalations` (list of producer strings) and `score_spread_log` (list of `{"producer", "spread"}`) in `evaluate_gate`'s return.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_review_gate.py`:

```python
def test_blocking_disagreement_escalates_within_a_dimension(tmp_path):
    d = _reviews(tmp_path)
    # Two verdicts, SAME producer (simulates panel_size>1): one blocks, one doesn't.
    write_verdict(out_dir=d, producer="inspector-voice", kind="inspector",
                  target="book-01/ch-07", name="inspector-voice-a",
                  blocking=["voice broke"], notes=[], metrics={}, evidence=[], score=2)
    write_verdict(out_dir=d, producer="inspector-voice", kind="inspector",
                  target="book-01/ch-07", name="inspector-voice-b",
                  blocking=[], notes=[], metrics={}, evidence=[], score=4)
    result = evaluate_gate(d, CONFIG)
    assert "inspector-voice" in result["escalations"]


def test_no_escalation_at_panel_one(tmp_path):
    # Distinct producers (the panel_size:1 default) -> disagreement check sleeps.
    d = _reviews(tmp_path)
    _inspector(d, "inspector-voice", blocking=["voice broke"], score=2)
    _inspector(d, "inspector-structure", blocking=[], score=4)
    result = evaluate_gate(d, CONFIG)
    assert result["escalations"] == []


def test_score_spread_logs_within_a_dimension(tmp_path):
    d = _reviews(tmp_path)
    write_verdict(out_dir=d, producer="inspector-structure", kind="inspector",
                  target="book-01/ch-07", name="inspector-structure-a",
                  blocking=[], notes=[], metrics={}, evidence=[], score=2)
    write_verdict(out_dir=d, producer="inspector-structure", kind="inspector",
                  target="book-01/ch-07", name="inspector-structure-b",
                  blocking=[], notes=[], metrics={}, evidence=[], score=5)
    result = evaluate_gate(d, CONFIG)  # default threshold is 2; spread is 3
    assert any(e["producer"] == "inspector-structure" and e["spread"] == 3
               for e in result["score_spread_log"])


def test_no_score_spread_at_panel_one(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-structure", score=2)
    _inspector(d, "inspector-voice", score=5)  # different dimensions, not a spread
    result = evaluate_gate(d, CONFIG)
    assert result["score_spread_log"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_review_gate.py -k "disagreement or spread or panel_one" -v`
Expected: FAIL — escalations/score_spread_log are still empty lists.

- [ ] **Step 3: Implement the two detectors and wire them in**

Add to `scripts/review_gate.py` (above `evaluate_gate`):

```python
def _detect_blocking_disagreement(verdicts, cfg) -> list[str]:
    if not cfg["escalate_on_blocking_disagreement"]:
        return []
    by_producer = defaultdict(list)
    for v in verdicts:
        by_producer[v["producer"]].append(v)
    out = []
    for producer, group in sorted(by_producer.items()):
        if len(group) < 2:
            continue  # one verdict per dimension at panel_size:1 -> sleeps
        if len({bool(v["blocking"]) for v in group}) > 1:
            out.append(producer)
    return out


def _detect_score_spread(verdicts, cfg) -> list[dict]:
    by_producer = defaultdict(list)
    for v in verdicts:
        if v["kind"] == "inspector" and v["score"] is not None:
            by_producer[v["producer"]].append(v["score"])
    out = []
    for producer, scores in sorted(by_producer.items()):
        if len(scores) < 2:
            continue
        spread = max(scores) - min(scores)
        if spread >= cfg["score_spread_log_threshold"]:
            out.append({"producer": producer, "spread": spread})
    return out
```

Then replace the two placeholder lines in `evaluate_gate`'s return dict:

```python
        "escalations": _detect_blocking_disagreement(verdicts, cfg),
        "score_spread_log": _detect_score_spread(verdicts, cfg),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_review_gate.py -v`
Expected: PASS (Task 2 + Task 3 tests). The `panel_one` tests prove dormant ≠ broken.

- [ ] **Step 5: Commit**

```bash
git add scripts/review_gate.py tests/test_review_gate.py
git commit -m "feat(gate): two-signal conflict resolution (dormant-but-tested at panel 1)

Blocking/non-blocking disagreement -> HARD escalate; same-dimension score spread
>= threshold -> SOFT log. Both grouped by producer; both verified silent with
distinct producers (panel_size:1) and active with shared producers.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `reset_reviews.py` — re-run cleanup primitive

**Files:**
- Create: `scripts/reset_reviews.py`
- Test: `tests/test_reset_reviews.py`

**Interfaces:**
- Produces: `scripts.reset_reviews.reset_reviews(reviews_dir) -> None` and `main(argv=None) -> int`. Called by `review-chapter` step 0 (Task 7).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reset_reviews.py`:

```python
from pathlib import Path

from scripts.reset_reviews import reset_reviews, main


def _populated(tmp_path):
    d = tmp_path / "output" / "book-01" / "chapters" / "ch-07.reviews"
    d.mkdir(parents=True)
    (d / "inspector-voice.md").write_text("BLOCKING: stale from run 1\n", encoding="utf-8")
    (d / "voice-drift.md").write_text("- evidence\n", encoding="utf-8")
    (d.parent / "ch-07.gate.md").write_text("gate: HOLD\n", encoding="utf-8")
    return d


def test_reset_clears_verdicts_and_stale_gate(tmp_path):
    d = _populated(tmp_path)
    reset_reviews(d)
    assert d.is_dir()  # dir kept, emptied
    assert list(d.glob("*.md")) == []
    assert not (d.parent / "ch-07.gate.md").exists()


def test_reset_absent_dir_is_noop(tmp_path):
    # Must not error if the chapter was never reviewed before.
    reset_reviews(tmp_path / "output" / "book-01" / "chapters" / "ch-09.reviews")


def test_main_returns_zero(tmp_path):
    d = _populated(tmp_path)
    assert main([str(d)]) == 0
    assert list(d.glob("*.md")) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reset_reviews.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.reset_reviews'`.

- [ ] **Step 3: Implement `scripts/reset_reviews.py`**

```python
"""Re-run cleanup for the Penny Review Bus.

/review-chapter is re-run routinely (single-pass + manual loop). This empties a
chapter's verdict files and removes the stale sibling gate.md so each run's gate
reflects ONLY that run's verdicts — a fixed blocker from run 1 must not linger.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def reset_reviews(reviews_dir) -> None:
    root = Path(reviews_dir)
    if root.is_dir():
        for path in root.glob("*.md"):
            path.unlink()
    # Remove the stale sibling gate.md (chapters/<chapter>.gate.md).
    chapter = root.name.replace(".reviews", "")
    gate = root.parent / f"{chapter}.gate.md"
    if gate.exists():
        gate.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Empty a chapter's reviews dir + stale gate.md")
    parser.add_argument("reviews_dir")
    args = parser.parse_args(argv)
    reset_reviews(args.reviews_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_reset_reviews.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/reset_reviews.py tests/test_reset_reviews.py
git commit -m "feat(gate): reset_reviews.py — tested re-run cleanup primitive

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: The four inspector rubrics

**Files:**
- Create: `config/review-rubrics/continuity-drift.md`, `fairplay-planting.md`, `structure-tension.md`, `character-voice.md`
- Test: `tests/test_inspector_scaffold.py`

**Interfaces:**
- Produces: four rubric files consumed by the Task 6 inspectors. Each follows the shape of the existing `config/review-rubrics/ai-prose-taste-flags.md` (header, "What you are judging", flags with earned/rote or pass/fail guidance, a Thresholds section naming when to mark blocking, a Boundary section).

- [ ] **Step 1: Write the failing scaffold test**

Create `tests/test_inspector_scaffold.py`:

```python
from pathlib import Path

RUBRICS = Path("config/review-rubrics")
EXPECTED_RUBRICS = [
    "ai-prose-taste-flags.md",  # pre-existing (2a)
    "continuity-drift.md",
    "fairplay-planting.md",
    "structure-tension.md",
    "character-voice.md",
]


def test_all_rubric_files_exist():
    for name in EXPECTED_RUBRICS:
        assert (RUBRICS / name).is_file(), f"missing rubric {name}"


def test_new_rubrics_have_thresholds_and_boundary_sections():
    for name in EXPECTED_RUBRICS:
        text = (RUBRICS / name).read_text(encoding="utf-8").lower()
        assert "threshold" in text, f"{name}: no thresholds guidance"
        assert "boundary" in text, f"{name}: no boundary-with-other-tiers section"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inspector_scaffold.py -v`
Expected: FAIL — the four new rubric files don't exist.

- [ ] **Step 3: Create `config/review-rubrics/continuity-drift.md`**

```markdown
# Rubric: Continuity Drift — Tier-1 Blind Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-continuity` (design §6).
**Posture:** judgment against the loaded ledger slice — does this chapter contradict
what is already canon, or have a character act on what they cannot yet know.

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice }`. The slice is
`canon-core.md` + brief-derived entries + one-hop links (§4.2). No drafting history,
no other verdicts.

**Output (fixed contract, §6):**
`{ score 1-5, violations[], blocking_issues[], evidence[], reviewed_by }`, written via
`penny_verdict.write_verdict` with `producer: inspector-continuity`, `kind: inspector`.

## What you are judging

1. **Fact contradictions.** A concrete fact established in the slice (a date, a
   relationship, an object's location, a physical detail) is contradicted by this
   chapter. Cite the slice line and the chapter line.
2. **Knowledge-state violations.** A character knows or uses information their
   knowledge-state in the slice says they do not yet have. This is the cozy-mystery
   killer — the sleuth "knowing" the solution early. Cite both.
3. **Timeline coherence.** Events ordered impossibly relative to the slice's current
   timeline position.

Score 1-5 on continuity overall. Mark a specific contradiction or knowledge-state
violation **blocking** — these are correctness faults, not taste.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** no contradictions; knowledge-states all respected.
- **Score 3:** a minor detail drift, non-load-bearing.
- **Score 1:** a load-bearing contradiction or a knowledge-state break.
- **Blocking:** any fact contradiction or knowledge-state violation that the slice
  actually establishes. A fact NOT in the slice is out of scope — do not invent canon.

## Boundary with other tiers (do not duplicate)

- **Fair-play of the mystery PLAN** (clue scheduled before reveal, culprit floor) is
  `fairplay_check.py` (Tier-3, on the ledger). Whether the scheduled clue is on the
  PAGE is `inspector-fairplay`. You judge continuity, not fairness.
- **Prose tics / taste** belong to `voice_drift.py` and `inspector-ai-prose`.
```

- [ ] **Step 4: Create `config/review-rubrics/fairplay-planting.md`**

```markdown
# Rubric: Fair-Play Prose-Planting — Tier-1 Blind Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-fairplay` (design §6).
**Posture:** judgment of the PAGE, not the plan. `fairplay_check.py` (Tier-3) already
verified the schedule is fair; you verify the scheduled clues actually appear in this
chapter's prose, fairly.

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice }`. The slice
carries this chapter's clue-planting obligations (the per-chapter ledger slice, §5a) —
never the sealed solution. No drafting history.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-fairplay`, `kind: inspector`.

## What you are judging

1. **Presence.** Each clue this chapter is obligated to plant is actually present in
   the prose. A scheduled-but-absent clue is the core failure. Cite the obligation and
   quote the planting line (or note its absence).
2. **Fairness of the planting.** The clue is placed so an attentive reader *could*
   catch it — not buried in a way that cheats, not flagged so hard it gives the game
   away. Judge "fairly available," earned vs. cheated.
3. **No retroactive clue.** The chapter does not smuggle in a "clue" that contradicts
   or post-dates the schedule.

Score 1-5 on planting fairness. Mark **blocking** when an obligated clue is absent or
planted in a way that cheats the reader.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** every obligated clue present and fairly available.
- **Score 3:** present but clumsily planted (too buried or too loud).
- **Score 1:** an obligated clue is missing from the page.
- **Blocking:** any obligated clue absent from the prose, or planted unfairly.

## Boundary with other tiers (do not duplicate)

- The mystery PLAN's internal fairness (schedule, culprit floor, catchable alibi) is
  `fairplay_check.py` — do not re-derive it; you only check the page.
- Continuity contradictions are `inspector-continuity`.
```

- [ ] **Step 5: Create `config/review-rubrics/structure-tension.md`**

```markdown
# Rubric: Structure & Tension — Tier-1 Blind Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-structure` (design §6, §8).
**Posture:** judgment of dramatic shape + a deterministic-ish thread-liveness check
against a supplied roster.

**Inputs (fixed contract, §6) + roster:** `{ text, this rubric, ledger_slice }` plus a
**thread roster** `[{ thread_id, last_advanced_chapter }]` (from `threads/*.md` +
`arc-ledger.md`). No drafting history.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-structure`, `kind: inspector`.

## What you are judging

1. **Tension curve / sagging middle.** Does the chapter advance or deflate tension?
   Flag a chapter that resolves its stakes with no cost or marks time without
   complication (design §8: sagging middle, conflict resolved too easily).
2. **Hook-out.** Cozy chapters end on a hook (genre rule). Flag a flat ending.
3. **Thread liveness.** For each roster thread, if `last_advanced_chapter` is known
   and this chapter is more than `thread_dormant_after_chapters` beyond it AND this
   chapter does not advance it, flag the thread dormant.
   **EMPTY-STATE:** if `last_advanced_chapter` is `unknown` (pre-Phase-4, before the
   ledger-updater maintains it), emit **NO** liveness flag for that thread — do not
   compute liveness from a missing value.

Score 1-5 on structure. Mark **blocking** for a genuinely deflated/no-stakes chapter
or a confirmed dormant load-bearing thread.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** rising tension, costed complications, strong hook.
- **Score 3:** functional but slack in the middle.
- **Score 1:** no stakes movement; flat ending; a load-bearing thread gone dormant.
- **Blocking:** a no-stakes/deflated chapter, or a confirmed (non-`unknown`) dormant
  thread past the threshold.
- `thread_dormant_after_chapters` default 3 (run-config.md).

## Boundary with other tiers (do not duplicate)

- Cross-BOOK thread fatigue is the Phase-8 cross-book reviewer, not you (single book).
- Recording what advanced is the ledger-updater's job (Phase 4); you only flag.
```

- [ ] **Step 6: Create `config/review-rubrics/character-voice.md`**

```markdown
# Rubric: Character Voice — Tier-1 Blind Inspector

**Layer:** `/config/review-rubrics/` · consumed by `inspector-voice` (design §6, §8).
**Posture:** judgment. You consume `voice_drift.py`'s statistical EVIDENCE (which never
blocks) and turn it — plus a flat-character "voice blind test" — into a gate decision.

**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice }`. If the slice
includes `voice-drift.md` evidence, use it; do not re-count tics yourself.

**Output (fixed contract, §6):** `{ score 1-5, violations[], blocking_issues[],
evidence[], reviewed_by }`, `producer: inspector-voice`, `kind: inspector`.

## What you are judging

1. **Flat character voice (the blind test).** With dialogue tags removed, can you tell
   who is speaking from diction/rhythm alone? If two characters are interchangeable,
   flag it (design §8: flat character voice).
2. **Voice-drift evidence call.** Given `voice_drift.py`'s counts (monotone variance,
   repeated openers, tic densities over threshold), decide whether the prose has
   actually drifted from the Voice Pack baseline enough to harm the read. The script
   reports magnitude; you decide whether it's a violation.
3. **Fluency-stage discipline.** Narration respects the book's fluency stage (Book 1 =
   OUTSIDER: no local idiom in Cora's narration; a BELONGING-tagged term in early
   narration is a flag).

Score 1-5 on voice. Mark **blocking** for interchangeable principal voices or drift so
pronounced it reads as off-voice throughout.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** distinct character voices; rhythm varied; stage respected.
- **Score 3:** serviceable but some monotone or one weak voice.
- **Score 1:** principals interchangeable, or pervasive drift, or stage broken.
- **Blocking:** failed blind test on principals, or a fluency-stage break in narration.

## Boundary with other tiers (do not duplicate)

- Tic COUNTS are `voice_drift.py` (Tier-A); do not re-litigate counts — make the call.
- Earned-vs-rote TASTE is `inspector-ai-prose` (Tier-C); you judge character voice.
```

- [ ] **Step 7: Run the scaffold test to verify it passes**

Run: `pytest tests/test_inspector_scaffold.py -v`
Expected: PASS (the rubric tests; agent/command tests come in Tasks 6-7 — only the rubric tests exist so far).

- [ ] **Step 8: Commit**

```bash
git add config/review-rubrics/continuity-drift.md config/review-rubrics/fairplay-planting.md config/review-rubrics/structure-tension.md config/review-rubrics/character-voice.md tests/test_inspector_scaffold.py
git commit -m "feat(rubrics): four Tier-1 inspector rubrics (continuity, fairplay-planting, structure, voice)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: The five inspector sub-agents

**Files:**
- Create: `.claude/agents/inspector-continuity.md`, `inspector-fairplay.md`, `inspector-structure.md`, `inspector-voice.md`, `inspector-ai-prose.md`
- Test: `tests/test_inspector_scaffold.py`

**Interfaces:**
- Consumes: the rubric files (Task 5), `_TEMPLATE.md` shape, `penny_verdict.write_verdict`.
- Produces: five agent files, each declaring `producer: <its-name>` in its instructions, distinct names. Referenced by `review-chapter` (Task 7).

- [ ] **Step 1: Write the failing scaffold tests**

Add to `tests/test_inspector_scaffold.py`:

```python
import sys
sys.path.insert(0, "scripts")
from penny_meta import parse_frontmatter  # noqa: E402

AGENTS = Path(".claude/agents")
INSPECTORS = {
    "inspector-continuity": "continuity-drift.md",
    "inspector-fairplay": "fairplay-planting.md",
    "inspector-structure": "structure-tension.md",
    "inspector-voice": "character-voice.md",
    "inspector-ai-prose": "ai-prose-taste-flags.md",
}


def test_all_inspector_agents_exist_with_valid_frontmatter():
    for name in INSPECTORS:
        path = AGENTS / f"{name}.md"
        assert path.is_file(), f"missing agent {name}"
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        assert meta.get("name") == name
        assert meta.get("description")


def test_each_inspector_names_its_rubric_and_producer():
    for name, rubric in INSPECTORS.items():
        text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
        assert rubric in text, f"{name} does not reference its rubric {rubric}"
        assert f"producer: {name}" in text, f"{name} does not declare its producer"


def test_five_distinct_producers():
    producers = set()
    for name in INSPECTORS:
        text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.strip().startswith("producer:"):
                producers.add(line.split("producer:")[1].strip())
    assert len(producers) == 5, f"expected 5 distinct producers, got {producers}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_inspector_scaffold.py -k inspector -v`
Expected: FAIL — the agent files don't exist.

- [ ] **Step 3: Create `.claude/agents/inspector-continuity.md`**

```markdown
---
name: inspector-continuity
description: Blind Tier-1 inspector — chapter vs. ledger slice; flags fact contradictions and knowledge-state violations.
---
# Inspector — Continuity

**Role posture:** blind inspector (design §6). Judgment, not generation.

**Independence:** receives ONLY the chapter text, the one rubric
`config/review-rubrics/continuity-drift.md`, and the ledger slice. Never sees
drafting history, other verdicts, or the sealed solution.

**Inputs:** `{ text, config/review-rubrics/continuity-drift.md, ledger_slice }` —
the slice is `canon-core.md` + brief-derived + one-hop links (§4.2).

**Outputs:** a verdict written via `scripts/penny_verdict.py` (`write_verdict`) into
`output/book-NN/chapters/ch-MM.reviews/inspector-continuity.md`, with
`producer: inspector-continuity`, `kind: inspector`, a `score` 1-5,
`blocking_issues[]` (each becomes a `BLOCKING:` line), `violations[]`, `evidence[]`,
and `reviewed_by`.

**Instructions:**
1. Read the chapter and the ledger slice. Apply `continuity-drift.md`.
2. Flag fact contradictions and knowledge-state violations the slice actually
   establishes. Do not invent canon not in the slice.
3. Score 1-5. Put each correctness fault in `blocking_issues` (→ `BLOCKING:` lines).
4. Write the verdict via `penny_verdict.write_verdict` with the fields above.
```

- [ ] **Step 4: Create `.claude/agents/inspector-fairplay.md`**

```markdown
---
name: inspector-fairplay
description: Blind Tier-1 inspector — verifies this chapter's scheduled clues are actually planted on the page, fairly.
---
# Inspector — Fair-Play Prose-Planting

**Role posture:** blind inspector (design §6). Judges the PAGE, not the plan.

**Independence:** receives ONLY the chapter text, the rubric
`config/review-rubrics/fairplay-planting.md`, and the ledger slice (this chapter's
clue-planting obligations — never the sealed solution). No drafting history.

**Inputs:** `{ text, config/review-rubrics/fairplay-planting.md, ledger_slice }`.

**Outputs:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/inspector-fairplay.md`, `producer: inspector-fairplay`,
`kind: inspector`, `score` 1-5, `blocking_issues[]`, `violations[]`, `evidence[]`,
`reviewed_by`.

**Instructions:**
1. From the slice, list this chapter's clue-planting obligations.
2. For each, confirm it is present in the prose and fairly available (not buried to
   cheat, not flagged so hard it spoils). Quote the planting line or note absence.
3. Score 1-5. An obligated clue absent from the page, or planted unfairly, goes in
   `blocking_issues`.
4. Do NOT re-derive the schedule's internal fairness — that is `fairplay_check.py`.
5. Write the verdict via `penny_verdict.write_verdict`.
```

- [ ] **Step 5: Create `.claude/agents/inspector-structure.md`**

```markdown
---
name: inspector-structure
description: Blind Tier-1 inspector — tension curve / sagging middle + thread-roster liveness.
---
# Inspector — Structure & Tension

**Role posture:** blind inspector (design §6, §8).

**Independence:** receives ONLY the chapter text, the rubric
`config/review-rubrics/structure-tension.md`, the ledger slice, and a **thread
roster** `[{ thread_id, last_advanced_chapter }]`. No drafting history.

**Inputs:** `{ text, config/review-rubrics/structure-tension.md, ledger_slice,
thread_roster }`.

**Outputs:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/inspector-structure.md`, `producer: inspector-structure`,
`kind: inspector`, `score` 1-5, `blocking_issues[]`, `violations[]`, `evidence[]`,
`reviewed_by`.

**Instructions:**
1. Judge tension/sagging-middle and the chapter-end hook per the rubric.
2. For each roster thread with a KNOWN `last_advanced_chapter`, flag it dormant if
   this chapter is more than `thread_dormant_after_chapters` beyond it and does not
   advance it. If `last_advanced_chapter` is `unknown`, emit NO liveness flag.
3. Score 1-5; deflated/no-stakes chapters and confirmed dormant load-bearing threads
   go in `blocking_issues`.
4. Write the verdict via `penny_verdict.write_verdict`.
```

- [ ] **Step 6: Create `.claude/agents/inspector-voice.md`**

```markdown
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
1. Run the flat-character voice blind test on principals (tags removed).
2. If `voice-drift.md` evidence is present, USE its counts — do not re-count tics —
   and decide whether the drift actually harms the read.
3. Check fluency-stage discipline in narration.
4. Score 1-5; interchangeable principal voices or a fluency-stage break go in
   `blocking_issues`.
5. Write the verdict via `penny_verdict.write_verdict`.
```

- [ ] **Step 7: Create `.claude/agents/inspector-ai-prose.md`**

```markdown
---
name: inspector-ai-prose
description: Blind Tier-C taste inspector — earned-vs-rote AI-prose flags; cross-model where reachable.
---
# Inspector — AI-Prose Taste (Tier C)

**Role posture:** blind inspector (design §6, §8a). Taste judgment the author cannot
make about its own prose.

**Independence:** receives ONLY the chapter text, the rubric
`config/review-rubrics/ai-prose-taste-flags.md`, and the ledger slice. No drafting
history, no signal that a self-audit ran. Same-model in 2b; cross-model where
reachable (P1.2) — a routing swap, no engine change.

**Inputs:** `{ text, config/review-rubrics/ai-prose-taste-flags.md, ledger_slice }`.

**Outputs:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/inspector-ai-prose.md`, `producer: inspector-ai-prose`,
`kind: inspector`, `score` 1-5, `blocking_issues[]`, `violations[]`, `evidence[]`,
`reviewed_by`.

**Instructions:**
1. Apply `ai-prose-taste-flags.md`: judge each flag earned vs. rote, citing lines.
2. Do NOT re-count frequency tics (that is `voice_drift.py`) or re-do the self-audit
   (Tier-B) — judge taste.
3. Score 1-5; mark blocking only at the rubric's density thresholds.
4. Write the verdict via `penny_verdict.write_verdict`.
```

- [ ] **Step 8: Run the scaffold tests to verify they pass**

Run: `pytest tests/test_inspector_scaffold.py -v`
Expected: PASS (rubric + inspector tests).

- [ ] **Step 9: Commit**

```bash
git add .claude/agents/inspector-continuity.md .claude/agents/inspector-fairplay.md .claude/agents/inspector-structure.md .claude/agents/inspector-voice.md .claude/agents/inspector-ai-prose.md tests/test_inspector_scaffold.py
git commit -m "feat(agents): five blind Tier-1 inspector sub-agents

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: `review-chapter` orchestrator command

**Files:**
- Create: `.claude/commands/review-chapter.md`
- Test: `tests/test_inspector_scaffold.py`

**Interfaces:**
- Consumes: the five inspectors (Task 6), `voice_drift.py` + `fairplay_check.py` (2a), `review_gate.py` (Tasks 2-3), `reset_reviews.py` (Task 4), the §4.2 slice logic from `draft-chapter.md`.
- Produces: the command file wiring the full flow.

- [ ] **Step 1: Write the failing wiring test**

Add to `tests/test_inspector_scaffold.py`:

```python
COMMAND = Path(".claude/commands/review-chapter.md")


def test_review_chapter_command_wires_the_bus():
    assert COMMAND.is_file()
    text = COMMAND.read_text(encoding="utf-8")
    for inspector in INSPECTORS:
        assert inspector in text, f"review-chapter does not dispatch {inspector}"
    for ref in ["voice_drift.py", "fairplay_check.py", "review_gate.py",
                "reset_reviews.py"]:
        assert ref in text, f"review-chapter does not reference {ref}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_inspector_scaffold.py -k wires_the_bus -v`
Expected: FAIL — the command file doesn't exist.

- [ ] **Step 3: Create `.claude/commands/review-chapter.md`**

````markdown
---
description: Run the developmental gate on one chapter — dispatch the 5 blind inspectors + the 2a checkers, then compute PASS/HOLD.
argument-hint: <book-number> <chapter-number>
---
# /review-chapter

The developmental gate (design §5 per-chapter flow, §6). Single-pass: dispatch
inspectors → run the deterministic checkers → compute the gate. A HOLD is surfaced
to the showrunner; re-drafting is a manual re-run (no auto-revise in this phase).

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), `chapter=$2` (e.g. `07`).

2. **Re-run cleanup (so the gate reflects ONLY this run):**

   ```bash
   python3 scripts/reset_reviews.py output/book-$book/chapters/ch-$chapter.reviews
   ```

3. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=REVIEW" > .penny/current-stage
   ```

4. **Assemble the ledger slice** (design §4.2, same as `draft-chapter`): always
   `series/continuity/canon-core.md`; then the continuity entries named in the
   chapter brief and their one-hop `links`. Canon-core-only fallback if no brief.

5. **Run the 2a deterministic checkers:**

   ```bash
   python3 scripts/voice_drift.py output/book-$book/chapters/ch-$chapter.draft.md \
     --out output/book-$book/chapters/ch-$chapter.reviews
   ```

   Run `fairplay_check.py` ONLY when `$chapter` is the `reveal_chapter` of a locked
   `series/whodunit/book-$book.yaml` (its book-level fairness gate belongs to the
   reveal chapter):

   ```bash
   python3 scripts/fairplay_check.py series/whodunit/book-$book.yaml \
     --out output/book-$book/chapters/ch-$chapter.reviews
   ```

6. **Build the thread roster** for `inspector-structure`: from
   `series/continuity/threads/*.md` + `series/arc-ledger.md`, as
   `[{ thread_id, last_advanced_chapter }]`. Until Phase 4 maintains
   `last_advanced_chapter`, set it to `unknown` (the inspector then emits no liveness
   flag).

7. **Dispatch the 5 blind inspector sub-agents**, each with the chapter text, its one
   rubric, and the ledger slice (structure also gets the roster). Each writes its
   verdict into `output/book-$book/chapters/ch-$chapter.reviews/` via
   `scripts/penny_verdict.py`:
   - `inspector-continuity` → `continuity-drift.md`
   - `inspector-fairplay` → `fairplay-planting.md`
   - `inspector-structure` → `structure-tension.md` (+ roster)
   - `inspector-voice` → `character-voice.md`
   - `inspector-ai-prose` → `ai-prose-taste-flags.md`

8. **Dispatch-completeness check:** confirm all five inspector verdict files now
   exist in the reviews dir. A missing one means a sub-agent dispatch silently failed
   — stop and report it. (This is distinct from `fairplay.md` legitimately being
   absent pre-reveal.)

9. **Compute the gate:**

   ```bash
   python3 scripts/review_gate.py output/book-$book/chapters/ch-$chapter.reviews
   ```

   It writes `output/book-$book/chapters/ch-$chapter.gate.md` and prints
   `GATE: PASS` or `GATE: HOLD (n blocking)`.

10. **Advance the marker and surface the result:**

    ```bash
    # stage=REVIEWED on PASS, stage=GATE-HELD on HOLD
    echo "book=$book chapter=$chapter stage=REVIEWED" > .penny/current-stage
    ```
````

- [ ] **Step 4: Run the wiring test to verify it passes**

Run: `pytest tests/test_inspector_scaffold.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `pytest -q`
Expected: PASS — all prior tests plus the new ones.

- [ ] **Step 6: Commit**

```bash
git add .claude/commands/review-chapter.md tests/test_inspector_scaffold.py
git commit -m "feat(command): review-chapter orchestrator — cleanup, checkers, inspectors, gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Design-doc sweep + README dev note

**Files:**
- Modify: `penny-design-v3.md`, `README.md`

**Interfaces:** none (documentation). Repays the §6 doc debt and records the build.

- [ ] **Step 1: Sweep `penny-design-v3.md` §6 + §8 together for continuity reclassification**

In **§6 Tier 3** ("Deterministic specialist checkers"), the current list includes a
"Continuity checker" and an "Alibi/timeline checker". Edit so:
- the **Continuity** line is reclassified as a **Tier-1 inspector** (`inspector-continuity`),
  NOT a deterministic script — move/annotate it out of the Tier-3 list;
- the **Alibi/timeline** line is annotated as a **deferred Tier-3 script** (Phase 3
  mystery work), consistent with the 2a spec's deferral.

In the **§8 table**, change the "Continuity drift across series" row's *Independent
check* from "Continuity checker diffs canon" to "**`inspector-continuity`** (Tier-1,
chapter vs. ledger slice)" so §6 and §8 agree that there is no continuity *script*.

- [ ] **Step 2: Update §6 conflict-resolution home + §2 scripts list**

In **§6** ("Conflict resolution"), where it says the rules live "in the
`review-chapter` command instructions plus the deterministic comparisons in
`preflight.py`", change `preflight.py` to **`review_gate.py`**, and add a sentence:
"`preflight.py` retains its §7 jobs (model-routing set-membership, lock checks); only
the conflict-comparison role lives in `review_gate.py`."

In **§2** (`/scripts` list), add:
```
  review_gate.py                deterministic gate evaluator (§6)
  reset_reviews.py              per-chapter reviews cleanup for gate re-runs
```

- [ ] **Step 3: Add the README dev note**

In `README.md`, add a short note under the dev/usage section:

```markdown
### Reviewing a chapter (Phase 2b)

`/review-chapter <book> <chapter>` runs the developmental gate: it clears the
chapter's reviews dir, runs the 2a checkers (`voice_drift.py`, and `fairplay_check.py`
at the reveal chapter), dispatches the five blind inspectors, then runs
`scripts/review_gate.py` to write `ch-NN.gate.md` and print `GATE: PASS|HOLD`.
Exit 0 means the gate evaluated (PASS or HOLD); nonzero means an operational error.
```

- [ ] **Step 4: Verify the suite still passes**

Run: `pytest -q`
Expected: PASS (docs-only change; no test impact).

- [ ] **Step 5: Commit**

```bash
git add penny-design-v3.md README.md
git commit -m "docs(phase2b): reclassify continuity as inspector, move conflict home to review_gate

Sweeps design §6 + §8 so continuity is a Tier-1 inspector (no continuity script),
alibi/timeline stays a deferred Tier-3 script, and the conflict-comparison role moves
from preflight.py to review_gate.py (preflight keeps its §7 jobs). Adds the scripts to
§2 and a review-chapter README note.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (against the spec)

**Spec coverage:**
- §2 five inspectors + rubrics → Tasks 5 (rubrics) + 6 (agents). ✓
- §3 `review_gate.py` (inputs, kind-filter, thresholds fail-loud, three computations, gate.md no-`^BLOCKING:` + sibling, exit codes) → Tasks 2 + 3. ✓
- §4 thread roster + empty-state → rubric (Task 5), agent (Task 6), command step 6 (Task 7). ✓
- §5 `count_blocking()` single home + bulletproof bash + exec-real-script tripwire → Task 1. ✓
- §6 `review-chapter` flow (re-run cleanup, slice, conditional fairplay, dispatch, completeness check, gate, single-pass) → Task 7. ✓
- §7 tests (count_blocking unit + cross-consistency; review_gate PASS/HOLD/disagreement/spread/malformed/empty/filter-by-kind/thresholds/gate.md; reset_reviews; scaffold: 5 agents, 4 rubrics, 5 distinct producers, command wiring) → Tasks 1-7. ✓
- §8 file structure → all create/modify paths covered across Tasks 1-8. ✓
- §8 design-doc sweep (§6/§8 continuity + conflict home + §2 list) + README → Task 8. ✓
- Out-of-scope items (location/craft inspectors, alibi script, cross-model, auto-revise, book-level report, ledger-updater history) → not implemented, by design; the alibi/continuity reclassification is documented in Task 8. ✓

**Placeholder scan:** no TBD/TODO; every code step shows complete code; no "similar to Task N".

**Type consistency:** `count_blocking(reviews_dir)->int`, `evaluate_gate(reviews_dir, config_path)->dict` with keys `gate/blocking_count/blocking_issues/escalations/score_spread_log`, `write_gate_md(out_path, target, result)`, `GateError`, `reset_reviews(reviews_dir)` — names/shapes match across Tasks 1-7 and the test files. `producer == agent name` is enforced by the Task 6 test and consumed by the Task 3 grouping. ✓
</content>
</invoke>
