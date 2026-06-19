# Penny Phase 2a — Deterministic Tier-3 Checkers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Penny's two deterministic Tier-3 review checkers — `voice_drift.py` (statistical prose evidence) and `fairplay_check.py` (whodunit-ledger consistency) — plus the shared `penny_verdict.py` writer they both use, so the Phase 2b inspector bus has machine-produced verdicts to consume.

**Architecture:** Three new scripts under `scripts/`. `penny_verdict.py` owns the verdict-file format (markdown + frontmatter + `BLOCKING:` lines) in one place. `voice_drift.py` holds detection regex/algorithms in code and reads tunable thresholds + compounding lists from `config/voice-pack/ai-tics-config.yaml`; it emits **evidence only, never `BLOCKING:`**. `fairplay_check.py` reads a per-book `series/whodunit/book-NN.yaml` ledger plus `culprit_by_fraction` from `run-config.md`, and **may emit `BLOCKING:`** for fairness failures. Each is a standalone CLI, exactly how Phase 2b's `review-chapter` will invoke them.

**Tech Stack:** Python 3 (stdlib `re`, `json`, `statistics`, `pathlib`, `argparse`) · **PyYAML** (newly approved — first third-party runtime dep; nested human-edited config) · reuses `scripts/penny_meta.py` (flat frontmatter/yaml-block parsing) · pytest.

**Scope:** Phase 2a only (deterministic checkers). Out of scope → Phase 2b: Tier-1 inspector sub-agents, their rubrics, the `review-chapter` orchestration, two-signal conflict resolution, and prose-planting fairplay verification. Source spec: `docs/superpowers/specs/2026-06-19-penny-phase2a-deterministic-checkers-design.md`.

**The two-reader boundary (hold it explicit):** flat data → `penny_meta.py` (stdlib); nested human-edited data → PyYAML. `voice_drift.py` reads its config via PyYAML; `fairplay_check.py` reads the ledger via PyYAML and the single `culprit_by_fraction` scalar from `run-config.md` via `penny_meta`.

---

## File Structure

**Create:**
- `requirements.txt` — declares `PyYAML`.
- `scripts/penny_verdict.py` — shared verdict-file writer (`write_verdict(...)`).
- `scripts/voice_drift.py` — statistical prose checker (CLI + `analyze()`).
- `scripts/fairplay_check.py` — ledger-consistency checker (CLI + `check_fairplay()`).
- `config/voice-pack/ai-tics-config.yaml` — tic thresholds + `banned_phrases`/`metaphor_pool`.
- `series/whodunit/book-01.yaml` — first real ledger slot, doubling as a fixture instance of the frozen `book-NN.yaml` contract.
- `tests/test_penny_verdict.py`, `tests/test_voice_drift.py`, `tests/test_fairplay_check.py`.
- `tests/fixtures/prose/` (clean, tic-saturated, monotone, adversarial-dialogue `.md`) and `tests/fixtures/ledgers/` (fair + each unfair case `.yaml`).

**Modify:**
- `config/voice-pack/ai-tics-detection.md` — rewrite to prose-only, declared non-parsed, pointing at the `.yaml`.
- `config/run-config.md` — add `culprit_by_fraction: 0.5`.
- `README.md` — dev note: `pip install -r requirements.txt`.
- `penny-design-v3.md` §2 + §5a, `penny-PRD-v3.md` P0.10 — per-book ledger path (the §5.2 frozen-contract doc edits).

**Reuse (do not modify):** `scripts/penny_meta.py`, `pytest.ini`.

---

## Task 1: Project dependency — PyYAML + requirements.txt

**Files:**
- Create: `requirements.txt`
- Modify: `README.md`

PyYAML was approved as Penny's first runtime dependency (spec §8). Install it and record it before any code uses it.

- [ ] **Step 1: Create `requirements.txt`**

```
PyYAML>=6.0
```

- [ ] **Step 2: Install it**

Run: `python3 -m pip install -r requirements.txt`
Expected: PyYAML installs (or "Requirement already satisfied").

- [ ] **Step 3: Verify import works**

Run: `python3 -c "import yaml; print(yaml.__version__)"`
Expected: prints a version (e.g. `6.0.2`), no `ModuleNotFoundError`.

- [ ] **Step 4: Add a dev note to `README.md`**

In `README.md`, under the `## Develop` section, replace the line:

```markdown
Requires `python3`, `jq` (status line), and `pytest`. No third-party Python deps.
```

with:

```markdown
Requires `python3`, `jq` (status line), and `pytest`. One third-party dependency
(PyYAML, for nested human-edited config/ledgers):

```bash
pip install -r requirements.txt
```
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt README.md
git commit -m "build: add PyYAML dependency (first runtime dep) + requirements.txt"
```

---

## Task 2: `penny_verdict.py` — the shared verdict writer

**Files:**
- Create: `scripts/penny_verdict.py`
- Test: `tests/test_penny_verdict.py`

Owns the verdict-file format so both checkers (and 2b inspectors) produce identical envelopes. A verdict is markdown: YAML-ish frontmatter (parseable by `penny_meta.parse_frontmatter`) + `BLOCKING:` lines + non-blocking `-` lines + optional `metrics:`/`evidence:` body. `score` is omitted entirely unless supplied (deterministic checkers never supply it).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_penny_verdict.py`:

```python
from pathlib import Path

from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict


def test_writes_frontmatter_and_blocking_lines(tmp_path):
    out = write_verdict(
        out_dir=tmp_path,
        producer="fairplay_check.py",
        kind="deterministic-checker",
        target="book-01/ch-22",
        name="fairplay",
        blocking=["necessary clue clue-x scheduled at/after reveal"],
        notes=["red herring rh-y scheduled after reveal"],
        metrics={"required_clues": 3},
        evidence=[],
    )
    assert out == tmp_path / "fairplay.md"
    text = out.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    assert meta["producer"] == "fairplay_check.py"
    assert meta["kind"] == "deterministic-checker"
    assert meta["target"] == "book-01/ch-22"
    assert meta["schema"] == "penny-verdict/1"
    # Blocking issues are ^BLOCKING: lines (Phase 1 status-line + gate convention).
    blocking_lines = [ln for ln in text.splitlines() if ln.startswith("BLOCKING:")]
    assert blocking_lines == ["BLOCKING: necessary clue clue-x scheduled at/after reveal"]
    # Non-blocking notes are "- " lines.
    assert "- red herring rh-y scheduled after reveal" in text


def test_omits_score_for_checkers(tmp_path):
    out = write_verdict(
        out_dir=tmp_path, producer="voice_drift.py", kind="deterministic-checker",
        target="book-01/ch-07", name="voice-drift",
        blocking=[], notes=[], metrics={}, evidence=[],
    )
    meta = parse_frontmatter(out.read_text(encoding="utf-8"))
    assert "score" not in meta


