from pathlib import Path

DRAFT_CMD = Path("commands/draft-chapter.md")


def test_draft_chapter_runs_preflight_gate():
    text = DRAFT_CMD.read_text(encoding="utf-8")
    assert "scripts/preflight.py" in text and "preflight.py\" draft" in text, (
        "draft-chapter must gate on the draft pre-flight"
    )


REPO = Path(__file__).resolve().parents[1]


def test_draft_chapter_prefers_the_compiled_brief():
    text = (REPO / "commands" / "draft-chapter.md").read_text(encoding="utf-8")
    assert "briefs/ch-$chapter.md" in text
    assert "falls back" in text.lower() or "fall back" in text.lower()


def test_drafter_no_longer_tells_the_model_to_pad():
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8")
    for banned in ("extend a scene", "deepen interiority", "slow a beat",
                   "add sensory texture"):
        assert banned not in text, f"padding directive survives: {banned!r}"


def test_drafter_treats_a_short_chapter_as_a_scene_count_problem():
    text = (REPO / "agents" / "drafter.md").read_text(encoding="utf-8").lower()
    assert "scene" in text and "do not pad" in text
