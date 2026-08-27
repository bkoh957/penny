from scripts import texture_apply as ta

PLAN = """# Texture allocation — book 01

## Chapter 01
- bakery 6am: proving-room warmth
- shed roof at 25 knots

## Chapter 02
- quiet — no sensory spend past the room
"""

CUT = """## Chapter 01 — The Life Maggie Chose

- **Beats:** 1-2
- **Summary:** A life chosen.
- **Compress:** Gallery logistics.
- **Setting:**
  - 1-2 — the pottery studio, late afternoon
- **M:** The murder enters a world just shown.

## Chapter 02 — Competent Doubt

- **Beats:** 3
- **Summary:** Tom closes the question.
- **Compress:** Procedure.
- **M:** The police are right.
"""


def test_parse_texture_plan_reads_chapters_and_items():
    assert ta.parse_texture_plan(PLAN) == {
        1: ["bakery 6am: proving-room warmth", "shed roof at 25 knots"],
        2: ["quiet — no sensory spend past the room"],
    }


def test_a_title_bullet_before_any_chapter_is_not_an_item():
    plan = "# Texture allocation\n- a note to myself\n\n## Chapter 01\n- one image\n"
    assert ta.parse_texture_plan(plan) == {1: ["one image"]}


def test_the_block_lands_after_compress_and_before_setting():
    out, blocking, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    assert blocking == []
    assert ("- **Compress:** Gallery logistics.\n"
            "- **Texture:**\n"
            "  - bakery 6am: proving-room warmth\n"
            "  - shed roof at 25 knots\n"
            "- **Setting:**\n") in out


def test_the_spliced_plan_parses_back_into_the_allocation():
    from scripts.penny_story import parse_cut_plan
    out, _, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    chapters = parse_cut_plan(out)
    assert chapters[0]["texture"] == ["bakery 6am: proving-room warmth",
                                      "shed roof at 25 knots"]
    assert chapters[1]["texture"] == ["quiet — no sensory spend past the room"]
    assert chapters[0]["compress"] == "Gallery logistics."
    assert chapters[0]["tracks"] == {"M": "The murder enters a world just shown."}


def test_applying_twice_is_idempotent():
    once, _, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    twice, _, _ = ta.apply_texture(once, ta.parse_texture_plan(PLAN))
    assert once == twice


def test_a_re_allocation_replaces_the_previous_block():
    once, _, _ = ta.apply_texture(CUT, ta.parse_texture_plan(PLAN))
    new, blocking, _ = ta.apply_texture(once, {1: ["only this now"], 2: ["x"]})
    assert blocking == []
    assert "proving-room warmth" not in new
    assert "  - only this now\n" in new


def test_an_allocation_for_a_chapter_the_plan_lacks_is_refused_by_name():
    out, blocking, _ = ta.apply_texture(CUT, {9: ["ghost image"]})
    assert any(f.startswith("unknown-chapter:") and "09" in f for f in blocking)
    assert out == CUT          # never partially applied


def test_a_chapter_with_no_allocation_is_an_advisory_not_a_finding():
    out, blocking, notes = ta.apply_texture(CUT, {1: ["one image"]})
    assert blocking == []
    assert any(n.startswith("unallocated-chapter:") and "02" in n for n in notes)
    assert "### " not in out   # untouched chapters keep their shape


def test_a_named_chapter_with_no_items_is_advised_and_left_alone():
    out, blocking, notes = ta.apply_texture(CUT, {1: [], 2: ["x"]})
    assert blocking == []
    assert any(n.startswith("empty-allocation:") and "01" in n for n in notes)
    from scripts.penny_story import parse_cut_plan
    assert parse_cut_plan(out)[0]["texture"] == []


def test_a_chapter_with_no_summary_or_compress_anchor_is_refused():
    cut = "## Chapter 01 — T\n\n- **Beats:** 1\n- **M:** m\n"
    out, blocking, _ = ta.apply_texture(cut, {1: ["one image"]})
    assert any(f.startswith("no-anchor:") for f in blocking)
    assert out == cut


def test_a_late_no_anchor_discards_the_splices_earlier_chapters_already_got():
    cut = ("## Chapter 01 — One\n\n- **Summary:** s\n- **Compress:** c\n\n"
           "## Chapter 02 — Two\n\n- **Beats:** 3\n- **M:** m\n")
    out, blocking, _ = ta.apply_texture(cut, {1: ["bakery 6am"], 2: ["x"]})
    assert any(f.startswith("no-anchor:") and "02" in f for f in blocking)
    assert out == cut                 # chapter 1's splice discarded too
    assert "bakery 6am" not in out


def test_prose_above_the_first_chapter_heading_is_preserved():
    cut = "# Cut plan — book 01\n\nApproved 2026-08-27.\n\n" + CUT
    out, blocking, _ = ta.apply_texture(cut, ta.parse_texture_plan(PLAN))
    assert blocking == []
    assert out.startswith("# Cut plan — book 01\n\nApproved 2026-08-27.\n")


def test_a_wrapped_item_folds_into_one_joined_by_a_single_space():
    # The agent file's own canonical "shed roof" example — hard-wrapped across
    # two physical lines, the way an agent actually writes prose. The
    # continuation must fold into the item rather than vanish.
    plan = (
        "## Chapter 01\n"
        "- bakery 6am: proving-room warmth, the scorched edge of the second tray\n"
        "- shed roof at 25 knots — the ridge capping lifting and dropping (plants the\n"
        "  ch 29 return)\n"
    )
    assert ta.parse_texture_plan(plan) == {
        1: [
            "bakery 6am: proving-room warmth, the scorched edge of the second tray",
            "shed roof at 25 knots — the ridge capping lifting and dropping "
            "(plants the ch 29 return)",
        ],
    }


def test_a_blank_line_between_items_still_separates_them():
    plan = (
        "## Chapter 01\n"
        "- bakery 6am: proving-room warmth\n"
        "\n"
        "- shed roof at 25 knots\n"
    )
    assert ta.parse_texture_plan(plan) == {
        1: ["bakery 6am: proving-room warmth", "shed roof at 25 knots"],
    }
