# Engine-Plugin + Series-Folders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one Penny engine (shipped as a Claude Code plugin) drive many series, where each series is an ordinary folder you `cd` into — the active series being the working directory, resolved by a `.penny` marker.

**Architecture:** Introduce a single resolver module (`scripts/penny_paths.py`) that knows two roots — the *plugin root* (engine code + config defaults, anchored at the engine repo) and the *series root* (the nearest ancestor of the cwd containing `.penny/`, holding that series' data). Every path-hardcoding script routes through it: **data paths** (`series/`, `input/`, `output/`, `.penny/`) resolve against the series root; **config paths** resolve via a two-tier overlay (series override, else plugin default). Pipeline logic is unchanged — only pathing.

**Tech Stack:** Python 3 stdlib only (no new deps — PyYAML stays confined to its current callers), pytest, bash (status line), a Claude Code plugin manifest.

## Global Constraints

- **No new runtime dependencies.** `penny_paths.py` is pure stdlib (`pathlib`, `os`, `sys`). Do not import PyYAML into it (dependency-split rule).
- **Two roots, never confused:**
  - *plugin root* = `Path(__file__).resolve().parents[1]` from `scripts/penny_paths.py` (the engine repo).
  - *series root* = nearest ancestor of the start dir (default `Path.cwd()`) that contains a `.penny/` directory; hard error if none.
- **Data vs config rule (apply in every consumer):**
  - `series/…`, `input/…`, `output/…`, `.penny/…` → `penny_paths.series_path/input_path/output_path/penny_path(rel, root=repo_root)`.
  - `config/…` → `penny_paths.config_path(rel, root=repo_root)` (overlay: series override else plugin default).
- **Preserve `repo_root` threading.** Consumers keep their `repo_root` parameter; it is passed to `penny_paths` helpers as `root=`. Only the *default* changes: `repo_root=REPO` (a module constant) becomes `repo_root=None`, resolved lazily to `penny_paths.series_root()` inside the function. This keeps every existing test that passes `repo_root=tmp_path` working.
- **Do not touch** `scripts/penny_meta.py`, `scripts/penny_verdict.py`, `scripts/penny_text.py` (already path-agnostic).
- **Do not touch** the `sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` lines — they anchor *module imports* to the plugin and remain correct.
- **Keep the full suite green** (`python3 -m pytest`, ~273 tests) after every task. Commit after every task.
- **Australian nothing here** — this is engine code, not prose.

## File Structure

- `scripts/penny_paths.py` — **new.** The only module that knows the layout. ~70 lines.
- `tests/test_penny_paths.py` — **new.** Resolver unit + parallel-safety tests.
- `scripts/preflight.py`, `lexicon_check.py`, `readiness_check.py`, `fairplay_check.py`, `outline_check.py`, `review_gate.py`, `revision_priority.py`, `assemble_book.py`, `voice_drift.py`, `canon_core_review.py`, `ledger_markers.py`, `reset_reviews.py` — **modify.** Route path building through `penny_paths`.
- `scripts/penny-statusline.sh` — **modify.** Read the series root's `.penny/current-stage`; show the series name.
- `.claude-plugin/plugin.json` (or the doc-confirmed manifest path) — **new.** Registers this repo as the `penny` plugin.
- `.claude/commands/new-series.md` — **new.** Scaffolds a series folder.
- `tests/fixtures/series-fixture/` — **new.** A minimal `.penny/ + config/ + series/ + input/ + output/` tree for resolver/gate tests.

---

### Task 1: The resolver — `scripts/penny_paths.py`

**Files:**
- Create: `scripts/penny_paths.py`
- Test: `tests/test_penny_paths.py`

**Interfaces:**
- Produces:
  - `plugin_root() -> Path`
  - `series_root(start: Path | None = None) -> Path` (walk-up to `.penny`; raises `SystemExit` with `penny-paths: no series root` if none)
  - `config_path(rel: str, root: Path | None = None) -> Path` (overlay)
  - `series_path(rel, root=None) -> Path`, `input_path(rel, root=None) -> Path`, `output_path(rel, root=None) -> Path`, `penny_path(rel, root=None) -> Path`
  - `active(root: Path | None = None) -> str` (the series folder name)
  - CLI: `python3 -m scripts.penny_paths resolve config <rel>` / `resolve series <rel>` / `active`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_penny_paths.py
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import penny_paths as pp


def _make_series(tmp_path: Path) -> Path:
    (tmp_path / ".penny").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "series").mkdir()
    return tmp_path


