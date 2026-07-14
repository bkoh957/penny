# The Outline Prompt — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile a locked outline into one prompt-shaped brief per chapter, so the drafter receives an emphasis hierarchy with word budgets instead of a flat list of ten equal instructions.

**Architecture:** A new deterministic compiler (`scripts/brief_render.py`) reads the locked outline, the whodunit ledger, the wiring, the series length profile, and the genre beat sheet, and writes `input/book-NN/briefs/ch-MM.md` — stamped with the sha256 of the outline it was built from. `/draft-chapter` reads that brief instead of the raw outline section and refuses a stale one. Scene weights (anchor / support / connective) are declared in the outline by the showrunner, proposed by an agent; the compiler never invents them. Unweighted outlines degrade to today's pass-through, so book 1 keeps drafting unchanged.

**Tech Stack:** Python 3 stdlib + `scripts/penny_meta.py` (config/frontmatter parsing — **not** PyYAML). PyYAML only for the whodunit ledger and beat sheet, which are already nested human-edited data. pytest.

**Spec:** `docs/superpowers/specs/2026-07-14-outline-prompt-design.md`

## Global Constraints

- **The engine is genre- and location-agnostic.** No word counts, band names, scene budgets, or hook-grade ratios may appear as constants in `scripts/` or in command logic. Every number is read from `config/length-profile.md` (series) or the genre's `beat-sheet.yaml` (resolved via `penny_genre.py beat-sheet`).
- **Dependency split (load-bearing).** Config and frontmatter are parsed with `scripts/penny_meta.py`. PyYAML is permitted **only** for `series/whodunit/*.yaml` and the genre `beat-sheet.yaml`. Do not reach for PyYAML to read `length-profile.md`.
- **Deterministic layer makes no LLM judgment.** Every check fails with a named predicate and a nonzero exit. The compiler is a compiler: given a weighted outline it has exactly one correct output.
- **Backward compatibility is a hard requirement.** An outline that declares no scene weights must produce today's behaviour exactly: the drafter gets the raw `## Chapter NN` section. Book 1 must keep drafting. Verify against the live series at `~/myBooks/series-pelicanscrook`.
- **Two parser landmines** (from the spec, §5):
  - A chapter-title flag **must sit after the em-dash**. `penny_wiring.py:26` requires the em-dash to follow the digits directly; a bracket before it makes the parser stop recognising the chapter.
  - The opening-line field **cannot be named `Opens:`** — that name already means *story questions opened* (`penny_wiring.py:27`). It is `First line:`.
- Tests live in `tests/`, fixtures in `tests/fixtures/`. Run the full suite (`python3 -m pytest`) before every commit; it is currently **490 passing** and must stay green.
- Commit after each task. Work on `main`.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/penny_length.py` *(new)* | Parse `config/length-profile.md`: chapter bands, emphasis weights, the connective floor. Compute per-scene word budgets. The one place word arithmetic lives. |
| `scripts/penny_wiring.py` *(modify)* | Already **the** wired-outline parser. Extend `parse_wired_chapters()` to also collect each chapter's `### Scene N` blocks, their declared `Weight:`, their beat count, and their instruction word count. One parse of the document, many consumers. |
| `scripts/brief_render.py` *(new)* | The compiler. `check` reports the prompt-level defects; `build` writes the briefs and stamps them. |
| `scripts/tension_check.py` *(modify)* | Gains the ninth named check, `overloaded-chapter` — a **plot** property, checked before the lock. |
| `scripts/preflight.py` *(modify)* | `cmd_draft` refuses a stale brief. |
| `commands/build-briefs.md` *(new)* | The runbook for the new stage. |
| `agents/brief-weigher.md` *(new)* | Proposes scene weights for a chapter. Taste stage: proposes, never decides. |
| `commands/draft-chapter.md`, `agents/drafter.md` *(modify)* | Read the compiled brief; the padding directive is removed. |
| `agents/outline-reviewer.md` *(modify)* | Gains the read-it-as-a-prompt lens. |
| `config/outline-template.md` *(modify)* | Documents `Weight:`, `First line:`, the hook grade, and the title flag. |
| `genres/cozy-mystery/beat-sheet.yaml` *(modify)* | Hook-grade distribution. |

---

### Task 1: The length profile becomes readable arithmetic

Today the only word-count logic in the engine is `parse_length_profile()` buried in `scripts/lmstudio_draft_chapter.py:224`, and it exists to serve one drafting route. The compiler needs the same numbers. Extract them into a module, and give the profile an explicit machine-readable block so nothing has to guess a chapter's type from prose.

**Files:**
- Create: `scripts/penny_length.py`
- Create: `tests/test_penny_length.py`
- Create: `tests/fixtures/length-profile.md`

**Interfaces:**
- Consumes: `scripts.penny_meta.parse_yaml_blocks`, `scripts.penny_meta.load`
- Produces:
  - `parse_profile(text: str) -> dict` → `{"bands": {"opening": (1800, 2400), ...}, "weights": {"anchor": 8, "support": 3, "connective": 1}, "min_connective_words": 100}`
  - `band_for(profile: dict, chapter_type: str | None) -> tuple[int, int]`
  - `scene_budgets(profile: dict, band: tuple[int, int], weights: list[str]) -> list[int]`

- [ ] **Step 1: Write the fixture profile**

Create `tests/fixtures/length-profile.md`. The flat `key: value` block is deliberate — `penny_meta` parses a flat subset, and per the Global Constraints this file must not require PyYAML.

```markdown
# Length Profile — fixture

```yaml
band_opening:      [1800, 2400]
band_standard:     [2000, 2500]
band_quick:        [1500, 2000]
band_major_reveal: [2500, 3200]
band_final:        [3000, 4000]
band_default:      [2000, 2500]
weight_anchor:      8
weight_support:     3
weight_connective:  1
min_connective_words: 100
```
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_penny_length.py`:

```python
from pathlib import Path

import pytest

from scripts import penny_length

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "length-profile.md"


def _profile():
    return penny_length.parse_profile(FIXTURE.read_text(encoding="utf-8"))


def test_parse_profile_reads_bands_and_weights():
    p = _profile()
    assert p["bands"]["opening"] == (1800, 2400)
    assert p["bands"]["major-reveal"] == (2500, 3200)
    assert p["weights"] == {"anchor": 8, "support": 3, "connective": 1}
    assert p["min_connective_words"] == 100


def test_band_for_unknown_type_falls_back_to_default():
    p = _profile()
    assert penny_length.band_for(p, None) == (2000, 2500)
    assert penny_length.band_for(p, "no-such-type") == (2000, 2500)


def test_band_for_known_type():
    p = _profile()
    assert penny_length.band_for(p, "opening") == (1800, 2400)


def test_scene_budgets_share_the_band_midpoint_by_weight():
    # midpoint of 1800-2400 is 2100; shares 8 + 3 + 1 + 1 + 1 = 14
    p = _profile()
    budgets = penny_length.scene_budgets(
        p, (1800, 2400), ["anchor", "support", "connective", "connective", "connective"])
    assert sum(budgets) == 2100
    assert budgets[0] == 1200   # 2100 * 8 / 14
    assert budgets[1] == 450    # 2100 * 3 / 14
    assert budgets[2] == 150    # 2100 * 1 / 14


def test_scene_budgets_rounding_still_sums_to_the_target():
    p = _profile()
    budgets = penny_length.scene_budgets(p, (2000, 2500), ["anchor", "support", "connective"])
    assert sum(budgets) == 2250  # remainder lands on the anchor, never lost


def test_scene_budgets_rejects_an_unknown_weight():
    p = _profile()
    with pytest.raises(ValueError) as e:
        penny_length.scene_budgets(p, (1800, 2400), ["anchor", "atmospheric"])
    assert "atmospheric" in str(e.value)
```

- [ ] **Step 3: Run the tests, watch them fail**

Run: `python3 -m pytest tests/test_penny_length.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_length'`

- [ ] **Step 4: Write the implementation**

Create `scripts/penny_length.py`:

