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
