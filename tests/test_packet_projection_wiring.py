"""Contract test: the packet projections are actually spent by the dispatches.

`--without-continuity` and `--inspector-slice` are read-only projections over a
packet already on disk. Nothing calls them but a runbook, so nothing FAILS when
a runbook stops calling them — the block simply goes back to being transmitted
whole to eight recipients, five of which never read it, and no test notices.
These pin the wiring itself (spec 2026-09-09-check-economics-design.md §3b).

Each runbook assertion is scoped to the STEP that must carry the flag, not to
the file. A substring-anywhere check passes on any other step's prose — step 4's
paragraph alone would satisfy a test aimed at step 7b — so the one regression
these exist to catch (a dispatch quietly reverting to the whole packet) would be
silent, which is the failure mode this plan has already hit twice.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A runbook step opens at column 0 as `4.`, `7b.` or `10.`.
_STEP_RE = re.compile(r"^(\d+[a-z]?)\. ", re.MULTILINE)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _step(rel: str, label: str) -> str:
    """The body of one numbered step of a runbook, up to the next step's number.

    Fails loudly when the label is gone: a renumbered runbook should break this
    test noisily and be re-pointed, never slide back to matching the whole file.
    """
    text = _read(rel)
    starts = [(m.group(1), m.start()) for m in _STEP_RE.finditer(text)]
    labels = [s for s, _ in starts]
    assert label in labels, f"{rel} has no step {label} — steps are {labels}"
    i = labels.index(label)
    end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
    return text[starts[i][1]:end]


def test_map_chapter_dispatches_the_map_maker_without_continuity():
    step = _step("commands/map-chapter.md", "3")
    assert "map-maker" in step
    assert "--without-continuity" in step


def test_review_chapter_gives_the_grading_inspectors_the_inspector_slice():
    step = _step("commands/review-chapter.md", "4")
    assert "--inspector-slice" in step
    assert "inspector-continuity" in step and "inspector-fairplay" in step


def test_review_chapter_names_the_three_inspectors_that_get_no_slice():
    step = _step("commands/review-chapter.md", "4")
    for name in ("inspector-structure", "inspector-voice", "inspector-ai-prose"):
        assert name in step, f"step 4 no longer says {name} gets no slice"


def test_review_chapter_gives_the_developmental_editor_no_continuity():
    step = _step("commands/review-chapter.md", "7b")
    assert "developmental-editor" in step
    assert "--without-continuity" in step


def test_neither_runbook_dispatches_a_projection_it_should_not():
    # `--inspector-slice` belongs to the two grading inspectors only; the
    # map-maker's dispatch must never acquire it, and vice versa.
    assert "--inspector-slice" not in _step("commands/map-chapter.md", "3")
    assert "--without-continuity" not in _step("commands/review-chapter.md", "4")


def test_slice_free_inspectors_do_not_declare_a_ledger_slice():
    for name in ("inspector-structure", "inspector-voice", "inspector-ai-prose"):
        text = _read(f"agents/{name}.md")
        assert "ledger_slice" not in text, f"{name} still declares ledger_slice"


def test_grading_inspectors_still_receive_a_slice():
    for name in ("inspector-continuity", "inspector-fairplay"):
        assert "ledger_slice" in _read(f"agents/{name}.md")
