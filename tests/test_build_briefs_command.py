from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CMD = REPO / "commands" / "build-briefs.md"
AGENT = REPO / "agents" / "brief-weigher.md"


def test_command_exists_and_runs_after_the_lock():
    text = CMD.read_text(encoding="utf-8")
    assert "lock" in text.lower()
    assert "brief_render.py" in text


def test_command_shells_out_through_the_plugin_root():
    # runbooks must resolve scripts regardless of which series folder is cwd
    assert "${CLAUDE_PLUGIN_ROOT}/scripts/brief_render.py" in CMD.read_text(encoding="utf-8")


def test_weigher_proposes_and_never_decides():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "propose" in text
    assert "never writes" in text or "does not write" in text
