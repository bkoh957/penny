# Genre-Pack Layer — Phase 2 (Genre-Aware Dispatch) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the review/planning commands read the genre manifest instead of a hardcoded set — so `review-chapter` fans out the *genre's* inspectors and a new genre-neutral `/plan-book` delegates to the genre's planning runbook — with cozy behavior unchanged (the cozy manifest reproduces today's set).

**Architecture:** Add data accessors + a CLI shim to `scripts/penny_genre.py` (`inspectors`, `gates`, `planning-command`, `planning-artifact`, `planning-lock`) so markdown runbooks can query the active series' genre without parsing YAML themselves. Then edit `commands/review-chapter.md` to resolve its inspector set from that CLI (keeping a static per-inspector rubric/verdict table the genre *selects from*), and add `commands/plan-book.md` as the genre-neutral planning front door. No deterministic-gate logic changes in this phase (preflight stays as-is; genre-aware gates are a later increment).

**Tech Stack:** Python 3 stdlib + PyYAML (in `penny_genre` only), pytest, Claude Code command runbooks (markdown).

## Global Constraints

- **`penny_paths` stays stdlib-only.** The manifest accessors live in `scripts/penny_genre.py` (PyYAML), not `penny_paths`.
- **Cozy behavior is unchanged.** The cozy manifest already declares `inspectors: [continuity, fairplay, structure, voice, ai-prose]` and `planning.command: plan-mystery` — the exact set/flow the runbooks hardcode today. After this phase, resolving them from the manifest yields the identical result for cozy series.
- **Runbooks reference bundled scripts via `${CLAUDE_PLUGIN_ROOT}`** (established in the plugin refactor), e.g. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" inspectors`.
- **The genre selects WHICH inspectors run; the engine knows each inspector's rubric + verdict filename.** That per-inspector detail is a static table in the `review-chapter` runbook (identical for every genre); the genre's `inspectors:` list chooses the subset. Inspector → (rubric, verdict file) map (today's five):
  - `continuity` → rubric `continuity-drift.md`, verdict `continuity-drift.md`
  - `fairplay` → rubric `fairplay-planting.md`, verdict `fairplay-planting.md`
  - `structure` → rubric `structure-tension.md`, verdict `structure-tension.md` (also gets the thread roster)
  - `voice` → rubric `character-voice.md`, verdict `character-voice.md`
  - `ai-prose` → rubric `ai-prose-taste-flags.md`, verdict `ai-prose-taste-flags.md`
- **Keep the full suite green** (`python3 -m pytest`, currently 298) after every task. Commit after every task.
- Work on a branch: `feat/genre-pack-phase2` (not `main`).

## File Structure

- `scripts/penny_genre.py` — **modify.** Add `inspectors()`, `gates()`, `planning()` accessors + extend the CLI (`_main`) with `inspectors|gates|planning-command|planning-artifact|planning-lock`.
- `tests/test_penny_genre.py` — **modify.** Accessor + CLI tests.
- `commands/plan-book.md` — **new.** Genre-neutral planning front door.
- `commands/review-chapter.md` — **modify.** Resolve the inspector set from the genre CLI; keep the static per-inspector table.

---

### Task 1: Manifest accessors + CLI in `penny_genre`

**Files:**
- Modify: `scripts/penny_genre.py`
- Test: `tests/test_penny_genre.py`

**Interfaces:**
- Consumes: `load_manifest(genre=None, *, root=None)` (Phase 1).
- Produces:
  - `inspectors(root: Path | None = None) -> list[str]` — the active genre's `inspectors`.
  - `gates(root: Path | None = None) -> list[str]` — the active genre's `gates`.
  - `planning(root: Path | None = None) -> dict` — the active genre's `planning` mapping.
  - CLI: `python3 -m scripts.penny_genre <inspectors|gates|planning-command|planning-artifact|planning-lock>` — prints newline-joined lists (inspectors/gates) or the single scalar (planning-*). `planning-lock`/`planning-validator` print an empty line when null.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_penny_genre.py`:

```python
import os
import subprocess
import sys


def _cozy_series(tmp_path):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "series.yaml").write_text("genre: cozy-mystery\n", encoding="utf-8")
    return tmp_path


