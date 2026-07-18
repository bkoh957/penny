from pathlib import Path

import pytest

from scripts import penny_whodunit

FIX = Path(__file__).resolve().parent / "fixtures"
LEDGERS = FIX / "ledgers"


def test_public_api_exists():
    for name in ("load_ledger", "clues_by_chapter", "ledger_identity",
                 "file_sha256"):
        assert callable(getattr(penny_whodunit, name))


def test_ledger_identity_absent_file_is_none_sentinel(tmp_path):
    assert penny_whodunit.ledger_identity(tmp_path / "missing.yaml") == "none"


# ---- ported from the deleted brief compiler's tests: load_ledger's guard must
# reach the shape of clue_schedule/red_herrings, not just the top level. ----

def test_load_ledger_raises_named_error_for_malformed_yaml(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: [ { unterminated\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        penny_whodunit.load_ledger(ledger)


def test_load_ledger_raises_named_error_for_top_level_list(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        penny_whodunit.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_clue_schedule_is_not_a_list(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\nclue_schedule: 'not a list'\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        penny_whodunit.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_clue_schedule_entry_is_not_a_mapping(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text(
        "book: '01'\nclue_schedule:\n  - just-a-string\n  - 42\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        penny_whodunit.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_red_herrings_is_not_a_list(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\nred_herrings: 'not a list'\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        penny_whodunit.load_ledger(ledger)


def test_load_ledger_raises_named_error_when_red_herrings_entry_is_not_a_mapping(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text(
        "book: '01'\nred_herrings:\n  - just-a-string\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-ledger"):
        penny_whodunit.load_ledger(ledger)


def test_load_ledger_reads_a_real_locked_ledger_fixture():
    data = penny_whodunit.load_ledger(LEDGERS / "fair.yaml")
    assert data["culprit"] == "margaret"
    assert len(data["clue_schedule"]) == 2


def test_unreadable_ledger_raises_named_error(tmp_path):
    import os
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text("book: '01'\n", encoding="utf-8")
    ledger.chmod(0o000)
    try:
        if os.access(ledger, os.R_OK):
            pytest.skip("running with elevated privileges; chmod 0o000 doesn't block reads")
        with pytest.raises(ValueError, match=r"unreadable-ledger"):
            penny_whodunit.load_ledger(ledger)
    finally:
        ledger.chmod(0o644)


# ---- clues_by_chapter: {chapter: [clue ids]} from clue_schedule + red_herrings ----

def test_clues_by_chapter_groups_clues_and_red_herrings_by_plant_chapter():
    out = penny_whodunit.clues_by_chapter(LEDGERS / "fair.yaml")
    assert out[5] == ["clue-torn-ticket"]
    assert out[9] == ["clue-tide-table"]
    assert out[7] == ["rh-the-neighbour"]


def test_clues_by_chapter_raises_named_error_on_null_plant_chapter(tmp_path):
    ledger = tmp_path / "book-01.yaml"
    ledger.write_text(
        "book: '01'\nclue_schedule:\n"
        "  - { id: clue-tide-table, plant_chapter: null, pays_off_chapter: 2, necessary: true }\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed-plant-chapter"):
        penny_whodunit.clues_by_chapter(ledger)


# ---- ledger_identity: sha256 hex, or the "none" sentinel for an absent ledger.
# packet_assemble.stale_packets compares this exact sentinel, so it must never
# change spelling. ------------------------------------------------------------

def test_ledger_identity_matches_file_sha256_for_an_existing_file():
    path = LEDGERS / "fair.yaml"
    assert penny_whodunit.ledger_identity(path) == penny_whodunit.file_sha256(path)


def test_ledger_identity_changes_when_the_file_changes(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_text("book: '01'\n", encoding="utf-8")
    first = penny_whodunit.ledger_identity(a)
    a.write_text("book: '02'\n", encoding="utf-8")
    second = penny_whodunit.ledger_identity(a)
    assert first != second


def test_file_sha256_is_a_64_char_hex_digest():
    digest = penny_whodunit.file_sha256(LEDGERS / "fair.yaml")
    assert len(digest) == 64
    int(digest, 16)  # raises ValueError if not hex
