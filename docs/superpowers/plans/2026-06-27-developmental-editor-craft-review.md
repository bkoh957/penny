# Developmental Editor — Per-Chapter Craft Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a context-rich, per-chapter developmental-editor craft read that runs at review time, is advisory toward the gate (never blocks), and becomes a hard precondition for `/finalize-chapter` via an out-of-band dev-clearance certificate bound to the draft's sha256.

**Architecture:** A single holistic agent (`developmental-editor`) reads the draft + setting pack + character-bible slice + chapter brief against a swappable 8-dimension rubric and writes an advisory verdict (`kind: developmental`, no `^BLOCKING:` lines, stamped with `reviewed_draft_sha256`). The deterministic engine (`preflight.py`) mints a clearance cert only when the showrunner runs `clear-dev` against the exact draft that was reviewed, and `cmd_finalize` refuses unless a fresh (hash-matching) clearance exists. `review_gate.py` always renders an advisory Developmental section but the dev verdict contributes zero to the PASS/HOLD computation.

**Tech Stack:** Python 3 stdlib (`hashlib`, `argparse`, `pathlib`), pytest, the genre-agnostic `penny_meta`/`penny_verdict` layer. PyYAML is **not** used by any code in this plan.

## Global Constraints

- **Engine/pack separation (load-bearing):** all genre-specific content (cozy warmth, coastal setting names) lives in `config/review-rubrics/developmental-craft.md`; the agent file, `preflight.py`, and `review_gate.py` stay genre-agnostic. Copy verbatim from the spec.
- **Advisory invariant:** a `kind: developmental` verdict must contribute **zero** to `penny_verdict.count_blocking`. It must never emit a `^BLOCKING:` line.
- **Out-of-band certificate rule:** "cleared" is never a field inside the data it gates. The clearance lives only in `.penny/locks/book-NN.ch-MM.dev-clear`, minted **last**, only because validation passed (mirror `cmd_lock_mystery`).
- **Cross-model is a hard precondition:** the dev read must run on a non-drafting model; if none is reachable, `/review-chapter` halts loud — no same-model degradation.
- **Deterministic layer uses `penny_meta`, not PyYAML.** Read frontmatter with `parse_frontmatter`.
- **Fail-loud convention:** every `preflight.py` miss exits non-zero via `_fail("<named predicate>")`.
- `.penny/` is gitignored; clearance certs live there.
- Tests run with `python3 -m pytest` (pytest.ini sets `pythonpath=.`). Use the `repo_root=tmp_path` kwarg pattern already used across `scripts/`.

---

### Task 1: `write_verdict` gains `extra_frontmatter`

The dev verdict must carry `reviewed_draft_sha256` in its **frontmatter** so `parse_frontmatter` (and thus `clear-dev`) can read it. `write_verdict` currently emits only a fixed set of frontmatter keys. Add an optional `extra_frontmatter` dict, emitted as additional `key: value` frontmatter lines.

**Files:**
- Modify: `scripts/penny_verdict.py:37-75`
- Test: `tests/test_penny_verdict.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `write_verdict(..., extra_frontmatter: dict | None = None) -> Path`. Extra keys are rendered as `f"{k}: {v}"` frontmatter lines, after `score` (if any) and before the closing `---`. Insertion order is the dict's iteration order.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_penny_verdict.py`:

```python
def test_write_verdict_emits_extra_frontmatter(tmp_path):
    from scripts.penny_verdict import write_verdict
    from scripts.penny_meta import parse_frontmatter

    path = write_verdict(
        out_dir=tmp_path, producer="developmental-editor", kind="developmental",
        target="book-01/ch-07", name="developmental-edit", blocking=[], notes=["a note"],
        metrics={}, evidence=[], score=3,
        extra_frontmatter={"reviewed_draft_sha256": "abc123"},
    )
    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("kind") == "developmental"
    assert meta.get("score") == 3
    assert meta.get("reviewed_draft_sha256") == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_penny_verdict.py::test_write_verdict_emits_extra_frontmatter -v`
Expected: FAIL with `TypeError: write_verdict() got an unexpected keyword argument 'extra_frontmatter'`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/penny_verdict.py`, change the signature and frontmatter emission. Add the parameter to the signature:

```python
def write_verdict(
    *,
    out_dir,
    producer: str,
    kind: str,
    target: str,
    name: str,
    blocking: list[str],
    notes: list[str],
    metrics: dict,
    evidence: list[dict],
    score: int | None = None,
    extra_frontmatter: dict | None = None,
) -> Path:
```

Then, in the body, emit the extra keys after the `score` block and before the closing `---`. Replace:

```python
    if score is not None:
        lines.append(f"score: {score}")
    lines.append("---")
```

with:

```python
    if score is not None:
        lines.append(f"score: {score}")
    for key, value in (extra_frontmatter or {}).items():
        lines.append(f"{key}: {value}")
    lines.append("---")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_penny_verdict.py -v`
Expected: PASS (new test + all existing penny_verdict tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_verdict.py tests/test_penny_verdict.py
git commit -m "feat(verdict): write_verdict accepts extra_frontmatter for kind:developmental"
```