```python
"""Word-count arithmetic for a series' length profile (design §5a).

The ONE place chapter bands and per-scene word budgets are computed. Reads
`config/length-profile.md` — a series-authored file — through penny_meta, never
PyYAML (see CLAUDE.md's dependency-split rule).

The profile carries a flat yaml block:

    band_opening:      [1800, 2400]
    band_default:      [2000, 2500]
    weight_anchor:      8
    weight_support:     3
    weight_connective:  1
    min_connective_words: 100

A scene's budget is its share of the band's midpoint, weighted by its emphasis
class. An anchor is worth eight connective beats because that is what the series
says it is worth — the engine ships no numbers of its own.
"""
from __future__ import annotations

from pathlib import Path

from scripts.penny_meta import load, parse_yaml_blocks

_BAND_PREFIX = "band_"
_WEIGHT_PREFIX = "weight_"


def _ints(value) -> list[int]:
    if isinstance(value, list):
        return [int(str(v).strip()) for v in value]
    raise ValueError(f"length-profile: expected a [min, max] pair, got {value!r}")


def parse_profile(text: str) -> dict:
    cfg = parse_yaml_blocks(text)
    bands: dict[str, tuple[int, int]] = {}
    weights: dict[str, int] = {}
    for key, value in cfg.items():
        if key.startswith(_BAND_PREFIX):
            lo, hi = _ints(value)
            bands[key[len(_BAND_PREFIX):].replace("_", "-")] = (lo, hi)
        elif key.startswith(_WEIGHT_PREFIX):
            weights[key[len(_WEIGHT_PREFIX):].replace("_", "-")] = int(str(value).strip())
    if "default" not in bands:
        raise ValueError("length-profile: no band_default")
    floor = cfg.get("min_connective_words")
    return {"bands": bands, "weights": weights,
            "min_connective_words": int(str(floor).strip()) if floor else 0}


def load_profile(path) -> dict:
    return parse_profile(load(Path(path)))


def band_for(profile: dict, chapter_type: "str | None") -> tuple[int, int]:
    """The [min, max] band for a declared chapter type; the default band otherwise.

    The type is DECLARED in the chapter title, never inferred from the prose — the
    drafter used to guess it, which is how a chapter gets graded against a band it
    was never written for.
    """
    bands = profile["bands"]
    if chapter_type and chapter_type in bands:
        return bands[chapter_type]
    return bands["default"]


def scene_budgets(profile: dict, band: tuple[int, int], weights: list[str]) -> list[int]:
    """Split the band's midpoint across scenes in proportion to their emphasis class.

    The remainder from integer division lands on the heaviest scene, so the budgets
    always sum to the target exactly — a chapter's price is never quietly lost to
    rounding.
    """
    table = profile["weights"]
    for w in weights:
        if w not in table:
            raise ValueError(f"unknown scene weight {w!r} (known: {sorted(table)})")
    target = (band[0] + band[1]) // 2
    shares = [table[w] for w in weights]
    total = sum(shares)
    if total == 0:
        return [0] * len(weights)
    budgets = [target * s // total for s in shares]
    heaviest = max(range(len(shares)), key=lambda i: shares[i])
    budgets[heaviest] += target - sum(budgets)
    return budgets
```

- [ ] **Step 5: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_penny_length.py -v`
Expected: 6 passed.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: 496 passed (490 + 6).

- [ ] **Step 7: Commit**

```bash
git add scripts/penny_length.py tests/test_penny_length.py tests/fixtures/length-profile.md
git commit -m "feat(length): chapter bands and per-scene word budgets as arithmetic

A scene's budget is its share of the band midpoint, weighted by its emphasis
class. All numbers come from the series' length-profile; the engine ships none."
```

---

### Task 2: The wiring parser learns to see scenes

`parse_wired_chapters()` is already **the** parser for a chapter block. Give it eyes for the scene structure so the compiler and the checks never parse the outline a second time.

**Files:**
- Modify: `scripts/penny_wiring.py`
- Modify: `tests/test_penny_wiring.py`
- Create: `tests/fixtures/outlines/weighted-clean.md`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - Each dict from `parse_wired_chapters()` gains: `"scenes": list[dict]`, `"first_line": str | None`, `"hook_grade": str | None`, `"chapter_type": str | None`, `"long_waiver": str | None`.
  - Each scene dict: `{"num": int, "title": str, "weight": str | None, "beats": int, "instruction_words": int}`
  - `has_weights(chapters: list[dict]) -> bool`

- [ ] **Step 1: Write the fixture**

Create `tests/fixtures/outlines/weighted-clean.md`. Chapter 2 carries the title flag; chapter 1 does not.

```markdown
---
book: 01
total_chapters: 2
---

# Fixture — a weighted outline

## Chapter 01 — The Wheelhouse

### Chapter Summary
She arrives and makes the shop real.

- **Because:** opening
- **Opens:** q-who-is-she — will the town take her?
- **Hook:** [cliffhanger] q-who-is-she — the key is missing.
- **First line:** in motion, mid-argument with the estate agent.

### Scene 1 — The Drive

**Weight:** connective

**Beat flow:**

1. Start in the car, not at the shop window.
2. The coast gives pleasure.

### Scene 2 — Cal and the Mug

**Weight:** anchor

**Beat flow:**

1. Cal reads her through the town's scepticism about sea-change reinventions.
2. She gives him the mug and it fits his hand with unnerving rightness.
3. He is stunned not by beauty but by fit.

### Track Movement
- **M:** None.
- **P:** She commits.

## Chapter 02 — The Reveal [type: major-reveal] [long: the confession runs its full course]

### Chapter Summary
Mary confesses.

- **Because:** ch 01 — the key turned up in the wrong hand.
- **Closes:** q-who-is-she
- **Hook:** [promise] q-what-now — she has to tell Cal.

### Scene 1 — The Kitchen

**Weight:** anchor

**Beat flow:**

1. Mary sets down the tin and does not sit.

### Track Movement
- **M:** The confession.
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_penny_wiring.py`:

```python
WEIGHTED = Path(__file__).resolve().parent / "fixtures" / "outlines" / "weighted-clean.md"


def test_parse_scenes_reads_weights_beats_and_instruction_mass():
    chapters = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    ch1 = chapters[0]
    assert [s["weight"] for s in ch1["scenes"]] == ["connective", "anchor"]
    assert [s["num"] for s in ch1["scenes"]] == [1, 2]
    assert ch1["scenes"][0]["title"] == "The Drive"
    assert ch1["scenes"][0]["beats"] == 2
    assert ch1["scenes"][1]["beats"] == 3
    # instruction mass = words in the beat-flow text; the anchor carries more here
    assert ch1["scenes"][1]["instruction_words"] > ch1["scenes"][0]["instruction_words"]


def test_parse_chapter_reads_first_line_and_hook_grade():
    chapters = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    assert chapters[0]["first_line"] == "in motion, mid-argument with the estate agent."
    assert chapters[0]["hook_grade"] == "cliffhanger"
    assert chapters[0]["hook_q"] == "q-who-is-she"   # the grade must not eat the id
    assert chapters[1]["hook_grade"] == "promise"


def test_title_flags_parse_type_and_long_waiver():
    chapters = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    assert chapters[0]["chapter_type"] is None
    assert chapters[0]["long_waiver"] is None
    assert chapters[1]["chapter_type"] == "major-reveal"
    assert chapters[1]["long_waiver"] == "the confession runs its full course"
    # the flags must not survive into the title the reader's copy prints
    assert chapters[1]["title"] == "The Reveal"


def test_has_weights_true_for_weighted_outline_false_for_the_wired_one():
    weighted = penny_wiring.parse_wired_chapters(WEIGHTED.read_text(encoding="utf-8"))
    assert penny_wiring.has_weights(weighted) is True
    wired = penny_wiring.parse_wired_chapters((FIX / "wired-clean.md").read_text(encoding="utf-8"))
    assert penny_wiring.has_weights(wired) is False
```

Note on names: `tests/test_penny_wiring.py` already defines `FIX` (the `tests/fixtures/outlines/` dir) and reads `wired-clean.md` inline through it — there is **no** `WIRED_CLEAN` constant. Reuse `FIX`; add only the `WEIGHTED` constant above.

- [ ] **Step 3: Run the tests, watch them fail**

Run: `python3 -m pytest tests/test_penny_wiring.py -k "scenes or first_line or title_flags or has_weights" -v`
Expected: FAIL — `KeyError: 'scenes'` and `AttributeError: module 'scripts.penny_wiring' has no attribute 'has_weights'`

- [ ] **Step 4: Write the implementation**

In `scripts/penny_wiring.py`, add these module-level regexes next to the existing ones (after `TP_FIELD_RE`):

```python
SCENE_RE = re.compile(r"^###\s+Scene\s+(\d+)(?:\s*[—-]\s*(.*))?$", re.MULTILINE)
WEIGHT_RE = re.compile(r"^\s*\*\*Weight:\*\*\s*(anchor|support|connective)\s*$",
                       re.MULTILINE | re.IGNORECASE)
BEAT_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
FIRSTLINE_RE = re.compile(r"^\s*-\s+\*\*First line:\*\*\s*(.*)$")
GRADE_RE = re.compile(r"^\[(cliffhanger|promise)\]\s*(.*)$", re.IGNORECASE)
TYPE_FLAG_RE = re.compile(r"\[type:\s*([a-z0-9-]+)\]", re.IGNORECASE)
LONG_FLAG_RE = re.compile(r"\[long:\s*([^\]]+)\]", re.IGNORECASE)
```

Add the scene parser:

```python
def parse_scenes(block: str) -> list[dict]:
    """The `### Scene N` blocks of one chapter, with their declared weight, beat
    count, and instruction mass.

    `instruction_words` is the word count of the beat-flow text — the covert word
    budget the model actually obeys. A 'connective' scene whose instruction mass
    exceeds the anchor's is the outline lying to the drafter about what matters.
    """
    scenes: list[dict] = []
    marks = list(SCENE_RE.finditer(block))
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(block)
        body = block[start:end]
        wm = WEIGHT_RE.search(body)
        beats = [BEAT_RE.match(line) for line in body.splitlines()]
        beat_texts = [b.group(2) for b in beats if b]
        scenes.append({
            "num": int(m.group(1)),
            "title": (m.group(2) or "").strip(),
            "weight": wm.group(1).lower() if wm else None,
            "beats": len(beat_texts),
            "instruction_words": sum(len(t.split()) for t in beat_texts),
        })
    return scenes


