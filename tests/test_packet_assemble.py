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
    m = re.search(r"\((\d+) entr(?:y|ies)", heading_line)
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


# --- Follow-up 2: two more leaf-block shapes the setext text-line guard
# missed — an HTML block (canon-meta comment) and an indented code block,
# both real shapes in this repo's own continuity data
# (docs/superpowers/specs/2026-08-27-packet-extract-heading-collision-fix.md
# review follow-up #2) ---

def test_demote_headings_canon_meta_comment_above_thematic_break_untouched():
    # <!-- canon-meta: ... --> opens every continuity entry the engine
    # ships. Immediately above a `---` it looks exactly like setext-heading
    # text unless HTML-block lines are excluded from the guard.
    src = "<!-- canon-meta: {id: mary} -->\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_fence_closer_above_thematic_break_untouched():
    # A fence-closing ``` line above a `---` must not become a demoted
    # heading — that would break the fence and re-render everything after
    # it as prose.
    src = "```\ncode inside\n```\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_indented_code_line_above_thematic_break_untouched():
    # A 4-space indented code line immediately above a `---` is a code
    # block, not setext-heading text.
    src = "    an indented code line\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_tab_indented_code_line_above_thematic_break_untouched():
    src = "\tan indented code line\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_table_row_above_thematic_break_untouched():
    # A GFM table row above a `---` must not be swallowed into a setext
    # heading either.
    src = "| a | b |\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_canonical_table_row_above_thematic_break_untouched():
    # The canonical GFM shape named in the earlier review: a table row
    # starts with a pipe.
    src = "| 1 | 2 |\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_indented_table_row_above_thematic_break_untouched():
    src = "  | 1 | 2 |\n---\n\nMore text.\n"
    assert packet_assemble._demote_headings(src) == src


def test_demote_headings_setext_h2_text_with_pipe_is_demoted():
    # A pipe appearing inside ordinary setext-heading text (not a table
    # row — the line doesn't start with `|`) must still demote. A pairing
    # heading like this is ordinary in hand-authored canon
    # (background_cut.py builds relationship entries from titles like
    # "Maggie and Cal").
    src = "Cal | Maggie\n---\n\nbody\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("###### Cal | Maggie\n")
    assert "---" not in out.split("\n\n", 1)[0]


def test_demote_headings_setext_h1_text_with_pipe_is_demoted():
    src = "Before | After\n===\n\nbody\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("##### Before | After\n")


def test_demote_headings_setext_text_line_indent_preserved():
    # The ATX path preserves a 1-3 space indent; the setext path must be
    # consistent with it instead of stripping the indent away.
    src = "   Canon Core\n===\n\nBody.\n"
    out = packet_assemble._demote_headings(src)
    assert out.startswith("   ##### Canon Core\n")




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


def test_continuity_extracts_survives_canon_meta_comment_above_thematic_break(series_tree):
    # canon-core.md opens with a <!-- canon-meta -->-style comment directly
    # above a `---` — the single shape guaranteed present in production
    # data (background_cut.py stamps it on every continuity entry). Before
    # the HTML-block exclusion, the setext guard would misread the comment
    # as setext-heading text and rewrite it to "###### <!-- canon-meta ... -->",
    # deleting the `---` in the process.
    cont = series_tree / "series/continuity"
    (cont / "canon-core.md").write_text(
        "<!-- canon-meta: {id: canon-core} -->\n"
        "---\n\n"
        "The Wheelhouse pottery studio. Maggie's Too-Much.\n",
        encoding="utf-8")
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")

    heading_line = next(l for l in text.splitlines()
                         if l.startswith("## Continuity Extracts"))
    start = text.index(heading_line) + len(heading_line)
    rest = text[start:]
    # `_first_real_markdown_boundary` treats *any* non-blank line followed
    # by a `===`/`---` underline as setext — including an HTML comment,
    # which a full parser reads as its own complete leaf block (it opens
    # and closes on one line) so the `---` after it is just a thematic
    # break, not glued to the comment as setext text. That would make the
    # helper itself misfire here, so this test instead locates the section
    # boundary the way the packet's own writer does: the next real,
    # non-indented `## ` sibling section header it emits.
    m = re.search(r"(?m)^## ", rest)
    section = rest[:m.start()] if m else rest

    assert "<!-- canon-meta: {id: canon-core} -->" in section
    assert "\n---\n" in section
    assert "The Wheelhouse pottery studio." in section
    assert "### canon-core.md" in section
    assert "### characters/mary.md" in section
    # And no level-1/2 heading (ATX or setext) survives in the section —
    # the demoted comment/thematic-break pair is at level 6, not level 2.
    assert not re.search(r"(?m)^#{1,2}(?!#)[ \t]", section)


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


# --- `## Ledger Clues` manifest + heading demotion -------------------------
# Spec `2026-08-29-curated-artifacts-declare-their-contents-design.md` §4a.
# The same bug the Continuity Extracts tests above cover, one section up in the
# packet, and worse where it lands: a truncated clue list means the chapter
# plants fewer clues than the ledger scheduled, and `inspector-fairplay` grades
# that chapter against the sealed ledger. The check and the thing it checks
# fail together. In the live book ten of forty-five clue entries carry
# multi-line block-scalar descriptions; none yet starts a line with `## `, so
# this is latent rather than live — which is exactly when it is cheap to close.

