from datetime import datetime, timezone

import pytest

from scripts import assemble_book, penny_meta


def test_strip_frontmatter_returns_body():
    text = "---\nschema: x\ndrafted_by: claude-opus\n---\n\nHello world.\n"
    assert penny_meta.strip_frontmatter(text) == "Hello world.\n"


def test_strip_frontmatter_no_frontmatter_is_identity():
    assert penny_meta.strip_frontmatter("Hello.\n") == "Hello.\n"


def _make_chapter(chapters_dir, num, drafted_by, body):
    chapters_dir.mkdir(parents=True, exist_ok=True)
    text = (f"---\nschema: penny-chapter/1\ntarget: book-99/ch-{num:02d}\n"
            f"drafted_by: {drafted_by}\n---\n\n{body}\n")
    (chapters_dir / f"ch-{num:02d}.final.md").write_text(text, encoding="utf-8")


def _book_tree(tmp_path, book="99"):
    return tmp_path / "output" / f"book-{book}" / "chapters"


FIXED_NOW = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)


def test_assemble_produces_manuscript(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "Chapter one prose.")
    _make_chapter(chapters, 2, "codex", "Chapter two prose.")
    assert assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW) == 0
    man = assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8")
    fm = penny_meta.parse_frontmatter(man)
    assert fm["schema"] == "penny-manuscript/1"
    assert fm["book"] == "99"
    assert fm["chapters"] == "2"
    assert fm["drafted_by"] == ["claude-opus", "codex"]   # sorted union
    assert fm["assembled_at"] == "2026-06-21T12:00:00+00:00"
    assert "read_by" not in fm                             # absent until seal
    body = penny_meta.strip_frontmatter(man)
    assert body == ("# Chapter 1\n\nChapter one prose.\n\n"
                    "# Chapter 2\n\nChapter two prose.\n")


def test_assemble_fails_on_gap(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    _make_chapter(chapters, 3, "codex", "three")        # gap at 2
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "not contiguous" in str(e.value)


def test_assemble_fails_on_zero_chapters(tmp_path):
    _book_tree(tmp_path).mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "no finalized chapters" in str(e.value)


def test_assemble_fails_on_missing_drafted_by(tmp_path):
    chapters = _book_tree(tmp_path)
    chapters.mkdir(parents=True, exist_ok=True)
    (chapters / "ch-01.final.md").write_text(
        "---\nschema: penny-chapter/1\n---\n\nbody\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "missing drafted_by" in str(e.value)


def test_assemble_fails_on_outline_count_mismatch(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    (tmp_path / "output" / "book-99" / "outline.md").write_text(
        "---\nchapters: 2\n---\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assert "outline declares 2" in str(e.value)


def test_frontmatter_note_does_not_leak_into_manuscript(tmp_path):
    # Pins the invariant a short-chapter report depends on: anything the
    # drafter writes in FRONTMATTER (e.g. a drafted_short shortfall note)
    # must never reach the assembled manuscript. Only the prose body should
    # survive assembly.
    chapters = _book_tree(tmp_path)
    chapters.mkdir(parents=True, exist_ok=True)
    text = ("---\nschema: penny-chapter/1\ndrafted_by: claude-opus\n"
            "drafted_short: landed at 1540 words against 1800 minimum, "
            "outline gives three beats where this chapter needs four, "
            "needs another scene not more prose\n"
            "---\n\nChapter one prose.\n")
    (chapters / "ch-01.final.md").write_text(text, encoding="utf-8")
    assert assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW) == 0
    man = assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8")
    assert "drafted_short" not in man
    assert "needs another scene" not in man
    body = penny_meta.strip_frontmatter(man)
    assert body == "# Chapter 1\n\nChapter one prose.\n"


def _seal_setup(tmp_path, read_by="codex"):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assemble_book.final_read_path("99", tmp_path).write_text(
        f"---\nschema: penny-final-read/1\nread_by: {read_by}\n"
        f"standalone: yes\nmystery_resolved: yes\nthread_left_open: yes\n---\n"
        "## Holistic verdict\nGood.\n", encoding="utf-8")


def test_seal_stamps_read_by(tmp_path):
    _seal_setup(tmp_path, read_by="codex")
    assert assemble_book.cmd_seal("99", repo_root=tmp_path) == 0
    fm = penny_meta.parse_frontmatter(
        assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8"))
    assert fm["read_by"] == "codex"


def test_seal_is_idempotent(tmp_path):
    _seal_setup(tmp_path, read_by="codex")
    assert assemble_book.cmd_seal("99", repo_root=tmp_path) == 0
    first = assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8")
    assert assemble_book.cmd_seal("99", repo_root=tmp_path) == 0     # re-seal = no-op
    assert assemble_book.manuscript_path("99", tmp_path).read_text(encoding="utf-8") == first


def test_seal_rejects_read_by_in_drafted_by(tmp_path):
    _seal_setup(tmp_path, read_by="claude-opus")     # claude-opus drafted ch-01
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_seal("99", repo_root=tmp_path)
    assert "appears in drafted_by" in str(e.value)


def test_seal_fails_when_final_read_absent(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_seal("99", repo_root=tmp_path)
    assert "no final-read artifact" in str(e.value)


def test_seal_fails_when_manuscript_absent(tmp_path):
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_seal("99", repo_root=tmp_path)
    assert "no manuscript to seal" in str(e.value)


def test_seal_fails_when_read_by_absent(tmp_path):
    chapters = _book_tree(tmp_path)
    _make_chapter(chapters, 1, "claude-opus", "one")
    assemble_book.cmd_assemble("99", repo_root=tmp_path, now=FIXED_NOW)
    assemble_book.final_read_path("99", tmp_path).write_text(
        "---\nschema: penny-final-read/1\nstandalone: yes\n---\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        assemble_book.cmd_seal("99", repo_root=tmp_path)
    assert "no read_by stamp" in str(e.value)


def _write_final_read(tmp_path, *, schema="penny-final-read/1", read_by="codex",
                      standalone="yes", mystery_resolved="yes", thread_left_open="yes"):
    book_dir = tmp_path / "output" / "book-99"
    book_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"schema: {schema}"]
    if read_by is not None:
        lines.append(f"read_by: {read_by}")
    if standalone is not None:
        lines.append(f"standalone: {standalone}")
    if mystery_resolved is not None:
        lines.append(f"mystery_resolved: {mystery_resolved}")
    if thread_left_open is not None:
        lines.append(f"thread_left_open: {thread_left_open}")
    lines += ["---", "", "## Holistic verdict", "Reads well.", ""]
    (book_dir / "book-99.final-read.md").write_text("\n".join(lines), encoding="utf-8")


def test_validate_read_accepts_enum(tmp_path):
    _write_final_read(tmp_path)
    assert assemble_book.validate_final_read("99", repo_root=tmp_path) == 0


def test_validate_read_rejects_hedge(tmp_path):
    _write_final_read(tmp_path, standalone="mostly")     # the hedge
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "standalone" in str(e.value) and "mostly" in str(e.value)


def test_validate_read_rejects_missing_boolean(tmp_path):
    _write_final_read(tmp_path, thread_left_open=None)
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "thread_left_open" in str(e.value)


def test_validate_read_rejects_missing_read_by(tmp_path):
    _write_final_read(tmp_path, read_by=None)
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "read_by" in str(e.value)


def test_validate_read_rejects_bad_schema(tmp_path):
    _write_final_read(tmp_path, schema="penny-beta/1")
    with pytest.raises(SystemExit) as e:
        assemble_book.validate_final_read("99", repo_root=tmp_path)
    assert "schema" in str(e.value)
