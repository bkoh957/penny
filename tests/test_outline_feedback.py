import copy
import subprocess
import sys
from pathlib import Path

import scripts.outline_feedback as of


def _seed():
    return {
        "book": "01",
        "reviewed_outline_sha256": "oldsha",
        "items": [
            {"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "a"},
            {"id": "OF-2", "source": "codex", "pass": 1, "state": "rejected", "text": "b"},
        ],
    }


def test_append_preserves_existing_items_exactly():
    ledger = _seed()
    before = copy.deepcopy(ledger["items"])
    out = of.append_items(
        ledger,
        [{"source": "claude", "text": "c"}, {"source": "codex", "text": "d"}],
        reviewed_sha="newsha",
    )
    assert out["items"][:2] == before  # existing items byte-identical
    assert out["reviewed_outline_sha256"] == "newsha"


def test_append_allocates_monotonic_ids_and_next_pass():
    out = of.append_items(_seed(), [{"source": "claude", "text": "c"}], reviewed_sha="s")
    assert out["items"][2] == {
        "id": "OF-3", "source": "claude", "pass": 2, "state": "open", "text": "c",
    }


def test_append_shares_one_pass_across_all_new_points():
    out = of.append_items(
        _seed(),
        [{"source": "claude", "text": "c"}, {"source": "codex", "text": "d"}],
        reviewed_sha="s",
    )
    assert out["items"][2]["pass"] == out["items"][3]["pass"] == 2
    assert out["items"][2]["id"] == "OF-3" and out["items"][3]["id"] == "OF-4"


def test_append_onto_empty_ledger_starts_at_one_and_pass_one():
    out = of.append_items(of.empty_ledger("01"), [{"source": "claude", "text": "x"}], reviewed_sha="s")
    assert out["items"] == [{"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "x"}]


def test_append_does_not_mutate_input_ledger():
    ledger = _seed()
    of.append_items(ledger, [{"source": "claude", "text": "c"}], reviewed_sha="s")
    assert len(ledger["items"]) == 2 and ledger["reviewed_outline_sha256"] == "oldsha"


def _write_ledger(tmp_path, book, ledger):
    d = tmp_path / "output" / f"book-{book}" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline-feedback.yaml").write_text(of.yaml.safe_dump(ledger), encoding="utf-8")


def _write_outline(tmp_path, book, text):
    d = tmp_path / "input" / f"book-{book}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline.md").write_text(text, encoding="utf-8")


def test_status_nudges_when_no_ledger(tmp_path):
    line = of.status_line("01", repo_root=tmp_path)
    assert "no outline review yet" in line


def test_status_stale_when_outline_changed(tmp_path):
    _write_outline(tmp_path, "01", "new outline text")
    _write_ledger(tmp_path, "01", {"book": "01", "reviewed_outline_sha256": "stale",
                                   "items": [{"id": "OF-1", "source": "claude", "pass": 1,
                                              "state": "open", "text": "x"}]})
    line = of.status_line("01", repo_root=tmp_path)
    assert "changed since" in line and "re-run" in line


def test_status_open_backlog_when_fresh(tmp_path):
    _write_outline(tmp_path, "01", "body")
    sha = of.sha256_of(tmp_path / "input" / "book-01" / "outline.md")
    _write_ledger(tmp_path, "01", {"book": "01", "reviewed_outline_sha256": sha,
        "items": [
            {"id": "OF-1", "source": "claude", "pass": 1, "state": "open", "text": "x"},
            {"id": "OF-2", "source": "codex", "pass": 1, "state": "solved", "text": "y"},
        ]})
    line = of.status_line("01", repo_root=tmp_path)
    assert "1 open" in line and "OF-1" in line


def test_status_clean_when_fresh_and_none_open(tmp_path):
    _write_outline(tmp_path, "01", "body")
    sha = of.sha256_of(tmp_path / "input" / "book-01" / "outline.md")
    _write_ledger(tmp_path, "01", {"book": "01", "reviewed_outline_sha256": sha,
        "items": [{"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "x"}]})
    assert "no open items" in of.status_line("01", repo_root=tmp_path)


def test_status_cli_always_exits_zero(tmp_path, capsys):
    # even with a garbage/absent setup, status must never block a draft
    assert of.main(["status", "99", "--root", str(tmp_path)]) == 0


def test_status_tolerates_malformed_ledger_yaml(tmp_path):
    _write_outline(tmp_path, "01", "body")
    d = tmp_path / "output" / "book-01" / "reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / "outline-feedback.yaml").write_text("items: [unbalanced: [brack", encoding="utf-8")
    line = of.status_line("01", repo_root=tmp_path)
    assert isinstance(line, str)
    assert of.main(["status", "01", "--root", str(tmp_path)]) == 0


def test_status_main_returns_zero_when_resolution_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        of, "status_line",
        lambda *a, **k: (_ for _ in ()).throw(SystemExit("no series root")),
    )
    assert of.main(["status", "01", "--root", str(tmp_path)]) == 0


def test_status_subprocess_exits_zero_without_series_root(tmp_path):
    # This is the real path /draft-chapter's Step 0b hits: `status $1` with NO
    # --root, so penny_paths.series_root() walks up from cwd looking for a
    # .penny/ marker. tmp_path has none — series_root() would sys.exit — so
    # this proves the exit-0 guarantee holds end-to-end, not just when
    # status_line/--root are mocked/supplied.
    script = Path(__file__).resolve().parents[1] / "scripts" / "outline_feedback.py"
    result = subprocess.run(
        [sys.executable, str(script), "status", "01"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_cli_append_writes_ledger_and_view(tmp_path):
    _write_outline(tmp_path, "01", "the outline body")
    points = tmp_path / "pts.json"
    points.write_text(of.json.dumps([
        {"source": "claude", "text": "romance thin ch7-11"},
        {"source": "codex", "text": "ch9 beat too vague"},
    ]), encoding="utf-8")

    rc = of.main(["append", "01", "--points", str(points), "--root", str(tmp_path)])
    assert rc == 0

    ledger = of.load_ledger("01", repo_root=tmp_path)
    assert [it["id"] for it in ledger["items"]] == ["OF-1", "OF-2"]
    assert all(it["state"] == "open" and it["pass"] == 1 for it in ledger["items"])
    assert ledger["reviewed_outline_sha256"] == of.sha256_of(
        tmp_path / "input" / "book-01" / "outline.md")
    assert of.view_path("01", repo_root=tmp_path).is_file()

    # second pass appends without disturbing the first pass's items/states
    (tmp_path / "input" / "book-01" / "outline.md").write_text("edited body", encoding="utf-8")
    points.write_text(of.json.dumps([{"source": "claude", "text": "new concern"}]), encoding="utf-8")
    of.main(["append", "01", "--points", str(points), "--root", str(tmp_path)])
    ledger2 = of.load_ledger("01", repo_root=tmp_path)
    assert [it["id"] for it in ledger2["items"]] == ["OF-1", "OF-2", "OF-3"]
    assert ledger2["items"][2] == {"id": "OF-3", "source": "claude", "pass": 2,
                                   "state": "open", "text": "new concern"}


def test_render_groups_open_first_and_tags_source():
    ledger = {"book": "01", "reviewed_outline_sha256": "s", "items": [
        {"id": "OF-1", "source": "claude", "pass": 1, "state": "solved", "text": "fixed ch9"},
        {"id": "OF-2", "source": "codex", "pass": 1, "state": "open", "text": "romance thin"},
        {"id": "OF-3", "source": "claude", "pass": 1, "state": "rejected", "text": "disagree"},
    ]}
    md = of.render_view(ledger)
    assert md.index("Open") < md.index("Solved") < md.index("Rejected")
    assert "OF-2" in md and "codex" in md and "romance thin" in md
    # a purely-solved/rejected item still appears, just not under Open
    assert "OF-1" in md and "OF-3" in md
