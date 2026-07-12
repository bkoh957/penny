import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import penny_genre as pg
from scripts import penny_paths as pp


def _write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


VALID = """\
genre: demo
conventions: conventions.md
planning:
  command: plan-mystery
  artifact: series/whodunit/book-{NN}.yaml
  validator: fairplay
  lock: mystery
inspectors: [continuity, fairplay]
gates: [fairplay, lexicon]
rubrics: [review-rubrics/fairplay-planting.md]
tracks: [M, P]
"""


def _engine(tmp_path: Path) -> Path:
    """A fake plugin root with the engine components the conformance check needs."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "commands").mkdir()
    (tmp_path / "commands" / "plan-mystery.md").write_text("x")
    (tmp_path / "agents").mkdir()
    for n in ("continuity", "fairplay"):
        (tmp_path / "agents" / f"inspector-{n}.md").write_text("x")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "fairplay_check.py").write_text("x")
    (tmp_path / "config" / "review-rubrics").mkdir(parents=True)
    (tmp_path / "config" / "review-rubrics" / "fairplay-planting.md").write_text("x")
    return tmp_path


def test_valid_manifest_has_no_errors(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "genre.yaml", VALID)
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load((gdir / "genre.yaml").read_text())
    assert pg.validate_manifest(manifest, gdir, plugin_root=engine) == []


def test_genre_must_match_dir(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "wrongname"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)  # genre: demo, but dir is 'wrongname'
    errs = pg.validate_manifest(manifest, gdir, plugin_root=engine)
    assert any("genre" in e and "wrongname" in e for e in errs)


def test_missing_inspector_agent_flagged(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)
    manifest["inspectors"] = ["continuity", "nonesuch"]
    errs = pg.validate_manifest(manifest, gdir, plugin_root=engine)
    assert any("nonesuch" in e for e in errs)


def test_missing_validator_script_flagged(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)
    manifest["planning"]["validator"] = "ghost"
    errs = pg.validate_manifest(manifest, gdir, plugin_root=engine)
    assert any("ghost" in e for e in errs)


def test_null_validator_and_lock_ok(tmp_path):
    engine = _engine(tmp_path / "engine")
    gdir = engine / "genres" / "demo"
    _write(gdir / "conventions.md", "x")
    import yaml
    manifest = yaml.safe_load(VALID)
    manifest["planning"]["validator"] = None
    manifest["planning"]["lock"] = None
    assert pg.validate_manifest(manifest, gdir, plugin_root=engine) == []


def test_real_cozy_manifest_conforms():
    """The shipped cozy-mystery manifest validates against the real engine."""
    engine = pp.plugin_root()
    gdir = engine / "genres" / "cozy-mystery"
    import yaml
    manifest = yaml.safe_load((gdir / "genre.yaml").read_text())
    assert pg.validate_manifest(manifest, gdir, plugin_root=engine) == []


def _make_genre_series(tmp_path, slug="cozy-mystery"):
    """A tmp series that declares a genre which really exists in the engine."""
    (tmp_path / ".penny").mkdir()
    (tmp_path / "series.yaml").write_text(f"genre: {slug}\n", encoding="utf-8")
    return tmp_path


def test_load_manifest_resolves_genre_from_series(tmp_path):
    """End-to-end: load_manifest(root=...) resolves the genre via penny_paths.genre()
    and returns the shipped cozy-mystery manifest."""
    s = _make_genre_series(tmp_path)
    manifest = pg.load_manifest(root=s)
    assert manifest["genre"] == "cozy-mystery"
    assert manifest["planning"]["command"] == "plan-mystery"


def _cozy_series(tmp_path):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "series.yaml").write_text("genre: cozy-mystery\n", encoding="utf-8")
    return tmp_path


def test_inspectors_accessor(tmp_path):
    s = _cozy_series(tmp_path)
    assert pg.inspectors(root=s) == ["continuity", "fairplay", "structure", "voice", "ai-prose"]


def test_gates_accessor(tmp_path):
    s = _cozy_series(tmp_path)
    assert pg.gates(root=s) == ["fairplay", "lexicon"]


def test_planning_accessor(tmp_path):
    s = _cozy_series(tmp_path)
    p = pg.planning(root=s)
    assert p["command"] == "plan-mystery"
    assert p["artifact"] == "series/whodunit/book-{NN}.yaml"
    assert p["validator"] == "fairplay"
    assert p["lock"] == "mystery"


def test_cli_inspectors_newline_joined(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "inspectors"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.returncode == 0
    assert out.stdout.split() == ["continuity", "fairplay", "structure", "voice", "ai-prose"]


def test_cli_direct_file_invocation_no_pythonpath(tmp_path):
    """Runbooks invoke penny_genre.py as a direct file path (not `-m`), with no
    PYTHONPATH set. Without a sys.path shim in the module itself, the deferred
    `from scripts import penny_paths` inside load_manifest() raises
    ModuleNotFoundError. Reproduces the exact runbook invocation."""
    s = _cozy_series(tmp_path)
    script = pp.plugin_root() / "scripts" / "penny_genre.py"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    out = subprocess.run([sys.executable, str(script), "inspectors"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["continuity", "fairplay", "structure", "voice", "ai-prose"]


def test_cli_planning_command(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "planning-command"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.stdout.strip() == "plan-mystery"


def test_cli_planning_lock(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "planning-lock"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.stdout.strip() == "mystery"


def test_cozy_manifest_declares_beat_sheet_and_fan_persona():
    m = pg.load_manifest("cozy-mystery")
    assert m["beat_sheet"] == "beat-sheet.yaml"
    assert m["fan_persona"] == "personas/genre-fan.md"


# --- FINAL REVIEW FINDING 5: genre.yaml's beat_sheet: key was validated but
# never actually RESOLVED anywhere — every reader hardcoded "beat-sheet.yaml". --

def test_beat_sheet_accessor_resolves_through_manifest_key(tmp_path):
    s = _cozy_series(tmp_path)
    p = pg.beat_sheet(root=s)
    assert p == pp.plugin_root() / "genres" / "cozy-mystery" / "beat-sheet.yaml"
    assert p.is_file()


def test_beat_sheet_accessor_returns_none_without_declared_genre(tmp_path):
    # Unlike inspectors()/gates()/planning() (book-scoped, genre mandatory),
    # beat_sheet() is consulted by the tension checker for outlines that may
    # have no genre context at all (a hand-wired outline, or a book that
    # hasn't reached /plot-book's genre-required door) — an undeclared genre
    # must not hard-fail lock-mystery for those.
    (tmp_path / ".penny").mkdir()
    assert pg.beat_sheet(root=tmp_path) is None


def test_cli_beat_sheet(tmp_path):
    s = _cozy_series(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(pp.plugin_root())}
    out = subprocess.run([sys.executable, "-m", "scripts.penny_genre", "beat-sheet"],
                         cwd=s, capture_output=True, text=True, env=env)
    assert out.returncode == 0
    assert out.stdout.strip() == str(pp.plugin_root() / "genres" / "cozy-mystery" / "beat-sheet.yaml")


def test_optional_file_keys_must_exist_when_present(tmp_path):
    gdir = tmp_path / "genres" / "test-genre"
    gdir.mkdir(parents=True)
    (gdir / "conventions.md").write_text("x", encoding="utf-8")
    manifest = {
        "genre": "test-genre", "conventions": "conventions.md",
        "planning": {"command": "plan-mystery", "artifact": "series/whodunit/book-{NN}.yaml",
                      "validator": "fairplay", "lock": "mystery"},
        "inspectors": [], "gates": [], "rubrics": [], "tracks": [],
        "beat_sheet": "beat-sheet.yaml",
    }
    from scripts import penny_paths
    errs = pg.validate_manifest(manifest, gdir, plugin_root=penny_paths.plugin_root())
    assert any("beat_sheet" in e for e in errs)
