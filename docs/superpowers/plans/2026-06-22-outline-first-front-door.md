# Outline-First, Multi-Strand Author Front Door — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the writer author a prose **outline** (beats + sealed `## Solution`s) and have the system derive the whodunit yaml, threads, entities, and canon-core updates for review, keeping the human on the unchanged taste gates.

**Architecture:** One new deterministic engine piece (`scripts/outline_check.py`) gates only the outline's structural *shape*; a `book-scaffolder` agent does all genre/semantic extraction into the already-shipped continuity layer; a `/scaffold-book` command orchestrates check → derive → tiered review → pause → run the **unchanged** `preflight.py lock-mystery`. The front door never writes a certificate.

**Tech Stack:** Python 3 stdlib + `scripts.penny_meta` (no PyYAML in the new script); `pytest` (`pythonpath=.` via `pytest.ini`); markdown command/agent files asserted by content tests, mirroring `tests/test_draft_preflight_wiring.py`.

## Global Constraints

- Engine stays **genre/location-agnostic**: all project content lives in swappable `config/` and `series/`/`output/`, never hardcoded in `scripts/` or command logic.
- The new script makes **zero LLM/genre judgment**, fails loud with a **named predicate + nonzero exit** (`outline_check: <predicate>`), exactly like `fairplay_check.py` / `preflight.py`.
- **Dependency-split rule:** the new script uses `scripts.penny_meta` for frontmatter/headings — **never PyYAML**. PyYAML is only for nested human-edited whodunit/lexicon data.
- **HARD constraint — do not touch shipped gate logic:** `scripts/fairplay_check.py`, the inspectors, and `preflight.py cmd_lock_mystery` must not change. Multi-mystery is achieved by looping the unchanged checker, and that loop is **deferred** (not built here).
- `parse_frontmatter` coerces every scalar to a **string** (e.g. `total_chapters: 24` → `"24"`). Integer checks must test digit-strings (`.isdigit()`), not `isinstance(int)`.
- The lock is an **out-of-band certificate**: never write a `locked:` field into derived data; the only lock writer is `preflight.py lock-mystery`.
- Test fixtures are **self-contained** — never reach into real `series/` content (it resets to a blank slate).
- v1 scope: **one** gated mystery; secondary mysteries ride as un-gated threads. Deferred (flag, don't build): per-chapter brief derivation, the looping multi-mystery gate, diff-on-edit re-derivation review.

---

### Task 1: `scripts/outline_check.py` + fixtures + template

The one new deterministic engine piece: four named structural predicates over the outline. Pure stdlib + `penny_meta`. Ends with a tested, self-verifying `config/outline-template.md`.

**Files:**
- Create: `scripts/outline_check.py`
- Create: `tests/test_outline_check.py`
- Create: `tests/fixtures/outlines/well-formed.md`
- Create: `tests/fixtures/outlines/missing-solution.md`
- Create: `tests/fixtures/outlines/chapter-gap.md`
- Create: `tests/fixtures/outlines/non-int-count.md`
- Create: `tests/fixtures/outlines/empty-beat.md`
- Create: `config/outline-template.md`

**Interfaces:**
- Consumes: `scripts.penny_meta.parse_frontmatter(text) -> dict` (scalars come back as strings).
- Produces (later tasks rely on these exact names/types):
  - `check_outline(outline_path, *, repo_root=None) -> dict` returning `{"blocking": list[str], "metrics": dict}`; `blocking` is empty iff well-formed; each blocking string starts with one of `outline-frontmatter` / `outline-solution` / `outline-chapters-contiguous` / `outline-nonempty-beats`.
  - `main(argv=None) -> int` — exit 0 iff well-formed, else 1; prints `outline_check: <blocking line>` per blocker.

- [ ] **Step 1: Write the fixtures**

`tests/fixtures/outlines/well-formed.md`:

```markdown
---
book: 01
total_chapters: 3
---

## Solution: the-tide-table-murder
- culprit: margaret
- victim: edwin-tilley
- central deception / motive: Margaret swapped the tide tables to fake the time of death.
- suspects: margaret, thomas
- key locations: the-bluff

## Threads
- romance — Cora and the harbourmaster circle each other; should pay off late.
- settling-in — Cora learns the town's rhythms.

## Chapter 01
Cora arrives at the Bluff and meets the town; the body is found at low tide.

## Chapter 02
The torn ferry ticket surfaces; Margaret is seen near the church fete.

## Chapter 03
The tide-table swap is exposed; Margaret's alibi collapses.
```

`tests/fixtures/outlines/missing-solution.md` (no `## Solution` block):

```markdown
---
book: 01
total_chapters: 2
---

## Threads
- romance — a slow burn.

## Chapter 01
Cora arrives.

## Chapter 02
Cora investigates.
```

`tests/fixtures/outlines/chapter-gap.md` (declares 3, ships 1 and 3):

```markdown
---
book: 01
total_chapters: 3
---

## Solution: the-murder
- culprit: margaret

## Chapter 01
Cora arrives.

## Chapter 03
The reveal.
```

`tests/fixtures/outlines/non-int-count.md` (`total_chapters` not an integer):

```markdown
---
book: 01
total_chapters: many
---

## Solution: the-murder
- culprit: margaret

## Chapter 01
Cora arrives.
```

`tests/fixtures/outlines/empty-beat.md` (Chapter 02 body is whitespace only):

```markdown
---
book: 01
total_chapters: 2
---

## Solution: the-murder
- culprit: margaret

## Chapter 01
Cora arrives.

## Chapter 02
   
```

- [ ] **Step 2: Write the failing tests**

`tests/test_outline_check.py`:

```python
from pathlib import Path

from scripts.outline_check import check_outline, main

FIX = Path("tests/fixtures/outlines")


def _predicates(result):
    return [b.split(":", 1)[0] for b in result["blocking"]]


def test_well_formed_has_no_blockers():
    result = check_outline(FIX / "well-formed.md")
    assert result["blocking"] == []


def test_well_formed_main_exits_zero():
    assert main([str(FIX / "well-formed.md")]) == 0


def test_missing_solution_fails_named_predicate():
    result = check_outline(FIX / "missing-solution.md")
    assert "outline-solution" in _predicates(result)


def test_chapter_gap_fails_contiguity():
    result = check_outline(FIX / "chapter-gap.md")
    assert "outline-chapters-contiguous" in _predicates(result)


def test_non_int_count_fails_frontmatter():
    result = check_outline(FIX / "non-int-count.md")
    assert "outline-frontmatter" in _predicates(result)


def test_empty_beat_fails_nonempty_beats():
    result = check_outline(FIX / "empty-beat.md")
    assert "outline-nonempty-beats" in _predicates(result)


def test_main_exits_nonzero_on_broken():
    assert main([str(FIX / "missing-solution.md")]) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_outline_check.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.outline_check'`.

- [ ] **Step 4: Write the implementation**

`scripts/outline_check.py`:

```python
"""Outline structural checker (deterministic, Tier-3, shape-only).

Validates that an author outline (output/book-NN/outline.md) is SHAPED like an
outline — nothing more. Four named predicates; zero genre/LLM judgment. Fairness,
suspect-existence and prose quality are judged elsewhere (the lock, the scaffolder,
the human review). Mirrors fairplay_check.py: named predicate + nonzero exit.

Dependency-free apart from scripts.penny_meta (frontmatter) — no PyYAML.

  python3 scripts/outline_check.py output/book-01/outline.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter

_HEADING_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
_CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)$")
_SOLUTION_RE = re.compile(r"^Solution\b(?::\s*(?P<label>.*?))?$")


def _chapter_numbers(text: str) -> list[int]:
    return [int(m.group(1)) for h in _HEADING_RE.findall(text)
            for m in [_CHAPTER_RE.match(h)] if m]


def _empty_chapter_beats(text: str) -> list[int]:
    empty: list[int] = []
    matches = list(_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = _CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if not text[start:end].strip():
            empty.append(int(cm.group(1)))
    return empty


def check_outline(outline_path, *, repo_root=None) -> dict:
    path = Path(outline_path)
    if not path.is_file():
        return {"blocking": [f"outline-frontmatter: outline not found: {path}"],
                "metrics": {}}
    text = path.read_text(encoding="utf-8")
    blocking: list[str] = []

    fm = parse_frontmatter(text)
    book = fm.get("book")
    total_raw = fm.get("total_chapters")
    if not (isinstance(book, str) and book.strip().isdigit()):
        blocking.append(f"outline-frontmatter: 'book' missing or not an integer: {book!r}")
    total = None
    if isinstance(total_raw, str) and total_raw.strip().isdigit():
        total = int(total_raw)
    else:
        blocking.append(
            f"outline-frontmatter: 'total_chapters' missing or not an integer: {total_raw!r}")

    headings = _HEADING_RE.findall(text)
    if not any(_SOLUTION_RE.match(h) for h in headings):
        blocking.append("outline-solution: no '## Solution' block found")

    nums = _chapter_numbers(text)
    if total is not None:
        expected = list(range(1, total + 1))
        if sorted(nums) != expected:
            blocking.append(
                f"outline-chapters-contiguous: chapter headings {sorted(nums)} are not "
                f"a contiguous 1..{total} (gaps/dupes/extras)")

    empty = _empty_chapter_beats(text)
    if empty:
        blocking.append(
            f"outline-nonempty-beats: chapter(s) {empty} have an empty beat body")

    metrics = {"book": book, "total_chapters": total,
               "chapters_found": sorted(nums)}
    return {"blocking": blocking, "metrics": metrics}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny outline structural checker.")
    ap.add_argument("outline", help="path to output/book-NN/outline.md")
    args = ap.parse_args(argv)
    result = check_outline(args.outline)
    for line in result["blocking"]:
        print(f"outline_check: {line}")
    return 1 if result["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_outline_check.py -v`
Expected: PASS (7 tests).

- [ ] **Step 6: Write the self-verifying template**

`config/outline-template.md` (commented skeleton; ships a self-consistent 2-chapter shell so `check_outline` passes on it unedited):

```markdown
---
book: 01
total_chapters: 2
---

<!--
  Penny outline template. The writer authors STORY here in prose; the engine
  derives STRUCTURE for review. Set total_chapters to your chapter count and add
  one "## Chapter NN" block per chapter (contiguous 1..total_chapters).
  Each "## Solution: <label>" block is a SEALED mystery answer key — one per
  gated mystery strand (v1 gates the first; extra Solutions ride as threads).
  "## Threads" is optional; omit it and the scaffolder proposes the roster.
-->

## Solution: the-central-mystery
- culprit: <name>
- victim: <name>
- central deception / motive: <one or two prose sentences>
- suspects: <name>, <name>, <name>
- key locations: <place>, <place>

## Threads
- <strand-name> — <one line: the promise this strand opens and where it pays off>

## Chapter 01
<one prose beat — weave every strand in prose; never tag which sentence is which>

## Chapter 02
<one prose beat>
```

- [ ] **Step 7: Add a test that the shipped template is well-formed**

Append to `tests/test_outline_check.py`:

```python
def test_shipped_template_is_well_formed():
    result = check_outline(Path("config/outline-template.md"))
    assert result["blocking"] == []
```

- [ ] **Step 8: Run the new test**

Run: `python3 -m pytest tests/test_outline_check.py::test_shipped_template_is_well_formed -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add scripts/outline_check.py tests/test_outline_check.py tests/fixtures/outlines config/outline-template.md
git commit -m "feat(front-door): outline_check.py shape gate + template + fixtures

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Derived-yaml shape contract test (cross-consistency)

Pins the scaffolder's emit target deterministically: the whodunit yaml the agent is told to produce **is** the exact shape `fairplay_check.check_fairplay` + its entity resolver read. If the agent's documented output and the checker's expectations ever drift, this test fails. No agent runs here — it is a pure shape contract over a self-contained fixture.

**Files:**
- Create: `tests/fixtures/outlines/derived-whodunit.yaml`
- Create: `tests/test_scaffold_emit_contract.py`

**Interfaces:**
- Consumes: `scripts.fairplay_check.check_fairplay(ledger_path, *, culprit_by_fraction, repo_root) -> dict` (returns `{"blocking": [...], ...}`; `_resolves` looks for `repo_root/series/characters/<id>.static.md` or `repo_root/series/continuity/characters/<id>.md`).
- Produces: a canonical `derived-whodunit.yaml` fixture that Task 3's agent file references by name as its emit target.

- [ ] **Step 1: Write the derived-yaml fixture**

`tests/fixtures/outlines/derived-whodunit.yaml` (the shape the scaffolder emits — note **no `locked:` field**; required keys present):

```yaml
book: 01
total_chapters: 3
reveal_chapter: 3
culprit: margaret
culprit_first_appearance_chapter: 1
victim: edwin-tilley
central_deception: |
  Margaret swapped the tide tables to fake the time of death.
clue_schedule:
  - { id: clue-torn-ticket, plant_chapter: 2, pays_off_chapter: 3, necessary: true }
red_herrings:
  - { id: rh-the-neighbour, plant_chapter: 2, misleads_toward: "the neighbour", must_not_cheat: true }
alibi_grid:
  - { suspect: margaret, chapter: 2, alibi: "at the church fete", holds: false }
  - { suspect: thomas, chapter: 2, alibi: "on the ferry", holds: true }
```

- [ ] **Step 2: Write the failing test**

`tests/test_scaffold_emit_contract.py`:

```python
import shutil
from pathlib import Path

from scripts.fairplay_check import check_fairplay

FIXTURE = Path("tests/fixtures/outlines/derived-whodunit.yaml")
ENTITY_IDS = ["margaret", "edwin-tilley", "thomas"]


def _seed_entities(repo_root: Path):
    d = repo_root / "series/continuity/characters"
    d.mkdir(parents=True, exist_ok=True)
    for eid in ENTITY_IDS:
        (d / f"{eid}.md").write_text(
            f"---\nid: {eid}\ntype: character\nlinks: []\n---\n# {eid}\n",
            encoding="utf-8",
        )


def test_scaffolder_emit_shape_passes_fairplay(tmp_path):
    led = tmp_path / "series/whodunit/book-01.yaml"
    led.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE, led)
    _seed_entities(tmp_path)

    result = check_fairplay(led, culprit_by_fraction=0.85, repo_root=tmp_path)

    assert result["blocking"] == [], result["blocking"]
