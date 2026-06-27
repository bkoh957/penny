import re as _re
from pathlib import Path

from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict, count_blocking


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


def test_count_blocking_anchored_and_case_sensitive(tmp_path):
    (tmp_path / "a.md").write_text(
        "BLOCKING: real one\n"
        "- not a blocker\n"
        "blocking: lowercase not counted\n"
        "see BLOCKING: mid-line not counted\n",
        encoding="utf-8",
    )
    (tmp_path / "b.md").write_text("BLOCKING: another\nBLOCKING: and another\n", encoding="utf-8")
    assert count_blocking(tmp_path) == 3


def test_count_blocking_absent_dir_is_zero(tmp_path):
    assert count_blocking(tmp_path / "nope") == 0


def test_count_blocking_agrees_with_real_status_line(penny_root):
    # The status line is the OTHER implementation of the ^BLOCKING: convention.
    # Pin them to agree by running the real script, not a transcribed grep.
    penny_root.write_stage("book=01 chapter=07 stage=REVIEW")
    penny_root.write_blocking("01", "07", 2)  # writes 2 BLOCKING: lines into the reviews dir
    out = penny_root.run('{"context_window": {"used_percentage": 41.2}}')
    rendered = int(_re.search(r"gate: (\d+) blocking", out).group(1))

    reviews = penny_root.path / "output" / "book-01" / "chapters" / "ch-07.reviews"
    assert count_blocking(reviews) == rendered == 2


def test_write_verdict_emits_extra_frontmatter(tmp_path):
    path = write_verdict(
        out_dir=tmp_path, producer="developmental-editor", kind="developmental",
        target="book-01/ch-07", name="developmental-edit", blocking=[], notes=["a note"],
        metrics={}, evidence=[], score=3,
        extra_frontmatter={"reviewed_draft_sha256": "abc123"},
    )
    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    assert meta.get("kind") == "developmental"
    assert meta.get("score") == "3"
    assert meta.get("reviewed_draft_sha256") == "abc123"
