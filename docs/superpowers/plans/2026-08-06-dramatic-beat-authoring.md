# Dramatic Beat Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the engine what a dramatic beat is — a craft document under the config overlay, a `story-author` role brief carrying authority, and a `story_cut.py check` subcommand whose one advisory tests grammar rather than drama.

**Architecture:** Two markdown documents (craft in `config/story-craft/`, authority in `agents/story-author.md`) plus two small script changes: a `directive-shaped-beat` advisory riding the *existing* non-blocking `notes` channel in `check_story`, and a `check` subcommand on `story_cut.py` that validates a story with no cut plan. `/plot-book` step 6 stops describing beats and starts pointing at the craft document.

**Tech Stack:** Python 3 stdlib only in `scripts/` (dependency-split rule — `penny_meta`, never PyYAML, for frontmatter/config), pytest, markdown for commands/agents/config.

**Spec:** `docs/superpowers/specs/2026-08-06-dramatic-beat-authoring-design.md`

## Global Constraints

- **The advisory must never block.** It goes in `check_story`'s existing `notes` list, never `blocking`; it never becomes a cut refusal; it never changes an exit code. (spec §5.1)
- **Sixteen blocking findings stay sixteen.** No finding is added, renamed, or removed by this plan.
- **`scripts/` stays genre- and location-agnostic.** No cozy filename, no book number, no series path in engine code. Job and clue ids continue to be injected into `check_story`, never looked up by it. (CLAUDE.md)
- **`scripts/` stays pure stdlib** except the existing `yaml` import in `story_cut.py`, which is for the ledger only.
- **`story_cut.py <book>` behaviour is unchanged.** Every existing test in `tests/test_story_cut*.py` must pass untouched.
- **Beats are one visible change** — the phrase the craft document must teach. (spec §2.2)
- Run the full suite with `python3 -m pytest` from the repo root (`pytest.ini` sets `pythonpath=.`). Baseline before this plan: **929 passing**.
- Commit after each task. Work on `main`.

## File Structure

| File | Responsibility |
|---|---|
| `scripts/story_cut.py` (modify) | add `_DIRECTIVE_OPENERS` + `directive_advisories()`, call it from `check_story`, add the `check` branch to `main` |
| `scripts/penny_paths.py` (modify) | add a `resolve-dir` CLI verb so a runbook can list an overlay directory's union from the shell |
| `config/story-craft/writing-beats.md` (create) | the craft document — the engine's only shipped file in that overlay directory |
| `agents/story-author.md` (create) | the authoring role and its authority table |
| `commands/plot-book.md` (modify) | step 6 cites the craft document; a new `story.md` gets a self-describing header |
| `CLAUDE.md` (modify) | source-layer paragraph learns the advisory, the `check` subcommand, and the new agent |
| `tests/test_story_cut.py` (modify) | advisory unit tests against `check_story` |
| `tests/test_story_cut_cli.py` (modify) | `check` subcommand exit codes and output filtering |
| `tests/test_penny_paths.py` (modify) | `resolve-dir` union/shadowing |
| `tests/test_story_craft_doc.py` (create) | contract test: the craft doc teaches block names the parsers actually read |
| `tests/test_story_author_agent.py` (create) | contract test: the authority table matches what `story_cut.py` validates |
| `tests/test_plot_book_command.py` (modify) | step 6 cites the craft path and has dropped the old clause |
| `tests/test_claude_md_check_count.py` (modify) | CLAUDE.md names the advisory and the `check` subcommand |

---

### Task 1: The `directive-shaped-beat` advisory

**Files:**
- Modify: `scripts/story_cut.py` (module constants near line 34; `check_story` before its `return` at line 200)
- Test: `tests/test_story_cut.py`

**Interfaces:**
- Consumes: `scripts.penny_story.parse_story(text) -> list[dict]`, where each beat dict has keys `text` (prose, tags stripped), `strands`, `jobs`, `opens`, `closes`, `clues`, `line`.
- Produces: `story_cut._DIRECTIVE_OPENERS` (a `frozenset[str]`) and `story_cut.directive_advisories(beats: list[dict]) -> list[str]`. `check_story`'s return shape is unchanged — `{"blocking": [...], "notes": [...]}` — with advisories appended to `notes`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_story_cut.py`:

```python
def test_directive_shaped_beat_is_advised_not_blocked():
    story = (
        "- Plant only the visible contradiction: a glimpse suggests Lisa met\n"
        "  someone she treated as Maggie.\n  @maggie\n\n"
        "- Maggie finds Lisa dead at the wheel.\n  @maggie\n"
    )
    r = check_story(story, "", JOBS, [])
    assert not [f for f in r["blocking"] if "directive-shaped-beat" in f]
    advisories = [n for n in r["notes"] if "directive-shaped-beat" in n]
    assert len(advisories) == 1
    assert "beat 1" in advisories[0]


def test_every_opener_in_the_closed_list_is_advised():
    from scripts.story_cut import _DIRECTIVE_OPENERS
    for word in _DIRECTIVE_OPENERS:
        story = f"- {word} the thing that happens next.\n  @maggie\n"
        r = check_story(story, "", JOBS, [])
        assert [n for n in r["notes"] if "directive-shaped-beat" in n], word


def test_ordinary_beats_containing_those_words_are_silent():
    story = (
        "- Maggie lets the kiln cool before she opens it.\n  @maggie\n\n"
        "- Faye keeps the corner table free all morning.\n  @faye\n\n"
        "- Tom makes a joke about the surf-club minutes.\n  @tom\n"
    )
    r = check_story(story, "", JOBS, [])
    assert not [n for n in r["notes"] if "directive-shaped-beat" in n]


def test_advisory_names_the_block_the_note_probably_wants():
    story = "- Do not reveal the impostor here.\n  @maggie\n"
    r = check_story(story, "", JOBS, [])
    note = [n for n in r["notes"] if "directive-shaped-beat" in n][0]
    assert "## Guardrails" in note
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut.py -k directive -v`
Expected: FAIL — `ImportError` on `_DIRECTIVE_OPENERS`, and empty advisory lists.

- [ ] **Step 3: Implement**

In `scripts/story_cut.py`, after the `_SCHEDULE_SIGILS` constant (line 34), add:

```python
#: Beats that open with one of these read as instructions to the writer, not
#: as something the reader watches happen (spec 2026-08-06 §5.1). Advisory
#: only, and deliberately grammar rather than judgment: the other two tells
#: the craft document teaches — an abstraction as subject, a verb that is not
#: an action — occur in perfectly good beats, and a checker for them would
#: fire on innocent lines. Same reasoning that keeps reveal-detection an LLM
#: judgment on inspector-fairplay instead of a name-grep.
_DIRECTIVE_OPENERS = frozenset({
    "Plant", "Keep", "Save", "Show", "Do", "Don't", "Avoid", "Ensure",
    "Establish", "Introduce", "Reveal", "Treat", "Let", "Leave", "Use",
    "Make",
})

_OPENER_RE = re.compile(r"^\s*(?P<word>[A-Za-z']+)")


def directive_advisories(beats: list) -> list:
    """Non-blocking notes for beats shaped like directions to the writer."""
    out = []
    for n, beat in enumerate(beats, 1):
        m = _OPENER_RE.match(beat["text"])
        if m and m.group("word") in _DIRECTIVE_OPENERS:
            out.append(
                f"directive-shaped-beat: beat {n} opens with "
                f"\"{m.group('word')}\", which addresses the writer rather "
                f"than describing what happens. If it is about how the prose "
                f"should read it belongs in `## Guardrails`; if it is about "
                f"where chapters fall, in `## Chapter Direction`. Advisory — "
                f"nothing blocks on it.")
    return out
```

Then in `check_story`, immediately before `return {"blocking": blocking, "notes": notes}` (line 200), add:

```python
    notes.extend(directive_advisories(beats))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut.py -v`
Expected: PASS, including the 29 pre-existing tests.

- [ ] **Step 5: Verify the advisory cannot refuse a cut**

Run: `python3 -m pytest tests/test_story_cut_cli.py tests/test_story_cut_emit.py -v`
Expected: PASS — the cut is unaffected; it simply prints one more `note:` line when a story has a directive-shaped beat.

- [ ] **Step 6: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut.py
git commit -m "feat(story): advise on beats shaped like directions to the writer"
```

