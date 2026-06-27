import hashlib
import shutil

import pytest

from scripts import preflight

SRC = preflight.REPO


def _scaffold_lockable(tmp_path, *, ledger_fixture, valid_lexicon=True):
    """Build a tmp repo able to run lock-mystery: real run-config, real canon-core,
    a (valid or malformed) lexicon, a resolvable character corpus, and a ledger."""
    # run-config + canon-core copied from the real repo (both valid).
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "config/run-config.md", tmp_path / "config/run-config.md")
    (tmp_path / "series/continuity").mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "series/continuity/canon-core.md",
                tmp_path / "series/continuity/canon-core.md")
    # lexicon: real (valid) or a malformed stub.
    (tmp_path / "config/setting-pack").mkdir(parents=True, exist_ok=True)
    if valid_lexicon:
        shutil.copy(SRC / "config/setting-pack/lexicon.yaml",
                    tmp_path / "config/setting-pack/lexicon.yaml")
    else:
        (tmp_path / "config/setting-pack/lexicon.yaml").write_text(
            "terms:\n  - {term: jumper}\n", encoding="utf-8")  # missing required fields
    # resolvable character corpus.
    cc = tmp_path / "series/continuity/characters"
    cc.mkdir(parents=True, exist_ok=True)
    for cid in ("margaret", "thomas", "edwin-tilley"):
        (cc / f"{cid}.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    # the proposed (unlocked) ledger.
    wd = tmp_path / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    shutil.copy(ledger_fixture, wd / "book-01.yaml")
    return wd / "book-01.yaml"


FAIR = SRC / "tests/fixtures/ledgers/fair.yaml"
UNFAIR = SRC / "tests/fixtures/ledgers/unfair_clue_after_reveal.yaml"


def test_lock_mystery_writes_lock_when_valid(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    assert preflight.cmd_lock_mystery("01", repo_root=tmp_path) == 0
    assert preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_fairplay_fails(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=UNFAIR, valid_lexicon=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "fairplay failed" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_lexicon_invalid(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "lexicon" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_canon_core_missing(tmp_path):
    _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    (tmp_path / "series/continuity/canon-core.md").unlink()
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "canon-core" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def test_lock_mystery_no_lock_when_culprit_unresolvable(tmp_path):
    led = _scaffold_lockable(tmp_path, ledger_fixture=FAIR, valid_lexicon=True)
    # remove margaret's entity so existence resolution blocks.
    (tmp_path / "series/continuity/characters/margaret.md").unlink()
    with pytest.raises(SystemExit) as e:
        preflight.cmd_lock_mystery("01", repo_root=tmp_path)
    assert "culprit id 'margaret'" in str(e.value)
    assert not preflight.lock_path("01", tmp_path).is_file()


def _make_book(root, book="01", *, populated=True, locked=True):
    wd = root / "series/whodunit"
    wd.mkdir(parents=True, exist_ok=True)
    led = wd / f"book-{book}.yaml"
    led.write_text("book: '01'\nculprit: margaret\n" if populated else "", encoding="utf-8")
    if locked:
        ld = root / ".penny/locks"
        ld.mkdir(parents=True, exist_ok=True)
        (ld / f"book-{book}.mystery.lock").write_text("ok\n", encoding="utf-8")
    return led


def test_draft_passes_when_populated_and_locked(tmp_path):
    _make_book(tmp_path, populated=True, locked=True)
    assert preflight.cmd_draft("01", "01", repo_root=tmp_path) == 0


def test_draft_fails_without_lock(tmp_path):
    _make_book(tmp_path, populated=True, locked=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no lock" in str(e.value)


def test_draft_fails_without_ledger(tmp_path):
    (tmp_path / "series/whodunit").mkdir(parents=True, exist_ok=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "no ledger" in str(e.value)


def test_draft_fails_when_ledger_unpopulated(tmp_path):
    _make_book(tmp_path, populated=False, locked=True)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_draft("01", "01", repo_root=tmp_path)
    assert "unpopulated" in str(e.value)


def _make_run_config(root, *, drafting, final_read):
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "run-config.md").write_text(
        "# fixture run-config\n\n```yaml\n"
        f"drafting_model:   {drafting}\n"
        f"final_read_model: {final_read}\n"
        "```\n",
        encoding="utf-8",
    )


def _make_chapter(root, book, ch, drafted_by):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.draft.md").write_text(
        f"---\ndrafted_by: {drafted_by}\n---\nprose\n", encoding="utf-8")


def _make_final_read(root, book, read_by):
    d = root / "output" / f"book-{book}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"book-{book}.final-read.md").write_text(
        f"---\nread_by: {read_by}\n---\nholistic read\n", encoding="utf-8")


def test_assemble_green(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "codex")
    assert preflight.cmd_assemble("01", repo_root=tmp_path) == 0


def test_assemble_config_invariant_fails_before_stamps(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="claude-opus")
    # no chapters at all — must still fail on the config compare
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "equals drafting_model" in str(e.value)


def test_assemble_drift_configured_final_reader_drafted(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_chapter(tmp_path, "01", "02", "codex")  # codex drafted ch-02 — config lies
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "configured final_read_model 'codex'" in str(e.value)


def test_assemble_read_by_collides_with_drafter(tmp_path):
    _make_run_config(tmp_path, drafting="claude-opus", final_read="codex")
    _make_chapter(tmp_path, "01", "01", "claude-opus")
    _make_final_read(tmp_path, "01", "claude-opus")  # final read done by a drafter
    with pytest.raises(SystemExit) as e:
        preflight.cmd_assemble("01", repo_root=tmp_path)
    assert "final-read model 'claude-opus'" in str(e.value)


def _make_gate(root, book, ch, verdict):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"ch-{ch}.gate.md").write_text(
        f"---\nproducer: review_gate.py\nkind: gate-summary\n"
        f"target: book-{book}/ch-{ch}\ngate: {verdict}\nblocking_count: 0\n"
        f"schema: penny-verdict/1\n---\n\n- {verdict}: 0 blocking issue(s)\n",
        encoding="utf-8",
    )


def test_finalize_passes_on_passing_gate(tmp_path):   # REPLACES the old same-named test
    _make_gate(tmp_path, "01", "07", "PASS")
    _clear_for(tmp_path, "01", "07")
    assert preflight.cmd_finalize("01", "07", repo_root=tmp_path) == 0


def test_finalize_blocks_on_held_gate(tmp_path):
    _make_gate(tmp_path, "01", "07", "HOLD")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "did not pass" in str(e.value)


def test_finalize_blocks_when_gate_missing(tmp_path):
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "no gate" in str(e.value)


def test_finalize_blocks_without_dev_clearance(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    _write_draft(tmp_path, "01", "07")          # gate PASS + draft, but never cleared
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "developmental clearance" in str(e.value)


def test_finalize_blocks_on_stale_dev_clearance(tmp_path):
    _make_gate(tmp_path, "01", "07", "PASS")
    _clear_for(tmp_path, "01", "07", body="original\n")
    _write_draft(tmp_path, "01", "07", body="REVISED after clearance\n")  # hash now differs
    with pytest.raises(SystemExit) as e:
        preflight.cmd_finalize("01", "07", repo_root=tmp_path)
    assert "stale" in str(e.value)


# ---------------------------------------------------------------------------
# approve-book tests
# ---------------------------------------------------------------------------
from scripts import assemble_book, revision_priority


def _approvable(tmp_path, *, read_by="codex", standalone="yes",
                with_report=True, with_manuscript=True):
    """Build a book-99 tree that approve-book should accept."""
    book = tmp_path / "output" / "book-99"
    (book / "chapters").mkdir(parents=True, exist_ok=True)
    if with_manuscript:
        assemble_book.manuscript_path("99", tmp_path).write_text(
            "---\nschema: penny-manuscript/1\nbook: 99\nchapters: 1\n"
            "drafted_by: [claude-opus]\nassembled_at: 2026-06-21T00:00:00+00:00\n---\n\n"
            "# Chapter 1\n\nprose\n", encoding="utf-8")
    assemble_book.final_read_path("99", tmp_path).write_text(
        f"---\nschema: penny-final-read/1\nread_by: {read_by}\n"
        f"standalone: {standalone}\nmystery_resolved: yes\nthread_left_open: yes\n---\n"
        "## Holistic verdict\nGood.\n", encoding="utf-8")
    if with_report:
        revision_priority.report_path("99", tmp_path).parent.mkdir(parents=True, exist_ok=True)
        revision_priority.report_path("99", tmp_path).write_text(
            "---\nschema: penny-revision-priority/1\nescalations: 0\n---\n", encoding="utf-8")


def test_approve_book_mints_cert_when_green(tmp_path):
    _approvable(tmp_path)
    assert preflight.cmd_approve_book("99", repo_root=tmp_path) == 0
    cert = tmp_path / ".penny/locks/book-99.approved"
    assert cert.is_file()


def test_approve_book_fails_without_manuscript(tmp_path):
    _approvable(tmp_path, with_manuscript=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "no manuscript" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_on_hedged_final_read(tmp_path):
    _approvable(tmp_path, standalone="mostly")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "standalone" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_when_read_by_drafted(tmp_path):
    _approvable(tmp_path, read_by="claude-opus")     # drafted_by is [claude-opus]
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "appears in drafted_by" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


def test_approve_book_fails_without_report(tmp_path):
    _approvable(tmp_path, with_report=False)
    with pytest.raises(SystemExit) as e:
        preflight.cmd_approve_book("99", repo_root=tmp_path)
    assert "revision-priority" in str(e.value)
    assert not (tmp_path / ".penny/locks/book-99.approved").exists()


# ---------------------------------------------------------------------------
# draft sha256 + dev path helpers
# ---------------------------------------------------------------------------

def _write_draft(root, book, ch, body="prose\n"):
    d = root / "output" / f"book-{book}" / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"ch-{ch}.draft.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_draft_sha256_matches_file_bytes(tmp_path):
    p = _write_draft(tmp_path, "01", "07", body="hello draft\n")
    expected = hashlib.sha256(p.read_bytes()).hexdigest()
    assert preflight.draft_sha256("01", "07", repo_root=tmp_path) == expected


def test_draft_sha256_fails_when_draft_missing(tmp_path):
    with pytest.raises(SystemExit) as e:
        preflight.draft_sha256("01", "07", repo_root=tmp_path)
    assert "no draft" in str(e.value)


def test_dev_path_helpers_shape(tmp_path):
    rep = preflight.dev_report_path("01", "07", tmp_path)
    cert = preflight.dev_clear_path("01", "07", tmp_path)
    assert rep.name == "developmental-edit.md"
    assert rep.parent.name == "ch-07.reviews"
    assert cert.name == "book-01.ch-07.dev-clear"


# ---------------------------------------------------------------------------
# clear-dev tests
# ---------------------------------------------------------------------------

def _write_dev_report(root, book, ch, reviewed_sha, *, score=3):
    rep = preflight.dev_report_path(book, ch, root)
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(
        f"---\nproducer: developmental-editor\nkind: developmental\n"
        f"target: book-{book}/ch-{ch}\nschema: penny-verdict/1\nscore: {score}\n"
        f"reviewed_draft_sha256: {reviewed_sha}\n---\n\n- setting grounding thin\n",
        encoding="utf-8",
    )
    return rep


def _clear_for(root, book, ch, body="prose\n"):
    """Draft + dev report + minted clearance, all hash-consistent."""
    _write_draft(root, book, ch, body=body)
    sha = preflight.draft_sha256(book, ch, repo_root=root)
    _write_dev_report(root, book, ch, sha)
    assert preflight.cmd_clear_dev(book, ch, repo_root=root) == 0


def test_clear_dev_mints_cert_when_hash_matches(tmp_path):
    _write_draft(tmp_path, "01", "07", body="reviewed body\n")
    sha = preflight.draft_sha256("01", "07", repo_root=tmp_path)
    _write_dev_report(tmp_path, "01", "07", sha)
    assert preflight.cmd_clear_dev("01", "07", repo_root=tmp_path) == 0
    cert = preflight.dev_clear_path("01", "07", tmp_path)
    assert cert.is_file()
    from scripts.penny_meta import parse_frontmatter
    assert parse_frontmatter(cert.read_text(encoding="utf-8"))["cleared_draft_sha256"] == sha


def test_clear_dev_fails_without_report(tmp_path):
    _write_draft(tmp_path, "01", "07")
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "no developmental read" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()


def test_clear_dev_fails_on_stale_report(tmp_path):
    _write_dev_report(tmp_path, "01", "07", "deadbeef")          # report for an old draft
    _write_draft(tmp_path, "01", "07", body="a DIFFERENT body\n")  # draft has since changed
    with pytest.raises(SystemExit) as e:
        preflight.cmd_clear_dev("01", "07", repo_root=tmp_path)
    assert "stale" in str(e.value)
    assert not preflight.dev_clear_path("01", "07", tmp_path).exists()