def test_includes_score_when_supplied(tmp_path):
    out = write_verdict(
        out_dir=tmp_path, producer="inspector-voice", kind="inspector",
        target="book-01/ch-07", name="inspector-voice",
        blocking=[], notes=[], metrics={}, evidence=[], score=4,
    )
    meta = parse_frontmatter(out.read_text(encoding="utf-8"))
    assert meta["score"] == "4"


def test_creates_out_dir_if_missing(tmp_path):
    nested = tmp_path / "ch-07.reviews"
    out = write_verdict(
        out_dir=nested, producer="voice_drift.py", kind="deterministic-checker",
        target="book-01/ch-07", name="voice-drift",
        blocking=[], notes=[], metrics={}, evidence=[],
    )
    assert out.exists()
    assert out.parent == nested


def test_evidence_rendered_as_json_lines(tmp_path):
    out = write_verdict(
        out_dir=tmp_path, producer="voice_drift.py", kind="deterministic-checker",
        target="book-01/ch-07", name="voice-drift", blocking=[], notes=[],
        metrics={"sentence_stdev": 5.1},
        evidence=[{"tic_id": "bodily_reaction", "span_text": "her heart pounded", "line": 12}],
    )
    text = out.read_text(encoding="utf-8")
    assert "metrics:" in text
    assert "evidence:" in text
    assert "bodily_reaction" in text
    assert "her heart pounded" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_verdict'`.

- [ ] **Step 3: Implement `scripts/penny_verdict.py`**

```python
"""Shared writer for Penny review verdict files.

A verdict is a markdown file in a chapter's ``ch-NN.reviews/`` directory. The
envelope is shared by deterministic checkers (Phase 2a) and inspector sub-agents
(Phase 2b):

    ---
    producer: <script or agent name>
    kind: deterministic-checker | inspector
    target: book-NN/ch-MM
    schema: penny-verdict/1
    score: <1-5>            # OPTIONAL — inspectors only; omitted for checkers
    ---
    BLOCKING: <one line per blocking issue>     # counted by the status line + gate
    - <one line per non-blocking note / evidence summary>
    metrics: <json>
    evidence:
      - <json>

Blocking issues are ``^BLOCKING:`` lines (the Phase 1 convention the status line
and gate count). ``penny_meta.parse_frontmatter`` reads the frontmatter.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "penny-verdict/1"


def write_verdict(
    *,
    out_dir,
    producer: str,
    kind: str,
    target: str,
    name: str,
    blocking: list[str],
    notes: list[str],
    metrics: dict,
    evidence: list[dict],
    score: int | None = None,
) -> Path:
    """Write ``<out_dir>/<name>.md`` and return its Path. Creates out_dir if needed."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.md"

    lines: list[str] = ["---", f"producer: {producer}", f"kind: {kind}",
                        f"target: {target}", f"schema: {SCHEMA}"]
    if score is not None:
        lines.append(f"score: {score}")
    lines.append("---")
    lines.append("")

    for issue in blocking:
        lines.append(f"BLOCKING: {issue}")
    for note in notes:
        lines.append(f"- {note}")
    if metrics:
        lines.append(f"metrics: {json.dumps(metrics, sort_keys=True)}")
    if evidence:
        lines.append("evidence:")
        for item in evidence:
            lines.append(f"  - {json.dumps(item, sort_keys=True)}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_verdict.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite (no regression on Phase 1)**

Run: `python3 -m pytest -q`
Expected: all prior tests + these 5 pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/penny_verdict.py tests/test_penny_verdict.py
git commit -m "feat(verdict): add shared penny_verdict writer (markdown + BLOCKING: lines)"
```

---

## Task 3: `ai-tics-config.yaml` + rewrite `ai-tics-detection.md`

**Files:**
- Create: `config/voice-pack/ai-tics-config.yaml`
- Modify: `config/voice-pack/ai-tics-detection.md`
- Test: `tests/test_voice_drift.py` (config-loading tests only in this task)

The authoritative machine-readable tic config (PyYAML). The existing `.md` becomes prose-only documentation, declared non-parsed.

- [ ] **Step 1: Write the failing config-loading tests**

