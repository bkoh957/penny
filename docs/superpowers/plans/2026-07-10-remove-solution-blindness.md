# Remove Solution-Blindness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete solution-blindness as an engine rule, moving its one real guarantee (no reveal before `reveal_chapter`) onto `inspector-fairplay` as a blocking predicate.

**Architecture:** Five agents become solution-aware; the beta-reader stays unknowing under a new justification ("reader simulation"). The premature-reveal rubric clause moves into the cozy genre pack. `scripts/` is not touched at all — the predicate is an LLM judgment and must stay out of the deterministic layer.

**Tech Stack:** Python 3 stdlib, pytest, PyYAML (unused here). Agents and commands are Markdown; tests assert on their prose contracts.

**Spec:** `docs/superpowers/specs/2026-07-10-remove-solution-blindness-design.md`

## Global Constraints

- **Zero changes under `scripts/`.** If a task tempts you to add a checker, stop — the spec forbids it. A name-grep for the culprit fires on every innocent sentence she appears in.
- **`tests/test_beta_scaffold.py` must pass untouched, at every commit.** It is the regression bar proving reader simulation survived. Never edit it.
- **Full suite green after every task:** `python3 -m pytest`. Baseline is **330 passed**.
- **Canonical strings** (tests assert on these verbatim; keep them identical across tasks):
  - Input token: `mystery-solution.md`
  - Inspector input token: `reveal_chapter`
  - Predicate phrase: `premature reveal`
  - Rubric clause heading: `4. **No premature reveal.**`
- **Australian spelling** in any prose added to agents/rubrics (per the existing guardrail).
- Commit after every task. Work on `main` (repo convention).
- Run tests from the repo root (`~/myTools/penny`); `pytest.ini` sets `pythonpath=.`, and tests resolve `Path("agents")` relative to cwd.

---

### Task 1: Give `inspector-fairplay` the solution and the premature-reveal predicate

Do this **first**. It installs the guard before any blindness is removed, so the repo is never in a state where the drafter knows the answer and nothing watches the page.

**Files:**
- Modify: `agents/inspector-fairplay.md:9-16` (Independence + Inputs), `:23-32` (Instructions)
- Modify: `genres/cozy-mystery/review-rubrics/fairplay-planting.md` (Inputs line; add clause 4; add blocking bullet)
- Modify: `commands/review-chapter.md` (pass `reveal_chapter` + solution to the fairplay dispatch)
- Create: `tests/test_solution_visibility.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the file `tests/test_solution_visibility.py`, exporting module constants
  `AGENTS = Path("agents")`, `COMMANDS = Path("commands")`,
  `GENRE_RUBRICS = Path("genres/cozy-mystery/review-rubrics")`, and the helper
  `_flat(p: Path) -> str` (collapses whitespace, lowercases — assertions must survive
  line-wrapping). Tasks 2–6 append to this file and reuse all four.

- [ ] **Step 1: Write the failing test**

Create `tests/test_solution_visibility.py`:

```python
"""Contract tests for the removal of solution-blindness (spec 2026-07-10).

Solution-blindness is gone; isolation and reader simulation remain. These tests
pin the prose contracts of the agents and commands that changed, so a future
edit cannot silently reintroduce a guardrail nothing enforces.
"""
from pathlib import Path

AGENTS = Path("agents")
COMMANDS = Path("commands")
GENRE_RUBRICS = Path("genres/cozy-mystery/review-rubrics")


def test_inspector_fairplay_receives_solution_and_reveal_chapter():
    text = (AGENTS / "inspector-fairplay.md").read_text(encoding="utf-8")
    assert "mystery-solution.md" in text
    assert "reveal_chapter" in text
    assert "never the sealed solution" not in text


def test_inspector_fairplay_declares_premature_reveal_predicate():
    text = (AGENTS / "inspector-fairplay.md").read_text(encoding="utf-8")
    assert "premature reveal" in text.lower()
    assert "blocking_issues" in text


def _flat(p: Path) -> str:
    """Collapse newlines/indent so assertions survive line-wrapping."""
    return " ".join(p.read_text(encoding="utf-8").split()).lower()


