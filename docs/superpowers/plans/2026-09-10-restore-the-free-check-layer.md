# Restore the Free Check Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the deterministic checks that cost nothing actually run — a book-number form of `tension_check` that resolves the same four inputs the lock does, a deterministic completeness gate so a silently-skipped checker is a stop, and an honest retirement of the one inspector half that has never had data.

**Architecture:** Three independent pieces. Task 1 extracts the four-input resolution `preflight lock-mystery` already performs and gives `tension_check.py` a book-number CLI over it, so a showrunner's report and the lock's gate cannot disagree about what ran. Task 2 removes `inspector-structure`'s thread-liveness half across the four live surfaces that declare it, and renumbers the runbook. Task 3 replaces the runbook's prose completeness check with a script, extended to the two evidence checkers.

**Spec:** `docs/superpowers/specs/2026-09-09-check-economics-design.md` §3a. (§3b shipped; §3c stays deferred.)

## Why these three

Measured on the live series, before this plan:

- `tension_check`'s **ten findings have never run**. The lock certificate reads `validated: fairplay+lexicon`. The guardrail-heading fix (`0e66a57`) removed the cause, but nothing yet gives the showrunner a way to *read* the findings before they gate.
- `voice_drift.py` and `lexicon_check.py` ran in **1 of 12** review rounds. Both are free. `inspector-voice` — which exists to weigh their evidence — recorded "No voice_drift.py evidence was supplied for this round" and made the blocking call blind, at ~22k tokens, eleven times.
- `inspector-structure`'s dormancy flag has **never had data**: `series/continuity/threads/` does not exist, `ledger_markers.py` only *updates* thread files and never creates one, and `arc-ledger.md` is an empty table. The genre's four tracks (M/P/R/B with `max_dark_gap`) already cover the same failure at book scale through `starved-thread`, which does work.

## Global Constraints

- **No named finding is added or removed.** Rosters stay fixed: `story_cut.py` twenty-three, `tension_check.py` ten, `map_check.py` seven, `background_cut.py` eight blocking + two advisories. This plan adds no `--waive` handle.
- **Deterministic layer is stdlib-only.** `scripts/` takes no PyYAML for config/frontmatter — use `scripts/penny_meta.py`. (`tension_check.py` already uses PyYAML for the beat sheet and whodunit ledger, which is the sanctioned nested-data exception; do not widen it.)
- **`tension_check` stays read-only.** It writes nothing and mints nothing. Only `preflight.py` writes a lock.
- **`CLAUDE.md:52`'s `full suite (N tests)` line must equal the real collected count** — `tests/test_texture_allocation_docs.py:118` re-collects and asserts it, so a test-adding commit that leaves it turns the suite red by construction. Move it in the same commit, to the **measured** count. Baseline: **1354 passed**.
- **Runbook edits:** read CLAUDE.md's "Runbook arguments" section first. `commands/*.md` render with argument substitution applied **including inside fenced code blocks**. **Never write a bare `$` before a digit** — `tests/test_runbook_arguments.py` fails the build on one. A runbook edit needs a session restart to take effect.
- **Do not modify anything under `~/myBooks/`** — the author's manuscript data, a separate repo.
- **Do not implement §3c** — no change to which inspectors run, and the developmental-editor stays unconditional.
- **Commit per task, on `main`. Do not push** — the operator pushes at phase end.

---

### Task 1: `tension_check.py NN` — the report the lock will agree with

`tension_check.py` takes an outline **path**. `preflight lock-mystery` resolves four inputs for it: the outline, the genre's beat sheet (through `penny_genre.beat_sheet`, never a hardcoded filename), the turning points, and the whodunit ledger. Given a bare path and nothing else, `beat_sheet_path` is `None` and **five of the ten checks silently do not run** — `dead-stretch`, `starved-thread`, `off-mark-beat`, `overloaded-chapter`, `monotonous-closings` — leaving only a note. A showrunner running the checker directly therefore gets half a report and no signal that it is half.

The cure is one resolution, called from both places. Two copies would let the report and the gate disagree about what was checked, which is worse than no report.

**Files:**
- Modify: `scripts/tension_check.py` — add the resolver + book-number CLI form
- Modify: `scripts/preflight.py:316-334` — call the resolver instead of resolving inline
- Test: `tests/test_tension_check.py`

