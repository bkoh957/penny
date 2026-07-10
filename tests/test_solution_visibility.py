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