def test_inspector_fairplay_keeps_its_isolation():
    """Solution-awareness must not become cross-talk: no other agent's output."""
    flat = _flat(AGENTS / "inspector-fairplay.md")
    assert "no drafting history" in flat
    assert "no other agent's output" in flat


def test_fairplay_rubric_carries_the_premature_reveal_clause():
    text = (GENRE_RUBRICS / "fairplay-planting.md").read_text(encoding="utf-8")
    assert "4. **No premature reveal.**" in text
    assert "reveal_chapter" in text


def test_review_chapter_passes_reveal_chapter_to_fairplay():
    text = (COMMANDS / "review-chapter.md").read_text(encoding="utf-8")
    assert "reveal_chapter" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_solution_visibility.py -v`
Expected: 5 FAILED, all `AssertionError` (files exist; the strings do not). Not `FileNotFoundError` — if you see that, your cwd is wrong.

- [ ] **Step 3: Rewrite the agent's Independence + Inputs**

In `agents/inspector-fairplay.md`, replace lines 9-16 (the `**Independence:**` paragraph and the `**Inputs:**` line) with:

```markdown
**Isolation (not blindness):** you receive no other agent's output and no drafting
history. Isolation is about *whose reasoning* you can see, never about *what is true* —
so you DO receive the solution. It lets you judge whether the page gives the game away
before it should. Your inputs are the chapter text, the rubric
`review-rubrics/fairplay-planting.md` (resolved via `config_path`, the series →
genre → default overlay — for a cozy series this is
`genres/cozy-mystery/review-rubrics/fairplay-planting.md`), the ledger slice (this
chapter's clue-planting obligations), the sealed `output/book-NN/mystery-solution.md`,
and this book's `reveal_chapter`.

**Inputs:** `{ text, review-rubrics/fairplay-planting.md, ledger_slice, mystery-solution.md, reveal_chapter }`.
```

- [ ] **Step 4: Add the predicate to the agent's Instructions**

In the same file, insert a new numbered instruction between the current items 3 and 4 (renumbering the rest):

```markdown
4. **Premature reveal.** Using the solution and `reveal_chapter`, judge whether this
   chapter asserts or confirms the culprit's guilt before `reveal_chapter`. Naming the
   culprit is NOT a violation — they are an on-page suspect for most of the book. Tying
   them to guilt, motive, or the central deception IS. Any such assertion before
   `reveal_chapter` goes in `blocking_issues`. If this book has no locked ledger, no
   `reveal_chapter` is passed: say so in `evidence[]` and skip this check.
```

- [ ] **Step 5: Add the clause to the genre rubric**

In `genres/cozy-mystery/review-rubrics/fairplay-planting.md`, replace the `**Inputs (fixed contract, §6):**` paragraph with:

```markdown
**Inputs (fixed contract, §6):** `{ text, this rubric, ledger_slice, mystery-solution.md,
reveal_chapter }`. The slice carries this chapter's clue-planting obligations (§5a). You
receive the solution: isolation means no other agent's reasoning, not ignorance of the
book. No drafting history.
```

Then, under `## What you are judging`, add after item 3:

```markdown
4. **No premature reveal.** The chapter does not assert or confirm the culprit's guilt
   before `reveal_chapter`. The culprit is a visible character; naming them in ordinary
   scene action is fine. What must never appear before `reveal_chapter` is the culprit
   tied to guilt, motive, or the central deception. Clues stay
   **present-but-unspotlighted**.
```

And in `## Thresholds`, extend the blocking bullet to:

```markdown
- **Blocking:** any obligated clue absent from the prose, planted unfairly, or any
  premature reveal of the culprit's guilt before `reveal_chapter`.
```

- [ ] **Step 6: Pass `reveal_chapter` at the dispatch site**

In `commands/review-chapter.md`, in the step that dispatches the inspectors (the static table at ~line 79 and the dispatch paragraph at ~line 86), append this sentence to the dispatch paragraph:

```markdown
   `inspector-fairplay` additionally receives `output/book-$book/mystery-solution.md`
   and the `reveal_chapter` value read from `series/whodunit/book-$book.yaml`. If the
   book has no locked ledger, dispatch it without `reveal_chapter` — the inspector will
   record the premature-reveal check as not applicable.
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_solution_visibility.py -v`
Expected: 5 passed.

- [ ] **Step 8: Run the full suite**

Run: `python3 -m pytest`
Expected: `335 passed` (330 baseline + 5 new). If `test_inspector_scaffold.py` fails, you removed a string it pins — restore it.

- [ ] **Step 9: Commit**

```bash
git add tests/test_solution_visibility.py agents/inspector-fairplay.md \
  genres/cozy-mystery/review-rubrics/fairplay-planting.md commands/review-chapter.md
git commit -m "feat(fairplay): inspector gains solution + premature-reveal predicate

Installs the guard BEFORE drafter blindness is removed, so the page is never
unwatched. Isolation is preserved: no other agent's output, no drafting history.
The predicate stays out of scripts/ — it is an LLM judgment.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Make the drafter solution-aware

**Files:**
- Modify: `agents/drafter.md:9-10` (Independence), `:12-26` (Inputs)
- Modify: `commands/draft-chapter.md:69-70` (dispatch note)
- Modify: `tests/test_solution_visibility.py` (append)

**Interfaces:**
- Consumes: `tests/test_solution_visibility.py` and its `AGENTS` / `COMMANDS` constants from Task 1.
- Produces: nothing later tasks depend on.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_solution_visibility.py`:

```python
def test_drafter_receives_the_solution():
    text = (AGENTS / "drafter.md").read_text(encoding="utf-8")
    assert "mystery-solution.md" in text
    assert "reveal_chapter" in text


def test_drafter_no_longer_claims_blindness():
    text = (AGENTS / "drafter.md").read_text(encoding="utf-8")
    assert "receives ONLY this chapter's clue-planting obligations" not in text
    assert "never\nthe full sealed" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_solution_visibility.py -k drafter -v`
Expected: 2 FAILED with `AssertionError`. Note `drafter.md` currently mentions
`mystery-solution.md` only inside the clause that *denies* it, so both tests are
genuinely red: the first on `reveal_chapter`, the second on the denial clause.

- [ ] **Step 3: Rewrite the drafter's Independence clause**

In `agents/drafter.md`, replace lines 9-10:

```markdown
**Independence:** receives ONLY this chapter's clue-planting obligations — never
the full sealed `mystery-solution.md` (design §5a). Does not write ledgers.
```

with:

```markdown
**Context:** you receive the sealed `mystery-solution.md`. Knowing the answer is how you
write toward it without accident — foreshadowing that lands, red herrings that are fair.
It is NOT licence to put the answer on the page: do not assert or confirm the culprit's
guilt before this book's `reveal_chapter`. `inspector-fairplay` blocks the gate if you do.
Does not write ledgers.
```

- [ ] **Step 4: Add it to the drafter's Inputs**

In the same file, add a bullet to the `**Inputs:**` list, after the ledger-slice bullet:

```markdown
- The sealed `output/book-NN/mystery-solution.md` (the whodunit answer key) and this
  book's `reveal_chapter` from `series/whodunit/book-NN.yaml`.
```

- [ ] **Step 5: Note it at the dispatch site**

In `commands/draft-chapter.md`, extend step 6 to read:

```markdown
6. **Dispatch the `drafter` sub-agent** with the inputs listed in
   `agents/drafter.md` — which now include `output/book-$book/mystery-solution.md` and
   the `reveal_chapter` from `series/whodunit/book-$book.yaml` — passing `draft_date`
   for the `drafted_on` stamp.
   Write its output to `output/book-$book/chapters/ch-$chapter.draft.md` including
   `drafted_by` and `drafted_on: $draft_date` frontmatter.
```

(`preflight draft N CH` already requires the lock, so the solution is guaranteed to exist.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_solution_visibility.py -v`
Expected: 7 passed.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest`
Expected: `337 passed`.

- [ ] **Step 8: Commit**

```bash
git add tests/test_solution_visibility.py agents/drafter.md commands/draft-chapter.md
git commit -m "feat(drafter): drafter is informed, not blind

Knowing the answer is how you foreshadow it. The reveal-timing constraint moves
to inspector-fairplay, which now blocks on it.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Make the developmental-editor solution-aware

**Files:**
- Modify: `agents/developmental-editor.md:11-18`
- Modify: `commands/review-chapter.md:107-108` (the `(NOT the whodunit solution)` parenthetical)
- Modify: `tests/test_developmental_editor.py:61` (invert the existing assertion)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

- [ ] **Step 1: Invert the existing failing assertion**

In `tests/test_developmental_editor.py`, in `test_agent_is_advisory_and_context_rich`, replace:

```python
    assert "whodunit" in text.lower()                 # explicitly denied the solution
```

with:

```python
    assert "mystery-solution.md" in text              # solution-aware (spec 2026-07-10)
    assert "denied the whodunit solution" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_developmental_editor.py::test_agent_is_advisory_and_context_rich -v`
Expected: FAIL — `assert "mystery-solution.md" in text`.

- [ ] **Step 3: Rewrite the agent's Independence + Inputs**

In `agents/developmental-editor.md`, replace lines 11-18 with:

```markdown
**Independence — context-rich.** Unlike the five inspectors (deliberately isolated), a
developmental editor must know what the chapter is *trying to do*. You receive the
setting pack, a character-bible slice, the chapter brief/intent, and the sealed
`mystery-solution.md` — a craft read is sharper when it knows what the book is building
toward. Independence here is model difference, not ignorance (see `final-reader`).

**Inputs:** `{ draft text, config/review-rubrics/developmental-craft.md, setting-pack,
character-bible slice, chapter brief, mystery-solution.md }`. No drafting history.
```

- [ ] **Step 4: Fix the dispatch site**

In `commands/review-chapter.md`, replace `and the chapter brief (NOT the whodunit solution). Pass` with:

```
and the chapter brief, plus `output/book-$book/mystery-solution.md`. Pass
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_developmental_editor.py -v`
Expected: all passed.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest`
Expected: `337 passed`.

- [ ] **Step 7: Commit**

```bash
git add tests/test_developmental_editor.py agents/developmental-editor.md commands/review-chapter.md
git commit -m "feat(dev-editor): craft read is solution-aware

Independence is model difference, not ignorance — final-reader.md already said so.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Stop lying to the outline-reviewer

`agents/outline-reviewer.md:13` says it is "denied the whodunit solution" while `/review-outline` hands it the whole outline, whose `## Solution` block names the culprit. Make the instruction true by deleting it.

**Files:**
- Modify: `agents/outline-reviewer.md:11-17`
- Modify: `commands/review-outline.md:36-39` (delete the withholding instruction)
- Modify: `tests/test_solution_visibility.py` (append)

**Interfaces:**
- Consumes: `tests/test_solution_visibility.py` from Task 1.
- Produces: nothing.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_solution_visibility.py`:

```python
def test_outline_reviewer_is_not_told_it_is_solution_blind():
    text = (AGENTS / "outline-reviewer.md").read_text(encoding="utf-8")
    assert "denied the whodunit solution" not in text
    assert "Solution-blind" not in text


def test_review_outline_no_longer_withholds_the_solution():
    text = (COMMANDS / "review-outline.md").read_text(encoding="utf-8")
    assert "do NOT pass" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_solution_visibility.py -k outline_reviewer -v`
Expected: FAILED with `AssertionError`.

Also run `python3 -m pytest tests/test_solution_visibility.py -k review_outline -v` → FAILED.

- [ ] **Step 3: Rewrite the agent's Independence block**

In `agents/outline-reviewer.md`, replace the `**Independence — context-rich, NOT blind (but solution-blind).**` paragraph (lines 11-14) and the `**Inputs:**` block (15-17) with:

```markdown
**Independence — context-rich.** You receive the whole outline, the genre coverage rubric,
the series bible, canon-core, and (if present) the arc-ledger. The outline's own
`## Solution` block names the culprit; that is intended. Independence here is that you are
one panel member who does not see the other's take this pass — not ignorance of the book.

**Inputs:** `{ whole outline.md (including its ## Solution block),
genres/<g>/review-rubrics/outline-craft.md, series bible, canon-core, arc-ledger
(optional), the current feedback ledger (for dedup), optional --focus directive }`.
```

- [ ] **Step 4: Fix the agent's hard constraints**

In the same file, in `**Hard constraints:**`, replace the bullet:

```markdown
- **Solution-blind.** Never name or imply the culprit/motive.
```

with:

```markdown
- **Critique the plan, do not leak it into prose.** You may reason about the solution —
  it is in the outline you were given. Your feedback goes to the showrunner, never to
  the page.
```

- [ ] **Step 5: Delete the withholding instruction from the command**

In `commands/review-outline.md`, in step 6, replace:

```markdown
   for dedup, and the `--focus` directive if given). **Solution-blind:** do NOT pass
   `output/book-$1/mystery-solution*.md` or the whodunit answer fields.
```

with:

```markdown
   for dedup, and the `--focus` directive if given). The outline includes its own
   `## Solution` block; panel members reason about the whole book.
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_solution_visibility.py -v`
Expected: 9 passed.

- [ ] **Step 7: Run the full suite**

Run: `python3 -m pytest`
Expected: `339 passed`.

- [ ] **Step 8: Commit**

```bash
git add tests/test_solution_visibility.py agents/outline-reviewer.md commands/review-outline.md
git commit -m "fix(outline-reviewer): stop asserting a blindness it never had

