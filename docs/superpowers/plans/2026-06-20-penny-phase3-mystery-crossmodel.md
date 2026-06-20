# Penny Phase 3 — Mystery + Cross-model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn on the per-book mystery authorship pipeline (`/plan-mystery` + `mystery-planner`) and the deterministic pre-flight gates (`preflight.py`) that certify it, and record Codex-via-plugin as the cross-model alternate.

**Architecture:** A lock file is a *certificate* — it exists only if `fairplay_check.py` (numeric fairness + character-id existence) and `lexicon_check.py --validate` (schema) both passed for the adjacent ledger. `/plan-mystery` validates-once-then-freezes; `/draft-chapter` gates cheaply by trusting the lock. `preflight.py` is one tool with three subcommands (`lock-mystery`, `draft`, `assemble`), all built and tested this phase; `assemble` (the §7 routing guard) is fixture-tested now with its call site arriving in Phase 6.

**Tech Stack:** Python 3.14, pytest, PyYAML (in the checker layer; `penny_meta` stays dependency-free). Claude-Code-native commands (`.claude/commands/*.md`) and sub-agents (`.claude/agents/*.md`).

## Global Constraints

- Python 3.14; run tests from repo root with `python3 -m pytest -q`.
- Scripts that import sibling modules use `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` then `from scripts.X import ...` (existing pattern).
- Deterministic-gate failures exit non-zero via `sys.exit(f"<tool>: <named predicate>")` — never a bare exception. `preflight.py` uses the prefix `preflight:`.
- `fairplay_check.py` reports failures as `BLOCKING:` lines in its result dict (the verdict convention in `scripts/penny_verdict.py`); `preflight.py` treats any blocking line as a lock failure.
- Existence/schema checks are **presence-only at lock time, never semantics** (no judging plausibility, fit, or prose).
- **No runtime cross-model code ships** — the live Codex final-read is a documented manual step; only its deterministic *guard* and fixtures ship.
- Surgical commits: never stage `.gitignore` or `HANDOFF.md`. Stage only the files each step names.
- End every commit message with:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Spec: `docs/superpowers/specs/2026-06-20-penny-phase3-mystery-crossmodel-design.md`.

---

### Task 1: Promote character-id existence-resolution in `fairplay_check.py` to BLOCKING

Today `fairplay_check.check_fairplay` resolves only the culprit id and only as an evidence note (`scripts/fairplay_check.py:117-121`). Promote it to a BLOCKING gate covering `culprit`, `victim`, and every `alibi_grid[].suspect`, resolving **static-or-continuity**, with an injectable `repo_root` so tests use fixture character corpora.

**Files:**
- Modify: `scripts/fairplay_check.py` (add `_resolves` helper; add `repo_root` param to `check_fairplay`; replace lines 117-121)
- Create: `tests/fixtures/whodunit-repo/series/continuity/characters/margaret.md`
- Create: `tests/fixtures/whodunit-repo/series/characters/thomas.static.md`
- Create: `tests/fixtures/whodunit-repo/series/continuity/characters/edwin-tilley.md`
- Modify/Test: `tests/test_fairplay_check.py`

**Interfaces:**
- Produces: `check_fairplay(ledger_path, *, culprit_by_fraction: float, repo_root: Path | str | None = None) -> dict` — `repo_root` defaults to the real repo root (`Path(__file__).resolve().parents[1]`); existence failures append `BLOCKING:` strings to `result["blocking"]`.
- Produces: `_resolves(entity_id: str, repo_root: Path) -> bool`.

- [ ] **Step 1: Create the fixture character corpus**

`tests/fixtures/whodunit-repo/series/continuity/characters/margaret.md`:
```markdown
---
id: margaret
type: character
links: []
---
Fixture entity (continuity). Existence-resolution corpus only.
```

`tests/fixtures/whodunit-repo/series/characters/thomas.static.md`:
```markdown
---
id: thomas
type: character
---
Fixture entity (static). Existence-resolution corpus only.
```

