# Penny Phase 5 — Beta-Reader Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the book-level beta-reader layer — six persona definitions, the reaction-report protocol, a blind `beta-reader` agent, a deterministic report serializer/collapser, and the input-agnostic `/beta-read <path>` command — fixture-tested now, live in Phase 6.

**Architecture:** The blind agent supplies *judgment* (engagement scores, put-down chapters, would-buy verdict); a deterministic Python module (`scripts/beta_report.py`) enforces *shape* — exactly the `penny_verdict.py` / `ledger_markers.py` split. The command fans six personas across reachable `beta_models`, each sub-agent receiving only `{text, persona_file}`, then collapses each persona's per-model readings into one converged report. Cross-persona rollup and P0.8 escalation are explicitly **not** built (Phase 6).

**Tech Stack:** Python 3 (stdlib only — `json`, `statistics`, `pathlib`), pytest, Markdown agent/command/config files in the existing Claude-Code-native layout.

**Spec:** `docs/superpowers/specs/2026-06-21-penny-phase5-beta-layer-design.md`

## Global Constraints

- Beta is **non-blocking**: the command never writes `.penny/current-stage` and never emits `^BLOCKING:` lines. (spec §6, §10)
- The blind contract: a beta-reader sub-agent receives **only** `{text, persona_file}` — no ledgers, outline, solution, or rules. (spec §3, §7)
- `driver` is **persona-stamped, never reader-picked**; the reader emits only `yes | no | n/a`. The Arc `facet` (`self | place`) is the only reader-chosen sub-tag. (spec §5.1 rule 3)
- `n/a` is a **first-class verdict, distinct from `no`**, and is excluded from the `would_buy_next` denominator. (spec §5.1 rule 2)
- Shared fields serialize as `{value, lens}` where `lens` = the emitting persona's stamped lens. (spec §5.1 rule 1)
- The six-value driver enum is the single source of truth in `scripts/beta_report.py` (`DRIVER_BY_PERSONA`); persona files' `driver:` frontmatter must agree with it.
- **No cross-persona rollup** anywhere in Phase 5 (it is the Phase-6 revision-priority report). (spec §5.2, §9)
- Tests resolve repo paths via `ROOT = Path(__file__).resolve().parents[1]` (doc/scaffold tests) or run from repo root (`parse_yaml_blocks(load("config/..."))`), matching the existing suite.
- Run the full suite with `python3 -m pytest -q` from the repo root.

---

### Task 1: `beta_report.py` — constants + raw-reading serializer

**Files:**
- Create: `scripts/beta_report.py`
- Test: `tests/test_beta_report.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `DRIVER_BY_PERSONA: dict[str,str]` — the 6 persona→driver mappings.
  - `VERDICTS: set[str]` = `{"yes","no","n/a"}`; `ARC_FACETS: set[str]` = `{"self","place"}`; `SCHEMA = "penny-beta/1"`.
  - `build_raw_reading(*, persona, model, engagement_curve, put_down_points, whodunit_guess, confusion_points, emotional_beats, would_buy_verdict, would_buy_facet=None, notes="") -> dict` — validated/normalized raw-reading dict; stamps `driver` and every `emotional_beats[*].lens` from the persona; the dict has top-level keys `schema, persona, model, engagement_curve, put_down_points, whodunit_guess, confusion_points, emotional_beats, would_buy_next, notes`, where `would_buy_next = {"verdict", "driver", "facet"?}` and `emotional_beats = [{"beat","lens"}, ...]`.
  - `serialize_raw_reading(reading) -> str`; `write_raw_reading(out_dir, reading) -> Path` (writes `<persona>.<model>.raw.md`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_beta_report.py
import json
import pytest
from scripts import beta_report as br


def _curve(*pairs):
    return [{"chapter": c, "score": s} for c, s in pairs]


def test_driver_is_stamped_from_persona_not_payload():
    r = br.build_raw_reading(
        persona="cozy-loyalist", model="codex",
        engagement_curve=_curve((1, 4)), put_down_points=[],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=["warm hearth scene"],
        would_buy_verdict="yes")
    assert r["would_buy_next"]["driver"] == "comfort-tone"
    assert r["emotional_beats"][0]["lens"] == "comfort-tone"


def test_verdict_enum_enforced():
    with pytest.raises(ValueError):
        br.build_raw_reading(
            persona="puzzle-hawk", model="codex",
            engagement_curve=_curve((1, 3)), put_down_points=[],
            whodunit_guess={"name": "X", "chapter": 9},
            confusion_points=[], emotional_beats=[],
            would_buy_verdict="maybe")


def test_na_is_distinct_from_no():
    r = br.build_raw_reading(
        persona="romance-reader", model="codex",
        engagement_curve=_curve((1, 3)), put_down_points=[],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=[],
        would_buy_verdict="n/a")
    assert r["would_buy_next"]["verdict"] == "n/a"
    assert r["would_buy_next"]["verdict"] != "no"


def test_facet_rejected_for_non_arc():
    with pytest.raises(ValueError):
        br.build_raw_reading(
            persona="cozy-loyalist", model="codex",
            engagement_curve=_curve((1, 4)), put_down_points=[],
            whodunit_guess={"name": None, "chapter": None},
            confusion_points=[], emotional_beats=[],
            would_buy_verdict="no", would_buy_facet="self")


def test_facet_allowed_for_arc():
    r = br.build_raw_reading(
        persona="arc-reader", model="codex",
        engagement_curve=_curve((1, 4)), put_down_points=[],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=["she chooses to stay"],
        would_buy_verdict="no", would_buy_facet="place")
    assert r["would_buy_next"]["facet"] == "place"


def test_unknown_persona_rejected():
    with pytest.raises(ValueError):
        br.build_raw_reading(
            persona="nope", model="codex",
            engagement_curve=_curve((1, 4)), put_down_points=[],
            whodunit_guess={"name": None, "chapter": None},
            confusion_points=[], emotional_beats=[],
            would_buy_verdict="yes")


def test_serialize_round_trips_payload(tmp_path):
    r = br.build_raw_reading(
        persona="impatient-skimmer", model="hermes",
        engagement_curve=_curve((1, 5), (2, 2)), put_down_points=[2],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=[],
        would_buy_verdict="no")
    path = br.write_raw_reading(tmp_path, r)
    assert path.name == "impatient-skimmer.hermes.raw.md"
    text = path.read_text(encoding="utf-8")
    assert "schema: penny-beta/1" in text
    payload = json.loads(text.split("---\n", 2)[2])
    assert payload["put_down_points"] == [2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_beta_report.py -q`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError: module 'scripts.beta_report' has no attribute 'build_raw_reading'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/beta_report.py
