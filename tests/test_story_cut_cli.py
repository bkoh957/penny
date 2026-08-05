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
        "reveal_chapter: 2\nclue_schedule:\n  - id: c-altered\n    plant_chapter: 99\n"
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
    assert led["clue_schedule"][0]["plant_chapter"] == 2


# --- FINAL REVIEW, Critical 1: the write-back targeted `chapter:`, a key NO
# consumer reads. `penny_whodunit._plant_chapter` (and through it
# `clues_by_chapter` -> packet_assemble + tension_check's overloaded-chapter),
# `fairplay_check`, and `lmstudio_draft_chapter` ALL read `plant_chapter`. The
# cut inserted `chapter: 2` above a stale `plant_chapter: 99`, so the chapter
# block named a clue the packet reported as "None" and fairplay blocked the
# lock. ---

def test_the_written_key_is_the_one_every_consumer_reads(tmp_path, monkeypatch):
    from scripts import penny_whodunit
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    # the real consumer entry point, not a re-read of the raw yaml
    assert penny_whodunit.clues_by_chapter(ledger_p) == {2: ["c-altered"]}
    # and no orphan `chapter:` key was left behind beside it
    assert "\n    chapter:" not in ledger_p.read_text(encoding="utf-8")


# --- FINAL REVIEW, Critical 1 (second half): `_ledger` read only
# `clue_schedule`, so a `!rh-…` tag was refused `unknown-clue` even though
# `clues_by_chapter` and `packet_assemble` both schedule `red_herrings` too. ---

