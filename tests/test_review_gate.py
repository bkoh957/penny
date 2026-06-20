import sys
from pathlib import Path

import pytest

from scripts.penny_meta import parse_frontmatter
from scripts.penny_verdict import write_verdict
from scripts.review_gate import GateError, evaluate_gate, write_gate_md, main

CONFIG = Path("config/run-config.md").resolve()


def _reviews(tmp_path):
    d = tmp_path / "output" / "book-01" / "chapters" / "ch-07.reviews"
    d.mkdir(parents=True)
    return d


def _inspector(d, name, *, blocking=None, score=3):
    write_verdict(out_dir=d, producer=name, kind="inspector", target="book-01/ch-07",
                  name=name, blocking=blocking or [], notes=[], metrics={}, evidence=[],
                  score=score)


def test_pass_when_no_blockers(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity")
    _inspector(d, "inspector-voice")
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "PASS"
    assert result["blocking_count"] == 0


def test_hold_counts_blockers(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity", blocking=["will referenced before reveal"])
    _inspector(d, "inspector-fairplay", blocking=["clue not on the page"])
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "HOLD"
    assert result["blocking_count"] == 2
    assert ("inspector-continuity", "will referenced before reveal") in result["blocking_issues"]


def test_gate_summary_files_are_ignored(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-voice")
    # A stray prior gate.md sitting in the dir must NOT be read as a verdict.
    write_gate_md(d / "ch-07.gate.md", "book-01/ch-07",
                  {"gate": "HOLD", "blocking_count": 9, "blocking_issues": [],
                   "escalations": [], "score_spread_log": []})
    result = evaluate_gate(d, CONFIG)
    assert result["gate"] == "PASS"  # the gate-summary's 9 is not counted


def test_malformed_verdict_missing_producer_raises(tmp_path):
    d = _reviews(tmp_path)
    (d / "broken.md").write_text("---\nkind: inspector\nscore: 3\n---\n- note\n", encoding="utf-8")
    with pytest.raises(GateError):
        evaluate_gate(d, CONFIG)


def test_inspector_missing_score_raises(tmp_path):
    d = _reviews(tmp_path)
    (d / "x.md").write_text("---\nproducer: inspector-voice\nkind: inspector\n---\n- note\n",
                            encoding="utf-8")
    with pytest.raises(GateError):
        evaluate_gate(d, CONFIG)


def test_empty_reviews_dir_raises(tmp_path):
    d = _reviews(tmp_path)
    with pytest.raises(GateError):
        evaluate_gate(d, CONFIG)


def test_missing_thresholds_raises(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-voice")
    bad_config = tmp_path / "bad.md"
    bad_config.write_text("# no yaml block here\n", encoding="utf-8")
    with pytest.raises(GateError):
        evaluate_gate(d, bad_config)


def test_gate_md_has_no_blocking_lines_and_is_sibling(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity", blocking=["bad thing"])
    result = evaluate_gate(d, CONFIG)
    out = d.parent / "ch-07.gate.md"
    write_gate_md(out, "book-01/ch-07", result)
    text = out.read_text(encoding="utf-8")
    assert not any(line.startswith("BLOCKING:") for line in text.splitlines())
    meta = parse_frontmatter(text)
    assert meta["kind"] == "gate-summary"
    assert meta["gate"] == "HOLD"
    assert out.parent.name == "chapters"  # sibling of the reviews dir, not inside it


def test_main_exit0_on_hold_and_writes_gate_md(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-continuity", blocking=["bad thing"])
    rc = main([str(d), "--config", str(CONFIG)])
    assert rc == 0  # HOLD is a result, not a crash
    assert (d.parent / "ch-07.gate.md").exists()


def test_main_nonzero_on_operational_error(tmp_path):
    d = _reviews(tmp_path)  # empty -> operational error
    rc = main([str(d), "--config", str(CONFIG)])
    assert rc != 0


def test_blocking_disagreement_escalates_within_a_dimension(tmp_path):
    d = _reviews(tmp_path)
    # Two verdicts, SAME producer (simulates panel_size>1): one blocks, one doesn't.
    write_verdict(out_dir=d, producer="inspector-voice", kind="inspector",
                  target="book-01/ch-07", name="inspector-voice-a",
                  blocking=["voice broke"], notes=[], metrics={}, evidence=[], score=2)
    write_verdict(out_dir=d, producer="inspector-voice", kind="inspector",
                  target="book-01/ch-07", name="inspector-voice-b",
                  blocking=[], notes=[], metrics={}, evidence=[], score=4)
    result = evaluate_gate(d, CONFIG)
    assert "inspector-voice" in result["escalations"]


def test_no_escalation_at_panel_one(tmp_path):
    # Distinct producers (the panel_size:1 default) -> disagreement check sleeps.
    d = _reviews(tmp_path)
    _inspector(d, "inspector-voice", blocking=["voice broke"], score=2)
    _inspector(d, "inspector-structure", blocking=[], score=4)
    result = evaluate_gate(d, CONFIG)
    assert result["escalations"] == []


def test_score_spread_logs_within_a_dimension(tmp_path):
    d = _reviews(tmp_path)
    write_verdict(out_dir=d, producer="inspector-structure", kind="inspector",
                  target="book-01/ch-07", name="inspector-structure-a",
                  blocking=[], notes=[], metrics={}, evidence=[], score=2)
    write_verdict(out_dir=d, producer="inspector-structure", kind="inspector",
                  target="book-01/ch-07", name="inspector-structure-b",
                  blocking=[], notes=[], metrics={}, evidence=[], score=5)
    result = evaluate_gate(d, CONFIG)  # default threshold is 2; spread is 3
    assert any(e["producer"] == "inspector-structure" and e["spread"] == 3
               for e in result["score_spread_log"])


def test_no_score_spread_at_panel_one(tmp_path):
    d = _reviews(tmp_path)
    _inspector(d, "inspector-structure", score=2)
    _inspector(d, "inspector-voice", score=5)  # different dimensions, not a spread
    result = evaluate_gate(d, CONFIG)
    assert result["score_spread_log"] == []
