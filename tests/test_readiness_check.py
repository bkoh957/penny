"""Tests for the pre-flight readiness checklist (scripts/readiness_check.py).

Builds tmp repos (engine neutral defaults from the plugin root, overlaid with
the cozy fixture's series overrides) and asserts the ready/missing/blocked
classification for engine config and per-book inputs.
"""
import shutil
from pathlib import Path

import yaml

from scripts import readiness_check

REPO = readiness_check.REPO
# A self-contained cozy series fixture: real copies of the config OVERRIDES
# (run-config, voice/setting/genre packs, beta personas) + canon-core. It does
# NOT contain the engine's neutral config DEFAULTS (rubrics, line/copy-edit,
# self-audit, outline-template, beta-protocol) — those come from the plugin root.
SRC = Path(__file__).resolve().parent / "fixtures" / "cozy"
FIXTURE_LEDGER = REPO / "tests/fixtures/ledgers/fair.yaml"


def _engine_ready(tmp):
    """Assemble engine neutral defaults + the fixture's overrides + canon-core."""
    shutil.copytree(readiness_check.penny_paths.plugin_root() / "config", tmp / "config")
    shutil.copytree(SRC / "config", tmp / "config", dirs_exist_ok=True)
    (tmp / "series/continuity").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "series/continuity/canon-core.md",
                tmp / "series/continuity/canon-core.md")


def _by(checks, name):
    return next(c for c in checks if c["name"] == name)


def _write_ledger(tmp):
    wd = tmp / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE_LEDGER, wd / "book-01.yaml")


def _write_entities(tmp, ids=("margaret", "edwin-tilley", "thomas")):
    cc = tmp / "series/continuity/characters"
    cc.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        (cc / f"{cid}.md").write_text("---\nid: x\n---\n", encoding="utf-8")


# --- engine / config ---------------------------------------------------------

def test_engine_all_ready_no_book(tmp_path):
    _engine_ready(tmp_path)
    report = readiness_check.check_readiness(repo_root=tmp_path)
    assert all(c["status"] == "ready" for c in report["engine_and_config"])
    assert "book_inputs" not in report
    assert report["summary"]["missing"] == 0
    assert report["summary"]["verdict"] == "READY"


def test_missing_engine_file_flagged(tmp_path):
    # Delete a *data* path (canon-core), not a config override: config paths fall
    # back to the plugin default, so a deleted override is never "missing". Only a
    # no-fallback data path can prove readiness flags a genuinely-absent file.
    _engine_ready(tmp_path)
    (tmp_path / "series/continuity/canon-core.md").unlink()
    report = readiness_check.check_readiness(repo_root=tmp_path)
    assert _by(report["engine_and_config"], "canon-core")["status"] == "missing"
    assert report["summary"]["verdict"] == "NOT-READY"
    assert report["summary"]["missing"] >= 1


def test_dir_with_too_few_files_blocked(tmp_path):
    _engine_ready(tmp_path)
    personas = sorted((tmp_path / "config/beta-readers/personas").glob("*.md"))
    personas[0].unlink()  # drop below the expected 6
    report = readiness_check.check_readiness(repo_root=tmp_path)
    entry = _by(report["engine_and_config"], "beta-personas")
    assert entry["status"] == "blocked"
    assert entry["kind"] == "dir"


# --- per-book inputs ---------------------------------------------------------

def test_book_inputs_all_missing(tmp_path):
    _engine_ready(tmp_path)
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    bi = report["book_inputs"]
    assert _by(bi, "mystery-ledger")["status"] == "missing"
    assert _by(bi, "chapter-briefs")["status"] == "missing"
    assert _by(bi, "mystery-lock")["status"] == "missing"
    assert report["summary"]["verdict"] == "NOT-READY"


def test_ledger_present_missing_entities_blocked(tmp_path):
    _engine_ready(tmp_path)
    _write_ledger(tmp_path)  # culprit margaret / victim edwin-tilley / suspect thomas
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    entry = _by(report["book_inputs"], "character-entities")
    assert entry["status"] == "blocked"
    assert "margaret" in entry["detail"]


def test_entities_present_character_and_fairplay_ready(tmp_path):
    _engine_ready(tmp_path)
    _write_ledger(tmp_path)
    _write_entities(tmp_path)
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    bi = report["book_inputs"]
    assert _by(bi, "character-entities")["status"] == "ready"
    assert _by(bi, "mystery-fairplay")["status"] == "ready"


def test_lock_present_ready(tmp_path):
    _engine_ready(tmp_path)
    locks = tmp_path / ".penny/locks"
    locks.mkdir(parents=True, exist_ok=True)
    (locks / "book-01.mystery.lock").write_text("book: 01\n", encoding="utf-8")
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    assert _by(report["book_inputs"], "mystery-lock")["status"] == "ready"


def test_briefs_dir_present_ready(tmp_path):
    _engine_ready(tmp_path)
    briefs = tmp_path / "series/briefs/book-01"
    briefs.mkdir(parents=True, exist_ok=True)
    (briefs / "ch-01-brief.md").write_text("# brief\n", encoding="utf-8")
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    entry = _by(report["book_inputs"], "chapter-briefs")
    assert entry["status"] == "ready"
    assert "1" in entry["detail"]


# --- pipeline progress (informational) ---------------------------------------

def test_pipeline_progress_counts(tmp_path):
    _engine_ready(tmp_path)
    _write_ledger(tmp_path)  # total_chapters: 24
    chapters = tmp_path / "output/book-01/chapters"
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / "ch-01.draft.md").write_text("x", encoding="utf-8")
    (chapters / "ch-01.final.md").write_text("x", encoding="utf-8")
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    pp = report["pipeline_progress"]
    assert pp["drafts"] == "1/24"
    assert pp["finals"] == "1/24"
    assert pp["manuscript"] == "missing"


# --- emission ----------------------------------------------------------------

def test_to_yaml_round_trips(tmp_path):
    _engine_ready(tmp_path)
    report = readiness_check.check_readiness(book="01", repo_root=tmp_path)
    text = readiness_check.to_yaml(report)
    parsed = yaml.safe_load(text)
    assert parsed["summary"]["verdict"] in ("READY", "NOT-READY")
    assert parsed["book"] == "01"


def test_main_no_book_emits_engine_config_yaml(capsys, monkeypatch):
    # Run main() end-to-end against the self-contained cozy fixture (it carries
    # its own .penny marker), not this repo's live series data.
    monkeypatch.chdir(SRC)
    rc = readiness_check.main([])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = yaml.safe_load(out)
    assert "engine_and_config" in parsed
    assert "book_inputs" not in parsed