`tests/fixtures/whodunit-repo/series/continuity/characters/edwin-tilley.md`:
```markdown
---
id: edwin-tilley
type: character
links: []
---
Fixture entity (continuity). Existence-resolution corpus only.
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_fairplay_check.py` (top, after the existing imports/constants):
```python
FIXTURE_REPO = REPO / "tests/fixtures/whodunit-repo"


def _write_chars(root, *, static=(), continuity=()):
    for cid in static:
        d = root / "series/characters"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{cid}.static.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    for cid in continuity:
        d = root / "series/continuity/characters"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{cid}.md").write_text("---\nid: x\n---\n", encoding="utf-8")


def test_all_ids_resolve_no_existence_block():
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert r["blocking"] == []


def test_culprit_resolves_via_static(tmp_path):
    _write_chars(tmp_path, static=("margaret", "thomas", "edwin-tilley"))
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert r["blocking"] == []


def test_culprit_resolves_via_continuity(tmp_path):
    _write_chars(tmp_path, continuity=("margaret", "thomas", "edwin-tilley"))
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert r["blocking"] == []


def test_unresolvable_culprit_blocks(tmp_path):
    _write_chars(tmp_path, continuity=("thomas", "edwin-tilley"))  # margaret missing
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert any("culprit id 'margaret'" in b for b in r["blocking"])


def test_unresolvable_suspect_blocks(tmp_path):
    _write_chars(tmp_path, continuity=("margaret", "edwin-tilley"))  # thomas missing
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert any("suspect id 'thomas'" in b for b in r["blocking"])


def test_existence_is_presence_only_not_semantic(tmp_path):
    # A resolvable culprit produces NO existence block regardless of plausibility —
    # the resolver checks the id has a home, never reads what is in it.
    _write_chars(tmp_path, static=("margaret", "thomas", "edwin-tilley"))
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert not any("id '" in b for b in r["blocking"])
```

Then update **every existing** `check_fairplay(...)` call in this file to pass `repo_root=FIXTURE_REPO` (the fairness fixtures reference `margaret`/`thomas`/`edwin-tilley`, which now resolve only via the corpus). The calls to update are in: `test_fair_ledger_has_no_blocking`, `test_necessary_clue_after_reveal_blocks`, `test_culprit_at_reveal_blocks_floor_only_once`, `test_culprit_past_fraction_blocks_seed`, `test_malformed_ledger_blocks_and_stops`, `test_culprit_alibi_always_holds_blocks`, `test_mention_before_appearance_is_evidence_not_blocking`. Example:
```python
def test_fair_ledger_has_no_blocking():
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert _blocking(r) == []
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `python3 -m pytest tests/test_fairplay_check.py -q`
Expected: FAIL — `check_fairplay()` got an unexpected keyword argument `repo_root`.

- [ ] **Step 4: Implement the resolver and the BLOCKING promotion**

In `scripts/fairplay_check.py`, add the helper after `_is_int_in_range` (around line 53):
```python
def _resolves(entity_id: str, repo_root: Path) -> bool:
    """True iff the id has a home as a static identity OR a continuity entry.
    Presence only — never reads the file's contents."""
    static = Path(repo_root) / "series/characters" / f"{entity_id}.static.md"
    cont = Path(repo_root) / "series/continuity/characters" / f"{entity_id}.md"
    return static.is_file() or cont.is_file()
```

Change the signature (line 56) to:
```python
def check_fairplay(ledger_path, *, culprit_by_fraction: float, repo_root=None) -> dict:
    repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    led = _load_ledger(ledger_path)
```

Replace the evidence-only block (current lines 117-121, the `# culprit-id resolution: evidence-only in 2a ...` through the `notes.append(...)` inside the `chars` guard) with a BLOCKING resolver placed just before the `metrics = {...}` line:
```python
    # Existence resolution (BLOCKING in Phase 3): culprit, victim, and every
    # alibi-grid suspect must have a home in series/characters/<id>.static.md or
    # series/continuity/characters/<id>.md. Presence only — never identity fit.
    to_resolve: list[tuple[str, str]] = [("culprit", culprit)]
    victim = led.get("victim")
    if isinstance(victim, str):
        to_resolve.append(("victim", victim))
    for a in led.get("alibi_grid", []):
        s = a.get("suspect")
        if isinstance(s, str):
            to_resolve.append(("suspect", s))
    seen: set[str] = set()
    for role, eid in to_resolve:
        if eid in seen:
            continue
        seen.add(eid)
        if not _resolves(eid, repo_root):
            blocking.append(
                f"{role} id '{eid}' has no character entity in "
                f"series/characters/ or series/continuity/characters/")
```

- [ ] **Step 5: Run the full fairplay test file**

Run: `python3 -m pytest tests/test_fairplay_check.py -q`
Expected: PASS (all old + new tests).

- [ ] **Step 6: Run the whole suite to confirm no regressions**

Run: `python3 -m pytest -q`
Expected: PASS (114 prior + the new fairplay tests).

