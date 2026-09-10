"""The review panel's completeness check, moved out of runbook prose.

`/review-chapter` used to ask an agent to confirm each verdict file existed.
On the live series `voice_drift.py` and `lexicon_check.py` ran in 1 of 12
rounds and nothing noticed — `inspector-voice` recorded "No voice_drift.py
evidence was supplied for this round" and made its blocking call blind, eleven
times. These tests pin the deterministic replacement: named lines, a nonzero
exit, and the two absences that are legitimate (no authored lexicon; an
inspector outside the active genre's roster).
"""
import pytest

from scripts import review_completeness

ROSTER_FILES = {
    "continuity": "continuity-drift.md",
    "fairplay": "fairplay-planting.md",
    "structure": "structure-tension.md",
    "voice": "character-voice.md",
    "ai-prose": "ai-prose-taste-flags.md",
}

ALL_FILES = tuple(ROSTER_FILES.values()) + (
    "developmental-edit.md", "voice-drift.md", "lexicon-fluency.md",
)


def _series_with_reviews(tmp_path, *, present, lexicon=True, book="01", chapter="05"):
    """A minimal cozy series root with a reviews dir holding `present`.

    `present` is "all", or an iterable of verdict filenames.
    """
    root = tmp_path / "series-fixture"
    (root / ".penny").mkdir(parents=True)
    (root / "series.yaml").write_text("genre: cozy-mystery\n", encoding="utf-8")

    if lexicon:
        lex = root / "config" / "setting-pack"
        lex.mkdir(parents=True)
        (lex / "lexicon.yaml").write_text(
            "terms:\n  - term: brack\n    narration_ok_from_stage: SETTLING\n"
            "    auto_detectable: true\n", encoding="utf-8")

    reviews = root / "output" / f"book-{book}" / "chapters" / f"ch-{chapter}.reviews"
    reviews.mkdir(parents=True)
    names = ALL_FILES if present == "all" else tuple(present)
    for name in names:
        (reviews / name).write_text(
            "---\nproducer: x\nkind: inspector\nschema: penny-verdict/1\n---\nok\n",
            encoding="utf-8")
    return root


def _reviews(root, book="01", chapter="05"):
    return root / "output" / f"book-{book}" / "chapters" / f"ch-{chapter}.reviews"


def test_reports_every_missing_file_by_name(tmp_path):
    root = _series_with_reviews(tmp_path, present=[])
    rc, lines = review_completeness.check("01", "05", repo_root=root)
    assert rc == 1
    joined = "\n".join(lines)
    assert "missing-voice-drift" in joined
    assert "missing-lexicon-fluency" in joined
    assert "missing-developmental-read" in joined


def test_clean_when_everything_ran(tmp_path):
    root = _series_with_reviews(tmp_path, present="all")
    rc, lines = review_completeness.check("01", "05", repo_root=root)
    assert rc == 0, lines


def test_absent_lexicon_yaml_is_a_note_not_a_finding(tmp_path):
    """The engine ships no lexicon; a series without one is legitimate, and
    lexicon_check exits rather than writing (spec 3a.2)."""
    root = _series_with_reviews(tmp_path, present="all", lexicon=False)
    (_reviews(root) / "lexicon-fluency.md").unlink()

    rc, lines = review_completeness.check("01", "05", repo_root=root)
    detail = review_completeness.check_detail("01", "05", repo_root=root)

    assert rc == 0
    assert not any("missing-lexicon-fluency" in l for l in lines)
    # Observed as a NOTE, not merely as "some line mentioning lexicon" — the
    # finding string contains the word too, so a substring match alone would
    # pass whichever channel the line came out on.
    assert detail["findings"] == []
    assert any("lexicon" in n.lower() for n in detail["notes"]), \
        "the inert check must be named"


def test_missing_voice_drift_alone_is_a_finding(tmp_path):
    """The exact live-series failure: every agent verdict present, both
    evidence checkers skipped, gate computed anyway."""
    root = _series_with_reviews(tmp_path, present="all")
    (_reviews(root) / "voice-drift.md").unlink()

    rc, lines = review_completeness.check("01", "05", repo_root=root)
    detail = review_completeness.check_detail("01", "05", repo_root=root)

    assert rc == 1
    assert any("missing-voice-drift" in l for l in lines)
    assert any("missing-voice-drift" in f for f in detail["findings"])


