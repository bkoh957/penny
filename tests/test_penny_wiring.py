from pathlib import Path

from scripts.penny_wiring import parse_wired_chapters, has_wiring, split_id

FIX = Path("tests/fixtures/outlines")


def _clean():
    return parse_wired_chapters((FIX / "wired-clean.md").read_text(encoding="utf-8"))


def test_parses_all_chapters_in_order():
    chs = _clean()
    assert [c["num"] for c in chs] == [1, 2, 3, 4, 5, 6]
    assert chs[0]["title"] == "Arrival"


def test_because_parsed():
    chs = _clean()
    assert chs[0]["because"] == "opening" and chs[0]["because_ch"] is None
    assert chs[1]["because_ch"] == 1


def test_opens_closes_carries_hook():
    chs = _clean()
    assert chs[0]["opens"] == [("q-who-killed-neil", "who killed the town GP?")]
    assert chs[4]["closes"] == ["q-who-killed-neil", "q-what-mary-hides"]
    assert chs[5]["carries"] == ["q-elspeth-vale"]
    assert chs[0]["hook_q"] == "q-who-killed-neil"


def test_tracks_parsed():
    chs = _clean()
    assert chs[1]["tracks"]["P"] == "None"
    assert chs[0]["tracks"]["M"] == "Body found."


def test_has_wiring_true_on_clean_false_on_legacy():
    assert has_wiring(_clean()) is True
    legacy = (FIX / "well-formed.md").read_text(encoding="utf-8")
    assert has_wiring(parse_wired_chapters(legacy)) is False


def test_bad_question_id_lands_in_errors():
    text = ("---\nbook: 01\ntotal_chapters: 1\n---\n\n## Solution: x\n- culprit: A\n\n"
            "## Chapter 01 — T\nbody\n- **Because:** opening\n- **Opens:** WhoDidIt — bad id\n")
    chs = parse_wired_chapters(text)
    assert chs[0]["errors"] and "WhoDidIt" in chs[0]["errors"][0]


def test_split_id():
    assert split_id("q-x — why?") == ("q-x", "why?")
    assert split_id("q-x") == ("q-x", "")
