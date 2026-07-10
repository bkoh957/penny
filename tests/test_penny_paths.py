import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import penny_paths as pp


def _make_series(tmp_path: Path) -> Path:
    (tmp_path / ".penny").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "series").mkdir(parents=True)
    return tmp_path


def test_series_root_found_from_root(tmp_path):
    s = _make_series(tmp_path)
    assert pp.series_root(start=s) == s


def test_series_root_found_from_nested_subdir(tmp_path):
    s = _make_series(tmp_path)
    nested = s / "series" / "continuity"
    nested.mkdir()
    assert pp.series_root(start=nested) == s


def test_series_root_missing_marker_fails_loud(tmp_path):
    with pytest.raises(SystemExit) as e:
        pp.series_root(start=tmp_path)
    assert "no series root" in str(e.value)


def test_plugin_root_is_engine_repo(tmp_path):
    # plugin_root is independent of cwd: it is where the engine code lives.
    assert (pp.plugin_root() / "scripts" / "penny_paths.py").is_file()


def test_config_path_uses_series_override_when_present(tmp_path):
    s = _make_series(tmp_path)
    override = s / "config" / "voice-pack"
    override.mkdir(parents=True)
    (override / "voice-pack.md").write_text("series voice")
    assert pp.config_path("voice-pack/voice-pack.md", root=s) == override / "voice-pack.md"


def test_config_path_falls_back_to_plugin_default(tmp_path):
    s = _make_series(tmp_path)  # empty config/, no override
    resolved = pp.config_path("review-rubrics/character-voice.md", root=s)
    assert resolved == pp.plugin_root() / "config" / "review-rubrics/character-voice.md"


def test_data_helpers_anchor_on_series_root(tmp_path):
    s = _make_series(tmp_path)
    assert pp.output_path("book-01/chapters", root=s) == s / "output" / "book-01/chapters"
    assert pp.series_path("whodunit/book-01.yaml", root=s) == s / "series" / "whodunit/book-01.yaml"
    assert pp.input_path("book-01/outline.md", root=s) == s / "input" / "book-01/outline.md"
    assert pp.penny_path("locks/book-01.mystery.lock", root=s) == s / ".penny" / "locks/book-01.mystery.lock"


def test_parallel_safety_two_series_disjoint(tmp_path):
    a = _make_series(tmp_path / "a")
    b = _make_series(tmp_path / "b")
    assert pp.output_path("x", root=a) != pp.output_path("x", root=b)
    assert pp.penny_path("x", root=a).parents[1] == a
    assert pp.penny_path("x", root=b).parents[1] == b


def test_active_is_folder_name(tmp_path):
    s = _make_series(tmp_path / "cozy-pelicans")
    assert pp.active(root=s) == "cozy-pelicans"


def test_cli_resolve_and_active(tmp_path):
    s = _make_series(tmp_path / "cozy-pelicans")
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run(
        [sys.executable, "-m", "scripts.penny_paths", "resolve", "series", "whodunit/x.yaml"],
        cwd=s, capture_output=True, text=True, env=env,
    )
    assert out.returncode == 0
    assert out.stdout.strip() == str(s / "series" / "whodunit/x.yaml")

    out2 = subprocess.run(
        [sys.executable, "-m", "scripts.penny_paths", "active"],
        cwd=s, capture_output=True, text=True, env=env,
    )
    assert out2.stdout.strip() == "cozy-pelicans"


def _make_genre_series(tmp_path, slug="cozy-mystery"):
    """A tmp series that declares a genre which really exists in the engine."""
    (tmp_path / ".penny").mkdir()
    (tmp_path / "series.yaml").write_text(f"genre: {slug}\n", encoding="utf-8")
    return tmp_path


def test_genre_reads_series_yaml(tmp_path):
    s = _make_genre_series(tmp_path)
    assert pp.genre(root=s) == "cozy-mystery"


def test_genre_missing_series_yaml_fails(tmp_path):
    (tmp_path / ".penny").mkdir()
    with pytest.raises(SystemExit) as e:
        pp.genre(root=tmp_path)
    assert "series.yaml" in str(e.value)


def test_genre_unknown_slug_fails(tmp_path):
    s = _make_genre_series(tmp_path, slug="no-such-genre")
    with pytest.raises(SystemExit) as e:
        pp.genre(root=s)
    assert "no-such-genre" in str(e.value)