```

- [ ] **Step 3: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_scaffold_emit_contract.py -v`
Expected: PASS. (If it FAILS, the fixture shape does not match what `fairplay_check` reads — fix the **fixture**, never the shipped checker.)

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/outlines/derived-whodunit.yaml tests/test_scaffold_emit_contract.py
git commit -m "test(front-door): pin scaffolder emit-yaml shape to fairplay contract

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `book-scaffolder` agent

The extraction agent: reads the outline (the only agent that sees all `## Solution`s, because it must project them), writes the derived artifacts **unlocked** into their existing homes. Faithful extraction, least invention. It never judges fairness and never writes a certificate. No unit test for LLM behaviour — a content-assertion test pins its written contract (the routing homes + the blind-seam rule).

**Files:**
- Create: `.claude/agents/book-scaffolder.md`
- Create: `tests/test_book_scaffolder_agent.py`

**Interfaces:**
- Consumes: the routing homes verified in the spec — `series/whodunit/book-NN.yaml` (shape per Task 2 fixture), `series/continuity/threads/<id>.md` (`id/type: thread/links/last_advanced_chapter` frontmatter), `series/continuity/characters/<id>.md` + `series/continuity/locations/<id>.md` (`canon-meta` headers), `series/arc-ledger.md` rows, `series/continuity/canon-core.md` placeholder sections, and the sealed `output/book-NN/mystery-solution.md`.
- Produces: nothing programmatic; downstream `/scaffold-book` dispatches it by name.