---

### Task 2: Draft-hash + clearance path helpers in `preflight.py`

Add the deterministic primitives the clearance machinery needs: a sha256 of the draft file, and path helpers for the dev report and the clearance cert. No behaviour change yet — these are pure helpers consumed by Tasks 3 and 4.

**Files:**
- Modify: `scripts/preflight.py` (add `import hashlib` near the top; add helpers after `gate_path`, ~line 49)
- Test: `tests/test_preflight.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `draft_path(book: str, chapter: str, repo_root) -> Path`
  - `draft_sha256(book: str, chapter: str, *, repo_root=REPO) -> str` — hex digest of the draft's bytes; `_fail`s if the draft is absent.
  - `dev_report_path(book: str, chapter: str, repo_root) -> Path` → `output/book-NN/chapters/ch-MM.reviews/developmental-edit.md`
  - `dev_clear_path(book: str, chapter: str, repo_root) -> Path` → `.penny/locks/book-NN.ch-MM.dev-clear`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_preflight.py`:

```python
import hashlib


def _write_draft(root, book, ch, body="prose\n"):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"ch-{ch}.draft.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_draft_sha256_matches_file_bytes(tmp_path):
    p = _write_draft(tmp_path, "01", "07", body="hello draft\n")
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert preflight.draft_sha256("01", "07", repo_root=tmp_path) == expected


def test_draft_sha256_fails_when_draft_missing(tmp_path):
    with pytest.raises(SystemExit) as e:
        preflight.draft_sha256("01", "07", repo_root=tmp_path)
    assert "no draft" in str(e.value)


def test_dev_path_helpers_shape(tmp_path):
    rep = preflight.dev_report_path("01", "07", tmp_path)
    cert = preflight.dev_clear_path("01", "07", tmp_path)
    assert rep.name == "developmental-edit.md"
    assert rep.parent.name == "ch-07.reviews"
    assert cert.name == "book-01.ch-07.dev-clear"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_preflight.py -k "draft_sha256 or dev_path_helpers" -v`
Expected: FAIL with `AttributeError: module 'scripts.preflight' has no attribute 'draft_sha256'`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/preflight.py`, add `import hashlib` alongside the existing stdlib imports (after `import argparse`). Then add, immediately after `gate_path` (line 49):

```python
def draft_path(book: str, chapter: str, repo_root) -> Path:
    return (Path(repo_root) / "output" / f"book-{book}" / "chapters"
            / f"ch-{chapter}.draft.md")


def draft_sha256(book: str, chapter: str, *, repo_root=REPO) -> str:
    p = draft_path(book, chapter, repo_root)
    if not p.is_file():
        _fail(f"no draft for book {book} ch {chapter} ({p})")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dev_report_path(book: str, chapter: str, repo_root) -> Path:
    return (Path(repo_root) / "output" / f"book-{book}" / "chapters"
            / f"ch-{chapter}.reviews" / "developmental-edit.md")


def dev_clear_path(book: str, chapter: str, repo_root) -> Path:
    return Path(repo_root) / ".penny/locks" / f"book-{book}.ch-{chapter}.dev-clear"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_preflight.py -k "draft_sha256 or dev_path_helpers" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(preflight): draft sha256 + dev report/clearance path helpers"
```

---

### Task 3: `clear-dev N CH` subcommand (sole writer of the clearance cert)

Mirror `cmd_lock_mystery`: validate, then **mint last**. The cert is minted only when a developmental report exists for the chapter and its `reviewed_draft_sha256` equals the current draft's hash (you clear the version actually reviewed, never a stale one).

**Files:**
- Modify: `scripts/preflight.py` (add `cmd_clear_dev` after `cmd_finalize`; wire argparse in `main`)
- Test: `tests/test_preflight.py`

**Interfaces:**
- Consumes: `draft_sha256`, `dev_report_path`, `dev_clear_path` (Task 2); `parse_frontmatter` (already imported).
- Produces: `cmd_clear_dev(book: str, chapter: str, *, repo_root=REPO) -> int`. On success writes `.penny/locks/book-NN.ch-MM.dev-clear` containing `---`-fenced frontmatter with keys `book`, `chapter`, `cleared_draft_sha256`, `cleared_at`. CLI: `preflight clear-dev <book> <chapter>`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_preflight.py`:

