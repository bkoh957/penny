# Series-Guardrail Heading Collision Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `config/series-guardrails.md`'s own `##` headings from structurally closing the containers it is carried into — the packet's guardrails section, and every chapter block of a cut outline.

**Architecture:** Two independent call sites of one defect, plus the test-fixture gap that hid it. `packet_assemble.py` already owns `_demote_headings` (line 117) and applies it to continuity extracts but not to the guardrails it appends — Task 1 applies it. `story_cut.py:652` pastes the whole file body into every chapter block — Task 2 replaces the body with a one-line reference, since the packet carries the body once. Task 3 makes the existing fixtures realistic, which is the actual root cause of the escape.

**Why this shipped:** `tests/test_story_cut_roundtrip.py:147` `test_the_emitted_outline_passes_tension_check_clean` **already asserts `result["wired"]`** — the exact property that is False in production. It passes because every fixture passes a *single-line* guardrails string (`guardrails="Stay in Maggie's POV."` at line 143, `guardrails="Do not name the culprit early."` at `tests/test_story_cut_emit.py:41`). A one-line string has no headings, so the collision cannot occur anywhere in the suite. Task 3 closes that gap and is the most important task in this plan.

**Tech Stack:** Python 3 stdlib only (the deterministic layer takes no PyYAML dependency). pytest; `pytest.ini` sets `pythonpath=.`.

**Spec:** `docs/superpowers/specs/2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md`

## Global Constraints

- **No new finding, and none removed.** `story_cut.py` stays at twenty-three named findings; `tension_check.py` stays at ten. This fix adds no `--waive` handle.
- **Deterministic layer is stdlib-only.** No PyYAML in `story_cut.py` / `packet_assemble.py` parsing paths; use `scripts/penny_meta.py` for frontmatter.
- **Run the full suite every task:** `python3 -m pytest` — baseline **1314 passed**. Report the new count each time.
- **Fixtures live in `tests/fixtures/`.** New deterministic behaviour is test-first.
- **Commit per task, on `main`. Do not push** — the operator pushes at phase end.
- **Do not edit `CLAUDE.md`'s test count.** The operator updates it once at the end.

**Shared literal — use this exact text wherever a plan step says REALISTIC_GUARDRAILS.** It reproduces the live series' shape (an H1 title, then `##` rule headings):

```python
REALISTIC_GUARDRAILS = (
    "# Standing Series Guardrails — Pelican's Crook\n\n"
    "## C — Warmth beats are never scheduled as clues\n\n"
    "Warmth is oxygen, not obligation.\n\n"
    "## B — The map states ends, not sentences\n\n"
    "A map says what a scene achieves.\n\n"
    "## Standing\n\n"
    "These apply to every book in the series.\n"
)
```

---

### Task 1: The packet's guardrails section carries its own body

`scripts/packet_assemble.py:318-322` reads `config/series-guardrails.md` raw and splices it at line ~358 under `## Standing Series Guardrails`. The file's `##` headings close that section immediately, so the section is empty and the body leaks out as sibling top-level sections.

**Files:**
- Modify: `scripts/packet_assemble.py:318-322`
- Test: `tests/test_packet_assemble.py`

**Interfaces:**
- Consumes: `_demote_headings(text: str, offset: int = 4, max_level: int = 6) -> str`, already defined at `scripts/packet_assemble.py:117`; the `series_tree` pytest fixture at `tests/test_packet_assemble.py:23`; the module-level `_SIBLING_HEADING_RE` used by `_continuity_extracts_section` at line 206.
- Produces: no signature change. The emitted `## Standing Series Guardrails` section contains the full guardrail body, every embedded heading demoted to `####` or deeper.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_packet_assemble.py`, directly below `_continuity_extracts_section` (line 206). Model the section isolator on that helper — do not write a second, weaker one.

```python
def _guardrails_section(text: str) -> str:
    """The packet's `## Standing Series Guardrails` section, isolated the way a
    markdown-structure-aware reader would: heading line to the next level-1/2
    sibling. A demoted `###`+ heading does NOT end it."""
    heading_line = next(l for l in text.splitlines()
                        if l.startswith("## Standing Series Guardrails"))
    start = text.index(heading_line) + len(heading_line)
    rest = text[start:]
    m = _SIBLING_HEADING_RE.search(rest)
    return rest[:m.start()] if m else rest


