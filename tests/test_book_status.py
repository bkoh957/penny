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


def test_unreadable_lock_file_reports_unknown_and_other_rows_render(tmp_path):
    """A corrupted or partially-written lock file with invalid UTF-8 must not
    crash book_rows(). The lock row should report unknown, and the other three
    rows should render normally."""
    root = _series(tmp_path)
    _write_outline(root)
    # Write a lock file with invalid UTF-8
    d = root / ".penny" / "locks"
    d.mkdir(parents=True, exist_ok=True)
    (d / "book-01.mystery.lock").write_bytes(b"book: 01\ninvalid: \xff\xfe\n")

    rows = book_status.book_rows("01", root)
    lock_row = _row(rows, "lock")

    # Lock row should report unknown, not crash
    assert lock_row.run.ok is True
    assert lock_row.passed.kind == "unknown"
    assert "could not be read" in lock_row.reason.lower() or "decode" in lock_row.reason.lower()

    # Other three rows should still render normally
    outline_row = _row(rows, "outline")
    assert outline_row.run.ok is True
    assert outline_row.passed.ok is True

    diagnostics_row = _row(rows, "diagnostics")
    assert diagnostics_row.run.ok is False  # no diagnostic views created

    feedback_row = _row(rows, "feedback")
    assert feedback_row.run.ok is False  # no feedback ledger