def test_series_root_found_from_root(tmp_path):
    s = _make_series(tmp_path)
    assert pp.series_root(start=s) == s


def test_series_root_found_from_nested_subdir(tmp_path):
    s = _make_series(tmp_path)
    nested = s / "series" / "continuity"
    nested.mkdir()
    assert pp.series_root(start=nested) == s


def test_series_root_missing_marker_fails_loud(tmp_path):
    with pytest.raises(SystemExit) as e:
        pp.series_root(start=tmp_path)
    assert "no series root" in str(e.value)


def test_plugin_root_is_engine_repo(tmp_path):
    # plugin_root is independent of cwd: it is where the engine code lives.
    assert (pp.plugin_root() / "scripts" / "penny_paths.py").is_file()


def test_config_path_uses_series_override_when_present(tmp_path):
    s = _make_series(tmp_path)
    override = s / "config" / "voice-pack"
    override.mkdir(parents=True)
    (override / "voice-pack.md").write_text("series voice")
    assert pp.config_path("voice-pack/voice-pack.md", root=s) == override / "voice-pack.md"


def test_config_path_falls_back_to_plugin_default(tmp_path):
    s = _make_series(tmp_path)  # empty config/, no override
    resolved = pp.config_path("review-rubrics/character-voice.md", root=s)
    assert resolved == pp.plugin_root() / "config" / "review-rubrics/character-voice.md"


def test_data_helpers_anchor_on_series_root(tmp_path):
    s = _make_series(tmp_path)
    assert pp.output_path("book-01/chapters", root=s) == s / "output" / "book-01/chapters"
    assert pp.series_path("whodunit/book-01.yaml", root=s) == s / "series" / "whodunit/book-01.yaml"
    assert pp.input_path("book-01/outline.md", root=s) == s / "input" / "book-01/outline.md"
    assert pp.penny_path("locks/book-01.mystery.lock", root=s) == s / ".penny" / "locks/book-01.mystery.lock"


def test_parallel_safety_two_series_disjoint(tmp_path):
    a = _make_series(tmp_path / "a")
    b = _make_series(tmp_path / "b")
    assert pp.output_path("x", root=a) != pp.output_path("x", root=b)
    assert pp.penny_path("x", root=a).parents[1] == a
    assert pp.penny_path("x", root=b).parents[1] == b


def test_active_is_folder_name(tmp_path):
    s = _make_series(tmp_path / "cozy-pelicans")
    assert pp.active(root=s) == "cozy-pelicans"


def test_cli_resolve_and_active(tmp_path):
    s = _make_series(tmp_path / "cozy-pelicans")
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run(
        [sys.executable, "-m", "scripts.penny_paths", "resolve", "series", "whodunit/x.yaml"],
        cwd=s, capture_output=True, text=True, env=env,
    )
    assert out.returncode == 0
    assert out.stdout.strip() == str(s / "series" / "whodunit/x.yaml")

    out2 = subprocess.run(
        [sys.executable, "-m", "scripts.penny_paths", "active"],
        cwd=s, capture_output=True, text=True, env=env,
    )
    assert out2.stdout.strip() == "cozy-pelicans"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_paths.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_paths'`.

- [ ] **Step 3: Write the implementation**