**Interfaces:**
- Produces: `resolve_inputs(book: str, repo_root=None) -> dict` in `scripts/tension_check.py`, returning `{"outline": Path|None, "beat_sheet_path": Path|None, "turning_points_path": Path|None, "whodunit_path": Path|None}`. The last three are named exactly as `check_tension`'s keyword arguments so a caller can splat them; `outline` is separate because `check_tension` takes it positionally as `outline_path`. Callers do `check_tension(got["outline"], **{k: v for k, v in got.items() if k != "outline"})` or the explicit equivalent — whichever reads better in each call site. A path that does not exist resolves to `None`, never to a non-existent `Path` — `config_path()` always returns *some* path, so the beat sheet must be normalised the way `preflight.py:328-333` already does or the "could not run" note never fires.
- Produces: CLI `python3 scripts/tension_check.py NN` (a 1-2 digit book number) resolving through `resolve_inputs`. The existing path form (`tension_check.py <outline-path> [--beat-sheet …]`) keeps working unchanged.
- Consumes: `penny_genre.beat_sheet`, `penny_paths` (`series_root`, `input_path`, `series_path`), and `preflight`'s `_first_file` behaviour (reimplement locally — do NOT import from `preflight`, which imports `check_tension` from this module and would create a cycle).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tension_check.py`. Read the module first for its fixture style; if it has no series-tree fixture, build the tmp tree in the test the way `tests/test_packet_assemble.py`'s `series_tree` does.

```python
def test_resolve_inputs_finds_all_four(tmp_path, monkeypatch):
    """The book-number form must resolve what preflight resolves — a missing
    beat sheet silently disables five of the ten checks (spec §3a.1)."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)      # outline, plot/turning-points.md, whodunit
    got = tension_check.resolve_inputs("01", repo_root=root)

    assert got["outline"] is not None and got["outline"].name == "outline.md"
    assert got["turning_points_path"] is not None
    assert got["whodunit_path"] is not None
    # The beat sheet resolves through the genre overlay, not a hardcoded name.
    assert got["beat_sheet_path"] is None or got["beat_sheet_path"].is_file()


def test_resolve_inputs_normalises_a_missing_beat_sheet_to_none(tmp_path):
    """`config_path()` always returns SOME path. An unnormalised miss would be
    passed to check_tension as a live path and the 'could not run' note that
    the lock certificate records as `skipped:` would never fire."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, genre="no-such-genre")
    got = tension_check.resolve_inputs("01", repo_root=root)

    assert got["beat_sheet_path"] is None


def test_resolve_inputs_returns_none_for_a_book_with_no_outline(tmp_path):
    from scripts import tension_check

    root = _series_with_book_01(tmp_path, write_outline=False)
    assert tension_check.resolve_inputs("01", repo_root=root)["outline"] is None


def test_cli_accepts_a_book_number(tmp_path, monkeypatch, capsys):
    """`tension_check.py 01` from a series folder must behave as the lock does."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    monkeypatch.chdir(root)
    rc = tension_check.main(["01"])
    out = capsys.readouterr().out

    assert rc in (0, 1)                       # 0 clean, 1 findings — never a usage error
    assert "usage:" not in out


def test_cli_still_accepts_an_outline_path(tmp_path):
    """The path form is what preflight and existing callers use — unchanged."""
    from scripts import tension_check

    root = _series_with_book_01(tmp_path)
    rc = tension_check.main([str(root / "input/book-01/outline.md")])
    assert rc in (0, 1)
```

Write `_series_with_book_01(tmp_path, *, genre="cozy-mystery", write_outline=True)` beside the tests: a `.penny/` marker dir, `series.yaml` with a `genre:` line, `input/book-01/outline.md` (reuse `tests/fixtures/outlines/packet-format.md`), `input/book-01/plot/turning-points.md`, and `series/whodunit/book-01.yaml`. Keep it minimal.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tension_check.py -k "resolve_inputs or cli_accepts" -v`
Expected: FAIL with `AttributeError: module 'scripts.tension_check' has no attribute 'resolve_inputs'`.

- [ ] **Step 3: Write the resolver and the CLI form**

In `scripts/tension_check.py`:

```python
_BOOK_RE = re.compile(r"^\d{1,2}$")


def _first_file(*paths):
    for p in paths:
        if p is not None and Path(p).is_file():
            return p
    return None


def resolve_inputs(book: str, repo_root=None) -> dict:
    """The four inputs `check_tension` needs, resolved for one book.

    ONE home, called by both `preflight lock-mystery` and this module's CLI: a
    second copy would let the showrunner's report and the lock's gate disagree
    about which checks ran, and the report exists precisely to predict the gate.

    A beat sheet that does not exist normalises to None rather than a live
    Path — `config_path()` always returns SOME path, so an unnormalised miss
    would be passed through as real and the named "could not run" note the
    certificate records as `skipped: <check-id>` would never fire.
    """
