from pathlib import Path

import pytest

from scripts import outline_views

FIXTURE = Path("tests/fixtures/outlines/views-sample.md")


@pytest.fixture
def text():
    return FIXTURE.read_text(encoding="utf-8")


def test_iter_chapters_yields_number_title_block_in_order(text):
    got = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    assert got == [(1, "The Arrival"), (2, "The Body"),
                   (3, "Quiet Rooms"), (4, "Tara")]


def test_iter_chapters_block_carries_the_sections(text):
    blocks = {n: b for n, _t, b in outline_views.iter_chapters(text)}
    assert "### Chapter Summary" in blocks[1]
    assert "### Chapter Summary" not in blocks[4]


def test_glance_carries_every_chapter_heading(text):
    out = outline_views.glance(text)
    assert "## 01 — The Arrival" in out
    assert "## 04 — Tara" in out


def test_glance_carries_summary_prose(text):
    out = outline_views.glance(text)
    assert "Maggie finds Lisa dead at the wheel" in out


def test_glance_names_a_missing_summary_rather_than_dropping_it(text):
    out = outline_views.glance(text)
    assert "*(no summary)*" in out


def test_glance_omits_required_beats(text):
    """The glance is summaries only — beats are the outline's noise, not signal."""
    out = outline_views.glance(text)
    assert "Simon mentions a scheduling irregularity" not in out


def test_name_tokens_splits_a_hyphenated_slug():
    assert outline_views.name_tokens("tara-marion") == ["tara", "marion"]
    assert outline_views.name_tokens("simon") == ["simon"]


def test_strand_collects_chapters_naming_the_character_in_order(text):
    hits = outline_views.strand(text, "simon")
    assert [n for n, _line in hits] == [1, 1]


def test_strand_matches_whole_words_only(text):
    """'Simone' at the surf club must not land in Simon's strand — a substring
    match would put another character's action on his page and invent a hole."""
    lines = [line for _n, line in outline_views.strand(text, "simon")]
    assert not any("surf club" in line for line in lines)


def test_strand_matches_any_token_of_a_hyphenated_slug(text):
    hits = outline_views.strand(text, "tara-marion")
    assert [n for n, _line in hits] == [4]


def test_strand_omits_chapters_that_never_name_the_character(text):
    assert 3 not in [n for n, _line in outline_views.strand(text, "simon")]


def test_strand_returns_empty_for_an_absent_character(text):
    assert outline_views.strand(text, "george") == []


def test_render_strand_shows_chapter_numbers(text):
    out = outline_views.render_strand("simon", outline_views.strand(text, "simon"))
    assert "simon" in out.lower()
    assert "ch 01" in out


def test_strand_raises_on_empty_slug(text):
    """A degenerate slug yields no tokens and would match every line — fail loud."""
    with pytest.raises(ValueError, match="strand: slug '' yields no name tokens"):
        outline_views.strand(text, "")


def test_strand_raises_on_hyphens_only_slug(text):
    """Hyphens alone split to empty tokens — fail loud, not silently."""
    with pytest.raises(ValueError, match="strand: slug '-' yields no name tokens"):
        outline_views.strand(text, "-")
    with pytest.raises(ValueError, match="strand: slug '--' yields no name tokens"):
        outline_views.strand(text, "--")


def test_parse_jobs_reads_ids_in_file_order():
    from scripts import penny_genre, penny_paths
    path = penny_genre.macro_structure()
    if path is None:                      # engine repo has no declared genre
        # cwd-relative fallback would break if pytest ran from a subdirectory —
        # anchor on the plugin root instead.
        path = (penny_paths.plugin_root() / "genres" / "cozy-mystery"
                 / "review-rubrics" / "macro-structure.md")
    jobs = outline_views.parse_jobs(Path(path).read_text(encoding="utf-8"))
    assert len(jobs) == 28
    assert jobs[0] == ("establish-protected-world", "Establish the Protected World")
    assert jobs[9][0] == "plant-fair-play-solution"
    assert jobs[27] == ("restore-world", "Restore the World")