```python
# scripts/penny_paths.py
"""The one module that knows the layout (design: engine-plugin + series-folders).

Two roots:
  - plugin_root(): the engine repo where this file lives (code + config DEFAULTS).
  - series_root(): the nearest ancestor of the cwd that contains a `.penny/` dir
    (that series' DATA). Hard error if none — never guess which series.

Data paths (series/, input/, output/, .penny/) anchor on the series root.
Config paths overlay: series override if present, else plugin default.
"""
from __future__ import annotations

import sys
from pathlib import Path

_MARKER = ".penny"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def series_root(start: Path | None = None) -> Path:
    cur = Path(start).resolve() if start is not None else Path.cwd().resolve()
    for d in (cur, *cur.parents):
        if (d / _MARKER).is_dir():
            return d
    sys.exit(f"penny-paths: no series root (no '{_MARKER}/' at or above {cur})")


def _root(root: Path | None) -> Path:
    return Path(root).resolve() if root is not None else series_root()


def config_path(rel: str, root: Path | None = None) -> Path:
    override = _root(root) / "config" / rel
    return override if override.exists() else plugin_root() / "config" / rel


def series_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / "series" / rel


def input_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / "input" / rel


def output_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / "output" / rel


def penny_path(rel: str, root: Path | None = None) -> Path:
    return _root(root) / _MARKER / rel


def active(root: Path | None = None) -> str:
    return _root(root).name


def _main(argv: list[str]) -> int:
    if not argv:
        print("usage: penny_paths resolve <config|series|input|output|penny> <rel> | active", file=sys.stderr)
        return 2
    if argv[0] == "active":
        print(active())
        return 0
    if argv[0] == "resolve" and len(argv) == 3:
        kind, rel = argv[1], argv[2]
        fn = {"config": config_path, "series": series_path, "input": input_path,
              "output": output_path, "penny": penny_path}.get(kind)
        if fn is None:
            print(f"penny-paths: unknown kind '{kind}'", file=sys.stderr)
            return 2
        print(fn(rel))
        return 0
    print("usage: penny_paths resolve <kind> <rel> | active", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_paths.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Run the full suite (must still be green — nothing consumes penny_paths yet)**

Run: `python3 -m pytest -q`
Expected: PASS, same count as before + the new tests.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_paths.py tests/test_penny_paths.py
git commit -m "feat(engine): add penny_paths resolver (plugin root + series-root overlay)"
```

---

### Task 2: Repoint `preflight.py`

**Files:**
- Modify: `scripts/preflight.py`
- Test: `tests/test_preflight.py` (existing; must stay green)

**Interfaces:**
- Consumes: `scripts.penny_paths` (`series_path`, `output_path`, `penny_path`, `config_path`, `series_root`).

- [ ] **Step 1: Add the import and drop the REPO constant default**

At the imports near the top add:
```python
from scripts import penny_paths
```
Change the module constant use: keep `REPO = Path(__file__).resolve().parents[1]` **only if** other code references it; otherwise remove it. Replace every function signature `*, repo_root=REPO` with `*, repo_root=None` and, as the first line of each such function body, add:
```python
    repo_root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
```

- [ ] **Step 2: Replace the path builders (data → series/output/penny; config → overlay)**

Apply these exact substitutions:
```python
# whodunit (DATA):
Path(repo_root) / "series/whodunit" / f"book-{book}.yaml"
# ->
penny_paths.series_path(f"whodunit/book-{book}.yaml", root=repo_root)

# locks (DATA under .penny):
Path(repo_root) / ".penny/locks" / f"book-{book}.mystery.lock"
# ->
penny_paths.penny_path(f"locks/book-{book}.mystery.lock", root=repo_root)
# (do the same for the .approved, .ch-{chapter}.dev-clear lock builders)

# chapters (DATA under output):
Path(repo_root) / "output" / f"book-{book}" / "chapters"
# ->
penny_paths.output_path(f"book-{book}/chapters", root=repo_root)

# final-read (DATA under output):
Path(repo_root) / "output" / f"book-{book}" / f"book-{book}.final-read.md"
# ->
penny_paths.output_path(f"book-{book}/book-{book}.final-read.md", root=repo_root)

# run-config (CONFIG → overlay):
Path(repo_root) / "config/run-config.md"        # and  repo_root / "config/run-config.md"
# ->
penny_paths.config_path("run-config.md", root=repo_root)

# lexicon (CONFIG → overlay):
repo_root / "config/setting-pack/lexicon.yaml"
# ->
penny_paths.config_path("setting-pack/lexicon.yaml", root=repo_root)

# canon-core (DATA under series):
repo_root / "series/continuity/canon-core.md"
# ->
penny_paths.series_path("continuity/canon-core.md", root=repo_root)
```

