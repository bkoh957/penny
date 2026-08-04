# Chapter Direction and Authored Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the showrunner record structural direction and per-strand prose guardrails inside `story.md`, scoped by the same sigils the beats use, so notes survive re-cuts and reach the cutter and the drafter respectively.

**Architecture:** Two optional `##` blocks in `input/book-NN/story.md`. `## Chapter Direction` is read by the `chapter-cutter` agent and never emitted. `## Guardrails` is distributed by `story_cut.emit_outline` into each chapter's `### Guardrails` section, scoped by `@strand`/`#job` against **that chapter's own beats**. Both parse through the existing `TAG_RE`, so there is no second syntax. Distribution is arithmetic — no LLM in the emit path.

**Tech Stack:** Python 3, stdlib only. `scripts/penny_story.py` (dependency-free parser, per the repo's dependency-split rule — do **not** import PyYAML here), `scripts/story_cut.py`, pytest.

**Spec:** `docs/superpowers/specs/2026-08-04-chapter-direction-and-guardrails-design.md`

## Global Constraints

- **The deterministic layer never makes an LLM judgment.** Everything in `scripts/` fails loud with a named predicate and a nonzero exit.
- **No waivers at this level.** New findings are blocking; the fix is to edit the story, per spec §5 and the source-layer spec §8.
- **`penny_story.py` stays dependency-free.** It parses Penny's small YAML/markdown subset without PyYAML.
- **Engine stays genre- and location-agnostic.** No hardcoded strand names, job ids, series filenames, or genre names in `scripts/`.
- **Both blocks are optional.** Their absence must reproduce today's behaviour byte for byte (spec §6).
- **Only `@strand` and `#job` scope a directive.** `+q`, `-q`, `!clue` are refused by name.
- Run the full suite with `python3 -m pytest` (`pytest.ini` sets `pythonpath=.`).
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FC2eDvFhAViaev3Kv5gt5x
  ```

---

### Task 1: Parse the two blocks, and keep their bullets out of the beat list

**Files:**
- Modify: `scripts/penny_story.py:36-38` (heading constants), `:63-95` (`parse_story`), and append `parse_directives` after `parse_questions` (`:98-110`)
- Test: `tests/test_penny_story.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `parse_directives(text: str, heading: str) -> list[dict]` — one dict per bullet in the named `##` block, same shape as a beat: `{"text": str, "strands": list, "jobs": list, "opens": list, "closes": list, "clues": list, "line": int}`. `heading` is matched case-insensitively against the heading text (`"Chapter Direction"`, `"Guardrails"`). Continuation lines are folded in, exactly as `parse_story` does.
  - `_INERT_HEADINGS: set[str]` — lowercased heading names whose bullets are **not** beats.

The load-bearing risk in this task: `parse_story` currently skips only `## Questions`. Left alone, every directive bullet becomes a phantom beat — silently shifting every beat index in the cut plan and corrupting the outline. That is the first test.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_penny_story.py`:

```python
from scripts.penny_story import parse_story, parse_directives

STORY_WITH_BLOCKS = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie @simon +q-clear

## Chapter Direction

- These two belong in one chapter. #establish-protected-world

## Guardrails

- Don't flatten Marion into a cackling villain; her usefulness is her camouflage.
  @tara-marion
- Keep the community on the page in the endgame.

## Questions
- q-clear — how can Maggie clear herself?
"""


def test_directive_bullets_are_not_beats():
    beats = parse_story(STORY_WITH_BLOCKS)
    assert [b["text"] for b in beats] == [
        "Maggie chooses this life.",
        "The appointment was altered.",
    ]


def test_parse_directives_reads_guardrails_with_continuation_lines():
    notes = parse_directives(STORY_WITH_BLOCKS, "Guardrails")
    assert len(notes) == 2
    assert notes[0]["text"] == (
        "Don't flatten Marion into a cackling villain; "
        "her usefulness is her camouflage.")
    assert notes[0]["strands"] == ["tara-marion"]
    assert notes[1]["strands"] == [] and notes[1]["jobs"] == []


def test_parse_directives_reads_chapter_direction_and_is_case_insensitive():
    notes = parse_directives(STORY_WITH_BLOCKS, "chapter direction")
    assert [n["text"] for n in notes] == ["These two belong in one chapter."]
    assert notes[0]["jobs"] == ["establish-protected-world"]


def test_parse_directives_returns_empty_when_the_block_is_absent():
    assert parse_directives("- A beat. @maggie\n", "Guardrails") == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_story.py -k "directive" -v`

Expected: FAIL — `ImportError: cannot import name 'parse_directives'`.

- [ ] **Step 3: Implement the parser and the inert-heading fix**

In `scripts/penny_story.py`, replace the `QUESTIONS_HEADING_RE` constant block (currently at `:36-38`) with:

```python
QUESTIONS_HEADING_RE = re.compile(r"^##\s+Questions\s*$", re.IGNORECASE)
_HEADING_RE = re.compile(r"^##\s+")
_BULLET_RE = re.compile(r"^-\s+(?P<rest>.*)$")
_QUESTION_LINE_RE = re.compile(rf"^-\s+(?P<id>q-{SLUG})\s*[—-]\s*(?P<prose>.+?)\s*$")

# Headings whose bullets are NOT beats. A directive bullet read as a beat would
# shift every later beat index, so the cut plan's `Beats: 22-25` would silently
# claim the wrong beats (spec 2026-08-04 §3).
_INERT_HEADINGS = {"questions", "chapter direction", "guardrails"}


def _heading_name(raw):
    """Lowercased text of a `## ` heading, or None if the line is not one."""
    m = _HEADING_RE.match(raw)
    return raw[m.end():].strip().lower() if m else None
```

In `parse_story`, replace the `in_questions` local and its two uses:

```python
    beats, current, prose = [], None, []
    inert = False

    for i, raw in enumerate(lines):
        if i < offset:
            continue
        if _HEADING_RE.match(raw):
            if current is not None:
                beats.append(_finish(current, prose))
                current, prose = None, []
            inert = _heading_name(raw) in _INERT_HEADINGS
            continue
        if inert:
            continue
```

Append after `parse_questions`:

```python
def parse_directives(text: str, heading: str) -> list[dict]:
    """Scoped direction lines from one `##` block (spec 2026-08-04 §3).

    Same shape as a beat, harvested by the same TAG_RE, so a directive scopes
    with @strand and #job and needs no second syntax. Chapter numbers cannot
    scope a directive — they do not exist until after the cut.
    """
    want = heading.strip().lower()
    out, current, prose, in_block = [], None, [], False

    for i, raw in enumerate(text.splitlines()):
        if _HEADING_RE.match(raw):
            if current is not None:
                out.append(_finish(current, prose))
                current, prose = None, []
            in_block = _heading_name(raw) == want
            continue
        if not in_block:
            continue
        m = _BULLET_RE.match(raw)
        if m:
            if current is not None:
                out.append(_finish(current, prose))
            current = _blank_beat(i + 1)
            prose = [_harvest(current, m.group("rest"))]
        elif current is not None:
            if not raw.strip():
                out.append(_finish(current, prose))
                current, prose = None, []
            else:
                prose.append(_harvest(current, raw.strip()))

    if current is not None:
        out.append(_finish(current, prose))
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_story.py -v`

Expected: PASS, including the pre-existing tests in that file.

- [ ] **Step 5: Run the full suite to prove nothing regressed**

Run: `python3 -m pytest`

Expected: PASS. `parse_story`'s behaviour on a story with no new blocks is unchanged — `_INERT_HEADINGS` still contains `"questions"`.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_story.py tests/test_penny_story.py
git commit -m "feat(story): parse chapter-direction and guardrail blocks

Directive bullets are harvested by the same TAG_RE as beats, so a note
scopes with @strand and #job. parse_story now treats all three meaningful
headings as inert, so a directive bullet can never be read as a beat and
shift every later beat index.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FC2eDvFhAViaev3Kv5gt5x"
```

---

### Task 2: Refuse orphan and misplaced directives

**Files:**
- Modify: `scripts/story_cut.py:30-47` (imports/preamble of `check_story`) and the beat loop that ends around `:77`
- Test: `tests/test_story_cut.py`

**Interfaces:**
- Consumes: `parse_directives` from Task 1.
- Produces: two new finding ids in `check_story`'s `blocking` list — `orphan-direction` and `misplaced-schedule-tag`. Existing `unknown-strand`/`unknown-job` strings extended to name a directive line rather than a beat number. `check_story`'s signature is unchanged: `check_story(story_text: str, cut_plan_text: str, job_ids: list, clue_ids: list) -> dict`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_story_cut.py`:

```python
from scripts.story_cut import check_story

_JOBS = ["establish-protected-world", "act-iii-apparent-defeat"]
_CLUES = ["c-altered"]

_BASE = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The firing fails in front of the town.
  @maggie #act-iii-apparent-defeat +q-clear -q-clear

## Questions
- q-clear — how can Maggie clear herself?
"""


def _findings(extra):
    return check_story(_BASE + extra, "", _JOBS, _CLUES)["blocking"]


def test_orphan_direction_names_a_strand_no_beat_uses():
    out = _findings("\n## Guardrails\n- Never soften her. @susan\n")
    assert any(f.startswith("orphan-direction:") and "@susan" in f for f in out)


def test_a_job_the_genre_does_not_declare_is_unknown_job_in_a_directive():
    out = _findings("\n## Chapter Direction\n- Give it room. #restore-world\n")
    assert any("unknown-job:" in f for f in out)


def test_a_typoed_strand_in_a_directive_is_refused_by_name():
    out = _findings("\n## Chapter Direction\n- Watch her. @Maggie\n")
    assert any(f.startswith("unknown-strand:") for f in out)


def test_orphan_direction_fires_for_a_declared_job_no_beat_carries():
    out = check_story(
        _BASE + "\n## Guardrails\n- Give it room. #restore-world\n",
        "", _JOBS + ["restore-world"], _CLUES)["blocking"]
    assert any(f.startswith("orphan-direction:") and "#restore-world" in f
               for f in out)


def test_misplaced_schedule_tag_refuses_clue_and_question_tags():
    for tag in ("!c-altered", "+q-clear", "-q-clear"):
        out = _findings(f"\n## Guardrails\n- A note. {tag}\n")
        assert any(f.startswith("misplaced-schedule-tag:") for f in out), tag


def test_a_scoped_directive_matching_a_used_tag_is_clean():
    out = _findings("\n## Guardrails\n- Never soften her. @maggie\n"
                    "- Book-wide, untagged.\n")
    assert not [f for f in out if "direction" in f or "schedule-tag" in f]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut.py -k "direction or schedule_tag" -v`

Expected: FAIL — no `orphan-direction` or `misplaced-schedule-tag` finding is produced.

- [ ] **Step 3: Implement the checks**

In `scripts/story_cut.py`, add `parse_directives` to the `penny_story` import line. Then, immediately **after** the existing `for n, beat in enumerate(beats, 1):` loop closes (after the `unknown-question` block that ends around `:77`) and before the question-level checks, insert:

```python
    used_strands = {s for b in beats for s in b["strands"]}
    used_jobs = {j for b in beats for j in b["jobs"]}

    for heading in ("Chapter Direction", "Guardrails"):
        for d in parse_directives(story_text, heading):
            where = f"{heading} line {d['line']}"
            for slug in d["strands"]:
                if not SLUG_RE.match(slug):
                    blocking.append(
                        f"unknown-strand: {where} tags @{slug}, which breaks "
                        f"the slug contract ^[a-z0-9][a-z0-9-]*$")
                elif slug not in used_strands:
                    blocking.append(
                        f"orphan-direction: {where} is scoped to @{slug}, "
                        f"which no beat tags — the note would be rendered "
                        f"nowhere and read by no one")
            for slug in d["jobs"]:
                if slug not in known_jobs:
                    blocking.append(
                        f"unknown-job: {where} tags #{slug}, which the active "
                        f"genre's macro-structure does not declare")
                elif slug not in used_jobs:
                    blocking.append(
                        f"orphan-direction: {where} is scoped to #{slug}, "
                        f"which no beat carries — the note would be rendered "
                        f"nowhere and read by no one")
            if d["opens"] or d["closes"] or d["clues"]:
                blocking.append(
                    f"misplaced-schedule-tag: {where} carries a +q/-q/!clue "
                    f"tag, which schedules nothing here — direction scopes "
                    f"with @strand and #job only")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut.py -v`

Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut.py
git commit -m "feat(cut): refuse orphan and misplaced directives by name

orphan-direction is the converse of orphan-question: a note scoped to a
strand or job nothing uses is worse than an unwritten one, because the
author believes it is in force. misplaced-schedule-tag refuses +q/-q/!clue
in a directive block, where they would look like a plant and never plant.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FC2eDvFhAViaev3Kv5gt5x"
```

---

### Task 3: Distribute authored guardrails into each chapter

**Files:**
- Modify: `scripts/story_cut.py:213-214` (top of `emit_outline`) and `:292-293` (the Guardrails append)
- Test: `tests/test_story_cut_emit.py`

**Interfaces:**
- Consumes: `parse_directives` from Task 1.
- Produces: no signature change. `emit_outline(story_text, cut_plan_text, questions, ledger, *, reveal_chapter, guardrails, job_titles, solution) -> str` keeps its exact signature — the authored notes are parsed from `story_text`, which the function already receives. `guardrails` remains the book-wide config string.

The trap this task must avoid: `emit_outline` already maintains `seen_strands`, a running high-water mark used for Character Knowledge. Scoping guardrails with it would push a note about Marion into every chapter after her first appearance, including ones she is absent from. Guardrails attach to **`mine`** — this chapter's own beats. Step 1's second test pins exactly that.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_story_cut_emit.py`, reusing the module's existing `PLAN`, `LEDGER`, `JOB_TITLES`:

```python
STORY_NOTED = """- Maggie chooses this life.
  @maggie #establish-protected-world

- The appointment was altered.
  @maggie @simon #crime-and-first-contradiction +q-clear !c-altered

- Tom rules it out.
  @tom -q-clear

## Chapter Direction

- These two belong together. #establish-protected-world

## Guardrails

- Simon is evasive, never sinister. @simon
- The crime must land on an ordinary morning.
  #crime-and-first-contradiction
- Keep the town warm even here.

## Questions
- q-clear — how can Maggie clear herself?
"""


def _emit_noted():
    return emit_outline(STORY_NOTED, PLAN, parse_questions(STORY_NOTED), LEDGER,
                        reveal_chapter=2, guardrails="Do not name the culprit early.",
                        job_titles=JOB_TITLES, solution={})


def _guardrails(out, num):
    return parse_packet_sections(chapter_block(out, num))["Guardrails"]


def test_strand_scoped_guardrail_lands_only_where_that_strand_acts():
    out = _emit_noted()
    assert "Simon is evasive, never sinister." in _guardrails(out, 1)
    # Chapter 02 is Tom's beat alone. A running strand high-water mark would
    # leak Simon's note into it; this chapter's own beats must not.
    assert "Simon is evasive" not in _guardrails(out, 2)


def test_job_scoped_guardrail_lands_on_the_chapter_carrying_the_job():
    out = _emit_noted()
    assert "ordinary morning" in _guardrails(out, 1)
    assert "ordinary morning" not in _guardrails(out, 2)


def test_untagged_guardrail_lands_in_every_chapter():
    out = _emit_noted()
    for num in (1, 2):
        assert "Keep the town warm even here." in _guardrails(out, num)


def test_series_guardrail_and_reveal_line_still_follow_the_authored_ones():
    body = _guardrails(_emit_noted(), 2)
    assert "Do not name the culprit early." in body
    assert "Do not resolve the mystery before chapter 02." in body
    assert body.index("Keep the town warm") < body.index("Do not name the culprit")


def test_chapter_direction_never_reaches_the_outline():
    assert "belong together" not in _emit_noted()


def test_a_story_with_no_directive_blocks_keeps_the_old_guardrails_shape():
    # STORY carries no ## Guardrails block, so the section must be exactly the
    # two lines it held before this feature — nothing added, nothing reordered.
    assert _guardrails(_emit(), 1).strip().splitlines() == [
        "- Do not name the culprit early.",
        "- Do not resolve the mystery before chapter 02.",
    ]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut_emit.py -k "guardrail or direction_never" -v`

Expected: FAIL — authored notes are absent from the emitted Guardrails section.

- [ ] **Step 3: Implement the distribution**

In `emit_outline`, just after `chapters = parse_cut_plan(cut_plan_text)` (`:214`):

```python
    notes = parse_directives(story_text, "Guardrails")
```

Then replace the Guardrails append (`:292-293`):

```python
        # Scoped to THIS chapter's own beats, never to `seen_strands` — that
        # is a running high-water mark for Character Knowledge, and reusing it
        # would follow a character's note into chapters she is absent from.
        mine_strands = {s for b in mine for s in b["strands"]}
        mine_jobs = {j for b in mine for j in b["jobs"]}
        authored = [d["text"] for d in notes
                    if (not d["strands"] and not d["jobs"])
                    or (set(d["strands"]) & mine_strands)
                    or (set(d["jobs"]) & mine_jobs)]

        out.append("### Guardrails\n"
                   + "".join(f"- {a}\n" for a in authored)
                   + "- " + guardrails.strip()
                   + f"\n- Do not resolve the mystery before chapter {reveal_chapter:02d}.\n")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut_emit.py -v`

Expected: PASS, including `test_a_story_with_no_directive_blocks_emits_exactly_as_before`.

- [ ] **Step 5: Prove the null case on the real book**

The spec's §6 compatibility promise is about a real story, not a fixture. Book 01's derived `story.md` has no directive blocks yet, so its cut must be unchanged.

Run:

```bash
python3 -m pytest tests/test_story_cut_roundtrip.py -v
```

Expected: PASS, unchanged. If this fails, the emitter changed behaviour for a story with no blocks — fix that before continuing; do not adjust the round-trip test.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_emit.py
git commit -m "feat(cut): distribute authored guardrails to the chapters they scope

A guardrail tagged @tara-marion lands in the chapters whose OWN beats tag
her — not the running strand high-water mark, which would follow her into
chapters she is absent from. Character Knowledge accumulates; guardrails
do not. Untagged notes are book-wide. Chapter Direction is never emitted.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FC2eDvFhAViaev3Kv5gt5x"
```

---

### Task 4: Teach the cutter about direction, and update the docs

**Files:**
- Modify: `agents/chapter-cutter.md:13-14` (Inputs) and add a short section after "What you decide" (`:21-25`)
- Modify: `CLAUDE.md` — the source-layer paragraph listing the findings ("thirteen findings")
- Modify: `README.md` — the same finding list
- Test: `tests/test_plot_agents.py:38` (`test_chapter_cutter_contract`)

**Interfaces:**
- Consumes: the finding names from Task 2 (`orphan-direction`, `misplaced-schedule-tag`).
- Produces: nothing other tasks depend on. This is the last task.

- [ ] **Step 1: Write the failing test**

In `tests/test_plot_agents.py`, add to the `for phrase in (...)` tuple inside `test_chapter_cutter_contract`, after `"beat sheet",`:

```python
        # --- direction is an input it must actually read (spec 2026-08-04 §4.1) ---
        "## Chapter Direction",
```

And add a new test in the same file:

```python
def test_chapter_cutter_is_told_direction_is_advisory_not_a_gate():
    t = _text("chapter-cutter.md")
    assert "Chapter Direction" in t
    assert "propose" in t.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_plot_agents.py -k chapter_cutter -v`

Expected: FAIL — `"## Chapter Direction"` is not in the agent brief.

- [ ] **Step 3: Update the agent brief**

In `agents/chapter-cutter.md`, replace the Inputs line (`:13-14`) with:

```markdown
**Inputs:** `{ input/book-NN/story.md — including its ## Chapter Direction block,
the genre beat sheet, the genre macro-structure, series/whodunit/book-NN.yaml,
output/book-NN/mystery-solution.md }`.
```

Add after the "What you decide" section:

```markdown
## The showrunner's direction

`story.md` may carry a `## Chapter Direction` block — the showrunner's own structural
notes, written while reading the beats. Each line is scoped by the same sigils the beats
use: `@strand` means it applies wherever that strand acts, `#job` means it applies to the
chapter carrying that job, and an untagged line is book-wide.

Read it before you propose. It is the showrunner's taste about *where the cuts fall* —
"these two belong in one chapter", "don't let this run become four procedural chapters",
"give the raku failure its own chapter". Follow it unless it contradicts a refusal you
would earn (`beats-without-chapter`, `duplicate-beat`, `obligations.max_per_chapter`,
`starved-thread`), and say so plainly in your proposal when it does.

It is direction, not a gate: nothing checks your plan against it, and the showrunner still
edits and approves what you propose. The separate `## Guardrails` block is not yours — it
is carried through the cut to the drafter, and you neither read it nor act on it.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_plot_agents.py -v`

Expected: PASS.

- [ ] **Step 5: Update `CLAUDE.md` and `README.md`**

In `CLAUDE.md`, find the source-layer paragraph beginning "`story_cut.py` fails loud, by name, on thirteen findings". Change "thirteen" to "fifteen" and append `orphan-direction`, `misplaced-schedule-tag` to the comma-separated list, before "— no waivers at this level".

In the same paragraph's preceding sentences, after the description of the `## Questions` block, add:

```
Two further blocks are optional and scope with the same sigils: `## Chapter Direction`
(structural notes the `chapter-cutter` reads and the cut never emits) and `## Guardrails`
(prose notes carried into each chapter's Guardrails section, scoped to that chapter's own
beats — spec `docs/superpowers/specs/2026-08-04-chapter-direction-and-guardrails-design.md`).
```

In `README.md`, make the same numeric and list change wherever the finding count appears.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`

Expected: PASS. Note `tests/test_readme_check_count.py` (or the equivalently named contract pin) may assert the old count — if it fails, **re-pin it to the new number**: the approved artefact wins, per the repo's standing rule for previously-approved artefacts.

- [ ] **Step 7: Commit**

```bash
git add agents/chapter-cutter.md tests/test_plot_agents.py CLAUDE.md README.md
git commit -m "docs(cut): chapter-cutter reads Chapter Direction; 15 findings

The cutter is told direction is advisory and that Guardrails is not its
block. CLAUDE.md and README record the two new findings.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FC2eDvFhAViaev3Kv5gt5x"
```

---

## Verification

After Task 4, prove the feature on the real book rather than on fixtures — the lesson from the last phase was that task-scoped reviews all passed while two Criticals lived in the seams.

- [ ] Add a `## Guardrails` block to `~/myBooks/pelicanscrook-series/input/book-01/story.md` with one `@tara-marion` note and one untagged note.
- [ ] Run the checker (`check_story` with an empty cut-plan string) and confirm zero new findings.
- [ ] Introduce a deliberate `@nobody` note; confirm `orphan-direction` fires by name; remove it.
