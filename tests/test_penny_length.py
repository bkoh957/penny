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


# --- FINAL REVIEW C1: the LEGACY length-profile (the live series' real file:
# a prose table + a book_target_words block, no band_*/weight_* keys at all)
# must fail with a NAMED, actionable error naming the keys it needs — never a
# bare "no band_default" that tells a series author nothing about a schema
# that changed under them. --------------------------------------------------

LEGACY = Path(__file__).resolve().parent / "fixtures" / "length-profile-legacy.md"


def test_legacy_profile_error_names_every_key_the_schema_needs():
    with pytest.raises(ValueError) as e:
        penny_length.parse_profile(LEGACY.read_text(encoding="utf-8"))
    message = str(e.value)
    for key in ("band_default", "weight_anchor", "min_connective_words"):
        assert key in message, f"the error must name {key}: {message}"


# --- FINAL REVIEW I5: the per-scene floors are generic over the profile's
# declared weight classes (min_<class>_words), so a starved SUPPORT scene is
# catchable with no constant in the engine. ---------------------------------

def test_parse_profile_reads_every_min_class_words_floor():
    text = ("```yaml\nband_default: [2000, 2500]\nweight_anchor: 8\n"
            "weight_support: 3\nweight_connective: 1\n"
            "min_connective_words: 100\nmin_support_words: 250\n```\n")
    p = penny_length.parse_profile(text)
    assert p["floors"] == {"connective": 100, "support": 250}
    assert p["min_connective_words"] == 100  # the old key still resolves


def test_profile_with_no_floors_declares_none_rather_than_guessing():
    text = "```yaml\nband_default: [2000, 2500]\nweight_anchor: 8\n```\n"
    p = penny_length.parse_profile(text)
    assert p["floors"] == {}
    assert p["min_connective_words"] == 0