def has_weights(chapters: list[dict]) -> bool:
    """An outline is weighted iff any scene declares a Weight. All-or-nothing per
    book, exactly like the wiring: an unweighted outline is passed through untouched.
    """
    return any(s["weight"] for c in chapters for s in c["scenes"])
```

Now extend `parse_wired_chapters()`. Replace the `ch = {...}` initialiser and the loop so the chapter block is captured and the new fields are filled. The full replacement for the body of the `for i, m in enumerate(matches):` loop:

```python
    for i, m in enumerate(matches):
        cm = CHAPTER_RE.match(m.group(1))
        if not cm:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        raw_title = (cm.group(2) or "").strip()
        tf = TYPE_FLAG_RE.search(raw_title)
        lf = LONG_FLAG_RE.search(raw_title)
        title = TYPE_FLAG_RE.sub("", raw_title)
        title = LONG_FLAG_RE.sub("", title).strip()
        ch = {"num": int(cm.group(1)), "title": title,
              "because": None, "because_ch": None, "opens": [], "closes": [],
              "carries": [], "hook_q": None, "hook_raw": None, "tracks": {},
              "scenes": parse_scenes(block), "first_line": None, "hook_grade": None,
              "chapter_type": tf.group(1).lower() if tf else None,
              "long_waiver": lf.group(1).strip() if lf else None,
              "errors": []}
        for line in block.splitlines():
            flm = FIRSTLINE_RE.match(line)
            if flm:
                ch["first_line"] = flm.group(1).strip()
                continue
            fm = FIELD_RE.match(line)
            if fm:
                field, value = fm.group(1), fm.group(2).strip()
                if field == "Because":
                    ch["because"] = value
                    bm = _BECAUSE_CH_RE.match(value)
                    if bm:
                        ch["because_ch"] = int(bm.group(1))
                elif field == "Hook":
                    gm = GRADE_RE.match(value)
                    if gm:
                        ch["hook_grade"] = gm.group(1).lower()
                        value = gm.group(2).strip()
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
```

The grade is stripped from the Hook value **before** `split_id` runs, so `hook_q` still resolves — the existing `broken-hook` check must keep working on a graded hook.

- [ ] **Step 5: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_penny_wiring.py -v`
Expected: all pass, including the pre-existing wiring tests.

- [ ] **Step 6: Prove the un-wired outline is still skipped**

This is the invariant `HANDOFF-plot.md` says to stop for if it ever breaks.

Run: `python3 scripts/tension_check.py ~/myBooks/series-pelicanscrook/input/book-01/outline.md`
Expected: `no wiring detected — skipped`, exit 0.

- [ ] **Step 7: Run the full suite and commit**

Run: `python3 -m pytest`
Expected: 500 passed.

```bash
git add scripts/penny_wiring.py tests/test_penny_wiring.py tests/fixtures/outlines/weighted-clean.md
git commit -m "feat(wiring): parse scenes, weights, first line, hook grade, title flags

One parse of the chapter block, many consumers. instruction_words is the covert
word budget the model actually obeys, so the checks can measure it."
```

---

### Task 3: `brief_render.py check` — the prompt-level defects

Three named checks, run at the brief stage — after the lock, because they are properties of the **prompt**, not of the plot.

**Files:**
- Create: `scripts/brief_render.py`
- Create: `tests/test_brief_render.py`
- Create: `tests/fixtures/outlines/weighted-inverted.md`

**Interfaces:**
- Consumes: `penny_wiring.parse_wired_chapters`, `penny_wiring.has_weights`, `penny_length.parse_profile`, `penny_length.band_for`, `penny_length.scene_budgets`
- Produces: `check_briefs(outline_path, *, profile_path, beat_sheet_path=None) -> dict` → `{"weighted": bool, "findings": list[str], "metrics": dict}`. A finding is a string beginning with its check id and a colon, matching `tension_check`'s convention.

- [ ] **Step 1: Write the fixture with the inversion**

Create `tests/fixtures/outlines/weighted-inverted.md` — a connective scene carrying more instruction mass than the anchor, which is exactly book 1's defect:

```markdown
---
book: 01
total_chapters: 1
---

# Fixture — a chapter whose prompt lies about what matters

## Chapter 01 — The Wheelhouse

- **Because:** opening
- **Opens:** q-who-is-she — will the town take her?
- **Hook:** q-who-is-she — the key is missing.

### Scene 1 — The Drive

**Weight:** connective

**Beat flow:**

1. Start in the car, not at the shop window. The hatchback smells of iron oxide, old cardboard, damp canvas and clay dust. Everything she has chosen to keep from the old life is physically around her, and everything she has refused to keep is conspicuously absent from it.
2. Establish why she chose this town specifically and not merely a coastal town in general, four years earlier, on a long weekend, standing too long in a doorway held by the light on glaze and the feel of a room built for hands rather than for meetings.

### Scene 2 — Cal and the Mug

**Weight:** anchor

**Beat flow:**

1. She gives him the mug.

### Track Movement
- **M:** None.
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_brief_render.py`:

```python
from pathlib import Path

from scripts import brief_render

FIX = Path(__file__).resolve().parent / "fixtures"
PROFILE = FIX / "length-profile.md"
WEIGHTED = FIX / "outlines" / "weighted-clean.md"
INVERTED = FIX / "outlines" / "weighted-inverted.md"
WIRED = FIX / "outlines" / "wired-clean.md"


def _ids(findings):
    return sorted({f.split(":", 1)[0] for f in findings})


def test_unweighted_outline_is_skipped_entirely():
    r = brief_render.check_briefs(WIRED, profile_path=PROFILE)
    assert r["weighted"] is False
    assert r["findings"] == []


def test_clean_weighted_outline_has_no_findings():
    r = brief_render.check_briefs(WEIGHTED, profile_path=PROFILE)
    assert r["weighted"] is True
    assert r["findings"] == []


def test_prompt_mass_inversion_is_flagged():
    r = brief_render.check_briefs(INVERTED, profile_path=PROFILE)
    assert "prompt-mass-inversion" in _ids(r["findings"])
    finding = next(f for f in r["findings"] if f.startswith("prompt-mass-inversion"))
    assert "ch 1" in finding
    assert "The Drive" in finding


def test_unweighted_chapter_in_a_weighted_book_is_flagged(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("**Weight:** anchor\n\n**Beat flow:**\n\n1. Mary sets down the tin and does not sit.", "**Beat flow:**\n\n1. Mary sets down the tin and does not sit.")
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p, profile_path=PROFILE)
    assert "unweighted-chapter" in _ids(r["findings"])


def test_all_cliffhangers_is_flagged_when_the_beat_sheet_caps_them(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("[promise]", "[cliffhanger]")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("hooks:\n  max_cliffhanger_fraction: 0.5\n", encoding="utf-8")
    r = brief_render.check_briefs(outline, profile_path=PROFILE, beat_sheet_path=sheet)
    assert "hook-grade-distribution" in _ids(r["findings"])


def test_missing_hook_grade_is_flagged(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("[cliffhanger] ", "")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(outline, profile_path=PROFILE)
    assert "hook-grade-distribution" in _ids(r["findings"])
```

- [ ] **Step 3: Run the tests, watch them fail**

Run: `python3 -m pytest tests/test_brief_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.brief_render'`

- [ ] **Step 4: Write the checks**

Create `scripts/brief_render.py`:

```python
"""Compile a locked outline into one prompt-shaped brief per chapter (spec:
docs/superpowers/specs/2026-07-14-outline-prompt-design.md).

Two subcommands:

  check  — the prompt-level defects: a scene whose instruction mass contradicts its
           declared weight, a chapter with no weights in a weighted book, a book of
           undeclared or unrelieved cliffhangers.
  build  — write input/book-NN/briefs/ch-MM.md, stamped with the outline's sha256.

Why this exists: /draft-chapter used to hand the drafter the raw outline section —
ten numbered beats, each written with equal lavishness, reference material formatted
identically to directives. A numbered list is a promise of parity and a model's
default unit is the scene, so ten beats became 3,802 words against an 1,800-2,400
band. The model obeyed the prompt it received. This turns the outline into a prompt.

Deterministic throughout: given a weighted outline there is exactly one correct
brief. The weights themselves are the showrunner's, declared in the outline.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # beat-sheet only — nested, human-edited (CLAUDE.md dependency split)

from scripts import penny_length, penny_paths
from scripts.penny_wiring import has_weights, parse_wired_chapters


def _load_sheet(path) -> dict:
    if path is None or not Path(path).is_file():
        return {}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def check_briefs(outline_path, *, profile_path, beat_sheet_path=None) -> dict:
    text = Path(outline_path).read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_weights(chapters):
        return {"weighted": False, "findings": [], "metrics": {"chapters": len(chapters)}}

    profile = penny_length.parse_profile(Path(profile_path).read_text(encoding="utf-8"))
    findings: list[str] = []

    for ch in chapters:
        scenes = ch["scenes"]
        if scenes and not any(s["weight"] for s in scenes):
            findings.append(
                f"unweighted-chapter: ch {ch['num']} declares no scene weights in a "
                f"weighted book — the drafter will treat all {len(scenes)} scenes as equal")
            continue
        anchors = [s for s in scenes if s["weight"] == "anchor"]
        if not anchors:
            findings.append(
                f"unweighted-chapter: ch {ch['num']} has no anchor scene — every chapter "
                f"needs one central dramatic experience")
            continue
        heaviest_anchor = max(s["instruction_words"] for s in anchors)
        for s in scenes:
            if s["weight"] == "connective" and s["instruction_words"] > heaviest_anchor:
                findings.append(
                    f"prompt-mass-inversion: ch {ch['num']} scene {s['num']} "
                    f"'{s['title']}' is marked connective but carries "
                    f"{s['instruction_words']} words of instruction against the anchor's "
                    f"{heaviest_anchor} — the prompt says it matters more than the anchor, "
                    f"and the drafter will believe the prompt")

    graded = [c for c in chapters if c["hook_grade"]]
    ungraded = [c["num"] for c in chapters if not c["hook_grade"]]
    if ungraded:
        findings.append(
            f"hook-grade-distribution: chapters {ungraded} declare no hook grade "
            f"(cliffhanger | promise) — a chapter that ends on neither ends on nothing")
    sheet = _load_sheet(beat_sheet_path)
    cap = (sheet.get("hooks") or {}).get("max_cliffhanger_fraction")
    if cap is not None and graded:
        cliffs = [c["num"] for c in graded if c["hook_grade"] == "cliffhanger"]
        fraction = len(cliffs) / len(graded)
        if fraction > float(cap):
            findings.append(
                f"hook-grade-distribution: {len(cliffs)}/{len(graded)} chapters end on a "
                f"cliffhanger ({fraction:.0%} > {float(cap):.0%}) — unrelieved cliffhangers "
                f"read as machinery and the reader stops believing them")

    return {"weighted": True, "findings": findings,
            "metrics": {"chapters": len(chapters),
                        "scenes": sum(len(c["scenes"]) for c in chapters)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compile a locked outline into chapter briefs.")
    ap.add_argument("command", choices=["check", "build"])
    ap.add_argument("book")
    ap.add_argument("--chapter", default=None, help="only this chapter, e.g. 03")
    args = ap.parse_args(argv)

    root = penny_paths.series_root()
    outline = penny_paths.input_path(f"book-{args.book}/outline.md", root=root)
    profile = penny_paths.config_path("length-profile.md", root=root)
    if not outline.is_file():
        sys.exit(f"brief: no outline at {outline}")
    if not profile.is_file():
        sys.exit(f"brief: no length profile at {profile}")

    if args.command == "check":
        result = check_briefs(outline, profile_path=profile,
                              beat_sheet_path=_beat_sheet_path(root))
        if not result["weighted"]:
            print("no scene weights detected — skipped "
                  "(the drafter will receive the raw outline section)")
            return 0
        for f in result["findings"]:
            print(f"FINDING: {f}")
        print(f"briefs: {result['metrics']['chapters']} chapter(s), "
              f"{result['metrics']['scenes']} scene(s), "
              f"{len(result['findings'])} finding(s)")
        return 1 if result["findings"] else 0

    return build(args.book, chapter=args.chapter, repo_root=root)


def _beat_sheet_path(root):
    """The active genre's beat sheet, resolved through penny_genre's `beat_sheet()`
    — never a hardcoded filename (CLAUDE.md). Returns None when the genre declares
    none, which the checks treat as 'no cap configured'."""
    from scripts import penny_genre
    return penny_genre.beat_sheet(root=root)


if __name__ == "__main__":
    raise SystemExit(main())
```

**Note for the implementer:** `penny_genre.beat_sheet(root=None) -> Path | None` is the real, existing helper (`scripts/penny_genre.py:102`) — it resolves the sheet through `genre.yaml`'s `beat_sheet:` key. Do **not** hardcode `genres/<g>/beat-sheet.yaml`. `build()` does not exist yet; it arrives in Task 4, so this task's `main` cannot run `build` until then. That is fine — Task 3's tests exercise `check_briefs` directly.

- [ ] **Step 5: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_brief_render.py -v`
Expected: 6 passed.

- [ ] **Step 6: Run the full suite and commit**

Run: `python3 -m pytest`
Expected: 506 passed.

```bash
git add scripts/brief_render.py tests/test_brief_render.py tests/fixtures/outlines/weighted-inverted.md
git commit -m "feat(brief): prompt-level checks — mass inversion, unweighted, hook grades

A connective scene carrying more instruction than the anchor is the outline lying
to the drafter about what matters. No taste required to detect it: count the words."
```

---

### Task 4: `brief_render.py build` — the compiler

**Files:**
- Modify: `scripts/brief_render.py`
- Modify: `tests/test_brief_render.py`

**Interfaces:**
- Consumes: everything from Task 3.
- Produces:
  - `render_brief(chapter: dict, *, profile: dict, obligations: dict, outline_text: str) -> str`
  - `build(book: str, *, chapter=None, repo_root=None) -> int` — writes `input/book-NN/briefs/ch-MM.md`, returns 0.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_brief_render.py`:

```python
from scripts import penny_length


def _ch(name, path=WEIGHTED):
    from scripts.penny_wiring import parse_wired_chapters
    chapters = parse_wired_chapters(path.read_text(encoding="utf-8"))
    return next(c for c in chapters if c["num"] == name)


def _profile():
    return penny_length.parse_profile(PROFILE.read_text(encoding="utf-8"))


def test_brief_leads_with_the_one_thing_then_the_anchor():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    one_thing = brief.index("## The one thing")
    shape = brief.index("## The shape")
    obligations = brief.index("## Obligations")
    reference = brief.index("## Reference")
    assert one_thing < shape < obligations < reference


def test_anchor_carries_the_largest_budget_and_the_budgets_sum_to_the_band():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    # ch 1 has no [type:] flag, so the default band 2000-2500 → midpoint 2250,
    # shares connective 1 + anchor 8 = 9 → 250 and 2000.
    assert "~2000 words" in brief   # the anchor
    assert "~250 words" in brief    # the connective drive
    assert "Cal and the Mug" in brief


def test_connective_scene_names_its_form_not_a_number_alone():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "in summary, not scene" in brief


def test_brief_commissions_the_first_line_and_forbids_the_warm_up():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "in motion, mid-argument with the estate agent." in brief
    assert "no weather, no waking, no arriving" in brief


def test_brief_commissions_the_graded_hook_and_forbids_the_button():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "cliffhanger" in brief
    assert "Do not add a closing paragraph of reflection" in brief


def test_obligations_are_a_checklist_not_beats():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": ["clue-tide-table"], "opens": ["q-who-is-she"],
                     "closes": [], "tracks": {"P": "She commits."}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "clue-tide-table" in brief
    assert "must be TRUE OF THE PAGE" in brief
    assert "not stops on an itinerary" in brief


def test_long_waiver_is_carried_into_the_brief():
    brief = brief_render.render_brief(
        _ch(2), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    # ch 2 declares [type: major-reveal] → band 2500-3200, midpoint 2850
    assert "~2850 words" in brief
    assert "the confession runs its full course" in brief
```

- [ ] **Step 2: Run the tests, watch them fail**

Run: `python3 -m pytest tests/test_brief_render.py -k render_brief -v`
Expected: FAIL — `AttributeError: module 'scripts.brief_render' has no attribute 'render_brief'`

- [ ] **Step 3: Write the compiler**

Add to `scripts/brief_render.py`:

```python
_FORM = {
    "anchor": "Dramatise fully. This is the chapter's reason to exist.",
    "support": "Brief scene texture, kept subordinate to the anchor.",
    "connective": "Compress: one paragraph, a transition, a phone call, or a line of "
                  "dialogue — in summary, not scene.",
}

_NO_WARMUP = ("Open in motion — no weather, no waking, no arriving, no scene-setting "
              "run-up. The chapter starts where the trouble starts.")

_NO_BUTTON = ("End on that line. Do not add a closing paragraph of reflection, and do "
              "not tie the chapter off.")

_GRADE = {
    "cliffhanger": "a turn, threat, or revelation that makes the next page involuntary",
    "promise": "a promise of the next action — an intention, an appointment, a decision "
               "taken (the lesser hook, and the right one for a connective chapter)",
}


def render_brief(chapter: dict, *, profile: dict, obligations: dict,
                 outline_text: str) -> str:
    """One chapter's brief: a prompt, not an outline section.

    The order is the instruction. The one thing comes before any beat; the anchor is
    the root and everything else is nested beneath it; obligations are a checklist,
    never stops; reference material is demoted out of instruction voice.
    """
    scenes = chapter["scenes"]
    band = penny_length.band_for(profile, chapter["chapter_type"])
    budgets = penny_length.scene_budgets(
        profile, band, [s["weight"] or "support" for s in scenes])
    target = sum(budgets)

    anchor = next((s for s in scenes if s["weight"] == "anchor"), None)
    out: list[str] = []
    out.append(f"# Chapter {chapter['num']:02d} — {chapter['title']}")
    out.append("")
    out.append("## The one thing")
    out.append("")
    out.append("The reader should finish this chapter remembering **one** central "
               "dramatic experience, not a list of technically correct stops:")
    out.append("")
    out.append(f"> {anchor['title'] if anchor else chapter['title']}")
    out.append("")
    out.append(f"Total budget: **~{target} words** (band {band[0]}–{band[1]}).")
    if chapter["long_waiver"]:
        out.append("")
        out.append(f"**Declared long:** {chapter['long_waiver']} — this override is "
                   f"recorded, and the length checks honour it.")
    out.append("")

    out.append("## The shape")
    out.append("")
    if anchor:
        i = scenes.index(anchor)
        out.append(f"### ANCHOR — Scene {anchor['num']}: {anchor['title']} "
                   f"(~{budgets[i]} words)")
        out.append("")
        out.append(_FORM["anchor"])
        out.append("")
        out.append("Everything below is **subordinate to this scene**. It is material in "
                   "service of it, not a peer of it.")
        out.append("")
    for i, s in enumerate(scenes):
        if s is anchor:
            continue
        weight = s["weight"] or "support"
        out.append(f"  - **{weight.upper()} — Scene {s['num']}: {s['title']}** "
                   f"(~{budgets[i]} words). {_FORM[weight]}")
    out.append("")

    out.append("## Obligations")
    out.append("")
    out.append("These **must be TRUE OF THE PAGE** by the end of the chapter. They are "
               "**not stops on an itinerary** — most can be discharged inside the anchor "
               "scene in a sentence. Do not give any of them their own scene.")
    out.append("")
    for clue in obligations.get("clues", []):
        out.append(f"- Plant: `{clue}` — fairly, on the page, in view of the reader.")
    for q in obligations.get("opens", []):
        out.append(f"- Open the question: `{q}`")
    for q in obligations.get("closes", []):
        out.append(f"- Close the question: `{q}`")
    for track, movement in (obligations.get("tracks") or {}).items():
        if movement and movement.strip().lower() != "none":
            out.append(f"- Advance thread **{track}**: {movement}")
    if not any(obligations.get(k) for k in ("clues", "opens", "closes", "tracks")):
        out.append("- None.")
    out.append("")

    out.append("## The first line")
    out.append("")
    if chapter["first_line"]:
        out.append(f"{chapter['first_line']}")
        out.append("")
    out.append(_NO_WARMUP)
    out.append("")

    out.append("## The last line")
    out.append("")
    grade = chapter["hook_grade"]
    if grade:
        out.append(f"End on a **{grade}**: {_GRADE[grade]}.")
    if chapter["hook_raw"]:
        out.append("")
        out.append(f"The hook: {chapter['hook_raw']}")
    out.append("")
    out.append(_NO_BUTTON)
    out.append("")

    out.append("## Negative space")
    out.append("")
    out.append("Do not resolve any question this chapter is not commissioned to close. "
               "Do not dramatise anything not named above — if an event must be "
               "acknowledged, refer to it in a line. Left to itself a model resolves "
               "tension early and stages everything; both are fatal to a page-turner.")
    out.append("")

    out.append("## Reference — available material, NOT a checklist")
    out.append("")
    out.append("Everything below is the outline as written. It is context you may draw "
               "on. It is **not** a list of things to do, and no line of it obliges you "
               "to write a scene.")
    out.append("")
    out.append("<details>")
    out.append("")
    out.append(_chapter_block(outline_text, chapter["num"]))
    out.append("")
    out.append("</details>")
    out.append("")
    return "\n".join(out)


def _chapter_block(outline_text: str, num: int) -> str:
    """The raw `## Chapter NN` section — reference only."""
    from scripts.penny_wiring import CHAPTER_RE, HEADING_RE
    marks = list(HEADING_RE.finditer(outline_text))
    for i, m in enumerate(marks):
        cm = CHAPTER_RE.match(m.group(1))
        if cm and int(cm.group(1)) == num:
            start = m.start()
            end = marks[i + 1].start() if i + 1 < len(marks) else len(outline_text)
            return outline_text[start:end].strip()
    return ""
```

- [ ] **Step 4: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_brief_render.py -v`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/brief_render.py tests/test_brief_render.py
git commit -m "feat(brief): render a chapter as a prompt — hierarchy, budgets, negative space

The anchor is the root and everything else is nested beneath it; obligations are a
checklist, never stops; reference is demoted out of instruction voice."
```

---

### Task 5: Write the briefs, stamp them, and refuse a stale one

**Files:**
- Modify: `scripts/brief_render.py` (add `build`)
- Modify: `scripts/preflight.py` (`cmd_draft`)
- Modify: `tests/test_brief_render.py`, `tests/test_preflight.py`

**Interfaces:**
- Consumes: `render_brief`, `scripts.plot_stage.stamp`, `scripts.penny_meta.parse_frontmatter`
- Produces:
  - `build(book, *, chapter=None, repo_root=None) -> int`
  - `brief_path(book, chapter, repo_root) -> Path` → `input/book-NN/briefs/ch-MM.md`
  - `stale_briefs(book, repo_root) -> list[str]` → chapter numbers whose `built_from_outline` no longer matches

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_brief_render.py`:

```python
import shutil


def _series(tmp_path):
    (tmp_path / ".penny").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(PROFILE, tmp_path / "config/length-profile.md")
    inp = tmp_path / "input/book-01"
    inp.mkdir(parents=True, exist_ok=True)
    shutil.copy(WEIGHTED, inp / "outline.md")
    (tmp_path / "series/whodunit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "series/whodunit/book-01.yaml").write_text(
        "book: '01'\nreveal_chapter: 2\nclue_schedule:\n"
        "  - { id: clue-tide-table, plant_chapter: 1, pays_off_chapter: 2, necessary: true }\n",
        encoding="utf-8")
    return tmp_path


def test_build_writes_one_brief_per_chapter_stamped_with_the_outline_sha(tmp_path):
    root = _series(tmp_path)
    assert brief_render.build("01", repo_root=root) == 0
    b1 = root / "input/book-01/briefs/ch-01.md"
    assert b1.is_file()
    from scripts.penny_meta import parse_frontmatter
    fm = parse_frontmatter(b1.read_text(encoding="utf-8"))
    assert fm["built_from_outline"]


def test_build_pulls_the_clue_obligation_from_the_locked_ledger(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    text = (root / "input/book-01/briefs/ch-01.md").read_text(encoding="utf-8")
    assert "clue-tide-table" in text


def test_editing_the_outline_makes_the_brief_stale(tmp_path):
    root = _series(tmp_path)
    brief_render.build("01", repo_root=root)
    assert brief_render.stale_briefs("01", root) == []
    outline = root / "input/book-01/outline.md"
    outline.write_text(outline.read_text(encoding="utf-8") + "\n<!-- edited -->\n",
                       encoding="utf-8")
    assert brief_render.stale_briefs("01", root) == ["01", "02"]
```

Append to `tests/test_preflight.py`:

```python
def test_draft_fails_on_a_stale_brief(tmp_path):
    _make_book(tmp_path, populated=True, locked=True)
    briefs = tmp_path / "input/book-01/briefs"
    briefs.mkdir(parents=True, exist_ok=True)
    (tmp_path / "input/book-01/outline.md").write_text("## Chapter 01 — X\n", encoding="utf-8")
    (briefs / "ch-01.md").write_text(
        "---\nbuilt_from_outline: deadbeef\n---\n# brief\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "stale brief" in str(e.value)


def test_draft_passes_when_no_briefs_exist_at_all(tmp_path):
    # Book 1 has no briefs and must keep drafting exactly as before.
    _make_book(tmp_path, populated=True, locked=True)
    assert preflight.cmd_draft("01", "01", repo_root=tmp_path) == 0
```

- [ ] **Step 2: Run the tests, watch them fail**

Run: `python3 -m pytest tests/test_brief_render.py tests/test_preflight.py -k "build or stale" -v`
Expected: FAIL — `AttributeError: module 'scripts.brief_render' has no attribute 'build'`, and the preflight stale test does not raise.

- [ ] **Step 3: Implement `build` and `stale_briefs`**

Add to `scripts/brief_render.py`:

