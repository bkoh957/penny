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
        "# Canon Core\n\nThe Wheelhouse pottery studio. Maggie's Too-Much.\n\n"
        "## Practical canon decisions (book 1)\n\nDon't resolve the mystery early.\n",
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


# --- Follow-up: indented ATX + setext headings still collide
# (docs/superpowers/specs/2026-08-27-packet-extract-heading-collision-fix.md
# review follow-up — three surviving shapes) ---

def test_demote_headings_indented_atx_1to3_spaces_is_demoted():
    # CommonMark: 1-3 leading spaces before `#` IS a heading. The indent
    # itself must survive in the output — the line is not left-stripped.
    src = "   ## Established facts\n\nSome fact.\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("   ###### Established facts\n")


def test_demote_headings_four_space_indent_is_code_block_left_alone():
    # 4+ leading spaces is an indented code block in CommonMark, not a
    # heading — must NOT be touched.
    src = "    ## Not a heading, a code block\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_setext_h1_converted_to_demoted_atx():
    src = "Canon Core\n===\n\nThe Wheelhouse pottery studio.\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("##### Canon Core\n")
    assert "===" not in out
    assert "The Wheelhouse pottery studio." in out


def test_demote_headings_setext_h2_converted_to_demoted_atx():
    src = "Practical canon decisions\n---\n\nMore text.\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("###### Practical canon decisions\n")
    assert "More text." in out


def test_demote_headings_setext_and_atx_land_at_same_offset():
    # `# Foo` and `Foo\n===\n` are both "level 1" and must land at the same
    # depth once demoted — same for level-2 `## Foo` vs `Foo\n---\n`.
    atx_h1 = packet_assemble._demote_headings("# Foo\n")
    setext_h1 = packet_assemble._demote_headings("Foo\n===\n")
    assert atx_h1.split("\n", 1)[0] == setext_h1.split("\n", 1)[0]

    atx_h2 = packet_assemble._demote_headings("## Bar\n")
    setext_h2 = packet_assemble._demote_headings("Bar\n---\n")
    assert atx_h2.split("\n", 1)[0] == setext_h2.split("\n", 1)[0]


def test_demote_headings_thematic_break_after_blank_line_untouched():
    # A `---` preceded by a blank line is a thematic break, not a setext
    # underline for anything — there is no text line for it to attach to.
    src = "Some paragraph.\n\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_thematic_break_at_start_of_text_untouched():
    src = "---\n\nText after a leading thematic break.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_frontmatter_block_untouched():
    # A `---`-delimited block at the very start of the file reads as YAML
    # frontmatter, not a setext heading — must be passed through whole.
    src = "---\ntitle: Canon Core\nkind: reference\n---\n\nBody text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_setext_underline_after_list_item_untouched():
    # A setext underline cannot follow a list item.
    src = "- A list item\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_setext_underline_after_blockquote_untouched():
    src = "> A quoted line\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_setext_underline_after_atx_heading_untouched():
    src = "## An ATX heading\n---\n\nMore text.\n"
    out = packet_assemble._demote_headings(src)
    # The ATX heading itself is demoted as always...
    assert out.startswith("###### An ATX heading\n")
    # ...but the `---` right after it is a thematic break, not converted
    # into a second heading for the ATX line above it.
    assert "\n---\n" in out


_SETEXT_UNDERLINE_ONLY_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")


def _first_real_markdown_boundary(text: str) -> int:
    """Index of the first level-1/2 heading a FULL markdown parser would
    see — ATX (`#`/`##`) OR setext (a text line followed by a `===`/`---`
    underline). `_continuity_extracts_section` above only understands ATX,
    which is exactly the narrower assumption that would let a setext
    collision slip past that helper undetected; this one is deliberately
    stricter so the setext regression test actually exercises the defect."""
    lines = text.split("\n")
    pos = 0
    for i, line in enumerate(lines):
        if re.match(r"^#{1,2}(?!#)[ \t]", line):
            return pos
        if i + 1 < len(lines) and line.strip():
            if _SETEXT_UNDERLINE_ONLY_RE.match(lines[i + 1]):
                return pos
        pos += len(line) + 1
    return len(text)


def test_continuity_extracts_section_survives_setext_headings(series_tree):
    # Same regression as the ATX case, but canon-core.md uses setext
    # headings — the shape a hand-authored file is most likely to carry
    # (a paragraph, then a `---` divider, read by CommonMark as an H2).
    cont = series_tree / "series/continuity"
    (cont / "canon-core.md").write_text(
        "Canon Core\n===\n\n"
        "The Wheelhouse pottery studio. Maggie's Too-Much.\n\n"
        "Practical canon decisions (book 1)\n---\n\n"
        "Don't resolve the mystery early.\n",
        encoding="utf-8")
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")

    heading_line = next(l for l in text.splitlines()
                         if l.startswith("## Continuity Extracts"))
    start = text.index(heading_line) + len(heading_line)
    rest = text[start:]
    boundary = _first_real_markdown_boundary(rest)
    section = rest[:boundary]

    # A real markdown parser must not find a level-1/2 heading (ATX or
    # setext) anywhere before the true next sibling `##` — i.e. the whole
    # rest of the continuity extracts must be inside `section`.
    assert "### canon-core.md" in section
    assert "### characters/mary.md" in section
    assert "### characters/cal.md" in section
    assert "The Wheelhouse pottery studio." in section
    assert "Don't resolve the mystery early." in section
    assert "Mary keeps everything in its place." in section
    assert "Cal notices what others miss." in section


# --- Manifest grammar and coverage ---

def test_continuity_slice_manifest_zero_entries(tmp_path):
    out, manifest = packet_assemble._continuity_slice(tmp_path, "Nothing named here.")
    assert manifest == "(0 entries)"


def test_continuity_slice_manifest_singular_one_entry(tmp_path):
    cont = tmp_path / "series/continuity"
    cont.mkdir(parents=True)
    (cont / "canon-core.md").write_text("Just canon core, nothing else matches.\n",
                                         encoding="utf-8")
    out, manifest = packet_assemble._continuity_slice(tmp_path, "Nothing named here.")
    assert manifest == "(1 entry: canon-core.md)"


def test_continuity_slice_manifest_multi_subdir_breakdown_order(tmp_path):
    cont = tmp_path / "series/continuity"
    for sub, stem, text in [
        ("characters", "mary", "Mary the character."),
        ("background", "wheelhouse", "The Wheelhouse background."),
        ("locations", "cafe", "The cafe location."),
        ("threads", "order", "The domestic order thread."),
    ]:
        d = cont / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{stem}.md").write_text(
            f"<!-- canon-meta: {{id: {stem}}} -->\n\n{text}\n", encoding="utf-8")
    (cont / "canon-core.md").write_text("Canon core body.\n", encoding="utf-8")

    chapter_text = "Mary and the Wheelhouse and the cafe and the domestic order."
    out, manifest = packet_assemble._continuity_slice(tmp_path, chapter_text)

    assert manifest == (
        "(5 entries: canon-core.md, 1 background/, 1 characters/, "
        "1 locations/, 1 threads/)")
    # The breakdown's subdirectory order must match the order entries are
    # actually emitted in the slice text.
    emit_order = [rel for rel in re.findall(r"^### (\S+)$", out, re.MULTILINE)
                  if rel != "canon-core.md"]
    subdir_order = [p.split("/", 1)[0] for p in emit_order]
    assert subdir_order == sorted(subdir_order)
    breakdown_subdirs = re.findall(r"\d+ (\w+)/", manifest)
    assert breakdown_subdirs == sorted(set(subdir_order))