Create `tests/test_voice_drift.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.voice_drift import load_config

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "config/voice-pack/ai-tics-config.yaml"


def test_default_config_has_required_keys():
    cfg = load_config(DEFAULT_CONFIG)
    for key in ("bodily_reaction", "soft_qualifiers", "sentence_variance",
                "lexical_repetition", "banned_phrases", "metaphor_pool"):
        assert key in cfg, f"ai-tics-config.yaml missing {key}"
    assert cfg["bodily_reaction"]["flag_at"] >= 1
    assert isinstance(cfg["metaphor_pool"], list)


def test_missing_config_hard_fails(tmp_path):
    with pytest.raises(SystemExit):
        load_config(tmp_path / "nope.yaml")
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest tests/test_voice_drift.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.voice_drift'` (the script is built in Task 4; this task creates the config + the `load_config` it needs, so implement `load_config` here as part of Task 4's file... see Step 3 note).

> **Ordering note:** `load_config` lives in `voice_drift.py` (Task 4). To keep this
> task self-contained, create `scripts/voice_drift.py` now containing ONLY
> `load_config` (Task 4 adds the analysis + CLI). This is the one place tasks share
> a file; the function signatures are fixed here and reused unchanged in Task 4.

- [ ] **Step 3: Create `config/voice-pack/ai-tics-config.yaml`**

```yaml
# Authoritative tic thresholds + compounding lists (PyYAML). Tunable Book-1 seeds.
# Detection patterns live in scripts/voice_drift.py; values live here.
# ai-tics-detection.md is the prose companion (non-parsed).
bodily_reaction:     { per_1k: 2, flag_at: 3 }
wave_templates:      { per_1k: 1, flag_at: 2 }
something_language:  { per_1k: 1, flag_at: 2 }
filtering_verbs:     { per_1k: 3, flag_at: 4 }
soft_qualifiers:     { per_1k: 4, flag_at: 5, cluster_in_sentence: 2 }
cinematic_fragments: { max_clusters_per_chapter: 1 }
metaphor_pool_rule:  { same_domain_flag_at: 3, total_flag_at: 5 }
sentence_variance:   { min_stdev: 4.0 }
lexical_repetition:  { opener_repeat_flag_at: 3, content_word_per_1k_flag_at: 8 }
banned_phrases: []
metaphor_pool: [wave, storm, weight, knife, thread, shadow, flame, spark, abyss, hollow]
```

- [ ] **Step 4: Create `scripts/voice_drift.py` with ONLY `load_config`**

```python
"""Voice-drift checker — statistical prose evidence (Tier-3, evidence-only).

Detection patterns/algorithms live in this file (stable). Tunable thresholds and
the compounding banned-phrase / metaphor lists live in
config/voice-pack/ai-tics-config.yaml (authoritative). Per spec, this checker NEVER
emits BLOCKING: lines — its flags are evidence the 2b voice inspector weighs.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `import scripts.*` when this file is run directly as `python3 scripts/voice_drift.py`
# (direct-run puts scripts/ on sys.path, not the repo root). Harmless under pytest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

DEFAULT_CONFIG = Path("config/voice-pack/ai-tics-config.yaml")


def load_config(path) -> dict:
    """Load the tic config. Hard-fail (SystemExit) if missing/unreadable/malformed —
    no hardcoded threshold fallback (spec §3.3)."""
    path = Path(path)
    if not path.is_file():
        sys.exit(f"voice_drift: config not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"voice_drift: config is not valid YAML ({path}): {exc}")
    if not isinstance(data, dict):
        sys.exit(f"voice_drift: config must be a mapping: {path}")
    return data
```

- [ ] **Step 5: Run config tests — pass**

Run: `python3 -m pytest tests/test_voice_drift.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Rewrite `config/voice-pack/ai-tics-detection.md` to prose-only**

Replace the entire file contents with:

```markdown
# AI-Tics Detection — prose companion (NON-PARSED)

> **This file is documentation only and is never parsed by code.** The authoritative,
> machine-read values live in `ai-tics-config.yaml` (thresholds + the compounding
> `banned_phrases` / `metaphor_pool` lists). Detection patterns live in
> `scripts/voice_drift.py`. Where a number appears both here and in the YAML, the
> YAML wins.

`voice_drift.py` is **evidence-only**: it counts tics and flags densities over
threshold, but never emits a blocking verdict. The blocking decision belongs to the
Tier-C voice inspector (Phase 2b), which reads this evidence.

## The seven tic categories
1. **Bodily reactions** — "her heart pounded", "breath caught", "stomach twisted".
   Frequency tic: one is fine, repetition is the failure.
2. **Wave / emotional-noun templates** — "a wave of grief washed over", "a sense of dread".
3. **"Something" language** — "something shifted between them", "something in his eyes".
4. **Filtering verbs** — "she noticed/realized/could feel" — distance from direct experience.
5. **Soft qualifiers** — "almost", "somehow", "as if" — hedging that drains conviction.
   Cluster rule: 2+ in one sentence is always flagged.
6. **Cinematic fragments** — runs of ultra-short verbless sentences ("A pause. A breath.").
7. **Emotional-metaphor pool** — overused source domains (wave, storm, knife, thread…).
   Keyword-count in MVP; LLM-classifier graduation is deferred.

Plus two statistical measures: **sentence-length variance** (flag monotone rhythm) and
**lexical repetition** (over-repeated content words / sentence openers).
```

- [ ] **Step 7: Commit**

```bash
git add config/voice-pack/ai-tics-config.yaml config/voice-pack/ai-tics-detection.md scripts/voice_drift.py tests/test_voice_drift.py
git commit -m "feat(config): add ai-tics-config.yaml + voice_drift.load_config; .md prose-only"
```

---

## Task 4: `voice_drift.py` — segmentation + analysis + CLI

**Files:**
- Modify: `scripts/voice_drift.py` (add segmentation, analysis, CLI; keep `load_config`)
- Create: `tests/fixtures/prose/clean.md`, `tests/fixtures/prose/tics.md`, `tests/fixtures/prose/monotone.md`, `tests/fixtures/prose/dialogue.md`
- Modify: `tests/test_voice_drift.py` (add analysis + segmentation + CLI tests)

Sentence segmentation is the named accuracy risk (spec §3.4): dependency-free heuristic with abbreviation guards, no split inside quotes, ellipsis/em-dash non-terminal. Output is evidence only — **zero `BLOCKING:` lines**, ever.

- [ ] **Step 1: Create the prose fixtures**

`tests/fixtures/prose/clean.md`:

```markdown
The harbour smelled of diesel and kelp. Cora counted the fishing boats twice,
unsure which was the Mary Vale. A gull dropped a mussel on the breakwater and
dived after it. She had expected the town to be smaller; instead it sprawled
along the cliff in a tangle of tin roofs and television aerials. Somewhere a
chainsaw started, then stopped. The tide was going out.
```

`tests/fixtures/prose/tics.md` (saturated with bodily reactions + qualifiers):

```markdown
Her heart pounded. Her breath caught. Her stomach twisted as she almost,
somehow, as if by instinct, reached for the door. Her pulse quickened. A wave
of dread washed over her. Something shifted between them. She noticed her hands
were shaking, and she realized, almost, that she could feel the cold creeping
up her spine. Her throat tightened. Her blood ran cold.
```

`tests/fixtures/prose/monotone.md` (uniform sentence length → low variance):

```markdown
Cora walked to the shop. She bought some bread there. She paid the man money.
She left the small shop. She walked back home then. She made herself some lunch.
She ate the bread alone. She washed the plate up.
```

`tests/fixtures/prose/dialogue.md` (adversarial: abbreviations, dialogue, ellipsis):

```markdown
"I'm fine," she said. Mrs. Pennington did not look fine. Dr. Alarcón had warned
her about the stairs at St. Brigid's. "It's just... a lot," Cora admitted —
though the tremor in her voice betrayed her. Mr. Voss said nothing at all.
```

- [ ] **Step 2: Write the failing analysis tests**

Append to `tests/test_voice_drift.py`:

```python
from scripts.voice_drift import segment_sentences, analyze

FIX = REPO / "tests/fixtures/prose"


def test_segmentation_handles_dialogue_and_abbreviations():
    text = (REPO / "tests/fixtures/prose/dialogue.md").read_text(encoding="utf-8")
    sents = segment_sentences(text)
    # "I'm fine," she said.  -> one sentence (no split at the comma inside quotes)
    assert any("I'm fine" in s and "she said" in s for s in sents)
    # "Mrs. Pennington did not look fine." -> not split at "Mrs."
    assert any(s.strip().startswith("Mrs. Pennington") for s in sents)
    # Ellipsis is non-terminal: the "It's just... a lot" line stays one sentence.
    assert any("just" in s and "a lot" in s for s in sents)


def test_clean_prose_flags_nothing(tmp_path):
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "clean.md").read_text(encoding="utf-8"), cfg)
    flagged = [t for t in result["tics"] if t["flagged"]]
    assert flagged == []
    assert result["blocking"] == []   # evidence-only: never any blocking


def test_tic_saturated_prose_flags_bodily_and_qualifiers(tmp_path):
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "tics.md").read_text(encoding="utf-8"), cfg)
    flagged_ids = {t["tic_id"] for t in result["tics"] if t["flagged"]}
    assert "bodily_reaction" in flagged_ids
    assert "soft_qualifiers" in flagged_ids
    assert result["blocking"] == []   # still no blocking, even when saturated


