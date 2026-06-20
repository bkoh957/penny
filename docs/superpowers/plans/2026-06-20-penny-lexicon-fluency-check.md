# Lexicon Fluency Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the newcomer fluency dial (`narration_ok_from_stage`) deterministically enforced by a Tier-3 evidence-only checker, instead of left to an inspector's fuzzy recall.

**Architecture:** Extract a shared quote-span primitive into `scripts/penny_text.py` (shared = where the quotes are; per-caller = policy), build a narration extractor on top of it, add `scripts/lexicon_check.py` (evidence-only, never `BLOCKING:`), migrate the lexicon to YAML with a required `auto_detectable` field validated at lock time, and store the current `fluency_stage` in a machine-readable `canon-meta` header in canon-core.

**Tech Stack:** Python 3.14, pytest 9, PyYAML 6 (already a runtime dep via `voice_drift`). Tests live in `tests/`, run with `python3 -m pytest` (pythonpath `.`, imports as `from scripts.X import ...`).

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-06-20-penny-lexicon-fluency-check-design.md` — implement to it.
- **The tripwire (Task 1):** the factor-out is correct **iff `voice_drift` produces byte-identical results and the existing 89 tests stay green with NO edits to any test or fixture file.** `tests/test_voice_drift.py` imports `from scripts.voice_drift import analyze, load_config, segment_sentences` — those names MUST remain importable from `scripts.voice_drift` after the move (re-export them).
- **Evidence-only:** `lexicon_check.py` MUST NOT emit `BLOCKING:` lines — `blocking=[]` always. The blocking call stays with `inspector-voice` (same rule as `voice_drift`).
- **Fail-loud, no silent defaults:** missing config / required field / stage → `SystemExit` with a clear message naming the offender. Never assume a default.
- **Required lexicon fields:** `term`, `narration_ok_from_stage`, `auto_detectable` (validated whole-lexicon at lock time, naming every offender — not per-chapter).
- **Stage ordering** is a fixed in-code enum: `OUTSIDER` < `SETTLING` < `BELONGING`.
- **Verdict envelope:** write via `scripts.penny_verdict.write_verdict(out_dir, producer, kind, target, name, blocking, notes, metrics, evidence, score=None)`.
- **Frequent commits:** one commit per task. Commit message trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Scope boundary:** do NOT change what `voice_drift` counts (no narration-only retrofit). Do NOT implement the insufficient-fluency (later-book) direction — that stays inspector judgment.

---

### Task 1: Factor text primitives into `scripts/penny_text.py` (behavior-preserving)

Pure move. `strip_frontmatter`, `_is_prose_line`, `segment_sentences` (and the `_ABBREV` set and `_words` helper they need) move out of `voice_drift.py` into a new shared module; `voice_drift` imports them back so its behavior is byte-identical.

**Files:**
- Create: `scripts/penny_text.py`
- Modify: `scripts/voice_drift.py` (remove the moved defs; import them from `penny_text`)
- Test: existing `tests/test_voice_drift.py` (UNCHANGED — it is the regression gate)

**Interfaces:**
- Produces (importable from `scripts.penny_text`): `strip_frontmatter(text: str) -> str`, `_is_prose_line(line: str) -> bool`, `segment_sentences(text: str) -> list[str]`, `_words(text: str) -> list[str]`, `_ABBREV: set[str]`.
- Produces (still importable from `scripts.voice_drift`, re-exported): `segment_sentences`, `strip_frontmatter`.

- [ ] **Step 1: Establish the green baseline**

Run: `python3 -m pytest -q`
Expected: `89 passed`. Record this number — it must not change.

- [ ] **Step 2: Create `scripts/penny_text.py` with the moved primitives**

```python
"""Shared prose text primitives for Penny's voice-related checkers.

The quote layer is split deliberately: this module exposes WHERE the quotes are
(`quote_spans`, added in a later task) and the segmentation helpers that operate
over prose. Each caller applies its own policy on top — voice_drift only avoids
splitting a sentence mid-quote; lexicon_check removes dialogue entirely. Putting a
strip policy in here would force it on every caller, so it stays out.
"""
from __future__ import annotations

import re

_ABBREV = {"mr", "mrs", "ms", "dr", "st", "mt", "rev", "prof", "sr", "jr"}


