# Genre-Pack Layer — Phase 1 (Resolver + Manifest) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the genre-resolution plumbing — a per-genre `genre.yaml` manifest, a loader/validator, and genre-aware path resolution — with **zero observable behavior change** (the cozy manifest reproduces today's hardcoded behavior, and nothing dispatches from it yet).

**Architecture:** `penny_paths` (stdlib-only) learns to read a flat `series.yaml → genre` and gains a three-tier config overlay (series → genre pack → engine default). A new PyYAML-using module `penny_genre` loads and validates the nested `genre.yaml` manifest (consistent with the dependency-split rule: PyYAML only for genuinely nested human-edited data). The cozy-mystery genre pack is authored to declare exactly the checks Penny runs today. No command or gate reads the manifest in this phase — that's Phase 2.

**Tech Stack:** Python 3 stdlib (`penny_paths`), PyYAML (`penny_genre`, same as existing checkers), pytest.

## Global Constraints

- **`scripts/penny_paths.py` stays stdlib-only** — no PyYAML, no third-party imports. It reads only the *flat* `series.yaml` (a `key: value` file) and does path math.
- **The nested `genre.yaml` manifest is parsed only by `scripts/penny_genre.py`**, which may import PyYAML (like `fairplay_check.py`, `lexicon_check.py`).
- **Zero behavior change in Phase 1.** No command, gate, or checker reads the manifest yet. The cozy manifest exists and validates; the three-tier overlay's middle (genre) tier finds nothing to override yet (the fair-play rubric doesn't move into the genre pack until Phase 3), so `config_path` resolves identically to today.
- **Manifest schema (exact):** a `genre.yaml` has keys `genre` (str, must equal its directory name), `conventions` (str, a file in the genre dir), `planning` (mapping: `command` str, `artifact` str containing `{NN}`, `validator` str-or-null, `lock` str-or-null), `inspectors` (list[str]), `gates` (list[str]), `rubrics` (list[str]), `tracks` (list[str]).
- **Conformance rule:** a manifest is valid only if every name it points at exists in the engine — `planning.command` → `commands/<command>.md`; each `inspectors` entry → `agents/inspector-<name>.md`; `planning.validator` (if non-null) → `scripts/<validator>_check.py`; `conventions` and each `rubrics` file → present under the genre dir.
- **Keep the full suite green** (`python3 -m pytest`, currently 284) after every task. Commit after every task.
- Work on a branch: `feat/genre-pack-phase1` (do not build on `main` directly).

## File Structure

