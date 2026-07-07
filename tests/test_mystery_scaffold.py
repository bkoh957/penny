from pathlib import Path

from scripts.penny_meta import parse_frontmatter

CMD = Path("commands/plan-mystery.md")
AGENT = Path("agents/mystery-planner.md")


def test_plan_mystery_command_exists():
    assert CMD.is_file()


def test_plan_mystery_invokes_lock_preflight_and_seals_solution():
    text = CMD.read_text(encoding="utf-8")
    assert "preflight.py lock-mystery" in text, "command must defer the lock to preflight"
    assert "mystery-solution.md" in text, "command must write the sealed solution"
    assert "mystery-planner" in text, "command must dispatch the planner agent"


def test_mystery_planner_agent_has_valid_frontmatter():
    assert AGENT.is_file()
    meta = parse_frontmatter(AGENT.read_text(encoding="utf-8"))
    assert meta.get("name") == "mystery-planner"
    assert meta.get("description")


def test_mystery_planner_never_receives_solution_seat():
    # The planner proposes; it must not be handed the sealed answer key.
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "sealed" in text or "never" in text, "agent must state the sealing discipline"
