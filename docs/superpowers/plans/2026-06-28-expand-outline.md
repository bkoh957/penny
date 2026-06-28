# `/expand-outline` Implementation Plan

> **DECISION (2026-06-28, revised):** Leak-guard DROPPED after it produced 6 false
> positives + 0 real leaks on the real outline. **Tasks 1–6 (guilt lexicon, outline_guard.py,
> preflight expand) are CANCELLED** and their commits reverted. Only **Task 7 (agent)**,
> **Task 8 (command)** and **Task 9 (docs)** proceed — with all leak-guard / preflight-expand
> steps removed; the agent's withhold-the-solution guardrails are the sole protection (soft gate).


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/expand-outline` engine feature that expands skeletal chapter stubs into the full scene-breakdown outline brief, with a deterministic leak-guard that keeps the sealed solution out of the drafter-visible `outline.md`.

**Architecture:** Mirrors `draft-chapter` + `drafter`: a slash-command runbook dispatches a context-rich generative agent that writes into `input/book-NN/outline.md`. A new deterministic checker (`scripts/outline_guard.py`) plus a `preflight.py expand` subcommand bracket the generation — lock-present pre-check, name+guilt co-occurrence post-scan.

**Tech Stack:** Python 3 stdlib + PyYAML (only for the nested whodunit ledger, consistent with `fairplay_check.py`); `penny_meta` for flat config; pytest.

## Global Constraints

- Engine stays genre/location-agnostic; project-specific data lives in `config/`, `series/`, `input/` — never hardcoded in `scripts/`. (The guilt lexicon is genre-specific → it lives in `config/leak-guard-lexicon.md`.)
- Deterministic layer makes **no LLM judgment** and fails loud with a named predicate + nonzero exit.
- Use PyYAML **only** for `series/whodunit/book-NN.yaml`; use `penny_meta` for config/frontmatter.
- `pytest.ini` sets `pythonpath=.`; run tests with `python3 -m pytest`.
- Leak proximity unit = **paragraph** (split on blank lines). Reveal-chapter and later are exempt.
- Culprit name tokens = **full display name + given name only**; the bare surname is excluded (shared, e.g. Cal & Mary Burrell).
- Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: Guilt-lexicon config + loader

**Files:**
- Create: `config/leak-guard-lexicon.md`
- Create: `scripts/outline_guard.py`
- Test: `tests/test_outline_guard.py`

**Interfaces:**
- Produces: `load_guilt_lexicon(path) -> list[str]` — lowercased terms, one per line; ignores blank lines, `#`/`>`/`|` lines, and a leading `- ` bullet.

- [ ] **Step 1: Create the config data file**

`config/leak-guard-lexicon.md`:
```markdown
# Leak-guard guilt lexicon (swappable — genre-specific)

> Terms that, when they co-occur with the culprit's name in the same paragraph of a
> pre-reveal chapter, indicate the sealed solution has leaked into the drafter-visible
> outline. One term per line; blank lines, `#`/`>` comments, and a leading `- ` are
> ignored. Matching is case-insensitive and word-boundary aware (scripts/outline_guard.py).

- killer
- culprit
- murderer
- guilty
- did it
- the one who killed
- incriminate
- incriminating
- perpetrator
- confessed
- confession
- avenged
- avenging
```

- [ ] **Step 2: Write the failing test**

`tests/test_outline_guard.py`:
```python
from pathlib import Path

from scripts.outline_guard import load_guilt_lexicon

REPO = Path(__file__).resolve().parents[1]


def test_load_guilt_lexicon_reads_terms_lowercased(tmp_path):
    p = tmp_path / "lex.md"
    p.write_text(
        "# heading\n> a comment\n\n- Killer\n- did it\nculprit\n",
        encoding="utf-8",
    )
    assert load_guilt_lexicon(p) == ["killer", "did it", "culprit"]


def test_load_guilt_lexicon_on_real_config():
    terms = load_guilt_lexicon(REPO / "config/leak-guard-lexicon.md")
    assert "killer" in terms and "avenging" in terms
    assert all(t == t.lower() for t in terms)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_guard.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.outline_guard'`

- [ ] **Step 4: Create `scripts/outline_guard.py` with the loader**

