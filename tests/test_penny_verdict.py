from pathlib import Path

from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict


def test_writes_frontmatter_and_blocking_lines(tmp_path):
    out = write_verdict(
        out_dir=tmp_path,
        producer="fairplay_check.py",
        kind="deterministic-checker",
        target="book-01/ch-22",
        name="fairplay",
        blocking=["necessary clue clue-x scheduled at/after reveal"],
        notes=["red herring rh-y scheduled after reveal"],
        metrics={"required_clues": 3},
        evidence=[],
    )
    assert out == tmp_path / "fairplay.md"
    text = out.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    assert meta["producer"] == "fairplay_check.py"
    assert meta["kind"] == "deterministic-checker"
    assert meta["target"] == "book-01/ch-22"
    assert meta["schema"] == "penny-verdict/1"
    # Blocking issues are ^BLOCKING: lines (Phase 1 status-line + gate convention).
    blocking_lines = [ln for ln in text.splitlines() if ln.startswith("BLOCKING:")]
    assert blocking_lines == ["BLOCKING: necessary clue clue-x scheduled at/after reveal"]
    # Non-blocking notes are "- " lines.
    assert "- red herring rh-y scheduled after reveal" in text


def test_omits_score_for_checkers(tmp_path):
    out = write_verdict(
        out_dir=tmp_path, producer="voice_drift.py", kind="deterministic-checker",
        target="book-01/ch-07", name="voice-drift",
        blocking=[], notes=[], metrics={}, evidence=[],
    )
    meta = parse_frontmatter(out.read_text(encoding="utf-8"))
    assert "score" not in meta


def test_includes_score_when_supplied(tmp_path):
    out = write_verdict(
        out_dir=tmp_path, producer="inspector-voice", kind="inspector",
        target="book-01/ch-07", name="inspector-voice",
        blocking=[], notes=[], metrics={}, evidence=[], score=4,
    )
    meta = parse_frontmatter(out.read_text(encoding="utf-8"))
    assert meta["score"] == "4"


def test_creates_out_dir_if_missing(tmp_path):
    nested = tmp_path / "ch-07.reviews"
    out = write_verdict(
        out_dir=nested, producer="voice_drift.py", kind="deterministic-checker",
        target="book-01/ch-07", name="voice-drift",
        blocking=[], notes=[], metrics={}, evidence=[],
    )
    assert out.exists()
    assert out.parent == nested


def test_evidence_rendered_as_json_lines(tmp_path):
    out = write_verdict(
        out_dir=tmp_path, producer="voice_drift.py", kind="deterministic-checker",
        target="book-01/ch-07", name="voice-drift", blocking=[], notes=[],
        metrics={"sentence_stdev": 5.1},
        evidence=[{"tic_id": "bodily_reaction", "span_text": "her heart pounded", "line": 12}],
    )
    text = out.read_text(encoding="utf-8")
    assert "metrics:" in text
    assert "evidence:" in text
    assert "bodily_reaction" in text
    assert "her heart pounded" in text
