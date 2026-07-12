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


def test_runbook_guards_the_absent_material_case():
    """FINDING 1: material.md is optional; when absent, premise has zero
    upstream save points and the stamp command must be skipped entirely
    rather than invoked with an empty --from (a hard argparse error)."""
    t = CMD.read_text(encoding="utf-8")
    assert "if [ -f input/book-$book/plot/material.md ]; then" in t
    assert "do NOT run `stamp` at all" in t
    assert "legitimate blank start" in t or "legitimate; plot_stage.py" in t


def test_runbook_rewrites_marker_at_weave_and_readback_transitions():
    """FINDING 2: a single run can span chapters -> weave (and on into
    readback) without pausing; the harness marker must be rewritten at each
    transition, not just once at step 3 for the entered stage."""
    t = CMD.read_text(encoding="utf-8")
    assert 'echo "book=$book stage=PLOT-WEAVE" > .penny/current-stage' in t
    assert 'echo "book=$book stage=PLOT-READBACK" > .penny/current-stage' in t


def test_runbook_gives_literal_bash_for_every_stamp_call():
    """FINDING 3: every plot_stage.py stamp call (premise, ending,
    turning-points, counterplot, chapters, readback) is a literal bash block
    with the exact --from list plot_stage.py's _UPSTREAM map expects, not
    prose alone."""
    t = CMD.read_text(encoding="utf-8")
    assert (
        "input/book-$book/plot/premise.md --from input/book-$book/plot/material.md"
        in t
    )
    assert (
        "input/book-$book/plot/ending.md --from input/book-$book/plot/premise.md"
        in t
    )
    assert (
        "input/book-$book/plot/turning-points.md \\\n"
        "     --from input/book-$book/plot/premise.md input/book-$book/plot/ending.md"
        in t
    )
    assert (
        "output/book-$book/mystery-solution.md \\\n"
        "     --from input/book-$book/plot/ending.md input/book-$book/plot/turning-points.md"
        in t
    )
    assert (
        "input/book-$book/outline-skeleton.md \\\n"
        "     --from input/book-$book/plot/turning-points.md output/book-$book/mystery-solution.md"
        in t
    )
    assert (
        "output/book-$book/reports/outline-fan.md \\\n"
        "     --from input/book-$book/outline-skeleton.md"
        in t
    )
