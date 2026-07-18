from pathlib import Path

import pytest

from scripts import penny_length

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "length-profile.md"


def _profile():
    return penny_length.parse_profile(FIXTURE.read_text(encoding="utf-8"))


def test_parse_profile_reads_bands():
    p = _profile()
    assert p["bands"]["opening"] == (1800, 2400)
    assert p["bands"]["major-reveal"] == (2500, 3200)


def test_parse_profile_tolerates_and_ignores_legacy_v1_keys():
    # The fixture still carries weight_<class> / min_<class>_words lines — the
    # v1 schema. They must parse cleanly (no error) and simply not surface.
    p = _profile()
    assert "weights" not in p
    assert p["min_scene_words"] is None  # no v2 floor declared in the fixture


def test_band_for_unknown_type_falls_back_to_default():
    p = _profile()
    assert penny_length.band_for(p, None) == (2000, 2500)
    assert penny_length.band_for(p, "no-such-type") == (2000, 2500)


def test_band_for_known_type():
    p = _profile()
    assert penny_length.band_for(p, "opening") == (1800, 2400)


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
    # v2 schema: band_default and min_scene_words are required; legacy keys tolerated
    for key in ("band_default", "min_scene_words"):
        assert key in message, f"the error must name {key}: {message}"


# --- Task 3: validate_targets and min_scene_words ----

from scripts.penny_length import validate_targets

V2_PROFILE = """
```yaml
band_default: [2000, 2500]
band_event: [2800, 3600]
min_scene_words: 250
```
"""


def _scenes(*targets):
    return [{"num": i + 1, "title": f"S{i + 1}", "target": t}
            for i, t in enumerate(targets)]


def test_parse_profile_reads_min_scene_words():
    p = penny_length.parse_profile(V2_PROFILE)
    assert p["min_scene_words"] == 250


def test_parse_profile_min_scene_words_absent_is_none():
    p = penny_length.parse_profile("```yaml\nband_default: [2000, 2500]\n```")
    assert p["min_scene_words"] is None


def test_validate_targets_clean_map_passes():
    p = penny_length.parse_profile(V2_PROFILE)
    out = validate_targets(p, (2800, 3600),
                           _scenes((350, 450), (900, 1100), (700, 850),
                                   (400, 550), (500, 650)))
    assert out["blocking"] == []


def test_validate_targets_band_mismatch_when_sum_cannot_reach_band():
    p = penny_length.parse_profile(V2_PROFILE)
    out = validate_targets(p, (2800, 3600), _scenes((300, 400), (300, 400)))
    assert any(b.startswith("band-mismatch") for b in out["blocking"])


def test_validate_targets_band_mismatch_when_sum_overshoots_band():
    p = penny_length.parse_profile(V2_PROFILE)
    out = validate_targets(p, (2000, 2500), _scenes((2600, 3000)))
    assert any(b.startswith("band-mismatch") for b in out["blocking"])


def test_validate_targets_starved_scene_below_floor():
    p = penny_length.parse_profile(V2_PROFILE)
    out = validate_targets(p, (2000, 2500), _scenes((100, 200), (1900, 2300)))
    assert any(b.startswith("starved-scene") and "S1" in b
               for b in out["blocking"])


def test_validate_targets_missing_floor_is_named_note_not_silence():
    p = penny_length.parse_profile("```yaml\nband_default: [2000, 2500]\n```")
    out = validate_targets(p, (2000, 2500), _scenes((100, 2400)))
    assert out["blocking"] == []
    assert any("min_scene_words" in n for n in out["notes"])


def test_validate_targets_unparseable_target_is_blocking():
    p = penny_length.parse_profile(V2_PROFILE)
    out = validate_targets(p, (2000, 2500), _scenes(None, (2000, 2400)))
    assert any(b.startswith("unparseable-target") for b in out["blocking"])
