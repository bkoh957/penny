# Outline Developmental Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pre-draft, advisory outline craft-review tier: an independent Claude+Codex reviewer panel produces side-by-side prose feedback, decomposed into ID'd items with an owner-set state, tracked in an append-only YAML ledger, surfaced at draft time by a deterministic banner.

**Architecture:** All correctness lives in one deterministic, unit-tested script (`scripts/outline_feedback.py`: `append` / `status` / `render`). The panel (a Claude sub-agent + a Codex invocation), the genre rubric, the `/review-outline` command, and the `/draft-chapter` banner hook are orchestration/data layered on top — no LLM judgment in any script, per CLAUDE.md's three-layer rule.

**Tech Stack:** Python 3 stdlib + PyYAML (already the repo's only dep; correct for the nested human-edited ledger per the dependency-split rule). Markdown runbooks/agents. pytest (`pythonpath=.` via pytest.ini).

## Global Constraints

- **Engine stays genre/series-agnostic.** No genre or series content in `scripts/` or agent/command logic. The craft rubric is pack data: `genres/<g>/review-rubrics/outline-craft.md`. (CLAUDE.md)
- **Advisory, never a gate.** Nothing here blocks drafting, writes a certificate, or emits a `^BLOCKING:` line. The status script MUST always exit 0. (spec §1, §8)
- **Scripts never make an LLM judgment.** Deterministic layer is pure Python. (CLAUDE.md)
- **Ledger is append-only over items.** The `append` function MUST NOT modify or delete any existing item's `id`/`source`/`pass`/`state`/`text`; it only appends new items and updates `reviewed_outline_sha256`. This is the load-bearing invariant. (spec §6)
- **No scores.** Feedback is prose; state is `open|solved|rejected`; the banner count is an open-item backlog, not a grade. (spec §1, §5)
- **Solution-blind.** The reviewer panel is denied `output/book-NN/mystery-solution*.md` and the whodunit answer fields. (spec §4)
- **Directly-invoked scripts need the sys.path shim** `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` before `from scripts import …`, because runbooks call them by file path via `${CLAUDE_PLUGIN_ROOT}`. (CLAUDE.md / existing scripts)
- **Runbooks reference scripts as** `${CLAUDE_PLUGIN_ROOT}/scripts/...` and take the book number as a positional arg (`$1`), matching `draft-chapter.md`.
- **`config/run-config.md` is series-side, not in the engine.** The panel roster is read from run-config via the overlay when present; the command falls back to a built-in default `[claude, codex]`. Do NOT create an engine `config/run-config.md`.

---

## File Structure

- `scripts/outline_feedback.py` — **new**, the only new engine logic: ledger load/append (append-only, monotonic IDs), `status` banner, `render` view. All correctness here.
- `tests/test_outline_feedback.py` — **new**, unit tests incl. the append-only invariant.
- `tests/fixtures/outline-feedback/` — **new**, self-contained ledger + points fixtures (never live `series/` content).
- `genres/cozy-mystery/review-rubrics/outline-craft.md` — **new**, the cozy coverage checklist (pack data).
- `agents/outline-reviewer.md` — **new**, the Claude reviewer role (prose points, solution-blind, dedup-aware), mirroring `agents/developmental-editor.md`.
- `commands/review-outline.md` — **new**, orchestrator: dispatch panel → `append` → `render` → print.
- `commands/draft-chapter.md` — **modify**, add one non-blocking banner step.

Tasks 1–4 (Python) are strict TDD. Tasks 5–8 (data/runbooks) are not unit-tested (LLM/runbook, per CLAUDE.md) — they carry authored content + acceptance checks + a manual smoke.

---

### Task 1: Ledger core — load, IDs, append-only append

**Files:**
- Create: `scripts/outline_feedback.py`
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: `scripts.penny_paths` (`output_path`, `input_path`).
- Produces:
  - `ledger_path(book, repo_root=None) -> Path` → `output/book-<book>/reports/outline-feedback.yaml`
  - `outline_src_path(book, repo_root=None) -> Path` → `input/book-<book>/outline.md`
  - `view_path(book, repo_root=None) -> Path` → `output/book-<book>/reports/outline-review.md`
  - `sha256_of(path) -> str` (hex digest; `""` if the file is missing)
  - `empty_ledger(book) -> dict` → `{"book": book, "reviewed_outline_sha256": "", "items": []}`
  - `load_ledger(book, repo_root=None) -> dict` (returns `empty_ledger` if the file is absent)
  - `max_id_num(items) -> int` (highest `n` in `OF-<n>`; 0 if none)
  - `max_pass(items) -> int` (highest `pass`; 0 if none)
  - `append_items(ledger, new_points, *, reviewed_sha) -> dict` where `new_points: list[{"source": str, "text": str}]`. Returns a NEW ledger with new items appended (`id` monotonic from `max_id_num+1`, `pass = max_pass+1` shared by all points in the call, `state="open"`) and `reviewed_outline_sha256=reviewed_sha`. Existing items unchanged.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_outline_feedback.py
import copy
import scripts.outline_feedback as of


def _seed():
    return {
        "book": "01",
        "reviewed_outline_sha256": "oldsha",
        "items": [
            {"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "a"},
            {"id": "OF-2", "source": "codex", "pass": 1, "state": "rejected", "text": "b"},
        ],
    }


def test_append_preserves_existing_items_exactly():
    ledger = _seed()
    before = copy.deepcopy(ledger["items"])
    out = of.append_items(
        ledger,
        [{"source": "claude", "text": "c"}, {"source": "codex", "text": "d"}],
        reviewed_sha="newsha",
    )
    assert out["items"][:2] == before  # existing items byte-identical
    assert out["reviewed_outline_sha256"] == "newsha"


def test_append_allocates_monotonic_ids_and_next_pass():
    out = of.append_items(_seed(), [{"source": "claude", "text": "c"}], reviewed_sha="s")
    assert out["items"][2] == {
        "id": "OF-3", "source": "claude", "pass": 2, "state": "open", "text": "c",
    }


def test_append_shares_one_pass_across_all_new_points():
    out = of.append_items(
        _seed(),
        [{"source": "claude", "text": "c"}, {"source": "codex", "text": "d"}],
        reviewed_sha="s",
    )
    assert out["items"][2]["pass"] == out["items"][3]["pass"] == 2
    assert out["items"][2]["id"] == "OF-3" and out["items"][3]["id"] == "OF-4"


def test_append_onto_empty_ledger_starts_at_one_and_pass_one():
    out = of.append_items(of.empty_ledger("01"), [{"source": "claude", "text": "x"}], reviewed_sha="s")
    assert out["items"] == [{"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "x"}]


def test_append_does_not_mutate_input_ledger():
    ledger = _seed()
    of.append_items(ledger, [{"source": "claude", "text": "c"}], reviewed_sha="s")
    assert len(ledger["items"]) == 2 and ledger["reviewed_outline_sha256"] == "oldsha"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: FAIL / collection error — `module scripts.outline_feedback has no attribute …` / import error.

- [ ] **Step 3: Write the minimal implementation**

```python
# scripts/outline_feedback.py
"""Outline-review feedback ledger + banner (deterministic, advisory, reporting-only).

Owns the append-only feedback ledger for the pre-draft outline review tier:
- `append` : append a review pass's prose points as new OF-<n> items (never mutates
  existing items or the showrunner's per-item state).
- `status` : the draft-time banner — open-item backlog + outline staleness. NEVER exits
  nonzero (it must never block drafting).
- `render` : regenerate the side-by-side markdown reading view from the yaml.

Nested human-edited data → PyYAML (the whodunit-ledger side of the dependency-split rule).
Zero LLM/genre judgment. See spec 2026-07-09-outline-developmental-review-design.md.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts import penny_paths

VALID_STATES = ("open", "solved", "rejected")


def ledger_path(book, repo_root=None) -> Path:
    return penny_paths.output_path(f"book-{book}/reports/outline-feedback.yaml", root=repo_root)


def view_path(book, repo_root=None) -> Path:
    return penny_paths.output_path(f"book-{book}/reports/outline-review.md", root=repo_root)


def outline_src_path(book, repo_root=None) -> Path:
    return penny_paths.input_path(f"book-{book}/outline.md", root=repo_root)


def sha256_of(path) -> str:
    p = Path(path)
    if not p.is_file():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def empty_ledger(book) -> dict:
    return {"book": book, "reviewed_outline_sha256": "", "items": []}


def load_ledger(book, repo_root=None) -> dict:
    p = ledger_path(book, repo_root)
    if not p.is_file():
        return empty_ledger(book)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return empty_ledger(book)
    data.setdefault("items", [])
    data.setdefault("reviewed_outline_sha256", "")
    return data


def max_id_num(items) -> int:
    nums = []
    for it in items:
        raw = str(it.get("id", ""))
        if raw.startswith("OF-") and raw[3:].isdigit():
            nums.append(int(raw[3:]))
    return max(nums) if nums else 0


def max_pass(items) -> int:
    passes = [it.get("pass", 0) for it in items if isinstance(it.get("pass"), int)]
    return max(passes) if passes else 0


def append_items(ledger, new_points, *, reviewed_sha) -> dict:
    out = copy.deepcopy(ledger)
    items = out.setdefault("items", [])
    next_id = max_id_num(items) + 1
    next_pass = max_pass(items) + 1
    for pt in new_points:
        items.append({
            "id": f"OF-{next_id}",
            "source": pt["source"],
            "pass": next_pass,
            "state": "open",
            "text": pt["text"],
        })
        next_id += 1
    out["reviewed_outline_sha256"] = reviewed_sha
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "feat(outline-review): append-only feedback ledger core"
```

---

### Task 2: `status` banner — open backlog + staleness, never nonzero

**Files:**
- Modify: `scripts/outline_feedback.py`
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: `load_ledger`, `sha256_of`, `outline_src_path`, `ledger_path`.
- Produces:
  - `open_items(ledger) -> list` (items with `state == "open"`)
  - `status_line(book, repo_root=None) -> str` (the banner text; pure — no printing)
  - `main(argv)` supporting `status <book>` (prints `status_line`, returns 0 always).

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_outline_feedback.py
import os


def _write_ledger(tmp_path, book, ledger):
    d = tmp_path / "output" / f"book-{book}" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline-feedback.yaml").write_text(of.yaml.safe_dump(ledger), encoding="utf-8")


def _write_outline(tmp_path, book, text):
    d = tmp_path / "input" / f"book-{book}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline.md").write_text(text, encoding="utf-8")


def test_status_nudges_when_no_ledger(tmp_path):
    line = of.status_line("01", repo_root=tmp_path)
    assert "no outline review yet" in line


def test_status_stale_when_outline_changed(tmp_path):
    _write_outline(tmp_path, "01", "new outline text")
    _write_ledger(tmp_path, "01", {"book": "01", "reviewed_outline_sha256": "stale",
                                   "items": [{"id": "OF-1", "source": "claude", "pass": 1,
                                              "state": "open", "text": "x"}]})
    line = of.status_line("01", repo_root=tmp_path)
    assert "changed since" in line and "re-run" in line


def test_status_open_backlog_when_fresh(tmp_path):
    _write_outline(tmp_path, "01", "body")
    sha = of.sha256_of(tmp_path / "input" / "book-01" / "outline.md")
    _write_ledger(tmp_path, "01", {"book": "01", "reviewed_outline_sha256": sha,
        "items": [
            {"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "x"},
            {"id": "OF-2", "source": "codex", "pass": 1, "state": "solved", "text": "y"},
        ]})
    line = of.status_line("01", repo_root=tmp_path)
    assert "1 open" in line and "OF-1" in line


def test_status_clean_when_fresh_and_none_open(tmp_path):
    _write_outline(tmp_path, "01", "body")
    sha = of.sha256_of(tmp_path / "input" / "book-01" / "outline.md")
    _write_ledger(tmp_path, "01", {"book": "01", "reviewed_outline_sha256": sha,
        "items": [{"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "x"}]})
    assert "no open items" in of.status_line("01", repo_root=tmp_path)


def test_status_cli_always_exits_zero(tmp_path, capsys):
    # even with a garbage/absent setup, status must never block a draft
    assert of.main(["status", "99", "--root", str(tmp_path)]) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_feedback.py -k status -v`
Expected: FAIL — `status_line` / `main` not defined.

- [ ] **Step 3: Write the minimal implementation**

Add to `scripts/outline_feedback.py`:

```python
def open_items(ledger) -> list:
    return [it for it in ledger.get("items", []) if it.get("state") == "open"]


def status_line(book, repo_root=None) -> str:
    if not ledger_path(book, repo_root).is_file():
        return f"no outline review yet — consider /review-outline {book}"
    ledger = load_ledger(book, repo_root)
    cur = sha256_of(outline_src_path(book, repo_root))
    if cur != ledger.get("reviewed_outline_sha256", ""):
        return f"⚠ OUTLINE changed since its last review — re-run /review-outline {book}"
    opens = open_items(ledger)
    if opens:
        ids = ", ".join(it["id"] for it in opens)
        rel = f"output/book-{book}/reports/outline-feedback.yaml"
        return (f"⚠ OUTLINE: {len(opens)} open feedback item(s) ({ids}) — "
                f"see {rel}. Drafting anyway.")
    return f"✓ outline reviewed — no open items (book {book})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Outline-review feedback ledger tool.")
    ap.add_argument("cmd", choices=["status"])
    ap.add_argument("book")
    ap.add_argument("--root", default=None, help="repo/series root override (tests)")
    args = ap.parse_args(argv)
    root = Path(args.root) if args.root else None
    if args.cmd == "status":
        print(status_line(args.book, repo_root=root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

No stubs: `main` is complete for this task. Tasks 3 and 4 extend its `choices` and add
one branch each as they add the `render`/`append` functions, so `main` stays coherent at
every task.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS (all Task 1 + Task 2 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "feat(outline-review): status banner (open backlog + staleness)"
```

---

### Task 3: `render` — side-by-side markdown view

**Files:**
- Modify: `scripts/outline_feedback.py`
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: `load_ledger`, `view_path`.
- Produces:
  - `render_view(ledger) -> str` (markdown; open items foregrounded, then solved, then rejected; each line carries `id`, `source`, `text`).
  - `_cli_render(book, root)` writes `render_view(load_ledger(...))` to `view_path`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_outline_feedback.py
def test_render_groups_open_first_and_tags_source():
    ledger = {"book": "01", "reviewed_outline_sha256": "s", "items": [
        {"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "fixed ch9"},
        {"id": "OF-2", "source": "codex", "pass": 1, "state": "open", "text": "romance thin"},
        {"id": "OF-3", "source": "claude", "pass": 1, "state": "rejected", "text": "disagree"},
    ]}
    md = of.render_view(ledger)
    assert md.index("Open") < md.index("Solved") < md.index("Rejected")
    assert "OF-2" in md and "codex" in md and "romance thin" in md
    # a purely-solved/rejected item still appears, just not under Open
    assert "OF-1" in md and "OF-3" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_feedback.py -k render -v`
Expected: FAIL — `render_view` not defined.

- [ ] **Step 3: Write the minimal implementation**

Add `render_view` and `_cli_render`:

```python
def render_view(ledger) -> str:
    book = ledger.get("book", "?")
    lines = [f"# Outline review — book {book}", "",
             "_Side-by-side feedback; edit `state` in outline-feedback.yaml to disposition._", ""]
    buckets = [("Open", "open"), ("Solved", "solved"), ("Rejected", "rejected")]
    for title, state in buckets:
        rows = [it for it in ledger.get("items", []) if it.get("state") == state]
        lines.append(f"## {title} ({len(rows)})")
        if not rows:
            lines.append("_none_")
        for it in rows:
            lines.append(f"- **{it.get('id')}** · _{it.get('source')}_ · pass {it.get('pass')}")
            lines.append(f"  {it.get('text', '').strip()}")
        lines.append("")
    return "\n".join(lines)


def _cli_render(book, root):
    ledger = load_ledger(book, repo_root=root)
    p = view_path(book, repo_root=root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_view(ledger), encoding="utf-8")
    print(f"rendered {p}")
```

Then extend `main` to accept `render` — change the `choices` line and add the branch:

```python
    ap.add_argument("cmd", choices=["status", "render"])
```
```python
    if args.cmd == "status":
        print(status_line(args.book, repo_root=root))
    elif args.cmd == "render":
        _cli_render(args.book, root)
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_outline_feedback.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "feat(outline-review): render side-by-side markdown view"
```

---

### Task 4: `append` CLI — marshal panel points onto the ledger

**Files:**
- Modify: `scripts/outline_feedback.py`
- Test: `tests/test_outline_feedback.py`

**Interfaces:**
- Consumes: `load_ledger`, `append_items`, `sha256_of`, `outline_src_path`, `ledger_path`, `write_view`.
- Produces:
  - `_cli_append(book, points_path, root)` — reads a JSON array of `{source,text}`, computes the reviewed sha from the current outline, appends, writes the ledger AND re-renders the view.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_outline_feedback.py
def test_cli_append_writes_ledger_and_view(tmp_path):
    _write_outline(tmp_path, "01", "the outline body")
    points = tmp_path / "pts.json"
    points.write_text(of.json.dumps([
        {"source": "claude", "text": "romance thin ch7-11"},
        {"source": "codex", "text": "ch9 beat too vague"},
    ]), encoding="utf-8")

    rc = of.main(["append", "01", "--points", str(points), "--root", str(tmp_path)])
    assert rc == 0

    ledger = of.load_ledger("01", repo_root=tmp_path)
    assert [it["id"] for it in ledger["items"]] == ["OF-1", "OF-2"]
    assert all(it["state"] == "open" and it["pass"] == 1 for it in ledger["items"])
    assert ledger["reviewed_outline_sha256"] == of.sha256_of(
        tmp_path / "input" / "book-01" / "outline.md")
    assert of.view_path("01", repo_root=tmp_path).is_file()

    # second pass appends without disturbing the first pass's items/states
    (tmp_path / "input" / "book-01" / "outline.md").write_text("edited body", encoding="utf-8")
    points.write_text(of.json.dumps([{"source": "claude", "text": "new concern"}]), encoding="utf-8")
    of.main(["append", "01", "--points", str(points), "--root", str(tmp_path)])
    ledger2 = of.load_ledger("01", repo_root=tmp_path)
    assert [it["id"] for it in ledger2["items"]] == ["OF-1", "OF-2", "OF-3"]
    assert ledger2["items"][2] == {"id": "OF-3", "source": "claude", "pass": 2,
                                   "state": "open", "text": "new concern"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_feedback.py -k cli_append -v`
Expected: FAIL — `_cli_append` is a no-op stub; ledger not written.

- [ ] **Step 3: Write the minimal implementation**

Add `write_ledger` and `_cli_append`:

```python
def write_ledger(ledger, book, repo_root=None) -> None:
    p = ledger_path(book, repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _cli_append(book, points_path, root):
    if not points_path:
        raise SystemExit("append: --points <json-file> is required")
    new_points = json.loads(Path(points_path).read_text(encoding="utf-8"))
    reviewed_sha = sha256_of(outline_src_path(book, repo_root=root))
    ledger = append_items(load_ledger(book, repo_root=root), new_points, reviewed_sha=reviewed_sha)
    write_ledger(ledger, book, repo_root=root)
    _cli_render(book, root)
    print(f"appended {len(new_points)} item(s) to book-{book} outline ledger")
```

Then extend `main` to accept `append` — change the `choices` line, add the `--points`
argument, and add the branch:

```python
    ap.add_argument("cmd", choices=["status", "render", "append"])
    ...
    ap.add_argument("--points", help="append: path to a JSON array of {source,text}")
```
```python
    elif args.cmd == "append":
        _cli_append(args.book, args.points, root)
    return 0
```

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest tests/test_outline_feedback.py -v && python3 -m pytest -q`
Expected: PASS (new file green; total suite still green — should read 308 + the new tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_feedback.py tests/test_outline_feedback.py
git commit -m "feat(outline-review): append CLI marshals panel points onto the ledger"
```

---

### Task 5: The cozy coverage rubric (pack data)

**Files:**
- Create: `genres/cozy-mystery/review-rubrics/outline-craft.md`

**Interfaces:** none (data). Consumed by the panel prompt (Tasks 6–7).

- [ ] **Step 1: Author the rubric** (complete content — it is a coverage checklist, NOT a grade sheet)

```markdown
# Outline craft — cozy-mystery coverage checklist

A reviewer reading the whole outline before drafting MUST address each area below **in
prose**. Do not score. Do not grade 1–5. Name what works, name what is thin, and for
anything thin quote the beat and suggest one concrete move. Silence on an area is a gap —
say "no notes here" explicitly if it is strong.

You are **solution-blind**: never state or infer whodunit. Judge the plan's craft, not its
fairness (fairness is gated elsewhere).

Cover, at minimum:

- **Escalation** — do the chapter problems *rise* across the arc, or plateau?
- **Connection / causality** — does each chapter's trouble grow *out of* the previous one,
  or arrive unrelated?
- **Strand sufficiency & balance** — is each declared strand (Mystery / Personal /
  Romance / Business) *present enough* across the book and never dark too long? For a cozy,
  the romance/community warmth is why readers are here — call out long gaps.
- **Mystery progression** — does the mystery thread actually *advance* in chapters that
  claim to move it?
- **Beat draftability** — is each chapter's beat *specific* enough to steer a strong draft,
  or is it a placeholder ("she investigates the shop")?
- **Hook chain** — does each chapter's hook genuinely earn the next?

If a `--focus` directive is supplied, weight it heavily *in addition to* the areas above —
never *instead of* them.
```

- [ ] **Step 2: Acceptance check**

Confirm the file exists and lists all six coverage areas, contains no numeric scoring, and states the solution-blind constraint.
Run: `grep -c -E "Escalation|Connection|Strand sufficiency|Mystery progression|Beat draftability|Hook chain" genres/cozy-mystery/review-rubrics/outline-craft.md`
Expected: `6`.

- [ ] **Step 3: Commit**

```bash
git add genres/cozy-mystery/review-rubrics/outline-craft.md
git commit -m "feat(outline-review): cozy outline-craft coverage rubric (pack data)"
```

---

### Task 6: The `outline-reviewer` agent (Claude panel member)

**Files:**
- Create: `agents/outline-reviewer.md`
- Reference (mirror its shape): `agents/developmental-editor.md`

**Interfaces:** invoked by `/review-outline` (Task 7) with `{ outline text, outline-craft rubric, series bible, canon-core, arc-ledger (optional), current ledger for dedup, optional --focus }`. Returns a JSON array of `{ "text": <one prose point> }` (the command tags `source` and allocates IDs).

- [ ] **Step 1: Author the agent** (complete content)

```markdown
---
name: outline-reviewer
description: Context-rich pre-draft outline craft reader — one independent panel member. Produces side-by-side prose feedback (no scores) on the whole outline; advisory, solution-blind, never gates.
---
# Outline Reviewer

**Role posture:** a developmental read of the WHOLE outline, before any chapter is drafted.
You are one member of an independent panel; you do NOT see the other member's take this
pass. Your job is a craft diagnosis, not a rewrite and not a fairness check.

**Independence — context-rich, NOT blind (but solution-blind).** You receive the whole
outline, the genre coverage rubric, the series bible, canon-core, and (if present) the
arc-ledger. You are **denied the whodunit solution** — never state or infer whodunit.

**Inputs:** `{ whole outline.md, genres/<g>/review-rubrics/outline-craft.md, series bible,
canon-core, arc-ledger (optional), the current feedback ledger (for dedup), optional
--focus directive }`.

**Hard constraints:**
- **Prose, no scores.** Never emit a 1–5 grade or a scorecard. Write an editor's letter.
- **Advisory — never block.** Never emit any `^BLOCKING:` line.
- **Diagnose, never rewrite.** Quote the beat, name the missing craft, suggest one concrete
  move. New writing flows back to the outline author, not to you.
- **Solution-blind.** Never name or imply the culprit/motive.
- **Dedup across passes.** You are shown the current ledger. Do NOT re-raise an item that is
  already `open`, `solved`, or `rejected` unless you have something materially new; you MAY
  add a new point noting a `rejected` concern still stands, with fresh reasoning.

**Instructions:**
1. Read the rubric's coverage areas. Read the whole outline as an arc.
2. Address every coverage area in prose. If `--focus` is set, weight it heavily in addition.
3. Produce your feedback as a JSON array of objects `{ "text": "<one focused prose point>" }`
   — one object per discrete point (quote the beat + name the gap + a concrete move).
   Emit `[]` if you genuinely have nothing new to add this pass. Do NOT assign IDs; do NOT
   add a `source` field (the command owns both).
```

- [ ] **Step 2: Acceptance check**

Confirm the agent file states: prose/no-scores, advisory/no-BLOCKING, solution-blind, dedup, and the JSON-array output contract.
Run: `grep -c -E "no scores|BLOCKING|solution-blind|dedup|JSON array" agents/outline-reviewer.md` (expect ≥ 4; wording may vary — verify by eye).

- [ ] **Step 3: Commit**

```bash
git add agents/outline-reviewer.md
git commit -m "feat(outline-review): outline-reviewer agent (Claude panel member)"
```

---

### Task 7: The `/review-outline` command (panel orchestrator)

**Files:**
- Create: `commands/review-outline.md`

**Interfaces:** dispatches the panel, writes points JSON, calls `scripts/outline_feedback.py append`, prints the result. Panel roster from run-config `outline_review_panel` when present, else default `[claude, codex]`.

- [ ] **Step 1: Author the command** (complete runbook)

```markdown
---
description: Independent pre-draft outline craft review — dispatch the Claude+Codex panel, append side-by-side prose feedback to the tracked ledger. Advisory; never gates.
argument-hint: <book-number> [--focus "<directive>"]
---
# /review-outline

Runs an INDEPENDENT reviewer panel over the whole outline and records side-by-side prose
feedback as ID'd items you can disposition. Advisory — nothing here blocks drafting.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`); optional `--focus "<directive>"` (only when you
   noticed the review missed something — the default run is unsteered).

2. **Preconditions:**
   ```bash
   test -f "input/book-$1/outline.md" || { echo "no outline for book $1 — run /scaffold-book or /expand-outline first"; exit 1; }
   ```
   Resolve the active genre (via `${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py`) and require
   its `review-rubrics/outline-craft.md`. If the active genre pack ships no `outline-craft.md`,
   abort: this tier needs the rubric.

3. **Marker:**
   ```bash
   mkdir -p .penny && echo "book=$1 stage=OUTLINE-REVIEW" > .penny/current-stage
   ```

4. **Resolve the panel roster:** read `outline_review_panel` from the active
   `config/run-config.md` (via the config overlay) if present; otherwise default to
   `[claude, codex]`.

5. **Load the current ledger** for dedup context (if it exists):
   `output/book-$1/reports/outline-feedback.yaml`.

6. **Dispatch each panel member independently, with identical inputs** (whole
   `input/book-$1/outline.md`, the genre `outline-craft.md`, `input/series/series-bible.md`,
   `series/continuity/canon-core.md`, `series/arc-ledger.md` if present, the current ledger
   for dedup, and the `--focus` directive if given). **Solution-blind:** do NOT pass
   `output/book-$1/mystery-solution*.md` or the whodunit answer fields.
   - `claude` → dispatch the `outline-reviewer` sub-agent.
   - `codex` → send the SAME rubric + inputs to the Codex reviewer via the codex plugin
     runtime (independent tool; this is the "difference, not identity" second set of eyes).
   - If a member is unreachable, continue with the rest and note
     `independence reduced: <member> unreachable this pass` in the console output.

7. **Collect points → JSON.** Each member returns a JSON array of `{ "text": ... }`. Tag
   each point with its member as `source` and concatenate into one array
   `[{ "source": "claude", "text": ... }, { "source": "codex", "text": ... }, ...]`. Write
   it to a temp file, e.g. `.penny/outline-points-$1.json`.

8. **Append + render** (deterministic; append-only — never disturbs your existing states):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" append $1 --points ".penny/outline-points-$1.json"
   ```

9. **Print the outcome:** the new items (id · source · one-line headline) and the current
   open-item count. Point the user at `output/book-$1/reports/outline-review.md` (side-by-side
   view) and `outline-feedback.yaml` (edit `state` to disposition: `open`→`solved`/`rejected`).

10. **Marker:**
    ```bash
    echo "book=$1 stage=OUTLINE-REVIEWED" > .penny/current-stage
    ```

Re-run any time after editing the outline; passes accumulate in the ledger and your
dispositions are never overwritten.
```

- [ ] **Step 2: Acceptance check**

Confirm the runbook: dispatches both panel members with identical solution-blind inputs, tags `source`, calls the `append` subcommand, and never gates.
Run: `grep -c -E "outline-reviewer|codex|append|solution-blind|independence reduced" commands/review-outline.md` (verify by eye that each concept is present).

- [ ] **Step 3: Commit**

```bash
git add commands/review-outline.md
git commit -m "feat(outline-review): /review-outline panel orchestrator"
```

---

### Task 8: Draft-time banner hook (non-blocking)

**Files:**
- Modify: `commands/draft-chapter.md`

**Interfaces:** adds one step that runs `scripts/outline_feedback.py status $1` and surfaces it; drafting proceeds regardless.

- [ ] **Step 1: Add the banner step**

Insert a new step immediately AFTER the Step 0 pre-flight gate block and BEFORE "Parse args" in `commands/draft-chapter.md`:

```markdown
0b. **Outline review notice (advisory, non-blocking).** Surface any open outline feedback
    or staleness before drafting. This NEVER blocks — always proceed regardless of output:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_feedback.py" status $1
    ```

    An open-item or "stale — re-run /review-outline" notice is a reminder, not a gate.
```

- [ ] **Step 2: Acceptance check**

Confirm the step exists, calls `outline_feedback.py status $1`, and is marked non-blocking.
Run: `grep -n "outline_feedback.py status" commands/draft-chapter.md`
Expected: one match, inside `draft-chapter.md`, after the preflight block.

- [ ] **Step 3: Manual smoke (end-to-end, deterministic layer)**

```bash
# from a scratch dir with a fake series root, or the thriller/cozy fixture:
python3 scripts/outline_feedback.py status 01   # → "no outline review yet …" (exit 0)
echo $?                                          # → 0
```
Expected: prints a nudge and exits 0.

- [ ] **Step 4: Commit**

```bash
git add commands/draft-chapter.md
git commit -m "feat(outline-review): non-blocking outline-review banner in /draft-chapter"
```

---

## Final verification

- [ ] Run the full suite: `python3 -m pytest -q` — expect the prior 308 + the new `test_outline_feedback.py` tests, all green.
- [ ] `python3 scripts/outline_feedback.py status 01` in a series with no review → nudge, exit 0.
- [ ] Confirm no engine `config/run-config.md` was created (panel default lives in the command).
- [ ] Confirm nothing new emits `^BLOCKING:` and `outline_feedback.py status` cannot return nonzero (the `test_status_cli_always_exits_zero` test guards this).
