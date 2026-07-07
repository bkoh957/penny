from pathlib import Path

AGENT = Path("agents/book-scaffolder.md")


def test_agent_file_exists():
    assert AGENT.is_file()


def test_agent_routes_to_existing_homes():
    text = AGENT.read_text(encoding="utf-8")
    for home in [
        "series/whodunit/book-",
        "series/continuity/threads/",
        "series/continuity/characters/",
        "series/continuity/locations/",
        "series/arc-ledger.md",
        "series/continuity/canon-core.md",
        "output/book-",  # sealed mystery-solution
    ]:
        assert home in text, f"scaffolder must route derived data to {home}"


def test_agent_never_writes_the_lock():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "lock" in text and "never" in text, "must state it never writes the lock"
    # Strengthened: verify the contract body (not just the frontmatter description)
    # explicitly names the lock path — ".penny/locks" only appears in the
    # "## What you NEVER do" body, not in the frontmatter.  Deleting that section
    # while leaving the frontmatter would no longer satisfy this assertion.
    assert "never write" in text and "lock" in text, (
        "agent must explicitly state it never writes the lock"
    )
    assert ".penny/locks" in text, (
        "the never-writes-the-lock contract must name the lock path (.penny/locks) "
        "in the body — deleting the ## What you NEVER do section fails this test"
    )
