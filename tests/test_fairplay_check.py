import subprocess
import sys
from pathlib import Path

import pytest

from scripts.fairplay_check import check_fairplay, load_fraction

REPO = Path(__file__).resolve().parents[1]
LED = REPO / "tests/fixtures/ledgers"
RUN_CONFIG = REPO / "config/run-config.md"
FIXTURE_REPO = REPO / "tests/fixtures/whodunit-repo"


def _blocking(result):
    return result["blocking"]


def _write_chars(root, *, static=(), continuity=()):
    for cid in static:
        d = root / "series/characters"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{cid}.static.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    for cid in continuity:
        d = root / "series/continuity/characters"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{cid}.md").write_text("---\nid: x\n---\n", encoding="utf-8")


def test_all_ids_resolve_no_existence_block():
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert r["blocking"] == []


def test_culprit_resolves_via_static(tmp_path):
    _write_chars(tmp_path, static=("margaret", "thomas", "edwin-tilley"))
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert r["blocking"] == []


def test_culprit_resolves_via_continuity(tmp_path):
    _write_chars(tmp_path, continuity=("margaret", "thomas", "edwin-tilley"))
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert r["blocking"] == []


def test_unresolvable_culprit_blocks(tmp_path):
    _write_chars(tmp_path, continuity=("thomas", "edwin-tilley"))  # margaret missing
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert any("culprit id 'margaret'" in b for b in r["blocking"])


def test_unresolvable_suspect_blocks(tmp_path):
    _write_chars(tmp_path, continuity=("margaret", "edwin-tilley"))  # thomas missing
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert any("suspect id 'thomas'" in b for b in r["blocking"])


def test_existence_is_presence_only_not_semantic(tmp_path):
    # A resolvable culprit produces NO existence block regardless of plausibility —
    # the resolver checks the id has a home, never reads what is in it.
    _write_chars(tmp_path, static=("margaret", "thomas", "edwin-tilley"))
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=tmp_path)
    assert not any("id '" in b for b in r["blocking"])


def test_fair_ledger_has_no_blocking():
    r = check_fairplay(LED / "fair.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert _blocking(r) == []


def test_necessary_clue_after_reveal_blocks():
    r = check_fairplay(LED / "unfair_clue_after_reveal.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert any("clue-tide-table" in b for b in _blocking(r))


def test_culprit_at_reveal_blocks_floor_only_once():
    r = check_fairplay(LED / "culprit_at_reveal.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    culprit_blocks = [b for b in _blocking(r) if "culprit" in b.lower()]
    # Floor fails -> exactly one culprit blocking line (seed must NOT also fire).
    assert len(culprit_blocks) == 1


def test_culprit_past_fraction_blocks_seed():
    r = check_fairplay(LED / "culprit_past_fraction.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert any("fraction" in b.lower() or "half" in b.lower() or "by chapter" in b.lower()
               for b in _blocking(r))


def test_malformed_ledger_blocks_and_stops():
    r = check_fairplay(LED / "malformed.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert _blocking(r)                     # at least one blocking line
    assert any("malformed" in b.lower() or "reveal" in b.lower() for b in _blocking(r))


def test_culprit_alibi_always_holds_blocks():
    r = check_fairplay(LED / "culprit_alibi_holds.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
    assert any("alibi" in b.lower() for b in _blocking(r))


def test_mention_before_appearance_is_evidence_not_blocking():
    r = check_fairplay(LED / "mention_before_appearance.yaml", culprit_by_fraction=0.5, repo_root=FIXTURE_REPO)
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
