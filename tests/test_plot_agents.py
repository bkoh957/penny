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


def test_chapter_weaver_contract():
    t = _text("chapter-weaver.md")
    for phrase in ("**Because:**", "**Opens:**", "**Closes:**", "**Carries:**",
                   "**Hook:**", "clue obligations",
                   "woven: true", "plot_stage.py", "worse in kind",
                   "never draft prose", "outline-skeleton.md",
                   "clear any stale `woven: true`", "**Independence"):
        assert phrase in t, phrase


def test_outline_fan_contract():
    t = _text("outline-fan.md")
    for phrase in (
        "reader's copy",
        "fresh sub-agent",              # was: **Independence
        "**Isolation",                  # the point of the change
        "outline-fan-stage-K.md",       # was: outline-fan.md
        "MUST never emit any",          # split from the token below by a line wrap
        "^BLOCKING:",
        "Nothing else",                 # was: NOTHING else
        "reveals:",                     # never shown the answer key
        "put the book down",            # was: put it down
        "cannot report whether the surprise works",   # was: guessed her in chapter four
    ):
        assert phrase in t, phrase
