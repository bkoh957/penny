# Genre-Pack Layer — Phase 3a (Decouple Tests from Live Data) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the engine test suite pass with **no live cozy series data present**, by building a fixture cozy series and repointing every test that currently reads the live cozy config/series/input at the repo root — the prerequisite that makes the cozy-data cutover to `~/myBooks/cozy-pelicans/` safe. Also move the fair-play rubric/conventions into the cozy genre pack.

**Architecture:** Add a self-contained `tests/fixtures/cozy/` series (its own `.penny`, `series.yaml: genre: cozy-mystery`, and copies of the config overrides + a minimal `series/`/`input/` that the content-contract tests validate). Expose it via a `cozy_fixture` conftest fixture. Repoint the ~47 data-dependent tests to that fixture instead of the repo root. Move `fairplay-planting.md` + cozy conventions into `genres/cozy-mystery/` so the genre tier (not the engine default) supplies them — the overlay already resolves this.

**Tech Stack:** pytest, Python 3 stdlib, git.

## Global Constraints

- **The fixture is a snapshot of real, valid cozy content** (copied from the live files at build time) so content-contract assertions hold by construction. Keep it minimal where content isn't asserted (e.g. a small outline, one or two character files), but copy the real `run-config.md`, `lexicon.yaml`, `ai-tics-config.yaml`, personas, and `canon-core.md` verbatim (those ARE what the contract tests validate).
- **No assertion is weakened.** Repointing changes only the *path source* (repo root → fixture), never what a test asserts. A content-contract test still asserts the same structural facts, now about the fixture's (real-content) copy.
- **The engine keeps genre-neutral config DEFAULTS**; the cozy overrides (voice/setting/genre packs, run-config, length-profile, personas) and the fair-play rubric are what move (to the fixture for tests, and — in the deferred cutover — to `~/myBooks`). Neutral rubrics (continuity/voice/structure-tension/ai-prose) stay engine defaults.
- **Suite stays green after every task** (`python3 -m pytest`, currently 305). Commit after every task.
- **Do NOT run the data cutover in this plan.** This plan ends with the suite green *while live data still exists*; the final task adds a temporary CI-style guard that proves the suite passes with live data hidden, then restores it. The real cutover is a separate, explicitly-gated step.
- Work on a branch: `feat/genre-pack-phase3a` (not `main`).

## File Structure

- `tests/fixtures/cozy/` — **new.** A complete minimal cozy series: `.penny/`, `series.yaml`, `config/` overrides, `series/continuity/{canon-core.md,characters/}`, `series/whodunit/`, `input/`.
- `tests/conftest.py` — **modify.** Add a `cozy_fixture` fixture returning `Path(tests/fixtures/cozy)`.
- `genres/cozy-mystery/review-rubrics/fairplay-planting.md` — **new (git mv from config/).**
- `genres/cozy-mystery/conventions.md` — **modify** (absorb the cozy genre conventions).
- The 14 test files listed below — **modify** to read the fixture instead of the repo root.

---

### Task 1: Build the fixture cozy series + `cozy_fixture` conftest fixture

**Files:**
- Create: `tests/fixtures/cozy/**`
- Modify: `tests/conftest.py`
- Test: `tests/test_cozy_fixture.py` (new — asserts the fixture is complete + valid)

**Interfaces:**
- Produces: `cozy_fixture` pytest fixture → `Path` to `tests/fixtures/cozy/`; and the on-disk fixture tree that later tasks point at.

- [ ] **Step 1: Build the fixture tree by copying real cozy content**

