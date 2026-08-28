import re
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


def test_background_entry_loads_when_named(tmp_path, monkeypatch):
    """A background entry named in the chapter lands in the packet, and its
    one-hop links pull the relationship entry with it."""
    bg = tmp_path / "series/continuity/background"
    bg.mkdir(parents=True)
    (bg / "maggie.md").write_text(
        "<!-- canon-meta: {id: maggie, kind: character, links: [cal--maggie]} -->\n\n"
        "A potter who does not perform fear.\n", encoding="utf-8")
    (bg / "cal--maggie.md").write_text(
        "<!-- canon-meta: {id: cal--maggie, kind: relationship, links: [cal, maggie]} -->\n\n"
        "Slow, and neither will name it first.\n", encoding="utf-8")
    (bg / "pruitt.md").write_text(
        "<!-- canon-meta: {id: pruitt, kind: character, links: []} -->\n\n"
        "Not in this chapter.\n", encoding="utf-8")

    out, manifest = packet_assemble._continuity_slice(tmp_path, "Maggie opens the studio.")
    assert "A potter who does not perform fear." in out
    assert "Slow, and neither will name it first." in out
    assert "Not in this chapter." not in out
    assert "(2 entries: 2 background/)" == manifest


# --- Task 4: the allocation reaches the packet with no packet_assemble code ---

def test_the_packet_carries_the_chapters_texture_allocation(series_tree):
    # packet_assemble embeds the chapter block VERBATIM, so this needs no code
    # of its own — pin it so a future refactor cannot quietly drop it.
    outline_p = series_tree / "input/book-01/outline.md"
    head, sep, tail = outline_p.read_text(encoding="utf-8").partition("## Chapter 05")
    assert sep, "fixture outline has no chapter 05"
    tail = tail.replace(
        "### Required Beats",
        "### Texture\n- bakery 6am: proving-room warmth\n\n### Required Beats", 1)
    outline_p.write_text(head + sep + tail, encoding="utf-8")

    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    assert "### Texture" in text
    assert "bakery 6am: proving-room warmth" in text


# --- Packet extract heading collision fix
# (docs/superpowers/specs/2026-08-27-packet-extract-heading-collision-fix.md) ---

_SIBLING_HEADING_RE = re.compile(r"\n#{1,2}(?!#)[ \t]")


def _continuity_extracts_section(text: str) -> str:
    """Isolate the packet's `## Continuity Extracts ...` section the way a
    markdown-structure-aware reader would: from its heading line up to (not
    including) the next sibling heading at level 1 or 2. A `###`+ heading
    (an embedded source's own, once demoted) does NOT end the section."""
    heading_line = next(l for l in text.splitlines() if l.startswith("## Continuity Extracts"))
    start = text.index(heading_line) + len(heading_line)
    rest = text[start:]
    m = _SIBLING_HEADING_RE.search(rest)
    return rest[:m.start()] if m else rest


def test_continuity_extracts_section_survives_embedded_headings(series_tree):
    # §4 regression test: the fixture's canon-core.md carries a level-1
    # heading ("# Canon Core") and characters/mary.md carries a level-2
    # heading ("## Mary") — exactly the collision the defect brief describes.
    # On unfixed code, "# Canon Core" structurally closes the section 19
    # "lines" in, before mary.md and cal.md are ever reached.
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    section = _continuity_extracts_section(text)
    assert "### canon-core.md" in section
    assert "### characters/mary.md" in section
    assert "### characters/cal.md" in section
    assert "Mary keeps everything in its place." in section
    assert "Cal notices what others miss." in section


def test_continuity_extracts_manifest_count_matches_emitted_entries(series_tree):
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    heading_line = next(l for l in text.splitlines() if l.startswith("## Continuity Extracts"))
    m = re.search(r"\((\d+) entries", heading_line)
    assert m, f"no manifest count in heading line: {heading_line!r}"
    claimed = int(m.group(1))
    section = _continuity_extracts_section(text)
    actual = len(re.findall(r"(?m)^### ", section))
    assert actual == claimed
    assert claimed > 0


def test_demote_headings_matches_spec_examples():
    src = "# Canon Core\n\nThe Wheelhouse pottery studio.\n\n## Practical canon decisions (book 1)\n\nMore text.\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("##### Canon Core\n")
    assert "\n###### Practical canon decisions (book 1)\n" in out


def test_demote_headings_clamps_at_level_6():
    # A level-5 source heading would map past level 6 (5 + 4 = 9); it must
    # clamp there instead, per the brief's own worked example.
    assert packet_assemble._demote_headings("##### Deep heading\n") == "###### Deep heading\n"
    # An already-level-6 heading has nowhere further to go.
    assert packet_assemble._demote_headings("###### Already deepest\n") == "###### Already deepest\n"


def test_demote_headings_ignores_non_heading_hashes():
    src = "Not a #hashtag heading.\n\nA mid-line # is fine too.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_no_headings_is_unchanged():
    # background/*.md entries carry zero headings in real series data — the
    # reason the defect was ~4%, not total. That path must pass through
    # byte-for-byte.
    src = "A potter who does not perform fear. Plain prose, no markdown structure.\n"
    assert packet_assemble._demote_headings(src) == src