def strip_frontmatter(text: str) -> str:
    """Remove a leading ---...--- block only; keep all prose. No crash if absent."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1:])
    return text


def _is_prose_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):                       # markdown heading
        return False
    if re.fullmatch(r"[-*]{3,}|(\* )+\*?", s):   # rule / scene-break (---, ***, * * *)
        return False
    return True


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def segment_sentences(text: str) -> list[str]:
    """Heuristic, dependency-free sentence splitter. Known failure modes: it is a
    heuristic over messy prose; abbreviations outside _ABBREV, nested quotes, and
    decimal numbers can mis-split. Counts are signal, not gospel."""
    prose = " ".join(l.strip() for l in strip_frontmatter(text).splitlines() if _is_prose_line(l))
    sentences: list[str] = []
    buf = ""
    i = 0
    quote_depth = 0
    while i < len(prose):
        ch = prose[i]
        buf += ch
        if ch in '"“”"':
            quote_depth = 0 if quote_depth else 1
        if ch == "." and prose[i:i + 3] == "...":
            buf += ".."
            i += 3
            continue
        if ch in ".!?":
            if quote_depth:
                i += 1
                continue
            m = re.search(r"(\w+)\.$", buf)
            if ch == "." and m and m.group(1).lower() in _ABBREV:
                i += 1
                continue
            rest = prose[i + 1:].lstrip()
            if rest == "" or rest[0].isupper() or rest[0] in '"“”':
                sentences.append(buf.strip())
                buf = ""
        i += 1
    if buf.strip():
        sentences.append(buf.strip())
    return [s for s in sentences if s]
```

> NOTE: copy the bodies verbatim from the current `voice_drift.py` (lines 44, 68–126, 129–130). The text above is that exact code. Do not "improve" it — byte-identical behavior is the requirement.

- [ ] **Step 3: Edit `scripts/voice_drift.py` to import from `penny_text`**

Remove the now-moved definitions (`_ABBREV`, `strip_frontmatter`, `_is_prose_line`, `segment_sentences`, `_words`) from `voice_drift.py`. Add, alongside the existing imports near the top (after `from scripts.penny_verdict import write_verdict`):

```python
from scripts.penny_text import (
    _ABBREV,
    _is_prose_line,
    _words,
    segment_sentences,
    strip_frontmatter,
)
```

`_PATTERNS`, `analyze`, `load_config`, `main` stay in `voice_drift.py` unchanged. The re-import keeps `from scripts.voice_drift import segment_sentences, strip_frontmatter` working for the test file.

- [ ] **Step 4: Run the regression gate — the tripwire**

Run: `python3 -m pytest -q`
Expected: `89 passed`, no test or fixture file modified. If any test fails or the count changed, the move was not behavior-preserving — fix `penny_text.py` until byte-identical, do NOT edit tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_text.py scripts/voice_drift.py
git commit -m "refactor(scripts): extract shared text primitives into penny_text.py

Behavior-preserving move of strip_frontmatter/_is_prose_line/segment_sentences
out of voice_drift; re-exported so the 89 tests stay green unchanged. Sets up
the shared quote primitive the lexicon check needs.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Add the quote-span primitive + narration extractor to `penny_text.py`

New capability: `quote_spans` (shared — where the double-quoted dialogue is) and `strip_dialogue` (policy on top — blank the dialogue, preserving length and newlines so a match offset on the result maps to the same line number as the original). `voice_drift` does NOT use these — its behavior is frozen.

**Files:**
- Modify: `scripts/penny_text.py`
- Create: `tests/test_penny_text.py`
- Create fixtures: `tests/fixtures/prose/narration_dialogue.md`

**Interfaces:**
- Consumes: nothing new.
- Produces (importable from `scripts.penny_text`): `quote_spans(text: str) -> list[tuple[int, int]]` (char-offset ranges of double-quoted dialogue, inclusive of the quote marks), `strip_dialogue(text: str) -> str` (same-length string with every dialogue span replaced by spaces; newlines preserved).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_penny_text.py`:

```python
from scripts.penny_text import quote_spans, strip_dialogue


def test_strip_dialogue_preserves_length_and_newlines():
    text = 'She walked home.\n"Get stuffed," he said.\nThe rain fell.'
    out = strip_dialogue(text)
    assert len(out) == len(text)                      # offsets stay aligned
    assert out.count("\n") == text.count("\n")        # line numbers stay aligned
    assert "Get stuffed" not in out                    # dialogue blanked
    assert "She walked home." in out                   # narration kept
    assert "he said." in out                           # said-bookend narration kept


def test_term_inside_quote_is_blanked_but_in_narration_is_kept():
    # 'arvo' inside dialogue must survive in the dialogue but be gone from narration;
    # 'arvo' in the narrative clause must remain.
    text = 'It was a quiet arvo.\n"See you this arvo," she called.'
    narration = strip_dialogue(text)
    assert "It was a quiet arvo." in narration          # narrative-clause term kept
    assert "See you this arvo" not in narration         # in-dialogue term removed


def test_apostrophe_is_not_treated_as_dialogue():
    text = "I'm fine and I don't care, the cat's tail twitched."
    out = strip_dialogue(text)
    assert out == text                                  # single quotes are apostrophes, untouched
    assert quote_spans(text) == []


def test_smart_quotes_are_stripped():
    text = "The wind rose. “It’s late,” Cora said."  # smart-quoted dialogue
    out = strip_dialogue(text)
    assert "late" not in out                            # dialogue content gone
    assert "The wind rose." in out                      # leading narration kept
    assert "Cora said." in out                          # said-bookend narration kept
    assert quote_spans(text)                             # span detected


def test_dialogue_spanning_a_blank_line_is_handled_conservatively():
    # Balanced double quotes across paragraphs: each quoted run is its own span.
    text = '"First line of speech."\n\n"Second line of speech."\nNarration after.'
    out = strip_dialogue(text)
    assert "First line of speech" not in out
    assert "Second line of speech" not in out
    assert "Narration after." in out
    assert out.count("\n") == text.count("\n")


def test_em_dash_text_without_quotes_is_narration():
    # House style is quoted dialogue; an em-dash line with no quotes is narration.
    text = "She paused — the arvo light slanting low — and frowned."
    assert strip_dialogue(text) == text
    assert quote_spans(text) == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_penny_text.py -v`
Expected: FAIL with `ImportError: cannot import name 'quote_spans'`.

- [ ] **Step 3: Implement `quote_spans` and `strip_dialogue`**

Append to `scripts/penny_text.py`:

```python
# Double-quote characters that open/close dialogue. Smart quotes are directional
# (U+201C opens, U+201D closes); straight ASCII " toggles. Single quotes are NEVER
# treated as dialogue — in cozy prose they are apostrophes (don't, cat's, 'I'm').
_OPEN_QUOTES = '"“'
_CLOSE_QUOTES = '"”'


def quote_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) char offsets of double-quoted dialogue runs, inclusive of
    the quote marks. Straight " toggles open/closed; smart quotes use direction.
    A run left unterminated at end-of-text is closed at end-of-text."""
    spans: list[tuple[int, int]] = []
    open_at: int | None = None
    for i, ch in enumerate(text):
        if open_at is None:
            if ch == '"' or ch in _OPEN_QUOTES:
                open_at = i
        else:
            if ch == '"' or ch in _CLOSE_QUOTES:
                spans.append((open_at, i + 1))
                open_at = None
    if open_at is not None:
        spans.append((open_at, len(text)))
    return spans