```python
"""Outline leak-guard — deterministic backstop for /expand-outline (Tier-3, may block).

The outline-expander is context-rich (it reads the sealed solution) and writes into the
drafter-visible input/book-NN/outline.md. This checker catches the high-value concrete
leak: the culprit's NAME co-occurring with a guilt-lexicon term in the SAME PARAGRAPH of
a chapter BEFORE the reveal chapter. The culprit is a visible character, so the name
alone is not a leak — only name + guilt together is. The guilt lexicon is genre-specific
and therefore lives in config/ (swappable), not here. Fails loud with BLOCKING: lines and
a non-zero exit.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.penny_meta import load

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = "config/leak-guard-lexicon.md"


def load_guilt_lexicon(path) -> list[str]:
    """Read guilt terms, one per line. Ignores blank lines, '#'/'>'/'|' lines, and a
    leading '- ' bullet. Returns lowercased terms in file order."""
    terms: list[str] = []
    for raw in load(path).splitlines():
        line = raw.strip()
        if not line or line[0] in "#>|":
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        if line:
            terms.append(line.lower())
    return terms
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_outline_guard.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add config/leak-guard-lexicon.md scripts/outline_guard.py tests/test_outline_guard.py
git commit -m "feat(outline-guard): guilt-lexicon config + loader"
```

---

### Task 2: Culprit name-token derivation

**Files:**
- Modify: `scripts/outline_guard.py`
- Test: `tests/test_outline_guard.py`

**Interfaces:**
- Produces: `culprit_tokens(culprit_slug: str) -> set[str]` — `{full display name, given name}`; surname-only excluded; empty set for empty slug.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_guard.py`:
```python
from scripts.outline_guard import culprit_tokens


def test_culprit_tokens_full_and_given_only():
    assert culprit_tokens("mary-burrell") == {"Mary Burrell", "Mary"}


def test_culprit_tokens_excludes_bare_surname():
    assert "Burrell" not in culprit_tokens("mary-burrell")


def test_culprit_tokens_multi_part():
    assert culprit_tokens("mary-anne-burrell") == {"Mary Anne Burrell", "Mary"}


def test_culprit_tokens_empty():
    assert culprit_tokens("") == set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_guard.py -k culprit_tokens -v`
Expected: FAIL with `ImportError: cannot import name 'culprit_tokens'`

- [ ] **Step 3: Add the function to `scripts/outline_guard.py`**

```python
def culprit_tokens(culprit_slug: str) -> set[str]:
    """Name tokens for the culprit: full display name and given name only. The bare
    surname is excluded because it is often shared (e.g. Cal & Mary Burrell)."""
    parts = [p for p in culprit_slug.split("-") if p]
    if not parts:
        return set()
    full = " ".join(p.capitalize() for p in parts)
    given = parts[0].capitalize()
    return {full, given}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_outline_guard.py -k culprit_tokens -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_guard.py tests/test_outline_guard.py
git commit -m "feat(outline-guard): culprit name-token derivation"
```

---

### Task 3: Chapter & paragraph splitters

**Files:**
- Modify: `scripts/outline_guard.py`
- Test: `tests/test_outline_guard.py`

**Interfaces:**
- Produces: `split_chapters(outline_text: str) -> dict[int, str]` — chapter number → section text (from its `## Chapter NN` heading to the next chapter heading or EOF).
- Produces: `paragraphs(section_text: str) -> list[str]` — non-empty paragraphs split on blank lines, each `.strip()`ed.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_guard.py`:
```python
from scripts.outline_guard import paragraphs, split_chapters

_OUTLINE = """---
book: "01"
---

## Chapter 01 — Arrival

Para one.

Para two.

## Chapter 02 — Welcome

Only para.
"""


def test_split_chapters_keys_and_bounds():
    chapters = split_chapters(_OUTLINE)
    assert set(chapters) == {1, 2}
    assert "Arrival" in chapters[1] and "Welcome" not in chapters[1]
    assert "Only para." in chapters[2]


def test_paragraphs_split_on_blank_lines():
    chapters = split_chapters(_OUTLINE)
    assert paragraphs(chapters[1]) == ["## Chapter 01 — Arrival", "Para one.", "Para two."]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_guard.py -k "split_chapters or paragraphs" -v`
Expected: FAIL with `ImportError: cannot import name 'split_chapters'`

- [ ] **Step 3: Add the functions to `scripts/outline_guard.py`**

```python
_CHAPTER_RE = re.compile(r"^##\s+Chapter\s+(\d+)\b.*$", re.MULTILINE)