def test_inspectors_accessor(tmp_path):
    s = _cozy_series(tmp_path)
    assert pg.inspectors(root=s) == ["continuity", "fairplay", "structure", "voice", "ai-prose"]


def test_gates_accessor(tmp_path):
    s = _cozy_series(tmp_path)
    assert pg.gates(root=s) == ["fairplay", "lexicon"]


def test_planning_accessor(tmp_path):
    s = _cozy_series(tmp_path)
    p = pg.planning(root=s)
    assert p["command"] == "plan-mystery"
    assert p["artifact"] == "series/whodunit/book-{NN}.yaml"
    assert p["validator"] == "fairplay"
    assert p["lock"] == "mystery"


def test_cli_inspectors_newline_joined(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "inspectors"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.returncode == 0
    assert out.stdout.split() == ["continuity", "fairplay", "structure", "voice", "ai-prose"]


def test_cli_planning_command(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "planning-command"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.stdout.strip() == "plan-mystery"


def test_cli_planning_lock(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "planning-lock"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.stdout.strip() == "mystery"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_genre.py -k "accessor or cli" -v`
Expected: FAIL — `AttributeError: module 'scripts.penny_genre' has no attribute 'inspectors'` (and no CLI).

- [ ] **Step 3: Add the accessors + CLI to `scripts/penny_genre.py`**

Append these functions (after `load_manifest`):

```python
def inspectors(root: Path | None = None) -> list[str]:
    return load_manifest(root=root)["inspectors"]


def gates(root: Path | None = None) -> list[str]:
    return load_manifest(root=root)["gates"]


def planning(root: Path | None = None) -> dict:
    return load_manifest(root=root)["planning"]


def _main(argv: list[str]) -> int:
    if not argv:
        print("usage: penny_genre <inspectors|gates|planning-command|planning-artifact|planning-lock|planning-validator>",
              file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "inspectors":
        print("\n".join(inspectors()))
        return 0
    if cmd == "gates":
        print("\n".join(gates()))
        return 0
    if cmd.startswith("planning-"):
        key = cmd[len("planning-"):]
        val = planning().get(key)
        print("" if val is None else val)
        return 0
    print(f"penny_genre: unknown command '{cmd}'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

Add `import sys` to the imports if not already present (it is — `penny_genre` already imports `sys`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_genre.py -v`
Expected: PASS (the Phase-1 tests + the 6 new ones).

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_genre.py tests/test_penny_genre.py
git commit -m "feat(genre): penny_genre manifest accessors + CLI (inspectors/gates/planning)"
```

---

### Task 2: `/plan-book` — the genre-neutral planning front door

**Files:**
- Create: `commands/plan-book.md`

**Interfaces:**
- Consumes: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" planning-command` (Task 1).

**Note:** this is a command runbook (markdown executed by the model), not unit-tested code. Its correctness is verified by review + the fact that the CLI it calls is tested in Task 1.

- [ ] **Step 1: Write the runbook**

Create `commands/plan-book.md`:

```markdown
---
name: plan-book
description: Plan a book — resolve the active series' genre and delegate to that genre's planning runbook.
---

# /plan-book NN

Genre-neutral planning front door. It resolves the active series' genre (from
`series.yaml`, via `penny_genre`) and runs that genre's planning flow — so a cozy
series runs the whodunit planner and a thriller runs the thriller planner, without
the author choosing a genre-specific command.

## Steps

1. **Parse args:** `book=NN` (e.g. `01`).

2. **Resolve the genre's planning command:**

   ```bash
   PLAN_CMD="$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" planning-command)"
   ```

   If this fails (no `series.yaml` / unknown genre), stop and tell the author to
   run `/new-series` or add a `genre:` line to `series.yaml`.

3. **Delegate** to the genre's planning runbook named by `$PLAN_CMD`
   (e.g. `plan-mystery` for cozy-mystery). Invoke that command with the same
   `book` argument and follow it to completion. `/plan-book` adds no planning
   logic of its own — it only routes.
```

- [ ] **Step 2: Sanity-check the CLI call the runbook relies on**

Run (from a cozy series root — the repo root works, it has `series.yaml`):
```bash
python3 scripts/penny_genre.py planning-command
```
Expected: `plan-mystery`

- [ ] **Step 3: Full suite (unaffected — runbook only)**

Run: `python3 -m pytest -q`
Expected: PASS (298 + Task 1's additions).

- [ ] **Step 4: Commit**

```bash
git add commands/plan-book.md
git commit -m "feat(genre): /plan-book genre-neutral planning front door"
```

---

### Task 3: `review-chapter` resolves its inspector set from the genre

**Files:**
- Modify: `commands/review-chapter.md`

**Interfaces:**
- Consumes: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" inspectors` (Task 1).

**Note:** runbook (markdown) change. Correctness = the resolved set for a cozy series equals today's hardcoded five, and the per-inspector rubric/verdict table is preserved.

- [ ] **Step 1: Replace the hardcoded inspector list with genre resolution**

In `commands/review-chapter.md`, find the step that enumerates "the 5 blind inspector sub-agents" and their verdict files (the numbered list mapping `inspector-continuity → continuity-drift.md`, etc.). Replace the *hardcoded enumeration* with:

1. A **resolution step** placed before dispatch:

   ```bash
   INSPECTORS="$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_genre.py" inspectors)"
   ```
   `$INSPECTORS` is the active genre's blind-inspector set (for a cozy series:
   `continuity fairplay structure voice ai-prose`).

2. A **static per-inspector reference table** (unchanged behavior — the genre selects
   from this; the engine owns each row). Keep it verbatim in the runbook:

   | inspector | agent | rubric | verdict file |
   |---|---|---|---|
   | continuity | inspector-continuity | continuity-drift.md | continuity-drift.md |
   | fairplay | inspector-fairplay | fairplay-planting.md | fairplay-planting.md |
   | structure | inspector-structure | structure-tension.md | structure-tension.md (also gets the thread roster) |
   | voice | inspector-voice | character-voice.md | character-voice.md |
   | ai-prose | inspector-ai-prose | ai-prose-taste-flags.md | ai-prose-taste-flags.md |

3. A **dispatch instruction:** "Dispatch, blind, exactly the inspectors named in
   `$INSPECTORS` — for each, the `inspector-<name>` sub-agent with the chapter text,
   its rubric (from the table), and the ledger slice (structure also gets the thread
   roster). Each writes its verdict to the named file in `ch-MM.reviews/`."

4. Update the **dispatch-completeness check** so it confirms one verdict file per
   inspector in `$INSPECTORS` (not a hardcoded "all five") — a thriller with four
   inspectors must not fail this check for a missing fifth.

Preserve everything else in the runbook (the developmental-editor step, the
cross-model guard, the deterministic checkers, the gate computation).

- [ ] **Step 2: Verify the resolved cozy set matches today's five**

Run (from the repo root cozy series):
```bash
python3 scripts/penny_genre.py inspectors | tr '\n' ' '
```
Expected: `continuity fairplay structure voice ai-prose ` — identical to the previously-hardcoded set, so cozy review behavior is unchanged.

- [ ] **Step 3: Full suite (unaffected — runbook only)**

Run: `python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add commands/review-chapter.md
git commit -m "feat(genre): review-chapter resolves its inspector set from the active genre"
```

---

## Self-Review

**Spec coverage (Phase 2 dispatch slice):**
- Manifest accessors so runbooks can query the genre → Task 1. ✓
- `review-chapter` dispatches the genre's inspectors → Task 3. ✓
- `/plan-book` genre-neutral planning front door → Task 2. ✓
- Cozy behavior unchanged (resolved set/flow == hardcoded) → Task 1 values + Task 3 Step 2 + Task 2 Step 2. ✓
- **Deferred to later increments (correctly out of this plan):** `preflight` genre-aware gates/lock (needs its tests repointed at manifest-aware fixtures); the fixture series + repointing the ~47 data-dependent tests (the cutover prerequisite, folds into Phase 3); the thriller genre (Phase 4).

**Placeholder scan:** none. Runbook tasks give complete markdown; the deferred items are named, not TBD.

**Type consistency:** `inspectors(root=None) -> list[str]`, `gates(root=None) -> list[str]`, `planning(root=None) -> dict` are used identically in Task 1's Produces, tests, and body; the CLI subcommands (`inspectors`, `gates`, `planning-command/artifact/lock/validator`) match between Task 1's CLI, its tests, and the runbook calls in Tasks 2–3. The inspector→(rubric, verdict) table is identical in the Global Constraints and Task 3.
