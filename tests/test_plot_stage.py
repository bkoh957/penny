import glob
from pathlib import Path

from scripts.plot_stage import (STAGE_ORDER, next_stage, readers_copy, readers_copy_text,
                                 stage_paths, stage_status, stamp)


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


# --- Re-verify the blind guarantee over every wired-* fixture ---------------

def test_no_leaks_survive_in_any_wired_fixture():
    for path in sorted(glob.glob("tests/fixtures/outlines/wired-*.md")):
        out = readers_copy_text(Path(path).read_text(encoding="utf-8"))
        assert "q-" not in out, f"question id leaked in {path}"
        for field in ("**Because:**", "**Opens:**", "**Closes:**", "**Carries:**"):
            assert field not in out, f"{field} leaked in {path}"
        assert "Solution" not in out, f"Solution leaked in {path}"
        assert "**M:**" not in out, f"track row leaked in {path}"