def strip_dialogue(text: str) -> str:
    """Return text with every dialogue span replaced by spaces, preserving overall
    length and all newlines so a match offset on the result maps to the same line
    number as the original. This is the narration extractor: it applies the 'remove
    dialogue' policy on top of `quote_spans`."""
    chars = list(text)
    for start, end in quote_spans(text):
        for i in range(start, end):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)
```

- [ ] **Step 4: Run to verify they pass + nothing regressed**

Run: `python3 -m pytest tests/test_penny_text.py -v && python3 -m pytest -q`
Expected: new tests PASS; total `95 passed` (89 + 6).

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_text.py tests/test_penny_text.py tests/fixtures/prose/narration_dialogue.md
git commit -m "feat(scripts): narration extractor (quote_spans + strip_dialogue) in penny_text

New, unproven capability with its own adversarial fixtures: dialogue removed,
said-bookend narration kept, in-quote term not surfaced, apostrophes safe, smart
quotes handled, length/newlines preserved for stable line numbers.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

> NOTE on the fixture file: `tests/fixtures/prose/narration_dialogue.md` is optional for these inline-string tests but create it with a short dialogue-dense passage (a paragraph of narration with embedded quoted dialogue including the word `arvo` inside a quote and in narration) so future tests can reuse it. Content:
> ```
> The arvo light slanted through the kitchen.
> "You right for the footy this arvo?" Bryn asked.
> Cora had no idea what the footy was. She nodded anyway.
> ```

---

### Task 3: Migrate the lexicon to YAML with `auto_detectable`

`config/setting-pack/lexicon.md` becomes a short schema doc; the data moves to `config/setting-pack/lexicon.yaml` with the new required `auto_detectable` boolean.

**Files:**
- Create: `config/setting-pack/lexicon.yaml`
- Modify: `config/setting-pack/lexicon.md` (demote to doc pointing at the YAML)
- Test: `tests/test_lexicon_schema.py`

**Interfaces:**
- Produces: `config/setting-pack/lexicon.yaml` with top-level key `terms:` → list of mappings, each: `term, gloss, register, speaker_type, freq_cap, narration_ok_from_stage, auto_detectable, notes`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lexicon_schema.py`:

```python
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LEXICON = REPO / "config/setting-pack/lexicon.yaml"
REQUIRED = ("term", "narration_ok_from_stage", "auto_detectable")
STAGES = {"OUTSIDER", "SETTLING", "BELONGING"}


def test_lexicon_yaml_loads_and_has_terms():
    data = yaml.safe_load(LEXICON.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and isinstance(data.get("terms"), list)
    assert data["terms"], "lexicon has no terms"


def test_every_term_has_required_fields_with_valid_types():
    data = yaml.safe_load(LEXICON.read_text(encoding="utf-8"))
    for entry in data["terms"]:
        for field in REQUIRED:
            assert field in entry, f"{entry.get('term', entry)} missing {field}"
        assert isinstance(entry["auto_detectable"], bool), entry["term"]
        assert entry["narration_ok_from_stage"] in STAGES, entry["term"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_lexicon_schema.py -v`
Expected: FAIL — `lexicon.yaml` does not exist (FileNotFoundError).

- [ ] **Step 3: Create `config/setting-pack/lexicon.yaml`**

```yaml
# Lexicon — authoritative data (schema fixed; contents swap per location).
# lexicon.md is the human doc; this file is what scripts read.
# Required on every entry: term, narration_ok_from_stage, auto_detectable.
# auto_detectable: false => homograph of standard English; lexicon_check leaves it
# to inspector-voice (carried as an inspector-only note, never a deterministic flag).
terms:
  - term: arvo
    gloss: afternoon
    register: casual
    speaker_type: local
    freq_cap: 2/ch
    narration_ok_from_stage: SETTLING
    auto_detectable: true
    notes: seed; verify regional use
  - term: servo
    gloss: petrol station
    register: casual
    speaker_type: local
    freq_cap: 1/ch
    narration_ok_from_stage: SETTLING
    auto_detectable: true
    notes: seed
  - term: the footy
    gloss: Australian Rules football
    register: casual
    speaker_type: local
    freq_cap: 1/ch
    narration_ok_from_stage: BELONGING
    auto_detectable: true
    notes: AFL loyalties intensely local — verify before lock
```

- [ ] **Step 4: Demote `config/setting-pack/lexicon.md` to a doc**

Replace the whole file with:

```markdown
# Lexicon (schema doc)

The authoritative lexicon data lives in **`lexicon.yaml`** (scripts read it; this
file is documentation only — do not duplicate rows here).

Schema (one mapping per entry under `terms:`):
`term | gloss | register | speaker_type | freq_cap | narration_ok_from_stage | auto_detectable | notes`

- `narration_ok_from_stage` couples each term to the fluency dial (`OUTSIDER` <
  `SETTLING` < `BELONGING`): a term whose stage is *later* than the book's current
  `fluency_stage`, appearing in **narration**, is a premature-term flag.
- `auto_detectable` (bool, required): `true` = safe to match mechanically
  (word-boundary). `false` = homograph of standard English; `lexicon_check.py` does
  not flag it — it is surfaced to `inspector-voice` as an inspector-only note.

`lexicon_check.py --validate` checks every entry has `term`,
`narration_ok_from_stage`, and `auto_detectable` before the lexicon is locked.

> **Accuracy note:** seeds are from general knowledge of Australian usage. Before a
> 13-book lock, a `research-notes.md` pass should verify coastal-Victorian idiom and
> AFL club loyalties.
```

- [ ] **Step 5: Run tests + commit**

Run: `python3 -m pytest tests/test_lexicon_schema.py -q && python3 -m pytest -q`
Expected: schema tests PASS; total `97 passed` (95 + 2).

```bash
git add config/setting-pack/lexicon.yaml config/setting-pack/lexicon.md tests/test_lexicon_schema.py
git commit -m "feat(config): migrate lexicon to YAML with required auto_detectable field

Data moves to lexicon.yaml (authoritative); lexicon.md demoted to schema doc, no
duplicated rows. Adds auto_detectable bool so the fluency check only mechanically
asserts on unambiguous terms.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Machine-readable `fluency_stage` via a `canon-meta` header

Add a `<!-- canon-meta: {...} -->` header to `canon-core.md` carrying `fluency_stage`, and a dependency-free `parse_canon_meta` reader in `penny_meta.py`. This adopts the demotion spec's header convention (the first real consumer) per the "adopt canon-meta when you touch canon-core structure" guidance.

**Files:**
- Modify: `series/continuity/canon-core.md` (add the header; keep the prose section)
- Modify: `scripts/penny_meta.py` (add `parse_canon_meta`)
- Test: `tests/test_penny_meta.py` (append cases)

**Interfaces:**
- Produces (importable from `scripts.penny_meta`): `parse_canon_meta(text: str) -> dict` — returns the key/value pairs from the first `<!-- canon-meta: {...} -->` comment; `{}` if absent. Handles flat scalar pairs (`{fluency_stage: OUTSIDER}`); sufficient for current use.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_penny_meta.py`:

```python
from scripts.penny_meta import parse_canon_meta


def test_parse_canon_meta_reads_flat_map():
    text = "# Canon Core\n<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->\nbody"
    meta = parse_canon_meta(text)
    assert meta["fluency_stage"] == "OUTSIDER"
    assert meta["id"] == "canon-core"


def test_parse_canon_meta_absent_returns_empty():
    assert parse_canon_meta("# No header here\njust prose") == {}


def test_real_canon_core_declares_a_valid_stage():
    from pathlib import Path
    repo = Path(__file__).resolve().parents[1]
    text = (repo / "series/continuity/canon-core.md").read_text(encoding="utf-8")
    meta = parse_canon_meta(text)
    assert meta.get("fluency_stage") in {"OUTSIDER", "SETTLING", "BELONGING"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_penny_meta.py -k canon_meta -v`
Expected: FAIL — `cannot import name 'parse_canon_meta'`.

- [ ] **Step 3: Implement `parse_canon_meta`**

Append to `scripts/penny_meta.py` (dependency-free, reusing `_parse_kv_lines`):

```python
import re as _re

_CANON_META_RE = _re.compile(r"<!--\s*canon-meta:\s*\{(.*?)\}\s*-->", _re.DOTALL)


def parse_canon_meta(text: str) -> dict:
    """Read the first ``<!-- canon-meta: {k: v, ...} -->`` header. Returns {} if
    absent. Supports flat scalar pairs (sufficient for fluency_stage); nested maps
    are deferred to the demotion machinery (Phase 8)."""
    m = _CANON_META_RE.search(text)
    if not m:
        return {}
    inner = m.group(1)
    # Split top-level commas (no nesting expected at this stage) into k: v lines.
    return _parse_kv_lines([part for part in inner.split(",")])
```

- [ ] **Step 4: Add the header to `series/continuity/canon-core.md`**

Insert the header immediately after the closing `---` of the existing frontmatter (before the `# Canon Core` heading). It must agree with the prose `## Fluency stage` section (currently OUTSIDER):

```markdown
<!-- canon-meta: {id: canon-core, fluency_stage: OUTSIDER} -->
```

Leave the `## Fluency stage (design §9 newcomer dial)` prose section as the human explanation.

- [ ] **Step 5: Run tests + commit**

Run: `python3 -m pytest tests/test_penny_meta.py -q && python3 -m pytest -q`
Expected: new cases PASS; total `100 passed` (97 + 3).

