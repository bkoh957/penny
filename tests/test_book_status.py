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
    p = _write_outline(root)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        f"reviewed_outline_sha256: {sha}\n"
        "items:\n  - {id: OF-1, state: open}\n  - {id: OF-2, state: solved}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.run.ok is True
    assert r.passed.ok is False
    assert "1 open" in r.reason


def test_feedback_row_passes_when_every_item_is_dispositioned(tmp_path):
    root = _series(tmp_path)
    p = _write_outline(root)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        f"reviewed_outline_sha256: {sha}\n"
        "items:\n  - {id: OF-1, state: solved}\n  - {id: OF-2, state: rejected}\n",
        encoding="utf-8")
    assert _row(book_status.book_rows("01", root), "feedback").passed.ok is True


def test_feedback_row_fails_when_stamp_mismatches_even_with_zero_open_items(tmp_path):
    """I2: the ledger's reviewed_outline_sha256 stamp must be honoured. A
    ledger with zero open items but a stamp that does not match the outline
    on disk must NOT report PASSED — the outline reviewed no longer exists."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "reviewed_outline_sha256: " + ("0" * 64) + "\n"
        "items:\n  - {id: OF-1, state: solved}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.run.ok is True
    assert r.passed.ok is False
    assert "stale" in r.reason.lower() or "changed" in r.reason.lower()


def test_feedback_row_fix_command_names_the_ledger_not_review_outline(tmp_path):
    """I1: the fix for an open backlog is hand-editing state:, not re-running
    /review-outline, which would append a second pass and grow the backlog."""
    root = _series(tmp_path)
    p = _write_outline(root)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        f"reviewed_outline_sha256: {sha}\n"
        "items:\n  - {id: OF-1, state: open}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.fix_command
    assert "review-outline" not in r.fix_command
    assert "outline-feedback.yaml" in r.fix_command


def test_feedback_row_unparseable_ledger_reports_unknown_not_stale(tmp_path):
    """N1: a genuinely unparseable ledger (bad indent) must land on the `?`
    footer with a named reason — never claim STALE (the outline did not
    change) and never fall through to /review-outline, which would
    silently overwrite every hand-set state: on the next append."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "reviewed_outline_sha256: abc\n"
        "items:\n"
        "  - {id: OF-1, state: open}\n"
        "   bad_indent: true\n",
        encoding="utf-8")
    rows = book_status.book_rows("01", root)
    r = _row(rows, "feedback")
    assert r.passed.kind == "unknown"
    assert r.reason
    assert "stale" not in r.reason.lower()
    # other rows still render
    assert _row(rows, "outline").passed.ok is True
    # excluded from next: selection
    assert r in book_status.unknown_rows(rows)
    nxt = book_status.next_action(rows)
    assert nxt is None or nxt.id != "feedback"