---

### Task 2: `story_cut.py check <book>`

**Files:**
- Modify: `scripts/story_cut.py` (`main`, from line 679)
- Test: `tests/test_story_cut_cli.py`

**Interfaces:**
- Consumes: `story_cut.check_story` and `story_cut.directive_advisories` from Task 1; `story_cut._job_ids_and_titles()`, `story_cut._ledger(root, book)` (returns `(clues, ledger_data, ledger_path)`).
- Produces: `story_cut.main(["check", "<book>"]) -> int` returning 0 (clean, advisories allowed), 1 (blocking findings), 2 (usage/missing file). `story_cut.main(["<book>"])` is unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_story_cut_cli.py`. The existing `_series` helper writes a clean book-02 story, cut plan, and ledger; `check` ignores the cut plan entirely.

```python
def test_check_exits_zero_on_a_clean_story(tmp_path, monkeypatch, capsys):
    _series(tmp_path, monkeypatch)
    assert story_cut.main(["check", "02"]) == 0
    assert "beats-without-chapter" not in capsys.readouterr().out


def test_check_suppresses_beats_without_chapter_but_not_other_findings(
        tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-unknown-id\n",
        encoding="utf-8")
    assert story_cut.main(["check", "02"]) == 1
    out = capsys.readouterr().out
    assert "unknown-clue" in out
    assert "beats-without-chapter" not in out


