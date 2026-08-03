import pytest

from scripts.story_cut import (body_sha, expand_in_place_refusal, recut_refusal,
                               stamp_outline)


def test_stamped_outline_round_trips_and_is_safe_to_recut():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64, book="02", total_chapters=1)
    assert "built_from_story: " + "a" * 64 in stamped
    assert recut_refusal(stamped) is None


def test_hand_edited_outline_refuses_by_name():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64, book="02", total_chapters=1)
    edited = stamped.replace("## Chapter 01 — One", "## Chapter 01 — One, Revised")
    finding = recut_refusal(edited)
    assert finding is not None
    assert finding.startswith("outline-modified-since-cut:")


def test_outline_with_no_stamp_is_treated_as_hand_authored_and_refuses():
    # Book 01's outline predates the cut entirely. Overwriting it would be the
    # exact loss spec 7 forbids, so absence of a stamp is a refusal, never a
    # licence.
    finding = recut_refusal("## Chapter 01 — One\n")
    assert finding is not None
    assert "no cut_output_sha256" in finding


def test_body_sha_ignores_frontmatter():
    a = stamp_outline("body\n", story_sha="a" * 64, cut_sha="b" * 64, book="02", total_chapters=1)
    b = stamp_outline("body\n", story_sha="c" * 64, cut_sha="d" * 64, book="02", total_chapters=1)
    assert body_sha(a) == body_sha(b)


# --- /expand-outline vs. a cut-produced outline (spec 2026-08-03 §12 ruling) ---
# /expand-outline is for outlines that were never cut, and refuses the ones
# that were: expanding a stub in place inside a cut-produced outline.md would
# silently make story.md and outline.md disagree — the drift that retired
# outline-skeleton.md in the first place.

def test_expand_in_place_refuses_a_cut_produced_outline_by_name():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64, book="02", total_chapters=1)
    finding = expand_in_place_refusal(stamped)
    assert finding is not None
    assert finding.startswith("cut-owned-outline:")


def test_expand_in_place_accepts_an_outline_with_no_cut_stamp():
    # Hand-authored or /scaffold-book-derived (book 01, for instance): never
    # cut from a story.md, so expanding in place is exactly today's behaviour.
    assert expand_in_place_refusal("## Chapter 01 — One\n") is None
