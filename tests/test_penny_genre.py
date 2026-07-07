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
