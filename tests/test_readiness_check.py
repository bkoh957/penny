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
    shutil.copy(SRC / "series.yaml", tmp / "series.yaml")
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


def _reroute_inspector(tmp, value):
    cfg = tmp / "config/run-config.md"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace("inspector_model:  claude-sonnet", value),
        encoding="utf-8")


def test_review_panel_routing_ready_when_inspector_differs_from_drafter(tmp_path):
    _engine_ready(tmp_path)
    entry = _by(readiness_check.engine_checks(tmp_path), "review-panel-routing")
    assert entry["status"] == "ready"


def test_review_panel_routing_blocked_when_inspector_is_the_drafter(tmp_path):
    _engine_ready(tmp_path)
    _reroute_inspector(tmp_path, "inspector_model:  claude-opus")
    entry = _by(readiness_check.engine_checks(tmp_path), "review-panel-routing")
    assert entry["status"] == "blocked"
    assert "drafting_model" in entry["detail"]


def test_review_panel_routing_blocked_when_inspector_model_absent(tmp_path):
    _engine_ready(tmp_path)
    _reroute_inspector(tmp_path, "")
    entry = _by(readiness_check.engine_checks(tmp_path), "review-panel-routing")
    assert entry["status"] == "blocked"
    assert "inspector_model" in entry["detail"]


def test_dir_with_too_few_files_blocked(tmp_path):
    _engine_ready(tmp_path)
    personas = sorted((tmp_path / "config/beta-readers/personas").glob("*.md"))
    personas[0].unlink()  # drop below the expected 6
    report = readiness_check.check_readiness(repo_root=tmp_path)
    entry = _by(report["engine_and_config"], "beta-personas")
    assert entry["status"] == "blocked"
    assert entry["kind"] == "dir"


def test_setting_and_genre_pack_are_not_hardcoded_to_cozy_fixture_names(tmp_path):
    """A non-cozy series with its own pack names should not be reported missing."""
    _engine_ready(tmp_path)
    (tmp_path / "series.yaml").write_text("genre: desert-noir\n", encoding="utf-8")
    (tmp_path / "config/setting-pack/coastal-victoria-au.md").unlink()
    (tmp_path / "config/genre-pack/cozy-mystery.md").unlink()
    (tmp_path / "config/setting-pack/desert-nevada.md").write_text("setting\n", encoding="utf-8")
    (tmp_path / "config/genre-pack/desert-noir.md").write_text("genre\n", encoding="utf-8")

    report = readiness_check.check_readiness(repo_root=tmp_path)

    assert _by(report["engine_and_config"], "setting-pack")["status"] == "ready"
    assert _by(report["engine_and_config"], "genre-pack")["status"] == "ready"


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


def test_review_rubrics_union_across_tiers_not_shadowed_by_genre_pack(tmp_path):
    """A genre pack that ships 2 rubrics must ADD to the plugin's 5, not hide them.

    Reproduces the real series layout (which `_engine_ready` masks by copying the
    plugin defaults into the *series* tier): no series-level review-rubrics/, so
    the lookup lands on genres/cozy-mystery/review-rubrics/ (2 files) and used to
    stop there, reporting `blocked: 2/5 file(s)`.
    """
    _engine_ready(tmp_path)
    shutil.rmtree(tmp_path / "config" / "review-rubrics")

    check = _by(readiness_check.engine_checks(repo_root=tmp_path), "review-rubrics")
    assert check["status"] == "ready", check


# --- the length profile's own schema (2026-08-25) ----------------------------
# `length-profile` was a bare presence check: a profile the engine cannot parse
# at all, or one still on schema v1 whose scene floors are silently ignored,
# both reported `ready`. A half-inert profile is a SERIES-level fact — the
# starved-scene check is dead for every chapter of every book — and until now
# its only trace was one note in one chapter's map_check output.

V1_PROFILE = (
    "```yaml\n"
    "band_default: [2000, 2500]\n"
    "weight_anchor: 8\n"
    "min_support_words: 250\n"
    "```\n"
)


def test_length_profile_ready_reports_its_bands_and_floor(tmp_path):
    _engine_ready(tmp_path)
    check = _by(readiness_check.engine_checks(repo_root=tmp_path), "length-profile")
    assert check["status"] == "ready", check
    assert "min_scene_words" in check["detail"]


def test_schema_v1_profile_is_blocked_and_names_what_is_inert(tmp_path):
    _engine_ready(tmp_path)
    (tmp_path / "config/length-profile.md").write_text(V1_PROFILE, encoding="utf-8")
    check = _by(readiness_check.engine_checks(repo_root=tmp_path), "length-profile")
    assert check["status"] == "blocked", check
    for phrase in ("no-scene-floor", "min_scene_words", "starved-scene",
                   "schema v1", "weight_anchor"):
        assert phrase in check["detail"], phrase


def test_a_floorless_v2_profile_is_ready_but_says_the_check_cannot_run(tmp_path):
    # Nothing failed to migrate here — min_scene_words is optional in the
    # schema — so the verdict must stay READY while the report still says
    # starved-scene is inert.
    _engine_ready(tmp_path)
    (tmp_path / "config/length-profile.md").write_text(
        "```yaml\nband_default: [2000, 2500]\n```\n", encoding="utf-8")
    check = _by(readiness_check.engine_checks(repo_root=tmp_path), "length-profile")
    assert check["status"] == "ready", check
    assert "starved-scene" in check["detail"]
    assert "schema v1" not in check["detail"]


def test_unparseable_profile_is_blocked_not_ready(tmp_path):
    # The pre-band legacy profile (a prose table, no band_* keys): every
    # chapter's word band is unknown, and readiness used to call it ready.
    _engine_ready(tmp_path)
    shutil.copy(REPO / "tests/fixtures/length-profile-legacy.md",
                tmp_path / "config/length-profile.md")
    check = _by(readiness_check.engine_checks(repo_root=tmp_path), "length-profile")
    assert check["status"] == "blocked", check
    assert "band_default" in check["detail"]


def test_missing_profile_is_still_missing(tmp_path):
    _engine_ready(tmp_path)
    (tmp_path / "config/length-profile.md").unlink()
    check = _by(readiness_check.engine_checks(repo_root=tmp_path), "length-profile")
    assert check["status"] == "missing", check
