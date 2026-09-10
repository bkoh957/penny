import re
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
        "input/book-$book/story.md \\\n"
        "     --from input/book-$book/plot/turning-points.md output/book-$book/mystery-solution.md"
        in t
    )
    # Readback stamps one report PER STAGE, so this is a loop rather than a
    # single literal path — but it is still literal bash with the exact --from
    # _UPSTREAM expects, which is what this test exists to pin.
    assert 'for f in output/book-$book/reports/outline-fan-stage-*.md; do' in t
    assert '"$f" --from input/book-$book/outline.md' in t


def test_plot_book_runs_the_cut_after_approval():
    """The cut stage dispatches chapter-cutter, takes the showrunner's approved
    plan, and only then runs the deterministic emitter — no waivers exist at
    this level, so a finding means fixing story.md or cut-plan.md and
    re-running, never a recorded exception."""
    t = CMD.read_text(encoding="utf-8")
    assert "chapter-cutter" in t
    assert "scripts/story_cut.py" in t
    assert "cut-plan.md" in t


def test_stage_chapters_points_at_the_craft_document():
    t = CMD.read_text(encoding="utf-8")
    assert "config/story-craft" in t
    assert "resolve-dir story-craft" in t


def test_stage_chapters_no_longer_defines_a_beat_by_its_syntax_alone():
    """The old clause described only the tag layout, which is what produced
    correctly-tagged architecture notes instead of beats (spec §1)."""
    t = CMD.read_text(encoding="utf-8")
    assert "one per bullet, prose first, tags\n   trailing" not in t
    assert "one visible change" in t


def _story_header_block(t: str) -> str:
    """The literal ```markdown``` fence the runbook tells the author to write
    into a new story.md — the portable header, isolated from the rest of the
    runbook's own prose so assertions about it can't accidentally pass
    because some OTHER paragraph happens to mention the same words."""
    start = t.index("```markdown\n   # Story")
    end = t.index("```", start + len("```markdown"))
    return t[start:end]


def test_a_new_story_gets_a_self_describing_header():
    t = CMD.read_text(encoding="utf-8")
    assert "writing-beats.md" in t


def test_the_header_resolves_the_craft_document_rather_than_naming_a_bare_path():
    """FINDING 3 (final review): under a series root, bare
    `config/story-craft/writing-beats.md` does not exist — the file ships in
    the plugin. The header must tell the reader how to RESOLVE the craft
    document (the same `resolve-dir story-craft` invocation the runbook uses
    on itself two paragraphs earlier), not point at a path that only exists
    inside the plugin repo."""
    block = _story_header_block(CMD.read_text(encoding="utf-8"))
    assert "resolve-dir story-craft" in block
    assert "config/story-craft/writing-beats.md" not in block


# A runbook step opens at column 0 as `4.` or `10.` — same shape as
# tests/test_packet_projection_wiring.py's `_step`, and for the same reason: an
# assertion scoped to the whole file passes on any other step's prose.
_STEP_RE = re.compile(r"^(\d+[a-z]?)\. ", re.MULTILINE)


def _step(label: str) -> str:
    text = CMD.read_text(encoding="utf-8")
    starts = [(m.group(1), m.start()) for m in _STEP_RE.finditer(text)]
    labels = [s for s, _ in starts]
    assert label in labels, f"plot-book.md has no step {label} — steps are {labels}"
    i = labels.index(label)
    end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
    return text[starts[i][1]:end]


def test_readback_calls_tension_check_by_book_number():
    """The engine's only tension_check caller must use the book-number form.

    The four-flag path form hand-assembles the inputs, and
    `penny_genre.py beat-sheet` prints an empty string when a genre declares no
    `beat_sheet:` key — the shell then passes `--beat-sheet ""`, which
    check_tension guards away with `.is_file()`, so dead-stretch,
    starved-thread, off-mark-beat, overloaded-chapter and monotonous-closings
    all vanish with no note. `_first_file` normalisation and that note live
    inside tension_check's book-number branch, so only this form gets them.
    """
    step = _step("9")
    assert "tension_check.py" in step
    assert re.search(r'tension_check\.py"\s+\$book\b', step), (
        "step 9 no longer invokes tension_check.py with the book number")
    assert "--beat-sheet" not in step, (
        "step 9 hand-assembles the beat sheet again — that path form silently "
        "drops the five beat-sheet-dependent checks")
    for flag in ("--turning-points", "--whodunit"):
        assert flag not in step, f"step 9 hand-assembles {flag} again"
