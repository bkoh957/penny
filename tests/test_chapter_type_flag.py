# tests/test_chapter_type_flag.py
#
# The `[type: …]` band flag is plumbed end to end — cut plan -> story_cut ->
# outline.md -> packet_assemble's `## Word Budget` -> map_check — but until
# 2026-08-25 nothing exercised that chain, and `chapter-cutter` (the /plot-book
# door into an outline) never proposed a flag at all. Book 01's 35 chapters
# carry none, so its reveal and its confrontation are both priced at the
# default band. These pins hold the path open now that the cutter proposes it.
from pathlib import Path

from scripts import packet_assemble, story_cut
from scripts.penny_wiring import parse_wired_chapters

PROFILE = (
    "```yaml\n"
    "band_default: [2000, 2500]\n"
    "band_reveal: [2500, 3200]\n"
    "min_scene_words: 250\n"
    "```\n"
)


def _series(tmp_path, monkeypatch):
    (tmp_path / ".penny" / "locks").mkdir(parents=True)
    (tmp_path / ".penny" / "locks" / "book-02.mystery.lock").write_text(
        "locked\n", encoding="utf-8")
    (tmp_path / "input" / "book-02").mkdir(parents=True)
    (tmp_path / "series" / "whodunit").mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "series-guardrails.md").write_text(
        "Do not name the culprit early.\n", encoding="utf-8")
    (tmp_path / "config" / "length-profile.md").write_text(PROFILE, encoding="utf-8")
    (tmp_path / "input" / "book-02" / "story.md").write_text(
        "- Maggie chooses this life.\n  @maggie #establish-protected-world\n\n"
        "- The appointment was altered; Maggie names who altered it.\n"
        "  @maggie !c-altered +q-clear -q-clear\n\n"
        "## Questions\n- q-clear — how can Maggie clear herself?\n",
        encoding="utf-8")
    # Chapter 01 carries no flag (the default band is encoded by ABSENCE);
    # chapter 02 declares the reveal band.
    (tmp_path / "input" / "book-02" / "cut-plan.md").write_text(
        "## Chapter 01 — One\n\n- **Beats:** 1\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n\n"
        "## Chapter 02 — Two [type: reveal]\n\n- **Beats:** 2\n- **Summary:** s\n"
        "- **Compress:** c\n- **M:** m\n", encoding="utf-8")
    (tmp_path / "series" / "whodunit" / "book-02.yaml").write_text(
        "reveal_chapter: 2\nclue_schedule:\n  - id: c-altered\n    plant_chapter: 99\n"
        "    description: the handover appointment, changed\n", encoding="utf-8")
    monkeypatch.setattr(story_cut.penny_paths, "series_root", lambda *a, **k: tmp_path)
    monkeypatch.setattr(story_cut, "_job_ids_and_titles",
                        lambda: (["establish-protected-world"],
                                 {"establish-protected-world": "Establish the Protected World"}))
    return tmp_path


def test_the_flag_survives_the_cut_into_the_outline_heading(tmp_path, monkeypatch, capsys):
    root = _series(tmp_path, monkeypatch)
    assert story_cut.main(["02"]) == 0, capsys.readouterr().out
    text = (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8")
    assert "## Chapter 02 — Two [type: reveal]" in text
    # and the unflagged chapter is not "fixed up" with an explicit default
    assert "## Chapter 01 — One\n" in text
    assert "[type: default]" not in text


def test_the_flag_does_not_leak_into_the_displayed_title(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    story_cut.main(["02"])
    text = (root / "input" / "book-02" / "outline.md").read_text(encoding="utf-8")
    chapters = {c["num"]: c for c in parse_wired_chapters(text)}
    assert chapters[2]["title"] == "Two"
    assert chapters[2]["chapter_type"] == "reveal"
    assert chapters[1]["chapter_type"] is None


def test_the_packet_prices_the_flagged_chapter_at_its_own_band(tmp_path, monkeypatch):
    root = _series(tmp_path, monkeypatch)
    story_cut.main(["02"])
    flagged = packet_assemble.assemble("02", "02", repo_root=root).read_text(encoding="utf-8")
    plain = packet_assemble.assemble("02", "01", repo_root=root).read_text(encoding="utf-8")
    assert "Band: 2500–3200 words (type: reveal)" in flagged
    assert "Band: 2000–2500 words (type: default)" in plain
