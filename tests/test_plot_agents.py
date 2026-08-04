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


# --- FINAL REVIEW, Important 8: retiring chapter-weaver dropped
# test_chapter_weaver_contract — which pinned the emitted wiring fields, the
# clue obligations, "never draft prose" and "**Independence" — and replaced it
# with two bare existence assertions. The guarantees are restored here, adapted
# to what chapter-cutter actually promises: it no longer emits wiring at all
# (story_cut.py derives it), so the pins move to the cut plan's own row shapes
# and to the checks downstream of them. ---

def test_chapter_cutter_contract():
    t = _text("chapter-cutter.md")
    for phrase in (
        # --- inputs and outputs, by name ---
        "story.md",
        "cut-plan.md",
        "series/whodunit/book-NN.yaml",
        "beat sheet",
        # --- direction is an input it must actually read (spec 2026-08-04 §4.1) ---
        "## Chapter Direction",
        # --- the cut plan's row shapes: story_cut.py's parse_cut_plan reads
        # exactly these, so a drifted format silently loses beats or tracks ---
        "**Beats:**",
        "**Summary:**",
        "**Compress:**",
        # --- the refusals its own output can earn ---
        "beats-without-chapter",
        "duplicate-beat",
        "obligations.max_per_chapter",
        "starved-thread",
        # --- posture: it proposes, the showrunner approves (was: the weaver's
        # "never draft prose" + certificate rule) ---
        "**Independence",
        "You propose. You never write.",
        "Never write prose.",
        "Never write a ledger or a certificate.",
    ):
        assert phrase in t, phrase


def test_chapter_cutter_never_claims_the_wiring_story_cut_derives():
    # The weaver emitted **Because:**/**Opens:**/**Closes:**/**Carries:**/
    # **Hook:** itself. The cutter must NOT — those are derived by
    # story_cut.py from the story's own tags, and an agent told to write them
    # would put a second, drifting author on the same fields. The agent may
    # name them only to disclaim them, so pin the disclaimer, not the absence.
    t = _text("chapter-cutter.md")
    # One whitespace-tolerant sentence pin, not two disjoint tokens: separate
    # assertions could each be satisfied by an unrelated sentence, silently
    # weakening the guarantee (the same reasoning as the outline-fan pin).
    assert re.search(r"Never\s+emit\s+outline\s+sections\s+—.*?wiring.*?"
                     r"derived\s+by\s+`story_cut\.py`", t, re.S), t


def test_chapter_cutter_is_told_direction_is_advisory_not_a_gate():
    t = _text("chapter-cutter.md")
    assert "Chapter Direction" in t
    assert "propose" in t.lower()


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