```

Resolve: outline `input/book-NN/outline.md`; `beat_sheet_path` via `penny_genre.beat_sheet(root=repo_root)`, normalised to `None` unless `.is_file()`; `turning_points_path` `input/book-NN/plot/turning-points.md`; `whodunit_path` `series/whodunit/book-NN.yaml`. All through `penny_paths`, all zero-padded to two digits.

Then in `main()`, before `ap.parse_args`: when the sole positional matches `_BOOK_RE` and no `--beat-sheet`/`--turning-points`/`--whodunit` override was given, resolve through `resolve_inputs` and fail by name if the outline is `None`. Keep every existing flag working.

**Then change `scripts/preflight.py:316-334` to call `resolve_inputs`** so the two cannot drift. Preserve its existing behaviour exactly, including the `beat_sheet_path is None` note.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_tension_check.py tests/test_preflight*.py -v` — PASS, all pre-existing included.
Run: `python3 -m pytest` — expect **1359 passed** (1354 + 5). Move `CLAUDE.md:52` to the measured count.

- [ ] **Step 5: Commit**

```bash
git add scripts/tension_check.py scripts/preflight.py tests/test_tension_check.py CLAUDE.md
git commit -m "feat(tension): a book-number form that resolves what the lock resolves

tension_check.py took an outline path, while preflight lock-mystery resolved
four inputs for it. Given a bare path, beat_sheet_path is None and five of the
ten checks silently do not run — dead-stretch, starved-thread, off-mark-beat,
overloaded-chapter, monotonous-closings — so a showrunner reading the findings
before the lock got half a report with no signal that it was half.

One resolver, called by both. Two copies would let the report and the gate
disagree about what was checked.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md 3a.1

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: retire `inspector-structure`'s thread-liveness half, honestly

The dormancy flag has never had data and cannot get any: `series/continuity/threads/` does not exist, `scripts/ledger_markers.py` only *updates* thread files (`p.read_text()` on a path that must already exist) and never creates one, and `series/arc-ledger.md` is a table with a header and no rows. The check has been declared, dispatched and scored around for its whole life without once being able to fire.

The genre's four tracks already catch the same failure at book scale — `tension_check`'s `starved-thread` reads each chapter's `### Track Movement` rows against the beat sheet's `tracks.max_dark_gap` (`M: 2, P: 4, R: 4, B: 5`) — and that check *does* work and is about to start running. Named per-thread dormancy is series-scale work (design §13 Phase 8), and belongs there.

**This removes a declaration, not a capability.** An agent that stops claiming a check it cannot make is more honest, not weaker.

**Files:**
- Modify: `agents/inspector-structure.md` — Independence, Inputs, instruction 2
- Modify: `config/review-rubrics/structure-tension.md` — the roster clause and the threshold note
- Modify: `commands/review-chapter.md` — delete step 6, renumber, fix two prose references
- Modify: `CLAUDE.md:361` — the slice-free-inspectors sentence names the thread roster
- Modify: `tests/test_packet_projection_wiring.py` — re-point one label
- Modify: `docs/superpowers/specs/2026-09-09-check-economics-design.md` §3a.3 — record which branch was taken and why
- Test: `tests/test_packet_projection_wiring.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `commands/review-chapter.md`'s step labels become `1,2,3,4,5,6,6b,7,8,9,10` (from `1,2,3,4,5,6,7,7b,8,9,10,11`). Task 3 edits the step that is **7** after this renumber.

**The renumber map — apply exactly:** `7 → 6`, `7b → 6b`, `8 → 7`, `9 → 8`, `10 → 9`, `11 → 10`. Steps 1-5 do not move. Cross-references to steps 4 and 5 (in the spec, and in the runbook's own prose) therefore stay correct and must not be touched.

- [ ] **Step 1: Write the failing test**

`tests/test_packet_projection_wiring.py:62` pins `_step("commands/review-chapter.md", "7b")`. Its `_step` helper asserts the label exists and prints the real label list — so after the renumber it fails loudly, which is the designed behaviour. **Re-point it to `"6b"`. Do not weaken the helper.**

Then add, in the same file:

```python
def test_review_chapter_does_not_build_a_thread_roster():
    """The dormancy flag never had data — nothing creates a thread file and
    arc-ledger.md is an empty table — so the roster step was removed rather
    than left declared. The genre's tracks cover the same failure at book
    scale through tension_check's starved-thread (spec §3a.3)."""
    text = _read("commands/review-chapter.md")
    assert "thread roster" not in text.lower()
    assert "thread_roster" not in text


