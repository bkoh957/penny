"""Contract test: the shipped craft document must teach block names the
parsers actually read, and must reach consumers through the overlay.

Same failure mode test_outline_expander_agent.py pins — a document that
teaches a heading no parser matches looks right and is silently wrong. Here
the routing rule tells the author "put that note in `## Guardrails`", and if
that heading string ever drifts from what penny_story.parse_directives folds
on, the advice sends notes into a block nothing reads.
"""
from pathlib import Path

from scripts import penny_paths
from scripts.penny_story import parse_directives, parse_questions

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "config" / "story-craft" / "writing-beats.md"


def test_the_document_ships():
    assert DOC.is_file()


def test_it_is_reachable_through_the_overlay_directory():
    names = [p.name for p in penny_paths.config_dir_files(
        "story-craft", root=REPO)]
    assert "writing-beats.md" in names


def test_a_series_file_unions_and_only_its_own_name_shadows(tmp_path, monkeypatch):
    """The reason this is a directory read and not config_path: a genre or
    series adding one file must not hide the engine's default."""
    (tmp_path / ".penny").mkdir()
    (tmp_path / "config" / "story-craft").mkdir(parents=True)
    (tmp_path / "config" / "story-craft" / "cozy-beats.md").write_text(
        "extra", encoding="utf-8")
    monkeypatch.setattr(penny_paths, "series_root", lambda *a, **k: tmp_path)

    names = [p.name for p in penny_paths.config_dir_files("story-craft")]
    assert "cozy-beats.md" in names
    assert "writing-beats.md" in names


def test_routing_rule_names_headings_the_parsers_fold_on():
    text = DOC.read_text(encoding="utf-8")
    for heading in ("## Guardrails", "## Chapter Direction", "## Questions"):
        assert heading in text, heading

    probe = ("## Guardrails\n- a note. @maggie\n\n"
             "## Chapter Direction\n- a boundary note. @maggie\n\n"
             "## Questions\n- q-x — a question?\n")
    assert parse_directives(probe, "Guardrails")
    assert parse_directives(probe, "Chapter Direction")
    assert parse_questions(probe) == {"q-x": "a question?"}


def test_it_teaches_the_test_and_the_beat_size_rule():
    text = DOC.read_text(encoding="utf-8")
    assert "one visible change" in text
    assert "directive-shaped-beat" in text


def test_chapter_frames_doc_ships_and_names_the_three_kinds():
    p = Path(__file__).resolve().parents[1] / "config/story-craft/writing-chapter-frames.md"
    assert p.is_file()
    body = p.read_text(encoding="utf-8").lower()
    for kind in ("cliffhanger", "irony", "promise of action"):
        assert kind in body


def test_chapter_cutter_declares_the_three_fields_and_the_craft_doc():
    body = (Path(__file__).resolve().parents[1] / "agents/chapter-cutter.md").read_text(
        encoding="utf-8")
    assert "**Setting:**" in body and "**Opening:**" in body
    assert "Closing (" in body
    assert "writing-chapter-frames.md" in body
    assert "setting-pack" in body


# Regression: a live-series character name leaked into a plugin-default craft
# doc's worked example TWICE on this branch (writing-chapter-frames.md, then
# writing-beats.md — both fixed by swapping in the doc's own invented names).
# `config/` is a shipped default inherited by every genre and every series
# (CLAUDE.md's genre/location-agnostic rule), so a real character name here
# is not a cosmetic slip — it is exactly the contamination the rule forbids.
# The names are hardcoded here, never read from the live series folder: that
# folder lives outside this repo and this test must work without it.
_LIVE_SERIES_NAMES = ("Maggie",)


def test_no_live_series_character_name_appears_under_config():
    config_dir = Path(__file__).resolve().parents[1] / "config"
    for path in config_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in _LIVE_SERIES_NAMES:
            assert name not in text, f"{name!r} found in {path}"
