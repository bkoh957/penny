# Chapter Setting and Frames Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record where each chapter happens and how it opens and closes in `cut-plan.md`, so those decisions are made at the cut rather than by the drafter.

**Architecture:** Three new fields are authored in `input/book-NN/cut-plan.md` (`Setting:`, `Opening:`, `Closing (<kind>):`), parsed by `penny_story.parse_cut_plan`, validated by five new blocking findings in `story_cut.check_story`, and emitted as three new `### ` sections by `story_cut.emit_outline`. A tenth, waivable `tension_check` check reads the emitted `### Closing` sections to catch a run of identical chapter endings. Everything downstream (packets, maps, drafts) receives the new sections for free because the packet inlines the whole chapter block.

**Tech Stack:** Python 3 stdlib only in `scripts/` (`penny_meta` for frontmatter, never PyYAML) except `tension_check.py`, which already uses PyYAML to read the genre beat sheet. Tests are pytest; `pytest.ini` sets `pythonpath=.`.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-08-12-chapter-setting-and-frames-design.md`. Section references below (§3, §5.1…) are to that file.
- **The engine is genre- and location-agnostic.** No setting name, place name, or series filename may appear in `scripts/`. The closing-run threshold comes from the active genre's beat sheet, resolved via `penny_genre.py beat-sheet`, never a hardcoded path.
- **The three closing kinds are exactly:** `cliffhanger`, `irony`, `promise of action`.
- **`story_cut.py` findings are unwaivable.** They go on the `blocking` channel. Do not add a waiver flag at this level (source-layer spec §8).
- **`tension_check.py` findings are waivable** via the existing `--waive check-id:"reason"` machinery, and a check that cannot run appends to `notes`, never a bare `return`.
- **Adoption is all-or-nothing per cut plan** (§5.1): if no chapter carries any of the three fields, none of the five findings fire; if any chapter carries any of them, every chapter must carry all three.
- **Test-first.** Every task writes the failing test, runs it to see it fail, then implements.
- Full suite: `python3 -m pytest` (978 passing before this work).

---

### Task 1: Parse the three fields from the cut plan

**Files:**
- Modify: `scripts/penny_story.py:184-224`
- Test: `tests/test_penny_story.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `parse_cut_plan(text) -> list[dict]`, where each chapter dict gains three keys beyond today's `num`/`title`/`beats`/`summary`/`compress`/`tracks`:
  - `settings: list[dict]` — each `{"beats": list[int], "text": str}`, in authored order. `[]` when the field is absent.
  - `opening: str` — `""` when absent.
  - `closing: dict | None` — `{"kind": str, "text": str}`, or `None` when absent. `kind` is the raw lowercased string from the key, **not** validated here (Task 2 validates it).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_penny_story.py`:

```python
from scripts.penny_story import parse_cut_plan

PLAN = """\
## Chapter 07 — The Tin in the Tide
- **Beats:** 22-25
- **Summary:** She finds the tin.
- **Compress:** the walk back
- **Setting:**
  - 22-23 — the pottery studio, late afternoon
  - 24-25 — the harbour road, dusk, rain coming in off the water
- **Opening:** The kiln door still warm and the studio empty behind her.
- **Closing (promise of action):** She pockets the tin and turns for the harbour.
- **M:** the tin surfaces
"""


def test_settings_parse_in_order_with_expanded_ranges():
    ch = parse_cut_plan(PLAN)[0]
    assert ch["settings"] == [
        {"beats": [22, 23], "text": "the pottery studio, late afternoon"},
        {"beats": [24, 25],
         "text": "the harbour road, dusk, rain coming in off the water"},
    ]


def test_opening_and_closing_parse_with_kind_in_the_key():
    ch = parse_cut_plan(PLAN)[0]
    assert ch["opening"] == "The kiln door still warm and the studio empty behind her."
    assert ch["closing"] == {"kind": "promise of action",
                             "text": "She pockets the tin and turns for the harbour."}


def test_setting_range_accepts_single_beats_and_lists():
    plan = ("## Chapter 01 — X\n"
            "- **Beats:** 1-4\n"
            "- **Setting:**\n"
            "  - 1 — the kitchen, dawn\n"
            "  - 2,4 — the yard, noon\n")
    assert [s["beats"] for s in parse_cut_plan(plan)[0]["settings"]] == [[1], [2, 4]]