def test_inspector_structure_does_not_declare_a_thread_roster():
    text = _read("agents/inspector-structure.md")
    assert "thread_roster" not in text
    assert "thread roster" not in text.lower()
    assert "dormant" not in text.lower()
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_packet_projection_wiring.py -v`
Expected: the two new tests FAIL; the re-pointed `7b`→`6b` test FAILS with `commands/review-chapter.md has no step 6b — steps are [...]` until the renumber lands.

- [ ] **Step 3: Make the edits**

**`agents/inspector-structure.md`** — drop `thread_roster` from Inputs and from the Independence paragraph; delete instruction 2 and renumber 3→2, 4→3; drop "and confirmed dormant load-bearing threads" from the scoring line. Leave instruction 1 (tension/sagging-middle and the chapter-end hook) untouched — that is the whole of this inspector's job now, and its blocking predicate is unchanged.

**`config/review-rubrics/structure-tension.md`** — remove the thread-roster input clause, the dormancy rule, and the `thread_dormant_after_chapters` default note. Say in one line that per-thread dormancy is not checked here and that book-scale track starvation is `tension_check`'s `starved-thread`, so a reader of the rubric is not left wondering where it went.

**`commands/review-chapter.md`** — delete step 6 entirely; apply the renumber map; fix the two prose references that name it (the slice-free-inspectors sentence in step 4, which currently says structure works "from the page plus the thread roster built in step 6", and the per-inspector enumeration in what is now step 6, which says "`structure` gets the thread roster from step 6"). Both should now say structure works from the page and its rubric.

**`CLAUDE.md:361`** — same sentence, same fix: "the tension curve is read from the page and the thread roster" is no longer true.

**`docs/superpowers/specs/2026-09-09-check-economics-design.md` §3a.3** — it offers two branches ("Either the directory is created and populated by `/finalize-chapter`, or the liveness half is switched off deliberately"). Record that the second was taken, and why: nothing creates thread files, the arc ledger is an empty table, the genre's tracks cover the same failure at book scale, and named threads are Phase 8 series-scale work.

**Leave alone:** `penny-design-v3.md` and `penny-PRD-v3.md` (design intent, and CLAUDE.md names them the source of truth for it — a divergence recorded in the spec is correct; silently rewriting the design docs is not), `gemini/` (historical review artefacts), older `docs/superpowers/plans/`, and `tests/fixtures/cozy/config/run-config.md`'s `thread_dormant_after_chapters` line (an inert config fixture).

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packet_projection_wiring.py -v` — PASS, including the re-pointed `6b`.
Run: `python3 -m pytest tests/test_runbook_arguments.py -v` — PASS.
Run: `python3 -m pytest` — expect **1361 passed** (1359 + 2). Move `CLAUDE.md:52` to the measured count.

- [ ] **Step 5: Commit**

