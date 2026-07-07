from pathlib import Path

from scripts.penny_meta import parse_frontmatter

RUBRIC = Path("config/review-rubrics/developmental-craft.md")

EIGHT_DIMENSIONS = [
    "setting grounding",
    "motivation",
    "scene economy",
    "subtext",
    "interiority",
    "show",          # show-don't-tell
    "genre delivery",
    "hook",
]


def test_rubric_exists_with_thresholds_and_boundary():
    assert RUBRIC.is_file()
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "threshold" in text
    assert "boundary" in text


def test_rubric_names_all_eight_dimensions():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    for dim in EIGHT_DIMENSIONS:
        assert dim in text, f"rubric missing dimension: {dim}"


def test_rubric_is_advisory_never_blocking():
    text = RUBRIC.read_text(encoding="utf-8").lower()
    assert "advisory" in text
    assert "no ^blocking" in text or "never block" in text or "not block" in text


AGENT = Path("agents/developmental-editor.md")


def test_agent_exists_with_valid_frontmatter():
    assert AGENT.is_file()
    meta = parse_frontmatter(AGENT.read_text(encoding="utf-8"))
    assert meta.get("name") == "developmental-editor"
    assert meta.get("description")


def test_agent_declares_contract():
    text = AGENT.read_text(encoding="utf-8")
    assert "developmental-craft.md" in text          # references its rubric
    assert "producer: developmental-editor" in text
    assert "kind: developmental" in text
    assert "reviewed_draft_sha256" in text


def test_agent_is_advisory_and_context_rich():
    text = AGENT.read_text(encoding="utf-8")
    assert "^BLOCKING" in text                        # explicitly forbids it
    assert "MUST NOT emit any" in text                # prohibition, not mere presence
    assert "setting-pack" in text or "setting pack" in text
    assert "whodunit" in text.lower()                 # explicitly denied the solution


REVIEW_CMD = Path("commands/review-chapter.md")
FINALIZE_CMD = Path("commands/finalize-chapter.md")


def test_review_chapter_dispatches_dev_editor_and_halts_cross_model():
    text = REVIEW_CMD.read_text(encoding="utf-8")
    assert "developmental-editor" in text
    assert "developmental-edit.md" in text
    assert "reviewed_draft_sha256" in text
    # cross-model is a hard precondition: the command must halt, not degrade.
    assert "halt" in text.lower()


def test_finalize_documents_dev_clearance():
    text = FINALIZE_CMD.read_text(encoding="utf-8")
    assert "clear-dev" in text
    assert "gate: PASS" in text                       # dual-precondition: gate + clearance