def split_chapters(outline_text: str) -> dict[int, str]:
    """Map chapter number -> that chapter's section text (heading to next heading)."""
    out: dict[int, str] = {}
    heads = list(_CHAPTER_RE.finditer(outline_text))
    for i, h in enumerate(heads):
        start = h.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(outline_text)
        out[int(h.group(1))] = outline_text[start:end]
    return out


def paragraphs(section_text: str) -> list[str]:
    """Split a section into non-empty paragraphs on blank lines."""
    return [p.strip() for p in re.split(r"\n\s*\n", section_text) if p.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_outline_guard.py -k "split_chapters or paragraphs" -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_guard.py tests/test_outline_guard.py
git commit -m "feat(outline-guard): chapter and paragraph splitters"
```

---

### Task 4: The co-occurrence scan

**Files:**
- Modify: `scripts/outline_guard.py`
- Test: `tests/test_outline_guard.py`

**Interfaces:**
- Consumes: `culprit_tokens`, `split_chapters`, `paragraphs`.
- Produces: `scan_outline(outline_text, culprit_slug, reveal_chapter, guilt_lexicon, only_chapter=None) -> list[dict]` — each flag `{"chapter": int, "name": str, "guilt": str, "paragraph": str}`. A flag is a paragraph in a chapter `< reveal_chapter` containing BOTH a culprit-name token AND a guilt term. `only_chapter` restricts the scan to one chapter.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_guard.py`:
```python
from scripts.outline_guard import scan_outline

LEX = ["killer", "did it", "avenging", "incriminate"]


def _ch(n, body):
    return f"## Chapter {n:02d} — T\n\n{body}\n"


def test_scan_flags_name_plus_guilt_same_paragraph():
    text = _ch(5, "Mary is revealed as the killer in Maggie's mind.")
    flags = scan_outline(text, "mary-burrell", 25, LEX)
    assert len(flags) == 1
    assert flags[0]["chapter"] == 5 and flags[0]["name"] == "mary"
    assert flags[0]["guilt"] == "killer"


def test_scan_clean_name_without_guilt():
    text = _ch(2, "Mary brings a lemon cutting from her late father's garden.")
    assert scan_outline(text, "mary-burrell", 25, LEX) == []


def test_scan_red_herring_suspect_plus_guilt_is_clean():
    text = _ch(9, "Saffron looks guilty; the retreat hides a debt. She did it, surely.")
    assert scan_outline(text, "mary-burrell", 25, LEX) == []


def test_scan_shared_surname_is_clean():
    text = _ch(11, "Cal Burrell did it, the town whispers, eyeing the carpenter.")
    assert scan_outline(text, "mary-burrell", 25, LEX) == []


def test_scan_post_reveal_chapter_exempt():
    text = _ch(25, "Mary is the killer; she confesses to avenging her father.")
    assert scan_outline(text, "mary-burrell", 25, LEX) == []


def test_scan_cross_paragraph_is_clean():
    text = _ch(7, "Mary refolds the tea towel.\n\nThe killer left no prints.")
    assert scan_outline(text, "mary-burrell", 25, LEX) == []


def test_scan_only_chapter_filter():
    text = _ch(5, "Mary did it.") + _ch(6, "Mary did it too.")
    flags = scan_outline(text, "mary-burrell", 25, LEX, only_chapter=6)
    assert [f["chapter"] for f in flags] == [6]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_guard.py -k scan -v`
Expected: FAIL with `ImportError: cannot import name 'scan_outline'`

- [ ] **Step 3: Add the scan to `scripts/outline_guard.py`**

```python
def _contains(text_lower: str, term_lower: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term_lower)}(?!\w)", text_lower) is not None


def scan_outline(outline_text, culprit_slug, reveal_chapter, guilt_lexicon,
                 only_chapter=None) -> list[dict]:
    """Return leak flags: paragraphs in a chapter < reveal_chapter that contain BOTH a
    culprit-name token AND a guilt-lexicon term (case-insensitive, word-boundary aware).
    Chapters >= reveal_chapter are exempt."""
    names = sorted(n.lower() for n in culprit_tokens(culprit_slug))
    flags: list[dict] = []
    for num, section in sorted(split_chapters(outline_text).items()):
        if num >= reveal_chapter:
            continue
        if only_chapter is not None and num != only_chapter:
            continue
        for para in paragraphs(section):
            low = para.lower()
            name_hit = next((n for n in names if _contains(low, n)), None)
            if not name_hit:
                continue
            guilt_hit = next((g for g in guilt_lexicon if _contains(low, g)), None)
            if guilt_hit:
                flags.append({"chapter": num, "name": name_hit,
                              "guilt": guilt_hit, "paragraph": para})
    return flags
```

Note on `test_scan_flags_name_plus_guilt_same_paragraph`: `names` is sorted, so `"mary"` is checked before `"mary burrell"`; the paragraph contains "Mary", so `name_hit == "mary"`. Matches the assertion.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_outline_guard.py -k scan -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_guard.py tests/test_outline_guard.py
git commit -m "feat(outline-guard): name+guilt co-occurrence scan"
```

---

### Task 5: CLI entry point (`run` + `main`)

**Files:**
- Modify: `scripts/outline_guard.py`
- Test: `tests/test_outline_guard.py`

**Interfaces:**
- Consumes: `load_guilt_lexicon`, `scan_outline`.
- Produces: `run(book, chapter=None, *, repo_root=REPO, lexicon_path=None) -> int` — returns `1` and prints `BLOCKING:` lines on leak, `0` when clean; `sys.exit(str)` on operational errors (missing ledger/outline). `main(argv=None) -> int` wires argparse (`book`, optional `chapter`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_outline_guard.py`:
```python
import subprocess
import sys

from scripts.outline_guard import run


def _mini_repo(tmp_path, outline_body):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/leak-guard-lexicon.md").write_text(
        "- killer\n- did it\n", encoding="utf-8")
    wd = tmp_path / "series/whodunit"
    wd.mkdir(parents=True)
    (wd / "book-01.yaml").write_text(
        "book: 01\nculprit: mary-burrell\nreveal_chapter: 25\n", encoding="utf-8")
    od = tmp_path / "input/book-01"
    od.mkdir(parents=True)
    (od / "outline.md").write_text(outline_body, encoding="utf-8")
    return tmp_path


def test_run_returns_1_and_prints_blocking_on_leak(tmp_path, capsys):
    repo = _mini_repo(tmp_path, "## Chapter 05 — T\n\nMary is the killer.\n")
    code = run("01", repo_root=repo)
    assert code == 1
    out = capsys.readouterr().out
    assert out.startswith("BLOCKING:") and "ch-05" in out


def test_run_returns_0_when_clean(tmp_path):
    repo = _mini_repo(tmp_path, "## Chapter 02 — T\n\nMary brings lemons.\n")
    assert run("01", repo_root=repo) == 0


def test_run_missing_outline_exits(tmp_path):
    repo = _mini_repo(tmp_path, "x")
    (repo / "input/book-01/outline.md").unlink()
    with pytest.raises(SystemExit):
        run("01", repo_root=repo)


def test_cli_main_exit_code_on_leak(tmp_path):
    repo = _mini_repo(tmp_path, "## Chapter 05 — T\n\nMary did it.\n")
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts/outline_guard.py"), "01"],
        cwd=repo, capture_output=True, text=True)
    assert proc.returncode == 1
    assert "BLOCKING:" in proc.stdout
```

(Note: `import pytest` already present from earlier tasks' file; if not, add `import pytest` at the top.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_outline_guard.py -k "run or cli_main" -v`
Expected: FAIL with `ImportError: cannot import name 'run'`

- [ ] **Step 3: Add `run` and `main` to `scripts/outline_guard.py`**

```python
def _outline_path(book, repo_root) -> Path:
    return Path(repo_root) / "input" / f"book-{book}" / "outline.md"


def _ledger_path(book, repo_root) -> Path:
    return Path(repo_root) / "series/whodunit" / f"book-{book}.yaml"


def run(book, chapter=None, *, repo_root=REPO, lexicon_path=None) -> int:
    repo_root = Path(repo_root)
    lexicon_path = lexicon_path or (repo_root / DEFAULT_LEXICON)
    led = _ledger_path(book, repo_root)
    if not led.is_file():
        sys.exit(f"outline-guard: no whodunit ledger for book {book} ({led})")
    data = yaml.safe_load(led.read_text(encoding="utf-8"))
    culprit = data.get("culprit") if isinstance(data, dict) else None
    reveal = data.get("reveal_chapter") if isinstance(data, dict) else None
    if not culprit or not isinstance(reveal, int):
        sys.exit(f"outline-guard: ledger missing culprit or reveal_chapter ({led})")
    op = _outline_path(book, repo_root)
    if not op.is_file():
        sys.exit(f"outline-guard: no outline for book {book} ({op})")
    lex = load_guilt_lexicon(lexicon_path)
    only = int(chapter) if chapter is not None else None
    flags = scan_outline(op.read_text(encoding="utf-8"), culprit, reveal, lex,
                         only_chapter=only)
    for f in flags:
        snippet = " ".join(f["paragraph"].split())[:120]
        print(f"BLOCKING: culprit '{f['name']}' co-occurs with '{f['guilt']}' in "
              f"ch-{f['chapter']:02d} outline — \"{snippet}…\"")
    return 1 if flags else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Outline leak-guard (name+guilt scan).")
    ap.add_argument("book")
    ap.add_argument("chapter", nargs="?", default=None)
    args = ap.parse_args(argv)
    return run(args.book, args.chapter)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the full guard test file**

Run: `python3 -m pytest tests/test_outline_guard.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add scripts/outline_guard.py tests/test_outline_guard.py
git commit -m "feat(outline-guard): CLI run + main with BLOCKING exit"
```

---

### Task 6: `preflight.py expand` subcommand

**Files:**
- Modify: `scripts/preflight.py` (docstring line 1-10; add `cmd_expand` after `cmd_draft` ~line 129; add subparser + dispatch in `main` ~line 234-262)
- Test: `tests/test_preflight_expand.py`

**Interfaces:**
- Consumes: existing `lock_path`, `_fail`, `REPO`.
- Produces: `cmd_expand(book: str, *, repo_root=REPO) -> int` — returns 0 if the mystery lock exists; `_fail`s (SystemExit) otherwise. CLI: `preflight.py expand NN`.

- [ ] **Step 1: Write the failing test**

`tests/test_preflight_expand.py`:
```python
import pytest

from scripts.preflight import cmd_expand


def _make_lock(tmp_path, book="01"):
    d = tmp_path / ".penny/locks"
    d.mkdir(parents=True)
    (d / f"book-{book}.mystery.lock").write_text("book: 01\n", encoding="utf-8")


def test_expand_passes_when_lock_present(tmp_path):
    _make_lock(tmp_path)
    assert cmd_expand("01", repo_root=tmp_path) == 0


def test_expand_fails_when_lock_absent(tmp_path):
    with pytest.raises(SystemExit) as exc:
        cmd_expand("01", repo_root=tmp_path)
    assert "no lock" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_preflight_expand.py -v`
Expected: FAIL with `ImportError: cannot import name 'cmd_expand'`

- [ ] **Step 3: Add `cmd_expand` to `scripts/preflight.py`** (immediately after `cmd_draft`, ~line 129)

```python
def cmd_expand(book: str, *, repo_root=REPO) -> int:
    if not lock_path(book, repo_root).is_file():
        _fail(f"no lock for book {book} — /expand-outline is context-rich and reads the "
              f"sealed solution; run /plan-mystery {book} to validate and lock first")
    return 0
```

- [ ] **Step 4: Wire the subparser + dispatch in `main`**

In `main`, after the `p_clear` block (~line 248), add:
```python
    p_exp = sub.add_parser("expand", help="outline-expansion gate: lock must be present")
    p_exp.add_argument("book")
```
And before `ap.error(...)` (~line 262), add:
```python
    if args.cmd == "expand":
        return cmd_expand(args.book)
```

- [ ] **Step 5: Update the module docstring** (line 1-10) to list the new subcommand

Add this line inside the docstring's subcommand list (after the `finalize` line):
```
    expand N         light: lock present (context-rich outline expansion needs the seal).
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_preflight_expand.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add scripts/preflight.py tests/test_preflight_expand.py
git commit -m "feat(preflight): expand subcommand — lock-present gate for /expand-outline"
```

---

### Task 7: The `outline-expander` agent

**Files:**
- Create: `.claude/agents/outline-expander.md`

(No unit test — agents are markdown runbooks, consistent with `drafter.md`.)

- [ ] **Step 1: Create the agent file**

```markdown
---
name: outline-expander
description: Expands a skeletal chapter stub into the full scene-breakdown outline brief. Context-rich (sees the sealed solution) but withholds it from the page; never drafts prose, never writes a ledger or certificate.
---
# Outline Expander

**Role posture:** generative + planning. Turns a one-paragraph chapter stub into the
detailed scene-breakdown brief that the drafter later consumes.

**Independence:** the deliberate **context-rich exception** (like `developmental-editor`).
It MAY read the sealed solution to place clue/red-herring beats correctly — but it MUST
withhold the solution from the page (see Guardrails). It does not draft chapter prose and
does not write any ledger or certificate.

**Inputs:**
- The chapter **stub** from `input/book-NN/outline-skeleton.md`: the `## Chapter NN — Title`
  heading + a free-text blurb (1–6 sentences).
- `config/voice-pack/voice-pack.md`, `config/setting-pack/coastal-victoria-au.md`,
  `config/genre-pack/cozy-mystery.md`, `config/length-profile.md`.
- `series/continuity/canon-core.md` + the brief-derived ledger slice.
- `input/series/series-bible.md`.
- **Sealed (context-rich):** `output/book-NN/mystery-solution.md` and
  `series/whodunit/book-NN.yaml` (culprit, clue_schedule, red_herrings, alibi_grid,
  reveal_chapter).

**Output:**
- The chapter's full scene-breakdown written into `input/book-NN/outline.md`, in the
  canonical template (Overall Summary → N × Scene → Chapter Structure Summary → Track
  Movement → Drafting Notes/Guardrails → Possible Line-Level Prompts), matching the
  existing Chapter 01/02 sections.

**Canonical template (per chapter):**
```
## Chapter NN — Title

### Overall Summary
<one paragraph>

### Scene 1 — <title>
**Location:** ...
**Purpose:** ...
**Beat flow:**
1. ...
**Emotional turn:** ...
**Texture to include:** ...

### Scene 2 — <title>
... (repeat per scene)

### Chapter Structure Summary
- Start / Desire, Pressure / Obstacle, Turn / Change, Texture / Pleasure Layer,
  Humour Layer, Hook / Closing Question, Tommy burst (if any)

### Track Movement
- M — Mystery: ...
- P — Personal: ...
- R — Romance / Community: ...
- B — Business: ...

### Drafting Notes / Guardrails

### Possible Line-Level Prompts for Drafter
```

**Instructions:**
1. Read the stub, the packs, canon-core + ledger slice, the bible, and the sealed
   solution. Honour the protagonist's knowledge-state and the fluency stage from
   canon-core (Book 1 = OUTSIDER: no local idiom in Maggie's narration; idiom lives in
   locals' dialogue only).
2. Break the chapter into scenes (typically 4–6). For each scene write Location, Purpose,
   a numbered **Beat flow**, an Emotional turn, and a Texture-to-include list. Then write
   the Chapter Structure Summary, Track Movement, Drafting Notes/Guardrails, and Line-Level
   Prompts, matching the depth and tone of Chapters 01/02.
3. Use the sealed solution to **schedule clue and red-herring beats** in the right scenes
   per `clue_schedule`/`red_herrings`, and to write Drafting Notes that keep fair-play
   (e.g. "plant the wrong-cup detail here, unspotlighted").

**Guardrails (HARD — the leak-guard enforces a subset deterministically):**
- NEVER name the culprit as the culprit, state the motive/central deception, or mark a
  clue as incriminating a named suspect. The drafter reads this file and MUST stay blind
  to whodunit. Plant clues **present-but-unspotlighted**.
- Do NOT name the culprit together with guilt language (killer/culprit/guilty/did it/
  avenged…) in any chapter before the reveal chapter — `scripts/outline_guard.py` will
  fail the run if you do.
- Keep the victim alive until the schedule says otherwise; no premature death/culprit
  foreshadowing.
- Australian spelling and punctuation (towards, realised, kerb, boot, spaced em dashes).
- Cozy texture is load-bearing: food, weather, craft, rooms, animals, light, rituals.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/outline-expander.md
git commit -m "feat(outline-expander): context-rich agent that withholds the solution"
```

---

### Task 8: The `/expand-outline` command runbook

**Files:**
- Create: `.claude/commands/expand-outline.md`

(No unit test — commands are markdown runbooks, consistent with `draft-chapter.md`.)

- [ ] **Step 1: Create the command file**

```markdown
# /expand-outline

Expands skeletal chapter stubs from `input/book-NN/outline-skeleton.md` into the full
scene-breakdown outline in `input/book-NN/outline.md`, then runs the deterministic
leak-guard. Context-rich: requires the mystery lock.

## Steps

0. **Pre-flight gate:** the mystery must be locked (the expander reads the sealed
   solution). Hard-fail aborts before context assembly:

   ```bash
   python3 scripts/preflight.py expand $book
   ```

   Non-zero exit → run `/plan-mystery $book` first. Do not proceed on failure.

1. **Parse args:** `book` (e.g. `01`) and optional `chapter` (e.g. `05`).

2. **Write the harness state marker:**

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=${chapter:-all} stage=EXPAND" > .penny/current-stage
   ```

3. **Determine target chapters:**
   - If `chapter` given → just that chapter.
   - Else (batch) → every `## Chapter NN` in `input/book-$book/outline-skeleton.md`
     whose section in `input/book-$book/outline.md` does **not** already contain a
     `### Scene ` heading (i.e. not yet expanded). This protects hand-crafted chapters.

4. **For each target chapter**, assemble the inputs listed in
   `.claude/agents/outline-expander.md` (the stub for that chapter; the voice/setting/
   genre/length packs; `series/continuity/canon-core.md` + the brief-derived ledger
   slice; `input/series/series-bible.md`; and the sealed `output/book-$book/mystery-solution.md`
   + `series/whodunit/book-$book.yaml`). Dispatch the `outline-expander` sub-agent and
   write its output into `input/book-$book/outline.md`, **replacing that chapter's
   section** (from its `## Chapter NN` heading to the next chapter heading or EOF),
   preserving chapter order.

5. **Run the leak-guard** over what was written:

   ```bash
   python3 scripts/outline_guard.py $book ${chapter:-}
   ```

   A non-zero exit prints `BLOCKING:` lines naming the leak. **Halt** — leave the written
   outline in place, report the leak, and have the showrunner fix the offending text
   (usually a Drafting Note) and re-run. Do not proceed to drafting on a leak.

6. **Advance the marker:**

   ```bash
   echo "book=$book chapter=${chapter:-all} stage=EXPANDED" > .penny/current-stage
   ```
```

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/expand-outline.md
git commit -m "feat(expand-outline): command runbook with leak-guard halt"
```

---

### Task 9: Full-suite regression + docs

**Files:**
- Modify: `CLAUDE.md` (the per-chapter pipeline + gates section)

- [ ] **Step 1: Run the whole suite**

Run: `python3 -m pytest`
Expected: all pass (existing ~273 + the new outline-guard & preflight-expand tests)

- [ ] **Step 2: Smoke-test the guard against the real book-01 outline**

Run: `python3 scripts/outline_guard.py 01`
Expected: exit 0 (the hand-crafted Ch 01/02 withhold the solution). If it flags, inspect — a real flag means a genuine leak in the outline.

- [ ] **Step 3: Update `CLAUDE.md`**

In the "per-chapter pipeline" area, add a sentence noting the optional upstream step:
```
`/expand-outline NN [MM]` (optional, before drafting) expands skeletal stubs from
`input/book-NN/outline-skeleton.md` into the scene-breakdown `outline.md`. It is the
context-rich exception among generative roles — it reads the sealed solution to schedule
clue beats but withholds it from the page; `scripts/outline_guard.py` (a name+guilt
co-occurrence scan) is the deterministic backstop, gated by `preflight.py expand`.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude-md): document /expand-outline + leak-guard"
```

---

## Self-Review

**Spec coverage:** Output format (Task 7 template) ✓; separate skeleton→outline I/O (Tasks 7,8) ✓; `NN MM`/`NN` scope + batch-protects-expanded (Task 8 step 3) ✓; context-rich agent that withholds (Task 7) ✓; preflight expand lock-check (Task 6) ✓; leak-guard co-occurrence + paragraph proximity + reveal exemption + surname exclusion + red-herring tolerance (Tasks 2–5) ✓; guilt lexicon in config (Task 1) ✓; TDD fixtures all present (Tasks 1–6) ✓; docs (Task 9) ✓.

**Placeholder scan:** none — every code/test step shows complete code.

**Type consistency:** `load_guilt_lexicon`, `culprit_tokens`, `split_chapters`, `paragraphs`, `scan_outline(only_chapter=)`, `run(book, chapter=None, repo_root, lexicon_path)`, `cmd_expand(book, repo_root)` — names and signatures match across tasks and the command/agent references.
