JSON_41 = '{"context_window": {"used_percentage": 41.2}}'
JSON_NONE = '{}'


def test_idle_when_no_stage_file(penny_root):
    # Remove the .penny dir to simulate a fresh repo.
    (penny_root.path / ".penny").rmdir()
    out = penny_root.run(JSON_41)
    assert out == "Penny · idle · ctx 41%"


def test_series_name_prefixed_when_inside_a_series(penny_root):
    # The series root is resolved via the penny_paths CLI shim (not $PENNY_ROOT
    # blind trust) and its folder name is prepended to the rendered line.
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    out = penny_root.run(JSON_41)
    assert out.startswith(f"[{penny_root.path.name}] Penny · Book 01")


def test_full_render_with_outline_and_blocking(penny_root):
    penny_root.write_stage("book=03 chapter=07 stage=COPY-EDIT")
    penny_root.write_outline("03", 24)
    penny_root.write_blocking("03", "07", 2)
    out = penny_root.run(JSON_41)
    series = penny_root.path.name
    assert out == f"[{series}] Penny · Book 03 · Ch 7/24 · COPY-EDIT · gate: 2 blocking · ctx 41%"


def test_no_reviews_means_zero_blocking(penny_root):
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    penny_root.write_outline("01", 24)
    out = penny_root.run(JSON_41)
    series = penny_root.path.name
    assert out == f"[{series}] Penny · Book 01 · Ch 1/24 · DRAFT · gate: 0 blocking · ctx 41%"


def test_missing_context_percentage_renders_question_mark(penny_root):
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    penny_root.write_outline("01", 10)
    out = penny_root.run(JSON_NONE)
    assert out.endswith("ctx ?%")


def test_total_falls_back_to_current_chapter_without_outline(penny_root):
    penny_root.write_stage("book=02 chapter=05 stage=PLAN")
    out = penny_root.run(JSON_41)
    assert "Ch 5/5" in out


def test_total_counts_only_numbered_chapters(penny_root):
    # Non-chapter "## " sections (Solution, Threads, the tricky "Chapter Engine"
    # heading, an Act header) must not inflate the chapter total — only numbered
    # "## Chapter NN" headings count. Regression for the 5/39 status-bar bug.
    penny_root.write_stage("book=01 chapter=02 stage=DRAFT")
    d = penny_root.path / "input" / "book-01"
    d.mkdir(parents=True, exist_ok=True)
    outline = (
        "# Outline\n\n"
        "total_chapters: 3\n\n"
        "## Solution: the-central-mystery\n\n"
        "## Threads\n\n"
        "## Chapter Engine Used Throughout\n\n"
        "## Act I — Arrival\n\n"
        "## Chapter 01 — A\n\n"
        "## Chapter 02 — B\n\n"
        "## Chapter 03 — C\n\n"
    )
    (d / "outline.md").write_text(outline, encoding="utf-8")
    out = penny_root.run(JSON_41)
    assert "Ch 2/3" in out


def test_malformed_marker_missing_chapter_renders_safely(penny_root):
    # A partially-written marker (no chapter=) must not error or render garbage.
    penny_root.write_stage("book=01 stage=DRAFT")  # run() uses check=True
    out = penny_root.run(JSON_41)
    assert f"[{penny_root.path.name}] Penny · Book 01" in out
    assert "Ch 0/0" in out
    assert out.endswith("ctx 41%")