def test_parse_jobs_ignores_a_heading_with_no_marker():
    text = "## 1. Titled\n<!-- job: titled -->\n\n## 2. Unmarked\n\nbody\n"
    assert outline_views.parse_jobs(text) == [("titled", "Titled")]


def test_parse_jobs_raises_on_marker_inline_with_its_heading():
    """A marker glued onto the heading line itself is present but malformed —
    unlike a heading with no marker at all, this must fail loud, not vanish."""
    text = "## 1. Titled <!-- job: titled -->\n\nbody\n"
    with pytest.raises(ValueError, match="malformed job marker"):
        outline_views.parse_jobs(text)


def test_parse_jobs_raises_on_indented_marker():
    text = "## 1. Titled\n    <!-- job: titled -->\n\nbody\n"
    with pytest.raises(ValueError, match="malformed job marker"):
        outline_views.parse_jobs(text)


def test_parse_jobs_raises_on_marker_id_with_uppercase_or_underscore():
    text = "## 1. Titled\n<!-- job: Titled_Job -->\n\nbody\n"
    with pytest.raises(ValueError, match="malformed job marker"):
        outline_views.parse_jobs(text)


def test_parse_jobs_raises_on_duplicate_job_id():
    """A job is addressed by its id — two jobs sharing one makes that address
    ambiguous, which defeats the entire point of adding ids."""
    text = ("## 1. First\n<!-- job: same-id -->\n\n"
            "## 2. Second\n<!-- job: same-id -->\n\nbody\n")
    with pytest.raises(ValueError, match="duplicate job id 'same-id'"):
        outline_views.parse_jobs(text)


def test_roster_reads_suspects_and_victim_from_the_ledger(tmp_path):
    """Regression for a Task-2 defect: roster() called series_path() with a
    'series/...' prefix, but series_path() already prepends 'series/', so the
    resolved path was <root>/series/series/whodunit/book-NN.yaml — never a
    real file — and roster() silently returned [] for every real series."""
    (tmp_path / ".penny").mkdir()
    ledger_dir = tmp_path / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(
        "victim: neil-hartigan\n"
        "alibi_grid:\n"
        "  - { suspect: mary-kearney, chapter: 7, alibi: x, holds: false }\n"
        "  - { suspect: saffron, chapter: 17, alibi: y, holds: true }\n",
        encoding="utf-8",
    )
    assert outline_views.roster("01", root=tmp_path) == [
        "mary-kearney", "saffron", "neil-hartigan",
    ]


def test_roster_returns_empty_list_when_ledger_is_missing(tmp_path):
    (tmp_path / ".penny").mkdir()
    assert outline_views.roster("01", root=tmp_path) == []


def test_spine_worksheet_lists_every_job_with_an_unfilled_slot(text):
    jobs = [("crime-and-first-contradiction", "Deliver the Crime"),
            ("restore-world", "Restore the World")]
    chapters = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    out = outline_views.spine_worksheet(jobs, chapters)
    assert "crime-and-first-contradiction" in out
    assert "Deliver the Crime" in out
    assert "restore-world" in out


def test_spine_worksheet_lists_the_books_chapters(text):
    chapters = [(n, t) for n, t, _b in outline_views.iter_chapters(text)]
    out = outline_views.spine_worksheet([("x", "X")], chapters)
    assert "01 — The Arrival" in out
    assert "04 — Tara" in out


def test_spine_worksheet_refuses_an_empty_job_list(text):
    with pytest.raises(ValueError, match="no structural jobs"):
        outline_views.spine_worksheet([], [(1, "A")])