```bash
F=tests/fixtures/cozy
mkdir -p $F/.penny/locks $F/series/continuity/characters $F/series/whodunit $F/input/series $F/input/book-01
printf 'genre: cozy-mystery\n' > $F/series.yaml
# config overrides — copy the REAL files (these are what content-contract tests validate)
mkdir -p $F/config/voice-pack $F/config/setting-pack $F/config/genre-pack $F/config/beta-readers
cp config/run-config.md $F/config/run-config.md
cp config/length-profile.md $F/config/length-profile.md
cp -R config/voice-pack/. $F/config/voice-pack/
cp -R config/setting-pack/. $F/config/setting-pack/
cp -R config/genre-pack/. $F/config/genre-pack/
cp -R config/beta-readers/personas $F/config/beta-readers/personas
# series data — real canon-core (contract-validated) + one real character + one whodunit
cp series/continuity/canon-core.md $F/series/continuity/canon-core.md
cp series/continuity/characters/maggie-quill.md $F/series/continuity/characters/maggie-quill.md
cp series/whodunit/book-01.yaml $F/series/whodunit/book-01.yaml 2>/dev/null || true
# input — a small outline + whodunit-ledger the scaffold tests look for
cp input/series/whodunit-ledger.md $F/input/series/whodunit-ledger.md 2>/dev/null || printf '# Whodunit Ledger\n' > $F/input/series/whodunit-ledger.md
head -40 input/book-01/outline.md > $F/input/book-01/outline.md
: > $F/.penny/.keep
```
Adjust the specific copies to whatever the content-contract tests in later tasks actually read (Task 3 enumerates them). If a source file doesn't exist, create a minimal valid stand-in and note it.

- [ ] **Step 2: Ensure the fixture's `.penny` is tracked (the `.gitignore` negation from the plugin refactor)**

The repo `.gitignore` ignores `.penny/` but already negates `tests/fixtures/series-fixture/.penny/`. Add a parallel negation for `tests/fixtures/cozy/.penny/`:
```bash
grep -q 'tests/fixtures/cozy/.penny' .gitignore || printf '!tests/fixtures/cozy/.penny/\n!tests/fixtures/cozy/.penny/**\n' >> .gitignore
```
Verify: `git check-ignore tests/fixtures/cozy/.penny/.keep` prints nothing (i.e. it is trackable).

- [ ] **Step 3: Write the failing fixture-completeness test**

```python
# tests/test_cozy_fixture.py
from pathlib import Path

FIX = Path(__file__).resolve().parent / "fixtures" / "cozy"


def test_cozy_fixture_is_a_complete_series():
    assert (FIX / ".penny").is_dir()
    assert (FIX / "series.yaml").read_text().strip() == "genre: cozy-mystery"
    for rel in ("config/run-config.md", "config/setting-pack/lexicon.yaml",
                "config/voice-pack/ai-tics-config.yaml", "config/beta-readers/personas",
                "series/continuity/canon-core.md", "input/series/whodunit-ledger.md"):
        assert (FIX / rel).exists(), f"fixture missing {rel}"


def test_cozy_fixture_genre_resolves():
    from scripts import penny_paths
    assert penny_paths.genre(root=FIX) == "cozy-mystery"
```

- [ ] **Step 4: Run it to verify pass** (the fixture already exists from Steps 1–2)

Run: `python3 -m pytest tests/test_cozy_fixture.py -v`
Expected: PASS. If a listed file is missing, add it to the fixture (Step 1) — do not weaken the assertion.

- [ ] **Step 5: Add the `cozy_fixture` conftest fixture**

In `tests/conftest.py`, add:
```python
@pytest.fixture
def cozy_fixture():
    """Path to the self-contained fixture cozy series (tests/fixtures/cozy/)."""
    return Path(__file__).resolve().parent / "fixtures" / "cozy"
```
(Ensure `from pathlib import Path` and `import pytest` are present at the top — they are.)

- [ ] **Step 6: Full suite + commit**

Run: `python3 -m pytest -q` (Expected: PASS — additive)
```bash
git add tests/fixtures/cozy tests/conftest.py tests/test_cozy_fixture.py .gitignore
git commit -m "test(genre): fixture cozy series + cozy_fixture conftest (decouple prep)"
```

---

### Task 2: Move the fair-play rubric + conventions into the cozy genre pack

**Files:**
- Move: `config/review-rubrics/fairplay-planting.md` → `genres/cozy-mystery/review-rubrics/fairplay-planting.md`
- Modify: `genres/cozy-mystery/conventions.md`

**Interfaces:**
- Consumes: the three-tier `config_path` (Phase 1) — after the move, `config_path("review-rubrics/fairplay-planting.md", root=<cozy series>)` resolves from the genre pack.