The agent was told it was denied the solution while receiving an outline whose
line 8 names the culprit. Make the instruction true by deleting it.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Retire the outline-expander's withholding apparatus

The expander already sees the solution. What dies is the framing that its discipline is "the ONLY protection" against a leak *to the drafter*, plus the manual post-expansion leak review. What **survives, reframed**, is the reveal-timing rule — now a planning constraint on the outline, enforced downstream by `inspector-fairplay`.

**Files:**
- Modify: `agents/outline-expander.md:3` (description), `:10-14` (Independence), `:80-90` (Guardrails)
- Modify: `commands/expand-outline.md:42-47` (delete step 6, renumber step 7 → 6)
- Modify: `tests/test_solution_visibility.py` (append)

**Interfaces:**
- Consumes: `tests/test_solution_visibility.py` from Task 1.
- Produces: nothing.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_solution_visibility.py`:

```python
def test_outline_expander_drops_the_leak_guard_framing():
    text = (AGENTS / "outline-expander.md").read_text(encoding="utf-8")
    assert "ONLY protection" not in text
    assert "no automated leak-guard" not in text
    assert "MUST stay blind to whodunit" not in text


def test_outline_expander_keeps_the_reveal_timing_rule():
    """The substance survives; only the blindness rationale dies.

    Asserts on the NEW guardrail wording. `present-but-unspotlighted` and the bare
    token `reveal_chapter` both already exist in this file, so asserting on those
    alone would pass before the edit and prove nothing.
    """
    flat = _flat(AGENTS / "outline-expander.md")
    assert "present-but-unspotlighted" in flat
    assert "never schedule a beat" in flat
    assert "before this book's `reveal_chapter`" in flat


