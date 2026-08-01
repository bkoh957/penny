import hashlib
from pathlib import Path

import pytest

from scripts import book_status


def _series(tmp_path):
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-01").mkdir(parents=True)
    (tmp_path / "output" / "book-01").mkdir(parents=True)
    return tmp_path


OUTLINE = """---
book: 01
total_chapters: 2
---

# Outline

## Solution
culprit is x.

## Chapter 01 — A

### Required Beats
- a beat.

## Chapter 02 — B

### Required Beats
- another beat.
"""


def _write_outline(root, text=OUTLINE):
    p = root / "input" / "book-01" / "outline.md"
    p.write_text(text, encoding="utf-8")
    return p


def _row(rows, row_id):
    return next(r for r in rows if r.id == row_id)


def test_outline_row_is_not_run_when_there_is_no_outline(tmp_path):
    root = _series(tmp_path)
    r = _row(book_status.book_rows("01", root), "outline")
    assert r.run.kind == "bool" and r.run.ok is False


def test_outline_row_runs_and_passes_for_a_well_shaped_outline(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    r = _row(book_status.book_rows("01", root), "outline")
    assert r.run.ok is True
    assert r.passed.ok is True


def test_diagnostics_row_has_nothing_to_pass(tmp_path):
    """`—` is not a pending state and must never render as a failure."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-glance.md").write_text("# g\n", encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "diagnostics")
    assert r.run.ok is True
    assert r.passed.kind == "na"


def test_feedback_row_fails_while_items_are_open(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "items:\n  - {id: OF-1, state: open}\n  - {id: OF-2, state: solved}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.run.ok is True
    assert r.passed.ok is False
    assert "1 open" in r.reason


def test_feedback_row_passes_when_every_item_is_dispositioned(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "items:\n  - {id: OF-1, state: solved}\n  - {id: OF-2, state: rejected}\n",
        encoding="utf-8")
    assert _row(book_status.book_rows("01", root), "feedback").passed.ok is True


def _write_lock(root, body):
    d = root / ".penny" / "locks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "book-01.mystery.lock").write_text(body, encoding="utf-8")


def test_lock_row_passes_when_the_fingerprint_matches(tmp_path):
    root = _series(tmp_path)
    p = _write_outline(root)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    _write_lock(root, f"book: 01\nvalidated: fairplay\n"
                      f"outline_source: input/book-01/outline.md\n"
                      f"outline_sha256: {sha}\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.ok is True


def test_lock_row_is_stale_when_the_outline_changed_since(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay\n"
                      "outline_source: input/book-01/outline.md\n"
                      "outline_sha256: " + ("0" * 64) + "\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.passed.ok is False
    assert "stale" in r.reason.lower()


def test_a_legacy_lock_reports_unknown_never_fresh_and_never_stale(tmp_path):
    """The sharpest rule in the spec: a certificate must not claim coverage it
    does not have. A lock minted before 7cb2f4e carries no fingerprint, so the
    honest answer is that the question cannot be answered."""
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay+lexicon\n"
                      "locked_at: 2026-07-28T03:10:33+00:00\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.kind == "unknown"
    assert "unknown" in r.reason.lower()


def test_lock_row_compares_against_the_source_the_lock_names(tmp_path):
    """lock-mystery prefers outline-skeleton.md, so the lock records WHICH file
    it validated. Comparing against outline.md regardless would report a
    confident wrong answer."""
    root = _series(tmp_path)
    _write_outline(root)
    skel = root / "input" / "book-01" / "outline-skeleton.md"
    skel.write_text("# skeleton\n", encoding="utf-8")
    sha = hashlib.sha256(skel.read_bytes()).hexdigest()
    _write_lock(root, f"book: 01\nvalidated: fairplay\n"
                      f"outline_source: input/book-01/outline-skeleton.md\n"
                      f"outline_sha256: {sha}\n")
    assert _row(book_status.book_rows("01", root), "lock").passed.ok is True


def test_every_row_carries_a_command_and_an_artefact(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    for r in book_status.book_rows("01", root):
        assert r.command, f"{r.id} has no command"
        assert r.artefact, f"{r.id} has no artefact"
