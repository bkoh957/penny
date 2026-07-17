# Packet / Map Chapter Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the scene-breakdown outline + brief compiler with the packet/map pipeline: packet-format chapter blocks in the outline, deterministic packet assembly, showrunner-approved prose maps, and named map checks — per spec `docs/superpowers/specs/2026-07-18-packet-map-chapter-design.md`.

**Architecture:** Three artifacts per chapter — outline block (authored, locked) → packet (`packet_assemble.py`, deterministic slice+lookups) → prose map (`map-maker` proposes, showrunner approves, `map_check.py` validates). `tension_check`'s `overloaded-chapter` re-bases from scene weights onto Required Beats. `brief_render.py` and the weigh-before-lock seam are deleted; ledger functions relocate to `penny_whodunit.py` first.

**Tech Stack:** Python 3 stdlib + PyYAML (whodunit/beat-sheet only), pytest, Claude Code plugin runbooks (markdown).

## Global Constraints

- Scripts NEVER make an LLM judgment; every gate fails loud with a named predicate and nonzero exit (CLAUDE.md, three-layer architecture).
- PyYAML ONLY for whodunit ledgers / lexicon / outline-feedback / beat sheets; config + frontmatter go through `penny_meta` (dependency-split rule).
- Engine is genre/location-agnostic: no series content, no hardcoded genre filenames in `scripts/`.
- Runbooks reference scripts as `${CLAUDE_PLUGIN_ROOT}/scripts/...`.
- Data paths resolve against the series root (`penny_paths`), never the plugin root.
- A check that cannot run is a NAMED note, never silence, never a traceback.
- Full suite: `python3 -m pytest` (pytest.ini sets `pythonpath=.`; imports are `from scripts.X import ...`).
- New scripts start with the repo's standard preamble:
  ```python
  from __future__ import annotations
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
  ```
- Commit after every task; end commit messages with the session trailer:
  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_019n5PzM6seZVddFofpR3pZw
  ```

---

### Task 1: Packet-format block parsing in `penny_wiring`

**Files:**
- Modify: `scripts/penny_wiring.py`
- Create: `tests/fixtures/outlines/packet-format.md`
- Test: `tests/test_penny_wiring.py` (append)

**Interfaces:**
- Consumes: existing `parse_wired_chapters(text) -> list[dict]`, `HEADING_RE`, `CHAPTER_RE`.
- Produces (later tasks rely on these exact names):
  - `parse_packet_sections(block: str) -> dict[str, str]` — H3 heading text → body text.
  - Every chapter dict from `parse_wired_chapters` gains two keys: `"sections": dict[str, str]` and `"required_beats": list[str]`.
  - `chapter_block(text: str, num: int) -> str` — the raw `## Chapter NN` block (moved from `brief_render._chapter_block`; same behavior: from the end of the chapter heading to the next `##` heading or EOF, stripped).

- [ ] **Step 1: Write the canonical fixture** — the spec §3 chapter block, verbatim, as `tests/fixtures/outlines/packet-format.md`:

```markdown
---
book: 1
total_chapters: 40
---

# Book One — Packet-Format Fixture

## Chapter 05 — Opening Day [type: event]

### Chapter Purpose
Maggie's open-studio afternoon succeeds commercially but tempts her to use
the Too-Much for public approval. She makes one survivable ethical mistake.
The chapter ends when news arrives that Neil is dead.

### Starting State
- The Wheelhouse is ready for its first open-studio event.
- Neil is alive at the beginning of the chapter.

### Ending State
- The Wheelhouse has made real sales.
- Mary's domestic-order habit has been planted inconspicuously.
- Neil has been found dead.

### Reader-Facing Shape
Primary anchor:
- The open-studio social set-piece.

Compress:
- Setup and pack-down.

### Required Beats
- Stronger pottery is finally displayed.
- Faye brings food.
- Iris's duplicate jam creates visible social geography.
- Maggie makes one accurate joke that earns a laugh.
- Faye warns her with a look.
- Maggie stops before revealing the deeper private wound.
- Mary helps with cups, plates and a tea towel.
- Cal notices Maggie has not eaten.
- Neil appears alive and concerned near closing.
- Faye receives the death call.

### Clues and Plants
- Mary restores cups, plates and towels to their places.
- The behaviour must appear ordinary and helpful.

### Character Knowledge
Maggie knows:
- Neil bought her ugly vase.

Maggie does not know:
- Mary will kill Neil.

### Guardrails
- Do not villain-signal Mary.
- Do not ominously foreshadow Neil's death.

- **Because:** ch 04 — opening day gathers the full cast the investigation will need.
- **Opens:** q-neil-death — who killed Neil?
- **Closes:** q-opening-ready
- **M:** the death arrives; the mystery begins.
- **R:** Cal notices Maggie's overload.
- **Hook:** q-neil-death — [cliffhanger] Faye receives the death call.

## Chapter 06 — The Morning After [type: standard]

### Chapter Purpose
The town rearranges itself around the death.

### Required Beats
- Maggie hears the official version of Neil's death.

### Guardrails
- Keep Maggie sympathetic.

- **Because:** ch 05 — the death call ends opening day.
- **Carries:** q-neil-death
- **Hook:** q-neil-death — [promise] the sergeant asks for Maggie's help.
```

- [ ] **Step 2: Write the failing tests** — append to `tests/test_penny_wiring.py`:

```python
from pathlib import Path

from scripts.penny_wiring import (chapter_block, parse_packet_sections,
                                  parse_wired_chapters)

PACKET_FIXTURE = Path("tests/fixtures/outlines/packet-format.md")


def test_parse_packet_sections_maps_h3_headings_to_bodies():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    block = chapter_block(text, 5)
    sections = parse_packet_sections(block)
    assert "Chapter Purpose" in sections
    assert "tempts her to use" in sections["Chapter Purpose"]
    assert "Required Beats" in sections
    assert "Guardrails" in sections
    # A section body stops at the next H3 heading
    assert "Faye brings food" not in sections["Chapter Purpose"]


def test_parse_wired_chapters_extracts_required_beats_in_order():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    ch5 = next(c for c in chapters if c["num"] == 5)
    assert len(ch5["required_beats"]) == 10
    assert ch5["required_beats"][0] == "Stronger pottery is finally displayed."
    assert ch5["required_beats"][9] == "Faye receives the death call."
    ch6 = next(c for c in chapters if c["num"] == 6)
    assert ch6["required_beats"] == [
        "Maggie hears the official version of Neil's death."]


def test_packet_format_block_keeps_wiring_and_type_flag():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    ch5 = next(c for c in chapters if c["num"] == 5)
    assert ch5["chapter_type"] == "event"
    assert ch5["because_ch"] == 4
    assert [q for q, _ in ch5["opens"]] == ["q-neil-death"]
    assert ch5["hook_grade"] == "cliffhanger"
    assert ch5["tracks"]["M"].startswith("the death arrives")
    # Packet blocks have no ### Scene sections — the scene list is empty
    assert ch5["scenes"] == []


def test_chapter_with_no_sections_has_empty_dict_and_beats():
    chapters = parse_wired_chapters("## Chapter 01 — Bare\n\nSome prose.\n")
    assert chapters[0]["sections"] == {}
    assert chapters[0]["required_beats"] == []


def test_chapter_block_returns_raw_block():
    text = PACKET_FIXTURE.read_text(encoding="utf-8")
    block = chapter_block(text, 6)
    assert block.startswith("### Chapter Purpose")
    assert "sergeant asks" in block
    assert "Opening Day" not in block
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_wiring.py -k "packet or chapter_block or required_beats or no_sections" -v`
Expected: FAIL — `ImportError: cannot import name 'chapter_block'`