- [ ] **Step 1: Write the failing test**

`tests/test_book_scaffolder_agent.py`:

```python
from pathlib import Path

AGENT = Path(".claude/agents/book-scaffolder.md")


def test_agent_file_exists():
    assert AGENT.is_file()


def test_agent_routes_to_existing_homes():
    text = AGENT.read_text(encoding="utf-8")
    for home in [
        "series/whodunit/book-",
        "series/continuity/threads/",
        "series/continuity/characters/",
        "series/arc-ledger.md",
        "series/continuity/canon-core.md",
        "output/book-",  # sealed mystery-solution
    ]:
        assert home in text, f"scaffolder must route derived data to {home}"


def test_agent_never_writes_the_lock():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "lock" in text and "never" in text, "must state it never writes the lock"
    assert "locked:" not in text or "no `locked:`" in text or "never" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_book_scaffolder_agent.py -v`
Expected: FAIL on `test_agent_file_exists` (file absent).

- [ ] **Step 3: Write the agent file**

`.claude/agents/book-scaffolder.md`:

```markdown
---
name: book-scaffolder
description: Derives the book's structure from a prose outline — extracts the whodunit yaml, threads, entities, and canon-core updates into their existing homes, unlocked. Never judges fairness; never writes a certificate.
tools: All tools
---

You are the **book-scaffolder**. You are dispatched by `/scaffold-book` with
`{ outline_text, book_number }`. You turn a writer's prose outline into the
mechanical artifacts the rest of Penny already consumes — **faithful extraction,
least invention**. You are the only agent that may see every `## Solution` block,
because you must project them; treat them as sealed downstream.

