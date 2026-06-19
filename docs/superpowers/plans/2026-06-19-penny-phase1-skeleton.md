# Penny Phase 1 (Skeleton) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Penny skeleton — the engine/config directory separation, the sectioned series-memory scaffold, and the TUI status bar — so a single chapter can be drafted manually and the harness state is visible in the Claude Code status line.

**Architecture:** Penny is Claude-Code-native (Option A): the harness *is* a repository of sub-agent definitions (`.claude/agents`), slash-commands (`.claude/commands`), and swappable config (`/config`, `/series`), with a thin deterministic `/scripts` layer. Phase 1 lays down that structure with real-but-minimal content, plus the one piece of executable code this phase needs — `scripts/penny-statusline.sh` — and a dependency-free Python validation layer that enforces the structural contracts (run-config keys, ledger frontmatter schema) the later phases depend on.

**Tech Stack:** Markdown (agents/commands/config/ledgers) · Python 3 (validation + a tiny frontmatter parser, no third-party deps) · Bash + `jq` (status line) · pytest (tests).

**Scope:** This plan covers **Phase 1 of 6** for MVP 1 — the Skeleton (design §13 step 1; PRD P0.1, P0.2, P0.9). It deliberately does **not** build the review bus (Phase 2), cross-model routing / `/plan-mystery` (Phase 3), prose passes (Phase 4), beta layer (Phase 5), or the book loop (Phase 6). Each of those gets its own plan. The agent/command files created here are **structural stubs** with the correct headers and one working manual `draft-chapter` path; their review/edit/finalize logic arrives in later phases.

**Spec references:** `penny-design-v3.md` (§2 layout, §4 series memory, §11 status bar, §12 run-config), `penny-PRD-v3.md` (P0.1, P0.2, P0.9; Timeline phase 1).

---

## File Structure

Files created in this phase, grouped by responsibility:

**Tooling / tests (the only executable code in Phase 1)**
- `pytest.ini` — pytest config (test discovery root).
- `scripts/penny_meta.py` — dependency-free parser: YAML-ish frontmatter blocks and fenced ` ```yaml ` blocks → `dict`. Reused by every structural test and by later-phase scripts.
- `scripts/penny-statusline.sh` — renders harness state for the Claude Code status line (design §11).
- `tests/conftest.py` — `penny_root` fixture that builds a throwaway repo tree for status-line tests.
- `tests/test_penny_meta.py` — unit tests for the parser.
- `tests/test_run_config.py` — asserts `config/run-config.md` declares every required key.
- `tests/test_ledger_schema.py` — asserts continuity entries carry valid `id`/`type`/`links` frontmatter and `canon-core.md` exists.
- `tests/test_scaffold.py` — asserts the engine/config/series directory contracts exist (P0.1 separation).
- `tests/test_statusline.py` — drives `penny-statusline.sh` via subprocess against fixtures.

**Engine config (`/config`, swappable)**
- `config/run-config.md` — model-per-role + run-mode flags + thresholds (design §7, §12; PRD B6).
- `config/genre-pack/cozy-mystery.md` — genre conventions (design §9).
- `config/voice-pack/voice-pack.md` — POV/tense/register/rhythm (joins the already-present `ai-tics-detection.md`).
- `config/setting-pack/coastal-victoria-au.md` + `config/setting-pack/lexicon.md` — setting + lexicon schema (design §9).
- `config/length-profile.md` — word-count targets.
- *(already present from brainstorming: `config/self-audit/self-audit-checklist.md`, `config/review-rubrics/ai-prose-taste-flags.md`, `config/voice-pack/ai-tics-detection.md`)*

**Series memory (`/series`, this project's data)**
- `series/series-bible.md`, `series/arc-ledger.md`, `series/style-sheet.md`, `series/whodunit-ledger.md` (per-book template).
- `series/continuity/canon-core.md` — always-loaded slice (design §4.2).
- `series/continuity/characters/cora-minstate.md` — example mutable knowledge-state entry.
- `series/continuity/locations/the-bluff.md` — example location entry.
- `series/continuity/threads/the-inheritance.md` — example thread entry.
- `series/characters/cora-mistate.static.md` — example STATIC character design (design §4.1 split).

**Claude-Code runtime (`.claude`)**
- `.claude/settings.json` — `statusLine` config (design §11).
- `.claude/agents/drafter.md` — working drafter role (manual single-chapter).
- `.claude/agents/_TEMPLATE.md` — the agent-definition contract every later agent follows.
- `.claude/commands/draft-chapter.md` — manual single-chapter command; writes `.penny/current-stage`.

**Runtime state**
- `.gitignore` — add `.penny/` (transient harness state) and `__pycache__/`.

---

## Task 1: Test harness + dependency-free metadata parser

**Files:**
- Create: `pytest.ini`
- Create: `scripts/penny_meta.py`
- Test: `tests/test_penny_meta.py`

The parser is the foundation every structural test reuses, so it is built and tested first. It must handle two shapes: a frontmatter block delimited by `---` lines at the top of a file, and fenced ` ```yaml ` blocks anywhere in a markdown file. It supports only the value types Penny uses: bare scalars and inline lists `[a, b, c]`. No third-party dependencies.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_penny_meta.py`:

```python
from scripts.penny_meta import parse_frontmatter, parse_yaml_blocks