def _series_with_red_herring(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-altered +q-clear !rh-decoy\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    (root / "series" / "whodunit" / "book-02.yaml").write_text(
        "reveal_chapter: 2\n"
        "clue_schedule:\n  - id: c-altered\n    plant_chapter: 99\n"
        "    description: the handover appointment, changed\n"
        "red_herrings:\n  - id: rh-decoy\n    plant_chapter: 77\n"
        "    misleads_toward: someone-else\n", encoding="utf-8")
    return root


def test_a_red_herring_tag_is_known_and_written_back(tmp_path, monkeypatch, capsys):
    from scripts import penny_whodunit
    root = _series_with_red_herring(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0, capsys.readouterr().out
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    assert penny_whodunit.clues_by_chapter(ledger_p) == {2: ["c-altered", "rh-decoy"]}


def test_a_red_herring_renders_from_misleads_toward_in_the_chapter_block(
        tmp_path, monkeypatch):
    root = _series_with_red_herring(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    text = (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8")
    assert "- [rh-decoy] someone-else" in text


# --- FINAL REVIEW, Important 6: the emitted frontmatter omitted `book:` and
# `total_chapters:`, so `book_status._total_chapters_with_reason` had nothing
# to read and blanked every per-chapter row for every cut book — and
# `tension_check`'s chapter-coverage silently fell back to `len(chapters)`,
# where a gap can never be seen. The cut knows the count. ---

def test_emitted_frontmatter_carries_book_and_total_chapters(tmp_path, monkeypatch):
    from scripts.penny_meta import parse_frontmatter
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    fm = parse_frontmatter(
        (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8"))
    assert fm["book"] == "02"
    assert fm["total_chapters"] == "2"


def test_book_status_reads_the_cut_outlines_chapter_count(tmp_path, monkeypatch):
    # The actual consumer, not a re-read of the frontmatter we just wrote.
    from scripts import book_status
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    total, reason = book_status._total_chapters_with_reason("02", root)
    assert total == 2, reason


# --- FINAL REVIEW, Important 5: `plot_stage`'s cut stage demands
# `built_from_story` AND `built_from_book-NN`, but the cut wrote only the
# first and no runbook step stamped the second — so `plot_stage status`
# reported `cut: stale (built_from_book-NN unstamped)` immediately after a
# clean cut and `next:` pinned to `cut` forever. Exercised through a REAL cut,
# never a hand-stamp. ---

def test_plot_stage_reports_cut_done_right_after_a_real_cut(tmp_path, monkeypatch):
    from scripts import plot_stage
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    rows = dict((name, (state, detail))
                for name, state, detail in plot_stage.stage_status("02", repo_root=root))
    assert rows["cut"][0] == "done", rows["cut"][1]


def test_the_cut_stamp_describes_the_ledger_the_cut_left_behind(tmp_path, monkeypatch):
    # The cut REWRITES the ledger (plant_chapter resolution), so a fingerprint
    # taken before that write would make the stage stale the instant it
    # finished — the same bug wearing a different hat.
    from scripts import plot_stage
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    assert "plant_chapter: 2" in ledger_p.read_text(encoding="utf-8")
    fm = story_cut.parse_frontmatter(
        (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8"))
    assert fm["built_from_book-02"] == plot_stage._upstream_sha(ledger_p)


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
# quoting all have to survive. `_rewrite_plant_chapters` is a pure text
# line-walk; these tests exercise it directly so a regression to
# yaml.safe_dump (or a broken indent/scan rule) fails loudly. ---

LEDGER_WITH_QUIRKS = (
    "reveal_chapter: 2\n"
    "# a showrunner note the yaml round trip must not eat\n"
    "spoiler_locked: no\n"
    "clue_schedule:\n"
    "  - id: c-altered\n"
    "    plant_chapter: 99  # scheduled provisionally\n"
    '    description: "the handover appointment, changed"\n'
    "  - id: c-untouched\n"
    "    plant_chapter: 42\n"
    "    description: a clue no beat plants\n"
    "  - id: c-new\n"
    "    description: a clue with no chapter key yet\n"
)


def test_rewrite_preserves_comments_bare_scalars_and_quoting():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert missing == []
    assert "# a showrunner note the yaml round trip must not eat" in out
    assert "spoiler_locked: no\n" in out
    assert '"the handover appointment, changed"' in out


def test_rewrite_changes_only_the_intended_chapter_lines():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert missing == []
    before = LEDGER_WITH_QUIRKS.splitlines()
    after = out.splitlines()
    assert len(before) == len(after)
    diffs = [(b, a) for b, a in zip(before, after) if b != a]
    assert diffs == [
        ("    plant_chapter: 99  # scheduled provisionally",
         "    plant_chapter: 2  # scheduled provisionally"),
    ]


def test_rewrite_inserts_a_missing_chapter_key_at_the_right_indentation():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_WITH_QUIRKS, {"c-new": 5})
    assert missing == []
    lines = out.splitlines()
    idx = lines.index("  - id: c-new")
    assert lines[idx + 1] == "    plant_chapter: 5"
    # the entry's original (chapter-less) description line still follows
    assert lines[idx + 2] == "    description: a clue with no chapter key yet"


def test_rewrite_leaves_an_unplanted_clues_chapter_untouched():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_WITH_QUIRKS, {"c-altered": 2})
    assert missing == []
    assert "    plant_chapter: 42\n" in out
    assert "c-untouched" in out


def test_rewrite_is_a_no_op_with_no_updates():
    assert story_cut._rewrite_plant_chapters(LEDGER_WITH_QUIRKS, {}) == (
        LEDGER_WITH_QUIRKS, [])


def test_rewrite_c_vase_and_c_vase_2_do_not_cross_match():
    """A prefix collision (`c-vase` is a prefix of `c-vase-2`) must resolve by
    exact id, not substring — updating one must never touch the other."""
    text = ("clue_schedule:\n"
            "  - id: c-vase\n    plant_chapter: 1\n"
            "  - id: c-vase-2\n    plant_chapter: 9\n")
    out, missing = story_cut._rewrite_plant_chapters(text, {"c-vase": 5})
    assert missing == []
    lines = out.splitlines()
    assert lines[lines.index("  - id: c-vase") + 1] == "    plant_chapter: 5"
    assert lines[lines.index("  - id: c-vase-2") + 1] == "    plant_chapter: 9"


def test_rewrite_a_chapter_key_outside_clue_schedule_is_untouched():
    text = ("plant_chapter: 1\n"
            "clue_schedule:\n"
            "  - id: c-altered\n    plant_chapter: 99\n")
    out, missing = story_cut._rewrite_plant_chapters(text, {"c-altered": 2})
    assert missing == []
    assert out.splitlines()[0] == "plant_chapter: 1"


def test_rewrite_never_treats_an_id_inside_a_quoted_description_as_an_id():
    text = ('clue_schedule:\n'
            '  - id: c-altered\n'
            '    description: "not id: c-fake, just prose"\n'
            '    plant_chapter: 99\n')
    out, missing = story_cut._rewrite_plant_chapters(text, {"c-fake": 3})
    # c-fake never appears as a real `id:` key anywhere, so it's unlocatable —
    # reported missing rather than silently matched against the description.
    assert missing == ["c-fake"]
    assert '"not id: c-fake, just prose"' in out


def test_rewrite_handles_extra_spaces_after_the_dash():
    text = "clue_schedule:\n  -    id: c-altered\n    plant_chapter: 99\n"
    out, missing = story_cut._rewrite_plant_chapters(text, {"c-altered": 2})
    assert missing == []
    assert "plant_chapter: 2" in out


# --- Important fix (round 2): YAML mappings are unordered, so `id:` may
# come AFTER `plant_chapter:` in an entry — the old `- id: <cid>` line-shape match
# silently skipped any such entry. Fixed by walking each list item's whole
# SPAN and finding `id:`/`plant_chapter:` wherever they land within it. ---

LEDGER_REORDERED = (
    "reveal_chapter: 2\n"
    "clue_schedule:\n"
    "  - plant_chapter: 99\n"
    "    id: c-altered\n"
    "    description: the handover appointment, changed\n"
    "  - description: another clue entirely\n"
    "    plant_chapter: 7\n"
    "    id: c-other\n"
)


def test_rewrite_updates_an_entry_whose_chapter_precedes_its_id():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_REORDERED, {"c-altered": 2})
    assert missing == []
    lines = out.splitlines()
    idx = lines.index("    id: c-altered")
    assert lines[idx - 1] == "  - plant_chapter: 2"


def test_rewrite_updates_an_entry_ordered_description_chapter_id():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_REORDERED, {"c-other": 3})
    assert missing == []
    lines = out.splitlines()
    idx = lines.index("    id: c-other")
    assert lines[idx - 1] == "    plant_chapter: 3"


def test_rewrite_reordered_shape_byte_identity_outside_changed_lines():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_REORDERED, {"c-altered": 2})
    assert missing == []
    before = LEDGER_REORDERED.splitlines()
    after = out.splitlines()
    assert len(before) == len(after)
    diffs = [(b, a) for b, a in zip(before, after) if b != a]
    assert diffs == [("  - plant_chapter: 99", "  - plant_chapter: 2")]


def test_id_loaded_but_not_locatable_in_text_blocks_and_writes_nothing(
        tmp_path, monkeypatch, capsys):
    """A dropped update must never be silent: if `_ledger`'s yaml.safe_load
    sees a clue id that the text-level walk can't find — here the whole
    collection is an inline flow SEQUENCE on the heading line, so there is no
    `clue_schedule:` block for the walk to enter — that must be a named
    blocking finding, and nothing gets written: not the outline, not the
    ledger."""
    root = _series(tmp_path, monkeypatch)
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    original = ('reveal_chapter: 2\n'
                'clue_schedule: [{id: c-altered, plant_chapter: 99}]\n')
    ledger_p.write_text(original, encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert not (root / "input" / "book-02" / "outline.md").exists()
    out = capsys.readouterr().out
    assert "clue-not-found-in-ledger-text" in out
    assert "c-altered" in out
    assert ledger_p.read_text(encoding="utf-8") == original


# --- FINAL REVIEW, Important 4: the line walk could not see a clue written as
# an inline flow mapping — `  - { id: clue-x, plant_chapter: 5, … }` — which is
# the shape tests/fixtures/cozy/series/whodunit/book-01.yaml uses throughout.
# Every clue in that style was refused `clue-not-found-in-ledger-text`: loud,
# but unusable against the repo's own fixtures. ---

LEDGER_FLOW_MAPPING = (
    "reveal_chapter: 2\n"
    "clue_schedule:\n"
    "  - { id: c-altered, plant_chapter: 99, pays_off_chapter: 20, necessary: true }\n"
    "  - { id: c-untouched, plant_chapter: 42, necessary: false }\n"
    "red_herrings:\n"
    '  - { id: rh-one, plant_chapter: 9, misleads_toward: "someone", must_not_cheat: true }\n'
    "  - { id: rh-nokey, misleads_toward: nobody }\n"
)


def test_rewrite_updates_a_flow_mapping_entry_in_place():
    out, missing = story_cut._rewrite_plant_chapters(
        LEDGER_FLOW_MAPPING, {"c-altered": 3})
    assert missing == []
    before, after = LEDGER_FLOW_MAPPING.splitlines(), out.splitlines()
    assert len(before) == len(after)
    diffs = [(b, a) for b, a in zip(before, after) if b != a]
    assert diffs == [
        ("  - { id: c-altered, plant_chapter: 99, pays_off_chapter: 20, necessary: true }",
         "  - { id: c-altered, plant_chapter: 3, pays_off_chapter: 20, necessary: true }"),
    ]


def test_rewrite_updates_a_flow_mapping_red_herring():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_FLOW_MAPPING, {"rh-one": 4})
    assert missing == []
    assert ('  - { id: rh-one, plant_chapter: 4, misleads_toward: "someone", '
            'must_not_cheat: true }') in out
    # the quoting and the sibling entries survive byte-for-byte
    assert "  - { id: c-altered, plant_chapter: 99, pays_off_chapter: 20, necessary: true }" in out


def test_rewrite_adds_plant_chapter_to_a_flow_mapping_that_lacks_it():
    out, missing = story_cut._rewrite_plant_chapters(LEDGER_FLOW_MAPPING, {"rh-nokey": 6})
    assert missing == []
    assert "  - { id: rh-nokey, misleads_toward: nobody, plant_chapter: 6 }" in out
    assert yaml.safe_load(out)["red_herrings"][1]["plant_chapter"] == 6


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
        "    plant_chapter: 99  # scheduled provisionally\n"
        '    description: "the handover appointment, changed"\n',
        encoding="utf-8")
    assert story_cut.main(["02"]) == 0
    text = ledger_p.read_text(encoding="utf-8")
    assert "# a showrunner note the yaml round trip must not eat" in text
    assert "spoiler_locked: no\n" in text
    assert '"the handover appointment, changed"' in text
    assert "plant_chapter: 2  # scheduled provisionally" in text


# --- Important fix: a missing reveal_chapter must be a named blocking
# finding, not a silent 0 baked into vacuous guardrail prose. ---

def test_missing_reveal_chapter_blocks_and_writes_nothing(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    ledger_p.write_text(
        "clue_schedule:\n  - id: c-altered\n    plant_chapter: 99\n"
        "    description: the handover appointment, changed\n", encoding="utf-8")
    assert story_cut.main(["02"]) == 1
    assert not (root / "input" / "book-02" / "outline.md").exists()
    assert "missing-reveal-chapter" in capsys.readouterr().out
    # nothing in the ledger changed either — the write-nothing rule is total
    assert ledger_p.read_text(encoding="utf-8") == (
        "clue_schedule:\n  - id: c-altered\n    plant_chapter: 99\n"
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
        "reveal_chapter: 2\nclue_schedule:\n  - id: c-altered\n    plant_chapter: 99\n"
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


def test_check_exits_zero_on_a_clean_story(tmp_path, monkeypatch, capsys):
    _series(tmp_path, monkeypatch)
    assert story_cut.main(["check", "02"]) == 0
    assert "beats-without-chapter" not in capsys.readouterr().out


def test_check_suppresses_beats_without_chapter_but_not_other_findings(
        tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-unknown-id\n",
        encoding="utf-8")
    assert story_cut.main(["check", "02"]) == 1
    out = capsys.readouterr().out
    assert "unknown-clue" in out
    assert "beats-without-chapter" not in out


def test_check_prints_advisories_under_their_own_heading_and_still_exits_zero(
        tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").write_text(
        "- Plant the contradiction here.\n  @maggie\n\n"
        "- Maggie finds Lisa dead.\n  @maggie !c-altered\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    assert story_cut.main(["check", "02"]) == 0
    out = capsys.readouterr().out
    assert "Advisory" in out
    assert "directive-shaped-beat" in out


def test_check_suppresses_unknown_clue_when_the_ledger_is_missing(
        tmp_path, monkeypatch, capsys):
    """The counterplot stage writes the ledger AFTER the chapters stage
    drafts the beats — a story with clue tags and no ledger yet is the
    normal mid-workshop state, not a defect. `_check` must not report a wall
    of unknown-clue findings it cannot trust (finding 1)."""
    root = _series(tmp_path, monkeypatch)
    ledger_p = root / "series" / "whodunit" / "book-02.yaml"
    ledger_p.unlink()
    assert story_cut.main(["check", "02"]) == 0
    out = capsys.readouterr().out
    assert "unknown-clue:" not in out
    assert "unscheduled-clue:" not in out
    assert "could not run" in out
    assert str(ledger_p) in out


def test_check_still_reports_a_genuine_unknown_clue_once_the_ledger_exists(
        tmp_path, monkeypatch, capsys):
    """The suppression in the test above must not blind the check once a
    ledger IS present — a clue id that is genuinely absent from it still
    needs to be caught."""
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered.\n  @maggie !c-unknown-id\n",
        encoding="utf-8")
    assert story_cut.main(["check", "02"]) == 1
    out = capsys.readouterr().out
    assert "unknown-clue: beat 2 tags !c-unknown-id" in out
    assert "could not run" not in out


def test_check_suppresses_unknown_job_when_the_job_list_is_unresolved(
        tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    monkeypatch.setattr(story_cut, "_job_ids_and_titles", lambda: ([], {}))
    assert story_cut.main(["check", "02"]) == 0
    out = capsys.readouterr().out
    assert "unknown-job:" not in out
    assert "could not run" in out


def test_check_still_exits_one_on_a_genuine_finding_with_both_preconditions_unresolved(
        tmp_path, monkeypatch, capsys):
    """Suppressing the unknown-clue/unknown-job guesses must not swallow a
    finding of a different kind — the exit code still reflects genuine
    problems even while both preconditions are unresolvable."""
    root = _series(tmp_path, monkeypatch)
    (root / "series" / "whodunit" / "book-02.yaml").unlink()
    monkeypatch.setattr(story_cut, "_job_ids_and_titles", lambda: ([], {}))
    (root / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @Bad-Slug\n\n"
        "- The appointment was altered.\n  @maggie !c-altered +q-clear\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    assert story_cut.main(["check", "02"]) == 1
    out = capsys.readouterr().out
    assert "unknown-strand" in out
    assert "unknown-clue:" not in out
    assert "unknown-job:" not in out


def test_check_needs_no_cut_plan(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "cut-plan.md").unlink()
    assert story_cut.main(["check", "02"]) == 0


def test_check_reports_a_missing_story(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    (root / "input" / "book-02" / "story.md").unlink()
    assert story_cut.main(["check", "02"]) == 2


def test_usage_line_names_both_forms(capsys):
    assert story_cut.main([]) == 2
    assert "check" in capsys.readouterr().err


def test_bare_check_is_not_mistaken_for_a_book_number(tmp_path, monkeypatch, capsys):
    """`story_cut.py check` with no book resolves book-check, which has no
    story — a clean exit 2, never a traceback."""
    _series(tmp_path, monkeypatch)
    assert story_cut.main(["check"]) == 2