def test_genre_dir_points_into_plugin(tmp_path):
    s = _make_genre_series(tmp_path)
    assert pp.genre_dir(root=s) == pp.plugin_root() / "genres" / "cozy-mystery"


def test_config_path_series_overrides_genre_and_default(tmp_path):
    s = _make_genre_series(tmp_path)
    ov = s / "config" / "review-rubrics"
    ov.mkdir(parents=True)
    (ov / "structure-tension.md").write_text("series", encoding="utf-8")
    assert pp.config_path("review-rubrics/structure-tension.md", root=s) == ov / "structure-tension.md"


def test_config_path_genre_tier_between_series_and_default(tmp_path, monkeypatch):
    # Simulate a genre-pack override by pointing genre_dir at a tmp dir that has the file.
    s = _make_genre_series(tmp_path)
    fake_genre = tmp_path / "fake-genre"
    (fake_genre / "review-rubrics").mkdir(parents=True)
    (fake_genre / "review-rubrics" / "fairplay-planting.md").write_text("genre", encoding="utf-8")
    monkeypatch.setattr(pp, "genre_dir", lambda g=None, root=None: fake_genre)
    got = pp.config_path("review-rubrics/fairplay-planting.md", root=s)
    assert got == fake_genre / "review-rubrics" / "fairplay-planting.md"


def test_config_path_falls_to_engine_default_when_no_override(tmp_path):
    s = _make_genre_series(tmp_path)  # no series override, cozy genre ships no such file yet
    got = pp.config_path("review-rubrics/character-voice.md", root=s)
    assert got == pp.plugin_root() / "config" / "review-rubrics/character-voice.md"


# --- config_dirs / config_dir_files: DIRECTORY lookups union across tiers ---
# First-hit-wins is right for a single file and wrong for a directory: a genre
# pack that adds one rubric must not hide the plugin's defaults.

def test_config_dirs_lists_every_existing_tier_highest_precedence_first(tmp_path, monkeypatch):
    s = _make_genre_series(tmp_path)
    series_ov = s / "config" / "review-rubrics"
    series_ov.mkdir(parents=True)
    fake_genre = tmp_path / "fake-genre"
    (fake_genre / "review-rubrics").mkdir(parents=True)
    monkeypatch.setattr(pp, "genre_dir", lambda g=None, root=None: fake_genre)

    assert pp.config_dirs("review-rubrics", root=s) == [
        series_ov,
        fake_genre / "review-rubrics",
        pp.plugin_root() / "config" / "review-rubrics",
    ]


def test_config_dirs_empty_when_no_tier_has_the_dir(tmp_path):
    s = _make_genre_series(tmp_path)
    assert pp.config_dirs("no-such-dir", root=s) == []


def test_config_dir_files_unions_genre_tier_over_plugin_defaults(tmp_path, monkeypatch):
    s = _make_genre_series(tmp_path)
    fake_genre = tmp_path / "fake-genre"
    (fake_genre / "review-rubrics").mkdir(parents=True)
    (fake_genre / "review-rubrics" / "fairplay-planting.md").write_text("genre", encoding="utf-8")
    monkeypatch.setattr(pp, "genre_dir", lambda g=None, root=None: fake_genre)

    names = sorted(p.name for p in pp.config_dir_files("review-rubrics", root=s))
    plugin_names = sorted(p.name for p in (pp.plugin_root() / "config" / "review-rubrics").glob("*.md"))
    assert names == sorted(plugin_names + ["fairplay-planting.md"])


def test_config_dir_files_higher_tier_shadows_same_filename(tmp_path, monkeypatch):
    s = _make_genre_series(tmp_path)
    series_ov = s / "config" / "review-rubrics"
    series_ov.mkdir(parents=True)
    (series_ov / "character-voice.md").write_text("series", encoding="utf-8")
    fake_genre = tmp_path / "fake-genre"
    (fake_genre / "review-rubrics").mkdir(parents=True)
    (fake_genre / "review-rubrics" / "character-voice.md").write_text("genre", encoding="utf-8")
    monkeypatch.setattr(pp, "genre_dir", lambda g=None, root=None: fake_genre)

    got = [p for p in pp.config_dir_files("review-rubrics", root=s) if p.name == "character-voice.md"]
    assert got == [series_ov / "character-voice.md"]