def test_closing_kind_is_lowercased_but_not_validated_here():
    plan = ("## Chapter 01 — X\n"
            "- **Beats:** 1\n"
            "- **Closing (Cliffhanger):** the door opens\n")
    assert parse_cut_plan(plan)[0]["closing"]["kind"] == "cliffhanger"


def test_legacy_plan_without_the_fields_gets_empty_defaults():
    plan = ("## Chapter 01 — X\n"
            "- **Beats:** 1-3\n"
            "- **Summary:** s\n"
            "- **Compress:** c\n"
            "- **M:** m\n")
    ch = parse_cut_plan(plan)[0]
    assert ch["settings"] == [] and ch["opening"] == "" and ch["closing"] is None
    assert ch["tracks"] == {"M": "m"}


def test_a_track_row_is_never_mistaken_for_a_new_field():
    ch = parse_cut_plan(PLAN)[0]
    assert ch["tracks"] == {"M": "the tin surfaces"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_story.py -k "setting or opening or closing or legacy_plan or track_row" -v`
Expected: FAIL with `KeyError: 'settings'` on most, and the legacy test failing the same way.

- [ ] **Step 3: Implement the parser changes**

In `scripts/penny_story.py`, replace the field regexes and `parse_cut_plan` body. `_CUT_FIELD_RE` gains `Setting|Opening`; `Closing` needs its own regex because the kind lives in the key; setting sub-items need a third. Note `_CUT_TRACK_RE` requires exactly one capital letter before the colon, so none of these collide with a track row.

```python
_CUT_FIELD_RE = re.compile(
    r"^\s*-\s+\*\*(?P<key>Beats|Summary|Compress|Setting|Opening):\*\*\s*(?P<val>.*)$")
_CUT_CLOSING_RE = re.compile(
    r"^\s*-\s+\*\*Closing\s*\((?P<kind>[^)]*)\):\*\*\s*(?P<val>.*)$")
# A setting sub-item: `  - 22-23 — the pottery studio, late afternoon`. The dash
# separating range from prose is an em dash; a hyphen would be ambiguous against
# the range's own `22-23`.
_CUT_SETTING_ITEM_RE = re.compile(r"^\s+-\s+(?P<spec>[\d,\s-]+?)\s+—\s+(?P<val>.*)$")
```

Then in `parse_cut_plan`, initialise the three keys and handle the new lines. The setting sub-item test must come **before** `_CUT_TRACK_RE`, and `in_setting` must be cleared by any other recognised field so a stray indented bullet later in the block is not swallowed:

```python
def parse_cut_plan(text: str) -> list[dict]:
    """The showrunner-approved grouping (spec §5.1).

    `settings`, `opening` and `closing` are the cut-level record of where a
    chapter happens and how it lands (spec 2026-08-12). They default empty, so a
    plan written before that design parses exactly as it always did — adoption is
    all-or-nothing and `story_cut.check_story` owns that rule, not this parser.
    """
    chapters, current, in_setting = [], None, False
    for raw in text.splitlines():
        m = _CUT_CHAPTER_RE.match(raw)
        if m:
            current = {"num": int(m.group("num")), "title": m.group("title"),
                       "beats": [], "summary": "", "compress": "", "tracks": {},
                       "settings": [], "opening": "", "closing": None}
            chapters.append(current)
            in_setting = False
            continue
        if current is None:
            continue
        if in_setting:
            sm = _CUT_SETTING_ITEM_RE.match(raw)
            if sm:
                current["settings"].append(
                    {"beats": _expand_beats(sm.group("spec")),
                     "text": sm.group("val").strip()})
                continue
        cm = _CUT_CLOSING_RE.match(raw)
        if cm:
            in_setting = False
            current["closing"] = {"kind": cm.group("kind").strip().lower(),
                                  "text": cm.group("val").strip()}
            continue
        fm = _CUT_FIELD_RE.match(raw)
        if fm:
            key, val = fm.group("key"), fm.group("val").strip()
            in_setting = key == "Setting"
            if key == "Beats":
                current["beats"] = _expand_beats(val)
            elif key != "Setting":
                current[key.lower()] = val
            continue
        tm = _CUT_TRACK_RE.match(raw)
        if tm:
            in_setting = False
            current["tracks"][tm.group("letter")] = tm.group("val").strip()
    return chapters
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_story.py -v`
Expected: PASS, including every pre-existing test in the file.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: 978 + 6 = 984 passing, 0 failing. If anything else fails, a consumer was relying on the old dict shape — fix it before committing.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_story.py tests/test_penny_story.py
git commit -m "feat(cut-plan): parse Setting, Opening and Closing"
```

---

### Task 2: The five blocking findings

**Files:**
- Modify: `scripts/story_cut.py` — inside `check_story`, after the beat-numbering block that ends at line 105
- Test: `tests/test_story_cut.py`

**Interfaces:**
- Consumes: `parse_cut_plan`'s `settings`/`opening`/`closing` keys from Task 1.
- Produces: nothing new in the public API. `check_story(story_text, cut_plan_text, job_ids, clue_ids) -> {"blocking": [...], "notes": [...]}` keeps its signature; five new strings can appear on `blocking`.

Finding message prefixes, exactly (§5.1): `beat-without-setting:`, `overlapping-setting:`, `setting-outside-chapter:`, `missing-chapter-frame:`, `unknown-closing-kind:`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_story_cut.py`. Match the file's existing helper style for building a story; if it has a fixture builder, use it — otherwise this minimal story works because these findings never read beats' tags:

```python
from scripts.story_cut import check_story

STORY = """\
# Story

- [1] Maggie opens the shop.
- [2] The tin turns up.
- [3] She walks to the harbour.
- [4] The light goes out.
"""


def _plan(body):
    return "## Chapter 01 — X\n- **Beats:** 1-4\n" + body


FRAME = ("- **Opening:** The kiln door still warm.\n"
         "- **Closing (cliffhanger):** The light goes out.\n")


def _blocking(plan):
    return check_story(STORY, plan, [], [])["blocking"]


def test_clean_plan_produces_none_of_the_new_findings():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n" + FRAME)
    assert not [b for b in _blocking(plan) if b.split(":")[0] in {
        "beat-without-setting", "overlapping-setting", "setting-outside-chapter",
        "missing-chapter-frame", "unknown-closing-kind"}]


def test_beat_without_setting_names_the_uncovered_beat():
    plan = _plan("- **Setting:**\n  - 1-3 — the shop, morning\n" + FRAME)
    assert any(b.startswith("beat-without-setting:") and "4" in b
               for b in _blocking(plan))


def test_overlapping_setting_fires_when_two_ranges_claim_one_beat():
    plan = _plan("- **Setting:**\n  - 1-3 — the shop, morning\n"
                 "  - 3-4 — the harbour, dusk\n" + FRAME)
    assert any(b.startswith("overlapping-setting:") and "3" in b
               for b in _blocking(plan))


def test_setting_outside_chapter_fires_on_a_beat_this_chapter_does_not_hold():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "  - 9 — the harbour, dusk\n" + FRAME)
    assert any(b.startswith("setting-outside-chapter:") and "9" in b
               for b in _blocking(plan))


