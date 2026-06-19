JSON_41 = '{"context_window": {"used_percentage": 41.2}}'
JSON_NONE = '{}'


def test_idle_when_no_stage_file(penny_root):
    # Remove the .penny dir to simulate a fresh repo.
    (penny_root.path / ".penny").rmdir()
    out = penny_root.run(JSON_41)
    assert out == "Penny · idle · ctx 41%"


def test_full_render_with_outline_and_blocking(penny_root):
    penny_root.write_stage("book=03 chapter=07 stage=COPY-EDIT")
    penny_root.write_outline("03", 24)
    penny_root.write_blocking("03", "07", 2)
    out = penny_root.run(JSON_41)
    assert out == "Penny · Book 03 · Ch 7/24 · COPY-EDIT · gate: 2 blocking · ctx 41%"


def test_no_reviews_means_zero_blocking(penny_root):
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    penny_root.write_outline("01", 24)
    out = penny_root.run(JSON_41)
    assert out == "Penny · Book 01 · Ch 1/24 · DRAFT · gate: 0 blocking · ctx 41%"


def test_missing_context_percentage_renders_question_mark(penny_root):
    penny_root.write_stage("book=01 chapter=01 stage=DRAFT")
    penny_root.write_outline("01", 10)
    out = penny_root.run(JSON_NONE)
    assert out.endswith("ctx ?%")


def test_total_falls_back_to_current_chapter_without_outline(penny_root):
    penny_root.write_stage("book=02 chapter=05 stage=PLAN")
    out = penny_root.run(JSON_41)
    assert "Ch 5/5" in out