def test_monotone_prose_flags_low_variance():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    assert result["metrics"]["sentence_stdev"] < cfg["sentence_variance"]["min_stdev"]
    assert any(t["tic_id"] == "sentence_variance" and t["flagged"] for t in result["tics"])


def test_evidence_capped_at_five_per_tic():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "tics.md").read_text(encoding="utf-8"), cfg)
    bodily = next(t for t in result["tics"] if t["tic_id"] == "bodily_reaction")
    assert len(bodily["evidence_spans"]) <= 5
    assert bodily["count"] >= len(bodily["evidence_spans"])  # count is the full signal
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_voice_drift.py -v`
Expected: FAIL — `ImportError: cannot import name 'segment_sentences'`.

- [ ] **Step 4: Implement segmentation + analysis in `scripts/voice_drift.py`**

Add to `scripts/voice_drift.py` (below `load_config`; keep `load_config` unchanged):

```python
import argparse
import re
import statistics

from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict

_ABBREV = {"mr", "mrs", "ms", "dr", "st", "mt", "rev", "prof", "sr", "jr"}

# Closed detection sets / patterns (the stable algorithm; values come from config).
_PATTERNS = {
    "bodily_reaction": re.compile(
        r"\b(heart (pounded|hammered|raced|thudded|skipped|clenched)"
        r"|breath (caught|hitched|stilled)"
        r"|stomach (twisted|dropped|knotted|churned|lurched)"
        r"|throat (tightened|closed|went dry)"
        r"|pulse (quickened|jumped)"
        r"|blood (ran cold|froze))", re.I),
    "wave_templates": re.compile(
        r"\ba (wave|surge|flood|rush|tide|swell) of \w+ (washed|swept|came|rolled|crashed) over"
        r"|\ba (deep |profound |strange )?sense of (unease|dread|loss|longing|foreboding)", re.I),
    "something_language": re.compile(
        r"\bsomething (shifted|changed|passed) between them"
        r"|\bsomething in (his|her|their) (voice|eyes|face|expression)", re.I),
    "filtering_verbs": re.compile(
        r"\b(noticed|realized|could feel|could see|could hear|watched as|saw that|seemed to)\b", re.I),
    "soft_qualifiers": re.compile(
        r"\b(almost|somehow|slightly|seemingly|as if|as though|a little|not quite)\b", re.I),
}


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


def segment_sentences(text: str) -> list[str]:
    """Heuristic, dependency-free sentence splitter. Known failure modes: it is a
    heuristic over messy prose; abbreviations outside _ABBREV, nested quotes, and
    decimal numbers can mis-split. Counts are signal, not gospel (spec §3.4)."""
    prose = " ".join(l.strip() for l in strip_frontmatter(text).splitlines() if _is_prose_line(l))
    sentences: list[str] = []
    buf = ""
    i = 0
    quote_depth = 0
    while i < len(prose):
        ch = prose[i]
        buf += ch
        if ch in '"“”':
            quote_depth = 0 if quote_depth else 1
        # Ellipsis: consume run of dots, treat as non-terminal.
        if ch == "." and prose[i:i + 3] == "...":
            buf += ".."
            i += 3
            continue
        if ch in ".!?":
            # Non-terminal if inside quotes.
            if quote_depth:
                i += 1
                continue
            # Abbreviation guard: last word before the period.
            m = re.search(r"(\w+)\.$", buf)
            if ch == "." and m and m.group(1).lower() in _ABBREV:
                i += 1
                continue
            # Terminal only if followed by space + (capital or opening quote) or end.
            rest = prose[i + 1:].lstrip()
            if rest == "" or rest[0].isupper() or rest[0] in '"“':
                sentences.append(buf.strip())
                buf = ""
        i += 1
    if buf.strip():
        sentences.append(buf.strip())
    return [s for s in sentences if s]


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def analyze(text: str, cfg: dict) -> dict:
    prose = strip_frontmatter(text)
    sentences = segment_sentences(text)
    words = _words(prose)
    n_words = max(len(words), 1)
    per_1k = 1000.0 / n_words

    tics: list[dict] = []

    def add(tic_id, spans):
        density = len(spans) * per_1k
        thr = cfg.get(tic_id, {})
        flag_at = thr.get("flag_at")          # per-1000-word density threshold
        flagged = flag_at is not None and density >= flag_at
        tics.append({
            "tic_id": tic_id, "count": len(spans),
            "threshold": flag_at, "density_per_1k": round(density, 2),
            "flagged": bool(flagged), "evidence_spans": spans[:5],
        })

    # Line numbers for evidence: search line by line.
    lines = prose.splitlines()

    def spans_for(pattern):
        out = []
        for ln_no, line in enumerate(lines, 1):
            for m in pattern.finditer(line):
                out.append({"tic_id": None, "span_text": m.group(0).strip(), "line": ln_no})
        return out

    for tic_id, pat in _PATTERNS.items():
        sp = spans_for(pat)
        for s in sp:
            s["tic_id"] = tic_id
        add(tic_id, sp)

    # Metaphor pool: count words drawn from the configured pool.
    pool = set(cfg.get("metaphor_pool", []))
    pool_spans = [{"tic_id": "metaphor_pool", "span_text": w, "line": 0}
                  for w in words if w.lower() in pool]
    density = len(pool_spans) * per_1k
    total_flag = cfg.get("metaphor_pool_rule", {}).get("total_flag_at")
    tics.append({
        "tic_id": "metaphor_pool", "count": len(pool_spans),
        "threshold": total_flag, "density_per_1k": round(density, 2),
        "flagged": total_flag is not None and len(pool_spans) >= total_flag,
        "evidence_spans": pool_spans[:5],
    })

    # Sentence-length variance.
    lengths = [len(_words(s)) for s in sentences] or [0]
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
    min_stdev = cfg.get("sentence_variance", {}).get("min_stdev", 0.0)
    tics.append({
        "tic_id": "sentence_variance", "count": len(sentences),
        "threshold": min_stdev, "density_per_1k": round(stdev, 2),
        "flagged": len(lengths) > 1 and stdev < min_stdev,
        "evidence_spans": [],
    })

    metrics = {"n_words": n_words, "n_sentences": len(sentences),
               "sentence_stdev": round(stdev, 2)}
    return {"tics": tics, "metrics": metrics, "blocking": []}  # evidence-only: always []