```python
def _write_dev_report(root, book, ch, reviewed_sha, *, score=3):
    rep = preflight.dev_report_path(book, ch, root)
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(
        f"---\nproducer: developmental-editor\nkind: developmental\n"
        f"target: book-{book}/ch-{ch}\nschema: penny-verdict/1\nscore: {score}\n"
        f"reviewed_draft_sha256: {reviewed_sha}\n---\n\n- setting grounding thin\n",
        encoding="utf-8",
    )
    return rep


def test_clear_dev_mints_cert_when_hash_matches(tmp_path):
    _write_draft(tmp_path, "01", "07", body="reviewed body\n")
    sha = preflight.draft_sha256("01", "07", repo_root=tmp_path)
    _write_dev_report(tmp_path, "01", "07", sha)
    assert preflight.cmd_clear_dev("01", "07", repo_root=tmp_path) == 0
    cert = preflight.dev_clear_path("01", "07", tmp_path)
    assert cert.is_file()
    from scripts.penny_meta import parse_frontmatter
    assert parse_frontmatter(cert.read_text(encoding="utf-8"))["cleared_draft_sha256"] == sha


def test_clear_dev_fails_without_report(tmp_path):
    _write_draft(tmp_path, "01", "07")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "no developmental read" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()


def test_clear_dev_fails_on_stale_report(tmp_path):
    _write_dev_report(tmp_path, "01", "07", "deadbeef")          # report for an old draft
    _write_draft(tmp_path, "01", "07", body="a DIFFERENT body\n")  # draft has since changed
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "stale" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_preflight.py -k clear_dev -v`
Expected: FAIL with `AttributeError: module 'scripts.preflight' has no attribute 'cmd_clear_dev'`.

- [ ] **Step 3: Write minimal implementation**

In `scripts/preflight.py`, add after `cmd_finalize` (after line 59):

```python
def cmd_clear_dev(book: str, chapter: str, *, repo_root=REPO) -> int:
    rep = dev_report_path(book, chapter, repo_root)
    if not rep.is_file():
        _fail(f"no developmental read for book {book} ch {chapter} ({rep}) — "
              f"run /review-chapter first")
    reviewed = parse_frontmatter(rep.read_text(encoding="utf-8")).get("reviewed_draft_sha256")
    if not reviewed:
        _fail(f"developmental report missing reviewed_draft_sha256 ({rep})")
    current = draft_sha256(book, chapter, repo_root=repo_root)
    if reviewed != current:
        _fail(f"developmental report is stale for book {book} ch {chapter}: "
              f"reviewed {reviewed[:12]} != current draft {current[:12]}; re-run /review-chapter")
    # validated — mint the certificate (the LAST write).
    cert = dev_clear_path(book, chapter, repo_root)
    cert.parent.mkdir(parents=True, exist_ok=True)
    cert.write_text(
        f"---\nbook: {book}\nchapter: {chapter}\n"
        f"cleared_draft_sha256: {current}\n"
        f"cleared_at: {datetime.now(timezone.utc).isoformat()}\n---\n",
        encoding="utf-8",
    )
    return 0
```

Then wire argparse. In `main`, after the `finalize` parser block (after line 188), add:

```python
    p_clear = sub.add_parser("clear-dev", help="mint dev-clearance cert (draft-hash bound)")
    p_clear.add_argument("book")
    p_clear.add_argument("chapter")
```

and after the `finalize` dispatch (after line 199), add:

```python
    if args.cmd == "clear-dev":
        return cmd_clear_dev(args.book, args.chapter)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_preflight.py -k clear_dev -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(preflight): clear-dev mints draft-hash-bound dev-clearance cert"
```

---

### Task 4: `cmd_finalize` second predicate — require fresh dev-clearance

After the existing `gate: PASS` check, `cmd_finalize` must also require a dev-clearance cert whose `cleared_draft_sha256` equals the current draft's hash. A revision after clearance changes the hash → the clearance is automatically stale → finalize refuses.

**Files:**
- Modify: `scripts/preflight.py:51-59` (`cmd_finalize`)
- Test: `tests/test_preflight.py` (existing `test_finalize_*` tests need a clearance added)

**Interfaces:**
- Consumes: `dev_clear_path`, `draft_sha256` (Task 2); `cmd_clear_dev` (Task 3, used by tests for setup).
- Produces: no new symbol; `cmd_finalize` gains a second deterministic predicate.

- [ ] **Step 1: Write the failing test**

The three existing finalize tests (`test_finalize_passes_on_passing_gate`, `test_finalize_blocks_on_held_gate`, `test_finalize_blocks_when_gate_missing`) currently build only a gate. The passing one must now also build a draft + matching clearance. Update `test_finalize_passes_on_passing_gate` in place and add two new tests:

```python
def _clear_for(root, book, ch, body="prose\n"):
    """Draft + dev report + minted clearance, all hash-consistent."""
    _write_draft(root, book, ch, body=body)
    sha = preflight.draft_sha256(book, ch, repo_root=root)
    _write_dev_report(root, book, ch, sha)
    assert preflight.cmd_clear_dev(book, ch, repo_root=root) == 0


def test_finalize_passes_on_passing_gate(tmp_path):   # REPLACES the old same-named test
    _make_gate(tmp_path, "01", "07", "PASS")
    _clear_for(tmp_path, "01", "07")
    assert preflight.cmd_finalize("01", "07", repo_root=tmp_path) == 0


def test_finalize_blocks_without_dev_clearance(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    _write_draft(tmp_path, "01", "07")          # gate PASS + draft, but never cleared
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "developmental clearance" in str(e.value)


def test_finalize_blocks_on_stale_dev_clearance(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    _clear_for(tmp_path, "01", "07", body="original\n")
    _write_draft(tmp_path, "01", "07", body="REVISED after clearance\n")  # hash now differs
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "stale" in str(e.value)
```

