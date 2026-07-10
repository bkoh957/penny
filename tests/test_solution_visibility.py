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


def test_review_chapter_passes_solution_and_reveal_chapter_to_fairplay():
    flat = _flat(COMMANDS / "review-chapter.md")
    assert "additionally receives" in flat
    assert "mystery-solution.md" in flat
    assert "premature-reveal check as not applicable" in flat


def test_drafter_receives_the_solution():
    text = (AGENTS / "drafter.md").read_text(encoding="utf-8")
    assert "mystery-solution.md" in text
    assert "reveal_chapter" in text


def test_drafter_no_longer_claims_blindness():
    flat = _flat(AGENTS / "drafter.md")
    assert "receives only this chapter's clue-planting obligations" not in flat
    assert "never\nthe full sealed" not in flat


def test_outline_reviewer_is_not_told_it_is_solution_blind():
    flat = _flat(AGENTS / "outline-reviewer.md")
    assert "denied the whodunit solution" not in flat
    assert "solution-blind" not in flat


def test_review_outline_no_longer_withholds_the_solution():
    flat = _flat(COMMANDS / "review-outline.md")
    assert "do not pass" not in flat


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


def test_readme_dev_editor_not_denied_the_solution():
    """The developmental-editor clause must say it GETS the solution, not that
    it's withheld — this was the earlier (wrong) phrasing."""
    flat = _flat(Path("README.md"))
    assert "but **not** the solution" not in flat
    assert "the chapter brief, and the solution" in flat


def test_book_scaffolder_drops_drafter_visible_framing():
    """'drafter-visible' named a blindness distinction the locality rule replaced."""
    flat = _flat(AGENTS / "book-scaffolder.md")
    assert "drafter-visible" not in flat


ALLOWED_TO_KEEP_BLIND = {
    "beta-reader.md",       # reader simulation — a real reader IS unknowing
    "final-reader.md",      # correct contrast: "unlike the blind beta readers"
    "outline-expander.md",  # deliberate denial: "not because anyone downstream is blind"
    "_TEMPLATE.md",         # scaffold placeholder text, not a live role label
}


def test_no_agent_still_calls_itself_a_blind_inspector_or_copy_editor():
    """Isolation replaced blindness as the role label for Tier-1 inspectors and the
    copy-editor. Only the allowlisted files above may keep the word 'blind'."""
    for path in sorted(AGENTS.glob("*.md")):
        if path.name in ALLOWED_TO_KEEP_BLIND:
            continue
        flat = _flat(path)
        assert "blind inspector" not in flat, path
        assert "blind copy-editor" not in flat, path


RUBRIC_PATHS = sorted(Path("config/review-rubrics").glob("*.md")) + sorted(
    Path(".").glob("genres/*/review-rubrics/*.md")
)


def test_no_rubric_anywhere_still_teaches_solution_blindness():
    """The agents stopped being solution-blind, but their rubrics — a separate input
    an agent reads alongside its agent file — were never swept. An agent dispatched
    cold reads both; if they disagree, the rubric wins the agent's actual behaviour.
    This globs BOTH config/review-rubrics/ and genres/*/review-rubrics/, unlike the
    agent-only glob above which structurally cannot see rubric files at all."""
    banned = [
        "solution-blind",
        "denied the whodunit solution",
        "denied** the whodunit",
        "not blind",
    ]
    for path in RUBRIC_PATHS:
        flat = _flat(path)
        for phrase in banned:
            assert phrase not in flat, (path, phrase)


def test_developmental_craft_rubric_gets_the_solution_and_defers_reveal_timing():
    flat = _flat(Path("config/review-rubrics/developmental-craft.md"))
    assert "mystery-solution.md" in flat
    assert "inspector-fairplay" in flat


def test_no_rubric_still_calls_an_inspector_blind():
    """Extends the agent-only 'blind inspector' check to the rubric files those same
    inspectors read — 'isolated' is the surviving term, not 'blind'."""
    for path in RUBRIC_PATHS:
        flat = _flat(path)
        assert "blind inspector" not in flat, path