def test_spine_worksheet_slots_are_empty_not_filled(text):
    """The 'chapters:' slot for each job must be empty—not auto-filled.

    Deciding which chapter answers which job is the agent's work (Task 5),
    not the frame's. A test that only checks for 'chapters:' substring would
    pass against broken implementations that drop the line entirely or fill it
    (e.g., 'chapters: 1'). This test pins the structure: chapters: exists,
    followed by nothing but whitespace until the next job heading or section."""
    jobs = [("job-1", "First Job"),
            ("job-2", "Second Job")]
    chapters = [(1, "Chapter One"), (2, "Chapter Two")]
    out = outline_views.spine_worksheet(jobs, chapters)
    lines = out.split('\n')

    # Find each job's chapters: line and verify the lines after it are empty
    # until the next section heading or job heading
    for job_id, _title in jobs:
        # Find the line containing this job's heading
        job_heading_idx = None
        for i, line in enumerate(lines):
            if line.strip() == f"### {job_id}":
                job_heading_idx = i
                break
        assert job_heading_idx is not None, f"Job heading not found: {job_id}"

        # Find the chapters: line for this job (should be a few lines after heading)
        chapters_line_idx = None
        for i in range(job_heading_idx + 1, min(job_heading_idx + 10, len(lines))):
            if lines[i].strip() == "chapters:":
                chapters_line_idx = i
                break
        assert chapters_line_idx is not None, f"'chapters:' slot not found for {job_id}"

        # Verify the line after chapters: is empty (or contains only whitespace)
        # and nothing is auto-filled (like "1" or "chapters: 1")
        if chapters_line_idx + 1 < len(lines):
            next_line = lines[chapters_line_idx + 1]
            assert next_line.strip() == "", \
                f"chapters: slot for {job_id} is not empty; got: {next_line!r}"

        # Verify the chapters: line itself is just "chapters:" with nothing after
        chapters_line_content = lines[chapters_line_idx].strip()
        assert chapters_line_content == "chapters:", \
            f"chapters: line for {job_id} has content after it: {chapters_line_content!r}"


import os
import subprocess
import sys


def _series(tmp_path, outline_text):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input" / "book-01"
    d.mkdir(parents=True)
    (d / "outline.md").write_text(outline_text, encoding="utf-8")
    return tmp_path


def _run(cwd, *args):
    # Extend the real environment rather than replacing it (tests/conftest.py's
    # penny_root fixture does the same) — a stripped env can break subprocess
    # execution on macOS.
    env = dict(os.environ, PYTHONPATH=str(Path.cwd()))
    return subprocess.run(
        [sys.executable, str(Path.cwd() / "scripts" / "outline_views.py"), *args],
        cwd=cwd, capture_output=True, text=True, env=env)


def test_cli_glance_writes_a_report(tmp_path, text):
    root = _series(tmp_path, text)
    proc = _run(root, "glance", "01")
    assert proc.returncode == 0, proc.stderr
    out = root / "output" / "book-01" / "reports" / "outline-glance.md"
    assert out.is_file()
    assert "The Arrival" in out.read_text(encoding="utf-8")


def test_cli_refuses_a_book_with_no_outline(tmp_path):
    root = _series(tmp_path, "")
    (root / "input" / "book-01" / "outline.md").unlink()
    proc = _run(root, "glance", "01")
    assert proc.returncode == 2
    assert "no outline" in (proc.stderr + proc.stdout).lower()


def test_cli_strands_honours_an_explicit_who(tmp_path, text):
    root = _series(tmp_path, text)
    proc = _run(root, "strands", "01", "--who", "simon")
    assert proc.returncode == 0, proc.stderr
    out = root / "output" / "book-01" / "reports" / "strands" / "simon.md"
    assert out.is_file()


def test_cli_strands_names_the_problem_when_it_has_no_roster(tmp_path, text):
    """No ledger and no --who is a refusal by name, never an empty report."""
    root = _series(tmp_path, text)
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    assert "roster" in (proc.stderr + proc.stdout).lower()


def test_cli_strands_names_a_degenerate_slug_and_exits_usage(tmp_path, text):
    """CARRY-FORWARD: a slug with no name tokens (a placeholder like '-' from
    a hand-edited ledger) must never reach strand() at all after the fix-round-1
    path-safety fix below — '-' fails the path-safety format check first
    (it can't start with a hyphen), which is a strictly earlier and stricter
    refusal than strand()'s own 'yields no name tokens' ValueError. Either way:
    named message on stderr, exit 2, never a raw traceback. (strand()'s own
    ValueError is still covered directly at the unit level by
    test_strand_raises_on_empty_slug / test_strand_raises_on_hyphens_only_slug
    above, since strand() may still be called by future non-CLI callers with
    an unvalidated slug.)"""
    root = _series(tmp_path, text)
    proc = _run(root, "strands", "01", "--who", "-")
    assert proc.returncode == 2
    msg = (proc.stderr + proc.stdout).lower()
    assert "invalid" in msg and "character slug" in msg