def test_check_prints_advisories_under_their_own_heading_and_still_exits_zero(
        tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").write_text(
        "- Plant the contradiction here.\n  @maggie\n\n"
        "- Maggie finds Lisa dead.\n  @maggie !c-altered\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    assert story_cut.main(["check", "02"]) == 0
    out = capsys.readouterr().out
    assert "Advisory" in out
    assert "directive-shaped-beat" in out


def test_check_needs_no_cut_plan(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "cut-plan.md").unlink()
    assert story_cut.main(["check", "02"]) == 0


def test_check_reports_a_missing_story(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").unlink()
    assert story_cut.main(["check", "02"]) == 2


def test_usage_line_names_both_forms(capsys):
    assert story_cut.main([]) == 2
    assert "check" in capsys.readouterr().err


def test_bare_check_is_not_mistaken_for_a_book_number(tmp_path, monkeypatch, capsys):
    """`story_cut.py check` with no book resolves book-check, which has no
    story — a clean exit 2, never a traceback."""
    _series(tmp_path, monkeypatch)
    assert story_cut.main(["check"]) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_story_cut_cli.py -k check -v`
Expected: FAIL — `main(["check", "02"])` returns 2 from the `len(argv) != 1` guard.

- [ ] **Step 3: Implement**

In `scripts/story_cut.py`, add this function immediately above `def main(`:

```python
def _check(book: str) -> int:
    """Validate story.md alone — no cut plan, no writes (spec 2026-08-06 §5).

    `beats-without-chapter` is filtered out because with no cut plan it fires
    once per beat, which is what a story mid-writing looks like, not a defect.
    Same call /book-status already made when it gave that finding to the `cut
    plan` row rather than the `story` row.
    """
    root = penny_paths.series_root()
    story_p = root / "input" / f"book-{book}" / "story.md"
    if not story_p.is_file():
        print(f"story_cut: missing {story_p}", file=sys.stderr)
        return 2

    job_ids, _ = _job_ids_and_titles()
    clues, _, _ = _ledger(root, book)
    result = check_story(story_p.read_text(encoding="utf-8"), "",
                         job_ids, list(clues))

    findings = [f for f in result["blocking"]
                if not f.startswith("beats-without-chapter")]
    for f in findings:
        print(f)
    if result["notes"]:
        print("\nAdvisory — nothing blocks on these:")
        for note in result["notes"]:
            print(f"  {note}")
    if not findings:
        print(f"story_cut: {story_p} has no blocking findings")
    return 1 if findings else 0
```

Then replace the head of `main` (lines 680-684) with:

```python
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "check":
        return _check(argv[1])
    if len(argv) != 1:
        print("usage: story_cut.py <book> | story_cut.py check <book>",
              file=sys.stderr)
        return 2
    book = argv[0]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_story_cut_cli.py -v`
Expected: PASS, including every pre-existing cut test.

- [ ] **Step 5: Commit**

```bash
git add scripts/story_cut.py tests/test_story_cut_cli.py
git commit -m "feat(story): story_cut.py check NN validates a story with no cut plan"
```

---

### Task 3: `penny_paths.py resolve-dir`

**Files:**
- Modify: `scripts/penny_paths.py` (`_main`, from line 141)
- Test: `tests/test_penny_paths.py`

**Interfaces:**
- Consumes: `penny_paths.config_dir_files(rel, pattern="*.md", root=None) -> list[Path]` (already exists — union across tiers, shadowing per filename, highest tier wins).
- Produces: `penny_paths._main(["resolve-dir", "<rel>"]) -> int`, printing one absolute path per line to stdout, exit 0. A runbook or agent uses it to list an overlay directory's union from the shell.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_penny_paths.py` (follow the existing series-fixture style in that file for `monkeypatch`ing `series_root`; if the file has a helper for a fake series root, reuse it rather than writing a second one):

```python
def test_resolve_dir_prints_one_path_per_line(tmp_path, monkeypatch, capsys):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "config" / "story-craft").mkdir(parents=True)
    (tmp_path / "config" / "story-craft" / "series-note.md").write_text(
        "x", encoding="utf-8")
    monkeypatch.setattr(penny_paths, "series_root", lambda *a, **k: tmp_path)

    assert pp._main(["resolve-dir", "story-craft"]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert str(tmp_path / "config" / "story-craft" / "series-note.md") in lines
    assert all(Path(l).is_file() for l in lines)


def test_resolve_dir_takes_a_glob(tmp_path, monkeypatch, capsys):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "config" / "story-craft").mkdir(parents=True)
    (tmp_path / "config" / "story-craft" / "note.md").write_text(
        "x", encoding="utf-8")
    (tmp_path / "config" / "story-craft" / "data.yaml").write_text(
        "k: v", encoding="utf-8")
    monkeypatch.setattr(penny_paths, "series_root", lambda *a, **k: tmp_path)

    assert pp._main(["resolve-dir", "story-craft", "*.yaml"]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert [Path(l).name for l in lines] == ["data.yaml"]


def test_resolve_dir_usage_error(capsys):
    assert pp._main(["resolve-dir"]) == 2
```

These tests deliberately assert nothing about the plugin tier's own files, so this
task carries no dependency on Task 4. The union-and-shadowing property against the
shipped default is asserted in Task 4's contract test, where the shipped file exists.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_penny_paths.py -k resolve_dir -v`
Expected: FAIL — `_main` prints the usage line and returns 2 for an unknown verb.

- [ ] **Step 3: Implement**

In `scripts/penny_paths.py`'s `_main`, after the `resolve` branch, add:

```python
    if argv[0] == "resolve-dir" and len(argv) in (2, 3):
        rel = argv[1]
        pattern = argv[2] if len(argv) == 3 else "*.md"
        for p in config_dir_files(rel, pattern=pattern):
            print(p)
        return 0
```

and update both usage strings in that function to:

```python
    print("usage: penny_paths resolve <config|series|input|output|penny> <rel>"
          " | resolve-dir <rel> [glob] | active", file=sys.stderr)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_penny_paths.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/penny_paths.py tests/test_penny_paths.py
git commit -m "feat(paths): resolve-dir lists an overlay directory's union"
```

---

### Task 4: The craft document

**Files:**
- Create: `config/story-craft/writing-beats.md`
- Test: `tests/test_story_craft_doc.py`

**Interfaces:**
- Consumes: nothing — it is data.
- Produces: a file at `config/story-craft/writing-beats.md` whose routing table names the three block headings the parsers read. `scripts/penny_story.py` reads `## Guardrails` and `## Chapter Direction` via `parse_directives(text, heading)` and `## Questions` via `QUESTIONS_HEADING_RE`.

- [ ] **Step 1: Write the failing contract test**

Create `tests/test_story_craft_doc.py`:

```python
"""Contract test: the shipped craft document must teach block names the
parsers actually read, and must reach consumers through the overlay.

Same failure mode test_outline_expander_agent.py pins — a document that
teaches a heading no parser matches looks right and is silently wrong. Here
the routing rule tells the author "put that note in `## Guardrails`", and if
that heading string ever drifts from what penny_story.parse_directives folds
on, the advice sends notes into a block nothing reads.
"""
from pathlib import Path

from scripts import penny_paths
from scripts.penny_story import parse_directives, parse_questions

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "config" / "story-craft" / "writing-beats.md"


def test_the_document_ships():
    assert DOC.is_file()


def test_it_is_reachable_through_the_overlay_directory():
    names = [p.name for p in penny_paths.config_dir_files(
        "story-craft", root=REPO)]
    assert "writing-beats.md" in names


def test_a_series_file_unions_and_only_its_own_name_shadows(tmp_path, monkeypatch):
    """The reason this is a directory read and not config_path: a genre or
    series adding one file must not hide the engine's default."""
    (tmp_path / ".penny").mkdir()
    (tmp_path / "config" / "story-craft").mkdir(parents=True)
    (tmp_path / "config" / "story-craft" / "cozy-beats.md").write_text(
        "extra", encoding="utf-8")
    monkeypatch.setattr(penny_paths, "series_root", lambda *a, **k: tmp_path)

    names = [p.name for p in penny_paths.config_dir_files("story-craft")]
    assert "cozy-beats.md" in names
    assert "writing-beats.md" in names


def test_routing_rule_names_headings_the_parsers_fold_on():
    text = DOC.read_text(encoding="utf-8")
    for heading in ("## Guardrails", "## Chapter Direction", "## Questions"):
        assert heading in text, heading

    probe = ("## Guardrails\n- a note. @maggie\n\n"
             "## Chapter Direction\n- a boundary note. @maggie\n\n"
             "## Questions\n- q-x — a question?\n")
    assert parse_directives(probe, "Guardrails")
    assert parse_directives(probe, "Chapter Direction")
    assert parse_questions(probe) == {"q-x": "a question?"}


def test_it_teaches_the_test_and_the_beat_size_rule():
    text = DOC.read_text(encoding="utf-8")
    assert "one visible change" in text
    assert "directive-shaped-beat" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_story_craft_doc.py -v`
Expected: FAIL — the file does not exist.

- [ ] **Step 3: Write the document**

Create `config/story-craft/writing-beats.md` with exactly this content:

````markdown
# Writing beats

The engine's default craft guidance for `input/book-NN/story.md`
(spec `2026-08-06-dramatic-beat-authoring-design.md` §3).

This file is read through the config overlay as a **directory** — a genre pack
or a series adds files beside it, and only a file of the same name replaces it.

## What a beat is

**A beat is a change on the page.** Someone wants something, does something,
and the situation is different afterwards.

If you cannot see it happen — who is present, what they do, what is true after
that was not before — it is not a beat yet.

**One beat is one visible change.** A bullet carrying four characters through
five actions is four beats. Chapters are made of beats later; a beat is not a
small chapter.

## Three tells that you have written architecture instead

**1 — The subject is an abstraction.**

> The town's warmth is strained by money and premises fear.

Nothing happened. A condition was described.

**2 — The verb is not an action.** *surfaces, reads as, is seeded, establishes,
gives, shows.*

> Cal's thread surfaces through practical repair.

Surfacing is something the *book* does, not something Cal does.

**3 — It addresses the writer, not the world.** *Plant, Keep, Save for later,
Do not reveal, rather than.*

> Plant only the visible contradiction: a glimpse, log or half-overheard gossip
> suggests Lisa may have met someone she treated as Maggie. Do not reveal the
> witness's certainty here.

That is a guardrail wearing a beat's clothes. `story_cut.py check NN` will name
it as `directive-shaped-beat` — advisory, never blocking, because only this
third tell is grammar rather than judgment.

## The repair

Ask **what does the reader watch happen?** and write that.

> Faye's premises fear surfaces through bakery work and customer rhythm rather
> than exposition.

becomes

> Faye hides the adjoining-shop letter under a tray when Maggie asks who else
> wanted The Wheelhouse.

Same information, now visible.

## Where the rest goes

Nothing you wrote is deleted. It is filed:

| the note is about | it belongs in |
|---|---|
| how the prose should read | `## Guardrails` |
| where chapters should fall | `## Chapter Direction` |
| what a question means | `## Questions` |
| what happens | the beat |

Direction and guardrails scope with the same sigils the beats use — `@strand`,
`#job`, or untagged for book-wide. Never a chapter number: chapters do not
exist until the cut, so any chapter-shaped scoping is invalidated by the next
re-cut.

## What a beat never carries

Chapter numbers, packet sections, Character Knowledge, Starting/Ending State,
wiring rows. All of those are **derived** by the cut from the ledger, the genre
and your tags. If you are typing one into `story.md`, it is already being
written for you somewhere else.
````

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_story_craft_doc.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config/story-craft/writing-beats.md tests/test_story_craft_doc.py
git commit -m "feat(craft): ship the beat-craft document under the config overlay"
```

---

### Task 5: The `story-author` agent

**Files:**
- Create: `agents/story-author.md`
- Test: `tests/test_story_author_agent.py`

**Interfaces:**
- Consumes: the craft document from Task 4 (by path, not by restating it); `story_cut._DIRECTIVE_OPENERS` is *not* referenced by the agent.
- Produces: an agent doc with `name: story-author` frontmatter, following `agents/_TEMPLATE.md`'s section order (Role posture, Independence, Inputs, Outputs, Instructions).

- [ ] **Step 1: Write the failing contract test**

Create `tests/test_story_author_agent.py`:

```python
"""Contract test: the story-author's authority table must match what the
engine actually validates.

story_cut.py checks @strand for slug SHAPE only, and checks #job and !clue-id
against external data (the genre's macro-structure, the whodunit ledger). An
agent brief that got this backwards would either refuse to name strands or
mint ledger ids freely — the second is what produced book 01's 18 unknown-clue
and unknown-job findings.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AGENT = REPO / "agents" / "story-author.md"


def test_agent_ships_with_the_expected_frontmatter():
    text = AGENT.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "name: story-author" in text


def test_it_defers_to_the_craft_document_rather_than_restating_it():
    text = AGENT.read_text(encoding="utf-8")
    assert "config/story-craft/" in text


def test_authority_table_gets_the_three_id_kinds_right():
    text = AGENT.read_text(encoding="utf-8")
    assert "^[a-z0-9][a-z0-9-]*$" in text          # strand: shape only
    assert "ledger fact" in text                    # clue: not the agent's
    assert "genre fact" in text                     # job: not the agent's
    assert "plant_chapter" in text                  # never authored


def test_it_states_the_propose_then_write_posture():
    text = AGENT.read_text(encoding="utf-8")
    for phrase in ("never renumbers", "outside the named range",
                   "at most one"):
        assert phrase in text, phrase
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest tests/test_story_author_agent.py -v`
Expected: FAIL — the file does not exist.

- [ ] **Step 3: Write the agent**

Create `agents/story-author.md`:

````markdown
---
name: story-author
description: Writes and repairs beats in story.md with the showrunner — dramatic beats, in story order, within a named range. Proposes; writes only on approval; never mints a ledger or genre id.
---
# Story Author

**Role posture:** the showrunner's hand on the source layer. Context-rich: you read
the sealed solution, because beats are written toward an ending.

**Independence:** not this agent's property. Knowing the solution is what lets a beat
land where it should; it is not licence to put the answer on the page.

**Inputs:** `{ input/book-NN/story.md, the union of config/story-craft/ (list it with
`penny_paths.py resolve-dir story-craft`), series/whodunit/book-NN.yaml (read-only),
the active genre's macro-structure job list, output/book-NN/mystery-solution.md,
and the beat range the showrunner names }`.

**Outputs:** proposed beat prose, in conversation. On the showrunner's explicit
approval, the same beats written into `input/book-NN/story.md` — inside the named
range and nowhere else.

## Craft

Read `config/story-craft/writing-beats.md` before you write anything. It is the
definition of a beat, and it is not restated here — one copy, one source.

The short version, so you know what you are being held to: a beat is a change on
the page, one visible change per beat, and a note addressed to the writer belongs
in `## Guardrails` rather than in a bullet.

## Authority

What you own, and what you must ask for. Drawn from what `story_cut.py` actually
validates.

| tag | yours? |
|---|---|
| `@strand` | **Yours to mint.** Only the slug shape `^[a-z0-9][a-z0-9-]*$` is enforced — strands are the author's own map of the book. |
| `!clue-id` | **Not yours.** A clue is a **ledger fact**. If a beat plants something new, name what it plants, in conversation, and stop. The showrunner writes the entry, with a `description:` and never a `plant_chapter:` — the cut resolves that. |
| `#job` | **Not yours.** A job is a **genre fact**. A job the genre's macro-structure does not declare is a genre-pack decision, escalated, never invented in the story. |
| `+q-id` / `-q-id` | You may open a question, but you must add its prose to `## Questions` and you must close it. **At most one** question survives a book — the seed its last chapter hooks. |
| beat prose in range | Yours to propose, under the craft document. |

State every one of these you needed and could not do. An agent that mints an id to
keep moving is how a story collects `unknown-clue` findings it cannot see.

## Instructions

1. Read the craft document, the story, the ledger, the job list, and the solution.
2. Confirm the beat range the showrunner named. If they named none, ask — you work a
   range, never the whole file at once.
3. Propose the rewritten beats, in conversation, in story order, tags trailing.
   Preserve the showrunner's phrasing wherever it already works; you are repairing
   beats, not restyling them.
4. Name separately, in a short list: every clue the beats now need, every job the
   genre does not declare, every question you opened.
5. On approval, write the range — and only the range. **Never renumber, never touch
   beats outside the named range, never reorder blocks.**
6. Tell the showrunner to run `story_cut.py check NN` when you are done.
````

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest tests/test_story_author_agent.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/story-author.md tests/test_story_author_agent.py
git commit -m "feat(agents): story-author writes beats and owns no ledger ids"
```

---

### Task 6: `/plot-book` step 6 and the self-describing header

**Files:**
- Modify: `commands/plot-book.md:106-118`
- Test: `tests/test_plot_book_command.py`

**Interfaces:**
- Consumes: `config/story-craft/writing-beats.md` (Task 4), `penny_paths.py resolve-dir` (Task 3).
- Produces: nothing other tasks consume.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plot_book_command.py`:

```python
def test_stage_chapters_points_at_the_craft_document():
    t = CMD.read_text(encoding="utf-8")
    assert "config/story-craft" in t
    assert "resolve-dir story-craft" in t


def test_stage_chapters_no_longer_defines_a_beat_by_its_syntax_alone():
    """The old clause described only the tag layout, which is what produced
    correctly-tagged architecture notes instead of beats (spec §1)."""
    t = CMD.read_text(encoding="utf-8")
    assert "one per bullet, prose first, tags\n   trailing" not in t
    assert "one visible change" in t


def test_a_new_story_gets_a_self_describing_header():
    t = CMD.read_text(encoding="utf-8")
    assert "writing-beats.md" in t
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_plot_book_command.py -k "craft or syntax or self_describing" -v`
Expected: FAIL on all three.

- [ ] **Step 3: Edit the runbook**

In `commands/plot-book.md`, replace lines 106-111 (the paragraph beginning `6. **Stage chapters:**` through `...the beat that plants it.`) with:

```markdown
6. **Stage chapters:** write `input/book-$book/story.md` directly — beats in
   story order between the turning points, one per bullet, tags trailing
   (`@strand`, `#job`, `+question`/`-question`, `!clue-id` — spec
   `2026-08-03-story-source-layer-design.md` §3).

   **Read the craft document before you write a single beat:**

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/penny_paths.py" resolve-dir story-craft
   ```

   Read every path it prints. That union — the engine's
   `config/story-craft/writing-beats.md` plus anything the genre or series adds
   — is what a beat is. The short version, which does not replace reading it:
   a beat is a change on the page, **one visible change per beat**, and a note
   addressed to the writer ("plant this", "do not reveal that", "keep it
   subtext") is not a beat — it belongs in `## Guardrails`, or in
   `## Chapter Direction` if it is about where chapters fall.

   Draw the clue schedule from `series/whodunit/book-$book.yaml` and tag each
   clue's `!clue-id` onto the beat that plants it.

   Open the file with this header, so an agent that arrives later — in this
   session or in another model entirely — finds the craft document from the
   file itself:

   ```markdown
   # Story — book NN

   Beats in story order. Chapters do not exist here; the cut decides them.
   Four sigils carry meaning — `@strand` `#job` `+q-id`/`-q-id` `!clue-id`.
   Everything else is for your reading.

   What a beat is: config/story-craft/writing-beats.md (read it before editing).
   Check this file with: story_cut.py check NN
   ```
```

Leave lines 112-135 (the `chapter-weaver` fold note, the re-plot `woven:` guidance, and the stamp command) exactly as they are.

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest tests/test_plot_book_command.py -v`
Expected: PASS, including the pre-existing runbook tests.

- [ ] **Step 5: Commit**

```bash
git add commands/plot-book.md tests/test_plot_book_command.py
git commit -m "docs(plot-book): stage chapters teaches beats, not just tag syntax"
```

---

### Task 7: CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (the source-layer paragraph around line 159, and the agent roster mention)
- Test: `tests/test_claude_md_check_count.py`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_claude_md_check_count.py`:

```python
def test_claude_md_documents_the_check_subcommand_and_the_advisory():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "story_cut.py check" in text
    assert "directive-shaped-beat" in text
    assert "sixteen findings" in text          # unchanged — no finding added


def test_claude_md_names_the_craft_document_and_the_authoring_agent():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "config/story-craft/" in text
    assert "story-author" in text
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_claude_md_check_count.py -v`
Expected: FAIL on both new tests.

- [ ] **Step 3: Edit CLAUDE.md**

In the source-layer section, after the sentence ending `— no waivers at this level (spec §8): fix the story or the cut plan.`, add this paragraph:

```markdown
What a beat *is* — as opposed to how it is tagged — lives in the config overlay at
`config/story-craft/`, read as a **directory** so a genre pack can add to it without
copying it (spec `2026-08-06-dramatic-beat-authoring-design.md`). A beat is a change
on the page, one visible change per beat; a note addressed to the writer belongs in
`## Guardrails`, and a note about where chapters fall in `## Chapter Direction`.
`/plot-book`'s chapters stage reads that union before writing a beat, and the
**`story-author`** agent works a named range of beats with the showrunner — it may
mint `@strand` slugs (shape-checked only) but never a `!clue-id` (a ledger fact) or a
`#job` (a genre fact), which is the authority book 01's 18 invented ids went missing.
`story_cut.py check NN` validates a story with no cut plan, suppressing
`beats-without-chapter` (with no plan it fires once per beat) and printing the one
advisory, **`directive-shaped-beat`** — a beat opening with an imperative such as
*Plant* or *Do not*. It rides the existing non-blocking `notes` channel, never
`blocking`: the sixteen findings stay sixteen, and an advisory that could block would
just be a seventeenth with a softer name.
```

Also add `story-author` to the roster sentence in the "Orchestration" layer description (the parenthetical listing `drafter, the 5 isolated inspectors, the context-rich developmental-editor, line/copy editors, beta-reader, etc.`).

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest tests/test_claude_md_check_count.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest`
Expected: PASS — 929 baseline plus the new tests, zero failures.

- [ ] **Step 6: Commit and push**

```bash
git add CLAUDE.md tests/test_claude_md_check_count.py
git commit -m "docs: CLAUDE.md learns the craft doc, story-author, and check NN"
git push
```

---

## Out of scope

Per spec §8 and §10, this plan does **not** touch book 01 or anything in
`~/myBooks/pelicanscrook-series`. The migration is series work the showrunner does with
the new role, in the order spec §8 records: split and file, resolve findings, delete the
outline and lock, then cut.
