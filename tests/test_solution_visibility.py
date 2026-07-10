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
    text = (AGENTS / "drafter.md").read_text(encoding="utf-8")
    assert "receives ONLY this chapter's clue-planting obligations" not in text
    assert "never\nthe full sealed" not in text


def test_outline_reviewer_is_not_told_it_is_solution_blind():
    flat = _flat(AGENTS / "outline-reviewer.md")
    assert "denied the whodunit solution" not in flat
    assert "solution-blind" not in flat


def test_review_outline_no_longer_withholds_the_solution():
    text = (COMMANDS / "review-outline.md").read_text(encoding="utf-8")
    assert "do NOT pass" not in text


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