- `genres/cozy-mystery/genre.yaml` — **new.** The cozy manifest (declares today's behavior).
- `genres/cozy-mystery/conventions.md` — **new.** Short conventions pointer (full consolidation is Phase 3).
- `series.yaml` — **new**, at the repo root (the current cozy series root). One line: `genre: cozy-mystery`.
- `scripts/penny_genre.py` — **new.** Manifest loader + validator (PyYAML). ~60 lines.
- `tests/test_penny_genre.py` — **new.** Loader/validator + real-cozy-manifest conformance tests.
- `scripts/penny_paths.py` — **modify.** Add `genre()`, `genre_dir()`; extend `config_path` to three tiers.
- `tests/test_penny_paths.py` — **modify.** Add genre-resolution + three-tier overlay tests.

---

### Task 1: Author the cozy-mystery genre pack + the series genre declaration

**Files:**
- Create: `genres/cozy-mystery/genre.yaml`
- Create: `genres/cozy-mystery/conventions.md`
- Create: `series.yaml`

**Interfaces:**
- Produces: the on-disk manifest that Task 2's validator and Task 3's resolver are tested against. The manifest's exact field values are the contract other tasks assert.

- [ ] **Step 1: Write the cozy manifest**

Create `genres/cozy-mystery/genre.yaml` verbatim:

```yaml
genre: cozy-mystery
conventions: conventions.md
planning:
  command: plan-mystery
  artifact: series/whodunit/book-{NN}.yaml
  validator: fairplay
  lock: mystery
inspectors:
  - continuity
  - fairplay
  - structure
  - voice
  - ai-prose
gates:
  - fairplay
  - lexicon
rubrics:
  - review-rubrics/fairplay-planting.md
tracks:
  - M
  - P
  - R
  - B
```

- [ ] **Step 2: Write the conventions pointer + the genre-pack rubric placeholder**

Create `genres/cozy-mystery/conventions.md`:

```markdown
# Cozy-mystery genre conventions

The cozy-mystery genre: an amateur sleuth, a closed community, fair-play clue
planting, no on-page gore, warmth and comfort texture, a satisfying reveal.

> Full conventions currently live in `config/genre-pack/cozy-mystery.md` and the
> series bible §3b. Phase 3 consolidates them here. This file exists so the
> manifest's `conventions:` reference resolves.
```

The manifest's `rubrics:` names `review-rubrics/fairplay-planting.md`. In Phase 1 the real rubric still lives at the engine default `config/review-rubrics/fairplay-planting.md` (it moves into the genre pack in Phase 3). So the conformance check for `rubrics` files (Task 2) must look them up **through the overlay** (genre dir OR engine default), not only in the genre dir. Create nothing else here.

- [ ] **Step 3: Write the series genre declaration**

Create `series.yaml` at the repo root (the current cozy series root):

```yaml
genre: cozy-mystery
```

- [ ] **Step 4: Verify the files parse as YAML**

Run:
```bash
python3 -c "import yaml; m=yaml.safe_load(open('genres/cozy-mystery/genre.yaml')); print(m['genre'], m['planning']['command'], m['inspectors'])"
```
Expected: `cozy-mystery plan-mystery ['continuity', 'fairplay', 'structure', 'voice', 'ai-prose']`

- [ ] **Step 5: Full suite unaffected**

Run: `python3 -m pytest -q`
Expected: PASS (284) — these are new data files, nothing reads them yet.

- [ ] **Step 6: Commit**

```bash
git add genres/cozy-mystery/genre.yaml genres/cozy-mystery/conventions.md series.yaml
git commit -m "feat(genre): cozy-mystery genre pack manifest + series genre declaration"
```

---

### Task 2: The manifest loader + validator — `scripts/penny_genre.py`

**Files:**
- Create: `scripts/penny_genre.py`
- Test: `tests/test_penny_genre.py`

**Interfaces:**
- Consumes: `scripts.penny_paths` (`plugin_root`, `series_root`) — imported lazily inside functions.
- Produces:
  - `MANIFEST_KEYS` (the required top-level keys) and `validate_manifest(manifest: dict, genre_dir: Path, *, plugin_root: Path) -> list[str]` (returns a list of error strings; empty = valid).
  - `load_manifest(genre: str | None = None, *, root: Path | None = None) -> dict` (resolves the active genre via `penny_paths`, reads + validates its `genre.yaml`, `sys.exit`s on error).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_penny_genre.py
from pathlib import Path

import pytest

from scripts import penny_genre as pg
from scripts import penny_paths as pp


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


VALID = """\
genre: demo
conventions: conventions.md
planning:
  command: plan-mystery
  artifact: series/whodunit/book-{NN}.yaml
  validator: fairplay
  lock: mystery
inspectors: [continuity, fairplay]
gates: [fairplay, lexicon]
rubrics: [review-rubrics/fairplay-planting.md]
tracks: [M, P]
"""


def _engine(tmp_path: Path) -> Path:
    """A fake plugin root with the engine components the conformance check needs."""
    (tmp_path / "commands").mkdir()
    (tmp_path / "commands" / "plan-mystery.md").write_text("x")
    (tmp_path / "agents").mkdir()
    for n in ("continuity", "fairplay"):
        (tmp_path / "agents" / f"inspector-{n}.md").write_text("x")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "fairplay_check.py").write_text("x")
    (tmp_path / "config" / "review-rubrics").mkdir(parents=True)
    (tmp_path / "config" / "review-rubrics" / "fairplay-planting.md").write_text("x")
    return tmp_path


def test_valid_manifest_has_no_errors(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "genre.yaml", VALID)
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load((gdir / "genre.yaml").read_text())
    assert pg.validate_manifest(manifest, gdir, plugin_root=engine) == []