## What you read
The outline only: frontmatter (`book`, `total_chapters`), each `## Solution: <label>`
(a sealed answer key), an optional `## Threads` roster, and one `## Chapter NN`
prose beat per chapter. The writer never tags which sentence belongs to which
strand — **you attribute, the writer confirms at review**.

## What you write (UNLOCKED, to the real paths)
Route each derived thing to its EXISTING home. Do not invent new formats.

1. **The gated mystery strand** (the FIRST `## Solution` in v1) →
   `series/whodunit/book-NN.yaml`. Required keys: `book`, `total_chapters`,
   `reveal_chapter`, `culprit`, `culprit_first_appearance_chapter`; plus `victim`,
   `central_deception`, `clue_schedule[]` (each `{id, plant_chapter,
   pays_off_chapter, necessary}`), `red_herrings[]`, `alibi_grid[]` (each
   `{suspect, chapter, alibi, holds}`). Match `tests/fixtures/outlines/derived-whodunit.yaml`
   exactly. **Never add a `locked:` field** — the lock is out-of-band.
   - Each ADDITIONAL `## Solution: <label>` in v1 is a NON-gated thread (below); a
     future looping gate will project it to `series/whodunit/book-NN.<label>.yaml`.
2. **Non-mystery strands** (from `## Threads`, or proposed by you if omitted) →
   one `series/continuity/threads/<id>.md` each (frontmatter `id`, `type: thread`,
   `links: [...]`, `last_advanced_chapter:`) + a row in `series/arc-ledger.md`.