```python
import hashlib

from scripts.penny_meta import parse_frontmatter, write_frontmatter_field


def brief_path(book: str, chapter: str, repo_root) -> Path:
    return penny_paths.input_path(f"book-{book}/briefs/ch-{chapter}.md", root=repo_root)


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _obligations(book: str, chapter: dict, repo_root) -> dict:
    """What must be TRUE OF THE PAGE — derived from the locked ledger and the wiring,
    never re-authored. This is why the stage runs after the lock."""
    led = penny_paths.series_path(f"whodunit/book-{book}.yaml", root=repo_root)
    clues: list[str] = []
    if led.is_file():
        data = yaml.safe_load(led.read_text(encoding="utf-8")) or {}
        for entry in (data.get("clue_schedule") or []):
            if int(entry.get("plant_chapter", 0)) == chapter["num"]:
                clues.append(str(entry["id"]))
        for entry in (data.get("red_herrings") or []):
            if int(entry.get("plant_chapter", 0)) == chapter["num"]:
                clues.append(str(entry["id"]))
    return {"clues": clues,
            "opens": [q for q, _ in chapter["opens"]],
            "closes": list(chapter["closes"]),
            "tracks": dict(chapter["tracks"])}


def build(book: str, *, chapter=None, repo_root=None) -> int:
    root = Path(repo_root) if repo_root is not None else penny_paths.series_root()
    outline = penny_paths.input_path(f"book-{book}/outline.md", root=root)
    profile_path = penny_paths.config_path("length-profile.md", root=root)
    text = outline.read_text(encoding="utf-8")
    chapters = parse_wired_chapters(text)
    if not has_weights(chapters):
        print("no scene weights detected — no briefs written "
              "(the drafter will receive the raw outline section, as today)")
        return 0
    profile = penny_length.parse_profile(profile_path.read_text(encoding="utf-8"))
    sha = _sha(outline)
    written = 0
    for ch in chapters:
        num = f"{ch['num']:02d}"
        if chapter is not None and num != str(chapter).zfill(2):
            continue
        body = render_brief(ch, profile=profile,
                            obligations=_obligations(book, ch, root),
                            outline_text=text)
        stamped = write_frontmatter_field("---\n---\n\n" + body,
                                          "built_from_outline", sha)
        p = brief_path(book, num, root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(stamped, encoding="utf-8")
        written += 1
    print(f"briefs: wrote {written} chapter brief(s) to input/book-{book}/briefs/")
    return 0


def stale_briefs(book: str, repo_root) -> list[str]:
    """Chapter numbers whose brief was built from a different outline than the one on
    disk. Editing the outline invalidates every brief built from it — nothing drifts
    silently (the workshop's own contract)."""
    root = Path(repo_root)
    outline = penny_paths.input_path(f"book-{book}/outline.md", root=root)
    briefs_dir = penny_paths.input_path(f"book-{book}/briefs", root=root)
    if not briefs_dir.is_dir() or not outline.is_file():
        return []
    sha = _sha(outline)
    stale = []
    for p in sorted(briefs_dir.glob("ch-*.md")):
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if fm.get("built_from_outline") != sha:
            stale.append(p.stem.replace("ch-", ""))
    return stale
```

In `scripts/preflight.py`, add to `cmd_draft` immediately before `return 0`:

```python
    # A brief built from a different outline is a lie about what this chapter owes.
    # No briefs at all is fine — that is book 1, and it drafts from the raw section.
    from scripts.brief_render import stale_briefs
    stale = stale_briefs(book, repo_root)
    if chapter.zfill(2) in stale:
        _fail(f"stale brief for ch {chapter} — the outline changed since it was built; "
              f"re-run /build-briefs {book}")
```

- [ ] **Step 4: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_brief_render.py tests/test_preflight.py -v`
Expected: all pass.

- [ ] **Step 5: Full suite and commit**

Run: `python3 -m pytest`
Expected: 518 passed.

```bash
git add scripts/brief_render.py scripts/preflight.py tests/test_brief_render.py tests/test_preflight.py
git commit -m "feat(brief): write and stamp the briefs; draft refuses a stale one

Each brief records the sha256 of the outline it was built from. Edit the outline
and every brief built from it goes stale — nothing drifts silently."
```

---

### Task 6: `overloaded-chapter` — the plot-level check

A chapter doing too much **in content** is a plot property, so it is caught before the lock, beside the other eight tension checks. The arithmetic detects it: if the chapter's scenes cannot each be paid for out of the band, the outline gave the chapter more than it can hold.

**Files:**
- Modify: `scripts/tension_check.py`
- Modify: `tests/test_tension_check.py`

**Interfaces:**
- Consumes: `penny_length.parse_profile`, `penny_length.band_for`, `penny_length.scene_budgets`
- Produces: a `overloaded-chapter: …` string in `check_tension(...)["blocking"]`. Waivable through the existing `--waive` machinery — no new flag.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tension_check.py`:

```python
PROFILE = Path(__file__).resolve().parent / "fixtures" / "length-profile.md"


def test_overloaded_chapter_flagged_when_a_connective_scene_cannot_be_paid_for(tmp_path):
    # 1 anchor + 8 connective in the default band (midpoint 2250): shares 8 + 8 = 16,
    # so each connective gets 2250/16 = 140 words... still above the 100 floor.
    # Push it to 20 connective scenes: 2250 * 1 / 28 = 80 < 100 → overloaded.
    scenes = "\n".join(
        f"### Scene {i} — Stop {i}\n\n**Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n"
        for i in range(2, 22))
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n"
        "## Chapter 01 — Too Much\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        + scenes, encoding="utf-8")
    result = tension_check.check_tension(outline, profile_path=PROFILE)
    assert any(b.startswith("overloaded-chapter") for b in result["blocking"])
    finding = next(b for b in result["blocking"] if b.startswith("overloaded-chapter"))
    assert "ch 1" in finding


def test_no_overload_when_the_scene_count_fits_the_band(tmp_path):
    outline = tmp_path / "outline.md"
    outline.write_text(
        "---\nbook: 01\ntotal_chapters: 1\n---\n\n"
        "## Chapter 01 — Just Right\n\n"
        "- **Because:** opening\n"
        "- **Opens:** q-a — a question.\n"
        "- **Hook:** q-a — a hook.\n\n"
        "### Scene 1 — The Anchor\n\n**Weight:** anchor\n\n**Beat flow:**\n\n1. The turn.\n\n"
        "### Scene 2 — A Stop\n\n**Weight:** connective\n\n**Beat flow:**\n\n1. A stop.\n",
        encoding="utf-8")
    result = tension_check.check_tension(outline, profile_path=PROFILE)
    assert not any(b.startswith("overloaded-chapter") for b in result["blocking"])


def test_unweighted_outline_is_never_overload_checked():
    # An un-weighted outline (book 1's shape) must never trip the check.
    wired = Path(__file__).resolve().parent / "fixtures" / "outlines" / "wired-clean.md"
    result = tension_check.check_tension(wired, profile_path=PROFILE)
    assert not any(b.startswith("overloaded-chapter") for b in result["blocking"])
```

Use whatever fixture constant `tests/test_tension_check.py` already defines for `wired-clean.md` if one exists; do not introduce a duplicate.

- [ ] **Step 2: Run the test, watch it fail**

Run: `python3 -m pytest tests/test_tension_check.py -k overload -v`
Expected: FAIL — `TypeError: check_tension() got an unexpected keyword argument 'profile_path'`

- [ ] **Step 3: Implement**

In `scripts/tension_check.py`, add the check function:

```python
def _overload_check(chapters, profile, blocking):
    """A chapter doing too much IN CONTENT — a plot property, visible before a word
    is drafted. If the band cannot pay each connective scene its floor, the outline
    gave this chapter more stops than it can hold, and it will run long no matter how
    well it is written.
    """
    from scripts import penny_length
    floor = profile.get("min_connective_words", 0)
    if not floor:
        return
    for ch in chapters:
        scenes = ch["scenes"]
        if not scenes or not any(s["weight"] for s in scenes):
            continue
        band = penny_length.band_for(profile, ch["chapter_type"])
        weights = [s["weight"] or "support" for s in scenes]
        budgets = penny_length.scene_budgets(profile, band, weights)
        for s, b in zip(scenes, budgets):
            if s["weight"] == "connective" and b < floor:
                blocking.append(
                    f"overloaded-chapter: ch {ch['num']} has {len(scenes)} scenes; at band "
                    f"{band[0]}–{band[1]} scene {s['num']} '{s['title']}' can only be paid "
                    f"{b} words against a {floor}-word floor — the chapter is doing too "
                    f"much to fit its length")
                break
```

Extend `check_tension`'s signature and call it. Change the signature line to:

```python
def check_tension(outline_path, *, beat_sheet_path=None, turning_points_path=None,
                  whodunit_path=None, profile_path=None) -> dict:
```

and immediately before the final `return {"wired": True, ...}`, add:

```python
    if profile_path is not None and Path(profile_path).is_file():
        from scripts import penny_length
        profile = penny_length.parse_profile(
            Path(profile_path).read_text(encoding="utf-8"))
        _overload_check(chapters, profile, blocking)
```

`tension_check.main()` takes its paths as explicit CLI flags (`--beat-sheet`, `--turning-points`, `--whodunit`) rather than resolving them itself. Follow that pattern exactly — add:

```python
    ap.add_argument("--profile", dest="profile")
```

and thread `profile_path=args.profile` into the `check_tension(...)` call.

Then, in `scripts/preflight.py`'s `cmd_lock_mystery`, pass `profile_path=penny_paths.config_path("length-profile.md", root=repo_root)` where it already passes the beat sheet, so the new check runs at lock time and its waivers land in the certificate like the other eight. **Guard it:** the engine ships no `length-profile.md`, so a series without one must still lock — `check_tension` already no-ops when `profile_path` is None or absent, which is the required behaviour, not an oversight.

- [ ] **Step 4: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_tension_check.py tests/test_preflight.py -v`
Expected: all pass.

- [ ] **Step 5: Prove book 1 still locks**

Run:
```bash
cd ~/myBooks/series-pelicanscrook && python3 ~/myTools/penny/scripts/tension_check.py input/book-01/outline.md
```
Expected: `no wiring detected — skipped`, exit 0. **If this breaks, stop** — `HANDOFF-plot.md` names it as the invariant that must hold.

- [ ] **Step 6: Full suite and commit**

Run: `python3 -m pytest`
Expected: 521 passed.

```bash
git add scripts/tension_check.py scripts/preflight.py tests/test_tension_check.py
git commit -m "feat(tension): overloaded-chapter — the ninth named check

A chapter whose connective scenes cannot be paid for out of its band is doing too
much, and will run long however well it is written. Caught in the plan, not the prose."
```

---

### Task 7: The stage — `/build-briefs` and the weight proposer

**Files:**
- Create: `commands/build-briefs.md`
- Create: `agents/brief-weigher.md`
- Create: `tests/test_build_briefs_command.py`

**Interfaces:**
- Consumes: `brief_render.py check` / `build`; dispatches `brief-weigher`.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing contract test**

Penny already tests its runbooks for the contracts that matter (see `tests/test_plot_book_command.py`). Create `tests/test_build_briefs_command.py`:

```python
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CMD = REPO / "commands" / "build-briefs.md"
AGENT = REPO / "agents" / "brief-weigher.md"


def test_command_exists_and_runs_after_the_lock():
    text = CMD.read_text(encoding="utf-8")
    assert "lock" in text.lower()
    assert "brief_render.py" in text


def test_command_shells_out_through_the_plugin_root():
    # runbooks must resolve scripts regardless of which series folder is cwd
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" in CMD.read_text(encoding="utf-8")


def test_weigher_proposes_and_never_decides():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "propose" in text
    assert "never writes" in text or "does not write" in text
```

- [ ] **Step 2: Run it, watch it fail**

Run: `python3 -m pytest tests/test_build_briefs_command.py -v`
Expected: FAIL — `FileNotFoundError: commands/build-briefs.md`

- [ ] **Step 3: Write the agent**

Create `agents/brief-weigher.md`:

```markdown
---
name: brief-weigher
description: Proposes each scene's dramatic weight (anchor / support / connective) for one chapter. Proposes only — the showrunner decides, and only the showrunner writes the outline.
---
# Brief Weigher

**Role posture:** proposer. Surfaces a weighting; never chooses it. The same posture as
`plot-proposer` at the workshop's taste stages (design §5a).

**Why this exists:** the drafter receives the chapter as a flat list of beats, and a flat
list is a promise of parity — it says *these are peers*. Ten equally-lavish beats produce
ten equal scenes and a chapter at nearly twice its band. Someone must say which scene is
the chapter's reason to exist. That someone is the showrunner; this agent hands them a
first draft of the answer.

**Inputs:**
- One chapter's `## Chapter NN` section from `input/book-NN/outline.md`.
- The chapter's word band from `config/length-profile.md`.

**Outputs:**
- A proposed weight for each `### Scene N` — `anchor`, `support`, or `connective` — with
  one sentence of reasoning each, and the resulting word budget.
- **Nothing else. It never writes the outline, a brief, a ledger, or a certificate.**

**How to weigh:**
- **Anchor** — the scene the reader will remember. The chapter's central dramatic
  experience. Usually exactly one; at most two. If you cannot name it, say so: a chapter
  with no anchor is a chapter with no reason to exist, and that is a finding, not a
  weighting.
- **Support** — a scene that pressures or complicates the anchor. Real scene work, kept
  subordinate.
- **Connective** — travel, errands, arrivals, a second example of something already
  established, a conversation whose only job is to move a fact from A to B. These become a
  paragraph, a transition, a phone call, or a line of dialogue.

**The trap to name explicitly:** a connective scene is often the *most lavishly written* in
the outline, because it is where an author enjoys themselves. Weigh what the scene DOES,
not how beautifully it is described. If a drive across the coast carries eight rich beats
and the confrontation carries one, the outline is lying to the drafter about what matters —
say so.
```

- [ ] **Step 4: Write the runbook**

Create `commands/build-briefs.md`:

```markdown
---
description: Compile a locked outline into one prompt-shaped brief per chapter — the emphasis hierarchy, the word budgets, the obligations checklist, the commissioned first and last lines.
---
# /build-briefs NN

The step between the lock and the first draft. The outline is an authoring artifact; this
turns it into a **prompt**.

**Preconditions:** the book is locked (`.penny/locks/book-NN.mystery.lock`). Run from the
series folder.

## Steps

1. **Refuse an unlocked book.**

   ```bash
   test -f ".penny/locks/book-$1.mystery.lock" || {
     echo "build-briefs: book $1 is not locked — the obligations are not settled yet."; exit 1; }
   ```

2. **Weigh the scenes (the taste stage).**

   If the outline declares no `- **Weight:**` on its scenes, dispatch the **`brief-weigher`**
   sub-agent once per chapter (pass `model:` = `plot_model` from `config/run-config.md`,
   defaulting to `drafting_model`). Present its proposal to the showrunner **per chapter**.

   The showrunner accepts, edits, or rejects. **Only the showrunner's accepted weights are
   written into `input/book-NN/outline.md`.** The machine never writes a weight it chose
   itself — the weighting is the chapter's dramatic hierarchy, and that is taste.

3. **Check the prompt.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" check "$1"
   ```

   Findings are reported, not enforced: `prompt-mass-inversion` (a connective scene
   carrying more instruction than the anchor — the outline lying about what matters),
   `unweighted-chapter`, `hook-grade-distribution`. Present them to the showrunner and
   resolve them by editing the outline, then re-run.

4. **Compile.**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" build "$1"
   ```

   Writes `input/book-NN/briefs/ch-MM.md`, each stamped with the sha256 of the outline it
   was built from. Edit the outline afterwards and every brief goes stale; `/draft-chapter`
   will refuse until you re-run this.

5. **Report.** Name the per-chapter word budgets and the total, so the showrunner sees the
   book priced before a word of it is drafted.

## Notes

- An outline with **no scene weights is passed through untouched** — no briefs are written,
  and `/draft-chapter` reads the raw outline section exactly as it does today. Book 1 is
  unaffected until you choose to weigh it.
- The weights live in the **outline**, not in the briefs. The briefs are compiled artifacts;
  the outline is the source of truth. Re-compiling is always safe.
```

- [ ] **Step 5: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_build_briefs_command.py -v`
Expected: 3 passed.

- [ ] **Step 6: Full suite and commit**

Run: `python3 -m pytest`
Expected: 524 passed.

```bash
git add commands/build-briefs.md agents/brief-weigher.md tests/test_build_briefs_command.py
git commit -m "feat(build-briefs): the stage between the lock and the first draft

The weigher proposes the dramatic hierarchy; the showrunner decides it. The machine
never writes a weight it chose itself."
```

---

### Task 8: The drafter reads the brief, and stops padding