```bash
git add agents/ config/review-rubrics/ commands/ CLAUDE.md tests/ docs/superpowers/specs/ 
git commit -m "fix(structure): retire the thread-liveness half it could never run

The dormancy flag has never had data and cannot get any: continuity/threads/
does not exist, ledger_markers.py only updates thread files and never creates
one, and arc-ledger.md is a table with a header and no rows. The check was
declared, dispatched and scored around for its whole life without once being
able to fire.

The genre's four tracks catch the same failure at book scale — starved-thread
reads Track Movement against the beat sheet's max_dark_gap (M:2 P:4 R:4 B:5) —
and that check works. Named per-thread dormancy is series-scale work.

Removes a declaration, not a capability. Runbook steps renumber 7->6, 7b->6b,
8->7, 9->8, 10->9, 11->10; the wiring test's label is re-pointed, not weakened.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md 3a.3

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: a deterministic completeness gate that covers the evidence checkers

`commands/review-chapter.md`'s completeness check is **prose** asking an agent to confirm files exist. That is the soft gate this engine exists to avoid — CLAUDE.md's own layer rule puts deterministic gates in `scripts/`, where they "never make an LLM judgment" and "fail loud with a named predicate and a nonzero exit". Its practical cost is measured: `voice_drift.py` and `lexicon_check.py` ran in 1 of 12 rounds on the live series, and nothing noticed.

**Files:**
- Create: `scripts/review_completeness.py`
- Modify: `commands/review-chapter.md` — the step that is **7** after Task 2's renumber
- Test: `tests/test_review_completeness.py`

**Interfaces:**
- Consumes: `penny_genre.py inspectors` (the active genre's roster), `penny_paths` for the reviews dir and `config_path` for the lexicon.
- Produces: `python3 scripts/review_completeness.py NN MM` → exit 0 when every expected verdict file is present, 1 with one named line per missing file, 2 on usage error. Named findings: `missing-inspector-verdict`, `missing-developmental-read`, `missing-voice-drift`, `missing-lexicon-fluency`. **These are report lines, not engine findings** — they do not join any roster, are not waivable, and gate nothing but this command's own step.

**The two cases that are legitimately absent, and must not be reported:**
1. `lexicon-fluency.md` when the series has no `config/setting-pack/lexicon.yaml` — the engine ships none, it is series-authored, and `lexicon_check.py` exits rather than writing when it is absent. Report nothing; print a named note saying the check is inert for this series.
2. Any inspector not in the active genre's roster.

**Not a case, and worth stating so nobody re-derives it:** `fairplay_check.py` writes
`fairplay.md` (`name="fairplay"` at `scripts/fairplay_check.py:171`), while
`inspector-fairplay` writes `fairplay-planting.md`. They are different files. Only the
inspector verdict is ever expected here, and it is expected in every chapter — so the
reveal-chapter gating that applies to `fairplay_check.py` never touches this check's
expected set. The runbook's old prose said the same thing ("distinct from `fairplay.md`
legitimately being absent pre-reveal"). **Do not add reveal-chapter logic.**

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review_completeness.py`:

```python
def test_reports_every_missing_file_by_name(tmp_path):
    from scripts import review_completeness
    root = _series_with_reviews(tmp_path, present=[])
    rc, lines = review_completeness.check("01", "05", repo_root=root)
    assert rc == 1
    joined = "\n".join(lines)
    assert "missing-voice-drift" in joined
    assert "missing-lexicon-fluency" in joined
    assert "missing-developmental-read" in joined


def test_clean_when_everything_ran(tmp_path):
    from scripts import review_completeness
    root = _series_with_reviews(tmp_path, present="all")
    rc, lines = review_completeness.check("01", "05", repo_root=root)
    assert rc == 0, lines


def test_absent_lexicon_yaml_is_a_note_not_a_finding(tmp_path):
    """The engine ships no lexicon; a series without one is legitimate and
    lexicon_check exits rather than writing (spec §3a.2)."""
    from scripts import review_completeness
    root = _series_with_reviews(tmp_path, present="all", lexicon=False)
    (root / "output/book-01/chapters/ch-05.reviews/lexicon-fluency.md").unlink()

    rc, lines = review_completeness.check("01", "05", repo_root=root)

    assert rc == 0
    assert not any("missing-lexicon-fluency" in l for l in lines)
    assert any("lexicon" in l.lower() for l in lines), "the inert check must be named"


def test_missing_voice_drift_alone_is_a_finding(tmp_path):
    """The exact live-series failure: every agent verdict present, both
    evidence checkers skipped, gate computed anyway."""
    from scripts import review_completeness
    root = _series_with_reviews(tmp_path, present="all")
    (root / "output/book-01/chapters/ch-05.reviews/voice-drift.md").unlink()

    rc, lines = review_completeness.check("01", "05", repo_root=root)

    assert rc == 1
    assert any("missing-voice-drift" in l for l in lines)
```

Write `_series_with_reviews(tmp_path, *, present, lexicon=True)` beside them.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_review_completeness.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.review_completeness'`.

- [ ] **Step 3: Write the script**

