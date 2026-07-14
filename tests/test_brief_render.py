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
