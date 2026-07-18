from pathlib import Path

import pytest

from scripts import packet_assemble
from scripts.penny_meta import parse_frontmatter

FIX = Path(__file__).resolve().parent / "fixtures"
PACKET_OUTLINE = FIX / "outlines" / "packet-format.md"

# The v2 length-profile yaml block from Task 3 (band_default/band_event +
# min_scene_words) — ch 05 of the fixture outline declares [type: event].
V2_PROFILE = (
    "```yaml\n"
    "band_default: [2000, 2500]\n"
    "band_event: [2800, 3600]\n"
    "min_scene_words: 250\n"
    "```\n"
)


@pytest.fixture
def series_tree(tmp_path):
    root = tmp_path
    (root / ".penny/locks").mkdir(parents=True)
    (root / ".penny/locks/book-01.mystery.lock").write_text("locked\n", encoding="utf-8")

    inp = root / "input/book-01"
    inp.mkdir(parents=True)
    outline_text = PACKET_OUTLINE.read_text(encoding="utf-8")
    # Chapter 7 does not exist in the shared fixture. Add a minimal block here
    # (tmp-tree only, never the shared fixture) that carries a Chapter
    # Purpose section but NO Required Beats — the "unmigrated chapter" case.
    outline_text += (
        "\n\n## Chapter 07 — No Beats\n\n"
        "### Chapter Purpose\n"
        "A stub chapter the migration hasn't reached yet.\n"
    )
    (inp / "outline.md").write_text(outline_text, encoding="utf-8")

    wd = root / "series/whodunit"
    wd.mkdir(parents=True)
    (wd / "book-01.yaml").write_text(
        "book: '01'\n"
        "reveal_chapter: 22\n"
        "clue_schedule:\n"
        "  - { id: mary-domestic-order, plant_chapter: 5, pays_off_chapter: 22, "
        "necessary: true, description: \"Mary restores cups, plates and towels "
        "to their places, as if nothing happened.\" }\n",
        encoding="utf-8")

    cont = root / "series/continuity"
    (cont / "characters").mkdir(parents=True)
    (cont / "canon-core.md").write_text(
        "# Canon Core\n\nThe Wheelhouse pottery studio. Maggie's Too-Much.\n",
        encoding="utf-8")
    (cont / "characters/mary.md").write_text(
        "<!-- canon-meta: {id: mary, links: [cal]} -->\n\n"
        "## Mary\n\nMary keeps everything in its place.\n",
        encoding="utf-8")
    (cont / "characters/cal.md").write_text(
        "<!-- canon-meta: {id: cal} -->\n\n"
        "## Cal\n\nCal notices what others miss.\n",
        encoding="utf-8")
    (cont / "characters/saffron.md").write_text(
        "<!-- canon-meta: {id: saffron} -->\n\n"
        "## Saffron\n\nSaffron runs the cafe next door.\n",
        encoding="utf-8")

    cfg = root / "config"
    cfg.mkdir(parents=True)
    (cfg / "length-profile.md").write_text(V2_PROFILE, encoding="utf-8")

    return root


def test_assemble_writes_stamped_packet(series_tree):
    p = packet_assemble.assemble("01", "05", repo_root=series_tree)
    text = p.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    assert len(fm["built_from_outline"]) == 64
    assert len(fm["built_from_whodunit"]) == 64
    assert "## Chapter 05 — Opening Day [type: event]" in text
    assert "### Required Beats" in text
    assert "- **Hook:**" in text                      # wiring footer rides along


def test_assemble_merges_ledger_clues(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "[mary-domestic-order]" in text


def test_assemble_slices_continuity_one_hop(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "canon-core" in text.lower()
    assert "mary" in text.lower()          # named in the block
    assert "cal" in text.lower()           # one hop from mary's links
    assert "saffron" not in text.lower()   # not named, not linked


def test_assemble_refuses_unlocked_book(series_tree):
    (series_tree / ".penny/locks/book-01.mystery.lock").unlink()
    with pytest.raises(SystemExit):
        packet_assemble.assemble("01", "05", repo_root=series_tree)


def test_assemble_refuses_chapter_without_required_beats(series_tree):
    with pytest.raises(SystemExit):
        packet_assemble.assemble("01", "07", repo_root=series_tree)


def test_missing_guardrails_file_is_named_note(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "no config/series-guardrails.md" in text


def test_stale_packets_flags_outline_edit(series_tree):
    packet_assemble.assemble("01", "05", repo_root=series_tree)
    assert packet_assemble.stale_packets("01", series_tree) == set()
    outline = series_tree / "input/book-01/outline.md"
    outline.write_text(outline.read_text(encoding="utf-8") + "\nedit\n",
                       encoding="utf-8")
    assert "05" in packet_assemble.stale_packets("01", series_tree)


def test_absent_ledger_is_stamped_none_and_late_ledger_goes_stale(series_tree):
    (series_tree / "series/whodunit/book-01.yaml").unlink()
    p = packet_assemble.assemble("01", "05", repo_root=series_tree)
    assert parse_frontmatter(p.read_text(encoding="utf-8"))["built_from_whodunit"] == "none"
    # The other half of the contract: a ledger that shows up LATER (after the
    # packet was built with none) must make the packet stale, exactly like an
    # outline edit does — the whodunit ledger is a real upstream of the packet.
    (series_tree / "series/whodunit").mkdir(parents=True, exist_ok=True)
    (series_tree / "series/whodunit/book-01.yaml").write_text(
        "book: '01'\nreveal_chapter: 22\n", encoding="utf-8")
    assert "05" in packet_assemble.stale_packets("01", series_tree)


def test_same_stem_in_two_continuity_subdirs_are_both_matched(series_tree):
    # characters/mary.md already exists in the fixture. Add threads/mary.md —
    # a same-named entry in a DIFFERENT subdir — and confirm both survive
    # into the packet rather than one silently clobbering the other in the
    # (formerly) bare-stem-keyed entries dict.
    threads = series_tree / "series/continuity/threads"
    threads.mkdir(parents=True, exist_ok=True)
    (threads / "mary.md").write_text(
        "<!-- canon-meta: {id: mary-thread} -->\n\n"
        "## Mary's Thread\n\nMary's domestic-order habit runs the whole book.\n",
        encoding="utf-8")
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(encoding="utf-8")
    assert "### characters/mary.md" in text
    assert "### threads/mary.md" in text
    assert "Mary's domestic-order habit runs the whole book." in text
    assert "Mary keeps everything in its place." in text
