# `story.md` Source Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `outline-skeleton.md` with `input/book-NN/story.md` — beats in story order carrying four sigils — and a deterministic cut that emits `input/book-NN/outline.md` in packet format.

**Architecture:** A new dependency-free parser (`scripts/penny_story.py`) reads `story.md` into beat dicts. A new checker/emitter (`scripts/story_cut.py`) validates the beats against the active genre's job list, the whodunit ledger and the `## Questions` block, then expands an approved `cut-plan.md` into packet-format chapter blocks, deriving every section the author does not write. A new `chapter-cutter` agent proposes the cut plan and absorbs `chapter-weaver`. `plot_stage.py` swaps its `chapters`/`weave` stages onto `story.md` and gains a `cut` stage.

**Tech Stack:** Python 3, stdlib only for the new modules (`penny_meta` family rule — PyYAML is used *only* where the existing code already uses it, i.e. reading `series/whodunit/book-NN.yaml`). pytest. Markdown for agent/command files.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-08-03-story-source-layer-design.md`. Cited as `spec §N`.
- **Engine is genre/location-agnostic.** No cozy filename, no series path, no job id may be hardcoded in `scripts/`. Job lists resolve through `penny_genre.macro_structure()`; data paths resolve through `penny_paths.series_root()`.
- **Dependency split.** `penny_story.py` and `story_cut.py` are stdlib-only for parsing story/cut-plan/outline. PyYAML appears only where the ledger (`series/whodunit/book-NN.yaml`) is read — that file is nested human-edited data and is already PyYAML's job.
- **Exit codes** follow `map_check.py`: `0` clean, `1` findings, `2` usage.
- **Findings are named strings** of the form `"<finding-id>: <prose>"`, collected in `{"blocking": [...], "notes": [...]}` — the exact shape `map_check.check_map` returns.
- **No waivers** at the cut level (spec §8). Fix the story or fix the cut plan.
- **Never overwrite hand-shaped chapter work** — spec §7, and `2026-07-30 §10`.
- **Slug contract:** `^[a-z0-9][a-z0-9-]*$` for `@strand`, `#job`, `!clue`.
- **Question ids:** `penny_wiring.QID_RE` — `^q-[a-z0-9][a-z0-9-]*$`.
- Tests are test-first, live in `tests/`, use `tmp_path` series fixtures in the style of `tests/test_plot_stage.py::_series`.
- Run the full suite with `python3 -m pytest` (780 passing at plan time). Commit after each task.
- Work on `main`, per project convention.

---

### Task 1: `penny_story.parse_story` — beats and sigils

**Files:**
- Create: `scripts/penny_story.py`
- Test: `tests/test_penny_story.py`

**Interfaces:**
- Consumes: `scripts.penny_meta.strip_frontmatter`, `scripts.penny_meta.parse_frontmatter`
- Produces:
  - `parse_story(text: str) -> list[dict]` — each beat `{"text": str, "strands": list[str], "jobs": list[str], "opens": list[str], "closes": list[str], "clues": list[str], "line": int}`. `text` has tags stripped and whitespace collapsed. `line` is 1-based, of the bullet's first line, counted in the **full** text including frontmatter.
  - `parse_questions(text: str) -> dict[str, str]` — id → prose, from the `## Questions` block.
  - `TAG_RE`, `SLUG_RE`, `QUESTIONS_HEADING_RE` module constants.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_penny_story.py
from scripts.penny_story import parse_story, parse_questions

STORY = """---
stage: story
book: 02
---

## Act I

- Maggie chooses this life: the gallery, the commission call
  with a closing date.
  @maggie #establish-protected-world

- The handover appointment was altered — in Maggie's name.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered

- Tom closes the file on the appointment.
  -q-clear

## Questions
- q-clear — how can Maggie clear herself without performing panic?
- q-main — who killed Lisa?
"""


def test_parses_beats_in_order_with_tags_stripped_from_text():
    beats = parse_story(STORY)
    assert len(beats) == 3
    assert beats[0]["text"] == (
        "Maggie chooses this life: the gallery, the commission call "
        "with a closing date.")
    assert beats[0]["strands"] == ["maggie"]
    assert beats[0]["jobs"] == ["establish-protected-world"]
    assert beats[0]["opens"] == []


def test_collects_every_sigil():
    b = parse_story(STORY)[1]
    assert b["strands"] == ["maggie", "simon"]
    assert b["jobs"] == ["crime-and-first-contradiction"]
    assert b["opens"] == ["q-clear"]
    assert b["clues"] == ["c-altered"]
    assert "@maggie" not in b["text"]
    assert "!c-altered" not in b["text"]


def test_close_sigil_is_not_confused_with_a_bullet():
    beats = parse_story(STORY)
    assert beats[2]["closes"] == ["q-clear"]
    assert beats[2]["text"] == "Tom closes the file on the appointment."


def test_headings_carry_no_meaning_and_questions_block_holds_no_beats():
    # "## Act I" must not become a beat, and the Questions block's bullets
    # must not either — spec 3.1, 3.1.1.
    assert all("Act I" not in b["text"] for b in parse_story(STORY))
    assert all("how can Maggie" not in b["text"] for b in parse_story(STORY))


def test_parse_questions_reads_id_and_prose():
    q = parse_questions(STORY)
    assert q["q-clear"] == "how can Maggie clear herself without performing panic?"
    assert q["q-main"] == "who killed Lisa?"


def test_line_numbers_count_from_the_full_text_including_frontmatter():
    beats = parse_story(STORY)
    assert STORY.splitlines()[beats[0]["line"] - 1].startswith("- Maggie chooses")