def test_expand_outline_drops_the_manual_leak_review():
    text = (COMMANDS / "expand-outline.md").read_text(encoding="utf-8")
    assert "Post-expansion review" not in text
    assert "no automated leak-guard" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_solution_visibility.py -k expander -v`
Expected: **all 3 FAILED**, each with `AssertionError`. If
`test_outline_expander_keeps_the_reveal_timing_rule` passes at this point you have
asserted on text that already exists — fix the test, not the agent.

If the exact whitespace in `"before this\n  book's \`reveal_chapter\`"` proves awkward
to match after your edit, normalise instead: `assert "reveal_chapter" in " ".join(text.split())`
— but keep `"NEVER schedule a beat"`, which is the assertion that must go red first.

- [ ] **Step 3: Rewrite the frontmatter description (line 3)**

```yaml
description: Expands a skeletal chapter stub into the full scene-breakdown outline brief. Context-rich (reads the solution) and schedules clue beats without staging the reveal early; never drafts prose, never writes a ledger or certificate.
```

- [ ] **Step 4: Rewrite the Independence paragraph (lines 10-14)**

```markdown
**Context:** you read the solution to place clue and red-herring beats correctly. You must
not schedule a reveal beat before this book's `reveal_chapter` (see Guardrails) — not
because anyone downstream is blind (the drafter is informed), but because the *story* must
not reveal early. `inspector-fairplay` blocks the gate on the page if it does. This agent
does not draft chapter prose and does not write any ledger or certificate.
```

- [ ] **Step 5: Rewrite the Guardrails heading and its first bullet (lines 80-86)**

Replace the heading:

```markdown
**Guardrails (HARD — there is no automated guard; this discipline is the only protection):**
```

with:

```markdown
**Guardrails (HARD — the outline is what schedules the reveal):**
```

Replace the first bullet:

```markdown
- NEVER name the culprit as the culprit, state the motive/central deception, or mark a
  clue as incriminating a named suspect, in any chapter BEFORE the culprit becomes known
  to the protagonist on the page (the in-story detective-click, ~ch19). The drafter reads
  this file and MUST stay blind to whodunit until the story itself reveals it. Plant clues
  **present-but-unspotlighted**.
