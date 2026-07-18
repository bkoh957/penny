from pathlib import Path

from scripts.map_check import check_map
from scripts.penny_length import parse_profile


def _packet_text():
    outline = Path("tests/fixtures/outlines/packet-format.md").read_text(encoding="utf-8")
    from scripts.penny_wiring import chapter_block
    return ("# Packet — Chapter 05\n\n## Chapter 05 — Opening Day [type: event]\n"
            + chapter_block(outline, 5)
            + "\n\n## Ledger Clues\n- [mary-domestic-order] plant_chapter 5: Mary restores order.\n")


def _map_text(**edits):
    text = Path("tests/fixtures/maps/ch-05.md").read_text(encoding="utf-8")
    for old, new in edits.items():
        assert old in text
        text = text.replace(old, new)
    return text


def _profile():
    return parse_profile("```yaml\nband_default: [2000, 2500]\n"
                         "band_event: [2800, 3600]\nmin_scene_words: 250\n```")


def test_clean_canonical_pair_passes():
    out = check_map(_packet_text(), _map_text(), _profile())
    assert out["blocking"] == []


def test_dropped_beat_named():
    out = check_map(_packet_text(), _map_text(**{"Beats covered: 9, 10": "Beats covered: 9"}), _profile())
    assert any(b.startswith("dropped-beat") and "10" in b for b in out["blocking"])


def test_duplicate_beat_named():
    out = check_map(_packet_text(), _map_text(**{"Beats covered: 7": "Beats covered: 1, 7"}), _profile())
    assert any(b.startswith("duplicate-beat") for b in out["blocking"])


def test_unscheduled_clue_named():
    out = check_map(_packet_text(), _map_text(**{"[whodunit: mary-domestic-order]": ""}), _profile())
    assert any(b.startswith("unscheduled-clue") and "mary-domestic-order" in b
               for b in out["blocking"])


def test_unscheduled_clue_is_not_satisfied_by_a_superstring_id():
    # A clue id that is a hyphenated PREFIX of another id ("clue-jam" inside
    # "clue-jam-2") must not be considered planted by that other id's mention
    # — substring/loose word-boundary matching both get this wrong.
    packet = (
        "# Packet — Chapter 01\n\n## Chapter 01 — Test\n\n"
        "### Required Beats\n- A beat.\n\n"
        "## Ledger Clues\n- [clue-jam] plant_chapter 1: the jam clue.\n"
    )
    map_text = (
        "---\nbuilt_from_packet: deadbeef\n---\n\n"
        "## Scene 1 — Only\n"
        "Beats covered: 1\n\n"
        "Clue:\n"
        "Something else entirely.\n"
        "[whodunit: clue-jam-2]\n"
    )
    out = check_map(packet, map_text, None)
    assert any(b.startswith("unscheduled-clue") and "[clue-jam]" in b for b in out["blocking"])


def test_no_profile_is_note_not_crash():
    out = check_map(_packet_text(), _map_text(), None)
    assert any("length profile" in n for n in out["notes"])
    # coverage checks still ran without a profile
    assert not any(b.startswith("dropped-beat") for b in out["blocking"])
