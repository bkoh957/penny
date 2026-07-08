from pathlib import Path

FIX = Path(__file__).resolve().parent / "fixtures" / "cozy"


def test_cozy_fixture_is_a_complete_series():
    assert (FIX / ".penny").is_dir()
    assert (FIX / "series.yaml").read_text().strip() == "genre: cozy-mystery"
    for rel in ("config/run-config.md", "config/setting-pack/lexicon.yaml",
                "config/voice-pack/ai-tics-config.yaml", "config/beta-readers/personas",
                "series/continuity/canon-core.md", "input/series/whodunit-ledger.md"):
        assert (FIX / rel).exists(), f"fixture missing {rel}"


def test_cozy_fixture_genre_resolves():
    from scripts import penny_paths
    assert penny_paths.genre(root=FIX) == "cozy-mystery"