```

with:

```markdown
- NEVER schedule a beat that names the culprit as the culprit, states the motive/central
  deception, or marks a clue as incriminating a named suspect, in any chapter BEFORE this
  book's `reveal_chapter` (the in-story detective-click). The drafter knows the answer;
  the *page* must not. Plant clues **present-but-unspotlighted**.
```

Leave the remaining bullets (click chapter onward, culprit-is-visible, victim-alive, Australian spelling) exactly as they are — they are still correct.

- [ ] **Step 6: Delete step 6 from the command and renumber**

In `commands/expand-outline.md`, delete the whole `6. **Post-expansion review (no automated leak-guard).** …` block (through `once this review passes.`), then renumber the following `7. **Advance the marker:**` to `6. **Advance the marker:**`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_solution_visibility.py -v`
Expected: 12 passed.

- [ ] **Step 8: Run the full suite**

Run: `python3 -m pytest`
Expected: `342 passed`.

- [ ] **Step 9: Commit**

```bash
git add tests/test_solution_visibility.py agents/outline-expander.md commands/expand-outline.md
git commit -m "refactor(outline-expander): reveal timing is a planning rule, not a leak guard

The withholding discipline existed to keep the drafter blind. The drafter is no
longer blind, so the rationale dies and the manual post-expansion leak review goes
with it. The reveal-timing rule survives, reframed and enforced by inspector-fairplay.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Pin reader simulation and rewrite the docs

**Files:**
- Modify: `CLAUDE.md:69`, `:133`, `:137`, `:183-200`
- Modify: `README.md:253`, `:257`, `:285`, `:288`, `:395`, `:425`
- Modify: `agents/book-scaffolder.md:60-69` (the `## Blind-seam rule` section)
- Modify: `config/self-audit/self-audit-checklist.md:13`
- Modify: `tests/test_solution_visibility.py` (append)
- **Do not touch** `agents/beta-reader.md` or `tests/test_beta_scaffold.py`.
- **Do not touch** `penny-design-v3.md`. It is the historical design record; the spec's
  header already declares it superseded on this point. Editing it would rewrite history.

