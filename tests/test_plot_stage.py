import glob
from pathlib import Path

import pytest

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
