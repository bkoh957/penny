"""Contract test: the packet projections are actually spent by the dispatches.

`--without-continuity` and `--inspector-slice` are read-only projections over a
packet already on disk. Nothing calls them but a runbook, so nothing FAILS when
a runbook stops calling them — the block simply goes back to being transmitted
whole to eight recipients, five of which never read it, and no test notices.
These pin the wiring itself (spec 2026-09-09-check-economics-design.md §3b).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
COMMANDS = ROOT / "commands"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_map_chapter_dispatches_the_map_maker_without_continuity():
    assert "--without-continuity" in _read("commands/map-chapter.md")


def test_review_chapter_uses_the_inspector_slice():
    assert "--inspector-slice" in _read("commands/review-chapter.md")


def test_review_chapter_gives_the_developmental_editor_no_continuity():
    assert "--without-continuity" in _read("commands/review-chapter.md")


def test_slice_free_inspectors_do_not_declare_a_ledger_slice():
    for name in ("inspector-structure", "inspector-voice", "inspector-ai-prose"):
        text = _read(f"agents/{name}.md")
        assert "ledger_slice" not in text, f"{name} still declares ledger_slice"


def test_grading_inspectors_still_receive_a_slice():
    for name in ("inspector-continuity", "inspector-fairplay"):
        assert "ledger_slice" in _read(f"agents/{name}.md")
