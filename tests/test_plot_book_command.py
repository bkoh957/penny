from pathlib import Path

CMD = Path("commands/plot-book.md")


def test_runbook_exists_and_references_the_machinery():
    t = CMD.read_text(encoding="utf-8")
    for ref in ("plot_stage.py", "tension_check.py", "lock-mystery", "--waive",
                "plot-proposer", "chapter-weaver", "outline-fan", "mystery-planner",
                "${CLAUDE_PLUGIN_ROOT}", "readers-copy", "stage=PLOT-"):
        assert ref in t, ref


def test_runbook_never_asks_what_a_file_answers():
    t = CMD.read_text(encoding="utf-8")
    assert "never asks you anything a file already answers" in t