```bash
git add scripts/penny_meta.py series/continuity/canon-core.md tests/test_penny_meta.py
git commit -m "feat(canon): machine-readable fluency_stage via canon-meta header

Adopts the demotion spec's canon-meta HTML-comment convention (first consumer:
fluency_stage), with a dependency-free parse_canon_meta reader. Header co-located
with canon-core active-book state; prose section stays as the human explanation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `lexicon_check.py` — premature-term detection (evidence-only)

The core checker: load `lexicon.yaml` + the chapter's `fluency_stage` from canon-core, scan narration (dialogue stripped) for `auto_detectable: true` terms whose stage is later than the current stage, write an evidence-only verdict.

**Files:**
- Create: `scripts/lexicon_check.py`
- Test: `tests/test_lexicon_check.py`

**Interfaces:**
- Consumes: `scripts.penny_text.strip_dialogue`, `scripts.penny_meta.parse_canon_meta`, `scripts.penny_verdict.write_verdict`, PyYAML.
- Produces (importable from `scripts.lexicon_check`): `STAGE_RANK: dict[str,int]`, `load_lexicon(path) -> list[dict]`, `current_stage(canon_core_path) -> str`, `scan(text: str, terms: list[dict], stage: str) -> dict` (returns `{"flags": [...], "inspector_notes": [...]}` where each flag is `{"term","line","term_stage","current_stage"}`), `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lexicon_check.py`:

```python
import pytest

from scripts.lexicon_check import STAGE_RANK, scan

TERMS = [
    {"term": "arvo", "narration_ok_from_stage": "SETTLING", "auto_detectable": True},
    {"term": "the footy", "narration_ok_from_stage": "BELONGING", "auto_detectable": True},
    {"term": "bogan", "narration_ok_from_stage": "SETTLING", "auto_detectable": False},
]


def test_stage_rank_is_ordered():
    assert STAGE_RANK["OUTSIDER"] < STAGE_RANK["SETTLING"] < STAGE_RANK["BELONGING"]


def test_premature_term_in_narration_is_flagged():
    text = "It was a slow arvo in the town."
    result = scan(text, TERMS, "OUTSIDER")
    assert any(f["term"] == "arvo" and f["line"] == 1 for f in result["flags"])


def test_in_stage_term_is_not_flagged():
    text = "It was a slow arvo in the town."
    result = scan(text, TERMS, "SETTLING")     # arvo ok from SETTLING
    assert not any(f["term"] == "arvo" for f in result["flags"])


def test_term_inside_dialogue_is_not_flagged():
    text = '"See you this arvo," she said.'
    result = scan(text, TERMS, "OUTSIDER")
    assert not any(f["term"] == "arvo" for f in result["flags"])


def test_auto_detectable_false_is_inspector_note_not_flag():
    text = "He was a bit of a bogan, she thought."
    result = scan(text, TERMS, "OUTSIDER")
    assert not any(f["term"] == "bogan" for f in result["flags"])
    assert any(n["term"] == "bogan" for n in result["inspector_notes"])


def test_word_boundary_matches_whole_word_only():
    terms = [{"term": "servo", "narration_ok_from_stage": "SETTLING", "auto_detectable": True}]
    # '\b servo \b' matches the standalone word but NOT the plural 'servos'
    # (trailing 's' means no word boundary after 'servo').
    text = "Two servos lined the road; she stopped at the servo."
    result = scan(text, terms, "OUTSIDER")
    hits = [f for f in result["flags"] if f["term"] == "servo"]
    assert len(hits) == 1


