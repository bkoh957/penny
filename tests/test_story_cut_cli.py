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
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert missing == []
    assert "# a showrunner note the yaml round trip must not eat" in out
    assert "spoiler_locked: no\n" in out
    assert '"the handover appointment, changed"' in out


def test_rewrite_changes_only_the_intended_chapter_lines():
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert missing == []
    before = LEDGER_WITH_QUIRKS.splitlines()
    after = out.splitlines()
    assert len(before) == len(after)
    diffs = [(b, a) for b, a in zip(before, after) if b != a]
    assert diffs == [
        ("    chapter: 99  # scheduled provisionally",
         "    chapter: 2  # scheduled provisionally"),
    ]


def test_rewrite_inserts_a_missing_chapter_key_at_the_right_indentation():
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-new": 5})
    assert missing == []
    lines = out.splitlines()
    idx = lines.index("  - id: c-new")
    assert lines[idx + 1] == "    chapter: 5"
    # the entry's original (chapter-less) description line still follows
    assert lines[idx + 2] == "    description: a clue with no chapter key yet"


def test_rewrite_leaves_an_unplanted_clues_chapter_untouched():
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert missing == []
    assert "    chapter: 42\n" in out
    assert "c-untouched" in out


def test_rewrite_is_a_no_op_with_no_updates():
    assert story_cut._rewrite_clue_chapters(LEDGER_WITH_QUIRKS, {}) == (
        LEDGER_WITH_QUIRKS, [])


def test_rewrite_c_vase_and_c_vase_2_do_not_cross_match():
    """A prefix collision (`c-vase` is a prefix of `c-vase-2`) must resolve by
    exact id, not substring — updating one must never touch the other."""
    text = ("clue_schedule:\n"
            "  - id: c-vase\n    chapter: 1\n"
            "  - id: c-vase-2\n    chapter: 9\n")
    out, missing = story_cut._rewrite_clue_chapters(text, {"c-vase": 5})
    assert missing == []
    lines = out.splitlines()
    assert lines[lines.index("  - id: c-vase") + 1] == "    chapter: 5"
    assert lines[lines.index("  - id: c-vase-2") + 1] == "    chapter: 9"


def test_rewrite_a_chapter_key_outside_clue_schedule_is_untouched():
    text = ("chapter: 1\n"
            "clue_schedule:\n"
            "  - id: c-altered\n    chapter: 99\n")
    out, missing = story_cut._rewrite_clue_chapters(text, {"c-altered": 2})
    assert missing == []
    assert out.splitlines()[0] == "chapter: 1"


def test_rewrite_never_treats_an_id_inside_a_quoted_description_as_an_id():
    text = ('clue_schedule:\n'
            '  - id: c-altered\n'
            '    description: "not id: c-fake, just prose"\n'
            '    chapter: 99\n')
    out, missing = story_cut._rewrite_clue_chapters(text, {"c-fake": 3})
    # c-fake never appears as a real `id:` key anywhere, so it's unlocatable —
    # reported missing rather than silently matched against the description.
    assert missing == ["c-fake"]
    assert '"not id: c-fake, just prose"' in out


def test_rewrite_handles_extra_spaces_after_the_dash():
    text = "clue_schedule:\n  -    id: c-altered\n    chapter: 99\n"
    out, missing = story_cut._rewrite_clue_chapters(text, {"c-altered": 2})
    assert missing == []
    assert "chapter: 2" in out


# --- Important fix (round 2): YAML mappings are unordered, so `id:` may
# come AFTER `chapter:` in an entry — the old `- id: <cid>` line-shape match
# silently skipped any such entry. Fixed by walking each list item's whole
# SPAN and finding `id:`/`chapter:` wherever they land within it. ---

LEDGER_REORDERED = (
    "reveal_chapter: 2\n"
    "clue_schedule:\n"
    "  - chapter: 99\n"
    "    id: c-altered\n"
    "    description: the handover appointment, changed\n"
    "  - description: another clue entirely\n"
    "    chapter: 7\n"
    "    id: c-other\n"
)


def test_rewrite_updates_an_entry_whose_chapter_precedes_its_id():
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_REORDERED, {"c-altered": 2})
    assert missing == []
    lines = out.splitlines()
    idx = lines.index("    id: c-altered")
    assert lines[idx - 1] == "  - chapter: 2"


def test_rewrite_updates_an_entry_ordered_description_chapter_id():
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_REORDERED, {"c-other": 3})
    assert missing == []
    lines = out.splitlines()
    idx = lines.index("    id: c-other")
    assert lines[idx - 1] == "    chapter: 3"


def test_rewrite_reordered_shape_byte_identity_outside_changed_lines():
    out, missing = story_cut._rewrite_clue_chapters(LEDGER_REORDERED, {"c-altered": 2})
    assert missing == []
    before = LEDGER_REORDERED.splitlines()
    after = out.splitlines()
    assert len(before) == len(after)
    diffs = [(b, a) for b, a in zip(before, after) if b != a]
    assert diffs == [("  - chapter: 99", "  - chapter: 2")]


def test_id_loaded_but_not_locatable_in_text_blocks_and_writes_nothing(
        tmp_path, monkeypatch, capsys):
    """A dropped update must never be silent: if `_ledger`'s yaml.safe_load
    sees a clue id that the text-level walk can't find (here, a flow-style
    `{id: ..., chapter: ...}` mapping our line-walk doesn't parse), that must
    be a named blocking finding, and nothing gets written — not the outline,
    not the ledger."""
    root = _series(tmp_path, monkeypatch)
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    original = ('reveal_chapter: 2\nclue_schedule:\n'
                '  - {id: c-altered, chapter: 99, description: "x"}\n')
    ledger_p.write_text(original, encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert not (root / "input" / "book-02" / "outline.md").exists()
    out = capsys.readouterr().out
    assert "clue-not-found-in-ledger-text" in out
    assert "c-altered" in out
    assert ledger_p.read_text(encoding="utf-8") == original


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