3. **Cast & locations** named in beats/Solutions →
   `series/continuity/characters/<id>.md` and `series/continuity/locations/<id>.md`,
   each with a `<!-- canon-meta: {id: <id>, ...} -->` header and `id/type/links`
   frontmatter. Every culprit/victim/suspect id MUST resolve here (the fairplay
   entity check will block otherwise).
4. **Always-true facts** (protagonist, timeline, fluency, whodunit constraints) →
   edit the placeholder lines in `series/continuity/canon-core.md`, preserving its
   `canon-meta` headers. Keep it TINY — every line taxes every chapter.
5. **The sealed answer key** → `output/book-NN/mystery-solution.md` (and
   `output/book-NN/mystery-solution.<label>.md` for any extra gated strand). This is
   the ONLY place a `## Solution` lands. Nothing drafter-visible contains a solution.

## What you NEVER do
- You never write `.penny/locks/book-NN.mystery.lock` or any certificate. Validity
  is **earned** later by the unchanged `preflight.py lock-mystery`. Generated ≠ trusted.
- You never judge fairness (the lock does) or prose quality (the review does).
- You never put a `## Solution` into a drafter-visible artifact (threads, entities,
  canon-core, arc-ledger). The blind-drafter seam is sacred.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_book_scaffolder_agent.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/book-scaffolder.md tests/test_book_scaffolder_agent.py