"""Beta-reader report serializer + per-persona cross-model collapser (Phase 5).

The blind beta-reader agent supplies *judgment* (engagement scores, put-down
chapters, would-buy verdict); this module enforces *shape* — exactly the
penny_verdict.py / ledger_markers.py split. It never decides anything a reader
should decide; it stamps the persona's lens, validates enums, and (Task 2)
collapses a persona's per-model readings into one converged report.

No cross-PERSONA rollup lives here — that is Phase 6 (the revision-priority
report). See docs/superpowers/specs/2026-06-21-penny-phase5-beta-layer-design.md.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "penny-beta/1"

# Single source of truth for the stamped driver enum (spec §5.1). One driver per
# persona lens. Mirrored by the persona files' `driver:` frontmatter; agreement
# is pinned by the scaffold test in Task 3.
DRIVER_BY_PERSONA = {
    "cozy-loyalist": "comfort-tone",
    "puzzle-hawk": "fairness",
    "arc-reader": "transformation",
    "romance-reader": "chemistry",
    "impatient-skimmer": "pace",
    "newcomer-outsider": "onboarding",
}
VERDICTS = {"yes", "no", "n/a"}
ARC_FACETS = {"self", "place"}


def _require(cond, msg):
    if not cond:
        raise ValueError(msg)


def build_raw_reading(*, persona, model, engagement_curve, put_down_points,
                      whodunit_guess, confusion_points, emotional_beats,
                      would_buy_verdict, would_buy_facet=None, notes=""):
    """Normalize + validate one (persona, model) reading into a raw-reading dict.

    `driver` and every emotional-beat `lens` are STAMPED from the persona — never
    taken from the agent payload (spec §5.1 rule 3). `would_buy_verdict` is the
    only yes|no|n/a the reader chooses; `would_buy_facet` (arc-reader only) is the
    only reader-chosen sub-tag.
    """
    _require(persona in DRIVER_BY_PERSONA, f"unknown persona {persona!r}")
    _require(would_buy_verdict in VERDICTS,
             f"would_buy_verdict {would_buy_verdict!r} not in {sorted(VERDICTS)}")
    driver = DRIVER_BY_PERSONA[persona]
    if would_buy_facet is not None:
        _require(persona == "arc-reader",
                 f"facet only valid for arc-reader, not {persona!r}")
        _require(would_buy_facet in ARC_FACETS,
                 f"facet {would_buy_facet!r} not in {sorted(ARC_FACETS)}")
    beats = [{"beat": b, "lens": driver} for b in emotional_beats]
    would_buy = {"verdict": would_buy_verdict, "driver": driver}
    if would_buy_facet is not None:
        would_buy["facet"] = would_buy_facet
    return {
        "schema": SCHEMA,
        "persona": persona,
        "model": model,
        "engagement_curve": list(engagement_curve),
        "put_down_points": list(put_down_points),
        "whodunit_guess": whodunit_guess,
        "confusion_points": list(confusion_points),
        "emotional_beats": beats,
        "would_buy_next": would_buy,
        "notes": notes,
    }


def serialize_raw_reading(reading) -> str:
    return ("---\n"
            f"schema: {reading['schema']}\n"
            f"persona: {reading['persona']}\n"
            f"model: {reading['model']}\n"
            "kind: beta-raw\n"
            "---\n"
            + json.dumps(reading, sort_keys=True, indent=2) + "\n")


def write_raw_reading(out_dir, reading) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{reading['persona']}.{reading['model']}.raw.md"
    path.write_text(serialize_raw_reading(reading), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_beta_report.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/beta_report.py tests/test_beta_report.py
git commit -m "feat(beta): beta_report raw-reading serializer with stamped driver + n/a-first-class"
```

---

### Task 2: `beta_report.py` — per-persona cross-model collapser

**Files:**
- Modify: `scripts/beta_report.py`
- Test: `tests/test_beta_report.py` (append)

**Interfaces:**
- Consumes: `build_raw_reading` output dicts (Task 1); `DRIVER_BY_PERSONA`, `SCHEMA`.
- Produces:
  - `collapse_persona(readings: list[dict], *, k: int, panel_size: int) -> dict` — one converged report for a single persona. Output keys: `schema, persona, driver, panel{m,k,panel_size,distinct_models,degraded}, engagement_curve[{chapter,central,band:[min,max]}], put_down_points{consensus:[int],logged:[int]}, would_buy_next{tally:{yes,no,"n/a"},denominator:int}`. A put-down chapter is `consensus` iff flagged by `>= k` of the `m` readings, else `logged`. `n/a` verdicts are excluded from `denominator`. `degraded` is true iff distinct models `< panel_size`.
  - `serialize_converged(report) -> str`; `write_converged(out_dir, report) -> Path` (writes `<persona>.converged.md`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_beta_report.py  (append)
def _reading(persona, model, curve, put_downs, verdict):
    return br.build_raw_reading(
        persona=persona, model=model, engagement_curve=_curve(*curve),
        put_down_points=put_downs, whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=[], would_buy_verdict=verdict)


def test_engagement_curve_central_and_band():
    readings = [
        _reading("impatient-skimmer", "codex", [(1, 5), (2, 2)], [], "no"),
        _reading("impatient-skimmer", "hermes", [(1, 3), (2, 2)], [], "no"),
        _reading("impatient-skimmer", "openclaw", [(1, 4), (2, 1)], [], "no"),
    ]
    rep = br.collapse_persona(readings, k=2, panel_size=3)
    ch1 = next(c for c in rep["engagement_curve"] if c["chapter"] == 1)
    assert ch1["central"] == 4          # median(5,3,4)
    assert ch1["band"] == [3, 5]


def test_put_down_consensus_k_of_m_drops_singletons():
    readings = [
        _reading("impatient-skimmer", "codex", [(1, 2)], [9], "no"),
        _reading("impatient-skimmer", "hermes", [(1, 2)], [9], "no"),
        _reading("impatient-skimmer", "openclaw", [(1, 2)], [4], "no"),
    ]
    rep = br.collapse_persona(readings, k=2, panel_size=3)
    assert rep["put_down_points"]["consensus"] == [9]   # 2 of 3
    assert rep["put_down_points"]["logged"] == [4]      # 1 of 3


def test_na_excluded_from_denominator():
    readings = [
        _reading("romance-reader", "codex", [(1, 3)], [], "n/a"),
        _reading("romance-reader", "hermes", [(1, 3)], [], "n/a"),
        _reading("romance-reader", "openclaw", [(1, 3)], [], "no"),
    ]
    rep = br.collapse_persona(readings, k=2, panel_size=3)
    assert rep["would_buy_next"]["tally"]["n/a"] == 2
    assert rep["would_buy_next"]["denominator"] == 1    # 3 - 2 n/a


def test_degraded_panel_flagged():
    readings = [
        _reading("puzzle-hawk", "codex", [(1, 3)], [], "yes"),
        _reading("puzzle-hawk", "codex", [(1, 4)], [], "yes"),  # repeat-sampled
    ]
    rep = br.collapse_persona(readings, k=2, panel_size=3)
    assert rep["panel"]["degraded"] is True
    assert rep["panel"]["distinct_models"] == ["codex"]


def test_mixed_personas_rejected():
    readings = [
        _reading("puzzle-hawk", "codex", [(1, 3)], [], "yes"),
        _reading("cozy-loyalist", "hermes", [(1, 3)], [], "yes"),
    ]
    with pytest.raises(ValueError):
        br.collapse_persona(readings, k=2, panel_size=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_beta_report.py -q`
Expected: FAIL — `AttributeError: module 'scripts.beta_report' has no attribute 'collapse_persona'`.

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/beta_report.py` (add `import statistics` at the top, next to `import json`):

```python
def collapse_persona(readings, *, k, panel_size):
    """Collapse one persona's per-model readings into a converged report.

    The within-persona consensus axis is the MODEL (spec §5.2). No cross-persona
    aggregation happens here — that is Phase 6.
    """
    _require(readings, "no readings to collapse")
    personas = {r["persona"] for r in readings}
    _require(len(personas) == 1, f"mixed personas in collapse: {sorted(personas)}")
    persona = next(iter(personas))
    m = len(readings)

    by_chapter: dict[int, list] = {}
    for r in readings:
        for pt in r["engagement_curve"]:
            by_chapter.setdefault(pt["chapter"], []).append(pt["score"])
    curve = []
    for ch in sorted(by_chapter):
        scores = by_chapter[ch]
        curve.append({"chapter": ch,
                      "central": statistics.median(scores),
                      "band": [min(scores), max(scores)]})

    counts: dict[int, int] = {}
    for r in readings:
        for ch in set(r["put_down_points"]):
            counts[ch] = counts.get(ch, 0) + 1
    consensus = sorted(ch for ch, c in counts.items() if c >= k)
    logged = sorted(ch for ch, c in counts.items() if c < k)

    tally = {"yes": 0, "no": 0, "n/a": 0}
    for r in readings:
        tally[r["would_buy_next"]["verdict"]] += 1
    denominator = m - tally["n/a"]

    distinct_models = sorted({r["model"] for r in readings})
    return {
        "schema": SCHEMA,
        "persona": persona,
        "driver": DRIVER_BY_PERSONA[persona],
        "panel": {"m": m, "k": k, "panel_size": panel_size,
                  "distinct_models": distinct_models,
                  "degraded": len(distinct_models) < panel_size},
        "engagement_curve": curve,
        "put_down_points": {"consensus": consensus, "logged": logged},
        "would_buy_next": {"tally": tally, "denominator": denominator},
    }


def serialize_converged(report) -> str:
    return ("---\n"
            f"schema: {report['schema']}\n"
            f"persona: {report['persona']}\n"
            f"driver: {report['driver']}\n"
            "kind: beta-converged\n"
            "---\n"
            + json.dumps(report, sort_keys=True, indent=2) + "\n")


def write_converged(out_dir, report) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report['persona']}.converged.md"
    path.write_text(serialize_converged(report), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_beta_report.py -q`
Expected: PASS (12 tests total).

- [ ] **Step 5: Commit**

```bash
git add scripts/beta_report.py tests/test_beta_report.py
git commit -m "feat(beta): per-persona cross-model collapser (k-of-m consensus, n/a-excluded denominator)"
```

---

### Task 3: The six persona files

**Files:**
- Create: `config/beta-readers/personas/cozy-loyalist.md`
- Create: `config/beta-readers/personas/puzzle-hawk.md`
- Create: `config/beta-readers/personas/arc-reader.md`
- Create: `config/beta-readers/personas/romance-reader.md`
- Create: `config/beta-readers/personas/impatient-skimmer.md`
- Create: `config/beta-readers/personas/newcomer-outsider.md`
- Test: `tests/test_beta_scaffold.py`

**Interfaces:**
- Consumes: `DRIVER_BY_PERSONA` (Task 1) — each file's `name`/`driver` frontmatter must match a mapping entry.
- Produces: persona files the `/beta-read` command (Task 6) loads by filename, parsed via `scripts.penny_meta.parse_frontmatter`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_beta_scaffold.py
from pathlib import Path
from scripts.penny_meta import parse_frontmatter
from scripts.beta_report import DRIVER_BY_PERSONA

ROOT = Path(__file__).resolve().parents[1]
PERSONA_DIR = ROOT / "config/beta-readers/personas"


def test_all_six_personas_present():
    names = {p.stem for p in PERSONA_DIR.glob("*.md")}
    assert names == set(DRIVER_BY_PERSONA), f"persona set mismatch: {names}"


def test_each_persona_declares_matching_driver():
    for path in PERSONA_DIR.glob("*.md"):
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        assert fm["name"] == path.stem
        assert fm["driver"] == DRIVER_BY_PERSONA[path.stem], path.stem
        assert "primary_axes" in fm


def test_only_arc_reader_declares_facets():
    for path in PERSONA_DIR.glob("*.md"):
        fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        facets = str(fm.get("facets", "[]"))
        if path.stem == "arc-reader":
            assert "self" in facets and "place" in facets
        else:
            assert "self" not in facets and "place" not in facets, path.stem


def test_newcomer_states_frozen_lexicon_cold_invariant():
    text = (PERSONA_DIR / "newcomer-outsider.md").read_text(encoding="utf-8").lower()
    assert "zero lexicon fluency" in text
    assert "regardless of series position" in text


def test_romance_authorizes_na_verdict():
    text = (PERSONA_DIR / "romance-reader.md").read_text(encoding="utf-8").lower()
    assert "n/a" in text and "romantic thread" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_beta_scaffold.py -q`
Expected: FAIL — `test_all_six_personas_present` errors (directory/files absent).

- [ ] **Step 3: Create the six persona files**

`config/beta-readers/personas/cozy-loyalist.md`:

```markdown
---
name: cozy-loyalist
driver: comfort-tone
primary_axes: [emotional_beats, would_buy_next]
facets: []
---
# Beta Reader — The Cozy Loyalist

You read cozy mysteries for the comfort contract: warmth, gentle humour, a strong
sense of place, and order restored by the end. You are the reader who *feels it*
when that contract breaks — gratuitous violence, real bleakness, cynicism, cruelty
that lingers. Setting-warmth is part of comfort: a town that feels like somewhere
you'd want to return to is the promise being kept.

React as a reader, not a critic. You have NOT been told any craft rules, the
outline, or the solution — you only have the text. Report what you felt, where,
and whether you'd buy the next book. Do not classify *why* you would or wouldn't —
just yes / no.
```

`config/beta-readers/personas/puzzle-hawk.md`:

```markdown
---
name: puzzle-hawk
driver: fairness
primary_axes: [whodunit_guess]
facets: []
---
# Beta Reader — The Puzzle Hawk

You read to solve. You track suspects, means, motive, and opportunity, and you try
to name the culprit before the reveal. Note the chapter where you first felt sure,
and who you named. Guessing too early means the clues were over-telegraphed;
never being able to guess means the mystery was unfair or muddy.

React as a reader, not an inspector. You have NOT been told the solution or any
fair-play rules — only the text. Report your running guess, your confusion points,
and whether you'd buy the next book (yes / no only).
```

`config/beta-readers/personas/arc-reader.md`:

```markdown
---
name: arc-reader
driver: transformation
primary_axes: [emotional_beats, would_buy_next]
facets: [self, place]
---
# Beta Reader — The Arc Reader

You read for the protagonist's interior journey: does she change as a person, is
the sea-change earned, is the growth real rather than asserted. You are indifferent
to romance specifically — you care about transformation. Her relationship to the
town is part of that arc: belonging-to-place is interiority pointed at setting.

If you would not buy the next book, you may tag *which* facet fell flat: `self`
(her interior arc) or `place` (her belonging to the town). That facet is the one
judgment you make about your verdict — otherwise just answer yes / no.

React as a reader, not a critic. You have only the text — no outline, no rules.
```

`config/beta-readers/personas/romance-reader.md`:

```markdown
---
name: romance-reader
driver: chemistry
primary_axes: [emotional_beats, would_buy_next]
facets: []
---
# Beta Reader — The Romance Reader

You read for relational tension and payoff: chemistry, slow-burn pacing, the
will-they/won't-they, whether the romantic beats land or feel perfunctory. Your
would-buy verdict is specifically *"did the romantic thread leave me wanting the
next book?"*

If this book carries **no live romantic thread at all**, your verdict is `n/a` —
NOT `no`. `n/a` means "there was nothing here for me to read"; `no` means "there
was a romance and it failed me." Keep them distinct.

React as a reader. You have only the text — no outline, no rules, no solution.
```

`config/beta-readers/personas/impatient-skimmer.md`:

```markdown
---
name: impatient-skimmer
driver: pace
primary_axes: [engagement_curve, put_down_points]
facets: []
---
# Beta Reader — The Impatient Skimmer

You read for momentum and bail the moment the pace sags. Rate each chapter's
engagement 1–5 as you go, and note every chapter where you nearly put the book
down. You are the reader who feels a sagging middle from the inside.

React as a reader, not a structure analyst. You have only the text. Report your
per-chapter engagement curve, your put-down points, and whether you'd buy the next
book (yes / no only).
```

`config/beta-readers/personas/newcomer-outsider.md`:

```markdown
---
name: newcomer-outsider
driver: onboarding
primary_axes: [confusion_points]
facets: []
---
# Beta Reader — The Newcomer-Outsider

You enter with **zero lexicon fluency regardless of series position** — you have
never learned this town's vocabulary, idiom, or local references. Flag any term,
idiom, or local reference the narration uses as if you already knew it. You test
one thing: can a reader who has not learned the lexicon still follow the book?

This is vocabulary cold-start only — you are NOT pretending you've never met the
characters (a book read in isolation is already character-cold). You react as a
real first-time-in-this-world reader. You have only the text. Report your
confusion points and whether you'd buy the next book (yes / no only).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_beta_scaffold.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add config/beta-readers/personas/ tests/test_beta_scaffold.py
git commit -m "feat(beta): six persona files (locked roster) with stamped-driver frontmatter"
```

---

### Task 4: `beta-protocol.md` — reaction-report schema

**Files:**
- Create: `config/beta-readers/beta-protocol.md`
- Test: `tests/test_beta_scaffold.py` (append)

**Interfaces:**
- Consumes: nothing structural — documents the shapes produced by `beta_report.py` (Tasks 1–2).
- Produces: the human-readable contract the `beta-reader` agent (Task 5) and `/beta-read` command (Task 6) reference.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_beta_scaffold.py  (append)
def test_beta_protocol_documents_contract_and_phase6_seam():
    text = (ROOT / "config/beta-readers/beta-protocol.md").read_text(encoding="utf-8").lower()
    # all §10 contract fields named
    for field in ["engagement_curve", "put_down_points", "whodunit_guess",
                  "confusion_points", "emotional_beats", "would_buy_next"]:
        assert field in text, field
    # the three serialization rules
    assert "n/a" in text and "first-class" in text          # rule 2
    assert "stamp" in text                                   # rule 3 (stamped driver)
    assert "{value, lens}" in text or "value, lens" in text  # rule 1
    # the seam
    assert "phase 6" in text
    assert "cross-persona" in text
    # non-blocking
    assert "non-blocking" in text or "never block" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_beta_scaffold.py::test_beta_protocol_documents_contract_and_phase6_seam -q`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Create the protocol file**

`config/beta-readers/beta-protocol.md`:

```markdown
# beta-protocol.md — Beta reaction-report format (design §5c, §10)

Beta readers react to assembled prose and report **experience**, never rules.
Output is **non-blocking** — it never holds a gate. Two artifacts.

## Raw reading — one per (persona, model)

The §10 contract fields, produced by a single blind `beta-reader` sub-agent and
serialized by `scripts/beta_report.py`:

- `engagement_curve` — per-chapter `{chapter, score}` (1–5).
- `put_down_points` — chapters where the reader nearly stopped.
- `whodunit_guess` — `{name, chapter}` (first chapter the reader felt sure).
- `confusion_points` — places the reader could not follow.
- `emotional_beats` — `[{beat, lens}]`.
- `would_buy_next` — `{verdict, driver, facet?}`.
- `notes` — free text.

### Three serialization rules

1. **Shared-field rule.** Any field with more than one primary owner serializes as
   `{value, lens}`, where `lens` = the emitting persona's stamped lens. Applies to
   `emotional_beats` (`[{beat, lens}]`) and `would_buy_next` (`{verdict, driver}`).
   This keeps cross-persona convergence computable, not coincidental.
2. **`n/a` is a first-class verdict, distinct from `no`.** A persona that cannot
   read an axis in a given book (e.g. the Romance Reader on a romance-less book)
   returns `n/a`, which is **excluded from the `would_buy_next` denominator** — it
   is never counted as a failure.
3. **`driver` is stamped, not reader-picked.** The reader emits only
   `yes | no | n/a`; the harness stamps `driver` from the persona's lens. The Arc
   Reader's `facet` (`self | place`) is the only reader-chosen sub-tag.

## Converged report — one per persona

`scripts/beta_report.py` collapses a persona's `M` model-readings (the within-
persona consensus axis is the **model**):

- `engagement_curve` — per chapter `{central, band:[min,max]}`.
- `put_down_points` — `{consensus, logged}`; a chapter is consensus iff flagged by
  `>= beta_consensus_k` of the `M` readings, else logged.
- `would_buy_next` — `{tally, denominator}` (`n/a` excluded from the denominator).
- `panel` — `{m, k, panel_size, distinct_models, degraded}`.

## Cross-persona rollup — [Phase 6]

Consensus *across* personas (do put-down points / "would not buy" span personas?)
and the escalation into showrunner book-approval (P0.8) are the **revision-priority
report**, built in **Phase 6**. Phase 5 stops at per-persona converged reports.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_beta_scaffold.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add config/beta-readers/beta-protocol.md tests/test_beta_scaffold.py
git commit -m "feat(beta): beta-protocol.md reaction-report schema + Phase-6 seam"
```

---

### Task 5: `beta-reader` agent

**Files:**
- Create: `.claude/agents/beta-reader.md`
- Test: `tests/test_beta_scaffold.py` (append)

**Interfaces:**
- Consumes: a persona file (Task 3) + manuscript text; writes via `beta_report.py` (Tasks 1–2).
- Produces: the sub-agent dispatched by `/beta-read` (Task 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_beta_scaffold.py  (append)
def test_beta_reader_agent_is_blind_and_well_formed():
    path = ROOT / ".claude/agents/beta-reader.md"
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert fm["name"] == "beta-reader"
    assert "description" in fm
    text = path.read_text(encoding="utf-8").lower()
    # blind contract: only text + persona file
    assert "persona" in text and "text" in text
    assert "no ledger" in text or "no ledgers" in text
    assert "no solution" in text
    # reacts, does not rule-reason; driver stamped not picked
    assert "react" in text
    assert "yes" in text and "no" in text and "n/a" in text
    assert "beta_report.py" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_beta_scaffold.py::test_beta_reader_agent_is_blind_and_well_formed -q`
Expected: FAIL — `FileNotFoundError`.

- [ ] **Step 3: Create the agent file**

`.claude/agents/beta-reader.md`:

```markdown
---
name: beta-reader
description: Blind book-level beta reader — reacts as one reader persona to assembled prose; reports experience, never rules.
---
# Beta Reader

**Role posture:** blind reaction reader (design §10). Reports *experience* —
"what is this like to read?" — never inspects against rules. A reader who knows
the rules starts inspecting instead of reacting.

**Independence:** receives ONLY `{ text, persona_file }`. No ledgers, no outline,
no solution, no rubrics, no other personas' reads — the same blindness a real
reader has.

**Inputs:** `{ text, persona_file }`.

**Outputs:** one raw reading written via `scripts/beta_report.py`
(`build_raw_reading` → `write_raw_reading`) into the run's reports dir. The
`would_buy_next` verdict is `yes | no | n/a` ONLY — you choose the verdict; you do
NOT choose the `driver` (the harness stamps it from the persona's lens). The Arc
Reader's `facet` (`self | place`) is the only sub-tag you may set.

**Instructions:**

1. Read the persona file. Adopt its lens and primary axes; read as that one reader.
2. Read the manuscript text start to finish as a reader, not an analyst. You have
   no rules, no outline, no solution — only the text.
3. Produce the §10 fields per `config/beta-readers/beta-protocol.md`: per-chapter
   `engagement_curve`, `put_down_points`, `whodunit_guess {name, chapter}`,
   `confusion_points`, `emotional_beats`, `would_buy_next` (`yes | no | n/a`), and
   `notes`. Romance Reader: return `n/a` (not `no`) when there is no live romantic
   thread.
4. Write the raw reading via `beta_report.py`. Do not classify *why* you would or
   would not buy next; emit only the verdict (and, for the Arc Reader, the facet).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_beta_scaffold.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/beta-reader.md tests/test_beta_scaffold.py
git commit -m "feat(beta): blind beta-reader agent (text + persona only)"
```

---

### Task 6: `/beta-read` command + `beta_consensus_k` run-config tunable

**Files:**
- Create: `.claude/commands/beta-read.md`
- Modify: `config/run-config.md` (add `beta_consensus_k` to the run-mode flags block)
- Test: `tests/test_beta_scaffold.py` (append) and `tests/test_run_config.py` (modify)

**Interfaces:**
- Consumes: `beta_models`, `panel_size`, `beta_consensus_k` from run-config; the `beta-reader` agent (Task 5); `beta_report.collapse_persona` / `write_converged` (Task 2); the six persona files (Task 3).
- Produces: the user-facing `/beta-read <path>` entry point. Terminal — nothing downstream in Phase 5 consumes its output (Phase 6 does).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_beta_scaffold.py  (append)
def test_beta_read_command_fans_out_and_is_non_blocking():
    text = (ROOT / ".claude/commands/beta-read.md").read_text(encoding="utf-8").lower()
    assert "beta_models" in text and "panel_size" in text and "beta_consensus_k" in text
    assert "beta-reader" in text                 # dispatches the agent
    assert "collapse_persona" in text            # per-persona collapse step
    assert "reachable" in text                   # reachability degradation handling
    # non-blocking guarantees (global constraint)
    assert "current-stage" in text and "not" in text
    assert "blocking" in text
    # input-agnostic: takes a path, not a book number
    assert "<path>" in text or "$1" in text
```

Add to `tests/test_run_config.py` — insert `"beta_consensus_k"` into the
`REQUIRED_KEYS` set (in the "run-mode flags" group):

```python
    # run-mode flags (design §12)
    "cadence", "panel_size", "gate_mode", "escalation_scope", "ledger_approval",
    "beta_consensus_k",
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_beta_scaffold.py tests/test_run_config.py -q`
Expected: FAIL — command file missing; `test_run_config_declares_all_required_keys` reports `beta_consensus_k` missing.

- [ ] **Step 3a: Add the run-config tunable**

In `config/run-config.md`, inside the run-mode flags YAML block (design §12), add the line after `panel_size`:

```yaml
beta_consensus_k: 2                # ≥K-of-M beta models must flag a put-down for
                                   # per-persona consensus; default = majority of
                                   # panel_size (book-level panel_size: 3 → 2); tunable
```

- [ ] **Step 3b: Create the command file**

`.claude/commands/beta-read.md`:

```markdown
---
description: Book-level beta read — fan the six personas across reachable beta_models on an assembled text, write per-persona converged reaction reports. Non-blocking.
argument-hint: <path-to-text> [--out <dir>]
---
# /beta-read

The beta-reader layer (design §5c, §10). **Input-agnostic:** takes a text path —
a finalized chapter fixture now, `book-NN.manuscript.md` in Phase 6 — and runs the
six blind reader personas on it. Beta is **non-blocking**: this command never
writes `.penny/current-stage` and never emits `BLOCKING:` lines.

## Steps

1. **Parse args:** `path=$1` (the text to read); optional `--out <dir>` (default
   `<dir-of-path>/beta-reports/`). Read the text once.

2. **Read run-config** (`config/run-config.md`, via `parse_yaml_blocks`):
   `beta_models`, `panel_size`, `beta_consensus_k`. Resolve the **reachable**
   subset of `beta_models` (skip models the adapter layer cannot reach today —
   cross-model access is rate-limited, §10).

3. **Fan out.** For each of the six personas in
   `config/beta-readers/personas/*.md`, dispatch up to `panel_size` `beta-reader`
   sub-agents across **distinct** reachable models. If fewer models are reachable
   than `panel_size`, repeat-sample the reachable ones (the collapser flags the
   panel `degraded`). Each sub-agent receives ONLY `{ text, persona_file }` — no
   ledgers, outline, solution, or rules.

4. **Each sub-agent** writes one raw reading via `scripts/beta_report.py`
   (`build_raw_reading` → `write_raw_reading`) into the `--out` dir.

5. **Collapse.** For each persona, load its raw readings and call
   `beta_report.collapse_persona(readings, k=beta_consensus_k, panel_size=panel_size)`,
   then `write_converged(out_dir, report)` → `<persona>.converged.md`.

6. **Report** to the showrunner: the six per-persona converged reports (engagement
   curves, consensus put-down points, would-buy tallies), noting any `degraded`
   panels. Do **NOT** aggregate across personas — the cross-persona revision-priority
   report is Phase 6. Do **NOT** write `.penny/current-stage`; this stage is
   non-blocking and outside the gate.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_beta_scaffold.py tests/test_run_config.py -q`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: PASS (all prior tests + the new beta tests; was 169 at Phase-4 close, now higher).

- [ ] **Step 6: Commit**

```bash
git add .claude/commands/beta-read.md config/run-config.md tests/test_beta_scaffold.py tests/test_run_config.py
git commit -m "feat(beta): input-agnostic /beta-read command + beta_consensus_k tunable"
```

---

## Self-Review

**Spec coverage:**
- §2 persona files → Task 3 ✓ · `beta-protocol.md` → Task 4 ✓ · `beta-reader` agent → Task 5 ✓ · `beta_report.py` → Tasks 1–2 ✓ · `/beta-read` command → Task 6 ✓ · `beta_consensus_k` → Task 6 ✓ · tests → every task ✓
- §4 roster (6 personas, drivers, arc facets, newcomer invariant, romance n/a) → Task 3 ✓
- §5.1 three rules (`{value,lens}`, n/a-first-class, stamped driver) → Tasks 1 (build) + 4 (doc) ✓
- §5.2 two artifacts (raw + converged) → Tasks 1, 2 ✓
- §6 runner fan-out + collapser + run-config → Tasks 2, 6 ✓
- §7 blind agent → Task 5 ✓
- §8 testing posture → all tasks ✓
- §9 Phase-6 seam (no cross-persona rollup) → asserted in Tasks 4, 6; absent from code by construction ✓
- §10 out-of-scope (no per-chapter site, no gating, non-blocking) → Global Constraints + Task 6 assertions ✓

**Placeholder scan:** no TBD/TODO; every code step shows complete code; every test step shows real assertions. ✓

**Type consistency:** `DRIVER_BY_PERSONA`, `VERDICTS`, `ARC_FACETS`, `SCHEMA`, `build_raw_reading`, `write_raw_reading`, `collapse_persona`, `write_converged` are named identically across Tasks 1, 2, 3, 5, 6. The raw-reading dict keys consumed by `collapse_persona` (`persona`, `model`, `engagement_curve[{chapter,score}]`, `put_down_points`, `would_buy_next{verdict}`) match what `build_raw_reading` produces. ✓