def test_feedback_row_ledger_is_a_list_reports_unknown_not_stale(tmp_path):
    """N1: a ledger that parses cleanly but to a YAML list rather than a
    mapping is exactly as unreadable as a syntax error — must not report
    STALE, must land on the `?` footer, and must not be selected as next."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "- id: OF-1\n  state: open\n", encoding="utf-8")
    rows = book_status.book_rows("01", root)
    r = _row(rows, "feedback")
    assert r.passed.kind == "unknown"
    assert r.reason
    assert "stale" not in r.reason.lower()
    assert _row(rows, "outline").passed.ok is True
    assert r in book_status.unknown_rows(rows)
    nxt = book_status.next_action(rows)
    assert nxt is None or nxt.id != "feedback"


def test_feedback_row_empty_stamp_with_open_items_is_not_stale(tmp_path):
    """N2: /plot-book's fan-audit items append with --source, which
    deliberately leaves reviewed_outline_sha256 empty because no review
    panel ever read outline.md. Once /expand-outline later writes
    outline.md, that empty stamp must NOT be read as a mismatch — the row
    must keep counting open items and keep its fix_command, not flip to
    STALE and lose the backlog."""
    root = _series(tmp_path)
    _write_outline(root)  # outline.md now exists, as it would post-expand
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "reviewed_outline_sha256: ''\n"
        "items:\n  - {id: OF-1, source: fan-audit, state: open}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.passed.kind != "unknown"
    assert "stale" not in r.reason.lower()
    assert r.passed.ok is False
    assert "1 open" in r.reason
    assert r.fix_command
    assert "outline-feedback.yaml" in r.fix_command


def test_feedback_row_shipped_i2_stale_case_still_fails(tmp_path):
    """Regression guard: the shipped I2 behaviour — a NON-EMPTY stamp that
    mismatches the outline on disk fails even with zero open items — must
    not regress while fixing N1/N2."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-feedback.yaml").write_text(
        "reviewed_outline_sha256: " + ("0" * 64) + "\n"
        "items:\n  - {id: OF-1, state: solved}\n",
        encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "feedback")
    assert r.run.ok is True
    assert r.passed.kind != "unknown"
    assert r.passed.ok is False
    assert "stale" in r.reason.lower() or "changed" in r.reason.lower()


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
    """book_status compares against whatever outline_source the cert names, not
    a hardcoded outline.md — e.g. a lock minted before outline-skeleton.md's
    retirement may still name it as the source it validated. Comparing against
    outline.md regardless would report a confident wrong answer."""
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


def test_nul_byte_in_outline_source_reports_unknown_not_a_traceback(tmp_path):
    """C1: a fifth unguarded read. `outline_source` containing an embedded NUL
    byte makes Path.resolve() raise ValueError('lstat: embedded null character
    in path') — this must degrade the lock row to unknown, not crash book_rows
    (and therefore the whole report) with an uncaught exception."""
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay\n"
                      "outline_source: input/book-01/x\x00y.md\n"
                      "outline_sha256: " + ("0" * 64) + "\n")
    r = _row(book_status.book_rows("01", root), "lock")
    assert r.run.ok is True
    assert r.passed.kind == "unknown"


def test_sha_raises_a_named_error_for_a_non_file_path(tmp_path):
    """Close the class permanently: _sha() itself should refuse a non-file
    path with a named ValueError rather than letting an OSError (e.g.
    IsADirectoryError) escape from whichever call site forgot to pre-filter."""
    with pytest.raises(ValueError):
        book_status._sha(tmp_path)


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


def test_packets_row_prefers_the_total_unknown_reason_over_a_staleness_failure(
        tmp_path, monkeypatch):
    """M10: when total_chapters is undeclared AND stale_packets() itself
    throws, the row must keep naming the more useful problem (no
    total_chapters) rather than letting the staleness exception's message
    overwrite it."""
    root = _series(tmp_path)
    _write_outline(root, "---\nbook: 01\n---\n\n## Chapter 01 — A\n")  # no total_chapters
    import scripts.packet_assemble as pa

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(pa, "stale_packets", boom)
    r = _row(book_status.chapter_rows("01", root), "packets")
    assert r.passed.kind == "unknown"
    assert r.reason == book_status._UNKNOWN_TOTAL


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


def _r(row_id, run, passed):
    return book_status.Row(row_id, row_id, run, passed, "cmd", "path")


