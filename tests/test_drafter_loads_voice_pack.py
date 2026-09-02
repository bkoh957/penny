"""Contract test: the voice pack reaches the drafter on the main draft path.

The LM Studio path (`draft-chapter-lmstudio.md`) has always loaded a voice
digest at the script level. The main path relies on the `drafter` agent reading
`config/voice-pack/voice-pack.md` itself — so the agent must name it as a
first-class input AND tell the drafter to read it *before* writing, not bury it
mid-list where a model treats it as optional. A draft with no voice calibration
is the "guessing at literary" failure `inspector-ai-prose` catches after the
fact.
"""
from pathlib import Path

AGENTS = Path("agents")
COMMANDS = Path("commands")


def _flat(p: Path) -> str:
    return " ".join(p.read_text(encoding="utf-8").split()).lower()


def test_drafter_names_the_voice_pack_as_its_own_input():
    text = (AGENTS / "drafter.md").read_text(encoding="utf-8")
    assert "config/voice-pack/voice-pack.md" in text


def test_drafter_instruction_one_reads_the_voice_pack_first():
    flat = _flat(AGENTS / "drafter.md")
    # Instruction 1 must direct the drafter to the packs before the map/packet.
    assert "read the voice pack" in flat
    assert flat.index("read the voice pack") < flat.index("read the map, the packet")


def test_main_draft_command_notes_the_packs_are_a_direct_agent_read():
    flat = _flat(COMMANDS / "draft-chapter.md")
    assert "config/voice-pack/voice-pack.md" in flat
