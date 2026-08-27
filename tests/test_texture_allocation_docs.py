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


MAP_MAKER = Path("agents/map-maker.md")
DRAFTER = Path("agents/drafter.md")
CUTTER = Path("agents/chapter-cutter.md")
PLOT_BOOK = Path("commands/plot-book.md")
MAP_CHAPTER = Path("commands/map-chapter.md")


def test_map_maker_distributes_texture_and_names_the_gate_that_does_not_exist():
    # Same house style as the texture-allocator: a reader must be able to tell
    # that no such finding exists under any name, not merely that this file
    # declined to mention one.
    t = MAP_MAKER.read_text(encoding="utf-8")
    assert "### Texture" in t
    assert "`Texture:`" in t
    assert "resource, not an obligation" in t
    assert "unscheduled-texture" in t
    assert "never will" in t


def test_map_maker_stays_isolated_to_the_packet():
    # The allocation is in the packet; the reservoir must NOT be added here.
    t = MAP_MAKER.read_text(encoding="utf-8")
    assert "reservoir.md" not in t


def test_drafter_names_the_reservoir_and_the_texture_section():
    t = DRAFTER.read_text(encoding="utf-8")
    assert "config/setting-pack/reservoir.md" in t
    assert "### Texture" in t


def test_chapter_cutter_does_not_author_texture_lines():
    t = CUTTER.read_text(encoding="utf-8")
    assert "/allocate-texture" in t


def test_plot_book_points_at_the_allocation_between_the_plan_and_the_cut():
    t = PLOT_BOOK.read_text(encoding="utf-8")
    assert "/allocate-texture" in t
    assert t.index("/allocate-texture") < t.index("Stage readback")


def test_map_chapter_tells_the_map_maker_about_texture():
    assert "Texture:" in MAP_CHAPTER.read_text(encoding="utf-8")


CLAUDE_MD = Path("CLAUDE.md")
README = Path("README.md")


def test_claude_md_documents_the_texture_layer():
    t = CLAUDE_MD.read_text(encoding="utf-8")
    for phrase in ("config/setting-pack/reservoir.md", "/allocate-texture",
                   "texture_apply.py", "### Texture",
                   "resource, not an obligation"):
        assert phrase in t, phrase


def test_claude_md_still_claims_twenty_three_story_cut_findings():
    # The texture layer adds no finding. If this fails, one was added.
    assert "twenty-three findings" in CLAUDE_MD.read_text(encoding="utf-8")


def test_readme_documents_the_reservoir_and_the_allocation():
    t = README.read_text(encoding="utf-8")
    for phrase in ("config/setting-pack/reservoir.md", "/allocate-texture"):
        assert phrase in t, phrase


def test_claude_md_test_count_matches_the_suite():
    import re
    import subprocess
    t = CLAUDE_MD.read_text(encoding="utf-8")
    claimed = int(re.search(r"full suite \((\d+) tests\)", t).group(1))
    # `-o addopts=""` neutralizes pytest.ini's own `addopts = -q`: stacking that
    # with this command's `-q` reaches pytest's double-quiet collect-only mode,
    # which prints per-file counts instead of a "N tests collected" total —
    # this command would then never find a total to compare against, no matter
    # what CLAUDE.md claims.
    out = subprocess.run(["python3", "-m", "pytest", "--collect-only", "-q",
                          "-o", "addopts="],
                         capture_output=True, text=True).stdout
    actual = int(re.search(r"(\d+) tests? collected", out).group(1))
    assert claimed == actual, f"CLAUDE.md says {claimed}, suite has {actual}"
