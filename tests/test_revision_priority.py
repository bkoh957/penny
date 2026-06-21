import json

import pytest

from scripts import beta_report, revision_priority


def _write_converged(reports_dir, persona, *, consensus=None, logged=None, no=0):
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "penny-beta/1", "persona": persona,
        "driver": beta_report.DRIVER_BY_PERSONA[persona],
        "panel": {"m": 2, "k": 2, "panel_size": 2,
                  "distinct_models": ["a", "b"], "degraded": False},
        "engagement_curve": [],
        "put_down_points": {"consensus": consensus or [], "logged": logged or []},
        "would_buy_next": {"tally": {"yes": 0, "no": no, "n/a": 0}, "denominator": 2},
    }
    beta_report.write_converged(reports_dir, report)


def _write_gate(chapters_dir, chapter, score_spread_log):
    chapters_dir.mkdir(parents=True, exist_ok=True)
    (chapters_dir / f"ch-{chapter:02d}.gate.md").write_text(
        "---\nproducer: review_gate.py\nkind: gate-summary\n"
        f"target: book-99/ch-{chapter:02d}\ngate: PASS\nblocking_count: 0\n"
        "schema: penny-verdict/1\n---\n\n- PASS: 0 blocking issue(s)\n"
        "- escalations: []\n"
        f"- score_spread_log: {score_spread_log}\n", encoding="utf-8")


def _book99(tmp_path):
    return (tmp_path / "output" / "book-99" / "reports",
            tmp_path / "output" / "book-99" / "chapters")


def _config(tmp_path, personas=2, would_buy=3):
    cfg = tmp_path / "run-config.md"
    cfg.write_text(f"```yaml\nrevision_escalate_personas: {personas}\n"
                   f"would_buy_escalate_count: {would_buy}\n```\n", encoding="utf-8")
    return cfg


def test_putdown_below_threshold_is_log(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "puzzle-hawk", consensus=[3])     # 1 persona at ch.3
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, personas=2))
    assert any("cross_persona_putdown<2" in ln and "ch.3" in ln for ln in res["log"])
    assert not any("ch.3" in ln for ln in res["escalate"])


def test_putdown_at_threshold_escalates(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "puzzle-hawk", consensus=[7])
    _write_converged(reports, "cozy-loyalist", logged=[7])      # 2 distinct personas at ch.7
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, personas=2))
    line = next(ln for ln in res["escalate"] if "ch.7" in ln)
    assert "cross_persona_putdown>=2" in line
    assert "2 personas" in line
    assert "cozy-loyalist" in line and "puzzle-hawk" in line   # named + sorted


def test_would_buy_no_at_threshold_escalates(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "puzzle-hawk", no=1)
    _write_converged(reports, "cozy-loyalist", no=1)
    _write_converged(reports, "arc-reader", no=1)               # total no = 3
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, would_buy=3))
    line = next(ln for ln in res["escalate"] if "would-buy" in ln)
    assert "would_buy_no>=3" in line and "3" in line


def test_score_spread_is_log_only(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_gate(chapters, 5, [{"producer": "inspector-voice", "spread": 2}])
    res = revision_priority.aggregate("99", repo_root=tmp_path, config_path=_config(tmp_path))
    line = next(ln for ln in res["log"] if "score-spread" in ln)
    assert "ch.5" in line and "inspector-voice" in line and "spread 2" in line
    assert not res["escalate"]


def test_all_clean_has_no_escalations(tmp_path):
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "cozy-loyalist", no=0)
    _write_gate(chapters, 1, [])
    rc = revision_priority.cmd_report("99", repo_root=tmp_path, config_path=_config(tmp_path))
    assert rc == 0
    text = revision_priority.report_path("99", tmp_path).read_text(encoding="utf-8")
    assert "escalations: 0" in text


def test_cross_consistency_with_beta_report(tmp_path):
    """Build a converged report the real way (beta_report) and feed it straight in:
    the aggregator must parse the exact shape write_converged emits."""
    reports, chapters = _book99(tmp_path)
    raws = [beta_report.build_raw_reading(
        persona="impatient-skimmer", model=m,
        engagement_curve=[{"chapter": 4, "score": 2}],
        put_down_points=[4], whodunit_guess={"name": "x", "chapter": 9},
        confusion_points=[], emotional_beats=["dread"], would_buy_verdict="no")
        for m in ("a", "b")]
    converged = beta_report.collapse_persona(raws, k=2, panel_size=2)
    beta_report.write_converged(reports, converged)
    res = revision_priority.aggregate("99", repo_root=tmp_path,
                                      config_path=_config(tmp_path, personas=1, would_buy=2))
    assert any("ch.4" in ln for ln in res["escalate"])          # 1 persona, threshold 1
    assert any("would-buy" in ln for ln in res["escalate"])     # tally.no=2, threshold 2


def test_zero_would_buy_no_emits_no_line(tmp_path):
    """When total_no == 0, no would-buy line should be emitted anywhere."""
    reports, chapters = _book99(tmp_path)
    _write_converged(reports, "cozy-loyalist", no=0)
    res = revision_priority.aggregate("99", repo_root=tmp_path, config_path=_config(tmp_path))
    assert not any("would-buy" in ln for ln in res["escalate"])
    assert not any("would-buy" in ln for ln in res["log"])
