import json

from scripts import canon_core_review


def test_review_returns_empty_candidate_list(tmp_path):
    canon = tmp_path / "canon-core.md"
    canon.write_text("# canon\n", encoding="utf-8")
    assert canon_core_review.review("99", str(canon)) == []


def test_cli_prints_empty_json_list(capsys, tmp_path):
    canon = tmp_path / "canon-core.md"
    canon.write_text("# canon\n", encoding="utf-8")
    rc = canon_core_review.main(["--book", "99", "--canon-core", str(canon)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out) == []
