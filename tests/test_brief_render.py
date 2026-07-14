from pathlib import Path

import pytest

from scripts import brief_render

FIX = Path(__file__).resolve().parent / "fixtures"
PROFILE = FIX / "length-profile.md"
WEIGHTED = FIX / "outlines" / "weighted-clean.md"
INVERTED = FIX / "outlines" / "weighted-inverted.md"
WIRED = FIX / "outlines" / "wired-clean.md"


def _ids(findings):
    return sorted({f.split(":", 1)[0] for f in findings})


def test_unweighted_outline_is_skipped_entirely():
    r = brief_render.check_briefs(WIRED)
    assert r["weighted"] is False
    assert r["findings"] == []


def test_clean_weighted_outline_has_no_findings():
    r = brief_render.check_briefs(WEIGHTED)
    assert r["weighted"] is True
    assert r["findings"] == []


def test_prompt_mass_inversion_is_flagged():
    r = brief_render.check_briefs(INVERTED)
    assert "prompt-mass-inversion" in _ids(r["findings"])
    finding = next(f for f in r["findings"] if f.startswith("prompt-mass-inversion"))
    assert "ch 1" in finding
    assert "The Drive" in finding


def test_unweighted_chapter_in_a_weighted_book_is_flagged(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("**Weight:** anchor\n\n**Beat flow:**\n\n1. Mary sets down the tin and does not sit.", "**Beat flow:**\n\n1. Mary sets down the tin and does not sit.")
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p)
    assert "unweighted-chapter" in _ids(r["findings"])


def test_all_cliffhangers_is_flagged_when_the_beat_sheet_caps_them(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("[promise]", "[cliffhanger]")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("hooks:\n  max_cliffhanger_fraction: 0.5\n", encoding="utf-8")
    r = brief_render.check_briefs(outline, beat_sheet_path=sheet)
    assert "hook-grade-distribution" in _ids(r["findings"])


def test_missing_hook_grade_is_flagged(tmp_path):
    text = WEIGHTED.read_text(encoding="utf-8").replace("[cliffhanger] ", "")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(outline)
    assert "hook-grade-distribution" in _ids(r["findings"])


def test_scene_less_stub_chapter_is_skipped_not_flagged(tmp_path):
    """A chapter with zero ### Scene blocks (compact-format, or a skeletal stub
    /expand-outline hasn't reached yet) has nothing to say about weights or
    anchors — it must be skipped entirely by the scene-level checks, not
    treated as an anchor-less chapter. Ch 1 stays weighted and clean so its
    checks still run; ch 2 is the scene-less stub."""
    stub = (
        "## Chapter 02 — Not Yet Expanded\n\n"
        "### Chapter Summary\n"
        "A stub the outline-expander hasn't reached yet.\n"
    )
    # WEIGHTED's own frontmatter says total_chapters: 2 and already has a real
    # chapter 2 — replace it with the scene-less stub rather than appending a
    # duplicate chapter number.
    text = WEIGHTED.read_text(encoding="utf-8").split("## Chapter 02")[0] + stub
    p = tmp_path / "outline.md"
    p.write_text(text, encoding="utf-8")
    r = brief_render.check_briefs(p)
    assert r["weighted"] is True
    ids_by_chapter = [f for f in r["findings"] if "ch 2" in f]
    assert ids_by_chapter == []
    assert "unweighted-chapter" not in _ids(r["findings"])
    assert "prompt-mass-inversion" not in _ids(r["findings"])


def test_check_briefs_no_longer_accepts_profile_path():
    """FIX 2: check_briefs never reads band/weight data — profile_path was a
    dead-code feed into parse_profile and is dropped from the signature
    entirely (YAGNI)."""
    with pytest.raises(TypeError):
        brief_render.check_briefs(WEIGHTED, profile_path=PROFILE)


def test_check_briefs_works_with_no_length_profile_on_disk(tmp_path):
    """FIX 2 regression: check_briefs must not crash when no length-profile.md
    exists at all — it has no reason to touch one."""
    r = brief_render.check_briefs(WEIGHTED)
    assert r["weighted"] is True


def test_malformed_hooks_scalar_is_treated_as_no_cap(tmp_path):
    """FIX 3: a hand-edited beat-sheet.yaml with `hooks:` as a scalar (not a
    mapping) must not crash .get() — treat it as 'no cap configured'."""
    text = WEIGHTED.read_text(encoding="utf-8").replace("[promise]", "[cliffhanger]")
    outline = tmp_path / "outline.md"
    outline.write_text(text, encoding="utf-8")
    sheet = tmp_path / "beat-sheet.yaml"
    sheet.write_text("hooks: none\n", encoding="utf-8")
    r = brief_render.check_briefs(outline, beat_sheet_path=sheet)
    # no crash, and no cap means no hook-grade-distribution finding from the
    # cliffhanger-fraction check (both hooks are now cliffhanger, but with no
    # cap configured there's nothing to compare against).
    assert r["weighted"] is True


from scripts import penny_length


def _ch(name, path=WEIGHTED):
    from scripts.penny_wiring import parse_wired_chapters
    chapters = parse_wired_chapters(path.read_text(encoding="utf-8"))
    return next(c for c in chapters if c["num"] == name)


def _profile():
    return penny_length.parse_profile(PROFILE.read_text(encoding="utf-8"))


def test_brief_leads_with_the_one_thing_then_the_anchor():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    one_thing = brief.index("## The one thing")
    shape = brief.index("## The shape")
    obligations = brief.index("## Obligations")
    reference = brief.index("## Reference")
    assert one_thing < shape < obligations < reference


def test_anchor_carries_the_largest_budget_and_the_budgets_sum_to_the_band():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    # ch 1 has no [type:] flag, so the default band 2000-2500 → midpoint 2250,
    # shares connective 1 + anchor 8 = 9 → 250 and 2000.
    assert "~2000 words" in brief   # the anchor
    assert "~250 words" in brief    # the connective drive
    assert "Cal and the Mug" in brief


def test_connective_scene_names_its_form_not_a_number_alone():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "in summary, not scene" in brief


def test_brief_commissions_the_first_line_and_forbids_the_warm_up():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "in motion, mid-argument with the estate agent." in brief
    assert "no weather, no waking, no arriving" in brief


def test_brief_commissions_the_graded_hook_and_forbids_the_button():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "cliffhanger" in brief
    assert "Do not add a closing paragraph of reflection" in brief


def test_obligations_are_a_checklist_not_beats():
    brief = brief_render.render_brief(
        _ch(1), profile=_profile(),
        obligations={"clues": ["clue-tide-table"], "opens": ["q-who-is-she"],
                     "closes": [], "tracks": {"P": "She commits."}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    assert "clue-tide-table" in brief
    assert "must be TRUE OF THE PAGE" in brief
    assert "not stops on an itinerary" in brief


def test_long_waiver_is_carried_into_the_brief():
    brief = brief_render.render_brief(
        _ch(2), profile=_profile(),
        obligations={"clues": [], "opens": [], "closes": [], "tracks": {}},
        outline_text=WEIGHTED.read_text(encoding="utf-8"))
    # ch 2 declares [type: major-reveal] → band 2500-3200, midpoint 2850
    assert "~2850 words" in brief
    assert "the confession runs its full course" in brief