- [ ] **Step 4: Implement** — in `scripts/penny_wiring.py`, add after `ANY_H3_RE` (reusing it) and before `parse_scenes`:

```python
H3_HEADING_RE = re.compile(r"^###\s+(.*?)\s*$", re.MULTILINE)
BULLET_RE = re.compile(r"^\s*-\s+(.*\S)\s*$")


def chapter_block(text: str, num: int) -> str:
    """The raw `## Chapter NN` block — heading end to the next `##` or EOF."""
    matches = list(HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        cm = CHAPTER_RE.match(m.group(1))
        if cm and int(cm.group(1)) == num:
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            return text[start:end].strip()
    return ""


def parse_packet_sections(block: str) -> dict[str, str]:
    """Packet-format `###` sections of one chapter block: heading -> body text.

    The packet-format block (spec 2026-07-18 §3) carries its authored content in
    named H3 sections (Chapter Purpose, Required Beats, Guardrails, ...). A
    `### Scene N` heading is NOT a packet section — scenes are the legacy format
    and parse_scenes owns them; both parsers reading one block must not fight.
    """
    sections: dict[str, str] = {}
    marks = [m for m in H3_HEADING_RE.finditer(block)
             if not SCENE_RE.match(m.group(0))]
    all_heads = sorted(m.start() for m in H3_HEADING_RE.finditer(block))
    for m in marks:
        start = m.end()
        end = len(block)
        for hs in all_heads:
            if hs > m.start():
                end = hs
                break
        sections[m.group(1)] = block[start:end].strip()
    return sections


def parse_required_beats(sections: dict[str, str]) -> list[str]:
    """The Required Beats list, in authored order. One line per beat — the
    1-based index into this list is the id a map's `Beats covered:` line uses,
    so ORDER IS CONTRACT: never sort, never dedupe."""
    body = sections.get("Required Beats", "")
    return [bm.group(1) for line in body.splitlines()
            if (bm := BULLET_RE.match(line))]
```

Then in `parse_wired_chapters`, extend the chapter dict construction — replace the line `"scenes": parse_scenes(block), "first_line": None, "hook_grade": None,` with:

```python
              "scenes": parse_scenes(block), "first_line": None, "hook_grade": None,
              "sections": (sections := parse_packet_sections(block)),
              "required_beats": parse_required_beats(sections),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_wiring.py -v`
Expected: all PASS (new and pre-existing).

- [ ] **Step 6: Full-suite sanity + commit**

Run: `python3 -m pytest -q` — expected: all pass (the new keys are additive).

```bash
git add scripts/penny_wiring.py tests/test_penny_wiring.py tests/fixtures/outlines/packet-format.md
git commit -m "feat(wiring): parse packet-format chapter blocks (sections + Required Beats)"
```

---

### Task 2: Relocate whodunit-ledger functions to `penny_whodunit.py`

**Files:**
- Create: `scripts/penny_whodunit.py`
- Modify: `scripts/brief_render.py` (delegate), `scripts/preflight.py:143`, `scripts/tension_check.py:213`
- Test: `tests/test_penny_whodunit.py` (new)

**Interfaces:**
- Consumes: current `brief_render.load_ledger`, `clues_by_chapter`, `_plant_chapter`, `_validate_entry_list`, `_ledger_identity`, `_sha`.
- Produces (exact public API later tasks import):
  - `penny_whodunit.load_ledger(path) -> dict` — identical behavior/messages to today's.
  - `penny_whodunit.clues_by_chapter(path) -> dict[int, list[str]]`
  - `penny_whodunit.ledger_identity(path) -> str` (public name for `_ledger_identity`: sha256 hex, or `"none"` for an absent/unreadable ledger — preserve the current sentinel exactly as `stale_briefs` uses it)
  - `penny_whodunit.file_sha256(path) -> str`

- [ ] **Step 1: Write the failing test** — `tests/test_penny_whodunit.py`. Port the ledger-shape assertions from `tests/test_brief_render.py` (read that file first; reuse its fixture ledger paths under `tests/fixtures/ledgers/` or its tmp-tree builders verbatim), plus:

```python
from scripts import penny_whodunit


def test_public_api_exists():
    for name in ("load_ledger", "clues_by_chapter", "ledger_identity",
                 "file_sha256"):
        assert callable(getattr(penny_whodunit, name))


def test_ledger_identity_absent_file_is_none_sentinel(tmp_path):
    assert penny_whodunit.ledger_identity(tmp_path / "missing.yaml") == "none"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_penny_whodunit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_whodunit'`

- [ ] **Step 3: Implement** — cut `load_ledger`, `_validate_entry_list`, `_plant_chapter`, `clues_by_chapter`, `_ledger_identity`, `_sha` out of `scripts/brief_render.py` and paste them into new `scripts/penny_whodunit.py` (standard preamble; module docstring: "Whodunit-ledger loading and identity — the ONE guarded entry point (PyYAML is allowed here: the ledger is genuinely nested human-edited data)."). Rename `_ledger_identity` → `ledger_identity` and `_sha` → `file_sha256` at the definition. In `brief_render.py`, replace the removed bodies with imports so its own callers keep working until Task 9 deletes it:

```python
from scripts.penny_whodunit import (clues_by_chapter, file_sha256 as _sha,
                                    ledger_identity as _ledger_identity,
                                    load_ledger)
```

Update the two external import sites:
- `scripts/preflight.py` line ~143: `from scripts.brief_render import load_ledger, stale_briefs` → `from scripts.brief_render import stale_briefs` and `from scripts.penny_whodunit import load_ledger`.
- `scripts/tension_check.py` line ~213: `from scripts.brief_render import clues_by_chapter` → `from scripts.penny_whodunit import clues_by_chapter`.

- [ ] **Step 4: Run the full suite**

Run: `python3 -m pytest -q`
Expected: all pass — this is a pure relocation.

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_whodunit.py scripts/brief_render.py scripts/preflight.py scripts/tension_check.py tests/test_penny_whodunit.py
git commit -m "refactor: relocate whodunit-ledger functions to penny_whodunit"
```

---

### Task 3: `penny_length` v2 — authored-target validation, `min_scene_words`

**Files:**
- Modify: `scripts/penny_length.py`
- Test: `tests/test_penny_length.py` (append)

**Interfaces:**
- Consumes: `parse_profile`, `band_for` (unchanged).
- Produces:
  - `parse_profile` result gains `"min_scene_words": int | None` (from a `min_scene_words:` key; `None` when absent). Legacy `weight_*` / `min_<class>_words` keys still parse into `weights`/`floors` untouched — tolerated, ignored by new code.
  - `validate_targets(profile: dict, band: tuple[int, int], scenes: list[dict]) -> dict` with keys `"blocking": list[str]`, `"notes": list[str]`. Each scene dict needs `"num"`, `"title"`, `"target": tuple[int, int] | None`. Finding vocabulary (exact prefixes, used verbatim by `map_check`): `band-mismatch`, `starved-scene`, `unparseable-target`.
  - `SCHEMA_HINT` rewritten for schema v2.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_penny_length.py`:

```python
from scripts.penny_length import parse_profile, validate_targets

V2_PROFILE = """
```yaml
band_default: [2000, 2500]
band_event: [2800, 3600]
min_scene_words: 250
```
"""


def _scenes(*targets):
    return [{"num": i + 1, "title": f"S{i + 1}", "target": t}
            for i, t in enumerate(targets)]


def test_parse_profile_reads_min_scene_words():
    p = parse_profile(V2_PROFILE)
    assert p["min_scene_words"] == 250


def test_parse_profile_min_scene_words_absent_is_none():
    p = parse_profile("```yaml\nband_default: [2000, 2500]\n```")
    assert p["min_scene_words"] is None


def test_validate_targets_clean_map_passes():
    p = parse_profile(V2_PROFILE)
    out = validate_targets(p, (2800, 3600),
                           _scenes((350, 450), (900, 1100), (700, 850),
                                   (400, 550), (500, 650)))
    assert out["blocking"] == []


def test_validate_targets_band_mismatch_when_sum_cannot_reach_band():
    p = parse_profile(V2_PROFILE)
    out = validate_targets(p, (2800, 3600), _scenes((300, 400), (300, 400)))
    assert any(b.startswith("band-mismatch") for b in out["blocking"])


def test_validate_targets_band_mismatch_when_sum_overshoots_band():
    p = parse_profile(V2_PROFILE)
    out = validate_targets(p, (2000, 2500), _scenes((2600, 3000)))
    assert any(b.startswith("band-mismatch") for b in out["blocking"])


def test_validate_targets_starved_scene_below_floor():
    p = parse_profile(V2_PROFILE)
    out = validate_targets(p, (2000, 2500), _scenes((100, 200), (1900, 2300)))
    assert any(b.startswith("starved-scene") and "S1" in b
               for b in out["blocking"])


def test_validate_targets_missing_floor_is_named_note_not_silence():
    p = parse_profile("```yaml\nband_default: [2000, 2500]\n```")
    out = validate_targets(p, (2000, 2500), _scenes((100, 2400)))
    assert out["blocking"] == []
    assert any("min_scene_words" in n for n in out["notes"])


def test_validate_targets_unparseable_target_is_blocking():
    p = parse_profile(V2_PROFILE)
    out = validate_targets(p, (2000, 2500), _scenes(None, (2000, 2400)))
    assert any(b.startswith("unparseable-target") for b in out["blocking"])
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_penny_length.py -k "min_scene or validate_targets" -v`
Expected: FAIL — `KeyError: 'min_scene_words'` / `ImportError: cannot import name 'validate_targets'`

- [ ] **Step 3: Implement** — in `scripts/penny_length.py`: in `parse_profile`'s return, add `"min_scene_words": floors.get("scene")` (the existing `_FLOOR_RE` already lands `min_scene_words:` in `floors["scene"]`). Replace `SCHEMA_HINT` with:

```python
SCHEMA_HINT = (
    "a length-profile needs band_default: [min, max] (plus any band_<type> "
    "overrides selected by a chapter title's [type: ...] flag) and a "
    "min_scene_words floor for the prose map's scenes — see README.md, 'The "
    "length profile'. (Legacy weight_<class> / min_<class>_words keys are "
    "tolerated and ignored.)"
)
```

Append after `scene_budgets` (which Task 9 deletes):

```python
def validate_targets(profile: dict, band: tuple[int, int],
                     scenes: list[dict]) -> dict:
    """Validate a prose map's AUTHORED per-scene targets against the band.

    The redesign flips this module from generator to validator: the map-maker
    proposes targets and the showrunner approves them; the engine's only
    opinion is whether the numbers add up (spec 2026-07-18 §6).
    """
    blocking: list[str] = []
    notes: list[str] = []
    parseable = [s for s in scenes if s.get("target")]
    for s in scenes:
        if not s.get("target"):
            blocking.append(
                f"unparseable-target: scene {s['num']} '{s['title']}' has no "
                f"parseable `Target: A–B words` line — every scene must be priced")
    if parseable:
        lo = sum(s["target"][0] for s in parseable)
        hi = sum(s["target"][1] for s in parseable)
        if lo > band[1] or hi < band[0]:
            blocking.append(
                f"band-mismatch: scene targets sum to {lo}–{hi} words against a "
                f"chapter band of {band[0]}–{band[1]} — the map and the length "
                f"profile disagree about the chapter's size")
    floor = profile.get("min_scene_words")
    if floor is None:
        notes.append(
            "starved-scene — the floor check could not run: the length profile "
            "declares no min_scene_words (schema v2); no scene can be called starved")
    else:
        for s in parseable:
            if s["target"][1] < floor:
                blocking.append(
                    f"starved-scene: scene {s['num']} '{s['title']}' tops out at "
                    f"{s['target'][1]} words against the profile's {floor}-word "
                    f"min_scene_words floor — a scene priced this low is a beat, "
                    f"not a scene; fold it into a neighbour or cut it")
    return {"blocking": blocking, "notes": notes}
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_penny_length.py -v` then `python3 -m pytest -q`
Expected: all PASS (legacy keys still parse; nothing else consumed `SCHEMA_HINT`'s wording except error paths asserted on `band_default`, which is unchanged — if a suite failure names SCHEMA_HINT text, update that assertion to the new hint).

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_length.py tests/test_penny_length.py
git commit -m "feat(length): schema v2 — min_scene_words + authored-target validation"
```

---

### Task 4: `penny_map.py` — prose-map parser

**Files:**
- Create: `scripts/penny_map.py`
- Create: `tests/fixtures/maps/ch-05.md`
- Test: `tests/test_penny_map.py` (new)

**Interfaces:**
- Consumes: `penny_meta.parse_frontmatter`, `penny_paths.input_path`.
- Produces:
  - `map_path(book: str, chapter: str, repo_root=None) -> Path` → `input/book-<book>/maps/ch-<chapter>.md` (zero-padded like `brief_render.brief_path` — read that for the exact padding convention and mirror it).
  - `parse_map(text: str) -> dict`: `{"stamp": str | None, "scenes": [{"num": int, "title": str, "target": tuple[int,int] | None, "weight": str | None, "beats_covered": list[int], "clue_text": str | None}]}`. `stamp` is frontmatter `built_from_packet` (None when absent).
  - Regexes later tasks rely on: `Target: 350–450 words` (comma-grouped numbers allowed, en-dash or hyphen), `Beats covered: 2, 7`, a `Clue:` field whose body runs to the next field/heading.

- [ ] **Step 1: Write the fixture** — `tests/fixtures/maps/ch-05.md`: the spec §4 canonical map, verbatim, PLUS frontmatter and coverage lines (spec §4 note — the fixture version adds them). Frontmatter first:

```markdown
---
built_from_packet: 0000000000000000000000000000000000000000000000000000000000000000
---

# Chapter 5 Prose Map
```

Then the five scenes exactly as the spec, with these lines added: Scene 1 gains `Beats covered: 1, 2` after its `Weight:` line; Scene 2 gains `Beats covered: 7` and its `Clue:` body gains a trailing line `[whodunit: mary-domestic-order]`; Scene 3 gains `Beats covered: 3, 4, 5, 6`; Scene 4 gains `Beats covered: 8`; Scene 5 gains `Beats covered: 9, 10`.

- [ ] **Step 2: Write the failing tests** — `tests/test_penny_map.py`:

```python
from pathlib import Path

from scripts.penny_map import map_path, parse_map

FIXTURE = Path("tests/fixtures/maps/ch-05.md")


def test_parse_map_scenes_and_targets():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["stamp"] == "0" * 64
    assert [s["num"] for s in m["scenes"]] == [1, 2, 3, 4, 5]
    assert m["scenes"][0]["title"] == "Before the Door Opens"
    assert m["scenes"][0]["target"] == (350, 450)
    assert m["scenes"][1]["target"] == (900, 1100)  # comma-grouped "1,100"


def test_parse_map_weight_is_free_text():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["scenes"][2]["weight"] == "Primary emotional anchor"
    assert m["scenes"][4]["weight"] == "Secondary anchor and chapter hook"


def test_parse_map_beats_covered_and_clue():
    m = parse_map(FIXTURE.read_text(encoding="utf-8"))
    assert m["scenes"][0]["beats_covered"] == [1, 2]
    assert m["scenes"][2]["beats_covered"] == [3, 4, 5, 6]
    assert "mary-domestic-order" in m["scenes"][1]["clue_text"]
    assert m["scenes"][0]["clue_text"] is None


def test_parse_map_missing_target_is_none_not_crash():
    m = parse_map("## Scene 1 — Untargeted\nWeight: Support\n\nAction:\nX.\n")
    assert m["scenes"][0]["target"] is None
    assert m["scenes"][0]["beats_covered"] == []


def test_map_path_shape(tmp_path):
    p = map_path("01", "5", tmp_path)
    assert str(p).endswith("input/book-01/maps/ch-05.md")
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_penny_map.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement** — `scripts/penny_map.py`:

```python
"""Parser for the prose map (spec 2026-07-18 §4) — the Pass-1 artifact that
replaced the brief. The machine parses ONLY: `## Scene N — Title`, `Target:`,
`Weight:`, `Beats covered:`, and `Clue:`. Every other field name (Desire /
Pressure / Action / Turn / ...) is open vocabulary for the drafter, used
selectively, and deliberately not parsed. Dependency-free (penny_meta only).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.penny_meta import parse_frontmatter
from scripts.penny_paths import input_path

MAP_SCENE_RE = re.compile(r"^##\s+Scene\s+(\d+)(?:\s*[—-]\s*(.*))?\s*$",
                          re.MULTILINE)
TARGET_RE = re.compile(r"^Target:\s*([\d,]+)\s*[–—-]\s*([\d,]+)\s*words?\s*$",
                       re.MULTILINE | re.IGNORECASE)
WEIGHT_LINE_RE = re.compile(r"^Weight:\s*(.+?)\s*$", re.MULTILINE)
BEATS_COVERED_RE = re.compile(r"^Beats covered:\s*([\d,\s]+?)\s*$",
                              re.MULTILINE | re.IGNORECASE)
# A `Clue:` field body runs until the next `Word:`-shaped field line, the next
# scene heading, or EOF — clue guidance is often multi-line.
CLUE_FIELD_RE = re.compile(
    r"^Clue:\s*\n?(.*?)(?=^\w[\w '’-]*:\s*$|^\w[\w '’-]*:\s|\Z|^##\s)",
    re.MULTILINE | re.DOTALL)


def map_path(book: str, chapter: str, repo_root=None) -> Path:
    return input_path(
        f"book-{str(book).zfill(2)}/maps/ch-{str(chapter).zfill(2)}.md",
        repo_root)


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def parse_map(text: str) -> dict:
    fm = parse_frontmatter(text)
    stamp = fm.get("built_from_packet")
    scenes: list[dict] = []
    marks = list(MAP_SCENE_RE.finditer(text))
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[start:end]
        tm = TARGET_RE.search(body)
        wm = WEIGHT_LINE_RE.search(body)
        bm = BEATS_COVERED_RE.search(body)
        cm = CLUE_FIELD_RE.search(body)
        clue = cm.group(1).strip() if cm and cm.group(1).strip() else None
        scenes.append({
            "num": int(m.group(1)),
            "title": (m.group(2) or "").strip(),
            "target": (_int(tm.group(1)), _int(tm.group(2))) if tm else None,
            "weight": wm.group(1) if wm else None,
            "beats_covered": [int(x) for x in bm.group(1).replace(",", " ").split()]
                             if bm else [],
            "clue_text": clue,
        })
    return {"stamp": stamp if isinstance(stamp, str) else None, "scenes": scenes}
```

- [ ] **Step 5: Run tests; adjust CLUE_FIELD_RE only if the fixture shows a real miss** (the multi-line clue with the trailing `[whodunit: ...]` line must land in `clue_text`; "Turn:" must terminate it).

Run: `python3 -m pytest tests/test_penny_map.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_map.py tests/test_penny_map.py tests/fixtures/maps/ch-05.md
git commit -m "feat(map): prose-map parser — scenes, targets, coverage, clue fields"
```

---

### Task 5: `packet_assemble.py` — deterministic packet assembly

**Files:**
- Create: `scripts/packet_assemble.py`
- Test: `tests/test_packet_assemble.py` (new)

**Interfaces:**
- Consumes: `penny_wiring.chapter_block`, `penny_wiring.parse_wired_chapters`; `penny_whodunit.clues_by_chapter`, `penny_whodunit.ledger_identity`, `penny_whodunit.file_sha256`; `penny_meta.parse_canon_meta`; `penny_paths` (`input_path`, `series_path`, `config_path`, `penny_path`); `penny_length.parse_profile`, `band_for`.
- Produces:
  - `packet_path(book, chapter, repo_root=None) -> Path` → `input/book-NN/packets/ch-MM.md`.
  - `assemble(book: str, chapter: str, *, repo_root=None) -> Path` — writes the packet, returns its path; raises `SystemExit` via `_fail(named predicate)` on: no lock, no chapter block, no Required Beats section (an unmigrated chapter must fail by name, not produce an empty packet).
  - `stale_packets(book: str, repo_root=None) -> set[str]` — zero-padded chapter strings whose packet stamps mismatch the current outline sha / ledger identity (mirror `brief_render.stale_briefs` logic — read it before writing this).
  - CLI: `python3 scripts/packet_assemble.py <book> <chapter>`.
  - Packet file layout (exact, tested):

```
---
built_from_outline: <sha256 of input/book-NN/outline.md>
built_from_whodunit: <ledger_identity — sha256 or "none">
---

# Packet — Chapter NN

## Chapter NN — Title [type: ...]
<the outline block, verbatim, including wiring footer>

## Ledger Clues
- [<clue-id>] plant_chapter <N>: <clue prose from the ledger>   (one per clue; or `- None.`)

## Continuity Extracts
<canon-core.md body, then each matched entry file's body>       (or `- None.` + named note)

## Standing Series Guardrails
<config/series-guardrails.md body>                              (or the note: `- None — this series has no config/series-guardrails.md.`)

## Word Budget
Band: <lo>–<hi> words (type: <chapter_type or default>)
```

- **Continuity-slice rule (deterministic):** include `series/continuity/characters|locations|threads/*.md` entries whose filename stem OR canon-meta `id` appears (case-insensitive substring on word boundary) in the chapter block text; then one hop: any entry named in a matched entry's canon-meta `links`/`refs` list. `canon-core.md` is always included first.

- [ ] **Step 1: Write the failing tests** — `tests/test_packet_assemble.py`. Build a tmp series tree (mirror the builder style of `tests/test_brief_render.py` — read it first and reuse its helpers' shape): `.penny/locks/book-01.mystery.lock`, `input/book-01/outline.md` (copy of `tests/fixtures/outlines/packet-format.md`), a minimal `series/whodunit/book-01.yaml` with one clue whose `plant_chapter: 5` and id `mary-domestic-order` (copy an entry from an existing ledger fixture in `tests/fixtures/ledgers/` and adjust), `series/continuity/canon-core.md`, `series/continuity/characters/mary.md` with a canon-meta header whose `id` is `mary` and `links: [cal]`, `series/continuity/characters/cal.md`, `series/continuity/characters/saffron.md` (NOT named in ch 5), `config/length-profile.md` with the v2 yaml block from Task 3.

```python
def test_assemble_writes_stamped_packet(series_tree):
    p = packet_assemble.assemble("01", "05", repo_root=series_tree)
    text = p.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    assert len(fm["built_from_outline"]) == 64
    assert len(fm["built_from_whodunit"]) == 64
    assert "## Chapter 05 — Opening Day [type: event]" in text
    assert "### Required Beats" in text
    assert "- **Hook:**" in text                      # wiring footer rides along


def test_assemble_merges_ledger_clues(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "[mary-domestic-order]" in text


def test_assemble_slices_continuity_one_hop(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "canon-core" in text.lower()
    assert "mary" in text.lower()          # named in the block
    assert "cal" in text.lower()           # one hop from mary's links
    assert "saffron" not in text.lower()   # not named, not linked


def test_assemble_refuses_unlocked_book(series_tree):
    (series_tree / ".penny/locks/book-01.mystery.lock").unlink()
    with pytest.raises(SystemExit):
        packet_assemble.assemble("01", "05", repo_root=series_tree)


def test_assemble_refuses_chapter_without_required_beats(series_tree):
    with pytest.raises(SystemExit):
        packet_assemble.assemble("01", "07", repo_root=series_tree)


def test_missing_guardrails_file_is_named_note(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "no config/series-guardrails.md" in text


def test_stale_packets_flags_outline_edit(series_tree):
    packet_assemble.assemble("01", "05", repo_root=series_tree)
    assert packet_assemble.stale_packets("01", series_tree) == set()
    outline = series_tree / "input/book-01/outline.md"
    outline.write_text(outline.read_text(encoding="utf-8") + "\nedit\n",
                       encoding="utf-8")
    assert "05" in packet_assemble.stale_packets("01", series_tree)


def test_absent_ledger_is_stamped_none_and_late_ledger_goes_stale(series_tree):
    (series_tree / "series/whodunit/book-01.yaml").unlink()
    p = packet_assemble.assemble("01", "05", repo_root=series_tree)
    assert parse_frontmatter(p.read_text(encoding="utf-8"))["built_from_whodunit"] == "none"
```

(Note for the absent-ledger test: `assemble` still requires the LOCK file; only the yaml is removed, mirroring the brief contract's `none` stamping.)

- [ ] **Step 2: Run to verify failure** — `python3 -m pytest tests/test_packet_assemble.py -v` — FAIL: `ModuleNotFoundError`.

- [ ] **Step 3: Implement** `scripts/packet_assemble.py`. Skeleton (fill bodies exactly as specified above; `_fail` mirrors `preflight._fail` — print `PREDICATE FAILED: ...` to stderr, `raise SystemExit(1)`):

```python
"""Assemble a chapter's PACKET — spec 2026-07-18 §5. Deterministic: a slice
plus lookups, no LLM. The packet is the curation boundary: this chapter's
block, its ledger clues, its continuity slice, the standing guardrails, its
band — and nothing else."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import penny_length
from scripts.penny_meta import load, parse_canon_meta, parse_frontmatter
from scripts.penny_paths import config_path, input_path, penny_path, series_path
from scripts.penny_whodunit import (clues_by_chapter, file_sha256,
                                    ledger_identity, load_ledger)
from scripts.penny_wiring import chapter_block, parse_wired_chapters


def _fail(predicate: str):
    print(f"PREDICATE FAILED: {predicate}", file=sys.stderr)
    raise SystemExit(1)


def packet_path(book: str, chapter: str, repo_root=None) -> Path:
    return input_path(
        f"book-{str(book).zfill(2)}/packets/ch-{str(chapter).zfill(2)}.md",
        repo_root)
```

Key implementation points (each is a tested behavior, not a suggestion):
- Lock check: `penny_path(f"locks/book-{book2}.mystery.lock", repo_root).is_file()` else `_fail(f"book {book} has no mystery lock — packet assembly needs the sealed ledger's obligations; run preflight lock-mystery {book}")`.
- Block: `chapter_block(outline_text, int(chapter))`; empty → `_fail` naming the chapter. Re-attach the heading line: find it via `parse_wired_chapters` (`title`, `chapter_type`, `long_waiver`) or slice the original heading line from the outline text — simplest is to regex the original `^## Chapter NN...$` line out of the outline and prepend it verbatim.
- Required Beats guard: `parse_packet_sections(block)` lacking a non-empty "Required Beats" → `_fail(f"chapter {chapter} has no ### Required Beats section — this chapter is not in packet format; migrate the block (spec 2026-07-18 §3) before assembling a packet")`.
- Ledger clues: ledger absent → stamp `none`, section `- None.`; present → `load_ledger` (validation), then `clues_by_chapter(path).get(int(chapter), [])`, one bullet per id. For clue prose, read the ledger dict's clue entries (`load_ledger` returns the parsed yaml — reuse however `brief_render._obligations` walked clues; read that function first and mirror its field access).
- Continuity slice per the rule above; word-boundary matching: `re.search(rf"\b{re.escape(name)}\b", block, re.IGNORECASE)`.
- Guardrails: `config_path("series-guardrails.md", repo_root)`; missing → the exact note string from Step 1's test.
- Band: `penny_length.parse_profile` on `config_path("length-profile.md", ...)`; unparseable/missing profile → `Band: unknown — <named reason>` line, never a crash.
- `stale_packets`: for each `packets/ch-*.md`, compare `built_from_outline` to `file_sha256(outline)` and `built_from_whodunit` to `ledger_identity(ledger)`.
- CLI `main(argv)`: two args, calls `assemble`, prints the written path.

- [ ] **Step 4: Run tests** — `python3 -m pytest tests/test_packet_assemble.py -v` — PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/packet_assemble.py tests/test_packet_assemble.py
git commit -m "feat(packet): deterministic packet assembly with staleness stamps"
```

---

### Task 6: `map_check.py` — the named map findings

**Files:**
- Create: `scripts/map_check.py`
- Test: `tests/test_map_check.py` (new)

**Interfaces:**
- Consumes: `penny_map.parse_map`, `penny_map.map_path`; `penny_wiring.parse_wired_chapters` (run on the PACKET text — the packet contains the chapter block, so `required_beats` and `chapter_type` parse straight out of it); `penny_length.parse_profile`, `band_for`, `validate_targets`; `packet_assemble.packet_path`; a `PACKET_CLUE_RE = re.compile(r"^\s*-\s*\[([^\]]+)\]", re.MULTILINE)` for the packet's `## Ledger Clues` ids.
- Produces:
  - `check_map(packet_text: str, map_text: str, profile: dict | None) -> dict` → `{"blocking": list[str], "notes": list[str]}`. Finding prefixes (exact): `band-mismatch`, `starved-scene`, `unparseable-target` (all three straight from `penny_length.validate_targets`), `dropped-beat`, `duplicate-beat`, `unscheduled-clue`, `stale-map` (map stamp ≠ sha256 of packet text).
  - CLI: `python3 scripts/map_check.py <book> <chapter>` — loads packet, map, profile; prints findings/notes; exit 1 iff blocking, exit 2 on operational error (missing packet/map file, by name).

- [ ] **Step 1: Write the failing tests** — `tests/test_map_check.py`. Reuse the Task 4 map fixture and Task 1 outline fixture; build packet text inline in the test as: frontmatter + the ch-05 block + a `## Ledger Clues\n- [mary-domestic-order] plant_chapter 5: Mary restores order.\n` section:

```python
def _packet_text():
    outline = Path("tests/fixtures/outlines/packet-format.md").read_text(encoding="utf-8")
    from scripts.penny_wiring import chapter_block
    return ("# Packet — Chapter 05\n\n## Chapter 05 — Opening Day [type: event]\n"
            + chapter_block(outline, 5)
            + "\n\n## Ledger Clues\n- [mary-domestic-order] plant_chapter 5: Mary restores order.\n")


def _map_text(**edits):
    text = Path("tests/fixtures/maps/ch-05.md").read_text(encoding="utf-8")
    for old, new in edits.items():
        assert old in text
        text = text.replace(old, new)
    return text


def _profile():
    return parse_profile("```yaml\nband_default: [2000, 2500]\n"
                         "band_event: [2800, 3600]\nmin_scene_words: 250\n```")


def test_clean_canonical_pair_passes():
    out = check_map(_packet_text(), _map_text(), _profile())
    assert out["blocking"] == []


def test_dropped_beat_named():
    out = check_map(_packet_text(), _map_text(**{"Beats covered: 9, 10": "Beats covered: 9"}), _profile())
    assert any(b.startswith("dropped-beat") and "10" in b for b in out["blocking"])


def test_duplicate_beat_named():
    out = check_map(_packet_text(), _map_text(**{"Beats covered: 7": "Beats covered: 1, 7"}), _profile())
    assert any(b.startswith("duplicate-beat") for b in out["blocking"])


def test_unscheduled_clue_named():
    out = check_map(_packet_text(), _map_text(**{"[whodunit: mary-domestic-order]": ""}), _profile())
    assert any(b.startswith("unscheduled-clue") and "mary-domestic-order" in b
               for b in out["blocking"])


def test_no_profile_is_note_not_crash():
    out = check_map(_packet_text(), _map_text(), None)
    assert any("length profile" in n for n in out["notes"])
    # coverage checks still ran without a profile
    assert not any(b.startswith("dropped-beat") for b in out["blocking"])
```

- [ ] **Step 2: Run to verify failure** — `python3 -m pytest tests/test_map_check.py -v` — FAIL: `ModuleNotFoundError`.

- [ ] **Step 3: Implement** — coverage logic:

```python
beats = ch["required_beats"]                     # from parse_wired_chapters(packet_text)
claimed: dict[int, list[int]] = {}
for s in parsed_map["scenes"]:
    for idx in s["beats_covered"]:
        claimed.setdefault(idx, []).append(s["num"])
        if not 1 <= idx <= len(beats):
            blocking.append(f"dropped-beat: scene {s['num']} claims beat {idx} "
                            f"but the packet lists only {len(beats)} Required Beats")
for i, beat in enumerate(beats, 1):
    owners = claimed.get(i, [])
    if not owners:
        blocking.append(f"dropped-beat: Required Beat {i} '{beat}' lands in no "
                        f"scene's `Beats covered:` line — the map loses a moment "
                        f"the book breaks without")
    elif len(owners) > 1:
        blocking.append(f"duplicate-beat: Required Beat {i} '{beat}' is claimed by "
                        f"scenes {owners} — one beat, one home")
clue_ids = PACKET_CLUE_RE.findall(packet_text_after_ledger_heading)
all_clue_text = " ".join(s["clue_text"] or "" for s in parsed_map["scenes"])
for cid in clue_ids:
    if cid not in all_clue_text:
        blocking.append(f"unscheduled-clue: ledger clue [{cid}] appears in no "
                        f"scene's Clue: line — an unplanted clue is an unfair reveal")
```

Band/targets: `band_for(profile, ch["chapter_type"])` + `validate_targets(...)`, merging its blocking/notes. `profile is None` → note `"targets — the pricing checks could not run: no parseable length profile"`. Stale: `check_map` takes the raw packet text; CLI computes `hashlib.sha256(packet_bytes)` and compares to the map's `stamp` → `stale-map` blocking finding. Restrict `PACKET_CLUE_RE` to the text after the `## Ledger Clues` heading so authored `- [x]`-style lines elsewhere can't inject ids.

- [ ] **Step 4: Run tests** — PASS. Then full suite: `python3 -m pytest -q` — PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/map_check.py tests/test_map_check.py
git commit -m "feat(map-check): named findings — coverage, pricing, staleness"
```

---

### Task 7: Re-base `tension_check`'s `overloaded-chapter` onto Required Beats

**Files:**
- Modify: `scripts/tension_check.py` (`check_overload`, `_overload_check`, `_obligation_load`, `check_tension`, `main`)
- Modify: `scripts/preflight.py` (`cmd_lock_mystery` call site — grep `check_tension(` / `profile_path`)
- Test: `tests/test_tension_check.py` (modify overload tests)

**Interfaces:**
- Consumes: chapter dicts now carrying `required_beats`; `penny_whodunit.clues_by_chapter`.
- Produces: `check_overload(chapters, *, beat_sheet_path=None, whodunit_path=None) -> dict` — `profile_path` parameter REMOVED (grep for every caller: `check_tension`, `main`, `preflight.cmd_lock_mystery`, tests). Return shape: `{"applicable": bool, "blocking": [...], "notes": [...]}` (rename from `"weighted"`; update every consumer found by `grep -rn '"weighted"' scripts/ tests/`).

- [ ] **Step 1: Rewrite the overload tests** in `tests/test_tension_check.py`. Read the existing overload tests first; replace scene-weight-based ones with:

```python
def test_overload_fires_on_beat_heavy_chapter(...):
    # packet-format fixture chapter with 10 Required Beats + 1 clue + opens/closes/tracks,
    # beat sheet cap obligations.max_per_chapter: 12 -> load 10+1+2+2 = 15 > 12: blocking
def test_overload_skips_by_name_without_required_beats(...):
    # legacy outline (scenes, weights, no Required Beats sections):
    # applicable False, no blocking, and NO notes — the unmigrated shape is
    # skipped entirely, exactly as unweighted outlines were (stop-everything invariant)
def test_overload_counts_beats_plus_obligations(...):
    # cap 20 -> clean
def test_overload_missing_cap_is_named_note(...):
```

Count basis (exact): `len(ch["required_beats"]) + len(clues) + len(opens) + len(closes) + len(tracks advanced)` — extend `_obligation_load` with the beats term and its message part (`"10 required beat(s), 1 clue(s) to plant, ..."`).

- [ ] **Step 2: Run to verify the new tests fail** — `python3 -m pytest tests/test_tension_check.py -v` — new FAIL, legacy-scene tests still pass (delete the weight-specific ones in this task; they test machinery this task removes).

- [ ] **Step 3: Implement** — in `_overload_check`: delete the entire scene/floor/budget half (the `penny_length` import, `undeclared_scene_weight` import and branch, floors note, budget loop). Keep only the cap half, now fed by the extended `_obligation_load`. In `check_overload`: gate becomes `any(ch["required_beats"] for ch in chapters)` → else `{"applicable": False, "blocking": [], "notes": []}`; delete the profile-parsing block and `profile_path` param. Update `check_tension` and `main` signatures/args, and `preflight.cmd_lock_mystery`'s call. Keep the lock-certificate `skipped:` plumbing exactly as is (notes still flow through).

- [ ] **Step 4: Run the full suite** — `python3 -m pytest -q`. Fix any caller the grep missed (expected tripwires: `tests/test_preflight.py` lock-mystery overload tests referencing `"weighted"` or profile fixtures).

- [ ] **Step 5: Commit**

```bash
git add scripts/tension_check.py scripts/preflight.py tests/test_tension_check.py tests/test_preflight.py
git commit -m "feat(tension): re-base overloaded-chapter onto Required Beats"
```

---

### Task 8: `preflight draft` — packet/map staleness chain, drop brief checks

**Files:**
- Modify: `scripts/preflight.py` (`cmd_draft`, lines ~138–183)
- Test: `tests/test_preflight.py` and/or `tests/test_draft_preflight_wiring.py` (read both; put new tests beside the existing stale-brief tests, then delete those)

**Interfaces:**
- Consumes: `packet_assemble.stale_packets`, `packet_assemble.packet_path`; `penny_map.map_path`, `penny_map.parse_map`; `penny_whodunit.load_ledger`, `file_sha256`.
- Produces: `cmd_draft` behavior contract:
  1. Existing lock/ledger/model-routing checks unchanged.
  2. If `packet_path(book, chapter).is_file()`: fail by name when `chapter in stale_packets(book)` → `"stale packet for ch NN — the outline or whodunit ledger changed since it was built; re-run /map-chapter <book> <ch>"`.
  3. If `map_path(book, chapter).is_file()`: fail by name when its `parse_map(...)["stamp"]` ≠ `file_sha256(packet_path(...))` (map without packet file → fail `"map exists but its packet is missing — re-run /map-chapter"`).
  4. Neither packet nor map exists → pass (legacy fallback: the runbook warns; preflight does not block).
  5. All `stale_briefs` logic removed.

- [ ] **Step 1: Write the failing tests** (build on the existing draft-preflight tmp-tree helpers — read them first; add packet+map files with good then broken stamps; cover contracts 2, 3, 4 above).

- [ ] **Step 2: Run to verify failure** — the new tests fail on the old brief-based messages.

- [ ] **Step 3: Implement** the swap in `cmd_draft` (imports at the top of the function, matching the file's local-import style).

- [ ] **Step 4: Full suite** — `python3 -m pytest -q`; delete the now-red stale-brief tests in the same commit (they test removed behavior).

- [ ] **Step 5: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py tests/test_draft_preflight_wiring.py
git commit -m "feat(preflight): draft gate reads the packet/map staleness chain"
```

---

### Task 9: Delete the brief machinery

**Files:**
- Delete: `scripts/brief_render.py`, `tests/test_brief_render.py`, `tests/test_build_briefs_command.py`, `commands/build-briefs.md`, `agents/brief-weigher.md`
- Modify: `scripts/penny_length.py` (delete `scene_budgets`; delete `weights`-only error paths it owned), `scripts/penny_wiring.py` (delete `WEIGHT_RE`, `has_weights`, `undeclared_scene_weight`; KEEP `parse_scenes` minus its weight lookup — `SCENE_RE`/beat counting still describe legacy blocks; simplest: keep `parse_scenes` but set `"weight": None` unconditionally and delete the other two), `tests/test_penny_length.py`, `tests/test_penny_wiring.py` (delete weight tests)
- Test: the full suite is the test.

- [ ] **Step 1: Grep for every remaining consumer**

Run: `grep -rn "brief_render\|brief-weigher\|build-briefs\|scene_budgets\|has_weights\|WEIGHT_RE\|undeclared_scene_weight\|briefs/" scripts/ tests/ commands/ agents/ config/ CLAUDE.md README.md .claude-plugin/ 2>/dev/null`
Expected consumers to fix in this task: `commands/draft-chapter.md` + `agents/drafter.md` (Task 10 rewrites those — leave for Task 10 ONLY if the suite stays green; any *script/test* hit gets fixed here). If `.claude-plugin/plugin.json` or the marketplace manifest lists commands by name, remove `build-briefs` there.

- [ ] **Step 2: Delete the files, apply the modifications, delete dead tests.**

- [ ] **Step 3: Full suite** — `python3 -m pytest -q` — all pass, and:

Run: `grep -rn "brief_render" scripts/ tests/` — expected: no hits.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat!: delete the brief compiler and scene-weight machinery"
```

---

### Task 10: Command, agent, template, and doc surface

**Files:**
- Create: `commands/map-chapter.md`, `agents/map-maker.md`
- Modify: `commands/draft-chapter.md` (step 3), `commands/expand-outline.md`, `commands/review-chapter.md` (brief→packet in ledger-slice + dev-editor inputs), `agents/drafter.md` (Inputs + instruction 1/3), `agents/outline-expander.md` (emit packet blocks, never scenes), `config/outline-template.md` (packet-format teaching copy + example), `CLAUDE.md` (pipeline section: `/build-briefs` paragraphs → `/map-chapter`; length-profile schema para → v2), `README.md` ("The length profile" schema v2)
- Test: `tests/test_map_chapter_command.py` (new; mirror the contract-test style of the deleted `test_build_briefs_command.py` — greps the runbook for load-bearing strings), update `config/outline-template.md`'s round-trip contract test (find it: `grep -rn "outline-template" tests/`)

**Interfaces:**
- Consumes: everything Tasks 1–9 built.
- Produces: the user-facing surface. Load-bearing strings the contract test pins in `commands/map-chapter.md`: `packet_assemble.py`, `map_check.py`, `${CLAUDE_PLUGIN_ROOT}`, `built_from_packet`, "the showrunner edits/approves", "lock".

- [ ] **Step 1: Write the runbook contract test**, run it, verify it fails.

- [ ] **Step 2: Write `commands/map-chapter.md`** — frontmatter (`description`, `argument-hint: <book-number> <chapter-number>`) + steps: (1) parse args + stage marker `stage=MAP`; (2) `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py" $1 $2` — a nonzero exit names the cure (no lock → lock first; no Required Beats → migrate the block); (3) dispatch `map-maker` (model: `plot_model` from run-config, defaulting to `drafting_model`; the agent def has no `model:` frontmatter, so pass the override explicitly) with the packet text; (4) present the proposed map — the showrunner edits/approves; only the approved map is written to `input/book-$1/maps/ch-$2.md` with frontmatter `built_from_packet: <sha256 of the packet file>`; (5) `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/map_check.py" $1 $2` — findings by name; the map is not consumable until clean (fix the map or the outline; no waivers at map level); (6) stage marker `stage=MAPPED`.

- [ ] **Step 3: Write `agents/map-maker.md`** — follow `agents/_TEMPLATE.md`'s section shape and `brief-weigher`'s posture language (read the git-deleted file via `git show HEAD~1:agents/brief-weigher.md` if useful). Role: proposes the complete prose map from the packet — scene divisions, `Target:` ranges, free-text `Weight:` labels, selective open-vocabulary fields, `Beats covered:` lines for every Required Beat, every `[<clue-id>]` from Ledger Clues placed in exactly one scene's `Clue:` field with anti-spotlight phrasing. Hard constraints: proposes only — the showrunner decides; never edits the outline; never writes ledgers or certificates; targets must sum inside the band printed in the packet's Word Budget.

- [ ] **Step 4: Apply the modification set** (each is a focused edit; keep surrounding style):
  - `commands/draft-chapter.md` step 3: brief lookup → `input/book-$book/packets/ch-$chapter.md` + `input/book-$book/maps/ch-$chapter.md` (map = instruction, packet = context); attach the previous chapter's final ~300 words (`.final.md`, else `.draft.md`, else say so); legacy fallback paragraph: no map → raw outline section verbatim + warning naming `/map-chapter`.
  - `agents/drafter.md`: Inputs list swaps compiled-brief for map+packet (+ previous-chapter tail); instruction 3's budget language: honour the map's per-scene `Target:` ranges; `drafted_short:`/no-padding rules unchanged.
  - `agents/outline-expander.md`: output contract = packet-format block (§3 sections + wiring footer), explicitly "never writes a `### Scene` section".
  - `config/outline-template.md`: teach the packet-format block; the example must round-trip (`parse_wired_chapters` finds its sections, Required Beats, wiring) — update the template's contract test accordingly.
  - `CLAUDE.md`: replace the `/build-briefs` + weigh-before-lock paragraphs with the packet/map flow (three artifacts, `/map-chapter`, the §6 finding names, length-profile schema v2); update the "nine checks" description of `overloaded-chapter` to the Required-Beats basis.
  - `README.md`: length-profile section → schema v2 (`band_*`, `min_scene_words`; legacy keys tolerated/ignored).

- [ ] **Step 5: Full suite + doc-pinning tests**

Run: `python3 -m pytest -q` — all pass (watch `tests/test_claude_md_check_count.py` and the outline-template round-trip; fix wording drift they catch).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(surface): /map-chapter, map-maker, packet-format template + docs"
```

---

### Task 11: End-to-end verification

**Files:** none new — this task exercises the built pipeline against a scratch series tree.

- [ ] **Step 1: Build a scratch series** under the session scratchpad (copy the Task 5 test tree layout: lock, packet-format outline, ledger, continuity, v2 profile, plus a hand-written `maps/ch-05.md` derived from the fixture with a real `built_from_packet` stamp).

- [ ] **Step 2: Drive the scripts end-to-end from the scratch series root**

```bash
cd <scratch-series>
python3 <plugin>/scripts/packet_assemble.py 01 05          # writes packets/ch-05.md, exit 0
python3 - <<'EOF'                                          # stamp the fixture map with the real packet sha
import hashlib, pathlib, re
sha = hashlib.sha256(pathlib.Path("input/book-01/packets/ch-05.md").read_bytes()).hexdigest()
p = pathlib.Path("input/book-01/maps/ch-05.md")
p.write_text(re.sub(r"built_from_packet: \w+", f"built_from_packet: {sha}", p.read_text()))
EOF
python3 <plugin>/scripts/map_check.py 01 05                # exit 0, no findings
python3 <plugin>/scripts/preflight.py draft 01 05          # passes the packet/map chain
python3 <plugin>/scripts/tension_check.py input/book-01/outline.md   # overload check runs on beats
echo "edit" >> input/book-01/outline.md
python3 <plugin>/scripts/preflight.py draft 01 05          # FAILS: stale packet, by name
```

Expected: exits and messages exactly as annotated. Also verify the legacy invariant: run `tension_check.py` against `tests/fixtures/outlines/` legacy scene-format fixture — overload skipped, exit 0.

- [ ] **Step 2b: Run the `verify` skill** against the working tree before the final commit (the repo convention for nontrivial changes).

- [ ] **Step 3: Final full suite + push-ready commit**

```bash
python3 -m pytest -q
git add -A && git commit -m "test: end-to-end packet/map pipeline verification" --allow-empty
```

(If Step 2 surfaced fixes, they land here with a real diff; `--allow-empty` covers the clean case so the phase end is marked.)

---

## Self-Review (performed at write time)

- **Spec coverage:** §3 block format → Tasks 1, 10 (template); §4 map → Task 4; §5 packet → Task 5; §6 checks → Tasks 3, 6, 7; §7 commands → Tasks 8, 10; §8 agents → Task 10; §9 deletions → Task 9; §12 testing → per-task TDD + Task 11. §10 (book-01 migration) is series-side by spec and has no engine task. Gap check: `readiness_check.py` requires a `length-profile.md` but not any schema — v2 changes nothing there (verified: it checks file existence).
- **Placeholder scan:** Tasks 5/8/10 reference reading existing files for helper shape — deliberate (the exact tmp-tree builders live in tests the implementer must open), with the behavior contracts stated in full here.
- **Type consistency:** `required_beats: list[str]` (T1) consumed by T5 guard, T6 coverage, T7 load; `target: tuple[int,int] | None` (T4) consumed by T3's `validate_targets` scene dicts (same key names); `ledger_identity`/`file_sha256` (T2) consumed by T5/T8; `"applicable"` rename (T7) grepped at its consumers.
