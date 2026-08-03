import re
from pathlib import Path

A = Path("agents")


def _text(name):
    p = A / name
    assert p.is_file(), f"missing agent file {p}"
    return p.read_text(encoding="utf-8")


def test_plot_proposer_contract():
    t = _text("plot-proposer.md")
    for phrase in ("never choose the core", "never invent silently",
                   "never improve chosen material", "one-sentence pitch",
                   "premise.md", "ending.md", "turning-points.md", "beat-sheet",
                   "**Independence"):
        assert phrase in t, phrase


def test_chapter_cutter_exists_and_weaver_is_retired():
    root = Path(__file__).resolve().parents[1]
    cutter = root / "agents" / "chapter-cutter.md"
    assert cutter.is_file()
    assert "name: chapter-cutter" in cutter.read_text(encoding="utf-8")
    assert not (root / "agents" / "chapter-weaver.md").exists()


def test_chapter_cutter_proposes_and_never_writes():
    root = Path(__file__).resolve().parents[1]
    text = (root / "agents" / "chapter-cutter.md").read_text(encoding="utf-8")
    assert "cut-plan.md" in text
    assert "writes nothing" in text.lower() or "never writes" in text.lower()


def test_outline_fan_contract():
    t = _text("outline-fan.md")
    for phrase in (
        "reader's copy",
        "fresh sub-agent",              # was: **Independence
        "**Isolation",                  # the point of the change
        "outline-fan-stage-K.md",       # was: outline-fan.md
        "Nothing else",                 # was: NOTHING else
        "reveals:",                     # never shown the answer key
        "put the book down",            # was: put it down
        "cannot report whether the surprise works",   # was: guessed her in chapter four
        # FINAL REVIEW: nothing pinned the two questions this whole spec
        # exists to add — the load-bearing ones that measure whether the
        # trapdoor is visible from outside and whether a thread died on the
        # page (2026-07-30-staged-reveal-readback-design.md §5).
        "What do you expect the next big turn to be?",
        "What have you stopped wondering about?",
    ):
        assert phrase in t, phrase
    # was: two disjoint pins, "MUST never emit any" + "^BLOCKING:" — two
    # SEPARATE sentences could each satisfy one half, silently weakening the
    # pin. Pin the whole sentence as one whitespace-tolerant regex instead so
    # a reflow (e.g. a line wrap moving the backtick token) still matches but
    # the sentence itself can't be split apart from the token it constrains.
    assert re.search(r"MUST never emit any\s+`\^BLOCKING:`", t)
