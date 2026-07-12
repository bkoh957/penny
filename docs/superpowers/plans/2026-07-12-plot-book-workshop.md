# Plotting Workshop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the plotting workshop — the wired outline format, its deterministic checker (`tension_check.py`), the stage machinery (`plot_stage.py`), the `/plot-book` command with three new agents, the cozy genre-pack beat sheet + fan persona, and the lock's tension gate with recorded waivers.

**Architecture:** One shared dependency-free parser (`penny_wiring.py`) feeds two deterministic scripts (`tension_check.py` for the seven named checks; `plot_stage.py` for save-point status, fingerprint stamping, and the blind reader's copy). `preflight.py lock-mystery` gains a third validator with per-check `--waive`. Orchestration is a single resumable runbook (`commands/plot-book.md`) dispatching three new role-scoped agents. Genre knowledge (beat positions, fan persona) lives in the cozy genre pack.

**Tech Stack:** Python 3 stdlib + `scripts/penny_meta.py` for all outline parsing (never PyYAML); PyYAML only for `beat-sheet.yaml` and the whodunit ledger (existing precedent). pytest with `tests/fixtures/`.

**Spec:** `docs/superpowers/specs/2026-07-12-plot-book-workshop-design.md` — read it before starting any task.

## Global Constraints

- **Dependency-split rule:** outline/frontmatter parsing uses `scripts/penny_meta.py` only. PyYAML is allowed only for `beat-sheet.yaml` and `series/whodunit/book-NN.yaml`.
- **Named predicates, loud failure:** every checker finding starts with its check id (`orphan-chapter:`, `dropped-question:`, `phantom-answer:`, `dead-stretch:`, `broken-hook:`, `starved-thread:`, `off-mark-beat:`, plus the hygiene id `wiring-parse:`). Nonzero exit on findings; 0 = evaluated clean.
- **Wiring is optional per book, all-or-nothing:** an outline "has wiring" iff any chapter carries a `**Because:**` or `**Opens:**` line; unwired outlines are skipped by the tension gate everywhere (exit 0, printed note). Book 1 of the live series must remain valid.
- **Certificates stay out-of-band:** no `locked:`/`validated:` field ever goes inside gated data. Waivers are recorded in the lock certificate body only.
- **Engine stays genre-blind:** no cozy-specific names in `scripts/`, `commands/`, `agents/`. Numbers and personas live in `genres/cozy-mystery/`.
- Question ids match `q-[a-z0-9][a-z0-9-]*`. Wiring lines are bold list-item fields (`- **Because:** …`), same style as the existing template fields.
- Run the full suite (`python3 -m pytest`) before every commit; all pre-existing tests must stay green.

## File Structure

| File | Responsibility |
|---|---|
| `scripts/penny_wiring.py` (new) | THE wired-format parser: chapters + wiring lines, turning points. Shared by both scripts below — no forked parsing. |
| `scripts/tension_check.py` (new) | The seven checks + beat-sheet/whodunit loading + CLI. |
| `scripts/plot_stage.py` (new) | Stage status, `built_from_*` fingerprint stamping, reader's-copy rendering + CLI. |
| `scripts/preflight.py` (modify) | `cmd_lock_mystery` gains the tension gate + `--waive`. |
| `scripts/penny_genre.py` (modify) | Validate optional manifest keys `beat_sheet`, `fan_persona`. |
| `genres/cozy-mystery/beat-sheet.yaml` (new) | Cozy beat positions, track dark-gap limits, question floor. |
| `genres/cozy-mystery/personas/genre-fan.md` (new) | The blind cozy-fan persona. |
| `genres/cozy-mystery/genre.yaml` (modify) | + `beat_sheet:`, `fan_persona:` keys. |
| `agents/plot-proposer.md`, `agents/chapter-weaver.md`, `agents/outline-fan.md` (new) | The three workshop agents with written output contracts. |
| `commands/plot-book.md` (new) | The resumable runbook. |
| `config/outline-template.md` (modify) | Wiring lines documented in the template. |
| `CLAUDE.md`, `genres/cozy-mystery/ideation-prompt.md` (modify) | Docs: third front door, dependency-split note, portaprompt pointer. |
| Tests | `tests/test_penny_wiring.py`, `tests/test_tension_check.py`, `tests/test_plot_stage.py`, `tests/test_plot_agents.py`, `tests/test_plot_book_command.py`, additions to `tests/test_preflight.py`, `tests/test_penny_genre.py`; fixtures under `tests/fixtures/outlines/` and `tests/fixtures/plot/`. |

---

### Task 1: `penny_wiring.py` — wired-chapter parser

**Files:**
- Create: `scripts/penny_wiring.py`
- Create: `tests/fixtures/outlines/wired-clean.md`
- Test: `tests/test_penny_wiring.py`

**Interfaces:**
- Consumes: `scripts.penny_meta.parse_frontmatter` (existing).
- Produces: `parse_wired_chapters(text: str) -> list[dict]` — each dict has keys `num:int, title:str, because:str|None, because_ch:int|None, opens:list[tuple[qid,phrasing]], closes:list[qid], carries:list[qid], hook_q:str|None, hook_raw:str|None, tracks:dict[str,str], errors:list[str]`, sorted by `num`. `has_wiring(chapters) -> bool`. Module-level regexes `HEADING_RE, CHAPTER_RE, FIELD_RE, QID_RE` and helper `split_id(value) -> tuple[str, str]` (public — Tasks 4–9 import them).

- [ ] **Step 1: Write the clean fixture** `tests/fixtures/outlines/wired-clean.md` (used by most later tasks — 6 chapters, fully wired, no violations):

```markdown
---
book: 01
total_chapters: 6
---

## Solution: the-central-mystery
- culprit: Mary
- victim: Neil

## Chapter 01 — Arrival

### Chapter Summary
Maggie arrives; the town GP is found dead.

### Chapter Structure
- **Turn / Change:** The welcome curdles; Maggie is a stranger near a death.
- **Hook:** q-who-killed-neil — the doctor is dead on his own kitchen floor.
- **Because:** opening
- **Opens:** q-who-killed-neil — who killed the town GP?

### Track Movement
- **M:** Body found.
- **P:** Doubt about the move.
- **R:** Meets Cal.
- **B:** Shop unopened.

## Chapter 02 — The Cake Tin

### Chapter Summary
Mary's kindness has edges.

### Chapter Structure
- **Turn / Change:** Mary lies about the cemetery box; the kindness now reads as watchfulness.
- **Hook:** q-what-mary-hides — the tin comes back, the papers do not.
- **Because:** ch 01 — the death puts every welcome under suspicion.
- **Opens:** q-what-mary-hides — why does Mary guard the workshop papers?

### Track Movement
- **M:** Mary's lie observed.
- **P:** None.
- **R:** None.
- **B:** First customer.

## Chapter 03 — The Missing Key

### Chapter Summary
The kiln-room key vanishes.

### Chapter Structure
- **Turn / Change:** The theft is aimed at Maggie; someone wants her looking guilty.
- **Hook:** q-key-theft — who wanted the kiln room open, and when?
- **Because:** ch 02 — Mary's lie sends Maggie looking where she shouldn't.
- **Opens:** q-key-theft — who took the kiln-room key?

### Track Movement
- **M:** Key theft tied to the cottage.
- **P:** None.
- **R:** Cal fixes the lock.
- **B:** None.

## Chapter 04 — Artie's Hint

### Chapter Summary
The key returns; Artie says too much.

### Chapter Structure
- **Turn / Change:** The key was borrowed to copy, not to steal; the game is longer than it looked.
- **Hook:** q-elspeth-vale — Artie has seen Maggie's kind of sight before.
- **Because:** ch 03 — the key theft forces Maggie to ask who had access.
- **Opens:** q-elspeth-vale — what does Artie know about the Too-Much?
- **Closes:** q-key-theft

### Track Movement
- **M:** Copy-not-theft deduction.
- **P:** Maggie trusts her sight.
- **R:** None.
- **B:** Commission offer.

## Chapter 05 — The Kitchen Truth

### Chapter Summary
The reveal: Mary, the letter, the mercy mistaken for murder.

### Chapter Structure
- **Turn / Change:** Mary is taken; the truth costs the chosen family its centre.
- **Hook:** q-elspeth-vale — Artie's door is still open.
- **Because:** ch 04 — the copied key places Mary in the cottage.
- **Closes:** q-who-killed-neil
- **Closes:** q-what-mary-hides

### Track Movement
- **M:** Reveal and arrest.
- **P:** Maggie owns her gift.
- **R:** Cal wounded but present.
- **B:** Shop stays open through it.

## Chapter 06 — After the Rain

### Chapter Summary
Order returns, warmer and more honest.

### Chapter Structure
- **Turn / Change:** The town re-forms around the loss; Maggie belongs.
- **Hook:** q-elspeth-vale — a name on an envelope, unopened.
- **Because:** ch 05 — the arrest leaves a hole the community must close.
- **Carries:** q-elspeth-vale

### Track Movement
- **M:** Aftermath.
- **P:** Settled.
- **R:** First dinner.
- **B:** Teaching space planned.
```

- [ ] **Step 2: Write the failing tests** `tests/test_penny_wiring.py`:

```python
from pathlib import Path

from scripts.penny_wiring import parse_wired_chapters, has_wiring, split_id

FIX = Path("tests/fixtures/outlines")


def _clean():
    return parse_wired_chapters((FIX / "wired-clean.md").read_text(encoding="utf-8"))


def test_parses_all_chapters_in_order():
    chs = _clean()
    assert [c["num"] for c in chs] == [1, 2, 3, 4, 5, 6]
    assert chs[0]["title"] == "Arrival"


def test_because_parsed():
    chs = _clean()
    assert chs[0]["because"] == "opening" and chs[0]["because_ch"] is None
    assert chs[1]["because_ch"] == 1


def test_opens_closes_carries_hook():
    chs = _clean()
    assert chs[0]["opens"] == [("q-who-killed-neil", "who killed the town GP?")]
    assert chs[4]["closes"] == ["q-who-killed-neil", "q-what-mary-hides"]
    assert chs[5]["carries"] == ["q-elspeth-vale"]
    assert chs[0]["hook_q"] == "q-who-killed-neil"


def test_tracks_parsed():
    chs = _clean()
    assert chs[1]["tracks"]["P"] == "None"
    assert chs[0]["tracks"]["M"] == "Body found."


def test_has_wiring_true_on_clean_false_on_legacy():
    assert has_wiring(_clean()) is True
    legacy = (FIX / "well-formed.md").read_text(encoding="utf-8")
    assert has_wiring(parse_wired_chapters(legacy)) is False


def test_bad_question_id_lands_in_errors():
    text = ("---\nbook: 01\ntotal_chapters: 1\n---\n\n## Solution: x\n- culprit: A\n\n"
            "## Chapter 01 — T\nbody\n- **Because:** opening\n- **Opens:** WhoDidIt — bad id\n")
    chs = parse_wired_chapters(text)
    assert chs[0]["errors"] and "WhoDidIt" in chs[0]["errors"][0]


def test_split_id():
    assert split_id("q-x — why?") == ("q-x", "why?")
    assert split_id("q-x") == ("q-x", "")
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_penny_wiring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_wiring'`

- [ ] **Step 4: Implement** `scripts/penny_wiring.py`:

```python
"""Parser for the WIRED outline format (plot-book workshop spec §5).

Chapters keep their existing fields; wiring lines are bold list-item fields in
the same style as the template's own:

  - **Because:** ch 06 — reason        (or, chapter 1 only: opening)
  - **Opens:** q-slug — phrasing       (repeatable, one question per line)
  - **Closes:** q-slug                 (repeatable)
  - **Carries:** q-slug                (repeatable; deliberately open past book end)
  - **Hook:** q-slug — prose           (id required only on wired outlines)

Dependency-free (penny_meta only — never PyYAML). This module is THE wired-field
parser, shared by tension_check.py and plot_stage.py: no forked conventions.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter  # noqa: F401  (re-exported for callers)

HEADING_RE = re.compile(r"^##\s+(.*?)\s*$", re.MULTILINE)
CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)(?:\s*[—-]\s*(.*))?$")
FIELD_RE = re.compile(r"^\s*-\s+\*\*(Because|Opens|Closes|Carries|Hook):\*\*\s*(.*)$")
QID_RE = re.compile(r"^q-[a-z0-9][a-z0-9-]*$")
TRACK_RE = re.compile(r"^\s*-\s+\*\*([A-Z]):\*\*\s*(.*)$")
TP_FIELD_RE = re.compile(r"^\s*-\s+\*\*(Beat|Chapter|Breaks):\*\*\s*(.*)$")
_BECAUSE_CH_RE = re.compile(r"^ch\s*(\d+)\b")


def split_id(value: str) -> tuple[str, str]:
    """'q-x — phrasing' -> ('q-x', 'phrasing'); 'q-x' -> ('q-x', '')."""
    parts = re.split(r"\s+[—-]\s+", value.strip(), maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def parse_wired_chapters(text: str) -> list[dict]:
    chapters: list[dict] = []
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        ch = {"num": int(cm.group(1)), "title": (cm.group(2) or "").strip(),
              "because": None, "because_ch": None, "opens": [], "closes": [],
              "carries": [], "hook_q": None, "hook_raw": None, "tracks": {},
              "errors": []}
        for line in text[start:end].splitlines():
            fm = FIELD_RE.match(line)
            if fm:
                field, value = fm.group(1), fm.group(2).strip()
                if field == "Because":
                    ch["because"] = value
                    bm = _BECAUSE_CH_RE.match(value)
                    if bm:
                        ch["because_ch"] = int(bm.group(1))
                elif field == "Hook":
                    ch["hook_raw"] = value
                    qid, _ = split_id(value)
                    if QID_RE.match(qid):
                        ch["hook_q"] = qid
                else:  # Opens / Closes / Carries
                    qid, phrasing = split_id(value)
                    if not QID_RE.match(qid):
                        ch["errors"].append(f"{field}: bad question id {qid!r}")
                    elif field == "Opens":
                        ch["opens"].append((qid, phrasing))
                    else:
                        ch[field.lower()].append(qid)
                continue
            tm = TRACK_RE.match(line)
            if tm:
                ch["tracks"][tm.group(1)] = tm.group(2).strip()
        chapters.append(ch)
    chapters.sort(key=lambda c: c["num"])
    return chapters


def has_wiring(chapters: list[dict]) -> bool:
    """Spec §5: an outline has wiring iff any chapter carries Because or Opens."""
    return any(c["because"] is not None or c["opens"] for c in chapters)
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/test_penny_wiring.py -v`
Expected: all PASS. Then `python3 -m pytest` — full suite green.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_wiring.py tests/test_penny_wiring.py tests/fixtures/outlines/wired-clean.md
git commit -m "feat(wiring): the shared wired-outline parser"
```

---

### Task 2: `penny_wiring.parse_turning_points`

**Files:**
- Modify: `scripts/penny_wiring.py` (append one function)
- Create: `tests/fixtures/plot/turning-points-good.md`
- Test: `tests/test_penny_wiring.py` (append)

**Interfaces:**
- Produces: `parse_turning_points(text: str) -> dict` — `{"total_chapters": int|None, "points": [{"title": str, "beat": str|None, "chapter": int|None}]}`. Uses `TP_FIELD_RE` from Task 1.

- [ ] **Step 1: Write the fixture** `tests/fixtures/plot/turning-points-good.md` (positions chosen to sit inside the Task 5 fixture beat sheet's windows for a 6-chapter book, reveal at 5):

```markdown
---
total_chapters: 6
---

## TP-1 — The body in the kitchen
- **Beat:** inciting-death
- **Chapter:** 2
- **Breaks:** the welcome curdles into suspicion.

## TP-2 — The copied key
- **Beat:** midpoint-reversal
- **Chapter:** 3
- **Breaks:** the theft was preparation, not theft — the game is longer.

## TP-3 — The letter surfaces
- **Beat:** dark-night
- **Chapter:** 5
- **Breaks:** the truth will cost the chosen family its centre.

## TP-4 — The kitchen truth
- **Beat:** reveal
- **Chapter:** 5
- **Breaks:** Mary, the letter, the mercy mistaken for murder.
```

- [ ] **Step 2: Append failing tests** to `tests/test_penny_wiring.py`:

```python
from scripts.penny_wiring import parse_turning_points

PLOT = Path("tests/fixtures/plot")


def test_turning_points_parsed():
    tp = parse_turning_points((PLOT / "turning-points-good.md").read_text(encoding="utf-8"))
    assert tp["total_chapters"] == 6
    assert tp["points"][0] == {"title": "TP-1 — The body in the kitchen",
                               "beat": "inciting-death", "chapter": 2}
    assert len(tp["points"]) == 4


def test_turning_points_tolerates_missing_fields():
    tp = parse_turning_points("---\ntotal_chapters: 4\n---\n\n## TP-1 — Untagged\n- **Breaks:** x\n")
    assert tp["points"][0]["beat"] is None and tp["points"][0]["chapter"] is None
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_penny_wiring.py -v -k turning`
Expected: FAIL — `ImportError: cannot import name 'parse_turning_points'`

- [ ] **Step 4: Implement** — append to `scripts/penny_wiring.py`:

```python
def parse_turning_points(text: str) -> dict:
    """Parse plot/turning-points.md: frontmatter total_chapters + one ## section
    per turning point carrying **Beat:** / **Chapter:** bold list fields."""
    fm = parse_frontmatter(text)
    total_raw = fm.get("total_chapters")
    total = int(total_raw) if isinstance(total_raw, str) and total_raw.strip().isdigit() else None
    points: list[dict] = []
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        point = {"title": m.group(1), "beat": None, "chapter": None}
        for line in text[start:end].splitlines():
            tm = TP_FIELD_RE.match(line)
            if not tm:
                continue
            field, value = tm.group(1), tm.group(2).strip()
            if field == "Beat":
                point["beat"] = value or None
            elif field == "Chapter" and value.isdigit():
                point["chapter"] = int(value)
        points.append(point)
    return {"total_chapters": total, "points": points}
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/test_penny_wiring.py -v` — all PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_wiring.py tests/test_penny_wiring.py tests/fixtures/plot/turning-points-good.md
git commit -m "feat(wiring): turning-points parser"
```

---

### Task 3: Genre pack — `beat-sheet.yaml`, fan persona, manifest keys

**Files:**
- Create: `genres/cozy-mystery/beat-sheet.yaml`
- Create: `genres/cozy-mystery/personas/genre-fan.md`
- Modify: `genres/cozy-mystery/genre.yaml`
- Modify: `scripts/penny_genre.py`
- Test: `tests/test_penny_genre.py` (append)

**Interfaces:**
- Produces: `genre.yaml` keys `beat_sheet: beat-sheet.yaml`, `fan_persona: personas/genre-fan.md` (both optional in the manifest schema; when present the file must exist in the genre dir). Runtime resolution of the beat sheet is via the existing overlay (`penny_paths.config_path("beat-sheet.yaml")` hits the genre tier) — no new resolver.

- [ ] **Step 1: Append failing tests** to `tests/test_penny_genre.py` (follow the file's existing style for building a manifest dict; use the real cozy dir for the happy path):

```python
def test_cozy_manifest_declares_beat_sheet_and_fan_persona():
    m = penny_genre.load_manifest("cozy-mystery")
    assert m["beat_sheet"] == "beat-sheet.yaml"
    assert m["fan_persona"] == "personas/genre-fan.md"


def test_optional_file_keys_must_exist_when_present(tmp_path):
    gdir = tmp_path / "genres" / "test-genre"
    gdir.mkdir(parents=True)
    (gdir / "conventions.md").write_text("x", encoding="utf-8")
    manifest = {
        "genre": "test-genre", "conventions": "conventions.md",
        "planning": {"command": "plan-mystery", "artifact": "series/whodunit/book-{NN}.yaml",
                      "validator": "fairplay", "lock": "mystery"},
        "inspectors": [], "gates": [], "rubrics": [], "tracks": [],
        "beat_sheet": "beat-sheet.yaml",
    }
    from scripts import penny_paths
    errs = penny_genre.validate_manifest(manifest, gdir, plugin_root=penny_paths.plugin_root())
    assert any("beat_sheet" in e for e in errs)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_penny_genre.py -v`
Expected: the two new tests FAIL (`KeyError: 'beat_sheet'` and no error emitted).

- [ ] **Step 3: Create** `genres/cozy-mystery/beat-sheet.yaml` (spec §6 seed values, tunable during Book 2):

```yaml
# Cozy-mystery dramatic shape — consumed by tension_check.py (off-mark-beat,
# starved-thread, dead-stretch) and read by plot-proposer at the spine stage.
# Fractions are of total_chapters, computed — never hand-numbered.
beats:
  - { id: inciting-death,    by_fraction: 0.15 }
  - { id: midpoint-reversal, at_fraction: 0.50, tolerance: 0.08 }
  - { id: dark-night,        window: [0.70, 0.85] }
  - { id: reveal,            from: whodunit }
tracks:
  max_dark_gap: { M: 2, P: 4, R: 4, B: 5 }
questions:
  min_open_before_reveal: 1
```

- [ ] **Step 4: Create** `genres/cozy-mystery/personas/genre-fan.md`:

```markdown
---
name: cozy-genre-fan
driver: comfort-tone
primary_axes: [engagement_curve, whodunit_guess, would_buy_next]
---
# Outline Beta — The Cozy Fan

You are a devoted cozy-mystery reader flipping through a book's chapter plan the
way you'd sample a new series in a shop. You have ONLY the reader's copy — you do
not know the solution, and you must never try to look for one outside the text.

React as a reader, never a critic. You are here for a murder puzzle inside a
warm, socially intimate world: you want clues you could theoretically solve, a
community worth returning to, food and craft and gentle humour, and justice that
restores rather than darkens.

Report, in order:
- Chapter-by-chapter interest, 1–5, one line each — where you leaned in, where
  you skimmed.
- Any chapter where you would have put it down, and why, in your own words.
- Who you think did it, and the chapter where you first felt sure.
- Would you buy this book off this story? yes / no, one sentence why.
```

- [ ] **Step 5: Modify** `genres/cozy-mystery/genre.yaml` — append two lines at the end:

```yaml
beat_sheet: beat-sheet.yaml
fan_persona: personas/genre-fan.md
```

- [ ] **Step 6: Modify** `scripts/penny_genre.py` — add after the `MANIFEST_KEYS` line:

```python
_OPTIONAL_FILE_KEYS = ("beat_sheet", "fan_persona")
```

and inside `validate_manifest`, after the conventions check block:

```python
    for key in _OPTIONAL_FILE_KEYS:
        val = manifest.get(key)
        if val is not None and not (genre_dir / str(val)).is_file():
            errs.append(f"{key} '{val}' not found in {genre_dir}")
```

- [ ] **Step 7: Run to verify pass**

Run: `python3 -m pytest tests/test_penny_genre.py -v` — all PASS. Then full suite.

- [ ] **Step 8: Commit**

```bash
git add genres/cozy-mystery scripts/penny_genre.py tests/test_penny_genre.py
git commit -m "feat(cozy): beat-sheet.yaml + genre-fan persona + optional manifest keys"
```

---

### Task 4: `tension_check.py` — graph checks

**Files:**
- Create: `scripts/tension_check.py`
- Create: `tests/fixtures/outlines/wired-orphan.md`, `wired-dropped-question.md`, `wired-phantom-answer.md`, `wired-broken-hook.md`
- Test: `tests/test_tension_check.py`

**Interfaces:**
- Consumes: `penny_wiring.parse_wired_chapters`, `has_wiring`, `parse_frontmatter`.
- Produces: `check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None, whodunit_path=None) -> dict` with keys `wired: bool`, `blocking: list[str]`, `metrics: dict`. (The two extra kwargs are wired in Tasks 5–6; accept-and-ignore-None from day one so the signature never changes.) Check-id prefixes as in Global Constraints.

- [ ] **Step 1: Write the four broken fixtures.** Each is minimal (3 chapters) and violates exactly the check under test where possible; a genuine dead book necessarily co-fires other checks, so tests assert the target predicate is PRESENT, not exclusive. Shared skeleton per chapter: Summary line, Hook, Because, wiring, tracks all-active (`- **M:** x.` etc. for M/P/R/B).

`wired-orphan.md` — ch 2 points at a nonexistent chapter:

```markdown
---
book: 01
total_chapters: 3
---

## Solution: x
- culprit: A

## Chapter 01 — One
### Chapter Structure
- **Hook:** q-a — what happened?
- **Because:** opening
- **Opens:** q-a — what happened?
### Track Movement
- **M:** x.
- **P:** x.
- **R:** x.
- **B:** x.

## Chapter 02 — Two
### Chapter Structure
- **Hook:** q-a — still open.
- **Because:** ch 05 — impossible; no such chapter.
### Track Movement
- **M:** x.
- **P:** x.
- **R:** x.
- **B:** x.

## Chapter 03 — Three
### Chapter Structure
- **Hook:** q-b — a new door.
- **Because:** ch 02 — follows on.
- **Opens:** q-b — a new door?
- **Closes:** q-a
- **Carries:** q-b
### Track Movement
- **M:** x.
- **P:** x.
- **R:** x.
- **B:** x.
```

`wired-dropped-question.md` (`q-b` opened, never closed or carried):

```markdown
---
book: 01
total_chapters: 3
---

## Solution: x
- culprit: A

## Chapter 01 — One
### Chapter Structure
- **Hook:** q-a — what happened?
- **Because:** opening
- **Opens:** q-a — what happened?

## Chapter 02 — Two
### Chapter Structure
- **Hook:** q-b — never answered.
- **Because:** ch 01 — follows on.
- **Opens:** q-b — never answered?

## Chapter 03 — Three
### Chapter Structure
- **Hook:** q-b — still dangling.
- **Because:** ch 02 — follows on.
- **Closes:** q-a
```

`wired-phantom-answer.md` (`q-ghost` closed but never opened):

```markdown
---
book: 01
total_chapters: 3
---

## Solution: x
- culprit: A

## Chapter 01 — One
### Chapter Structure
- **Hook:** q-a — what happened?
- **Because:** opening
- **Opens:** q-a — what happened?

## Chapter 02 — Two
### Chapter Structure
- **Hook:** q-a — still open.
- **Because:** ch 01 — follows on.
- **Closes:** q-ghost

## Chapter 03 — Three
### Chapter Structure
- **Hook:** q-b — a new door.
- **Because:** ch 02 — follows on.
- **Opens:** q-b — a new door?
- **Closes:** q-a
- **Carries:** q-b
```

`wired-broken-hook.md` (ch 03 hooks `q-a`, already closed in ch 02):

```markdown
---
book: 01
total_chapters: 3
---

## Solution: x
- culprit: A

## Chapter 01 — One
### Chapter Structure
- **Hook:** q-a — what happened?
- **Because:** opening
- **Opens:** q-a — what happened?

## Chapter 02 — Two
### Chapter Structure
- **Hook:** q-b — the second door.
- **Because:** ch 01 — follows on.
- **Opens:** q-b — the second door?
- **Closes:** q-a

## Chapter 03 — Three
### Chapter Structure
- **Hook:** q-a — but this was answered in chapter two.
- **Because:** ch 02 — follows on.
- **Carries:** q-b
```

- [ ] **Step 2: Write the failing tests** `tests/test_tension_check.py`:

```python
from pathlib import Path

from scripts.tension_check import check_tension

FIX = Path("tests/fixtures/outlines")


def _predicates(result):
    return {b.split(":", 1)[0] for b in result["blocking"]}


def test_clean_wired_outline_has_no_findings():
    r = check_tension(FIX / "wired-clean.md")
    assert r["wired"] is True and r["blocking"] == []


def test_unwired_outline_is_skipped():
    r = check_tension(FIX / "well-formed.md")
    assert r["wired"] is False and r["blocking"] == []


def test_orphan_chapter():
    assert "orphan-chapter" in _predicates(check_tension(FIX / "wired-orphan.md"))


def test_dropped_question():
    assert "dropped-question" in _predicates(check_tension(FIX / "wired-dropped-question.md"))


def test_phantom_answer():
    assert "phantom-answer" in _predicates(check_tension(FIX / "wired-phantom-answer.md"))


def test_broken_hook_on_already_closed_question():
    assert "broken-hook" in _predicates(check_tension(FIX / "wired-broken-hook.md"))


def test_carried_question_stays_hookable():
    # wired-clean ch 06 carries q-elspeth-vale and hooks it: must NOT be broken-hook.
    r = check_tension(FIX / "wired-clean.md")
    assert not any(b.startswith("broken-hook") for b in r["blocking"])
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_tension_check.py -v`
Expected: FAIL — no module `scripts.tension_check`.

- [ ] **Step 4: Implement** `scripts/tension_check.py`:

```python
"""Dramatic-wiring checker (deterministic; plot-book workshop spec §6).

Named checks over the wired outline format — causality graph, open-question
ledger, hook chain (this task), plus curve/beat checks against the genre beat
sheet (Tasks 5–6). No LLM judgment: every check is arithmetic over the wiring.
An outline without wiring is SKIPPED (wired: False, exit 0) — book 1 stays valid.

  python3 scripts/tension_check.py input/book-NN/outline-skeleton.md \
      [--beat-sheet P] [--turning-points P] [--whodunit P]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter
from scripts.penny_wiring import has_wiring, parse_wired_chapters


def _graph_checks(chapters: list[dict], blocking: list[str]) -> dict:
    """Causality + question ledger + hook chain. Returns the question maps
    (open/closed/carried chapter indices) for the curve checks."""
    nums = {c["num"] for c in chapters}
    open_ch: dict[str, int] = {}
    for c in chapters:
        for qid, _ in c["opens"]:
            open_ch.setdefault(qid, c["num"])
    closed_ch: dict[str, int] = {}
    carried: set[str] = set()
    for c in chapters:
        for err in c["errors"]:
            blocking.append(f"wiring-parse: ch {c['num']:02d} — {err}")
        val = (c["because"] or "").strip()
        if not val:
            blocking.append(f"orphan-chapter: ch {c['num']:02d} has no Because line")
        elif val.lower() == "opening":
            if c["num"] != 1:
                blocking.append(
                    f"orphan-chapter: ch {c['num']:02d} claims 'opening' but is not chapter 1")
        elif c["because_ch"] is None:
            blocking.append(
                f"orphan-chapter: ch {c['num']:02d} Because names no chapter: {val!r}")
        elif c["because_ch"] not in nums:
            blocking.append(
                f"orphan-chapter: ch {c['num']:02d} Because names nonexistent ch {c['because_ch']:02d}")
        elif c["because_ch"] >= c["num"]:
            blocking.append(
                f"orphan-chapter: ch {c['num']:02d} Because points forward/self (ch {c['because_ch']:02d})")
        for qid in c["closes"] + c["carries"]:
            if open_ch.get(qid) is None or open_ch[qid] > c["num"]:
                blocking.append(
                    f"phantom-answer: ch {c['num']:02d} closes/carries {qid} which no earlier chapter opened")
            elif qid in c["carries"]:
                carried.add(qid)
            else:
                closed_ch.setdefault(qid, c["num"])
    for qid, oc in sorted(open_ch.items()):
        if qid not in closed_ch and qid not in carried:
            blocking.append(
                f"dropped-question: {qid} (opened ch {oc:02d}) is never closed or carried")
    for c in chapters:
        if c["hook_q"] is None:
            blocking.append(
                f"broken-hook: ch {c['num']:02d} Hook does not lead with a question id")
        elif open_ch.get(c["hook_q"]) is None or open_ch[c["hook_q"]] > c["num"]:
            blocking.append(
                f"broken-hook: ch {c['num']:02d} hook names unknown/not-yet-open question {c['hook_q']}")
        elif c["hook_q"] in closed_ch and closed_ch[c["hook_q"]] <= c["num"]:
            blocking.append(
                f"broken-hook: ch {c['num']:02d} hook names {c['hook_q']}, already closed by ch "
                f"{closed_ch[c['hook_q']]:02d}")
    return {"open_ch": open_ch, "closed_ch": closed_ch, "carried": carried}


def check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None,
                  whodunit_path=None) -> dict:
    path = Path(outline_path)
    if not path.is_file():
        return {"wired": False,
                "blocking": [f"wiring-parse: outline not found: {path}"], "metrics": {}}
    text = path.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_wiring(chapters):
        return {"wired": False, "blocking": [], "metrics": {"chapters": len(chapters)}}
    blocking: list[str] = []
    qmaps = _graph_checks(chapters, blocking)
    fm = parse_frontmatter(text)
    total_raw = fm.get("total_chapters")
    total = int(total_raw) if isinstance(total_raw, str) and total_raw.strip().isdigit() else len(chapters)
    metrics = {"chapters": len(chapters), "total_chapters": total,
               "questions": sorted(qmaps["open_ch"])}
    # Curve + beat checks (Tasks 5–6) hook in here.
    return {"wired": True, "blocking": blocking, "metrics": metrics}
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 -m pytest tests/test_tension_check.py -v` — all PASS. Full suite green.

- [ ] **Step 6: Commit**

```bash
git add scripts/tension_check.py tests/test_tension_check.py tests/fixtures/outlines/wired-*.md
git commit -m "feat(tension): graph checks — orphan, dropped, phantom, broken-hook"
```

---

### Task 5: `tension_check.py` — curve checks (dead-stretch, starved-thread)

**Files:**
- Modify: `scripts/tension_check.py`
- Create: `tests/fixtures/plot/beat-sheet.yaml`, `tests/fixtures/outlines/wired-dead-stretch.md`, `wired-starved-thread.md`, `tests/fixtures/plot/whodunit-mini.yaml`
- Test: `tests/test_tension_check.py` (append)

**Interfaces:**
- `check_tension` now honours `beat_sheet_path` (PyYAML load) and `whodunit_path` (reads top-level `reveal_chapter`). Without a beat sheet, curve checks are skipped (graph checks still run). Without a whodunit, the reveal proxy is `total_chapters`.

- [ ] **Step 1: Write fixtures.**

`tests/fixtures/plot/beat-sheet.yaml` (test-stable numbers for a 6-chapter book; M's gap deliberately tight for the starved fixture):

```yaml
beats:
  - { id: inciting-death,    by_fraction: 0.34 }
  - { id: midpoint-reversal, at_fraction: 0.50, tolerance: 0.17 }
  - { id: dark-night,        window: [0.60, 0.95] }
  - { id: reveal,            from: whodunit }
tracks:
  max_dark_gap: { M: 2, P: 4, R: 4, B: 5 }
questions:
  min_open_before_reveal: 1
```

`tests/fixtures/plot/whodunit-mini.yaml`:

```yaml
reveal_chapter: 5
```

`wired-dead-stretch.md` — 3 chapters, `q-a` opens ch 01 / closes ch 02, nothing open after ch 02 (reveal proxy = 3, so ch 02 < 3 fires `dead-stretch`; ch 02–03 hooks necessarily co-fire `broken-hook` — a genuinely dead book has nothing to hook, note this in the fixture comment). All Because valid, tracks all-active.

`wired-starved-thread.md` — 4 chapters, valid graph (`q-a` opens ch 01 / closes ch 04, hooks `q-a` throughout, Because chain 01←opening, 02←01, 03←02, 04←03), but track `M` reads `None.` in chapters 01–03 (run of 3 > limit 2) while P/R/B stay active.

- [ ] **Step 2: Append failing tests:**

```python
BEATS = Path("tests/fixtures/plot/beat-sheet.yaml")
WHOD = Path("tests/fixtures/plot/whodunit-mini.yaml")


def test_dead_stretch_fires_before_reveal_proxy():
    r = check_tension(FIX / "wired-dead-stretch.md", beat_sheet_path=BEATS)
    assert "dead-stretch" in _predicates(r)


def test_starved_thread_fires_past_max_dark_gap():
    r = check_tension(FIX / "wired-starved-thread.md", beat_sheet_path=BEATS)
    assert "starved-thread" in _predicates(r)


def test_clean_outline_survives_curve_checks_with_real_reveal():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS, whodunit_path=WHOD)
    assert r["blocking"] == []


def test_curve_checks_skipped_without_beat_sheet():
    r = check_tension(FIX / "wired-starved-thread.md")
    assert "starved-thread" not in _predicates(r)
```

- [ ] **Step 3: Run to verify failure** — the two `fires` tests FAIL (no findings emitted).

- [ ] **Step 4: Implement** — in `scripts/tension_check.py` add near the top:

```python
def _load_yaml(path):
    import yaml  # PyYAML: beat sheet + whodunit are genuinely nested human data
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
```

add the curve function:

```python
def _curve_checks(chapters, beat_sheet, reveal_ch, blocking):
    min_open = int((beat_sheet.get("questions") or {}).get("min_open_before_reveal", 1))
    open_now: set[str] = set()
    counts: dict[int, int] = {}
    for c in chapters:
        open_now.update(q for q, _ in c["opens"])
        open_now.difference_update(c["closes"])  # carries stay open past book end
        counts[c["num"]] = len(open_now)
    last = reveal_ch if reveal_ch else max(counts, default=0)
    for n in sorted(counts):
        if n < last and counts[n] < min_open:
            blocking.append(
                f"dead-stretch: ch {n:02d} ends with {counts[n]} open question(s) "
                f"(< {min_open}) before the reveal (ch {last:02d})")
    for track, limit in sorted(((beat_sheet.get("tracks") or {}).get("max_dark_gap") or {}).items()):
        run, run_start = 0, None
        for c in chapters:
            val = c["tracks"].get(track)
            dark = isinstance(val, str) and val.strip().lower().startswith("none")
            if dark:
                run += 1
                run_start = run_start if run_start is not None else c["num"]
                if run == int(limit) + 1:
                    blocking.append(
                        f"starved-thread: track {track} dark for more than {limit} "
                        f"consecutive chapters (from ch {run_start:02d})")
            else:
                run, run_start = 0, None
    return counts
```

and in `check_tension`, replace the `# Curve + beat checks` comment with:

```python
    reveal_ch = None
    if whodunit_path is not None and Path(whodunit_path).is_file():
        rc = _load_yaml(whodunit_path).get("reveal_chapter")
        reveal_ch = int(rc) if isinstance(rc, int) or (isinstance(rc, str) and rc.isdigit()) else None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        beat_sheet = _load_yaml(beat_sheet_path)
        metrics["open_counts"] = _curve_checks(chapters, beat_sheet, reveal_ch, blocking)
        # off-mark-beat (Task 6) hooks in here with the same beat_sheet/reveal_ch.
```

- [ ] **Step 5: Run to verify pass** — `python3 -m pytest tests/test_tension_check.py -v`, then full suite.

- [ ] **Step 6: Commit**

```bash
git add scripts/tension_check.py tests/test_tension_check.py tests/fixtures/plot tests/fixtures/outlines/wired-dead-stretch.md tests/fixtures/outlines/wired-starved-thread.md
git commit -m "feat(tension): curve checks — dead-stretch + starved-thread"
```

---

### Task 6: `tension_check.py` — off-mark-beat + CLI

**Files:**
- Modify: `scripts/tension_check.py`
- Create: `tests/fixtures/plot/turning-points-offmark.md`
- Test: `tests/test_tension_check.py` (append)

**Interfaces:**
- `check_tension` now honours `turning_points_path`. `main(argv) -> int` — args: `outline`, `--beat-sheet`, `--turning-points`, `--whodunit`; prints `tension_check: <finding>` lines (or the unwired skip note) and exits 1 iff blocking. Task 7 imports `check_tension`; the runbook (Task 11) calls `main` via CLI.

- [ ] **Step 1: Fixture** `tests/fixtures/plot/turning-points-offmark.md` — copy of `turning-points-good.md` with TP-1's chapter changed to `5` (inciting-death window for total 6 at `by_fraction 0.34` is ch 1–3; 5 is off-mark).

- [ ] **Step 2: Append failing tests:**

```python
from scripts.tension_check import main as tension_main

TP_GOOD = Path("tests/fixtures/plot/turning-points-good.md")
TP_BAD = Path("tests/fixtures/plot/turning-points-offmark.md")


def test_off_mark_beat_fires():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=TP_BAD, whodunit_path=WHOD)
    assert "off-mark-beat" in _predicates(r)


def test_on_mark_beats_pass():
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=TP_GOOD, whodunit_path=WHOD)
    assert r["blocking"] == []


def test_reveal_beat_checked_against_whodunit():
    bad_whod = Path("tests/fixtures/plot/whodunit-mini.yaml")  # reveal 5
    # TP_GOOD places reveal at 5 → clean; re-point at ch 4 via off-mark fixture logic:
    text = TP_GOOD.read_text(encoding="utf-8").replace(
        "## TP-4 — The kitchen truth\n- **Beat:** reveal\n- **Chapter:** 5",
        "## TP-4 — The kitchen truth\n- **Beat:** reveal\n- **Chapter:** 4")
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
    r = check_tension(FIX / "wired-clean.md", beat_sheet_path=BEATS,
                      turning_points_path=f.name, whodunit_path=bad_whod)
    assert "off-mark-beat" in _predicates(r)


def test_cli_exit_codes(capsys):
    assert tension_main([str(FIX / "wired-clean.md"), "--beat-sheet", str(BEATS),
                         "--whodunit", str(WHOD)]) == 0
    assert tension_main([str(FIX / "wired-orphan.md")]) == 1
    assert "orphan-chapter" in capsys.readouterr().out


def test_cli_unwired_skips_exit_zero(capsys):
    assert tension_main([str(FIX / "well-formed.md")]) == 0
    assert "no wiring" in capsys.readouterr().out
```

- [ ] **Step 3: Run to verify failure** — new tests FAIL (`off-mark-beat` absent; no `main`).

- [ ] **Step 4: Implement** — append to `scripts/tension_check.py`:

```python
import math


def _beat_window(beat: dict, total: int):
    if "by_fraction" in beat:
        return 1, math.ceil(float(beat["by_fraction"]) * total)
    if "at_fraction" in beat:
        f, tol = float(beat["at_fraction"]), float(beat.get("tolerance", 0.05))
        return max(1, math.floor((f - tol) * total)), math.ceil((f + tol) * total)
    if "window" in beat:
        a, b = beat["window"]
        return max(1, math.floor(float(a) * total)), math.ceil(float(b) * total)
    return None


def _beat_checks(points, beat_sheet, total, reveal_ch, blocking):
    defs = {b["id"]: b for b in (beat_sheet.get("beats") or []) if isinstance(b, dict) and "id" in b}
    for p in points:
        bid, ch = p.get("beat"), p.get("chapter")
        if not bid or ch is None:
            continue
        beat = defs.get(bid)
        if beat is None:
            blocking.append(f"off-mark-beat: turning point tags unknown beat id {bid!r}")
        elif beat.get("from") == "whodunit":
            if reveal_ch is not None and ch != reveal_ch:
                blocking.append(
                    f"off-mark-beat: {bid} at ch {ch:02d} but whodunit reveal_chapter is {reveal_ch}")
        else:
            w = _beat_window(beat, total)
            if w and not (w[0] <= ch <= w[1]):
                blocking.append(
                    f"off-mark-beat: {bid} at ch {ch:02d} outside window ch {w[0]:02d}–{w[1]:02d}")
```

Inside `check_tension`, under the beat-sheet block (replacing the Task-5 comment):

```python
        if turning_points_path is not None and Path(turning_points_path).is_file():
            from scripts.penny_wiring import parse_turning_points
            tp = parse_turning_points(Path(turning_points_path).read_text(encoding="utf-8"))
            _beat_checks(tp["points"], beat_sheet, total, reveal_ch, blocking)
```

Append the CLI:

```python
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Penny dramatic-wiring checker.")
    ap.add_argument("outline")
    ap.add_argument("--beat-sheet", dest="beat_sheet")
    ap.add_argument("--turning-points", dest="turning_points")
    ap.add_argument("--whodunit", dest="whodunit")
    args = ap.parse_args(argv)
    result = check_tension(args.outline, beat_sheet_path=args.beat_sheet,
                           turning_points_path=args.turning_points,
                           whodunit_path=args.whodunit)
    if not result["wired"] and not result["blocking"]:
        print("tension_check: no wiring detected — skipped (book is un-wired; see spec §5)")
        return 0
    for line in result["blocking"]:
        print(f"tension_check: {line}")
    return 1 if result["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run to verify pass** — `python3 -m pytest tests/test_tension_check.py -v`, then full suite.

- [ ] **Step 6: Commit**

```bash
git add scripts/tension_check.py tests/test_tension_check.py tests/fixtures/plot/turning-points-offmark.md
git commit -m "feat(tension): off-mark-beat + CLI — the proofreader is complete"
```

---

### Task 7: `preflight.py lock-mystery` — tension gate + recorded waivers

**Files:**
- Modify: `scripts/preflight.py` (`cmd_lock_mystery`, `main`)
- Test: `tests/test_preflight.py` (append)

**Interfaces:**
- Consumes: `tension_check.check_tension` (Task 6 final signature).
- Produces: `cmd_lock_mystery(book, *, repo_root=None, run_config=None, waivers=None) -> int` where `waivers` is a list of `"check-id:reason"` strings (CLI: repeatable `--waive`). Lock body gains `validated: fairplay+lexicon+tension` when wiring was checked, plus one `waived: <check-id> — <reason>` line per applied waiver.

- [ ] **Step 1: Append failing tests** to `tests/test_preflight.py` (reuse `_scaffold_lockable`; the wired-orphan fixture drives a deterministic tension failure without needing a beat sheet):

```python
WIRED_BAD = SRC / "tests/fixtures/outlines/wired-orphan.md"


def _add_wired_skeleton(tmp_path, fixture):
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture, d / "outline-skeleton.md")


def test_lock_refused_on_unwaived_tension_finding(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_BAD)
    with pytest.raises(SystemExit):
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_waived_finding_locks_and_records_reason(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    _add_wired_skeleton(tmp_path, WIRED_BAD)
    assert preflight.cmd_lock_mystery(
        "01", repo_root=tmp_path,
        waivers=['orphan-chapter:ch2 gap is the designed time-skip']) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "validated: fairplay+lexicon+tension" in body
    assert "waived: orphan-chapter — ch2 gap is the designed time-skip" in body


def test_unwired_book_locks_exactly_as_before(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    body = preflight.lock_path("01", tmp_path).read_text(encoding="utf-8")
    assert "validated: fairplay+lexicon\n" in body


def test_malformed_waiver_fails_loud(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    with pytest.raises(SystemExit):
        preflight.cmd_lock_mystery("01", repo_root=tmp_path, waivers=["no-reason"])
```

- [ ] **Step 2: Run to verify failure** — `python3 -m pytest tests/test_preflight.py -v -k waiv or tension` (the new tests FAIL: unexpected kwargs / no gate).

- [ ] **Step 3: Implement.** In `scripts/preflight.py` add near the other helpers:

```python
def _parse_waivers(raw) -> dict:
    """['check-id:reason', ...] -> {check-id: reason}. Both halves required."""
    out: dict[str, str] = {}
    for item in raw or []:
        check, _, reason = str(item).partition(":")
        if not check.strip() or not reason.strip():
            _fail(f'bad --waive {item!r}; expected check-id:"reason"')
        out[check.strip()] = reason.strip()
    return out


def _first_file(*paths):
    for p in paths:
        if p is not None and Path(p).is_file():
            return p
    return None
```

Change the signature to `def cmd_lock_mystery(book: str, *, repo_root=None, run_config=None, waivers=None) -> int:` and, between the lexicon block and the mint block, insert:

```python
    # 3. tension gate (plot-book workshop spec §6): only when the outline has wiring.
    from scripts.tension_check import check_tension
    waiver_map = _parse_waivers(waivers)
    outline = _first_file(
        repo_root / "input" / f"book-{book}" / "outline-skeleton.md",
        repo_root / "input" / f"book-{book}" / "outline.md")
    # NOTE: before relying on config_path below, check penny_paths.config_path's
    # behaviour when NO tier has the file (read scripts/penny_paths.py) — if it
    # exits/raises rather than returning a nonexistent default path, wrap the
    # call in try/except and pass None to check_tension instead.
    validated = "fairplay+lexicon"
    waived_lines: list[str] = []
    if outline is not None:
        tres = check_tension(
            outline,
            beat_sheet_path=_first_file(penny_paths.config_path("beat-sheet.yaml", root=repo_root)),
            turning_points_path=_first_file(
                repo_root / "input" / f"book-{book}" / "plot" / "turning-points.md"),
            whodunit_path=led)
        if tres["wired"]:
            validated = "fairplay+lexicon+tension"
            for f in tres["blocking"]:
                print(f"tension_check: {f}")
            unwaived = [f for f in tres["blocking"]
                        if f.split(":", 1)[0] not in waiver_map]
            if unwaived:
                _fail("tension failed; lock NOT written:\n  - " + "\n  - ".join(unwaived))
            fired = {f.split(":", 1)[0] for f in tres["blocking"]}
            for check, reason in sorted(waiver_map.items()):
                if check in fired:
                    waived_lines.append(f"waived: {check} — {reason}")
                else:
                    print(f"lock-mystery: note — waiver for '{check}' matched no finding; not recorded")
```

Change the mint block to use the new pieces:

```python
    lp.write_text(
        f"book: {book}\nvalidated: {validated}\n"
        f"locked_at: {datetime.now(timezone.utc).isoformat()}\n"
        + "".join(line + "\n" for line in waived_lines),
        encoding="utf-8",
    )
```

In `main`: `p_lock.add_argument("--waive", action="append", default=[], metavar='CHECK:"REASON"')` and dispatch `return cmd_lock_mystery(args.book, waivers=args.waive)`.

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_preflight.py -v`, then the FULL suite (the live series' book 1 path is exercised by other tests; everything must stay green).

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "feat(lock): tension gate on wired books, per-check waivers recorded in the cert"
```

---

### Task 8: `plot_stage.py` — status + stamp

**Files:**
- Create: `scripts/plot_stage.py`
- Test: `tests/test_plot_stage.py`

**Interfaces:**
- Consumes: `penny_meta.parse_frontmatter`, `penny_meta.write_frontmatter_field`, `penny_paths.series_root`.
- Produces: `STAGE_ORDER` (7 names: `premise, ending, turning-points, counterplot, chapters, weave, readback`), `stage_paths(book, root) -> dict[str, Path]`, `stage_status(book, *, repo_root=None) -> list[tuple[name, state, detail]]` (`state ∈ done|missing|stale`), `next_stage(rows) -> str|None`, `stamp(book, target, upstreams, *, repo_root=None)`. Fingerprint fields are `built_from_<upstream-file-stem>` (e.g. `built_from_premise`, `built_from_turning-points`, `built_from_mystery-solution`). CLI subcommands `status <book>` and `stamp <book> <file> --from P [P...]`. The `weave` stage is done iff the skeleton's frontmatter has `woven: true`.

- [ ] **Step 1: Write the failing tests** `tests/test_plot_stage.py`:

```python
from pathlib import Path

from scripts.plot_stage import (STAGE_ORDER, next_stage, stage_paths, stage_status, stamp)


def _series(tmp_path, book="01"):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / f"book-{book}" / "plot").mkdir(parents=True)
    (tmp_path / "output" / f"book-{book}" / "reports").mkdir(parents=True)
    return tmp_path


def _write(root, rel, text="---\n---\nbody\n"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_stage_order_is_the_spec_order():
    assert STAGE_ORDER == ["premise", "ending", "turning-points", "counterplot",
                           "chapters", "weave", "readback"]


def test_all_missing_next_is_premise(tmp_path):
    root = _series(tmp_path)
    rows = stage_status("01", repo_root=root)
    assert all(state == "missing" for _, state, _ in rows)
    assert next_stage(rows) == "premise"


def test_stamped_stage_is_done_and_edit_upstream_makes_it_stale(tmp_path):
    root = _series(tmp_path)
    prem = _write(root, "input/book-01/plot/premise.md")   # material absent: optional
    end = _write(root, "input/book-01/plot/ending.md")
    stamp("01", end, [prem], repo_root=root)
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["premise"] == "done" and rows["ending"] == "done"
    prem.write_text(prem.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["ending"] == "stale"


def test_premise_stale_when_material_present_but_unstamped(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/plot/material.md")
    _write(root, "input/book-01/plot/premise.md")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["premise"] == "stale"


def test_weave_needs_woven_flag(tmp_path):
    root = _series(tmp_path)
    skel = _write(root, "input/book-01/outline-skeleton.md")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["weave"] == "missing"
    skel.write_text("---\nwoven: true\n---\nbody\n", encoding="utf-8")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["weave"] == "done"


def test_stamp_creates_frontmatter_if_absent(tmp_path):
    root = _series(tmp_path)
    prem = _write(root, "input/book-01/plot/premise.md", "no frontmatter here\n")
    end = _write(root, "input/book-01/plot/ending.md", "also bare\n")
    stamp("01", end, [prem], repo_root=root)
    assert "built_from_premise:" in end.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run to verify failure** — `ModuleNotFoundError: scripts.plot_stage`.

- [ ] **Step 3: Implement** `scripts/plot_stage.py`:

```python
"""Save-point machinery for the plotting workshop (spec §7).

Deterministic: which stage is next, what is stale (built_from_* sha256
fingerprints — the clear-dev binding trick applied to planning files), and the
blind reader's-copy rendering (Task 9). The /plot-book runbook only ever ASKS
this script; it never improvises stage detection.

  python3 scripts/plot_stage.py status 01
  python3 scripts/plot_stage.py stamp 01 input/book-01/plot/ending.md \
      --from input/book-01/plot/premise.md
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths
from scripts.penny_meta import parse_frontmatter, write_frontmatter_field

STAGE_ORDER = ["premise", "ending", "turning-points", "counterplot",
               "chapters", "weave", "readback"]

_UPSTREAM = {
    "premise": ["material"],           # material is optional (spec §4)
    "ending": ["premise"],
    "turning-points": ["premise", "ending"],
    "counterplot": ["ending", "turning-points"],
    "chapters": ["turning-points", "counterplot"],
    "weave": [],                       # done-ness is the skeleton's woven flag
    "readback": ["chapters"],
}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _root(repo_root) -> Path:
    return Path(repo_root) if repo_root is not None else penny_paths.series_root()


def stage_paths(book: str, root: Path) -> dict:
    plot = root / "input" / f"book-{book}" / "plot"
    out = root / "output" / f"book-{book}"
    skel = root / "input" / f"book-{book}" / "outline-skeleton.md"
    return {"material": plot / "material.md", "premise": plot / "premise.md",
            "ending": plot / "ending.md", "turning-points": plot / "turning-points.md",
            "counterplot": out / "mystery-solution.md", "chapters": skel,
            "weave": skel, "readback": out / "reports" / "outline-fan.md"}


def stage_status(book: str, *, repo_root=None) -> list:
    root = _root(repo_root)
    paths = stage_paths(book, root)
    rows = []
    for name in STAGE_ORDER:
        p = paths[name]
        if not p.is_file():
            rows.append((name, "missing", str(p)))
            continue
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if name == "weave":
            done = str(fm.get("woven", "")).strip().lower() == "true"
            rows.append((name, "done" if done else "missing", "woven flag"))
            continue
        stale = []
        for up in _UPSTREAM[name]:
            upath = paths[up]
            field = f"built_from_{upath.stem}"
            recorded = fm.get(field)
            if recorded is None:
                if up == "material" and not upath.is_file():
                    continue  # absent material is a legitimate blank start
                stale.append(f"{field} unstamped")
            elif not upath.is_file() or _sha(upath) != recorded:
                stale.append(f"{field} mismatch")
        rows.append((name, "stale" if stale else "done", "; ".join(stale)))
    return rows


def next_stage(rows) -> "str | None":
    for name, state, _ in rows:
        if state != "done":
            return name
    return None


def stamp(book: str, target, upstreams, *, repo_root=None) -> None:
    p = Path(target)
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        text = "---\n---\n\n" + text
    for up in upstreams:
        upp = Path(up)
        text = write_frontmatter_field(text, f"built_from_{upp.stem}", _sha(upp))
    p.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plotting-workshop stage machinery.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_st = sub.add_parser("status")
    p_st.add_argument("book")
    p_sp = sub.add_parser("stamp")
    p_sp.add_argument("book")
    p_sp.add_argument("target")
    p_sp.add_argument("--from", dest="upstreams", nargs="+", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "status":
        rows = stage_status(args.book)
        for name, state, detail in rows:
            print(f"stage {name}: {state}" + (f" ({detail})" if state == "stale" and detail else ""))
        nxt = next_stage(rows)
        print(f"next: {nxt if nxt else 'none — plan complete'}")
        return 0
    if args.cmd == "stamp":
        stamp(args.book, args.target, args.upstreams)
        return 0
    ap.error(f"unknown command {args.cmd!r}")  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_plot_stage.py -v`, then full suite.

- [ ] **Step 5: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "feat(plot-stage): save-point status + built_from fingerprints"
```

---

### Task 9: `plot_stage.py readers-copy` — the blind guarantee

**Files:**
- Modify: `scripts/plot_stage.py`
- Test: `tests/test_plot_stage.py` (append)

**Interfaces:**
- Produces: `readers_copy_text(text: str) -> str` (pure), `readers_copy(book, *, repo_root=None) -> Path` (reads the skeleton, writes `output/book-NN/reports/outline-readers-copy.md`), CLI subcommand `readers-copy <book>`. Task 11's runbook calls the CLI before dispatching `outline-fan`.

- [ ] **Step 1: Append failing tests** (the blind guarantee is deterministic — test that nothing solution-shaped survives):

```python
from scripts.plot_stage import readers_copy, readers_copy_text

WIRED_CLEAN = Path("tests/fixtures/outlines/wired-clean.md")


def test_readers_copy_keeps_story_drops_wiring_and_solution():
    out = readers_copy_text(WIRED_CLEAN.read_text(encoding="utf-8"))
    assert "## Chapter 01" in out and "Maggie arrives" in out
    assert "Solution" not in out and "Mary" not in out.split("Chapter 01")[0]
    assert "q-" not in out                      # no question ids anywhere
    assert "**Because:**" not in out and "**Opens:**" not in out
    assert "Track Movement" not in out and "**M:**" not in out


def test_readers_copy_keeps_hook_prose_without_id():
    out = readers_copy_text(WIRED_CLEAN.read_text(encoding="utf-8"))
    assert "the doctor is dead on his own kitchen floor." in out


def test_readers_copy_writes_report_file(tmp_path):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text(WIRED_CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    p = readers_copy("01", repo_root=tmp_path)
    assert p == tmp_path / "output/book-01/reports/outline-readers-copy.md"
    assert p.is_file() and "q-" not in p.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run to verify failure** — ImportError on `readers_copy_text`.

- [ ] **Step 3: Implement** — append to `scripts/plot_stage.py`:

```python
import re

from scripts.penny_meta import strip_frontmatter
from scripts.penny_wiring import CHAPTER_RE, FIELD_RE, HEADING_RE, QID_RE, split_id

_DROP_FIELDS = {"Because", "Opens", "Closes", "Carries"}
_DROP_SUBSECTIONS = ("Track Movement", "Drafting Notes", "Possible Line-Level Prompts")
_H3_RE = re.compile(r"^###\s+(.*)$")


def readers_copy_text(text: str) -> str:
    """The blind reader's copy (spec §5): chapters only, in story order, with the
    Solution/Threads sections, wiring lines, question ids, and drafting machinery
    stripped BY CONSTRUCTION — blindness is not an instruction to an agent."""
    body = strip_frontmatter(text)
    sections = list(HEADING_RE.finditer(body))
    out_lines = ["# Outline — reader's copy", ""]
    for i, m in enumerate(sections):
        if not CHAPTER_RE.match(m.group(1)):
            continue
        start = m.start()
        end = sections[i + 1].start() if i + 1 < len(sections) else len(body)
        skipping = False
        for line in body[start:end].splitlines():
            h3 = _H3_RE.match(line)
            if h3:
                skipping = any(s in h3.group(1) for s in _DROP_SUBSECTIONS)
                if skipping:
                    continue
            elif skipping:
                continue
            fm = FIELD_RE.match(line)
            if fm:
                field, value = fm.group(1), fm.group(2)
                if field in _DROP_FIELDS:
                    continue
                if field == "Hook":
                    qid, rest = split_id(value)
                    if QID_RE.match(qid):
                        line = line[:line.index("**Hook:**") + len("**Hook:**")] + (
                            f" {rest}" if rest else "")
            out_lines.append(line)
        out_lines.append("")
    return "\n".join(out_lines).rstrip() + "\n"


def readers_copy(book: str, *, repo_root=None) -> Path:
    root = _root(repo_root)
    skel = stage_paths(book, root)["chapters"]
    if not skel.is_file():
        sys.exit(f"plot_stage: no outline-skeleton for book {book} ({skel})")
    dest = root / "output" / f"book-{book}" / "reports" / "outline-readers-copy.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(readers_copy_text(skel.read_text(encoding="utf-8")), encoding="utf-8")
    return dest
```

Add the CLI branch in `main` (a `readers-copy` subparser with a `book` arg, dispatching `print(readers_copy(args.book))` and `return 0`).

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_plot_stage.py -v`, then full suite.

- [ ] **Step 5: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "feat(plot-stage): readers-copy — blindness by construction"
```

---

### Task 10: The three agents

**Files:**
- Create: `agents/plot-proposer.md`, `agents/chapter-weaver.md`, `agents/outline-fan.md`
- Test: `tests/test_plot_agents.py`

**Interfaces:**
- Produces: the three agent contracts the Task 11 runbook dispatches. Contract anchor phrases (asserted by tests, referenced by the runbook — keep in lockstep): proposer never chooses the core; weaver emits wired fields and sets `woven: true`; fan gets `{ reader's copy, persona }` only and never emits `^BLOCKING:`.

- [ ] **Step 1: Write the failing contract tests** `tests/test_plot_agents.py`:

```python
from pathlib import Path

A = Path("agents")


def _text(name):
    p = A / name
    assert p.is_file(), f"missing agent file {p}"
    return p.read_text(encoding="utf-8")


def test_plot_proposer_contract():
    t = _text("plot-proposer.md")
    for phrase in ("never choose the core", "never invent silently",
                   "never improve chosen material", "one-sentence pitch",
                   "premise.md", "ending.md", "turning-points.md", "beat-sheet"):
        assert phrase in t, phrase


def test_chapter_weaver_contract():
    t = _text("chapter-weaver.md")
    for phrase in ("**Because:**", "**Opens:**", "**Hook:**", "clue obligations",
                   "woven: true", "plot_stage.py", "worse in kind",
                   "never draft prose", "outline-skeleton.md"):
        assert phrase in t, phrase


def test_outline_fan_contract():
    t = _text("outline-fan.md")
    for phrase in ("reader's copy", "whodunit guess", "put it down",
                   "outline-fan.md", "never emit any `^BLOCKING:`",
                   "persona"):
        assert phrase in t, phrase
```

- [ ] **Step 2: Run to verify failure** — missing files.

- [ ] **Step 3: Write** `agents/plot-proposer.md` (follow `agents/_TEMPLATE.md` frontmatter conventions):

```markdown
---
name: plot-proposer
description: Runs the workshop's three taste stages — lays out the showrunner's material with every rival surfaced, generates machine rivals against the genre archetype and beat sheet, and presents a choice. Never chooses the core; never writes until the showrunner picks.
---
# Plot Proposer

**Role posture:** proposer. You surface and generate options; the showrunner
chooses. You are dispatched three times per book — once each for the premise,
ending, and turning-points stages — with the stage named in your dispatch.

**Salvage rules (binding, from the ideation portaprompt):** if
`input/book-NN/plot/material.md` exists, it is the showrunner's own material.
Lay out every substantive idea in it, including every rival version of the same
beat, and present rivals as equals. You may never choose the core (culprit,
victim, central deception, series-arc constraints), never invent silently (a gap
is reported, not filled), and never improve chosen material (record the pick in
substance as written). Recency is not a decision. One question at a time.

**Inputs:** `{ stage name, material.md if present, the genre archetype document,
the genre beat-sheet (resolved via the config overlay), earlier plot/ save
points, series bible if present }`.

**Stage obligations:**
- **premise** — generate rival dramatic engines to fill gaps in the material
  (aim for a dozen candidates boiled to a shortlist of 3–5): what she wants,
  what opposes her, why she cannot walk away, why the reader cannot. Apply the
  one-sentence pitch test brutally: if hearing the premise does not create the
  urge to read it, it does not make the shortlist. Record the chosen engine AND
  the rejected shortlist in `premise.md`.
- **ending** — 3 rival endings honouring the chosen premise: who did it and why,
  the worst moment (dark night), what the truth costs, what restored looks like.
  The pick becomes `ending.md` — for a mystery this is the irreducible core.
- **turning-points** — 3 rival tentpole sets (6–9 scenes each) placed against the
  beat-sheet positions, with `total_chapters` proposed. The pick becomes
  `turning-points.md`, each point carrying `- **Beat:**` and `- **Chapter:**`
  fields where a beat applies.

**Output contract:** write NOTHING until the showrunner has chosen. Then write
exactly one save-point file in the documented format, ending with the
`/plot-book` runbook's stamp step. Your proposals live in conversation; only the
decision lands on disk.
```

- [ ] **Step 4: Write** `agents/chapter-weaver.md`:

```markdown
---
name: chapter-weaver
description: Fills the chapters between turning points (interpolation, escalating, carrying clue obligations) and then weaves the secondary tracks through them. Emits wired chapter blocks only — never drafts prose, never writes ledgers or certificates.
---
# Chapter Weaver

**Role posture:** constructive planner. Context-rich: you read the sealed
solution — you are building the road the drafter will drive, and you must know
where it goes.

**Inputs:** `{ pass name (fill | weave), premise.md, ending.md,
turning-points.md, series/whodunit/book-NN.yaml, output/book-NN/mystery-solution.md,
the genre beat-sheet, canon-core + ledger slice }`.

**Fill pass (one dispatch per gap between consecutive turning points):** both
endpoint scenes are FIXED. Write the wired chapter blocks that force the path
from one to the next — every chapter caused by the previous turn ("therefore/
but", never "and then"), each escalation worse in kind, not just degree, and
each chapter carrying the clue obligations the whodunit yaml schedules for it.
Every chapter block you emit MUST carry complete wiring: `- **Because:**`,
`- **Opens:**` / `- **Closes:**` / `- **Carries:**` as the story requires, and a
`- **Hook:**` leading with the id of a question still open. Do not resolve
tension the plan does not schedule: the questions you may close are the ones the
turning points imply, no others. Output goes into `input/book-NN/outline-skeleton.md`
(initialize its frontmatter from turning-points.md's total_chapters on first write).

**Weave pass (one dispatch over the filled skeleton):** braid the secondary
tracks (for a cozy: P/R/B) through the chapters, respecting the beat-sheet's
`max_dark_gap` limits, preferring collisions (two tracks advanced by one scene)
over parallel lanes. Update Track Movement rows; adjust wiring only where a
woven beat genuinely opens or closes a question. When done set `woven: true` in
the skeleton frontmatter and re-stamp via
`${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py`.

**Hard constraints:** you never draft prose (the drafter owns prose); you never
write `series/` ledgers, locks, or certificates; you never move the reveal; you
never emit a chapter without complete wiring.
```

- [ ] **Step 5: Write** `agents/outline-fan.md`:

```markdown
---
name: outline-fan
description: Blind outline beta reader — a genre-fan persona reads the reader's copy of the chapter plan in story order and reports experience: interest curve, put-down risk, whodunit guess + chapter, would-buy. Advisory; never blocks.
---
# Outline Fan

**Role posture:** reader simulation. You are the one voice in the workshop that
does not know the ending — and that is the entire value. A reader who knows the
culprit cannot report when she guessed.

**Inputs:** `{ the reader's copy (output/book-NN/reports/outline-readers-copy.md),
the genre fan persona (resolved from genre.yaml's fan_persona via the overlay) }`
— and NOTHING else. No solution, no wiring, no plot/ folder, no whodunit yaml,
no other agent's output. The copy you receive was stripped by
`plot_stage.py readers-copy`; do not go looking for what it removed.

**Cross-model:** run on a non-plotting model where reachable; if none is
reachable, proceed and state "independence reduced" in the report header
(same degrade rule as /review-outline).

**Output:** `output/book-NN/reports/outline-fan.md`, in the persona's report
order: per-chapter interest 1–5 (one line each), any chapter where you would
put it down and why, your whodunit guess as `{name, chapter first sure}`, and
would-buy yes/no with one sentence. Prose as a reader, never rules or craft
jargon. Advisory: you MUST never emit any `^BLOCKING:` line, and your report
never holds any gate.
```

- [ ] **Step 6: Reconcile the weaver test phrase** — in `tests/test_plot_agents.py` use `"never draft prose"` and make the agent text match; re-run.

Run: `python3 -m pytest tests/test_plot_agents.py -v` — all PASS. Full suite green.

- [ ] **Step 7: Commit**

```bash
git add agents/plot-proposer.md agents/chapter-weaver.md agents/outline-fan.md tests/test_plot_agents.py
git commit -m "feat(agents): plot-proposer, chapter-weaver, outline-fan with written contracts"
```

---

### Task 11: `commands/plot-book.md` — the runbook

**Files:**
- Create: `commands/plot-book.md` (distinct from the existing `commands/plan-book.md` — verify no clash with `ls commands/` before writing)
- Test: `tests/test_plot_book_command.py`

**Interfaces:**
- Consumes: `plot_stage.py` CLI (Task 8–9), `tension_check.py` CLI (Task 6), `preflight.py lock-mystery --waive` (Task 7), the three agents (Task 10), `penny_genre.py` (`fan_persona`, `beat_sheet` keys), the existing `mystery-planner` agent.
- Produces: the twelfth slash command. Stage markers written to `.penny/current-stage`: `PLOT-PREMISE`, `PLOT-ENDING`, `PLOT-SPINE`, `PLOT-COUNTERPLOT`, `PLOT-CHAPTERS`, `PLOT-WEAVE`, `PLOT-READBACK`.

- [ ] **Step 1: Write the failing test** `tests/test_plot_book_command.py`:

```python
from pathlib import Path

CMD = Path("commands/plot-book.md")


def test_runbook_exists_and_references_the_machinery():
    t = CMD.read_text(encoding="utf-8")
    for ref in ("plot_stage.py", "tension_check.py", "lock-mystery", "--waive",
                "plot-proposer", "chapter-weaver", "outline-fan", "mystery-planner",
                "${CLAUDE_PLUGIN_ROOT}", "readers-copy", "stage=PLOT-"):
        assert ref in t, ref


def test_runbook_never_asks_what_a_file_answers():
    t = CMD.read_text(encoding="utf-8")
    assert "never asks you anything a file already answers" in t
```

- [ ] **Step 2: Run to verify failure** — file missing.

- [ ] **Step 3: Write** `commands/plot-book.md`:

```markdown
---
description: The plotting workshop — build a book's dramatic outline in staged, resumable save points; your taste at premise/ending/turning-points, machine work below, blind fan read-back, then the lock.
argument-hint: <book-number>
---
# /plot-book

The recommended front door for a NEW book (spec: docs/superpowers/specs/
2026-07-12-plot-book-workshop-design.md). Resumable: the planning files ARE the
state; this command never asks you anything a file already answers.

## Steps

1. **Parse args:** `book=$1` (e.g. `02`). Resolve the active series root (hard
   error outside a series). Resolve the genre from `series.yaml` and hard-error
   without it (same rule as /plan-book).

2. **Ask the stage machinery where we are:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" status $book
   ```

   Report the full stage table to the showrunner, then enter the stage named
   `next:`. If `next: none`, say so and stop — the plan is complete.

3. **Write the harness marker for the entered stage** (name per the table below):

   ```bash
   mkdir -p .penny && echo "book=$book stage=PLOT-<STAGE>" > .penny/current-stage
   ```

   | stage | marker | pauses? |
   |---|---|---|
   | premise | PLOT-PREMISE | yes — showrunner chooses |
   | ending | PLOT-ENDING | yes — showrunner chooses |
   | turning-points | PLOT-SPINE | yes — showrunner chooses |
   | counterplot | PLOT-COUNTERPLOT | yes — showrunner approves the yaml |
   | chapters | PLOT-CHAPTERS | no |
   | weave | PLOT-WEAVE | no |
   | readback | PLOT-READBACK | yes — showrunner signs off → lock |

4. **Stages premise / ending / turning-points:** dispatch the `plot-proposer`
   sub-agent with the stage name, `input/book-$book/plot/material.md` if present,
   the genre archetype document (`genres/<genre>/archetype.md`), the beat sheet
   (overlay-resolved `beat-sheet.yaml`), and every earlier save point. Relay its
   options to the showrunner; when they choose, the proposer writes the one save
   point, then stamp it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" stamp $book \
     input/book-$book/plot/<file>.md --from <each upstream save point that exists>
   ```

   End the run after the stamp — one taste decision per sitting.

5. **Stage counterplot:** dispatch the existing `mystery-planner` with the core
   read from `ending.md` + the spine from `turning-points.md` (do NOT re-ask the
   showrunner for the core — it is on disk). It proposes
   `series/whodunit/book-$book.yaml`; the showrunner edits until right; write the
   sealed solution to `output/book-$book/mystery-solution.md`, then stamp the
   solution file `--from` ending.md and turning-points.md. **No lock here** —
   the lock is stage readback's last act (validate once, then freeze).

6. **Stage chapters:** for each gap between consecutive turning points, dispatch
   `chapter-weaver` (fill pass) with both endpoints fixed and the clue schedule
   from the whodunit yaml. Then stamp the skeleton `--from` turning-points.md and
   the solution file. Continue directly to weave.

7. **Stage weave:** dispatch `chapter-weaver` (weave pass) over the filled
   skeleton. It sets `woven: true` and re-stamps.

8. **Stage readback:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plot_stage.py" readers-copy $book
   ```

   Dispatch `outline-fan` on the reader's copy with the genre's `fan_persona`
   (cross-model where reachable; degrade with "independence reduced", never halt).
   Then run the proofreader:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tension_check.py" \
     input/book-$book/outline-skeleton.md \
     --beat-sheet "$(python3 -c "import sys; sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}'); from scripts import penny_paths; print(penny_paths.config_path('beat-sheet.yaml'))")" \
     --turning-points input/book-$book/plot/turning-points.md \
     --whodunit series/whodunit/book-$book.yaml
   ```

   Present the fan's report and the findings side by side. The showrunner either
   revises (edit any file — staleness re-opens the right stages on the next run)
   or signs off. On sign-off, stamp the fan report `--from` the skeleton, then
   mint the lock — with any per-check waivers the showrunner dictates, each with
   a reason:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book \
     [--waive check-id:"reason"]...
   ```

   From here the book proceeds exactly as today: /expand-outline, /review-outline,
   /draft-chapter.
```

- [ ] **Step 4: Run to verify pass** — `python3 -m pytest tests/test_plot_book_command.py -v`, then full suite.

- [ ] **Step 5: Commit**

```bash
git add commands/plot-book.md tests/test_plot_book_command.py
git commit -m "feat(plot-book): the resumable workshop runbook"
```

---

### Task 12: Template + docs

**Files:**
- Modify: `config/outline-template.md`, `CLAUDE.md`, `README.md`, `genres/cozy-mystery/ideation-prompt.md`

- [ ] **Step 1: Template.** In `config/outline-template.md`, sharpen the Turn/Change line in BOTH chapter blocks to:

```markdown
- **Turn / Change:** <What is materially different by the end — what is worse now, and for whom.>
```

and add after each chapter's `**Hook:**` line (comment-documented, optional):

```markdown
<!-- Wiring (optional; all-or-nothing per book — see tension_check.py). -->
- **Because:** <ch NN — which earlier turn forced this chapter; chapter 1 writes: opening>
- **Opens:** <q-slug — the question this chapter plants>
- **Closes:** <q-slug>
```

and in the Hook line's placeholder, note the wired form: `<q-slug — the unresolved question that earns the next chapter. On a wired book the id comes first.>`

- [ ] **Step 2: CLAUDE.md.** In "The pipeline", add `/plot-book NN` as the recommended front door for a new book (one short paragraph: staged save points under `input/book-NN/plot/`, showrunner taste at premise/ending/turning-points, mystery planning absorbed at its natural moment, blind fan read-back, lock last — with per-check `--waive` recorded in the cert). In "Gates and the verdict convention", add `tension_check.py` to the deterministic-checker list (seven named checks; skips unwired books). In the dependency-split section, add `beat-sheet.yaml` to the PyYAML side. In "Run configuration", note the optional `plot_model:` key (defaults to `drafting_model`; the fan prefers any reachable non-`plot_model` model). Update the two-front-doors sentence to three.

- [ ] **Step 2b: README.md.** In the engine README's genre-pack description, add `beat-sheet.yaml` and `fan_persona` as part of the genre-pack contract (the worked example the thriller pack will follow).

- [ ] **Step 3: Portaprompt pointer.** At the top of `genres/cozy-mystery/ideation-prompt.md`'s usage note, add one line: brainstorm salvage now has a first-class home — save the transcript as `input/book-NN/plot/material.md` and run `/plot-book NN`; this portaprompt remains the manual path.

- [ ] **Step 4: Verify + commit**

Run: `python3 -m pytest` — full suite green (doc-contract tests like `test_phase3_doc_note.py` may assert CLAUDE.md content; fix any that legitimately changed).

```bash
git add config/outline-template.md CLAUDE.md README.md genres/cozy-mystery/ideation-prompt.md
git commit -m "docs(plot-book): third front door, wired template, dependency-split note"
```

---

## Post-plan

- **Shakedown (not in this plan):** plot Pelican's Crook book 2 via `/plot-book 02` from the series folder — the live test of the taste stages, the weaver's wiring discipline, and the fan report. Fold findings back into the spec's seed thresholds.
- **Deferred by spec:** brief renderer (Part 3), adversarial predict-the-twist loop (Part 4), rival-count run-config knobs, multi-fan panels, book-1 wiring retrofit.