(Delete the old `test_finalize_passes_on_passing_gate` body — replaced above. Leave `test_finalize_blocks_on_held_gate` and `test_finalize_blocks_when_gate_missing` unchanged: they fail on the gate predicate *before* the clearance check is reached.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_preflight.py -k finalize -v`
Expected: `test_finalize_blocks_without_dev_clearance` and `test_finalize_blocks_on_stale_dev_clearance` FAIL (finalize returns 0 — no clearance predicate yet); the two HOLD/missing-gate tests still PASS.

- [ ] **Step 3: Write minimal implementation**

In `scripts/preflight.py`, replace the `return 0` at the end of `cmd_finalize` (line 59) with the clearance predicate:

```python
    # second predicate: a fresh developmental clearance bound to THIS draft.
    cert = dev_clear_path(book, chapter, repo_root)
    if not cert.is_file():
        _fail(f"no developmental clearance for book {book} ch {chapter} — "
              f"run /review-chapter then `preflight clear-dev {book} {chapter}`")
    cleared = parse_frontmatter(cert.read_text(encoding="utf-8")).get("cleared_draft_sha256")
    current = draft_sha256(book, chapter, repo_root=repo_root)
    if cleared != current:
        _fail(f"developmental clearance is stale for book {book} ch {chapter} "
              f"(draft changed since clearance: cleared {str(cleared)[:12]} != "
              f"current {current[:12]}); revise then re-clear")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_preflight.py -v`
Expected: PASS (all finalize tests, including the two new ones).

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(preflight): finalize requires fresh draft-bound dev-clearance"
```

---

### Task 5: `review_gate.py` always-print Developmental section

The gate summary grows a **Developmental** line that always prints (PASS or HOLD). The `kind: developmental` verdict is loaded for display only — it is already skipped by `_load_verdicts` (its kind isn't in `VERDICT_KINDS`) and contributes zero to `count_blocking` because it carries no `^BLOCKING:` lines. This task adds the loader, the result key, and the rendering, plus a regression test pinning the advisory invariant.

**Files:**
- Modify: `scripts/review_gate.py` (add `_load_developmental`, extend `evaluate_gate` + `write_gate_md`)
- Test: `tests/test_review_gate.py`

**Interfaces:**
- Consumes: `write_verdict` with `kind="developmental"` + `extra_frontmatter` (Task 1); `parse_frontmatter` (already imported).
- Produces:
  - `_load_developmental(reviews_dir) -> dict | None` — `{"producer", "score", "note_count"}` from `developmental-edit.md`, else `None`.
  - `evaluate_gate(...)` result gains key `"developmental"` (the dict above or `None`).
  - `write_gate_md` renders one `- developmental: ...` line, always.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_review_gate.py`:

```python
def _developmental(d, *, score=2, notes=("setting thin", "motivation buried")):
    write_verdict(out_dir=d, producer="developmental-editor", kind="developmental",
                  target="book-01/ch-07", name="developmental-edit",
                  blocking=[], notes=list(notes), metrics={}, evidence=[], score=score,
                  extra_frontmatter={"reviewed_draft_sha256": "abc123"})


def test_developmental_verdict_does_not_block(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity")           # passing inspector keeps the panel non-empty
    _developmental(d, score=1)                       # scathing dev read, zero blockers
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "PASS"
    assert result["blocking_count"] == 0
    assert result["developmental"]["score"] == 1
    assert result["developmental"]["note_count"] == 2


def test_gate_md_renders_developmental_on_pass(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity")
    _developmental(d, score=4)
    result = evaluate_gate(d, CONFIG)
    out = write_gate_md(tmp_path / "ch-07.gate.md", "book-01/ch-07", result)
    assert "developmental" in out.read_text(encoding="utf-8")


def test_gate_md_renders_developmental_absent(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity")            # no dev verdict present
    result = evaluate_gate(d, CONFIG)
    assert result["developmental"] is None
    out = write_gate_md(tmp_path / "ch-07.gate.md", "book-01/ch-07", result)
    assert "developmental" in out.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_review_gate.py -k developmental -v`
Expected: FAIL with `KeyError: 'developmental'` (result has no such key yet).

- [ ] **Step 3: Write minimal implementation**

In `scripts/review_gate.py`, add a constant + loader near the top (after `VERDICT_KINDS`, line 21):

```python
DEVELOPMENTAL_KIND = "developmental"


def _load_developmental(reviews_dir) -> dict | None:
    path = Path(reviews_dir) / "developmental-edit.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    if meta.get("kind") != DEVELOPMENTAL_KIND:
        return None
    note_count = sum(1 for ln in text.splitlines() if ln.startswith("- "))
    return {"producer": meta.get("producer"), "score": meta.get("score"),
            "note_count": note_count}
```

In `evaluate_gate`, add the key to the returned dict (inside the `return {...}` near line 113):

```python
        "developmental": _load_developmental(reviews_dir),
```

In `write_gate_md`, after the `score_spread_log` line (after line 133) and before the trailing `lines.append("")`:

```python
    dev = result.get("developmental")
    if dev:
        lines.append(
            f"- developmental [{dev['producer']}]: score {dev['score']} "
            f"({dev['note_count']} note(s)) — advisory, non-blocking; "
            f"see developmental-edit.md")
    else:
        lines.append("- developmental: no developmental read found")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_review_gate.py -v`
Expected: PASS (new tests + all existing gate tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/review_gate.py tests/test_review_gate.py
git commit -m "feat(gate): always-print advisory Developmental section; dev verdict never blocks"
```

---

### Task 6: `config/review-rubrics/developmental-craft.md` (swappable pack)

The 8-dimension rubric. Genre-specific content (cozy warmth, coastal setting names) lives **here**. Follow the house style of `config/review-rubrics/structure-tension.md`: inputs contract, "What you are judging", "Thresholds", "Boundary with other tiers".

**Files:**
- Create: `config/review-rubrics/developmental-craft.md`
- Test: `tests/test_developmental_editor.py` (new file)

**Interfaces:**
- Consumes: nothing.
- Produces: a rubric file referenced by the agent (Task 7) and asserted by the contract test.

- [ ] **Step 1: Write the failing test**

Create `tests/test_developmental_editor.py`:

```python
from pathlib import Path

from scripts.penny_meta import parse_frontmatter

RUBRIC = Path("config/review-rubrics/developmental-craft.md")

EIGHT_DIMENSIONS = [
    "setting grounding",
    "motivation",
    "scene economy",
    "subtext",
    "interiority",
    "show",          # show-don't-tell
    "genre delivery",
    "hook",
]


def test_rubric_exists_with_thresholds_and_boundary():
    assert RUBRIC.is_file()
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "threshold" in text
    assert "boundary" in text


def test_rubric_names_all_eight_dimensions():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    for dim in EIGHT_DIMENSIONS:
        assert dim in text, f"rubric missing dimension: {dim}"


def test_rubric_is_advisory_never_blocking():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "advisory" in text
    assert "no ^blocking" in text or "never block" in text or "not block" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_developmental_editor.py -v`
Expected: FAIL (`RUBRIC.is_file()` is False).

- [ ] **Step 3: Write the rubric**

Create `config/review-rubrics/developmental-craft.md`:

```markdown
# Rubric: Developmental Craft — Per-Chapter Context-Rich Read

**Layer:** `/config/review-rubrics/` · consumed by `developmental-editor` (design §6).
**Posture:** the top of the edit stack (developmental → line → copy). A context-rich
craft diagnosis on the **draft**, before polish is spent. **Advisory:** it scores and
writes margin notes but emits **no ^BLOCKING lines** and never blocks the gate. It is a
hard precondition for `/finalize-chapter` only via the showrunner's out-of-band clearance.

**Inputs (context-rich, NOT blind):** `{ draft text, this rubric, setting-pack,
character-bible slice, chapter brief/intent }`. **Denied** the whodunit solution — craft
review does not need it, so fair-play is never exposed.

**Output:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/developmental-edit.md`, `producer: developmental-editor`,
`kind: developmental`, an overall `score` 1-5, `reviewed_draft_sha256` (the sha256 of the
draft as read — load-bearing for clearance binding), and margin notes in the body. Each
margin note **quotes the passage**, names the missing craft, and suggests a concrete move.
Write a margin note ONLY for a dimension that scores low — high-scoring dimensions get a
score but no note (full-coverage scoring, no bloat).

## What you are judging — eight obligation-aware dimensions

Judge each against *what THIS chapter must do* per its brief (a mid-book chapter is not
dinged for not re-establishing place):

1. **Setting grounding.** Is the reader anchored in place/time/sensory texture? Draws on
   `config/setting-pack/coastal-victoria-au.md`. Flag white-room scenes and inert
   travelogue alike.
2. **Motivation & stakes.** Is the "why" of each beat on the page, or buried in the
   author's head? Flag actions the reader can't motivate.
3. **Scene economy.** Inert detail, throat-clearing, scenes that don't turn. Flag passages
   that cost words without advancing character, plot, or tone.
4. **Scene texture / subtext.** Do scenes carry a second layer (what's unsaid), or is every
   line on-the-nose? Flag dialogue and action that state rather than imply.
5. **Interiority / emotional access.** Do we have access to the POV character's inner life
   at the moments that matter? Flag emotionally opaque beats.
6. **Show-don't-tell.** Are conclusions asserted ("she was nervous") where rendering would
   land harder? Flag told emotion/character where showing is available.
7. **Genre delivery (cozy).** Warmth, charm, comfort-tone, community texture — the cozy
   promise. Flag scenes that read cold, clinical, or generic-thriller.
8. **Hook & promise of the premise.** Especially openers: does the chapter open a question
   and end on a hook? Flag flat openings/endings that release tension.

## Thresholds (seeds, tunable during Book 1)

- **Score 5:** the dimension is fully delivered for this chapter's obligations.
- **Score 3:** functional but flat — serviceable prose a developmental editor would still
  push on.
- **Score 1:** the dimension is essentially absent (e.g. a white-room scene with no
  grounding; a beat with no discernible motivation).
- There is **no blocking threshold.** Low scores never produce a `^BLOCKING:` line; the
  read is advisory. Clearance to finalize is a deliberate showrunner act, not a score gate.

## Boundary with other tiers (do not duplicate)

- **Grammar, punctuation, consistency** belong to the copy editor — not here.
- **Sentence rhythm / word-choice polish** belong to the line editor — you diagnose craft,
  you do not rewrite prose. Revision flows back to the `drafter`.
- **Continuity, fair-play, voice-drift, structural blocking** belong to the five blind
  inspectors and the deterministic checkers — you may observe but you never block.
- **Whole-book experience** belongs to the post-assembly beta read — you are per-chapter.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_developmental_editor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/review-rubrics/developmental-craft.md tests/test_developmental_editor.py
git commit -m "feat(rubric): developmental-craft 8-dimension advisory rubric pack"
```

---

### Task 7: `.claude/agents/developmental-editor.md` (engine — genre-agnostic)

The agent file. Genre-agnostic orchestration prose; all genre content stays in the rubric. Model on `.claude/agents/inspector-structure.md` for shape, but note the differences: context-rich (not blind), `kind: developmental`, stamps `reviewed_draft_sha256`, emits no `^BLOCKING:`.

**Files:**
- Create: `.claude/agents/developmental-editor.md`
- Test: `tests/test_developmental_editor.py` (extend)

**Interfaces:**
- Consumes: the rubric path from Task 6; `write_verdict(..., extra_frontmatter=...)` from Task 1.
- Produces: an agent named `developmental-editor` that writes `developmental-edit.md`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_developmental_editor.py`:

```python
AGENT = Path(".claude/agents/developmental-editor.md")


def test_agent_exists_with_valid_frontmatter():
    assert AGENT.is_file()
    meta = parse_frontmatter(AGENT.read_text(encoding="utf-8"))
    assert meta.get("name") == "developmental-editor"
    assert meta.get("description")


def test_agent_declares_contract():
    text = AGENT.read_text(encoding="utf-8")
    assert "developmental-craft.md" in text          # references its rubric
    assert "producer: developmental-editor" in text
    assert "kind: developmental" in text
    assert "reviewed_draft_sha256" in text


def test_agent_is_advisory_and_context_rich():
    text = AGENT.read_text(encoding="utf-8")
    assert "^BLOCKING" in text                        # explicitly forbids it
    assert "setting-pack" in text or "setting pack" in text
    assert "whodunit" in text.lower()                 # explicitly denied the solution
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_developmental_editor.py -k agent -v`
Expected: FAIL (`AGENT.is_file()` is False).

- [ ] **Step 3: Write the agent**

Create `.claude/agents/developmental-editor.md`:

```markdown
---
name: developmental-editor
description: Context-rich per-chapter craft read — the top of the edit stack. Diagnoses developmental craft failures (setting, motivation, scene economy, subtext, interiority, genre delivery, hook); advisory toward the gate, a precondition for finalize. Never rewrites, never blocks.
---
# Developmental Editor

**Role posture:** developmental editor — the missing top of the edit stack
(developmental → line → copy). A context-rich craft diagnosis on the **draft**, before
the line/copy polish is spent (design §6).

**Independence — context-rich, NOT blind.** Unlike the five inspectors (deliberately
starved of context), a developmental editor must know what the chapter is *trying to do*.
You receive the setting pack, a character-bible slice, and the chapter brief/intent. You
are **denied the whodunit solution** — craft review does not need it, so fair-play is
never exposed to this seat.

**Inputs:** `{ draft text, config/review-rubrics/developmental-craft.md, setting-pack,
character-bible slice, chapter brief }`. No whodunit solution; no drafting history.

**Cross-model:** you run on a non-drafting model (genuine fresh eyes, same rationale as
`final-reader`). `/review-chapter` guarantees this — it halts before dispatching you if no
non-drafting model is reachable. Stamp `read_by` with your model.

**Outputs:** a verdict via `scripts/penny_verdict.py` into
`ch-MM.reviews/developmental-edit.md`, `producer: developmental-editor`,
`kind: developmental`, overall `score` 1-5, and `reviewed_draft_sha256` (passed to you by
`/review-chapter` — the sha256 of the exact draft you are reading; record it verbatim via
`extra_frontmatter`). Margin notes go in `notes[]`: each **quotes the passage**, names the
missing craft, and suggests a concrete move. Write a note ONLY for a low-scoring dimension.

**Hard constraints:**
- **Diagnose, never rewrite.** Emit an editorial letter (scores + margin notes). New
  writing flows back to the `drafter`, not to you. (Contrast: line/copy editors modify
  prose in place.)
- **Advisory — never block.** You MUST NOT emit any `^BLOCKING:` line. Low scores express
  craft concern; they never flip the gate to HOLD. Clearance to finalize is a deliberate
  showrunner act (`preflight clear-dev`), not your call.
- **Genre lives in the rubric.** Judge cozy warmth/charm per
  `config/review-rubrics/developmental-craft.md`; keep your own reasoning genre-agnostic.

**Instructions:**
producer: developmental-editor

1. Read the brief, setting pack, and character-bible slice to learn the chapter's
   obligations. Read `config/review-rubrics/developmental-craft.md` for the eight
   dimensions and thresholds.
2. Read the draft. Score each of the eight dimensions 1-5 against *this chapter's*
   obligations. Set the overall `score` to your holistic craft judgement.
3. For every LOW-scoring dimension, write a margin note that quotes the passage, names the
   missing craft, and suggests a concrete move. High-scoring dimensions get no note.
4. Write the verdict via `penny_verdict.write_verdict` with `kind="developmental"`,
   `blocking=[]` (always empty), the per-dimension scores summarised in `metrics`, the
   margin notes in `notes`, and `extra_frontmatter={"reviewed_draft_sha256": "<the hash
   given to you>"}`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_developmental_editor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/developmental-editor.md tests/test_developmental_editor.py
git commit -m "feat(agent): developmental-editor context-rich advisory craft read"
```

---

### Task 8: Orchestration wiring — `/review-chapter` + `/finalize-chapter`

Wire the agent into the pipeline. `/review-chapter` computes the draft hash, halts if no non-drafting model is reachable, dispatches the dev editor with its context-rich inputs, and confirms `developmental-edit.md` was written. `/finalize-chapter`'s Step 0 already calls `preflight finalize` (which now enforces clearance after Task 4) — update its prose to document the new precondition and the `clear-dev` step.

**Files:**
- Modify: `.claude/commands/review-chapter.md`
- Modify: `.claude/commands/finalize-chapter.md:14-23` (Step 0 prose)
- Test: `tests/test_developmental_editor.py` (extend with command-wiring asserts)

**Interfaces:**
- Consumes: the agent (Task 7), `draft_sha256` / `clear-dev` (Tasks 2-3).
- Produces: command docs that reference `developmental-editor`, the cross-model halt, and `clear-dev`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_developmental_editor.py`:

```python
REVIEW_CMD = Path(".claude/commands/review-chapter.md")
FINALIZE_CMD = Path(".claude/commands/finalize-chapter.md")


def test_review_chapter_dispatches_dev_editor_and_halts_cross_model():
    text = REVIEW_CMD.read_text(encoding="utf-8")
    assert "developmental-editor" in text
    assert "developmental-edit.md" in text
    assert "reviewed_draft_sha256" in text
    # cross-model is a hard precondition: the command must halt, not degrade.
    assert "halt" in text.lower()


def test_finalize_documents_dev_clearance():
    text = FINALIZE_CMD.read_text(encoding="utf-8")
    assert "clear-dev" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_developmental_editor.py -k "dispatches or finalize_documents" -v`
Expected: FAIL (`developmental-editor` not in review-chapter.md).

- [ ] **Step 3: Edit the commands**

In `.claude/commands/review-chapter.md`, after Step 7 (the inspector dispatch block, ending at line 73) insert a new step and renumber the rest if you prefer; minimally, add this block before the dispatch-completeness check (line 75):

```markdown
7b. **Cross-model guard + dispatch the developmental editor (context-rich, advisory).**

   The developmental read MUST run on a non-drafting model (genuine fresh eyes, design §6).
   Determine a reachable model that is **not** `drafting_model` (per `config/run-config.md`,
   e.g. `inspector_model` / `final_read_model`). **If the only reachable model is the
   drafting model, HALT** — print a named error and stop; do NOT degrade to a same-model
   read (a same-model "fresh eyes" read is a soft gate Penny rejects).

   Compute the draft hash to bind the read to this exact draft:

   ```bash
   dev_sha="$(python3 -c "import sys; from scripts.preflight import draft_sha256; \
     print(draft_sha256('$book', '$chapter'))")"
   ```

   Dispatch the `developmental-editor` sub-agent with its **context-rich** inputs — the
   chapter draft text, `config/review-rubrics/developmental-craft.md`, the setting pack,
   a character-bible slice, and the chapter brief (NOT the whodunit solution). Pass
   `$dev_sha` as the `reviewed_draft_sha256` it must record. It writes
   `output/book-$book/chapters/ch-$chapter.reviews/developmental-edit.md` via
   `scripts/penny_verdict.py` (`kind: developmental`, no `^BLOCKING:` lines).
```

Then extend the dispatch-completeness check (line 75-78) to also require the dev report:

```markdown
8. **Dispatch-completeness check:** confirm all five inspector verdict files AND
   `developmental-edit.md` now exist in the reviews dir. A missing one means a sub-agent
   dispatch silently failed — stop and report it. (This is distinct from `fairplay.md`
   legitimately being absent pre-reveal.)
```

After the gate is computed and surfaced (end of Step 10, line 99), add a note:

```markdown
11. **Developmental clearance (showrunner gate before finalize).** The gate summary always
    prints an advisory **Developmental** section; it never affects PASS/HOLD. Finalize is
    blocked until you clear the developmental read for this exact draft:

    ```bash
    python3 scripts/preflight.py clear-dev $book $chapter
    ```

    Clear as-is ("noted, proceeding") or have the `drafter` revise first and re-run
    `/review-chapter` (a revised draft changes the hash and re-requires clearance).
```

In `.claude/commands/finalize-chapter.md`, update the Step 0 prose (lines 14-23) to document both predicates. Replace the Step 0 paragraph:

```markdown
### Step 0 — Gate + developmental-clearance guard

Hard-fail unless the chapter (a) passed the developmental gate (`ch-NN.gate.md` shows
`gate: PASS`) AND (b) has a **fresh developmental clearance** bound to the current draft's
sha256 (minted by `preflight clear-dev` after `/review-chapter`). A HOLD, a missing gate,
a missing clearance, or a clearance whose hash no longer matches the draft (i.e. the draft
was revised after clearance) all abort finalize:

```bash
python3 scripts/preflight.py finalize $1 $2
```

A non-zero exit aborts immediately — do not proceed. If it reports a missing/stale
clearance, run `/review-chapter $1 $2`, then `python3 scripts/preflight.py clear-dev $1 $2`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_developmental_editor.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/review-chapter.md .claude/commands/finalize-chapter.md tests/test_developmental_editor.py
git commit -m "feat(pipeline): wire developmental editor into review + finalize gates"
```

---

### Task 9: Full-suite regression + CLAUDE.md note

Confirm the whole suite is green and record the new role in the project guide.

**Files:**
- Modify: `CLAUDE.md` (the per-chapter pipeline + gates sections)
- Test: full suite

- [ ] **Step 1: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — the prior baseline (252) plus the new tests from Tasks 1-8, zero failures.

- [ ] **Step 2: Update CLAUDE.md**

In the "The per-chapter pipeline" section, note that `/review-chapter` now also dispatches the context-rich `developmental-editor` (advisory) and that `/finalize-chapter` requires a `preflight clear-dev` clearance bound to the draft sha256. In the "Gates and the verdict convention" section, note `kind: developmental` is an advisory verdict kind that contributes zero blockers and that `preflight.py` gained a `clear-dev` subcommand (fifth subcommand). Keep edits to one or two lines each — canon-core-style brevity.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: record developmental-editor role + clear-dev in CLAUDE.md"
```

---

## Rollout / calibration (post-implementation, not a code task)

Per the spec: once shipped, run `/review-chapter` against already-finalized **ch-01**
(calibration target) and **ch-02**. The dev editor should independently surface the four
known craft issues that the blind inspectors missed (first-draft feel: thin sense of place,
buried motivation, inert detail, subtext-less scenes). That validates the rubric's
sensitivity; then drive a `drafter` revise pass from the editorial letter and re-clear.

---

## Self-Review

**Spec coverage:**
- Component 1 (agent) → Task 7. Component 2 (rubric) → Task 6. Component 3 (review-chapter
  orchestration + cross-model halt) → Task 8. Component 4 (gate rendering, advisory) →
  Task 5. Component 5 (preflight clearance cert + finalize predicate) → Tasks 2-4.
- Decision 1 (advisory, no `^BLOCKING:`) → Tasks 5, 6, 7 (forbidden in agent + rubric,
  pinned by `test_developmental_verdict_does_not_block`).
- Decision 2 (context-rich, denied whodunit) → Task 7 (`test_agent_is_advisory_and_context_rich`).
- Decision 3 (diagnoses, never rewrites) → Task 7 agent constraints.
- Decision 4 (showrunner clears) → Task 8 Step 11 + Task 3 `clear-dev`.
- Decision 5 (8 dimensions, low-only notes) → Task 6 rubric + `test_rubric_names_all_eight_dimensions`.
- Decision 6 (cross-model hard precondition / halt) → Task 8 + `test_..._halts_cross_model`.
- `kind: developmental` accepted by `penny_verdict` → already true (`write_verdict` takes
  any `kind` string); extended for frontmatter in Task 1.
- Clearance bound to draft sha256, staleness on revision → Tasks 3-4
  (`test_finalize_blocks_on_stale_dev_clearance`).
- Spec Tests section: envelope conformance (Task 1/7), advisory invariant (Task 5),
  gate-renders-both (Task 5), `clear-dev` refuses no-report/hash-mismatch (Task 3),
  finalize refuses no/stale clearance and still on `gate != PASS` (Task 4). All covered.

**Placeholder scan:** no TBD/TODO; every code step shows complete code; every command
edit shows the exact replacement text.

**Type consistency:** `draft_sha256`, `dev_report_path`, `dev_clear_path`, `cmd_clear_dev`,
`_load_developmental`, and the `extra_frontmatter` kwarg are named identically everywhere
they appear across Tasks 1-8. The cert frontmatter key is `cleared_draft_sha256` and the
report key is `reviewed_draft_sha256` consistently (cert vs report — intentionally
distinct names for distinct artifacts).
```