**Files:**
- Modify: `commands/draft-chapter.md:42–55`
- Modify: `agents/drafter.md` (the Inputs block; line 61's padding directive)
- Modify: `tests/test_draft_preflight_wiring.py`

**Interfaces:**
- Consumes: `input/book-NN/briefs/ch-MM.md` when present.
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_draft_preflight_wiring.py`:

```python
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_draft_chapter_prefers_the_compiled_brief():
    text = (REPO / "commands" / "draft-chapter.md").read_text(encoding="utf-8")
    assert "briefs/ch-$chapter.md" in text
    assert "falls back" in text.lower() or "fall back" in text.lower()


def test_drafter_no_longer_tells_the_model_to_pad():
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8")
    for banned in ("extend a scene", "deepen interiority", "slow a beat",
                   "add sensory texture"):
        assert banned not in text, f"padding directive survives: {banned!r}"


def test_drafter_treats_a_short_chapter_as_a_scene_count_problem():
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8").lower()
    assert "scene" in text and "do not pad" in text
```

- [ ] **Step 2: Run them, watch them fail**

Run: `python3 -m pytest tests/test_draft_preflight_wiring.py -k "brief or pad or scene_count" -v`
Expected: FAIL — the padding strings are still present.

- [ ] **Step 3: Rewrite the drafter's length instruction**

In `agents/drafter.md`, replace instruction 3 in its entirety:

```markdown
3. **Write to the brief's budget.** If `input/book-NN/briefs/ch-MM.md` exists it is your
   prompt: the anchor scene is the chapter's reason to exist and carries the largest word
   budget; support beats are subordinate; connective beats are a paragraph, a transition, a
   phone call, or a line of dialogue — **in summary, not scene.** Honour the per-scene
   budgets. The obligations list names what must be TRUE OF THE PAGE; discharge them inside
   the scenes you are already writing. **Do not give an obligation its own scene.**

   **Do not pad.** If the chapter runs short, that is a **scene-count** problem and it
   belongs to the outline, not to your prose — report it rather than inflating what is
   there. Never extend a scene, slow a beat, or add texture to reach a number: dilution is
   the opposite of a page-turner, and a chapter is not improved by being longer.

   Plant exactly the clues the brief names.
```

In the **Inputs** block of `agents/drafter.md`, add above the existing chapter-brief bullet:

```markdown
- **The compiled brief** — `input/book-NN/briefs/ch-MM.md`, when it exists. This is a
  prompt, not an outline: the anchor scene is the root and every other scene is subordinate
  to it. When there is no brief, you receive the raw `## Chapter NN` outline section
  instead (the legacy path) — in that case treat the beats as **unweighted**, and read the
  chapter summary to decide which scene is the chapter's one dramatic experience.
```

- [ ] **Step 4: Rewrite the brief assembly in the runbook**

In `commands/draft-chapter.md`, replace step 3's chapter-brief bullet with:

```markdown
   - **Chapter brief:** if `input/book-$book/briefs/ch-$chapter.md` exists, that file **is**
     the brief — pass it verbatim. It is a compiled prompt: an emphasis hierarchy with word
     budgets, an obligations checklist, a commissioned first line, a graded hook, declared
     negative space, and the raw outline section demoted to reference.

     If it does not exist, **fall back** to the legacy path: read
     `input/book-$book/outline.md` and extract the full `## Chapter $chapter` section. Warn
     that the chapter is drafting from an uncompiled outline, and that a flat beat list
     will be read by the model as a promise of parity — run `/build-briefs $book` to fix it.
```

- [ ] **Step 5: Run the tests, watch them pass**

Run: `python3 -m pytest tests/test_draft_preflight_wiring.py -v`
Expected: all pass.

- [ ] **Step 6: Full suite and commit**

Run: `python3 -m pytest`
Expected: 527 passed.

```bash
git add commands/draft-chapter.md agents/drafter.md tests/test_draft_preflight_wiring.py
git commit -m "feat(drafter): read the compiled brief; the padding directive is gone

'If you are under the minimum, extend a scene, deepen interiority, slow a beat' was
dilution on demand. A short chapter is a scene-count problem and belongs to the outline."
```

---

### Task 9: Templates, the genre pack, the reviewer's lens, and the docs

**Files:**
- Modify: `config/outline-template.md`
- Modify: `genres/cozy-mystery/beat-sheet.yaml`
- Modify: `agents/outline-reviewer.md`
- Modify: `CLAUDE.md`, `README.md`

- [ ] **Step 1: Extend the outline template**

In `config/outline-template.md`, inside the `## Chapter 01` block, add the new fields and a scene block with its weight:

```markdown
## Chapter 01 — <Title> [type: opening]

<!-- Title flags are OPTIONAL and must come AFTER the em-dash — a bracket before it
     stops the wiring parser recognising the chapter at all.
       [type: <band>]     selects the word band from config/length-profile.md
       [long: <reason>]   a recorded override: this chapter is allowed to run long -->

### Chapter Summary
<The one dramatic experience the reader will remember.>

### Chapter Structure
- **Start / Desire:** <What the protagonist wants at the chapter's opening.>
- **Pressure / Obstacle:** <What blocks or complicates that want.>
- **Turn / Change:** <What is materially different by the end — what is worse now, and for whom.>
- **Texture / Pleasure Layer:** <Humour, setting, food, animals, community rituals.>
- **First line:** <What the opening sentence must DO — land in motion, on an image, or
  mid-exchange. Never weather, waking, arriving, or a scene-setting run-up.>
- **Hook:** <[cliffhanger] or [promise], then the q-slug. A cliffhanger is a turn, threat
  or revelation that makes the next page involuntary; a promise is the lesser hook — an
  intention, an appointment, a decision taken. A chapter that ends on neither ends on
  nothing.>

### Scene 1 — <Title>

**Weight:** <anchor | support | connective — anchor is the chapter's reason to exist;
connective becomes a paragraph, a transition, or a line of dialogue. Write connective
beats THINLY: the prompt's own density is a word budget the model obeys.>

**Beat flow:**

1. <beat>
```

- [ ] **Step 2: Add the hook-grade cap to the genre pack**

In `genres/cozy-mystery/beat-sheet.yaml`, append:

```yaml
# Consumed by brief_render.py's hook-grade-distribution check. Unrelieved cliffhangers
# read as machinery and the reader stops believing them; a cozy earns its turns.
hooks:
  max_cliffhanger_fraction: 0.4
```

- [ ] **Step 3: Give the outline reviewer the prompt lens**

In `agents/outline-reviewer.md`, add to its instructions:

```markdown
**Read the outline as a prompt, not only as literature.** The drafter sees nothing but this
document, so its defects as a *prompt* reach the page as surely as its defects as a *plan*.
For each chapter ask:

- **What will the model actually DO with this instruction?** A numbered list is a promise of
  parity — it tells the model these beats are peers. A beat described in ninety lavish words
  will become several paragraphs whatever its dramatic weight, because instruction mass sets
  output mass.
- **Is any beat's prompt mass out of proportion to its dramatic weight?** A connective beat
  written gorgeously is a trap: it reads as minor and prompts as major. This is the single
  most common cause of a chapter running to twice its band.
- **Is an obligation being staged as a stop?** A clue that must be planted is a thing that
  must be *true of the page*, not a scene. Six obligations rendered as six beats become six
  technically correct stops, and the reader remembers none of them.
```

- [ ] **Step 4: Update the docs**

In `CLAUDE.md`, under **The pipeline**, after the three front doors, add:

```markdown
**Per book, after the lock:** `/build-briefs NN` compiles the locked outline into one
prompt-shaped brief per chapter (`input/book-NN/briefs/ch-MM.md`) — an emphasis hierarchy
(anchor/support/connective) with per-scene word budgets from `config/length-profile.md`,
obligations as a checklist rather than stops, a commissioned first line, a graded hook
(cliffhanger | promise), declared negative space, and the raw outline section demoted to
reference. Each brief is stamped `built_from_outline: <sha256>`; edit the outline and
`preflight draft` refuses until the briefs are rebuilt. **An outline with no scene weights
is passed through untouched** — `/draft-chapter` then reads the raw section exactly as
before, so book 1 is unaffected. The weights are declared by the showrunner in the outline;
`brief-weigher` proposes, it never decides.
```

Add `overloaded-chapter` to the `tension_check.py` check list in the same file (it now names
**nine**), and note that `scripts/penny_length.py` owns all word arithmetic.

In `README.md`, add `/build-briefs` to the workflow between the lock and drafting.

- [ ] **Step 5: Full suite**

Run: `python3 -m pytest`
Expected: 527 passed (this task adds no tests — it is documentation and data).

- [ ] **Step 6: Commit**

```bash
git add config/outline-template.md genres/cozy-mystery/beat-sheet.yaml agents/outline-reviewer.md CLAUDE.md README.md
git commit -m "docs(outline-prompt): the template, the hook cap, the reviewer's prompt lens"
```

---

## Shakedown (not a task — the real verification)

The deterministic layer will be green long before this thing is any good. The taste stage —
does `brief-weigher` name the right anchor? — cannot be unit-tested, exactly as the plotting
workshop's stages could not.

Run it on the hardest case in the repo:

```bash
cd ~/myBooks/series-pelicanscrook
# weigh book 1's chapter 1 by hand or via the weigher, then:
python3 ~/myTools/penny/scripts/brief_render.py check 01
python3 ~/myTools/penny/scripts/brief_render.py build 01
```

**What success looks like:** `check` flags chapter 1's Scene 1 — the coastal drive, eight
lavish beats, its own stated purpose "let Maggie think before the town/murder machinery
begins" — as `prompt-mass-inversion` against the Cal-and-the-mug anchor. The compiled brief
prices chapter 1 at roughly 2,100 words with the drive at ~250, against the 3,802 the flat
list actually produced.

Re-drafting chapter 1 against the new brief is the only test that matters, and it is the
first question to ask when this lands.
