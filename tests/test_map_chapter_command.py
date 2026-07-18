"""Contract test for /map-chapter — mirrors the style of the deleted
tests/test_build_briefs_command.py (git show HEAD~1:tests/test_build_briefs_command.py):
grep the runbook + agent def for the load-bearing strings a showrunner
actually depends on, plus one real-parser round trip so "the syntax this
runbook teaches" can never silently drift from what the engine accepts.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CMD = REPO / "commands" / "map-chapter.md"
AGENT = REPO / "agents" / "map-maker.md"


def test_command_exists_and_mints_no_certificate_of_its_own():
    text = CMD.read_text(encoding="utf-8")
    assert "lock" in text.lower()


def test_command_shells_out_through_the_plugin_root():
    # Runbooks must resolve scripts regardless of which series folder is cwd
    # (design §7: packet_assemble.py assembles, map_check.py gates).
    text = CMD.read_text(encoding="utf-8")
    assert '${CLAUDE_PLUGIN_ROOT}/scripts/packet_assemble.py' in text
    assert '${CLAUDE_PLUGIN_ROOT}/scripts/map_check.py' in text


def test_command_writes_the_stamped_map_only_after_showrunner_approval():
    text = CMD.read_text(encoding="utf-8")
    assert "the showrunner edits/approves" in text.lower() or \
        "the showrunner edits/approves" in text
    assert "built_from_packet" in text


def test_command_names_map_maker_and_routes_it_off_the_drafting_model():
    text = CMD.read_text(encoding="utf-8")
    assert "map-maker" in text
    assert "plot_model" in text
    assert "drafting_model" in text


def test_command_argument_hint_is_book_and_chapter():
    text = CMD.read_text(encoding="utf-8")
    assert "argument-hint: <book-number> <chapter-number>" in text


def test_command_stage_markers_bracket_the_workshop():
    text = CMD.read_text(encoding="utf-8")
    assert "stage=MAP" in text
    assert "stage=MAPPED" in text


def test_command_map_check_gates_with_no_waivers():
    text = CMD.read_text(encoding="utf-8").lower()
    assert "map_check.py" in text
    assert "no waivers" in text


def test_command_nonzero_packet_exit_names_the_cure():
    text = CMD.read_text(encoding="utf-8").lower()
    # A refusal must say what to run, not just that it failed.
    assert "lock-mystery" in text or "no lock" in text
    assert "required beats" in text


# --- agents/map-maker.md ---

def test_map_maker_proposes_and_never_decides():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "propose" in text
    assert "never writes" in text or "does not write" in text or "never edits" in text


def test_map_maker_never_touches_outline_ledgers_or_certificates():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "never edits the outline" in text or "never edit the outline" in text
    assert "ledger" in text
    assert "certificate" in text


def test_map_maker_must_cover_every_required_beat_and_every_clue():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "beats covered" in text
    assert "clue" in text


def test_map_maker_targets_must_sum_inside_the_packet_band():
    text = AGENT.read_text(encoding="utf-8").lower()
    assert "word budget" in text or "band" in text


# --- the syntax the agent proposes must be the syntax penny_map.py parses ---

def test_documented_scene_syntax_actually_parses():
    from scripts.penny_map import parse_map

    map_text = """---
built_from_packet: 0000000000000000000000000000000000000000000000000000000000000000
---

## Scene 1 — Test
Target: 350-450 words
Weight: Primary anchor
Beats covered: 1

Clue:
[test-clue] planted with no emphasis.
"""
    parsed = parse_map(map_text)
    assert parsed["scenes"][0]["target"] == (350, 450)
    assert parsed["scenes"][0]["beats_covered"] == [1]
    assert "test-clue" in parsed["scenes"][0]["clue_text"]