def test_guardrails_section_survives_embedded_headings(series_tree):
    """A guardrails file with its own `##` headings must not close the packet's
    `## Standing Series Guardrails` section (spec 2026-09-09). On unfixed code
    the section is empty and the body leaks out as sibling `##` sections."""
    (series_tree / "config").mkdir(parents=True, exist_ok=True)
    (series_tree / "config/series-guardrails.md").write_text(
        REALISTIC_GUARDRAILS, encoding="utf-8")

    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    section = _guardrails_section(text)

    assert "Warmth is oxygen, not obligation." in section
    assert "A map says what a scene achieves." in section
    assert "These apply to every book in the series." in section
    # The carried file must introduce no sibling top-level section.
    assert "\n## C — Warmth beats" not in text
    assert "\n## B — The map states" not in text
    assert "\n## Standing\n" not in text
```

Add `REALISTIC_GUARDRAILS` (the Global Constraints literal) as a module-level constant near the top of the file. If `series_tree` already writes a `config/series-guardrails.md`, overwrite it in the test rather than adding a second fixture.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_packet_assemble.py::test_guardrails_section_survives_embedded_headings -v`

Expected: FAIL on `"Warmth is oxygen, not obligation." in section` — the section is empty.

- [ ] **Step 3: Write minimal implementation**

In `scripts/packet_assemble.py`, at the guardrails read (line 318-322):

```python
    guardrails_path = config_path("series-guardrails.md", root)
    if guardrails_path.is_file():
        # The carried file's own headings must not close the packet's
        # `## Standing Series Guardrails` section — the rule the continuity
        # extracts already follow (spec 2026-08-27, extended to this site by
        # spec 2026-09-09).
        guardrails_section = _demote_headings(
            guardrails_path.read_text(encoding="utf-8").strip())
    else:
        guardrails_section = "- None — this series has no config/series-guardrails.md."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_packet_assemble.py -v`
Expected: PASS, including the pre-existing `test_missing_guardrails_file_is_named_note` (line 114).

Run: `python3 -m pytest`
Expected: **1315 passed**.

- [ ] **Step 5: Commit**

```bash
git add scripts/packet_assemble.py tests/test_packet_assemble.py
git commit -m "fix(packet): demote carried guardrail headings so the section keeps its body

The packet read config/series-guardrails.md raw and spliced it under
## Standing Series Guardrails. The file's own ## headings closed that
section immediately, leaving it 10 words long and leaking the body out as
sibling top-level sections. _demote_headings was already defined in this
file and applied to continuity extracts — it just was not applied here.

Spec: docs/superpowers/specs/2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: The cut emits a guardrail reference, not the body

`scripts/story_cut.py:652` appends the entire guardrails file as one bullet inside every chapter's `### Guardrails` section. The first line is bulleted, but every subsequent `##` sits at column 0 and truncates the chapter block — orphaning that chapter's `### Chapter Structure` and `### Track Movement` footer. The body does not belong here: the packet carries it once (Task 1).

**Files:**
- Modify: `scripts/story_cut.py:646-654` (the `### Guardrails` emission in `emit_outline`)
- Test: `tests/test_story_cut_emit.py`

**Interfaces:**
- Consumes: `emit_outline(story_text, cut_plan_text, questions, ledger, *, reveal_chapter: int, guardrails: str, job_titles: dict, solution: dict) -> str` — **signature unchanged**. `guardrails` is now used only to decide whether the series has guardrails at all.
- Produces: each chapter's `### Guardrails` section is the authored bullets, then one reference bullet (only when `guardrails.strip()` is truthy), then the derived reveal line.

- [ ] **Step 1: Write the failing test**

`tests/test_story_cut_emit.py:39` currently defines `def _emit():` with no parameters, hardcoding `guardrails="Do not name the culprit early."`. Give it a keyword with that same default so every existing caller is unchanged:

```python
def _emit(guardrails="Do not name the culprit early."):
    return emit_outline(STORY, PLAN, parse_questions(STORY), LEDGER,
                        reveal_chapter=2, guardrails=guardrails,
                        job_titles=JOB_TITLES, solution={})
```