- [ ] **Step 7: Commit**

```bash
git add scripts/fairplay_check.py tests/test_fairplay_check.py tests/fixtures/whodunit-repo
git commit -m "feat(fairplay): promote culprit/victim/suspect existence to BLOCKING (static-or-continuity)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `preflight.py` skeleton + `draft` subcommand (light gate)

Create the tool with shared helpers and the cheap draft-time gate: lock present + ledger populated, pure file check.

**Files:**
- Create: `scripts/preflight.py`
- Create: `tests/test_preflight.py`

**Interfaces:**
- Produces: `ledger_path(book: str, repo_root) -> Path` → `<repo>/series/whodunit/book-<book>.yaml`.
- Produces: `lock_path(book: str, repo_root) -> Path` → `<repo>/.penny/locks/book-<book>.mystery.lock`.
- Produces: `cmd_draft(book: str, chapter: str, *, repo_root=REPO) -> int` (raises `SystemExit` via `_fail` on any gate miss; returns `0` when green).
- Produces: `REPO`, `_fail(predicate: str)` (calls `sys.exit(f"preflight: {predicate}")`).

- [ ] **Step 1: Write the failing tests**

`tests/test_preflight.py`:
```python
import pytest

from scripts import preflight


def _make_book(root, book="01", *, populated=True, locked=True):
    wd = root / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    led = wd / f"book-{book}.yaml"
    led.write_text("book: '01'\nculprit: margaret\n" if populated else "", encoding="utf-8")
    if locked:
        ld = root / ".penny/locks"
        ld.mkdir(parents=True, exist_ok=True)
        (ld / f"book-{book}.mystery.lock").write_text("ok\n", encoding="utf-8")
    return led


def test_draft_passes_when_populated_and_locked(tmp_path):
    _make_book(tmp_path, populated=True, locked=True)
    assert preflight.cmd_draft("01", "01", repo_root=tmp_path) == 0


def test_draft_fails_without_lock(tmp_path):
    _make_book(tmp_path, populated=True, locked=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no lock" in str(e.value)


def test_draft_fails_without_ledger(tmp_path):
    (tmp_path / "series/whodunit").mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no ledger" in str(e.value)


def test_draft_fails_when_ledger_unpopulated(tmp_path):
    _make_book(tmp_path, populated=False, locked=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "unpopulated" in str(e.value)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.preflight'`.

- [ ] **Step 3: Implement the skeleton + `draft`**

`scripts/preflight.py`:
```python
"""Deterministic pre-flight gates (Tier-3, structural). One tool, three subcommands:

    lock-mystery N   heavy: fairplay + lexicon --validate; sole writer of the lock.
    draft N CH       light: lock present + ledger populated; pure file check.
    assemble N       routing: final_read_model != drafting_model + set membership.

Gates never make an LLM judgment, so they survive Option-A's soft-gate weakness.
Every miss exits non-zero via `preflight: <named predicate>`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

REPO = Path(__file__).resolve().parents[1]


def _fail(predicate: str):
    sys.exit(f"preflight: {predicate}")


def ledger_path(book: str, repo_root) -> Path:
    return Path(repo_root) / "series/whodunit" / f"book-{book}.yaml"


def lock_path(book: str, repo_root) -> Path:
    return Path(repo_root) / ".penny/locks" / f"book-{book}.mystery.lock"


def cmd_draft(book: str, chapter: str, *, repo_root=REPO) -> int:
    led = ledger_path(book, repo_root)
    if not led.is_file():
        _fail(f"no ledger for book {book} ({led}) — run /plan-mystery {book}")
    data = yaml.safe_load(led.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        _fail(f"ledger unpopulated for book {book} ({led})")
    if not lock_path(book, repo_root).is_file():
        _fail(f"no lock for book {book} — run /plan-mystery {book} to validate and lock")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny deterministic pre-flight gates.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_draft = sub.add_parser("draft", help="draft-time gate")
    p_draft.add_argument("book")
    p_draft.add_argument("chapter")
    args = ap.parse_args(argv)
    if args.cmd == "draft":
        return cmd_draft(args.book, args.chapter)
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(preflight): scripts/preflight.py skeleton + draft-time light gate

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `assemble` subcommand — the §7 cross-model routing guard

Add the routing guard: config-invariant (`final_read_model != drafting_model`) then reality-check (the configured final reader, and the actual final-read artifact's `read_by`, must not appear among chapter `drafted_by` stamps). Fixture-tested now; call site arrives in Phase 6.

**Files:**
- Modify: `scripts/preflight.py` (add helpers + `cmd_assemble` + dispatch case)
- Modify: `tests/test_preflight.py`

**Interfaces:**
- Consumes: `parse_frontmatter`, `parse_yaml_blocks`, `load` from `scripts.penny_meta`.
- Produces: `cmd_assemble(book: str, *, repo_root=REPO, run_config=None) -> int`.
- Produces: `_drafted_by_set(book, repo_root) -> set[str]`, `_final_read_path(book, repo_root) -> Path` (`<repo>/output/book-<book>/book-<book>.final-read.md`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_preflight.py`:
```python
def _make_run_config(root, *, drafting, final_read):
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "run-config.md").write_text(
        "# fixture run-config\n\n```yaml\n"
        f"drafting_model:   {drafting}\n"
        f"final_read_model: {final_read}\n"
        "```\n",
        encoding="utf-8",
    )


def _make_chapter(root, book, ch, drafted_by):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.draft.md").write_text(
        f"---\ndrafted_by: {drafted_by}\n---\nprose\n", encoding="utf-8")


