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
