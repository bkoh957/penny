"""extract_brief.py — spec 2026-08-29-runbook-render-corrupts-positional-vars-fix.md
§4b. Replaces `finalize-chapter.md` step 3a's inline awk, which read `$0`
(the whole matched line, always) as if it were the drafting model's first
positional argument once the runbook was rendered — an off-by-one in the
harness's substitution, not in the awk itself. `$brief` came out empty every
time, silently, and `ledger-updater` ran unscoped as a result. This module
lives in `scripts/`, which is never rendered into an agent's context, so no
substitution can reach it.

Fixture: tests/fixtures/outlines/packet-format.md — two packet-format
chapters, 05 (`[type: event]`) then 06 (`[type: standard]`), the same
fixture test_packet_assemble.py already shares.
"""
from pathlib import Path

import pytest

from scripts.extract_brief import extract_brief, main

FIX = Path(__file__).resolve().parent / "fixtures" / "outlines" / "packet-format.md"


def _series(tmp_path):
    (tmp_path / ".penny").mkdir()
    inp = tmp_path / "input" / "book-01"
    inp.mkdir(parents=True)
    (inp / "outline.md").write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


# --- core extraction ---

def test_brief_is_nonempty_and_starts_with_the_chapter_heading():
    brief = extract_brief(FIX.read_text(encoding="utf-8"), 5)
    assert brief.strip() != ""
    assert brief.startswith("## Chapter 05 — Opening Day [type: event]")


def test_brief_stops_before_the_next_chapter_heading():
    brief = extract_brief(FIX.read_text(encoding="utf-8"), 5)
    assert "## Chapter 06" not in brief
    assert "The Morning After" not in brief


def test_brief_carries_the_chapter_body():
    brief = extract_brief(FIX.read_text(encoding="utf-8"), 5)
    assert "Faye receives the death call." in brief


def test_missing_chapter_raises_by_name():
    with pytest.raises(ValueError, match=r"[Cc]hapter 99"):
        extract_brief(FIX.read_text(encoding="utf-8"), 99)


def test_zero_padded_and_unpadded_chapter_args_agree():
    text = FIX.read_text(encoding="utf-8")
    assert extract_brief(text, 5) == extract_brief(text, "05")
    assert extract_brief(text, "5") == extract_brief(text, "05")


def test_type_flag_is_preserved_in_the_heading():
    brief = extract_brief(FIX.read_text(encoding="utf-8"), 6)
    assert brief.startswith("## Chapter 06 — The Morning After [type: standard]")


# --- CLI ---

def test_main_writes_the_brief_to_stdout(tmp_path, monkeypatch, capsys):
    _series(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["01", "05"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("## Chapter 05 — Opening Day [type: event]")
    assert "## Chapter 06" not in out


def test_main_accepts_unpadded_book_and_chapter(tmp_path, monkeypatch, capsys):
    _series(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["1", "5"]) == 0
    assert capsys.readouterr().out.startswith("## Chapter 05")


def test_main_refuses_a_missing_chapter_loudly(tmp_path, monkeypatch, capsys):
    _series(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["01", "99"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "chapter 99" in captured.err.lower()


def test_main_refuses_a_missing_outline_by_name(tmp_path, monkeypatch, capsys):
    (tmp_path / ".penny").mkdir()
    monkeypatch.chdir(tmp_path)
    assert main(["01", "05"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no outline" in captured.err.lower() or "outline" in captured.err.lower()


def test_main_usage_error():
    assert main(["01"]) == 2


def test_main_rejects_non_numeric_chapter_loudly(tmp_path, monkeypatch, capsys):
    """Non-numeric chapter surfaces a named error, not Python's raw ValueError."""
    _series(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["01", "abc"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "chapter" in captured.err.lower()
    assert "number" in captured.err.lower() or "numeric" in captured.err.lower()
    assert "abc" in captured.err


def test_main_rejects_non_numeric_book_loudly(tmp_path, monkeypatch, capsys):
    """Non-numeric book surfaces a named error, not Python's raw ValueError."""
    (tmp_path / ".penny").mkdir()
    monkeypatch.chdir(tmp_path)
    assert main(["abc", "05"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "book" in captured.err.lower()
    assert "number" in captured.err.lower() or "numeric" in captured.err.lower()
    assert "abc" in captured.err


# --- self-review: identical to the old awk on a chapter that exists ---

def test_matches_the_awk_it_replaces(tmp_path):
    """Same content as the awk it replaces, for a chapter that exists. The
    only difference is two blank lines at the block's own boundaries (right
    after the heading, and right before the next one) — `chapter_block()`
    (the reused, shared parser; see module docstring) strips its slice, the
    awk did not. Reproducing that stripping exactly here would mean
    re-slicing the outline by hand instead of reusing `chapter_block()`,
    which is the third-parser fork this module was told not to write — so
    every *content* line is compared instead, in order."""
    import subprocess
    outline = FIX
    awk_script = (
        'awk -v h="## Chapter 05 " \'\n'
        "  index($0, h) == 1 { grab = 1; print; next }\n"
        "  grab && (/^## / || /^# /) { exit }\n"
        "  grab { print }\n"
        f"' {outline}"
    )
    awk_out = subprocess.run(awk_script, shell=True, capture_output=True,
                             text=True, check=True).stdout
    brief = extract_brief(outline.read_text(encoding="utf-8"), 5)

    awk_lines = [ln for ln in awk_out.splitlines() if ln.strip()]
    brief_lines = [ln for ln in brief.splitlines() if ln.strip()]
    assert brief_lines == awk_lines


def test_an_interposed_h1_is_not_a_boundary_unlike_the_awk():
    """The old awk stopped at either ## or # heading: `grab && (/^## / || /^# /)`.
    `chapter_block()` stops only at ^##, not at ^# — a divergence inherited from
    the reused parser. This differs from the awk it replaced. No current outline
    triggers it (the only ^# in config/outline-template.md and fixtures is the
    title line before all chapters). Changing chapter_block() to stop at h1 would
    alter what every chapter packet contains, which is a far bigger decision than
    this module's scope; the correct action is documenting it here."""
    outline_with_h1 = """---
book: 1
total_chapters: 2
---

# Book One

## Chapter 01 — First

Body of chapter one.

# Appendix

Appendix content.

## Chapter 02 — Second

Body of chapter two.
"""
    brief = extract_brief(outline_with_h1, 1)
    # The brief includes the appendix content (inherited, not a bug).
    assert "## Chapter 01 — First" in brief
    assert "Body of chapter one" in brief
    assert "# Appendix" in brief
    assert "Appendix content" in brief
    # The next chapter still stops the block.
    assert "## Chapter 02" not in brief
    assert "Body of chapter two" not in brief


# --- the runbook itself ---

COMMAND_MD = Path(__file__).resolve().parents[1] / "commands" / "finalize-chapter.md"


def test_finalize_chapter_runbook_calls_the_script_not_awk():
    text = COMMAND_MD.read_text(encoding="utf-8")
    assert "scripts/extract_brief.py" in text
    assert "awk" not in text


def test_finalize_chapter_runbook_explains_why_its_a_script():
    text = COMMAND_MD.read_text(encoding="utf-8")
    assert "interpolated" in text
