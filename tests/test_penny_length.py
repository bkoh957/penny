from pathlib import Path

import pytest

from scripts import penny_length

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "length-profile.md"


def _profile():
    return penny_length.parse_profile(FIXTURE.read_text(encoding="utf-8"))


def test_parse_profile_reads_bands_and_weights():
    p = _profile()
    assert p["bands"]["opening"] == (1800, 2400)
    assert p["bands"]["major-reveal"] == (2500, 3200)
    assert p["weights"] == {"anchor": 8, "support": 3, "connective": 1}
    assert p["min_connective_words"] == 100


def test_band_for_unknown_type_falls_back_to_default():
    p = _profile()
    assert penny_length.band_for(p, None) == (2000, 2500)
    assert penny_length.band_for(p, "no-such-type") == (2000, 2500)


def test_band_for_known_type():
    p = _profile()
    assert penny_length.band_for(p, "opening") == (1800, 2400)


def test_scene_budgets_share_the_band_midpoint_by_weight():
    # midpoint of 1800-2400 is 2100; shares 8 + 3 + 1 + 1 + 1 = 14
    p = _profile()
    budgets = penny_length.scene_budgets(
        p, (1800, 2400), ["anchor", "support", "connective", "connective", "connective"])
    assert sum(budgets) == 2100
    assert budgets[0] == 1200   # 2100 * 8 / 14
    assert budgets[1] == 450    # 2100 * 3 / 14
    assert budgets[2] == 150    # 2100 * 1 / 14


def test_scene_budgets_rounding_still_sums_to_the_target():
    p = _profile()
    budgets = penny_length.scene_budgets(p, (2000, 2500), ["anchor", "support", "connective"])
    assert sum(budgets) == 2250  # remainder lands on the anchor, never lost


def test_scene_budgets_rejects_an_unknown_weight():
    p = _profile()
    with pytest.raises(ValueError) as e:
        penny_length.scene_budgets(p, (1800, 2400), ["anchor", "atmospheric"])
    assert "atmospheric" in str(e.value)


def test_scene_budgets_rejects_all_zero_weights_instead_of_silently_zeroing():
    # A length-profile that assigns weight 0 to a class must not silently drop
    # the whole chapter's word target to zero when every scene is that class.
    p = {"weights": {"atmospheric": 0}}
    with pytest.raises(ValueError) as e:
        penny_length.scene_budgets(p, (1800, 2400), ["atmospheric", "atmospheric"])
    message = str(e.value)
    assert "atmospheric" in message
    assert "length-profile" in message


def test_scene_budgets_empty_scene_list_returns_empty():
    p = _profile()
    assert penny_length.scene_budgets(p, (1800, 2400), []) == []