def test_cli_strands_refuses_a_traversal_slug_and_leaves_the_outline_untouched(tmp_path, text):
    """CRITICAL fix (round 1): a character slug reached Path(...) via
    f"{slug}.md" with no validation — the reviewer demonstrated
    `strands 01 --who '../../../../input/book-01/outline'` silently
    overwriting input/book-01/outline.md with exit 0. Must now refuse by
    name, exit 2, and leave the outline byte-for-byte untouched, with no
    'strands' report directory created at all (validate-before-write)."""
    root = _series(tmp_path, text)
    outline_path = root / "input" / "book-01" / "outline.md"
    before = outline_path.read_text(encoding="utf-8")
    proc = _run(root, "strands", "01", "--who",
                "../../../../input/book-01/outline")
    assert proc.returncode == 2
    msg = (proc.stderr + proc.stdout).lower()
    assert "invalid" in msg and "character slug" in msg
    assert outline_path.read_text(encoding="utf-8") == before
    assert not (root / "output" / "book-01" / "reports" / "strands").exists()


def test_cli_strands_refuses_a_traversal_slug_reaching_the_lock_dir(tmp_path, text):
    """Same defect as above, aimed at .penny/locks/ instead of the outline —
    the reviewer named both as reachable targets of the same unvalidated
    slug-as-filename construction."""
    root = _series(tmp_path, text)
    lock_dir = root / ".penny" / "locks"
    lock_dir.mkdir(parents=True)
    lock_path = lock_dir / "book-01.mystery.lock"
    lock_path.write_text("SEALED\n", encoding="utf-8")
    proc = _run(root, "strands", "01", "--who",
                "../../../../.penny/locks/book-01.mystery")
    assert proc.returncode == 2
    assert "invalid" in (proc.stderr + proc.stdout).lower()
    assert lock_path.read_text(encoding="utf-8") == "SEALED\n"


def test_cli_refuses_a_traversal_book_id_that_escapes_output(tmp_path, text):
    """CRITICAL fix (round 1), test CORRECTED in round 2.

    The original version of this test used book='../..', which the
    PRE-FIX code already refused for an unrelated reason: _outline_text's
    plain 'no such outline' check fires first (input/book-.../../outline.md
    never exists), so returncode==2 and 'output/ was never created' both
    passed even against the vulnerable code — only the wording assertion
    ('invalid' in the message) actually depended on the fix. It pinned this
    test's own prose, not the vulnerability.

    The re-reviewer's real escape: book='01/../../input/book-01' resolves,
    via _outline_text, to the EXACT SAME outline.md this fixture already
    created (the traversal cancels itself out for the input side) — so the
    pre-fix code happily reads it and proceeds — while _reports_dir resolves
    the same book string to input/book-01/reports/ instead of
    output/book-01/reports/, escaping the reports tree entirely and writing
    there with exit 0. This version fails pre-fix for that real reason
    (confirmed via `git stash` on the script fix) and asserts the escaped
    location was never created, not just that 'output/' wasn't."""
    root = _series(tmp_path, text)
    proc = _run(root, "glance", "01/../../input/book-01")
    assert proc.returncode == 2
    assert "invalid" in (proc.stderr + proc.stdout).lower()
    assert not (root / "input" / "book-01" / "reports").exists()
    assert not (root / "output").exists()


def test_cli_strands_refuses_cleanly_when_who_has_no_value(tmp_path, text):
    """Important fix (round 1): --who as the very last argument used to raise
    IndexError (exit 1, raw traceback) instead of a named exit-2 refusal like
    every other bad-input case."""
    root = _series(tmp_path, text)
    proc = _run(root, "strands", "01", "--who")
    assert proc.returncode == 2
    assert "--who requires a value" in (proc.stderr + proc.stdout)


