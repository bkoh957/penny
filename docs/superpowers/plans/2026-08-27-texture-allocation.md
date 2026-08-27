# Texture Allocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give texture an allocation layer — an authored reservoir of concrete
sensory material cut into the setting pack, and a per-chapter `Texture:` spend
authored once across the whole book in `cut-plan.md`, flowing down the existing
cut → outline → packet → map → drafter pipe.

**Architecture:** Two additive halves, no new pipe. (1) `background_cut.py`
learns a second verbatim part, `## Reservoir`, and cuts it to
`config/setting-pack/reservoir.md` — a directory four agents already read
directly. (2) `cut-plan.md` gains a nested `- **Texture:**` field that
`penny_story.parse_cut_plan` parses, `story_cut.emit_outline` renders as a
`### Texture` section, and `packet_assemble` carries into the packet for free
(it embeds the whole chapter block verbatim). A new `/allocate-texture`
command dispatches a new `texture-allocator` agent, saves the approved
allocation to `input/book-NN/plot/texture.md`, and splices it into
`cut-plan.md` with a new deterministic script.

**Tech Stack:** Python 3 stdlib only (`re`, `hashlib`, `pathlib`); pytest;
markdown runbooks and agent definitions. PyYAML is **not** used by anything in
this plan — every file touched here is flat authored text, which belongs to
`penny_meta`'s family (CLAUDE.md, "Dependency-split rule").

**Spec:** `docs/superpowers/specs/2026-08-27-texture-allocation-design.md`

## Global Constraints

- **Scope is §4.1 + §4.2 only. §4.3 (the punch-up pass) is a separate plan and
  MUST NOT be written or built here** (spec §4, "Scope for planning"). Do not
  create `/punch-up`, a punch-up agent, or a word-overrun allowance.
- **Texture is a resource allocation, not a discharge requirement** (spec §4.2).
  `map_check.py` gains **no new finding**. There is no `unscheduled-texture`.
  `inspector-fairplay` is untouched. A chapter using three of four allocated
  images is correct, not short. The whole layer is advisory and can never block
  a finalize.
- **`story_cut.py`'s blocking finding roster stays at exactly 23 named
  findings.** Texture reuses the existing `wiring-shaped-directive` name; it
  introduces no 24th. `tests/test_readme_check_count.py::STORY_CUT_FINDING_IDS`
  and `tests/test_claude_md_check_count.py` pin this — if either goes red you
  have added a finding and must not.
- **`background_cut.py` stays at eight blocking findings and two advisories.**
  The reservoir is optional: an absent `## Reservoir` section writes no file and
  reports nothing.
