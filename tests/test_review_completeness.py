"""The review panel's completeness check, moved out of runbook prose.

`/review-chapter` used to ask an agent to confirm each verdict file existed.
On the live series `voice_drift.py` and `lexicon_check.py` ran in 1 of 12
rounds and nothing noticed — `inspector-voice` recorded "No voice_drift.py
evidence was supplied for this round" and made its blocking call blind, eleven
times. These tests pin the deterministic replacement: named lines, a nonzero
exit, and the two absences that are legitimate (no authored lexicon; an
inspector outside the active genre's roster).
"""
import re
from pathlib import Path

from scripts import review_completeness

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "commands" / "review-chapter.md"

# Deliberately NOT a second copy of the table: a duplicate declared here would
# agree with the script by construction and keep agreeing if both drifted. The
# expected set is read from the script, and the script's table is pinned against
# the runbook's — the one place outside it that names these files.
ALL_FILES = tuple(review_completeness.VERDICT_FILES.values()) + (
    "developmental-edit.md", "voice-drift.md", "lexicon-fluency.md",
)


def _runbook_table():
    """{inspector: verdict file} parsed from the runbook's static table.

    `cells[3]` is the `verdict file` column. Today it is byte-identical to the
    `rubric` column in all five rows, so a wrong index would read the same
    strings and this helper would look right while checking nothing — worth
    re-deriving from the table's header if either column ever moves.
    """
    rows = {}
    for line in RUNBOOK.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("inspector", "---") or set(cells[0]) == {"-"}:
            continue
        if not re.fullmatch(r"[a-z-]+", cells[0]):
            continue
        rows[cells[0]] = cells[3]
    return rows


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


def test_both_evidence_checkers_skipped_is_the_live_failure(tmp_path):
    """The scenario itself: every agent verdict present, BOTH free checkers
    skipped, gate computed anyway — eleven times of twelve on the live series.
    Covered as a union by the two single-removal tests above; it happened as a
    pair, so it is pinned as a pair."""
    root = _series_with_reviews(tmp_path, present="all")
    (_reviews(root) / "voice-drift.md").unlink()
    (_reviews(root) / "lexicon-fluency.md").unlink()

    rc, lines = review_completeness.check("01", "05", repo_root=root)
    detail = review_completeness.check_detail("01", "05", repo_root=root)

    assert rc == 1
    assert len(detail["findings"]) == 2, detail
    assert any("missing-voice-drift" in f for f in detail["findings"])
    assert any("missing-lexicon-fluency" in f for f in detail["findings"])
    # ...and nothing else is blamed: the agent panel was complete.
    assert not any("missing-inspector-verdict" in f for f in detail["findings"])
    assert not any("missing-developmental-read" in f for f in detail["findings"])


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
    for verdict in review_completeness.VERDICT_FILES.values():
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


def test_runbook_table_is_parseable_at_all():
    """The pin below is only worth anything if the parse found the table — a
    renamed column or a reformatted row would otherwise silently compare {} to
    {} and pass."""
    assert len(_runbook_table()) == 5, _runbook_table()


def test_verdict_files_agree_with_the_runbook_table():
    """The script's inspector -> verdict-file table and the runbook's are the
    same table written twice; the dispatch follows the runbook, the check
    follows the script, and a drift between them means the check looks for a
    file nobody was told to write."""
    assert review_completeness.VERDICT_FILES == _runbook_table()


def test_each_inspector_agent_names_the_verdict_file_this_check_expects():
    """The agent definitions and the check must name one filename each.

    All five said `ch-MM.reviews/inspector-<name>.md` while the runbook's table,
    this script and the live series used the rubric names. That drift was inert
    while the agents followed the runbook's dispatch — but an agent that follows
    its own definition now writes a file nobody looks for, and the completeness
    check turns a silent mismatch into `missing-inspector-verdict` and a hard
    stop before the gate.
    """
    for name, verdict in review_completeness.VERDICT_FILES.items():
        text = (ROOT / "agents" / f"inspector-{name}.md").read_text(encoding="utf-8")
        assert f"ch-MM.reviews/{verdict}" in text, (
            f"agents/inspector-{name}.md does not write {verdict}")
        assert f"reviews/inspector-{name}.md" not in text, (
            f"agents/inspector-{name}.md still names its own verdict file")