**Scope note (added during execution, after Task 2's review):** the original plan listed
only `CLAUDE.md` and three `README.md` lines. A reviewer found four more live claims of
drafter blindness. `agents/book-scaffolder.md` is the serious one — it carries a whole
`## Blind-seam rule` section calling the seam "sacred", which is now false. Its *substance*
survives, reframed: the solution must live in exactly one file. That is now justified by
(a) `canon-core.md` is loaded every chapter and must stay tiny, and (b) the four inspectors
other than fairplay remain isolated and have no need of the answer. Not by drafter blindness.

**Interfaces:**
- Consumes: `tests/test_solution_visibility.py` from Task 1.
- Produces: nothing.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_solution_visibility.py`:

```python
DOCS = [Path("CLAUDE.md"), Path("README.md")]


def test_beta_reader_still_simulates_a_reader():
    """Reader simulation is NOT a guardrail and must survive the removal."""
    text = (AGENTS / "beta-reader.md").read_text(encoding="utf-8")
    assert "no solution" in text
    assert "{ text, persona_file }" in text


def test_docs_no_longer_teach_solution_blindness():
    """CLAUDE.md may still SAY 'there is no solution-blindness' — that is the point.

    So assert on the phrases that TEACH the rule, not on the word itself.
    """
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        assert "Blind sub-agents" not in text, doc
        assert "solution-blind inputs" not in text, doc
        assert "Drafter blindness" not in text, doc
        assert "blind to the full solution" not in text, doc


def test_docs_teach_the_three_properties():
    text = Path("CLAUDE.md").read_text(encoding="utf-8")
    assert "reader simulation" in text.lower()
    assert "Isolation" in text


def test_book_scaffolder_seam_is_about_locality_not_blindness():
    flat = _flat(AGENTS / "book-scaffolder.md")
    assert "blind-seam rule" not in flat
    assert "blind-drafter seam is sacred" not in flat
    assert "the drafter must never see a solution" not in flat
    # the substance survives:
    assert "mystery-solution.md" in flat
    assert "canon-core" in flat


def test_self_audit_says_isolated_not_blind():
    flat = _flat(Path("config/self-audit/self-audit-checklist.md"))
    assert "blind as always" not in flat
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_solution_visibility.py -k docs -v`
Expected: 2 FAILED. `test_beta_reader_still_simulates_a_reader` should **already pass** — that is the point; it proves you have not damaged the survivor.

- [ ] **Step 3: Replace the `### Blind sub-agents` section in `CLAUDE.md`**

Replace the whole section (lines 183-200, from `### Blind sub-agents` through the `outline-reviewer` bullet) with:

```markdown
### Independence, isolation, reader simulation

One word — *blind* — used to name three unrelated things. It named them badly. There are
three properties, each with its own justification (spec:
`docs/superpowers/specs/2026-07-10-remove-solution-blindness-design.md`):

- **Independence = model difference, not ignorance.** The reviewing model must not be the
  drafting model. Enforced by `preflight.py assemble` against `drafted_by`. `final-reader`
  sees the whole solution and is the most independent agent in the system.
- **Isolation = narrow inputs, no cross-talk.** Each inspector gets one chapter, one
  rubric, one ledger slice, and never another inspector's verdict. Isolation is about
  *whose reasoning* an inspector can see, never about *what is true* — which is why
  `inspector-fairplay` holds the solution and is still isolated.
- **Reader simulation = the beta reader stays unknowing.** `{ text, persona_file }` only.
  Not a guardrail: a reader who knows the culprit cannot report that she guessed her in
  chapter four. Personas are distinct lenses and are **never averaged**; models are the
  within-persona consensus axis (≥K-of-M via `beta_consensus_k`).

**There is no solution-blindness.** The drafter, outline-expander, outline-reviewer,
developmental-editor, and inspector-fairplay all read `mystery-solution.md`. The one thing
drafter blindness bought — no reveal before `reveal_chapter` — is a blocking predicate on
`inspector-fairplay`, with the rubric clause in the genre pack. It is deliberately **not**
a script: it is an LLM judgment, and a name-grep would fire on every innocent sentence the
culprit appears in.

A **mystery lock** is still "sealed" — meaning *frozen against edits*, never *hidden from
agents*.
```

- [ ] **Step 4: Fix the three other `CLAUDE.md` lines**

- Line 69: `the 5 blind inspectors` → `the 5 isolated inspectors`
- Line 133 (in the `/expand-outline` paragraph): delete the sentence beginning `It is the **context-rich exception**…` through `Drafter blindness holds until the in-story detective-click (~ch19).` Replace with: `It reads the solution to schedule clue beats, and must not schedule a reveal beat before \`reveal_chapter\`.`
- Line 137 (in the `/review-outline` paragraph): `identical solution-blind inputs` → `identical inputs`

- [ ] **Step 5: Fix `README.md`**

- Line 253: delete `— there is no automated leak-guard. Drafter blindness holds until the` and the clause continuing it; replace the sentence with: `It reads the solution to schedule clue beats; the reveal-timing rule is enforced on the page by \`inspector-fairplay\`.`
- Line 257: `identical solution-blind inputs` → `identical inputs`
- Line 285: `The drafter is blind to the full solution; it gets only this` → `The drafter reads the full solution; it also gets this`
- Line 288: `Five **blind** inspectors` → `Five **isolated** inspectors`
- Line 395: `drafter, five blind inspectors` → `drafter, five isolated inspectors`
- Line 425: replace the `- **Sub-agents are dispatched blind.**` bullet with:
  `- **Sub-agents are isolated, not ignorant.** Inspectors get one rubric + a ledger slice and never another agent's output; beta readers get only \`{text, persona}\` because a reader who knows the culprit stops reacting like a reader. Everyone else reads the solution.`

Read each line in context before editing — the surrounding sentence must still parse.

- [ ] **Step 6: Reframe the book-scaffolder's blind-seam rule**

In `agents/book-scaffolder.md`, replace the bullet ending `The blind-drafter seam is sacred.` with:

```markdown
- You never put a `## Solution` into a continuity artifact (threads, entities,
  canon-core, arc-ledger). The solution lives in exactly one file.
