from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude/agents"
CONFIG = ROOT / "config"


def test_prose_pass_files_exist():
    for p in [
        AGENTS / "line-editor.md",
        AGENTS / "copy-editor.md",
        AGENTS / "ledger-updater.md",
        CONFIG / "line-edit/line-edit.md",
        CONFIG / "copy-edit/copy-edit.md",
    ]:
        assert p.is_file(), f"missing {p}"


def test_copy_editor_is_fresh_context():
    text = (AGENTS / "copy-editor.md").read_text(encoding="utf-8").lower()
    assert "style sheet" in text or "style-sheet" in text
    assert "drafting history" in text          # must state it never sees it


def test_ledger_updater_states_its_guards():
    text = (AGENTS / "ledger-updater.md").read_text(encoding="utf-8").lower()
    assert "write-scope" in text or "loaded slice" in text   # bounded writes
    assert "canon-core" in text                              # never mutates body
    assert "advanced" in text                                # emits per-thread flag