def test_missing_lexicon_verdict_with_an_authored_lexicon_is_a_finding(tmp_path):
    """The converse of the note: the series HAS a lexicon, so lexicon_check
    would have written a verdict — its absence is a skipped dispatch."""
    root = _series_with_reviews(tmp_path, present="all", lexicon=True)
    (_reviews(root) / "lexicon-fluency.md").unlink()

    detail = review_completeness.check_detail("01", "05", repo_root=root)

    assert any("missing-lexicon-fluency" in f for f in detail["findings"])
    assert not any("lexicon" in n.lower() for n in detail["notes"])


def test_missing_inspector_verdict_names_the_inspector_and_the_file(tmp_path):
    root = _series_with_reviews(tmp_path, present="all")
    (_reviews(root) / "character-voice.md").unlink()

    detail = review_completeness.check_detail("01", "05", repo_root=root)

    hits = [f for f in detail["findings"] if f.startswith("missing-inspector-verdict")]
    assert len(hits) == 1, detail
    assert "character-voice.md" in hits[0]
    assert "voice" in hits[0]


def test_expected_inspectors_come_from_the_genre_roster(tmp_path, monkeypatch):
    """The genre chooses WHICH inspectors run: a fixed list here would report a
    cozy-only inspector missing from a thriller panel."""
    monkeypatch.setattr(review_completeness.penny_genre, "inspectors",
                        lambda root=None: ["continuity"])
    root = _series_with_reviews(tmp_path, present=[
        "continuity-drift.md", "developmental-edit.md", "voice-drift.md",
        "lexicon-fluency.md"])

    rc, lines = review_completeness.check("01", "05", repo_root=root)

    assert rc == 0, lines
    assert not any("missing-inspector-verdict" in l for l in lines)


def test_an_inspector_the_engine_table_does_not_map_is_a_note(tmp_path, monkeypatch):
    """A genre may name an inspector this engine has no verdict-file row for.
    The check cannot verify what it cannot name — so it says so out loud rather
    than claiming coverage it does not have."""
    monkeypatch.setattr(review_completeness.penny_genre, "inspectors",
                        lambda root=None: ["continuity", "pace"])
    root = _series_with_reviews(tmp_path, present=[
        "continuity-drift.md", "developmental-edit.md", "voice-drift.md",
        "lexicon-fluency.md"])

    detail = review_completeness.check_detail("01", "05", repo_root=root)

    assert detail["findings"] == []
    assert any("unmapped-inspector" in n and "pace" in n for n in detail["notes"])


def test_missing_reviews_dir_reports_every_expected_file(tmp_path):
    root = _series_with_reviews(tmp_path, present=[])
    import shutil
    shutil.rmtree(_reviews(root))

    rc, lines = review_completeness.check("01", "05", repo_root=root)

    assert rc == 1
    joined = "\n".join(lines)
    for verdict in ROSTER_FILES.values():
        assert verdict in joined


def test_chapter_and_book_numbers_are_zero_padded(tmp_path):
    root = _series_with_reviews(tmp_path, present="all", book="01", chapter="05")
    rc, lines = review_completeness.check(1, 5, repo_root=root)
    assert rc == 0, lines


def test_cli_exit_codes(tmp_path, monkeypatch, capsys):
    root = _series_with_reviews(tmp_path, present="all")
    monkeypatch.chdir(root)

    assert review_completeness.main(["01", "05"]) == 0
    assert "OK" in capsys.readouterr().out

    (_reviews(root) / "voice-drift.md").unlink()
    assert review_completeness.main(["01", "05"]) == 1
    assert "missing-voice-drift" in capsys.readouterr().out

    assert review_completeness.main([]) == 2
    assert review_completeness.main(["01", "05", "extra"]) == 2


def test_runbook_calls_the_script_and_keeps_the_reasoning():
    from pathlib import Path
    text = Path("commands/review-chapter.md").read_text(encoding="utf-8")
    assert "scripts/review_completeness.py" in text
    assert "$book $chapter" in text
    # The instruction to LOOK is what is replaced; the reasoning stays.
    assert "silently failed" in text
    # And the check must be wired ahead of the gate, not after it.
    assert text.index("review_completeness.py") < text.index("review_gate.py")


@pytest.mark.parametrize("name,verdict", sorted(ROSTER_FILES.items()))
def test_static_table_matches_the_script(name, verdict):
    assert review_completeness.VERDICT_FILES[name] == verdict
