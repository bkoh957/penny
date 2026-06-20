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
