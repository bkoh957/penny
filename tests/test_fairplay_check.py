import subprocess
import sys
from pathlib import Path

import pytest

from scripts.fairplay_check import check_fairplay, load_fraction

REPO = Path(__file__).resolve().parents[1]
LED = REPO / "tests/fixtures/ledgers"
RUN_CONFIG = REPO / "config/run-config.md"


def _blocking(result):
    return result["blocking"]


def test_fair_ledger_has_no_blocking():
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5)
    assert _blocking(r) == []


def test_necessary_clue_after_reveal_blocks():
    r = check_fairplay(LED / "unfair_clue_after_reveal.yaml", culprit_by_fraction=0.5)
    assert any("clue-tide-table" in b for b in _blocking(r))


def test_culprit_at_reveal_blocks_floor_only_once():
    r = check_fairplay(LED / "culprit_at_reveal.yaml", culprit_by_fraction=0.5)
    culprit_blocks = [b for b in _blocking(r) if "culprit" in b.lower()]
    # Floor fails -> exactly one culprit blocking line (seed must NOT also fire).
    assert len(culprit_blocks) == 1


def test_culprit_past_fraction_blocks_seed():
    r = check_fairplay(LED / "culprit_past_fraction.yaml", culprit_by_fraction=0.5)
    assert any("fraction" in b.lower() or "half" in b.lower() or "by chapter" in b.lower()
               for b in _blocking(r))


def test_malformed_ledger_blocks_and_stops():
    r = check_fairplay(LED / "malformed.yaml", culprit_by_fraction=0.5)
    assert _blocking(r)                     # at least one blocking line
    assert any("malformed" in b.lower() or "reveal" in b.lower() for b in _blocking(r))


def test_culprit_alibi_always_holds_blocks():
    r = check_fairplay(LED / "culprit_alibi_holds.yaml", culprit_by_fraction=0.5)
    assert any("alibi" in b.lower() for b in _blocking(r))


def test_mention_before_appearance_is_evidence_not_blocking():
    r = check_fairplay(LED / "mention_before_appearance.yaml", culprit_by_fraction=0.5)
    assert _blocking(r) == []
    assert any("mention" in n.lower() for n in r["notes"])


def test_load_fraction_hard_fails_if_absent(tmp_path):
    bad = tmp_path / "run-config.md"
    bad.write_text("# no fraction here\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_fraction(bad)


def test_load_fraction_reads_run_config():
    assert load_fraction(RUN_CONFIG) == 0.5


def test_cli_writes_blocking_verdict(tmp_path):
    rc = subprocess.run(
        [sys.executable, str(REPO / "scripts/fairplay_check.py"),
         str(LED / "unfair_clue_after_reveal.yaml"),
         "--out", str(tmp_path), "--run-config", str(RUN_CONFIG),
         "--target", "book-01/ch-22"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert rc.returncode == 0, rc.stderr
    verdict = (tmp_path / "fairplay.md").read_text(encoding="utf-8")
    assert any(ln.startswith("BLOCKING:") for ln in verdict.splitlines())