```

- [ ] **Step 5: Run analysis tests — pass**

Run: `python3 -m pytest tests/test_voice_drift.py -v`
Expected: PASS (all config + segmentation + analysis tests).

- [ ] **Step 6: Add the CLI + a CLI test**

Append the CLI to `scripts/voice_drift.py`:

```python
def _flatten_evidence(tics: list[dict]) -> list[dict]:
    out = []
    for t in tics:
        out.extend(t["evidence_spans"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Voice-drift checker (evidence-only).")
    ap.add_argument("chapter", help="path to the chapter markdown file")
    ap.add_argument("--out", default=None, help="reviews dir to write voice-drift.md")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    text = Path(args.chapter).read_text(encoding="utf-8")
    result = analyze(text, cfg)

    notes = [f"{t['tic_id']}: {t['count']} (density {t['density_per_1k']}/1k, "
             f"threshold {t['threshold']}) {'FLAGGED' if t['flagged'] else 'ok'}"
             for t in result["tics"]]

    out_dir = args.out or str(Path(args.chapter).parent)
    write_verdict(
        out_dir=out_dir, producer="voice_drift.py", kind="deterministic-checker",
        target=args.target, name="voice-drift",
        blocking=result["blocking"],          # always [] — evidence-only
        notes=notes, metrics=result["metrics"],
        evidence=_flatten_evidence(result["tics"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Append the CLI test to `tests/test_voice_drift.py`:

```python
def test_cli_writes_verdict_with_no_blocking_lines(tmp_path):
    chapter = tmp_path / "ch-07.draft.md"
    chapter.write_text((FIX / "tics.md").read_text(encoding="utf-8"), encoding="utf-8")
    rc = subprocess.run(
        [sys.executable, str(REPO / "scripts/voice_drift.py"), str(chapter),
         "--out", str(tmp_path), "--target", "book-01/ch-07"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    verdict = (tmp_path / "voice-drift.md").read_text(encoding="utf-8")
    # HARD RULE: voice_drift never emits BLOCKING: lines, even on saturated prose.
    assert not any(ln.startswith("BLOCKING:") for ln in verdict.splitlines())
    assert "producer: voice_drift.py" in verdict
```

- [ ] **Step 7: Run the full voice_drift suite — pass**

Run: `python3 -m pytest tests/test_voice_drift.py -v`
Expected: PASS (config + segmentation + analysis + CLI).

- [ ] **Step 8: Commit**

```bash
git add scripts/voice_drift.py tests/test_voice_drift.py tests/fixtures/prose
git commit -m "feat(voice-drift): segmentation + tic/variance analysis + evidence-only CLI"
```

---

## Task 4b: `voice_drift.py` — remaining detectors (cluster rule, cinematic fragments, lexical repetition)

**Files:**
- Modify: `scripts/voice_drift.py` (extend `analyze`)
- Create: `tests/fixtures/prose/fragments.md`
- Modify: `tests/test_voice_drift.py` (add tests)

Completes §3.1: the soft-qualifier ≥2-in-one-sentence cluster rule, cinematic-fragment cluster counting, and lexical repetition (repeated openers + over-repeated content words). All still evidence-only.

- [ ] **Step 1: Create the cinematic-fragments fixture**

`tests/fixtures/prose/fragments.md`:

```markdown
A pause. A breath. Then nothing. The room waited around her, holding its shape
the way a held breath holds, and Cora found she could not move from the doorway.
A creak. A whisper. Then silence.
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_voice_drift.py`:

```python
def test_soft_qualifiers_two_in_one_sentence_flags():
    # The cluster rule path: a sentence with >= cluster_in_sentence qualifiers flags.
    cfg = load_config(DEFAULT_CONFIG)
    text = "He walked home. She was almost, somehow, certain of nothing in particular today."
    result = analyze(text, cfg)
    sq = next(t for t in result["tics"] if t["tic_id"] == "soft_qualifiers")
    assert sq["flagged"] is True


def test_cinematic_fragments_counted():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "fragments.md").read_text(encoding="utf-8"), cfg)
    cf = next(t for t in result["tics"] if t["tic_id"] == "cinematic_fragments")
    assert cf["count"] >= 2          # two runs of short verbless fragments
    assert result["blocking"] == []  # still evidence-only


def test_lexical_repetition_flags_repeated_openers():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "monotone.md").read_text(encoding="utf-8"), cfg)
    lr = next(t for t in result["tics"] if t["tic_id"] == "lexical_repetition")
    assert lr["flagged"] is True     # "She" opens many sentences


def test_clean_prose_still_flags_nothing_after_extra_detectors():
    cfg = load_config(DEFAULT_CONFIG)
    result = analyze((FIX / "clean.md").read_text(encoding="utf-8"), cfg)
    assert [t for t in result["tics"] if t["flagged"]] == []
```

- [ ] **Step 3: Run to verify failure**

Run: `python3 -m pytest tests/test_voice_drift.py -k "two_in_one or cinematic or lexical or after_extra" -v`
Expected: FAIL — `cinematic_fragments`/`lexical_repetition` tics not present yet; cluster not enforced.

- [ ] **Step 4: Extend `analyze` in `scripts/voice_drift.py`**

Add this import near the top of `scripts/voice_drift.py` (with the other imports):

```python
from collections import Counter
```

Then, in `analyze`, **immediately before** the line `metrics = {"n_words": n_words, ...}`, insert:

```python
    # Soft-qualifier cluster rule: flag if any sentence has >= cluster_in_sentence qualifiers.
    cluster_n = cfg.get("soft_qualifiers", {}).get("cluster_in_sentence")
    if cluster_n:
        qpat = _PATTERNS["soft_qualifiers"]
        if any(len(qpat.findall(s)) >= cluster_n for s in sentences):
            for t in tics:
                if t["tic_id"] == "soft_qualifiers":
                    t["flagged"] = True

    # Cinematic fragments: clusters of >=3 consecutive sub-4-word sentences, >=2 verbless.
    def _verbless(s: str) -> bool:
        return not re.search(
            r"\b(\w+ed|is|was|were|are|am|be|been|had|has|have|did|do|does|"
            r"went|ran|came|saw|said|holds?|held|waited?)\b", s, re.I)

    frag_clusters = 0
    run: list[str] = []
    for s in sentences:
        if len(_words(s)) < 4:
            run.append(s)
        else:
            if len(run) >= 3 and sum(_verbless(x) for x in run) >= 2:
                frag_clusters += 1
            run = []
    if len(run) >= 3 and sum(_verbless(x) for x in run) >= 2:
        frag_clusters += 1
    max_clusters = cfg.get("cinematic_fragments", {}).get("max_clusters_per_chapter", 1)
    tics.append({"tic_id": "cinematic_fragments", "count": frag_clusters,
                 "threshold": max_clusters, "density_per_1k": 0.0,
                 "flagged": frag_clusters > max_clusters, "evidence_spans": []})

    # Lexical repetition: repeated sentence openers + over-repeated content words.
    _STOP = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
             "she", "he", "they", "her", "his", "it", "was", "had", "with", "for"}
    openers = Counter((_words(s)[0].lower() if _words(s) else "") for s in sentences)
    top_opener = max(openers.values(), default=0)
    content = [w.lower() for w in words if w.lower() not in _STOP and len(w) > 3]
    cw_counts = Counter(content)
    top_cw_density = max(cw_counts.values(), default=0) * per_1k
    lr = cfg.get("lexical_repetition", {})
    opener_flag = lr.get("opener_repeat_flag_at")
    cw_flag = lr.get("content_word_per_1k_flag_at")
    lex_flagged = ((opener_flag is not None and top_opener >= opener_flag) or
                   (cw_flag is not None and top_cw_density >= cw_flag))
    tics.append({"tic_id": "lexical_repetition", "count": top_opener,
                 "threshold": opener_flag, "density_per_1k": round(top_cw_density, 2),
                 "flagged": bool(lex_flagged), "evidence_spans": []})
```

- [ ] **Step 5: Run the voice_drift suite — pass**

Run: `python3 -m pytest tests/test_voice_drift.py -v`
Expected: PASS (all earlier tests + the 4 new ones; `clean.md` still flags nothing).

- [ ] **Step 6: Commit**

```bash
git add scripts/voice_drift.py tests/test_voice_drift.py tests/fixtures/prose/fragments.md
git commit -m "feat(voice-drift): add qualifier-cluster, cinematic-fragment, lexical-repetition detectors"
```

---

## Task 5: `fairplay_check.py` — ledger-consistency checker

**Files:**
- Create: `scripts/fairplay_check.py`
- Create: `series/whodunit/book-01.yaml`
- Modify: `config/run-config.md` (add `culprit_by_fraction`)
- Create: `tests/fixtures/ledgers/fair.yaml`, `unfair_clue_after_reveal.yaml`, `culprit_at_reveal.yaml`, `culprit_past_fraction.yaml`, `malformed.yaml`, `culprit_alibi_holds.yaml`, `mention_before_appearance.yaml`
- Test: `tests/test_fairplay_check.py`

Reads a per-book ledger (PyYAML) + `culprit_by_fraction` from `run-config.md` (via `penny_meta`, fail-loud). Emits `BLOCKING:` for fairness failures; evidence `-` lines for override context. Well-formed check runs first and short-circuits.

- [ ] **Step 1: Add `culprit_by_fraction` to `config/run-config.md`**

In `config/run-config.md`, in the `## Structure inspector (design §8)` yaml block (or a new `## Fairplay` block), add the line so the block reads:

```yaml
thread_dormant_after_chapters: 3          # flag a thread idle beyond N chapters; tunable
culprit_by_fraction: 0.5                  # fairplay: culprit on-page by this fraction of the book; tunable
```

- [ ] **Step 2: Create the fixture ledgers**

`tests/fixtures/ledgers/fair.yaml`:

```yaml
book: 01
locked: true
total_chapters: 24
reveal_chapter: 22
culprit: margaret
culprit_first_appearance_chapter: 2
culprit_first_mention_chapter: 2
victim: edwin-tilley
central_deception: |
  Margaret swapped the tide tables.
clue_schedule:
  - { id: clue-torn-ticket, plant_chapter: 5, pays_off_chapter: 22, necessary: true }
  - { id: clue-tide-table, plant_chapter: 9, pays_off_chapter: 22, necessary: true }
red_herrings:
  - { id: rh-the-neighbour, plant_chapter: 7, misleads_toward: "the neighbour", must_not_cheat: true }
alibi_grid:
  - { suspect: margaret, chapter: 12, alibi: "at the church fete", holds: false }
  - { suspect: thomas, chapter: 12, alibi: "on the ferry", holds: true }
```

`tests/fixtures/ledgers/unfair_clue_after_reveal.yaml` — copy of `fair.yaml` but change `clue-tide-table` to `plant_chapter: 23`.

`tests/fixtures/ledgers/culprit_at_reveal.yaml` — copy of `fair.yaml` but `culprit_first_appearance_chapter: 22`.

`tests/fixtures/ledgers/culprit_past_fraction.yaml` — copy of `fair.yaml` but `culprit_first_appearance_chapter: 18` (floor passes since 18 < 22, but 18 > round(0.5*24)=12).

`tests/fixtures/ledgers/malformed.yaml`:

```yaml
book: 01
locked: true
total_chapters: 24
reveal_chapter: 30
culprit: margaret
```

`tests/fixtures/ledgers/culprit_alibi_holds.yaml` — copy of `fair.yaml` but change margaret's alibi entry to `holds: true`.

`tests/fixtures/ledgers/mention_before_appearance.yaml` — copy of `fair.yaml` but `culprit_first_mention_chapter: 1` (appearance stays 2).

- [ ] **Step 3: Write the failing tests**

Create `tests/test_fairplay_check.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.fairplay_check import check_fairplay, load_fraction

REPO = Path(__file__).resolve().parents[1]
LED = REPO / "tests/fixtures/ledgers"
RUN_CONFIG = REPO / "config/run-config.md"


def _blocking(result):
    return result["blocking"]


def test_fair_ledger_has_no_blocking():
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5)
    assert _blocking(r) == []


def test_necessary_clue_after_reveal_blocks():
    r = check_fairplay(LED / "unfair_clue_after_reveal.yaml", culprit_by_fraction=0.5)
    assert any("clue-tide-table" in b for b in _blocking(r))


def test_culprit_at_reveal_blocks_floor_only_once():
    r = check_fairplay(LED / "culprit_at_reveal.yaml", culprit_by_fraction=0.5)
    culprit_blocks = [b for b in _blocking(r) if "culprit" in b.lower()]
    # Floor fails -> exactly one culprit blocking line (seed must NOT also fire).
    assert len(culprit_blocks) == 1


def test_culprit_past_fraction_blocks_seed():
    r = check_fairplay(LED / "culprit_past_fraction.yaml", culprit_by_fraction=0.5)
    assert any("fraction" in b.lower() or "half" in b.lower() or "by chapter" in b.lower()
               for b in _blocking(r))


def test_malformed_ledger_blocks_and_stops():
    r = check_fairplay(LED / "malformed.yaml", culprit_by_fraction=0.5)
    assert _blocking(r)                     # at least one blocking line
    assert any("malformed" in b.lower() or "reveal" in b.lower() for b in _blocking(r))


def test_culprit_alibi_always_holds_blocks():
    r = check_fairplay(LED / "culprit_alibi_holds.yaml", culprit_by_fraction=0.5)
    assert any("alibi" in b.lower() for b in _blocking(r))


def test_mention_before_appearance_is_evidence_not_blocking():
    r = check_fairplay(LED / "mention_before_appearance.yaml", culprit_by_fraction=0.5)
    assert _blocking(r) == []
    assert any("mention" in n.lower() for n in r["notes"])


def test_load_fraction_hard_fails_if_absent(tmp_path):
    bad = tmp_path / "run-config.md"
    bad.write_text("# no fraction here\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_fraction(bad)


def test_load_fraction_reads_run_config():
    assert load_fraction(RUN_CONFIG) == 0.5


def test_cli_writes_blocking_verdict(tmp_path):
    rc = subprocess.run(
        [sys.executable, str(REPO / "scripts/fairplay_check.py"),
         str(LED / "unfair_clue_after_reveal.yaml"),
         "--out", str(tmp_path), "--run-config", str(RUN_CONFIG),
         "--target", "book-01/ch-22"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    verdict = (tmp_path / "fairplay.md").read_text(encoding="utf-8")
    assert any(ln.startswith("BLOCKING:") for ln in verdict.splitlines())
```

- [ ] **Step 4: Run to verify failure**

Run: `python3 -m pytest tests/test_fairplay_check.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.fairplay_check'`.

- [ ] **Step 5: Implement `scripts/fairplay_check.py`**

```python
"""Fair-play checker — whodunit-ledger consistency (Tier-3, may block).

Reads a per-book ledger (series/whodunit/book-NN.yaml, PyYAML) and the scalar
culprit_by_fraction from run-config.md (penny_meta — the flat side of the
two-reader boundary). Audits the PLAN's fairness, not the prose (prose-planting is
the 2b inspector's job). Fairness failures emit BLOCKING: lines.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `import scripts.*` when run directly as `python3 scripts/fairplay_check.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.penny_meta import load, parse_yaml_blocks
from scripts.penny_verdict import write_verdict

DEFAULT_RUN_CONFIG = Path("config/run-config.md")
_REQUIRED = ("book", "total_chapters", "reveal_chapter", "culprit",
             "culprit_first_appearance_chapter")


def load_fraction(run_config_path) -> float:
    """Read culprit_by_fraction from run-config.md. Hard-fail if absent/non-numeric."""
    cfg = parse_yaml_blocks(load(run_config_path))
    raw = cfg.get("culprit_by_fraction")
    if raw is None:
        sys.exit("fairplay: culprit_by_fraction missing from run-config.md")
    try:
        return float(raw)
    except (TypeError, ValueError):
        sys.exit(f"fairplay: culprit_by_fraction not numeric: {raw!r}")


def _load_ledger(path) -> dict:
    path = Path(path)
    if not path.is_file():
        sys.exit(f"fairplay: ledger not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.exit(f"fairplay: ledger is not valid YAML ({path}): {exc}")
    if not isinstance(data, dict):
        sys.exit(f"fairplay: ledger must be a mapping: {path}")
    return data


def _is_int_in_range(v, lo, hi) -> bool:
    return isinstance(v, int) and lo <= v <= hi


def check_fairplay(ledger_path, *, culprit_by_fraction: float) -> dict:
    led = _load_ledger(ledger_path)
    blocking: list[str] = []
    notes: list[str] = []

    # 1. Well-formed first; on failure, stop (don't pile on derived failures).
    missing = [k for k in _REQUIRED if k not in led]
    total = led.get("total_chapters")
    reveal = led.get("reveal_chapter")
    if missing:
        blocking.append(f"malformed ledger: missing fields {sorted(missing)}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}
    if not _is_int_in_range(total, 1, 10_000):
        blocking.append(f"malformed ledger: total_chapters not in range: {total!r}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}
    if not _is_int_in_range(reveal, 1, total):
        blocking.append(f"malformed ledger: reveal_chapter not in 1..total_chapters: {reveal!r}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}

    appearance = led["culprit_first_appearance_chapter"]
    if not _is_int_in_range(appearance, 1, total):
        blocking.append(f"malformed ledger: culprit_first_appearance_chapter invalid: {appearance!r}")
        return {"blocking": blocking, "notes": notes, "metrics": {}}

    # 2. Necessary clues scheduled before the reveal.
    for clue in led.get("clue_schedule", []):
        if clue.get("necessary"):
            plant = clue.get("plant_chapter")
            cid = clue.get("id", "?")
            if not isinstance(plant, int):
                blocking.append(f"necessary clue {cid} has no valid plant_chapter")
            elif plant >= reveal:
                blocking.append(f"necessary clue {cid} scheduled at/after reveal (ch {plant} >= {reveal})")

    # 3. Culprit floor (non-negotiable). Seed only if floor passes (one fault, one line).
    if appearance >= reveal:
        blocking.append(f"culprit first appears at/after reveal (ch {appearance} >= {reveal})")
    else:
        bound = round(culprit_by_fraction * total)
        if appearance > bound:
            blocking.append(
                f"culprit introduced too late: first appears ch {appearance}, "
                f"must be by chapter {bound} ({culprit_by_fraction:g} of the book)")

    # 4. Auditable culprit gap.
    culprit = led["culprit"]
    culprit_alibis = [a for a in led.get("alibi_grid", []) if a.get("suspect") == culprit]
    if culprit_alibis and all(a.get("holds") for a in culprit_alibis):
        blocking.append(f"culprit {culprit} has no auditable alibi gap (all alibis hold)")

    # Evidence (non-blocking).
    mention = led.get("culprit_first_mention_chapter")
    if isinstance(mention, int) and mention < appearance:
        notes.append(f"culprit mentioned (ch {mention}) before on-page appearance (ch {appearance})")
    for clue in led.get("clue_schedule", []):
        p = clue.get("plant_chapter")
        if isinstance(p, int) and p >= reveal:
            notes.append(f"clue {clue.get('id','?')} planted at/after reveal (non-necessary)")
    for rh in led.get("red_herrings", []):
        if rh.get("must_not_cheat") is False:
            notes.append(f"red herring {rh.get('id','?')} flagged must_not_cheat: false")
    # culprit-id resolution: evidence-only in 2a (promoted to BLOCKING in 2b/3).
    chars = Path("series/continuity/characters")
    if chars.is_dir() and any(chars.iterdir()):
        if not (chars / f"{culprit}.md").is_file():
            notes.append(f"culprit id '{culprit}' does not resolve in series/continuity/characters/ (evidence; blocking in 2b/3)")

    metrics = {"reveal_chapter": reveal, "total_chapters": total,
               "culprit_first_appearance_chapter": appearance}
    return {"blocking": blocking, "notes": notes, "metrics": metrics}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fair-play ledger-consistency checker.")
    ap.add_argument("ledger", help="path to series/whodunit/book-NN.yaml")
    ap.add_argument("--out", default=None, help="reviews dir to write fairplay.md")
    ap.add_argument("--run-config", default=str(DEFAULT_RUN_CONFIG))
    ap.add_argument("--target", default="unknown")
    args = ap.parse_args(argv)

    fraction = load_fraction(args.run_config)
    result = check_fairplay(args.ledger, culprit_by_fraction=fraction)

    out_dir = args.out or "."
    write_verdict(
        out_dir=out_dir, producer="fairplay_check.py", kind="deterministic-checker",
        target=args.target, name="fairplay",
        blocking=result["blocking"], notes=result["notes"],
        metrics=result["metrics"], evidence=[],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the fairplay tests — pass**

Run: `python3 -m pytest tests/test_fairplay_check.py -v`
Expected: PASS (10 passed).

- [ ] **Step 7: Create the real ledger slot `series/whodunit/book-01.yaml`**

Copy the content of `tests/fixtures/ledgers/fair.yaml` into `series/whodunit/book-01.yaml` (the first real, fair ledger instance of the frozen `book-NN.yaml` contract). Verify it passes:

Run: `python3 scripts/fairplay_check.py series/whodunit/book-01.yaml --out /tmp/fp --run-config config/run-config.md --target book-01/ch-22 && grep -c '^BLOCKING:' /tmp/fp/fairplay.md; rm -rf /tmp/fp`
Expected: prints `0` (no blocking lines for the fair ledger).

- [ ] **Step 8: Commit**

```bash
git add scripts/fairplay_check.py series/whodunit/book-01.yaml config/run-config.md tests/test_fairplay_check.py tests/fixtures/ledgers
git commit -m "feat(fairplay): ledger-consistency checker (layered culprit bound, alibi gap, evidence)"
```

---

## Task 6: Doc edits — freeze the per-book ledger contract

**Files:**
- Modify: `penny-design-v3.md` (§2 repo layout, §5a)
- Modify: `penny-PRD-v3.md` (P0.10)
- Modify: `config/run-config.md` validation test? (no — `test_run_config.py` doesn't pin `culprit_by_fraction`; leave it.)

These are the mandatory §5.2 contract edits so Phase 3's `/plan-mystery` targets the per-book yaml, not the prose ledger.

- [ ] **Step 1: Update `penny-design-v3.md` §2 repo layout**

In the `/series` block of the §2 layout, replace:

```
  whodunit-ledger.md            per-book: culprit, per-chapter clue schedule,
                                red herrings, alibi grid (authored by /plan-mystery)
```

with:

```
  whodunit-ledger.md            [human doc, NEVER parsed] how the schedule works,
                                narrative notes
  /whodunit
    book-NN.yaml                [machine-read, LOCKED] culprit, per-chapter clue
                                schedule, red herrings, alibi grid (authored by
                                /plan-mystery; read by fairplay_check.py)
```

- [ ] **Step 2: Update `penny-design-v3.md` §5a**

Find the sentence in §5a beginning "On approval, `/plan-mystery` writes `/series/whodunit-ledger.md`" and replace the artifact reference so it reads:

```
On approval, `/plan-mystery` writes `/series/whodunit/book-NN.yaml` (the trackable
clue/red-herring/alibi data, **structured per chapter** so each chapter's planting
obligations can be handed out without revealing the answer) and updates the prose
`/series/whodunit-ledger.md` (human notes), and writes
`/output/book-NN/mystery-solution.md` (the sealed answer key), then sets
`.penny/locks/book-NN.mystery.lock`.
```

- [ ] **Step 3: Update `penny-PRD-v3.md` P0.10**

In P0.10, change the acceptance line referencing `whodunit-ledger.md` (per-chapter clue schedule) to reference `series/whodunit/book-NN.yaml`:

```
- [ ] `/plan-mystery N`: showrunner sets core (culprit, deception, arc
  constraints) → `mystery-planner` proposes clue schedule + red herrings + alibi
  grid → showrunner approves → writes `series/whodunit/book-NN.yaml` (per-chapter
  clue schedule, machine-read; schema frozen in Phase 2a) + sealed
  `mystery-solution.md` → sets `book-NN.mystery.lock`.
```

- [ ] **Step 4: Verify nothing references the old single-file ledger as machine-read**

Run: `grep -rn "whodunit-ledger.md" penny-design-v3.md penny-PRD-v3.md`
Expected: remaining mentions describe it only as the human/prose doc (not as the machine-parsed source). Read the hits and confirm.

- [ ] **Step 5: Commit**

```bash
git add penny-design-v3.md penny-PRD-v3.md
git commit -m "docs: freeze per-book series/whodunit/book-NN.yaml ledger contract (§2/§5a/P0.10)"
```

---

## Task 7: Phase 2a acceptance — full suite + push

**Files:** none (verification + push)

- [ ] **Step 1: Run the complete suite from a clean cache**

Run: `find . -name __pycache__ -type d -prune -exec rm -rf {} + ; rm -rf .pytest_cache; python3 -m pytest -q`
Expected: ALL pass (Phase 1 tests + Task 2/4/5 tests). If any fail, STOP and fix before continuing.

- [ ] **Step 2: Smoke the two checkers end-to-end**

Run:

```bash
# voice_drift on the tic-saturated fixture -> verdict with NO blocking lines
python3 scripts/voice_drift.py tests/fixtures/prose/tics.md --out /tmp/vd --target book-01/ch-07
echo "voice-drift blocking count:"; grep -c '^BLOCKING:' /tmp/vd/voice-drift.md   # expect 0
# fairplay on the fair ledger -> no blocking; on the unfair -> blocking
python3 scripts/fairplay_check.py series/whodunit/book-01.yaml --out /tmp/fp_fair --run-config config/run-config.md --target book-01/ch-22
echo "fairplay fair blocking count:"; grep -c '^BLOCKING:' /tmp/fp_fair/fairplay.md   # expect 0
python3 scripts/fairplay_check.py tests/fixtures/ledgers/unfair_clue_after_reveal.yaml --out /tmp/fp_bad --run-config config/run-config.md --target book-01/ch-22
echo "fairplay unfair blocking count:"; grep -c '^BLOCKING:' /tmp/fp_bad/fairplay.md   # expect >=1
rm -rf /tmp/vd /tmp/fp_fair /tmp/fp_bad
```

Expected: `0`, `0`, then `1` (or more). Confirm.

- [ ] **Step 3: Confirm clean git status**

Run: `git status --short`
Expected: clean except untracked `HANDOFF.md` (and no stray `/tmp` artifacts, `__pycache__`).

- [ ] **Step 4: Push**

```bash
git push origin main
```

Confirm the push succeeded.

---

## Phase 2a Done — what comes next

When this plan is complete: both deterministic Tier-3 checkers exist and write verdicts in the shared envelope; `voice_drift.py` is evidence-only (never blocks); `fairplay_check.py` blocks on fairness failures with the layered culprit bound; the per-book `book-NN.yaml` ledger contract is frozen and documented; PyYAML is a recorded dependency.

**Next plan: Phase 2b (Inspector Bus)** — Tier-1 blind inspector sub-agents (incl. the Tier-C AI-prose taste inspector and the prose-planting `inspector-fairplay`), their per-failure-mode rubrics, the `review-chapter` command that dispatches inspectors + runs these two checkers + collects verdicts, the structure inspector's thread roster, and the two-signal conflict resolution. It will consume `penny_verdict.py`, the `BLOCKING:` convention, and these checkers' CLIs unchanged.