def test_genre_must_match_dir(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "wrongname"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)  # genre: demo, but dir is 'wrongname'
    errs = pg.validate_manifest(manifest, gdir, plugin_root=engine)
    assert any("genre" in e and "wrongname" in e for e in errs)


def test_missing_inspector_agent_flagged(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)
    manifest["inspectors"] = ["continuity", "nonesuch"]
    errs = pg.validate_manifest(manifest, gdir, plugin_root=engine)
    assert any("nonesuch" in e for e in errs)


def test_missing_validator_script_flagged(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)
    manifest["planning"]["validator"] = "ghost"
    errs = pg.validate_manifest(manifest, gdir, plugin_root=engine)
    assert any("ghost" in e for e in errs)


def test_null_validator_and_lock_ok(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)
    manifest["planning"]["validator"] = None
    manifest["planning"]["lock"] = None
    assert pg.validate_manifest(manifest, gdir, plugin_root=engine) == []


def test_real_cozy_manifest_conforms():
    """The shipped cozy-mystery manifest validates against the real engine."""
    engine = pp.plugin_root()
    gdir = engine / "genres" / "cozy-mystery"
    import yaml
    manifest = yaml.safe_load((gdir / "genre.yaml").read_text())
    assert pg.validate_manifest(manifest, gdir, plugin_root=engine) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_genre.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_genre'`.

- [ ] **Step 3: Write the implementation**

```python
# scripts/penny_genre.py
"""Load and validate a genre manifest (genres/<genre>/genre.yaml).

The manifest is genuinely nested human-edited data, so this module (unlike the
stdlib-only penny_paths) uses PyYAML — consistent with the dependency-split rule.
It is the ONLY reader of the nested manifest; penny_paths reads only the flat
series.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

MANIFEST_KEYS = ("genre", "conventions", "planning", "inspectors", "gates", "rubrics", "tracks")
_PLANNING_KEYS = ("command", "artifact", "validator", "lock")


def validate_manifest(manifest: dict, genre_dir: Path, *, plugin_root: Path) -> list[str]:
    """Return a list of error strings (empty means valid)."""
    errs: list[str] = []
    for k in MANIFEST_KEYS:
        if k not in manifest:
            errs.append(f"manifest missing required key: {k}")
    if errs:
        return errs

    if manifest["genre"] != genre_dir.name:
        errs.append(f"genre '{manifest['genre']}' does not match directory '{genre_dir.name}'")

    planning = manifest["planning"]
    if not isinstance(planning, dict):
        errs.append("planning must be a mapping")
    else:
        for k in _PLANNING_KEYS:
            if k not in planning:
                errs.append(f"planning missing key: {k}")
        if "artifact" in planning and "{NN}" not in str(planning["artifact"]):
            errs.append("planning.artifact must contain the {NN} book placeholder")
        cmd = planning.get("command")
        if cmd and not (plugin_root / "commands" / f"{cmd}.md").is_file():
            errs.append(f"planning.command '{cmd}' -> commands/{cmd}.md not found")
        val = planning.get("validator")
        if val is not None and not (plugin_root / "scripts" / f"{val}_check.py").is_file():
            errs.append(f"planning.validator '{val}' -> scripts/{val}_check.py not found")

    for name in manifest.get("inspectors", []):
        if not (plugin_root / "agents" / f"inspector-{name}.md").is_file():
            errs.append(f"inspector '{name}' -> agents/inspector-{name}.md not found")

    # conventions + rubric files: resolve through the overlay (genre dir OR engine default)
    conv = manifest["conventions"]
    if not (genre_dir / conv).is_file():
        errs.append(f"conventions '{conv}' not found in {genre_dir}")
    for rel in manifest.get("rubrics", []):
        if not ((genre_dir / rel).is_file() or (plugin_root / "config" / rel).is_file()):
            errs.append(f"rubric '{rel}' not found in genre pack or engine defaults")

    for key in ("inspectors", "gates", "rubrics", "tracks"):
        if not isinstance(manifest.get(key), list):
            errs.append(f"{key} must be a list")
    return errs


def load_manifest(genre: str | None = None, *, root: Path | None = None) -> dict:
    from scripts import penny_paths
    if genre is None:
        genre = penny_paths.genre(root=root)
    genre_dir = penny_paths.plugin_root() / "genres" / genre
    mpath = genre_dir / "genre.yaml"
    if not mpath.is_file():
        sys.exit(f"penny-genre: no manifest at {mpath}")
    manifest = yaml.safe_load(mpath.read_text(encoding="utf-8"))
    errs = validate_manifest(manifest, genre_dir, plugin_root=penny_paths.plugin_root())
    if errs:
        sys.exit("penny-genre: invalid manifest:\n  - " + "\n  - ".join(errs))
    return manifest
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_genre.py -v`
Expected: PASS (all 6). Note `test_real_cozy_manifest_conforms` proves the Task-1 manifest names only components that exist.

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_genre.py tests/test_penny_genre.py
git commit -m "feat(genre): manifest loader + conformance validator (penny_genre)"
```

---

### Task 3: Genre resolution + three-tier overlay in `penny_paths`

**Files:**
- Modify: `scripts/penny_paths.py`
- Test: `tests/test_penny_paths.py`

**Interfaces:**
- Consumes: existing `plugin_root()`, `series_root()`, `_root()`.
- Produces:
  - `genre(root: Path | None = None) -> str` — reads `<series-root>/series.yaml`, returns the `genre` value; `sys.exit`s if the file is missing, has no `genre:` line, or names a genre with no `genres/<slug>/` dir under `plugin_root()`.
  - `genre_dir(g: str | None = None, root: Path | None = None) -> Path` — `plugin_root()/genres/<g or genre()>`.
  - `config_path(rel, root=None)` — now three-tier: series override → genre pack → engine default.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_penny_paths.py`:

