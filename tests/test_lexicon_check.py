import pytest

from scripts.lexicon_check import STAGE_RANK, scan

TERMS = [
    {"term": "arvo", "narration_ok_from_stage": "SETTLING", "auto_detectable": True},
    {"term": "the footy", "narration_ok_from_stage": "BELONGING", "auto_detectable": True},
    {"term": "bogan", "narration_ok_from_stage": "SETTLING", "auto_detectable": False},
]


def test_stage_rank_is_ordered():
    assert STAGE_RANK["OUTSIDER"] < STAGE_RANK["SETTLING"] < STAGE_RANK["BELONGING"]


def test_premature_term_in_narration_is_flagged():
    text = "It was a slow arvo in the town."
    result = scan(text, TERMS, "OUTSIDER")
    assert any(f["term"] == "arvo" and f["line"] == 1 for f in result["flags"])


def test_in_stage_term_is_not_flagged():
    text = "It was a slow arvo in the town."
    result = scan(text, TERMS, "SETTLING")     # arvo ok from SETTLING
    assert not any(f["term"] == "arvo" for f in result["flags"])


def test_term_inside_dialogue_is_not_flagged():
    text = '"See you this arvo," she said.'
    result = scan(text, TERMS, "OUTSIDER")
    assert not any(f["term"] == "arvo" for f in result["flags"])


def test_auto_detectable_false_is_inspector_note_not_flag():
    text = "He was a bit of a bogan, she thought."
    result = scan(text, TERMS, "OUTSIDER")
    assert not any(f["term"] == "bogan" for f in result["flags"])
    assert any(n["term"] == "bogan" for n in result["inspector_notes"])


def test_word_boundary_matches_whole_word_only():
    terms = [{"term": "servo", "narration_ok_from_stage": "SETTLING", "auto_detectable": True}]
    # '\b servo \b' matches the standalone word but NOT the plural 'servos'
    # (trailing 's' means no word boundary after 'servo').
    text = "Two servos lined the road; she stopped at the servo."
    result = scan(text, terms, "OUTSIDER")
    hits = [f for f in result["flags"] if f["term"] == "servo"]
    assert len(hits) == 1


def test_multiword_term_flagged():
    text = "She still didn't understand the footy."
    result = scan(text, TERMS, "SETTLING")   # the footy ok only from BELONGING
    assert any(f["term"] == "the footy" for f in result["flags"])


def test_main_writes_evidence_only_verdict(tmp_path):
    from scripts.lexicon_check import main
    lexicon = tmp_path / "lex.yaml"
    lexicon.write_text(
        "terms:\n"
        "  - term: arvo\n    narration_ok_from_stage: SETTLING\n    auto_detectable: true\n",
        encoding="utf-8")
    canon = tmp_path / "canon.md"
    canon.write_text("<!-- canon-meta: {fluency_stage: OUTSIDER} -->\n", encoding="utf-8")
    chap = tmp_path / "ch.md"
    chap.write_text("It was a slow arvo.\n", encoding="utf-8")
    out = tmp_path / "reviews"
    rc = main([str(chap), "--out", str(out), "--lexicon", str(lexicon),
               "--canon-core", str(canon), "--target", "book-01/ch-01"])
    assert rc == 0
    verdict = (out / "lexicon-fluency.md").read_text(encoding="utf-8")
    assert "producer: lexicon_check.py" in verdict
    assert "kind: deterministic-checker" in verdict
    assert "BLOCKING:" not in verdict          # evidence-only, never blocks
    assert "arvo" in verdict


def test_main_explicit_paths_need_no_series_root(tmp_path, monkeypatch):
    # Run from a directory with no .penny marker: when the caller supplies
    # explicit --lexicon/--canon-core, main() must not resolve series_root()
    # for defaults it isn't using (regression: eager argparse default eval).
    from scripts.lexicon_check import main
    monkeypatch.chdir(tmp_path)  # no .penny at or above here
    lexicon = tmp_path / "lex.yaml"
    lexicon.write_text(
        "terms:\n  - term: arvo\n    narration_ok_from_stage: SETTLING\n    auto_detectable: true\n",
        encoding="utf-8")
    canon = tmp_path / "canon.md"
    canon.write_text("<!-- canon-meta: {fluency_stage: OUTSIDER} -->\n", encoding="utf-8")
    chap = tmp_path / "ch.md"
    chap.write_text("A slow arvo.\n", encoding="utf-8")
    out = tmp_path / "reviews"
    rc = main([str(chap), "--out", str(out), "--lexicon", str(lexicon),
               "--canon-core", str(canon), "--target", "book-01/ch-01"])
    assert rc == 0
    assert (out / "lexicon-fluency.md").is_file()


def test_missing_stage_hard_fails(tmp_path):
    from scripts.lexicon_check import current_stage
    canon = tmp_path / "canon.md"
    canon.write_text("# no header\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        current_stage(canon)


from scripts.lexicon_check import validate_lexicon, prose_stage, stage_drift


def test_validate_names_every_offender():
    terms = [
        {"term": "ok", "narration_ok_from_stage": "SETTLING", "auto_detectable": True},
        {"term": "bad1", "auto_detectable": True},                    # missing stage
        {"narration_ok_from_stage": "SETTLING", "auto_detectable": True},  # missing term
        {"term": "bad3", "narration_ok_from_stage": "SETTLING"},      # missing auto_detectable
        {"term": "bad4", "narration_ok_from_stage": "NOPE", "auto_detectable": True},  # bad stage
    ]
    errors = validate_lexicon(terms)
    blob = " | ".join(errors)
    assert "bad1" in blob and "bad3" in blob and "bad4" in blob
    assert "term" in blob                       # the missing-term entry is named
    assert len(errors) >= 4                       # every offender reported, not just first


def test_validate_clean_lexicon_is_empty():
    terms = [{"term": "arvo", "narration_ok_from_stage": "SETTLING", "auto_detectable": True}]
    assert validate_lexicon(terms) == []


def test_prose_stage_reads_bolded_stage():
    text = "## Fluency stage\n- **OUTSIDER** (Books 1-2): narration is standard English.\n"
    assert prose_stage(text) == "OUTSIDER"


def test_stage_drift_detects_mismatch():
    text = ("<!-- canon-meta: {fluency_stage: SETTLING} -->\n"
            "## Fluency stage\n- **OUTSIDER** (Books 1-2): ...\n")
    assert stage_drift(text) is not None
    aligned = ("<!-- canon-meta: {fluency_stage: OUTSIDER} -->\n"
               "## Fluency stage\n- **OUTSIDER** (Books 1-2): ...\n")
    assert stage_drift(aligned) is None


def test_main_fails_loud_on_malformed_lexicon(tmp_path):
    """Per-chapter path must exit with a clear message when a lexicon entry is missing
    a required field (belt-and-suspenders, Spec §5.1)."""
    from scripts.lexicon_check import main
    lexicon = tmp_path / "lex.yaml"
    lexicon.write_text(
        "terms:\n"
        "  - term: arvo\n    auto_detectable: true\n",  # missing narration_ok_from_stage
        encoding="utf-8")
    canon = tmp_path / "canon.md"
    canon.write_text("<!-- canon-meta: {fluency_stage: OUTSIDER} -->\n", encoding="utf-8")
    chap = tmp_path / "ch.md"
    chap.write_text("It was a slow arvo.\n", encoding="utf-8")
    out = tmp_path / "reviews"
    with pytest.raises(SystemExit):
        main([str(chap), "--out", str(out), "--lexicon", str(lexicon),
              "--canon-core", str(canon), "--target", "book-01/ch-01"])
