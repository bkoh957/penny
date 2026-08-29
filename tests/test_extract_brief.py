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


# --- the runbook itself ---

COMMAND_MD = Path(__file__).resolve().parents[1] / "commands" / "finalize-chapter.md"


def test_finalize_chapter_runbook_calls_the_script_not_awk():
    text = COMMAND_MD.read_text(encoding="utf-8")
    assert "scripts/extract_brief.py" in text
    assert "awk" not in text


def test_finalize_chapter_runbook_explains_why_its_a_script():
    text = COMMAND_MD.read_text(encoding="utf-8")
    assert "interpolated" in text
