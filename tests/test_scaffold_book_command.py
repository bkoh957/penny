from pathlib import Path

CMD = Path(".claude/commands/scaffold-book.md")
RUN_CONFIG = Path("config/run-config.md")


def test_command_gates_on_outline_check():
    text = CMD.read_text(encoding="utf-8")
    assert "outline_check.py" in text, "must gate on the outline structural check"


def test_command_dispatches_scaffolder():
    text = CMD.read_text(encoding="utf-8")
    assert "book-scaffolder" in text, "must dispatch the extraction agent"


def test_command_runs_unchanged_lock_on_approve():
    text = CMD.read_text(encoding="utf-8")
    assert "preflight.py lock-mystery" in text, "approval must run the shipped lock"


def test_command_deletes_lock_on_rederive():
    text = CMD.read_text(encoding="utf-8")
    assert "mystery.lock" in text, "re-derivation must delete the existing lock first"


def test_run_config_has_scaffold_approval():
    assert "scaffold_approval" in RUN_CONFIG.read_text(encoding="utf-8")