def test_unreadable_outline_source_reports_unknown(tmp_path):
    """If the source file the lock names cannot be read, report unknown."""
    root = _series(tmp_path)
    _write_outline(root)
    # Create a lock that points to a non-existent file
    _write_lock(root, "book: 01\nvalidated: fairplay\n"
                      "outline_source: input/book-01/nonexistent.md\n"
                      "outline_sha256: " + ("0" * 64) + "\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.kind == "unknown"
    assert "no longer exists" in r.reason.lower()


def test_absolute_path_in_outline_source_is_rejected(tmp_path):
    """An absolute path in outline_source escapes the series root and must be
    rejected, not read."""
    root = _series(tmp_path)
    _write_outline(root)
    # Create a lock with absolute path (should be rejected for security)
    _write_lock(root, "book: 01\nvalidated: fairplay\n"
                      "outline_source: /etc/passwd\n"
                      "outline_sha256: " + ("0" * 64) + "\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.kind == "unknown"
    assert "outside" in r.reason.lower() or "escape" in r.reason.lower()


def test_dotdot_escape_in_outline_source_is_rejected(tmp_path):
    """A relative path with .. that escapes the series root must be rejected."""
    root = _series(tmp_path)
    _write_outline(root)
    # Create a lock with escaping relative path
    _write_lock(root, "book: 01\nvalidated: fairplay\n"
                      "outline_source: ../../etc/passwd\n"
                      "outline_sha256: " + ("0" * 64) + "\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.kind == "unknown"
    assert "outside" in r.reason.lower() or "escape" in r.reason.lower()


def _chapters_dir(root):
    d = root / "output" / "book-01" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_total_chapters_comes_from_the_outline_frontmatter(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    assert book_status.total_chapters("01", root) == 2


def test_total_chapters_is_none_when_the_outline_does_not_declare_it(tmp_path):
    root = _series(tmp_path)
    _write_outline(root, "---\nbook: 01\n---\n\n## Chapter 01 — A\n")
    assert book_status.total_chapters("01", root) is None


def test_count_rows_are_unknown_when_total_chapters_is_unknown(tmp_path):
    """A count with no denominator is a guess. Report that it cannot be
    computed rather than inventing a total from whichever directory is fullest."""
    root = _series(tmp_path)
    _write_outline(root, "---\nbook: 01\n---\n\n## Chapter 01 — A\n")
    for r in book_status.chapter_rows("01", root):
        assert r.run.kind == "unknown" or r.passed.kind == "unknown"


def test_drafts_row_counts_draft_files(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").write_text("x\n", encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "drafts")
    assert (r.run.done, r.run.total) == (1, 2)
    assert r.run.ok is False


def test_drafts_row_passes_only_when_every_chapter_has_one(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    for n in ("01", "02"):
        (d / f"ch-{n}.draft.md").write_text("x\n", encoding="utf-8")
    assert _row(book_status.chapter_rows("01", root), "drafts").run.ok is True


def test_gates_row_counts_only_passing_gates(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.gate.md").write_text("gate: PASS\n", encoding="utf-8")
    (d / "ch-02.gate.md").write_text("gate: HOLD\n", encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "gates")
    assert r.run.kind == "na"
    assert (r.passed.done, r.passed.total) == (1, 2)


def test_dev_cleared_counts_only_certs_bound_to_the_current_draft(tmp_path):
    """The cert records cleared_draft_sha256 — a cert for a draft that has since
    been edited is not a clearance for the draft on disk."""
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    draft = d / "ch-01.draft.md"
    draft.write_text("current text\n", encoding="utf-8")
    (d / "ch-02.draft.md").write_text("other\n", encoding="utf-8")
    locks = root / ".penny" / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    good = hashlib.sha256(draft.read_bytes()).hexdigest()
    (locks / "book-01.ch-01.dev-clear").write_text(
        f"---\ncleared_draft_sha256: {good}\n---\n", encoding="utf-8")
    (locks / "book-01.ch-02.dev-clear").write_text(
        "---\ncleared_draft_sha256: " + ("0" * 64) + "\n---\n", encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "dev-cleared")
    assert (r.passed.done, r.passed.total) == (1, 2)


def test_packets_row_reports_stale_packets_as_not_passed(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    pk = root / "input" / "book-01" / "packets"
    pk.mkdir(parents=True, exist_ok=True)
    (pk / "ch-01.md").write_text(
        "---\nbuilt_from_outline: deadbeef\n---\n\n### Required Beats\n- x\n",
        encoding="utf-8")
    r = _row(book_status.chapter_rows("01", root), "packets")
    assert (r.run.done, r.run.total) == (1, 2)
    assert r.passed.done == 0


def test_gate_file_with_invalid_utf8_reports_unknown_and_other_rows_render(tmp_path):
    """A gate file with invalid UTF-8 raises UnicodeDecodeError out of
    chapter_rows() and kills all six rows. Instead, the gates row should report
    unknown and the other rows should render normally."""
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.gate.md").write_bytes(b"gate: PASS\n")
    (d / "ch-02.gate.md").write_bytes(b"invalid: \xff\xfe\n")
    rows = book_status.chapter_rows("01", root)
    gates_row = _row(rows, "gates")
    assert gates_row.passed.kind == "unknown"
    assert "ch-02" in gates_row.reason.lower()
    # Other rows must still render
    assert _row(rows, "packets").run.kind in ("count", "unknown")
    assert _row(rows, "drafts").run.kind in ("count", "unknown")


def test_unreadable_dev_clear_cert_reports_unknown_and_other_rows_render(tmp_path):
    """A dev-clear cert with invalid UTF-8 raises UnicodeDecodeError out of
    chapter_rows() and kills all six rows. Instead, the dev-cleared row should
    report unknown and the other rows should render normally."""
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").write_text("text\n", encoding="utf-8")
    (d / "ch-02.draft.md").write_text("text\n", encoding="utf-8")
    locks = root / ".penny" / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    (locks / "book-01.ch-01.dev-clear").write_bytes(b"valid\n")
    (locks / "book-01.ch-02.dev-clear").write_bytes(b"invalid: \xff\xfe\n")
    rows = book_status.chapter_rows("01", root)
    devclear_row = _row(rows, "dev-cleared")
    assert devclear_row.passed.kind == "unknown"
    assert "ch-02" in devclear_row.reason.lower()
    # Other rows must still render
    assert _row(rows, "packets").run.kind in ("count", "unknown")
    assert _row(rows, "gates").run.kind in ("na", "unknown")


def test_directory_named_like_a_chapter_file_does_not_crash(tmp_path):
    """A stray directory named ch-01.draft.md/ must not crash chapter_rows when
    the dev-cleared loop tries to process it. Pre-fix, glob() would match the
    directory, add it to drafts, and then _sha(directory) raises IsADirectoryError
    out of chapter_rows(). With .is_file() filter, the directory never enters
    drafts, so the loop never tries to process it."""
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").mkdir()  # Directory, not file
    (d / "ch-02.draft.md").write_text("text\n", encoding="utf-8")
    # Add dev-clear certs for both chapters so loop tries to process both
    locks = root / ".penny" / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    (locks / "book-01.ch-01.dev-clear").write_text(
        "---\ncleared_draft_sha256: " + ("0" * 64) + "\n---\n", encoding="utf-8")
    good_sha = hashlib.sha256((d / "ch-02.draft.md").read_bytes()).hexdigest()
    (locks / "book-01.ch-02.dev-clear").write_text(
        f"---\ncleared_draft_sha256: {good_sha}\n---\n", encoding="utf-8")
    # Must not crash despite directory matching glob pattern
    rows = book_status.chapter_rows("01", root)
    devclear_row = _row(rows, "dev-cleared")
    assert devclear_row.passed.kind in ("count", "unknown")
    # Only the real file should be in drafts, not the directory
    drafts_row = _row(rows, "drafts")
    assert drafts_row.run.done == 1  # Only ch-02, not ch-01 directory
    assert drafts_row.run.total == 2