- **The reservoir is derived, never hand-edited** (spec §6, "Reservoir
  staleness"). Do not create a hand-maintained second copy under `config/`.
- **The reservoir does NOT go into the packet** (decision, this plan). Four
  agents — `drafter`, `chapter-cutter`, `outline-expander`,
  `developmental-editor` — already read the whole `config/setting-pack/`
  directory directly, so a file cut into that directory reaches them with no
  plumbing; embedding a global constant in a per-chapter artifact is the failure
  CLAUDE.md names for the voice and genre packs.
- **The `Texture:` field is nested sub-bullets**, like `Setting:`, not a single
  line like `Compress:` (decision, this plan).
- Runbooks reference scripts as `${CLAUDE_PLUGIN_ROOT}/scripts/...`, never a
  relative path — they run from a series folder, not this repo.
- New deterministic behaviour is test-first. Run the full suite
  (`python3 -m pytest`) before each commit; it must stay green.
- Commit after every task.

---

## File Structure

**Created:**
- `scripts/texture_apply.py` — parse `input/book-NN/plot/texture.md`, splice
  `- **Texture:**` blocks into `input/book-NN/cut-plan.md`. Idempotent.
- `agents/texture-allocator.md` — whole-book allocation proposer.
- `commands/allocate-texture.md` — the runbook.
- `tests/test_texture_apply.py` — the splice script's tests.
- `tests/test_texture_allocation_docs.py` — agent/command/doc contract pins.

**Modified:**
- `scripts/background_cut.py` — `## Reservoir` as a second verbatim part;
  `config/setting-pack/reservoir.md` as a second derived target.
- `scripts/lmstudio_draft_chapter.py:79-98` — exclude `reservoir.md` from the
  pack concatenation that gets truncated at 2,500 chars.
- `scripts/penny_story.py:208-250` (`parse_cut_plan`) — parse the nested
  `Texture:` field.
- `scripts/story_cut.py` — emit `### Texture`; extend the cut-plan
  wiring-forgery guard over texture items.
- `scripts/penny_map.py` — parse a scene's `Texture:` field.
- `agents/map-maker.md`, `agents/drafter.md`, `agents/chapter-cutter.md`
- `commands/plot-book.md` (step 8), `commands/map-chapter.md` (step 3)
- `CLAUDE.md`, `README.md`
- `tests/test_background_cut.py`, `tests/test_penny_story.py`,
  `tests/test_story_cut_emit.py`, `tests/test_story_cut.py`,
  `tests/test_plot_stage.py`, `tests/test_penny_map.py`,
  `tests/test_map_check.py`, `tests/test_packet_assemble.py`,
  `tests/test_lmstudio_draft_chapter.py`

**Untouched on purpose:** `scripts/map_check.py` (spec §6: "resisting the urge
to gate this is the point"), `scripts/packet_assemble.py` (it embeds the whole
chapter block verbatim, so `### Texture` arrives with no code change — Task 4
pins that with a test), `scripts/tension_check.py`, `scripts/preflight.py`,
`scripts/readiness_check.py`, `agents/inspector-*.md`.

---

## Task 1: The reservoir — cut `## Reservoir` into the setting pack

**Files:**
- Modify: `scripts/background_cut.py`
- Test: `tests/test_background_cut.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `background_cut.RESERVOIR_REL == "config/setting-pack/reservoir.md"`;
  `background_cut.VERBATIM_PARTS == ("Stance", "Reservoir")`;
  `parse_background(text)` gains a `"reservoir"` key (str, `""` when absent)
  alongside its existing `"stance"`.

**Context an implementer needs.** `background_cut.py` cuts one authored file,
`input/series/background-history.md`, into derived files. Today it splits on
`## Part` headings: `Stance` is carried verbatim into
`config/setting-pack/setting.md`, and `Town`/`Characters`/`Relationships`/
`Secrets` have each `### Entry` cut into its own file under
`series/continuity/background/`. The reservoir is a **catalogue**, not a set of
entries — its `###` group headings (by location, weather, season, time of day,
craft process, social ritual) are how it is read, and it must not become 40
derived files. So it joins `Stance` as a *verbatim part*.

One deliberate behaviour change falls out: today a `###` heading inside
`## Stance` is silently dropped from the emitted stance (the level-3 branch
`continue`s before appending). After this task both verbatim parts carry their
headings. That is strictly better — the heading was authored content — and
Step 1's last test pins it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_background_cut.py`:

```python
# --- Task 1: the reservoir is a second verbatim part (spec 2026-08-27 §4.1) ---

RESERVOIR_SOURCE = SOURCE + """
## Reservoir

### The bakery
- 6am: proving-room warmth, yeast, the scorched edge of the second tray.
- 3pm: cooling racks ticking, flour gone to paste in the sink corner.

### Wind on the shed roof
- 10 knots: a rattle you stop hearing by the second cup.
- 25 knots: the ridge capping lifts and drops, a slow handclap.
"""


def test_reservoir_is_carried_verbatim_including_its_group_headings():
    parsed = bc.parse_background(RESERVOIR_SOURCE)
    assert "### The bakery" in parsed["reservoir"]
    assert "### Wind on the shed roof" in parsed["reservoir"]
    assert "6am: proving-room warmth" in parsed["reservoir"]


def test_reservoir_groups_are_not_cut_into_background_entries():
    parsed = bc.parse_background(RESERVOIR_SOURCE)
    slugs = {e["slug"] for e in parsed["entries"]}
    assert "the-bakery" not in slugs
    assert "wind-on-the-shed-roof" not in slugs


def test_reservoir_is_not_an_unknown_section_and_blocks_nothing():
    result = bc.check_background(bc.parse_background(RESERVOIR_SOURCE))
    assert result["blocking"] == []


def test_reservoir_is_written_to_the_setting_pack_with_a_stamp():
    parsed = bc.parse_background(RESERVOIR_SOURCE)
    built = bc.build_entries(parsed, "deadbeef")
    hit = next(b for b in built if b["rel"] == bc.RESERVOIR_REL)
    assert bc.RESERVOIR_REL == "config/setting-pack/reservoir.md"
    meta = penny_meta.parse_canon_meta(hit["text"])
    assert meta["id"] == "reservoir"
    assert meta["kind"] == "reservoir"
    assert meta["built_from_background"] == "deadbeef"
    assert meta["cut_output_sha256"] == bc.body_sha(parsed["reservoir"])


def test_a_source_with_no_reservoir_writes_no_reservoir_file():
    parsed = bc.parse_background(SOURCE)
    assert parsed["reservoir"] == ""
    built = bc.build_entries(parsed, "deadbeef")
    assert all(b["rel"] != bc.RESERVOIR_REL for b in built)
    assert bc.check_background(parsed)["blocking"] == []


def test_reservoir_md_is_part_of_the_setting_pack_contract():
    # Otherwise every cut would advise `stale-setting-pack` about the file the
    # cut itself just wrote.
    assert bc.stale_setting_pack_notes(["config/setting-pack/reservoir.md"]) == []


def test_a_deep_heading_inside_the_reservoir_is_content_not_a_depth_error():
    # The entry-depth rule exists because entries become filenames. Nothing in
    # a verbatim part does, so its headings are free-form.
    text = SOURCE + "\n## Reservoir\n\n### The bakery\n#### 6am\n- yeast.\n"
    parsed = bc.parse_background(text)
    assert bc.check_background(parsed)["blocking"] == []
    assert "#### 6am" in parsed["reservoir"]


def test_a_heading_inside_the_stance_is_now_carried_rather_than_dropped():
    text = "## Stance\n### Weather\n- Southern Ocean, not tropical.\n"
    parsed = bc.parse_background(text)
    assert "### Weather" in parsed["stance"]
    assert "Southern Ocean, not tropical." in parsed["stance"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_background_cut.py -k "reservoir or stance_is_now" -v`
Expected: FAIL — `AttributeError: module 'scripts.background_cut' has no
attribute 'RESERVOIR_REL'` and `KeyError: 'reservoir'`.

- [ ] **Step 3: Add the verbatim-part machinery**

In `scripts/background_cut.py`, replace the `PART_HEADINGS` line and add
`VERBATIM_PARTS` beneath it:

```python
PART_HEADINGS = ("Stance", "Reservoir", "Town", "Characters", "Relationships",
                 "Secrets")
#: Parts carried into a derived file VERBATIM rather than cut into one entry per
#: `###` heading. Their headings are content, not entry names: the stance is
#: authored prose the setting pack loads on every chapter (spec 2026-08-13
#: §3.1), and the reservoir is a grouped catalogue whose group headings — by
#: location, weather, season, time of day, craft process, social ritual — are
#: how it is read (spec 2026-08-27 §4.1). Cutting the reservoir into entries
#: would turn one catalogue into forty continuity files that nothing links to.
VERBATIM_PARTS = ("Stance", "Reservoir")
```

- [ ] **Step 4: Teach `parse_background` about verbatim parts**

Replace the body of `parse_background` from its local declarations through the
`return`. The changed lines are the `verbatim` dict (replacing `stance_lines`),
the `elif part in verbatim` branch, the new `if part in verbatim` branch ahead
of the depth check, the simplified `if part is None`, and the two keys in the
`return`:

```python
def parse_background(text: str) -> dict:
    """Split the source on its heading contract (spec §3)."""
    verbatim: dict = {name: [] for name in VERBATIM_PARTS}
    entries: list[dict] = []
    unknown_parts: list[str] = []
    deep_headings: list[str] = []

    part: "str | None" = None
    current: "dict | None" = None
    buf: list[str] = []

    def flush():
        nonlocal current, buf
        if current is not None:
            current["body"] = "\n".join(buf).strip()
            entries.append(current)
        current, buf = None, []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if not m:
            if current is not None:
                buf.append(line)
            elif part in verbatim:
                verbatim[part].append(line)
            continue

        level, title = len(m.group("hashes")), m.group("title")
        if level == 2:
            flush()
            part = title if title in PART_HEADINGS else None
            if title not in PART_HEADINGS:
                unknown_parts.append(title)
            continue
        if part in verbatim:
            # A `###`/`####` inside a verbatim part is a group heading in a
            # catalogue, not an entry that becomes a file — so it is carried,
            # and the entry-depth rule (which exists because entries become
            # filenames) does not apply to it.
            verbatim[part].append(line)
            continue
        if level >= 4:
            deep_headings.append(title)
            continue
        # level == 3
        flush()
        if part is None:
            continue
        kind = KIND_BY_PART[part]
        s = relationship_slug(title) if kind == "relationship" else slug(title)
        current = {"part": part, "kind": kind, "title": title, "slug": s}

    flush()
    return {
        "stance": "\n".join(verbatim["Stance"]).strip(),
        "reservoir": "\n".join(verbatim["Reservoir"]).strip(),
        "entries": entries,
        "unknown_parts": unknown_parts,
        "deep_headings": deep_headings,
    }
```

Note `KIND_BY_PART` is unchanged and correctly has no `Reservoir` key — the
`part in verbatim` branch above returns before it is indexed.

- [ ] **Step 5: Emit the reservoir file**

In `scripts/background_cut.py`, add the constant next to `SETTING_PACK_REL`:

```python
RESERVOIR_REL = f"{SETTING_PACK_DIR}/reservoir.md"
```

Add `"reservoir.md"` to `SETTING_PACK_CONTRACT_FILES`:

```python
SETTING_PACK_CONTRACT_FILES = {
    "setting.md", "reservoir.md", "lexicon.md", "ai-tics-detection.md",
    "lmstudio-digest.md",
}
```

In `build_entries`, immediately before `return out`, after the existing stance
append:

```python
    reservoir = parsed.get("reservoir", "")
    if reservoir:
        out.append({
            "rel": RESERVOIR_REL,
            "text": stamp(reservoir, {
                "id": "reservoir",
                "kind": "reservoir",
                "built_from_background": source_sha,
                "cut_output_sha256": body_sha(reservoir),
            }),
        })
    return out
```

An absent or empty `## Reservoir` writes nothing and reports nothing: the
reservoir is optional, and a series that has not authored one must keep cutting
exactly as before.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_background_cut.py -v`
Expected: PASS, all tests in the file.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS (count grows by the 8 new tests).

- [ ] **Step 8: Commit**

```bash
git add scripts/background_cut.py tests/test_background_cut.py
git commit -m "background_cut: cut ## Reservoir into config/setting-pack/reservoir.md"
```

---

## Task 2: Keep the reservoir out of the LM Studio setting-pack budget

**Files:**
- Modify: `scripts/lmstudio_draft_chapter.py:79-98`
- Test: `tests/test_lmstudio_draft_chapter.py`

**Interfaces:**
- Consumes: `background_cut.RESERVOIR_REL`'s filename, `reservoir.md` (Task 1).
- Produces: `lmstudio_draft_chapter._PACK_SKIP` — filenames the pack
  concatenation never includes.

**Context an implementer needs.** `_read_config_pack_for_lmstudio("setting-pack",
root)` concatenates every `*.md` in the resolved pack dir, and the caller
truncates the result at **2,500 characters** (`limits["setting_pack"]`).
`reservoir.md` sorts before `setting.md`, and at 150–250 catalogue items it would
consume the entire budget — silently truncating away the authored stance, which
is the one thing the setting pack exists to carry. The reservoir reaches the
drafter through the chapter's own texture allocation instead.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_lmstudio_draft_chapter.py`:

```python
# --- Task 2: the reservoir never eats the 2,500-char setting-pack budget ---

def test_reservoir_is_excluded_from_the_lmstudio_setting_pack(tmp_path):
    from scripts import lmstudio_draft_chapter as ld

    (tmp_path / ".penny").mkdir()
    pack = tmp_path / "config" / "setting-pack"
    pack.mkdir(parents=True)
    (pack / "setting.md").write_text("Southern Ocean, not tropical.\n",
                                     encoding="utf-8")
    (pack / "reservoir.md").write_text("- 6am: proving-room warmth.\n" * 400,
                                       encoding="utf-8")

    text = ld._read_config_pack_for_lmstudio("setting-pack", tmp_path)
    assert "Southern Ocean, not tropical." in text
    assert "proving-room warmth" not in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_lmstudio_draft_chapter.py -k reservoir -v`
Expected: FAIL — `assert "proving-room warmth" not in text`.

- [ ] **Step 3: Add the skip list**

In `scripts/lmstudio_draft_chapter.py`, directly above
`def _read_config_pack_for_lmstudio`:

```python
#: Files under a resolved pack dir that this digest path never concatenates.
#: `lmstudio-digest.md` is the digest itself. `reservoir.md` is the texture
#: reservoir (spec 2026-08-27 §4.1): 150–250 catalogue items that sort before
#: `setting.md` and would consume the whole 2,500-char setting_pack budget,
#: truncating away the authored stance the pack exists to carry. The reservoir
#: reaches the drafter through the chapter's own texture allocation, which is
#: already in the packet.
_PACK_SKIP = {"lmstudio-digest.md", "reservoir.md"}
```

Then in the loop replace:

```python
            if p.name == "lmstudio-digest.md":
                continue
```

with:

```python
            if p.name in _PACK_SKIP:
                continue
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_lmstudio_draft_chapter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/lmstudio_draft_chapter.py tests/test_lmstudio_draft_chapter.py
git commit -m "lmstudio: keep reservoir.md out of the truncated setting pack"
```

---

## Task 3: Parse the nested `Texture:` field in `cut-plan.md`

**Files:**
- Modify: `scripts/penny_story.py:208-250` (`parse_cut_plan` and its regexes)
- Test: `tests/test_penny_story.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: every chapter dict from `penny_story.parse_cut_plan(text)` gains
  `"texture": list[str]` — the allocated items in authoring order, defaulting
  to `[]`.

**Context an implementer needs.** `parse_cut_plan` walks the approved cut plan
line by line with a single `in_setting` flag for `Setting:`'s nested sub-items.
Texture needs the same nesting, but its item pattern is deliberately broad
(free prose), so — unlike the narrow setting-item pattern — it must be matched
**last**, after the closing/field/track patterns, or an indented track row would
be swallowed as a texture item. The authored shape is:

```markdown
- **Compress:** The rumour cloud — never reported gossip.
- **Texture:**
  - bakery 6am: proving-room warmth, the scorched tray edge
  - shed roof at 25 knots (plants the ch 29 return)
  - quiet after the argument — no sensory spend past the room
```

An inline value (`- **Texture:** one item`) is also accepted as a first item —
forgiving is cheap here, and silently dropping an author's line is not.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_penny_story.py`:

```python
# --- Task 3: the cut plan's Texture allocation (spec 2026-08-27 §4.2) --------

TEXTURE_PLAN = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen, and the body that ends it.
- **Compress:** Gallery logistics.
- **Texture:**
  - bakery 6am: proving-room warmth, the scorched tray edge
  - shed roof at 25 knots (plants the ch 29 return)
- **Setting:**
  - 1-2 — the pottery studio, late afternoon
- **Opening:** The kiln is still warm.
- **Closing (irony):** She locks a door that was never the way in.
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right in a way Maggie resents.
"""


def test_texture_items_are_parsed_in_authoring_order():
    chapters = parse_cut_plan(TEXTURE_PLAN)
    assert chapters[0]["texture"] == [
        "bakery 6am: proving-room warmth, the scorched tray edge",
        "shed roof at 25 knots (plants the ch 29 return)",
    ]


def test_a_chapter_with_no_texture_field_defaults_to_empty():
    chapters = parse_cut_plan(TEXTURE_PLAN)
    assert chapters[1]["texture"] == []


def test_texture_nesting_does_not_swallow_the_fields_that_follow_it():
    chapters = parse_cut_plan(TEXTURE_PLAN)
    ch = chapters[0]
    assert [s["text"] for s in ch["settings"]] == ["the pottery studio, late afternoon"]
    assert ch["opening"] == "The kiln is still warm."
    assert ch["closing"]["kind"] == "irony"
    assert ch["tracks"] == {"M": "The murder enters a world just shown."}
    assert ch["compress"] == "Gallery logistics."


def test_an_indented_track_row_after_texture_is_still_a_track_not_an_item():
    # The item pattern is broad free prose, so the field patterns must win.
    plan = """## Chapter 01 — T

- **Summary:** s
- **Texture:**
  - one image
  - **M:** the mystery moves
"""
    ch = parse_cut_plan(plan)[0]
    assert ch["texture"] == ["one image"]
    assert ch["tracks"] == {"M": "the mystery moves"}


def test_an_inline_texture_value_is_kept_as_a_first_item():
    plan = "## Chapter 01 — T\n\n- **Summary:** s\n- **Texture:** one image\n"
    assert parse_cut_plan(plan)[0]["texture"] == ["one image"]


def test_a_plan_written_before_texture_existed_parses_exactly_as_before():
    plan = "## Chapter 01 — T\n\n- **Beats:** 1-2\n- **Summary:** s\n- **M:** m\n"
    ch = parse_cut_plan(plan)[0]
    assert ch["texture"] == []
    assert ch["beats"] == [1, 2]
    assert ch["tracks"] == {"M": "m"}
```

(`parse_cut_plan` is already imported at the top of that file — line 2.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_story.py -k texture -v`
Expected: FAIL — `KeyError: 'texture'`.

- [ ] **Step 3: Add the regexes**

In `scripts/penny_story.py`, replace `_CUT_FIELD_RE` and add two constants
beneath the existing `_CUT_SETTING_ITEM_RE`:

```python
_CUT_FIELD_RE = re.compile(
    r"^\s*-\s+\*\*(?P<key>Beats|Summary|Compress|Setting|Texture|Opening):\*\*"
    r"\s*(?P<val>.*)$")
```

```python
# A texture sub-item: `  - bakery 6am: proving-room warmth`. Deliberately BROAD
# where the setting item pattern is narrow — an allocated image is free prose
# with no range to anchor on. That breadth is why the texture branch is matched
# LAST in the loop below, after the closing/field/track patterns: an indented
# `- **M:** …` must stay a track row, not become an image.
_CUT_TEXTURE_ITEM_RE = re.compile(r"^\s+-\s+(?P<val>\S.*?)\s*$")
#: Which cut-plan fields open a nested block, and the chapter key it fills.
_NESTED_BY_KEY = {"Setting": "settings", "Texture": "texture"}
```

- [ ] **Step 4: Rewrite the loop**

Replace `parse_cut_plan`'s body (docstring kept, extended) with:

```python
def parse_cut_plan(text: str) -> list[dict]:
    """The showrunner-approved grouping (spec §5.1).

    `settings`, `opening` and `closing` are the cut-level record of where a
    chapter happens and how it lands (spec 2026-08-12). `texture` is the
    cut-level record of what it may SPEND (spec 2026-08-27 §4.2) — the positive
    half of the `compress` line, allocated once across the whole book. All four
    default empty, so a plan written before any of those designs parses exactly
    as it always did — adoption rules live in `story_cut.check_story`, not here.
    """
    chapters, current, nested = [], None, None
    for raw in text.splitlines():
        m = _CUT_CHAPTER_RE.match(raw)
        if m:
            current = {"num": int(m.group("num")), "title": m.group("title"),
                       "beats": [], "summary": "", "compress": "", "tracks": {},
                       "settings": [], "opening": "", "closing": None,
                       "texture": []}
            chapters.append(current)
            nested = None
            continue
        if current is None:
            continue
        if nested == "settings":
            sm = _CUT_SETTING_ITEM_RE.match(raw)
            if sm:
                current["settings"].append(
                    {"beats": _expand_beats(sm.group("spec")),
                     "text": sm.group("val").strip()})
                continue
        cm = _CUT_CLOSING_RE.match(raw)
        if cm:
            nested = None
            current["closing"] = {"kind": cm.group("kind").strip().lower(),
                                  "text": cm.group("val").strip()}
            continue
        fm = _CUT_FIELD_RE.match(raw)
        if fm:
            key, val = fm.group("key"), fm.group("val").strip()
            nested = _NESTED_BY_KEY.get(key)
            if key == "Beats":
                current["beats"] = _expand_beats(val)
            elif key == "Texture":
                # An inline value is a legal one-item allocation. Dropping it
                # silently would lose an author's line to a formatting choice.
                if val:
                    current["texture"].append(val)
            elif key != "Setting":
                current[key.lower()] = val
            continue
        tm = _CUT_TRACK_RE.match(raw)
        if tm:
            nested = None
            current["tracks"][tm.group("letter")] = tm.group("val").strip()
            continue
        if nested == "texture":
            im = _CUT_TEXTURE_ITEM_RE.match(raw)
            if im:
                current["texture"].append(im.group("val").strip())
    return chapters
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_story.py tests/test_story_cut.py tests/test_story_cut_emit.py tests/test_book_status.py -v`
Expected: PASS — the last three exercise `parse_cut_plan` through its callers
and prove the rewrite changed no existing behaviour.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/penny_story.py tests/test_penny_story.py
git commit -m "penny_story: parse the cut plan's nested Texture allocation"
```

---

## Task 4: Emit `### Texture`, and guard it against wiring forgery

**Files:**
- Modify: `scripts/story_cut.py` (`check_story`'s cut-plan forgery loop;
  `emit_outline`)
- Test: `tests/test_story_cut_emit.py`, `tests/test_story_cut.py`,
  `tests/test_plot_stage.py`, `tests/test_packet_assemble.py`

**Interfaces:**
- Consumes: `parse_cut_plan(...)[i]["texture"]` (Task 3).
- Produces: a `### Texture` H3 section in each emitted chapter block, placed
  immediately after `### Reader-Facing Shape` and before `### Opening`. Emitted
  only when the chapter has texture items. No new finding name.

**Context an implementer needs.** Two things.

First, **placement**. `### Reader-Facing Shape` carries the `Compress:`
sub-block — what the chapter must *not* spend. Texture is the positive
counterpart of exactly that line (spec §4.2), so the two sit adjacent.

Second, **forgery**. `emit_outline` writes cut-plan prose into the chapter block
at column 0, and `penny_wiring` matches `FIELD_RE`/`TRACK_RE` against *every*
line of that block — not only the wiring section. An authored
`- **Closes:** q-bogus` in a texture item would become a wiring line the cut
never wrote, and `tension_check` would fire `phantom-answer` on a chapter whose
footer says no such thing. `check_story` already guards `Opening`,
`Chapter Summary` and `Compress` this way; texture items join that guard, reusing
the **existing** `wiring-shaped-directive` finding name — the roster stays at 23.

Third, and requiring no code: the blind reader's copy. `plot_stage`'s
`_KEEP_SUBSECTIONS` is an **allowlist**, so `### Texture` is dropped from the
reader's copy by construction. That is correct — texture allocation is drafting
instruction addressed to the writer, like `Compress:`, not something a reader
experiences. Step 1 pins it so nobody "fixes" it later.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_story_cut_emit.py`:

```python
# --- Task 4: emit ### Texture (spec 2026-08-27 §4.2) ------------------------

TEXTURE_PLAN = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen, and the body that ends it.
- **Compress:** Gallery logistics.
- **Texture:**
  - bakery 6am: proving-room warmth, the scorched tray edge
  - shed roof at 25 knots (plants the ch 29 return)
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right in a way Maggie resents.
"""


def _emit_textured():
    return emit_outline(STORY, TEXTURE_PLAN, parse_questions(STORY), LEDGER,
                        reveal_chapter=2, guardrails="Do not name the culprit early.",
                        job_titles=JOB_TITLES, solution={})


def test_texture_items_are_emitted_as_a_bulleted_section():
    out = _emit_textured()
    assert ("### Texture\n"
            "- bakery 6am: proving-room warmth, the scorched tray edge\n"
            "- shed roof at 25 knots (plants the ch 29 return)\n") in out


def test_texture_sits_between_reader_facing_shape_and_required_beats():
    out = _emit_textured()
    assert out.index("### Reader-Facing Shape") < out.index("### Texture")
    assert out.index("### Texture") < out.index("### Required Beats")


def test_texture_is_a_packet_section_the_wiring_parser_can_read_back():
    sections = parse_packet_sections(chapter_block(_emit_textured(), 1))
    assert sections["Texture"].startswith("- bakery 6am:")


def test_a_chapter_with_no_allocation_gets_no_texture_section():
    block = chapter_block(_emit_textured(), 2)
    assert "### Texture" not in block


def test_a_plan_with_no_texture_anywhere_emits_exactly_what_it_did_before():
    assert "### Texture" not in _emit()
```

Append to `tests/test_story_cut.py`:

```python
# --- Task 4: a texture item may not forge a wiring line ---------------------

# `GOOD_STORY`, `JOBS` and `CLUES` are this file's existing module-level
# fixtures (top of the file). GOOD_STORY has exactly three beats, so the plan
# below claims 1-3 and the only findings in play are the ones under test.

def _plan_with_texture(item):
    return ("## Chapter 01 — One\n\n- **Beats:** 1-3\n- **Summary:** s\n"
            f"- **Compress:** c\n- **Texture:**\n  - {item}\n")


def test_a_texture_item_shaped_like_a_wiring_field_is_refused():
    r = check_story(GOOD_STORY, _plan_with_texture("**Closes:** q-bogus"),
                    JOBS, CLUES)
    assert any("wiring-shaped-directive" in f and "Texture" in f
               for f in r["blocking"])


def test_a_texture_item_shaped_like_a_track_row_is_refused():
    r = check_story(GOOD_STORY, _plan_with_texture("**M:** the mystery moves"),
                    JOBS, CLUES)
    assert any("wiring-shaped-directive" in f for f in r["blocking"])


def test_an_ordinary_texture_item_is_clean():
    r = check_story(GOOD_STORY, _plan_with_texture("bakery 6am: yeast, warmth"),
                    JOBS, CLUES)
    assert r["blocking"] == []
```

Append to `tests/test_plot_stage.py`:

```python
# --- Task 4: texture is drafting instruction, never reader-facing -----------

def test_readers_copy_drops_the_texture_section():
    text = ("## Chapter 01 — T\n\n### Chapter Summary\nShe locks up.\n\n"
            "### Texture\n- bakery 6am: proving-room warmth\n\n"
            "### Required Beats\n- She locks up.\n")
    out = readers_copy_text(text)
    assert "proving-room warmth" not in out
    assert "Texture" not in out
    assert "She locks up." in out
```

Append to `tests/test_packet_assemble.py` (it already has a `series_tree`
fixture returning the tmp series root, and an outline at
`input/book-01/outline.md` whose chapter 05 is in packet format):

```python
# --- Task 4: the allocation reaches the packet with no packet_assemble code ---

def test_the_packet_carries_the_chapters_texture_allocation(series_tree):
    # packet_assemble embeds the chapter block VERBATIM, so this needs no code
    # of its own — pin it so a future refactor cannot quietly drop it.
    outline_p = series_tree / "input/book-01/outline.md"
    head, sep, tail = outline_p.read_text(encoding="utf-8").partition("## Chapter 05")
    assert sep, "fixture outline has no chapter 05"
    tail = tail.replace(
        "### Required Beats",
        "### Texture\n- bakery 6am: proving-room warmth\n\n### Required Beats", 1)
    outline_p.write_text(head + sep + tail, encoding="utf-8")

    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    assert "### Texture" in text
    assert "bakery 6am: proving-room warmth" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut_emit.py tests/test_story_cut.py tests/test_plot_stage.py tests/test_packet_assemble.py -k texture -v`
Expected: FAIL on the emit and forgery tests (`### Texture` never appears; no
`wiring-shaped-directive` for a texture item). The `readers_copy` test should
already PASS — the allowlist gives it for free; that is the point of pinning it.

- [ ] **Step 3: Extend the forgery guard**

In `scripts/story_cut.py`, inside `check_story`, directly after the existing
`for ch in chapters:` / `for label, emitted in (...)` guard loop, add:

```python
    # Texture items are emitted the same way, one bullet each — same forgery,
    # same finding. Reusing `wiring-shaped-directive` rather than minting a
    # texture-specific name is deliberate: the failure is identical, and the
    # roster stays at twenty-three.
    for ch in chapters:
        for item in ch["texture"]:
            emitted = f"- {item}"
            if FIELD_RE.match(emitted) or TRACK_RE.match(emitted):
                blocking.append(
                    f"wiring-shaped-directive: ch {ch['num']:02d} Texture reads "
                    f"'{emitted}', which the outline parser would read as a "
                    f"wiring field or a Track Movement row rather than as prose "
                    f"— the cut writes those itself. Reword the item so it does "
                    f"not begin with **Because:**/**Opens:**/**Closes:**/"
                    f"**Carries:**/**Hook:** or **<letter>:**")
```

- [ ] **Step 4: Emit the section**

In `emit_outline`, immediately after the `### Reader-Facing Shape` append and
before the `if ch["opening"]:` block:

```python
        # The positive half of the Compress line above it (spec 2026-08-27
        # §4.2): what this chapter MAY spend, allocated once across the whole
        # book so no image is spent twice. A resource, not an obligation —
        # nothing downstream checks that it was spent, and map_check has no
        # `unscheduled-texture` on purpose.
        if ch["texture"]:
            out.append("### Texture\n"
                       + "\n".join(f"- {t}" for t in ch["texture"]) + "\n")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut_emit.py tests/test_story_cut.py tests/test_plot_stage.py tests/test_packet_assemble.py -v`
Expected: PASS.

- [ ] **Step 6: Confirm the finding roster did not grow**

Run: `python3 -m pytest tests/test_readme_check_count.py tests/test_claude_md_check_count.py -v`
Expected: PASS — 23 story_cut findings, unchanged.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_emit.py tests/test_story_cut.py \
        tests/test_plot_stage.py tests/test_packet_assemble.py
git commit -m "story_cut: emit ### Texture and guard its items against wiring forgery"
```

---

## Task 5: A scene's `Texture:` field in the prose map

**Files:**
- Modify: `scripts/penny_map.py`
- Test: `tests/test_penny_map.py`, `tests/test_map_check.py`,
  `tests/fixtures/maps/ch-05.md`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: each scene dict from `penny_map.parse_map(text)` gains
  `"texture_text": str | None` — the scene's `Texture:` body, or `None`.

**Context an implementer needs.** The map's `Clue:` field is the model: a
multi-line body that runs until the next field-shaped line, scene heading, or
EOF. `Texture:` is exactly parallel in authoring, and **deliberately not
parallel in enforcement** — `map_check.py` gains no finding, because texture is
a resource, not a discharge requirement (spec §4.2). Parsing it anyway is what
makes it a first-class field rather than open-vocabulary prose, and Step 1's
last test pins the *absence* of a gate so nobody adds one by reflex.

- [ ] **Step 1: Write the failing tests**

First add a `Texture:` field to an existing scene in
`tests/fixtures/maps/ch-05.md` — put it in Scene 1, directly after that scene's
`Beats covered:` line:

```
Texture:
Bakery at 6am — proving-room warmth, the scorched edge of the second tray.
Shed roof at 25 knots, once, from inside.
```

Then append to `tests/test_penny_map.py`:

```python
# --- Task 5: the scene-level Texture field (spec 2026-08-27 §4.2) -----------

def test_parse_map_reads_a_scenes_texture_field():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    t = m["scenes"][0]["texture_text"]
    assert "proving-room warmth" in t
    assert "Shed roof at 25 knots" in t


def test_a_scene_with_no_texture_field_is_none():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["scenes"][1]["texture_text"] is None


def test_a_texture_field_does_not_swallow_the_clue_that_follows_it():
    text = ("## Scene 1 — S\nTarget: 400–500 words\nWeight: anchor\n"
            "Beats covered: 1\n"
            "Texture:\nBakery at 6am — proving-room warmth.\n"
            "Clue:\n[c-altered] the appointment, changed.\n")
    s = parse_map(text)["scenes"][0]
    assert "proving-room warmth" in s["texture_text"]
    assert "[c-altered]" not in s["texture_text"]
    assert "[c-altered]" in s["clue_text"]
```

Append to `tests/test_map_check.py`. That file's `_map_text()` reads the very
fixture you just edited, and `_packet_text()` builds the matching packet, so the
existing `test_clean_canonical_pair_passes` is already the proof that a
`Texture:` field gates nothing — this test says so by name:

```python
# --- Task 5: texture is a resource, not a discharge requirement -------------

def test_map_check_has_no_finding_for_texture():
    # Spec 2026-08-27 §4.2: there is deliberately no `unscheduled-texture`. A
    # chapter that spends three of four allocated images is correct, not short,
    # and an image that competed with beats and clues for the beat sheet's
    # obligation budget would be exactly the wrong kind of win.
    text = _map_text()
    assert "Texture:" in text, "fixture ch-05.md should now carry a Texture field"
    out = check_map(_packet_text(), text, _profile())
    assert out["blocking"] == []
    assert not any("texture" in b.lower() for b in out["blocking"] + out["notes"])
```

(`check_map(packet_text, map_text, profile)` returns
`{"blocking": [...], "notes": [...]}` — both keys always exist.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_map.py tests/test_map_check.py -v`
Expected: FAIL — `KeyError: 'texture_text'`.

- [ ] **Step 3: Add the field regex**

In `scripts/penny_map.py`, directly beneath `CLUE_FIELD_RE`:

```python
# Parallel to CLUE_FIELD_RE in authoring and deliberately NOT parallel in
# enforcement: a scene's share of the chapter's texture allocation (spec
# 2026-08-27 §4.2). `map_check.py` has no finding for it — texture is a
# resource the chapter MAY spend, never an obligation it must prove it spent,
# and an `unscheduled-texture` would put images into competition with beats and
# clues for the genre beat sheet's obligation budget.
TEXTURE_FIELD_RE = re.compile(
    r"^Texture:\s*\n?(.*?)(?=^\w[\w '’-]*:\s*$|^\w[\w '’-]*:\s|\Z|^##\s)",
    re.MULTILINE | re.DOTALL)
```

- [ ] **Step 4: Populate the field**

In `parse_map`'s scene loop, add beside the existing `cm = CLUE_FIELD_RE...`:

```python
        xm = TEXTURE_FIELD_RE.search(body)
        texture = xm.group(1).strip() if xm and xm.group(1).strip() else None
```

and add to the appended dict, after `"clue_text": clue,`:

```python
            "texture_text": texture,
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_map.py tests/test_map_check.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/penny_map.py tests/test_penny_map.py tests/test_map_check.py \
        tests/fixtures/maps/ch-05.md
git commit -m "penny_map: parse a scene's Texture field (no map_check finding)"
```

---

## Task 6: `texture_apply.py` — splice the approved allocation into the cut plan

**Files:**
- Create: `scripts/texture_apply.py`
- Test: `tests/test_texture_apply.py`

**Interfaces:**
- Consumes: `penny_paths.series_root()`; the field shape Task 3 parses.
- Produces:
  - `texture_apply.PLAN_REL == "plot/texture.md"` (relative to `input/book-NN/`)
  - `parse_texture_plan(text) -> dict[int, list[str]]`
  - `apply_texture(cut_plan_text: str, plan: dict) -> tuple[str, list[str], list[str]]`
    returning `(new_text, blocking, notes)`; `new_text` is the input unchanged
    whenever `blocking` is non-empty.
  - `main(argv=None) -> int` — exit 0 clean (file written), 1 blocking findings
    (nothing written), 2 usage/missing file.

**Context an implementer needs.** The allocation is a taste call the showrunner
makes over the whole book at once; landing ~35 blocks in the right chapters is
mechanics, and mechanics belong in the deterministic layer rather than in a hand
edit that can silently put one chapter's spend in its neighbour. The script is
**idempotent** — re-running replaces the block it wrote last time — so
re-allocating after a boundary move is one command.

The save-point file `input/book-NN/plot/texture.md` looks like:

```markdown
# Texture allocation — book 01

## Chapter 01
- bakery 6am: proving-room warmth, the scorched tray edge
- shed roof at 25 knots (plants the ch 29 return)

## Chapter 02
- quiet — no sensory spend past the room
```

Placement rule: the block goes immediately after the chapter's **last**
`Summary:`/`Compress:` line, so it sits with the compress line it is the
positive half of, and above `Setting:`/`Opening:`/`Closing:`/tracks.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_texture_apply.py`:

```python
from scripts import texture_apply as ta

PLAN = """# Texture allocation — book 01

## Chapter 01
- bakery 6am: proving-room warmth
- shed roof at 25 knots

## Chapter 02
- quiet — no sensory spend past the room
"""

CUT = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen.
- **Compress:** Gallery logistics.
- **Setting:**
  - 1-2 — the pottery studio, late afternoon
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right.
"""


def test_parse_texture_plan_reads_chapters_and_items():
    assert ta.parse_texture_plan(PLAN) == {
        1: ["bakery 6am: proving-room warmth", "shed roof at 25 knots"],
        2: ["quiet — no sensory spend past the room"],
    }


def test_a_title_bullet_before_any_chapter_is_not_an_item():
    plan = "# Texture allocation\n- a note to myself\n\n## Chapter 01\n- one image\n"
    assert ta.parse_texture_plan(plan) == {1: ["one image"]}


def test_the_block_lands_after_compress_and_before_setting():
    out, blocking, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    assert blocking == []
    assert ("- **Compress:** Gallery logistics.\n"
            "- **Texture:**\n"
            "  - bakery 6am: proving-room warmth\n"
            "  - shed roof at 25 knots\n"
            "- **Setting:**\n") in out


def test_the_spliced_plan_parses_back_into_the_allocation():
    from scripts.penny_story import parse_cut_plan
    out, _, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    chapters = parse_cut_plan(out)
    assert chapters[0]["texture"] == ["bakery 6am: proving-room warmth",
                                      "shed roof at 25 knots"]
    assert chapters[1]["texture"] == ["quiet — no sensory spend past the room"]
    assert chapters[0]["compress"] == "Gallery logistics."
    assert chapters[0]["tracks"] == {"M": "The murder enters a world just shown."}


def test_applying_twice_is_idempotent():
    once, _, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    twice, _, _ = ta.apply_texture(once, ta.parse_texture_plan(PLAN))
    assert once == twice


def test_a_re_allocation_replaces_the_previous_block():
    once, _, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    new, blocking, _ = ta.apply_texture(once, {1: ["only this now"], 2: ["x"]})
    assert blocking == []
    assert "proving-room warmth" not in new
    assert "  - only this now\n" in new


def test_an_allocation_for_a_chapter_the_plan_lacks_is_refused_by_name():
    out, blocking, _ = ta.apply_texture(CUT, {9: ["ghost image"]})
    assert any(f.startswith("unknown-chapter:") and "09" in f for f in blocking)
    assert out == CUT          # never partially applied


def test_a_chapter_with_no_allocation_is_an_advisory_not_a_finding():
    out, blocking, notes = ta.apply_texture(CUT, {1: ["one image"]})
    assert blocking == []
    assert any(n.startswith("unallocated-chapter:") and "02" in n for n in notes)
    assert "### " not in out   # untouched chapters keep their shape


def test_a_named_chapter_with_no_items_is_advised_and_left_alone():
    out, blocking, notes = ta.apply_texture(CUT, {1: [], 2: ["x"]})
    assert blocking == []
    assert any(n.startswith("empty-allocation:") and "01" in n for n in notes)
    from scripts.penny_story import parse_cut_plan
    assert parse_cut_plan(out)[0]["texture"] == []


def test_a_chapter_with_no_summary_or_compress_anchor_is_refused():
    cut = "## Chapter 01 — T\n\n- **Beats:** 1\n- **M:** m\n"
    out, blocking, _ = ta.apply_texture(cut, {1: ["one image"]})
    assert any(f.startswith("no-anchor:") for f in blocking)
    assert out == cut


def test_prose_above_the_first_chapter_heading_is_preserved():
    cut = "# Cut plan — book 01\n\nApproved 2026-08-27.\n\n" + CUT
    out, blocking, _ = ta.apply_texture(cut, ta.parse_texture_plan(PLAN))
    assert blocking == []
    assert out.startswith("# Cut plan — book 01\n\nApproved 2026-08-27.\n")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_texture_apply.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.texture_apply'`.

- [ ] **Step 3: Write the script**

Create `scripts/texture_apply.py`:

```python
#!/usr/bin/env python3
"""Splice an approved texture allocation into a book's cut plan (spec
2026-08-27 §4.2).

The allocation itself is a taste call — which chapter spends which image, where
texture goes deliberately quiet, which images recur as motifs — made by the
showrunner over the whole book at once and saved to
`input/book-NN/plot/texture.md`. Landing thirty-five blocks in the right chapter
blocks is not a taste call; it is mechanics, and a hand edit that puts one
chapter's spend in its neighbour has no symptom until a drafted chapter reads
wrong.

Idempotent: re-running replaces the `- **Texture:**` block it wrote last time,
so re-allocating after a chapter boundary moves is one command rather than a
manual diff.

Never partially applies. A blocking finding leaves cut-plan.md byte-identical.

  python3 scripts/texture_apply.py 01
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_paths

#: The allocation save point, relative to `input/book-NN/`. It lives beside the
#: plot workshop's other save points because it is the same kind of artifact:
#: the showrunner's own judgment, written once, arguable in one place, cheap to
#: redo.
PLAN_REL = "plot/texture.md"

_CHAPTER_RE = re.compile(r"^##\s+Chapter\s+(?P<num>\d+)\b")
_ITEM_RE = re.compile(r"^\s*-\s+(?P<val>\S.*?)\s*$")
_TEXTURE_FIELD_RE = re.compile(r"^\s*-\s+\*\*Texture:\*\*")
_ANCHOR_RE = re.compile(r"^\s*-\s+\*\*(?:Summary|Compress):\*\*")
_NESTED_ITEM_RE = re.compile(r"^\s+-\s")


def parse_texture_plan(text: str) -> dict:
    """chapter number -> its allocated items, in authoring order.

    A chapter heading with no items yields an empty list rather than vanishing:
    naming a chapter and allocating it nothing is a different statement from not
    naming it, and `apply_texture` reports the two differently.
    """
    out: dict = {}
    current = None
    for raw in text.splitlines():
        m = _CHAPTER_RE.match(raw)
        if m:
            current = int(m.group("num"))
            out.setdefault(current, [])
            continue
        if current is None:
            continue
        im = _ITEM_RE.match(raw)
        if im:
            out[current].append(im.group("val"))
    return out


def _strip_texture(block: list) -> list:
    """The chapter block with any previously spliced Texture block removed."""
    out, dropping = [], False
    for raw in block:
        if _TEXTURE_FIELD_RE.match(raw):
            dropping = True
            continue
        if dropping:
            if not raw.strip():
                dropping = False
                out.append(raw)
                continue
            if _NESTED_ITEM_RE.match(raw):
                continue
            dropping = False
        out.append(raw)
    return out


def _anchor_index(block: list) -> "int | None":
    """Index of the line the Texture block goes after: the LAST Summary or
    Compress line. Texture is the positive half of the compress line, so it
    belongs with it — above Setting, Opening, Closing and the track rows."""
    hits = [i for i, raw in enumerate(block) if _ANCHOR_RE.match(raw)]
    return hits[-1] if hits else None


def apply_texture(cut_plan_text: str, plan: dict) -> tuple:
    """(new_text, blocking, notes).

    `new_text` is the input unchanged whenever `blocking` is non-empty — a
    half-applied allocation is worse than none, because the half that landed
    looks approved.
    """
    lines = cut_plan_text.splitlines()
    blocking: list = []
    notes: list = []

    order = [(int(m.group("num")), i) for i, raw in enumerate(lines)
             if (m := _CHAPTER_RE.match(raw))]
    starts = {num: i for num, i in order}
    ends = {num: (order[k + 1][1] if k + 1 < len(order) else len(lines))
            for k, (num, i) in enumerate(order)}

    for num in sorted(plan):
        if num not in starts:
            blocking.append(
                f"unknown-chapter: the allocation names chapter {num:02d}, "
                f"which cut-plan.md does not have — a boundary moved since the "
                f"allocation was written; re-allocate against the current plan")
    if blocking:
        return cut_plan_text, blocking, notes

    out = lines[:order[0][1]] if order else list(lines)
    for num, start in order:
        block = _strip_texture(lines[start:ends[num]])
        items = plan.get(num)
        if items is None:
            notes.append(
                f"unallocated-chapter: chapter {num:02d} has no allocation — it "
                f"spends nothing this book, which is legal: texture is a "
                f"resource, not an obligation")
            out.extend(block)
            continue
        if not items:
            notes.append(
                f"empty-allocation: chapter {num:02d} is named by the "
                f"allocation with no items — no Texture block written")
            out.extend(block)
            continue
        anchor = _anchor_index(block)
        if anchor is None:
            blocking.append(
                f"no-anchor: chapter {num:02d} has neither a **Summary:** nor a "
                f"**Compress:** line to place the Texture block after — repair "
                f"the cut plan")
            out.extend(block)
            continue
        rendered = ["- **Texture:**"] + [f"  - {t}" for t in items]
        out.extend(block[:anchor + 1] + rendered + block[anchor + 1:])

    if blocking:
        return cut_plan_text, blocking, notes
    return "\n".join(out) + "\n", blocking, notes


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: texture_apply.py <book>", file=sys.stderr)
        return 2
    book = str(argv[0]).zfill(2)

    root = penny_paths.series_root()
    bookdir = root / "input" / f"book-{book}"
    plan_p, cut_p = bookdir / PLAN_REL, bookdir / "cut-plan.md"
    for p in (plan_p, cut_p):
        if not p.is_file():
            print(f"texture_apply: missing {p}", file=sys.stderr)
            return 2

    plan = parse_texture_plan(plan_p.read_text(encoding="utf-8"))
    if not plan:
        print(f"texture_apply: {plan_p} names no chapters", file=sys.stderr)
        return 2

    text, blocking, notes = apply_texture(cut_p.read_text(encoding="utf-8"), plan)
    if blocking:
        for f in blocking:
            print(f)
        print("\nNothing written — cut-plan.md is unchanged.", file=sys.stderr)
        return 1

    cut_p.write_text(text, encoding="utf-8")
    print(f"texture_apply: allocated {len(plan)} chapters into {cut_p}")
    if notes:
        print("\nAdvisory — nothing blocks on these:")
        for n in notes:
            print(f"  {n}")
    # No literal path here: this runs from a series folder, where the engine
    # lives at ${CLAUDE_PLUGIN_ROOT}. The runbook owns the invocation.
    print(f"\nNow re-run the cut (story_cut.py {book}) so outline.md carries "
          f"the allocation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_texture_apply.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/texture_apply.py tests/test_texture_apply.py
git commit -m "texture_apply: splice an approved allocation into cut-plan.md"
```

---

## Task 7: The `texture-allocator` agent and the `/allocate-texture` command

**Files:**
- Create: `agents/texture-allocator.md`
- Create: `commands/allocate-texture.md`
- Create: `tests/test_texture_allocation_docs.py`

**Interfaces:**
- Consumes: `scripts/texture_apply.py` (Task 6), `config/setting-pack/reservoir.md`
  (Task 1), the `- **Texture:**` cut-plan shape (Task 3).
- Produces: the runbook every later doc change points at.

**Context an implementer needs.** The agent's posture is the engine's standard
one: **it proposes, the showrunner approves, only the approved artifact is
consumed** — same as `mystery-planner`, `chapter-cutter` and `map-maker`. Two
rules are load-bearing and must appear in the agent file in so many words:

1. **No image is allocated twice.** Repetition past chapter 10 is the real
   failure mode (spec §3, "The reservoir is thin" — ~25 documented images across
   35 chapters), and one whole-book pass is what prevents it *by construction*
   rather than by accounting.
2. **Never invent a town fact.** Every item must come from the reservoir or the
   setting pack. The one drafting failure the spec records is an invented one —
   a kiln "tested a fortnight ago by an electrician who charged her properly for
   it", which broke two later beats. A gap in the reservoir is reported back to
   the showrunner, never filled in.

- [ ] **Step 1: Write the failing contract test**

Create `tests/test_texture_allocation_docs.py`:

```python
from pathlib import Path

AGENT = Path("agents/texture-allocator.md")
COMMAND = Path("commands/allocate-texture.md")


def test_the_agent_exists_and_declares_its_name():
    assert AGENT.is_file()
    assert "name: texture-allocator" in AGENT.read_text(encoding="utf-8")


def test_the_agent_holds_the_two_load_bearing_rules():
    t = AGENT.read_text(encoding="utf-8")
    for phrase in ("no image twice", "never invent", "config/setting-pack/reservoir.md",
                   "cut-plan.md", "input/book-NN/plot/texture.md",
                   "You propose. You never write.", "resource, not an obligation",
                   "Register under pressure"):
        assert phrase in t, phrase


def test_the_agent_never_gains_a_gate():
    t = AGENT.read_text(encoding="utf-8")
    assert "unscheduled-texture" not in t


def test_the_command_runs_the_splice_the_cut_and_names_the_lock_cost():
    t = COMMAND.read_text(encoding="utf-8")
    for phrase in ("texture_apply.py", "story_cut.py", "texture-allocator",
                   "input/book-$book/plot/texture.md",
                   "${CLAUDE_PLUGIN_ROOT}/scripts/texture_apply.py",
                   "lock-mystery", "map-chapter"):
        assert phrase in t, phrase


def test_the_command_uses_the_plugin_root_for_every_script_call():
    t = COMMAND.read_text(encoding="utf-8")
    for line in t.splitlines():
        if "scripts/" in line and "python3" in line:
            assert "${CLAUDE_PLUGIN_ROOT}" in line, line
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_texture_allocation_docs.py -v`
Expected: FAIL — `assert AGENT.is_file()`.

- [ ] **Step 3: Write the agent**

Create `agents/texture-allocator.md`:

```markdown
---
name: texture-allocator
description: Allocates a book's sensory texture across all its chapters at once — which chapter spends which image, where texture goes deliberately quiet, which images return as motifs. Proposes only; writes nothing.
---
# Texture Allocator

**Role posture:** proposer, whole-book. The same posture as `mystery-planner`
and `chapter-cutter`: you surface a complete allocation; the showrunner chooses
it.

**Independence:** not this agent's property. You read the whole book's plan and
the sealed solution, because knowing where the pressure lands is how you know
which chapters must go quiet.

**Why you exist:** every other creative concern in this engine is split into a
cheap whole-book allocation and a local prose job. Clues have a schedule; beats
have a schedule; words have a band. Texture had only a wish — one standing
guardrail repeated identically into every chapter, asking the chapters under the
most tonal pressure to reach for warmth they are least likely to reach for
unprompted. You are the missing schedule.

**Inputs:**
- `input/book-NN/cut-plan.md` — every chapter's title, type flag, summary,
  compress line, setting ranges, opening and closing. This is your whole view of
  the book and it is why the allocation can be made at all.
- `config/setting-pack/reservoir.md` — the town's concrete sensory inventory,
  grouped by location, weather, season, time of day, craft process and social
  ritual. **This is your supply.** It is derived from
  `input/series/background-history.md`; you never edit it.
- `config/setting-pack/setting.md` — the authored stance.
- `config/voice-pack/voice-pack.md` — in particular *Register under pressure*
  and *Cozy sensuality*.
- The genre beat sheet (resolve it with
  `penny_genre.py beat-sheet`) — the tension curve you are allocating against.
- `output/book-NN/mystery-solution.md` — so a motif planted early can mean
  something different when it returns.

**You propose. You never write.** Emit the allocation as your message. The
showrunner edits it and saves the approved version to
`input/book-NN/plot/texture.md`, which `scripts/texture_apply.py` splices into
`cut-plan.md`. Writing either file yourself would make a generated artifact look
approved.

## What you decide

- **Which chapters carry heavy sensory load and which run lean.** Load is not
  spread evenly and must not be: an evenly-textured book has no texture, it has
  wallpaper.
- **Where texture goes deliberately quiet.** The voice pack rules it: *"Peak
  tension: sentences stop building. Things happen and the prose reports them. No
  wit until the pressure drops."* A chapter at peak pressure is allocated
  silence, and you say so in the allocation — "quiet: no sensory spend past the
  room" is a real allocation, not an omission.
- **Which images recur as motifs, and where.** An image planted at ch 3 and
  returned at ch 29 meaning something different is the highest-value thing you
  can allocate. Name both ends, and say in the item which chapter the return is
  for.
- **What each chapter spends, so that nothing is spent twice.**

## The two rules that are not negotiable

**Allocate no image twice.** This is the whole reason the allocation is a single
whole-book pass. The town's documented inventory is thin — roughly twenty-five
concrete images before the reservoir was written — and the failure mode past
chapter ten is not genericness but repetition. Because one pass allocates across
every chapter at once, no chapter can be handed an image another chapter already
holds. A deliberate motif return is the one exception, and it is only an
exception when you name it as one.

**Never invent a town fact.** Every item you allocate must be in the reservoir
or the setting pack, or be an ordinary derivation from one (the bakery's 6am
warmth at 3pm instead; the shed roof at a different wind strength). If a chapter
needs sensory material the reservoir does not have, **say so in your proposal
and allocate nothing for it** — that gap is a note to the showrunner to extend
`input/series/background-history.md`, and the reservoir is re-cut. The one
recorded drafting failure in this engine is an invented one: a kiln "tested a
fortnight ago by an electrician who charged her properly for it", specified by
nothing, which broke two later beats. Where the drafter was told exactly what to
do it was good; where it improvised it caused a continuity failure.

## What this layer is not

Texture is a **resource, not an obligation**. The chapter is told what it *may*
spend, never what it must prove it spent. Nothing checks that an allocated image
reached the page: `map_check.py` has no `unscheduled-texture`, and it never will
— an image that competed with beats and clues for the genre beat sheet's
obligation budget would be exactly the wrong kind of win. A chapter that uses
three of its four allocated images is correct, not short.

So allocate generously enough that the chapter has choices, and specifically
enough that the choices are this town's.

## Output format — exactly this

```markdown
# Texture allocation — book NN

## Chapter 01
- bakery 6am: proving-room warmth, the scorched edge of the second tray
- shed roof at 25 knots — the ridge capping lifting and dropping (plants the
  ch 29 return)

## Chapter 02
- quiet — no sensory spend past the room; pressure lands here
```

One `## Chapter NN` heading per chapter you allocate, then one `- ` item per
image. Chapter numbers must match `cut-plan.md` exactly — `texture_apply.py`
refuses `unknown-chapter` otherwise. A chapter you allocate nothing may be left
out; leaving it out and allocating it silence are different statements, so make
the silence explicit when it is a choice.

Keep each item one line where you can. An item may not begin with
`**Because:**` / `**Opens:**` / `**Closes:**` / `**Carries:**` / `**Hook:**` or
`**<letter>:**` — those parse as the cut's own wiring output, and `story_cut.py`
refuses `wiring-shaped-directive` rather than emitting them.

## What you never do

Never write prose. Never write the cut plan, the outline, a ledger or a
certificate. Never edit `config/setting-pack/reservoir.md` — it is derived.
Never move a chapter boundary; if the allocation makes one look wrong, say so
and leave it to the cut.
```

- [ ] **Step 4: Write the command**

Create `commands/allocate-texture.md`:

```markdown
---
description: Allocate a book's sensory texture across every chapter at once — the positive half of the cut plan's compress line (spec 2026-08-27 §4.2).
argument-hint: <book-number>
---
# /allocate-texture

Run once per book, **after `cut-plan.md` is approved and before `/map-chapter`**.
One whole-book pass decides which chapter spends which image, where texture goes
deliberately quiet, and which images return as motifs — so that no image is spent
twice and no chapter is left asking the drafter to improvise the town.

Same economics as the clue schedule: a few hundred lines, readable in five
minutes, arguable, cheap to redo.

**Read this before running it on a book already in flight.** The allocation edits
`cut-plan.md`, which means the book must be re-cut, which changes `outline.md`.
If the book is already locked, the lock must be re-minted and every packet built
from the old outline is stale. That is known and cheap, but it is a deliberate
act — not a background improvement. Step 6 covers it.

## Steps

1. **Parse args and write the harness state marker:**

   ```bash
   book=$1
   mkdir -p .penny
   echo "book=$book stage=TEXTURE" > .penny/current-stage
   ```

2. **Check the preconditions.** `input/book-$book/cut-plan.md` must exist and be
   the approved plan — the allocation is written against its chapter numbers.
   `config/setting-pack/reservoir.md` should exist; if it does not, the series
   has not authored a `## Reservoir` section in
   `input/series/background-history.md`. Write one and run:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/background_cut.py"
   ```

   Allocating against an absent reservoir is possible but thin — the whole point
   of the layer is that it spends a real inventory rather than a wish.

3. **Dispatch the `texture-allocator` sub-agent** (pass `model:` = `plot_model`
   from `config/run-config.md`, defaulting to `drafting_model` when unset —
   planning work, same routing as the workshop; the agent def carries no
   `model:` frontmatter, so without this override it silently inherits the
   parent). It reads the whole cut plan, the reservoir, the setting and voice
   packs, the genre beat sheet and the sealed solution, and proposes the
   allocation for every chapter at once. **It proposes only and writes nothing.**

4. **Present the proposal to the showrunner.** This is a taste call: which
   chapters run rich, which run lean, which go silent under pressure, which
   images return and where. The showrunner edits it. Save the **approved**
   allocation — and only the approved allocation — to
   `input/book-$book/plot/texture.md`.

5. **Splice it into the cut plan and re-cut:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/texture_apply.py" $book
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/story_cut.py" $book
   ```

   `texture_apply.py` is idempotent — it replaces any block it wrote before, so
   re-allocating is one command. Exit 1 names what it refused and writes
   nothing:
   - `unknown-chapter` — the allocation names a chapter `cut-plan.md` does not
     have. A boundary moved; re-allocate against the current plan.
   - `no-anchor` — a chapter has neither a `**Summary:**` nor a `**Compress:**`
     line to place the block after; repair the cut plan.

   Advisories are printed and block nothing: `unallocated-chapter` (a chapter
   spends nothing this book — legal; texture is a resource, not an obligation)
   and `empty-allocation` (a chapter named with no items).

   `story_cut.py` then rewrites `outline.md` with a `### Texture` section in each
   allocated chapter block. It refuses `outline-modified-since-cut` if the
   outline has been hand-edited since the cut wrote it — that work is yours to
   keep or discard, and the cut will not decide for you.

6. **If the book was already locked, re-mint and re-map.** `cut-plan.md` is one
   of the two files whose edit invalidates the lock:

   ```bash
   rm .penny/locks/book-$book.mystery.lock
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py" lock-mystery $book
   ```

   Every packet built from the previous outline is now stale (`built_from_outline`
   no longer matches). Re-run `/map-chapter $book <MM>` for any chapter already
   mapped; `preflight draft` will refuse a stale packet or map by name if you
   forget.

7. **Advance the marker:**

   ```bash
   echo "book=$book stage=TEXTURED" > .penny/current-stage
   ```

   The book's chapters now carry what they may spend. `/map-chapter` distributes
   each chapter's allocation across its scenes' `Texture:` fields, and the
   drafter renders it.
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_texture_allocation_docs.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agents/texture-allocator.md commands/allocate-texture.md \
        tests/test_texture_allocation_docs.py
git commit -m "allocate-texture: whole-book texture allocation command and agent"
```

---

## Task 8: Wire the consumers — map-maker, drafter, chapter-cutter, runbooks

**Files:**
- Modify: `agents/map-maker.md`, `agents/drafter.md`, `agents/chapter-cutter.md`
- Modify: `commands/plot-book.md` (step 8), `commands/map-chapter.md` (step 3)
- Test: `tests/test_texture_allocation_docs.py`

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: no code interface — this is the instruction layer that makes the
  allocation reach prose.

**Context an implementer needs.** `map-maker`'s isolation is deliberate and must
survive: it receives **only** the chapter's packet. That is enough — the
allocation is *in* the packet, and the items are already concrete, so the
map-maker needs neither the reservoir nor another chapter. Do not add the
reservoir to its inputs.

The `drafter` does read the setting pack directory directly, so `reservoir.md`
reaches it with no plumbing; its Inputs list should name it so the drafter knows
what it is looking at and what its relationship to the allocation is.

`chapter-cutter` must be told **not** to invent Texture lines — they are added
later, by a pass that sees the reservoir and every chapter at once.

- [ ] **Step 1: Write the failing contract tests**

Append to `tests/test_texture_allocation_docs.py`:

```python
MAP_MAKER = Path("agents/map-maker.md")
DRAFTER = Path("agents/drafter.md")
CUTTER = Path("agents/chapter-cutter.md")
PLOT_BOOK = Path("commands/plot-book.md")
MAP_CHAPTER = Path("commands/map-chapter.md")


def test_map_maker_distributes_texture_without_gaining_a_gate():
    t = MAP_MAKER.read_text(encoding="utf-8")
    assert "### Texture" in t
    assert "`Texture:`" in t
    assert "resource, not an obligation" in t
    assert "unscheduled-texture" not in t


def test_map_maker_stays_isolated_to_the_packet():
    # The allocation is in the packet; the reservoir must NOT be added here.
    t = MAP_MAKER.read_text(encoding="utf-8")
    assert "reservoir.md" not in t


def test_drafter_names_the_reservoir_and_the_texture_section():
    t = DRAFTER.read_text(encoding="utf-8")
    assert "config/setting-pack/reservoir.md" in t
    assert "### Texture" in t


def test_chapter_cutter_does_not_author_texture_lines():
    t = CUTTER.read_text(encoding="utf-8")
    assert "/allocate-texture" in t


def test_plot_book_points_at_the_allocation_between_the_plan_and_the_cut():
    t = PLOT_BOOK.read_text(encoding="utf-8")
    assert "/allocate-texture" in t
    assert t.index("/allocate-texture") < t.index("Stage readback")


def test_map_chapter_tells_the_map_maker_about_texture():
    assert "Texture:" in MAP_CHAPTER.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_texture_allocation_docs.py -v`
Expected: FAIL on the six new tests.

- [ ] **Step 3: Update `agents/map-maker.md`**

In the **Inputs** bullet listing the packet's sections, add `### Texture` to the
parenthesised list of outline-block sections. Then add this bullet to
**How to stage the chapter**, directly after the "Plant every ledger clue"
bullet:

```markdown
- **Distribute the chapter's `### Texture` allocation across the scenes, in a
  `Texture:` field.** The packet's Texture section is what this chapter *may*
  spend — concrete sensory material allocated to it, once, by a pass that saw
  every chapter at once so that no image is spent twice. Put each item in the
  scene where it belongs: a location image goes in the scene set there, a motif
  return goes in the scene it means something in. Write the field like `Clue:` —
  the field name on its own line, then the guidance beneath it.
- **Texture is a resource, not an obligation.** Nothing checks it: `map_check.py`
  has no `unscheduled-texture` and never will. A chapter that spends three of its
  four allocated items is correct, not short — so place what the scenes actually
  want and leave the rest. Never invent sensory material the allocation does not
  carry; a gap belongs in your proposal as a note, not on the page as a new fact
  about the town. A chapter with no `### Texture` section was allocated nothing
  and needs no `Texture:` field anywhere.
```

- [ ] **Step 4: Update `agents/drafter.md`**

In the **map** input bullet, add `Texture` to the open-vocabulary field list
(`Desire / Pressure / Action / Turn / Result / Clue / Texture / …`).

In the **packet** input bullet, extend the sentence that lists `### Setting`,
`### Opening` and `### Closing` to also name `### Texture`, then add after it:

```markdown
  `### Texture` is what this chapter **may** spend: concrete sensory material
  allocated to it once, across the whole book, so that no image is spent twice.
  It is a resource, not a checklist — nothing verifies it reached the page, and
  a chapter that spends most of it is correct. Where the map assigns items to
  scenes in a `Texture:` field, follow the map.
```

In the inputs bullet naming the setting pack, extend it:

```markdown
- `config/voice-pack/voice-pack.md`, the active series' setting pack under
  `config/setting-pack/` — including `config/setting-pack/reservoir.md`, this
  town's concrete sensory inventory, which is where your chapter's `### Texture`
  allocation was drawn from — the active genre prose pack under
  `config/genre-pack/`, and `config/length-profile.md`.
```

And add to the drafting instructions, near the guardrail instructions:

```markdown
**Do not invent facts about the town to fill a thin chapter.** If the texture you
need is not in the allocation, the reservoir or the setting pack, write the
chapter without it and note the gap — an invented one ("the kiln was tested a
fortnight ago by an electrician who charged her properly for it") reads fine and
breaks later chapters that depended on the opposite.
```

- [ ] **Step 5: Update `agents/chapter-cutter.md`**

In **Output format — exactly this**, add a line beneath the `Compress:` line:

```markdown
- **Texture:** — you do NOT write this field. See below.
```

and add a short section after **The compress line**:

```markdown
## The texture line you do not write

`cut-plan.md` also carries a `- **Texture:**` block — what each chapter *may*
spend in concrete sensory material, the positive half of your compress line.
**It is not yours.** It is authored later by `/allocate-texture`, in one pass
that reads the town's reservoir and every chapter of your approved plan at once,
so that no image is spent twice. You see one book's structure; that pass sees
one book's supply. Propose no Texture lines, and do not treat their absence as
something missing from your plan.
```

- [ ] **Step 6: Update `commands/plot-book.md`**

At the end of step 8 (stage cut), after the paragraph about moving a chapter
boundary, add:

```markdown
   **Then allocate texture, before you read back.** With the plan approved and
   the cut clean, run `/allocate-texture $book` — one whole-book pass deciding
   what each chapter may spend in concrete sensory material, so no image is
   spent twice and no chapter is left asking the drafter to improvise the town
   (spec `2026-08-27-texture-allocation-design.md` §4.2). It edits
   `cut-plan.md` and re-cuts, which is why it belongs here: before the lock, so
   nothing has to be re-minted. It is optional — a book with no allocation cuts
   and locks exactly as before — but it is far cheaper here than after.
```

- [ ] **Step 7: Update `commands/map-chapter.md`**

In step 3, extend the sentence describing what the map-maker proposes:

```markdown
   ... and every ledger clue id placed in exactly one scene's `Clue:` field. When
   the packet carries a `### Texture` section, it also distributes that
   allocation across the scenes in a `Texture:` field — a resource the chapter
   may spend, never an obligation, so `map_check.py` has no finding for it.
```

- [ ] **Step 8: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_texture_allocation_docs.py tests/test_plot_book_command.py tests/test_map_chapter_command.py tests/test_plot_agents.py -v`
Expected: PASS.

- [ ] **Step 9: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add agents/map-maker.md agents/drafter.md agents/chapter-cutter.md \
        commands/plot-book.md commands/map-chapter.md \
        tests/test_texture_allocation_docs.py
git commit -m "agents+runbooks: distribute and render the texture allocation"
```

---

## Task 9: Documentation — CLAUDE.md and README.md

**Files:**
- Modify: `CLAUDE.md`, `README.md`
- Test: `tests/test_texture_allocation_docs.py`

**Interfaces:**
- Consumes: everything from Tasks 1–8.
- Produces: nothing downstream.

**Context an implementer needs.** Both docs are pinned by tests
(`test_claude_md_check_count.py`, `test_readme_check_count.py`) precisely
because they have drifted before. Neither finding count changes here, but three
prose claims do: the background layer now has a second derived target, the
source layer now has a `Texture:` field, and the pipeline has a new command.
CLAUDE.md's test count (`full suite (1115 tests)`) must be updated to whatever
`python3 -m pytest` now reports.

- [ ] **Step 1: Write the failing doc test**

Append to `tests/test_texture_allocation_docs.py`:

```python
CLAUDE_MD = Path("CLAUDE.md")
README = Path("README.md")


def test_claude_md_documents_the_texture_layer():
    t = CLAUDE_MD.read_text(encoding="utf-8")
    for phrase in ("config/setting-pack/reservoir.md", "/allocate-texture",
                   "texture_apply.py", "### Texture",
                   "resource, not an obligation"):
        assert phrase in t, phrase


def test_claude_md_still_claims_twenty_three_story_cut_findings():
    # The texture layer adds no finding. If this fails, one was added.
    assert "twenty-three findings" in CLAUDE_MD.read_text(encoding="utf-8")


def test_readme_documents_the_reservoir_and_the_allocation():
    t = README.read_text(encoding="utf-8")
    for phrase in ("config/setting-pack/reservoir.md", "/allocate-texture"):
        assert phrase in t, phrase


def test_claude_md_test_count_matches_the_suite():
    import re
    import subprocess
    t = CLAUDE_MD.read_text(encoding="utf-8")
    claimed = int(re.search(r"full suite \((\d+) tests\)", t).group(1))
    out = subprocess.run(["python3", "-m", "pytest", "--collect-only", "-q"],
                         capture_output=True, text=True).stdout
    actual = int(re.search(r"(\d+) tests? collected", out).group(1))
    assert claimed == actual, f"CLAUDE.md says {claimed}, suite has {actual}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_texture_allocation_docs.py -k "claude_md or readme" -v`
Expected: FAIL — the phrases are absent and the count is stale.

- [ ] **Step 3: Update CLAUDE.md — the background layer paragraph**

In the paragraph beginning "**The background layer**", change the sentence
naming what `background_cut.py` writes so it names both derived targets, and add
the reservoir sentence:

```markdown
`input/series/background-history.md` is one authored, series-level document — town
history, character histories, relationships, secrets — that `scripts/background_cut.py`
cuts into a flat `series/continuity/background/`, the derived
`config/setting-pack/setting.md`, and the derived
`config/setting-pack/reservoir.md`. The `## Stance` and `## Reservoir` blocks are
**authored, not compressed**, and are the two parts carried into a derived file
verbatim — including their own `###` group headings, which in a catalogue are
content rather than entry names. The reservoir (spec
`2026-08-27-texture-allocation-design.md` §4.1) is the town's concrete sensory
inventory — what the bakery smells like at 6am versus 3pm, what the wind does to
the shed roof at three strengths — and it is optional: a source with no
`## Reservoir` writes no file and reports nothing. It is excluded from
`lmstudio_draft_chapter`'s pack concatenation on purpose, since it would consume
the whole 2,500-char setting-pack budget and truncate away the stance.
```

- [ ] **Step 4: Update CLAUDE.md — the source layer and the pipeline**

In the source-layer section, after the paragraph describing `cut-plan.md`'s
`Setting:`/`Opening:`/`Closing (<kind>):` fields, add:

```markdown
**What a chapter may SPEND in sensory texture is a cut-level decision too** (spec
`docs/superpowers/specs/2026-08-27-texture-allocation-design.md`). `cut-plan.md`
carries a nested `- **Texture:**` block beside `Compress:` — the positive half of
a line already written, since every compress line says what a chapter must *not*
render and nothing said what it *does* — and the cut emits `### Texture` into the
chapter block, from which `packet_assemble` carries it into the packet with no
code of its own. `/allocate-texture NN` authors it: the `texture-allocator`
proposes the whole book at once (so no image is spent twice, which is
construction rather than accounting), the showrunner approves it to
`input/book-NN/plot/texture.md`, and `scripts/texture_apply.py` splices it into
the cut plan idempotently, refusing `unknown-chapter` when a boundary has moved
since. Texture is a **resource, not an obligation**: `map_check.py` gains no
finding, there is no `unscheduled-texture`, and a chapter that spends three of
four allocated images is correct, not short — an obligation would put images into
competition with beats and clues for the genre beat sheet's
`obligations.max_per_chapter` budget. It adds no `story_cut.py` finding either:
a texture item shaped like a wiring field is refused by the existing
`wiring-shaped-directive`, so the roster stays at twenty-three.
```

In the **The pipeline** section, add `/allocate-texture NN` to the per-book list,
after the three front doors:

```markdown
- `/allocate-texture NN` — optional, after the cut plan is approved and before
  the lock. Allocates the book's sensory texture across every chapter at once.
  Run after the lock and the lock must be re-minted (`cut-plan.md` is one of the
  two files whose edit invalidates it), which is why the plot workshop calls it
  before `readback`.
```

- [ ] **Step 5: Update CLAUDE.md — the test count**

Run `python3 -m pytest --collect-only -q | tail -3`, read the collected count,
and replace `full suite (1115 tests)` with the new number.

- [ ] **Step 6: Update README.md**

Three edits:

1. In the derived-tree diagram under "The background layer", add the second
   derived target beside `config/setting-pack/setting.md`:

```
    └─────────────────────────► config/setting-pack/setting.md      loaded every chapter
    └─────────────────────────► config/setting-pack/reservoir.md    the texture reservoir
```

2. In the same section's prose (the "Eight blocking" paragraph near the end of
   the file), add a sentence: the reservoir is optional, is carried verbatim
   including its group headings, and is excluded from the LM Studio pack digest.

3. In the consumers table row for the setting pack, add `/allocate-texture` and
   `texture-allocator` as consumers of `config/setting-pack/reservoir.md`, and
   add a line to the commands list documenting `/allocate-texture <book>`.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_texture_allocation_docs.py tests/test_claude_md_check_count.py tests/test_readme_check_count.py -v`
Expected: PASS.

- [ ] **Step 8: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS. If the collected count changed since Step 5, update CLAUDE.md
again and re-run.

- [ ] **Step 9: Commit**

```bash
git add CLAUDE.md README.md tests/test_texture_allocation_docs.py
git commit -m "docs: record the reservoir, the Texture allocation, and /allocate-texture"
```

---

## Out of scope — do not build

- **§4.3, the punch-up pass.** `/punch-up`, its agent, the 15% word overrun, the
  protected-text manifest, the re-gating of `inspector-continuity`. Whether it is
  needed at all is an open question (spec §7.3) that only becomes answerable once
  chapters have been drafted against an allocation. Planning it now would presume
  the answer.
- **Authoring the reservoir's 150–250 items.** That is showrunner material for
  the series repo (`~/myBooks/series-pelicanscrook/`), not engine work — and spec
  §7.1 recommends building 30 items for one location and drafting a chapter
  against them before committing to a taxonomy.
- **The stale-protagonist lint** in the spec's appendix ("Cora" surviving in six
  engine files). Recorded there so it is not lost; explicitly "not part of this
  design".
