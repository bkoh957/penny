from pathlib import Path

from scripts.draft_words import stamp_words, main
from scripts.penny_text import word_count


def _draft(body="One two three four five.\n"):
    return ("---\nschema: penny-chapter/1\ndrafted_by: claude-opus\n"
            "drafted_on: 2026-08-25\n---\n\n" + body)


def test_word_count_counts_prose_words():
    assert word_count("One two three four five.") == 5


def test_word_count_ignores_scene_breaks_and_rules():
    # A scene-break marker is punctuation, not a word.
    assert word_count("Two words.\n\n* * *\n\n---\n\nThree more words here.") == 6


def test_word_count_ignores_markdown_headings():
    # assemble_book supplies "# Chapter N"; a stray scene heading is not chapter words.
    assert word_count("## Scene 2\n\nThree words here.") == 3


def test_word_count_keeps_hyphenates_and_contractions_whole():
    assert word_count("She didn’t half-turn.") == 3


def test_stamp_inserts_the_field_and_returns_the_count():
    text, n = stamp_words(_draft())
    assert n == 5
    assert "drafted_words: 5\n" in text
    assert text.endswith("One two three four five.\n")


def test_stamp_counts_the_body_only_not_the_frontmatter():
    # drafted_by / drafted_on / schema words must not inflate the count.
    _, n = stamp_words(_draft("Just four words here.\n"))
    assert n == 4


def test_stamp_is_idempotent_and_rewrites_a_stale_count():
    stale = _draft().replace("drafted_on: 2026-08-25\n",
                             "drafted_on: 2026-08-25\ndrafted_words: 999\n")
    text, n = stamp_words(stale)
    assert n == 5
    assert "drafted_words: 5\n" in text
    assert "999" not in text
    assert stamp_words(text)[0] == text


def test_stamp_refuses_a_draft_with_no_frontmatter():
    try:
        stamp_words("No frontmatter here.\n")
    except ValueError as e:
        assert "frontmatter" in str(e)
    else:
        raise AssertionError("expected ValueError")


def _series(tmp_path, body="One two three four five.\n"):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "output" / "book-01" / "chapters"
    d.mkdir(parents=True)
    (d / "ch-07.draft.md").write_text(_draft(body), encoding="utf-8")
    return d / "ch-07.draft.md"


def test_main_stamps_the_draft_in_place(tmp_path, monkeypatch, capsys):
    p = _series(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["01", "07"]) == 0
    assert "drafted_words: 5\n" in p.read_text(encoding="utf-8")
    assert "5" in capsys.readouterr().out


def test_main_reports_a_missing_draft_by_name(tmp_path, monkeypatch, capsys):
    (tmp_path / ".penny").mkdir()
    monkeypatch.chdir(tmp_path)
    assert main(["01", "07"]) == 2
    assert "draft not found" in capsys.readouterr().err


def test_main_usage_error(capsys):
    assert main(["01"]) == 2
    assert "usage" in capsys.readouterr().err


def test_draft_chapter_runbook_stamps_after_the_drafter():
    text = Path("commands/draft-chapter.md").read_text(encoding="utf-8")
    assert "scripts/draft_words.py" in text
    # Counted after the agent writes, never before it.
    assert text.index("Dispatch the `drafter` sub-agent") < text.index("draft_words.py")


def test_drafter_agent_is_told_not_to_write_the_field():
    text = Path("agents/drafter.md").read_text(encoding="utf-8")
    assert "drafted_words" in text and "Never write that field" in text