```python
"""Review-panel completeness gate — deterministic, no LLM judgment.

`/review-chapter` used prose to ask an agent to confirm each verdict file
existed. On the live series `voice_drift.py` and `lexicon_check.py` ran in 1
of 12 rounds and nothing noticed, while `inspector-voice` recorded "No
voice_drift.py evidence was supplied for this round" and made its blocking
call blind. A gate computed over an incomplete panel is the soft gate this
engine exists to reject, so the check moves to `scripts/` where it fails loud
with a named line and a nonzero exit.

The lines below are report findings, NOT engine findings: they join no roster,
take no `--waive`, and gate nothing but this command's own step.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_genre
from scripts.penny_paths import config_path, output_path, series_path


def check(book: str, chapter: str, *, repo_root=None) -> tuple[int, list[str]]:
    """(exit_code, lines). 0 = every expected verdict present."""
    book2, ch2 = str(book).zfill(2), str(chapter).zfill(2)
    reviews = output_path(f"book-{book2}/chapters/ch-{ch2}.reviews", repo_root)
    lines: list[str] = []

    present = {p.name for p in reviews.glob("*.md")} if reviews.is_dir() else set()

    # One verdict per inspector in the ACTIVE GENRE's roster — the genre chooses
    # which run, so a fixed list here would report a cozy-only inspector missing
    # from a thriller panel.
    for name, verdict in _roster(repo_root):
        if verdict not in present:
            lines.append(f"missing-inspector-verdict: {verdict} — inspector "
                         f"'{name}' is in the genre roster but wrote no verdict")

    if "developmental-edit.md" not in present:
        lines.append("missing-developmental-read: developmental-edit.md")

    if "voice-drift.md" not in present:
        lines.append("missing-voice-drift: voice-drift.md — the evidence "
                     "inspector-voice weighs; it is free and it did not run")

    # The engine ships no lexicon: a series without one is legitimate, and
    # lexicon_check exits rather than writing. Name the inert check, never
    # report it as a skipped dispatch.
    lexicon = config_path("setting-pack/lexicon.yaml", repo_root)
    if not lexicon.is_file():
        lines.append("note: lexicon-fluency is inert for this series — no "
                     "config/setting-pack/lexicon.yaml")
    elif "lexicon-fluency.md" not in present:
        lines.append("missing-lexicon-fluency: lexicon-fluency.md")

    findings = [l for l in lines if not l.startswith("note:")]
    return (1 if findings else 0), lines


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: review_completeness.py <book> <chapter>", file=sys.stderr)
        return 2
    rc, lines = check(argv[0], argv[1])
    for line in lines:
        print(f"review_completeness: {line}")
    if rc == 0 and not lines:
        print("review_completeness: OK (every expected verdict present)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
```

Write `_roster(repo_root) -> list[tuple[str, str]]` from `penny_genre`'s inspector set and the runbook's static inspector→verdict-file table (`continuity → continuity-drift.md`, `fairplay → fairplay-planting.md`, `structure → structure-tension.md`, `voice → character-voice.md`, `ai-prose → ai-prose-taste-flags.md`). No reveal-chapter logic is needed — see the note above on `fairplay.md` versus
`fairplay-planting.md`.

- [ ] **Step 4: Wire it into the runbook**

Replace the prose completeness step (step **7** after Task 2) with the script call, keeping the prose that explains *why* a missing file means a silent dispatch failure:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_completeness.py" $book $chapter
```

State that a non-zero exit stops the run before the gate is computed — a gate over an incomplete panel is the soft gate this engine rejects. **No bare `$` before a digit.**

- [ ] **Step 5: Run tests and commit**

Run: `python3 -m pytest` — expect **1365 passed** (1361 + 4). Move `CLAUDE.md:52` to the measured count. Run `tests/test_runbook_arguments.py` too.

```bash
git add scripts/review_completeness.py tests/test_review_completeness.py commands/review-chapter.md CLAUDE.md
git commit -m "feat(review): a deterministic completeness gate covering the 2a checkers

The completeness check was prose asking an agent to confirm files exist —
the soft gate this engine exists to avoid. Its cost is measured: voice_drift
and lexicon_check ran in 1 of 12 rounds on the live series, and inspector-voice
made the blocking call blind eleven times, recording 'No voice_drift.py
evidence was supplied for this round' in its own verdict.

Three absences stay legitimate and are never reported: fairplay-planting
before the reveal chapter, lexicon-fluency in a series with no authored
lexicon (the engine ships none), and any inspector outside the genre roster.

Spec: docs/superpowers/specs/2026-09-09-check-economics-design.md 3a.2

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Out of scope for this plan

- **Running `tension_check` against book 01.** Task 1 builds the report; reading it is a session with the showrunner, because the findings are about the book and some will be waived rather than fixed. Do not run it against `~/myBooks/`.
- **Creating `series/continuity/threads/` or seeding `arc-ledger.md`.** Task 2 retires the check; it does not build the feature.
- **Spec §3c** — which inspectors run, and the developmental-editor's cadence.
- **The four follow-ups in `HANDOFF.md`** — the authored-`Summary:` collision, a `--ledger-clues` projection, the spec's stale `--no-continuity` at §5/§6, the README drafter-slice pass.
- **Do not push.**
