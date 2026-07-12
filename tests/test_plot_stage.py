from pathlib import Path

from scripts.plot_stage import (STAGE_ORDER, next_stage, stage_paths, stage_status, stamp)


def _series(tmp_path, book="01"):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / f"book-{book}" / "plot").mkdir(parents=True)
    (tmp_path / "output" / f"book-{book}" / "reports").mkdir(parents=True)
    return tmp_path


def _write(root, rel, text="---\n---\nbody\n"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_stage_order_is_the_spec_order():
    assert STAGE_ORDER == ["premise", "ending", "turning-points", "counterplot",
                           "chapters", "weave", "readback"]


def test_all_missing_next_is_premise(tmp_path):
    root = _series(tmp_path)
    rows = stage_status("01", repo_root=root)
    assert all(state == "missing" for _, state, _ in rows)
    assert next_stage(rows) == "premise"


def test_stamped_stage_is_done_and_edit_upstream_makes_it_stale(tmp_path):
    root = _series(tmp_path)
    prem = _write(root, "input/book-01/plot/premise.md")   # material absent: optional
    end = _write(root, "input/book-01/plot/ending.md")
    stamp("01", end, [prem], repo_root=root)
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["premise"] == "done" and rows["ending"] == "done"
    prem.write_text(prem.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["ending"] == "stale"


def test_premise_stale_when_material_present_but_unstamped(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/plot/material.md")
    _write(root, "input/book-01/plot/premise.md")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["premise"] == "stale"


def test_weave_needs_woven_flag(tmp_path):
    root = _series(tmp_path)
    skel = _write(root, "input/book-01/outline-skeleton.md")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["weave"] == "missing"
    skel.write_text("---\nwoven: true\n---\nbody\n", encoding="utf-8")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["weave"] == "done"


def test_stamp_creates_frontmatter_if_absent(tmp_path):
    root = _series(tmp_path)
    prem = _write(root, "input/book-01/plot/premise.md", "no frontmatter here\n")
    end = _write(root, "input/book-01/plot/ending.md", "also bare\n")
    stamp("01", end, [prem], repo_root=root)
    assert "built_from_premise:" in end.read_text(encoding="utf-8")