```python
def _make_genre_series(tmp_path, slug="cozy-mystery"):
    """A tmp series that declares a genre which really exists in the engine."""
    (tmp_path / ".penny").mkdir()
    (tmp_path / "series.yaml").write_text(f"genre: {slug}\n", encoding="utf-8")
    return tmp_path


def test_genre_reads_series_yaml(tmp_path):
    s = _make_genre_series(tmp_path)
    assert pp.genre(root=s) == "cozy-mystery"


def test_genre_missing_series_yaml_fails(tmp_path):
    (tmp_path / ".penny").mkdir()
    with pytest.raises(SystemExit) as e:
        pp.genre(root=tmp_path)
    assert "series.yaml" in str(e.value)


def test_genre_unknown_slug_fails(tmp_path):
    s = _make_genre_series(tmp_path, slug="no-such-genre")
    with pytest.raises(SystemExit) as e:
        pp.genre(root=s)
    assert "no-such-genre" in str(e.value)


def test_genre_dir_points_into_plugin(tmp_path):
    s = _make_genre_series(tmp_path)
    assert pp.genre_dir(root=s) == pp.plugin_root() / "genres" / "cozy-mystery"


def test_config_path_series_overrides_genre_and_default(tmp_path):
    s = _make_genre_series(tmp_path)
    ov = s / "config" / "review-rubrics"
    ov.mkdir(parents=True)
    (ov / "structure-tension.md").write_text("series", encoding="utf-8")
    assert pp.config_path("review-rubrics/structure-tension.md", root=s) == ov / "structure-tension.md"


def test_config_path_genre_tier_between_series_and_default(tmp_path, monkeypatch):
    # Simulate a genre-pack override by pointing genre_dir at a tmp dir that has the file.
    s = _make_genre_series(tmp_path)
    fake_genre = tmp_path / "fake-genre"
    (fake_genre / "review-rubrics").mkdir(parents=True)
    (fake_genre / "review-rubrics" / "fairplay-planting.md").write_text("genre", encoding="utf-8")
    monkeypatch.setattr(pp, "genre_dir", lambda g=None, root=None: fake_genre)
    got = pp.config_path("review-rubrics/fairplay-planting.md", root=s)
    assert got == fake_genre / "review-rubrics" / "fairplay-planting.md"


def test_config_path_falls_to_engine_default_when_no_override(tmp_path):
    s = _make_genre_series(tmp_path)  # no series override, cozy genre ships no such file yet
    got = pp.config_path("review-rubrics/character-voice.md", root=s)
    assert got == pp.plugin_root() / "config" / "review-rubrics/character-voice.md"
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_paths.py -k "genre or config_path_genre or config_path_series or config_path_falls" -v`
Expected: FAIL — `AttributeError: module 'scripts.penny_paths' has no attribute 'genre'` (and the overlay tests fail on the two-tier `config_path`).