```

Then replace the whole `## Blind-seam rule` section heading and body with:

```markdown
## Solution-locality rule

The solution lives in exactly one file: `output/book-NN/mystery-solution.md`. Threads
files, character/location files, arc-ledger rows, and canon-core entries must contain
**only** what a chapter needs — no culprit identity, no revelation text, no spoiler from
any `## Solution` block.

This is no longer about hiding the answer from the drafter (the drafter reads it). It is
about locality: `canon-core.md` is loaded on **every** chapter and must stay tiny, and the
four inspectors other than `inspector-fairplay` remain isolated and have no use for the
answer. One home, loaded deliberately.
```

- [ ] **Step 7: Fix the self-audit checklist**

In `config/self-audit/self-audit-checklist.md:13`, replace `blind as always` with
`isolated as always`. Leave lines 92 and 100 (`removing them blind`, `the blind inspector`)
alone — read them; if they refer to inspector isolation they are still correct.

- [ ] **Step 8: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_solution_visibility.py -v`
Expected: 17 passed.

- [ ] **Step 9: Run the full suite**

Run: `python3 -m pytest`
Expected: `347 passed`. **`tests/test_beta_scaffold.py` must be among the passes and must be unmodified** — verify with `git diff --stat tests/test_beta_scaffold.py` (expect empty output).