Add `REALISTIC_GUARDRAILS` (the Global Constraints literal) as a module-level constant, then these three tests:

```python
def test_guardrail_body_is_not_pasted_into_chapter_blocks():
    """The cut emits a reference, never the file's body — its own `##`
    headings would truncate every chapter block (spec 2026-09-09)."""
    out = _emit(guardrails=REALISTIC_GUARDRAILS)

    assert "Warmth is oxygen, not obligation." not in out
    assert "A map says what a scene achieves." not in out
    assert "config/series-guardrails.md" in out


def test_no_stray_top_level_heading_in_a_cut_outline():
    """A cut outline's column-0 `##` headings are exactly its chapters plus
    `## Solution` — anything else truncates a chapter block."""
    out = _emit(guardrails=REALISTIC_GUARDRAILS)

    stray = [ln for ln in out.splitlines()
             if ln.startswith("## ")
             and not ln.startswith("## Chapter ")
             and ln.strip() != "## Solution"]
    assert stray == [], f"stray top-level headings truncate chapter blocks: {stray}"


def test_no_guardrail_reference_when_the_series_has_none():
    """An empty guardrails string emits no reference bullet and no empty one."""
    out = _emit(guardrails="")

    assert "config/series-guardrails.md" not in out
    assert "\n- \n" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut_emit.py -k "guardrail or stray" -v`

Expected: FAIL. `test_guardrail_body_is_not_pasted_into_chapter_blocks` fails on `"Warmth is oxygen, not obligation." not in out`; `test_no_stray_top_level_heading_in_a_cut_outline` fails listing `## C — Warmth beats are never scheduled as clues`. Note `test_no_guardrail_reference_when_the_series_has_none` may already pass — that is fine, it is a guard against Task 2's own regression.

- [ ] **Step 3: Write minimal implementation**

In `scripts/story_cut.py`, replace `+ "- " + guardrails.strip()` in the `### Guardrails` emission:

```python
        # The standing series guardrails are a global, constant file. Pasting
        # the body here put its own `##` headings at column 0, truncating every
        # chapter block and orphaning the wiring footer (spec 2026-09-09). The
        # packet carries the body once, as `## Standing Series Guardrails`.
        guardrail_ref = (
            "- Standing series guardrails apply in full — "
            "`config/series-guardrails.md`, carried into each packet as "
            "`## Standing Series Guardrails`.\n"
            if guardrails.strip() else "")
        out.append("### Guardrails\n"
                   + "".join(f"- {a}\n" for a in authored)
                   + guardrail_ref
                   + f"- {reveal_line}\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut_emit.py -v`
Expected: PASS.

Run: `python3 -m pytest`
Expected: **1318 passed**. If `test_guardrails_and_purpose_are_derived` (line 95) fails, it is asserting the old paste behaviour — read it, confirm that is exactly what it asserts, and update it to expect the reference bullet. Do not weaken any assertion about the authored bullets or the reveal line.

- [ ] **Step 5: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_emit.py
git commit -m "fix(cut): emit a guardrail reference, not the file body

story_cut pasted the whole of config/series-guardrails.md into every
chapter's ### Guardrails section. Its ## headings landed at column 0, so
every chapter block truncated there and each chapter's Chapter Structure /
Track Movement footer was orphaned into a pseudo-block parse_wired_chapters
discards — the outline parsed as unwired, all ten tension_check findings
went dark, and the packet carried no wiring at all.

The body is global and constant; the packet carries it once.

Spec: docs/superpowers/specs/2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Make the fixtures realistic — close the gap that hid this

The most important task. `test_the_emitted_outline_passes_tension_check_clean` already asserts the property that is False in production; it passes only because its fixture guardrail is one line long. Give the roundtrip fixture a realistic guardrails file and that existing test becomes the regression.

**Files:**
- Modify: `tests/test_story_cut_roundtrip.py:140-145` (`_tagged_outline`)
- Test: `tests/test_story_cut_roundtrip.py`

**Interfaces:**
- Consumes: `_tagged_outline()` at line 140; `check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None, whodunit_path=None) -> dict` returning keys `wired`, `blocking`, `notes`, `metrics`; `parse_wired_chapters(text) -> list[dict]` and `has_wiring(chapters) -> bool` from `scripts.penny_wiring`.
- Produces: nothing consumed downstream.

- [ ] **Step 1: Change the fixture and add the block-level assertion**

Add `REALISTIC_GUARDRAILS` (the Global Constraints literal) as a module-level constant, then change `_tagged_outline` to use it as the default:

```python
def _tagged_outline(guardrails=REALISTIC_GUARDRAILS):
    from scripts.story_cut import emit_outline as emit
    return emit(TAGGED_STORY, TAGGED_PLAN, TAGGED_QUESTIONS, TAGGED_LEDGER,
                reveal_chapter=5, guardrails=guardrails,
                job_titles={}, solution=TAGGED_SOLUTION)
```

Then add, beside the existing tension test:

```python
def test_every_chapter_block_keeps_its_wiring_footer():
    """A `##` heading inside a carried file truncates the chapter block and
    orphans its Chapter Structure / Track Movement footer (spec 2026-09-09).
    The fixture's guardrails carry `##` headings, exactly as a real series' do."""
    from scripts.penny_wiring import parse_wired_chapters, has_wiring

    chapters = parse_wired_chapters(_tagged_outline())

    assert chapters, "no chapters parsed"
    assert has_wiring(chapters), "the cut outline parsed as unwired"
    for ch in chapters:
        assert ch["because"] is not None or ch["opens"], (
            f"chapter {ch['num']} lost its wiring footer")
```

`parse_wired_chapters` chapter dicts have **no `raw` or `text` key** (verified at
`scripts/penny_wiring.py:167-175`). The wiring lives in the parsed fields — `because`,
`opens`, `closes`, `hook_q`, `tracks` — which is exactly what `has_wiring` keys on
(`penny_wiring.py:227-229`: `any(c["because"] is not None or c["opens"] ...)`). Assert on
those fields, as above. Do not reach for a raw-text key.

- [ ] **Step 2: Run tests to verify the failure is real**

Run: `git stash push scripts/story_cut.py && python3 -m pytest tests/test_story_cut_roundtrip.py -v; git stash pop`

Expected while stashed: **both** `test_the_emitted_outline_passes_tension_check_clean` (on `assert result["wired"]`) and `test_every_chapter_block_keeps_its_wiring_footer` FAIL. This is the proof that the existing test was blind, not absent.

If `git stash push` on a single path is awkward in this state, achieve the same by temporarily reverting the Task 2 hunk by hand — the point is to see the two tests fail against pre-fix code.

- [ ] **Step 3: No implementation needed**

These are regressions over Task 2. If they fail with Task 2 applied, the bug is in Task 2 — fix it there. Never weaken the test.

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest`
Expected: **1319 passed**.

- [ ] **Step 5: Commit**

```bash
git add tests/test_story_cut_roundtrip.py
git commit -m "test(cut): give the roundtrip fixture a realistic guardrails file

test_the_emitted_outline_passes_tension_check_clean already asserted
result['wired'] — the exact property that was False for a whole live
series. It passed because every fixture used a one-line guardrails string,
which has no headings, so the collision could not occur anywhere in the
suite. The fixture now carries ## headings as a real series' file does, and
that existing test becomes the regression.

Spec: docs/superpowers/specs/2026-09-09-guardrail-headings-truncate-chapter-blocks-fix.md

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Out of scope for this plan

Do not do these; they are the operator's calls or belong to the companion spec.

- **Do not re-cut or otherwise touch the live series** (`~/myBooks/pelicanscrook-series`). It is a separate repo; its outline is stamped, and re-cutting rewrites `plant_chapter:` in the whodunit ledger and invalidates the mystery lock. The operator sequences that.
- **Do not push.** Commit only.
- **Do not update `CLAUDE.md`'s test count** (1314 → final). The operator does that once.
- **Do not implement anything from `2026-09-09-check-economics-design.md`** — the `--no-continuity` render, the consumer split, the one-hop rule. Separate plan.
- **Do not add a finding, a waiver handle, or a runbook edit.**
