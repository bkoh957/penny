from pathlib import Path

DRAFT_CMD = Path("commands/draft-chapter.md")


def test_draft_chapter_runs_preflight_gate():
    text = DRAFT_CMD.read_text(encoding="utf-8")
    assert "scripts/preflight.py" in text and "preflight.py\" draft" in text, (
        "draft-chapter must gate on the draft pre-flight"
    )


REPO = Path(__file__).resolve().parents[1]


def test_draft_chapter_prefers_the_map_and_packet():
    text = (REPO / "commands" / "draft-chapter.md").read_text(encoding="utf-8")
    assert "maps/ch-$chapter.md" in text
    assert "packets/ch-$chapter.md" in text
    assert "falls back" in text.lower() or "fall back" in text.lower()
    assert "/map-chapter" in text


def test_drafter_no_longer_tells_the_model_to_pad():
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8")
    for banned in ("extend a scene", "deepen interiority", "slow a beat",
                   "add sensory texture"):
        assert banned not in text, f"padding directive survives: {banned!r}"


def test_drafter_treats_a_short_chapter_as_a_scene_count_problem():
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8").lower()
    assert "scene" in text and "do not pad" in text


def test_drafter_short_chapter_instruction_is_specific_not_just_word_soup():
    # A reworded padding directive can dodge a phrase ban-list while still
    # telling the model to inflate. Pin the actual behaviour, not just the
    # presence of the words "scene" and "pad" somewhere in the file.
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8").lower()
    assert "scene-count problem" in text
    assert "belongs to the outline" in text
    assert "report it" in text


def test_drafter_short_chapter_note_goes_in_frontmatter_not_the_body():
    # A note in the prose body rides through line-edit, copy-edit, and the
    # literal cp-to-.final.md promotion untouched, then into the manuscript
    # (assemble_book.py only strips frontmatter). Frontmatter is the one
    # channel that is stripped before the manuscript is built.
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8")
    assert "drafted_short" in text, "expected a drafted_short frontmatter field"
    assert "<!-- drafter-note" not in text, (
        "drafter must not be told to leave a note in the draft body"
    )