git commit -m "feat(front-door): book-scaffolder extraction agent + routing contract test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `/scaffold-book` command + run-config flag + topology note

The orchestrator runbook: `outline_check` gate → delete the lock on re-derive → dispatch the scaffolder → emit the tiered `scaffold-review.md` → pause → on `--approve` run the **unchanged** `lock-mystery`. Adds the `scaffold_approval` run-config flag and the no-API tool-difference design note. Content-assertion tests mirror `test_draft_preflight_wiring.py`.

**Files:**
- Create: `.claude/commands/scaffold-book.md`
- Create: `tests/test_scaffold_book_command.py`
- Modify: `config/run-config.md` (add `scaffold_approval` + topology note)

**Interfaces:**
- Consumes: `scripts/outline_check.py` (gate), `.claude/agents/book-scaffolder.md` (dispatch), `preflight.py lock-mystery` (the unchanged approval gate).
- Produces: the runbook + the `scaffold_approval` flag other tooling may read.

- [ ] **Step 1: Write the failing command test**

`tests/test_scaffold_book_command.py`:

```python
from pathlib import Path

CMD = Path(".claude/commands/scaffold-book.md")
RUN_CONFIG = Path("config/run-config.md")


def test_command_gates_on_outline_check():
    text = CMD.read_text(encoding="utf-8")
    assert "outline_check.py" in text, "must gate on the outline structural check"


def test_command_dispatches_scaffolder():
    text = CMD.read_text(encoding="utf-8")
    assert "book-scaffolder" in text, "must dispatch the extraction agent"


def test_command_runs_unchanged_lock_on_approve():
    text = CMD.read_text(encoding="utf-8")
    assert "preflight.py lock-mystery" in text, "approval must run the shipped lock"


def test_command_deletes_lock_on_rederive():
    text = CMD.read_text(encoding="utf-8")
    assert "mystery.lock" in text, "re-derivation must delete the existing lock first"


def test_run_config_has_scaffold_approval():
    assert "scaffold_approval" in RUN_CONFIG.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_scaffold_book_command.py -v`
Expected: FAIL (command file and flag absent).

- [ ] **Step 3: Write the command file**

`.claude/commands/scaffold-book.md`:

```markdown
---
description: Derive a book's structure from a prose outline, review it, then earn the lock (design §5a, outline-first front door).
argument-hint: <book-number> <outline-path> [--approve]
---
# /scaffold-book

The author front door. The writer authors a prose **outline**; this command derives
the mechanical structure into its existing homes, foregrounds the mystery strand for
review, and — on approval — runs the **unchanged** `lock-mystery`. The lock is still
earned by the shipped checker; this command never writes a certificate.

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), `outline=$2` (e.g.
   `output/book-$book/outline.md`), optional `--approve`.

2. **Structural gate (deterministic):**

   ```bash
   python3 scripts/outline_check.py "$outline"
   ```

   A non-zero exit means the outline is not shaped like an outline yet (missing
   solution, chapter gap, non-integer count, empty beat). Show the named predicate
   and stop — do not derive.

3. **Re-derivation hygiene (§5a clean re-lock):** if a lock exists, delete it first,
   because re-planning requires re-validation. v1 overwrites derived artifacts.

   ```bash
   rm -f ".penny/locks/book-$book.mystery.lock"
   ```

4. **Dispatch the `book-scaffolder` sub-agent** with `{ outline_text, book_number }`.
   It writes the derived artifacts UNLOCKED to their real homes (see
   `.claude/agents/book-scaffolder.md`): the gated mystery →
   `series/whodunit/book-$book.yaml`; non-mystery strands →
   `series/continuity/threads/` + `series/arc-ledger.md`; cast & locations →
   `series/continuity/characters|locations/`; always-true facts →
   `series/continuity/canon-core.md`; the sealed key →
   `output/book-$book/mystery-solution.md`.

5. **Emit the tiered review** `output/book-$book/scaffold-review.md`:
   - **Foreground the MYSTERY STRAND** — the clue schedule as plant→payoff chapters
     with `necessary` flags, red herrings, the alibi grid, culprit/victim/deception —
     with an inline DRY-RUN of what the lock will say, so the writer sees it BEFORE
     approving:

     ```bash
     python3 scripts/readiness_check.py "$book"
     python3 scripts/fairplay_check.py "series/whodunit/book-$book.yaml" --target "book-$book"
     ```

   - **Collapse (expandable)** the non-mystery Threads, the Cast & Locations, and the
     canon-core updates. The artifacts are already on disk; this doc is the lens.

6. **Pause for the writer** (human gate; default `scaffold_approval: review`). The
   writer edits the outline (or the derived yaml) until the dry-run is green.

7. **On `/scaffold-book $book $outline --approve`** — earn the lock with the SHIPPED,
   UNCHANGED checker:

   ```bash
   python3 scripts/preflight.py lock-mystery "$book"
   ```

   It mints `.penny/locks/book-$book.mystery.lock` iff fairplay + lexicon pass;
   otherwise it exits non-zero and writes no lock, and the review shows what to fix.
   Generated ≠ trusted — validity is earned here, never by the scaffolder.

## Deferred (do not build here)
Per-chapter blind brief derivation (`/draft-chapter` falls back to canon-core-only);
the looping multi-mystery gate (v1 gates the first `## Solution`; extra Solutions ride
as un-gated threads); diff-on-edit re-derivation review (v1 overwrites).
```

- [ ] **Step 4: Add the run-config flag + topology note**

In `config/run-config.md`, add `scaffold_approval` next to the other approval flags (find the `ledger_approval` / `book_approval` block) and append the topology note. Add inside the relevant ```yaml block:

