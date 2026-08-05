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