def test_roster_raises_value_error_on_malformed_yaml(tmp_path):
    """Important fix (round 1): a hand-edited ledger that isn't valid YAML
    used to raise a raw yaml.YAMLError out of roster() — not a ValueError,
    so the CLI's single `except ValueError` never caught it either."""
    (tmp_path / ".penny").mkdir()
    ledger_dir = tmp_path / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(
        "victim: [unterminated\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid YAML"):
        outline_views.roster("01", root=tmp_path)


def test_cli_strands_names_a_malformed_ledger_and_exits_usage(tmp_path, text):
    """CLI-level companion to the unit test above: a malformed ledger must
    surface as a named exit-2 refusal, not a traceback, when strands falls
    back to roster() (no --who given)."""
    root = _series(tmp_path, text)
    ledger_dir = root / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(
        "victim: [unterminated\n", encoding="utf-8")
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    msg = (proc.stderr + proc.stdout).lower()
    assert "not valid yaml" in msg


@pytest.mark.parametrize("body", ["just a string\n", "- one\n- two\n"])
def test_roster_raises_value_error_on_a_ledger_that_parses_but_is_not_a_mapping(tmp_path, body):
    """Important fix (round 2): the round-1 fix guarded yaml.safe_load itself
    but not the very next line, `data.get("alibi_grid")` — a ledger truncated
    to a bare scalar or saved as a top-level list is VALID yaml (so the
    YAMLError guard never fires) but has no .get(), so it raised a raw
    AttributeError. Covers both the scalar and the list shape."""
    (tmp_path / ".penny").mkdir()
    ledger_dir = tmp_path / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping"):
        outline_views.roster("01", root=tmp_path)


@pytest.mark.parametrize("body", ["just a string\n", "- one\n- two\n"])
def test_cli_strands_names_a_non_mapping_ledger_and_exits_usage(tmp_path, text, body):
    """CLI-level companion: a ledger that parses but isn't a mapping must
    surface as a named exit-2 refusal, not an AttributeError traceback."""
    root = _series(tmp_path, text)
    ledger_dir = root / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(body, encoding="utf-8")
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    msg = (proc.stderr + proc.stdout).lower()
    assert "must be a mapping" in msg


def test_cli_strands_refuses_a_ledger_slug_with_a_trailing_newline(tmp_path, text):
    """Minor fix (round 2): re.MULTILINE-less `$` also matches immediately
    before a trailing newline, so a slug of 'simon\\n' passed the old
    `^[a-z0-9][a-z0-9-]*$` check even though it is not the plain 'simon' it
    looks like — a soft edge on the one regex that IS the security boundary.
    Tightened to \\A...\\Z, which has no such exception.

    NOTE: --who values are `.strip()`-ped before validation, so a --who
    argument can never carry an unstripped trailing newline through to
    _slug_error — this test instead goes through the one code path that
    reaches _slug_error UNSTRIPPED: a `suspect:` value read straight out of
    the whodunit ledger by roster(). That is the realistic route the
    round-2 finding named ('from a hand-edited ledger's suspect:/victim:
    field')."""
    root = _series(tmp_path, text)
    ledger_dir = root / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(
        'alibi_grid:\n'
        '  - { suspect: "simon\\n", chapter: 1, alibi: x, holds: true }\n',
        encoding="utf-8")
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    assert "invalid" in (proc.stderr + proc.stdout).lower()


def test_cli_refuses_a_book_id_with_a_trailing_newline(tmp_path):
    """Same \\A...\\Z fix, the book-id side."""
    (tmp_path / ".penny").mkdir()
    proc = _run(tmp_path, "glance", "01\n")
    assert proc.returncode == 2