def test_parse_frontmatter_scalars_and_list():
    text = (
        "---\n"
        "id: margaret\n"
        "type: character\n"
        "links: [the-inheritance, lighthouse]\n"
        "---\n"
        "body text here\n"
    )
    meta = parse_frontmatter(text)
    assert meta["id"] == "margaret"
    assert meta["type"] == "character"
    assert meta["links"] == ["the-inheritance", "lighthouse"]


def test_parse_frontmatter_empty_list():
    text = "---\nid: x\ntype: thread\nlinks: []\n---\n"
    assert parse_frontmatter(text)["links"] == []


def test_parse_frontmatter_absent_returns_empty():
    assert parse_frontmatter("no frontmatter here\n") == {}


def test_parse_yaml_blocks_merges_keys_and_ignores_comments():
    text = (
        "# Title\n\n"
        "```yaml\n"
        "drafting_model: claude-opus   # a comment\n"
        "beta_models: [codex, hermes]\n"
        "```\n\n"
        "prose\n\n"
        "```yaml\n"
        "ledger_approval: review\n"
        "```\n"
    )
    cfg = parse_yaml_blocks(text)
    assert cfg["drafting_model"] == "claude-opus"
    assert cfg["beta_models"] == ["codex", "hermes"]
    assert cfg["ledger_approval"] == "review"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_meta.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.penny_meta'`.

- [ ] **Step 3: Create the parser**

Create `scripts/penny_meta.py`:

```python
"""Dependency-free metadata parsing for Penny config and ledger files.

Supports only the small subset of YAML that Penny uses: a ``key: value`` line
where the value is a bare scalar or an inline list ``[a, b, c]``. This avoids a
PyYAML dependency in the deterministic ``/scripts`` layer.
"""
from __future__ import annotations

from pathlib import Path


def _coerce(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",") if item.strip()]
    return value


def _parse_kv_lines(lines: list[str]) -> dict:
    out: dict = {}
    for raw in lines:
        line = raw.rstrip("\n")
        # Strip trailing comments that are not inside a value.
        if "#" in line and not line.strip().startswith("#"):
            # Only strip a comment that follows whitespace (so "[a, b]  # x" works).
            hash_idx = line.find("#")
            line = line[:hash_idx]
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = _coerce(value)
    return out


def parse_frontmatter(text: str) -> dict:
    """Parse a leading ``---`` delimited frontmatter block. Returns {} if absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    return _parse_kv_lines(body)


def parse_yaml_blocks(text: str) -> dict:
    """Merge all fenced ```yaml blocks in a markdown document into one dict."""
    out: dict = {}
    in_block = False
    block: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not in_block and stripped.startswith("```") and "yaml" in stripped:
            in_block = True
            block = []
            continue
        if in_block and stripped.startswith("```"):
            in_block = False
            out.update(_parse_kv_lines(block))
            continue
        if in_block:
            block.append(line)
    return out


def load(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
```

- [ ] **Step 4: Create pytest config so `scripts` is importable**

Create `pytest.ini`:

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -q
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_meta.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add pytest.ini scripts/penny_meta.py tests/test_penny_meta.py
git commit -m "feat(scripts): add dependency-free frontmatter/yaml parser + test harness"
```

---

## Task 2: `run-config.md` with required-key validation

**Files:**
- Create: `config/run-config.md`
- Test: `tests/test_run_config.py`

`run-config.md` is named an explicit Phase 1 deliverable (PRD B6) so every later reference resolves. The test pins the exact set of keys the design promises (model-per-role §7, run-mode flags + thresholds §12), so a later edit that drops a key fails loudly.

- [ ] **Step 1: Write the failing test**

Create `tests/test_run_config.py`:

```python
from scripts.penny_meta import load, parse_yaml_blocks

REQUIRED_KEYS = {
    # model-per-role (design §7)
    "drafting_model", "inspector_model", "copyedit_model",
    "final_read_model", "beta_models",
    # run-mode flags (design §12)
    "cadence", "panel_size", "gate_mode", "escalation_scope", "ledger_approval",
    # escalation thresholds (design §6)
    "escalate_on_blocking_disagreement", "score_spread_log_threshold",
    # structure inspector (design §8)
    "thread_dormant_after_chapters",
}


def test_run_config_declares_all_required_keys():
    cfg = parse_yaml_blocks(load("config/run-config.md"))
    missing = REQUIRED_KEYS - set(cfg)
    assert not missing, f"run-config.md missing keys: {sorted(missing)}"


def test_final_read_differs_from_drafting_model():
    cfg = parse_yaml_blocks(load("config/run-config.md"))
    assert cfg["final_read_model"] != cfg["drafting_model"], (
        "final_read_model must differ from drafting_model (design §7 invariant)"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_run_config.py -v`
Expected: FAIL — `FileNotFoundError` for `config/run-config.md`.

- [ ] **Step 3: Create the config file**

Create `config/run-config.md`:

````markdown
# run-config.md — Penny run configuration

The fixed engine reads this file for model routing, run-mode flags, and escalation
thresholds. All values are MVP 1 defaults; thresholds marked "tunable" are Book-1
seeds, not load-bearing constants. See design §7 (routing), §12 (flags), §6
(thresholds), §8 (structure inspector).

## Model-per-role (design §7)

The final-read invariant is **difference, not identity**: `final_read_model` must
not appear among the chapters' `drafted_by` stamps (enforced by `preflight.py` in
Phase 3). Substitute any reachable alternate model.

```yaml
drafting_model:   claude-opus
inspector_model:  claude-opus
copyedit_model:   claude-opus
final_read_model: codex            # MUST differ from drafting_model
beta_models:      [codex, hermes, openclaw]
```

## Run-mode flags (design §12)

```yaml
cadence:          chapter          # chapter | book-milestone
panel_size:       1                # 1 (fast) | 3 (consensus)
gate_mode:        strict           # strict | fast
escalation_scope: minor-auto       # minor-auto | log-all
ledger_approval:  review           # review (early/tuning) | auto (once clean)
```

## Escalation thresholds (design §6)

```yaml
escalate_on_blocking_disagreement: true   # HARD — holds gate, escalates now
score_spread_log_threshold: 2             # SOFT — logged only; tunable Book 1
```

## Structure inspector (design §8)

```yaml
thread_dormant_after_chapters: 3          # flag a thread idle beyond N chapters; tunable
```
````

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_run_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add config/run-config.md tests/test_run_config.py
git commit -m "feat(config): add run-config.md with model-per-role, flags, thresholds"
```

---

## Task 3: Sectioned continuity ledger + frontmatter schema

**Files:**
- Create: `series/continuity/canon-core.md`
- Create: `series/continuity/characters/cora-mistate.md`
- Create: `series/continuity/locations/the-bluff.md`
- Create: `series/continuity/threads/the-inheritance.md`
- Create: `series/characters/cora-mistate.static.md`
- Test: `tests/test_ledger_schema.py`

This is the heart of P0.2: the addressable, sectioned ledger the slice loader will read (design §4). Every entry under `series/continuity/{characters,locations,threads}/` MUST carry `id`, `type`, and a `links` list. The test enforces the schema and the static-vs-mutable split (design §4.1). `canon-core.md` must exist (always-loaded slice).

- [ ] **Step 1: Write the failing test**

Create `tests/test_ledger_schema.py`:

```python
from pathlib import Path

from scripts.penny_meta import load, parse_frontmatter

CONTINUITY = Path("series/continuity")
VALID_TYPES = {"character", "location", "thread"}
TYPE_DIRS = {"characters": "character", "locations": "location", "threads": "thread"}


def test_canon_core_exists():
    assert (CONTINUITY / "canon-core.md").is_file(), "canon-core.md is the always-loaded slice"


def test_every_continuity_entry_has_valid_frontmatter():
    entries = []
    for subdir in TYPE_DIRS:
        entries.extend((CONTINUITY / subdir).glob("*.md"))
    assert entries, "expected at least one example continuity entry per type"
    for path in entries:
        meta = parse_frontmatter(load(path))
        assert meta.get("id"), f"{path} missing id"
        assert meta.get("type") in VALID_TYPES, f"{path} has invalid type {meta.get('type')!r}"
        assert isinstance(meta.get("links"), list), f"{path} links must be a list"


def test_entry_type_matches_its_directory():
    for subdir, expected_type in TYPE_DIRS.items():
        for path in (CONTINUITY / subdir).glob("*.md"):
            meta = parse_frontmatter(load(path))
            assert meta["type"] == expected_type, (
                f"{path} is in /{subdir} but typed {meta['type']!r}"
            )


def test_links_resolve_to_existing_entries():
    by_id = {}
    for subdir in TYPE_DIRS:
        for path in (CONTINUITY / subdir).glob("*.md"):
            meta = parse_frontmatter(load(path))
            by_id[meta["id"]] = path
    for subdir in TYPE_DIRS:
        for path in (CONTINUITY / subdir).glob("*.md"):
            meta = parse_frontmatter(load(path))
            for link in meta["links"]:
                assert link in by_id, f"{path} links to unknown id {link!r}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_ledger_schema.py -v`
Expected: FAIL — `canon-core.md` missing / no entries found.

- [ ] **Step 3: Create the canon-core slice**

Create `series/continuity/canon-core.md`:

```markdown
---
id: canon-core
type: thread
links: []
---
# Canon Core — always loaded every chapter (design §4.2)

Keep this small: every line is a tax on every chapter. Holds only what is always
relevant.

## Protagonist fixed facts
- **Cora Mistate**, 44, recently divorced, relocated from Melbourne to the town of
  Wreckers Bluff. Outsider. Fluency stage tracked below.

## Current timeline position
- Book 01, pre-draft. Season: late autumn. No deaths yet recorded.

## Active-book whodunit constraints
- None locked yet (authored per book by `/plan-mystery`, Phase 3).

## Fluency stage (design §9 newcomer dial)
- **OUTSIDER** (Books 1–2): narration is standard English; local idiom lives in
  other characters' mouths, never Cora's narration.
```

- [ ] **Step 4: Create the three example continuity entries**

Create `series/continuity/characters/cora-mistate.md`:

```markdown
---
id: cora-mistate
type: character
links: [the-inheritance]
---
# Cora Mistate — knowledge-state (MUTABLE; updated post-gate by the ledger-updater)

This file records what Cora *knows* and what has become canonically true on the
page. The ledger-updater (Phase 4) writes here; the drafter only reads it.

## Knowledge-state (as of: Book 01, pre-draft)
- Knows she has inherited a property at the Bluff from an aunt she barely met.
- Does NOT yet know the property's history.

## Established facts
- (none yet — populated as chapters finalize)
```

Create `series/continuity/locations/the-bluff.md`:

```markdown
---
id: the-bluff
type: location
links: []
---
# Wreckers Bluff — location facts

- A wind-scoured headland over the Southern Ocean; kelp, salt, eucalypt, hard
  southern light. Ordinary to locals, strange to Cora.
- Cora's inherited property sits on the Bluff road.
```

Create `series/continuity/threads/the-inheritance.md`:

```markdown
---
id: the-inheritance
type: thread
links: [the-bluff, cora-mistate]
---
# Thread: the inheritance

- Cora inherited the Bluff property from her aunt. The aunt's reason, and the
  property's past, are open threads driving the personal B-plot.
- Status: OPEN.
```

- [ ] **Step 5: Create the matching static character file (design §4.1 split)**

Create `series/characters/cora-mistate.static.md`:

```markdown
# Cora Mistate — STATIC character design (authored by showrunner; rarely changes)

Distinct from `series/continuity/characters/cora-mistate.md` (mutable knowledge-state).
This file is design intent; that file is what has become true on the page.

## Voice fingerprint
- Precise, faintly formal diction (ex-archivist). Understates feeling. Asks one
  question too many. Never uses local slang in Book 1.

## Arc intention (13-book)
- Outsider → belonging. Each book's mystery is the vehicle; her transformation is
  the spine.

## Secrets
- (none authored yet)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_ledger_schema.py -v`
Expected: PASS (4 passed).

- [ ] **Step 7: Commit**

```bash
git add series/continuity series/characters tests/test_ledger_schema.py
git commit -m "feat(series): add sectioned continuity ledger scaffold + schema test"
```

---

## Task 4: Series-memory documents (bible, arc-ledger, style-sheet, whodunit template)

**Files:**
- Create: `series/series-bible.md`
- Create: `series/arc-ledger.md`
- Create: `series/style-sheet.md`
- Create: `series/whodunit-ledger.md`
- Test: extend `tests/test_scaffold.py` (created here)

These are the living-memory documents read/written across books. In Phase 1 they hold starter content and clear "authored later by" notes; the whodunit-ledger is a per-book template (its real content is produced by `/plan-mystery` in Phase 3).

- [ ] **Step 1: Write the failing scaffold test**

Create `tests/test_scaffold.py`:

```python
from pathlib import Path

import pytest

REQUIRED_SERIES_FILES = [
    "series/series-bible.md",
    "series/arc-ledger.md",
    "series/style-sheet.md",
    "series/whodunit-ledger.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_SERIES_FILES)
def test_series_memory_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: FAIL — series memory files missing.

- [ ] **Step 3: Create the four documents**

Create `series/series-bible.md`:

```markdown
# Series Bible — (cozy mystery / coastal Victoria AU)

> Discipline: keep this FUNCTIONAL, not comprehensive. Track only what will be
> referenced. Document after each chapter/book while fresh. Resist lore-building
> before Book 1 reveals what matters.

## The long game (13 books)
- Cora Mistate's transformation from divorced Melbourne outsider to a woman who
  belongs in Wreckers Bluff. Each book: one murder solved (A-plot) + one personal
  thread advanced but not closed (B-plot), driving the next purchase.

## Themes
- Reinvention; what "home" means after it breaks; the ordinary made strange.
```

Create `series/arc-ledger.md`:

```markdown
# Arc Ledger — which threads open/resolve in which book

| Thread | Opens | Advances | Resolves | Notes |
|---|---|---|---|---|
| the-inheritance | Book 01 | — | — | personal B-plot spine |

> The structure inspector reads a slice of this as the per-book thread roster
> (design §8). Updated as books are planned.
```

Create `series/style-sheet.md`:

```markdown
# Style Sheet — accumulating spelling/punctuation/consistency decisions

> Distinct from the Voice Pack: the Voice Pack says *how to write*; this records
> *what was decided*. The copy-edit pass (Phase 4) appends here. Accumulates
> across all 13 books.

## Decisions
- Spelling: Australian (colour, realise, -ise endings).
- (more added as chapters are copy-edited)
```

Create `series/whodunit-ledger.md`:

```markdown
# Whodunit Ledger — per-book mystery construction (TEMPLATE)

> Authored per book by `/plan-mystery` (Phase 3), then LOCKED. The drafter reads
> only the current chapter's clue-planting obligations from here; the full
> solution lives sealed in `output/book-NN/mystery-solution.md`. This file is the
> empty template until a book is planned.

## Book NN
- **Culprit:** (set by showrunner core)
- **Central deception:** 
- **Clue schedule (per chapter):**
  - ch-01: 
- **Red herrings:** 
- **Alibi grid:** 
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add series/series-bible.md series/arc-ledger.md series/style-sheet.md series/whodunit-ledger.md tests/test_scaffold.py
git commit -m "feat(series): add series-memory documents + whodunit template"
```

---

## Task 5: One Genre / Voice / Setting pack + length profile

**Files:**
- Create: `config/genre-pack/cozy-mystery.md`
- Create: `config/voice-pack/voice-pack.md`
- Create: `config/setting-pack/coastal-victoria-au.md`
- Create: `config/setting-pack/lexicon.md`
- Create: `config/length-profile.md`
- Test: extend `tests/test_scaffold.py`

Proves P0.1 engine/config separation with one real, swappable pack (design §9). Content is starter-real, not exhaustive. The already-present Tier files (`config/voice-pack/ai-tics-detection.md`, `config/self-audit/self-audit-checklist.md`, `config/review-rubrics/ai-prose-taste-flags.md`) belong to this config layer; the test asserts they are present alongside the new pack files.

- [ ] **Step 1: Extend the scaffold test (add failing config assertions)**

In `tests/test_scaffold.py`, append:

```python
REQUIRED_CONFIG_FILES = [
    "config/run-config.md",
    "config/genre-pack/cozy-mystery.md",
    "config/voice-pack/voice-pack.md",
    "config/voice-pack/ai-tics-detection.md",        # Tier A (already present)
    "config/self-audit/self-audit-checklist.md",     # Tier B (already present)
    "config/review-rubrics/ai-prose-taste-flags.md", # Tier C (already present)
    "config/setting-pack/coastal-victoria-au.md",
    "config/setting-pack/lexicon.md",
    "config/length-profile.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_CONFIG_FILES)
def test_config_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: FAIL — new config pack files missing (the three Tier files already pass).

- [ ] **Step 3: Create the genre pack**

Create `config/genre-pack/cozy-mystery.md`:

```markdown
# Genre Pack — Cozy Mystery

## Conventions
- Amateur sleuth; no graphic violence or sex; small contained community; justice
  restored; balance of comfort and puzzle.

## Dual engine
- **A-plot:** the book's mystery (a death, solved by the end).
- **B-plot:** the protagonist's post-divorce sea-change, threaded across all 13
  books via the arc-ledger.

## Per-book rule
- The mystery **resolves**; a personal thread **does not** (drives the next
  purchase). Chapter-end hooks are mandatory.
```

- [ ] **Step 4: Create the voice pack**

Create `config/voice-pack/voice-pack.md`:

```markdown
# Voice Pack — POV / tense / register / rhythm

> Says *how to write*. (What was *decided* lives in `series/style-sheet.md`.)
> Frequency tics and the banned-phrase/metaphor list live in the sibling
> `ai-tics-detection.md` (Tier A, design §8a).

## POV & tense
- Third person limited, past tense, anchored to Cora.

## Register
- Precise, lightly formal narration. Warmth through observation, not gush.

## Rhythm rules
- Vary sentence length deliberately; do not open consecutive sentences the same
  way. (Enforced statistically by `voice_drift.py` in Phase 2.)
```

- [ ] **Step 5: Create the setting pack + lexicon**

Create `config/setting-pack/coastal-victoria-au.md`:

```markdown
# Setting Pack — Coastal Victoria, Australia (invented town: Wreckers Bluff)

> Real region, **invented town**. A `fictionalization-map.md` (added when the
> setting locks) firewalls real-derived texture from invented names. Research
> stays in config; verify coastal-Victorian idiom + AFL loyalties before locking
> (design §9 accuracy note).

## Physical stance
- Southern Ocean, not tropical: cool, changeable; southerly busters; kelp, salt,
  eucalypt; hard southern light; wind as a constant.

## Core stance
- The town is **ordinary to locals, strange to the protagonist** — never
  travel-brochure framing. Cora's ignorance is the reader's onboarding.

## Newcomer fluency dial (design §9)
- Books 1–2 OUTSIDER · Books 3–6 SETTLING · Books 7–13 BELONGING. Couples to the
  lexicon's `narration_ok_from_stage` field.
```

Create `config/setting-pack/lexicon.md`:

```markdown
# Lexicon (schema fixed; contents swap per location)

Schema: `term | gloss | register | speaker_type | freq_cap | narration_ok_from_stage | notes`

`narration_ok_from_stage` couples each term to the fluency dial — a `BELONGING`
term appearing in Book 2 narration is an automatic reviewer flag.

| term | gloss | register | speaker_type | freq_cap | narration_ok_from_stage | notes |
|---|---|---|---|---|---|---|
| arvo | afternoon | casual | local | 2/ch | SETTLING | seed; verify regional use |
| servo | petrol station | casual | local | 1/ch | SETTLING | seed |
| the footy | Australian Rules football | casual | local | 1/ch | BELONGING | AFL loyalties intensely local — verify before lock |
```

- [ ] **Step 6: Create the length profile**

Create `config/length-profile.md`:

```markdown
# Length Profile — word-count targets

```yaml
chapter_target_words: 2500
chapter_min_words: 1800
chapter_max_words: 3500
book_target_words: 65000
book_chapter_count: 24
```
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: PASS (all config + series scaffold files present).

- [ ] **Step 8: Commit**

```bash
git add config/genre-pack config/voice-pack/voice-pack.md config/setting-pack config/length-profile.md tests/test_scaffold.py
git commit -m "feat(config): add cozy-mystery genre/voice/setting pack + length profile"
```

---

## Task 6: `.claude` agent + command scaffold (manual single-chapter)

**Files:**
- Create: `.claude/agents/_TEMPLATE.md`
- Create: `.claude/agents/drafter.md`
- Create: `.claude/commands/draft-chapter.md`
- Create: `.gitignore` entries for `.penny/` and `__pycache__/`
- Test: extend `tests/test_scaffold.py`

Phase 1 only needs a working **manual** `draft-chapter` path plus the agent-definition contract later agents will follow. The command's defining Phase 1 behavior is writing `.penny/current-stage` (so the status bar reflects position) and loading the right config + ledger slice. The test asserts the files exist and the command documents the `.penny/current-stage` write.

- [ ] **Step 1: Write the failing test**

In `tests/test_scaffold.py`, append:

```python
REQUIRED_CLAUDE_FILES = [
    ".claude/agents/_TEMPLATE.md",
    ".claude/agents/drafter.md",
    ".claude/commands/draft-chapter.md",
]


@pytest.mark.parametrize("relpath", REQUIRED_CLAUDE_FILES)
def test_claude_file_exists_and_nonempty(relpath):
    path = Path(relpath)
    assert path.is_file(), f"missing {relpath}"
    assert path.read_text(encoding="utf-8").strip(), f"{relpath} is empty"


def test_draft_chapter_writes_current_stage():
    text = Path(".claude/commands/draft-chapter.md").read_text(encoding="utf-8")
    assert ".penny/current-stage" in text, (
        "draft-chapter must document writing the harness state marker (design §11)"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scaffold.py -k claude -v`
Expected: FAIL — `.claude` files missing.

- [ ] **Step 3: Create the agent template**

Create `.claude/agents/_TEMPLATE.md`:

```markdown
---
name: <agent-id>
description: <one line — when this agent is used>
---
# <Agent Name>

**Role posture:** <e.g. generative drafter | literal extractive record-keeper | blind inspector>

**Independence:** <what this agent may and may NOT see — the core of design §6>

**Inputs:** <exact files/fields this agent receives>

**Outputs:** <exact artifact(s) and their schema>

**Instructions:**
1. ...
```

- [ ] **Step 4: Create the drafter agent**

Create `.claude/agents/drafter.md`:

```markdown
---
name: drafter
description: Writes a chapter draft against the brief, voice pack, setting pack, and this chapter's clue obligations.
---
# Drafter

**Role posture:** generative. Writes prose; fills gaps creatively.

**Independence:** receives ONLY this chapter's clue-planting obligations — never
the full sealed `mystery-solution.md` (design §5a). Does not write ledgers.

**Inputs:**
- The chapter brief (beats, POV, clue/red-herring to plant, emotional turn, hook).
- `config/voice-pack/voice-pack.md`, `config/setting-pack/coastal-victoria-au.md`,
  `config/genre-pack/cozy-mystery.md`, `config/length-profile.md`.
- The loaded ledger slice: `series/continuity/canon-core.md` + brief-derived
  entries + one-hop links (design §4.2).

**Outputs:**
- `output/book-NN/chapters/ch-NN.draft.md`, with frontmatter `drafted_by: <model>`
  (used by the Phase 3 cross-model set-membership check).

**Instructions:**
1. Read the brief and the loaded ledger slice. Honour Cora's knowledge-state.
2. Honour the fluency stage from canon-core (Book 1 = OUTSIDER: no local idiom in
   narration).
3. Write to the chapter word target. Plant exactly the clues the brief names.
4. End on a hook. Write `drafted_by` frontmatter. Do NOT update any ledger.
```

- [ ] **Step 5: Create the draft-chapter command**

Create `.claude/commands/draft-chapter.md`:

````markdown
---
description: Manually draft one chapter (Phase 1: no review bus yet).
argument-hint: <book-number> <chapter-number>
---
# /draft-chapter

Manual single-chapter draft. Phase 1 path: assemble context → dispatch the drafter
→ write the draft. (Review/edit/finalize arrive in later phases.)

## Steps

1. **Parse args:** `book=$1` (e.g. `01`), `chapter=$2` (e.g. `01`).

2. **Write the harness state marker** so the status bar reflects position
   (design §11):

   ```bash
   mkdir -p .penny
   echo "book=$book chapter=$chapter stage=DRAFT" > .penny/current-stage
   ```

3. **Assemble the ledger slice** (design §4.2): always load
   `series/continuity/canon-core.md`; then load the continuity entries named in the
   chapter brief and their one-hop `links`. (Phase 1: if no brief exists yet, load
   canon-core only.)

4. **Ensure output paths exist:**

   ```bash
   mkdir -p output/book-$book/chapters
   ```

5. **Dispatch the `drafter` sub-agent** with the inputs listed in
   `.claude/agents/drafter.md`. Write its output to
   `output/book-$book/chapters/ch-$chapter.draft.md` including `drafted_by`
   frontmatter.

6. **Clear/advance the marker** when done:

   ```bash
   echo "book=$book chapter=$chapter stage=DRAFTED" > .penny/current-stage
   ```
````

- [ ] **Step 6: Create/extend `.gitignore`**

Add these lines to `.gitignore` (create if the entries are absent):

```
.penny/
__pycache__/
.pytest_cache/
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: PASS (all scaffold assertions).

- [ ] **Step 8: Commit**

```bash
git add .claude/agents .claude/commands tests/test_scaffold.py .gitignore
git commit -m "feat(claude): add agent template, drafter, and manual draft-chapter command"
```

---

## Task 7: TUI status bar — `penny-statusline.sh` + settings

**Files:**
- Create: `scripts/penny-statusline.sh`
- Create: `.claude/settings.json`
- Create: `tests/conftest.py`
- Test: `tests/test_statusline.py`

The one piece of executable harness code in Phase 1 (design §11). It reads harness state from files under `$PENNY_ROOT` (default `.`, overridable so tests can point at a fixture tree) and the session JSON from stdin. **Convention defined here and honoured by Phase 2:** a blocking verdict is a line beginning `BLOCKING:` in a file under `ch-NN.reviews/`.

- [ ] **Step 1: Write the conftest fixture**

Create `tests/conftest.py`:

```python
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path("scripts/penny-statusline.sh").resolve()


@pytest.fixture
def penny_root(tmp_path):
    """Build a throwaway Penny tree; return a runner that invokes the status line."""
    (tmp_path / ".penny").mkdir()

    def write_stage(line: str):
        (tmp_path / ".penny" / "current-stage").write_text(line + "\n", encoding="utf-8")

    def write_outline(book: str, chapter_count: int):
        d = tmp_path / "output" / f"book-{book}"
        d.mkdir(parents=True, exist_ok=True)
        body = "# Outline\n\n" + "".join(f"## Chapter {i}\n\n" for i in range(1, chapter_count + 1))
        (d / "outline.md").write_text(body, encoding="utf-8")

    def write_blocking(book: str, chapter: str, count: int):
        d = tmp_path / "output" / f"book-{book}" / "chapters" / f"ch-{chapter}.reviews"
        d.mkdir(parents=True, exist_ok=True)
        body = "".join(f"BLOCKING: issue {i}\n" for i in range(count))
        (d / "inspector-continuity.md").write_text(body or "ok\n", encoding="utf-8")

    def run(session_json: str) -> str:
        env = dict(os.environ, PENNY_ROOT=str(tmp_path))
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            input=session_json, capture_output=True, text=True, env=env, check=True,
        )
        return proc.stdout.strip()

    return type("PennyRoot", (), {
        "path": tmp_path, "write_stage": staticmethod(write_stage),
        "write_outline": staticmethod(write_outline),
        "write_blocking": staticmethod(write_blocking), "run": staticmethod(run),
    })
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_statusline.py`:

```python
JSON_41 = '{"context_window": {"used_percentage": 41.2}}'
JSON_NONE = '{}'


def test_idle_when_no_stage_file(penny_root):
    # Remove the .penny dir to simulate a fresh repo.
    (penny_root.path / ".penny").rmdir()
    out = penny_root.run(JSON_41)
    assert out == "Penny · idle · ctx 41%"


def test_full_render_with_outline_and_blocking(penny_root):
    penny_root.write_stage("book=03 chapter=07 stage=COPY-EDIT")
    penny_root.write_outline("03", 24)
    penny_root.write_blocking("03", "07", 2)
    out = penny_root.run(JSON_41)
    assert out == "Penny · Book 03 · Ch 7/24 · COPY-EDIT · gate: 2 blocking · ctx 41%"


def test_no_reviews_means_zero_blocking(penny_root):
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    penny_root.write_outline("01", 24)
    out = penny_root.run(JSON_41)
    assert out == "Penny · Book 01 · Ch 1/24 · DRAFT · gate: 0 blocking · ctx 41%"


def test_missing_context_percentage_renders_question_mark(penny_root):
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    penny_root.write_outline("01", 10)
    out = penny_root.run(JSON_NONE)
    assert out.endswith("ctx ?%")


def test_total_falls_back_to_current_chapter_without_outline(penny_root):
    penny_root.write_stage("book=02 chapter=05 stage=PLAN")
    out = penny_root.run(JSON_41)
    assert "Ch 5/5" in out
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_statusline.py -v`
Expected: FAIL — `scripts/penny-statusline.sh` does not exist (subprocess raises).

- [ ] **Step 4: Write the status-line script**

Create `scripts/penny-statusline.sh`:

```bash
#!/usr/bin/env bash
# penny-statusline.sh — render Penny harness state for the Claude Code status line.
# Harness state is read from files under $PENNY_ROOT (default "."); the Claude Code
# session JSON arrives on stdin. Only the first line of stdout becomes the status line.
set -uo pipefail

ROOT="${PENNY_ROOT:-.}"
STAGE_FILE="$ROOT/.penny/current-stage"

# Consume stdin once (the session JSON).
session_json="$(cat)"

# Context-window percentage (design §11). NOTE: confirm this jq path matches the
# live Claude Code status-line JSON schema during execution; adjust if needed.
ctx="$(printf '%s' "$session_json" | jq -r '.context_window.used_percentage // empty' 2>/dev/null)"
if [ -z "${ctx:-}" ]; then
  ctx="?"
else
  ctx="$(printf '%.0f' "$ctx" 2>/dev/null || printf '%s' "$ctx")"
fi

# No harness state yet → idle.
if [ ! -f "$STAGE_FILE" ]; then
  printf 'Penny · idle · ctx %s%%\n' "$ctx"
  exit 0
fi

stage_line="$(head -n1 "$STAGE_FILE")"
book="$(printf '%s' "$stage_line" | sed -n 's/.*book=\([^ ]*\).*/\1/p')"
chapter="$(printf '%s' "$stage_line" | sed -n 's/.*chapter=\([^ ]*\).*/\1/p')"
stage="$(printf '%s' "$stage_line" | sed -n 's/.*stage=\([^ ]*\).*/\1/p')"

# Total chapters from the book outline (## headings); fall back to current chapter.
outline="$ROOT/output/book-$book/outline.md"
if [ -f "$outline" ]; then
  total="$( { grep -c '^## ' "$outline" || true; } | head -n1)"
else
  total="$chapter"
fi
# Strip a possible leading zero for display (07 -> 7) without arithmetic on bare 0.
chapter_disp="$((10#$chapter))"

# Blocking verdicts = lines beginning "BLOCKING:" in the chapter's reviews dir.
reviews="$ROOT/output/book-$book/chapters/ch-$chapter.reviews"
if [ -d "$reviews" ]; then
  blocking="$( { grep -rh '^BLOCKING:' "$reviews" 2>/dev/null || true; } | grep -c '^BLOCKING:' || true)"
  [ -z "${blocking:-}" ] && blocking=0
else
  blocking=0
fi

printf 'Penny · Book %s · Ch %s/%s · %s · gate: %s blocking · ctx %s%%\n' \
  "$book" "$chapter_disp" "$total" "$stage" "$blocking" "$ctx"
```

- [ ] **Step 5: Make it executable**

Run:

```bash
chmod +x scripts/penny-statusline.sh
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_statusline.py -v`
Expected: PASS (5 passed).

> If `test_full_render` shows `Ch 07/24` instead of `Ch 7/24`, the `10#$chapter`
> normalization step was omitted — re-check Step 4.

- [ ] **Step 7: Create the statusLine settings**

Create `.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "scripts/penny-statusline.sh",
    "padding": 0
  }
}
```

- [ ] **Step 8: Commit**

```bash
git add scripts/penny-statusline.sh .claude/settings.json tests/conftest.py tests/test_statusline.py
git commit -m "feat(statusline): add penny-statusline.sh harness dashboard + tests"
```

---

## Task 8: Phase 1 acceptance — full suite + README + manual smoke

**Files:**
- Create: `README.md`
- Test: full `pytest` run

Ties Phase 1 together: a green suite, a short operator README, and a documented manual smoke check for the single-chapter path and the status line.

- [ ] **Step 1: Run the complete test suite**

Run: `python3 -m pytest -v`
Expected: PASS — all tests from Tasks 1–7 green.

- [ ] **Step 2: Manual smoke — status line idle → active**

Run:

```bash
# Idle (no marker):
echo '{"context_window":{"used_percentage":12.5}}' | PENNY_ROOT=. bash scripts/penny-statusline.sh
# Expected: Penny · idle · ctx 13%

# Simulate mid-draft:
mkdir -p .penny && echo "book=01 chapter=01 stage=DRAFT" > .penny/current-stage
echo '{"context_window":{"used_percentage":12.5}}' | PENNY_ROOT=. bash scripts/penny-statusline.sh
# Expected: Penny · Book 01 · Ch 1/1 · DRAFT · gate: 0 blocking · ctx 13%
rm -rf .penny
```

Confirm both lines match. (`.penny/` is gitignored, so the smoke leaves no tracked changes.)

- [ ] **Step 3: Write the operator README**

Create `README.md`:

```markdown
# Penny

Modular, Claude-Code-native harness for producing a 13-book commercial fiction
series with independent quality review. Genre/location-agnostic: everything
project-specific lives in swappable config, never in the engine.

See `penny-design-v3.md` (design) and `penny-PRD-v3.md` (requirements).

## Status: Phase 1 (Skeleton)

In place: engine/config separation, sectioned continuity ledger + canon-core,
series-memory documents, one cozy-mystery / coastal-Victoria pack, the three-tier
AI-prose defense config, run-config, and the TUI status bar. Manual single-chapter
drafting via `/draft-chapter`.

Not yet built: review bus (Phase 2), `/plan-mystery` + cross-model routing
(Phase 3), prose passes (Phase 4), beta layer (Phase 5), book loop (Phase 6).

## Develop

```bash
python3 -m pytest          # run the structural + status-line tests
```

Requires `python3`, `jq` (status line), and `pytest`. No third-party Python deps.

## Status line

`scripts/penny-statusline.sh` is wired in `.claude/settings.json`. It reads harness
state from `.penny/current-stage` and `/output`, and the session JSON from stdin.
Honours `$PENNY_ROOT` (default `.`).
```

- [ ] **Step 4: Run the suite once more to confirm green after README**

Run: `python3 -m pytest -q`
Expected: PASS (README adds no code; confirms nothing regressed).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add operator README; Phase 1 skeleton complete"
```

- [ ] **Step 6: Push**

```bash
git push origin main
```

---

## Phase 1 Done — what comes next

When this plan is complete the repo has: enforced engine/config separation (P0.1), the sectioned series-memory scaffold with a validated frontmatter schema (P0.2), and a working file-driven status bar (P0.9). A chapter can be drafted manually.

**Next plan: Phase 2 (Review Bus)** — Tier-1 blind inspector sub-agents (incl. the Tier-C AI-prose taste inspector), Tier-3 `/scripts` checkers (`voice_drift.py` consuming `ai-tics-detection.md`, plus continuity/fair-play/alibi), the structure inspector's thread roster, and the two-signal conflict resolution (mostly dormant at `panel_size: 1`). That plan will reuse `scripts/penny_meta.py` and the `BLOCKING:` verdict convention defined here.