- [ ] **Step 1: git mv the rubric into the genre pack**

```bash
mkdir -p genres/cozy-mystery/review-rubrics
git mv config/review-rubrics/fairplay-planting.md genres/cozy-mystery/review-rubrics/fairplay-planting.md
```

- [ ] **Step 2: Verify the overlay resolves it from the genre tier**

```bash
python3 -c "from scripts import penny_paths as p; import pathlib; print(p.config_path('review-rubrics/fairplay-planting.md', root=pathlib.Path('.')))"
```
Expected: a path ending in `genres/cozy-mystery/review-rubrics/fairplay-planting.md` (the repo root declares `genre: cozy-mystery`, so the genre tier now supplies the rubric).

Also confirm a **genre-less** caller still falls to the engine default gracefully (the file is gone from `config/`, so a genre-less series would now get a non-existent engine-default path — that's acceptable because fair-play is cozy-genre-specific; no genre-less series uses it). Confirm the manifest-conformance test still passes (it resolves the rubric via genre-dir OR engine-default): `python3 -m pytest tests/test_penny_genre.py -k conform -v`.

- [ ] **Step 3: Consolidate cozy conventions**

Replace `genres/cozy-mystery/conventions.md`'s "full conventions live elsewhere" pointer with the actual cozy genre conventions: move the genre-general content from `config/genre-pack/cozy-mystery.md` into it (or reference it). Keep it factual; do not invent conventions. If `config/genre-pack/cozy-mystery.md` is still consumed elsewhere, leave it and have `conventions.md` point at it — grep first: `grep -rn "genre-pack/cozy-mystery" --include=*.md --include=*.py .`

- [ ] **Step 4: Full suite + commit**

Run: `python3 -m pytest -q`
Expected: PASS. If any test read `config/review-rubrics/fairplay-planting.md` directly (grep to check: `grep -rn "fairplay-planting" tests/`), repoint it through `config_path(root=cozy_fixture)` or the genre-pack path — do not leave a dangling reference.
```bash
git add -A genres/cozy-mystery config/review-rubrics config/genre-pack
git commit -m "feat(genre): move fair-play rubric + conventions into cozy-mystery genre pack"
```

---

### Task 3: Repoint the content-contract tests to the fixture

**Files (modify):** `tests/test_run_config.py`, `tests/test_lexicon_schema.py`, `tests/test_canon_core_contract.py`, `tests/test_ledger_schema.py`, `tests/test_penny_meta.py`, `tests/test_beta_scaffold.py`

**These assert the real cozy files are well-formed. Repoint each to the fixture's (real-content) copies.** Exact current references and their replacements:

- [ ] **Step 1: `test_run_config.py`** — `load("config/run-config.md")` (relative to cwd) → load the fixture's copy. Add `FIX = Path(__file__).resolve().parent / "fixtures" / "cozy"` and change both `load("config/run-config.md")` calls to `load(str(FIX / "config/run-config.md"))`.
- [ ] **Step 2: `test_lexicon_schema.py`** — `LEXICON = REPO / "config/setting-pack/lexicon.yaml"` → `LEXICON = Path(__file__).resolve().parent / "fixtures/cozy/config/setting-pack/lexicon.yaml"`.
- [ ] **Step 3: `test_canon_core_contract.py`** — `CANON = REPO / "series/continuity/canon-core.md"` → `CANON = Path(__file__).resolve().parent / "fixtures/cozy/series/continuity/canon-core.md"`.
- [ ] **Step 4: `test_ledger_schema.py`** — `CONTINUITY = Path("series/continuity")` → `CONTINUITY = Path(__file__).resolve().parent / "fixtures/cozy/series/continuity"`. (Ensure the fixture's continuity dir has canon-core + at least one character so the glob asserts something.)
- [ ] **Step 5: `test_penny_meta.py`** — the one test reading `repo / "series/continuity/canon-core.md"` → the fixture's copy.
- [ ] **Step 6: `test_beta_scaffold.py`** — `PERSONA_DIR = ROOT / "config/beta-readers/personas"` → `Path(__file__).resolve().parent / "fixtures/cozy/config/beta-readers/personas"`.
- [ ] **Step 7: Run these files + full suite; commit**

Run: `python3 -m pytest tests/test_run_config.py tests/test_lexicon_schema.py tests/test_canon_core_contract.py tests/test_ledger_schema.py tests/test_penny_meta.py tests/test_beta_scaffold.py -v` (Expected: PASS — assertions unchanged, now about the fixture's real-content copies), then `python3 -m pytest -q` (PASS).
```bash
git add tests/test_run_config.py tests/test_lexicon_schema.py tests/test_canon_core_contract.py tests/test_ledger_schema.py tests/test_penny_meta.py tests/test_beta_scaffold.py
git commit -m "test(genre): repoint content-contract tests at the cozy fixture"
```

---

### Task 4: Repoint the config-copying gate tests to the fixture

**Files (modify):** `tests/test_readiness_check.py`, `tests/test_preflight.py`

Both build a tmp repo by copying the live `config/` + `canon-core`. After the cutover the live overrides are gone, so copy from the **fixture** instead.

- [ ] **Step 1: `test_readiness_check.py`** — `SRC = readiness_check.REPO` then `shutil.copytree(SRC / "config", tmp/"config")`. Change `SRC` to the fixture root: `SRC = Path(__file__).resolve().parent / "fixtures/cozy"`. Now `copytree(SRC/"config", ...)` copies the fixture's overrides, and the canon-core copy (`SRC/"series/continuity"`) comes from the fixture. **But** readiness also needs the engine's neutral config DEFAULTS (rubrics, line/copy-edit, self-audit, outline-template, beta-protocol) which are NOT in the fixture — so the tmp tree must ALSO include those. Simplest: copy the engine defaults first (`shutil.copytree(readiness_check.penny_paths.plugin_root()/"config", tmp/"config")`) then overlay the fixture's overrides on top. Implement whichever keeps every existing assertion passing; if the test asserts a specific override file's presence, ensure it's present.
- [ ] **Step 2: `test_preflight.py`** — `SRC = preflight.REPO`; it copies real run-config + canon-core into the tmp tree. Change the run-config/canon-core sources to the fixture (`Path(__file__).resolve().parent/"fixtures/cozy"`). The whodunit ledger it writes stays as-is (tmp-authored).
- [ ] **Step 3: Run these files + full suite; commit**

Run: `python3 -m pytest tests/test_readiness_check.py tests/test_preflight.py -v` (PASS), then `python3 -m pytest -q` (PASS).
```bash
git add tests/test_readiness_check.py tests/test_preflight.py
git commit -m "test(genre): repoint readiness/preflight fixtures at the cozy fixture + engine defaults"
```

---

### Task 5: Repoint the remaining engine-logic tests to the fixture

**Files (modify):** `tests/test_review_gate.py`, `tests/test_voice_drift.py`, `tests/test_scaffold.py`, `tests/test_scaffold_book_command.py`, `tests/test_fairplay_check.py`, `tests/test_lexicon_check.py`

These read specific live override files as input. Repoint each named reference to the fixture; leave references to engine-owned files (`commands/*.md`, `tests/fixtures/prose|ledgers|whodunit-repo`) unchanged.

- [ ] **Step 1: `test_review_gate.py`** — `CONFIG = Path("config/run-config.md")` → `Path(__file__).resolve().parent/"fixtures/cozy/config/run-config.md"`.
- [ ] **Step 2: `test_voice_drift.py`** — `DEFAULT_CONFIG = REPO/"config/voice-pack/ai-tics-config.yaml"` → the fixture's copy. (`FIX = REPO/"tests/fixtures/prose"` stays — that's an engine test fixture.)
- [ ] **Step 3: `test_scaffold.py`** — its expected-files list mixes engine files (`commands/draft-chapter.md` — stays) and cozy overrides/inputs (`config/run-config.md`, `input/series/whodunit-ledger.md` — repoint to fixture). Split the list: engine files checked at repo root; series/config-override files checked in the fixture.
- [ ] **Step 4: `test_scaffold_book_command.py`** — `RUN_CONFIG = Path("config/run-config.md")` → fixture copy; `CMD = Path("commands/scaffold-book.md")` stays (engine).
- [ ] **Step 5: `test_fairplay_check.py`** — `RUN_CONFIG = REPO/"config/run-config.md"` → fixture copy. (`LED`/`FIXTURE_REPO` under tests/fixtures stay.)
- [ ] **Step 6: `test_lexicon_check.py`** — the `--canon-core` argument path (live canon-core) → the fixture's canon-core.
- [ ] **Step 7: Run these files + full suite; commit**

Run: the six files `-v` (PASS), then `python3 -m pytest -q` (PASS).
```bash
git add tests/test_review_gate.py tests/test_voice_drift.py tests/test_scaffold.py tests/test_scaffold_book_command.py tests/test_fairplay_check.py tests/test_lexicon_check.py
git commit -m "test(genre): repoint remaining engine-logic tests at the cozy fixture"
```

---

### Task 6: Prove the suite passes with live cozy data hidden (decoupling gate)

**Files:** none (a verification task).

- [ ] **Step 1: Temporarily hide the live cozy data and run the full suite**

```bash
STASH=$(mktemp -d)
mv series input config/voice-pack config/setting-pack config/genre-pack config/length-profile.md config/run-config.md config/beta-readers/personas .penny series.yaml "$STASH"/ 2>/dev/null
python3 -m pytest -q; echo "EXIT=$?"
```
Expected: **all pass** (the decoupling is complete — no test depends on the live data). Record the pass count.

- [ ] **Step 2: Restore the live data (carefully — restore config overrides back UNDER config/)**

```bash
mv "$STASH"/series "$STASH"/input "$STASH"/.penny "$STASH"/series.yaml . 2>/dev/null
mv "$STASH"/voice-pack "$STASH"/setting-pack "$STASH"/genre-pack config/ 2>/dev/null
mv "$STASH"/length-profile.md "$STASH"/run-config.md config/ 2>/dev/null
mv "$STASH"/personas config/beta-readers/ 2>/dev/null
rmdir "$STASH" 2>/dev/null || echo "WARN: $STASH not empty — inspect"
python3 -m pytest -q   # Expected: PASS, back to full count
git status --short      # Expected: clean (nothing moved permanently)
```
(Note the earlier stash-restore footgun: config overrides live UNDER `config/`, so they must be restored into `config/`, not the repo root.)

- [ ] **Step 3: Commit the gate note**

No code change; append the "suite passes with live data hidden (N passed)" result to the branch's progress ledger. The branch is now ready: the real cutover (move to `~/myBooks/cozy-pelicans/`, git rm from engine) is the separate gated step, and it will pass because this task proved the suite is data-independent.

---

## Self-Review

**Spec coverage (Phase 3 decoupling slice):**
- Fixture cozy series + `cozy_fixture` → Task 1. ✓
- Move fair-play rubric/conventions into the genre pack → Task 2. ✓
- Repoint the ~47 data-dependent tests (all 14 files enumerated across Tasks 3–5) → Tasks 3, 4, 5. ✓
- Prove data-independence (the cutover's safety precondition) → Task 6. ✓
- **Deferred (correctly out of this plan):** the actual data cutover to `~/myBooks/cozy-pelicans/` (destructive, machine-touching — a separate gated step, unblocked by Task 6).

**Placeholder scan:** the fixture Step 1 says "adjust copies to whatever the contract tests read" — Tasks 3–5 enumerate every file, so the fixture's required contents are fully determined; not a TBD. Each repointing task names the exact current reference and its fixture replacement.

**Type/name consistency:** `cozy_fixture` (conftest) and the `FIX`/`fixtures/cozy` path are used consistently. The fixture path `tests/fixtures/cozy/` is identical across Tasks 1–6. The set of moving override files (run-config, voice-pack, setting-pack, genre-pack, length-profile, personas) matches between the fixture build (Task 1), the repointing tasks (3–5), and the hide/restore in Task 6.
