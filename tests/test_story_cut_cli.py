import yaml

from scripts import story_cut


def _series(tmp_path, monkeypatch):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-02").mkdir(parents=True)
    (tmp_path / "series" / "whodunit").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "series-guardrails.md").write_text(
        "Do not name the culprit early.\n", encoding="utf-8")
    (tmp_path / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-altered +q-clear\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    (tmp_path / "input" / "book-02" / "cut-plan.md").write_text(
        "## Chapter 01 — One\n\n- **Beats:** 1\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n\n"
        "## Chapter 02 — Two\n\n- **Beats:** 2\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n", encoding="utf-8")
    (tmp_path / "series" / "whodunit" / "book-02.yaml").write_text(
        "reveal_chapter: 2\nclue_schedule:\n  - id: c-altered\n    chapter: 99\n"
        "    description: the handover appointment, changed\n", encoding="utf-8")
    monkeypatch.setattr(story_cut.penny_paths, "series_root", lambda *a, **k: tmp_path)
    monkeypatch.setattr(story_cut, "_job_ids_and_titles",
                        lambda: (["establish-protected-world"],
                                 {"establish-protected-world": "Establish the Protected World"}))
    return tmp_path


def test_clean_cut_writes_the_outline_and_exits_zero(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    text = (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8")
    assert "## Chapter 01 — One" in text
    assert "cut_output_sha256:" in text


def test_cut_writes_resolved_chapter_numbers_back_into_the_ledger(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    story_cut.main(["02"])
    led = yaml.safe_load((root / "series" / "whodunit" / "book-02.yaml").read_text())
    assert led["clue_schedule"][0]["chapter"] == 2


def test_findings_exit_one_and_write_nothing(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    plan = root / "input" / "book-02" / "cut-plan.md"
    plan.write_text(plan.read_text().replace("- **Beats:** 2", "- **Beats:** 1"),
                    encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert not (root / "input" / "book-02" / "outline.md").exists()
    assert "beats-without-chapter" in capsys.readouterr().out


def test_usage_error_exits_two(capsys):
    assert story_cut.main([]) == 2


def test_second_cut_refuses_after_a_hand_edit(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    outline = root / "input" / "book-02" / "outline.md"
    outline.write_text(outline.read_text() + "\nhand edit\n", encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert "outline-modified-since-cut" in capsys.readouterr().out


def test_second_cut_is_allowed_when_the_outline_is_untouched(tmp_path, monkeypatch):
    _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    assert story_cut.main(["02"]) == 0


# --- Critical fix: the ledger write-back must never round-trip through
# yaml.safe_dump — a hand-authored file's comments, bare scalars, and
# quoting all have to survive. `_rewrite_clue_chapters` is a pure text
# line-walk; these tests exercise it directly so a regression to
# yaml.safe_dump (or a broken indent/scan rule) fails loudly. ---

LEDGER_WITH_QUIRKS = (
    "reveal_chapter: 2\n"
    "# a showrunner note the yaml round trip must not eat\n"
    "spoiler_locked: no\n"
    "clue_schedule:\n"
    "  - id: c-altered\n"
    "    chapter: 99  # scheduled provisionally\n"
    '    description: "the handover appointment, changed"\n'
    "  - id: c-untouched\n"
    "    chapter: 42\n"
    "    description: a clue no beat plants\n"
    "  - id: c-new\n"
    "    description: a clue with no chapter key yet\n"
)


def test_rewrite_preserves_comments_bare_scalars_and_quoting():
    out = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert "# a showrunner note the yaml round trip must not eat" in out
    assert "spoiler_locked: no\n" in out
    assert '"the handover appointment, changed"' in out


def test_rewrite_changes_only_the_intended_chapter_lines():
    out = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    before = LEDGER_WITH_QUIRKS.splitlines()
    after = out.splitlines()
    assert len(before) == len(after)
    diffs = [(b, a) for b, a in zip(before, after) if b != a]
    assert diffs == [
        ("    chapter: 99  # scheduled provisionally",
         "    chapter: 2  # scheduled provisionally"),
    ]


def test_rewrite_inserts_a_missing_chapter_key_at_the_right_indentation():
    out = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-new": 5})
    lines = out.splitlines()
    idx = lines.index("  - id: c-new")
    assert lines[idx + 1] == "    chapter: 5"
    # the entry's original (chapter-less) description line still follows
    assert lines[idx + 2] == "    description: a clue with no chapter key yet"


def test_rewrite_leaves_an_unplanted_clues_chapter_untouched():
    out = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert "    chapter: 42\n" in out
    assert "c-untouched" in out


def test_rewrite_is_a_no_op_with_no_updates():
    assert story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {}) == LEDGER_WITH_QUIRKS


def test_cut_survives_ledger_quirks_end_to_end(tmp_path, monkeypatch):
    """The full CLI path, not just the pure helper: a ledger with a comment,
    a bare `no`, and a quoted string comes out with all three intact after a
    real cut, and only the tagged clue's chapter number changes."""
    root = _series(tmp_path, monkeypatch)
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    ledger_p.write_text(
        "reveal_chapter: 2\n"
        "# a showrunner note the yaml round trip must not eat\n"
        "spoiler_locked: no\n"
        "clue_schedule:\n"
        "  - id: c-altered\n"
        "    chapter: 99  # scheduled provisionally\n"
        '    description: "the handover appointment, changed"\n',
        encoding="utf-8")
    assert story_cut.main(["02"]) == 0
    text = ledger_p.read_text(encoding="utf-8")
    assert "# a showrunner note the yaml round trip must not eat" in text
    assert "spoiler_locked: no\n" in text
    assert '"the handover appointment, changed"' in text
    assert "chapter: 2  # scheduled provisionally" in text


# --- Important fix: a missing reveal_chapter must be a named blocking
# finding, not a silent 0 baked into vacuous guardrail prose. ---

def test_missing_reveal_chapter_blocks_and_writes_nothing(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    ledger_p.write_text(
        "clue_schedule:\n  - id: c-altered\n    chapter: 99\n"
        "    description: the handover appointment, changed\n", encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert not (root / "input" / "book-02" / "outline.md").exists()
    assert "missing-reveal-chapter" in capsys.readouterr().out
    # nothing in the ledger changed either — the write-nothing rule is total
    assert ledger_p.read_text(encoding="utf-8") == (
        "clue_schedule:\n  - id: c-altered\n    chapter: 99\n"
        "    description: the handover appointment, changed\n")


# --- Important fix: at least one test must NOT patch _job_ids_and_titles,
# so a broken penny_genre.macro_structure() -> outline_views.parse_jobs
# wiring inside this module can't hide behind the other tests' patch. Follows
# tests/test_penny_genre.py's pattern of declaring the real, shipped
# cozy-mystery genre pack via series.yaml rather than fabricating a fake
# plugin root (macro_structure()'s genre_dir always resolves under the real
# plugin_root(), so a fake genre pack can't live under tmp_path anyway). ---

def _series_with_real_genre(tmp_path, monkeypatch):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-02").mkdir(parents=True)
    (tmp_path / "series" / "whodunit").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "series-guardrails.md").write_text(
        "Do not name the culprit early.\n", encoding="utf-8")
    (tmp_path / "series.yaml").write_text("genre: cozy-mystery\n", encoding="utf-8")
    (tmp_path / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-altered +q-clear\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    (tmp_path / "input" / "book-02" / "cut-plan.md").write_text(
        "## Chapter 01 — One\n\n- **Beats:** 1\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n\n"
        "## Chapter 02 — Two\n\n- **Beats:** 2\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n", encoding="utf-8")
    (tmp_path / "series" / "whodunit" / "book-02.yaml").write_text(
        "reveal_chapter: 2\nclue_schedule:\n  - id: c-altered\n    chapter: 99\n"
        "    description: the handover appointment, changed\n", encoding="utf-8")
    # cwd-based resolution only: penny_genre.macro_structure() and
    # penny_paths.series_root() both resolve relative to the process cwd, not
    # to any monkeypatched accessor, so this test chdirs for real rather than
    # patching series_root — that's what makes the genre lookup itself real.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_job_ids_resolve_through_the_real_genre_lookup(tmp_path, monkeypatch):
    root = _series_with_real_genre(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    text = (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8")
    # "establish-protected-world" is job 1 of the real, shipped cozy-mystery
    # macro-structure — its title only appears in the outline if
    # _job_ids_and_titles() genuinely resolved through penny_genre and
    # outline_views.parse_jobs, not through the shared fixture's patch.
    assert "Establish the Protected World" in text