def test_untagged_beat_is_legal():
    beats = parse_story("- Just a thing that happens.\n")
    assert beats[0]["text"] == "Just a thing that happens."
    assert beats[0]["strands"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_penny_story.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_story'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/penny_story.py
"""Parser for input/book-NN/story.md — the source layer (spec 2026-08-03 §3).

Dependency-free by the split rule: story.md is flat authored text, not nested
data, so it belongs to penny_meta's family and never to PyYAML.

The file is beats in story order. Four sigils and nothing else carry meaning:

    @strand   #job   +q-id / -q-id   !clue-id

`##` headings are for the author's reading and are ignored, with one exception:
`## Questions` holds id-to-prose lines and no beats (spec §3.1.1). That
asymmetry is deliberate — the moment a heading means something, the file has a
form to arrange, and arranging a form is what turned outline-skeleton.md into a
duplicate of outline.md (spec §1).
"""
import re

from scripts.penny_meta import strip_frontmatter  # noqa: F401  (re-exported for callers)

SLUG = r"[a-z0-9][a-z0-9-]*"
SLUG_RE = re.compile(rf"^{SLUG}$")

# A tag is a sigil + slug standing as its own whitespace-delimited token.
# The (?<!\S) guard is what keeps "-q-clear" (a close tag) distinct from
# "- text" (a bullet): a bullet's hyphen is followed by a space, so the slug
# sub-pattern cannot match it. Trailing (?=\s|$) stops "#job." from silently
# parsing as the job "job" with the period dropped into nowhere.
TAG_RE = re.compile(rf"(?<!\S)(?P<sigil>[@#+!-])(?P<slug>{SLUG})(?=\s|$)")

QUESTIONS_HEADING_RE = re.compile(r"^##\s+Questions\s*$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^##\s+")
_BULLET_RE = re.compile(r"^-\s+(?P<rest>.*)$")
_QUESTION_LINE_RE = re.compile(rf"^-\s+(?P<id>q-{SLUG})\s*[—-]\s*(?P<prose>.+?)\s*$")

_SIGIL_KEY = {"@": "strands", "#": "jobs", "+": "opens", "-": "closes", "!": "clues"}


def _blank_beat(line_no):
    return {"text": "", "strands": [], "jobs": [], "opens": [], "closes": [],
            "clues": [], "line": line_no}


def _harvest(beat, raw):
    """Pull tags out of one raw line, returning the prose that is left."""
    for m in TAG_RE.finditer(raw):
        beat[_SIGIL_KEY[m.group("sigil")]].append(m.group("slug"))
    return TAG_RE.sub("", raw)


def _finish(beat, prose_parts):
    beat["text"] = " ".join(" ".join(prose_parts).split())
    return beat


def parse_story(text: str) -> list[dict]:
    """Beats in story order. Tags are stripped from each beat's `text`."""
    lines = text.splitlines()
    offset = len(text.splitlines()) - len(strip_frontmatter(text).splitlines())
    beats, current, prose = [], None, []
    in_questions = False

    for i, raw in enumerate(lines):
        if i < offset:
            continue
        if _HEADING_RE.match(raw):
            if current is not None:
                beats.append(_finish(current, prose))
                current, prose = None, []
            in_questions = bool(QUESTIONS_HEADING_RE.match(raw))
            continue
        if in_questions:
            continue
        m = _BULLET_RE.match(raw)
        if m:
            if current is not None:
                beats.append(_finish(current, prose))
            current = _blank_beat(i + 1)
            prose = [_harvest(current, m.group("rest"))]
        elif current is not None:
            if not raw.strip():
                beats.append(_finish(current, prose))
                current, prose = None, []
            else:
                prose.append(_harvest(current, raw.strip()))

    if current is not None:
        beats.append(_finish(current, prose))
    return [b for b in beats if b["text"] or any(
        b[k] for k in ("strands", "jobs", "opens", "closes", "clues"))]


def parse_questions(text: str) -> dict[str, str]:
    """id -> prose, from the single `## Questions` block (spec §3.1.1)."""
    out, in_block = {}, False
    for raw in text.splitlines():
        if _HEADING_RE.match(raw):
            in_block = bool(QUESTIONS_HEADING_RE.match(raw))
            continue
        if not in_block:
            continue
        m = _QUESTION_LINE_RE.match(raw)
        if m:
            out[m.group("id")] = m.group("prose")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_penny_story.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: 787 passing, 0 failing.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_story.py tests/test_penny_story.py
git commit -m "feat(story): parse story.md beats and the four sigils"
```

---

### Task 2: `parse_cut_plan` — the approved chapter grouping

**Files:**
- Modify: `scripts/penny_story.py`
- Test: `tests/test_penny_story.py`

**Interfaces:**
- Consumes: Task 1's module.
- Produces: `parse_cut_plan(text: str) -> list[dict]` — each chapter `{"num": int, "title": str, "beats": list[int], "summary": str, "compress": str, "tracks": dict[str, str]}`. `beats` are 1-based indices into `parse_story`'s list, expanded from ranges.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_penny_story.py
from scripts.penny_story import parse_cut_plan

CUT_PLAN = """---
book: 02
---

## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-3
- **Summary:** Maggie's chosen life, and the body that ends it.
- **Compress:** Gallery logistics and the drive out.
- **M:** The murder enters a world we have just been shown.
- **P:** Maggie is happy, which is what she has to lose.

## Chapter 02 — The Woman Who Found Her

- **Beats:** 4, 6-7
- **Summary:** Faye's account, and the altered appointment.
- **Compress:** Repeated introductions.
- **M:** The appointment contradiction lands.
"""


def test_parse_cut_plan_expands_ranges_and_lists():
    chapters = parse_cut_plan(CUT_PLAN)
    assert [c["num"] for c in chapters] == [1, 2]
    assert chapters[0]["beats"] == [1, 2, 3]
    assert chapters[1]["beats"] == [4, 6, 7]


def test_parse_cut_plan_reads_title_summary_compress():
    c = parse_cut_plan(CUT_PLAN)[0]
    assert c["title"] == "The Life Maggie Chose"
    assert c["summary"] == "Maggie's chosen life, and the body that ends it."
    assert c["compress"] == "Gallery logistics and the drive out."


def test_parse_cut_plan_reads_track_rows_keyed_by_letter():
    chapters = parse_cut_plan(CUT_PLAN)
    assert chapters[0]["tracks"] == {
        "M": "The murder enters a world we have just been shown.",
        "P": "Maggie is happy, which is what she has to lose."}
    assert list(chapters[1]["tracks"]) == ["M"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_penny_story.py -k cut_plan -v`
Expected: FAIL — `ImportError: cannot import name 'parse_cut_plan'`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/penny_story.py`:

```python
_CUT_CHAPTER_RE = re.compile(r"^##\s+Chapter\s+(?P<num>\d+)\s*[—-]\s*(?P<title>.+?)\s*$")
_CUT_FIELD_RE = re.compile(r"^\s*-\s+\*\*(?P<key>Beats|Summary|Compress):\*\*\s*(?P<val>.*)$")
_CUT_TRACK_RE = re.compile(r"^\s*-\s+\*\*(?P<letter>[A-Z]):\*\*\s*(?P<val>.*)$")
_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def _expand_beats(spec: str) -> list[int]:
    out = []
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        m = _RANGE_RE.match(part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            out.extend(range(lo, hi + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def parse_cut_plan(text: str) -> list[dict]:
    """The showrunner-approved grouping (spec §5.1)."""
    chapters, current = [], None
    for raw in text.splitlines():
        m = _CUT_CHAPTER_RE.match(raw)
        if m:
            current = {"num": int(m.group("num")), "title": m.group("title"),
                       "beats": [], "summary": "", "compress": "", "tracks": {}}
            chapters.append(current)
            continue
        if current is None:
            continue
        fm = _CUT_FIELD_RE.match(raw)
        if fm:
            key, val = fm.group("key"), fm.group("val").strip()
            if key == "Beats":
                current["beats"] = _expand_beats(val)
            else:
                current[key.lower()] = val
            continue
        tm = _CUT_TRACK_RE.match(raw)
        if tm:
            current["tracks"][tm.group("letter")] = tm.group("val").strip()
    return chapters
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_penny_story.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_story.py tests/test_penny_story.py
git commit -m "feat(story): parse the approved cut plan"
```

---

### Task 3: `story_cut.check_story` — the seven refusals

**Files:**
- Create: `scripts/story_cut.py`
- Test: `tests/test_story_cut.py`

**Interfaces:**
- Consumes: `penny_story.parse_story`, `parse_questions`, `parse_cut_plan`; `penny_wiring.QID_RE`.
- Produces: `check_story(story_text, cut_plan_text, job_ids, clue_ids) -> dict` with keys `"blocking"` and `"notes"`, values `list[str]` shaped `"<finding-id>: <prose>"`. `job_ids` and `clue_ids` are `list[str]`, injected by the caller so this function stays free of genre and series lookups.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_story_cut.py
from scripts.story_cut import check_story

JOBS = ["establish-protected-world", "crime-and-first-contradiction"]
CLUES = ["c-altered", "c-vase"]

GOOD_STORY = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie #crime-and-first-contradiction +q-clear !c-altered

- The vase is wrong.
  @maggie !c-vase -q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""

GOOD_PLAN = """## Chapter 01 — One

- **Beats:** 1-2
- **Summary:** s
- **Compress:** c

## Chapter 02 — Two

- **Beats:** 3
- **Summary:** s
- **Compress:** c
"""


def _ids(findings):
    return sorted(f.split(":")[0] for f in findings)


def test_clean_story_and_plan_produce_no_findings():
    r = check_story(GOOD_STORY, GOOD_PLAN, JOBS, CLUES)
    assert r["blocking"] == []


def test_unknown_job_is_named():
    story = GOOD_STORY.replace("#establish-protected-world", "#invented-job")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert _ids(r["blocking"]) == ["unknown-job"]
    assert "invented-job" in r["blocking"][0]


def test_unknown_clue_is_named():
    story = GOOD_STORY.replace("!c-vase", "!c-ghost")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unknown-clue" in _ids(r["blocking"])


def test_unscheduled_clue_is_named_when_no_beat_plants_it():
    story = GOOD_STORY.replace(" !c-vase", "")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unscheduled-clue" in _ids(r["blocking"])
    assert "c-vase" in " ".join(r["blocking"])


def test_orphan_question_when_closed_without_opening():
    story = GOOD_STORY.replace("+q-clear", "")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "orphan-question" in _ids(r["blocking"])


def test_unknown_question_when_absent_from_questions_block():
    story = GOOD_STORY.replace("- q-clear — how can Maggie clear herself?", "")
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    assert "unknown-question" in _ids(r["blocking"])


def test_beats_without_chapter_when_plan_misses_a_beat():
    plan = GOOD_PLAN.replace("- **Beats:** 3", "- **Beats:** 2")
    r = check_story(GOOD_STORY, plan, JOBS, CLUES)
    assert "beats-without-chapter" in _ids(r["blocking"])
    assert "3" in " ".join(r["blocking"])


def test_unknown_strand_when_slug_contract_is_broken():
    story = GOOD_STORY.replace("@maggie", "@Maggie", 1)
    r = check_story(story, GOOD_PLAN, JOBS, CLUES)
    # "@Maggie" cannot tokenise as a tag at all, so the beat loses its strand
    # rather than carrying an illegal one; the plan must still be complete.
    assert r["blocking"] == [] or "unknown-strand" in _ids(r["blocking"])


def test_a_beat_claimed_by_two_chapters_is_named():
    plan = GOOD_PLAN.replace("- **Beats:** 3", "- **Beats:** 2-3")
    r = check_story(GOOD_STORY, plan, JOBS, CLUES)
    assert "duplicate-beat" in _ids(r["blocking"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_story_cut.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.story_cut'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/story_cut.py
"""Validate story.md + cut-plan.md, then emit outline.md (spec 2026-08-03).

Deterministic throughout: this module makes no LLM judgment. The one judgment
in the cut — where chapter boundaries fall — is made by the `chapter-cutter`
agent and approved by the showrunner before this module ever runs (spec §5).

No waivers exist at this level (spec §8). Fix the story or fix the cut plan.
"""
import sys

from scripts.penny_story import (SLUG_RE, parse_cut_plan, parse_questions,
                                 parse_story)
from scripts.penny_wiring import QID_RE


def check_story(story_text: str, cut_plan_text: str,
                job_ids: list, clue_ids: list) -> dict:
    """Named findings over the story and its cut plan.

    job_ids and clue_ids are injected rather than looked up so this function
    holds no genre or series knowledge — the engine's location-agnostic rule.
    """
    blocking: list[str] = []
    notes: list[str] = []

    beats = parse_story(story_text)
    questions = parse_questions(story_text)
    chapters = parse_cut_plan(cut_plan_text)

    known_jobs, known_clues = set(job_ids), set(clue_ids)
    planted: set = set()
    opened: set = set()

    for n, beat in enumerate(beats, 1):
        for slug in beat["strands"]:
            if not SLUG_RE.match(slug):
                blocking.append(
                    f"unknown-strand: beat {n} tags @{slug}, which breaks the "
                    f"slug contract ^[a-z0-9][a-z0-9-]*$ — strand ids become "
                    f"filenames on the strand pages")
        for slug in beat["jobs"]:
            if slug not in known_jobs:
                blocking.append(
                    f"unknown-job: beat {n} tags #{slug}, which the active "
                    f"genre's macro-structure does not declare")
        for cid in beat["clues"]:
            if cid not in known_clues:
                blocking.append(
                    f"unknown-clue: beat {n} tags !{cid}, which is not in the "
                    f"whodunit ledger")
            planted.add(cid)
        for qid in beat["opens"]:
            opened.add(qid)
        for qid in beat["opens"] + beat["closes"]:
            if not QID_RE.match(qid):
                blocking.append(
                    f"unknown-question: beat {n} names '{qid}', which is not a "
                    f"question id (expected q-…)")
            elif qid not in questions:
                blocking.append(
                    f"unknown-question: beat {n} names {qid}, absent from the "
                    f"## Questions block — the wiring line needs its prose")
        for qid in beat["closes"]:
            if qid not in opened:
                blocking.append(
                    f"orphan-question: beat {n} closes {qid}, which no earlier "
                    f"beat opens")

    for cid in clue_ids:
        if cid not in planted:
            blocking.append(
                f"unscheduled-clue: ledger clue [{cid}] is planted by no beat — "
                f"an unplanted clue is an unfair reveal")

    owners: dict = {}
    for ch in chapters:
        for idx in ch["beats"]:
            owners.setdefault(idx, []).append(ch["num"])
    for n in range(1, len(beats) + 1):
        who = owners.get(n, [])
        if not who:
            blocking.append(
                f"beats-without-chapter: beat {n} lands in no chapter — the cut "
                f"plan must cover every beat")
        elif len(who) > 1:
            blocking.append(
                f"duplicate-beat: beat {n} is claimed by chapters {who} — one "
                f"beat, one home")
    for idx in sorted(owners):
        if idx > len(beats):
            blocking.append(
                f"beats-without-chapter: the cut plan claims beat {idx} but the "
                f"story has only {len(beats)}")

    return {"blocking": blocking, "notes": notes}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_story_cut.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut.py
git commit -m "feat(story): named refusals over story.md and its cut plan"
```

---

### Task 4: The emitter — packet-format chapter blocks

**Files:**
- Modify: `scripts/story_cut.py`
- Test: `tests/test_story_cut_emit.py`

**Interfaces:**
- Consumes: Task 3's module; `penny_wiring.parse_packet_sections`, `parse_wired_chapters`.
- Produces: `emit_outline(story_text, cut_plan_text, questions, ledger, *, reveal_chapter, guardrails, job_titles) -> str` — the full `outline.md` body (no frontmatter; Task 5 adds it). `ledger` is `dict` clue-id → description. `job_titles` is `dict` job-id → human title. `guardrails` is `str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_story_cut_emit.py
from scripts.penny_wiring import (parse_packet_sections, parse_required_beats,
                                  parse_wired_chapters, chapter_block)
from scripts.story_cut import emit_outline
from scripts.penny_story import parse_questions

STORY = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered

- Tom rules it out.
  @tom -q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""

PLAN = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen, and the body that ends it.
- **Compress:** Gallery logistics.
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right in a way Maggie resents.
"""

LEDGER = {"c-altered": "the handover appointment, changed in Maggie's name"}
JOB_TITLES = {"establish-protected-world": "Establish the Protected World",
              "crime-and-first-contradiction": "Deliver the Crime and Its First Contradiction"}


def _emit():
    return emit_outline(STORY, PLAN, parse_questions(STORY), LEDGER,
                        reveal_chapter=2, guardrails="Do not name the culprit early.",
                        job_titles=JOB_TITLES)


def test_emits_one_block_per_chapter_that_the_wiring_parser_accepts():
    chapters = parse_wired_chapters(_emit())
    assert [c["num"] for c in chapters] == [1, 2]
    assert chapters[0]["title"] == "The Life Maggie Chose"


def test_required_beats_are_the_chapters_beats_in_order():
    sections = parse_packet_sections(chapter_block(_emit(), 1))
    beats = parse_required_beats(sections)
    assert beats == ["Maggie chooses this life.", "The appointment was altered."]


def test_wiring_carries_opens_and_closes_with_question_prose():
    out = _emit()
    assert "- **Opens:** q-clear — how can Maggie clear herself?" in out
    assert "- **Closes:** q-clear — how can Maggie clear herself?" in out


def test_because_chains_each_chapter_to_the_one_before():
    out = _emit()
    assert "- **Because:** ch 01" in out
    assert out.count("- **Because:**") == 1  # chapter 01 has no antecedent


def test_clue_section_renders_the_ledger_description():
    sections = parse_packet_sections(chapter_block(_emit(), 1))
    assert "c-altered" in sections["Clues and Plants"]
    assert "handover appointment" in sections["Clues and Plants"]


def test_character_knowledge_names_only_strands_seen_so_far():
    ch1 = parse_packet_sections(chapter_block(_emit(), 1))["Character Knowledge"]
    assert "maggie" in ch1 and "simon" in ch1
    assert "tom" not in ch1


def test_guardrails_and_purpose_are_derived():
    sections = parse_packet_sections(chapter_block(_emit(), 1))
    assert "Do not name the culprit early." in sections["Guardrails"]
    assert "Establish the Protected World" in sections["Chapter Purpose"]


def test_track_movement_rows_come_from_the_cut_plan():
    sections = parse_packet_sections(chapter_block(_emit(), 2))
    assert "- **M:** The police are right in a way Maggie resents." in sections["Track Movement"]


def test_compress_line_is_per_chapter_not_boilerplate():
    a = parse_packet_sections(chapter_block(_emit(), 1))["Reader-Facing Shape"]
    b = parse_packet_sections(chapter_block(_emit(), 2))["Reader-Facing Shape"]
    assert "Gallery logistics." in a
    assert "Procedure." in b
    assert a != b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_story_cut_emit.py -v`
Expected: FAIL — `ImportError: cannot import name 'emit_outline'`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/story_cut.py`:

```python
def _carried(chapters_beats, upto_index, opened_by, closed_by):
    """Question ids opened at or before this chapter and not yet closed."""
    live = []
    for qid, opened_at in opened_by.items():
        if opened_at <= upto_index and closed_by.get(qid, 10 ** 9) >= upto_index:
            live.append(qid)
    return sorted(live)


def emit_outline(story_text: str, cut_plan_text: str, questions: dict,
                 ledger: dict, *, reveal_chapter: int, guardrails: str,
                 job_titles: dict) -> str:
    """Expand an approved cut plan into packet-format chapter blocks (spec §5.2)."""
    beats = parse_story(story_text)
    chapters = parse_cut_plan(cut_plan_text)

    opened_by, closed_by, beat_chapter = {}, {}, {}
    for ch in chapters:
        for idx in ch["beats"]:
            beat_chapter[idx] = ch["num"]
    for n, beat in enumerate(beats, 1):
        for qid in beat["opens"]:
            opened_by.setdefault(qid, beat_chapter.get(n, 0))
        for qid in beat["closes"]:
            closed_by[qid] = beat_chapter.get(n, 0)

    def qline(qid):
        return f"{qid} — {questions.get(qid, '')}".rstrip(" —")

    out = []
    for pos, ch in enumerate(chapters):
        mine = [beats[i - 1] for i in ch["beats"] if 1 <= i <= len(beats)]
        strands_so_far = sorted({s for i in range(1, max(ch["beats"], default=0) + 1)
                                 for s in (beats[i - 1]["strands"] if i <= len(beats) else [])})
        opens = [q for b in mine for q in b["opens"]]
        closes = [q for b in mine for q in b["closes"]]
        jobs = []
        for b in mine:
            for j in b["jobs"]:
                if j not in jobs:
                    jobs.append(j)

        out.append(f"## Chapter {ch['num']:02d} — {ch['title']}\n")
        out.append("### Chapter Summary\n" + ch["summary"] + "\n")
        out.append("### Chapter Purpose\n"
                   + "\n".join(f"- {job_titles.get(j, j)}" for j in jobs) + "\n")

        carried = _carried(chapters, ch["num"], opened_by, closed_by)
        start = [f"- Chapter {ch['num']:02d} is forced by ch {chapters[pos - 1]['num']:02d}."] \
            if pos else ["- This chapter opens the book."]
        start += [f"- Carried in: {qline(q)}" for q in carried if q not in opens]
        out.append("### Starting State\n" + "\n".join(start) + "\n")

        end = [f"- {mine[-1]['text']}"] if mine else []
        end += [f"- Closes: {qline(q)}" for q in closes]
        end += [f"- Hook question remains: {qline(q)}" for q in opens if q not in closes]
        out.append("### Ending State\n" + "\n".join(end) + "\n")

        out.append("### Reader-Facing Shape\nPrimary anchor:\n"
                   + (f"- {mine[0]['text']}\n" if mine else "")
                   + "\nCompress:\n- " + ch["compress"] + "\n")

        out.append("### Required Beats\n"
                   + "\n".join(f"- {b['text']}" for b in mine) + "\n")

        clues = [c for b in mine for c in b["clues"]]
        out.append("### Clues and Plants\n" + ("\n".join(
            f"- [{c}] {ledger.get(c, c)}" for c in clues)
            or "- No ledger clue is scheduled for this chapter.") + "\n")

        out.append("### Character Knowledge\nOn the page so far:\n"
                   + "\n".join(f"- {s}" for s in strands_so_far) + "\n"
                   + f"\nNot yet known:\n- The solution, until chapter "
                     f"{reveal_chapter:02d}.\n")

        out.append("### Guardrails\n- " + guardrails.strip()
                   + f"\n- Do not resolve the mystery before chapter {reveal_chapter:02d}.\n")

        wiring = []
        if opens:
            wiring.append(f"- **Hook:** {qline(opens[0])}")
        if pos:
            wiring.append(f"- **Because:** ch {chapters[pos - 1]['num']:02d}")
        wiring += [f"- **Opens:** {qline(q)}" for q in opens]
        wiring += [f"- **Closes:** {qline(q)}" for q in closes]
        wiring += [f"- **Carries:** {q}" for q in carried]
        out.append("### Chapter Structure\n" + "\n".join(wiring) + "\n")

        out.append("### Track Movement\n" + "\n".join(
            f"- **{k}:** {v}" for k, v in ch["tracks"].items()) + "\n")

    return "\n".join(out).rstrip() + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_story_cut_emit.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_emit.py
git commit -m "feat(story): emit packet-format chapter blocks from the cut plan"
```

---

### Task 5: Staleness stamps and the re-cut refusal

**Files:**
- Modify: `scripts/story_cut.py`
- Test: `tests/test_story_cut_staleness.py`

**Interfaces:**
- Consumes: `penny_meta.parse_frontmatter`, `penny_meta.strip_frontmatter`; `hashlib`.
- Produces:
  - `body_sha(text: str) -> str` — sha256 of the body with frontmatter stripped.
  - `stamp_outline(body, *, story_sha, cut_sha) -> str` — body with frontmatter containing `built_from_story`, `built_from_cut`, `cut_output_sha256`.
  - `recut_refusal(existing_outline_text: str) -> str | None` — the `outline-modified-since-cut` finding, or `None` when re-cutting is safe.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_story_cut_staleness.py
import pytest

from scripts.story_cut import body_sha, recut_refusal, stamp_outline


def test_stamped_outline_round_trips_and_is_safe_to_recut():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64)
    assert "built_from_story: " + "a" * 64 in stamped
    assert recut_refusal(stamped) is None


def test_hand_edited_outline_refuses_by_name():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64)
    edited = stamped.replace("## Chapter 01 — One", "## Chapter 01 — One, Revised")
    finding = recut_refusal(edited)
    assert finding is not None
    assert finding.startswith("outline-modified-since-cut:")


def test_outline_with_no_stamp_is_treated_as_hand_authored_and_refuses():
    # Book 01's outline predates the cut entirely. Overwriting it would be the
    # exact loss spec 7 forbids, so absence of a stamp is a refusal, never a
    # licence.
    finding = recut_refusal("## Chapter 01 — One\n")
    assert finding is not None
    assert "no cut_output_sha256" in finding


def test_body_sha_ignores_frontmatter():
    a = stamp_outline("body\n", story_sha="a" * 64, cut_sha="b" * 64)
    b = stamp_outline("body\n", story_sha="c" * 64, cut_sha="d" * 64)
    assert body_sha(a) == body_sha(b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_story_cut_staleness.py -v`
Expected: FAIL — `ImportError: cannot import name 'body_sha'`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/story_cut.py`:

```python
import hashlib

from scripts.penny_meta import parse_frontmatter, strip_frontmatter


def body_sha(text: str) -> str:
    """sha256 of the outline body, frontmatter excluded.

    Excluding frontmatter is what lets the stamp describe the prose without
    describing itself — a hash that covered its own field could never match.
    """
    return hashlib.sha256(strip_frontmatter(text).encode("utf-8")).hexdigest()


def stamp_outline(body: str, *, story_sha: str, cut_sha: str) -> str:
    out_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return ("---\n"
            f"built_from_story: {story_sha}\n"
            f"built_from_cut: {cut_sha}\n"
            f"cut_output_sha256: {out_sha}\n"
            "---\n\n" + body)


def recut_refusal(existing_outline_text: str) -> "str | None":
    """None when re-cutting is safe; a named finding when it is not (spec §7)."""
    meta = parse_frontmatter(existing_outline_text)
    recorded = meta.get("cut_output_sha256")
    if not recorded:
        return ("outline-modified-since-cut: the outline carries no "
                "cut_output_sha256, so it was not produced by the cut — "
                "refusing to overwrite hand-authored chapter work")
    if body_sha(existing_outline_text) != recorded:
        return ("outline-modified-since-cut: the outline has been edited since "
                "the cut wrote it — re-cutting would discard that work. Edit "
                "story.md and cut a fresh book, or keep the hand edits")
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_story_cut_staleness.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_staleness.py
git commit -m "feat(story): stamp the cut and refuse to overwrite hand edits"
```

---

### Task 6: CLI — genre, ledger, and ledger write-back

**Files:**
- Modify: `scripts/story_cut.py`
- Test: `tests/test_story_cut_cli.py`

**Interfaces:**
- Consumes: `penny_paths.series_root`, `penny_genre.macro_structure`, `outline_views.parse_jobs`, PyYAML for the ledger.
- Produces: `main(argv=None) -> int` — `story_cut.py <book>`; exit `0` clean, `1` findings, `2` usage. Writes `input/book-NN/outline.md` and updates `clue_schedule` chapter numbers in `series/whodunit/book-NN.yaml`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_story_cut_cli.py
import yaml

from scripts import story_cut


def _series(tmp_path, monkeypatch):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-02").mkdir(parents=True)
    (tmp_path / "series" / "whodunit").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "series-guardrails.md").write_text(
        "Do not name the culprit early.\n", encoding="utf-8")
    (tmp_path / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-altered +q-clear\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    (tmp_path / "input" / "book-02" / "cut-plan.md").write_text(
        "## Chapter 01 — One\n\n- **Beats:** 1\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n\n"
        "## Chapter 02 — Two\n\n- **Beats:** 2\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n", encoding="utf-8")
    (tmp_path / "series" / "whodunit" / "book-02.yaml").write_text(
        "reveal_chapter: 2\nclue_schedule:\n  - id: c-altered\n    chapter: 99\n"
        "    description: the handover appointment, changed\n", encoding="utf-8")
    monkeypatch.setattr(story_cut.penny_paths, "series_root", lambda *a, **k: tmp_path)
    monkeypatch.setattr(story_cut, "_job_ids_and_titles",
                        lambda: (["establish-protected-world"],
                                 {"establish-protected-world": "Establish the Protected World"}))
    return tmp_path


def test_clean_cut_writes_the_outline_and_exits_zero(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    text = (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8")
    assert "## Chapter 01 — One" in text
    assert "cut_output_sha256:" in text


def test_cut_writes_resolved_chapter_numbers_back_into_the_ledger(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    story_cut.main(["02"])
    led = yaml.safe_load((root / "series" / "whodunit" / "book-02.yaml").read_text())
    assert led["clue_schedule"][0]["chapter"] == 2


def test_findings_exit_one_and_write_nothing(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    plan = root / "input" / "book-02" / "cut-plan.md"
    plan.write_text(plan.read_text().replace("- **Beats:** 2", "- **Beats:** 1"),
                    encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert not (root / "input" / "book-02" / "outline.md").exists()
    assert "beats-without-chapter" in capsys.readouterr().out


def test_usage_error_exits_two(capsys):
    assert story_cut.main([]) == 2


def test_second_cut_refuses_after_a_hand_edit(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    outline = root / "input" / "book-02" / "outline.md"
    outline.write_text(outline.read_text() + "\nhand edit\n", encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert "outline-modified-since-cut" in capsys.readouterr().out


def test_second_cut_is_allowed_when_the_outline_is_untouched(tmp_path, monkeypatch):
    _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    assert story_cut.main(["02"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_story_cut_cli.py -v`
Expected: FAIL — `AttributeError: module 'scripts.story_cut' has no attribute 'penny_paths'`

- [ ] **Step 3: Write minimal implementation**

Append to `scripts/story_cut.py`:

```python
import yaml  # ledger only — nested human-edited data (dependency-split rule)

from scripts import penny_genre, penny_paths
from scripts.outline_views import parse_jobs


def _job_ids_and_titles():
    """(ids, id->title) from the active genre's macro-structure, or ([], {})."""
    path = penny_genre.macro_structure()
    if path is None or not path.is_file():
        return [], {}
    jobs = parse_jobs(path.read_text(encoding="utf-8"))
    return [jid for jid, _ in jobs], {jid: title for jid, title in jobs}


def _ledger(root, book):
    p = root / "series" / "whodunit" / f"book-{book}.yaml"
    if not p.is_file():
        return {}, None, p
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    clues = {c["id"]: c.get("description", c["id"])
             for c in (data.get("clue_schedule") or []) if c.get("id")}
    return clues, data, p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: story_cut.py <book>", file=sys.stderr)
        return 2
    book = argv[0]
    root = penny_paths.series_root()
    bookdir = root / "input" / f"book-{book}"
    story_p, plan_p = bookdir / "story.md", bookdir / "cut-plan.md"
    for p in (story_p, plan_p):
        if not p.is_file():
            print(f"story_cut: missing {p}", file=sys.stderr)
            return 2

    story_text = story_p.read_text(encoding="utf-8")
    plan_text = plan_p.read_text(encoding="utf-8")
    job_ids, job_titles = _job_ids_and_titles()
    clues, ledger_data, ledger_p = _ledger(root, book)

    outline_p = bookdir / "outline.md"
    findings = []
    if outline_p.is_file():
        refusal = recut_refusal(outline_p.read_text(encoding="utf-8"))
        if refusal:
            findings.append(refusal)

    result = check_story(story_text, plan_text, job_ids, list(clues))
    findings.extend(result["blocking"])
    for note in result["notes"]:
        print(f"note: {note}")
    if findings:
        for f in findings:
            print(f)
        return 1

    guard_p = root / "config" / "series-guardrails.md"
    guardrails = guard_p.read_text(encoding="utf-8") if guard_p.is_file() else ""
    reveal = int((ledger_data or {}).get("reveal_chapter") or 0)

    body = emit_outline(story_text, plan_text, parse_questions(story_text), clues,
                        reveal_chapter=reveal, guardrails=guardrails,
                        job_titles=job_titles)
    outline_p.write_text(
        stamp_outline(body,
                      story_sha=hashlib.sha256(story_text.encode()).hexdigest(),
                      cut_sha=hashlib.sha256(plan_text.encode()).hexdigest()),
        encoding="utf-8")

    # Chapter numbers are derived, so the ledger's are too (spec §6). Safe
    # because lock-mystery runs after the cut — the ledger is still unsealed.
    if ledger_data and ledger_data.get("clue_schedule"):
        beats = parse_story(story_text)
        chapters = parse_cut_plan(plan_text)
        home = {i: c["num"] for c in chapters for i in c["beats"]}
        where = {cid: home.get(n) for n, b in enumerate(beats, 1) for cid in b["clues"]}
        for entry in ledger_data["clue_schedule"]:
            if entry.get("id") in where and where[entry["id"]]:
                entry["chapter"] = where[entry["id"]]
        ledger_p.write_text(yaml.safe_dump(ledger_data, sort_keys=False,
                                           allow_unicode=True), encoding="utf-8")

    print(f"story_cut: wrote {outline_p} ({len(parse_cut_plan(plan_text))} chapters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_story_cut_cli.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_cli.py
git commit -m "feat(story): story_cut CLI, genre job lookup, ledger write-back"
```

---

### Task 7: `plot_stage.py` — swap the stages

**Files:**
- Modify: `scripts/plot_stage.py` (`STAGE_ORDER`, `stage_paths`, `_UPSTREAM`, `_readback_source`)
- Test: `tests/test_plot_stage.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `STAGE_ORDER` gains `"cut"` after `"weave"`; `stage_paths()["chapters"]` and `["weave"]` return `input/book-NN/story.md`; `stage_paths()["cut"]` returns `input/book-NN/outline.md`; `_UPSTREAM["cut"] == ["chapters", "whodunit"]`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_plot_stage.py
def test_chapters_and_weave_stages_point_at_story_md(tmp_path):
    root = _series(tmp_path)
    paths = stage_paths("01", root)
    assert paths["chapters"].name == "story.md"
    assert paths["weave"] == paths["chapters"]


def test_cut_stage_produces_the_outline(tmp_path):
    root = _series(tmp_path)
    assert stage_paths("01", root)["cut"].name == "outline.md"
    assert "cut" in STAGE_ORDER
    assert STAGE_ORDER.index("cut") == STAGE_ORDER.index("weave") + 1


def test_readback_reads_story_before_the_cut_and_outline_after(tmp_path):
    from scripts.plot_stage import _readback_source
    root = _series(tmp_path)
    story = root / "input" / "book-01" / "story.md"
    story.parent.mkdir(parents=True, exist_ok=True)
    story.write_text("- a beat\n", encoding="utf-8")
    assert _readback_source("01", repo_root=root) == story
    story.unlink()
    outline = root / "input" / "book-01" / "outline.md"
    outline.write_text("## Chapter 01 — One\n", encoding="utf-8")
    assert _readback_source("01", repo_root=root) == outline


def test_no_stage_path_names_the_retired_skeleton(tmp_path):
    root = _series(tmp_path)
    assert all("skeleton" not in p.name for p in stage_paths("01", root).values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_plot_stage.py -k "story_md or cut_stage or skeleton or readback_reads" -v`
Expected: FAIL — `KeyError: 'cut'` / assertion on `outline-skeleton.md`

- [ ] **Step 3: Write minimal implementation**

In `scripts/plot_stage.py`:

```python
STAGE_ORDER = ["premise", "ending", "turning-points", "counterplot",
               "chapters", "weave", "cut", "readback"]
```

In `stage_paths`, replace the `skel = ...` line and the `"chapters"`/`"weave"` entries:

```python
    story = root / "input" / f"book-{book}" / "story.md"
    outline = root / "input" / f"book-{book}" / "outline.md"
    return {"material": plot / "material.md", "premise": plot / "premise.md",
            "ending": plot / "ending.md", "turning-points": plot / "turning-points.md",
            "counterplot": out / "mystery-solution.md",
            # chapters and weave are one act now: strands and questions are
            # tagged inline as the beats are written, so there is no second
            # pass to bolt wiring on (spec 2026-08-03 §4).
            "chapters": story, "weave": story, "cut": outline,
            "readback": out / "reports" / "outline-fan.md",
            "whodunit": root / "series" / "whodunit" / f"book-{book}.yaml"}
```

In `_UPSTREAM`, add the `cut` entry and leave the rest:

```python
    "cut": ["chapters", "whodunit"],
```

Replace `_readback_source`'s body and docstring:

```python
def _readback_source(book: str, *, repo_root=None) -> Path:
    """The file the reader's copy is cut from.

    story.md before the cut, outline.md after it (spec 2026-08-03 §4). The
    skeleton branch this function used to carry is gone with the file.
    """
    root = _root(repo_root)
    story = stage_paths(book, root)["chapters"]
    if story.is_file():
        return story
    outline = root / "input" / f"book-{book}" / "outline.md"
    if outline.is_file():
        return outline
    sys.exit(f"plot_stage: no story or outline for book {book} — looked for "
             f"{story} and {outline}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_plot_stage.py -v`
Expected: PASS. Some pre-existing tests referencing `outline-skeleton.md` will fail — update them to `story.md`, since the artifact is retired by design, not by accident.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "feat(story): plot_stage swaps chapters/weave onto story.md, adds cut"
```

---

### Task 8: The `chapter-cutter` agent

**Files:**
- Create: `agents/chapter-cutter.md`
- Delete: `agents/chapter-weaver.md`
- Test: `tests/test_plot_agents.py` — the existing plot-agent contract file, which already
  pins `chapter-weaver`. Its weaver assertions are replaced, not added to.

**Interfaces:**
- Consumes: nothing in Python.
- Produces: an agent whose frontmatter `name:` is `chapter-cutter`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_plot_agents.py — and delete its chapter-weaver assertions,
# which pin an agent this task retires
from pathlib import Path


def test_chapter_cutter_exists_and_weaver_is_retired():
    root = Path(__file__).resolve().parents[1]
    cutter = root / "agents" / "chapter-cutter.md"
    assert cutter.is_file()
    assert "name: chapter-cutter" in cutter.read_text(encoding="utf-8")
    assert not (root / "agents" / "chapter-weaver.md").exists()


def test_chapter_cutter_proposes_and_never_writes():
    root = Path(__file__).resolve().parents[1]
    text = (root / "agents" / "chapter-cutter.md").read_text(encoding="utf-8")
    assert "cut-plan.md" in text
    assert "writes nothing" in text.lower() or "never writes" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_plot_agents.py -k chapter_cutter -v`
Expected: FAIL — file does not exist.

- [ ] **Step 3: Write the agent**

```markdown
---
name: chapter-cutter
description: Proposes where a book's chapters fall, from story.md's beats — boundaries, titles, summaries, per-chapter compress lines and track movement. Proposes only; writes nothing. Absorbs the retired chapter-weaver.
---
# Chapter Cutter

**Role posture:** constructive planner. Context-rich: you read the sealed solution,
because you are deciding where the road's junctions go and you must know where it ends.

**Independence:** not this agent's property. Knowing the solution is what lets you land a
turn on the right beat; it is not licence to put the answer on the page.

**Inputs:** `{ input/book-NN/story.md, the genre beat sheet, the genre macro-structure,
series/whodunit/book-NN.yaml, output/book-NN/mystery-solution.md }`.

**You propose. You never write.** Emit the cut plan as your message. The showrunner edits
it and saves the approved version to `input/book-NN/cut-plan.md`. Only the approved file
is cut from. Writing the file yourself would make a generated artifact look approved —
the same forged-certificate error a lock field inside the data it gates would be.

## What you decide

Chapter count, and which beats become which chapter. Combining and splitting are yours:
the foundation underneath is already sound, so these are technical calls, not story ones.
Use the genre beat sheet's turn positions — a beat carrying a turn should land at the
position the beat sheet expects, and a chapter should not be asked to carry more
obligations than `obligations.max_per_chapter` allows.

## Output format — exactly this

```markdown
## Chapter 01 — <title>

- **Beats:** 1-3
- **Summary:** <one line; this is what the story-at-a-glance view renders>
- **Compress:** <what this chapter should spend few words on — specific to THIS
  chapter, never a standing phrase>
- **M:** <how the mystery track moves here>
- **P:** <the personal track>
```

`Beats:` takes indices into `story.md`'s beats in order — ranges (`1-3`), lists
(`4, 6-7`), or both. **Every beat must land in exactly one chapter**; `story_cut.py`
refuses `beats-without-chapter` and `duplicate-beat` otherwise.

One `- **X:**` row per track the genre declares. These rows are load-bearing, not
decoration: `tension_check.py`'s `starved-thread` check reads them and so does the
drafter.

## The compress line

Write a different one for every chapter. A standing phrase repeated down the book reads
to the drafter as a vacuum rather than an instruction — that is a live complaint against
the current outline, and this is where it gets fixed.

## What you never do

Never write prose. Never write a ledger or a certificate. Never move the reveal. Never
emit outline sections — Character Knowledge, Guardrails, wiring and the rest are derived
by `story_cut.py` from the ledger, the genre and the story's own tags.
```

- [ ] **Step 4: Delete the weaver and run the tests**

```bash
git rm agents/chapter-weaver.md
python3 -m pytest tests/test_plot_agents.py -v
```
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: all green. If a test pins the agent roster by count or name, update it — the roster changed by design.

- [ ] **Step 6: Commit**

```bash
git add agents/chapter-cutter.md tests/
git commit -m "feat(story): chapter-cutter proposes the cut, absorbing chapter-weaver"
```

---

### Task 9: Retire `outline-skeleton.md` across the repo

**Files:**
- Modify: every file naming the artifact. Enumerate first — this is the step both 2026-07-30 plan defects came from.
- Test: `tests/test_skeleton_retired.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a repo with no live reference to `outline-skeleton.md` outside `docs/`.

- [ ] **Step 1: Enumerate every reference**

Run and read the whole output before editing anything:

```bash
grep -rn "outline-skeleton\|outline_skeleton" \
  scripts/ commands/ agents/ genres/ README.md CLAUDE.md tests/
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_skeleton_retired.py
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_live_reference_to_the_retired_skeleton():
    """docs/ keeps its history; live engine surfaces must not name the file."""
    hits = subprocess.run(
        ["grep", "-rn", "outline-skeleton", "scripts", "commands", "agents",
         "genres", "README.md", "CLAUDE.md"],
        cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert hits == "", f"still naming the retired skeleton:\n{hits}"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_skeleton_retired.py -v`
Expected: FAIL, listing every remaining reference.

- [ ] **Step 4: Remove each reference**

Work the grep list from Step 1 file by file. In each case the replacement is
`input/book-NN/story.md` before the cut and `input/book-NN/outline.md` after it. Delete
comment paragraphs that explain the skeleton's existence rather than rewriting them.
`genres/cozy-mystery/ideation-prompt.md` describes the artifact a showrunner produces —
update it to describe `story.md`'s beat format from spec §3.

- [ ] **Step 5: Run the test and the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(story): retire outline-skeleton.md across the engine"
```

---

### Task 10: `/plot-book` runbook — the cut stage

**Files:**
- Modify: `commands/plot-book.md`
- Test: `tests/test_plot_book_command.py` — the existing runbook contract file. Note it
  already contains `test_runbook_gives_literal_bash_for_every_stamp_call`, which trips on
  deliberate runbook rewrites; re-pin it, since the approved artefact wins.

**Interfaces:**
- Consumes: Tasks 6–8.
- Produces: a runbook whose cut stage dispatches `chapter-cutter`, takes approval, then shells `${CLAUDE_PLUGIN_ROOT}/scripts/story_cut.py`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_plot_book_command.py
def test_plot_book_runs_the_cut_after_approval():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "commands" / "plot-book.md"
            ).read_text(encoding="utf-8")
    assert "chapter-cutter" in text
    assert "scripts/story_cut.py" in text
    assert "cut-plan.md" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -k plot_book_runs_the_cut -v`
Expected: FAIL.

- [ ] **Step 3: Edit the runbook**

Read `commands/plot-book.md` first. Replace the `chapters` and `weave` stage sections
with a single stage that writes `story.md`, and add the cut stage after it:

````markdown
### Stage: cut

1. Dispatch the **`chapter-cutter`** sub-agent with `input/book-$book/story.md`.
   It proposes the grouping and writes nothing.
2. Present the proposal. The showrunner edits boundaries, titles, summaries,
   compress lines and track rows. Save the **approved** plan — and only the
   approved plan — to `input/book-$book/cut-plan.md`.
3. Run the cut:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/story_cut.py" "$book"
```

Exit 0 wrote `input/book-$book/outline.md`. Exit 1 printed named findings — fix
`story.md` or `cut-plan.md` and run it again; there are no waivers here. Exit 2 is a
usage or missing-file error.

Re-cutting is safe while `outline.md` is exactly what the cut wrote. Once it has been
hand-edited the cut refuses `outline-modified-since-cut` rather than discarding the work.
````

- [ ] **Step 4: Run the test and the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add commands/plot-book.md tests/
git commit -m "feat(story): /plot-book gains the cut stage"
```

---

### Task 11: Round-trip proof on book 01

**Files:**
- Create: `tests/fixtures/story/book-01-excerpt.outline.md` (three real chapter blocks, copied from the series' `input/book-01/outline.md`)
- Create: `tests/test_story_cut_roundtrip.py`

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: proof that `emit_outline` produces blocks the existing parsers accept, on real material rather than hand-written fixtures.

**Why this task exists:** every other test uses fixtures written to suit the emitter. This is the only one that proves the emitter's output satisfies the parsers the rest of the engine already runs (spec §9).

- [ ] **Step 1: Build the fixture**

Copy three consecutive chapter blocks from `~/myBooks/pelicanscrook-series/input/book-01/outline.md`
into the fixture path, verbatim. Do not edit them — material written to suit the emitter
proves nothing.

If that folder is unreachable, fall back to `tests/fixtures/outlines/packet-format.md`,
which already holds two packet-format chapter blocks. Two is enough for every assertion
here except the `Because:` chain, which needs a third; add one by copying the second block
and renumbering it.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_story_cut_roundtrip.py
from pathlib import Path

from scripts.penny_wiring import (chapter_block, parse_packet_sections,
                                  parse_required_beats, parse_wired_chapters)
from scripts.penny_story import parse_questions
from scripts.story_cut import emit_outline

FIXTURE = Path(__file__).parent / "fixtures" / "story" / "book-01-excerpt.outline.md"

REQUIRED_SECTIONS = ["Chapter Summary", "Chapter Purpose", "Starting State",
                     "Ending State", "Reader-Facing Shape", "Required Beats",
                     "Clues and Plants", "Character Knowledge", "Guardrails",
                     "Chapter Structure", "Track Movement"]


def _story_and_plan_from(outline_text):
    """Derive beats and a cut plan from a real outline — the lossy direction,
    used here only to build a test input, never as a source (spec §11)."""
    story_lines, plan_lines, n = [], [], 0
    for ch in parse_wired_chapters(outline_text):
        block = chapter_block(outline_text, ch["num"])
        beats = parse_required_beats(parse_packet_sections(block))
        first = n + 1
        for b in beats:
            n += 1
            story_lines.append(f"- {b}\n")
        plan_lines.append(
            f"## Chapter {ch['num']:02d} — {ch['title']}\n\n"
            f"- **Beats:** {first}-{n}\n- **Summary:** s\n- **Compress:** c\n"
            f"- **M:** m\n")
    return "\n".join(story_lines), "\n".join(plan_lines)


def test_emitted_blocks_carry_every_section_the_engine_parses():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={})
    for ch in parse_wired_chapters(emitted):
        sections = parse_packet_sections(chapter_block(emitted, ch["num"]))
        for name in REQUIRED_SECTIONS:
            assert name in sections, f"chapter {ch['num']} lost {name}"


def test_every_beat_survives_the_round_trip_in_order():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={})
    original = [b for ch in parse_wired_chapters(outline)
                for b in parse_required_beats(
                    parse_packet_sections(chapter_block(outline, ch["num"])))]
    produced = [b for ch in parse_wired_chapters(emitted)
                for b in parse_required_beats(
                    parse_packet_sections(chapter_block(emitted, ch["num"])))]
    assert produced == original


def test_chapter_count_and_titles_are_preserved():
    outline = FIXTURE.read_text(encoding="utf-8")
    story, plan = _story_and_plan_from(outline)
    emitted = emit_outline(story, plan, parse_questions(story), {},
                           reveal_chapter=24, guardrails="g", job_titles={})
    assert ([(c["num"], c["title"]) for c in parse_wired_chapters(emitted)]
            == [(c["num"], c["title"]) for c in parse_wired_chapters(outline)])
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_story_cut_roundtrip.py -v`
Expected: FAIL until the fixture exists; then any real mismatch between the emitter and the parsers.

- [ ] **Step 4: Fix the emitter, not the test**

If a section is missing or a beat is lost, the defect is in `emit_outline`. The parsers
are the contract — they are what `packet_assemble.py` and `tension_check.py` already use.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/story tests/test_story_cut_roundtrip.py scripts/story_cut.py
git commit -m "test(story): round-trip the emitter against real book-01 blocks"
```

---

### Task 12: Documentation

**Files:**
- Modify: `README.md`, `CLAUDE.md`
- Test: `tests/test_readme_check_count.py` — holds
  `test_readme_and_claude_md_roster_every_derived_check_id`, which will need the cut's
  seven finding ids added to its roster.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: docs describing `story.md`, the four sigils, the `## Questions` block, the cut, and the re-cut rule.

- [ ] **Step 1: Update `CLAUDE.md`**

In the pipeline section, replace the `outline-skeleton.md` mentions and add above the
packet/map diagram:

```markdown
**The source layer (spec `docs/superpowers/specs/2026-08-03-story-source-layer-design.md`):**

```
story.md    input/book-NN/story.md      beats in story order, four sigils
    │  chapter-cutter proposes, showrunner approves — cut-plan.md
    ▼
outline.md  input/book-NN/outline.md    packet format, generated  (locked)
```

`story.md` carries only what the author decides — what happens, in what order, to whom
(`@strand`), which structural job a beat answers (`#job`), which questions open and close
(`+q-id` / `-q-id`), and where a ledger clue is planted (`!clue-id`). Question prose lives
once, in a `## Questions` block. Everything else in a chapter block — Character Knowledge,
Guardrails, wiring, Starting/Ending State, Chapter Purpose — is **derived** by
`scripts/story_cut.py` from the ledger, the genre and the tags. There is nowhere to type
boilerplate, which is why `story.md` cannot drift into the duplicate that
`outline-skeleton.md` became.

Re-cutting is free while `outline.md` still matches its `cut_output_sha256` stamp, and
refuses `outline-modified-since-cut` the moment it does not. Book 01 predates all of this
and keeps its hand-edited outline.
```

- [ ] **Step 2: Update `README.md`**

Find the section describing the plotting stages and apply the same change. If the README
contract test counts checks or commands, update the count and the test together — the
approved artefact wins.

- [ ] **Step 3: Run the full suite**

Run: `python3 -m pytest`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add README.md CLAUDE.md tests/
git commit -m "docs(story): document the source layer, the sigils, and the cut"
```

---

## Self-review

**Spec coverage:**

| spec § | task |
|---|---|
| §3 story.md format | 1 |
| §3.1 four sigils | 1 |
| §3.1.1 `## Questions` | 1, 4 |
| §4 stages | 7 |
| §5 the cut, three moves | 6, 8, 10 |
| §5.1 cut-plan fields | 2, 8 |
| §5.2 derivation table | 4 |
| §6 clue write-back | 6 |
| §7 re-cutting | 5, 6 |
| §8 refusals | 3, 6 |
| §9 testing / round-trip | 11 |
| §10 skeleton retirement | 9 |
| §11 book 01 untouched | 5 (no-stamp refusal), 12 |

**Known gaps, deliberately left to execution:**

- `_carried` treats a question closed in the same chapter that opens it as still carried
  for that chapter. That matches how `outline.md` reads today (chapter 02 carries
  `q-clear` in the same block that opens it), so it is intended, not an oversight.
- Task 9's grep list cannot be enumerated at planning time — the plan makes enumerating it
  Step 1 rather than guessing, which is the fix for the 2026-07-30 defect class.
- Task 11's fixture depends on the series folder being reachable; the step names the
  fallback.