def test_multiword_term_flagged():
    text = "She still didn't understand the footy."
    result = scan(text, TERMS, "SETTLING")   # the footy ok only from BELONGING
    assert any(f["term"] == "the footy" for f in result["flags"])
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_lexicon_check.py -v`
Expected: FAIL — `cannot import name 'scan'`.

- [ ] **Step 3: Implement `scripts/lexicon_check.py`**

```python
"""Lexicon fluency check — Tier-3, evidence-only.

Detects premature out-of-stage lexicon terms in NARRATION (dialogue removed). The
fluency dial is deterministic in one direction only — a term tagged for a later
stage appearing now is countable evidence. Insufficient idiom in later books is a
taste judgment and stays inspector-voice's job. Per the Phase-2a rule, this checker
NEVER emits BLOCKING: lines — the blocking call is inspector-voice's.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.penny_meta import parse_canon_meta
from scripts.penny_text import strip_dialogue
from scripts.penny_verdict import write_verdict

REPO = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = REPO / "config/setting-pack/lexicon.yaml"
DEFAULT_CANON_CORE = REPO / "series/continuity/canon-core.md"

STAGE_RANK = {"OUTSIDER": 0, "SETTLING": 1, "BELONGING": 2}
REQUIRED = ("term", "narration_ok_from_stage", "auto_detectable")


def load_lexicon(path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        sys.exit(f"lexicon_check: lexicon not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"lexicon_check: lexicon is not valid YAML ({path}): {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("terms"), list):
        sys.exit(f"lexicon_check: lexicon must have a 'terms:' list: {path}")
    return data["terms"]


def current_stage(canon_core_path) -> str:
    text = Path(canon_core_path).read_text(encoding="utf-8")
    meta = parse_canon_meta(text)
    stage = meta.get("fluency_stage")
    if stage not in STAGE_RANK:
        sys.exit(
            f"lexicon_check: canon-core declares no valid fluency_stage "
            f"(got {stage!r}); expected one of {sorted(STAGE_RANK)}"
        )
    return stage


def scan(text: str, terms: list[dict], stage: str) -> dict:
    """Return {'flags': [...], 'inspector_notes': [...]}. A flag fires iff the term
    is auto_detectable, word-boundary-matches in narration, and its stage outranks
    the current stage. auto_detectable: false terms become inspector-only notes."""
    cur = STAGE_RANK[stage]
    narration = strip_dialogue(text)
    flags: list[dict] = []
    notes: list[dict] = []
    for entry in terms:
        term = entry["term"]
        term_stage = entry["narration_ok_from_stage"]
        if STAGE_RANK[term_stage] <= cur:
            continue  # in-stage (or earlier) — allowed in narration now
        if not entry.get("auto_detectable", False):
            notes.append({"term": term, "term_stage": term_stage,
                          "reason": "auto_detectable=false; inspector judgment"})
            continue
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.I)
        for m in pattern.finditer(narration):
            line = narration[:m.start()].count("\n") + 1
            flags.append({"term": term, "line": line,
                          "term_stage": term_stage, "current_stage": stage})
    return {"flags": flags, "inspector_notes": notes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lexicon fluency check (evidence-only).")
    ap.add_argument("chapter", help="path to the chapter markdown file")
    ap.add_argument("--out", default=None, help="reviews dir to write lexicon-fluency.md")
    ap.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    ap.add_argument("--canon-core", default=str(DEFAULT_CANON_CORE))
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    terms = load_lexicon(args.lexicon)
    stage = current_stage(args.canon_core)
    text = Path(args.chapter).read_text(encoding="utf-8")
    result = scan(text, terms, stage)

    flags, notes = result["flags"], result["inspector_notes"]
    summary = [f"current fluency_stage: {stage}",
               f"premature-term flags: {len(flags)} (evidence-only; inspector decides)"]
    for n in notes:
        summary.append(f"inspector-only term (auto_detectable=false): {n['term']} "
                       f"(ok from {n['term_stage']})")

    out_dir = args.out or str(Path(args.chapter).parent)
    write_verdict(
        out_dir=out_dir, producer="lexicon_check.py", kind="deterministic-checker",
        target=args.target, name="lexicon-fluency",
        blocking=[],  # evidence-only — never blocks
        notes=summary,
        metrics={"current_stage": stage, "flag_count": len(flags),
                 "inspector_note_count": len(notes)},
        evidence=flags[:5],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests + the full suite**

Run: `python3 -m pytest tests/test_lexicon_check.py -v && python3 -m pytest -q`
Expected: new tests PASS; total `107 passed` (100 + 7).

- [ ] **Step 5: Add a verdict-shape integration test**

Append to `tests/test_lexicon_check.py`:

```python
def test_main_writes_evidence_only_verdict(tmp_path):
    from scripts.lexicon_check import main
    lexicon = tmp_path / "lex.yaml"
    lexicon.write_text(
        "terms:\n"
        "  - term: arvo\n    narration_ok_from_stage: SETTLING\n    auto_detectable: true\n",
        encoding="utf-8")
    canon = tmp_path / "canon.md"
    canon.write_text("<!-- canon-meta: {fluency_stage: OUTSIDER} -->\n", encoding="utf-8")
    chap = tmp_path / "ch.md"
    chap.write_text("It was a slow arvo.\n", encoding="utf-8")
    out = tmp_path / "reviews"
    rc = main([str(chap), "--out", str(out), "--lexicon", str(lexicon),
               "--canon-core", str(canon), "--target", "book-01/ch-01"])
    assert rc == 0
    verdict = (out / "lexicon-fluency.md").read_text(encoding="utf-8")
    assert "producer: lexicon_check.py" in verdict
    assert "kind: deterministic-checker" in verdict
    assert "BLOCKING:" not in verdict          # evidence-only, never blocks
    assert "arvo" in verdict


def test_missing_stage_hard_fails(tmp_path):
    from scripts.lexicon_check import current_stage
    canon = tmp_path / "canon.md"
    canon.write_text("# no header\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        current_stage(canon)
```

Run: `python3 -m pytest tests/test_lexicon_check.py -q && python3 -m pytest -q`
Expected: total `109 passed` (107 + 2).

- [ ] **Step 6: Commit**

```bash
git add scripts/lexicon_check.py tests/test_lexicon_check.py
git commit -m "feat(scripts): lexicon_check.py — premature-term fluency detection (evidence-only)

Loads lexicon.yaml + canon-core fluency_stage, scans narration (dialogue stripped),
flags auto_detectable terms whose stage outranks the current stage. Never emits
BLOCKING; auto_detectable=false terms become inspector-only notes. Word-boundary
matching; multi-word terms supported.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `--validate` mode (whole-lexicon fail-loud) + stage drift-guard

Two config-gate guards. `--validate` checks every lexicon entry has the required fields, naming EVERY offender at once (lock-time, not mid-scan). The drift-guard surfaces a disagreement between the `canon-meta` stage and the prose `## Fluency stage` section.

**Files:**
- Modify: `scripts/lexicon_check.py` (add `validate_lexicon`, `prose_stage`, `stage_drift`, and `--validate` CLI branch)
- Test: `tests/test_lexicon_check.py` (append)

**Interfaces:**
- Consumes: `load_lexicon`, `STAGE_RANK`, `REQUIRED` from Task 5.
- Produces (importable from `scripts.lexicon_check`): `validate_lexicon(terms: list[dict]) -> list[str]` (returns a list of human-readable error strings, one per offending entry/field; empty = valid), `prose_stage(canon_core_text: str) -> str | None` (the stage named in the `## Fluency stage` prose, or None), `stage_drift(canon_core_text: str) -> str | None` (a message if `canon-meta` and prose disagree, else None).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_lexicon_check.py`:

```python
from scripts.lexicon_check import validate_lexicon, prose_stage, stage_drift


def test_validate_names_every_offender():
    terms = [
        {"term": "ok", "narration_ok_from_stage": "SETTLING", "auto_detectable": True},
        {"term": "bad1", "auto_detectable": True},                    # missing stage
        {"narration_ok_from_stage": "SETTLING", "auto_detectable": True},  # missing term
        {"term": "bad3", "narration_ok_from_stage": "SETTLING"},      # missing auto_detectable
        {"term": "bad4", "narration_ok_from_stage": "NOPE", "auto_detectable": True},  # bad stage
    ]
    errors = validate_lexicon(terms)
    blob = " | ".join(errors)
    assert "bad1" in blob and "bad3" in blob and "bad4" in blob
    assert "term" in blob                       # the missing-term entry is named
    assert len(errors) >= 4                       # every offender reported, not just first


def test_validate_clean_lexicon_is_empty():
    terms = [{"term": "arvo", "narration_ok_from_stage": "SETTLING", "auto_detectable": True}]
    assert validate_lexicon(terms) == []


def test_prose_stage_reads_bolded_stage():
    text = "## Fluency stage\n- **OUTSIDER** (Books 1-2): narration is standard English.\n"
    assert prose_stage(text) == "OUTSIDER"


def test_stage_drift_detects_mismatch():
    text = ("<!-- canon-meta: {fluency_stage: SETTLING} -->\n"
            "## Fluency stage\n- **OUTSIDER** (Books 1-2): ...\n")
    assert stage_drift(text) is not None
    aligned = ("<!-- canon-meta: {fluency_stage: OUTSIDER} -->\n"
               "## Fluency stage\n- **OUTSIDER** (Books 1-2): ...\n")
    assert stage_drift(aligned) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_lexicon_check.py -k "validate or prose or drift" -v`
Expected: FAIL — `cannot import name 'validate_lexicon'`.

- [ ] **Step 3: Implement the validators**

Add to `scripts/lexicon_check.py` (after `current_stage`):

```python
def validate_lexicon(terms: list[dict]) -> list[str]:
    """Whole-lexicon required-field check. Returns one error string per offending
    entry/field — ALL of them, never just the first. Empty list == valid."""
    errors: list[str] = []
    for i, entry in enumerate(terms):
        label = entry.get("term", f"<entry #{i + 1} missing 'term'>")
        for field in REQUIRED:
            if field not in entry:
                errors.append(f"{label}: missing required field '{field}'")
        if "auto_detectable" in entry and not isinstance(entry["auto_detectable"], bool):
            errors.append(f"{label}: auto_detectable must be true/false")
        stage = entry.get("narration_ok_from_stage")
        if stage is not None and stage not in STAGE_RANK:
            errors.append(f"{label}: invalid narration_ok_from_stage {stage!r}")
    return errors


_PROSE_STAGE_RE = re.compile(r"\*\*(OUTSIDER|SETTLING|BELONGING)\*\*")


def prose_stage(canon_core_text: str) -> "str | None":
    """The first bolded stage name in the prose body, or None."""
    m = _PROSE_STAGE_RE.search(canon_core_text)
    return m.group(1) if m else None


def stage_drift(canon_core_text: str) -> "str | None":
    """A message if the canon-meta stage and the prose stage disagree, else None.
    A missing prose stage is not drift (the machine value is authoritative)."""
    meta = parse_canon_meta(canon_core_text).get("fluency_stage")
    prose = prose_stage(canon_core_text)
    if prose is not None and meta is not None and prose != meta:
        return (f"fluency_stage drift: canon-meta says {meta!r} but prose says "
                f"{prose!r} — reconcile (canon-meta is authoritative)")
    return None
```

- [ ] **Step 4: Wire `--validate` into `main`**

In `main`, add the flag and an early branch (before the per-chapter scan). Change the argparse so `chapter` is optional when `--validate` is given:

```python
    ap.add_argument("--validate", action="store_true",
                    help="validate the whole lexicon (lock-time gate) and exit")
```

Make `chapter` optional: change `ap.add_argument("chapter", ...)` to
`ap.add_argument("chapter", nargs="?", default=None, ...)`. Then at the top of `main` after parsing:

```python
    if args.validate:
        errors = validate_lexicon(load_lexicon(args.lexicon))
        drift = stage_drift(Path(args.canon_core).read_text(encoding="utf-8"))
        if drift:
            errors.append(drift)
        if errors:
            sys.exit("lexicon_check --validate FAILED:\n  - " + "\n  - ".join(errors))
        print("lexicon_check: OK (lexicon valid, no stage drift)")
        return 0
    if args.chapter is None:
        ap.error("chapter is required unless --validate is given")
```

Also fold the drift-guard into per-chapter runs: after computing `stage` in the scan path, append any drift message to `summary` (non-fatal evidence):

```python
    drift = stage_drift(Path(args.canon_core).read_text(encoding="utf-8"))
    if drift:
        summary.append(drift)
```

- [ ] **Step 5: Run tests + full suite**

Run: `python3 -m pytest tests/test_lexicon_check.py -q && python3 -m pytest -q`
Expected: new tests PASS; total `113 passed` (109 + 4).

- [ ] **Step 6: Smoke-test the validator against the real lexicon**

Run: `python3 scripts/lexicon_check.py --validate`
Expected: `lexicon_check: OK (lexicon valid, no stage drift)`.

- [ ] **Step 7: Commit**

```bash
git add scripts/lexicon_check.py tests/test_lexicon_check.py
git commit -m "feat(scripts): lexicon_check --validate (whole-lexicon, names every offender) + stage drift-guard

Lock-time validation reports all missing/invalid required fields at once, not
mid-scan. Drift-guard surfaces canon-meta vs prose fluency_stage disagreement
(fatal at --validate, non-fatal evidence per chapter).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Wire into `review-chapter` + widen `inspector-voice` scope

Run `lexicon_check.py` alongside `voice_drift.py` in the orchestrator, and give `inspector-voice` the lexicon, the current stage, and the new evidence file (plus the insufficient-fluency judgment the script can't make).

**Files:**
- Modify: `.claude/commands/review-chapter.md` (step 5 — add the lexicon checker)
- Modify: `.claude/agents/inspector-voice.md` (inputs + instructions)
- Test: none (orchestrator + agent prompts are markdown; covered by the script's own tests). Verify by inspection + a manual dry run.

**Interfaces:**
- Consumes: `scripts/lexicon_check.py` CLI from Tasks 5–6.

- [ ] **Step 1: Add the lexicon checker to `review-chapter.md` step 5**

After the `voice_drift.py` block in step 5, add:

````markdown
   ```bash
   python3 scripts/lexicon_check.py output/book-$book/chapters/ch-$chapter.draft.md \
     --out output/book-$book/chapters/ch-$chapter.reviews \
     --target book-$book/ch-$chapter
   ```
````

And add a sentence noting it is evidence-only (writes `lexicon-fluency.md`; never blocks; `inspector-voice` weighs it).

- [ ] **Step 2: Widen `inspector-voice.md` inputs and instructions**

In `.claude/agents/inspector-voice.md`:
- Add to **Inputs**: `config/setting-pack/lexicon.yaml`, the current `fluency_stage`, and the `lexicon-fluency.md` evidence file.
- Change instruction 3 from "Check fluency-stage discipline in narration" to:

```markdown
3. Fluency-stage discipline. If `lexicon-fluency.md` evidence is present, USE its
   premature-term flags — do not re-detect terms — and decide which are real fluency
   breaks vs benign collisions (a name clash, the protagonist quoting a local inside
   a narrative clause, a standard-English homograph). ALSO judge the direction the
   script cannot: insufficient local idiom for the current stage in the Belonging
   books (a taste call). Inspector-only notes (auto_detectable=false terms) are for
   you to eyeball — they are not deterministic violations.
```

- Keep instruction 4 (a fluency-stage break still goes in `blocking_issues`) — the inspector keeps the blocking call.

- [ ] **Step 3: Verify the full suite is still green**

Run: `python3 -m pytest -q`
Expected: `113 passed` (markdown edits don't change test count; this confirms nothing was broken).

- [ ] **Step 4: Manual dry run of the checker as the orchestrator would call it**

Create a throwaway chapter and run the exact command shape from step 1 against a temp reviews dir (or an existing draft if one exists), confirming `lexicon-fluency.md` is written with `kind: deterministic-checker` and no `BLOCKING:` line. Document the observed output in the task report.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands/review-chapter.md .claude/agents/inspector-voice.md
git commit -m "feat(review): wire lexicon_check into review-chapter + widen inspector-voice scope

lexicon_check runs beside voice_drift (evidence-only). inspector-voice gains the
lexicon, current stage, and lexicon-fluency.md evidence, and now judges the
insufficient-fluency direction the script cannot. Inspector keeps the blocking call.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the whole suite: `python3 -m pytest -q` → expect `113 passed`.
- [ ] Confirm the tripwire held: `git log --oneline` shows Task 1 changed only `scripts/`, no `tests/` or `tests/fixtures/` edits.
- [ ] `python3 scripts/lexicon_check.py --validate` → `OK`.
- [ ] Grep guard: `grep -n "BLOCKING" scripts/lexicon_check.py` returns only the `blocking=[]` / comment lines — the checker never emits a `BLOCKING:` string.

## Spec coverage map

- §2 evidence-only / both-not-either → Tasks 5 (evidence-only) + 7 (inspector scope).
- §3 shared module, shared=spans / per-caller=policy → Tasks 1 + 2.
- §3.1 tripwire (89 green, no fixture edits) → Task 1 Step 4 + Final verification.
- §3.2 voice_drift behavior frozen → Task 1 (no analyze change) + Global Constraints.
- §4 flag rule / stage rank / auto_detectable false → inspector note / word-boundary / multi-word → Task 5.
- §4.1 directional scope (premature only) → Task 5 (no later-direction code) + Task 7 instruction 3.
- §5 lexicon→YAML + auto_detectable + three required fields → Task 3.
- §5.1 lock-time validation naming every offender → Task 6.
- §6 canon-meta fluency_stage + parse_canon_meta + no-default fail-loud → Task 4 + Task 5 `current_stage`.
- §6.1 prose-vs-machine drift-guard → Task 6.
- §7 inspector-voice scope widening → Task 7.
- §9 wiring into review-chapter → Task 7.
