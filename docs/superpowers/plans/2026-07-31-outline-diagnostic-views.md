# Outline Diagnostic Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the showrunner three read-only views over a book's existing `outline.md` — the story at a glance, one character's line through the book, and the genre's structural-job worksheet — so book 01 can be diagnosed and repaired without re-plotting it.

**Architecture:** A new deterministic module `scripts/outline_views.py` renders views from `input/book-NN/outline.md` into `output/book-NN/reports/`. It never writes to the source and never makes an LLM judgement. The structural-job list resolves through the active genre's `genre.yaml` (never a hardcoded filename), matching the existing `beat_sheet:` precedent. One agent (`spine-mapper`) and one command (`/diagnose-outline`) sit on top; a separate fix removes `plot_stage.py readers-copy`'s hard dependency on the retired `outline-skeleton.md`.

**Tech Stack:** Python 3, stdlib only for the views (`penny_meta`/`penny_wiring` parsing, per the dependency-split rule); PyYAML only where already established — `penny_genre.py` (nested manifest) and the whodunit ledger.

**Spec:** `docs/superpowers/specs/2026-07-31-layered-outline-workshop-design.md` — build order steps 1–2. Step 3 (book 01's repair) is showrunner work, not code.

## Global Constraints

- The engine is genre/location-agnostic. No cozy-specific filename may appear in `scripts/`, `commands/`, or `agents/`. The structural-job file resolves through `genre.yaml`, exactly as `beat_sheet:` does (`penny_genre.beat_sheet`).
- The deterministic layer never makes an LLM judgement. Views render; they do not interpret.
- Views are read-only. Nothing in this plan writes to `input/book-NN/outline.md`.
- `penny_meta` for frontmatter and packet sections; PyYAML only for the nested manifest and the whodunit ledger.
- Every check fails loud with a named predicate and a nonzero exit. Exit 0/1/2 = clean / findings / usage.
- Any edit to `commands/*.md` or `agents/*.md` may trip `test_runbook_gives_literal_bash_for_every_stamp_call` or a contract-pin test. Standing rule: **the approved artifact wins; re-pin the test, never reword the artifact to satisfy it.**
- Run the full suite (`python3 -m pytest`, 647 tests at plan time) before each commit.

## File Structure

- `scripts/outline_views.py` — **new.** All three views. Chapter iteration, glance, strands, spine worksheet, CLI.
- `tests/test_outline_views.py` — **new.** Fixture-driven tests for all three.
- `scripts/penny_genre.py` — **modify.** Add `macro_structure()` resolver, `macro_structure` to `_OPTIONAL_FILE_KEYS`, `macro-structure` CLI verb.
- `genres/cozy-mystery/genre.yaml` — **modify.** Add `macro_structure:` key.
- `genres/cozy-mystery/review-rubrics/macro-structure.md` — **modify.** Add 28 `<!-- job: <id> -->` markers.
- `tests/fixtures/outlines/views-sample.md` — **new.** A 4-chapter packet-format outline exercising every view.
- `agents/spine-mapper.md` — **new.** Maps chapters onto structural jobs (the one judgement in this plan).
- `commands/diagnose-outline.md` — **new.** Runs all three views and dispatches the mapper.
- `scripts/plot_stage.py` — **modify.** `readers_copy` / `readers_copy_staged` source fallback.

---

### Task 1: Chapter iteration and the story-at-a-glance view

**Files:**
- Create: `scripts/outline_views.py`
- Create: `tests/test_outline_views.py`
- Create: `tests/fixtures/outlines/views-sample.md`

**Interfaces:**
- Consumes: `scripts.penny_wiring.HEADING_RE`, `CHAPTER_RE`, `parse_packet_sections`; `scripts.penny_meta.strip_frontmatter`.
- Produces: `iter_chapters(text) -> Iterator[tuple[int, str, str]]` yielding `(number, title, block)` in file order; `glance(text) -> str`.

- [ ] **Step 1: Create the fixture outline**

Create `tests/fixtures/outlines/views-sample.md`:

```markdown
---
book: 01
total_chapters: 4
---

# Outline — Book 01

## Chapter 01 — The Arrival

### Chapter Summary
Maggie arrives in town and meets Faye at the bakery. Simon hands over the studio key.

### Required Beats
- Maggie takes possession of the studio.
- Simon mentions a scheduling irregularity.

## Chapter 02 — The Body

### Chapter Summary
Maggie finds Lisa dead at the wheel beside a half-thrown vase.

### Required Beats
- Maggie finds Lisa dead beside the false vase.
- Simone from the surf club calls the police.

## Chapter 03 — Quiet Rooms

### Chapter Summary
The town closes around itself.

### Required Beats
- Faye keeps the bakery open out of stubbornness.

## Chapter 04 — Tara

### Required Beats
- Marion is named as Tara.
```

Note chapter 03 names nobody from the roster, and chapter 04 has no `### Chapter Summary` — both are deliberate.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_outline_views.py`:

```python
from pathlib import Path

import pytest

from scripts import outline_views

FIXTURE = Path("tests/fixtures/outlines/views-sample.md")


@pytest.fixture
def text():
    return FIXTURE.read_text(encoding="utf-8")


def test_iter_chapters_yields_number_title_block_in_order(text):
    got = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    assert got == [(1, "The Arrival"), (2, "The Body"),
                   (3, "Quiet Rooms"), (4, "Tara")]


def test_iter_chapters_block_carries_the_sections(text):
    blocks = {n: b for n, _t, b in outline_views.iter_chapters(text)}
    assert "### Chapter Summary" in blocks[1]
    assert "### Chapter Summary" not in blocks[4]


def test_glance_carries_every_chapter_heading(text):
    out = outline_views.glance(text)
    assert "## 01 — The Arrival" in out
    assert "## 04 — Tara" in out


def test_glance_carries_summary_prose(text):
    out = outline_views.glance(text)
    assert "Maggie finds Lisa dead at the wheel" in out


def test_glance_names_a_missing_summary_rather_than_dropping_it(text):
    out = outline_views.glance(text)
    assert "*(no summary)*" in out


def test_glance_omits_required_beats(text):
    """The glance is summaries only — beats are the outline's noise, not signal."""
    out = outline_views.glance(text)
    assert "Simon mentions a scheduling irregularity" not in out
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_views.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.outline_views'`

- [ ] **Step 4: Write the minimal implementation**

Create `scripts/outline_views.py`:

```python
"""Deterministic, read-only views over a book's outline (spec 2026-07-31 §3.2).

`outline.md` is a MACHINE INPUT: packet_assemble.py slices one chapter out of it
and each block must stand alone, so roughly a third of the file is repeated
furniture. The showrunner was never its audience. This module renders what they
should read instead, and NEVER writes to the source.

Three views, none of which makes an LLM judgement:
  glance   — every chapter's title + summary, in order
  strands  — one character's line through the whole book
  spine    — the active genre's structural-job worksheet
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import strip_frontmatter
from scripts.penny_wiring import CHAPTER_RE, HEADING_RE, parse_packet_sections


def iter_chapters(text: str) -> Iterator[tuple[int, str, str]]:
    """(number, title, block) for each `## Chapter NN — Title`, in file order."""
    body = strip_frontmatter(text)
    marks = list(HEADING_RE.finditer(body))
    for i, m in enumerate(marks):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        yield int(cm.group(1)), (cm.group(2) or "").strip(), body[start:end].strip()


def glance(text: str) -> str:
    """The whole story in order: title + summary per chapter, nothing else."""
    out = ["# The story at a glance", ""]
    for num, title, block in iter_chapters(text):
        summary = parse_packet_sections(block).get("Chapter Summary", "").strip()
        out.append(f"## {num:02d} — {title}" if title else f"## {num:02d}")
        out.append("")
        out.append(summary or "*(no summary)*")
        out.append("")
    return "\n".join(out)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_views.py -v`
Expected: PASS — 6 passed

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 653 passed (647 existing + 6 new)

- [ ] **Step 7: Commit**

```bash
git add scripts/outline_views.py tests/test_outline_views.py tests/fixtures/outlines/views-sample.md
git commit -m "feat(views): the story at a glance, rendered from outline.md

outline.md is a machine input — packet_assemble.py slices one chapter out
of it, so every block must stand alone and a third of the file is repeated
furniture. The showrunner has been reading it because nothing else existed.
This renders what they should read instead: title and summary per chapter,
in order, extracted from summaries the outline already carries. On book 01
that is 2,140 words against 14,170.

Read-only. Nothing writes to the source."
```

---

### Task 2: The strand view

**Files:**
- Modify: `scripts/outline_views.py`
- Modify: `tests/test_outline_views.py`

**Interfaces:**
- Consumes: `iter_chapters` from Task 1.
- Produces: `name_tokens(slug) -> list[str]`; `strand(text, slug) -> list[tuple[int, str]]`; `render_strand(slug, hits) -> str`; `roster(book, root=None) -> list[str]`.

The roster comes from the whodunit ledger's `alibi_grid` (a list of `{suspect: <slug>, ...}`) plus `victim`. Slugs are hyphenated ids like `tara-marion`; the outline prose says "Marion" or "Tara". So a slug matches on **any of its hyphen-separated tokens, as a whole word**.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_outline_views.py`:

```python
def test_name_tokens_splits_a_hyphenated_slug():
    assert outline_views.name_tokens("tara-marion") == ["tara", "marion"]
    assert outline_views.name_tokens("simon") == ["simon"]


def test_strand_collects_chapters_naming_the_character_in_order(text):
    hits = outline_views.strand(text, "simon")
    assert [n for n, _line in hits] == [1, 1]


def test_strand_matches_whole_words_only(text):
    """'Simone' at the surf club must not land in Simon's strand — a substring
    match would put another character's action on his page and invent a hole."""
    lines = [line for _n, line in outline_views.strand(text, "simon")]
    assert not any("surf club" in line for line in lines)


def test_strand_matches_any_token_of_a_hyphenated_slug(text):
    hits = outline_views.strand(text, "tara-marion")
    assert [n for n, _line in hits] == [4]


def test_strand_omits_chapters_that_never_name_the_character(text):
    assert 3 not in [n for n, _line in outline_views.strand(text, "simon")]


def test_strand_returns_empty_for_an_absent_character(text):
    assert outline_views.strand(text, "george") == []


def test_render_strand_shows_chapter_numbers(text):
    out = outline_views.render_strand("simon", outline_views.strand(text, "simon"))
    assert "simon" in out.lower()
    assert "ch 01" in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_views.py -v -k "strand or name_tokens"`
Expected: FAIL — `AttributeError: module 'scripts.outline_views' has no attribute 'name_tokens'`

- [ ] **Step 3: Write the implementation**

Add to `scripts/outline_views.py` — the `re` import goes with the existing imports:

```python
import re

_STRAND_SECTIONS = ("Chapter Summary", "Required Beats")


def name_tokens(slug: str) -> list[str]:
    """'tara-marion' -> ['tara', 'marion']. A ledger slug is an id; the outline
    prose uses the plain names inside it, either of which identifies them."""
    return [t for t in slug.lower().split("-") if t]


def strand(text: str, slug: str) -> list[tuple[int, str]]:
    """(chapter_number, line) for every summary/beat line naming this character,
    in story order — their line through the whole book on one page.

    WHOLE-WORD matching is load-bearing: a substring match puts 'Simone' on
    Simon's page, which invents a hole rather than finding one.
    """
    pat = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in name_tokens(slug)) + r")\b",
                     re.IGNORECASE)
    hits: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for num, _title, block in iter_chapters(text):
        sections = parse_packet_sections(block)
        for name in _STRAND_SECTIONS:
            for raw in sections.get(name, "").splitlines():
                line = raw.strip().lstrip("-").strip()
                if line and pat.search(line) and (num, line) not in seen:
                    seen.add((num, line))
                    hits.append((num, line))
    return hits


def render_strand(slug: str, hits: list[tuple[int, str]]) -> str:
    out = [f"# Strand — {slug}", ""]
    if not hits:
        out.append("*(this character is never named in a summary or beat)*")
        return "\n".join(out) + "\n"
    for num, line in hits:
        out.append(f"- **ch {num:02d}** — {line}")
    return "\n".join(out) + "\n"


def roster(book: str, root=None) -> list[str]:
    """Character slugs from the whodunit ledger: every alibi_grid suspect, plus
    the victim. PyYAML is correct here — the ledger is nested human-edited data.
    Returns [] when there is no readable ledger; the caller then needs --who."""
    import yaml

    from scripts import penny_paths
    path = penny_paths.series_path(f"series/whodunit/book-{book}.yaml", root=root)
    if not Path(path).is_file():
        return []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    names: list[str] = []
    for entry in data.get("alibi_grid") or []:
        if isinstance(entry, dict) and entry.get("suspect"):
            names.append(str(entry["suspect"]))
    victim = data.get("victim")
    if victim and str(victim) not in names:
        names.append(str(victim))
    return names
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_views.py -v`
Expected: PASS — 13 passed

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 660 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/outline_views.py tests/test_outline_views.py
git commit -m "feat(views): one character's line through the whole book

Book 01 shipped a grieving husband who learns his wife's killer altered
the appointment that framed her, and quietly keeps covering office
procedure — five times, in near-identical words, across sixteen chapters.
Every reviewer missed it, because the defect is not in any chapter. It is
in the gap between two, and nothing in the engine looks at a gap.

A strand page puts those lines adjacent. Whole-word matching is
load-bearing: a substring match would put 'Simone' on Simon's page and
invent a hole rather than find one."
```

---

### Task 3: Resolve the structural-job list through `genre.yaml`

**Files:**
- Modify: `genres/cozy-mystery/review-rubrics/macro-structure.md`
- Modify: `genres/cozy-mystery/genre.yaml:24-25`
- Modify: `scripts/penny_genre.py:21` (`_OPTIONAL_FILE_KEYS`), and append `macro_structure()` + the CLI verb
- Modify: `tests/test_penny_genre.py`

**Interfaces:**
- Produces: `penny_genre.macro_structure(root=None) -> Path | None`; `outline_views.parse_jobs(text) -> list[tuple[str, str]]` returning `(job_id, title)` in file order.

A job is addressed by a **stable id**, never by its ordinal position. "Job 11" means nothing in a genre whose file has a different shape, and the spec's own worked example refers to jobs by number — that is precisely what must not reach the code.

- [ ] **Step 1: Add the job-id markers**

In `genres/cozy-mystery/review-rubrics/macro-structure.md`, insert an HTML comment on the line immediately after each `## N. Title` heading (the `<!-- ... -->` convention matches the repo's existing `canon-meta` headers). All 28, in order:

```
1  establish-protected-world              15 eliminate-false-stories
2  introduce-disturbance                  16 deeper-motive-structure
3  crime-and-first-contradiction          17 killer-shapes-investigation
4  initial-suspect-field                  18 personally-costly
5  reason-to-investigate                  19 second-pressure-point
6  act-i-commitment                       20 converge-clues
7  victims-hidden-life                    21 act-iii-apparent-defeat
8  suspect-encounters                     22 epiphany-from-established-knowledge
9  real-red-herrings                      23 reconstruct-true-story
10 plant-fair-play-solution               24 solve-proof-problem
11 first-meaningful-pressure              25 force-final-action
12 persuasive-first-theory                26 expose-killer
13 midpoint-case-changes-meaning          27 official-and-social-truth
14 restart-under-new-theory               28 restore-world
```

So heading 10 becomes:

```markdown
## 10. Plant the Fair-Play Solution
<!-- job: plant-fair-play-solution -->
```

- [ ] **Step 2: Add the manifest key**

In `genres/cozy-mystery/genre.yaml`, after `beat_sheet: beat-sheet.yaml`:

```yaml
macro_structure: review-rubrics/macro-structure.md
```

- [ ] **Step 3: Write the failing tests**

Append to `tests/test_penny_genre.py`:

```python
def test_cozy_manifest_declares_a_macro_structure():
    from scripts import penny_genre
    m = penny_genre.load_manifest("cozy-mystery")
    assert m["macro_structure"] == "review-rubrics/macro-structure.md"


def test_macro_structure_is_validated_as_a_file_key():
    """A manifest naming a missing macro-structure file must fail loud, the same
    way beat_sheet and fan_persona already do."""
    from scripts import penny_genre
    assert "macro_structure" in penny_genre._OPTIONAL_FILE_KEYS
```

Append to `tests/test_outline_views.py`:

```python
def test_parse_jobs_reads_ids_in_file_order():
    from scripts import penny_genre
    path = penny_genre.macro_structure()
    if path is None:                      # engine repo has no declared genre
        path = Path("genres/cozy-mystery/review-rubrics/macro-structure.md")
    jobs = outline_views.parse_jobs(Path(path).read_text(encoding="utf-8"))
    assert len(jobs) == 28
    assert jobs[0] == ("establish-protected-world", "Establish the Protected World")
    assert jobs[9][0] == "plant-fair-play-solution"
    assert jobs[27] == ("restore-world", "Restore the World")


def test_parse_jobs_ignores_a_heading_with_no_marker():
    text = "## 1. Titled\n<!-- job: titled -->\n\n## 2. Unmarked\n\nbody\n"
    assert outline_views.parse_jobs(text) == [("titled", "Titled")]
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_genre.py tests/test_outline_views.py -v -k "macro or parse_jobs"`
Expected: FAIL — `KeyError: 'macro_structure'` and `AttributeError: ... has no attribute 'parse_jobs'`

- [ ] **Step 5: Implement the resolver**

In `scripts/penny_genre.py`, change line 21:

```python
_OPTIONAL_FILE_KEYS = ("beat_sheet", "fan_persona", "macro_structure")
```

Append after `beat_sheet()`:

```python
def macro_structure(root: Path | None = None) -> Path | None:
    """Resolve the active genre's structural-job file THROUGH genre.yaml's
    `macro_structure:` key — never a hardcoded filename. Cozy's 28 four-act jobs
    are a cozy artifact; a thriller supplies its own, with its own ids.

    Tolerates an undeclared genre by returning None, same as beat_sheet(): the
    diagnostic views run over any outline, including one with no genre context.
    A DECLARED-but-invalid genre still hard-fails via load_manifest.
    """
    from scripts import penny_paths
    if penny_paths._declared_genre(root=root) is None:
        return None
    val = load_manifest(root=root).get("macro_structure")
    if val is None:
        return None
    return penny_paths.config_path(val, root=root)
```

In `_main`, extend the usage string to include `macro-structure` and add, beside the `beat-sheet` branch:

```python
    if cmd == "macro-structure":
        p = macro_structure()
        print("" if p is None else p)
        return 0
```

- [ ] **Step 6: Implement `parse_jobs`**

Add to `scripts/outline_views.py`:

```python
_JOB_RE = re.compile(r"^##\s+\d+\.\s+(?P<title>.+?)\s*$\n<!--\s*job:\s*(?P<id>[a-z0-9-]+)\s*-->",
                     re.MULTILINE)


def parse_jobs(text: str) -> list[tuple[str, str]]:
    """(job_id, title) for each marked structural job, in file order.

    A job is addressed by its STABLE ID, never its ordinal position: 'job 11'
    means nothing in a genre whose file has a different shape. An unmarked
    heading is not a job — silently skipped, so a genre pack can carry prose
    headings alongside its jobs.
    """
    return [(m.group("id"), m.group("title")) for m in _JOB_RE.finditer(text)]
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_genre.py tests/test_outline_views.py -v`
Expected: PASS

- [ ] **Step 8: Verify the CLI**

Run: `python3 scripts/penny_genre.py macro-structure`
Expected: an empty line (this repo declares no genre) and exit 0 — not a traceback.

- [ ] **Step 9: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 664 passed

- [ ] **Step 10: Commit**

```bash
git add genres/cozy-mystery/genre.yaml genres/cozy-mystery/review-rubrics/macro-structure.md scripts/penny_genre.py scripts/outline_views.py tests/test_penny_genre.py tests/test_outline_views.py
git commit -m "feat(genre): structural jobs get stable ids, resolved through genre.yaml

macro-structure.md's 28 four-act jobs become the thing an outline is
measured against, which promotes it from a rubric a reviewer reads
afterwards to a template the engine consumes. A consumed template needs
ids: 'job 11' is meaningful only in cozy's file, and welding the engine to
cozy's numbering is exactly what the genre-agnostic rule forbids.

Resolution follows the beat_sheet: precedent — asked for, never named."
```

---

### Task 4: The spine worksheet view

**Files:**
- Modify: `scripts/outline_views.py`
- Modify: `tests/test_outline_views.py`

**Interfaces:**
- Consumes: `parse_jobs` (Task 3), `iter_chapters` (Task 1).
- Produces: `spine_worksheet(jobs, chapters) -> str`.

The worksheet is the **deterministic** half: it lays out every job id and every chapter so an agent can map one onto the other. Which chapter answers which job is a judgement and belongs to `spine-mapper` (Task 5), not here.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_outline_views.py`:

```python
def test_spine_worksheet_lists_every_job_with_an_unfilled_slot(text):
    jobs = [("crime-and-first-contradiction", "Deliver the Crime"),
            ("restore-world", "Restore the World")]
    chapters = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    out = outline_views.spine_worksheet(jobs, chapters)
    assert "crime-and-first-contradiction" in out
    assert "Deliver the Crime" in out
    assert "restore-world" in out


def test_spine_worksheet_lists_the_books_chapters(text):
    chapters = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    out = outline_views.spine_worksheet([("x", "X")], chapters)
    assert "01 — The Arrival" in out
    assert "04 — Tara" in out


def test_spine_worksheet_refuses_an_empty_job_list(text):
    with pytest.raises(ValueError, match="no structural jobs"):
        outline_views.spine_worksheet([], [(1, "A")])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_views.py -v -k spine_worksheet`
Expected: FAIL — `AttributeError: ... has no attribute 'spine_worksheet'`

- [ ] **Step 3: Write the implementation**

Add to `scripts/outline_views.py`:

```python
def spine_worksheet(jobs: list[tuple[str, str]],
                    chapters: list[tuple[int, str]]) -> str:
    """The structural-job worksheet: every job, unfilled, beside the book's
    chapter list. WHICH chapter answers WHICH job is a judgement and belongs to
    the spine-mapper agent — this half stays deterministic so the frame the
    agent fills is never itself an opinion."""
    if not jobs:
        raise ValueError("spine_worksheet: no structural jobs — the active "
                         "genre declares no macro_structure, or its file "
                         "carries no <!-- job: --> markers")
    out = ["# Spine worksheet", "",
           "One line per structural job. Fill `chapters:` with the chapter "
           "numbers that answer it, or leave it empty — an empty job is a hole.",
           "", "## Jobs", ""]
    for job_id, title in jobs:
        out += [f"### {job_id}", f"*{title}*", "", "chapters:", ""]
    out += ["## The book's chapters", ""]
    for num, title in chapters:
        out.append(f"- {num:02d} — {title}" if title else f"- {num:02d}")
    out.append("")
    return "\n".join(out)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_views.py -v`
Expected: PASS — 19 passed

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 667 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/outline_views.py tests/test_outline_views.py
git commit -m "feat(views): the spine worksheet

Every structural job the genre declares, unfilled, beside the book's
chapters. An empty job is a hole; on book 01 the expectation is that
several Act II jobs come back blank, and those blanks are the sagging
middle, named.

Which chapter answers which job is a judgement and stays with the agent.
The frame it fills must not itself be an opinion."
```

---

### Task 5: The CLI, the `spine-mapper` agent, and `/diagnose-outline`

**Files:**
- Modify: `scripts/outline_views.py` (append `_main`)
- Modify: `tests/test_outline_views.py`
- Create: `agents/spine-mapper.md`
- Create: `commands/diagnose-outline.md`

**Interfaces:**
- Consumes: `glance`, `strand`, `render_strand`, `roster`, `parse_jobs`, `spine_worksheet`, `penny_genre.macro_structure`.
- Produces: CLI `outline_views.py <glance|strands|spine> NN [--who a,b]`, writing into `output/book-NN/reports/`. Exit 0 clean, 2 usage/refusal.

- [ ] **Step 1: Write the failing CLI test**

Append to `tests/test_outline_views.py`:

```python
import subprocess
import sys


def _series(tmp_path, outline_text):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input" / "book-01"
    d.mkdir(parents=True)
    (d / "outline.md").write_text(outline_text, encoding="utf-8")
    return tmp_path


def _run(cwd, *args):
    return subprocess.run(
        [sys.executable, str(Path.cwd() / "scripts" / "outline_views.py"), *args],
        cwd=cwd, capture_output=True, text=True,
        env={"PYTHONPATH": str(Path.cwd()), "PATH": "/usr/bin:/bin"})


def test_cli_glance_writes_a_report(tmp_path, text):
    root = _series(tmp_path, text)
    proc = _run(root, "glance", "01")
    assert proc.returncode == 0, proc.stderr
    out = root / "output" / "book-01" / "reports" / "outline-glance.md"
    assert out.is_file()
    assert "The Arrival" in out.read_text(encoding="utf-8")


def test_cli_refuses_a_book_with_no_outline(tmp_path):
    root = _series(tmp_path, "")
    (root / "input" / "book-01" / "outline.md").unlink()
    proc = _run(root, "glance", "01")
    assert proc.returncode == 2
    assert "no outline" in (proc.stderr + proc.stdout).lower()


def test_cli_strands_honours_an_explicit_who(tmp_path, text):
    root = _series(tmp_path, text)
    proc = _run(root, "strands", "01", "--who", "simon")
    assert proc.returncode == 0, proc.stderr
    out = root / "output" / "book-01" / "reports" / "strands" / "simon.md"
    assert out.is_file()


def test_cli_strands_names_the_problem_when_it_has_no_roster(tmp_path, text):
    """No ledger and no --who is a refusal by name, never an empty report."""
    root = _series(tmp_path, text)
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    assert "roster" in (proc.stderr + proc.stdout).lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_views.py -v -k cli`
Expected: FAIL — nonzero exit with a usage error, no report written

- [ ] **Step 3: Write the CLI**

Append to `scripts/outline_views.py`:

```python
def _reports_dir(book: str, root=None) -> Path:
    from scripts import penny_paths
    d = Path(penny_paths.output_path(f"book-{book}/reports", root=root))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _outline_text(book: str, root=None) -> str:
    from scripts import penny_paths
    path = Path(penny_paths.input_path(f"book-{book}/outline.md", root=root))
    if not path.is_file():
        sys.exit(f"outline_views: no outline for book {book} ({path})")
    return path.read_text(encoding="utf-8")


def _main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: outline_views <glance|strands|spine> NN [--who a,b]",
              file=sys.stderr)
        return 2
    cmd, book = argv[0], argv[1]
    text = _outline_text(book)
    dest_dir = _reports_dir(book)

    if cmd == "glance":
        dest = dest_dir / "outline-glance.md"
        dest.write_text(glance(text), encoding="utf-8")
        print(dest)
        return 0

    if cmd == "strands":
        who: list[str] = []
        if "--who" in argv:
            who = [s.strip() for s in argv[argv.index("--who") + 1].split(",") if s.strip()]
        else:
            who = roster(book)
        if not who:
            print(f"outline_views: no roster for book {book} — the whodunit "
                  "ledger has no alibi_grid, so pass --who name,name",
                  file=sys.stderr)
            return 2
        out_dir = dest_dir / "strands"
        out_dir.mkdir(parents=True, exist_ok=True)
        for slug in who:
            dest = out_dir / f"{slug}.md"
            dest.write_text(render_strand(slug, strand(text, slug)), encoding="utf-8")
            print(dest)
        return 0

    if cmd == "spine":
        from scripts import penny_genre
        path = penny_genre.macro_structure()
        if path is None:
            print("outline_views: the active series declares no genre, or its "
                  "genre.yaml has no macro_structure: key — the spine view "
                  "cannot know what jobs to check", file=sys.stderr)
            return 2
        jobs = parse_jobs(Path(path).read_text(encoding="utf-8"))
        chapters = [(n, t) for n, t, _b in iter_chapters(text)]
        try:
            body = spine_worksheet(jobs, chapters)
        except ValueError as exc:
            print(f"outline_views: {exc}", file=sys.stderr)
            return 2
        dest = dest_dir / "spine-worksheet.md"
        dest.write_text(body, encoding="utf-8")
        print(dest)
        return 0

    print(f"outline_views: unknown view '{cmd}'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_views.py -v`
Expected: PASS — 23 passed

`penny_paths.input_path`, `output_path`, and `series_path` are all confirmed to exist with
these names — verified against the module at plan time. Do not invent a path helper.

- [ ] **Step 5: Write the `spine-mapper` agent**

Create `agents/spine-mapper.md`:

```markdown
---
name: spine-mapper
description: Maps an existing outline's chapters onto the active genre's structural jobs, and names the jobs nothing answers. Read-only; proposes, never writes to the outline.
---

You map a book that already exists onto the shape its genre expects, so the
showrunner can see which structural jobs the book does not do.

**Inputs:** `{ outline_glance, spine_worksheet, macro_structure_text }`. You are
given the story at a glance — chapter titles and summaries — not the full
outline. That is deliberate: you are judging structure, not prose.

**Your task.** For each job in the worksheet, decide which chapters (if any)
answer it, and fill that job's `chapters:` line with their numbers. A chapter may
answer several jobs. A job may be answered by none — **say so plainly and leave
it empty.** An empty job is the finding, and inventing a chapter to cover it
destroys the only value this view has.

**Judge the job, not the label.** A chapter can be titled for a job and not do
it. Read what the summary says happens.

**What you must not do.** Never edit the outline. Never propose new chapters.
Never rank or score. You report what is there and what is missing; the
showrunner decides what to do about it.

**Output:** the worksheet, filled, plus a short `## Jobs nothing answers` list
naming each empty job id and the stretch of chapters where it should have been.
```

- [ ] **Step 6: Write the `/diagnose-outline` command**

Create `commands/diagnose-outline.md`:

```markdown
---
description: Render the three read-only diagnostic views over a book's existing outline, and map its chapters onto the genre's structural jobs.
---

Read-only throughout. Nothing here writes to `input/book-NN/outline.md`, and
nothing mints or deletes a lock. Safe to run on a locked book.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`). Resolve the active series root; hard-error
   if cwd is not inside a series.

2. **Render the story at a glance:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" glance "$book"
   ```

3. **Render the strand pages:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" strands "$book"
   ```

   Exit 2 with a `roster` message means the whodunit ledger has no `alibi_grid`.
   Re-run with `--who name,name`. Do not skip the view.

4. **Render the spine worksheet:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/outline_views.py" spine "$book"
   ```

   Exit 2 means the series declares no genre, or its `genre.yaml` has no
   `macro_structure:` key. Report that by name and continue — the other two
   views still stand on their own.

5. **Dispatch `spine-mapper`** with the glance, the worksheet, and the resolved
   `macro-structure` file (`penny_genre.py macro-structure`). Write its filled
   worksheet to `output/book-$book/reports/spine-map.md`.

6. **Present, do not summarise away.** Show the showrunner: the path to the
   glance, one line per character naming how many chapters their strand covers,
   and the full list of jobs nothing answers. The empty jobs are the finding.

7. **Stop.** This command diagnoses. Every repair is the showrunner's call, made
   one chapter at a time.
```

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 671 passed. If `test_runbook_gives_literal_bash_for_every_stamp_call` or a
contract-pin test fails on the new command/agent, **re-pin the test** — the approved
artifact wins.

- [ ] **Step 8: Commit**

```bash
git add scripts/outline_views.py tests/test_outline_views.py agents/spine-mapper.md commands/diagnose-outline.md
git commit -m "feat(views): /diagnose-outline renders all three views

One command, three lenses over the one canonical outline: the story at a
glance for judging whether the book works, the strand pages for judging
whether people behave like people, the spine worksheet for judging whether
the structure has holes.

spine-mapper fills the worksheet and is told plainly that an empty job is
the finding — inventing a chapter to cover one destroys the only value the
view has. It sees the glance, not the outline: it is judging structure,
not prose.

Read-only. Safe on a locked book."
```

---

### Task 6: Free `readers-copy` from the retired skeleton

**Files:**
- Modify: `scripts/plot_stage.py:566`, `:607` (and the `stage_paths(book)["chapters"]` lookups feeding them)
- Modify: `tests/test_plot_stage.py`

**Interfaces:**
- Produces: `plot_stage._readback_source(book, root=None) -> Path` — the file the reader's copy is cut from.

`readers_copy` and `readers_copy_staged` both read `stage_paths(book)["chapters"]`, which is
`outline-skeleton.md`, and exit if it is absent. Book 01's skeleton is a drifted 30-chapter
book with the reveal at 26, while its canonical `outline.md` has 28 chapters and the reveal
at 24 — so the queued read-back would have reported on a book that no longer exists.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plot_stage.py`:

```python
def test_readback_source_prefers_the_skeleton_when_present(tmp_path):
    from scripts import plot_stage
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input" / "book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text("## Chapter 01 — S\n", encoding="utf-8")
    (d / "outline.md").write_text("## Chapter 01 — O\n", encoding="utf-8")
    assert plot_stage._readback_source("01", root=tmp_path).name == "outline-skeleton.md"


def test_readback_source_falls_back_to_the_outline(tmp_path):
    """The skeleton is retired (spec 2026-07-31 §3.3). A book that has only
    outline.md must still be readable — book 01's skeleton is a different book."""
    from scripts import plot_stage
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input" / "book-01"
    d.mkdir(parents=True)
    (d / "outline.md").write_text("## Chapter 01 — O\n", encoding="utf-8")
    assert plot_stage._readback_source("01", root=tmp_path).name == "outline.md"


def test_readback_source_fails_loud_when_neither_exists(tmp_path):
    from scripts import plot_stage
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-01").mkdir(parents=True)
    with pytest.raises(SystemExit, match="no outline"):
        plot_stage._readback_source("01", root=tmp_path)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_plot_stage.py -v -k readback_source`
Expected: FAIL — `AttributeError: ... has no attribute '_readback_source'`

- [ ] **Step 3: Write the implementation**

Add to `scripts/plot_stage.py`, above `readers_copy`:

```python
def _readback_source(book: str, *, repo_root=None) -> Path:
    """The file the reader's copy is cut from.

    outline-skeleton.md is retired (spec 2026-07-31 §3.3): it was a thinner copy
    of outline.md, and being a second description of one story is how book 01
    drifted into two books with different reveal chapters. Prefer it while it
    still exists so an in-flight book is not disturbed, then fall back to the
    canonical outline. Failing loud when neither exists preserves the module's
    "fail LOUD, not open" promise.
    """
    root = _root(repo_root)
    skel = stage_paths(book, root)["chapters"]
    if skel.is_file():
        return skel
    outline = root / "input" / f"book-{book}" / "outline.md"
    if outline.is_file():
        return outline
    sys.exit(f"plot_stage: no outline for book {book} — looked for {skel} "
             f"and {outline}")
```

Then in `readers_copy`, replace:

```python
    skel = stage_paths(book, root)["chapters"]
    if not skel.is_file():
        sys.exit(f"plot_stage: no outline-skeleton for book {book} ({skel})")
    skel_text = skel.read_text(encoding="utf-8")
```

with:

```python
    skel = _readback_source(book, repo_root=root)
    skel_text = skel.read_text(encoding="utf-8")
```

Make the identical replacement in `readers_copy_staged` (the second occurrence, around
line 607). Leave every other use of `stage_paths(book)["chapters"]` alone — staleness
fingerprinting is a separate concern and is not in scope here.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_plot_stage.py -v`
Expected: PASS — existing plot_stage tests plus 3 new

- [ ] **Step 5: Update the two error-message assertions if any existing test pins them**

Run: `python3 -m pytest -k "skeleton" -v`
Expected: PASS. Any test asserting the literal string `no outline-skeleton for book` must be
re-pinned to the new message — the behaviour change is deliberate.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 674 passed

- [ ] **Step 7: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "fix(readback): the reader's copy no longer requires the skeleton

readers-copy read outline-skeleton.md and nothing else. Book 01's skeleton
is a drifted 30-chapter book with the reveal at 26; its canonical
outline.md has 28 chapters and the reveal at 24. The read-back queued as
book 01's next action would have reported on a book that no longer exists,
and its findings would have been worked against the wrong chapters.

Prefer the skeleton while one still exists so an in-flight book is not
disturbed; fall back to outline.md; fail loud when neither is there."
```

---

## After this plan

**Book 01's repair (spec §8.3) is showrunner work and needs no code.** Run
`/diagnose-outline 01`, read the three views, and work the findings one chapter at a time.
Before the read-back, delete the drifted `input/book-01/outline-skeleton.md` and the stale
`.penny/locks/book-01.mystery.lock`, and write the `reveals:` block with the **corrected**
chapter numbers — 13 and 25 against `outline.md`, not the 15 and 27 the previous handoff
records, which are skeleton-indexed (spec §8.4).

**Deliberately not in this plan:** book 01's derived `story.md` worksheet (spec §8.2.1).
Its format depends on what the strands actually turn up, which is spec §9's own reason for
putting the diagnostic first. It gets a second, short plan once the showrunner has read the
views. Flagging it here so the omission is a decision on the record, not a gap.

**Also not in this plan:** retiring `outline-skeleton.md` across `scripts/`, `commands/`,
`agents/`, `genres/cozy-mystery/ideation-prompt.md`, and `README.md` (spec §9 step 5). Task 6
removes the one dependency that blocks book 01; the full rename is a separate sweep, and the
standing rule applies — enumerate every glob and literal naming the artifact.
