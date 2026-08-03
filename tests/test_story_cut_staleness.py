import pytest

from scripts.story_cut import body_sha, recut_refusal, stamp_outline


def test_stamped_outline_round_trips_and_is_safe_to_recut():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64)
    assert "built_from_story: " + "a" * 64 in stamped
    assert recut_refusal(stamped) is None


def test_hand_edited_outline_refuses_by_name():
    stamped = stamp_outline("## Chapter 01 — One\n", story_sha="a" * 64,
                            cut_sha="b" * 64)
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
    a = stamp_outline("body\n", story_sha="a" * 64, cut_sha="b" * 64)
    b = stamp_outline("body\n", story_sha="c" * 64, cut_sha="d" * 64)
    assert body_sha(a) == body_sha(b)
