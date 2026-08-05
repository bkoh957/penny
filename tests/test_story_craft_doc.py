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
