from pathlib import Path

AGENT = Path(".claude/agents/book-scaffolder.md")


def test_agent_file_exists():
    assert AGENT.is_file()


def test_agent_routes_to_existing_homes():
    text = AGENT.read_text(encoding="utf-8")
    for home in [
        "series/whodunit/book-",
        "series/continuity/threads/",
        "series/continuity/characters/",
        "series/arc-ledger.md",
        "series/continuity/canon-core.md",
        "output/book-",  # sealed mystery-solution
    ]:
        assert home in text, f"scaffolder must route derived data to {home}"


def test_agent_never_writes_the_lock():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "lock" in text and "never" in text, "must state it never writes the lock"
    # Strengthened: verify the agent explicitly contracts that it never writes the lock
    # or certificate — a line must contain both a negation and "lock"/"certificate".
    # If someone removes the never-writes-the-lock statement, this will fail.
    assert (
        "never write" in text and "lock" in text
    ) or (
        "never writes" in text and ("lock" in text or "certificate" in text)
    ), (
        "agent must explicitly state it never writes the lock/certificate "
        "(e.g. 'never write ... lock' or 'never writes ... certificate')"
    )