def test_next_is_the_first_run_but_not_passed_row():
    rows = [_r("a", book_status.yes(), book_status.yes()),
            _r("b", book_status.yes(), book_status.no()),
            _r("c", book_status.no(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_next_prefers_fixing_over_starting():
    """A half-done thing outranks an unstarted one — that is the whole rule."""
    rows = [_r("a", book_status.no(), book_status.no()),
            _r("b", book_status.yes(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_next_falls_through_to_the_first_unrun_row():
    rows = [_r("a", book_status.yes(), book_status.yes()),
            _r("b", book_status.no(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_a_partly_done_count_row_is_run_but_not_passed():
    rows = [_r("a", book_status.count(3, 28), book_status.na())]
    assert book_status.next_action(rows).id == "a"


def test_an_na_passed_cell_never_makes_a_row_fail():
    rows = [_r("a", book_status.yes(), book_status.na()),
            _r("b", book_status.no(), book_status.no())]
    assert book_status.next_action(rows).id == "b"


def test_an_na_run_cell_is_judged_only_on_passed():
    rows = [_r("a", book_status.na(), book_status.count(0, 28))]
    assert book_status.next_action(rows).id == "a"


def test_unknown_rows_are_never_selected_as_next():
    """Guessing a next action from a fact the engine admits it does not have is
    exactly the failure this replaces."""
    rows = [_r("a", book_status.yes(), book_status.unknown()),
            _r("b", book_status.yes(), book_status.no())]
    assert book_status.next_action(rows).id == "b"
    assert [r.id for r in book_status.unknown_rows(rows)] == ["a"]


def test_next_is_none_when_everything_has_passed():
    rows = [_r("a", book_status.yes(), book_status.yes())]
    assert book_status.next_action(rows) is None


def test_manuscript_row_passes_only_with_an_approved_cert(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    (root / "output" / "book-01" / "book-01.manuscript.md").write_text(
        "x\n", encoding="utf-8")
    r = _row(book_status.tail_rows("01", root), "manuscript")
    assert r.run.ok is True and r.passed.ok is False
    (root / ".penny" / "locks").mkdir(parents=True, exist_ok=True)
    (root / ".penny" / "locks" / "book-01.approved").write_text("x\n", encoding="utf-8")
    assert _row(book_status.tail_rows("01", root), "manuscript").passed.ok is True


def test_manuscript_row_fix_command_adds_approve_flag_not_a_re_assemble(tmp_path):
    """I1: assembled-but-not-approved must fix forward with --approve, not
    print the bare /assemble-book command, which would re-run the cross-model
    final read for no reason."""
    root = _series(tmp_path)
    _write_outline(root)
    (root / "output" / "book-01" / "book-01.manuscript.md").write_text(
        "x\n", encoding="utf-8")
    r = _row(book_status.tail_rows("01", root), "manuscript")
    assert r.fix_command
    assert "--approve" in r.fix_command
    assert r.fix_command != r.command


def test_render_prefers_fix_command_over_command_when_both_are_set():
    """The row body still shows `command` (every row's create action stays
    visible); only the `next:` footer line — the one the showrunner actually
    acts on — prefers fix_command."""
    r = book_status.Row("x", "x", book_status.yes(), book_status.no(),
                         "the-create-command", "path",
                         fix_command="the-fix-command")
    out = book_status.render("01", [r], r, [])
    next_line = next(l for l in out.splitlines() if l.startswith("next:"))
    assert "the-fix-command" in next_line
    assert "the-create-command" not in next_line


def test_beta_row_runs_when_converged_reports_exist(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = root / "output" / "book-01" / "beta-reports"
    d.mkdir(parents=True, exist_ok=True)
    (d / "cosy-reader.converged.md").write_text("x\n", encoding="utf-8")
    r = _row(book_status.tail_rows("01", root), "beta")
    assert r.run.ok is True and r.passed.kind == "na"


def test_book_01_shape_selects_the_feedback_row(tmp_path):
    """The real case: an outline that passes, diagnostics run, a feedback ledger
    with open items, and a lock. plot_stage.py says 'next: premise' for this
    shape — go rewrite the premise of a book shaped by hand for weeks."""
    root = _series(tmp_path)
    _write_outline(root)
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True)
    (reports / "outline-glance.md").write_text("# g\n", encoding="utf-8")
    (reports / "outline-feedback.yaml").write_text(
        "items:\n  - {id: OF-1, state: open}\n", encoding="utf-8")
    _write_lock(root, "book: 01\nvalidated: fairplay\n")
    assert book_status.next_action(book_status.all_rows("01", root)).id == "feedback"


def test_na_run_cell_with_0_passed_count_does_not_win_over_unstarted():
    """A na()-RUN row with a 0/28 PASSED count must not be selected over an
    unstarted row. gates and dev-cleared have this shape. Once an outline is
    locked, their passed count becomes count(0, 28), but that is not evidence
    that the step ran."""
    rows = [
        _r("packets", book_status.count(0, 28), book_status.na()),     # unstarted
        _r("gates", book_status.na(), book_status.count(0, 28)),       # na run, 0 passed
    ]
    assert book_status.next_action(rows).id == "packets"


def test_locked_outline_clean_feedback_no_drafts_selects_packets(tmp_path):
    """The critical real-world shape: an outline that passes, diagnostics run,
    feedback clean (all items closed), lock in place, but no chapter work
    at all. The correct next action is 'packets', not 'gates'."""
    root = _series(tmp_path)
    _write_outline(root)

    # Lock the outline
    p_outline = root / "input" / "book-01" / "outline.md"
    sha = hashlib.sha256(p_outline.read_bytes()).hexdigest()
    _write_lock(root, f"book: 01\nvalidated: fairplay\n"
                      f"outline_source: input/book-01/outline.md\n"
                      f"outline_sha256: {sha}\n")

    # Add clean feedback (all items closed), stamped against the current outline
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "outline-glance.md").write_text("# g\n", encoding="utf-8")
    (reports / "outline-feedback.yaml").write_text(
        f"reviewed_outline_sha256: {sha}\n"
        "items:\n  - {id: OF-1, state: solved}\n  - {id: OF-2, state: rejected}\n",
        encoding="utf-8")

    # No chapter work at all
    # No packets, maps, drafts, finals, gates, or dev-clear certs

    rows = book_status.all_rows("01", root)
    next_row = book_status.next_action(rows)
    assert next_row is not None, "Should have a next action"
    assert next_row.id == "packets", f"Expected 'packets', got '{next_row.id}'"


import subprocess
import sys
import os


def test_render_cell_shapes():
    assert book_status.render_cell(book_status.yes()) == "✓"
    assert book_status.render_cell(book_status.no()) == "✗"
    assert book_status.render_cell(book_status.na()) == "—"
    assert book_status.render_cell(book_status.unknown()) == "?"
    assert book_status.render_cell(book_status.count(3, 28)) == "3/28"


def test_render_includes_every_row_its_command_and_its_artefact(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    rows = book_status.all_rows("01", root)
    out = book_status.render("01", rows, book_status.next_action(rows),
                             book_status.unknown_rows(rows))
    for r in rows:
        assert r.label in out
        assert r.command in out
    assert "next:" in out


def test_render_names_unknown_rows_beneath_next(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    _write_lock(root, "book: 01\nvalidated: fairplay\n")   # legacy, no fingerprint
    rows = book_status.all_rows("01", root)
    out = book_status.render("01", rows, book_status.next_action(rows),
                             book_status.unknown_rows(rows))
    assert "mystery lock" in out
    assert "unknown" in out.lower()


def test_one_chapter_rows_cover_the_per_chapter_pipeline(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").write_text("x\n", encoding="utf-8")
    ids = [r.id for r in book_status.one_chapter_rows("01", "01", root)]
    assert ids == ["packet", "map", "draft", "gate", "dev-clear", "final"]
    assert _row(book_status.one_chapter_rows("01", "01", root), "draft").run.ok is True


def _run(cwd, *args):
    env = dict(os.environ, PYTHONPATH=str(Path.cwd()))
    return subprocess.run(
        [sys.executable, str(Path.cwd() / "scripts" / "book_status.py"), *args],
        cwd=cwd, capture_output=True, text=True, env=env)


def test_cli_exits_zero_even_when_every_row_fails(tmp_path):
    """A report is not a gate. A book with everything undone is a SUCCESSFUL
    run of book-status."""
    root = _series(tmp_path)
    _write_outline(root)
    proc = _run(root, "01")
    assert proc.returncode == 0, proc.stderr
    assert "next:" in proc.stdout


def test_cli_refuses_a_book_with_no_outline(tmp_path):
    root = _series(tmp_path)
    proc = _run(root, "01")
    assert proc.returncode == 2
    assert "outline" in (proc.stdout + proc.stderr).lower()


def test_cli_exits_one_outside_a_series(tmp_path):
    """M1 ruling: the house convention wins. Every other engine script exits
    1 via penny_paths.series_root()'s sys.exit(msg); book_status must match,
    not carve out its own exit 2 for this case. tmp_path has no .penny/
    marker anywhere above it, so this is genuinely outside a series."""
    proc = _run(tmp_path, "01")
    assert proc.returncode == 1
    assert "series" in (proc.stdout + proc.stderr).lower()


def test_cli_refuses_a_traversal_book_id(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    proc = _run(root, "01/../../etc")
    assert proc.returncode == 2
    assert "invalid" in (proc.stdout + proc.stderr).lower()


def test_cli_writes_nothing(tmp_path):
    """The module's central promise. Nothing is created — not even a reports dir."""
    root = _series(tmp_path)
    _write_outline(root)
    before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    names_before = {str(p.relative_to(root)) for p in root.rglob("*")}
    assert _run(root, "01").returncode == 0
    names_after = {str(p.relative_to(root)) for p in root.rglob("*")}
    after = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
    assert names_before == names_after, "book-status created something"
    assert before == after, "book-status modified something"


def test_cli_drills_into_one_chapter(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    proc = _run(root, "01", "01")
    assert proc.returncode == 0, proc.stderr
    assert "packet" in proc.stdout and "final" in proc.stdout


# --- fix round 1: a bad byte in outline.md must never crash the report -----

def test_total_chapters_is_none_when_the_outline_is_not_valid_utf8(tmp_path):
    root = _series(tmp_path)
    p = root / "input" / "book-01" / "outline.md"
    p.write_bytes(b"---\nbook: 01\ntotal_chapters: 2\n---\n\n## Chapter 01\n\xff\xfe\n")
    assert book_status.total_chapters("01", root) is None


def test_unreadable_outline_gives_a_distinct_reason_not_the_missing_key_message(tmp_path):
    """A failed read and a missing frontmatter key are different problems with
    different fixes. Telling a writer to add total_chapters: when the key is
    already there — it's just that one stray byte made the file unreadable —
    sends them chasing the wrong thing."""
    root = _series(tmp_path)
    p = root / "input" / "book-01" / "outline.md"
    p.write_bytes(b"---\nbook: 01\ntotal_chapters: 2\n---\n\n## Chapter 01\n\xff\xfe\n")
    r = _row(book_status.chapter_rows("01", root), "maps")
    assert r.run.kind == "unknown"
    assert "could not be read" in r.reason.lower()
    assert r.reason != book_status._UNKNOWN_TOTAL
    assert "not declared" not in r.reason.lower()


def test_cli_exits_zero_with_a_non_utf8_byte_in_the_outline(tmp_path):
    """The book IS readable — it has one bad byte. That must never traceback
    or turn a readable report into exit 1."""
    root = _series(tmp_path)
    p = root / "input" / "book-01" / "outline.md"
    p.write_bytes(b"---\nbook: 01\ntotal_chapters: 2\n---\n\n## Chapter 01\n\xff\xfe\n")
    proc = _run(root, "01")
    assert proc.returncode == 0, proc.stderr
    assert "Traceback" not in proc.stderr
    assert "next:" in proc.stdout


# --- fix round 1: one_chapter_rows failure paths, tested rather than only
# defended by inspection -----------------------------------------------------

def test_one_chapter_rows_gate_unreadable_reports_unknown_and_others_render(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.gate.md").write_bytes(b"gate: PASS\n\xff\xfe\n")
    rows = book_status.one_chapter_rows("01", "01", root)
    gate_row = _row(rows, "gate")
    assert gate_row.passed.kind == "unknown"
    assert "could not be read" in gate_row.reason.lower()
    # other rows must still render
    assert _row(rows, "packet").run.kind == "bool"
    assert _row(rows, "draft").run.kind == "bool"
    assert _row(rows, "final").run.kind == "bool"


def test_one_chapter_rows_dev_clear_cert_unreadable_reports_unknown_and_others_render(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    d = _chapters_dir(root)
    (d / "ch-01.draft.md").write_text("text\n", encoding="utf-8")
    locks = root / ".penny" / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    (locks / "book-01.ch-01.dev-clear").write_bytes(b"cleared_draft_sha256: \xff\xfe\n")
    rows = book_status.one_chapter_rows("01", "01", root)
    dc_row = _row(rows, "dev-clear")
    assert dc_row.passed.kind == "unknown"
    assert "could not be read" in dc_row.reason.lower()
    # other rows must still render
    assert _row(rows, "draft").run.ok is True
    assert _row(rows, "gate").run.ok is False


# --- fix round 1: drill-down artefact paths must be relative, like the
# book-level rows, not absolute --------------------------------------------

def test_one_chapter_rows_artefacts_are_relative_to_the_series_root(tmp_path):
    root = _series(tmp_path)
    _write_outline(root)
    rows = book_status.one_chapter_rows("01", "01", root)
    for r in rows:
        assert not Path(r.artefact).is_absolute(), f"{r.id} artefact is absolute: {r.artefact}"
    assert _row(rows, "draft").artefact == "output/book-01/chapters/ch-01.draft.md"


# --- the story layer (spec 2026-08-03): three rows above the outline, because
# since the source layer the outline is a build product and the table was
# reporting on the output while the author worked on the input ---------------

STORY = """---
book: 01
---

# Story — book 01

- Maggie chooses this life. @maggie #establish-protected-world +q-clear
- The vase is wrong. @maggie #crime-and-first-contradiction -q-clear !c-vase

## Questions
- q-clear — how can Maggie clear herself?
"""

CUT_PLAN = """## Chapter 01 — One

- **Beats:** 1
- **Summary:** s
- **Compress:** c

## Chapter 02 — Two

- **Beats:** 2
- **Summary:** s
- **Compress:** c
"""

LEDGER = """reveal_chapter: 2
culprit: marion
clue_schedule:
  - id: c-vase
    plant_chapter: 1
    description: the wrong vase
"""


def _source_layer(root, story=STORY, plan=None, ledger=LEDGER, genre="cozy-mystery"):
    """A series folder that is ON the source layer: a story.md, a genre the
    engine can resolve jobs from, and a whodunit ledger to resolve clue ids."""
    if genre is not None:
        (root / "series.yaml").write_text(f"genre: {genre}\n", encoding="utf-8")
    if ledger is not None:
        d = root / "series" / "whodunit"
        d.mkdir(parents=True, exist_ok=True)
        (d / "book-01.yaml").write_text(ledger, encoding="utf-8")
    p = root / "input" / "book-01" / "story.md"
    p.write_text(story, encoding="utf-8")
    if plan is not None:
        (root / "input" / "book-01" / "cut-plan.md").write_text(plan, encoding="utf-8")
    return p


def _write_cut_outline(root, story_text, plan_text=CUT_PLAN, body="# Outline\n\nbody.\n"):
    """An outline stamped by the real emitter, so these tests break if the
    stamp format moves."""
    from scripts import story_cut
    text = story_cut.stamp_outline(
        body,
        story_sha=hashlib.sha256(story_text.encode("utf-8")).hexdigest(),
        cut_sha=hashlib.sha256(plan_text.encode("utf-8")).hexdigest(),
        book="01", total_chapters=2, whodunit_sha=None)
    p = root / "input" / "book-01" / "outline.md"
    p.write_text(text, encoding="utf-8")
    return p


def _ids(rows):
    return [r.id for r in rows]


def test_a_book_with_no_story_md_gets_no_story_layer_rows(tmp_path):
    """Presence on disk is the switch — no adoption flag. A hand-authored book
    is not on the source layer and rows about it would be noise."""
    root = _series(tmp_path)
    _write_outline(root)
    ids = _ids(book_status.book_rows("01", root))
    assert "story" not in ids and "cut-plan" not in ids and "cut" not in ids


def test_story_layer_rows_come_before_the_outline_row(tmp_path):
    """Row order IS the mechanism: next_action prefers the first ran-but-failed
    row, so the source must sit above the build product."""
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN)
    ids = _ids(book_status.book_rows("01", root))
    assert ids.index("story") < ids.index("outline")
    assert ids.index("cut-plan") < ids.index("outline")
    assert ids.index("cut") < ids.index("outline")


def test_story_row_passes_for_a_story_with_no_findings(tmp_path):
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN)
    r = _row(book_status.book_rows("01", root), "story")
    assert r.run.ok is True and r.passed.ok is True
    assert "2 beats" in r.reason


def test_story_row_fails_and_counts_findings(tmp_path):
    root = _series(tmp_path)
    _source_layer(root, story=STORY.replace("#establish-protected-world",
                                            "#invented-job"), plan=CUT_PLAN)
    r = _row(book_status.book_rows("01", root), "story")
    assert r.run.ok is True and r.passed.ok is False
    assert "1 finding" in r.reason


def test_story_row_ignores_beats_without_chapter(tmp_path):
    """That finding is the cut plan's business, not the story's. With no cut
    plan it fires for every beat and would make every live story look broken."""
    root = _series(tmp_path)
    _source_layer(root, plan=None)
    r = _row(book_status.book_rows("01", root), "story")
    assert r.passed.ok is True


def test_story_row_is_unknown_when_the_genre_cannot_be_resolved(tmp_path):
    """No series.yaml means no job list, so every #job would read as unknown-job.
    A report that guesses is worse than one that admits."""
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN, genre=None)
    r = _row(book_status.book_rows("01", root), "story")
    assert r.passed.kind == "unknown"
    assert "genre" in r.reason.lower()


def test_story_row_is_unknown_when_the_whodunit_ledger_is_missing(tmp_path):
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN, ledger=None)
    r = _row(book_status.book_rows("01", root), "story")
    assert r.passed.kind == "unknown"
    assert "ledger" in r.reason.lower()


def test_cut_plan_row_is_not_run_without_a_cut_plan(tmp_path):
    root = _series(tmp_path)
    _source_layer(root, plan=None)
    r = _row(book_status.book_rows("01", root), "cut-plan")
    assert r.run.ok is False


def test_cut_plan_row_fails_when_a_beat_is_in_no_chapter(tmp_path):
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN.split("## Chapter 02")[0])
    r = _row(book_status.book_rows("01", root), "cut-plan")
    assert r.run.ok is True and r.passed.ok is False
    assert "beat" in r.reason.lower()


def test_cut_row_passes_when_the_outline_was_cut_from_this_story(tmp_path):
    root = _series(tmp_path)
    p = _source_layer(root, plan=CUT_PLAN)
    _write_cut_outline(root, p.read_text(encoding="utf-8"))
    r = _row(book_status.book_rows("01", root), "cut")
    assert r.run.ok is True and r.passed.ok is True


def test_cut_row_fails_when_story_md_changed_since_the_cut(tmp_path):
    """The quiet failure this whole row exists for: outline valid, lock valid,
    everything downstream green, and the author has moved on upstream."""
    root = _series(tmp_path)
    p = _source_layer(root, plan=CUT_PLAN)
    _write_cut_outline(root, p.read_text(encoding="utf-8"))
    p.write_text(STORY + "\n- One more beat. @maggie\n", encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "cut")
    assert r.run.ok is True and r.passed.ok is False
    assert "story.md" in r.reason


def test_cut_row_fails_when_the_outline_was_not_produced_by_the_cut(tmp_path):
    """Book 01's shape mid-migration: a legacy outline with no built_from_story.
    Not unknown — it is a known fact that this outline is not the story's output."""
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN)
    _write_outline(root)
    r = _row(book_status.book_rows("01", root), "cut")
    assert r.run.ok is True and r.passed.ok is False
    assert "built_from_story" in r.reason


def test_cut_row_is_not_run_when_there_is_no_outline(tmp_path):
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN)
    r = _row(book_status.book_rows("01", root), "cut")
    assert r.run.ok is False


def test_next_action_prefers_a_moved_story_over_a_stale_feedback_ledger(tmp_path):
    """The bug in one test: book 02 mid-edit. Feedback is STALE and would win
    the next: line, sending the showrunner to re-run a panel over an outline
    the story has already left behind."""
    root = _series(tmp_path)
    p = _source_layer(root, plan=CUT_PLAN)
    _write_cut_outline(root, p.read_text(encoding="utf-8"))
    p.write_text(STORY + "\n- One more beat. @maggie\n", encoding="utf-8")
    reports = root / "output" / "book-01" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "outline-feedback.yaml").write_text(
        "reviewed_outline_sha256: deadbeef\n"
        "items:\n  - {id: OF-1, state: open}\n", encoding="utf-8")
    assert book_status.next_action(book_status.all_rows("01", root)).id == "cut"


def test_cut_row_offers_no_runnable_recut_command(tmp_path):
    """Re-cutting rewrites the ledger and restales every packet. The row states
    the discrepancy and its cost; it must not hand over a copy-pasteable
    command that hides the prerequisite."""
    root = _series(tmp_path)
    p = _source_layer(root, plan=CUT_PLAN)
    _write_cut_outline(root, p.read_text(encoding="utf-8"))
    p.write_text(STORY + "\n- One more beat. @maggie\n", encoding="utf-8")
    r = _row(book_status.book_rows("01", root), "cut")
    out = book_status.render("01", [r], r, [])
    next_line = next(l for l in out.splitlines() if l.startswith("next:"))
    assert "story_cut.py" not in next_line and "/plot-book" not in next_line
    assert "re-cut" in next_line.lower()


def test_cut_row_names_the_lock_as_a_cost_when_one_exists(tmp_path):
    """Cascade the row must not hide: re-cutting needs the ledger unsealed."""
    root = _series(tmp_path)
    p = _source_layer(root, plan=CUT_PLAN)
    _write_cut_outline(root, p.read_text(encoding="utf-8"))
    p.write_text(STORY + "\n- One more beat. @maggie\n", encoding="utf-8")
    _write_lock(root, "book: 01\nvalidated: fairplay\n")
    r = _row(book_status.book_rows("01", root), "cut")
    assert "lock" in (r.fix_command or "").lower()


def test_main_reports_a_book_that_has_a_story_but_no_outline_yet(tmp_path, monkeypatch, capsys):
    """Two real shapes have a story.md and no outline: book 02 between
    /plot-book writing story.md and the first cut, and book 01 the moment its
    legacy outline is deleted to migrate. Refusing here would make the
    documented migration step turn the table off."""
    root = _series(tmp_path)
    _source_layer(root, plan=CUT_PLAN)
    monkeypatch.chdir(root)
    assert book_status._main(["01"]) == 0
    assert "story" in capsys.readouterr().out


def test_main_still_refuses_a_book_with_neither_story_nor_outline(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path)
    monkeypatch.chdir(root)
    assert book_status._main(["01"]) == 2
    assert "nothing to report" in capsys.readouterr().err.lower()