def test_roster_raises_value_error_on_a_non_list_alibi_grid(tmp_path):
    """FINDING 3: `for entry in data.get("alibi_grid") or []` raised a raw
    TypeError ('int' object is not iterable) on a ledger with a scalar
    alibi_grid — a third member of the ledger-shape family this file has
    twice already closed (malformed YAML, non-mapping top level)."""
    (tmp_path / ".penny").mkdir()
    ledger_dir = tmp_path / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text("alibi_grid: 5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="alibi_grid.*must be a list"):
        outline_views.roster("01", root=tmp_path)


def test_cli_strands_names_a_non_list_alibi_grid_and_exits_usage(tmp_path, text):
    """CLI-level companion to the unit test above."""
    root = _series(tmp_path, text)
    ledger_dir = root / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text("alibi_grid: 5\n", encoding="utf-8")
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    assert "must be a list" in (proc.stderr + proc.stdout).lower()


@pytest.mark.parametrize("body", ["false\n", "0\n", "[]\n"])
def test_roster_raises_value_error_on_a_falsy_non_mapping_ledger(tmp_path, body):
    """FINDING 3 (masking bug): `yaml.safe_load(...) or {}` turned a falsy
    non-dict top level (false/0/[]) into `{}` BEFORE the isinstance guard
    ever saw it, so a ledger this malformed silently reported "no whodunit
    ledger was found" instead of naming it as malformed — worse than the
    already-fixed non-falsy non-mapping cases ("just a string", a populated
    list), which never hit the `or {}` fallback because they're truthy."""
    (tmp_path / ".penny").mkdir()
    ledger_dir = tmp_path / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match="must be a mapping"):
        outline_views.roster("01", root=tmp_path)


@pytest.mark.parametrize("body", ["false\n", "0\n", "[]\n"])
def test_cli_strands_names_a_falsy_non_mapping_ledger_and_exits_usage(tmp_path, text, body):
    """CLI-level companion: must surface as a named 'must be a mapping'
    refusal, never the generic 'no roster'/'no whodunit ledger was found'
    message that the masking bug produced instead."""
    root = _series(tmp_path, text)
    ledger_dir = root / "series" / "whodunit"
    ledger_dir.mkdir(parents=True)
    (ledger_dir / "book-01.yaml").write_text(body, encoding="utf-8")
    proc = _run(root, "strands", "01")
    assert proc.returncode == 2
    msg = (proc.stderr + proc.stdout).lower()
    assert "must be a mapping" in msg
    assert "no whodunit ledger was found" not in msg


@pytest.mark.parametrize("text", [
    "## 1. Titled\n    <!--job: titled -->\n\nbody\n",
    "## 1. Titled <!--job: titled -->\n\nbody\n",
])
def test_parse_jobs_catches_a_stray_marker_with_no_space_after_the_opener(text):
    """FINDING 4: the stray-marker scan looked for the literal '<!-- job:'
    (one space after the opener), so a malformed marker written as
    '<!--job:' (no space) — indented, or glued inline to its heading — was
    silently dropped instead of failing loud like every other malformed
    placement this function already catches."""
    with pytest.raises(ValueError, match="malformed job marker"):
        outline_views.parse_jobs(text)


def test_cli_spine_names_a_missing_macro_structure_file_and_exits_usage(
        tmp_path, text, monkeypatch):
    """FINDING 2: macro_structure() resolves through the overlay's
    config_path(), which falls back to a plugin-default path that may not
    exist on disk — Path.read_text() on that missing file used to raise a
    raw FileNotFoundError (exit 1, full traceback) instead of the named
    exit-2 refusal every other bad-input case in this module gets.

    Reproduced by monkeypatching penny_genre.macro_structure() directly
    (called via `from scripts import penny_genre` inside outline_views._main)
    rather than fabricating a genre pack: a genre.yaml declaring a
    macro_structure file that doesn't exist in its own genre_dir would
    already be refused earlier, by penny_genre.load_manifest's manifest
    validation — this defends outline_views.py itself against trusting
    macro_structure()'s return without checking it landed on a real file."""
    root = _series(tmp_path, text)
    monkeypatch.chdir(root)
    monkeypatch.syspath_prepend(str(Path.cwd()))
    from scripts import penny_genre
    missing = tmp_path / "no-such-macro-structure.md"
    monkeypatch.setattr(penny_genre, "macro_structure", lambda root=None: missing)
    rc = outline_views._main(["spine", "01"])
    assert rc == 2