def _make_final_read(root, book, read_by):
    d = root / "output" / f"book-{book}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"book-{book}.final-read.md").write_text(
        f"---\nread_by: {read_by}\n---\nholistic read\n", encoding="utf-8")


def test_assemble_green(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "codex")
    assert preflight.cmd_assemble("01", repo_root=tmp_path) == 0


def test_assemble_config_invariant_fails_before_stamps(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="claude-opus")
    # no chapters at all — must still fail on the config compare
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "equals drafting_model" in str(e.value)


def test_assemble_drift_configured_final_reader_drafted(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_chapter(tmp_path, "01", "02", "codex")  # codex drafted ch-02 — config lies
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "configured final_read_model 'codex'" in str(e.value)


def test_assemble_read_by_collides_with_drafter(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "claude-opus")  # final read done by a drafter
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "final-read model 'claude-opus'" in str(e.value)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: FAIL — `AttributeError: module 'scripts.preflight' has no attribute 'cmd_assemble'`.

- [ ] **Step 3: Implement `cmd_assemble`**

In `scripts/preflight.py`, extend the imports:
```python
from scripts.penny_meta import load, parse_frontmatter, parse_yaml_blocks
```
Add the helpers and command (before `main`):
```python
def _drafted_by_set(book: str, repo_root) -> set[str]:
    chapters = Path(repo_root) / "output" / f"book-{book}" / "chapters"
    stamps: set[str] = set()
    for ch in sorted(chapters.glob("ch-*.draft.md")):
        m = parse_frontmatter(ch.read_text(encoding="utf-8")).get("drafted_by")
        if isinstance(m, str) and m:
            stamps.add(m)
    return stamps


def _final_read_path(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}" / f"book-{book}.final-read.md"


def cmd_assemble(book: str, *, repo_root=REPO, run_config=None) -> int:
    run_config = run_config or (Path(repo_root) / "config/run-config.md")
    cfg = parse_yaml_blocks(load(run_config))
    drafting = cfg.get("drafting_model")
    final_read = cfg.get("final_read_model")
    if not drafting or not final_read:
        _fail("run-config missing drafting_model or final_read_model")
    # 1. config-invariant — fails before stamps matter.
    if final_read == drafting:
        _fail(f"final_read_model equals drafting_model ({final_read})")
    # 2. reality-check: the configured final reader must not be among drafters.
    drafted = _drafted_by_set(book, repo_root)
    if final_read in drafted:
        _fail(f"configured final_read_model '{final_read}' appears in "
              f"drafted_by set {sorted(drafted)}")
    # 3. the actual final-read artifact (if present): read_by must not be a drafter.
    fr = _final_read_path(book, repo_root)
    if fr.is_file():
        read_by = parse_frontmatter(fr.read_text(encoding="utf-8")).get("read_by")
        if not read_by:
            _fail(f"final-read artifact has no read_by stamp ({fr})")
        if read_by in drafted:
            _fail(f"final-read model '{read_by}' appears in "
                  f"drafted_by set {sorted(drafted)}")
    return 0
```
Add the dispatch case in `main` (after the `draft` parser, before `args = ...`):
```python
    p_asm = sub.add_parser("assemble", help="cross-model routing guard")
    p_asm.add_argument("book")
```
and in the dispatch body (after the `draft` branch):
```python
    if args.cmd == "assemble":
        return cmd_assemble(args.book)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: PASS (draft + assemble tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(preflight): assemble subcommand — §7 cross-model routing guard (fixture-tested)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `lock-mystery` subcommand — the certificate writer

The heavy lock-time gate: validate the on-disk ledger with `fairplay_check` (numeric + existence) and `lexicon_check --validate` (schema). Only if both pass, write the lock file **last**. A failure leaves no lock.

**Files:**
- Modify: `scripts/preflight.py` (add `cmd_lock_mystery` + dispatch case)
- Modify: `tests/test_preflight.py`

**Interfaces:**
- Consumes: `check_fairplay`, `load_fraction` from `scripts.fairplay_check`; `validate_lexicon`, `load_lexicon`, `stage_drift` from `scripts.lexicon_check`.
- Produces: `cmd_lock_mystery(book: str, *, repo_root=REPO, run_config=None) -> int` — sole writer of `lock_path(book, repo_root)`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_preflight.py` (top, add `import shutil` and a repo-scaffold helper):
```python
import shutil

SRC = preflight.REPO


def _scaffold_lockable(tmp_path, *, ledger_fixture, valid_lexicon=True):
    """Build a tmp repo able to run lock-mystery: real run-config, real canon-core,
    a (valid or malformed) lexicon, a resolvable character corpus, and a ledger."""
    # run-config + canon-core copied from the real repo (both valid).
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "config/run-config.md", tmp_path / "config/run-config.md")
    (tmp_path / "series/continuity").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "series/continuity/canon-core.md",
                tmp_path / "series/continuity/canon-core.md")
    # lexicon: real (valid) or a malformed stub.
    (tmp_path / "config/setting-pack").mkdir(parents=True, exist_ok=True)
    if valid_lexicon:
        shutil.copy(SRC / "config/setting-pack/lexicon.yaml",
                    tmp_path / "config/setting-pack/lexicon.yaml")
    else:
        (tmp_path / "config/setting-pack/lexicon.yaml").write_text(
            "terms:\n  - {term: jumper}\n", encoding="utf-8")  # missing required fields
    # resolvable character corpus.
    cc = tmp_path / "series/continuity/characters"
    cc.mkdir(parents=True, exist_ok=True)
    for cid in ("margaret", "thomas", "edwin-tilley"):
        (cc / f"{cid}.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    # the proposed (unlocked) ledger.
    wd = tmp_path / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    shutil.copy(ledger_fixture, wd / "book-01.yaml")
    return wd / "book-01.yaml"


FAIR = SRC / "tests/fixtures/ledgers/fair.yaml"
UNFAIR = SRC / "tests/fixtures/ledgers/unfair_clue_after_reveal.yaml"


def test_lock_mystery_writes_lock_when_valid(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    assert preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_fairplay_fails(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=UNFAIR, valid_lexicon=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "fairplay failed" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_lexicon_invalid(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "lexicon" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_culprit_unresolvable(tmp_path):
    led = _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    # remove margaret's entity so existence resolution blocks.
    (tmp_path / "series/continuity/characters/margaret.md").unlink()
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "culprit id 'margaret'" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: FAIL — `AttributeError: module 'scripts.preflight' has no attribute 'cmd_lock_mystery'`.

- [ ] **Step 3: Implement `cmd_lock_mystery`**

In `scripts/preflight.py`, extend imports:
```python
from datetime import datetime, timezone

from scripts.fairplay_check import check_fairplay, load_fraction
from scripts.lexicon_check import load_lexicon, stage_drift, validate_lexicon
```
Add the command (before `main`):
```python
def cmd_lock_mystery(book: str, *, repo_root=REPO, run_config=None) -> int:
    repo_root = Path(repo_root)
    run_config = run_config or (repo_root / "config/run-config.md")
    led = ledger_path(book, repo_root)
    if not led.is_file():
        _fail(f"no ledger to lock for book {book} ({led})")
    # 1. fairplay: numeric fairness + character-id existence (BLOCKING gate).
    fraction = load_fraction(run_config)
    fp = check_fairplay(led, culprit_by_fraction=fraction, repo_root=repo_root)
    if fp["blocking"]:
        _fail("fairplay failed; lock NOT written:\n  - " + "\n  - ".join(fp["blocking"]))
    # 2. lexicon schema validation (+ stage drift).
    errors = validate_lexicon(load_lexicon(repo_root / "config/setting-pack/lexicon.yaml"))
    drift = stage_drift((repo_root / "series/continuity/canon-core.md")
                        .read_text(encoding="utf-8"))
    if drift:
        errors.append(drift)
    if errors:
        _fail("lexicon --validate failed; lock NOT written:\n  - " + "\n  - ".join(errors))
    # 3. both passed — mint the certificate (the LAST write).
    lp = lock_path(book, repo_root)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_text(
        f"book: {book}\nvalidated: fairplay+lexicon\n"
        f"locked_at: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    return 0
```
Add dispatch in `main` (parser + branch):
```python
    p_lock = sub.add_parser("lock-mystery", help="validate + write the lock (last)")
    p_lock.add_argument("book")
```
```python
    if args.cmd == "lock-mystery":
        return cmd_lock_mystery(args.book)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_preflight.py -q`
Expected: PASS (draft + assemble + lock-mystery).

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(preflight): lock-mystery — validate (fairplay+lexicon) then write lock last

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `/plan-mystery` command + `mystery-planner` agent + scaffold tests

Author the §5a authorship flow (command) and the proposer sub-agent (agent), with scaffold tests mirroring `tests/test_inspector_scaffold.py`.

**Files:**
- Create: `.claude/commands/plan-mystery.md`
- Create: `.claude/agents/mystery-planner.md`
- Create: `tests/test_mystery_scaffold.py`

**Interfaces:**
- Produces: a command file that invokes `scripts/preflight.py lock-mystery $book` as its final step and writes (in order) the unlocked yaml, the sealed solution, then defers the lock to preflight.
- Produces: an agent file with `name: mystery-planner` frontmatter.

- [ ] **Step 1: Write the failing tests**

`tests/test_mystery_scaffold.py`:
```python
from pathlib import Path

from scripts.penny_meta import parse_frontmatter

CMD = Path(".claude/commands/plan-mystery.md")
AGENT = Path(".claude/agents/mystery-planner.md")


def test_plan_mystery_command_exists():
    assert CMD.is_file()


def test_plan_mystery_invokes_lock_preflight_and_seals_solution():
    text = CMD.read_text(encoding="utf-8")
    assert "preflight.py lock-mystery" in text, "command must defer the lock to preflight"
    assert "mystery-solution.md" in text, "command must write the sealed solution"
    assert "mystery-planner" in text, "command must dispatch the planner agent"


def test_mystery_planner_agent_has_valid_frontmatter():
    assert AGENT.is_file()
    meta = parse_frontmatter(AGENT.read_text(encoding="utf-8"))
    assert meta.get("name") == "mystery-planner"
    assert meta.get("description")


def test_mystery_planner_never_receives_solution_seat():
    # The planner proposes; it must not be handed the sealed answer key.
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "sealed" in text or "never" in text, "agent must state the sealing discipline"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_mystery_scaffold.py -q`
Expected: FAIL — files missing.

- [ ] **Step 3: Create the agent file**

`.claude/agents/mystery-planner.md`:
```markdown
---
name: mystery-planner
description: Proposes a per-book whodunit construction (clue schedule, red herrings, alibi grid) from the showrunner's irreducible core. Never writes from a drafter's seat.
---
# Mystery Planner

**Role posture:** proposer (design §5a). Given the showrunner's irreducible core
(who did it, why, the central deception, series-arc constraints), do the heavy
combinatorial craft: the clue schedule, the red herrings (mislead-but-don't-cheat),
and the alibi grid — structured per chapter so each chapter's planting obligations
can be handed out without revealing the answer.

**Independence:** the sealed `mystery-solution.md` is authored by the `/plan-mystery`
command, never handed to a drafter. The planner proposes the construction; it does
not draft prose and never sees a chapter's drafting history.

**Inputs:** the irreducible core (interactive from the showrunner) + the series
bible / arc-ledger for continuity.

**Output:** a proposed `series/whodunit/book-NN.yaml` body — `book`,
`total_chapters`, `reveal_chapter`, `culprit`, `victim`,
`culprit_first_appearance_chapter`, `clue_schedule[]`, `red_herrings[]`,
`alibi_grid[]` — for the showrunner to review, edit, and lock.

**Discipline:** propose only; the showrunner approves and the command validates +
locks. `culprit`, `victim`, and every `alibi_grid` suspect must be ids that resolve
to existing character entities (the lock-time existence gate will block otherwise).
```

- [ ] **Step 4: Create the command file**

`.claude/commands/plan-mystery.md`:
```markdown
---
description: Per-book mystery design + lock (design §5a). Validate-once-then-freeze.
argument-hint: <book-number>
---
# /plan-mystery

Run once per book, before any `/draft-chapter`. Separates three roles: showrunner
sets the core, `mystery-planner` proposes the construction, showrunner approves and
locks. The lock file is a **certificate** — it exists only if fairplay + lexicon
validation passed (the only writer is `preflight.py lock-mystery`).

## Steps

1. **Parse args:** `book=$1` (e.g. `01`).

2. **Showrunner sets the irreducible core** (interactive): who did it, why, the
   central deception, and any series-arc constraints. This is the irreducibly human
   taste-and-strategy layer.

3. **Dispatch the `mystery-planner` sub-agent** with the core + series bible. It
   proposes the clue schedule, red herrings, and alibi grid.

4. **Write the proposed (unlocked) ledger** to `series/whodunit/book-$book.yaml`.
   Do NOT add a `locked:` field — the lock is an out-of-band file, never a field
   inside the data it gates (a field would be a forgeable certificate).

5. **Showrunner reviews and approves** (taste): edit the proposed yaml until right.

6. **Write the sealed solution** to `output/book-$book/mystery-solution.md` — the
   full answer key, sealed from the drafter, beta, and final readers.

7. **Validate and lock (LAST):**

   ```bash
   python3 scripts/preflight.py lock-mystery $book
   ```

   This runs `fairplay_check.py` (numeric fairness + culprit/victim/suspect
   existence) and `lexicon_check.py --validate` (lexicon schema). Only if both pass
   does it write `.penny/locks/book-$book.mystery.lock`. If either fails it exits
   non-zero and writes no lock — leaving an unlocked-but-present yaml that
   `/draft-chapter` correctly rejects. Fix the reported issues and re-run.

   **Re-planning:** delete the lock, edit the yaml, re-run this step — the clean
   re-lock story (§5a).
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/test_mystery_scaffold.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .claude/commands/plan-mystery.md .claude/agents/mystery-planner.md tests/test_mystery_scaffold.py
git commit -m "feat(mystery): /plan-mystery command + mystery-planner agent (§5a certificate flow)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Wire `/draft-chapter` step 0 + drop `locked:` from `book-01.yaml`

Make `/draft-chapter` run the draft-time gate before any work, and remove the now-forgeable `locked:` field from the example ledger.

**Files:**
- Modify: `.claude/commands/draft-chapter.md` (insert step 0)
- Modify: `series/whodunit/book-01.yaml` (remove `locked: true`)
- Create: `tests/test_draft_preflight_wiring.py`

**Interfaces:**
- Consumes: `scripts/preflight.py draft` (Task 2).

- [ ] **Step 1: Write the failing tests**

`tests/test_draft_preflight_wiring.py`:
```python
from pathlib import Path

import yaml

DRAFT_CMD = Path(".claude/commands/draft-chapter.md")
BOOK01 = Path("series/whodunit/book-01.yaml")


def test_draft_chapter_runs_preflight_gate():
    text = DRAFT_CMD.read_text(encoding="utf-8")
    assert "preflight.py draft" in text, "draft-chapter must gate on the draft pre-flight"


def test_book01_has_no_locked_field():
    data = yaml.safe_load(BOOK01.read_text(encoding="utf-8"))
    assert "locked" not in data, "the lock is an out-of-band file, not a yaml field"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_draft_preflight_wiring.py -q`
Expected: FAIL (no `preflight.py draft` reference; `locked` present).

- [ ] **Step 3: Remove `locked: true` from `series/whodunit/book-01.yaml`**

Delete the line `locked: true` (line 2). The file now begins:
```yaml
book: 01
total_chapters: 24
```

- [ ] **Step 4: Insert step 0 into `.claude/commands/draft-chapter.md`**

After the `## Steps` heading and before the current step `1. **Parse args:** ...`, insert:
```markdown
0. **Pre-flight gate (Phase 3):** the mystery must be validated and locked before
   any chapter is drafted. Hard-fail aborts before context assembly:

   ```bash
   python3 scripts/preflight.py draft $1 $2
   ```

   A non-zero exit means the book's mystery is absent, unpopulated, or unlocked —
   run `/plan-mystery $1` first. Do not proceed on failure.
```
(`$1`/`$2` are book/chapter, parsed in step 1 as `book`/`chapter`.)

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/test_draft_preflight_wiring.py -q`
Expected: PASS.

- [ ] **Step 6: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .claude/commands/draft-chapter.md series/whodunit/book-01.yaml tests/test_draft_preflight_wiring.py
git commit -m "feat(draft): gate /draft-chapter on preflight draft; drop forgeable locked: field

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Record Codex-via-plugin in the master design doc

Append a dated Phase 3 implementation note to `penny-design-v3.md` superseding the `/scripts` cross-model adapter wording (§7, §13.3): the alternate is **Codex via the official Codex plugin**; Hermes/OpenClaw drop out; no runtime cross-model code ships in Phase 3.

**Files:**
- Modify: `penny-design-v3.md` (append a note at the end, before/after the change log)
- Create: `tests/test_phase3_doc_note.py`

- [ ] **Step 1: Write the failing test**

`tests/test_phase3_doc_note.py`:
```python
from pathlib import Path

DESIGN = Path("penny-design-v3.md")


def test_codex_plugin_recorded():
    text = DESIGN.read_text(encoding="utf-8")
    assert "Codex plugin" in text, "master doc must record the Codex-via-plugin decision"
    assert "supersedes" in text.lower(), "the note must mark it as superseding the adapter wording"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_phase3_doc_note.py -q`
Expected: FAIL.

- [ ] **Step 3: Append the note to `penny-design-v3.md`**

Add at the end of the file:
```markdown
---

## Phase 3 implementation note (2026-06-20) — cross-model = Codex via plugin

This note **supersedes** the "`/scripts` adapter" cross-model wording in §7 and the
"`/scripts` adapters" item in §13.3 build order. The cross-model alternate is
**Codex via the official Codex plugin for Claude Code** (`openai/codex-plugin-cc`),
invoked from command instructions (plugin/CLI), not a hand-rolled API adapter.
**Hermes/OpenClaw drop out.** `run-config.md` keeps `final_read_model: codex`; only
the *mechanism* changes. The `[ENGINEERING]` cross-model open item shrinks to
"install plugin + Codex credential + Codex CLI present" — self-serve.

No runtime cross-model code ships in Phase 3: the live final-read is a documented
manual step whose only engine obligation is writing `read_by: codex` provenance;
its call site is the Phase 6 `assemble-book` command. The deterministic guard that
consumes that provenance (`preflight.py assemble`) is built and fixture-tested in
Phase 3. See `docs/superpowers/specs/2026-06-20-penny-phase3-mystery-crossmodel-design.md` §7.
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest tests/test_phase3_doc_note.py -q`
Expected: PASS.

- [ ] **Step 5: Final full-suite run**

Run: `python3 -m pytest -q`
Expected: PASS (all Phase 3 tests + the prior suite).

- [ ] **Step 6: Commit**

```bash
git add penny-design-v3.md tests/test_phase3_doc_note.py
git commit -m "docs(phase3): record Codex-via-plugin, superseding /scripts adapter wording

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- §2 `/plan-mystery` + `mystery-planner` → Task 5. ✓
- §2/§4.1 `preflight.py` three subcommands → Tasks 2 (draft), 3 (assemble), 4 (lock-mystery). ✓
- §4.2 fairplay existence-resolution BLOCKING, static-or-continuity, presence-only → Task 1. ✓
- §4.3 `lexicon_check --validate` schema-only at lock → invoked in Task 4. ✓
- §4.6 `/draft-chapter` step 0 → Task 6. ✓
- §3 drop `locked:` field → Task 6. ✓
- §5 certificate write-order, lock written last, failure leaves no lock → Task 4 (impl + tests). ✓
- §7 Codex-via-plugin recorded; routing guard built + fixture-tested incl. **drift fixture** → Task 3 (`test_assemble_drift_configured_final_reader_drafted`) + Task 7. ✓
- §9 test corpus (lock-mystery pass/fairplay-fail/lexicon-fail/existence-fail; draft 4 cases; assemble 4 cases incl. drift; fairplay existence cases; scaffold tests; book-01 reframed as fixture) → Tasks 1-7. ✓
- §6 solution isolation (command/agent discipline) → Task 5 (command writes sealed solution; agent states sealing). ✓
- §11 out-of-scope carry-forwards → not built (correct). ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every test shows assertions; commands give exact paths and expected output. ✓

**Type consistency:** `check_fairplay(..., repo_root=...)` defined in Task 1, consumed in Task 4. `cmd_draft`/`cmd_assemble`/`cmd_lock_mystery`/`ledger_path`/`lock_path`/`_fail`/`REPO` defined in Tasks 2-4 and consumed by tests with consistent signatures. `_drafted_by_set`/`_final_read_path` defined and used in Task 3. ✓