- [ ] **Step 3: Implement genre resolution + three-tier overlay**

In `scripts/penny_paths.py`, add after `active()`:

```python
def _read_genre_decl(series_yaml: Path) -> str | None:
    for line in series_yaml.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("genre:"):
            return s.split(":", 1)[1].strip()
    return None


def genre(root: Path | None = None) -> str:
    series_yaml = _root(root) / "series.yaml"
    if not series_yaml.is_file():
        sys.exit(f"penny-paths: no series.yaml (cannot resolve genre) at {series_yaml}")
    g = _read_genre_decl(series_yaml)
    if not g:
        sys.exit(f"penny-paths: series.yaml has no 'genre:' line ({series_yaml})")
    if not (plugin_root() / "genres" / g).is_dir():
        sys.exit(f"penny-paths: unknown genre '{g}' (no genres/{g}/ in plugin)")
    return g


def genre_dir(g: str | None = None, root: Path | None = None) -> Path:
    return plugin_root() / "genres" / (g or genre(root=root))
```

Replace `config_path` with the three-tier version:

```python
def config_path(rel: str, root: Path | None = None) -> Path:
    series_override = _root(root) / "config" / rel
    if series_override.exists():
        return series_override
    genre_override = genre_dir(root=root) / rel
    if genre_override.exists():
        return genre_override
    return plugin_root() / "config" / rel
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_paths.py -v`
Expected: PASS (existing tests + the 7 new ones).

- [ ] **Step 5: Full suite — behavior preserved**

Run: `python3 -m pytest -q`
Expected: PASS. Critically, all pre-existing `config_path` tests still pass: the new genre tier only activates when a `genres/<genre>/<rel>` file exists, and the shipped cozy pack ships none yet (the fair-play rubric moves in Phase 3), so resolution is identical to before.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_paths.py tests/test_penny_paths.py
git commit -m "feat(genre): penny_paths genre resolution + three-tier config overlay"
```

---

## Self-Review

**Spec coverage (Phase 1 slice):**
- Manifest schema + the cozy manifest reproducing today's behavior → Task 1. ✓
- `genre.yaml` loader + conformance (names must exist in engine) → Task 2. ✓
- `genre()` / `genre_dir()` + three-tier `config_path` → Task 3. ✓
- Manifest-conformance test (shipped genre validates against real engine) → Task 2 `test_real_cozy_manifest_conforms`. ✓
- Zero behavior change → Task 3 Step 5 (genre tier ships no overrides yet) + no command reads the manifest this phase. ✓
- `penny_paths` stays stdlib; PyYAML confined to `penny_genre` → enforced by file structure (Task 3 adds no import; Task 2 is the only PyYAML addition). ✓
- Deferred to later phases (correctly out of this plan): dispatch from the manifest (P2), fixture series + repointing the ~47 tests (P2), moving the fair-play rubric into the genre pack + the cutover (P3), the thriller pack (P4).

**Placeholder scan:** none — every code step shows complete code; the conventions.md "full consolidation in Phase 3" is an intentional, scoped deferral, not a TBD in this phase's deliverable.

**Type consistency:** `validate_manifest(manifest, genre_dir, *, plugin_root)` and `load_manifest(genre=None, *, root=None)` are used identically in Task 2's tests and body; `genre(root=None)`, `genre_dir(g=None, root=None)`, `config_path(rel, root=None)` match between Task 3's Produces block, its implementation, and the tests. The conformance rule (inspector→`agents/inspector-<name>.md`, validator→`scripts/<v>_check.py`, command→`commands/<cmd>.md`) is identical in the Global Constraints, Task 2's validator, and Task 1's manifest values.