_HEADING_IN_DESCRIPTION_LEDGER = (
    "book: '01'\n"
    "reveal_chapter: 22\n"
    "clue_schedule:\n"
    "  - { id: mary-domestic-order, plant_chapter: 5, pays_off_chapter: 22, "
    "necessary: true, description: \"Mary restores cups and plates to their places.\" }\n"
    "  - id: kiln-log-gap\n"
    "    plant_chapter: 5\n"
    "    pays_off_chapter: 22\n"
    "    necessary: true\n"
    "    description: |\n"
    "      The kiln log skips the Tuesday firing.\n"
    "      ## Why the gap matters\n"
    "      Nobody initialled it, and Mary initials everything.\n"
    "red_herrings:\n"
    "  - { id: rh-saffron-till, plant_chapter: 5, "
    "misleads_toward: \"Saffron's till is short and she will not say why.\" }\n"
)


def _ledger_clues_section(text: str) -> str:
    """Isolate the packet's `## Ledger Clues ...` section the way a
    markdown-structure-aware reader would — the same rule
    `_continuity_extracts_section` uses: from its heading line up to (not
    including) the next sibling heading at level 1 or 2."""
    heading_line = next(l for l in text.splitlines() if l.startswith("## Ledger Clues"))
    start = text.index(heading_line) + len(heading_line)
    rest = text[start:]
    m = _SIBLING_HEADING_RE.search(rest)
    return rest[:m.start()] if m else rest


def _clues_heading(text: str) -> str:
    return next(l for l in text.splitlines() if l.startswith("## Ledger Clues"))


def test_ledger_clues_section_survives_a_heading_in_a_description(series_tree):
    # The direct analogue of test_continuity_extracts_section_survives_embedded
    # _headings. On unfixed code `## Why the gap matters` structurally closes
    # `## Ledger Clues`, and rh-saffron-till — a real scheduled obligation —
    # falls outside the section every structure-aware reader slices.
    (series_tree / "series/whodunit/book-01.yaml").write_text(
        _HEADING_IN_DESCRIPTION_LEDGER, encoding="utf-8")
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    section = _ledger_clues_section(text)
    assert "[mary-domestic-order]" in section
    assert "[kiln-log-gap]" in section
    assert "[rh-saffron-till]" in section
    assert "Nobody initialled it" in section


def test_ledger_clues_manifest_count_matches_emitted_clues(series_tree):
    # Spec §5.1: derive both numbers from the artifact, so the test cannot
    # pass by reading the same variable twice.
    (series_tree / "series/whodunit/book-01.yaml").write_text(
        _HEADING_IN_DESCRIPTION_LEDGER, encoding="utf-8")
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    heading = _clues_heading(text)
    m = re.search(r"\((\d+) scheduled", heading)
    assert m, f"no manifest count in heading line: {heading!r}"
    claimed = int(m.group(1))
    section = _ledger_clues_section(text)
    actual = len(re.findall(r"(?m)^- \[", section))
    assert actual == claimed
    assert claimed == 3


def test_ledger_clues_manifest_names_every_id_it_counts(series_tree):
    (series_tree / "series/whodunit/book-01.yaml").write_text(
        _HEADING_IN_DESCRIPTION_LEDGER, encoding="utf-8")
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    heading = _clues_heading(text)
    listed = re.search(r"\(\d+ scheduled: ([^)]*)\)", heading)
    assert listed, f"manifest names no ids: {heading!r}"
    named = {s.strip() for s in listed.group(1).split(",")}
    section = _ledger_clues_section(text)
    emitted = set(re.findall(r"(?m)^- \[([^\]]+)\]", section))
    assert named == emitted


def test_ledger_clues_manifest_singular_one_scheduled(series_tree):
    # The shared fixture schedules exactly one clue into chapter 05.
    text = packet_assemble.assemble("01", "05", repo_root=series_tree).read_text(
        encoding="utf-8")
    assert _clues_heading(text) == "## Ledger Clues (1 scheduled: mary-domestic-order)"


def test_ledger_clues_manifest_zero_scheduled(series_tree):
    # Chapter 06 has no scheduled clue. A section that says "None." must still
    # declare that nothing was withheld — silence is what a curated artifact
    # may never do (spec §3).
    text = packet_assemble.assemble("01", "06", repo_root=series_tree).read_text(
        encoding="utf-8")
    assert _clues_heading(text) == "## Ledger Clues (0 scheduled)"
    assert "- None." in _ledger_clues_section(text)


# The manifest is only worth emitting if a consumer is told to check it. When
# `## Continuity Extracts` gained one it was written into all three contracts
# that read a packet — drafter, map-maker, review-chapter — and this mirrors
# that. Beyond spec §4a's two literal bullets, and deliberately: a declaration
# nobody is asked to compare against is decoration.
_PACKET_CONSUMERS = (
    "agents/drafter.md",
    "agents/map-maker.md",
    "commands/review-chapter.md",
)
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("rel", _PACKET_CONSUMERS)
def test_packet_consumers_are_told_to_check_the_ledger_clues_manifest(rel):
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    # Matched as two facts rather than one literal string: these three files
    # already phrase the Continuity Extracts manifest two different ways —
    # attached (`## Continuity Extracts (N entries: ...)`) in drafter and
    # review-chapter, detached (`its heading carries a manifest — `(N entries:
    # ...)``) in map-maker. Pinning one phrasing would force a house style the
    # repo does not have.
    assert "Ledger Clues" in text and "(N scheduled" in text, (
        f"{rel} reads the packet's `## Ledger Clues` section but is never told"
        " its heading declares what was scheduled. It already carries the same"
        " instruction for `## Continuity Extracts`; without the pair, a"
        " truncated clue list still reads as a complete one."
    )
