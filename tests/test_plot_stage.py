import glob
import hashlib
from pathlib import Path

import pytest

from scripts.plot_stage import (STAGE_ORDER, next_stage, readers_copy, readers_copy_staged,
                                 readers_copy_text, reveal_stages, stage_paths, stage_status,
                                 stamp, _reveals, _sha, _upstream_sha)


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


def _whodunit(root, book="01", extra=""):
    return _write(root, f"series/whodunit/book-{book}.yaml",
                  "book: '01'\ntotal_chapters: 30\nreveal_chapter: 26\n" + extra)


def test_reveals_absent_ledger_returns_empty(tmp_path):
    root = _series(tmp_path)
    assert _reveals("01", root) == []


def test_reveals_key_absent_returns_empty(tmp_path):
    root = _series(tmp_path)
    _whodunit(root)
    assert _reveals("01", root) == []


def test_reveals_parsed_in_order(tmp_path):
    root = _series(tmp_path)
    _whodunit(root, extra=(
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
        "  reader_should_think_before:\n"
        "  - Lisa was abusing property records\n"
        "- id: marion-is-tara\n"
        "  reveal_chapter: 27\n"
        "  author_truth: Marion is Tara.\n"))
    got = _reveals("01", root)
    assert [r["id"] for r in got] == ["impersonation", "marion-is-tara"]
    assert [r["reveal_chapter"] for r in got] == [15, 27]
    assert got[0]["reader_should_think_before"] == ["Lisa was abusing property records"]
    assert "reader_should_think_before" not in got[1]


@pytest.mark.parametrize("bad,needle", [
    ("reveals: not-a-list\n", "must be a list"),
    ("reveals:\n- reveal_chapter: 15\n  author_truth: x\n", "missing 'id'"),
    ("reveals:\n- id: a\n  author_truth: x\n", "missing 'reveal_chapter'"),
    ("reveals:\n- id: a\n  reveal_chapter: 15\n", "missing 'author_truth'"),
    ("reveals:\n- id: a\n  reveal_chapter: nine\n  author_truth: x\n", "not an integer"),
    ("reveals:\n- id: a\n  reveal_chapter: 1\n  author_truth: x\n", "cannot be chapter 1"),
    ("reveals:\n- id: a\n  reveal_chapter: 31\n  author_truth: x\n", "beyond total_chapters"),
    ("reveals:\n- id: a\n  reveal_chapter: 20\n  author_truth: x\n"
     "- id: b\n  reveal_chapter: 15\n  author_truth: y\n", "not in ascending"),
    ("reveals:\n- id: a\n  reveal_chapter: 15\n  author_truth: x\n"
     "- id: a\n  reveal_chapter: 20\n  author_truth: y\n", "duplicate reveal id"),
    ("reveals:\n- id: a\n  reveal_chapter: 15\n  author_truth: x\n"
     "  reader_should_think_before: bare string\n", "must be a non-empty list"),
    ("reveals:\n- id: a\n  reveal_chapter: 15\n  author_truth: x\n"
     "  reader_should_think_before: []\n", "must be a non-empty list"),
])
def test_reveals_malformed_exits_loud(tmp_path, bad, needle):
    root = _series(tmp_path)
    _whodunit(root, extra=bad)
    with pytest.raises(SystemExit) as exc:
        _reveals("01", root)
    assert needle in str(exc.value)


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


# --- FINAL REVIEW FINDING 3: the whodunit ledger is a real upstream of
# "chapters" but was absent from the fingerprint graph --------------------

def test_stage_paths_includes_whodunit_ledger(tmp_path):
    root = _series(tmp_path)
    paths = stage_paths("01", root)
    assert paths["whodunit"] == root / "series" / "whodunit" / "book-01.yaml"