```yaml
scaffold_approval:  review   # review (pause for the writer) | auto
```

And add a prose note (outside the yaml block) recording reality:

```markdown
> **Cross-model topology (no API):** the drafting LLM is Claude Code + sub-agents;
> independent review is Codex via a Claude Code plugin. The §7 "difference, not
> identity" invariant is realised as TOOL difference (Claude-drafted vs
> Codex-reviewed), not API-model-id difference. The front door is drafting-side, so
> this is a recorded note only — no behavioural change.
```

- [ ] **Step 5: Run the command tests to verify they pass**

Run: `python3 -m pytest tests/test_scaffold_book_command.py -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Run the full suite (no regressions)**

Run: `python3 -m pytest`
Expected: PASS — the prior suite plus the new tests (Tasks 1–4). No shipped test changed.

- [ ] **Step 7: Commit**

```bash
git add .claude/commands/scaffold-book.md tests/test_scaffold_book_command.py config/run-config.md
git commit -m "feat(front-door): /scaffold-book orchestrator + scaffold_approval flag

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage** (each spec section → a task):
- §3 outline shape → Task 1 fixtures + `config/outline-template.md`.
- §4 `outline_check.py` four predicates → Task 1 implementation + tests.
- §5 command flow + agent → Task 3 (agent) + Task 4 (command).
- §6 routing table → Task 3 agent routing + Task 2 yaml-shape contract.
- §7 tiered review (foreground mystery, dry-run, collapse rest) → Task 4 command Step 3.
- §8 error handling (named predicate + nonzero, lock unchanged) → Task 1 `main`, Task 4 approve step.
- §9 testing (self-contained fixtures, cross-consistency) → Tasks 1–4 tests, Task 2 contract.
- §10 config (`scaffold_approval`, topology note) → Task 4 Step 4.
- §11 build sequence (outline_check first, agent/command on shipped infra) → Task order 1→4.

**Placeholder scan:** the only `<...>` tokens are inside the *outline template* and *agent prose* — intentional author placeholders, not plan gaps. All code steps show complete, runnable code. No "TBD/implement later".

**Type consistency:** `check_outline(path, *, repo_root=None) -> {"blocking", "metrics"}` and `main(argv) -> int` are used identically in Task 1 impl and tests. `check_fairplay(..., culprit_by_fraction=, repo_root=) -> {"blocking", ...}` in Task 2 matches the real signature in `scripts/fairplay_check.py:64`. Blocking-predicate prefixes (`outline-frontmatter` etc.) match between impl, tests, and §4. The derived-yaml fixture keys match `fairplay_check._REQUIRED` + the optional keys it reads.