- [ ] **Step 3: Run preflight tests**

Run: `python3 -m pytest tests/test_preflight.py -v`
Expected: PASS. (Existing tests pass `repo_root=tmp_path` with a full fixture tree; `config_path(root=tmp)` finds the fixture's `config/…` when present, else the plugin default — behavior preserved.)

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py
git commit -m "refactor(engine): route preflight paths through penny_paths"
```

---

### Task 3: Repoint `lexicon_check.py`

**Files:**
- Modify: `scripts/lexicon_check.py`
- Test: `tests/test_lexicon_check.py` (existing; must stay green)

- [ ] **Step 1: Add import, repoint the two module defaults**

Add `from scripts import penny_paths`. Replace:
```python
REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = REPO / "config/setting-pack/lexicon.yaml"
DEFAULT_CANON_CORE = REPO / "series/continuity/canon-core.md"
```
with lazy resolvers (module constants must not call `series_root()` at import, since import happens outside a series):
```python
def default_lexicon(repo_root=None):
    return penny_paths.config_path("setting-pack/lexicon.yaml", root=repo_root)

def default_canon_core(repo_root=None):
    return penny_paths.series_path("continuity/canon-core.md", root=repo_root)
```
Update the callers/CLI that referenced `DEFAULT_LEXICON` / `DEFAULT_CANON_CORE` to call these functions (passing `repo_root` where one is in scope, else `None`).

- [ ] **Step 2: Run lexicon tests**

Run: `python3 -m pytest tests/test_lexicon_check.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/lexicon_check.py
git commit -m "refactor(engine): route lexicon_check paths through penny_paths"
```

---

### Task 4: Repoint `readiness_check.py`

**Files:**
- Modify: `scripts/readiness_check.py`
- Test: `tests/test_readiness_check.py` (existing; must stay green)

**Note:** this is the widest hardcoder (24 literals). It builds `Path(repo_root) / rel` for both config-pack files and canon-core. Split by data-vs-config.

- [ ] **Step 1: Add import; classify each `rel` as config vs data**

Add `from scripts import penny_paths`. In `_file_check`/`_dir_check` (which do `Path(repo_root) / rel`), route each check through the correct helper based on its `rel` prefix:
```python
def _resolve(rel: str, repo_root) -> Path:
    if rel.startswith("config/"):
        return penny_paths.config_path(rel[len("config/"):], root=repo_root)
    if rel.startswith("series/"):
        return penny_paths.series_path(rel[len("series/"):], root=repo_root)
    if rel.startswith("input/"):
        return penny_paths.input_path(rel[len("input/"):], root=repo_root)
    if rel.startswith("output/"):
        return penny_paths.output_path(rel[len("output/"):], root=repo_root)
    return Path(repo_root) / rel
```
Then in `_file_check`/`_dir_check`, replace `Path(repo_root) / rel` with `_resolve(rel, repo_root)`. Change the module `REPO` default so `engine_checks(repo_root=None)` resolves `repo_root = repo_root or penny_paths.series_root()` at entry.

- [ ] **Step 2: Run readiness tests**

Run: `python3 -m pytest tests/test_readiness_check.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add scripts/readiness_check.py
git commit -m "refactor(engine): route readiness_check paths through penny_paths"
```

---

### Task 5: Repoint `fairplay_check.py`

**Files:**
- Modify: `scripts/fairplay_check.py`
- Test: `tests/test_fairplay_check.py` (existing; must stay green)

- [ ] **Step 1: Add import; repoint character resolution**

Add `from scripts import penny_paths`. In `_resolves`:
```python
static = Path(repo_root) / "series/characters" / f"{entity_id}.static.md"
cont = Path(repo_root) / "series/continuity/characters" / f"{entity_id}.md"
# ->
static = penny_paths.series_path(f"characters/{entity_id}.static.md", root=repo_root)
cont = penny_paths.series_path(f"continuity/characters/{entity_id}.md", root=repo_root)
```
In `check_fairplay`, keep the existing `repo_root = Path(repo_root) if repo_root is not None else ...` line but change the fallback from `Path(__file__).resolve().parents[1]` to `penny_paths.series_root()`. Any `run-config` read here becomes `penny_paths.config_path("run-config.md", root=repo_root)`.

- [ ] **Step 2: Run fairplay tests**

Run: `python3 -m pytest tests/test_fairplay_check.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/fairplay_check.py
git commit -m "refactor(engine): route fairplay_check paths through penny_paths"
```

---

### Task 6: Repoint `outline_check.py`

**Files:**
- Modify: `scripts/outline_check.py`
- Test: `tests/test_outline_check.py` (existing; must stay green)

**Note:** `check_outline(outline_path, *, repo_root=None)` already takes an explicit `outline_path`, so the primary path is caller-supplied. Only repoint any internal `repo_root`-relative build (if present) and the CLI default that constructs `input/book-NN/outline.md`.

- [ ] **Step 1: Add import; repoint the CLI outline path**

Add `from scripts import penny_paths`. Where the CLI builds the default outline path from a book number, use:
```python
penny_paths.input_path(f"book-{book}/outline.md", root=repo_root)
```
Leave the explicit-`outline_path` code path untouched.

- [ ] **Step 2: Run outline tests**

Run: `python3 -m pytest tests/test_outline_check.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/outline_check.py
git commit -m "refactor(engine): route outline_check paths through penny_paths"
```

---

### Task 7: Repoint `review_gate.py`

**Files:**
- Modify: `scripts/review_gate.py`
- Test: `tests/test_review_gate.py` (existing; must stay green)

**Note:** review_gate takes `--config default "config/run-config.md"` and the reviews dir is already passed in relative. Route the config default through the overlay.

- [ ] **Step 1: Add import; overlay the config default**

Add `from scripts import penny_paths`. Change the argparse default so the run-config resolves via overlay: keep `--config` accepting an explicit path, but when it is the sentinel default (or omitted), resolve `penny_paths.config_path("run-config.md")`. Concretely, set `default=None` and after parsing:
```python
config = args.config or str(penny_paths.config_path("run-config.md"))
```

- [ ] **Step 2: Run review_gate tests**

Run: `python3 -m pytest tests/test_review_gate.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/review_gate.py
git commit -m "refactor(engine): overlay review_gate run-config via penny_paths"
```

---

### Task 8: Repoint `revision_priority.py`

**Files:**
- Modify: `scripts/revision_priority.py`
- Test: `tests/test_revision_priority.py` (existing; must stay green)

- [ ] **Step 1: Add import; repoint output dir + run-config**

Add `from scripts import penny_paths`. Replace:
```python
Path(repo_root) / "output" / f"book-{book}"
# ->
penny_paths.output_path(f"book-{book}", root=repo_root)

config_path = config_path or (Path(repo_root) / "config/run-config.md")
# ->
config_path = config_path or penny_paths.config_path("run-config.md", root=repo_root)
```
Change `repo_root=REPO` defaults to `repo_root=None` + lazy resolve at the top of `aggregate`/`cmd_report`.

- [ ] **Step 2: Run revision_priority tests**

Run: `python3 -m pytest tests/test_revision_priority.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/revision_priority.py
git commit -m "refactor(engine): route revision_priority paths through penny_paths"
```

---

### Task 9: Repoint `assemble_book.py`

**Files:**
- Modify: `scripts/assemble_book.py`
- Test: `tests/test_assemble_book.py` (existing; must stay green)

- [ ] **Step 1: Add import; repoint the output builders**

Add `from scripts import penny_paths`. Replace the `book_dir` helper body:
```python
def book_dir(book: str, repo_root) -> Path:
    return Path(repo_root) / "output" / f"book-{book}"
# ->
def book_dir(book: str, repo_root) -> Path:
    return penny_paths.output_path(f"book-{book}", root=repo_root)
```
`chapters_dir`, `manuscript_path`, `final_read_path` derive from `book_dir` and need no change. In `cmd_assemble`, the `outline = book_dir(book, repo_root) / "outline.md"` line — confirm whether the outline should come from `input/` (DATA) instead; if the current code reads the outline from `output/book-NN/outline.md`, leave as-is (behavior-preserving); do not change semantics in this refactor. Change `repo_root=REPO` defaults to `repo_root=None` + lazy resolve.

- [ ] **Step 2: Run assemble tests**

Run: `python3 -m pytest tests/test_assemble_book.py -v`
Expected: PASS.

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/assemble_book.py
git commit -m "refactor(engine): route assemble_book paths through penny_paths"
```

---

### Task 10: Repoint `voice_drift.py` + sweep the stragglers

**Files:**
- Modify: `scripts/voice_drift.py`, `scripts/canon_core_review.py`, `scripts/ledger_markers.py`, `scripts/reset_reviews.py`
- Test: their existing test files (must stay green)

- [ ] **Step 1: `voice_drift.py` — overlay the config default**

Add `from scripts import penny_paths`. Replace:
```python
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config/voice-pack/ai-tics-config.yaml"
# ->
def default_config(repo_root=None):
    return penny_paths.config_path("voice-pack/ai-tics-config.yaml", root=repo_root)
```
Update its callers/CLI default to call `default_config(...)`.

- [ ] **Step 2: Sweep `canon_core_review.py`, `ledger_markers.py`, `reset_reviews.py`**

For each: grep for hardcoded `config/`, `series/`, `input/`, `output/`, `.penny/` literals and repoint per the Global Constraints data-vs-config rule. Run:
```bash
grep -nE "\"(config|series|input|output)|'(config|series|input|output)|\.penny|parents\[1\] */" scripts/canon_core_review.py scripts/ledger_markers.py scripts/reset_reviews.py
```
Apply `series_path/input_path/output_path/penny_path` for data and `config_path` for config. If a file has no data/config literal (only the `sys.path.insert` import anchor), leave it unchanged.

- [ ] **Step 3: Confirm no path literals remain in `scripts/`**

Run:
```bash
grep -rnE "Path\([^)]*\) */ *\"(config|series|input|output)|/ *\"\.penny" scripts/*.py | grep -v penny_paths.py
```
Expected: no output (every consumer now routes through `penny_paths`).

- [ ] **Step 4: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/voice_drift.py scripts/canon_core_review.py scripts/ledger_markers.py scripts/reset_reviews.py
git commit -m "refactor(engine): sweep remaining scripts onto penny_paths"
```

---

### Task 11: Status line — series root + series name

**Files:**
- Modify: `scripts/penny-statusline.sh`
- Test: `tests/test_statusline.sh` or the existing status-line test if present (else add a bats-style/bash assertion)

**Interfaces:**
- Consumes: `python3 -m scripts.penny_paths resolve penny current-stage` and `... active`.

- [ ] **Step 1: Resolve the series root instead of assuming repo root**

Replace the current `ROOT`/`STAGE_FILE` derivation:
```bash
STAGE_FILE="$ROOT/.penny/current-stage"
```
with a series-root resolution via the CLI shim (falling back gracefully if not in a series):
```bash
STAGE_FILE="$(python3 -m scripts.penny_paths resolve penny current-stage 2>/dev/null)"
SERIES="$(python3 -m scripts.penny_paths active 2>/dev/null)"
```
Prepend the series name to the rendered line (e.g. `[$SERIES] …`) when `$SERIES` is non-empty. Keep the existing `PENNY_NO_CCSTATUSLINE` behavior and the ccstatusline append (do not remove it).

- [ ] **Step 2: Manual smoke test**

Run from a fixture series dir:
```bash
( cd tests/fixtures/series-fixture && printf 'book=01 chapter=03 stage=DRAFT' > .penny/current-stage && bash "$OLDPWD/scripts/penny-statusline.sh" <<<'{}' )
```
Expected: output contains the series name and `stage=DRAFT`.

- [ ] **Step 3: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS)
```bash
git add scripts/penny-statusline.sh
git commit -m "refactor(engine): status line reads series root + shows series name"
```

---

### Task 12: The fixture series + migrate any live-path tests

**Files:**
- Create: `tests/fixtures/series-fixture/.penny/`, `.../config/`, `.../series/`, `.../input/`, `.../output/` (minimal)
- Modify: any test that asserted a literal repo-root data path and now needs a series marker

- [ ] **Step 1: Build the minimal fixture tree**

```bash
mkdir -p tests/fixtures/series-fixture/.penny/locks
mkdir -p tests/fixtures/series-fixture/config
mkdir -p tests/fixtures/series-fixture/series/continuity/characters
mkdir -p tests/fixtures/series-fixture/series/whodunit
mkdir -p tests/fixtures/series-fixture/input
mkdir -p tests/fixtures/series-fixture/output
: > tests/fixtures/series-fixture/.penny/.keep
```

- [ ] **Step 2: Repoint any test that relied on the repo root being a series**

Run the suite and inspect failures (there should be few or none, since consumers thread `repo_root=tmp`):
```bash
python3 -m pytest -q
```
For any failure whose cause is `penny-paths: no series root`, give that test's tmp tree a `.penny/` dir (mirror `_make_series` from `tests/test_penny_paths.py`) or pass `root=tmp_path` explicitly. Do not weaken assertions — only supply the marker the resolver now requires.

- [ ] **Step 3: Full suite green + commit**

Run: `python3 -m pytest -q` (Expected: PASS, full count)
```bash
git add tests/fixtures/series-fixture tests/
git commit -m "test(engine): add fixture series; give marker-dependent tests a .penny root"
```

---

### Task 13: `/new-series` command + plugin manifest

**Files:**
- Create: `.claude/commands/new-series.md`
- Create: the plugin manifest (path/schema confirmed against Claude Code docs — see Step 1)

- [ ] **Step 1: Confirm the plugin manifest format**

Consult the current Claude Code plugin docs (via the built-in claude-code guide) for: the manifest filename + required fields, how commands/agents/skills/scripts are discovered, the stable plugin-root reference available to command runbooks, and the user-level enable step. Record the confirmed answers as a short comment block at the top of the manifest. (This is a documentation-lookup step, not a code guess — do not invent field names.)

- [ ] **Step 2: Write the manifest**

Create the manifest that registers this repo as the `penny` plugin bundling `.claude/commands`, `.claude/agents`, skills, and `scripts/`, per the confirmed schema from Step 1.

- [ ] **Step 3: Write `/new-series`**

`.claude/commands/new-series.md` — a runbook that, given `<name>`, creates `~/myBooks/<name>/` (the `~/myBooks` root configurable; default `~/myBooks`) with:
```
.penny/                       (marker + runtime; locks/ subdir)
config/                       (empty; overrides live here)
series/continuity/canon-core.md   (empty stub)
series/continuity/characters/     series/continuity/locations/  series/continuity/threads/
series/whodunit/              (empty)
input/   output/
```
then `git init` in the new folder and print the path + "cd there and run /plan-mystery 01". It invents no story content.

- [ ] **Step 4: Manual smoke test**

```bash
# Dry check the runbook logic by scaffolding to a tmp target, not ~/myBooks:
```
Verify the directory contract is created and `python3 -m scripts.penny_paths active` run from the new folder prints `<name>`.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/new-series.md .claude-plugin/
git commit -m "feat(engine): plugin manifest + /new-series scaffolder"
```

---

### Task 14: Update engine docs (CLAUDE.md) for the new topology

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the architecture description**

Update CLAUDE.md's "Three-layer architecture" and any path references to describe: engine = this repo/plugin; series = folders you `cd` into; active series = cwd via `.penny` marker; `penny_paths` as the resolver; config overlay. Remove any statement that implies data lives at the repo root. Note that `/use-series` / `PENNY_SERIES` do not exist (selection is by directory).

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(engine): CLAUDE.md describes plugin + series-folder topology"
```

---

### Task 15: Migrate the cozy series out to `~/myBooks/cozy-pelicans/`

**Files:**
- Move (out of this repo): `series/`, `input/`, `output/`, config **overrides**, `.penny/` runtime.
- Keep (engine defaults): `config/review-rubrics/`, `config/line-edit/`, `config/copy-edit/`, `config/self-audit/`, `config/outline-template.md`, `config/beta-readers/beta-protocol.md`.

**Note:** this is the one-time cutover; do it only after Tasks 1–14 are green. Not a pytest task — verified by running a real command from the new folder.

- [ ] **Step 1: Create the destination**

```bash
mkdir -p ~/myBooks
git -C "$(pwd)" ls-files series input output config/voice-pack config/setting-pack config/genre-pack config/length-profile.md config/run-config.md config/beta-readers/personas > /tmp/cozy-move.txt
```

- [ ] **Step 2: Move the series data into a fresh repo**

Copy (not `git mv`, since the destination is a new repo) the cozy data, then remove it from the engine repo:
```bash
mkdir -p ~/myBooks/cozy-pelicans
# copy data + overrides preserving structure
rsync -a --relative series input output config/voice-pack config/setting-pack config/genre-pack config/length-profile.md config/run-config.md config/beta-readers/personas ~/myBooks/cozy-pelicans/
# runtime marker + locks
rsync -a .penny ~/myBooks/cozy-pelicans/
# fresh repo
( cd ~/myBooks/cozy-pelicans && git init -q && git add -A && git commit -q -m "chore: cozy-pelicans series data (migrated from penny engine repo)" )
```

- [ ] **Step 3: Remove the moved data from the engine repo (keep engine defaults)**

```bash
git rm -r --quiet series input output \
  config/voice-pack config/setting-pack config/genre-pack \
  config/length-profile.md config/run-config.md config/beta-readers/personas .penny
git commit -q -m "chore(engine): remove migrated cozy series data (now in ~/myBooks/cozy-pelicans)"
```

- [ ] **Step 4: Smoke-test the whole thing from the series folder**

```bash
cd ~/myBooks/cozy-pelicans
python3 -m scripts.penny_paths active          # expect: cozy-pelicans   (scripts importable via the installed plugin)
python3 -m scripts.penny_paths resolve output book-01/chapters   # expect: ~/myBooks/cozy-pelicans/output/book-01/chapters
# run a real read-only gate against migrated data, e.g. readiness or preflight draft check
```
Expected: paths resolve into `~/myBooks/cozy-pelicans/…`, and config defaults still resolve back into the engine plugin.

- [ ] **Step 5: Engine suite still green (now against the fixture, not live data)**

```bash
cd -   # back to the engine repo
python3 -m pytest -q
```
Expected: PASS — tests depend on `tests/fixtures/`, not the removed cozy data.

---

## Self-Review

**Spec coverage:**
- Two roots → Task 1 (`plugin_root`, `series_root`). ✓
- Active series = cwd marker → Task 1 `series_root` walk-up; Tasks 2–11 default to it. ✓
- Config two-tier overlay → Task 1 `config_path`; applied in Tasks 2–10. ✓
- Selection apparatus removed → confirmed none exists (grep in planning); CLAUDE.md note in Task 14. ✓
- Scripts repointed (data→series, config→overlay) → Tasks 2–10 (each named script) + Task 10 sweep. ✓
- Status line → Task 11. ✓
- `/new-series`; `/use-series` deleted → Task 13 (create); deletion is a no-op (never existed) noted Task 14. ✓
- Plugin manifest + user-level enable → Task 13. ✓
- Fixture series + test migration → Task 12. ✓
- Migration cutover (fresh repo, engine keeps defaults + history) → Task 15. ✓
- Parallel safety test → Task 1 `test_parallel_safety_two_series_disjoint`. ✓

**Placeholder scan:** Task 13 Step 1 is a documentation-confirmation step (plugin manifest schema), explicitly not a code guess — the only externally-dependent item, and the design does not hinge on specific field names. No other TBD/TODO.

**Type/name consistency:** `series_root`, `plugin_root`, `config_path`, `series_path`, `input_path`, `output_path`, `penny_path`, `active` — used identically in Task 1 (definition) and Tasks 2–11 (consumers). `root=repo_root` keyword is consistent everywhere.