def test_missing_chapter_frame_fires_once_per_missing_field():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n")
    found = [b for b in _blocking(plan) if b.startswith("missing-chapter-frame:")]
    assert len(found) == 2
    assert any("Opening" in b for b in found) and any("Closing" in b for b in found)


def test_unknown_closing_kind_names_the_three_valid_kinds():
    plan = _plan("- **Setting:**\n  - 1-4 — the shop, morning\n"
                 "- **Opening:** The kiln door.\n"
                 "- **Closing (twist):** The light goes out.\n")
    hits = [b for b in _blocking(plan) if b.startswith("unknown-closing-kind:")]
    assert hits and "promise of action" in hits[0]


def test_a_plan_carrying_none_of_the_fields_is_pre_design_and_silent():
    plan = _plan("- **Summary:** s\n- **Compress:** c\n")
    assert not [b for b in _blocking(plan) if b.split(":")[0] in {
        "beat-without-setting", "overlapping-setting", "setting-outside-chapter",
        "missing-chapter-frame", "unknown-closing-kind"}]


def test_adoption_is_all_or_nothing_across_the_whole_plan():
    plan = ("## Chapter 01 — X\n- **Beats:** 1-2\n"
            "- **Setting:**\n  - 1-2 — the shop, morning\n"
            "- **Opening:** The kiln door.\n"
            "- **Closing (irony):** She laughs.\n"
            "## Chapter 02 — Y\n- **Beats:** 3-4\n"
            "- **Summary:** s\n")
    found = [b for b in _blocking(plan) if b.startswith("missing-chapter-frame:")]
    assert len(found) == 2 and all("ch 02" in b for b in found)
    assert any(b.startswith("beat-without-setting:") and "ch 02" in b
               for b in _blocking(plan))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut.py -k "setting or frame or closing_kind or adoption or pre_design" -v`
Expected: FAIL — the assertions find no matching findings.

- [ ] **Step 3: Implement the checks**

In `scripts/story_cut.py`, add this module constant near the other regexes at the top:

```python
# The three kinds a chapter may end on (spec 2026-08-12 §3). Engine-level rather
# than genre-level: these name shapes of ending, not cozy conventions.
CLOSING_KINDS = ("cliffhanger", "irony", "promise of action")
```

Then insert this block inside `check_story`, immediately after the beat-numbering loop (after line 105, before the `for n, beat in enumerate(beats, 1):` loop at line 107):

```python
    # Setting and chapter frames are cut-level, all-or-nothing per plan (spec
    # 2026-08-12 §5.1). Checking each chapter independently would make a
    # half-adopted book the quiet default: the chapters that were filled in are
    # governed and the rest silently return the ending to the drafter.
    adopted = any(ch["settings"] or ch["opening"] or ch["closing"]
                  for ch in chapters)
    if adopted:
        for ch in chapters:
            held = set(ch["beats"])
            seen: set = set()
            for s in ch["settings"]:
                for n in s["beats"]:
                    if n not in held:
                        blocking.append(
                            f"setting-outside-chapter: ch {ch['num']:02d} has a "
                            f"setting covering beat {n}, which this chapter does "
                            f"not hold — a chapter boundary moved and the setting "
                            f"ranges did not move with it; repair cut-plan.md")
                    elif n in seen:
                        blocking.append(
                            f"overlapping-setting: ch {ch['num']:02d} has two "
                            f"settings covering beat {n}, so where it happens is "
                            f"ambiguous")
                    seen.add(n)
            for n in sorted(held - seen):
                blocking.append(
                    f"beat-without-setting: ch {ch['num']:02d} beat {n} is covered "
                    f"by no setting — every beat must say where it happens, or the "
                    f"drafter picks the room")
            if not ch["opening"]:
                blocking.append(
                    f"missing-chapter-frame: ch {ch['num']:02d} has no Opening — "
                    f"other chapters in this plan carry one, and adoption is "
                    f"all-or-nothing")
            if not ch["closing"]:
                blocking.append(
                    f"missing-chapter-frame: ch {ch['num']:02d} has no Closing — "
                    f"a missing ending hands the last line back to the drafter")
            elif ch["closing"]["kind"] not in CLOSING_KINDS:
                blocking.append(
                    f"unknown-closing-kind: ch {ch['num']:02d} ends on "
                    f"'{ch['closing']['kind']}', which is not one of "
                    f"{', '.join(CLOSING_KINDS)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut.py -v`
Expected: PASS, including every pre-existing test.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all passing. `tests/test_story_cut_cli.py` and `tests/test_story_cut_roundtrip.py` use fixture plans that carry none of the new fields, so they stay silent under the all-or-nothing rule — if one fails, its fixture has partially adopted the fields and needs completing, not exempting.

- [ ] **Step 6: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut.py
git commit -m "feat(story-cut): five findings for chapter setting and frames"
```

---

### Task 3: Emit the three sections into the outline

**Files:**
- Modify: `scripts/story_cut.py:371-392` — inside `emit_outline`'s per-chapter loop
- Test: `tests/test_story_cut_emit.py`

**Interfaces:**
- Consumes: Task 1's parsed fields; Task 2's `CLOSING_KINDS` is not needed here.
- Produces: three `### ` sections in `outline.md`, named exactly `### Setting`, `### Opening`, `### Closing`. Task 4 parses `### Closing`; Task 5 admits all three to the reader's copy by these exact names.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_story_cut_emit.py`, following that file's existing pattern for calling `emit_outline`:

```python
def test_setting_is_emitted_after_chapter_summary_with_chapter_local_beats():
    # A chapter holding book-level beats 3-4 renders them as Beats 1-2, matching
    # how ### Required Beats already lists this chapter's beats, not the book's.
    out = emit_outline(STORY, PLAN_WITH_SETTING, QUESTIONS, ...)
    assert "### Setting\n- Beats 1-2 — the shop, morning\n" in out
    assert out.index("### Chapter Summary") < out.index("### Setting")
    assert out.index("### Setting") < out.index("### Chapter Purpose")


def test_opening_and_closing_follow_reader_facing_shape():
    out = emit_outline(STORY, PLAN_WITH_SETTING, QUESTIONS, ...)
    assert out.index("### Reader-Facing Shape") < out.index("### Opening")
    assert out.index("### Opening") < out.index("### Closing")
    assert out.index("### Closing") < out.index("### Required Beats")


def test_closing_renders_its_kind_as_a_prose_lead_in():
    out = emit_outline(STORY, PLAN_WITH_SETTING, QUESTIONS, ...)
    assert "### Closing\nPromise of action — she pockets the tin" in out


def test_a_plan_without_the_fields_emits_no_empty_sections():
    out = emit_outline(STORY, LEGACY_PLAN, QUESTIONS, ...)
    assert "### Setting" not in out
    assert "### Opening" not in out and "### Closing" not in out
```

Build `PLAN_WITH_SETTING` and `LEGACY_PLAN` in the same shape the file's existing plan fixtures use, and fill the `...` with whatever positional arguments `emit_outline` already takes in that file's other tests.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut_emit.py -k "setting or opening or closing or empty_sections" -v`
Expected: FAIL — the sections are absent from the output.

- [ ] **Step 3: Implement the emission**

In `emit_outline`, after the `### Chapter Summary` append at line 372, add:

```python
        if ch["settings"]:
            # Chapter-local beat numbers, matching ### Required Beats, which
            # already lists this chapter's beats rather than the book's. Book
            # positions here would send the drafter to the wrong line.
            first = min(ch["beats"]) if ch["beats"] else 1
            def _local(ns):
                loc = sorted(n - first + 1 for n in ns)
                return (f"{loc[0]}-{loc[-1]}"
                        if len(loc) > 1 and loc == list(range(loc[0], loc[-1] + 1))
                        else ",".join(str(n) for n in loc))
            out.append("### Setting\n" + "\n".join(
                f"- Beats {_local(s['beats'])} — {s['text']}"
                for s in ch["settings"]) + "\n")
```

Then after the `### Reader-Facing Shape` append at line 387-389, and before `### Required Beats` at line 391, add:

```python
        if ch["opening"]:
            out.append("### Opening\n" + ch["opening"] + "\n")
        if ch["closing"]:
            # The kind becomes a prose lead-in rather than a parenthetical key:
            # the emitted block is read by agents and by the reader's copy, never
            # parsed back into the cut plan.
            kind = ch["closing"]["kind"]
            out.append(f"### Closing\n{kind[0].upper() + kind[1:]} — "
                       f"{ch['closing']['text']}\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut_emit.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all passing. Watch `tests/test_packet_assemble.py` — it inlines the whole chapter block, so a fixture outline that gains sections may need its expected text updated.

- [ ] **Step 6: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_emit.py
git commit -m "feat(story-cut): emit Setting, Opening and Closing sections"
```

---

### Task 4: `monotonous-closings` in tension_check

**Files:**
- Modify: `scripts/tension_check.py` — new `_closings_check`, called from `check_tension`
- Modify: `genres/cozy-mystery/beat-sheet.yaml`
- Test: `tests/test_tension_check.py`

**Interfaces:**
- Consumes: Task 3's `### Closing` section text, read via `ch["sections"].get("Closing")` — `parse_wired_chapters` already stores every packet section under `sections` (`penny_wiring.py:155`), so no new parser field is needed.
- Produces: `_closings_check(chapters, blocking, notes, *, max_run=None) -> None`, appending to the caller's lists in place, matching `_overload_check`'s signature style.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_tension_check.py`:

```python
from scripts.tension_check import _closings_check


def _ch(num, kind):
    return {"num": num,
            "sections": {"Closing": f"{kind} — something happens"} if kind else {}}


def test_a_run_longer_than_the_cap_fires():
    chapters = [_ch(n, "Cliffhanger") for n in range(1, 5)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert any(b.startswith("monotonous-closings:") and "ch 04" in b
               for b in blocking)


def test_a_run_exactly_at_the_cap_does_not_fire():
    chapters = [_ch(n, "Cliffhanger") for n in range(1, 4)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []


def test_a_varied_book_does_not_fire():
    chapters = [_ch(1, "Cliffhanger"), _ch(2, "Irony"),
                _ch(3, "Cliffhanger"), _ch(4, "Promise of action")]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == []


def test_absent_genre_key_is_a_named_note_never_a_silent_pass():
    chapters = [_ch(n, "Cliffhanger") for n in range(1, 6)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=None)
    assert blocking == []
    assert any(n.startswith("monotonous-closings —") for n in notes)


def test_an_outline_with_no_closings_is_skipped_entirely():
    chapters = [_ch(n, None) for n in range(1, 6)]
    blocking, notes = [], []
    _closings_check(chapters, blocking, notes, max_run=3)
    assert blocking == [] and notes == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_tension_check.py -k closings -v`
Expected: FAIL with `ImportError: cannot import name '_closings_check'`.

- [ ] **Step 3: Implement the check**

Add to `scripts/tension_check.py`, beside `_overload_check`:

```python
def _closings_check(chapters, blocking, notes, *, max_run=None):
    """The tenth check: a run of identical chapter endings (spec 2026-08-12 §5.2).

    Five cliffhangers running is a fact about the BOOK, not a defect in any one
    chapter — which is why it lives here and not among story_cut's per-chapter
    findings. The threshold is a genre number, so an absent key is a named note
    on the certificate, never a silent pass.

    An outline carrying no ### Closing anywhere is the legacy shape and is
    skipped entirely — it has no note to give, exactly as an outline with no
    Required Beats is skipped by the overload check.
    """
    kinds = [(ch["num"], (ch.get("sections") or {}).get("Closing", "")
              .split("—")[0].strip().lower())
             for ch in chapters]
    kinds = [(num, k) for num, k in kinds if k]
    if not kinds:
        return
    if max_run is None:
        notes.append(
            "monotonous-closings — the check could not run: the genre's beat sheet "
            "declares no closings.max_same_kind_run")
        return
    run_kind, run_len = None, 0
    for num, kind in kinds:
        run_len = run_len + 1 if kind == run_kind else 1
        run_kind = kind
        if run_len > int(max_run):
            blocking.append(
                f"monotonous-closings: ch {num:02d} is the {run_len}th chapter in a "
                f"row ending on {run_kind}, against the genre's run cap of {max_run} "
                f"— a book whose endings stop varying reads as machinery no matter "
                f"how good each one is")
```

Then in `check_tension`, read the threshold and call it. Add this beside the existing beat-sheet read, and call `_closings_check` in **both** return paths — the wired path and the `if not has_wiring(chapters)` early return — so an unwired outline still gets the check:

```python
    max_run = None
    if beat_sheet_path is not None and Path(beat_sheet_path).is_file():
        closings = _load_yaml(beat_sheet_path).get("closings")
        if isinstance(closings, dict) and closings.get("max_same_kind_run") is not None:
            max_run = int(closings["max_same_kind_run"])
    _closings_check(chapters, over["blocking"], over["notes"], max_run=max_run)
```

Place this immediately after the `over = check_overload(...)` call, so both return paths carry the findings.

- [ ] **Step 4: Declare the genre threshold**

In `genres/cozy-mystery/beat-sheet.yaml`, add beside `obligations:`:

```yaml
# How many chapters may end on the same kind in a row before the book stops
# feeling varied. A cozy runs short chapters with a hook on nearly every one, so
# the risk is not too few endings but too many of one shape.
closings:
  max_same_kind_run: 3
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_tension_check.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all passing.

- [ ] **Step 7: Commit**

```bash
git add scripts/tension_check.py genres/cozy-mystery/beat-sheet.yaml tests/test_tension_check.py
git commit -m "feat(tension-check): monotonous-closings, tenth check"
```

---

### Task 5: Admit the three sections to the reader's copy

**Files:**
- Modify: `scripts/plot_stage.py` — `_KEEP_SUBSECTIONS`
- Test: `tests/test_plot_stage.py`

**Interfaces:**
- Consumes: Task 3's exact section names.
- Produces: nothing new. `readers_copy_text` keeps its signature.

**Note:** the working tree already converts `_KEEP_SUBSECTIONS` from a denylist to an allowlist. Build on that; do not revert it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_plot_stage.py`:

```python
def test_the_reader_sees_setting_opening_and_closing():
    text = ("## Chapter 01 — X\n"
            "### Chapter Summary\nShe opens the shop.\n"
            "### Setting\n- Beats 1-2 — the shop, morning\n"
            "### Opening\nThe kiln door still warm.\n"
            "### Closing\nCliffhanger — the light goes out.\n"
            "### Guardrails\n- The culprit is Susan.\n")
    out = readers_copy_text(text)
    assert "the shop, morning" in out
    assert "The kiln door still warm." in out
    assert "the light goes out." in out
    assert "Susan" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_plot_stage.py -k reader_sees_setting -v`
Expected: FAIL — setting/opening/closing are dropped, because an allowlist drops anything it does not name.

- [ ] **Step 3: Admit the three sections**

In `scripts/plot_stage.py`, extend the tuple and its comment:

```python
# `setting`, `opening` and `closing` are admitted deliberately (spec 2026-08-12
# §6.3): setting is what a reader experiences, and the closing line is what
# put-down risk is actually made of, so hiding it would waste the read-back.
# Truncation at reveal_chapter still applies, so a late closing cannot leak the
# solution.
_KEEP_SUBSECTIONS = ("chapter summary", "reader-facing shape", "chapter structure",
                     "setting", "opening", "closing")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_plot_stage.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/plot_stage.py tests/test_plot_stage.py
git commit -m "feat(plot-stage): admit setting and frames to the reader's copy"
```

---

### Task 6: The craft doc and the agents that write and read the fields

**Files:**
- Create: `config/story-craft/writing-chapter-frames.md`
- Modify: `agents/chapter-cutter.md` — Inputs (line 13) and "Output format — exactly this" (line 47)
- Modify: `agents/map-maker.md`, `agents/drafter.md`
- Modify: `commands/plot-book.md` — the cut stage, around line 220
- Test: `tests/test_story_craft_doc.py`

**Interfaces:**
- Consumes: the field format from Task 1 and the section names from Task 3.
- Produces: no code. `tests/test_story_craft_doc.py` already asserts things about `config/story-craft/`; extend its pattern rather than inventing a new test file.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_story_craft_doc.py`, following the file's existing style for locating the craft directory:

```python
def test_chapter_frames_doc_ships_and_names_the_three_kinds():
    p = Path(__file__).resolve().parents[1] / "config/story-craft/writing-chapter-frames.md"
    assert p.is_file()
    body = p.read_text(encoding="utf-8").lower()
    for kind in ("cliffhanger", "irony", "promise of action"):
        assert kind in body


def test_chapter_cutter_declares_the_three_fields_and_the_craft_doc():
    body = (Path(__file__).resolve().parents[1] / "agents/chapter-cutter.md").read_text(
        encoding="utf-8")
    assert "**Setting:**" in body and "**Opening:**" in body
    assert "Closing (" in body
    assert "writing-chapter-frames.md" in body
    assert "setting-pack" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_story_craft_doc.py -k "chapter_frames or chapter_cutter" -v`
Expected: FAIL — the file does not exist.

- [ ] **Step 3: Write the craft doc**

Create `config/story-craft/writing-chapter-frames.md`. It is prose for an agent, in the same voice as `writing-beats.md` — read that file first and match it. It must cover:

- **What an opening does.** The first sentence earns the next one. Concrete image or action in progress over scene-setting; the room can arrive in the second sentence. It is not a recap of the previous chapter.
- **The three closing kinds, distinguished by what they leave the reader holding.** *Cliffhanger* — an unresolved event: something happens and the outcome is withheld. *Irony* — a gap the reader can see and the character cannot: the reader now knows why this is worse than it looks. *Promise of action* — the character commits, and the next chapter's shape is now inevitable.
- **Why a run of the same kind goes dead.** Three cliffhangers running teaches the reader that the withheld outcome always turns out survivable, so the fourth costs nothing. Variety is not decoration; it is what keeps each kind expensive.
- **That the closing belongs to the chapter's last beat**, not to a new event invented at the boundary. If the last beat cannot carry the ending, the cut is in the wrong place.

- [ ] **Step 4: Update `agents/chapter-cutter.md`**

- Add to **Inputs** (line 13): the series setting pack, resolved through the config overlay, and the union of `config/story-craft/` listed with `penny_paths.py resolve-dir story-craft` — matching how `agents/story-author.md:13` declares it.
- Add to the **Output format** block (line 47), in the order from spec §3, so the fields sit between `Compress:` and the track rows:

```markdown
- **Setting:**
  - <beat range> — <place, time[, condition]>
  - <beat range> — <place, time[, condition]>
- **Opening:** <the chapter's first image or action — one line>
- **Closing (cliffhanger|irony|promise of action):** <how the chapter lands — one line>
```

- Add a short section stating: every beat in the chapter must be covered by exactly one setting range, ranges use the same positional beat numbers as `Beats:`, and place names must match the setting pack's names.
- Add: read `writing-chapter-frames.md` before proposing any Opening or Closing, and vary the closing kinds across the book.

- [ ] **Step 5: Update `agents/map-maker.md` and `agents/drafter.md`**

- `map-maker`: `### Setting` is the strongest available signal for where scenes break, because a location change is usually a scene boundary; the chapter's `### Opening` belongs to the first scene and `### Closing` to the last.
- `drafter`: `### Opening` and `### Closing` are instruction, not context — the chapter opens and lands as they say.

- [ ] **Step 6: Update `commands/plot-book.md`**

In the cut stage (around line 220), state that the approved plan carries the three fields, and name the drift hazard: **moving a chapter boundary moves beats between chapters and leaves the setting ranges behind**, which reports `setting-outside-chapter` and `beat-without-setting` together, and both are repaired in `cut-plan.md`, not `story.md`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_story_craft_doc.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add config/story-craft/writing-chapter-frames.md agents/ commands/plot-book.md tests/test_story_craft_doc.py
git commit -m "feat(cutter): propose setting and chapter frames"
```

---

### Task 7: Flip the documented counts

**Files:**
- Modify: `CLAUDE.md` — the source-layer findings paragraph (line 165) and the paragraph added by commit `c28fe22`
- Modify: `README.md` — cut-plan format

**Interfaces:** none. Documentation only, and it must run last, because until Tasks 2 and 4 land the counts would be false.

- [ ] **Step 1: Update the findings list**

In `CLAUDE.md`, change "fails loud, by name, on sixteen findings" to "twenty-one findings" and append the five names to that list: `beat-without-setting`, `overlapping-setting`, `setting-outside-chapter`, `missing-chapter-frame`, `unknown-closing-kind`.

Also update the sentence further down that reads "the sixteen findings stay sixteen, and an advisory that could block would just be a seventeenth with a softer name" — it becomes twenty-one and twenty-second. The point it makes about the advisory channel is unchanged.

- [ ] **Step 2: Update the tension_check list**

In `CLAUDE.md`, the `preflight` section lists nine named checks. Add `monotonous-closings` as the tenth and change "nine named checks" to "ten named checks".

- [ ] **Step 3: Rewrite the approved-not-built paragraph**

The paragraph added by `c28fe22` says the design is approved and not yet built, and holds the counts. Rewrite it in the present tense as shipped behaviour, dropping the "those counts stay at sixteen and nine until the code lands" sentence.

- [ ] **Step 4: Update README**

Add `Setting:`, `Opening:` and `Closing (<kind>):` to the cut-plan format description, using spec §3's example verbatim.

- [ ] **Step 5: Verify the docs match the code**

Run: `python3 -m pytest -q` and confirm all tests pass, then grep the finding names out of the source and check every one appears in CLAUDE.md:

```bash
grep -o "^\s*f\"[a-z-]*:" scripts/story_cut.py | grep -o "[a-z-]*:" | sort -u
```

Expected: every name printed here appears in CLAUDE.md's list.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: setting and chapter frames ship; 21 findings, 10 checks"
```

---

## Self-Review

**Spec coverage.** §3 format → Task 1. §4 emitted block → Task 3. §5.1 five findings and all-or-nothing → Task 2. §5.2 `monotonous-closings` and the genre key → Task 4. §6.1 generation → Task 6. §6.2 modification → Task 6 Step 6. §6.3 consumption → Tasks 1, 3, 5, 6 (packet_assemble and book_status need no change, per spec). §6.4 documentation → Task 7. §8 testing → distributed across every task's tests. §7 out-of-scope items appear in no task, correctly.

**Type consistency.** `settings` is `list[dict]` with keys `beats`/`text` in Tasks 1, 2 and 3. `closing` is `dict | None` with keys `kind`/`text` in Tasks 1, 2 and 3. `_closings_check` reads `ch["sections"]["Closing"]` — the *emitted* section from Task 3, not the cut-plan dict, because tension_check runs over `outline.md`. `CLOSING_KINDS` is defined once in `story_cut.py` (Task 2) and referenced nowhere else; Task 4 matches on the rendered lead-in text instead, which is why an unknown kind must block in Task 2 or the run check silently measures a nonexistent kind.

**Known gap the executor must handle:** Task 3's test fixtures are written as `PLAN_WITH_SETTING`, `LEGACY_PLAN` and `...` positional args, because `emit_outline`'s exact signature and this file's fixture style must be read from `tests/test_story_cut_emit.py` at execution time. That is the one place the plan does not carry literal code, and it is deliberate — inventing a signature here would be worse than reading the real one.
