import json
import pytest
from scripts import beta_report as br


def _curve(*pairs):
    return [{"chapter": c, "score": s} for c, s in pairs]


def test_driver_is_stamped_from_persona_not_payload():
    r = br.build_raw_reading(
        persona="cozy-loyalist", model="codex",
        engagement_curve=_curve((1, 4)), put_down_points=[],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=["warm hearth scene"],
        would_buy_verdict="yes")
    assert r["would_buy_next"]["driver"] == "comfort-tone"
    assert r["emotional_beats"][0]["lens"] == "comfort-tone"


def test_verdict_enum_enforced():
    with pytest.raises(ValueError):
        br.build_raw_reading(
            persona="puzzle-hawk", model="codex",
            engagement_curve=_curve((1, 3)), put_down_points=[],
            whodunit_guess={"name": "X", "chapter": 9},
            confusion_points=[], emotional_beats=[],
            would_buy_verdict="maybe")


def test_na_is_distinct_from_no():
    r = br.build_raw_reading(
        persona="romance-reader", model="codex",
        engagement_curve=_curve((1, 3)), put_down_points=[],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=[],
        would_buy_verdict="n/a")
    assert r["would_buy_next"]["verdict"] == "n/a"
    assert r["would_buy_next"]["verdict"] != "no"


def test_facet_rejected_for_non_arc():
    with pytest.raises(ValueError):
        br.build_raw_reading(
            persona="cozy-loyalist", model="codex",
            engagement_curve=_curve((1, 4)), put_down_points=[],
            whodunit_guess={"name": None, "chapter": None},
            confusion_points=[], emotional_beats=[],
            would_buy_verdict="no", would_buy_facet="self")


def test_facet_allowed_for_arc():
    r = br.build_raw_reading(
        persona="arc-reader", model="codex",
        engagement_curve=_curve((1, 4)), put_down_points=[],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=["she chooses to stay"],
        would_buy_verdict="no", would_buy_facet="place")
    assert r["would_buy_next"]["facet"] == "place"


def test_unknown_persona_rejected():
    with pytest.raises(ValueError):
        br.build_raw_reading(
            persona="nope", model="codex",
            engagement_curve=_curve((1, 4)), put_down_points=[],
            whodunit_guess={"name": None, "chapter": None},
            confusion_points=[], emotional_beats=[],
            would_buy_verdict="yes")


def test_serialize_round_trips_payload(tmp_path):
    r = br.build_raw_reading(
        persona="impatient-skimmer", model="hermes",
        engagement_curve=_curve((1, 5), (2, 2)), put_down_points=[2],
        whodunit_guess={"name": None, "chapter": None},
        confusion_points=[], emotional_beats=[],
        would_buy_verdict="no")
    path = br.write_raw_reading(tmp_path, r)
    assert path.name == "impatient-skimmer.hermes.raw.md"
    text = path.read_text(encoding="utf-8")
    assert "schema: penny-beta/1" in text
    payload = json.loads(text.split("---\n", 2)[2])
    assert payload["put_down_points"] == [2]