- [ ] **Step 10: Commit**

```bash
git add tests/test_solution_visibility.py CLAUDE.md README.md \
  agents/book-scaffolder.md config/self-audit/self-audit-checklist.md
git commit -m "docs: replace 'blind' with independence / isolation / reader simulation

Solution-blindness is gone. The beta reader stays unknowing — not as a guardrail,
but because a reader who knows the culprit cannot report guessing her. The
book-scaffolder's blind-seam rule becomes a solution-locality rule: canon-core is
loaded every chapter and must stay tiny.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] `python3 -m pytest` → `347 passed`
- [ ] `git diff --stat 9ed6239 -- scripts/` → **empty**. (`9ed6239` is the plan commit, i.e. the
      base this work starts from. Do **not** use `main~6` — a single fix commit shifts it.)
      The spec forbids script changes; this proves it.
- [ ] `git diff --stat -- tests/test_beta_scaffold.py agents/beta-reader.md` → **empty**.
- [ ] `grep -rn "Blind sub-agents\|solution-blind inputs\|Drafter blindness\|MUST stay blind\|ONLY protection\|no automated leak-guard\|Blind-seam\|blind-drafter seam\|dispatched blind\|blind as always" CLAUDE.md README.md agents/ commands/ config/` → no hits.
      (The last four were missed by the original spec's verification list and found by
      Task 2's reviewer. `penny-design-v3.md` is deliberately excluded — superseded, not edited.)
- [ ] `grep -rln "blind" agents/` → `beta-reader.md` (reader simulation — correct),
      `_TEMPLATE.md`, plus any file whose new prose *denies* blindness
      (e.g. `inspector-fairplay.md`'s "Isolation (not blindness)"). Read each hit; the
      only acceptable uses are reader simulation and explicit denial.
- [ ] Push: `git push origin main`
