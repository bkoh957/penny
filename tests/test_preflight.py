import pytest

from scripts import preflight


def _make_book(root, book="01", *, populated=True, locked=True):
    wd = root / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    led = wd / f"book-{book}.yaml"
    led.write_text("book: '01'\nculprit: margaret\n" if populated else "", encoding="utf-8")
    if locked:
        ld = root / ".penny/locks"
        ld.mkdir(parents=True, exist_ok=True)
        (ld / f"book-{book}.mystery.lock").write_text("ok\n", encoding="utf-8")
    return led


def test_draft_passes_when_populated_and_locked(tmp_path):
    _make_book(tmp_path, populated=True, locked=True)
    assert preflight.cmd_draft("01", "01", repo_root=tmp_path) == 0


def test_draft_fails_without_lock(tmp_path):
    _make_book(tmp_path, populated=True, locked=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no lock" in str(e.value)


def test_draft_fails_without_ledger(tmp_path):
    (tmp_path / "series/whodunit").mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no ledger" in str(e.value)


def test_draft_fails_when_ledger_unpopulated(tmp_path):
    _make_book(tmp_path, populated=False, locked=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "unpopulated" in str(e.value)


def _make_run_config(root, *, drafting, final_read):
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "run-config.md").write_text(
        "# fixture run-config\n\n```yaml\n"
        f"drafting_model:   {drafting}\n"
        f"final_read_model: {final_read}\n"
        "```\n",
        encoding="utf-8",
    )


def _make_chapter(root, book, ch, drafted_by):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.draft.md").write_text(
        f"---\ndrafted_by: {drafted_by}\n---\nprose\n", encoding="utf-8")


def _make_final_read(root, book, read_by):
    d = root / "output" / f"book-{book}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"book-{book}.final-read.md").write_text(
        f"---\nread_by: {read_by}\n---\nholistic read\n", encoding="utf-8")


def test_assemble_green(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "codex")
    assert preflight.cmd_assemble("01", repo_root=tmp_path) == 0


def test_assemble_config_invariant_fails_before_stamps(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="claude-opus")
    # no chapters at all — must still fail on the config compare
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "equals drafting_model" in str(e.value)


def test_assemble_drift_configured_final_reader_drafted(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_chapter(tmp_path, "01", "02", "codex")  # codex drafted ch-02 — config lies
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "configured final_read_model 'codex'" in str(e.value)


def test_assemble_read_by_collides_with_drafter(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "claude-opus")  # final read done by a drafter
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "final-read model 'claude-opus'" in str(e.value)