def test_chapters_stage_goes_stale_when_whodunit_ledger_edited(tmp_path):
    root = _series(tmp_path)
    tp = _write(root, "input/book-01/plot/turning-points.md")
    sol = _write(root, "output/book-01/mystery-solution.md")
    wd = _write(root, "series/whodunit/book-01.yaml", "reveal_chapter: 5\n")
    skel = _write(root, "input/book-01/outline-skeleton.md")
    stamp("01", skel, [tp, sol, wd], repo_root=root)
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["chapters"] == "done"
    wd.write_text(wd.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    rows = dict((n, s) for n, s, _ in stage_status("01", repo_root=root))
    assert rows["chapters"] == "stale"


def test_stage_order_unaffected_by_whodunit_upstream_addition():
    # STAGE_ORDER must stay the 7 real stages — whodunit is a fingerprint
    # upstream, never a stage of its own.
    assert STAGE_ORDER == ["premise", "ending", "turning-points", "counterplot",
                           "chapters", "weave", "readback"]
    assert "whodunit" not in STAGE_ORDER


# --- FINAL REVIEW C1 (Critical, RULING): declaring reveals: must not send
# /plot-book back to chapter regeneration — only the clue schedule is a real
# upstream of "chapters"; reveals: feeds only readback. ----------------------

def _chapters_ready(root, book="01"):
    """Stamp every stage through "chapters" (incl. the whodunit ledger, per
    FINDING 3), so the returned whodunit path can be edited to isolate what
    that edit does to the "chapters" verdict."""
    prem = _write(root, f"input/book-{book}/plot/premise.md")
    end = _write(root, f"input/book-{book}/plot/ending.md")
    tp = _write(root, f"input/book-{book}/plot/turning-points.md")
    sol = _write(root, f"output/book-{book}/mystery-solution.md")
    wd = _whodunit(root, book=book)
    skel = _write(root, f"input/book-{book}/outline-skeleton.md",
                  "---\nwoven: true\n---\n## Chapter 01 — A\n")
    stamp(book, end, [prem], repo_root=root)
    stamp(book, tp, [prem, end], repo_root=root)
    stamp(book, sol, [end, tp], repo_root=root)
    stamp(book, skel, [tp, sol, wd], repo_root=root)
    return wd


def test_declaring_reveals_leaves_next_stage_unchanged(tmp_path):
    """Regression pin for C1: writing a reveals: block onto an already-stamped
    ledger must not make "chapters" go stale — next_stage() must not step
    backwards to "chapters"."""
    root = _series(tmp_path)
    wd = _chapters_ready(root)
    rows = stage_status("01", repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"

    wd.write_text(wd.read_text(encoding="utf-8") + (
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
    ), encoding="utf-8")

    rows = stage_status("01", repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"
    assert next_stage(rows) != "chapters"


def test_editing_clue_schedule_still_makes_chapters_stale(tmp_path):
    """The link that must survive C1's fix: the clue schedule genuinely feeds
    chapter-weaver, so editing it (unlike editing reveals:) must still make
    "chapters" stale."""
    root = _series(tmp_path)
    wd = _chapters_ready(root)
    assert dict((n, s) for n, s, _ in stage_status("01", repo_root=root))["chapters"] == "done"

    wd.write_text(wd.read_text(encoding="utf-8") + (
        "clue_schedule:\n- id: c01-early-key-note\n  chapter: 2\n"
    ), encoding="utf-8")

    rows = stage_status("01", repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "stale"


def test_upstream_sha_without_reveals_is_blank_line_insensitive(tmp_path):
    """RULING (final review re-review): the whitespace-proof fingerprint
    applies to EVERY whodunit ledger, not just ones that declare reveals: —
    so a ledger with no reveals: key no longer equals the bare _sha(path)
    (that was the old, whitespace-EXACT contract this test used to pin; it
    broke the moment spec §3's own documented example layout — a blank line
    before reveals: — was followed). This is a SANCTIONED test-contract
    change, not a weakening: what must hold now is that hashing a ledger's
    non-blank lines is insensitive to blank lines with nothing else changed,
    and the formula is pinned explicitly below."""
    root = _series(tmp_path)
    wd = _whodunit(root)
    no_blank = _upstream_sha(wd)
    wd.write_text(wd.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    with_blank = _upstream_sha(wd)
    assert no_blank == with_blank

    non_blank_text = "".join(
        line for line in wd.read_text(encoding="utf-8").splitlines(keepends=True)
        if line.strip())
    assert with_blank == hashlib.sha256(non_blank_text.encode("utf-8")).hexdigest()


def test_declaring_reveals_with_blank_line_before_leaves_next_stage_unchanged(tmp_path):
    """RULING (final review re-review): spec §3's own reveals: example puts a
    blank line between reveal_chapter: and reveals: — a showrunner following
    the docs must not go stale for it."""
    root = _series(tmp_path)
    wd = _chapters_ready(root)
    wd.write_text(wd.read_text(encoding="utf-8") + "\n" + (
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
    ), encoding="utf-8")

    rows = stage_status("01", repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"
    assert next_stage(rows) != "chapters"


def test_declaring_reveals_with_blank_line_after_leaves_next_stage_unchanged(tmp_path):
    root = _series(tmp_path)
    wd = _chapters_ready(root)
    wd.write_text(wd.read_text(encoding="utf-8") + (
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
        "\n"
    ), encoding="utf-8")

    rows = stage_status("01", repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"
    assert next_stage(rows) != "chapters"


def test_reveals_inserted_before_a_pre_existing_trailing_comment_leaves_chapters_done(tmp_path):
    """A column-0 comment that PRE-EXISTS the reveals: block is real content
    the block doesn't own and must survive being stripped, not be swept away
    with it (final review re-review — an earlier version's boundary regex
    excluded '#' from ending the block, so a standalone comment sitting right
    after an inserted reveals: block was deleted along with it, moving the
    hash even though the comment itself never changed)."""
    root = _series(tmp_path)
    book = "01"
    prem = _write(root, f"input/book-{book}/plot/premise.md")
    end = _write(root, f"input/book-{book}/plot/ending.md")
    tp = _write(root, f"input/book-{book}/plot/turning-points.md")
    sol = _write(root, f"output/book-{book}/mystery-solution.md")
    wd = _write(root, f"series/whodunit/book-{book}.yaml",
                "book: '01'\ntotal_chapters: 30\nreveal_chapter: 26\n"
                "# a trailing note\n")
    skel = _write(root, f"input/book-{book}/outline-skeleton.md",
                  "---\nwoven: true\n---\n## Chapter 01 — A\n")
    stamp(book, end, [prem], repo_root=root)
    stamp(book, tp, [prem, end], repo_root=root)
    stamp(book, sol, [end, tp], repo_root=root)
    stamp(book, skel, [tp, sol, wd], repo_root=root)
    assert dict((n, s) for n, s, _ in stage_status(book, repo_root=root))["chapters"] == "done"

    wd.write_text(
        "book: '01'\ntotal_chapters: 30\nreveal_chapter: 26\n"
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
        "# a trailing note\n",
        encoding="utf-8")

    rows = stage_status(book, repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"
    assert next_stage(rows) != "chapters"


def test_declaring_then_removing_reveals_returns_to_the_original_fingerprint(tmp_path):
    """Round-trip: declaring reveals: and later deleting it again must not
    leave chapters stale either way — the whitespace-proof rule has no memory
    of what used to be there, only of what's on the page now."""
    root = _series(tmp_path)
    wd = _chapters_ready(root)
    original = wd.read_text(encoding="utf-8")
    wd.write_text(original + (
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
    ), encoding="utf-8")
    assert dict((n, s) for n, s, _ in stage_status("01", repo_root=root))["chapters"] == "done"

    wd.write_text(original, encoding="utf-8")   # reveals: removed again

    rows = stage_status("01", repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"
    assert next_stage(rows) != "chapters"


def test_declaring_reveals_in_the_middle_of_the_ledger_leaves_chapters_done(tmp_path):
    """Text-level stripping, not a yaml.safe_dump round-trip, is what makes
    C1's fix work — and inserting reveals: BETWEEN two existing keys (not
    just appending at EOF) is the case most likely to break line-boundary
    logic. Stripping the inserted block should restore the original bytes
    exactly, same as the append case."""
    root = _series(tmp_path)
    book = "01"
    prem = _write(root, f"input/book-{book}/plot/premise.md")
    end = _write(root, f"input/book-{book}/plot/ending.md")
    tp = _write(root, f"input/book-{book}/plot/turning-points.md")
    sol = _write(root, f"output/book-{book}/mystery-solution.md")
    wd = _write(root, f"series/whodunit/book-{book}.yaml",
                "book: '01'\n"
                "total_chapters: 30\n"
                "clue_schedule:\n"
                "- id: c01-early-key-note\n"
                "  chapter: 2\n"
                "reveal_chapter: 26\n")
    skel = _write(root, f"input/book-{book}/outline-skeleton.md",
                  "---\nwoven: true\n---\n## Chapter 01 — A\n")
    stamp(book, end, [prem], repo_root=root)
    stamp(book, tp, [prem, end], repo_root=root)
    stamp(book, sol, [end, tp], repo_root=root)
    stamp(book, skel, [tp, sol, wd], repo_root=root)
    assert dict((n, s) for n, s, _ in stage_status(book, repo_root=root))["chapters"] == "done"

    # Insert reveals: between total_chapters: and clue_schedule:, not at EOF.
    wd.write_text(
        "book: '01'\n"
        "total_chapters: 30\n"
        "reveals:\n"
        "- id: impersonation\n"
        "  reveal_chapter: 15\n"
        "  author_truth: Someone used Maggie's identity before she arrived.\n"
        "clue_schedule:\n"
        "- id: c01-early-key-note\n"
        "  chapter: 2\n"
        "reveal_chapter: 26\n",
        encoding="utf-8")

    rows = stage_status(book, repo_root=root)
    assert dict((n, s) for n, s, _ in rows)["chapters"] == "done"
    assert next_stage(rows) != "chapters"


def test_stamp_creates_frontmatter_if_absent(tmp_path):
    root = _series(tmp_path)
    prem = _write(root, "input/book-01/plot/premise.md", "no frontmatter here\n")
    end = _write(root, "input/book-01/plot/ending.md", "also bare\n")
    stamp("01", end, [prem], repo_root=root)
    assert "built_from_premise:" in end.read_text(encoding="utf-8")


WIRED_CLEAN = Path("tests/fixtures/outlines/wired-clean.md")


def test_readers_copy_keeps_story_drops_wiring_and_solution():
    out = readers_copy_text(WIRED_CLEAN.read_text(encoding="utf-8"))
    assert "## Chapter 01" in out and "Maggie arrives" in out
    assert "Solution" not in out and "Mary" not in out.split("Chapter 01")[0]
    assert "q-" not in out                      # no question ids anywhere
    assert "**Because:**" not in out and "**Opens:**" not in out
    assert "Track Movement" not in out and "**M:**" not in out


def test_readers_copy_keeps_hook_prose_without_id():
    out = readers_copy_text(WIRED_CLEAN.read_text(encoding="utf-8"))
    assert "the doctor is dead on his own kitchen floor." in out


def test_readers_copy_scrubs_malformed_hook_missing_separator():
    # A Hook line that doesn't follow the canonical "id — prose" shape (no
    # em-dash/hyphen separator between the question id and the prose) must
    # still lose its question id: the blind guarantee is enforced at the
    # strip itself, not by trusting that tension_check's broken-hook rule
    # already rejected malformed wiring before this ever runs.
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
- **Hook:** q-a the doctor is dead on his own kitchen floor
- **Because:** opening
"""
    out = readers_copy_text(text)
    assert "q-" not in out
    assert "the doctor is dead on his own kitchen floor" in out


def test_readers_copy_writes_report_file(tmp_path):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text(WIRED_CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    p = readers_copy("01", repo_root=tmp_path)
    assert p == tmp_path / "output/book-01/reports/outline-readers-copy.md"
    assert p.is_file() and "q-" not in p.read_text(encoding="utf-8")


def test_readers_copy_end_to_end_from_outline_when_no_skeleton(tmp_path):
    """End-to-end wiring check (spec 2026-07-31 §3.3): a book whose skeleton
    has been retired — ONLY outline.md remains, no outline-skeleton.md at all —
    must still produce a reader's copy, and it must be cut from outline.md.
    Every other readers_copy test in this file writes outline-skeleton.md, so
    without this test a regression in the one-line _readback_source wiring at
    this call site would pass the whole suite."""
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True)
    (d / "outline.md").write_text(WIRED_CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    assert not (d / "outline-skeleton.md").exists()
    p = readers_copy("01", repo_root=tmp_path)
    assert p == tmp_path / "output/book-01/reports/outline-readers-copy.md"
    assert p.is_file()
    out = p.read_text(encoding="utf-8")
    assert "Maggie arrives" in out  # content unique to outline.md's fixture text
    assert "q-" not in out  # solution/wiring still stripped


# --- FINDING 1: the H3 subsection strip must not fail open ------------------

def test_track_rows_dropped_under_lowercase_track_movement_heading():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Track movement
- **M:** Mary moves the body.
"""
    out = readers_copy_text(text)
    assert "**M:**" not in out and "Mary moves the body" not in out


def test_track_rows_dropped_under_bare_tracks_heading():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Tracks
- **M:** Mary moves the body.
"""
    out = readers_copy_text(text)
    assert "**M:**" not in out and "Mary moves the body" not in out


def test_track_rows_dropped_under_h4_track_movement_heading():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

#### Track Movement
- **M:** Mary moves the body.
"""
    out = readers_copy_text(text)
    assert "**M:**" not in out and "Mary moves the body" not in out


def test_track_rows_dropped_with_no_heading_at_all():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
- **Turn / Change:** Something happens.
- **M:** Mary moves the body.
"""
    out = readers_copy_text(text)
    assert "**M:**" not in out and "Mary moves the body" not in out
    assert "Something happens" in out  # unrelated line under the same heading survives


def _track_row_text(row: str) -> str:
    return f"""---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
{row}
"""


def test_track_row_asterisk_bullet_dropped():
    out = readers_copy_text(_track_row_text("* **M:** Mary poisons the tea."))
    assert "Mary poisons the tea" not in out and "**M:**" not in out


def test_track_row_no_space_after_dash_dropped():
    out = readers_copy_text(_track_row_text("-**M:** Mary poisons the tea."))
    assert "Mary poisons the tea" not in out and "**M:**" not in out


def test_track_row_no_bullet_at_all_dropped():
    out = readers_copy_text(_track_row_text("**M:** Mary poisons the tea."))
    assert "Mary poisons the tea" not in out and "**M:**" not in out


def test_track_row_colon_outside_bold_dropped():
    out = readers_copy_text(_track_row_text("- **M**: Mary poisons the tea."))
    assert "Mary poisons the tea" not in out


def test_track_row_lowercase_letter_dropped():
    out = readers_copy_text(_track_row_text("- **m:** Mary poisons the tea."))
    assert "Mary poisons the tea" not in out and "**m:**" not in out


def test_track_row_multiletter_key_dropped():
    out = readers_copy_text(_track_row_text("- **MC:** Mary poisons the tea."))
    assert "Mary poisons the tea" not in out and "**MC:**" not in out


def test_track_row_canonical_still_dropped():
    out = readers_copy_text(_track_row_text("- **M:** x."))
    assert "**M:**" not in out and " x." not in out


def test_track_row_em_dash_bullet_dropped():
    # Found by the adversarial sweep: an em-dash bullet ("—", distinct from
    # "-*+") escaped the original permissive pattern because a track row's
    # prose has no content-level backstop (unlike a wiring field's q- id,
    # which the unconditional _QID_TOKEN_RE scrub catches regardless of
    # bullet shape). This codebase already treats em-dash and hyphen as
    # interchangeable elsewhere (CHAPTER_RE's "[—-]" separator).
    out = readers_copy_text(_track_row_text("— **M:** Mary poisons the tea."))
    assert "Mary poisons the tea" not in out and "**M:**" not in out


def test_track_drop_does_not_eat_turn_change_row():
    out = readers_copy_text(_track_row_text("- **Turn / Change:** Something happens."))
    assert "Something happens" in out


def test_track_drop_does_not_eat_hook_row():
    out = readers_copy_text(_track_row_text("- **Hook:** q-a — the doctor is dead."))
    assert "the doctor is dead" in out


def test_track_drop_does_not_eat_bolded_prose_without_colon():
    out = readers_copy_text(_track_row_text("- **Maggie** went to the shop."))
    assert "Maggie" in out and "went to the shop" in out


def test_chapter_internal_solution_heading_dropped():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Solution
Mary did it, for the letter.

### Chapter Structure
- **Turn / Change:** Something happens.
"""
    out = readers_copy_text(text)
    assert "Mary did it" not in out
    assert "Something happens" in out


# --- FINDING 2: non-canonical wiring bullets must not leak question ids -----

def test_asterisk_bullet_closes_field_dropped():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
* **Closes:** q-who-killed-neil
"""
    out = readers_copy_text(text)
    assert "q-" not in out


def test_dash_no_space_carries_field_dropped():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
-**Carries:** q-elspeth-vale
"""
    out = readers_copy_text(text)
    assert "q-" not in out


def test_colon_outside_bold_opens_field_dropped():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
- **Opens**: q-sneaky — colon outside the bold
"""
    out = readers_copy_text(text)
    assert "q-" not in out


def test_no_bullet_at_all_opens_field_dropped():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
**Opens:** q-x — who killed the GP?
"""
    out = readers_copy_text(text)
    assert "q-" not in out


def test_case_drifted_hook_still_scrubs_question_id():
    # "hook" (lowercase) misses FIELD_RE's exact case, and Hook is
    # deliberately excluded from _WIRING_DROP_RE so its prose can survive —
    # so this line only loses its id via the unconditional belt-and-braces
    # scrub (FINDING 2), not via either field-shape pattern.
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Structure
- **hook:** q-who-killed-neil — the doctor is dead.
"""
    out = readers_copy_text(text)
    assert "q-" not in out
    assert "the doctor is dead" in out


def test_question_id_in_bare_prose_is_scrubbed_anywhere():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Chapter Summary
Maggie mutters q-who-killed-neil under her breath, unprompted.
"""
    out = readers_copy_text(text)
    assert "q-" not in out
    assert "Maggie mutters" in out and "under her breath" in out


# --- FINDING 3: truncate before the reveal chapter --------------------------

def test_reveal_chapter_truncates_and_notes_it():
    out = readers_copy_text(WIRED_CLEAN.read_text(encoding="utf-8"), reveal_chapter=5)
    assert "## Chapter 04" in out
    assert "## Chapter 05" not in out and "## Chapter 06" not in out
    assert "Chapters 1–4" in out
    assert "deliberately withheld" in out


def test_no_reveal_chapter_emits_everything_and_no_note():
    out = readers_copy_text(WIRED_CLEAN.read_text(encoding="utf-8"), reveal_chapter=None)
    assert "## Chapter 06" in out
    assert "deliberately withheld" not in out
    assert "Chapters 1" not in out.splitlines()[1]  # no truncation line at all


def test_readers_copy_reads_reveal_chapter_from_whodunit_ledger(tmp_path):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text(WIRED_CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    wd = tmp_path / "series/whodunit"
    wd.mkdir(parents=True)
    (wd / "book-01.yaml").write_text("reveal_chapter: 5\nculprit: Mary\n", encoding="utf-8")
    p = readers_copy("01", repo_root=tmp_path)
    out = p.read_text(encoding="utf-8")
    assert "## Chapter 04" in out
    assert "## Chapter 05" not in out
    assert "deliberately withheld" in out


def test_readers_copy_with_no_ledger_emits_all_chapters(tmp_path):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text(WIRED_CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    p = readers_copy("01", repo_root=tmp_path)
    out = p.read_text(encoding="utf-8")
    assert "## Chapter 06" in out
    assert "deliberately withheld" not in out


def _ledger_series(tmp_path, ledger_text):
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input/book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text(WIRED_CLEAN.read_text(encoding="utf-8"), encoding="utf-8")
    wd = tmp_path / "series/whodunit"
    wd.mkdir(parents=True)
    (wd / "book-01.yaml").write_text(ledger_text, encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("ledger_text", [
    "reveal_chapter: five\nculprit: Mary\n",     # not an integer
    "reveal_chapter:\nculprit: Mary\n",          # null
    "reveal_chapter: true\nculprit: Mary\n",     # boolean
    "culprit: Mary\n",                           # key missing entirely
])
def test_present_ledger_with_invalid_reveal_chapter_exits_loud(tmp_path, ledger_text):
    root = _ledger_series(tmp_path, ledger_text)
    with pytest.raises(SystemExit) as e:
        readers_copy("01", repo_root=root)
    assert "plot_stage:" in str(e.value)
    assert "reveal_chapter" in str(e.value)


def test_reveal_chapter_accepts_numeric_string(tmp_path):
    # _reveal_chapter deliberately tolerates reveal_chapter: '15' (string) —
    # this tolerance is critical to preserve through the _load_whodunit refactor.
    root = _ledger_series(tmp_path, "reveal_chapter: '5'\nculprit: Mary\n")
    p = readers_copy("01", repo_root=root)
    out = p.read_text(encoding="utf-8")
    assert "## Chapter 04" in out
    assert "## Chapter 05" not in out


# --- FINAL REVIEW FINDING 1: an out-of-range reveal_chapter must not un-blind
# the fan by falling through to "emit everything, no truncation" -------------

def test_reveal_chapter_beyond_last_chapter_exits_loud(tmp_path):
    # WIRED_CLEAN has 6 chapters; reveal_chapter: 9 has nothing to truncate
    # before, so readers_copy_text would silently emit every chapter —
    # including the reveal chapter's own culprit-naming summary — unless
    # readers_copy() catches the out-of-range value first.
    root = _ledger_series(tmp_path, "reveal_chapter: 9\nculprit: Mary\n")
    with pytest.raises(SystemExit) as e:
        readers_copy("01", repo_root=root)
    assert "plot_stage:" in str(e.value)
    assert "reveal_chapter" in str(e.value)


def test_reveal_chapter_equal_to_last_chapter_is_not_out_of_range(tmp_path):
    # reveal_chapter == the last chapter is the normal case (truncate before
    # it) — must NOT be treated as out-of-range.
    root = _ledger_series(tmp_path, "reveal_chapter: 6\nculprit: Mary\n")
    p = readers_copy("01", repo_root=root)
    out = p.read_text(encoding="utf-8")
    assert "## Chapter 05" in out
    assert "## Chapter 06" not in out


def test_malformed_yaml_ledger_exits_with_named_error_not_traceback(tmp_path):
    root = _ledger_series(tmp_path, "reveal_chapter: [unterminated\n")
    with pytest.raises(SystemExit) as e:
        readers_copy("01", repo_root=root)
    assert "plot_stage:" in str(e.value)


def test_list_shaped_ledger_exits_with_named_error_not_traceback(tmp_path):
    root = _ledger_series(tmp_path, "- reveal_chapter: 5\n- culprit: Mary\n")
    with pytest.raises(SystemExit) as e:
        readers_copy("01", repo_root=root)
    assert "plot_stage:" in str(e.value)


def test_resolution_heading_survives_the_solution_drop():
    text = """---
book: 01
total_chapters: 1
---

## Chapter 01 — One

### Resolution
Everything wraps up nicely for the town.
"""
    out = readers_copy_text(text)
    assert "Everything wraps up nicely" in out


# --- Re-verify the blind guarantee over every wired-* fixture ---------------

def test_no_leaks_survive_in_any_wired_fixture():
    for path in sorted(glob.glob("tests/fixtures/outlines/wired-*.md")):
        out = readers_copy_text(Path(path).read_text(encoding="utf-8"))
        assert "q-" not in out, f"question id leaked in {path}"
        for field in ("**Because:**", "**Opens:**", "**Closes:**", "**Carries:**"):
            assert field not in out, f"{field} leaked in {path}"
        assert "Solution" not in out, f"Solution leaked in {path}"
        assert "**M:**" not in out, f"track row leaked in {path}"


# --- Chapter-title flags ([type: ...] / [long: ...]) are a spoiler --------
# A flagged heading like "## Chapter 14 — The Reveal [type: major-reveal]"
# tells the blind reader exactly which chapter is the reveal. The strip must
# be by construction, so it reuses penny_wiring's own TYPE_FLAG_RE/LONG_FLAG_RE
# — never a second, forkable pattern.

WEIGHTED = Path("tests/fixtures/outlines/weighted-clean.md")


def test_readers_copy_strips_title_flags_from_flagged_heading():
    out = readers_copy_text(WEIGHTED.read_text(encoding="utf-8"))
    assert "## Chapter 02 — The Reveal" in out
    assert "[type:" not in out and "[long:" not in out
    assert "major-reveal" not in out
    assert "the confession runs its full course" not in out


def test_readers_copy_unflagged_heading_round_trips_unchanged():
    out = readers_copy_text(WEIGHTED.read_text(encoding="utf-8"))
    assert "## Chapter 01 — The Wheelhouse" in out


# --- reveal_stages: derive stage boundaries from protected turns ---------

def test_reveal_stages_empty_when_no_reveals():
    assert reveal_stages([]) == []


def test_reveal_stages_two_reveals_gives_three_stages():
    reveals = [{"id": "a", "reveal_chapter": 15, "author_truth": "x"},
               {"id": "b", "reveal_chapter": 27, "author_truth": "y"}]
    assert reveal_stages(reveals) == [14, 26, None]


def test_reveal_stages_single_reveal_gives_two_stages():
    assert reveal_stages([{"id": "a", "reveal_chapter": 15, "author_truth": "x"}]) == [14, None]


def test_reveal_stages_dedupes_shared_chapter():
    reveals = [{"id": "a", "reveal_chapter": 27, "author_truth": "x"},
               {"id": "b", "reveal_chapter": 27, "author_truth": "y"}]
    assert reveal_stages(reveals) == [26, None]


# --- readers_copy_text: staged (last_chapter) vs legacy (reveal_chapter) cut

_SKEL = """---
book: '01'
total_chapters: 4
---

## Chapter 01 — Arrival

### Required Beats
- Maggie arrives.

- **Hook:** q-start — what is wrong with the studio?
- **Opens:** q-start
### Track Movement
- **M:** Setup.

## Chapter 02 — The Key

### Required Beats
- An odd early key note surfaces.

## Chapter 03 — The Turn

### Required Beats
- The case changes shape.

## Chapter 04 — The End

### Required Beats
- Maggie names the culprit.
"""


def test_readers_copy_text_last_chapter_is_inclusive():
    out = readers_copy_text(_SKEL, last_chapter=2)
    assert "## Chapter 02" in out
    assert "## Chapter 03" not in out
    assert "Chapters 1–2" in out


def test_readers_copy_text_rejects_both_cut_params():
    with pytest.raises(ValueError):
        readers_copy_text(_SKEL, reveal_chapter=3, last_chapter=2)


def test_readers_copy_text_last_chapter_none_emits_all():
    out = readers_copy_text(_SKEL, last_chapter=None)
    assert "## Chapter 04" in out
    assert "The book continues past this point" not in out


def test_readers_copy_text_still_strips_wiring_at_every_cut():
    for kwargs in ({"last_chapter": 2}, {"last_chapter": None}, {"reveal_chapter": 3}):
        out = readers_copy_text(_SKEL, **kwargs)
        assert "**Opens:**" not in out
        assert "q-start" not in out
        assert "**M:**" not in out


def test_readers_copy_staged_writes_one_file_per_stage(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n"
           "reveals:\n- id: turn\n  reveal_chapter: 3\n  author_truth: The case turns.\n")
    paths = readers_copy_staged("01", repo_root=root)
    assert [p.name for p in paths] == ["outline-readers-copy-stage-1.md",
                                       "outline-readers-copy-stage-2.md"]
    s1 = paths[0].read_text(encoding="utf-8")
    assert "## Chapter 02" in s1 and "## Chapter 03" not in s1
    s2 = paths[1].read_text(encoding="utf-8")
    assert "## Chapter 04" in s2


def test_readers_copy_staged_end_to_end_from_outline_when_no_skeleton(tmp_path):
    """End-to-end wiring check (spec 2026-07-31 §3.3): identical to
    test_readers_copy_staged_writes_one_file_per_stage above, except the book
    has ONLY outline.md — no outline-skeleton.md at all — which is exactly the
    state the live book will be in once its drifted skeleton is deleted.
    Every other readers_copy_staged test in this file writes
    outline-skeleton.md, so without this test a regression in the one-line
    _readback_source wiring at this call site would pass the whole suite."""
    root = _series(tmp_path)
    _write(root, "input/book-01/outline.md", _SKEL)
    assert not (root / "input/book-01/outline-skeleton.md").exists()
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n"
           "reveals:\n- id: turn\n  reveal_chapter: 3\n  author_truth: The case turns.\n")
    paths = readers_copy_staged("01", repo_root=root)
    assert [p.name for p in paths] == ["outline-readers-copy-stage-1.md",
                                       "outline-readers-copy-stage-2.md"]
    s1 = paths[0].read_text(encoding="utf-8")
    assert "## Chapter 02" in s1 and "## Chapter 03" not in s1
    s2 = paths[1].read_text(encoding="utf-8")
    assert "## Chapter 04" in s2


def test_readers_copy_staged_is_cumulative_from_chapter_one(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n"
           "reveals:\n- id: turn\n  reveal_chapter: 3\n  author_truth: The case turns.\n")
    s2 = readers_copy_staged("01", repo_root=root)[1].read_text(encoding="utf-8")
    assert "## Chapter 01" in s2  # spec §4: cumulative, not just the new chapters


def test_readers_copy_staged_returns_empty_without_reveals(tmp_path):
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n")
    assert readers_copy_staged("01", repo_root=root) == []


def test_legacy_readers_copy_unchanged_without_reveals(tmp_path):
    """Regression pin — the legacy invariant (Global Constraints)."""
    root = _series(tmp_path)
    _write(root, "input/book-01/outline-skeleton.md", _SKEL)
    _write(root, "series/whodunit/book-01.yaml",
           "book: '01'\ntotal_chapters: 4\nreveal_chapter: 4\n")
    dest = readers_copy("01", repo_root=root)
    assert dest.name == "outline-readers-copy.md"
    assert dest.read_text(encoding="utf-8") == readers_copy_text(_SKEL, reveal_chapter=4)


def _readback_ready(root, book="01"):
    """A book whose earlier stages are all done, so stage_status's verdict on
    readback is the only thing under test.

    T7-deferred (final review): this must stamp the whodunit ledger too, since
    "chapters" (final review FINDING 3 / C1) counts it as a real upstream —
    without it "chapters" itself reads "stale" and the docstring's claim would
    be false, even though every test below only asserts on "readback"."""
    skel = _write(root, f"input/book-{book}/outline-skeleton.md",
                  "---\nwoven: true\n---\n## Chapter 01 — A\n")
    prem = _write(root, f"input/book-{book}/plot/premise.md")
    end = _write(root, f"input/book-{book}/plot/ending.md")
    tp = _write(root, f"input/book-{book}/plot/turning-points.md")
    sol = _write(root, f"output/book-{book}/mystery-solution.md")
    wd = _whodunit(root, book=book)
    stamp(book, end, [prem], repo_root=root)
    stamp(book, tp, [prem, end], repo_root=root)
    stamp(book, sol, [end, tp], repo_root=root)
    stamp(book, skel, [tp, sol, wd], repo_root=root)
    return skel


def _readback_state(root, book="01"):
    return dict((n, s) for n, s, _ in stage_status(book, repo_root=root))["readback"]


def test_readback_missing_when_no_fan_report(tmp_path):
    root = _series(tmp_path)
    _readback_ready(root)
    assert _readback_state(root) == "missing"


def test_readback_done_from_a_staged_fan_report(tmp_path):
    root = _series(tmp_path)
    skel = _readback_ready(root)
    fan = _write(root, "output/book-01/reports/outline-fan-stage-1.md")
    stamp("01", fan, [skel], repo_root=root)
    assert _readback_state(root) == "done"


def test_readback_done_only_when_every_stage_report_is_stamped(tmp_path):
    root = _series(tmp_path)
    skel = _readback_ready(root)
    f1 = _write(root, "output/book-01/reports/outline-fan-stage-1.md")
    f2 = _write(root, "output/book-01/reports/outline-fan-stage-2.md")
    stamp("01", f1, [skel], repo_root=root)
    assert _readback_state(root) == "stale"   # f2 unstamped
    stamp("01", f2, [skel], repo_root=root)
    assert _readback_state(root) == "done"


def test_readback_goes_stale_when_the_skeleton_changes(tmp_path):
    root = _series(tmp_path)
    skel = _readback_ready(root)
    fan = _write(root, "output/book-01/reports/outline-fan-stage-1.md")
    stamp("01", fan, [skel], repo_root=root)
    assert _readback_state(root) == "done"
    skel.write_text("---\nwoven: true\n---\n## Chapter 01 — A\n## Chapter 02 — B\n",
                    encoding="utf-8")
    assert _readback_state(root) == "stale"


def test_readback_detail_names_the_offending_report(tmp_path):
    root = _series(tmp_path)
    skel = _readback_ready(root)
    _write(root, "output/book-01/reports/outline-fan-stage-1.md")
    detail = dict((n, d) for n, _, d in stage_status("01", repo_root=root))["readback"]
    assert "outline-fan-stage-1" in detail


def test_legacy_unstaged_fan_report_still_counts(tmp_path):
    """A book read back before this change wrote plain outline-fan.md. The glob
    must keep recognising it — an existing series must not be told to redo its
    readback."""
    root = _series(tmp_path)
    skel = _readback_ready(root)
    fan = _write(root, "output/book-01/reports/outline-fan.md")
    stamp("01", fan, [skel], repo_root=root)
    assert _readback_state(root) == "done"


def test_readback_source_prefers_the_skeleton_when_present(tmp_path):
    from scripts import plot_stage
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input" / "book-01"
    d.mkdir(parents=True)
    (d / "outline-skeleton.md").write_text("## Chapter 01 — S\n", encoding="utf-8")
    (d / "outline.md").write_text("## Chapter 01 — O\n", encoding="utf-8")
    assert plot_stage._readback_source("01", repo_root=tmp_path).name == "outline-skeleton.md"


def test_readback_source_falls_back_to_the_outline(tmp_path):
    """The skeleton is retired (spec 2026-07-31 §3.3). A book that has only
    outline.md must still be readable — book 01's skeleton is a different book."""
    from scripts import plot_stage
    (tmp_path / ".penny").mkdir()
    d = tmp_path / "input" / "book-01"
    d.mkdir(parents=True)
    (d / "outline.md").write_text("## Chapter 01 — O\n", encoding="utf-8")
    assert plot_stage._readback_source("01", repo_root=tmp_path).name == "outline.md"


def test_readback_source_fails_loud_when_neither_exists(tmp_path):
    from scripts import plot_stage
    (tmp_path / ".penny").mkdir()
    (tmp_path / "input" / "book-01").mkdir(parents=True)
    with pytest.raises(SystemExit, match="no outline"):
        plot_stage._readback_source("01", repo_root=tmp_path)
