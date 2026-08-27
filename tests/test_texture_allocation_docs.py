from pathlib import Path

AGENT = Path("agents/texture-allocator.md")
COMMAND = Path("commands/allocate-texture.md")


def test_the_agent_exists_and_declares_its_name():
    assert AGENT.is_file()
    assert "name: texture-allocator" in AGENT.read_text(encoding="utf-8")


def test_the_agent_holds_the_two_load_bearing_rules():
    t = AGENT.read_text(encoding="utf-8")
    low = t.lower()
    for phrase in ("no image twice", "never invent"):
        assert phrase in low, phrase
    for phrase in ("config/setting-pack/reservoir.md", "cut-plan.md",
                   "input/book-NN/plot/texture.md",
                   "You propose. You never write.", "resource, not an obligation",
                   "Register under pressure"):
        assert phrase in t, phrase


def test_the_agent_names_the_texture_gate_that_does_not_exist():
    # The house style for a load-bearing absence is to NAME it: a reader must be
    # able to tell that no such finding exists under any name, not merely that
    # this file declined to mention one.
    t = AGENT.read_text(encoding="utf-8")
    assert "unscheduled-texture" in t
    assert "never will" in t


def test_the_command_runs_the_splice_the_cut_and_names_the_lock_cost():
    t = COMMAND.read_text(encoding="utf-8")
    for phrase in ("texture_apply.py", "story_cut.py", "texture-allocator",
                   "input/book-$book/plot/texture.md",
                   "${CLAUDE_PLUGIN_ROOT}/scripts/texture_apply.py",
                   "lock-mystery", "map-chapter"):
        assert phrase in t, phrase


def test_the_command_uses_the_plugin_root_for_every_script_call():
    t = COMMAND.read_text(encoding="utf-8")
    for line in t.splitlines():
        if "scripts/" in line and "python3" in line:
            assert "${CLAUDE_PLUGIN_ROOT}" in line, line
